from selve.util import *

class CommandStop(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.STOP)

class CommandDriveUp(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.DRIVEUP)

class CommandDriveDown(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.DRIVEDOWN)

class CommandDrivePos1(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.DRIVEPOS1)

class CommandSavePos1(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.SAVEPOS1)

class CommandDrivePos2(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.DRIVEPOS2)

class CommandSavePos2(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.SAVEPOS2)

class CommandDrivePos(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.DRIVEPOS)

class CommandStepUp(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.STEPUP)

class CommandStepDown(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.STEPDOWN)

class CommandAutoOn(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.AUTOON)

class CommandAutoOff(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.DriveCommandType.AUTOOFF)