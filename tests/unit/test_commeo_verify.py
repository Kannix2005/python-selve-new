"""
Commeo drive commands the gateway confirms in successIds can still be lost on
the radio ("COMMEO: Radio line is busy" log event). After a reported success
the library verifies that the cover actually moved and re-sends otherwise.
"""
import asyncio
import time
from unittest.mock import Mock, AsyncMock

import pytest

import selve as selve_mod
from selve import Selve
from selve.commands.command import CommandResultResponse
from selve.util import LogEventResponse
from selve.device import SelveDevice
from selve.util.protocol import (
    CommunicationType, DeviceCommandType, DeviceType, DriveCommandCommeo,
    LogType, MovementState, SelveTypes,
)


@pytest.fixture(autouse=True)
def fast_delays(monkeypatch):
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_BASE_DELAY", 0.02)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_STAGGER", 0.02)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_SPACING", 0.05)
    monkeypatch.setattr(selve_mod, "COMMEO_VERIFY_DELAY", 0.1)
    monkeypatch.setattr(selve_mod, "COMMEO_VERIFY_BUSY_DELAY", 0.01)


def _make_selve(values=None):
    """Selve with mocked I/O. *values* maps device id -> (state, raw value)
    the gateway reports on DeviceGetValues during verification."""
    s = Selve(port=None, discover=False, develop=False, logger=Mock())
    s.executeCommand = AsyncMock()
    s._start_movement_polling = Mock()
    s.reported = values if values is not None else {}

    async def get_values(id):
        if id in s.reported:
            state, value = s.reported[id]
            _report(s, id, state, value)
        return None
    s.deviceGetValues = AsyncMock(side_effect=get_values)
    return s


def _report(s, id, state, value):
    """Apply gateway-sourced values the way updateCommeoDeviceValuesFromResponse does."""
    resp = Mock()
    resp.name = "dev"
    resp.movementState = state
    resp.value = value
    resp.targetValue = value
    resp.unreachable = False
    for f in ("overload", "obstructed", "alarm", "lostSensor", "automaticMode",
              "gatewayNotLearned", "windAlarm", "rainAlarm", "freezingAlarm", "dayMode"):
        setattr(resp, f, False)
    s.updateCommeoDeviceValuesFromResponse(id, resp)


def _device(s, id, value):
    d = SelveDevice(id, SelveTypes.DEVICE, DeviceType.SHUTTER)
    d.communicationType = CommunicationType.COMMEO
    d.value = value
    d.state = MovementState.STOPPED_OFF
    s.devices[SelveTypes.DEVICE.value][id] = d
    return d


def _result(command, success=(), failed=()):
    r = CommandResultResponse.__new__(CommandResultResponse)
    r.command = command
    r.commandType = DeviceCommandType.MANUAL
    r.executed = True
    r.successIds = list(success)
    r.failedIds = list(failed)
    return r


def _busy_log():
    r = LogEventResponse.__new__(LogEventResponse)
    r.logType = LogType.WARNING
    r.logCode = "1300"
    r.logStamp = "616877309"
    r.logValue = "1"
    r.logDescription = "COMMEO: Radio line is busy (01)!"
    return r


async def _settle(s, timeout=3.0):
    end = time.monotonic() + timeout
    while (s._commeo_retry_tasks or s._commeo_verify_tasks) and time.monotonic() < end:
        await asyncio.sleep(0.01)


UP = DriveCommandCommeo.DRIVEUP


