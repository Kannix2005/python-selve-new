from selve.util import *



class ServicePing(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.PING)

class ServiceGetState(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.GETSTATE)

class ServiceGetVersion(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.GETVERSION)

class ServiceReset(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.RESET)

class ServiceFactoryReset(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.FACTORYRESET)

class ServiceSetLed(GatewayCommand):
    def __init__(self, on: bool):
        super().__init__(CommandType.CommeoServiceCommand.SETLED, [(ParameterType.INT, 1 if on else 0)])

class ServiceGetLed(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoServiceCommand.GETLED)
