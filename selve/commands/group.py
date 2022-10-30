from selve.util import *


class GroupRead(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoGroupCommand.READ, [(ParameterType.INT, id)])


class GroupWrite(GatewayCommand):
    def __init__(self, id: int, actorIds: dict, name: str):
        super().__init__(CommeoGroupCommand.WRITE,
                         [(ParameterType.INT, id), (ParameterType.BASE64, Util.multimask(actorIds)),
                          (ParameterType.STRING, name)])


class GroupGetIds(GatewayCommand):
    def __init__(self):
        super().__init__(CommeoGroupCommand.GETIDS)


class GroupDelete(GatewayCommand):
    def __init__(self, id: int):
        super().__init__(CommeoGroupCommand.DELETE, [(ParameterType.INT, id)])


class GroupReadResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.id = int(parameters[1][1])
        self.mask = parameters[2][1]
        self.name = str(parameters[0][1])


class GroupWriteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])


class GroupGetIdsResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.ids = [b for b in Util.true_in_list(Util.b64bytes_to_bitlist(parameters[0][1]))]


class GroupDeleteResponse(MethodResponse):
    def __init__(self, name, parameters):
        super().__init__(name, parameters)
        self.executed = bool(parameters[0][1])
