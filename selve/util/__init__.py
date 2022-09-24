import protocol
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
        
    def executeAsync(self):
        pass
    def execute(self):
        pass

class GatewayCommand(Command):

    def __init__(self, method_name, parameters = []):
         super().__init__("selve.GW." + method_name.value, parameters)

class CommandSingle(Command):

    def __init__(self, method_name, iveoID):
        super().__init__(method_name, [(ParameterType.INT, iveoID)])

class CommandMask(Command):

    def __init__(self, method_name, mask, command):
        super().__init__(method_name, [(ParameterType.BASE64, mask), (ParameterType.INT, command.value)])

class Util():
    
    def singlemask(self, id):
        #Obtains a base64 encoded to modify just one index
        mask =  64 * [0]
        #need to transform the position
        newid = int((id // 8) * 8  + 7 - (id % 8))    
        mask[newid] = 1
        bitstring = "".join(str(x) for x in mask)
        return base64.b64encode(self.bitstring_to_bytes(bitstring)).decode('utf8')

    def multimask(self, ids):
        mask = 64 * [0]
        for id in ids:
            newid = int((id // 8) * 8  + 7 - (id % 8))    
            mask[newid] = 1
        bitstring = "".join(str(x) for x in mask)
        return base64.b64encode(self.bitstring_to_bytes(bitstring)).decode('utf8')


    def bitstring_to_bytes(self, s):
        return int(s, 2).to_bytes(len(s) // 8, byteorder='big')

    def b64bytes_to_bitlist(self, b):
        byts = base64.b64decode(b)
        return [bool(int(value)) for value in list(''.join([bin(by).lstrip('0b').zfill(8)[::-1] for by in byts]))]

    def true_in_list(self, l):
        return [i for i,v in enumerate(l) if v]

    def valueToPercentage(self, value):
        return int((value / 65535)*100)

    def percentageToValue(self, perc):
        return int((65535/100)*(perc))

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