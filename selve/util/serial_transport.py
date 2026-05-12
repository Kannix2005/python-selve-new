import asyncio
import logging
from typing import Optional

import serialx
from serialx import Parity

_READLINE_TIMEOUT = 12.0  # seconds — gateway goes silent during RF motor ops


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
            self._logger.info("Serial: %s opened, reader=%r writer=%r", self._port, self._reader, self._writer)

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
        self._logger.info("Serial: starting reader task, reader=%r", self._reader)
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
        self._logger.info("Serial: reader loop started, reader=%r at_eof=%s",
                          self._reader,
                          self._reader.at_eof() if self._reader else "N/A")
        buffer = ""
        iteration = 0
        while True:
            try:
                if self._reader is None:
                    self._logger.warning("Serial: reader is None in loop, reopening")
                    await self.ensure_open()
                self._logger.debug("Serial: awaiting readline (iter=%d, buf=%r)", iteration, buffer)
                line_bytes = await asyncio.wait_for(
                    self._reader.readline(), timeout=_READLINE_TIMEOUT
                )
                self._logger.debug("Serial: readline returned %d bytes (iter=%d)", len(line_bytes), iteration)
                iteration += 1
            except asyncio.TimeoutError:
                self._logger.warning(
                    "Serial: readline timeout after %.0fs (iter=%d, buf=%r) — reconnecting",
                    _READLINE_TIMEOUT, iteration, buffer,
                )
                buffer = ""
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

            if not line_bytes:
                self._logger.debug("Serial: readline returned empty bytes (EOF?), reader.at_eof=%s",
                                   self._reader.at_eof() if self._reader else "N/A")
                await asyncio.sleep(0.01)
                continue

            decoded = line_bytes.decode(errors="ignore").strip()
            if decoded == "":
                if buffer and self._rx_queue:
                    self._logger.debug("Serial RX: %s", buffer)
                    await self._rx_queue.put(buffer)
                    buffer = ""
                continue

            buffer += decoded

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
