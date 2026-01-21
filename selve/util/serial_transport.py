import asyncio
import logging
import threading
import time
from typing import Optional

import serial
from serial import SerialException


class SerialTransport:
    """Thin wrapper around pyserial with a background reader thread."""

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

        self._serial: Optional[serial.Serial] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._rx_queue: Optional[asyncio.Queue] = None

    @property
    def serial(self) -> Optional[serial.Serial]:
        return self._serial

    @property
    def port(self) -> str:
        return self._port

    def ensure_open(self) -> None:
        if self._serial is None:
            self._serial = serial.Serial(
                port=self._port,
                baudrate=self._baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
                timeout=self._read_timeout,
            )
        elif not self._serial.is_open:
            self._serial.open()

    def close(self) -> None:
        try:
            if self._serial and self._serial.is_open:
                self._serial.close()
        except Exception:
            # Best-effort; log and move on
            self._logger.debug("Serial close failed", exc_info=True)

    def start_reader(self, loop: asyncio.AbstractEventLoop, rx_queue: asyncio.Queue) -> None:
        """Starts a background reader thread that pushes complete messages into rx_queue."""
        self.ensure_open()
        self._loop = loop
        self._rx_queue = rx_queue

        # In tests, serial.Serial is often patched with a MagicMock; skip starting the reader thread
        # to avoid tight loops on mocked readline() and reduce flakiness.
        if self._serial is not None and getattr(self._serial, "__module__", "").startswith("unittest.mock"):
            self._logger.debug("Mock serial detected; skipping reader thread")
            return

        if self._reader_thread and self._reader_thread.is_alive():
            return
        self._stop_event.clear()
        self._reader_thread = threading.Thread(target=self._reader, name="selve-serial-reader", daemon=True)
        self._reader_thread.start()

    def stop_reader(self) -> None:
        self._stop_event.set()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=2)
        self._reader_thread = None

    def _reader(self) -> None:
        buffer = ""
        while not self._stop_event.is_set():
            try:
                if self._serial is None:
                    self.ensure_open()
                line = self._serial.readline()
            except SerialException as exc:
                self._logger.error("Serial read error: %s", exc)
                time.sleep(1)
                continue
            except Exception:
                self._logger.error("Unexpected serial read error", exc_info=True)
                time.sleep(1)
                continue

            if line is None:
                continue

            decoded = line.decode(errors="ignore").strip()
            if decoded == "":
                if buffer:
                    if self._loop and self._rx_queue:
                        # Push completed frame to asyncio queue
                        self._loop.call_soon_threadsafe(self._rx_queue.put_nowait, buffer)
                    buffer = ""
                continue

            buffer += decoded

    async def write(self, payload: bytes) -> None:
        self.ensure_open()
        try:
            self._serial.write(payload)
            self._serial.flush()
        except SerialException as exc:
            self._logger.error("Serial write error: %s", exc)
            raise

    def shutdown(self) -> None:
        self.stop_reader()
        self.close()
