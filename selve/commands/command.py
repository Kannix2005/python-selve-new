from __future__ import annotations

from selve.util import *

class CommeoCommand(GatewayCommand):
    def __init__(self, id: int | dict, driveComm: DriveCommandCommeo, type: DeviceCommandType, param: int = 0, isGroupCmd: bool = False):
        if not isGroupCmd:
            comm = CommeoCommandCommand.DEVICE
        else:
            comm = CommeoCommandCommand.GROUP
        super().__init__(comm, [(ParameterType.INT, id), (ParameterType.INT, driveComm.value),
                                (ParameterType.INT, type.value), (ParameterType.INT, param)])

class CommandStop(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STOP, type, param, False)

class CommandDriveUp(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEUP, type, param, False)

class CommandDriveDown(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEDOWN, type, param, False)

class CommandDrivePos1(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS1, type, param, False)

class CommandSavePos1(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.SAVEPOS1, type, param, False)

class CommandDrivePos2(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS2, type, param, False)

class CommandSavePos2(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.SAVEPOS2, type, param, False)

class CommandDrivePos(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS, type, param, False)

class CommandDriveStepUp(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STEPUP, type, param, False)

class CommandDriveStepDown(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STEPDOWN, type, param, False)

class CommandDriveAutoOn(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.AUTOON, type, param, False)

class CommandDriveAutoOff(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.AUTOOFF, type, param, False)


class CommandStopGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STOP, type, param, True)

class CommandDriveUpGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEUP, type, param, True)

class CommandDriveDownGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEDOWN, type, param, True)

class CommandDrivePos1Group(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS1, type, param, True)

class CommandSavePos1Group(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.SAVEPOS1, type, param, True)

class CommandDrivePos2Group(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS2, type, param, True)

class CommandSavePos2Group(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.SAVEPOS2, type, param, True)

class CommandDrivePosGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.DRIVEPOS, type, param, True)

class CommandStepUpGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STEPUP, type, param, True)

class CommandStepDownGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.STEPDOWN, type, param, True)

class CommandAutoOnGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.AUTOON, type, param, True)

class CommandAutoOffGroup(CommeoCommand):
    def __init__(self, id: int, type: DeviceCommandType, param: int = 0):
        super().__init__(id, DriveCommandCommeo.AUTOOFF, type, param, True)



class CommandGroupMan(GatewayCommand):
    def __init__(self, command, type: DeviceCommandType, ids: dict, param: int = 0):
        super().__init__(CommeoCommandCommand.GROUPMAN, [(ParameterType.INT, command.value), (ParameterType.INT, type.value), (ParameterType.BASE64, Util.multimask(ids)), (ParameterType.INT, param)])



class CommandDeviceResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class CommandGroupResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])

class CommandGroupManResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
        self.ids = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[1][1]))]


class CommandResultResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.command = DriveCommandCommeo(int(parameters[0][1]))
        self.commandType = DeviceCommandType(int(parameters[1][1]))
        self.executed = bool(parameters[2][1])
        self.successIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[3][1]))]
        self.failedIds = [ b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[4][1]))]