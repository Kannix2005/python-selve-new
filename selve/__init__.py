from __future__ import annotations

# Version handling
try:
    from ._version import version as __version__
except ImportError:
    # Fallback for development
    try:
        from setuptools_scm import get_version
        __version__ = get_version(root='..', relative_to=__file__)
    except:
        __version__ = "unknown"

import asyncio
import inspect
import logging
import time
from collections import deque
from itertools import chain
from typing import Callable, Optional

try:
    from serial.tools import list_ports as _serial_list_ports
    def _comports():
        return _serial_list_ports.comports()
except ImportError:
    def _comports():  # type: ignore[misc]
        return []

import untangle

from selve.commands import param, service
from selve.commands import device
from selve.commands.device import *
from selve.commands.command import *
from selve.commands.event import *
from selve.commands.group import *
from selve.commands.iveo import *
from selve.commands.service import *
from selve.commands.param import *
from selve.commands.event import *
from selve.commands.senSim import *
from selve.commands.sensor import *
from selve.commands.sender import *
from selve.commands.firmware import *
from selve.device import SelveDevice
from selve.group import SelveGroup
from selve.iveo import IveoDevice
from selve.senSim import SelveSenSim
from selve.sender import SelveSender
from selve.sensor import SelveSensor
from selve.util import *
from selve.util import Command
from selve.util.errors import *
from selve.util.protocol import ParameterType, SelveTypes, MovementState
from selve.util.serial_transport import SerialTransport

# Ping the gateway when no data has arrived for this long. Must be shorter
# than the serial transport's 60s idle-reconnect so a healthy but quiet link
# never gets torn down (reconnect windows would drop unsolicited events).
_KEEPALIVE_INTERVAL = 30.0

# IVEO is a one-way protocol: the motor never reports back, so a lost RF
# telegram is a silent failure. Like a physical handsender we repeat each
# telegram a few times to improve the odds it is received.
#
# The delay between repeats must exceed the gateway's RF transmission window,
# otherwise a repeat overwrites the still-in-progress telegram (the gateway
# logs "IVEO: Command overwritten") and the repeats collapse into one
# continuous burst instead of discrete retry attempts. Measured against real
# hardware: a 0.15s gap overwrites, >=0.3s is clean; 0.7s keeps a safe margin.
_IVEO_REPEAT = 3
_IVEO_REPEAT_DELAY = 0.7
# How long an IVEO shutter is assumed to travel. IVEO reports nothing back,
# so this is the only way the movement state can ever end.
_IVEO_TRAVEL_TIME = 30.0

# How long to wait for the 868 MHz duty cycle to recover before giving up on
# a send. The gateway pushes DutyCycleResponse events as airtime frees up.
_DUTY_CYCLE_WAIT = 5.0


# Automatic retry of Commeo drive commands the gateway reports as failed
# (e.g. "COMMEO: Radio line is busy" when several covers are driven at once).
COMMEO_RETRY_MAX = 2          # re-sends per command
COMMEO_RETRY_BASE_DELAY = 1.5  # seconds, multiplied by the attempt number
COMMEO_RETRY_STAGGER = 0.4    # seconds per position in failedIds
COMMEO_RETRY_WINDOW = 30      # seconds a result may arrive after sending


