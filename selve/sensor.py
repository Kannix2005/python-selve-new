from selve.util import *
        
class SensorTechStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSensorCommand.TEACHSTART)
        
class SensorTeachStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSensorCommand.TEACHSTOP)

class SensorGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoSensorCommand.GETIDS)
        
class SensorGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSensorCommand.GETINFO, [(ParameterType.INT, id)])
        
class SensorGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSensorCommand.GETVALUES, [(ParameterType.INT, id)])
        
class SensorSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommandType.CommeoSensorCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])
        
class SensorDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoSensorCommand.DELETE, [(ParameterType.INT, id)])
        
class SensorWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, name: str):
        super().__init__(CommandType.CommeoSensorCommand.WRITEMANUAL, [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.STRING, name)])