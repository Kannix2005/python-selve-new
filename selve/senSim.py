from selve import SelveTypes, DeviceType, Util, CommunicationType, windDigital, rainDigital, tempDigital, lightDigital, \
    SensorState


class SelveSenSim:
    def __init__(self, id: int, device_type: SelveTypes = SelveTypes.SENSIM,
                 device_sub_type: DeviceType = DeviceType.UNKNOWN):
        self.id = id
        self.device_type = device_type
        self.device_sub_type = device_sub_type
        self.mask = Util.singlemask(id)
        self.name = "SensorSim " + str(id)
        self.activity = ""
        self.communicationType = CommunicationType.COMMEO
        self.windDigital = windDigital.NONE
        self.rainDigital = rainDigital.NONE
        self.tempDigital = tempDigital.NONE
        self.lightDigital = lightDigital.NONE
        self.sensorState = SensorState.AVAILABLE
        self.tempAnalog = 0
        self.windAnalog = 0
        self.sun1Analog = 0
        self.dayLightAnalog = 0
        self.sun2Analog = 0
        self.sun3Analog = 0
    def __str__(self):
        return "Sensor " + self.device_type.name + " of type: " + self.communicationType.name + " on channel " + str(
            self.id) + " with name " + self.name
