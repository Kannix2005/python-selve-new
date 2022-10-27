from selve.util import *
        
class SenderTeachStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSenderCommand.TEACHSTART)
        
class SenderTeachStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSenderCommand.TEACHSTOP)
        
class SenderTeachResult(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSenderCommand.TEACHRESULT)
        
class SenderGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSenderCommand.GETIDS)
        
class SenderGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenderCommand.GETINFO, [(ParameterType.INT, id)])
        
class SenderGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenderCommand.GETVALUES, [(ParameterType.INT, id)])
        
class SenderSetLabel(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenderCommand.SETLABEL, [(ParameterType.INT, id)])
        
class SenderDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenderCommand.DELETE, [(ParameterType.INT, id)])
        
class SenderWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, channel: int, resetCount: int, name: str):
        super().__init__(CommeoSenderCommand.WRITEMANUAL, [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.INT, channel), (ParameterType.INT, resetCount), (ParameterType.STRING, name)])




class SenderTeachStartResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class SenderTeachStopResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class SenderTeachResultResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = str(parameters[0][1])
        self.teachState = TeachState(int(parameters[1][1]))
        self.timeLeft = int(parameters[1][1])
        self.senderId = int(parameters[2][1])
        self.senderEvent = senderEvents(int(parameters[3][1]))

class SenderGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]

class SenderGetInfoResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = parameters[0][1] if parameters[0][1] else ""
        self.rfAddress = parameters[2][1]
        self.rfChannel = int(parameters[3][1])
        self.rfResetCount = int(parameters[4][1])

class SenderGetValuesResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.lastEvent = senderEvents(int(parameters[1][1]))

class SenderSetLabelResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class SenderDeleteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class SenderWriteManualResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
