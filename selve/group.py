from selve.util import *
        
class GroupRead(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommandType.CommeoGroupCommand.READ, [(ParameterType.INT, id)])
        
class GroupWrite(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.WRITE, [(ParameterType.INT, id)])
        
class GroupGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.GETIDS)
        
class GroupDelete(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.CommeoGroupCommand.DELETE)