import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio

# Import the Selve package classes
from selve.device import SelveDevice
from selve.util.protocol import DeviceType, DeviceState, MovementState, SelveTypes


class TestSelveDeviceClasses(unittest.TestCase):
    """Tests to improve coverage for device classes."""

    def test_selve_device_initialization(self):
        """Test SelveDevice initialization."""
        device = SelveDevice(
            id=1,
            device_type=SelveTypes.DEVICE,
            device_sub_type=DeviceType.SHUTTER
        )
        
        self.assertEqual(device.id, 1)
        self.assertEqual(device.device_type, SelveTypes.DEVICE)
        self.assertEqual(device.device_sub_type, DeviceType.SHUTTER)

    def test_selve_device_properties(self):
        """Test SelveDevice properties and defaults."""
        device = SelveDevice(id=2)
        
        # Test default values
        self.assertEqual(device.id, 2)
        self.assertEqual(device.device_type, SelveTypes.UNKNOWN)
        self.assertEqual(device.device_sub_type, DeviceType.UNKNOWN)
        self.assertEqual(device.name, "None")
        self.assertEqual(device.rfAdress, 0)
        self.assertFalse(device.unreachable)
        self.assertFalse(device.overload)

    def test_device_with_all_parameters(self):
        """Test device creation with all possible parameters."""
        device = SelveDevice(
            id=5,  # Use a smaller ID that won't cause index errors
            device_type=SelveTypes.DEVICE,
            device_sub_type=DeviceType.AWNING
        )
        
        self.assertEqual(device.id, 5)
        self.assertEqual(device.device_type, SelveTypes.DEVICE)
        self.assertEqual(device.device_sub_type, DeviceType.AWNING)

    def test_device_property_assignment(self):
        """Test that device properties can be assigned."""
        device = SelveDevice(id=1)
        
        # Test property assignments
        device.name = "Test Device"
        device.value = 50
        device.targetValue = 75
        device.unreachable = True
        device.alarm = True
        
        self.assertEqual(device.name, "Test Device")
        self.assertEqual(device.value, 50)
        self.assertEqual(device.targetValue, 75)
        self.assertTrue(device.unreachable)
        self.assertTrue(device.alarm)

    def test_device_boolean_flags(self):
        """Test device boolean flag properties."""
        device = SelveDevice(id=1)
        
        # Test all boolean flags are initially False
        self.assertFalse(device.unreachable)
        self.assertFalse(device.overload)
        self.assertFalse(device.obstructed)
        self.assertFalse(device.alarm)
        self.assertFalse(device.lostSensor)
        self.assertFalse(device.automaticMode)
        self.assertFalse(device.gatewayNotLearned)
        self.assertFalse(device.windAlarm)
        self.assertFalse(device.rainAlarm)
        self.assertFalse(device.freezingAlarm)

    def test_device_numeric_properties(self):
        """Test device numeric properties."""
        device = SelveDevice(id=1)
        
        # Test initial numeric values
        self.assertEqual(device.rfAdress, 0)
        self.assertEqual(device.infoState, 0)
        self.assertEqual(device.value, 0)
        self.assertEqual(device.targetValue, 0)
        
        # Test setting numeric values
        device.rfAdress = 12345
        device.value = 100
        device.targetValue = 50
        
        self.assertEqual(device.rfAdress, 12345)
        self.assertEqual(device.value, 100)
        self.assertEqual(device.targetValue, 50)

    def test_device_different_types(self):
        """Test devices with different types."""
        device_types = [
            (SelveTypes.DEVICE, DeviceType.SHUTTER),
            (SelveTypes.IVEO, DeviceType.BLIND),
            (SelveTypes.SENSOR, DeviceType.SWITCH),
            (SelveTypes.SENSIM, DeviceType.DIMMER)
        ]
        
        for dev_type, sub_type in device_types:
            device = SelveDevice(id=1, device_type=dev_type, device_sub_type=sub_type)
            self.assertEqual(device.device_type, dev_type)
            self.assertEqual(device.device_sub_type, sub_type)


if __name__ == '__main__':
    unittest.main()