class Selve:
    """Implementation of the serial communication to the Selve Gateway"""

    def __init__(self, port=None, discover=True, develop=False, logger=None, loop=None):
        # Gateway state
        # callback -> whether it accepts the changed device as argument
        self._callbacks: dict = {}
        self._eventCallbacks = set()
        self.lastLogEvent = None
        self.state = None
        self.loop = loop

        # Data from Duty Cycle Event
        self.utilization = 0
        self.sendingBlocked = DutyMode.NOT_BLOCKED

        # Known devices
        self.devices: dict = {
            SelveTypes.DEVICE.value: {},
            SelveTypes.IVEO.value: {},
            SelveTypes.GROUP.value: {},
            SelveTypes.SENSIM.value: {},
            SelveTypes.SENSOR.value: {},
            SelveTypes.SENDER.value: {}
        }

        # Flags for enabling reader and writer in the worker thread
        self._pauseWorker = asyncio.Event()
        self._stopThread = asyncio.Event()

        # The worker thread
        self.workerTask = None
        self._tx_task = None
        self._dispatch_task = None

        # Transport
        self._transport: Optional[SerialTransport] = None

        # Port where the Selve gateway was found
        self._port = port
        self._serial = None

        # Write lock to safely write to the gateway
        self._writeLock = asyncio.Lock()
        self._readLock = asyncio.Lock()

        # Trasmit and Recieve Queue init
        self.txQ = None
        self.rxQ = None
        self._pending_futures = deque()
        self._event_queue = None

        # Keepalive: ping the gateway when the link has been idle so the
        # serial reader's idle-reconnect only fires on a truly dead port.
        self._keepalive_task = None
        self._keepalive_interval = _KEEPALIVE_INTERVAL
        self._last_rx = 0.0
        # Dead-link escalation: after this many consecutive unanswered pings
        # the keepalive triggers a full worker+transport rebuild.
        self._keepalive_max_failures = 3
        self._ping_failures = 0
        self._recover_task = None
        self._recovering = False
        self._closing = False
        # Serializes everything that rebuilds transport/queues/workers
        # (setup, discover, recovery) — without it a reload landing inside a
        # running recovery reintroduces the very race these guards prevent.
        self._connLock = asyncio.Lock()
        # False once the keepalive declared the link dead, True again as soon
        # as any data arrives. Transitions notify callbacks so consumers can
        # re-evaluate availability — nothing else would ever ask.
        self._link_ok = True

        # Active movement polling tasks keyed by device id
        self._movement_tasks: dict = {}

        # Last Commeo drive command per device id, kept until the gateway
        # reports its result: {id: {"command", "attempts", "sent_at"}}
        self._commeo_pending: dict = {}
        self._commeo_retry_tasks: set = set()

        # IVEO has no return channel: the gateway only confirms that it sent
        # the telegram, never that the shutter stopped. Without a timer the
        # movement state would stay UP_ON/DOWN_ON forever.
        self._iveo_travel_tasks: dict = {}

        #Options
        self.reversedStopPosition = 0
        # IVEO reliability: how often a one-way telegram is repeated, and the
        # gap between repeats (must exceed the gateway's RF send window — see
        # _IVEO_REPEAT_DELAY). Tunable via updateOptions().
        self.iveoRepeat = _IVEO_REPEAT
        self.iveoRepeatDelay = _IVEO_REPEAT_DELAY
        self.iveoTravelTime = _IVEO_TRAVEL_TIME

        #Logger
        self._LOGGER: logging.Logger = logger or logging.getLogger(__name__)


    # Legacy worker was removed in favor of dedicated TX/RX tasks.
    async def _worker(self):
        # Kept for backward compatibility in tests/mocks.
        return True

    async def _build_transport(self, port: str):
        self._transport = SerialTransport(port=port, logger=self._LOGGER)
        await self._transport.ensure_open()
        self._serial = None

    async def _teardown_transport(self):
        if self._transport:
            await self._transport.shutdown()
        self._transport = None
        self._serial = None

    async def _probe_port(self, port: str, fromConfigFlow: bool = False) -> bool:
        """Attempt to connect and verify a Selve gateway on the given port."""
        try:
            await self._build_transport(port)
            ok = await self.pingGateway(fromConfigFlow=fromConfigFlow)
            if ok:
                try:
                    ver = await self.getVersionG()
                    if hasattr(ver, "name") and ver.name == "selve.GW." + str(CommeoServiceCommand.GETVERSION.value):
                        self._port = port
                        await self.stopWorker()
                        return True
                except Exception as e:
                    self._LOGGER.debug(f"Probe getVersion failed on {port}: {e}")
        except Exception as e:
            self._LOGGER.debug(f"Probe failed on {port}: {e}")

        await self.stopWorker()
        await self._teardown_transport()
        return False
    

    def list_ports(self):
        return _comports()

    async def check_port(self, port):
        if port is not None:
            async with self._connLock:
                return await self._probe_port(port, fromConfigFlow=True)
        return False


    async def setup(self, discover=False, fromConfigFlow=False):
        async with self._connLock:
            return await self._setup_unlocked(discover, fromConfigFlow)

    async def _setup_unlocked(self, discover=False, fromConfigFlow=False):
        self._LOGGER.info("Setup")
        self._closing = False

        # Never swap the queues under a running worker: a dispatch task still
        # awaiting the old rxQ instance would hang on it forever while the
        # reader feeds the new queue — the frozen-state failure mode.
        if any(t is not None and not t.done()
               for t in (self._tx_task, self._dispatch_task, self._keepalive_task)):
            await self.stopWorker()

        self.rxQ = asyncio.Queue()
        self.txQ = asyncio.Queue()


        if self._port is not None:
            try:
                if await self._probe_port(self._port, fromConfigFlow=fromConfigFlow):
                    if not fromConfigFlow:
                        if discover:
                            self._LOGGER.info("Discovering devices")
                            await self._discover_unlocked()
                        await self.startWorker()
                    return
            except (OSError, IOError) as e:
                self._LOGGER.debug("Configured port not valid! " + str(e))
            except Exception as e:
                self._LOGGER.error("Unknown exception: " + str(e))


        loop = asyncio.get_running_loop()
        available_ports = await loop.run_in_executor(None, _comports)
        
        self._LOGGER.debug("available comports: " + str(available_ports))

        if len(available_ports) == 0:
            self._LOGGER.error("No available comports!")
            raise PortError

        for p in available_ports:
            try:
                if await self._probe_port(p.device, fromConfigFlow=fromConfigFlow):
                    if not fromConfigFlow:
                        if discover:
                            self._LOGGER.info("Discovering devices")
                            await self._discover_unlocked()
                        await self.startWorker()
                    return
            except Exception as e:
                self._LOGGER.error("Error at com port: " + str(e))
        else:
            self._LOGGER.error("No gateway on comports found!")
            raise PortError

    async def recover(self):
        self._LOGGER.info("(Selve Worker): " + "Recover serial connection")
        self._LOGGER.debug("(Selve Worker): " + "Waiting 5 seconds before trying...")
        await asyncio.sleep(5)
        self._LOGGER.debug("(Selve Worker): " + "Recovering")

        # Tear down the broken transport, then rebuild it directly without calling
        # _probe_port / stopWorker, which would kill the running TX/dispatch tasks.
        await self._teardown_transport()

        if self._port is not None:
            try:
                await self._build_transport(self._port)
                if self.rxQ is not None and self._transport is not None:
                    await self._transport.start_reader(self.rxQ)
                self._LOGGER.info("(Selve Worker): Recovery successful on " + str(self._port))
                return
            except (OSError, IOError) as e:
                self._LOGGER.debug("(Selve Worker): " + "Configured port not valid, maybe it has changed, trying other ports... " + str(e))
            except Exception as e:
                self._LOGGER.error("(Selve Worker): " + "Unknown exception: " + str(e))

        loop = asyncio.get_running_loop()
        available_ports = await loop.run_in_executor(None, _comports)

        self._LOGGER.debug("(Selve Worker): " + "available comports: " + str(available_ports))

        if len(available_ports) == 0:
            self._LOGGER.error("(Selve Worker): " + "No available comports!")
            return False

        for p in available_ports:
            try:
                await self._build_transport(p.device)
                self._port = p.device
                if self.rxQ is not None and self._transport is not None:
                    await self._transport.start_reader(self.rxQ)
                self._LOGGER.info("(Selve Worker): Recovery successful on " + str(p.device))
                return
            except Exception as e:
                self._LOGGER.error("(Selve Worker): " + "Error at com port: " + str(e))
        else:
            self._LOGGER.error("(Selve Worker): " + "No gateway on comports found!")
            raise PortError


    @property
    def connected(self) -> bool:
        """True while the worker pipeline and transport are up.

        Integrations can bind entity availability to this — a dead gateway
        that still shows "available" entities masks the failure for hours.
        Reports False during an ongoing recovery.
        """
        if self._recovering or not self._link_ok:
            return False
        workers = (self._tx_task, self._dispatch_task)
        return (self._transport is not None
                and all(t is not None and not t.done() for t in workers))

    def _set_link_ok(self, value: bool) -> None:
        """Update link health and push the change to registered callbacks."""
        if self._link_ok == value:
            return
        self._link_ok = value
        self._LOGGER.info("(Selve): link %s", "restored" if value else "lost")
        # device=None -> "something global changed, refresh everything"
        self._fire_callbacks(None)

    async def startWorker(self):
        # All three workers must be alive for the early-return: checking only
        # the TX task let a dead dispatch task go unnoticed forever — TX kept
        # "working" while no response was ever processed again (frozen states).
        workers = (self._tx_task, self._dispatch_task, self._keepalive_task)
        if all(t is not None and not t.done() for t in workers):
            return  # already running
        self._LOGGER.debug("Starting worker")
        self._pauseWorker.clear()
        self._stopThread.clear()

        if self.txQ is None or not isinstance(self.txQ, asyncio.Queue):
            self.txQ = asyncio.Queue()
        if self.rxQ is None or not isinstance(self.rxQ, asyncio.Queue):
            self.rxQ = asyncio.Queue()
        if self._event_queue is None or not isinstance(self._event_queue, asyncio.Queue):
            self._event_queue = asyncio.Queue()

        # Ensure transport and reader task are running
        if self._transport is None and self._port is not None:
            await self._build_transport(self._port)
        if self._transport is not None:
            await self._transport.start_reader(self.rxQ)

        if self._tx_task is None or self._tx_task.done():
            self._tx_task = asyncio.create_task(self._tx_loop())

        if self._dispatch_task is None or self._dispatch_task.done():
            self._dispatch_task = asyncio.create_task(self._dispatch_loop())

        if self._keepalive_task is None or self._keepalive_task.done():
            self._last_rx = time.monotonic()
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())

        # Maintain legacy attribute name for compatibility
        self.workerTask = self._tx_task


    async def _tx_loop(self):
        self._LOGGER.debug("(Selve TX): loop started")
        while not self._stopThread.is_set():
            try:
                item = await self.txQ.get()
                future = None
                # Allow legacy queue usage with bare Command
                if isinstance(item, tuple) and len(item) == 2:
                    command, future = item
                else:
                    command, future = item, None

                if future is not None:
                    # Remember which method this future waits for: matching
                    # responses by position alone silently mis-assigns every
                    # later response once a single one is lost or late.
                    self._pending_futures.append(
                        (future, getattr(command, "method_name", None))
                    )

                await self._sendCommandToGateway(command)

                if future is not None:
                    # Pace transmissions by the response instead of a fixed
                    # delay: the gateway answers in order, so the next command
                    # may go out as soon as this one's response has arrived.
                    # A timeout keeps a lost response from stalling the queue.
                    await asyncio.wait({future}, timeout=5)
                else:
                    # Fire-and-forget commands still produce a gateway reply;
                    # keep a small gap so the gateway is not flooded.
                    await asyncio.sleep(0.05)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._LOGGER.error("(Selve TX): error %s", str(e))
                if future is not None and not future.done():
                    future.set_result(False)
            finally:
                try:
                    self.txQ.task_done()
                except Exception:
                    pass


    async def _keepalive_loop(self):
        """Ping the gateway when the link has been idle.

        The serial reader reconnects after 60s without data, but an idle link
        is normal for a gateway with no traffic. The ping response keeps the
        link verifiably alive, so the reader's idle-reconnect (which drops
        unsolicited events during its close/reopen window) only fires when
        the port is actually dead.
        """
        self._LOGGER.debug("(Selve keepalive): loop started")
        while not self._stopThread.is_set():
            try:
                await asyncio.sleep(self._keepalive_interval)
                if self._stopThread.is_set():
                    break
                if time.monotonic() - self._last_rx < self._keepalive_interval:
                    self._ping_failures = 0
                    continue
                resp = await self._executeCommandSyncWithResponse(ServicePing())
                if resp is False:
                    # Timeout: the gateway (or our own dispatch pipeline) did
                    # not answer. A hung dispatch task is not "done", so the
                    # startWorker health check cannot see it — the ping is the
                    # only signal that RX is dead. Escalate instead of
                    # discarding the result.
                    self._ping_failures += 1
                    self._LOGGER.warning(
                        "(Selve keepalive): ping unanswered (%d/%d)",
                        self._ping_failures, self._keepalive_max_failures,
                    )
                    if self._ping_failures >= self._keepalive_max_failures:
                        self._ping_failures = 0
                        self._LOGGER.error(
                            "(Selve keepalive): link dead — triggering worker/transport recovery"
                        )
                        # Tell consumers now: entities should show unavailable
                        # while we rebuild, not a stale state.
                        self._set_link_ok(False)
                        # Own task: stopWorker() cancels this keepalive task,
                        # so recovery must not run inside it.
                        self._recover_task = asyncio.create_task(self._recover_from_hang())
                        return
                else:
                    self._ping_failures = 0
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._LOGGER.debug("(Selve keepalive): error %s", e)

    async def _recover_from_hang(self):
        """Full worker+transport rebuild after the keepalive declared the link dead.

        Fresh queues are essential: a hung dispatch task may still await the
        old rxQ instance; the new dispatch task must read the queue the
        reader actually feeds.
        """
        if self._recovering or self._closing:
            return
        self._recovering = True
        try:
            async with self._connLock:
                self._LOGGER.warning("(Selve recovery): rebuilding workers and transport")
                await self.stopWorker()
                await self._teardown_transport()
                if self._closing:
                    return
                self.rxQ = asyncio.Queue()
                self.txQ = asyncio.Queue()
                self._pending_futures.clear()
                await self.startWorker()
            # Ping outside the lock: it goes through the freshly started
            # workers and must not block a concurrent setup/reload.
            resp = await self._executeCommandSyncWithResponse(ServicePing())
            if resp is not False:
                self._LOGGER.info("(Selve recovery): gateway responding again")
                self._set_link_ok(True)
            else:
                self._LOGGER.error(
                    "(Selve recovery): gateway still not responding after rebuild "
                    "(next keepalive cycle will retry)"
                )
        except Exception as e:
            self._LOGGER.error("(Selve recovery): failed: %s", e)
        finally:
            self._recovering = False
            self._fire_callbacks(None)  # recovery finished: refresh availability

    async def _dispatch_loop(self):
        self._LOGGER.debug("(Selve RX): dispatcher started")
        while not self._stopThread.is_set():
            try:
                msg = await self.rxQ.get()
            except asyncio.CancelledError:
                break
            self._last_rx = time.monotonic()
            if not self._link_ok:
                self._set_link_ok(True)  # data flowing again

            try:
                resp = await self.processResponse(msg)
                if isinstance(resp, ErrorResponse):
                    # A fault is the gateway's reply to a command: resolve the
                    # waiting future with False right away instead of letting
                    # the caller run into its 10s timeout.
                    if not self._resolve_next_future(False):
                        self._LOGGER.debug("(Selve RX): error response without pending future -> %s", resp)
                elif resp not in (False, True, None):
                    if not self._resolve_next_future(
                        resp, getattr(resp, "method_name", None)
                    ):
                        self._LOGGER.debug("(Selve RX): response without pending future -> %s", resp)
                self.rxQ.task_done()
            except Exception as e:
                self._LOGGER.error("(Selve RX): error %s", str(e))
                try:
                    self.rxQ.task_done()
                except Exception:
                    pass


    def _resolve_next_future(self, result, method_name=None):
        """Resolve the pending future waiting for *method_name*.

        Without a name (gateway faults carry none) the oldest pending future
        is used. With one, only a future that actually asked for this method
        is resolved — a late or unsolicited response is dropped instead of
        being handed to the next unrelated caller.
        """
        # Drop futures nobody waits for any more (timed out / cancelled).
        while self._pending_futures and self._pending_futures[0][0].done():
            self._pending_futures.popleft()

        if not self._pending_futures:
            return False

        if method_name is None:
            fut, _ = self._pending_futures.popleft()
            fut.set_result(result)
            return True

        for idx, (fut, expected) in enumerate(self._pending_futures):
            if expected is None or expected == method_name:
                del self._pending_futures[idx]
                if idx:
                    self._LOGGER.debug(
                        "(Selve RX): response %s matched out of order (skipped %d)",
                        method_name, idx,
                    )
                fut.set_result(result)
                return True
        return False

    @staticmethod
    def _executed(response) -> bool:
        """The gateway's ``executed`` flag, or False when there is no reply.

        ``executeCommandSyncWithResponse`` returns ``False`` instead of a
        response object on a timeout or a gateway fault; reading
        ``.executed`` from that crashed every command method (#50).
        """
        return bool(getattr(response, "executed", False))

    def _discard_pending_future(self, future):
        """Remove a future from the pending queue (caller gave up on it)."""
        for idx, (fut, _) in enumerate(self._pending_futures):
            if fut is future:
                del self._pending_futures[idx]
                return

    async def stopWorker(self):
        self._LOGGER.debug("Stopping worker")
        self._pauseWorker.set()
        self._stopThread.set()
        tasks = [self._tx_task, self._dispatch_task, self._keepalive_task]
        for task in tasks:
            if task is None:
                continue
            try:
                task.cancel()
                await asyncio.wait_for(task, timeout=5)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self._LOGGER.debug("Task stopping exception: " + str(e))
        self.workerTask = None
        self._tx_task = None
        self._dispatch_task = None
        self._keepalive_task = None
        self._pending_futures.clear()
        if self._transport:
            await self._transport.stop_reader()
        if self._event_queue is not None:
            while not self._event_queue.empty():
                try:
                    self._event_queue.get_nowait()
                    self._event_queue.task_done()
                except Exception:
                    break


    async def stopGateway(self):
        # wait for the rx/tx thread to end, these need to be gathered to
        # collect all the exceptions
        self._LOGGER.debug("Preparing for termination")
        self._closing = True  # keeps a pending keepalive recovery from resurrecting the workers
        await self.stopWorker()
        # close the serial port, do the cleanup
        await self._teardown_transport()
        return True


    def register_callback(self, callback: Callable) -> None:
        """Register callback, called when a device changes state.

        The callback may optionally accept the changed device as its single
        positional argument; parameterless callbacks keep working and are
        invoked without arguments.
        """
        accepts_device = True
        try:
            inspect.signature(callback).bind(None)
        except TypeError:
            accepts_device = False
        except ValueError:
            # Builtins without introspectable signature: assume no args
            accepts_device = False
        self._callbacks[callback] = accepts_device

    def remove_callback(self, callback: Callable) -> None:
        """Remove previously registered callback."""
        self._callbacks.pop(callback, None)

    def _fire_callbacks(self, device=None) -> None:
        """Notify registered callbacks, passing the changed device if known."""
        for callback, accepts_device in list(self._callbacks.items()):
            try:
                if accepts_device:
                    callback(device)
                else:
                    callback()
            except Exception:
                self._LOGGER.exception("Error in update callback")

    def register_event_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when other events take place."""
        self._eventCallbacks.add(callback)

    def remove_event_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._eventCallbacks.discard(callback)


    async def events(self):
        """Async iterator over gateway events (device/sensor/sender/log/duty)."""
        await self.startWorker()
        while True:
            evt = await self._event_queue.get()
            self._event_queue.task_done()
            yield evt


    def updateOptions(self, reversedStopPosition = 0, iveoRepeat = None,
                      iveoRepeatDelay = None, iveoTravelTime = None):
        self.reversedStopPosition = reversedStopPosition
        if iveoRepeat is not None:
            self.iveoRepeat = iveoRepeat
        if iveoRepeatDelay is not None:
            self.iveoRepeatDelay = iveoRepeatDelay
        if iveoTravelTime is not None:
            self.iveoTravelTime = iveoTravelTime


    async def _sendCommandToGateway(self, command: Command):
        commandstr = command.serializeToXML()
        self._LOGGER.debug('Gateway writing: %s', commandstr)
        try:
            if self._transport is None:
                if self._port is None:
                    raise PortError("No serial port configured")
                await self._build_transport(self._port)

            await self._transport.write(commandstr)

        except (OSError, IOError) as se:
            self._LOGGER.info('Serial error, trying to reconnect once... %s', se)
            await self.recover()

            try:
                self._LOGGER.debug('Trying again...')
                if self._transport is None and self._port is not None:
                    await self._build_transport(self._port)
                await self._transport.write(commandstr)

            except Exception as e:
                self._LOGGER.error("error communicating: %s ; Please restart the integration!", e)

        except Exception as e:
            self._LOGGER.error("error communicating: %s ; Please restart the integration!", e)

    async def processResponse(self, xmlstr):
        """Processes an XML String into a response object. Returns False if something went wrong or the gateway returned an error."""
        # check which command was received
        # do something with the data
        # return the ready to eat response

        # The selve device sometimes answers a badformed header. This is a patch
        xmlstr = str(xmlstr)
        if '<?xml version="1.0"? encoding="UTF-8">' in xmlstr:
            xmlstr = xmlstr.replace('<?xml version="1.0"? encoding="UTF-8">', '<?xml version="1.0" encoding="UTF-8"?>')
        try:
            res = untangle.parse(xmlstr)
        except Exception as e:
            self._LOGGER.error("Error in XML: %s : %s", e, xmlstr)
            return False
        try:
            if not hasattr(res, 'methodResponse') and not hasattr(res, 'methodCall'):
                self._LOGGER.error("Bad response format")
                return None
            if hasattr(res, 'methodResponse'):
                if hasattr(res.methodResponse, 'fault'):
                    return self.create_error(res)
                else:
                    response = self.create_response(res)
            else:
                response = self.create_response_call(res)
        except Exception as e:
            self._LOGGER.error("Error in response creation: " + str(e) + " : " + xmlstr)
            return False
        try:
            # if it's a MethodResponse, it has not been sent by the gateway itself, so we can safely return it
            # otherwise it's an event, and we have to process it accordingly
            if isinstance(response, CommeoDeviceEventResponse) \
                    or isinstance(response, SensorEventResponse) \
                    or isinstance(response, SenderEventResponse) \
                    or isinstance(response, LogEventResponse) \
                    or isinstance(response, DutyCycleResponse):
                await self.processEventResponse(response)
                return True
            if isinstance(response, CommandResultResponse)\
                    or isinstance(response, IveoResultResponse):
                #update device values
                self._handleCommandResult(response)
            if isinstance(response, DeviceGetValuesResponse):
                self.updateCommeoDeviceValuesFromResponse(int(response.parameters[1][1]), response)
            if isinstance(response, SenderTeachResultResponse) \
                or isinstance(response, SensorTeachResultResponse)\
                or isinstance(response, DeviceScanResultResponse):
                await self.processTeachResponse(response)
                return True

            return response


        except Exception as e:
            self._LOGGER.error("Error in response processing: %s : %s", e, xmlstr)
            return False

    def create_error(self, obj):
        if hasattr(obj, "methodResponse"):
            return ErrorResponse(obj.methodResponse.fault.array.string.cdata, obj.methodResponse.fault.array.int.cdata)
        else:
            return False

    def create_response(self, obj):
        if hasattr(obj, "methodResponse"):
            array = obj.methodResponse.array
            return self._create_response(array)
        else:
            raise CommunicationError()

    def create_response_call(self, obj):
        if hasattr(obj, "methodCall"):
            array = obj.methodCall.array
            return self._create_response(array, obj.methodCall.methodName)
        else:
            raise CommunicationError()

    def _create_response(self, array, methodName = ""):
        str_params = []
        if hasattr(array, "string"):
            if methodName == "":
                methodName = list(array.string)[0].cdata
                str_params_tmp = list(array.string)[1:]
            else:
                str_params_tmp = list(array.string)[0:]
            str_params = [(ParameterType.STRING, v.cdata) for v in str_params_tmp]
        int_params = []
        if hasattr(array, str(ParameterType.INT.value)):
            int_params = [(ParameterType.INT, v.cdata) for v in list(array.int)]
        b64_params = []
        if hasattr(array, str(ParameterType.BASE64.value)):
            b64_params = [(ParameterType.BASE64, v.cdata) for v in list(array.base64)]
        paramslist = [str_params, int_params, b64_params]
        flat_params_list = list(chain.from_iterable(paramslist))

        ##Service
        if methodName == "selve.GW." + str(CommeoServiceCommand.PING.value):
            return ServicePingResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.GETSTATE.value):
            return ServiceGetStateResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.GETVERSION.value):
            return ServiceGetVersionResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.RESET.value):
            return ServiceResetResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.FACTORYRESET.value):
            return ServiceFactoryResetResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.SETLED.value):
            return ServiceSetLedResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoServiceCommand.GETLED.value):
            return ServiceGetLedResponse(methodName, flat_params_list)

        ##Param
        if methodName == "selve.GW." + str(CommeoParamCommand.SETFORWARD.value):
            return ParamSetForwardResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETFORWARD.value):
            return ParamGetForwardResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.SETEVENT.value):
            return ParamSetEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETEVENT.value):
            return ParamGetEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.SETDUTY.value):
            return ParamSetDutyResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETDUTY.value):
            return ParamGetDutyResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.SETRF.value):
            return ParamSetRfResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETRF.value):
            return ParamGetRfResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETTEMPERATURE.value):
            return ParamGetTemperatureResponse(methodName, flat_params_list)

        ##Device
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SCANSTART.value):
            return DeviceScanStartResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SCANSTOP.value):
            return DeviceScanStopResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SCANRESULT.value):
            return DeviceScanResultResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SAVE.value):
            return DeviceSaveResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.GETIDS.value):
            return DeviceGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.GETINFO.value):
            return DeviceGetInfoResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.GETVALUES.value):
            return DeviceGetValuesResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SETFUNCTION.value):
            return DeviceSetFunctionResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SETLABEL.value):
            return DeviceSetLabelResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.SETTYPE.value):
            return DeviceSetTypeResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.DELETE.value):
            return DeviceDeleteResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoDeviceCommand.WRITEMANUAL.value):
            return DeviceWriteManualResponse(methodName, flat_params_list)

        ##Sensor
        if methodName == "selve.GW." + str(CommeoSensorCommand.TEACHSTART.value):
            return SensorTeachStartResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.TEACHSTOP.value):
            return SensorTeachStopResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.TEACHRESULT.value):
            return SensorTeachResultResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.GETIDS.value):
            return SensorGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.GETINFO.value):
            return SensorGetInfoResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.GETVALUES.value):
            return SensorGetValuesResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.SETLABEL.value):
            return SensorSetLabelResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.DELETE.value):
            return SensorDeleteResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSensorCommand.WRITEMANUAL.value):
            return SensorWriteManualResponse(methodName, flat_params_list)

        ##SenSim
        if methodName == "selve.GW." + str(CommeoSenSimCommand.STORE.value):
            return SenSimStoreResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.DELETE.value):
            return SenSimDeleteResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.GETCONFIG.value):
            return SenSimGetConfigResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.SETCONFIG.value):
            return SenSimSetConfigResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.SETLABEL.value):
            return SenSimSetLabelResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.SETVALUES.value):
            return SenSimSetValuesResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.GETVALUES.value):
            return SenSimGetValuesResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.GETIDS.value):
            return SenSimGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.FACTORY.value):
            return SenSimFactoryResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.DRIVE.value):
            return SenSimDriveResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.SETTEST.value):
            return SenSimSetTestResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenSimCommand.GETTEST.value):
            return SenSimGetTestResponse(methodName, flat_params_list)

        ##Sender
        if methodName == "selve.GW." + str(CommeoSenderCommand.TEACHSTART.value):
            return SenderTeachStartResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.TEACHSTOP.value):
            return SenderTeachStopResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.TEACHRESULT.value):
            return SenderTeachResultResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.GETIDS.value):
            return SenderGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.GETINFO.value):
            return SenderGetInfoResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.GETVALUES.value):
            return SenderGetValuesResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.SETLABEL.value):
            return SenderSetLabelResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.DELETE.value):
            return SenderDeleteResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoSenderCommand.WRITEMANUAL.value):
            return SenderWriteManualResponse(methodName, flat_params_list)

        ##Group
        if methodName == "selve.GW." + str(CommeoGroupCommand.READ.value):
            return GroupReadResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoGroupCommand.WRITE.value):
            return GroupWriteResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoGroupCommand.GETIDS.value):
            return GroupGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoGroupCommand.DELETE.value):
            return GroupDeleteResponse(methodName, flat_params_list)

        ##Command
        if methodName == "selve.GW." + str(CommeoCommandCommand.DEVICE.value):
            return CommandDeviceResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoCommandCommand.GROUP.value):
            return CommandGroupResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoCommandCommand.GROUPMAN.value):
            return CommandGroupManResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoCommandCommand.RESULT.value):
            return CommandResultResponse(methodName, flat_params_list)

        ##Iveo
        if methodName == "selve.GW." + str(IveoCommand.FACTORY.value):
            return IveoFactoryResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.SETCONFIG.value):
            return IveoSetConfigResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.GETCONFIG.value):
            return IveoGetConfigResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.GETIDS.value):
            return IveoGetIdsResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.SETREPEATER.value):
            return IveoSetRepeaterResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.GETREPEATER.value):
            return IveoGetRepeaterResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.SETLABEL.value):
            return IveoSetLabelResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.TEACH.value):
            return IveoTeachResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.LEARN.value):
            return IveoLearnResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.MANUAL.value):
            return IveoManualResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.AUTOMATIC.value):
            return IveoAutomaticResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(IveoCommand.RESULT.value):
            return IveoResultResponse(methodName, flat_params_list)

        ##Firmware
        if methodName == "selve.GW." + str(CommeoFirmwareCommand.GETVERSION.value):
            return FirmwareGetVersionResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoFirmwareCommand.UPDATE.value):
            return FirmwareUpdateResponse(methodName, flat_params_list)

        ##Events
        if methodName == "selve.GW." + str(CommeoEventCommand.DEVICE.value):
            return CommeoDeviceEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoEventCommand.SENSOR.value):
            return SensorEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoEventCommand.SENDER.value):
            return SenderEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoEventCommand.LOG.value):
            return LogEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoEventCommand.DUTYCYCLE.value):
            return DutyCycleResponse(methodName, flat_params_list)

        # Any other response (unknown)
        return MethodResponse(methodName, flat_params_list)

    async def executeCommand(self, command: Command):
        await self.startWorker()
        await self.txQ.put((command, None))


    async def executeCommandSyncWithResponse(self, command: Command, fromConfigFlow=False):
        await self.startWorker()
        resp = await self._executeCommandSyncWithResponse(command)
        if resp is False:
            resp = await self._executeCommandSyncWithResponse(command)
        return resp


    async def executeCommandSyncWithResponsefromWorker(self, command: Command):
        resp = await self._executeCommandSyncWithResponse(command)
        if resp is False:
            resp = await self._executeCommandSyncWithResponse(command)
        return resp

    async def _executeCommandSyncWithResponse(self, command: Command):
        await self.startWorker()
        loop = self.loop or asyncio.get_running_loop()
        future = loop.create_future()
        await self.txQ.put((command, future))

        try:
            return await asyncio.wait_for(future, timeout=10)
        except asyncio.TimeoutError:
            if not future.done():
                future.cancel()
            # Leaving it queued would let a late response be handed to an
            # unrelated caller further down the line.
            self._discard_pending_future(future)
            return False




    async def discover(self):
        async with self._connLock:
            return await self._discover_unlocked()

    async def _discover_unlocked(self):

        await self.stopWorker()
        # Rebuild transport for a clean connection (avoids stale StreamReader state
        # left over from _probe_port, which explains why USB-replug was needed).
        await self._teardown_transport()
        # Flush any stale messages left in the receive queue from the probe phase
        # (unsolicited gateway events or responses the cancelled dispatch task never
        # consumed).  If we don't do this, the dispatch loop matches those old
        # messages against the new discover() command futures, resolving them with
        # the wrong response object and causing silent discover failures.
        self.rxQ = asyncio.Queue()
        # txQ too: a command queued just before discover() would otherwise be
        # injected into the middle of the discovery sequence.
        self.txQ = asyncio.Queue()
        self._pending_futures.clear()
        await self.setEvents(0,0,0,0,0)
        rdy = await self.gatewayReady()
        if rdy:
            iveoIds: IveoGetIdsResponse = await self.executeCommandSyncWithResponse(IveoGetIds())
            deviceIds: DeviceGetIdsResponse = await self.executeCommandSyncWithResponse(DeviceGetIds())
            groupIds: GroupGetIdsResponse = await self.executeCommandSyncWithResponse(GroupGetIds())
            sensorIds: SensorGetIdsResponse = await self.executeCommandSyncWithResponse(SensorGetIds())
            senderIds: SenderGetIdsResponse = await self.executeCommandSyncWithResponse(SenderGetIds())
            senSimIds: SenSimGetIdsResponse = await self.executeCommandSyncWithResponse(SenSimGetIds())

            for i in iveoIds.ids:
                config: IveoGetConfigResponse = await self.executeCommandSyncWithResponse(IveoGetConfig(i))
                device = IveoDevice(i, device_sub_type=config.deviceType)
                device.name = config.name
                device.activity = config.activity
                self.addOrUpdateDevice(device, SelveTypes.IVEO)

            for i in deviceIds.ids:
                config: DeviceGetInfoResponse = await self.executeCommandSyncWithResponse(DeviceGetInfo(i))
                device = SelveDevice(i, device_type=SelveTypes.DEVICE, device_sub_type=config.deviceType)
                device.name = config.name
                device.device_sub_type = config.deviceType
                device.rfAdress = config.rfAddress
                device.infoState = config.state
                self.addOrUpdateDevice(device, SelveTypes.DEVICE)
                config: DeviceGetValuesResponse = await self.executeCommandSyncWithResponse(DeviceGetValues(i))
                device.state = config.movementState

                # None = gateway reported "position unknown" (0x8000): leave it
                # unknown instead of inventing a definite position at startup.
                if config.value is None:
                    device.value = None
                elif self.reversedStopPosition == 0:
                    device.value = config.value
                else:
                    device.value = 100 - config.value

                if config.targetValue is None:
                    device.targetValue = None
                elif self.reversedStopPosition == 0:
                    device.targetValue = config.targetValue
                else:
                    device.targetValue = 100 - config.targetValue

                device.unreachable = config.unreachable
                device.overload = config.overload
                device.obstructed = config.obstructed
                device.alarm = config.alarm
                device.lostSensor = config.lostSensor
                device.automaticMode = config.automaticMode
                device.gatewayNotLearned = config.gatewayNotLearned
                device.windAlarm = config.windAlarm
                device.rainAlarm = config.rainAlarm
                device.freezingAlarm = config.freezingAlarm
                device.dayMode = config.dayMode
                self.addOrUpdateDevice(device, SelveTypes.DEVICE)

            for i in groupIds.ids:
                config: GroupReadResponse = await self.executeCommandSyncWithResponse(GroupRead(i))
                device = SelveGroup(i)
                device.device_type = SelveTypes.GROUP
                device.name = config.groupName
                device.mask = config.mask
                self.addOrUpdateDevice(device, SelveTypes.GROUP)

            for i in sensorIds.ids:
                device = SelveSensor(i)
                config: SensorGetInfoResponse = await self.executeCommandSyncWithResponse(SensorGetInfo(i))
                device.rfAdress = config.rfAddress
                device.device_type = SelveTypes.SENSOR
                self.addOrUpdateDevice(device, SelveTypes.SENSOR)
                config: SensorGetValuesResponse = await self.executeCommandSyncWithResponse(SensorGetValues(i))
                device.windDigital = config.windDigital
                device.rainDigital = config.rainDigital
                device.tempDigital = config.tempDigital
                device.lightDigital = config.lightDigital
                device.sensorState = config.sensorState
                device.tempAnalog = config.tempAnalog
                device.windAnalog = config.windAnalog
                device.sun1Analog = config.sun1Analog
                device.dayLightAnalog = config.dayLightAnalog
                device.sun2Analog = config.sun2Analog
                device.sun3Analog = config.sun3Analog
                self.addOrUpdateDevice(device, SelveTypes.SENSOR)

            for i in senderIds.ids:
                config: SenderGetInfoResponse = await self.executeCommandSyncWithResponse(SenderGetInfo(i))
                device = SelveSender(i)
                device.device_type = SelveTypes.SENDER
                device.name = config.name
                device.rfAdress = config.rfAddress
                device.channel = config.rfChannel
                device.resetCount = config.rfResetCount
                self.addOrUpdateDevice(device, SelveTypes.SENDER)

            for i in senSimIds.ids:
                config: SenSimGetConfigResponse = await self.executeCommandSyncWithResponse(SenSimGetConfig(i))
                device = SelveSenSim(i)
                device.activity = config.activity
                device.device_type = SelveTypes.SENSIM
                self.addOrUpdateDevice(device, SelveTypes.SENSIM)
                config: SenSimGetValuesResponse = await self.executeCommandSyncWithResponse(SenSimGetValues(i))
                device.windDigital = config.windDigital
                device.rainDigital = config.rainDigital
                device.tempDigital = config.tempDigital
                device.lightDigital = config.lightDigital
                device.sensorState = config.sensorState
                device.tempAnalog = config.tempAnalog
                device.windAnalog = config.windAnalog
                device.sun1Analog = config.sun1Analog
                device.dayLightAnalog = config.dayLightAnalog
                device.sun2Analog = config.sun2Analog
                device.sun3Analog = config.sun3Analog
                self.addOrUpdateDevice(device, SelveTypes.SENSIM)

        await self.setEvents(1,1,1,1,1)
        await self.startWorker()
        self.list_devices()


    async def updateAllDevices(self):
        for device in list(self.devices[SelveTypes.DEVICE.value].values()):
            await self.updateCommeoDeviceValues(device.id)
        for sensor in list(self.devices[SelveTypes.SENSOR.value].values()):
            await self.updateSensorValuesAsync(sensor.id)
        for senSim in list(self.devices[SelveTypes.SENSIM.value].values()):
            await self.updateSenSimValuesAsync(senSim.id)
        for sender in list(self.devices[SelveTypes.SENDER.value].values()):
            await self.updateSenderValuesAsync(sender.id)



    def addOrUpdateDevice(self, device, type: SelveTypes):
        self.devices[type.value][device.id] = device
        # add in gateway

        # if there is a callback for updates, call it
        self._fire_callbacks(device)

    def getDevice(self, id: int, type: SelveTypes) -> SelveDevice | SelveSensor | SelveSender | SelveGroup | SelveSenSim | None:
        if id in self.devices[type.value]:
            return self.devices[type.value][id]
        return None


    def deleteDevice(self, id, type: SelveTypes):
        # delete in GW
        self.devices[type.value].pop(id)

    def is_id_registered(self, id, type: SelveTypes):
        return id in self.devices[type.value]

    def findFreeId(self, type: SelveTypes):
        i = 0
        boundary = 1
        if type is SelveTypes.SENDER:
            boundary = 62
        if type is SelveTypes.SENSOR:
            boundary = 7
        if type is SelveTypes.DEVICE:
            boundary = 63
        if type is SelveTypes.GROUP:
            boundary = 31
        if type is SelveTypes.IVEO:
            boundary = 63
        if type is SelveTypes.SENSIM:
            boundary = 7

        while i < boundary:
            if not self.is_id_registered(i, type):
                return i
            i = i + 1

    async def processTeachResponse(self, response):
        if isinstance(response, SenderTeachResultResponse):
            if response.senderId == -1:
                self._LOGGER.info("No Senders found yet...")
            else:
                self._LOGGER.info("Sender found: " + str(response.name) + " - " + str(response.senderId))
            self._LOGGER.info("Time left for teaching: " + str(response.timeLeft) + "s")
            self._LOGGER.debug("Current teaching state: " + str(response.teachState.name))
            self._LOGGER.info("Last event: " + str(response.senderEvent.name))

        if isinstance(response, SensorTeachResultResponse):
            if response.foundId == -1:
                self._LOGGER.info("No Senders found yet...")
            else:
                self._LOGGER.info("Sensor found: " + str(response.foundId))
            self._LOGGER.info("Time left for teaching: " + str(response.timeLeft) + "s")
            self._LOGGER.debug("Current teaching state: " + str(response.teachState.name))

        if isinstance(response, DeviceScanResultResponse):
            if response.noNewDevices <= 0:
                self._LOGGER.info("No Senders found yet...")
            else:
                self._LOGGER.info("Devices found: " + str(response.foundIds))
            self._LOGGER.debug("Current teaching state: " + str(response.scanState.name))


        for callback in self._eventCallbacks:
            callback(response)

        if self._event_queue is not None:
            await self._event_queue.put(response)


    async def processEventResponse(self, response):
        if isinstance(response, CommeoDeviceEventResponse):
            # This is a commeo device response, Iveo does not generate events because it is a one way communication protocol
            if self.is_id_registered(response.id, SelveTypes.DEVICE):
                device: SelveDevice = self.devices[SelveTypes.DEVICE.value][response.id]
            else:
                device = SelveDevice(response.id, SelveTypes.DEVICE, response.deviceType)
                device.name = response.name
                device.communicationType = CommunicationType.COMMEO
                self._LOGGER.error("Id not found, creating")

            device.state = response.actorState

            # None = gateway reported "position unknown" (0x8000): keep the
            # last known value instead of overwriting it with a phantom.
            if response.value is not None:
                if self.reversedStopPosition == 0:
                    device.value = response.value
                else:
                    device.value = 100 - response.value

            if response.targetValue is not None:
                if self.reversedStopPosition == 0:
                    device.targetValue = response.targetValue
                else:
                    device.targetValue = 100 - response.targetValue

            device.unreachable = response.unreachable
            device.overload = response.overload
            device.obstructed = response.obstructed
            device.alarm = response.alarm
            device.lostSensor = response.lostSensor
            device.automaticMode = response.automaticMode
            device.gatewayNotLearned = response.gatewayNotLearned
            device.windAlarm = response.windAlarm
            device.rainAlarm = response.rainAlarm
            device.freezingAlarm = response.freezingAlarm
            device.dayMode = response.dayMode
            device.device_type = response.deviceType

            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            if device.state == MovementState.STOPPED_OFF:
                self._stop_movement_polling(device.id)

        if isinstance(response, SensorEventResponse):
            if self.is_id_registered(response.id, SelveTypes.SENSOR):
                sensor: SelveSensor = self.devices[SelveTypes.SENSOR.value][response.id]
            else:
                sensor = SelveSensor(response.id)
                self._LOGGER.error("Id not found, creating")

            sensor.windDigital = response.windDigital
            sensor.rainDigital = response.rainDigital
            sensor.tempDigital = response.tempDigital
            sensor.lightDigital = response.lightDigital
            sensor.sensorState = response.sensorState
            sensor.tempAnalog = response.tempAnalog
            sensor.windAnalog = response.windAnalog
            sensor.sun1Analog = response.sun1Analog
            sensor.dayLightAnalog = response.dayLightAnalog
            sensor.sun2Analog = response.sun2Analog
            sensor.sun3Analog = response.sun3Analog
            self.addOrUpdateDevice(sensor, SelveTypes.SENSOR)

        if isinstance(response, SenderEventResponse):
            if self.is_id_registered(response.id, SelveTypes.SENDER):
                sender: SelveSender = self.getDevice(response.id, SelveTypes.SENDER)
            else:
                sender = SelveSender(response.id)
                self._LOGGER.info("Id not found, creating")

            sender.lastEvent = response.event
            sender.name = response.senderName
            self.addOrUpdateDevice(sender, SelveTypes.SENDER)

        if isinstance(response, LogEventResponse):
            self.lastLogEvent = response
            # The gateway's own diagnostics, not faults of this library —
            # logged one level lower than the gateway rates them. "Command
            # overwritten" only means a newer command replaced a pending one
            # (normal operation); at any level it flooded the HA log (#48).
            level, label = {
                LogType.INFO: (logging.DEBUG, "Info"),
                LogType.WARNING: (logging.INFO, "Warning"),
                LogType.ERROR: (logging.WARNING, "Error"),
            }.get(response.logType, (logging.INFO, "Info"))
            if "overwritten" in response.logDescription.lower():
                level = logging.DEBUG
            self._LOGGER.log(
                level, "Gateway Log %s: %s - %s - %s - %s", label,
                response.logCode, response.logStamp, response.logValue,
                response.logDescription,
            )

        if isinstance(response, DutyCycleResponse):
            self.sendingBlocked = response.mode
            self.utilization = response.traffic
            

        for callback in self._eventCallbacks:
            callback(response)


    def _handleCommandResult(self, response):
        if isinstance(response, IveoResultResponse):
            for id in response.executedIds:
                dev = self.getDevice(id, SelveTypes.IVEO)
                if dev is None:
                    continue
                if response.command is DriveCommandIveo.DOWN:
                    dev.state = MovementState.DOWN_ON
                    self._start_iveo_travel_timer(id)
                elif response.command is DriveCommandIveo.UP:
                    dev.state = MovementState.UP_ON
                    self._start_iveo_travel_timer(id)
                elif response.command is DriveCommandIveo.STOP:
                    dev.state = MovementState.STOPPED_OFF
                    self._stop_iveo_travel_timer(id)
                self.addOrUpdateDevice(dev, SelveTypes.IVEO)

        elif isinstance(response, CommandResultResponse):
            for id in response.successIds:
                self._commeo_pending.pop(id, None)
                dev = self.getDevice(id, SelveTypes.DEVICE)
                if dev is None:
                    continue
                dev.unreachable = False
                if response.command is DriveCommandCommeo.DRIVEDOWN:
                    dev.state = MovementState.DOWN_ON
                elif response.command is DriveCommandCommeo.DRIVEUP:
                    dev.state = MovementState.UP_ON
                elif response.command is DriveCommandCommeo.STOP:
                    dev.state = MovementState.STOPPED_OFF
                elif response.command is DriveCommandCommeo.STEPDOWN:
                    dev.state = MovementState.DOWN_ON
                elif response.command is DriveCommandCommeo.STEPUP:
                    dev.state = MovementState.UP_ON
                self.addOrUpdateDevice(dev, SelveTypes.DEVICE)
            for position, id in enumerate(response.failedIds):
                self._schedule_commeo_retry(id, position)
                dev = self.getDevice(id, SelveTypes.DEVICE)
                if dev is None:
                    continue
                dev.unreachable = True
                self.addOrUpdateDevice(dev, SelveTypes.DEVICE)


    ### Service

    async def pingGateway(self, fromConfigFlow=False):
        cmd = ServicePing()
        methodResponse = await self.executeCommandSyncWithResponse(cmd, fromConfigFlow=fromConfigFlow)
        try:
            if hasattr(methodResponse, "name"):
                if methodResponse.name == "selve.GW.service.ping":
                    self._LOGGER.debug("Ping back")
                    return True
        except:
            self._LOGGER.debug("Error in ping")
        self._LOGGER.debug("No ping")
        return False

    async def pingGatewayFromWorker(self, fromConfigFlow=False):
        cmd = ServicePing()
        methodResponse = await self.executeCommandSyncWithResponsefromWorker(cmd)
        try:
            if hasattr(methodResponse, "name"):
                if methodResponse.name == "selve.GW.service.ping":
                    self._LOGGER.debug("Ping back")
                    return True
        except:
            self._LOGGER.debug("Error in ping")
        self._LOGGER.debug("No ping")
        return False


    async def gatewayState(self):
        cmd = ServiceGetState()
        try:
            methodResponse = await self.executeCommandSyncWithResponse(cmd)
        except GatewayError:
            self._LOGGER.error(str(GatewayError))
            methodResponse = None

        if hasattr(methodResponse, "name"):
            if methodResponse.name == "selve.GW." + str(CommeoServiceCommand.GETSTATE.value):
                if hasattr(methodResponse, "parameters"):
                    status = ServiceState(int(methodResponse.parameters[0][1]))
                    self._LOGGER.debug(f'Gateway state: {status}')
                    self.state = status
                    return status
        return None

    async def gatewayReady(self):
        state = await self.gatewayState()
        return state is ServiceState.READY

    async def getVersionG(self):
        cmd = ServiceGetVersion()
        methodResponse = await self.executeCommandSyncWithResponse(cmd)
        return methodResponse

    async def getGatewayFirmwareVersion(self):
        command = await self.getVersionG()
        if hasattr(command, "version"):
            return command.version
        else:
            return False

    async def getGatewaySerial(self):
        command = await self.getVersionG()
        if hasattr(command, "serial"):
            return command.serial
        else:
            return False

    async def getGatewaySpec(self):
        command = await self.getVersionG()
        if hasattr(command, "spec"):
            return command.spec
        else:
            return False

    def list_devices(self):
        """[summary]
        Log the list of registered devices
        """
        for id, val in self.devices.items():
            for ida, device in val.items():
                self._LOGGER.info(str(device))

    async def resetGateway(self):
        command = ServiceReset()
        response: ServiceResetResponse = await self.executeCommandSyncWithResponse(command)
        if self._executed(response) is not True:
            self._LOGGER.info("Error: Gateway could not be reset or loads too long")

        # time.sleep(2)

        start_time = time.time()
        while await self.gatewayState() != ServiceState.READY:
            if time.time() - start_time >= 30:
                self._LOGGER.info("Error: Gateway could not be reset or loads too long")
                break
            await asyncio.sleep(0.1)
        self._LOGGER.info("Gateway reset")

    async def factoryResetGateway(self):
        command = ServiceFactoryReset()
        response: ServiceFactoryResetResponse = await self.executeCommandSyncWithResponse(command)
        if self._executed(response) is not True:
            self._LOGGER.info("Error: Gateway could not be reset or loads too long")

        start_time = time.time()
        while await self.gatewayState() != ServiceState.READY:
            if time.time() - start_time >= 60:
                self._LOGGER.info("Error: Gateway could not be reset or loads too long")
                break
            await asyncio.sleep(0.1)
        self._LOGGER.info("Gateway factory reset")
        return self._executed(response)

    async def setLED(self, state: bool):
        command = ServiceSetLed(state)
        response: ServiceSetLedResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def getLED(self):
        command = ServiceGetLed()
        response: ServiceGetLedResponse = await self.executeCommandSyncWithResponse(command)
        return response

    ### Param
    async def setForward(self, state: bool):
        command = ParamSetForward(state)
        response: ParamSetForwardResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def getForward(self):
        command = ParamGetForward()
        response: ParamGetForwardResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def setEvents(self, eventDevice = False, eventSensor = False, eventSender = False, eventLogging = False, eventDuty = False):
        command = ParamSetEvent(eventDevice, eventSensor, eventSender, eventLogging, eventDuty)
        return await self.executeCommandSyncWithResponse(command)


    async def getEvents(self):
        command = ParamGetEvent()
        response: ParamGetEventResponse = await self.executeCommandSyncWithResponse(command)
        return response


    async def getDuty(self):
        command = ParamGetDuty()
        response: ParamGetDutyResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def getRF(self):
        command = ParamGetRf()
        response: ParamGetRfResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def setDuty(self, mode: int):
        command = ParamSetDuty(mode)
        response: ParamSetDutyResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def setRF(self, netAddress: int, resetCount: int):
        command = ParamSetRf(netAddress, resetCount)
        response: ParamSetRfResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def getTemperature(self):
        command = ParamGetTemperature()
        response: ParamGetTemperatureResponse = await self.executeCommandSyncWithResponse(command)
        return response



    ##Device functions
    async def scanStart(self):
        command = DeviceScanStart()
        response: DeviceScanStartResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def scanStop(self):
        command = DeviceScanStop()
        response: DeviceScanStopResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def scanResult(self):
        """ manually polls the scan state, but the states are being reported automatically by the gateway itself"""
        command = DeviceScanResult()
        response: DeviceScanResultResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def deviceSave(self, id: int):
        command = DeviceSave(id)
        response: DeviceSaveResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceGetIds(self):
        command = DeviceGetIds()
        response: DeviceGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def deviceGetInfo(self, id: int):
        command = DeviceGetInfo(id)
        response: DeviceGetInfoResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def deviceGetValues(self, id: int):
        command = DeviceGetValues(id)
        response: DeviceGetValuesResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def deviceSetFunction(self, id: int, function: DeviceFunctions):
        command = DeviceSetFunction(id, function)
        response: DeviceSetFunctionResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceSetLabel(self, id: int, label: str):
        command = DeviceSetLabel(id, label)
        response: DeviceSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceSetType(self, id: int, type: DeviceType):
        command = DeviceSetType(id, type)
        response: DeviceSetTypeResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceDelete(self, id: int):
        command = DeviceDelete(id)
        response: DeviceDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceWriteManual(self, id: int, address: int, name: str, config: DeviceType):
        command = DeviceWriteManual(id, address, name, config)
        response: DeviceWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def deviceSavePos1(self, device: SelveDevice, type=DeviceCommandType.MANUAL):
        """Save current position as Position 1 for the device."""
        await self.executeCommand(CommandSavePos1(device.id, type))
        await self.updateCommeoDeviceValuesAsync(device.id)

    async def deviceSavePos2(self, device: SelveDevice, type=DeviceCommandType.MANUAL):
        """Save current position as Position 2 for the device."""
        await self.executeCommand(CommandSavePos2(device.id, type))
        await self.updateCommeoDeviceValuesAsync(device.id)

    async def commandResult(self):
        """Query the result of the last command execution."""
        command = CommandResult()
        response: CommandResultResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def updateCommeoDeviceValues(self, id: int):
        response: DeviceGetValuesResponse = await self.executeCommandSyncWithResponse(DeviceGetValues(id))
        self.updateCommeoDeviceValuesFromResponse(id, response)

    async def updateCommeoDeviceValuesAsync(self, id: int):
        await self.executeCommand(DeviceGetValues(id))

    def updateCommeoDeviceValuesFromResponse(self, id: int, response: DeviceGetValuesResponse):
        dev = self.getDevice(id, SelveTypes.DEVICE)
        if dev is None:
            # Values for a device we don't know (yet). Raising here would
            # abort response processing and strand the waiting future.
            self._LOGGER.debug("Values for unknown device id %s — ignored", id)
            return
        dev.name = response.name if response.name else "None"
        dev.state = response.movementState if response.movementState else MovementState.UNKOWN.value
        # None = "position unknown" sentinel (0x8000): keep last known value.
        if response.value is not None:
            if self.reversedStopPosition == 0:
                dev.value = response.value
            else:
                dev.value = 100 - response.value

        if response.targetValue is not None:
            if self.reversedStopPosition == 0:
                dev.targetValue = response.targetValue
            else:
                dev.targetValue = 100 - response.targetValue

        dev.unreachable = response.unreachable
        dev.overload = response.overload if response.overload else False
        dev.obstructed = response.obstructed if response.obstructed else False
        dev.alarm = response.alarm if response.alarm else False
        dev.lostSensor = response.lostSensor if response.lostSensor else False
        dev.automaticMode = response.automaticMode if response.automaticMode else False
        dev.gatewayNotLearned = response.gatewayNotLearned if response.gatewayNotLearned else False
        dev.windAlarm = response.windAlarm if response.windAlarm else False
        dev.rainAlarm = response.rainAlarm if response.rainAlarm else False
        dev.freezingAlarm = response.freezingAlarm if response.freezingAlarm else False
        dev.dayMode = response.dayMode if response.dayMode else False
        self.addOrUpdateDevice(dev, SelveTypes.DEVICE)
        if dev is not None and dev.state == MovementState.STOPPED_OFF:
            self._stop_movement_polling(id)

    def setDeviceValue(self, id: int, value: int | None, type: SelveTypes):
        dev = self.getDevice(id, type)
        # None means "position unknown" and must not be inverted.
        if value is None or self.reversedStopPosition == 0:
            dev.value = value
        else:
            dev.value = 100 - value

        self.addOrUpdateDevice(dev, type)

    def setDeviceTargetValue(self, id: int, value: int | None, type: SelveTypes):
        dev = self.getDevice(id, type)
        if value is None or self.reversedStopPosition == 0:
            dev.targetValue = value
        else:
            dev.targetValue = 100 - value
        self.addOrUpdateDevice(dev, type)

    def setDeviceState(self, id: int, state: MovementState, type: SelveTypes):
        dev = self.getDevice(id, type)
        dev.state = state
        self.addOrUpdateDevice(dev, type)

    def _track_commeo_command(self, device_id: int, command) -> None:
        """Remember the last Commeo drive command so it can be re-sent if the gateway reports it failed."""
        self._commeo_pending[device_id] = {
            "command": command,
            "attempts": 0,
            "sent_at": time.monotonic(),
        }

    def _schedule_commeo_retry(self, device_id: int, position: int) -> None:
        """Re-send a failed Commeo command after a backoff, if still allowed."""
        entry = self._commeo_pending.get(device_id)
        if entry is None:
            return
        if time.monotonic() - entry["sent_at"] > COMMEO_RETRY_WINDOW:
            self._commeo_pending.pop(device_id, None)
            return
        if entry["attempts"] >= COMMEO_RETRY_MAX:
            self._LOGGER.warning(
                "Commeo command for device %s failed, giving up after %d retries",
                device_id, COMMEO_RETRY_MAX,
            )
            self._commeo_pending.pop(device_id, None)
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # no running event loop (unit tests, etc.)
        entry["attempts"] += 1
        attempt = entry["attempts"]
        self._LOGGER.info(
            "Commeo command for device %s failed (gateway reported), retry %d/%d",
            device_id, attempt, COMMEO_RETRY_MAX,
        )
        delay = COMMEO_RETRY_BASE_DELAY * attempt + COMMEO_RETRY_STAGGER * position
        task = loop.create_task(
            self._commeo_retry(device_id, entry["command"], delay)
        )
        self._commeo_retry_tasks.add(task)
        task.add_done_callback(self._commeo_retry_tasks.discard)

    async def _commeo_retry(self, device_id: int, command, delay: float) -> None:
        await asyncio.sleep(delay)
        entry = self._commeo_pending.get(device_id)
        if entry is None or entry["command"] is not command:
            return  # superseded by a newer command or already succeeded
        try:
            await self.executeCommand(command)
        except Exception:
            self._LOGGER.exception("Retry of Commeo command for device %s failed", device_id)
            return
        self._start_movement_polling(device_id)

    def _start_movement_polling(self, device_id: int) -> None:
        """Start a background task that polls device values every 0.5 s during movement."""
        self._stop_movement_polling(device_id)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no running event loop (unit tests, etc.)
        task = asyncio.create_task(self._movement_poll_loop(device_id))
        self._movement_tasks[device_id] = task

    def _start_iveo_travel_timer(self, device_id: int) -> None:
        """Clear an IVEO movement state once the shutter has had time to travel.

        IVEO is one-way: the gateway acknowledges that it transmitted, never
        that the motor stopped, and there is no polling for it either. Without
        this timer the movement state set from that acknowledgement stays for
        good — covers were left showing "opening" until the next command.
        """
        self._stop_iveo_travel_timer(device_id)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return  # no running event loop (unit tests, etc.)
        self._iveo_travel_tasks[device_id] = asyncio.create_task(
            self._iveo_travel_loop(device_id)
        )

    def _stop_iveo_travel_timer(self, device_id: int) -> None:
        task = self._iveo_travel_tasks.pop(device_id, None)
        if task and not task.done():
            task.cancel()

    async def _iveo_travel_loop(self, device_id: int) -> None:
        try:
            await asyncio.sleep(self.iveoTravelTime)
            dev = self.getDevice(device_id, SelveTypes.IVEO)
            if dev is not None and dev.state in (MovementState.UP_ON, MovementState.DOWN_ON):
                dev.state = MovementState.STOPPED_OFF
                self.addOrUpdateDevice(dev, SelveTypes.IVEO)
        except asyncio.CancelledError:
            pass
        finally:
            self._iveo_travel_tasks.pop(device_id, None)

    def _stop_movement_polling(self, device_id: int) -> None:
        """Cancel movement polling task for a device if one is active."""
        task = self._movement_tasks.pop(device_id, None)
        if task and not task.done():
            task.cancel()

    async def _movement_poll_loop(self, device_id: int, interval: float = 0.5, timeout: float = 60.0) -> None:
        """Poll DeviceGetValues every *interval* seconds until movement stops or timeout."""
        elapsed = 0.0
        try:
            while not self._stopThread.is_set() and elapsed < timeout:
                await asyncio.sleep(interval)
                elapsed += interval
                if self.getDevice(device_id, SelveTypes.DEVICE) is None:
                    break
                await self.updateCommeoDeviceValuesAsync(device_id)
            if elapsed >= timeout:
                # No stop confirmation arrived: don't let the optimistic
                # UP_ON/DOWN_ON stand forever (it froze HA covers in
                # "opening" for hours) — be honest and mark it unknown.
                dev = self.getDevice(device_id, SelveTypes.DEVICE)
                if dev is not None and dev.state in (MovementState.UP_ON, MovementState.DOWN_ON):
                    self._LOGGER.warning(
                        "Device %s: no movement-stop confirmation within %.0fs — "
                        "marking movement state unknown", device_id, timeout,
                    )
                    dev.state = MovementState.UNKOWN
                    self.addOrUpdateDevice(dev, SelveTypes.DEVICE)
        except asyncio.CancelledError:
            pass
        finally:
            self._movement_tasks.pop(device_id, None)

    async def _await_duty_cycle(self, timeout: float = _DUTY_CYCLE_WAIT) -> bool:
        """Wait until the gateway reports the RF duty cycle is no longer blocked.

        The 868 MHz band has a ~1% airtime limit; once exhausted the gateway
        silently drops further telegrams. The gateway pushes DutyCycleResponse
        events as the budget recovers, which keep ``self.sendingBlocked``
        current. Returns True if sending is allowed, False if still blocked
        after *timeout* seconds.
        """
        if self.sendingBlocked != DutyMode.BLOCKED:
            return True
        self._LOGGER.warning(
            "Duty cycle blocked (utilization %s) — waiting up to %.0fs before sending",
            self.utilization, timeout,
        )
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            await asyncio.sleep(0.25)
            if self.sendingBlocked != DutyMode.BLOCKED:
                return True
        return False

    async def _send_iveo_command(self, actor_id: int, command: DriveCommandIveo) -> bool:
        """Send an IVEO manual drive command reliably.

        IVEO is one-way — the motor never acknowledges — so a single lost
        telegram is a silent failure. We repeat the telegram like a physical
        handsender and use the gateway's ``executed`` flag (the only feedback
        available) to detect when the gateway itself could not transmit, e.g.
        because the duty cycle is exhausted. Returns True if the gateway
        confirmed at least one transmission.
        """
        confirmed = False
        repeats = max(1, self.iveoRepeat)
        for attempt in range(repeats):
            if not await self._await_duty_cycle():
                self._LOGGER.warning(
                    "IVEO actor %s: duty cycle still blocked, skipping remaining sends",
                    actor_id,
                )
                break
            resp = await self._executeCommandSyncWithResponse(IveoManual(actor_id, command))
            if getattr(resp, "executed", False):
                confirmed = True
            if attempt < repeats - 1:
                await asyncio.sleep(self.iveoRepeatDelay)
        if not confirmed:
            self._LOGGER.warning(
                "IVEO actor %s command %s: gateway did not confirm transmission "
                "(one-way protocol — shutter may not have moved)",
                actor_id, getattr(command, "name", command),
            )
        return confirmed

    async def moveDeviceUp(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            cmd = CommandDriveUp(device.id, type)
            self._track_commeo_command(device.id, cmd)
            await self.executeCommand(cmd)
            device.state = MovementState.UP_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            self._start_movement_polling(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            confirmed = await self._send_iveo_command(device.id, DriveCommandIveo.UP)
            # Only claim the new position when the gateway confirmed at least
            # one transmission — otherwise HA shows a move that never happened.
            if confirmed:
                self.setDeviceValue(device.id, 0, SelveTypes.IVEO)
                self.setDeviceTargetValue(device.id, 0, SelveTypes.IVEO)
                # Shutter is travelling now; the timer ends the movement state
                # because IVEO never reports that it stopped.
                self._start_iveo_travel_timer(device.id)
            else:
                # Nothing went out, so nothing is moving.
                self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)

    async def moveDeviceDown(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            cmd = CommandDriveDown(device.id, type)
            self._track_commeo_command(device.id, cmd)
            await self.executeCommand(cmd)
            device.state = MovementState.DOWN_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            self._start_movement_polling(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            confirmed = await self._send_iveo_command(device.id, DriveCommandIveo.DOWN)
            if confirmed:
                self.setDeviceValue(device.id, 100, SelveTypes.IVEO)
                self.setDeviceTargetValue(device.id, 100, SelveTypes.IVEO)
                # Shutter is travelling now; the timer ends the movement state
                # because IVEO never reports that it stopped.
                self._start_iveo_travel_timer(device.id)
            else:
                # Nothing went out, so nothing is moving.
                self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)

    async def moveDevicePos1(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            cmd = CommandDrivePos1(device.id, type)
            self._track_commeo_command(device.id, cmd)
            await self.executeCommand(cmd)
            self._start_movement_polling(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            confirmed = await self._send_iveo_command(device.id, DriveCommandIveo.POS1)
            if confirmed:
                self.setDeviceValue(device.id, 66, SelveTypes.IVEO)
                self.setDeviceTargetValue(device.id, 66, SelveTypes.IVEO)
                # Shutter is travelling now; the timer ends the movement state
                # because IVEO never reports that it stopped.
                self._start_iveo_travel_timer(device.id)
            else:
                # Nothing went out, so nothing is moving.
                self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)

    async def moveDevicePos2(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            cmd = CommandDrivePos2(device.id, type)
            self._track_commeo_command(device.id, cmd)
            await self.executeCommand(cmd)
            self._start_movement_polling(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            confirmed = await self._send_iveo_command(device.id, DriveCommandIveo.POS2)
            if confirmed:
                self.setDeviceValue(device.id, 33, SelveTypes.IVEO)
                self.setDeviceTargetValue(device.id, 33, SelveTypes.IVEO)
                # Shutter is travelling now; the timer ends the movement state
                # because IVEO never reports that it stopped.
                self._start_iveo_travel_timer(device.id)
            else:
                # Nothing went out, so nothing is moving.
                self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)

    async def moveDevicePos(self, device: SelveDevice, pos: int = 0, type=DeviceCommandType.MANUAL):
        cmd = CommandDrivePos(device.id, type, param=Util.percentageToValue(pos))
        self._track_commeo_command(device.id, cmd)
        await self.executeCommand(cmd)
        self._start_movement_polling(device.id)

    async def moveDeviceStepUp(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        cmd = CommandDriveStepUp(device.id, type, param=Util.degreesToValue(degrees))
        self._track_commeo_command(device.id, cmd)
        await self.executeCommand(cmd)
        device.state = MovementState.UP_ON
        self.addOrUpdateDevice(device, SelveTypes.DEVICE)
        self._start_movement_polling(device.id)

    async def moveDeviceStepDown(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        cmd = CommandDriveStepDown(device.id, type, param=Util.degreesToValue(degrees))
        self._track_commeo_command(device.id, cmd)
        await self.executeCommand(cmd)
        device.state = MovementState.DOWN_ON
        self.addOrUpdateDevice(device, SelveTypes.DEVICE)
        self._start_movement_polling(device.id)

    async def stopDevice(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self._stop_movement_polling(device.id)
            cmd = CommandStop(device.id, type)
            self._track_commeo_command(device.id, cmd)
            await self.executeCommand(cmd)
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            confirmed = await self._send_iveo_command(device.id, DriveCommandIveo.STOP)
            self._stop_iveo_travel_timer(device.id)
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            if confirmed:
                # IVEO gives no position feedback: after a stop the position
                # is genuinely unknown rather than "half open".
                self.setDeviceValue(device.id, None, SelveTypes.IVEO)
                self.setDeviceTargetValue(device.id, None, SelveTypes.IVEO)


    ## Group
    async def groupRead(self, id: int):
        command = GroupRead(id)
        response: GroupReadResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def groupWrite(self, id: int, actorIds: dict, name: str):
        command = GroupWrite(id, actorIds, name)
        response: GroupWriteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def groupGetIds(self):
        command = GroupGetIds()
        response: GroupGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def groupDelete(self, id: int):
        command = GroupDelete(id)
        response: GroupDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def moveGroupUp(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        await self.executeCommandSyncWithResponse(CommandDriveUpGroup(group.id, type))
        ids = Util.b64bytes_to_bitobject(group.mask)
        for key, value in ids.items():
            if value:
                await self.updateCommeoDeviceValuesAsync(key)

    async def moveGroupDown(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        await self.executeCommandSyncWithResponse(CommandDriveDownGroup(group.id, type))
        ids = Util.b64bytes_to_bitobject(group.mask)
        for key, value in ids.items():
            if value:
                await self.updateCommeoDeviceValuesAsync(key)

    async def stopGroup(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        await self.executeCommandSyncWithResponse(CommandStopGroup(group.id, type))
        ids = Util.b64bytes_to_bitobject(group.mask)
        for key, value in ids.items():
            if value:
                await self.updateCommeoDeviceValuesAsync(key)


    ### Iveo
    async def iveoSetRepeater(self, repeaterInstalled: int):
        """
            Sets the repeater level. \n
            repeaterInstalled: int can be \n
            0 = no repeater installed\n
            1 = repeater installed for 1-time forwarding\n
            2 = multiple repeaters installed for 2-time forwarding
        """
        command = IveoSetRepeater(repeaterInstalled)
        response: IveoSetRepeaterResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoGetRepeater(self):
        """
            Gets the repeater level. \n
            response.repeaterState: int can be \n
            0 = no repeater installed\n
            1 = repeater installed for 1-time forwarding\n
            2 = multiple repeaters installed for 2-time forwarding
        """
        command = IveoGetRepeater()
        response: IveoGetRepeaterResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def iveoSetLabel(self, id: int, label: str):
        command = IveoSetLabel(id, label)
        response: IveoSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoSetType(self, id: int, activity: int, type: DeviceType):
        """
        Sets the device configuration. \n
        id: Iveo device id
        activity: 0 = channel deactivated, 1 = channel active
        type: DeviceType

        """
        command = IveoSetConfig(id, activity, type)
        response: IveoSetConfigResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoGetType(self, id: int):
        """
        Gets the device configuration.

        Params:
        id: Iveo device id

        Response:
        name: Name of device
        activity: 0 = channel deactivated, 1 = channel active
        type: DeviceType

        """
        command = IveoGetConfig(id)
        response: IveoGetConfigResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def iveoGetIds(self):
        command = IveoGetIds()
        response: IveoGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def iveoFactoryReset(self, id: int):
        command = IveoFactory(id)
        response: IveoFactoryResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoTeach(self, id: int):
        command = IveoTeach(id)
        response: IveoTeachResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoLearn(self, id: int):
        command = IveoLearn(id)
        response: IveoLearnResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoCommandManual(self, actorId: int, command: DriveCommandIveo):
        command = IveoManual(actorId, command)
        response: IveoManualResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoCommandAutomatic(self, actorId: int, command: DriveCommandIveo):
        command = IveoAutomatic(actorId, command)
        response: IveoAutomaticResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def iveoCommandResult(self):
        """Query the result of the last iveo command execution."""
        command = IveoResult()
        response: IveoResultResponse = await self.executeCommandSyncWithResponse(command)
        return response



    ### Sensor
    async def sensorTeachStart(self):
        command = SensorTechStart()
        response: SensorTeachStartResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def sensorTeachStop(self):
        command = SensorTeachStop()
        response: SensorTeachStopResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def sensorTeachResult(self):
        """ manually polls the teach result state, but the states are being reported automatically by the gateway itself"""
        command = SensorTeachResult()
        response: SensorTeachResultResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def sensorGetIds(self):
        command = SensorGetIds()
        response: SensorGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def sensorGetInfo(self, id: int):
        command = SensorGetInfo(id)
        response: SensorGetInfoResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def sensorGetValues(self, id: int):
        command = SensorGetValues(id)
        response: SensorGetValuesResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def sensorSetLabel(self, id: int, label: str):
        command = SensorSetLabel(id, label)
        response: SensorSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def sensorDelete(self, id: int):
        command = SensorDelete(id)
        response: SensorDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def sensorWriteManual(self, id: int, address: int, name: str):
        command = SensorWriteManual(id, address, name)
        response: SensorWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def updateSensorValuesAsync(self, id: int):
        await self.executeCommand(SensorGetValues(id))



    ### SenSim
    async def senSimGetIds(self):
        command = SenSimGetIds()
        response: SenSimGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senSimGetConfig(self, id: int):
        command = SenSimGetConfig(id)
        response: SenSimGetConfigResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senSimSetConfig(self, id: int, activity: bool):
        command = SenSimSetConfig(id, activity)
        response: SenSimSetConfigResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimGetValues(self, id: int):
        command = SenSimGetValues(id)
        response: SenSimGetValuesResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senSimSetValues(self, id: int, windDigital: int, rainDigital: int, tempDigital: int, lightDigital: int,
                              tempAnalog: int, windAnalog: int, sun1Analog: int, dayLightAnalog: int,
                              sun2Analog: int, sun3Analog: int):
        command = SenSimSetValues(id, windDigital, rainDigital, tempDigital, lightDigital,
                                  tempAnalog, windAnalog, sun1Analog, dayLightAnalog,
                                  sun2Analog, sun3Analog)
        response: SenSimSetValuesResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimSetLabel(self, id: int, label: str):
        command = SenSimSetLabel(id, label)
        response: SenSimSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimDrive(self, id: int, driveCommand: SenSimCommandType):
        command = SenSimDrive(id, driveCommand)
        response: SenSimDriveResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimStore(self, id: int, actorId: int):
        command = SenSimStore(id, actorId)
        response: SenSimStoreResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimDelete(self, id: int, actorId: int):
        command = SenSimDelete(id, actorId)
        response: SenSimDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimFactory(self, id: int):
        command = SenSimFactory(id)
        response: SenSimFactoryResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senSimGetTest(self, id: int):
        command = SenSimGetTest(id)
        response: SenSimGetTestResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senSimSetTest(self, id: int, testMode: int):
        command = SenSimSetTest(id, testMode)
        response: SenSimSetTestResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def updateSenSimValuesAsync(self, id: int):
        await self.executeCommand(SenSimGetValues(id))


    ### Firmware
    async def firmwareGetVersion(self):
        command = FirmwareGetVersion()
        response: FirmwareGetVersionResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def firmwareUpdate(self):
        command = FirmwareUpdate()
        response: FirmwareUpdateResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    ### Sender
    async def senderTeachStart(self):
        command = SenderTeachStart()
        response: SenderTeachStartResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senderTeachStop(self):
        command = SenderTeachStop()
        response: SenderTeachStopResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senderTeachResult(self):
        """ manually polls the teach result state, but the states are being reported automatically by the gateway itself"""
        command = SenderTeachResult()
        response: SenderTeachResultResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senderGetIds(self):
        command = SenderGetIds()
        response: SenderGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senderGetInfo(self, id: int):
        command = SenderGetInfo(id)
        response: SenderGetInfoResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senderGetValues(self, id: int):
        command = SenderGetValues(id)
        response: SenderGetValuesResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def senderSetLabel(self, id: int, label: str):
        command = SenderSetLabel(id, label)
        response: SenderSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senderDelete(self, id: int):
        command = SenderDelete(id)
        response: SenderDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)

    async def senderWriteManual(self, id: int, address: int, channel: int, resetCount: int, name: str):
        command = SenderWriteManual(id, address, channel, resetCount, name)
        response: SenderWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return self._executed(response)




    async def updateSenderValuesAsync(self, id: int):
        await self.executeCommand(SenderGetValues(id))