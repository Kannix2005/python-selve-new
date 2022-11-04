import base64
from selve.util.protocol import *

class Command():
    def __init__(self, method_name, parameters = []) -> None:
        self.method_name = method_name
        self.parameters = parameters

    def serializeToXML(self):
            xmlstr = "<methodCall>"
            xmlstr += "<methodName>"+self.method_name+"</methodName>"
            if (len(self.parameters) > 0):
                xmlstr += "<array>"
                for typ, val in self.parameters:
                    xmlstr+="<{0}>{1}</{0}>".format(typ.value, val)
                xmlstr += "</array>"
            xmlstr+= "</methodCall>"
            return xmlstr.encode('utf-8')
 

class GatewayCommand(Command):

    def __init__(self, method_name, parameters = []):
         super().__init__("selve.GW." + method_name.value, parameters)

class CommandSingle(Command):

    def __init__(self, method_name, iveoID):
        super().__init__(method_name, [(ParameterType.INT, iveoID)])

class CommandMask(Command):

    def __init__(self, method_name, mask, command):
        super().__init__(method_name, [(ParameterType.BASE64, mask), (ParameterType.INT, command.value)])


class MethodResponse:

    def __init__(self, name, parameters):
        self.name = name
        self.parameters = parameters
        
class CommeoCommandResult(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.command = self.name
        self.commandType = DeviceCommandType(int(parameters[1][1]))
        self.executed = bool(parameters[2][1])
        self.successIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[3][1]))]
        self.failedIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[4][1]))]

class CommeoDeviceEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        #self.name = parameters[0][1] if parameters[0][1] else ""
        self.id = int(parameters[0][1])
        self.actorState = MovementState(int(parameters[1][1])) if int(parameters[2][1]) and int(parameters[2][1]) < 4 else MovementState(0)        
        self.value = Util.valueToPercentage(int(parameters[2][1]))
        self.targetValue = Util.valueToPercentage(int(parameters[3][1]))
        
        bArr = Util.intToBoolarray(int(parameters[4][1]))
        self.unreachable = bArr[0]
        self.overload = bArr[1]
        self.obstructed = bArr[2]
        self.alarm = bArr[3]
        self.lostSensor = bArr[4]
        self.automaticMode = bArr[5]
        self.gatewayNotLearned = bArr[6]
        self.windAlarm = bArr[7]
        self.rainAlarm = bArr[8]
        self.freezingAlarm = bArr[9]
        self.dayMode = DayMode(int(parameters[5][1]))
        self.deviceType = DeviceType(int(parameters[6][1]))

class LogEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.logCode = str(parameters[0][1])
        self.logStamp = str(parameters[1][1])
        self.logValue = str(parameters[2][1])
        self.logDescription = str(parameters[3][1])
        self.logType = LogType(int(parameters[4][1]))

class DutyCycleResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.mode = DutyMode(int(parameters[0][1]))
        self.traffic = int(parameters[1][1])

class SensorEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.id = int(parameters[0][1])
        self.windDigital = windDigital(int(parameters[1][1]))
        self.rainDigital = rainDigital(int(parameters[2][1]))
        self.tempDigital = tempDigital(int(parameters[3][1]))
        self.lightDigital = lightDigital(int(parameters[4][1]))
        self.sensorState = SensorState(int(parameters[5][1]))
        self.tempAnalog = int(parameters[6][1])
        self.windAnalog = int(parameters[7][1])
        self.sun1Analog = int(parameters[8][1])
        self.dayLightAnalog = int(parameters[9][1])
        self.sun2Analog = int(parameters[10][1])
        self.sun3Analog = int(parameters[11][1])

class SenderEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.senderName = str(parameters[0][1])
        self.id = int(parameters[1][1])
        self.event = senderEvents(int(parameters[2][1]))

class ErrorResponse:
    def __init__(self, message, code):
        self.message = message
        self.code = code


