from selve.util import *

class ParamSetForward(GatewayCommand):
    def __init__(self, on: bool):
        super().__init__(CommandType.CommeoParamCommand.SETFORWARD, [(ParameterType.INT, 1 if on else 0)])
        
class ParamGetForward(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoParamCommand.GETFORWARD)
        
class ParamSetEvent(GatewayCommand):
    def __init__(self, EventDevice: bool, EventSensor: bool, EventSender: bool, Logging: bool, EventDuty: bool):
        super().__init__(CommandType.CommeoParamCommand.SETEVENT, [(ParameterType.INT, EventDevice), (ParameterType.INT, EventSensor), (ParameterType.INT, EventSender), (ParameterType.INT, Logging), (ParameterType.INT, EventDuty)])
        
class ParamGetEvent(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoParamCommand.GETEVENT)
        
class ParamGetDuty(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoParamCommand.GETDUTY)
        
class ParamGetRf(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoParamCommand.GETRF)
