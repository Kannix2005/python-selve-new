from selve.util import *


class IveoFactory(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(IveoCommand.FACTORY, [(ParameterType.INT, id)])


class IveoSetConfig(GatewayCommand):
    def __init__(self, id: int, activity: int, type: DeviceType):
        super().__init__(IveoCommand.SETCONFIG,
                         [(ParameterType.INT, id), (ParameterType.INT, activity), (ParameterType.INT, type.value)])


class IveoGetConfig(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(IveoCommand.GETCONFIG, [(ParameterType.INT, id)])


class IveoGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(IveoCommand.GETIDS)


class IveoSetRepeater(GatewayCommand):
    def __init__(self, repeaterInstalled: int):
        super().__init__(IveoCommand.SETREPEATER, [(ParameterType.INT, repeaterInstalled)])


class IveoGetRepeater(GatewayCommand):
    def __init__(self):
        super().__init__(IveoCommand.GETREPEATER)


class IveoSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(IveoCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])


class IveoTeach(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(IveoCommand.TEACH, [(ParameterType.INT, id)])


class IveoLearn(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(IveoCommand.LEARN, [(ParameterType.INT, id)])


class IveoManual(GatewayCommand):
    def __init__(self, actorId: int, command: DriveCommandIveo):
        super().__init__(IveoCommand.MANUAL,
                         [(ParameterType.BASE64, Util.singlemask(actorId)), (ParameterType.INT, command.value)])


class IveoAutomatic(GatewayCommand):
    def __init__(self, actorId: int, command: DriveCommandIveo):
        super().__init__(IveoCommand.AUTOMATIC,
                         [(ParameterType.BASE64, Util.singlemask(actorId)), (ParameterType.INT, command.value)])


class IveoResult(GatewayCommand):
    def __init__(self):
        super().__init__(IveoCommand.RESULT)


class IveoFactoryResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoSetConfigResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoGetConfigResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.name = parameters[0][1]
        self.activity = parameters[2][1]
        self.deviceType = DeviceType(int(parameters[3][1]))


class IveoGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]


class IveoSetRepeaterResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoGetRepeaterResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.repeaterState = RepeaterState(int(parameters[0][1]))


class IveoSetLabelResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoTeachResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoLearnResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoManualResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoAutomaticResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class IveoResultResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.command = DriveCommandIveo(int(parameters[0][1]))
        self.state = CommandResultState(int(parameters[1][1]))
        self.executedIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[2][1]))]
