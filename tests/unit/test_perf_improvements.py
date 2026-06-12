"""
Tests for the performance improvements:
- response-paced TX loop (no fixed 100ms delay)
- ErrorResponse resolves the pending future immediately
- callbacks receive the changed device (with zero-arg compatibility)
- updateAllDevices iterates device objects, not ids
"""
import asyncio
import time
from unittest.mock import Mock, AsyncMock

import pytest

from selve import Selve
from selve.commands.service import ServicePing
from selve.util.errors import ErrorResponse
from selve.util.protocol import SelveTypes


def _make_selve():
    return Selve(port=None, discover=False, develop=False, logger=Mock())


class TestResolveNextFuture:
    def test_resolves_oldest_pending_future(self):
        selve = _make_selve()
        loop = asyncio.new_event_loop()
        try:
            fut1 = loop.create_future()
            fut2 = loop.create_future()
            selve._pending_futures.append(fut1)
            selve._pending_futures.append(fut2)

            assert selve._resolve_next_future("result") is True
            assert fut1.result() == "result"
            assert not fut2.done()
        finally:
            loop.close()

    def test_skips_cancelled_futures(self):
        selve = _make_selve()
        loop = asyncio.new_event_loop()
        try:
            fut1 = loop.create_future()
            fut1.cancel()
            fut2 = loop.create_future()
            selve._pending_futures.append(fut1)
            selve._pending_futures.append(fut2)

            assert selve._resolve_next_future(False) is True
            assert fut2.result() is False
        finally:
            loop.close()

    def test_returns_false_without_pending_future(self):
        selve = _make_selve()
        assert selve._resolve_next_future("x") is False


@pytest.mark.asyncio
async def test_error_response_resolves_future_immediately():
    """A gateway fault must resolve the waiting command future with False
    instead of letting the caller run into its 10s timeout."""
    selve = _make_selve()
    selve.rxQ = asyncio.Queue()

    async def fake_process(msg):
        return ErrorResponse("Method not supported", 2)

    selve.processResponse = fake_process

    future = asyncio.get_running_loop().create_future()
    selve._pending_futures.append(future)
    await selve.rxQ.put("<dummy/>")

    task = asyncio.create_task(selve._dispatch_loop())
    try:
        for _ in range(100):
            if future.done():
                break
            await asyncio.sleep(0.01)
        assert future.done(), "future was not resolved by the error response"
        assert future.result() is False
    finally:
        selve._stopThread.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_tx_loop_waits_for_response_before_next_command():
    """The TX loop must not send the next command before the previous
    command's response future is resolved."""
    selve = _make_selve()
    selve.txQ = asyncio.Queue()
    send_times = []

    async def fake_send(command):
        send_times.append(time.monotonic())

    selve._sendCommandToGateway = fake_send

    loop = asyncio.get_running_loop()
    fut1 = loop.create_future()
    fut2 = loop.create_future()
    await selve.txQ.put((ServicePing(), fut1))
    await selve.txQ.put((ServicePing(), fut2))

    task = asyncio.create_task(selve._tx_loop())
    try:
        await asyncio.sleep(0.15)
        # only the first command may have been sent so far
        assert len(send_times) == 1
        fut1.set_result("pong")
        await asyncio.sleep(0.1)
        assert len(send_times) == 2
    finally:
        selve._stopThread.set()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


class TestDeviceCallbacks:
    def test_callback_receives_device(self):
        selve = _make_selve()
        received = []
        selve.register_callback(lambda device: received.append(device))

        sentinel = object()
        selve._fire_callbacks(sentinel)
        assert received == [sentinel]

    def test_zero_arg_callback_still_works(self):
        selve = _make_selve()
        calls = []

        def legacy_callback():
            calls.append(1)

        selve.register_callback(legacy_callback)
        selve._fire_callbacks(object())
        assert calls == [1]

    def test_failing_callback_does_not_break_others(self):
        selve = _make_selve()
        received = []

        def bad_callback(device):
            raise RuntimeError("boom")

        selve.register_callback(bad_callback)
        selve.register_callback(lambda device: received.append(device))
        selve._fire_callbacks("dev")
        assert received == ["dev"]

    def test_remove_callback(self):
        selve = _make_selve()
        cb = lambda device: None
        selve.register_callback(cb)
        selve.remove_callback(cb)
        assert cb not in selve._callbacks

    def test_add_or_update_device_fires_callback_with_device(self):
        selve = _make_selve()
        received = []
        selve.register_callback(lambda device: received.append(device))

        dev = Mock()
        dev.id = 7
        selve.addOrUpdateDevice(dev, SelveTypes.DEVICE)
        assert received == [dev]
        assert selve.devices[SelveTypes.DEVICE.value][7] is dev


@pytest.mark.asyncio
async def test_update_all_devices_iterates_device_objects():
    selve = _make_selve()
    dev = Mock()
    dev.id = 3
    selve.devices[SelveTypes.DEVICE.value][3] = dev

    selve.updateCommeoDeviceValues = AsyncMock()
    selve.updateSensorValuesAsync = AsyncMock()
    selve.updateSenSimValuesAsync = AsyncMock()
    selve.updateSenderValuesAsync = AsyncMock()

    await selve.updateAllDevices()
    selve.updateCommeoDeviceValues.assert_awaited_once_with(3)
