import unittest
from unittest.mock import MagicMock, patch
from selve.device import SelveDevice
from selve.util.protocol import SelveTypes, DeviceType, MovementState, CommunicationType, DayMode


class TestSelveDevice(unittest.TestCase):

    def setUp(self):
        """Set up test cases."""
        self.device = SelveDevice(id=1, device_type=SelveTypes.DEVICE, device_sub_type=DeviceType.SHUTTER)

    def test_device_initialization(self):
        """Test if a device is correctly initialized with the given values."""
        self.assertEqual(self.device.id, 1)
        self.assertEqual(self.device.device_type, SelveTypes.DEVICE)
        self.assertEqual(self.device.device_sub_type, DeviceType.SHUTTER)
        self.assertEqual(self.device.communicationType, CommunicationType.COMMEO)
        self.assertEqual(self.device.state, MovementState.UNKOWN)
        self.assertEqual(self.device.name, "None")
    
    def test_default_values(self):
        """Test if default values are correctly set."""
        self.assertEqual(self.device.value, 0)
        self.assertEqual(self.device.targetValue, 0)
        self.assertFalse(self.device.unreachable)
        self.assertFalse(self.device.overload)
        self.assertFalse(self.device.obstructed)
        self.assertFalse(self.device.alarm)
        self.assertFalse(self.device.lostSensor)
        self.assertFalse(self.device.automaticMode)
        self.assertFalse(self.device.gatewayNotLearned)
        self.assertFalse(self.device.windAlarm)
        self.assertFalse(self.device.rainAlarm)
        self.assertFalse(self.device.freezingAlarm)
        self.assertEqual(self.device.dayMode, DayMode.UNKOWN)

    def test_str_representation(self):
        """Test the string representation of a device."""
        expected = "Device DEVICE SHUTTER of type: COMMEO on channel 1 with name None"
        self.assertEqual(str(self.device), expected)
    
    def test_mask_generation(self):
        """Test if the mask is correctly generated for the device ID."""
        # Device with ID 1 should have mask with bit 1 set
        self.assertEqual(self.device.mask, "AgAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske


if __name__ == "__main__":
    unittest.main()
