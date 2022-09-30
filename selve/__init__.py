import asyncio
from itertools import chain
import logging
import queue
from time import time
from selve.util import CommeoCommandResult, CommeoDeviceEventResponse, DutyCycleResponse, ErrorResponse, LogEventResponse, MethodResponse, ResponseType, SenderEventResponse, SensorEventResponse, Util
#import nest_asyncio
from selve.util.commandFactory import Command
from selve.util.protocol import ParameterType
import serial_asyncio
import serial
import aioconsole
import untangle

from selve.service import *
from selve import *
from selve.util import Command

_LOGGER = logging.getLogger(__name__)

class Selve():
    """Implementation of the serial communication to the Selve Gateway"""

    def __init__(self, port, loop : asyncio.AbstractEventLoop = None, discover = True, develop = False):
        self.port = port
        self.connected = False
        self._LOGGER = _LOGGER
        self.devices: dict = {}
        self.develop = develop
        #nest_asyncio.apply(loop)

        if loop == None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:  # no event loop running:
                loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.loop = loop
        asyncio.run(self._setup())
        self.loop.create_task(self._start())

        if discover:
            _LOGGER.info("Discovering devices")
            asyncio.run(self.discover())

    @property
    def port(self):
        return self.port

    @property
    def loop(self):
        return self.loop
    
    @property
    def devices(self):
        return self.devices

    @property
    def gateway(self):
        return self

    @port.setter
    def port(self, value):
        self._port = value

    @devices.setter
    def devices(self, value):
        self._devices = value

    @loop.setter
    def loop(self, value):
        self._loop = value

    async def _setup(self):
        print ("Setup")
        self.rxQ = asyncio.Queue()
        self.txQ = asyncio.Queue()
        self.pauseWorker = False
        self.reader, self.writer = await serial_asyncio.open_serial_connection(
            loop=self.loop, 
            url="COM8", 
            baudrate=115200, 
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )


    async def _readLoop(self):
        # Infinite loop to collect all incoming data
        print ("Reader started")
        try:
            while True:
                msg = await self.reader.readuntil(b' ')
                #if msg.rstrip() == b' ':
                print(f'Recieved:  {msg.decode()}')
                
                await self.rxQ.put(msg.decode())
        # serial port exceptions, all of these notify that we are in some
        # serious trouble
        except serial.SerialException:
            # log message
            self._LOGGER.error('Serial Port RX error')

    async def _writeLoop(self):
        # Infinite loop to collect all incoming data
        print ("Writer started")
        try:
            while True:
                data = await self.txQ.get()

                await self._sendCommandToGateway(data)

                self.txQ.task_done()
        # serial port exceptions, all of these notify that we are in some
        # serious trouble
        except serial.SerialException:
            # log message
            self._LOGGER.error('Serial Port TX error')


    async def _workerLoop(self):
        print("worker started")
        while True:
            if not self.pauseWorker:
                if self.rxQ.qsize() > 0:
                    comm = await self.rxQ.get()
                    print(f'Data recieved: {comm}')
                    ## do something with the recieved data
                    self.processResponse(comm)
                else:
                    if(self.develop == True):
                        line = await aioconsole.ainput('Command: ')

                    cmd = Command(line, [])

                    await self.executeCommand(cmd)


    async def _sendCommandToGateway(self, command: Command):
        commandstr = command.serializeToXML()
        _LOGGER.info('Gateway writing: ' + str(commandstr))
        try:
            self.writer.write(commandstr)
        except Exception as e:
            _LOGGER.error ("error communicating: " + str(e))
        #self.writer.close()


    async def _start(self):
        """Start all looping threads.
        """
        asyncio.set_event_loop(self.loop)
        self.readLoopTask = asyncio.create_task(self._readLoop())
        self.writeLoopTask = asyncio.create_task(self._writeLoop())
        self.workerThreadTask = asyncio.create_task(self._workerLoop())

    # close the serial port, do the cleanup
    async def close(self):
        # wait for the rx/tx thread to end, these need to be gathered to
        # collect all the exceptions
        await asyncio.gather(self.readLoopTask, self._readLoop)
        await asyncio.gather(self.readLoopTask, self._writeLoop)
        await asyncio.gather(self.readLoopTask, self._workerLoop)

    def processResponse(self, comm):
        """Processes an XML String into a response object."""
        # check which command was recieved
        # do something with the data
        # return the ready to eat command

        _LOGGER.debug(str(xmlstr))
        #The selve device sometimes answers a badformed header. This is a patch
        xmlstr = str(xmlstr).replace('<?xml version="1.0"? encoding="UTF-8">', '<?xml version="1.0" encoding="UTF-8"?>')
        try:
            res = untangle.parse(xmlstr)
            if not hasattr(res, 'methodResponse'):
                _LOGGER.error("Bad response format")
                return None
            if hasattr(res.methodResponse, 'fault'):
                return self.create_error(res)
            return self.create_response(res)
        except Exception as e:
            _LOGGER.error("Error in XML: " + str(e) + " : " + xmlstr)

    def create_error(obj):
        return ErrorResponse(obj.methodResponse.fault.array.string.cdata, obj.methodResponse.fault.array.int.cdata)


    def create_response(obj):
        array = obj.methodResponse.array
        methodName = list(array.string)[0].cdata
        str_params_tmp = list(array.string)[1:]
        str_params = [(ParameterType.STRING, v.cdata) for v in str_params_tmp]
        int_params = []
        if hasattr(array, ParameterType.INT.value):
            int_params = [(ParameterType.INT, v.cdata) for v in list(array.int)]
        b64_params = []
        if hasattr(array, ParameterType.BASE64.value):
            b64_params = [(ParameterType.BASE64, v.cdata) for v in list(array.base64)]
        paramslist = [str_params, int_params, b64_params]
        flat_params_list = list(chain.from_iterable(paramslist))


        if methodName == "selve.GW.command.result":
            return CommeoCommandResult(methodName, flat_params_list)
        if methodName == "selve.GW.event.device":
            return CommeoDeviceEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW.event.sensor":
            return SensorEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW.event.sender":
            return SenderEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW.event.log":
            return LogEventResponse(methodName, flat_params_list)
        if methodName == "selve.GW.event.dutyCycle":
            return DutyCycleResponse(methodName, flat_params_list)

        return MethodResponse(methodName, flat_params_list)


    async def executeCommand(self, command: Command):
        await self.txQ.put(command)

    def executeCommandSync(self, command: Command, responseName: str):
        self.pauseWorker = True
        self.loop.run_until_complete(self._sendCommandToGateway(command))
        #search response in queue

        startTimer = time.time() + 20 #20 sec timeout

        while foundCommand := self._searchInQueue(responseName) is False:
            if time.time() > startTimer:
                self.pauseWorker = False
                return False
        else:
            self.pauseWorker = False
            return self.processResponse(foundCommand)



    async def discover(self):
        print("discover")

    async def addDevice(self, id, device):
        self.devices[id] = device
        # add in gateway
        pass

    async def deleteDevice(self, id):
        #delete in GW
        self.devices.pop(id)
        pass

    async def is_id_registered(self, id):
        return id in self.devices

    async def findFreeId(self):
        i = 0
        while i < 64:
            if not self.is_id_registered(i):
                return i
            i=i+1

    async def pingGateway(self):
        self.gatewayReady()
        command = ServicePing()
        await command.execute(self)
        print("Ping")


    async def gatewayState(self):
        command = ServiceGetState()
        await command.execute(self)
        if hasattr(command, "status"):
            return command.status

    async def gatewayReady(self):
        state = await self.gatewayState() 
        if state == ServiceState.READY:
            return
        else:
            raise GatewayError

    async def getVersionG(self):
        self.gatewayReady()
        command = ServiceGetVersion()
        return await command.execute(self)

    async def getGatewayFirmwareVersion(self):
        command = self.getVersionG()
        if hasattr(command, "version"):
            return command.version

    async def getGatewaySerial(self):
        command = self.getVersionG()
        if hasattr(command, "serial"):
            return command.serial

    async def getGatewaySpec(self):
        command = self.getVersionG()
        if hasattr(command, "spec"):
            return command.spec

