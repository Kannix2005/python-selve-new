from selve.util import *
        
class GroupRead(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.READ)
        
class GroupWrite(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.WRITE)
        
class GroupGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.GETIDS)
        
class GroupDelete(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.DELETE)
        
class CommandDevice(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoCommandCommand.DEVICE)
        
class CommandGroup(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoCommandCommand.GROUP)
        
class CommandGroupman(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoCommandCommand.GROUPMAN)
        
class CommandResult(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoCommandCommand.RESULT)