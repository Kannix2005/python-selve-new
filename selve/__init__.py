from __future__ import annotations

import asyncio
import queue
import threading
import time
from itertools import chain
from typing import Callable

import serial
from serial.tools import list_ports
import untangle

from selve.commands import param, service
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


def _worker(selve: Selve):
    # Infinite loop to collect all incoming data
    selve._LOGGER.debug("Reader started")
    try:
        while True:
            if not selve._pauseReader:
                with selve._readLock:
                    if selve._serial.in_waiting > 0:
                        msg = ""
                        while True:
                            response = selve._serial.readline().strip()
                            msg += response.decode()
                            if response.decode() == '':
                                break

                        # do something with the received data
                        selve.processResponse(msg)

                        # if msg.rstrip() == b' ':
                        selve._LOGGER.debug(f'Received: {msg}')

            if not selve._pauseWriter:
                if not selve.txQ.empty():
                    data: Command = selve.txQ.get_nowait()
                    commandstr = data.serializeToXML()
                    selve._LOGGER.debug('Gateway writing: ' + str(commandstr))
                    try:
                        with selve._writeLock:
                            if not selve._serial.is_open:
                                selve._serial.open()
                            selve._serial.write(commandstr)
                            selve._serial.flush()
                    except Exception as e:
                        selve._LOGGER.error("error communicating: " + str(e))

                    selve.txQ.task_done()

                    # always sleep after writing
                    time.sleep(0.5)

            time.sleep(0.01)
    # serial port exceptions, all of these notify that we are in some
    # serious trouble
    except serial.SerialException:
        # log message
        selve._LOGGER.error('Serial Port RX error')


