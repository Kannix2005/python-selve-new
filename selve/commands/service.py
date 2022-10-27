from selve.util import *


class ServicePing(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.PING)


class ServiceGetState(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.GETSTATE)


class ServiceGetVersion(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.GETVERSION)


class ServiceReset(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.RESET)


class ServiceFactoryReset(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.FACTORYRESET)


class ServiceSetLed(GatewayCommand):
    def __init__(self, on: bool):
        super().__init__(CommeoServiceCommand.SETLED, [(ParameterType.INT, 1 if on else 0)])


class ServiceGetLed(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoServiceCommand.GETLED)


class ServicePingResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)


class ServiceGetStateResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.state = parameters[0][1]


class ServiceGetVersionResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.serial = str(parameters[0][1])
        self.version = int(parameters[1][1]) + "." + int(parameters[2][1]) + "." + int(parameters[3][1]) + "." + int(
            parameters[6][1])
        self.spec = int(parameters[4][1]) + "." + int(parameters[5][1])


class ServiceResetResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class ServiceFactoryResetResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class ServiceSetLedResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class ServiceGetLedResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ledmode = LEDMode(int(parameters[0][1]))
