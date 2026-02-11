from selve.util import *


class FirmwareGetVersion(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoFirmwareCommand.GETVERSION)


class FirmwareUpdate(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoFirmwareCommand.UPDATE)


class FirmwareGetVersionResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.version = str(parameters[0][1]) if len(parameters) > 0 else "unknown"
        self.state = str(parameters[1][1]) if len(parameters) > 1 else "unknown"


class FirmwareUpdateResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
