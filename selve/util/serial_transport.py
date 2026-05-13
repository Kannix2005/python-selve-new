import asyncio
import logging
from typing import Optional

import serialx
from serialx import Parity

# Any data chunk arriving within this window extends the deadline.
# Only a truly dead/disconnected port triggers a reconnect.
_IDLE_TIMEOUT = 60.0

# The gateway protocol uses XML-RPC framing. Every message ends with one of
# these two tags; there are no other root-level closing tags in the protocol.
_END_TAGS = (b"</methodResponse>", b"</methodCall>")


class SerialTransport:
    """Async serial transport using serialx (replaces pyserial + background thread)."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        read_timeout: float = 1.0,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._port = port
        self._baudrate = baudrate
        self._read_timeout = read_timeout
        self._logger = logger or logging.getLogger(__name__)

        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._reader_task: Optional[asyncio.Task] = None
        self._rx_queue: Optional[asyncio.Queue] = None

    @property
    def port(self) -> str:
        return self._port

    @property
    def is_open(self) -> bool:
        return self._writer is not None and not self._writer.is_closing()

    async def ensure_open(self) -> None:
        if not self.is_open:
            self._logger.info("Serial: opening %s", self._port)
            self._reader, self._writer = await serialx.open_serial_connection(
                url=self._port,
                baudrate=self._baudrate,
                bytesize=8,
                parity=Parity.NONE,
                stopbits=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            self._logger.info("Serial: %s opened", self._port)

    async def close(self) -> None:
        self._logger.info("Serial: closing %s", self._port)
        try:
            if self._writer and not self._writer.is_closing():
                self._writer.close()
                await self._writer.wait_closed()
        except Exception:
            self._logger.debug("Serial close failed", exc_info=True)
        self._reader = None
        self._writer = None
        self._logger.info("Serial: %s closed", self._port)

    async def start_reader(self, rx_queue: asyncio.Queue) -> None:
        """Opens the serial port and starts the async reader task."""
        await self.ensure_open()
        self._rx_queue = rx_queue
        if self._reader_task and not self._reader_task.done():
            self._logger.info("Serial: reader task already running")
            return
        self._logger.info("Serial: starting reader task")
        self._reader_task = asyncio.create_task(
            self._reader_loop(), name="selve-serial-reader"
        )

    async def stop_reader(self) -> None:
        if self._reader_task:
            self._logger.info("Serial: stopping reader task")
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None
            self._logger.info("Serial: reader task stopped")

    async def _reader_loop(self) -> None:
        """Read raw bytes and dispatch complete XML messages by framing on closing tags.

        Using read() instead of readline() avoids depending on \\n as a message
        delimiter. The Selve protocol is XML-RPC: every gateway message ends with
        either </methodResponse> or </methodCall>. We scan the byte buffer for
        these tags and dispatch as soon as a complete message is available.

        A 60-second idle timeout (no bytes at all) triggers a reconnect. This is
        far more conservative than the old 12-second readline hack and only fires
        when the serial port is truly dead.
        """
        self._logger.info("Serial: reader loop started")
        buffer = b""
        while True:
            try:
                await self.ensure_open()
                assert self._reader is not None
                chunk = await asyncio.wait_for(
                    self._reader.read(4096), timeout=_IDLE_TIMEOUT
                )
            except asyncio.TimeoutError:
                self._logger.warning(
                    "Serial: no data for %.0fs — reconnecting", _IDLE_TIMEOUT
                )
                buffer = b""
                await self.close()
                await asyncio.sleep(1.0)
                await self.ensure_open()
                continue
            except asyncio.CancelledError:
                self._logger.info("Serial: reader loop cancelled")
                break
            except (OSError, EOFError) as exc:
                self._logger.error("Serial read error: %s", exc)
                await asyncio.sleep(1)
                continue
            except Exception:
                self._logger.error("Unexpected serial read error", exc_info=True)
                await asyncio.sleep(1)
                continue

            if not chunk:
                await asyncio.sleep(0.01)
                continue

            buffer += chunk

            # Extract all complete XML messages from the buffer
            while True:
                # Find the earliest closing tag
                earliest_end = None
                for tag in _END_TAGS:
                    pos = buffer.find(tag)
                    if pos >= 0:
                        end = pos + len(tag)
                        if earliest_end is None or end < earliest_end:
                            earliest_end = end

                if earliest_end is None:
                    break

                msg = buffer[:earliest_end].decode(errors="ignore").strip()
                buffer = buffer[earliest_end:]

                if msg and self._rx_queue:
                    self._logger.debug("Serial RX: %s", msg)
                    await self._rx_queue.put(msg)

    async def write(self, payload: bytes) -> None:
        await self.ensure_open()
        try:
            self._writer.write(payload)
            await self._writer.drain()
        except OSError as exc:
            self._logger.error("Serial write error: %s", exc)
            raise

    async def shutdown(self) -> None:
        await self.stop_reader()
        await self.close()
