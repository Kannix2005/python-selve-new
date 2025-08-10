import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Import the Selve package
import selve
from selve.commands.sensor import *
from selve.util.protocol import ParameterType, TeachState, SensorState
from selve.util import Util


class TestSelveSensorCommandsExtended(unittest.TestCase):
    """Extended tests to improve coverage for sensor command classes."""
    
    def test_sensor_tech_start_command(self):
        """Test SensorTechStart command creation."""
        cmd = SensorTechStart()
        self.assertIsNotNone(cmd)

    def test_sensor_teach_stop_command(self):
        """Test SensorTeachStop command creation."""
        cmd = SensorTeachStop()
        self.assertIsNotNone(cmd)

    def test_sensor_teach_result_command(self):
        """Test SensorTeachResult command creation."""
        cmd = SensorTeachResult()
        self.assertIsNotNone(cmd)

    def test_sensor_get_info_command(self):
        """Test SensorGetInfo command creation."""
        cmd = SensorGetInfo(1)
        self.assertIsNotNone(cmd)

    def test_sensor_delete_command(self):
        """Test SensorDelete command creation."""
        cmd = SensorDelete(1)
        self.assertIsNotNone(cmd)

    def test_sensor_write_manual_command(self):
        """Test SensorWriteManual command creation."""
        cmd = SensorWriteManual(1, 12345, "Manual Sensor")
        self.assertIsNotNone(cmd)

    def test_sensor_teach_start_response(self):
        """Test SensorTeachStartResponse creation and properties."""
        # Test with executed = True
        response = SensorTeachStartResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SensorTeachStartResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensor_teach_stop_response(self):
        """Test SensorTeachStopResponse creation and properties."""
        # Test with executed = True
        response = SensorTeachStopResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SensorTeachStopResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensor_teach_result_response(self):
        """Test SensorTeachResultResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 1),    # teachState
            (ParameterType.INT, 30),   # timeLeft
            (ParameterType.INT, 123),  # foundId
        ]
        response = SensorTeachResultResponse("test", parameters)
        self.assertEqual(response.teachState, TeachState.RUN)
        self.assertEqual(response.timeLeft, 30)
        self.assertEqual(response.foundId, 123)

    def test_sensor_get_ids_response(self):
        """Test SensorGetIdsResponse creation and properties."""
        response = SensorGetIdsResponse("test", [(ParameterType.STRING, "AQIDBA==")])
        self.assertIsInstance(response.ids, list)

    def test_sensor_get_info_response(self):
        """Test SensorGetInfoResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test Sensor"),  # name
            (ParameterType.INT, 1),                 # unused
            (ParameterType.INT, 12345),             # rfAddress
        ]
        response = SensorGetInfoResponse("test", parameters)
        self.assertEqual(response.name, "Test Sensor")
        self.assertEqual(response.rfAddress, 12345)

    def test_sensor_get_values_response(self):
        """Test SensorGetValuesResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test"),  # name/unused
            (ParameterType.INT, 1),          # windDigital
            (ParameterType.INT, 0),          # rainDigital
            (ParameterType.INT, 1),          # tempDigital
            (ParameterType.INT, 0),          # lightDigital
            (ParameterType.INT, 2),          # sensorState
            (ParameterType.INT, 25),         # tempAnalog
            (ParameterType.INT, 10),         # windAnalog
            (ParameterType.INT, 800),        # sun1Analog
            (ParameterType.INT, 1200),       # dayLightAnalog
            (ParameterType.INT, 900),        # sun2Analog
            (ParameterType.INT, 700),        # sun3Analog
        ]
        response = SensorGetValuesResponse("test", parameters)
        self.assertEqual(response.sensorState, SensorState.LOW_BATTERY)
        self.assertEqual(response.tempAnalog, 25)
        self.assertEqual(response.windAnalog, 10)
        self.assertEqual(response.sun1Analog, 800)
        self.assertEqual(response.dayLightAnalog, 1200)
        self.assertEqual(response.sun2Analog, 900)
        self.assertEqual(response.sun3Analog, 700)

    def test_sensor_set_label_response(self):
        """Test SensorSetLabelResponse creation and properties."""
        # Test with executed = True
        response = SensorSetLabelResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SensorSetLabelResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensor_delete_response(self):
        """Test SensorDeleteResponse creation and properties."""
        # Test with executed = True
        response = SensorDeleteResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SensorDeleteResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensor_write_manual_response(self):
        """Test SensorWriteManualResponse creation and properties."""
        # Test with executed = True
        response = SensorWriteManualResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SensorWriteManualResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)


if __name__ == "__main__":
    unittest.main()
