import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from selve.util.serial_transport import _extract_messages


# ---------------------------------------------------------------------------
# Pure synchronous tests for _extract_messages
# ---------------------------------------------------------------------------

def test_single_method_response():
    xml = b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    msgs, remaining = _extract_messages(xml)
    assert len(msgs) == 1
    assert "</methodResponse>" in msgs[0]
    assert "selve.GW.service.ping" in msgs[0]
    assert remaining == b""


def test_single_method_call():
    xml = b"<methodCall><methodName>selve.GW.event.device</methodName><array></array></methodCall>"
    msgs, remaining = _extract_messages(xml)
    assert len(msgs) == 1
    assert "</methodCall>" in msgs[0]
    assert "event.device" in msgs[0]
    assert remaining == b""


def test_two_messages_in_one_chunk():
    chunk = (
        b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
        b"<methodCall><methodName>selve.GW.event.dutyCycle</methodName><array></array></methodCall>"
    )
    msgs, remaining = _extract_messages(chunk)
    assert len(msgs) == 2
    assert any("methodResponse" in m for m in msgs)
    assert any("methodCall" in m for m in msgs)
    assert remaining == b""


def test_incomplete_message_stays_in_buffer():
    partial = b"<methodResponse><array><string>selve.GW.service.ping</string></array>"
    msgs, remaining = _extract_messages(partial)
    assert msgs == []
    assert remaining == partial


def test_message_split_across_chunks():
    xml = b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    mid = len(xml) // 2
    # First chunk: no complete message yet
    msgs1, buf = _extract_messages(xml[:mid])
    assert msgs1 == []
    # Second chunk completes the message
    msgs2, remaining = _extract_messages(buf + xml[mid:])
    assert len(msgs2) == 1
    assert "</methodResponse>" in msgs2[0]
    assert remaining == b""


def test_xml_preamble_included_in_message():
    xml = (
        b'<?xml version="1.0"? encoding="UTF-8">'
        b"<methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>"
    )
    msgs, remaining = _extract_messages(xml)
    assert len(msgs) == 1
    assert "methodResponse" in msgs[0]


def test_garbage_before_message_is_included():
    """Leading whitespace/garbage bytes before the opening tag stay in the message."""
    xml = b"\r\n  <methodResponse><array></array></methodResponse>"
    msgs, remaining = _extract_messages(xml)
    assert len(msgs) == 1
    assert "methodResponse" in msgs[0]


def test_empty_buffer():
    msgs, remaining = _extract_messages(b"")
    assert msgs == []
    assert remaining == b""


def test_fault_response_uses_method_response_tag():
    """Fault responses are wrapped in <methodResponse>, same closing tag."""
    xml = b"<methodResponse><fault><array><string>Error</string><int>-1</int></array></fault></methodResponse>"
    msgs, remaining = _extract_messages(xml)
    assert len(msgs) == 1
    assert "fault" in msgs[0]
    assert remaining == b""


# ---------------------------------------------------------------------------
# Async test: idle timeout triggers reconnect
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idle_timeout_triggers_reconnect():
    """If no data arrives for _IDLE_TIMEOUT seconds, close+ensure_open are called."""
    import selve.util.serial_transport as st
    from selve.util.serial_transport import SerialTransport

    transport = SerialTransport(port="COM_TEST", logger=MagicMock())

    # Reader that never produces data (simulates dead port)
    reader = asyncio.StreamReader()
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

    original = st._IDLE_TIMEOUT
    st._IDLE_TIMEOUT = 0.05
    try:
        task = asyncio.create_task(transport._reader_loop())
        await asyncio.sleep(0.25)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    finally:
        st._IDLE_TIMEOUT = original

    assert len(close_calls) >= 1, "close() should be called on idle timeout"
    assert len(ensure_calls) >= 1, "ensure_open() should be called after reconnect"
