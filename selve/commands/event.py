from selve.util import *
        
class EventDevice(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoEventCommand.DEVICE)
        
class EventSensor(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoEventCommand.SENSOR)
        
class EventSender(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoEventCommand.SENDER)
        
class EventLog(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoEventCommand.LOG)
        
class EventDutyCycle(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoEventCommand.DUTYCYCLE)