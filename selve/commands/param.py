from selve.util import *


class ParamSetForward(GatewayCommand):
    def __init__(self, on: bool):
        super().__init__(CommeoParamCommand.SETFORWARD, [(ParameterType.INT, 1 if on else 0)])


class ParamGetForward(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoParamCommand.GETFORWARD)


class ParamSetEvent(GatewayCommand):
    def __init__(self, EventDevice: bool, EventSensor: bool, EventSender: bool, Logging: bool, EventDuty: bool):
        super().__init__(CommeoParamCommand.SETEVENT,
                         [(ParameterType.INT, EventDevice), (ParameterType.INT, EventSensor),
                          (ParameterType.INT, EventSender), (ParameterType.INT, Logging),
                          (ParameterType.INT, EventDuty)])


class ParamGetEvent(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoParamCommand.GETEVENT)


class ParamGetDuty(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoParamCommand.GETDUTY)


class ParamGetRf(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoParamCommand.GETRF)


class ParamSetForwardResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class ParamGetForwardResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.forwarding = Forwarding(int(parameters[0][1]))


class ParamSetEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class ParamGetEventResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.eventDevice = bool(parameters[0][1])
        self.eventSensor = bool(parameters[1][1])
        self.eventSender = bool(parameters[2][1])
        self.eventLogging = bool(parameters[3][1])
        self.eventDuty = bool(parameters[4][1])


class ParamGetDutyResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.dutyMode = DutyMode(int(parameters[0][1]))
        self.rfTraffic = int(parameters[1][1])


class ParamGetRfResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.netAddress = int(parameters[0][1])
        self.resetCount = int(parameters[1][1])
        self.rfBaseId = int(parameters[2][1])
        self.sensorNetAddress = int(parameters[3][1])
        self.rfSensorId = int(parameters[4][1])
        self.iveoResetCount = int(parameters[5][1])
        self.rfIveoId = int(parameters[6][1])
