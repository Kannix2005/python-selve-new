from selve.util import *


class SensorTechStart(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSensorCommand.TEACHSTART)


class SensorTeachStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSensorCommand.TEACHSTOP)


class SensorGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSensorCommand.GETIDS)


class SensorGetInfo(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSensorCommand.GETINFO, [(ParameterType.INT, id)])


class SensorGetValues(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSensorCommand.GETVALUES, [(ParameterType.INT, id)])


class SensorSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommeoSensorCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])


class SensorDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSensorCommand.DELETE, [(ParameterType.INT, id)])


class SensorWriteManual(GatewayCommand):
    def __init__(self, id: int, adress: int, name: str):
        super().__init__(CommeoSensorCommand.WRITEMANUAL,
                         [(ParameterType.INT, id), (ParameterType.INT, adress), (ParameterType.STRING, name)])


class SensorTeachStartResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SensorTeachStopResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SensorTeachResultResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.teachState = TeachState(int(parameters[0][1]))
        self.timeLeft = int(parameters[1][1])
        self.foundId = int(parameters[2][1])


class SensorGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]


class SensorGetInfoResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = parameters[0][1]
        self.rfAddress = parameters[2][1]


class SensorGetValuesResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
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


class SensorSetLabelResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SensorDeleteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SensorWriteManualResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
