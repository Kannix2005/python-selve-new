from __future__ import annotations

from selve.util import *

class CommeoCommand(GatewayCommand):
    def __init__(self, id: int | dict, driveComm: DriveCommandType, type: DeviceCommandTypes, param: int, isGroupCmd: bool = False):
        if not isGroupCmd:
            comm = CommandType.COMMAND.DEVICE
        else:
            if isinstance(id, dict):
                idB64 = Util.multimask(id)
                super().__init__(CommandType.COMMAND.DEVICE, [(ParameterType.BASE64, idB64), (ParameterType.STRING, driveComm), (ParameterType.INT, type.value), (ParameterType.INT, param)])
            else:
                comm = CommandType.COMMAND.GROUP
        super().__init__(comm, [(ParameterType.INT, id), (ParameterType.STRING, driveComm), (ParameterType.INT, type.value), (ParameterType.INT, param)])

class CommandStopSingle(CommeoCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.STOP, type, param, False)

class CommandDriveUp(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.DRIVEUP, type, param, False)

class CommandDriveDown(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.DRIVEDOWN, type, param, False)

class CommandDrivePos1(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.DRIVEPOS1, type, param, False)

class CommandSavePos1(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.SAVEPOS1, type, param, False)

class CommandDrivePos2(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.DRIVEPOS2, type, param, False)

class CommandSavePos2(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.SAVEPOS2, type, param, False)

class CommandDrivePos(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.DRIVEPOS, type, param, False)

class CommandStepUp(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.STEPUP, type, param, False)

class CommandStepDown(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.STEPDOWN, type, param, False)

class CommandAutoOn(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.AUTOON, type, param, False)

class CommandAutoOff(GatewayCommand):
    def __init__(self, id: int | dict, type: DeviceCommandTypes, param: int, groupcmd: bool):
        super().__init__(id, DriveCommandType.AUTOOFF, type, param, False)
