from selve import SelveTypes, DeviceType, Util, CommunicationType


class SelveGroup:
    def __init__(self, id: int, device_type: SelveTypes = SelveTypes.GROUP,
                 device_sub_type: DeviceType = DeviceType.UNKNOWN):
        self.id = id
        self.rfAddress = ""
        self.device_type = device_type
        self.device_sub_type = device_sub_type
        self.mask = None
        self.name = "None"
        self.communicationType = CommunicationType.COMMEO