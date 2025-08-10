import unittest
from unittest.mock import MagicMock, patch
from selve.commands.group import (
    GroupRead, GroupWrite, GroupGetIds, GroupDelete,
    GroupReadResponse, GroupWriteResponse, GroupGetIdsResponse, GroupDeleteResponse
)
from selve.util import Util
from selve.util.protocol import ParameterType


class TestGroupCommands(unittest.TestCase):

    def test_group_read_command(self):
        """Test creation of a group read command."""
        cmd = GroupRead(5)
        self.assertEqual(cmd.method_name, "selve.GW.group.read")
        self.assertEqual(len(cmd.parameters), 1)
        self.assertEqual(cmd.parameters[0][0], ParameterType.INT)
        self.assertEqual(cmd.parameters[0][1], 5)

    def test_group_write_command(self):
        """Test creation of a group write command."""
        # Create a group with devices 1, 3, and 5
        cmd = GroupWrite(2, {1: True, 3: True, 5: True}, "Test Group")
        self.assertEqual(cmd.method_name, "selve.GW.group.write")
        self.assertEqual(len(cmd.parameters), 3)
        self.assertEqual(cmd.parameters[0][0], ParameterType.INT)
        self.assertEqual(cmd.parameters[0][1], 2)  # Group ID
        self.assertEqual(cmd.parameters[1][0], ParameterType.BASE64)
        # The mask should include bits 1, 3, and 5
        self.assertEqual(cmd.parameters[1][1], Util.multimask({1: True, 3: True, 5: True}))
        self.assertEqual(cmd.parameters[2][0], ParameterType.STRING)
        self.assertEqual(cmd.parameters[2][1], "Test Group")  # Group name

    def test_group_get_ids_command(self):
        """Test creation of a group get IDs command."""
        cmd = GroupGetIds()
        self.assertEqual(cmd.method_name, "selve.GW.group.getIDs")
        self.assertEqual(len(cmd.parameters), 0)

    def test_group_delete_command(self):
        """Test creation of a group delete command."""
        cmd = GroupDelete(3)
        self.assertEqual(cmd.method_name, "selve.GW.group.delete")
        self.assertEqual(len(cmd.parameters), 1)
        self.assertEqual(cmd.parameters[0][0], ParameterType.INT)
        self.assertEqual(cmd.parameters[0][1], 3)  # Group ID to delete

    def test_group_read_response(self):
        """Test parsing a group read response."""
        # Simulate a response for a group with name "Living Room", ID 2, and a certain mask
        response = GroupReadResponse("selve.GW.group.read", 
                                    [(ParameterType.STRING, "Living Room"), 
                                     (ParameterType.INT, 2), 
                                     (ParameterType.BASE64, "Aw==")])  # Base64 for bit 0 and 1 set
        
        self.assertEqual(response.name, "selve.GW.group.read")
        self.assertEqual(response.id, 2)
        self.assertEqual(response.groupName, "Living Room")  # Änderung von name zu groupName
        self.assertEqual(response.mask, "Aw==")

    def test_group_write_response(self):
        """Test parsing a group write response."""
        # Simulate a successful write
        response_success = GroupWriteResponse("selve.GW.group.write", [(ParameterType.BOOL, True)])
        self.assertEqual(response_success.name, "selve.GW.group.write")
        self.assertTrue(response_success.executed)
        
        # Simulate a failed write
        response_failure = GroupWriteResponse("selve.GW.group.write", [(ParameterType.BOOL, False)])
        self.assertEqual(response_failure.name, "selve.GW.group.write")
        self.assertFalse(response_failure.executed)

    def test_group_get_ids_response(self):
        """Test parsing a group get IDs response."""
        # Mock Util.b64bytes_to_bitlist and Util.true_in_list
        with patch('selve.commands.group.Util.b64bytes_to_bitlist') as mock_to_bitlist, \
             patch('selve.commands.group.Util.true_in_list') as mock_true_in_list:
            
            # Setup mocks
            mock_to_bitlist.return_value = [True, False, True, False, True]  # Bits 0, 2, 4 set
            mock_true_in_list.return_value = [0, 2, 4]  # IDs 0, 2, 4
            
            # Create response
            response = GroupGetIdsResponse("selve.GW.group.getIds", [(ParameterType.BASE64, "some_base64")])
            
            self.assertEqual(response.name, "selve.GW.group.getIds")
            self.assertEqual(response.ids, [0, 2, 4])
            
            # Verify our mocks were called correctly
            mock_to_bitlist.assert_called_once_with("some_base64")
            mock_true_in_list.assert_called_once()

    def test_group_delete_response(self):
        """Test parsing a group delete response."""
        # Simulate a successful delete
        response_success = GroupDeleteResponse("selve.GW.group.delete", [(ParameterType.BOOL, True)])
        self.assertEqual(response_success.name, "selve.GW.group.delete")
        self.assertTrue(response_success.executed)
        
        # Simulate a failed delete
        response_failure = GroupDeleteResponse("selve.GW.group.delete", [(ParameterType.BOOL, False)])
        self.assertEqual(response_failure.name, "selve.GW.group.delete")
        self.assertFalse(response_failure.executed)


if __name__ == "__main__":
    unittest.main()
