from selve.util import *
        
class SenderTeachStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSenderCommand.TEACHSTART)
        
class SenderTeachStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSenderCommand.TEACHSTOP)
        
class SenderTeachResult(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSenderCommand.TEACHRESULT)
        
class SenderGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSenderCommand.GETIDS)
        
class SenderGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenderCommand.GETINFO, [(ParameterType.INT, id)])
        
class SenderGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenderCommand.GETVALUES, [(ParameterType.INT, id)])
        
class SenderSetLabel(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenderCommand.SETLABEL, [(ParameterType.INT, id)])
        
class SenderDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenderCommand.DELETE, [(ParameterType.INT, id)])
        
class SenderWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, channel: int, resetCount: int, name: str):
        super().__init__(CommandType.CommeoSenderCommand.WRITEMANUAL, [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.INT, channel), (ParameterType.INT, resetCount), (ParameterType.STRING, name)])