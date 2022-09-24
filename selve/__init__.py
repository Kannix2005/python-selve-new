import asyncio
import logging
import queue
#import nest_asyncio
from selve.util.commandFactory import Command
import serial_asyncio
import serial
import aioconsole

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


    async def _setup(self):
        print ("Setup")
        self.rxQ = asyncio.Queue()
        self.txQ = asyncio.Queue()
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

        # serial port exceptions, all of these notify that we are in some
        # serious trouble
        except serial.SerialException:
            # log message
            self._LOGGER.error('Serial Port TX error')


    async def _workerLoop(self):
        print("worker started")
        while True:
            if self.rxQ.qsize() > 0:
                print("Checktrue")
                data = await self.rxQ.get()
                print(f'Data: {data}')
                ## do something with the recieved data
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
        


    async def executeCommand(self, command: Command):
        await self.txQ.put(command)

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
        command = CommeoServicePing()
        await command.execute(self)
        print("Ping")


    async def gatewayState(self):
        command = CommeoServiceGetState()
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
        command = CommeoServiceGetVersion()
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

