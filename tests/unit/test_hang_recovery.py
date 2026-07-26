"""
Regression tests for the 2026-07-25 gateway-hang incident:
- startWorker() health check must cover ALL worker tasks, not just TX
- keepalive escalates unanswered pings into a full worker/transport recovery
- movement polling must not leave an optimistic UP_ON/DOWN_ON forever
- 0x8000 "position unknown" sentinel must not become a phantom 50%
- IVEO drive commands must not claim a position the gateway never confirmed
"""
import asyncio
import time
from types import SimpleNamespace
from unittest.mock import Mock, AsyncMock

import pytest

from selve import Selve
from selve.util import Util
from selve.util.protocol import (
    CommunicationType,
    MovementState,
    SelveTypes,
)


def _make_selve():
    return Selve(port=None, discover=False, develop=False, logger=Mock())


def _values_response(value, target_value, state=MovementState.STOPPED_OFF):
    return SimpleNamespace(
        name="dev",
        movementState=state,
        value=value,
        targetValue=target_value,
        unreachable=False,
        overload=False,
        obstructed=False,
        alarm=False,
        lostSensor=False,
        automaticMode=False,
        gatewayNotLearned=False,
        windAlarm=False,
        rainAlarm=False,
        freezingAlarm=False,
        dayMode=False,
    )


def _register_device(s, comm_type=CommunicationType.COMMEO,
                     selve_type=SelveTypes.DEVICE, value=42):
    dev = SimpleNamespace(
        id=1,
        name="dev",
        communicationType=comm_type,
        state=MovementState.STOPPED_OFF,
        value=value,
        targetValue=value,
    )
    s.devices[selve_type.value][dev.id] = dev
    return dev


class TestUnknownPositionSentinel:
    def test_sentinel_returns_none(self):
        assert Util.valueToPercentage(0x8000) is None

    def test_normal_values_still_convert(self):
        assert Util.valueToPercentage(0) == 0
        assert Util.valueToPercentage(65535) == 100
        # A commanded 50% is 32767, not the 32768 sentinel
        assert Util.valueToPercentage(Util.percentageToValue(50)) == 49

    def test_get_values_response_keeps_last_known_position(self):
        s = _make_selve()
        dev = _register_device(s, value=42)
        s.updateCommeoDeviceValuesFromResponse(1, _values_response(None, None))
        assert dev.value == 42
        assert dev.targetValue == 42

    def test_get_values_response_applies_real_position(self):
        s = _make_selve()
        dev = _register_device(s, value=42)
        s.updateCommeoDeviceValuesFromResponse(1, _values_response(80, 80))
        assert dev.value == 80
        assert dev.targetValue == 80


class TestStartWorkerHealthCheck:
    @pytest.mark.asyncio
    async def test_restarts_dead_dispatch_task(self):
        s = _make_selve()
        try:
            await s.startWorker()
            assert s._dispatch_task is not None and not s._dispatch_task.done()
            # Kill only the dispatch task — the old guard checked only TX and
            # would have returned early, leaving RX dead forever.
            s._dispatch_task.cancel()
            try:
                await s._dispatch_task
            except asyncio.CancelledError:
                pass
            assert s._dispatch_task.done()
            assert not s._tx_task.done()

            await s.startWorker()
            assert not s._dispatch_task.done()
        finally:
            await s.stopWorker()


class TestKeepaliveEscalation:
    @pytest.mark.asyncio
    async def test_unanswered_pings_trigger_recovery(self):
        s = _make_selve()
        s._keepalive_interval = 0.01
        s._keepalive_max_failures = 2
        s._last_rx = time.monotonic() - 999
        s._executeCommandSyncWithResponse = AsyncMock(return_value=False)
        s._recover_from_hang = AsyncMock()

        task = asyncio.create_task(s._keepalive_loop())
        # No asyncio.wait_for here: nest_asyncio (pulled in by the test setup)
        # breaks its internal asyncio.timeout. Bounded polling instead.
        for _ in range(200):
            await asyncio.sleep(0.01)
            if s._recover_from_hang.called:
                break
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert s._executeCommandSyncWithResponse.await_count == 2
        s._recover_from_hang.assert_called_once()

    @pytest.mark.asyncio
    async def test_successful_ping_resets_failure_counter(self):
        s = _make_selve()
        s._keepalive_interval = 0.01
        s._keepalive_max_failures = 2
        s._last_rx = time.monotonic() - 999
        s._ping_failures = 1
        s._executeCommandSyncWithResponse = AsyncMock(return_value=SimpleNamespace())
        s._recover_from_hang = AsyncMock()

        task = asyncio.create_task(s._keepalive_loop())
        await asyncio.sleep(0.05)
        s._stopThread.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert s._ping_failures == 0
        s._recover_from_hang.assert_not_called()

    @pytest.mark.asyncio
    async def test_recovery_skipped_while_closing(self):
        s = _make_selve()
        s._closing = True
        s.stopWorker = AsyncMock()
        await s._recover_from_hang()
        s.stopWorker.assert_not_called()


class TestMovementPollTimeout:
    @pytest.mark.asyncio
    async def test_timeout_clears_stale_moving_state(self):
        s = _make_selve()
        dev = _register_device(s)
        dev.state = MovementState.UP_ON
        s.updateCommeoDeviceValuesAsync = AsyncMock()

        await s._movement_poll_loop(1, interval=0.01, timeout=0.03)

        assert dev.state == MovementState.UNKOWN

    @pytest.mark.asyncio
    async def test_timeout_leaves_settled_state_alone(self):
        s = _make_selve()
        dev = _register_device(s)
        dev.state = MovementState.STOPPED_OFF
        s.updateCommeoDeviceValuesAsync = AsyncMock()

        await s._movement_poll_loop(1, interval=0.01, timeout=0.03)

        assert dev.state == MovementState.STOPPED_OFF


class TestIveoConfirmedPosition:
    @pytest.mark.asyncio
    async def test_unconfirmed_send_keeps_position(self):
        s = _make_selve()
        dev = _register_device(s, comm_type=CommunicationType.IVEO,
                               selve_type=SelveTypes.IVEO, value=7)
        s._send_iveo_command = AsyncMock(return_value=False)

        await s.moveDeviceDown(dev)

        assert dev.state == MovementState.STOPPED_OFF
        assert dev.value == 7  # unchanged: gateway never confirmed a send

    @pytest.mark.asyncio
    async def test_confirmed_send_updates_position(self):
        s = _make_selve()
        dev = _register_device(s, comm_type=CommunicationType.IVEO,
                               selve_type=SelveTypes.IVEO, value=7)
        s._send_iveo_command = AsyncMock(return_value=True)

        await s.moveDeviceDown(dev)

        assert dev.value == 100
