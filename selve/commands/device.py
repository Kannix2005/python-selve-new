from selve.util import *


class DeviceScanStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoDeviceCommand.SCANSTART)


class DeviceScanStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoDeviceCommand.SCANSTOP)


class DeviceSave(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoDeviceCommand.SAVE, [(ParameterType.INT, id)])


class DeviceGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoDeviceCommand.GETIDS)


class DeviceGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoDeviceCommand.GETINFO, [(ParameterType.INT, id)])


class DeviceGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoDeviceCommand.GETVALUES, [(ParameterType.INT, id)])


class DeviceSetFunction(GatewayCommand):
    def __init__(self, id: int, function: DeviceFunctions):
        super().__init__(CommeoDeviceCommand.SETFUNCTION,
                         [(ParameterType.INT, id), (ParameterType.INT, function.value)])


class DeviceSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommeoDeviceCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])


class DeviceSetType(GatewayCommand):
    def __init__(self, id: int, type: DeviceType):
        super().__init__(CommeoDeviceCommand.SETTYPE, [(ParameterType.INT, id), (ParameterType.INT, type.value)])


class DeviceDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoDeviceCommand.DELETE, [(ParameterType.INT, id)])


class DeviceWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, name: str, type: DeviceType):
        super().__init__(CommeoDeviceCommand.WRITEMANUAL,
                         [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.STRING, name),
                          (ParameterType.INT, type.value)])


class DeviceScanStartResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceScanStopResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class DeviceScanResultResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.scanState = ScanState(int(parameters[0][1]))
        self.noNewDevices = int(parameters[1][1])
        self.foundIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[2][1]))]


class DeviceSaveResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]


class DeviceGetInfoResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = parameters[0][1]
        self.rfAddress = parameters[2][1]
        self.deviceType = DeviceType(int(parameters[3][1]))
        self.state = DeviceState(int(parameters[4][1]))


class DeviceGetValuesResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = parameters[0][1] if parameters[0][1] else ""
        self.movementState = MovementState(int(parameters[2][1])) if int(parameters[2][1]) else MovementState(0)
        self.value = Util.valueToPercentage(int(parameters[3][1]))
        self.targetValue = Util.valueToPercentage(int(parameters[4][1]))

        bArr = Util.intToBoolarray(int(parameters[5][1]))
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

        self.dayMode = DayMode(int(parameters[6][1]))


class DeviceSetFunctionResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceSetLabelResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceSetTypeResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceDeleteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class DeviceWriteManualResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
