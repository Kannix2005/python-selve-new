from __future__ import annotations

import asyncio
import queue
import threading
import time
from itertools import chain
from typing import Callable
from contextlib import asynccontextmanager

import serial
import serial_asyncio
from serial.tools import list_ports
from serial import SerialException
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
from selve.device import SelveDevice
from selve.group import SelveGroup
from selve.iveo import IveoDevice
from selve.senSim import SelveSenSim
from selve.sender import SelveSender
from selve.sensor import SelveSensor
from selve.util import *
from selve.util import Command
from selve.util.errors import *
from selve.util.protocol import ParameterType


class Selve:
    """Implementation of the serial communication to the Selve Gateway"""

    def __init__(self, port=None, discover=True, develop=False, logger=None, loop=None):
        # Gateway state
        self._callbacks = set()
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

        # Worker control
        self._worker_running = False
        self._worker_task = None
        self._stop_event = asyncio.Event()
        
        # Connection state
        self._port = port
        self._reader = None
        self._writer = None
        self._connection_lock = asyncio.Lock()
        
        # Communication queues
        self.txQ = None
        self.rxQ = None
        
        # Response tracking for synchronous commands
        self._pending_responses = {}
        self._response_timeout = 10.0
        
        # Serial connection parameters
        self._serial_params = {
            'baudrate': 115200,
            'bytesize': serial.EIGHTBITS,
            'parity': serial.PARITY_NONE,
            'stopbits': serial.STOPBITS_ONE,
            'timeout': 1.0
        }

        #Options
        self.reversedStopPosition = 0

        #Logger
        self._LOGGER = logger


    @asynccontextmanager
    async def _serial_connection(self, port):
        """Context manager for serial connection"""
        reader = None
        writer = None
        try:
            reader, writer = await serial_asyncio.open_serial_connection(
                url=port, **self._serial_params
            )
            yield reader, writer
        except Exception as e:
            self._LOGGER.error(f"Failed to open serial connection: {e}")
            raise
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()

    async def _worker(self):
        """Improved worker with proper async I/O and error handling"""
        self._LOGGER.debug("Worker started")
        
        while not self._stop_event.is_set():
            try:
                async with self._connection_lock:
                    if not self._reader or not self._writer:
                        await self._reconnect()
                
                # Process outgoing commands
                await self._process_tx_queue()
                
                # Process incoming data
                await self._process_rx_data()
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                self._LOGGER.debug("Worker cancelled")
                break
            except Exception as e:
                self._LOGGER.error(f"Worker error: {e}")
                await self._handle_worker_error(e)
                
        self._LOGGER.debug("Worker stopped")

    async def _process_tx_queue(self):
        """Process outgoing commands from queue"""
        try:
            if not self.txQ.empty():
                command = await asyncio.wait_for(self.txQ.get(), timeout=0.1)
                await self._send_command_async(command)
                self.txQ.task_done()
        except asyncio.TimeoutError:
            pass  # No command in queue
        except Exception as e:
            self._LOGGER.error(f"TX queue processing error: {e}")

    async def _process_rx_data(self):
        """Process incoming data with proper buffering for multi-line XML responses"""
        try:
            if self._reader and not self._reader.at_eof():
                # Read available data with timeout
                try:
                    data = await asyncio.wait_for(
                        self._reader.read(1024), timeout=0.1
                    )
                    
                    if data:
                        text = data.decode('utf-8', errors='ignore')
                        
                        # Initialize message buffer if not exists
                        if not hasattr(self, '_message_buffer'):
                            self._message_buffer = ""
                        
                        self._message_buffer += text
                        
                        # Process complete XML messages from buffer
                        while True:
                            xml_response, self._message_buffer = self._extract_xml_response(self._message_buffer)
                            if xml_response:
                                # Process the complete message
                                await self._handle_incoming_message(xml_response)
                            else:
                                # No complete message yet
                                break
                        
                except asyncio.TimeoutError:
                    pass  # No data available
        except Exception as e:
            self._LOGGER.error(f"RX processing error: {e}")

    async def _handle_incoming_message(self, message):
        """Handle incoming message with proper response routing"""
        try:
            self._LOGGER.debug(f"Received: {message}")
            
            # Try to process as response
            response = await self.processResponse(message)
            
            # Route response to waiting command if applicable
            # For synchronous commands, we need to match with pending responses
            if response and response is not True:
                # Check if there are any pending responses waiting
                if self._pending_responses:
                    # For now, route to the first pending response
                    # This is a simplified approach - in a real system you'd want to match by command type
                    for command_id, future in list(self._pending_responses.items()):
                        if not future.cancelled():
                            future.set_result(response)
                            self._pending_responses.pop(command_id)
                            break
                        
        except Exception as e:
            self._LOGGER.error(f"Message handling error: {e}")

    async def _send_command_async(self, command: Command):
        """Send command with improved error handling"""
        if not self._writer:
            raise ConnectionError("No active serial connection")
            
        try:
            command_data = command.serializeToXML()
            self._LOGGER.debug(f'Sending: {command_data}')
            
            self._writer.write(command_data)
            await self._writer.drain()
            
            # Optional delay for device processing
            await asyncio.sleep(0.1)
            
        except Exception as e:
            self._LOGGER.error(f"Command send error: {e}")
            raise

    async def _reconnect(self):
        """Reconnect to serial device"""
        self._LOGGER.info("Attempting to reconnect...")
        
        # Close existing connections
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        
        self._reader = None
        self._writer = None
        
        # Try to reconnect
        if self._port:
            try:
                self._reader, self._writer = await serial_asyncio.open_serial_connection(
                    url=self._port, **self._serial_params
                )
                self._LOGGER.info(f"Reconnected to {self._port}")
                return True
            except Exception as e:
                self._LOGGER.error(f"Reconnection failed: {e}")
        
        # Try to find device on other ports
        return await self._find_and_connect()

    async def _find_and_connect(self):
        """Find and connect to device on available ports"""
        available_ports = await asyncio.get_event_loop().run_in_executor(
            None, list_ports.comports
        )
        
        for port_info in available_ports:
            try:
                reader, writer = await serial_asyncio.open_serial_connection(
                    url=port_info.device, **self._serial_params
                )
                
                # Test connection with ping
                if await self._test_connection(reader, writer):
                    self._reader = reader
                    self._writer = writer
                    self._port = port_info.device
                    self._LOGGER.info(f"Connected to {port_info.device}")
                    return True
                else:
                    writer.close()
                    await writer.wait_closed()
                    
            except Exception as e:
                self._LOGGER.debug(f"Failed to connect to {port_info.device}: {e}")
                
        self._LOGGER.error("No suitable device found")
        return False

    async def _test_connection(self, reader, writer):
        """Test if connection is to correct device"""
        try:
            # Send ping command
            ping_cmd = ServicePing()
            command_data = ping_cmd.serializeToXML()
            
            writer.write(command_data)
            await writer.drain()
            
            # Wait for complete response using read instead of readuntil
            full_response = ""
            start_time = time.time()
            
            while time.time() - start_time < 3.0:
                try:
                    data = await asyncio.wait_for(
                        reader.read(1024), timeout=1.0
                    )
                    
                    if data:
                        text = data.decode('utf-8', errors='ignore')
                        full_response += text
                        
                        # Check if we have a complete response
                        if '</methodResponse>' in full_response:
                            break
                            
                except asyncio.TimeoutError:
                    # Check if we already have a complete response
                    if '</methodResponse>' in full_response:
                        break
                    continue
            
            # Check if response indicates correct device
            return 'selve.GW.service.ping' in full_response
            
        except Exception as e:
            self._LOGGER.debug(f"Connection test failed: {e}")
            return False

    async def _handle_worker_error(self, error):
        """Handle worker errors with backoff strategy"""
        self._LOGGER.error(f"Worker error: {error}")
        
        # Close connections on error
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        
        self._reader = None
        self._writer = None
        
        # Wait before retry with exponential backoff
        await asyncio.sleep(min(5.0, 0.5 * (2 ** getattr(self, '_error_count', 0))))
        
        # Track error count for backoff
        self._error_count = getattr(self, '_error_count', 0) + 1
        if self._error_count > 10:
            self._error_count = 0  # Reset after too many errors
    # serial port exceptions, all of these notify that we are in some
    # serious trouble
    

    def list_ports(self):
        available_ports = list_ports.comports()
        return available_ports

    async def check_port(self, port):
        if port is not None:
            try:
                self._serial = serial.Serial(
                    port=port,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False)

                if await self.pingGateway(fromConfigFlow=True):
                    self._serial.close()
                    return True
            except (serial.SerialException, IOError) as e:
                self._LOGGER.debug("Configured port not valid! " + str(e))
                return False
            except Exception as e:
                self._LOGGER.error("Unknown exception: " + str(e))
                return False
        return False


    async def setup(self, discover=False, fromConfigFlow=False):
        """Setup with improved connection handling and error recovery"""
        self._LOGGER.info("Setup")

        # Initialize queues
        self.rxQ = asyncio.Queue()
        self.txQ = asyncio.Queue()

        # Try specified port first
        if self._port is not None:
            if await self._try_connect_port(self._port, fromConfigFlow, discover):
                return True

        # Scan for available ports
        if await self._scan_and_connect(fromConfigFlow, discover):
            return True
            
        self._LOGGER.error("No gateway found on any port!")
        raise PortError

    async def _try_connect_port(self, port, fromConfigFlow=False, discover=False):
        """Try to connect to specific port"""
        try:
            # Create persistent connection directly and test it
            self._reader, self._writer = await serial_asyncio.open_serial_connection(
                url=port, **self._serial_params
            )
            
            # Test connection with the persistent connection
            if await self._test_connection(self._reader, self._writer):
                # Connection test passed
                self._port = port
                
                if not fromConfigFlow:
                    if discover:
                        self._LOGGER.info("Discovering devices")
                        await self.discover()
                    await self.startWorker()
                return True
            else:
                # Test failed, close connection
                if self._writer:
                    self._writer.close()
                    await self._writer.wait_closed()
                self._reader = None
                self._writer = None
                return False
                    
        except Exception as e:
            self._LOGGER.debug(f"Port {port} not valid: {e}")
            # Clean up any partial connection
            if hasattr(self, '_writer') and self._writer:
                try:
                    self._writer.close()
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._reader = None
            self._writer = None
            
        return False

    async def _scan_and_connect(self, fromConfigFlow=False, discover=False):
        """Scan all available ports for gateway"""
        if self.loop is not None:
            available_ports = await self.loop.run_in_executor(None, list_ports.comports)
        else:
            available_ports = list_ports.comports()
        
        self._LOGGER.debug(f"Available comports: {available_ports}")

        if len(available_ports) == 0:
            self._LOGGER.error("No available comports!")
            return False

        for port_info in available_ports:
            if await self._try_connect_port(port_info.device, fromConfigFlow, discover):
                return True
                
        return False

    async def recover(self):
        self._LOGGER.info("(Selve Worker): " + "Recover serial connection")
        self._LOGGER.debug("(Selve Worker): " + "Waiting 5 seconds before trying...")
        await asyncio.sleep(5)
        self._LOGGER.debug("(Selve Worker): " + "Recovering")

        if self._port is not None:
            try:
                self._serial = serial.Serial(
                    port=self._port,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False)

                if await self.pingGatewayFromWorker():
                    return
            except (serial.SerialException, IOError) as e:
                self._LOGGER.debug("(Selve Worker): " + "Configured port not valid, maybe it has changed, trying other ports...")
            except Exception as e:
                self._LOGGER.error("(Selve Worker): " + "Unknown exception: " + str(e))

        if self.loop is not None:
            available_ports = await self.loop.run_in_executor(None, list_ports.comports)
        else:
            available_ports = list_ports.comports()
        
        self._LOGGER.debug("(Selve Worker): " + "available comports: " + str(available_ports))

        if len(available_ports) == 0:
            self._LOGGER.error("(Selve Worker): " + "No available comports!")
            return False

        for p in available_ports:
            try:
                self._serial = serial.Serial(
                    port=p.device,
                    baudrate=115200,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False)
            except Exception as e:
                self._LOGGER.error("(Selve Worker): " + "Error at com port: " + str(e))
                try:
                    self._serial.close()
                except Exception:
                    self._LOGGER.debug("(Selve Worker): " + "Cannot close com port")
            if await self.pingGatewayFromWorker():
                self._port = p.device
                return
            else:
                self._serial.close()
                self._serial = None
        else:
            self._LOGGER.error("(Selve Worker): " + "No gateway on comports found!")
            raise PortError


    async def startWorker(self):
        """Start the worker with improved state management"""
        if self._worker_running:
            self._LOGGER.debug("Worker already running")
            return
            
        self._LOGGER.debug("Starting worker")
        
        # Initialize queues
        if not self.txQ:
            self.txQ = asyncio.Queue()
        if not self.rxQ:
            self.rxQ = asyncio.Queue()
            
        # Reset stop event
        self._stop_event.clear()
        
        # Start worker task
        self._worker_task = asyncio.create_task(self._worker())
        self._worker_running = True
        
        # Reset error counter on successful start
        self._error_count = 0

    async def stopWorker(self):
        """Stop the worker gracefully"""
        if not self._worker_running:
            self._LOGGER.debug("Worker not running")
            return
            
        self._LOGGER.debug("Stopping worker")
        
        # Signal worker to stop
        self._stop_event.set()
        self._worker_running = False
        
        # Cancel and wait for worker task
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await asyncio.wait_for(self._worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._LOGGER.warning("Worker did not stop gracefully")
            except asyncio.CancelledError:
                pass
        
        # Close connections
        async with self._connection_lock:
            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._reader = None
            self._writer = None
        
        # Cancel pending responses
        for future in self._pending_responses.values():
            if not future.cancelled():
                future.cancel()
        self._pending_responses.clear()
        
        self._worker_task = None

    async def stopGateway(self):
        """Stop gateway and cleanup resources"""
        self._LOGGER.debug("Preparing for termination")
        await self.stopWorker()
        
        # Additional cleanup to ensure port is properly released
        async with self._connection_lock:
            if self._writer:
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._reader = None
            self._writer = None
            
        # Small delay to ensure port is fully released
        await asyncio.sleep(0.1)
        return True


    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    def register_event_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when other events take place."""
        self._eventCallbacks.add(callback)

    def remove_event_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._eventCallbacks.discard(callback)


    def updateOptions(self, reversedStopPosition = 0):
        self.reversedStopPosition = reversedStopPosition


    async def _sendCommandToGateway(self, command: Command):
        commandstr = command.serializeToXML()
        self._LOGGER.debug('Gateway writing: ' + str(commandstr))
        try:
            if not self._serial.is_open:
                self._serial.open()
            self._serial.write(commandstr)
            self._serial.flush()
            #always sleep after writing
            await asyncio.sleep(0.5)

        except (serial.SerialException, IOError) as se:
            self._LOGGER.info('Serial error, trying to reconnect once... ' + str(se))
            await self.recover()

            try:
                self._LOGGER.debug('Trying again...')
                if not self._serial.is_open:
                    self._serial.open()
                self._serial.write(commandstr)
                self._serial.flush()
                #always sleep after writing
                await asyncio.sleep(0.5)
            
            except Exception as e:
                self._LOGGER.error("error communicating: " + str(e) + " ; Please restart the integration!")

        except Exception as e:
            self._LOGGER.error("error communicating: " + str(e) + " ; Please restart the integration!")

    async def processResponse(self, xmlstr):
        """Processes an XML String into a response object. Returns False if something went wrong or the gateway returned an error."""
        # check which command was received
        # do something with the data
        # return the ready to eat response

        # The selve device sometimes answers a badformed header. This is a patch
        xmlstr = str(xmlstr).replace('<?xml version="1.0"? encoding="UTF-8">', '<?xml version="1.0" encoding="UTF-8"?>')
        try:
            res = untangle.parse(xmlstr)
        except Exception as e:
            self._LOGGER.error("Error in XML: " + str(e) + " : " + xmlstr)
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
                self.commandResult(response)
            if isinstance(response, DeviceGetValuesResponse):
                self.updateCommeoDeviceValuesFromResponse(int(response.parameters[1][1]), response)
            if isinstance(response, SenderTeachResultResponse) \
                or isinstance(response, SensorTeachResultResponse)\
                or isinstance(response, DeviceScanResultResponse):
                self.processTeachResponse(response)
                return True

            for callback in self._callbacks:
                callback()
            return response


        except Exception as e:
            self._LOGGER.error("Error in response processing: " + str(e) + " : " + xmlstr)
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
        if methodName == "selve.GW." + str(CommeoParamCommand.GETDUTY.value):
            return ParamGetDutyResponse(methodName, flat_params_list)
        if methodName == "selve.GW." + str(CommeoParamCommand.GETRF.value):
            return ParamGetRfResponse(methodName, flat_params_list)

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
        """Execute command asynchronously via worker"""
        await self.startWorker()
        await self.txQ.put(command)

    async def executeCommandSyncWithResponse(self, command: Command, fromConfigFlow=False, timeout=None):
        """Execute command and wait for response with improved timeout handling"""
        if timeout is None:
            timeout = self._response_timeout
            
        # Generate unique command ID for response tracking
        command_id = id(command)
        
        # Create future for response
        response_future = asyncio.Future()
        self._pending_responses[command_id] = response_future
        
        try:
            # For config flow, stop worker to ensure synchronous execution
            if fromConfigFlow:
                await self.stopWorker()
                response = await self._execute_command_direct(command, timeout)
                if not fromConfigFlow:
                    await self.startWorker()
                return response
            else:
                # Execute via worker
                await self.startWorker()
                await self.txQ.put(command)
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(response_future, timeout=timeout)
                    return response
                except asyncio.TimeoutError:
                    self._LOGGER.warning(f"Command timeout after {timeout}s")
                    return False
                    
        finally:
            # Cleanup pending response
            self._pending_responses.pop(command_id, None)

    def _extract_xml_response(self, message_buffer):
        """Extract complete XML response from buffer and return (response, remaining_buffer)"""
        if not ('</methodResponse>' in message_buffer or '</methodCall>' in message_buffer):
            return None, message_buffer
            
        if '<?xml' not in message_buffer:
            return None, message_buffer
            
        start_idx = message_buffer.find('<?xml')
        end_idx = -1
        
        if '</methodResponse>' in message_buffer:
            end_idx = message_buffer.find('</methodResponse>', start_idx) + len('</methodResponse>')
        elif '</methodCall>' in message_buffer:
            end_idx = message_buffer.find('</methodCall>', start_idx) + len('</methodCall>')
        
        if start_idx != -1 and end_idx != -1:
            complete_message = message_buffer[start_idx:end_idx]
            remaining_buffer = message_buffer[end_idx:]
            return complete_message, remaining_buffer
            
        return None, message_buffer

    async def _execute_command_direct(self, command: Command, timeout=10.0):
        """Execute command directly without worker for critical operations"""
        async with self._connection_lock:
            if not self._reader or not self._writer:
                await self._reconnect()
                
            if not self._writer:
                return False
                
            try:
                # Send command
                await self._send_command_async(command)
                
                # Wait for complete response
                start_time = time.time()
                message_buffer = ""
                
                while time.time() - start_time < timeout:
                    try:
                        # Read available data with timeout
                        data = await asyncio.wait_for(
                            self._reader.read(1024), timeout=1.0
                        )
                        
                        if data:
                            text = data.decode('utf-8', errors='ignore')
                            message_buffer += text
                            
                            # Try to extract complete XML response
                            xml_response, message_buffer = self._extract_xml_response(message_buffer)
                            if xml_response:
                                self._LOGGER.debug(f"Processing direct command response: {xml_response[:100]}...")
                                response = await self.processResponse(xml_response)
                                self._LOGGER.debug(f"Response type: {type(response)} - Value: {response}")
                                if response and response is not True:
                                    return response
                                
                    except asyncio.TimeoutError:
                        # Check if we have a complete message in buffer anyway
                        xml_response, message_buffer = self._extract_xml_response(message_buffer)
                        if xml_response:
                            response = await self.processResponse(xml_response)
                            if response and response is not True:
                                return response
                        continue
                
                self._LOGGER.warning("Direct command execution timeout")
                return False
                
            except Exception as e:
                self._LOGGER.error(f"Direct command execution error: {e}")
                return False




    async def discover(self):

        await self.stopWorker()
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

                if self.reversedStopPosition == 0:
                    device.value = config.value if config.value else 0
                else:
                    device.value = 100 - config.value if config.value else 0


                if self.reversedStopPosition == 0:
                    device.targetValue = config.targetValue if config.targetValue else 0
                else:
                    device.targetValue = 100 - config.targetValue if config.targetValue else 0

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
                device.name = config.name
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
        for device in self.devices[SelveTypes.DEVICE.value].values():
            await self.updateCommeoDeviceValues(device.id)
        for sensor in self.devices[SelveTypes.SENSOR.value].values():
            await self.updateSensorValuesAsync(sensor.id)
        for senSim in self.devices[SelveTypes.SENSIM.value].values():
            await self.updateSenSimValuesAsync(senSim.id)
        for sender in self.devices[SelveTypes.SENDER.value].values():
            await self.updateSenderValuesAsync(sender.id)



    def addOrUpdateDevice(self, device, type: SelveTypes):
        self.devices[type.value][device.id] = device
        # add in gateway

        # if there is a callback for updates, call it
        for callback in self._callbacks:
            callback()

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

            if self.reversedStopPosition == 0:
                device.value = response.value if response.value else 0
            else:
                device.value = 100 - response.value if response.value else 0


            if self.reversedStopPosition == 0:
                device.targetValue = response.targetValue if response.targetValue else 0
            else:
                device.targetValue = 100 - response.targetValue if response.targetValue else 0

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
            self.addOrUpdateDevice(sender, SelveTypes.SENSOR)

        if isinstance(response, LogEventResponse):
            self.lastLogEvent = response
            if response.logType == LogType.INFO:
                self._LOGGER.info(
                    f'Gateway Log Info: {response.logCode} - {response.logStamp} - {response.logValue} - {response.logDescription}')
            if response.logType == LogType.WARNING:
                self._LOGGER.warning(
                    f'Gateway Log Info: {response.logCode} - {response.logStamp} - {response.logValue} - {response.logDescription}')
            if response.logType == LogType.ERROR:
                self._LOGGER.error(
                    f'Gateway Log Info: {response.logCode} - {response.logStamp} - {response.logValue} - {response.logDescription}')

        if isinstance(response, DutyCycleResponse):
            self.sendingBlocked = response.mode
            self.utilization = response.traffic
            

        for callback in self._eventCallbacks:
            callback(response)


    def commandResult(self, response: IveoResultResponse | CommandResultResponse):

        # if isinstance(response, IveoResultResponse):
        #     for id in response.executedIds:
        #         dev = self.getDevice(id, SelveTypes.IVEO)

        #         if response.command is DriveCommandIveo.DOWN:
        #             dev.state = MovementState.DOWN_ON
        #         if response.command is DriveCommandIveo.UP:
        #             dev.state = MovementState.UP_ON
        #         if response.command is DriveCommandIveo.STOP:
        #             dev.state = MovementState.STOPPED_OFF

        #         self.addOrUpdateDevice(dev, SelveTypes.IVEO)

        for callback in self._callbacks:
            callback()


    ### Service

    async def pingGateway(self, fromConfigFlow=False):
        cmd = ServicePing()
        methodResponse = await self.executeCommandSyncWithResponse(cmd, fromConfigFlow=fromConfigFlow)
        try:
            if hasattr(methodResponse, "name"):
                if methodResponse.name == "selve.GW.service.ping":
                    self._LOGGER.debug("Ping back")
                    return True
        except Exception:
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
        except Exception:
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
        if response.executed is not True:
            self._LOGGER.info("Error: Gateway could not be reset or loads too long")

        # time.sleep(2)

        start_time = time.time()
        while await self.gatewayState() != ServiceState.READY:
            if time.time() - start_time >= 30:
                self._LOGGER.info("Error: Gateway could not be reset or loads too long")
                break
            await asyncio.sleep(0.5)  # Wait before next check
        self._LOGGER.info("Gateway reset")

    async def factoryResetGateway(self):
        command = ServiceFactoryReset()
        response: ServiceFactoryResetResponse = await self.executeCommandSyncWithResponse(command)
        if response.executed is not True:
            self._LOGGER.info("Error: Gateway could not be reset or loads too long")

        start_time = time.time()
        while await self.gatewayState() != ServiceState.READY:
            if time.time() - start_time >= 60:
                self._LOGGER.info("Error: Gateway could not be reset or loads too long")
                break
            await asyncio.sleep(0.5)  # Wait before next check
        self._LOGGER.info("Gateway factory reset")
        return response.executed

    async def setLED(self, state: bool):
        command = ServiceSetLed(state)
        response: ServiceSetLedResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def getLED(self):
        command = ServiceGetLed()
        response: ServiceGetLedResponse = await self.executeCommandSyncWithResponse(command)
        return response

    ### Param
    async def setForward(self, state: bool):
        command = ParamSetForward(state)
        response: ParamSetForwardResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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



    ##Device functions
    async def scanStart(self):
        command = DeviceScanStart()
        response: DeviceScanStartResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def scanStop(self):
        command = DeviceScanStop()
        response: DeviceScanStopResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def scanResult(self):
        """ manually polls the scan state, but the states are being reported automatically by the gateway itself"""
        command = DeviceScanResult()
        response: DeviceScanResultResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def deviceSave(self, id: int):
        command = DeviceSave(id)
        response: DeviceSaveResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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
        return response.executed

    async def deviceSetLabel(self, id: int, label: str):
        command = DeviceSetLabel(id, label)
        response: DeviceSetLabelResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def deviceSetType(self, id: int, type: DeviceType):
        command = DeviceSetType(id, type)
        response: DeviceSetTypeResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def deviceDelete(self, id: int):
        command = DeviceDelete(id)
        response: DeviceDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def deviceWriteManual(self, id: int, address: int, name: str, config: DeviceType):
        command = DeviceWriteManual(id, address, name, config)
        response: DeviceWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def updateCommeoDeviceValues(self, id: int):
        response: DeviceGetValuesResponse = await self.executeCommandSyncWithResponse(DeviceGetValues(id))
        self.updateCommeoDeviceValuesFromResponse(id, response)

    async def updateCommeoDeviceValuesAsync(self, id: int):
        await self.executeCommand(DeviceGetValues(id))

    def updateCommeoDeviceValuesFromResponse(self, id: int, response: DeviceGetValuesResponse):
        dev = self.getDevice(id, SelveTypes.DEVICE)
        dev.name = response.name if response.name else "None"
        dev.state = response.movementState if response.movementState else MovementState.UNKOWN.value
        if self.reversedStopPosition == 0:
            dev.value = response.value if response.value else 0
        else:
            dev.value = 100 - response.value if response.value else 0


        if self.reversedStopPosition == 0:
            dev.targetValue = response.targetValue if response.targetValue else 0
        else:
            dev.targetValue = 100 - response.targetValue if response.targetValue else 0

        dev.unreachable = response.unreachable if response.unreachable else True
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

    def setDeviceValue(self, id: int, value: int, type: SelveTypes):
        dev = self.getDevice(id, type)
        if self.reversedStopPosition == 0:
            dev.value = value
        else:
            dev.value = 100 - value

        self.addOrUpdateDevice(dev, type)

    def setDeviceTargetValue(self, id: int, value: int, type: SelveTypes):
        dev = self.getDevice(id, type)
        if self.reversedStopPosition == 0:
            dev.targetValue = value
        else:
            dev.targetValue = 100 - value
        self.addOrUpdateDevice(dev, type)

    def setDeviceState(self, id: int, state: MovementState, type: SelveTypes):
        dev = self.getDevice(id, type)
        dev.state = state
        self.addOrUpdateDevice(dev, type)

    async def moveDeviceUp(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            await self.executeCommand(CommandDriveUp(device.id, type))
            device.state = MovementState.UP_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            await self.executeCommand(IveoManual(device.id, DriveCommandIveo.UP))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 0, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 0, SelveTypes.IVEO)

    async def moveDeviceDown(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            await self.executeCommand(CommandDriveDown(device.id, type))
            device.state = MovementState.DOWN_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            await self.executeCommand(IveoManual(device.id, DriveCommandIveo.DOWN))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 100, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 100, SelveTypes.IVEO)

    async def moveDevicePos1(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            await self.executeCommand(CommandDrivePos1(device.id, type))
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            await self.executeCommand(IveoManual(device.id, DriveCommandIveo.POS1))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 66, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 66, SelveTypes.IVEO)

    async def moveDevicePos2(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            await self.executeCommand(CommandDrivePos2(device.id, type))
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            await self.executeCommand(IveoManual(device.id, DriveCommandIveo.POS2))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 33, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 33, SelveTypes.IVEO)

    async def moveDevicePos(self, device: SelveDevice, pos: int = 0, type=DeviceCommandType.MANUAL):
        await self.executeCommand(CommandDrivePos(device.id, type, param=Util.percentageToValue(pos)))
        await self.updateCommeoDeviceValuesAsync(device.id)

    async def moveDeviceStepUp(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        await self.executeCommand(CommandDriveStepUp(device.id, type, param=Util.degreesToValue(degrees)))
        await self.updateCommeoDeviceValuesAsync(device.id)

    async def moveDeviceStepDown(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        await self.executeCommand(CommandDriveStepDown(device.id, type, param=Util.degreesToValue(degrees)))
        await self.updateCommeoDeviceValuesAsync(device.id)

    async def stopDevice(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            await self.executeCommand(CommandStop(device.id, type))
            await self.updateCommeoDeviceValuesAsync(device.id)
        else:
            await self.executeCommand(IveoManual(device.id, DriveCommandIveo.STOP))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 50, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 50, SelveTypes.IVEO)


    ## Group
    async def groupRead(self, id: int):
        command = GroupRead(id)
        response: GroupReadResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def groupWrite(self, id: int, actorIds: dict, name: str):
        command = GroupWrite(id, actorIds, name)
        response: GroupWriteResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def groupGetIds(self):
        command = GroupGetIds()
        response: GroupGetIdsResponse = await self.executeCommandSyncWithResponse(command)
        return response

    async def groupDelete(self, id: int):
        command = GroupDelete(id)
        response: GroupDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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
        return response.executed

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
        return response.executed

    async def iveoSetType(self, id: int, activity: int, type: DeviceType):
        """
        Sets the device configuration. \n
        id: Iveo device id
        activity: 0 = channel deactivated, 1 = channel active
        type: DeviceType

        """
        command = IveoSetConfig(id, activity, type)
        response: IveoSetConfigResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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

    async def iveoFactoryReset(self):
        command = IveoFactory()
        response: IveoFactoryResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def iveoTeach(self):
        command = IveoTeach()
        response: IveoTeachResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def iveoLearn(self, id: int):
        command = IveoLearn(id)
        response: IveoLearnResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def iveoCommandManual(self, actorId: int, command: DriveCommandIveo):
        command = IveoManual(actorId, command)
        response: IveoManualResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def iveoCommandAutomatic(self, actorId: int, command: DriveCommandIveo):
        command = IveoAutomatic(actorId, command)
        response: IveoAutomaticResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed



    ### Sensor
    async def sensorTeachStart(self):
        command = SensorTechStart()
        response: SensorTeachStartResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def sensorTeachStop(self):
        command = SensorTeachStop()
        response: SensorTeachStopResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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
        return response.executed

    async def sensorDelete(self, id: int):
        command = SensorDelete(id)
        response: SensorDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def sensorWriteManual(self, id: int, address: int, name: str):
        command = SensorWriteManual(id, address, name)
        response: SensorWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def updateSensorValuesAsync(self, id: int):
        await self.executeCommand(SensorGetValues(id))



    ### SenSim - ToDo
    async def updateSenSimValuesAsync(self, id: int):
        await self.executeCommand(SenSimGetValues(id))

    ### Sender
    async def senderTeachStart(self):
        command = SenderTeachStart()
        response: SenderTeachStartResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def senderTeachStop(self):
        command = SenderTeachStop()
        response: SenderTeachStopResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

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
        return response.executed

    async def senderDelete(self, id: int):
        command = SenderDelete(id)
        response: SenderDeleteResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed

    async def senderWriteManual(self, id: int, address: int, channel: int, resetCount: int, name: str):
        command = SenderWriteManual(id, address, channel, resetCount, name)
        response: SenderWriteManualResponse = await self.executeCommandSyncWithResponse(command)
        return response.executed




    async def updateSenderValuesAsync(self, id: int):
        await self.executeCommand(SenderGetValues(id))
