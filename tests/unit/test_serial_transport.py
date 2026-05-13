import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def transport(event_loop):
    from selve.util.serial_transport import SerialTransport
    t = SerialTransport(port="COM_TEST", logger=MagicMock())
    return t


def _make_reader(*chunks):
    """Return an asyncio.StreamReader pre-loaded with the given byte chunks."""
    reader = asyncio.StreamReader()
    for c in chunks:
        reader.feed_data(c)
    reader.feed_eof()
    return reader


async def _collect(transport, reader, n_messages, timeout=2.0):
    """Run _reader_loop until n_messages are dispatched, then cancel."""
    q = asyncio.Queue()
    transport._reader = reader
    transport._writer = MagicMock(is_closing=MagicMock(return_value=False))
    transport._rx_queue = q

    task = asyncio.create_task(transport._reader_loop())
    messages = []
    try:
        async with asyncio.timeout(timeout):
            while len(messages) < n_messages:
                msg = await q.get()
                messages.append(msg)
    except (asyncio.TimeoutError, Exception):
        pass
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    return messages


@pytest.mark.asyncio
async def test_single_method_response(transport):
    xml = b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    reader = _make_reader(xml)
    msgs = await _collect(transport, reader, 1)
    assert len(msgs) == 1
    assert "</methodResponse>" in msgs[0]
    assert "selve.GW.service.ping" in msgs[0]


@pytest.mark.asyncio
async def test_single_method_call(transport):
    xml = b"<methodCall><methodName>selve.GW.event.device</methodName><array></array></methodCall>"
    reader = _make_reader(xml)
    msgs = await _collect(transport, reader, 1)
    assert len(msgs) == 1
    assert "</methodCall>" in msgs[0]
    assert "event.device" in msgs[0]


@pytest.mark.asyncio
async def test_two_messages_in_one_chunk(transport):
    """Both a response and an event arriving in the same read() call."""
    chunk = (
        b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
        b"<methodCall><methodName>selve.GW.event.dutyCycle</methodName><array></array></methodCall>"
    )
    reader = _make_reader(chunk)
    msgs = await _collect(transport, reader, 2)
    assert len(msgs) == 2
    assert any("methodResponse" in m for m in msgs)
    assert any("methodCall" in m for m in msgs)


@pytest.mark.asyncio
async def test_message_split_across_chunks(transport):
    """Message split at an arbitrary byte boundary."""
    xml = b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    mid = len(xml) // 2
    reader = _make_reader(xml[:mid], xml[mid:])
    msgs = await _collect(transport, reader, 1)
    assert len(msgs) == 1
    assert "</methodResponse>" in msgs[0]


@pytest.mark.asyncio
async def test_xml_preamble_is_included(transport):
    """Gateway sometimes prefixes messages with a (malformed) XML declaration."""
    xml = (
        b'<?xml version="1.0"? encoding="UTF-8">'
        b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    )
    reader = _make_reader(xml)
    msgs = await _collect(transport, reader, 1)
    assert len(msgs) == 1
    assert "methodResponse" in msgs[0]


@pytest.mark.asyncio
async def test_idle_timeout_triggers_reconnect(transport):
    """If no data arrives for _IDLE_TIMEOUT seconds, the transport reconnects."""
    from selve.util import serial_transport as st

    reader = asyncio.StreamReader()  # never feeds data → triggers timeout

    transport._reader = reader
    transport._writer = MagicMock(is_closing=MagicMock(return_value=False))
    transport._rx_queue = asyncio.Queue()

    close_calls = []
    ensure_calls = []

    async def fake_close():
        close_calls.append(1)
        transport._reader = None
        transport._writer = None

    async def fake_ensure():
        ensure_calls.append(1)
        transport._reader = asyncio.StreamReader()
        transport._writer = MagicMock(is_closing=MagicMock(return_value=False))

    transport.close = fake_close
    transport.ensure_open = fake_ensure

    original_timeout = st._IDLE_TIMEOUT
    st._IDLE_TIMEOUT = 0.05
    try:
        task = asyncio.create_task(transport._reader_loop())
        await asyncio.sleep(0.3)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    finally:
        st._IDLE_TIMEOUT = original_timeout

    assert len(close_calls) >= 1, "close() should have been called on idle timeout"
    assert len(ensure_calls) >= 1, "ensure_open() should have been called after reconnect"
