from enum import Enum
from typing import Dict


class GatewayError:
    pass


ErrorCodes = [
    "Unknown Error",
    "Method not supported",
    "Method not reachable",
    "Parameter count",
    "Parameter order",
    "Execution failed",
    "Parameter out of range",
    "Syntax error",
    "Method length too large",
    "ID is not used",
    "ID already exists",
    "Address is already used",
    "No member available",
    "Duty Cycle is reached"
]
ErrorCodes[40] = "Bootl: Method not supported"
ErrorCodes[41] = "Bootl: Wrong file"
ErrorCodes[42] = "Bootl: Checksum error"
ErrorCodes[43] = "Bootl: Syntax error"