class TestCommeoVerify:
    async def test_success_without_movement_is_resent(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        d = _device(s, 3, 81)  # raw 81 = 19 % open in HA
        await s.moveDeviceUp(d)
        cmd = s.executeCommand.await_args.args[0]
        s._handleCommandResult(_result(UP, success=[3]))
        assert 3 in s._commeo_pending  # kept for verification
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count >= 2
        assert s.executeCommand.await_args_list[1].args[0] is cmd
        info_msgs = [c.args[0] % c.args[1:] for c in s._LOGGER.info.call_args_list]
        assert any("did not move" in m for m in info_msgs)

    async def test_movement_detected_no_resend(self):
        s = _make_selve({3: (MovementState.UP_ON, 70)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1
        assert 3 not in s._commeo_pending

    async def test_moving_state_at_verify_counts_as_moved(self):
        s = _make_selve({3: (MovementState.UP_ON, 81)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1

    async def test_optimistic_state_is_not_movement(self):
        # _handleCommandResult sets UP_ON itself; that must not count as moved
        # when the gateway itself never reported anything.
        s = _make_selve()  # gateway reports nothing new
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        assert d.state == MovementState.UP_ON
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count >= 2

    @pytest.mark.parametrize("call,drive", [
        ("stepup", DriveCommandCommeo.STEPUP),
        ("pos1", DriveCommandCommeo.DRIVEPOS1),
    ])
    async def test_step_and_saved_positions_are_never_resent(self, call, drive):
        # A re-sent STEP would step twice; POS1/2 targets are unknown.
        s = _make_selve()  # gateway reports nothing new -> "no movement"
        d = _device(s, 3, 50)
        fn = {"stepup": lambda: s.moveDeviceStepUp(d, 10),
              "pos1": lambda: s.moveDevicePos1(d)}[call]
        await fn()
        s._handleCommandResult(_result(drive, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1

    async def test_event_position_change_counts_as_moved(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 0)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        _report(s, 3, MovementState.UP_ON, 60)  # device event during travel
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1

    @pytest.mark.parametrize("call,start,drive", [
        ("up", 0, DriveCommandCommeo.DRIVEUP),
        ("up", 1, DriveCommandCommeo.DRIVEUP),
        ("down", 100, DriveCommandCommeo.DRIVEDOWN),
        ("pos", 40, DriveCommandCommeo.DRIVEPOS),
        ("stepup", 0, DriveCommandCommeo.STEPUP),
    ])
    async def test_target_already_reached_no_resend(self, call, start, drive):
        s = _make_selve({3: (MovementState.STOPPED_OFF, start)})
        d = _device(s, 3, start)
        fn = {"up": lambda: s.moveDeviceUp(d), "down": lambda: s.moveDeviceDown(d),
              "pos": lambda: s.moveDevicePos(d, 40),
              "stepup": lambda: s.moveDeviceStepUp(d, 10)}[call]
        await fn()
        s._handleCommandResult(_result(drive, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1
        assert 3 not in s._commeo_pending

    async def test_target_reached_respects_reversed_mapping(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 0)})
        s.reversedStopPosition = 1
        d = _device(s, 3, 100)  # stored inverted: 100 - raw 0
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 1

    async def test_pos_not_reached_is_resent(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        d = _device(s, 3, 81)
        await s.moveDevicePos(d, 40)
        s._handleCommandResult(_result(DriveCommandCommeo.DRIVEPOS, success=[3]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count >= 2

    async def test_gives_up_after_max_retries(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        for _ in range(selve_mod.COMMEO_RETRY_MAX + 1):
            s._handleCommandResult(_result(UP, success=[3]))
            await asyncio.sleep(0.15)
            await _settle(s)
        assert s.executeCommand.await_count == 1 + selve_mod.COMMEO_RETRY_MAX
        assert 3 not in s._commeo_pending
        s._LOGGER.warning.assert_called_once()
        w = s._LOGGER.warning.call_args.args
        assert "did not move" in w[0] % w[1:]

    async def test_stop_cancels_pending_verify(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        s.updateCommeoDeviceValuesAsync = AsyncMock()
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        await s.stopDevice(d)
        await asyncio.sleep(0.15)
        await _settle(s)
        assert s.executeCommand.await_count == 2  # up + stop, no resend
        assert s.executeCommand.await_args.args[0].parameters[1][1] == DriveCommandCommeo.STOP.value

    async def test_newer_command_cancels_scheduled_retry(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        await asyncio.sleep(0.12)  # verify ran, retry is scheduled
        await s.moveDeviceDown(d)
        await _settle(s)
        sent = [c.args[0].parameters[1][1] for c in s.executeCommand.await_args_list]
        assert sent == [UP.value, DriveCommandCommeo.DRIVEDOWN.value]

    async def test_late_result_of_other_command_does_not_confirm(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(DriveCommandCommeo.DRIVEDOWN, success=[3]))
        assert 3 not in s._commeo_verify_tasks
        assert 3 in s._commeo_pending

    async def test_busy_log_triggers_early_verify(self, monkeypatch):
        monkeypatch.setattr(selve_mod, "COMMEO_VERIFY_DELAY", 30)
        s = _make_selve({1: (MovementState.STOPPED_OFF, 81),
                         2: (MovementState.UP_ON, 50)})
        d1, d2 = _device(s, 1, 81), _device(s, 2, 60)
        await s.moveDeviceUp(d1)
        await s.moveDeviceUp(d2)
        s._handleCommandResult(_result(UP, success=[1]))
        s._handleCommandResult(_result(UP, success=[2]))
        await s.processEventResponse(_busy_log())
        await asyncio.sleep(0.05)
        await _settle(s)
        resent = [c.args[0].parameters[0][1] for c in s.executeCommand.await_args_list[2:]]
        assert resent and set(resent) == {1}  # only the cover that did not move
        assert s.deviceGetValues.await_count >= 2

    async def test_busy_log_ignores_old_entries(self, monkeypatch):
        monkeypatch.setattr(selve_mod, "COMMEO_VERIFY_DELAY", 30)
        s = _make_selve({1: (MovementState.STOPPED_OFF, 81)})
        d1 = _device(s, 1, 81)
        await s.moveDeviceUp(d1)
        s._commeo_pending[1]["last_sent"] -= 60
        await s.processEventResponse(_busy_log())
        await asyncio.sleep(0.05)
        assert s.deviceGetValues.await_count == 0
        for t in list(s._commeo_verify_tasks.values()):
            t[0].cancel()

    async def test_stuck_covers_are_resent_staggered(self, monkeypatch):
        monkeypatch.setattr(selve_mod, "COMMEO_RETRY_SPACING", 0.2)
        s = _make_selve({1: (MovementState.STOPPED_OFF, 81),
                         2: (MovementState.STOPPED_OFF, 70)})
        d1, d2 = _device(s, 1, 81), _device(s, 2, 70)
        await s.moveDeviceUp(d1)
        await s.moveDeviceUp(d2)
        times = []

        async def record(cmd):
            times.append(time.monotonic())
        s.executeCommand.side_effect = record
        s._handleCommandResult(_result(UP, success=[1, 2]))
        await asyncio.sleep(0.15)
        await _settle(s)
        assert len(times) == 2
        assert times[1] - times[0] >= 0.18

    async def test_stop_is_not_verified(self):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        s.updateCommeoDeviceValuesAsync = AsyncMock()
        d = _device(s, 3, 81)
        await s.stopDevice(d)
        s._handleCommandResult(_result(DriveCommandCommeo.STOP, success=[3]))
        assert 3 not in s._commeo_pending
        assert s._commeo_verify_tasks == {}

    async def test_group_command_cancels_member_pending(self, monkeypatch):
        s = _make_selve({3: (MovementState.STOPPED_OFF, 81)})
        s.executeCommandSyncWithResponse = AsyncMock()
        s.updateCommeoDeviceValuesAsync = AsyncMock()
        d = _device(s, 3, 81)
        await s.moveDeviceUp(d)
        s._handleCommandResult(_result(UP, success=[3]))
        group = Mock()
        group.id = 1
        monkeypatch.setattr(selve_mod.Util, "b64bytes_to_bitobject", lambda m: {3: True})
        await s.moveGroupDown(group)
        assert 3 not in s._commeo_pending
        await asyncio.sleep(0.15)
        assert s.executeCommand.await_count == 1
