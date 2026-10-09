"""
Commeo drive commands the gateway reports as failed (e.g. "Radio line is busy")
must be re-sent automatically instead of being silently lost.
"""
import asyncio
import logging
import time
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

import selve as selve_mod
from selve import Selve
from selve.commands.command import CommandResultResponse
from selve.util.protocol import (
    CommunicationType, DeviceCommandType, DriveCommandCommeo, DriveCommandIveo,
)


@pytest.fixture(autouse=True)
def fast_delays(monkeypatch):
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_BASE_DELAY", 0.02)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_STAGGER", 0.05)


def _make_selve():
    s = Selve(port=None, discover=False, develop=False, logger=Mock())
    s.executeCommand = AsyncMock()
    s._start_movement_polling = Mock()
    return s


def _dev(id, comm=CommunicationType.COMMEO):
    return SimpleNamespace(id=id, communicationType=comm, state=None)


def _result(success=(), failed=()):
    r = CommandResultResponse.__new__(CommandResultResponse)
    r.command = DriveCommandCommeo.DRIVEDOWN
    r.commandType = DeviceCommandType.MANUAL
    r.executed = True
    r.successIds = list(success)
    r.failedIds = list(failed)
    return r


async def _drain(s):
    while s._commeo_retry_tasks:
        await asyncio.gather(*list(s._commeo_retry_tasks))


class TestCommeoRetry:
    async def test_failed_id_is_resent_with_same_command(self):
        s = _make_selve()
        await s.moveDeviceDown(_dev(3))
        cmd = s.executeCommand.await_args.args[0]
        s._handleCommandResult(_result(failed=[3]))
        await _drain(s)
        assert s.executeCommand.await_count == 2
        assert s.executeCommand.await_args.args[0] is cmd
        s._start_movement_polling.assert_called_with(3)

    async def test_success_clears_pending(self):
        s = _make_selve()
        await s.moveDeviceUp(_dev(3))
        assert 3 in s._commeo_pending
        s._handleCommandResult(_result(success=[3]))
        assert 3 not in s._commeo_pending
        s._handleCommandResult(_result(failed=[3]))
        await _drain(s)
        assert s.executeCommand.await_count == 1

    async def test_retries_capped_then_warning(self):
        s = _make_selve()
        await s.moveDeviceDown(_dev(3))
        for _ in range(3):
            s._handleCommandResult(_result(failed=[3]))
            await _drain(s)
        assert s.executeCommand.await_count == 3  # original + 2 retries
        assert 3 not in s._commeo_pending
        s._LOGGER.warning.assert_called_once()

    async def test_stale_entry_not_retried(self):
        s = _make_selve()
        await s.moveDeviceDown(_dev(3))
        s._commeo_pending[3]["sent_at"] = time.monotonic() - 31
        s._handleCommandResult(_result(failed=[3]))
        await _drain(s)
        assert s.executeCommand.await_count == 1

    async def test_iveo_never_tracked(self):
        s = _make_selve()
        s._send_iveo_command = AsyncMock(return_value=False)
        s.setDeviceState = Mock()
        iveo = _dev(4, CommunicationType.IVEO)
        for call in (s.moveDeviceUp, s.moveDeviceDown, s.moveDevicePos1,
                     s.moveDevicePos2, s.stopDevice):
            await call(iveo)
        assert s._commeo_pending == {}

    async def test_new_command_replaces_entry(self):
        s = _make_selve()
        await s.moveDeviceDown(_dev(3))
        s._handleCommandResult(_result(failed=[3]))
        await _drain(s)
        assert s._commeo_pending[3]["attempts"] == 1
        await s.moveDeviceUp(_dev(3))
        assert s._commeo_pending[3]["attempts"] == 0

    async def test_other_commeo_commands_tracked(self):
        s = _make_selve()
        s.updateCommeoDeviceValuesAsync = AsyncMock()
        d = _dev(5)
        for call in (lambda: s.moveDevicePos(d, 50), lambda: s.moveDeviceStepUp(d, 10),
                     lambda: s.moveDeviceStepDown(d, 10), lambda: s.stopDevice(d),
                     lambda: s.moveDevicePos1(d), lambda: s.moveDevicePos2(d)):
            s._commeo_pending.clear()
            await call()
            assert s._commeo_pending[5]["command"] is s.executeCommand.await_args.args[0]

    async def test_two_failed_ids_are_staggered(self):
        s = _make_selve()
        await s.moveDeviceDown(_dev(1))
        await s.moveDeviceDown(_dev(2))
        s.executeCommand.reset_mock()
        times = {}

        async def record(cmd):
            times[cmd.id if hasattr(cmd, "id") else id(cmd)] = time.monotonic()
        s.executeCommand.side_effect = record
        t0 = time.monotonic()
        s._handleCommandResult(_result(failed=[1, 2]))
        await _drain(s)
        t = sorted(times.values())
        assert len(t) == 2
        assert t[1] - t[0] >= 0.04

    def test_no_running_loop_is_skipped(self):
        s = _make_selve()
        s._track_commeo_command(3, object())
        s._handleCommandResult(_result(failed=[3]))  # must not raise
        assert s._commeo_pending[3]["attempts"] == 0
