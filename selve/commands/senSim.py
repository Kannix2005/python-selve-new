from selve.util import *


class SenSimStore(GatewayCommand):
    def __init__(self, id: int, actorId: int):
        super().__init__(CommeoSenSimCommand.STORE, [(ParameterType.INT, id), (ParameterType.INT, actorId)])


class SenSimDelete(GatewayCommand):
    def __init__(self, id: int, actorId: int):
        super().__init__(CommeoSenSimCommand.DELETE, [(ParameterType.INT, id), (ParameterType.INT, actorId)])


class SenSimGetConfig(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenSimCommand.GETCONFIG, [(ParameterType.INT, id)])


class SenSimSetConfig(GatewayCommand):
    def __init__(self, id: int, activity: bool):
        super().__init__(CommeoSenSimCommand.SETCONFIG,
                         [(ParameterType.INT, id), (ParameterType.INT, 1 if activity else 0)])


class SenSimSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommeoSenSimCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])


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
        super().__init__(CommeoSenSimCommand.SETVALUES,
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
        super().__init__(CommeoSenSimCommand.GETVALUES, [(ParameterType.INT, id)])


class SenSimGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoSenSimCommand.GETIDS)


class SenSimFactory(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenSimCommand.FACTORY, [(ParameterType.INT, id)])


class SenSimDrive(GatewayCommand):
    def __init__(self, id: int, command: SenSimCommandType):
        super().__init__(CommeoSenSimCommand.DRIVE, [(ParameterType.INT, id), (ParameterType.INT, command)])


class SenSimSetTest(GatewayCommand):
    def __init__(self, id: int, testMode: int):
        super().__init__(CommeoSenSimCommand.SETTEST, [(ParameterType.INT, id), (ParameterType.INT, testMode)])


class SenSimGetTest(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoSenSimCommand.GETTEST, [(ParameterType.INT, id)])


class SenSimStoreResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimDeleteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimGetConfigResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = str(parameters[0][1])
        self.senSimId = int(parameters[1][1])
        self.activity = bool(parameters[2][1])


class SenSimSetConfigResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimSetLabelResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimSetValuesResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimGetValuesResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.sensorState = None
        self.windDigital = windDigital(int(parameters[1][1]))
        self.rainDigital = rainDigital(int(parameters[2][1]))
        self.tempDigital = tempDigital(int(parameters[3][1]))
        self.lightDigital = lightDigital(int(parameters[4][1]))
        self.tempAnalog = int(parameters[5][1])
        self.windAnalog = int(parameters[6][1])
        self.sun1Analog = int(parameters[7][1])
        self.dayLightAnalog = int(parameters[8][1])
        self.sun2Analog = int(parameters[9][1])
        self.sun3Analog = int(parameters[10][1])


class SenSimGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]


class SenSimFactoryResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimDriveResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimSetTestResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class SenSimGetTestResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.id = int(parameters[0][1])
        self.testMode = bool(parameters[1][1])
