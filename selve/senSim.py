from selve.util import *
        
class SenSimStoreStore(GatewayCommand):
    def __init__(self, id: int, actorId: int):
        super().__init__(CommandType.CommeoSenSimCommand.STORE, [(ParameterType.INT, id), (ParameterType.INT, actorId)])
        
class SenSimDelete(GatewayCommand):
    def __init__(self, id: int, actorId: int):
        super().__init__(CommandType.CommeoSenSimCommand.DELETE, [(ParameterType.INT, id), (ParameterType.INT, actorId)])
        
class SenSimGetConfig(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenSimCommand.GETCONFIG, [(ParameterType.INT, id)])
        
class SenSimSetConfig(GatewayCommand):
    def __init__(self, id: int, activity: bool):
        super().__init__(CommandType.CommeoSenSimCommand.SETCONFIG, [(ParameterType.INT, id), (ParameterType.INT, 1 if activity else 0)])
        
class SenSimSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommandType.CommeoSenSimCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])
        
class SenSimSetValues(GatewayCommand):
    def __init__(
        self, 
        id: int, 
        windDigital: int, 
        rainDigital: int, 
        tempDigital: int, 
        lightDigital: int, 
        tempAnalog: int, 
        windAnalog: int, 
        sun1Analog: int, 
        dayLightAnalog: int, 
        sun2Analog: int, 
        sun3Analog: int
        ):
        super().__init__(CommandType.CommeoSenSimCommand.SETVALUES, 
                         [(ParameterType.INT, id), 
                          (ParameterType.INT, windDigital), 
                          (ParameterType.INT, rainDigital), 
                          (ParameterType.INT, tempDigital), 
                          (ParameterType.INT, lightDigital), 
                          (ParameterType.INT, tempAnalog), 
                          (ParameterType.INT, windAnalog), 
                          (ParameterType.INT, sun1Analog), 
                          (ParameterType.INT, dayLightAnalog), 
                          (ParameterType.INT, sun2Analog), 
                          (ParameterType.INT, sun3Analog)])
        
class SenSimGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenSimCommand.GETVALUES, [(ParameterType.INT, id)])
        
class SenSimGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSenSimCommand.GETIDS)
        
class SenSimFactory(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenSimCommand.FACTORY, [(ParameterType.INT, id)])
        
class SenSimDrive(GatewayCommand):
    def __init__(self, id: int, command: SenSimCommandType):
        super().__init__(CommandType.CommeoSenSimCommand.DRIVE, [(ParameterType.INT, id), (ParameterType.INT, command)])
        
class SenSimSetTest(GatewayCommand):
    def __init__(self, id: int, testMode: int):
        super().__init__(CommandType.CommeoSenSimCommand.SETTEST, [(ParameterType.INT, id), (ParameterType.INT, testMode)])
        
class SenSimGetTest(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSenSimCommand.GETTEST, [(ParameterType.INT, id)])