class Util():
    @classmethod
    def singlemask(self, id):
        #Obtains a base64 encoded to modify just one index
        mask =  64 * [0]
        #need to transform the position
        newid = int((int(id) // 8) * 8  + 7 - (int(id) % 8))    
        mask[newid] = 1
        bitstring = "".join(str(x) for x in mask)
        return base64.b64encode(self.bitstring_to_bytes(bitstring)).decode('utf8')

    @classmethod
    def multimask(self, ids):
        mask = 64 * [0]
        for id in ids:
            newid = int((int(id) // 8) * 8  + 7 - (int(id) % 8))    
            mask[newid] = 1
        bitstring = "".join(str(x) for x in mask)
        return base64.b64encode(self.bitstring_to_bytes(bitstring)).decode('utf8')

    @classmethod
    def bitstring_to_bytes(self, s):
        return int(s, 2).to_bytes(len(s) // 8, byteorder='big')

    @classmethod
    def b64bytes_to_bitlist(self, b):
        byts = base64.b64decode(b)
        return [bool(int(value)) for value in list(''.join([bin(by).lstrip('0b').zfill(8)[::-1] for by in byts]))]

    @classmethod
    def b64_mask_to_list(self, b):
        return self.true_in_list(self.b64bytes_to_bitlist(b))


    @classmethod
    def true_in_list(self, l):
        return [i for i,v in enumerate(l) if v]

    @classmethod
    def valueToPercentage(self, value):
        return int((int(value) / 65535)*100)
    @classmethod
    def valueToDegrees(self, value):
        return int((int(value) / 65535)*360)

    @classmethod
    def percentageToValue(self, perc):
        return int((65535/100)*(int(perc)))
    @classmethod
    def degreesToValue(self, perc):
        return int((65535/360)*(int(perc)))

    @classmethod
    def intToBoolarray(self, value):
        return [bool(bit) for bit in '{0:10b}'.format(value)]

from enum import Enum

class CommeoServiceCommand(Enum):
    PING = "service.ping"
    GETSTATE = "service.getState"
    GETVERSION = "service.getVersion"
    RESET = "service.reset"
    FACTORYRESET = "service.factoryReset"
    SETLED = "service.setLED"
    GETLED = "service.getLED"
    
class CommeoParamCommand(Enum):
    SETFORWARD = "param.setForward"
    GETFORWARD = "param.getForward"
    SETEVENT = "param.setEvent"
    GETEVENT = "param.getEvent"
    GETDUTY = "param.getDuty"
    GETRF = "param.getRF"

class CommeoDeviceCommand(Enum):
    SCANSTART = "device.scanStart"
    SCANSTOP = "device.scanStop"
    SCANRESULT = "device.scanResult"
    SAVE = "device.save"
    GETIDS = "device.getIDs"
    GETINFO = "device.getInfo"
    GETVALUES = "device.getValues"
    SETFUNCTION = "device.setFunction"
    SETLABEL = "device.setLabel"
    SETTYPE = "device.setType"
    DELETE = "device.delete"
    WRITEMANUAL = "device.writeManual"
    
class CommeoSensorCommand(Enum):
    TEACHSTART = "sensor.teachStart"
    TEACHSTOP = "sensor.teachStop"
    TEACHRESULT = "sensor.teachResult"
    GETIDS = "sensor.getIDs"
    GETINFO = "sensor.getInfo"
    GETVALUES = "sensor.getValues"
    SETLABEL = "sensor.setLabel"
    DELETE = "sensor.delete"
    WRITEMANUAL = "sensor.writeManual"

class CommeoSenSimCommand(Enum):
    STORE = "senSim.store"
    DELETE = "senSim.delete"
    GETCONFIG = "senSim.getConfig"
    SETCONFIG = "senSim.setConfig"
    SETLABEL = "senSim.setLabel"
    SETVALUES = "senSim.setValues"
    GETVALUES = "senSim.getValues"
    GETIDS = "senSim.getIDs"
    FACTORY = "senSim.factory"
    DRIVE = "senSim.drive"
    SETTEST = "senSim.setTest"
    GETTEST = "senSim.getTest"
    
class CommeoSenderCommand(Enum):
    TEACHSTART = "sender.teachStart"
    TEACHSTOP = "sender.teachStop"
    TEACHRESULT = "sender.teachResult"
    GETIDS = "sender.getIDs"
    GETINFO = "sender.getInfo"
    GETVALUES = "sender.getValues"
    SETLABEL = "sender.setLabel"
    DELETE = "sender.delete"
    WRITEMANUAL = "sender.writeManual"

class CommeoGroupCommand(Enum):
    READ = "group.read"
    WRITE = "group.write"
    GETIDS = "group.getIDs"
    DELETE = "group.delete"

class CommeoCommandCommand(Enum):
    DEVICE = "command.device"
    GROUP = "command.group"
    GROUPMAN = "command.groupMan"
    RESULT = "command.result"
    
class CommeoEventCommand(Enum):
    DEVICE = "event.device"
    SENSOR = "event.sensor"
    SENDER = "event.sender"
    LOG = "event.log"
    DUTYCYCLE = "event.dutyCycle"

class IveoCommand(Enum):
    FACTORY = "iveo.factory"
    SETCONFIG = "iveo.setConfig"
    GETCONFIG = "iveo.getConfig"
    GETIDS = "iveo.getIDs"
    SETREPEATER = "iveo.setRepeater"
    GETREPEATER = "iveo.getRepeater"
    SETLABEL = "iveo.setLabel"
    TEACH = "iveo.commandTeach"
    LEARN = "iveo.commandLearn"
    MANUAL = "iveo.commandManual"
    AUTOMATIC = "iveo.commandAutomatic"
    RESULT = "iveo.commandResult"
    

class CommandType(Enum):
    def __getattr__(self, item):
        if item != '_value_':
            return getattr(self.value, item).value
        raise AttributeError
    SERVICE = CommeoServiceCommand   
    PARAM = CommeoParamCommand
    DEVICE = CommeoDeviceCommand
    SENSOR = CommeoSensorCommand
    SENSIM = CommeoSenSimCommand
    SENDER = CommeoSenderCommand
    GROUP = CommeoGroupCommand
    COMMAND = CommeoCommandCommand
    EVENT = CommeoEventCommand
    IVEO = IveoCommand

### Responses
    
class ResponseTypes(Enum):
    COMMANDRESULT = "selve.gw.command.result"