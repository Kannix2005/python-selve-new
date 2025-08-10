import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Import the Selve package
import selve
from selve.commands.sender import *
from selve.util.protocol import ParameterType, TeachState, senderEvents
from selve.util import Util


class TestSelveSenderCommandsExtended(unittest.TestCase):
    """Extended tests to improve coverage for sender command classes."""
    
    def test_sender_teach_start_command(self):
        """Test SenderTeachStart command creation."""
        cmd = SenderTeachStart()
        self.assertIsNotNone(cmd)

    def test_sender_teach_stop_command(self):
        """Test SenderTeachStop command creation."""
        cmd = SenderTeachStop()
        self.assertIsNotNone(cmd)

    def test_sender_teach_result_command(self):
        """Test SenderTeachResult command creation."""
        cmd = SenderTeachResult()
        self.assertIsNotNone(cmd)

    def test_sender_get_info_command(self):
        """Test SenderGetInfo command creation."""
        cmd = SenderGetInfo(1)
        self.assertIsNotNone(cmd)

    def test_sender_delete_command(self):
        """Test SenderDelete command creation."""
        cmd = SenderDelete(1)
        self.assertIsNotNone(cmd)

    def test_sender_write_manual_command(self):
        """Test SenderWriteManual command creation."""
        cmd = SenderWriteManual(1, 12345, 1, 0, "Manual Sender")
        self.assertIsNotNone(cmd)

    def test_sender_teach_start_response(self):
        """Test SenderTeachStartResponse creation and properties."""
        # Test with executed = True
        response = SenderTeachStartResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenderTeachStartResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sender_teach_stop_response(self):
        """Test SenderTeachStopResponse creation and properties."""
        # Test with executed = True
        response = SenderTeachStopResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenderTeachStopResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sender_teach_result_response(self):
        """Test SenderTeachResultResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test"),   # name
            (ParameterType.INT, 1),           # teachState & timeLeft
            (ParameterType.INT, 123),         # senderId
            (ParameterType.INT, 1),           # senderEvent
        ]
        response = SenderTeachResultResponse("test", parameters)
        self.assertEqual(response.teachState, TeachState.RUN)
        self.assertEqual(response.timeLeft, 1)
        self.assertEqual(response.senderId, 123)
        self.assertEqual(response.senderEvent, senderEvents.DRIVEUP)

    def test_sender_get_ids_response(self):
        """Test SenderGetIdsResponse creation and properties."""
        response = SenderGetIdsResponse("test", [(ParameterType.STRING, "AQIDBA==")])
        self.assertIsInstance(response.ids, list)

    def test_sender_get_info_response(self):
        """Test SenderGetInfoResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test Sender"),  # name
            (ParameterType.INT, 1),                 # unused
            (ParameterType.INT, 12345),             # rfAddress
            (ParameterType.INT, 1),                 # rfChannel
            (ParameterType.INT, 0),                 # rfResetCount
        ]
        response = SenderGetInfoResponse("test", parameters)
        self.assertEqual(response.name, "Test Sender")
        self.assertEqual(response.rfAddress, 12345)
        self.assertEqual(response.rfChannel, 1)
        self.assertEqual(response.rfResetCount, 0)

    def test_sender_get_values_response(self):
        """Test SenderGetValuesResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test Sender"),  # name/unused
            (ParameterType.INT, 1),                 # lastEvent
        ]
        response = SenderGetValuesResponse("test", parameters)
        self.assertEqual(response.lastEvent, senderEvents.DRIVEUP)

    def test_sender_set_label_response(self):
        """Test SenderSetLabelResponse creation and properties."""
        # Test with executed = True
        response = SenderSetLabelResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenderSetLabelResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sender_delete_response(self):
        """Test SenderDeleteResponse creation and properties."""
        # Test with executed = True
        response = SenderDeleteResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenderDeleteResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sender_write_manual_response(self):
        """Test SenderWriteManualResponse creation and properties."""
        # Test with executed = True
        response = SenderWriteManualResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenderWriteManualResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)


if __name__ == "__main__":
    unittest.main()
