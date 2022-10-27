from enum import Enum
from typing import Dict


class GatewayError(Exception):
    pass

class PortError(Exception):
    pass
class CommunicationError(Exception):
    pass
class ReadTimeoutError(Exception):
    pass


ErrorCodes = {
    1: "Unknown Error",
    2: "Method not supported",
    3: "Method not reachable",
    4: "Parameter count",
    5: "Parameter order",
    6: "Execution failed",
    7: "Parameter out of range",
    8: "Syntax error",
    9: "Method length too large",
    10: "ID is not used",
    11: "ID already exists",
    12: "Address is already used",
    13: "No member available",
    14: "Duty Cycle is reached",
    40: "Bootl: Method not supported",
    41: "Bootl: Wrong file",
    42: "Bootl: Checksum error",
    43: "Bootl: Syntax error"
}

