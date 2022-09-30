from selve.util import *


class IveoFactory(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.IveoCommand.FACTORY, [(ParameterType.INT, id)])


class IveoSetConfig(GatewayCommand):
    def __init__(self, id: int, activity: int, type: DeviceType):
        super().__init__(CommandType.IveoCommand.SETCONFIG, [(ParameterType.INT, id), (ParameterType.INT, activity), (ParameterType.INT, type.value)])


class IveoGetConfig(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.IveoCommand.GETCONFIG, [(ParameterType.INT, id)])


class IveoGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.GETIDS)


class IveoSetRepeater(GatewayCommand):
    def __init__(self, repeaterInstalled: int):
        super().__init__(CommandType.IveoCommand.SETREPEATER, [(ParameterType.INT, id)])


class IveoGetRepeater(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.GETREPEATER)


class IveoSetLabel(GatewayCommand):
    def __init__(self, id: bool, name: str):
        super().__init__(CommandType.IveoCommand.SETLABEL, [(ParameterType.INT, id), (ParameterType.STRING, name)])


class IveoTeach(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.IveoCommand.TEACH, [(ParameterType.INT, id)])


class IveoLearn(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.IveoCommand.LEARN, [(ParameterType.INT, id)])


class IveoManual(GatewayCommand):
    def __init__(self, actorIds: dict, command: DriveCommands):
        super().__init__(CommandType.IveoCommand.MANUAL, [(ParameterType.BASE64, Util.multimask(actorIds)), (ParameterType.INT, command.value)])


class IveoAutomatic(GatewayCommand):
    def __init__(self, actorIds: dict, command: DriveCommands):
        super().__init__(CommandType.IveoCommand.AUTOMATIC, [(ParameterType.BASE64, Util.multimask(actorIds)), (ParameterType.INT, command.value)])


class IveoResult(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.RESULT)
