import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Import the Selve package
import selve
from selve.commands.param import *
from selve.util.protocol import ParameterType, Forwarding, DutyMode


class TestSelveParamCommandsExtended(unittest.TestCase):
    """Extended tests to improve coverage for parameter command classes."""
    
    def test_param_set_forward_commands(self):
        """Test ParamSetForward command creation."""
        # Test with True
        cmd = ParamSetForward(True)
        self.assertIsNotNone(cmd)
        
        # Test with False
        cmd = ParamSetForward(False)
        self.assertIsNotNone(cmd)

    def test_param_get_forward_command(self):
        """Test ParamGetForward command creation."""
        cmd = ParamGetForward()
        self.assertIsNotNone(cmd)

    def test_param_get_event_command(self):
        """Test ParamGetEvent command creation."""
        cmd = ParamGetEvent()
        self.assertIsNotNone(cmd)

    def test_param_get_duty_command(self):
        """Test ParamGetDuty command creation."""
        cmd = ParamGetDuty()
        self.assertIsNotNone(cmd)

    def test_param_get_rf_command(self):
        """Test ParamGetRf command creation."""
        cmd = ParamGetRf()
        self.assertIsNotNone(cmd)

    def test_param_set_forward_response(self):
        """Test ParamSetForwardResponse creation and properties."""
        # Test with executed = True
        response = ParamSetForwardResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = ParamSetForwardResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_param_get_forward_response(self):
        """Test ParamGetForwardResponse creation and properties."""
        # Test with different forwarding values
        response = ParamGetForwardResponse("test", [(ParameterType.INT, 0)])
        self.assertEqual(response.forwarding, Forwarding.OFF)
        
        response = ParamGetForwardResponse("test", [(ParameterType.INT, 1)])
        self.assertEqual(response.forwarding, Forwarding.ON)

    def test_param_set_event_response(self):
        """Test ParamSetEventResponse creation and properties."""
        # Test with executed = True
        response = ParamSetEventResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = ParamSetEventResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_param_get_event_response(self):
        """Test ParamGetEventResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 1),  # eventDevice
            (ParameterType.INT, 0),  # eventSensor
            (ParameterType.INT, 1),  # eventSender
            (ParameterType.INT, 0),  # eventLogging
            (ParameterType.INT, 1),  # eventDuty
        ]
        response = ParamGetEventResponse("test", parameters)
        self.assertTrue(response.eventDevice)
        self.assertFalse(response.eventSensor)
        self.assertTrue(response.eventSender)
        self.assertFalse(response.eventLogging)
        self.assertTrue(response.eventDuty)

    def test_param_get_duty_response(self):
        """Test ParamGetDutyResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 0),  # dutyMode
            (ParameterType.INT, 123)  # rfTraffic
        ]
        response = ParamGetDutyResponse("test", parameters)
        self.assertEqual(response.dutyMode, DutyMode.NOT_BLOCKED)
        self.assertEqual(response.rfTraffic, 123)

    def test_param_get_rf_response(self):
        """Test ParamGetRfResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 1234),  # netAddress
            (ParameterType.INT, 5),     # resetCount
            (ParameterType.INT, 6789),  # rfBaseId
            (ParameterType.INT, 2345),  # sensorNetAddress
            (ParameterType.INT, 7890),  # rfSensorId
            (ParameterType.INT, 10),    # iveoResetCount
            (ParameterType.INT, 3456),  # rfIveoId
        ]
        response = ParamGetRfResponse("test", parameters)
        self.assertEqual(response.netAddress, 1234)
        self.assertEqual(response.resetCount, 5)
        self.assertEqual(response.rfBaseId, 6789)
        self.assertEqual(response.sensorNetAddress, 2345)
        self.assertEqual(response.rfSensorId, 7890)
        self.assertEqual(response.iveoResetCount, 10)
        self.assertEqual(response.rfIveoId, 3456)


if __name__ == "__main__":
    unittest.main()
