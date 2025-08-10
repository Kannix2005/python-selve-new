import unittest
from unittest.mock import MagicMock, patch
from selve.group import SelveGroup
from selve.util.protocol import SelveTypes, DeviceType, CommunicationType


class TestSelveGroup(unittest.TestCase):

    def setUp(self):
        """Set up test cases."""
        self.group = SelveGroup(id=5, device_type=SelveTypes.GROUP, device_sub_type=DeviceType.SHUTTER)

    def test_group_initialization(self):
        """Test if a group is correctly initialized with the given values."""
        self.assertEqual(self.group.id, 5)
        self.assertEqual(self.group.device_type, SelveTypes.GROUP)
        self.assertEqual(self.group.device_sub_type, DeviceType.SHUTTER)
        self.assertEqual(self.group.communicationType, CommunicationType.COMMEO)
        self.assertEqual(self.group.name, "None")
        self.assertEqual(self.group.rfAddress, "")
        self.assertIsNone(self.group.mask)

    def test_str_representation(self):
        """Test the string representation of a group."""
        expected = "Group GROUP of type: COMMEO on channel 5 with name None"
        self.assertEqual(str(self.group), expected)


if __name__ == "__main__":
    unittest.main()
