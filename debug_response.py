#!/usr/bin/env python3

from unittest.mock import Mock, patch
from selve import Selve
from selve.util import CommeoServiceCommand, CommeoParamCommand

# Test what happens when we create a response
selve = Selve(logger=Mock())

print("=== Testing ServiceGetVersionResponse ===")
mock_array = Mock()
mock_array.string = [Mock() for _ in range(7)]
mock_array.string[0].cdata = "12345"
mock_array.string[1].cdata = "1"
mock_array.string[2].cdata = "0"
mock_array.string[3].cdata = "0"
mock_array.string[4].cdata = "2"
mock_array.string[5].cdata = "1"
mock_array.string[6].cdata = "100"

# Mock hasattr properly to only return True for 'string'
def mock_hasattr_func(obj, attr):
    return attr == 'string'

try:
    with patch('builtins.hasattr', side_effect=mock_hasattr_func):
        response = selve._create_response(mock_array, "selve.GW." + str(CommeoServiceCommand.GETVERSION.value))
        print(f"Response created: {response}")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {[a for a in dir(response) if not a.startswith('_')]}")
        if hasattr(response, 'serial'):
            print(f"Serial: {response.serial}")
        if hasattr(response, 'version'):
            print(f"Version: {response.version}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n=== Testing ParamGetForwardResponse ===")
mock_array2 = Mock()
mock_array2.string = [Mock()]
mock_array2.string[0].cdata = "1"  # forwarding value

try:
    with patch('builtins.hasattr', side_effect=mock_hasattr_func):
        response2 = selve._create_response(mock_array2, "selve.GW." + str(CommeoParamCommand.GETFORWARD.value))
        print(f"Response created: {response2}")
        print(f"Response type: {type(response2)}")
        print(f"Response attributes: {[a for a in dir(response2) if not a.startswith('_')]}")
        if hasattr(response2, 'forwarding'):
            print(f"Forwarding: {response2.forwarding}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
