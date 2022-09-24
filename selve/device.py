from selve.util import *
        
class DeviceScanStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoDeviceCommand.SCANSTART)
        
class DeviceScanStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoDeviceCommand.SCANSTOP)
        
class DeviceSave(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoDeviceCommand.SAVE, [(ParameterType.INT, id)])
        
class DeviceGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoDeviceCommand.GETIDS)
        
class DeviceGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoDeviceCommand.GETINFO, [(ParameterType.INT, id)])
        
class DeviceGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoDeviceCommand.GETVALUES, [(ParameterType.INT, id)])
        
class DeviceSetFunction(GatewayCommand):
    def __init__(self, id: int, function: DeviceFunctions):
        super().__init__(CommandType.CommeoDeviceCommand.SETFUNCTION, [(ParameterType.INT, id), (ParameterType.INT, function.value)])
        
class DeviceSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommandType.CommeoDeviceCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])
        
class DeviceSetType(GatewayCommand):
    def __init__(self, id: int, type: DeviceType):
        super().__init__(CommandType.CommeoDeviceCommand.SETTYPE, [(ParameterType.INT, id), (ParameterType.INT, type.value)])
        
class DeviceDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoDeviceCommand.DELETE, [(ParameterType.INT, id)])
        
class DeviceWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, name: str, type: DeviceType):
        super().__init__(CommandType.CommeoDeviceCommand.WRITEMANUAL, [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.STRING, name), (ParameterType.INT, type.value)])