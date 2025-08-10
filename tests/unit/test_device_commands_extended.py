import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Import the Selve package
import selve
from selve.commands.device import *
from selve.util.protocol import ParameterType, DeviceType, DeviceFunctions, ScanState, DeviceState, MovementState, DayMode
from selve.util import Util


class TestSelveDeviceCommandsExtended(unittest.TestCase):
    """Extended tests to improve coverage for device command classes."""
    
    def test_device_scan_result_command(self):
        """Test DeviceScanResult command creation."""
        cmd = DeviceScanResult()
        self.assertIsNotNone(cmd)

    def test_device_write_manual_command(self):
        """Test DeviceWriteManual command creation."""
        cmd = DeviceWriteManual(1, 12345, "Manual Device", DeviceType.SHUTTER)
        self.assertIsNotNone(cmd)

    def test_device_scan_start_response(self):
        """Test DeviceScanStartResponse creation and properties."""
        # Test with executed = True
        response = DeviceScanStartResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceScanStartResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_scan_stop_response(self):
        """Test DeviceScanStopResponse creation and properties."""
        # Test with executed = True
        response = DeviceScanStopResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceScanStopResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_scan_result_response(self):
        """Test DeviceScanResultResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 1),  # scanState
            (ParameterType.INT, 2),  # noNewDevices
            (ParameterType.STRING, "AQIDBA=="),  # foundIds (base64)
        ]
        response = DeviceScanResultResponse("test", parameters)
        self.assertEqual(response.scanState, ScanState.RUN)
        self.assertEqual(response.noNewDevices, 2)
        self.assertIsInstance(response.foundIds, list)

    def test_device_save_response(self):
        """Test DeviceSaveResponse creation and properties."""
        # Test with executed = True
        response = DeviceSaveResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceSaveResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_get_ids_response(self):
        """Test DeviceGetIdsResponse creation and properties."""
        response = DeviceGetIdsResponse("test", [(ParameterType.STRING, "AQIDBA==")])
        self.assertIsInstance(response.ids, list)

    def test_device_get_info_response(self):
        """Test DeviceGetInfoResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test Device"),  # name
            (ParameterType.INT, 1),                 # unused
            (ParameterType.INT, 12345),             # rfAddress
            (ParameterType.INT, 1),                 # deviceType
            (ParameterType.INT, 2),                 # state
        ]
        response = DeviceGetInfoResponse("test", parameters)
        self.assertEqual(response.name, "Test Device")
        self.assertEqual(response.rfAddress, 12345)
        self.assertEqual(response.deviceType, DeviceType.SHUTTER)
        self.assertEqual(response.state, DeviceState.TEMPORARY)
        
        # Test with empty name
        parameters[0] = (ParameterType.STRING, "")
        response = DeviceGetInfoResponse("test", parameters)
        self.assertEqual(response.name, "None")
        
        # Test with zero device type
        parameters[3] = (ParameterType.INT, 0)
        response = DeviceGetInfoResponse("test", parameters)
        self.assertEqual(response.deviceType, DeviceType(0))

    def test_device_get_values_response(self):
        """Test DeviceGetValuesResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test Device"),  # name
            (ParameterType.INT, 1),                 # unused
            (ParameterType.INT, 1),                 # movementState
            (ParameterType.INT, 32768),             # value (50% of 65535)
            (ParameterType.INT, 65535),             # targetValue (100% of 65535)
            (ParameterType.INT, 0b1010101010),      # flags
            (ParameterType.INT, 1),                 # dayMode
        ]
        response = DeviceGetValuesResponse("test", parameters)
        self.assertEqual(response.name, "Test Device")
        self.assertEqual(response.movementState, MovementState.STOPPED_OFF)
        self.assertAlmostEqual(response.value, 50.0, places=1)
        self.assertAlmostEqual(response.targetValue, 100.0, places=1)
        self.assertEqual(response.dayMode, DayMode.NIGHTMODE)
        
        # Test boolean flags
        self.assertIsInstance(response.unreachable, bool)
        self.assertIsInstance(response.overload, bool)
        self.assertIsInstance(response.obstructed, bool)
        self.assertIsInstance(response.alarm, bool)
        self.assertIsInstance(response.lostSensor, bool)
        self.assertIsInstance(response.automaticMode, bool)
        self.assertIsInstance(response.gatewayNotLearned, bool)
        self.assertIsInstance(response.windAlarm, bool)
        self.assertIsInstance(response.rainAlarm, bool)
        self.assertIsInstance(response.freezingAlarm, bool)
        
        # Test with empty name
        parameters[0] = (ParameterType.STRING, "")
        response = DeviceGetValuesResponse("test", parameters)
        self.assertEqual(response.name, "")
        
        # Test with zero movement state
        parameters[2] = (ParameterType.INT, 0)
        response = DeviceGetValuesResponse("test", parameters)
        self.assertEqual(response.movementState, MovementState(0))

    def test_device_set_function_response(self):
        """Test DeviceSetFunctionResponse creation and properties."""
        # Test with executed = True
        response = DeviceSetFunctionResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceSetFunctionResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_set_label_response(self):
        """Test DeviceSetLabelResponse creation and properties."""
        # Test with executed = True
        response = DeviceSetLabelResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceSetLabelResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_set_type_response(self):
        """Test DeviceSetTypeResponse creation and properties."""
        # Test with executed = True
        response = DeviceSetTypeResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceSetTypeResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_delete_response(self):
        """Test DeviceDeleteResponse creation and properties."""
        # Test with executed = True
        response = DeviceDeleteResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceDeleteResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_device_write_manual_response(self):
        """Test DeviceWriteManualResponse creation and properties."""
        # Test with executed = True
        response = DeviceWriteManualResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = DeviceWriteManualResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)


if __name__ == "__main__":
    unittest.main()
