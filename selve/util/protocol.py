import logging
from enum import Enum

_LOGGER = logging.getLogger(__name__)
class DeviceType(Enum):
    UNKNOWN = 0
    SHUTTER = 1
    BLIND = 2
    AWNING = 3
    SWITCH = 4
    DIMMER = 5
    NIGHT_LIGHT = 6
    DRAWN_LIGHT = 7
    HEATING = 8
    COOLING = 9
    SWITCHDAY = 10
    GATEWAY = 11

class SelveTypes(Enum):
    SERVICE = "service"
    PARAM = "param"
    DEVICE = "device"
    SENSOR = "sensor"
    SENSIM = "senSim"
    SENDER = "sender"
    GROUP = "group"
    COMMAND = "command"
    EVENT = "event"
    IVEO = "iveo"
    COMMEO = "commeo"
    FIRMWARE = "firmware"
    UNKNOWN = "unknown"

class DeviceState(Enum):
    UNUSED = 0
    USED = 1
    TEMPORARY = 2
    STALLED = 3

class MovementState(Enum):
    UNKOWN = 0
    STOPPED_OFF = 1
    UP_ON = 2
    DOWN_ON = 3

class CommunicationType(Enum):
    COMMEO = 0
    IVEO = 1
    UNKNOWN = 99

class SenSimCommandType(Enum):
    STOP = 0
    DRIVEUP = 1
    DRIVEDOWN = 2
    POSITION_1 = 3
    POSITION_2 = 4

class DriveCommandCommeo(Enum):
    STOP = 0
    DRIVEUP = 1
    DRIVEDOWN = 2
    DRIVEPOS1 = 3
    SAVEPOS1 = 4
    DRIVEPOS2 = 5
    SAVEPOS2 = 6
    DRIVEPOS = 7
    STEPUP = 8
    STEPDOWN = 9 
    AUTOON = 10
    AUTOOFF = 11

class DeviceCommandType(Enum):
    FORCED = 0
    MANUAL = 1
    TIME = 2
    GLASS = 3

class DriveCommandIveo(Enum):
    STOP = 0
    UP = 1
    DOWN = 2
    POS1 = 3
    POS2 = 5
    LEARNTELEGRAMSENT = 254
    TEACHTELEGRAMSENT = 255

class ParameterType(Enum):
    INT = "int"
    STRING = "string"
    BASE64 = "base64"

class ScanState(Enum):
    IDLE = 0
    RUN = 1
    VERIFY = 2
    END_SUCCESS = 3
    END_FAILED = 4

class TeachState(Enum):
    IDLE = 0
    RUN = 1
    END_SUCCESS = 2

class CommandResultState(Enum):
    IDLE = 0
    SEND = 1

class ServiceState(Enum):
    BOOTLOADER = 0
    UPDATE = 1
    STARTUP = 2
    READY = 3

class SensorState(Enum):
    INVALID = 0
    AVAILABLE = 1
    LOW_BATTERY = 2
    COMMUNICATION_LOSS = 3
    TESTMODE = 4
    SERVICEMODE = 5

class RepeaterState(Enum):
    NONE = 0
    SINGLEREPEAT = 1
    MULTIREPEAT = 2

class LEDMode(Enum):
    OFF = 0
    ON = 1

class Forwarding(Enum):
    OFF = 0
    ON = 1

class DutyMode(Enum):
    NOT_BLOCKED = 0
    BLOCKED = 1

class DayMode(Enum):
    UNKOWN = 0
    NIGHTMODE = 1
    DAWNING = 2
    DAY = 3
    DUSK = 4

class DeviceFunctions(Enum):
    SELECT = 0
    INSTALL = 1
    SENSOR = 2
    MANPROG = 3
    AUTOPROG = 4
    STOREPOSITION = 5
    DRIVEUP = 6
    DRIVEDOWN = 7
    KEYRELEASE = 8
    DRIVESTOP = 9

class LogType(Enum):
    INFO = 0
    WARNING = 1
    ERROR = 2

class DeviceClass(Enum):
    ACTOR = 0
    GROUP = 1
    SENDER = 2
    SENSIM = 3
    SENSOR = 4
    IVEO = 5
    UNKOWN = 99

## SensorVariables ##

class windDigital(Enum):
    NONE = 0
    NO_ALARM = 1
    ALARM = 2

class rainDigital(Enum):
    NONE = 0
    NO_ALARM = 1
    ALARM = 2

class tempDigital(Enum):
    NONE = 0
    NORMAL = 1
    FREEZING = 2
    HEAT = 3

class lightDigital(Enum):
    NONE = 0
    DARK = 1
    DAWN = 2
    NORMAL = 3
    LIGHT = 4

## senderEvents ##

class senderEvents(Enum):
    UNKNOWN = 0
    DRIVEUP = 1
    DRIVEDOWN = 2
    STOP = 3
    POS1 = 4
    POS2 = 5
    SAVEPOS1 = 6
    SAVEPOS2 = 7
    AUTO = 8
    MAN = 9
    NAME = 10
    KEYRELEASE = 11
    SELECT = 12
    DELETE = 13


