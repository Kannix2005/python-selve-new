from selve import SelveTypes, Util, DeviceType, CommunicationType, MovementState, DayMode, \
    DeviceGetIdsResponse, DeviceGetInfoResponse, DeviceGetInfo, DeviceGetValuesResponse, DeviceGetValues


class SelveDevice:
    def __init__(self, id: int, device_type: SelveTypes = SelveTypes.UNKNOWN,
                 device_sub_type: DeviceType = DeviceType.UNKNOWN):
        self.id = id
        self.device_type = device_type
        self.device_sub_type = device_sub_type
        self.mask = Util.singlemask(id)
        self.name = "None"
        self.rfAdress = 0
        self.communicationType = CommunicationType.COMMEO
        self.state = MovementState.UNKOWN
        self.infoState = 0
        self.value = 0
        self.targetValue = 0
        self.unreachable = False
        self.overload = False
        self.obstructed = False
        self.alarm = False
        self.lostSensor = False
        self.automaticMode = False
        self.gatewayNotLearned = False
        self.windAlarm = False
        self.rainAlarm = False
        self.freezingAlarm = False
        self.dayMode = DayMode.UNKOWN


    def __str__(self):
        return "Device " + self.device_type.name + " " + self.device_sub_type.name + " of type: " + self.communicationType.name + " on channel " + str(
            self.id) + " with name " + self.name