class Selve:
    """Implementation of the serial communication to the Selve Gateway"""

    def __init__(self, port=None, discover=True, develop=False, logger=None):
        # Gateway state
        self._callbacks = set()
        self.lastLogEvent = None
        self.state = None

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
        self._pauseReader = False
        self._pauseWriter = False

        # Port where the Selve gateway was found
        self._port = port

        # Write lock to safely write to the gateway
        self._writeLock = threading.Lock()
        self._readLock = threading.Lock()

        self._LOGGER = logger

        self._setup()
        
        self.readLoopTask = threading.Thread(target=_worker, args=(self, ))
        self.readLoopTask.daemon = False
        self.readLoopTask.start()

        if discover:
            self._LOGGER.info("Discovering devices")
            self.discover()

    def _setup(self):
        self._LOGGER.info("Setup")
        self.rxQ = queue.Queue()
        self.txQ = queue.Queue()


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
                
                if self.pingGateway():    
                    return
            except Exception:
                self._LOGGER.error("Configured port not valid!")
                

        available_ports = list_ports.comports()

        if len(available_ports) == 0:
            self._LOGGER.error("No available comports!")
            raise PortError

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
                if self.pingGateway():
                    self._port = p.name
                    return
                else:
                    self._serial = None
            except PortError:
                pass
        else:
            self._LOGGER.error("No gateway on comports found!")
            raise PortError

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register callback, called when Roller changes state."""
        self._callbacks.add(callback)

    def remove_callback(self, callback: Callable[[], None]) -> None:
        """Remove previously registered callback."""
        self._callbacks.discard(callback)

    def _sendCommandToGateway(self, command: Command):
        commandstr = command.serializeToXML()
        self._LOGGER.debug('Gateway writing: ' + str(commandstr))
        try:
            with self._writeLock:
                if not self._serial.is_open:
                    self._serial.open()
                self._serial.write(commandstr)
                self._serial.flush()
        except Exception as e:
            self._LOGGER.error("error communicating: " + str(e))
        # self.writer.close()

    # close the serial port, do the cleanup
    def close(self):
        # wait for the rx/tx thread to end, these need to be gathered to
        # collect all the exceptions
        self.readLoopTask.join(5)
        self._serial.close()

    def processResponse(self, xmlstr):
        """Processes an XML String into a response object."""
        # check which command was received
        # do something with the data
        # return the ready to eat response

        # The selve device sometimes answers a badformed header. This is a patch
        xmlstr = str(xmlstr).replace('<?xml version="1.0"? encoding="UTF-8">', '<?xml version="1.0" encoding="UTF-8"?>')
        try:
            res = untangle.parse(xmlstr)
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
            # if it's a MethodResponse, it has not been sent by the gateway itself, so we can safely return it
            # otherwise it's an event, and we have to process it accordingly
            if isinstance(response, CommeoDeviceEventResponse) \
                    or isinstance(response, SensorEventResponse) \
                    or isinstance(response, SenderEventResponse) \
                    or isinstance(response, LogEventResponse) \
                    or isinstance(response, DutyCycleResponse):
                return self.processEventResponse(response)
            if isinstance(response, CommandResultResponse)\
                    or isinstance(response, IveoResultResponse):
                #update device values
                self.commandResult(response)
            if isinstance(response, DeviceGetValuesResponse):
                self.updateCommeoDeviceValuesFromResponse(int(response.parameters[1][1]), response)

            return response

        except Exception as e:
            self._LOGGER.error("Error in XML: " + str(e) + " : " + xmlstr)

    def create_error(self, obj):
        if hasattr(obj, "methodResponse"):
            return ErrorResponse(obj.methodResponse.fault.array.string.cdata, obj.methodResponse.fault.array.int.cdata)
        else:
            raise CommunicationError()

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

    def executeCommand(self, command: Command):
        self.txQ.put_nowait(command)

    def executeCommandSyncWithResponse(self, command: Command):

        self._pauseWriter = True
        self._pauseReader = True
        self._pauseWorker = True
        if not self._serial.is_open:
            self._serial.open()

        self._sendCommandToGateway(command)

        start_time = time.time()
        while True:
            with self._readLock:
                if self._serial.in_waiting > 0:
                    msg = ""
                    while True:
                        response = self._serial.readline().strip()
                        msg += response.decode()
                        if response.decode() == '':
                            break
                    # if msg.rstrip() == b' ':
                    self._LOGGER.debug(f'Received: {msg}')

                    self._pauseReader = False
                    self._pauseWriter = False
                    self._pauseWorker = False

                    resp = self.processResponse(msg)
                    if isinstance(resp, ErrorResponse):
                        self._LOGGER.error(resp.message)
                        raise GatewayError
                    else:
                        #time.sleep(0.5)
                        return resp
                if time.time() - start_time > 10:
                    time.sleep(0.05)
                    return None


    def discover(self):
        if self.gatewayReady():
            iveoIds: IveoGetIdsResponse = self.executeCommandSyncWithResponse(IveoGetIds())
            deviceIds: DeviceGetIdsResponse = self.executeCommandSyncWithResponse(DeviceGetIds())
            groupIds: GroupGetIdsResponse = self.executeCommandSyncWithResponse(GroupGetIds())
            sensorIds: SensorGetIdsResponse = self.executeCommandSyncWithResponse(SensorGetIds())
            senderIds: SenderGetIdsResponse = self.executeCommandSyncWithResponse(SenderGetIds())
            senSimIds: SenSimGetIdsResponse = self.executeCommandSyncWithResponse(SenSimGetIds())

            for i in iveoIds.ids:
                config: IveoGetConfigResponse = self.executeCommandSyncWithResponse(IveoGetConfig(i))
                device = IveoDevice(i, device_sub_type=config.deviceType)
                device.name = config.name
                device.activity = config.activity
                self.addOrUpdateDevice(device, SelveTypes.IVEO)

            for i in deviceIds.ids:
                config: DeviceGetInfoResponse = self.executeCommandSyncWithResponse(DeviceGetInfo(i))
                device = SelveDevice(i, device_type=SelveTypes.DEVICE, device_sub_type=config.deviceType)
                device.name = config.name
                device.device_sub_type = config.deviceType
                device.rfAdress = config.rfAddress
                device.infoState = config.state
                self.addOrUpdateDevice(device, SelveTypes.DEVICE)
                config: DeviceGetValuesResponse = self.executeCommandSyncWithResponse(DeviceGetValues(i))
                device.state = config.movementState
                device.value = config.value
                device.targetValue = config.targetValue
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
                config: GroupReadResponse = self.executeCommandSyncWithResponse(GroupRead(i))
                device = SelveGroup(i)
                device.device_type = SelveTypes.GROUP
                device.name = config.name
                device.mask = config.mask
                self.addOrUpdateDevice(device, SelveTypes.GROUP)

            for i in sensorIds.ids:
                device = SelveSensor(i)
                config: SensorGetInfoResponse = self.executeCommandSyncWithResponse(SensorGetInfo(i))
                device.rfAdress = config.rfAddress
                device.device_type = SelveTypes.SENSOR
                self.addOrUpdateDevice(device, SelveTypes.SENSOR)
                config: SensorGetValuesResponse = self.executeCommandSyncWithResponse(SensorGetValues(i))
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
                config: SenderGetInfoResponse = self.executeCommandSyncWithResponse(SenderGetInfo(i))
                device = SelveSender(i)
                device.device_type = SelveTypes.SENDER
                device.name = config.name
                device.rfAdress = config.rfAddress
                device.channel = config.rfChannel
                device.resetCount = config.rfResetCount
                self.addOrUpdateDevice(device, SelveTypes.SENDER)

            for i in senSimIds.ids:
                config: SenSimGetConfigResponse = self.executeCommandSyncWithResponse(SenSimGetConfig(i))
                device = SelveSenSim(i)
                device.activity = config.activity
                device.device_type = SelveTypes.SENSIM
                self.addOrUpdateDevice(device, SelveTypes.SENSIM)
                config: SenSimGetValuesResponse = self.executeCommandSyncWithResponse(SenSimGetValues(i))
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
        self.list_devices()


    def updateAllDevices(self):
        for device in self.devices[SelveTypes.DEVICE.value]:
            self.updateCommeoDeviceValues(device.id)
        for sensor in self.devices[SelveTypes.SENSOR.value]:
            pass
        for senSim in self.devices[SelveTypes.SENSIM.value]:
            pass
        for sender in self.devices[SelveTypes.SENDER.value]:
            pass



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

    def pingGateway(self):
        cmd = service.ServicePing()
        methodResponse = self.executeCommandSyncWithResponse(cmd)
        if hasattr(methodResponse, "name"):
            if methodResponse.name == "selve.GW.service.ping":
                self._LOGGER.debug("Ping back")
                return True
        self._LOGGER.debug("No ping")
        return False


    def gatewayState(self):
        cmd = service.ServiceGetState()
        try:
            methodResponse = self.executeCommandSyncWithResponse(cmd)
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

    def gatewayReady(self):
        state = self.gatewayState()
        return state is ServiceState.READY

    def getVersionG(self):
        cmd = service.ServiceGetVersion()
        methodResponse = self.executeCommandSyncWithResponse(cmd)
        return methodResponse

    def getGatewayFirmwareVersion(self):
        command = self.getVersionG()
        if hasattr(command, "version"):
            return command.version
        else:
            return False

    def getGatewaySerial(self):
        command = self.getVersionG()
        if hasattr(command, "serial"):
            return command.serial
        else:
            return False

    def getGatewaySpec(self):
        command = self.getVersionG()
        if hasattr(command, "spec"):
            return command.spec
        else:
            return False

    def list_devices(self):
        """[summary]
        Log the list of registered devices
        """
        for id, val in self.devices.items():
            for id, device in val.items():
                self._LOGGER.info(str(device))

    def resetGateway(self):
        command = service.ServiceReset()
        response: ServiceResetResponse = self.executeCommandSyncWithResponse(command)
        if response.executed != 1:
            self._LOGGER.info("Error: Gateway could not be reset or loads too long")

        # time.sleep(2)

        start_time = time.time()
        while self.gatewayState() != ServiceState.READY:
            if time.time() - start_time >= 10:
                self._LOGGER.info("Error: Gateway could not be reset or loads too long")
            pass
        self._LOGGER.info("Gateway reset")

    def processEventResponse(self, response):
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
            device.value = response.value
            device.targetValue = response.targetValue
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


    def commandResult(self, response):
        for callback in self._callbacks:
            callback()

    ##Device functions

    def updateCommeoDeviceValues(self, id: int):
        response: DeviceGetValuesResponse = self.executeCommandSyncWithResponse(DeviceGetValues(id))
        self.updateCommeoDeviceValuesFromResponse(id, response)

    def updateCommeoDeviceValuesAsync(self, id: int):
        self.executeCommand(DeviceGetValues(id))
        
    def updateCommeoDeviceValuesFromResponse(self, id: int, response: DeviceGetValuesResponse):
        dev = self.getDevice(id, SelveTypes.DEVICE)
        dev.name = response.name
        dev.state = response.movementState
        dev.value = response.value
        dev.targetValue = response.targetValue
        dev.unreachable = response.unreachable
        dev.overload = response.overload
        dev.obstructed = response.obstructed
        dev.alarm = response.alarm
        dev.lostSensor = response.lostSensor
        dev.automaticMode = response.automaticMode
        dev.gatewayNotLearned = response.gatewayNotLearned
        dev.windAlarm = response.windAlarm
        dev.rainAlarm = response.rainAlarm
        dev.freezingAlarm = response.freezingAlarm
        dev.dayMode = response.dayMode
        self.addOrUpdateDevice(dev, SelveTypes.DEVICE)
        
    def setDeviceValue(self, id: int, value: int, type: SelveTypes):
        dev = self.getDevice(id, type)
        dev.value = value
        self.addOrUpdateDevice(dev, type)
        
    def setDeviceTargetValue(self, id: int, value: int, type: SelveTypes):
        dev = self.getDevice(id, type)
        dev.targetValue = value
        self.addOrUpdateDevice(dev, type)

    def setDeviceState(self, id: int, state: MovementState, type: SelveTypes):
        dev = self.getDevice(id, type)
        dev.state = state
        self.addOrUpdateDevice(dev, type)

    def moveDeviceUp(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self.executeCommand(CommandDriveUp(device.id, type))
            device.state = MovementState.UP_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            self.executeCommand(IveoManual(device.id, DriveCommandIveo.UP))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 0, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 0, SelveTypes.IVEO)

    def moveDeviceDown(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self.executeCommand(CommandDriveDown(device.id, type))
            device.state = MovementState.DOWN_ON
            self.addOrUpdateDevice(device, SelveTypes.DEVICE)
            self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            self.executeCommand(IveoManual(device.id, DriveCommandIveo.DOWN))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 100, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 100, SelveTypes.IVEO)

    def moveDevicePos1(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self.executeCommand(CommandDrivePos1(device.id, type))
            self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.UP_ON, SelveTypes.IVEO)
            self.executeCommand(IveoManual(device.id, DriveCommandIveo.POS1))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 66, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 66, SelveTypes.IVEO)

    def moveDevicePos2(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self.executeCommand(CommandDrivePos2(device.id, type))
            self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.setDeviceState(device.id, MovementState.DOWN_ON, SelveTypes.IVEO)
            self.executeCommand(IveoManual(device.id, DriveCommandIveo.POS2))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 33, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 33, SelveTypes.IVEO)

    def moveDevicePos(self, device: SelveDevice, pos: int = 0, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandDrivePos(device.id, type, param=Util.percentageToValue(pos)))
        self.updateCommeoDeviceValuesAsync(device.id)

    def moveDeviceStepUp(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandDriveStepUp(device.id, type, param=Util.degreesToValue(degrees)))
        self.updateCommeoDeviceValuesAsync(device.id)

    def moveDeviceStepDown(self, device: SelveDevice, degrees: int = 0, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandDriveStepDown(device.id, type, param=Util.degreesToValue(degrees)))
        self.updateCommeoDeviceValuesAsync(device.id)

    def stopDevice(self, device: SelveDevice | IveoDevice, type=DeviceCommandType.MANUAL):
        if device.communicationType is CommunicationType.COMMEO:
            self.executeCommand(CommandStop(device.id, type))
            self.updateCommeoDeviceValuesAsync(device.id)
        else:
            self.executeCommand(IveoManual(device.id, DriveCommandIveo.STOP))
            self.setDeviceState(device.id, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.setDeviceValue(device.id, 50, SelveTypes.IVEO)
            self.setDeviceTargetValue(device.id, 50, SelveTypes.IVEO)

    ## Group
    def moveGroupUp(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandDriveUpGroup(group.id, type))
        for id in Util.b64_mask_to_list(group.mask):
            self.updateCommeoDeviceValuesAsync(id)

    def moveGroupDown(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandDriveDownGroup(group.id, type))
        for id in Util.b64bytes_to_bitlist(group.mask):
            self.updateCommeoDeviceValuesAsync(id)

    def stopGroup(self, group: SelveGroup, type=DeviceCommandType.MANUAL):
        self.executeCommand(CommandStopGroup(group.id, type))
        for id in Util.b64bytes_to_bitlist(group.mask):
            self.updateCommeoDeviceValuesAsync(id)