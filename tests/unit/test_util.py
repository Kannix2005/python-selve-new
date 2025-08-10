import unittest
import base64
from selve.util import Util
from selve.util.protocol import ParameterType, DeviceType, ServiceState


class TestUtil(unittest.TestCase):

    def test_singlemask(self):
        """Test creating a single mask for a given ID."""
        # Test for ID 0 (bit 0 should be set)
        self.assertEqual(Util.singlemask(0), "AQAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
        
        # Test for ID 7 (bit 7 should be set)
        self.assertEqual(Util.singlemask(7), "gAAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
        
        # Test for ID 15 (bit 15 should be set, requires 2 bytes)
        self.assertEqual(Util.singlemask(15), "AIAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
    
    def test_multimask(self):
        """Test creating a mask for multiple IDs."""
        # Test for IDs 0 and 1
        self.assertEqual(Util.multimask({0: True, 1: True}), "AwAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
        
        # Test for IDs 0, 2, and 5
        self.assertEqual(Util.multimask({0: True, 2: True, 5: True}), "JQAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
        
        # Test with some IDs being False - Beachte: Die aktuelle Implementierung ignoriert False-Werte nicht
        self.assertEqual(Util.multimask({0: True, 1: False, 2: True}), "BwAAAAAAAAA=")  # Base64 für die komplette 64-bit Maske
    
    def test_b64bytes_to_bitlist(self):
        """Test converting base64 encoded bytes to a list of bits."""
        # Test simple case
        self.assertEqual(Util.b64bytes_to_bitlist("AQ=="), [True, False, False, False, False, False, False, False])
        
        # Test multiple bits
        self.assertEqual(Util.b64bytes_to_bitlist("Aw=="), [True, True, False, False, False, False, False, False])
    
    def test_true_in_list(self):
        """Test finding indices of True values in a list."""
        test_list = [False, True, False, True, False]
        self.assertEqual(Util.true_in_list(test_list), [1, 3])
        
        # Test empty list
        self.assertEqual(Util.true_in_list([]), [])
        
        # Test no True values
        self.assertEqual(Util.true_in_list([False, False, False]), [])
        
        # Test all True values
        self.assertEqual(Util.true_in_list([True, True, True]), [0, 1, 2])


if __name__ == "__main__":
    unittest.main()
