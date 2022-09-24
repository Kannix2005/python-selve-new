from selve.util import *
        
class EventDevice(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoEventCommand.DEVICE)
        
class EventSensor(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoEventCommand.SENSOR)
        
class EventSender(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoEventCommand.SENDER)
        
class EventLog(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoEventCommand.LOG)
        
class EventDutyCycle(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoEventCommand.DUTYCYCLE)