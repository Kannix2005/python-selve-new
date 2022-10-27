from selve import SelveTypes, DeviceType, Util, CommunicationType


class SelveSender:
    def __init__(self, id: int, device_type: SelveTypes = SelveTypes.SENDER,
                 device_sub_type: DeviceType = DeviceType.UNKNOWN):
        self.id = id
        self.rfAddress = ""
        self.channel = 0
        self.resetCount = 0
        self.device_type = device_type
        self.device_sub_type = device_sub_type
        self.mask = Util.singlemask(id)
        self.name = "None"
        self.communicationType = CommunicationType.COMMEO
        self.lastEvent = None