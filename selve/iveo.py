from selve.util import *
        
class IveoFactory(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.FACTORY)
        
class IveoSetConfig(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.SETCONFIG)
        
class IveoGetConfig(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.GETCONFIG)
        
class IveoGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.GETIDS)
        
class IveoSetRepeater(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.SETREPEATER)
        
class IveoGetRepeater(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.GETREPEATER)
        
class IveoSetLabel(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.SETLABEL)
        
class IveoTeach(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.TEACH)
        
class IveoLearn(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.LEARN)
        
class IveoManual(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.MANUAL)
        
class IveoAutomatic(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.AUTOMATIC)
        
class IveoResult(GatewayCommand):
    def __init__(self):
        super().__init__(CommandType.IveoCommand.RESULT)