"""
Live debug log: Commeo drive commands for different devices went out ~50 ms
apart; the gateway answered "COMMEO: Command overwritten" / "Radio line is
busy" and covers stayed put. RF drive commands (Commeo device/group, IVEO
manual) are now spaced by RF_SEND_SPACING, non-RF traffic is not held back.
"""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import selve as selve_mod
from selve import Selve
from selve.commands.command import (
    CommandDriveUp, CommandDriveUpGroup, CommandResultResponse,
)
from selve.commands.device import DeviceGetValues
from selve.commands.iveo import IveoManual
from selve.util.protocol import (
    CommunicationType, DeviceCommandType, DriveCommandCommeo, DriveCommandIveo,
)

SPACING = 0.2


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(selve_mod, "RF_SEND_SPACING", SPACING)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_BASE_DELAY", 0.0)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_STAGGER", 0.0)
    monkeypatch.setattr(selve_mod, "COMMEO_RETRY_SPACING", 0.0)


@pytest.fixture
async def selve():
    s = Selve(port=None, discover=False, develop=False, logger=Mock())
    s.sent = []

    async def send(cmd):
        s.sent.append((cmd, time.monotonic()))
        # answer synchronous commands at once so the TX loop does not wait
        if s._pending_futures:
            fut, _ = s._pending_futures.popleft()
            if not fut.done():
                fut.set_result(SimpleNamespace(executed=True))
    s._sendCommandToGateway = send
    s._start_movement_polling = Mock()
    yield s
    await s.stopWorker()


def _dev(id):
    return SimpleNamespace(id=id, communicationType=CommunicationType.COMMEO, state=None)


def _rf_times(s):
    return [t for cmd, t in s.sent if selve_mod._is_rf_drive(cmd)]


async def _wait_sent(s, n, timeout=3.0):
    end = time.monotonic() + timeout
    while len(_rf_times(s)) < n and time.monotonic() < end:
        await asyncio.sleep(0.01)


def _assert_spaced(times):
    gaps = [b - a for a, b in zip(times, times[1:])]
    assert all(g >= SPACING - 0.02 for g in gaps), gaps


class TestRfSendSpacing:
    async def test_back_to_back_drives_to_different_devices_are_spaced(self, selve):
        await asyncio.gather(*(selve.moveDeviceUp(_dev(i)) for i in range(4)))
        await _wait_sent(selve, 4)
        times = _rf_times(selve)
        assert len(times) == 4
        _assert_spaced(times)
        # FIFO: order of the calls is preserved
        assert [c.parameters[0][1] for c, _ in selve.sent] == [0, 1, 2, 3]

    async def test_retry_is_spaced_from_other_drives(self, selve):
        await selve.moveDeviceUp(_dev(1))
        r = CommandResultResponse.__new__(CommandResultResponse)
        r.command, r.successIds, r.failedIds = DriveCommandCommeo.DRIVEUP, [], [1]
        selve._handleCommandResult(r)              # retry with zero backoff
        await selve.moveDeviceUp(_dev(2))
        await _wait_sent(selve, 3)
        times = _rf_times(selve)
        assert len(times) == 3
        _assert_spaced(times)

    async def test_group_and_iveo_share_the_spacing(self, selve):
        await selve.moveDeviceUp(_dev(1))
        await selve.executeCommand(CommandDriveUpGroup(1, DeviceCommandType.MANUAL))
        await selve.executeCommand(IveoManual(5, DriveCommandIveo.UP))
        await _wait_sent(selve, 3)
        times = _rf_times(selve)
        assert len(times) == 3
        _assert_spaced(times)

    async def test_sync_path_is_gated_before_enqueue(self, selve):
        # (asyncio.wait_for cannot run under the test's nest_asyncio, so only
        # check that the synchronous path waits for its slot first.)
        class Gate(Exception):
            pass

        async def gate(cmd):
            raise Gate
        selve._await_rf_slot = gate
        selve.startWorker = AsyncMock()
        selve.txQ = asyncio.Queue()
        with pytest.raises(Gate):
            await selve._executeCommandSyncWithResponse(IveoManual(5, DriveCommandIveo.UP))
        assert selve.txQ.empty()

    async def test_write_time_guard_spaces_queued_drives(self, selve):
        # Commands that reach the TX queue together (bypassing the caller
        # gate) are still written apart.
        await selve.startWorker()
        for i in range(3):
            await selve.txQ.put((CommandDriveUp(i, DeviceCommandType.MANUAL), None))
        await _wait_sent(selve, 3)
        _assert_spaced(_rf_times(selve))

    async def test_non_rf_traffic_is_not_held_back(self, selve):
        await selve.moveDeviceUp(_dev(1))
        t0 = time.monotonic()
        drive = asyncio.create_task(selve.moveDeviceUp(_dev(2)))  # waits for its slot
        await asyncio.sleep(0.01)
        await selve.executeCommand(DeviceGetValues(1))
        await asyncio.sleep(0.05)
        values = [t for c, t in selve.sent if not selve_mod._is_rf_drive(c)]
        assert values and values[0] - t0 < SPACING / 2
        await drive
