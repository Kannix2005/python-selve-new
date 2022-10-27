from selve import MovementState, CommunicationType, Util, DeviceType, SelveTypes


class IveoDevice:
    def __init__(self, id: int, device_type: SelveTypes = SelveTypes.IVEO,
                 device_sub_type: DeviceType = DeviceType.UNKNOWN):
        self.id = id
        self.device_type = device_type
        self.device_sub_type = device_sub_type
        self.mask = Util.singlemask(id)
        self.name = "None"
        self.rfAdress = 0
        self.communicationType = CommunicationType.IVEO
        self.state = MovementState.UNKOWN
        self.activity = 0
        self.value = 0
        self.targetValue = 0


    def __str__(self):
        return "Device " + self.device_type.name + " of type: " + self.communicationType.name + " on channel " + str(
            self.id) + " with name " + self.name


