"""
Tests for IVEO one-way reliability improvements:
- telegram repeat (handsender-style)
- gateway 'executed' acknowledgement handling
- duty-cycle guard before sending
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

from selve import Selve
from selve.util.protocol import DutyMode, DriveCommandIveo, CommunicationType, SelveTypes


def _make_selve():
    s = Selve(port=None, discover=False, develop=False, logger=Mock())
    s.iveoRepeatDelay = 0  # keep tests fast
    return s


def _resp(executed=True):
    return SimpleNamespace(executed=executed)


class TestAwaitDutyCycle:
    @pytest.mark.asyncio
    async def test_returns_true_immediately_when_not_blocked(self):
        s = _make_selve()
        s.sendingBlocked = DutyMode.NOT_BLOCKED
        assert await s._await_duty_cycle() is True

    @pytest.mark.asyncio
    async def test_returns_false_after_timeout_when_blocked(self):
        s = _make_selve()
        s.sendingBlocked = DutyMode.BLOCKED
        assert await s._await_duty_cycle(timeout=0.1) is False

    @pytest.mark.asyncio
    async def test_returns_true_when_block_clears(self):
        s = _make_selve()
        s.sendingBlocked = DutyMode.BLOCKED

        async def clear_soon():
            await asyncio.sleep(0.1)
            s.sendingBlocked = DutyMode.NOT_BLOCKED

        asyncio.create_task(clear_soon())
        assert await s._await_duty_cycle(timeout=2.0) is True


class TestSendIveoCommand:
    @pytest.mark.asyncio
    async def test_repeats_telegram_iveo_repeat_times(self):
        s = _make_selve()
        s.iveoRepeat = 3
        calls = []

        async def fake_exec(cmd):
            calls.append(cmd)
            return _resp(executed=True)

        s._executeCommandSyncWithResponse = fake_exec
        ok = await s._send_iveo_command(5, DriveCommandIveo.DOWN)
        assert ok is True
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_respects_custom_repeat_count(self):
        s = _make_selve()
        s.iveoRepeat = 1
        calls = []

        async def fake_exec(cmd):
            calls.append(cmd)
            return _resp(executed=True)

        s._executeCommandSyncWithResponse = fake_exec
        await s._send_iveo_command(2, DriveCommandIveo.UP)
        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_confirmed_false_when_gateway_never_executes(self):
        s = _make_selve()
        s.iveoRepeat = 2
        s._executeCommandSyncWithResponse = AsyncMock(return_value=_resp(executed=False))
        ok = await s._send_iveo_command(5, DriveCommandIveo.DOWN)
        assert ok is False
        # warning logged about unconfirmed transmission
        assert s._LOGGER.warning.called

    @pytest.mark.asyncio
    async def test_confirmed_true_if_any_attempt_executes(self):
        s = _make_selve()
        s.iveoRepeat = 3
        seq = [_resp(executed=False), _resp(executed=True), _resp(executed=False)]

        async def fake_exec(cmd):
            return seq.pop(0)

        s._executeCommandSyncWithResponse = fake_exec
        assert await s._send_iveo_command(5, DriveCommandIveo.DOWN) is True

    @pytest.mark.asyncio
    async def test_handles_false_response_from_timeout(self):
        s = _make_selve()
        s.iveoRepeat = 2
        # _executeCommandSyncWithResponse returns False on timeout
        s._executeCommandSyncWithResponse = AsyncMock(return_value=False)
        ok = await s._send_iveo_command(5, DriveCommandIveo.STOP)
        assert ok is False

    @pytest.mark.asyncio
    async def test_stops_sending_when_duty_blocked(self):
        s = _make_selve()
        s.iveoRepeat = 3
        s.sendingBlocked = DutyMode.BLOCKED  # never clears
        calls = []

        async def fake_exec(cmd):
            calls.append(cmd)
            return _resp(executed=True)

        s._executeCommandSyncWithResponse = fake_exec
        # shorten the duty wait so the test is fast
        s._await_duty_cycle = AsyncMock(return_value=False)
        ok = await s._send_iveo_command(5, DriveCommandIveo.DOWN)
        assert ok is False
        assert calls == []  # nothing sent while blocked


class TestMoveDeviceUsesHelper:
    @pytest.mark.asyncio
    async def test_iveo_move_down_uses_repeat_helper(self):
        s = _make_selve()
        s._send_iveo_command = AsyncMock(return_value=True)

        device = SimpleNamespace(
            id=5,
            communicationType=CommunicationType.IVEO,
            state=None, value=0, targetValue=0,
        )
        # register so the optimistic setDeviceState/Value lookups resolve
        s.devices[SelveTypes.IVEO.value][5] = device

        await s.moveDeviceDown(device)
        s._send_iveo_command.assert_awaited_once_with(5, DriveCommandIveo.DOWN)

    @pytest.mark.asyncio
    async def test_commeo_move_down_does_not_use_iveo_helper(self):
        s = _make_selve()
        s._send_iveo_command = AsyncMock(return_value=True)
        s.executeCommand = AsyncMock()
        s._start_movement_polling = Mock()  # avoid spawning a background task

        device = SimpleNamespace(
            id=3,
            communicationType=CommunicationType.COMMEO,
            state=None,
        )
        s.devices[SelveTypes.DEVICE.value][3] = device

        await s.moveDeviceDown(device)
        s._send_iveo_command.assert_not_awaited()
        s.executeCommand.assert_awaited_once()
