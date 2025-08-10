import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Import the Selve package
import selve
from selve.commands.senSim import *
from selve.util.protocol import ParameterType, SenSimCommandType
from selve.util import Util


class TestSelveSenSimCommandsExtended(unittest.TestCase):
    """Extended tests to improve coverage for SenSim command classes."""
    
    def test_sensim_store_command(self):
        """Test SenSimStore command creation."""
        cmd = SenSimStore(1, 123)
        self.assertIsNotNone(cmd)

    def test_sensim_delete_command(self):
        """Test SenSimDelete command creation."""
        cmd = SenSimDelete(1, 123)
        self.assertIsNotNone(cmd)

    def test_sensim_get_config_command(self):
        """Test SenSimGetConfig command creation."""
        cmd = SenSimGetConfig(1)
        self.assertIsNotNone(cmd)

    def test_sensim_set_values_command(self):
        """Test SenSimSetValues command creation."""
        cmd = SenSimSetValues(
            id=1,
            windDigital=1,
            rainDigital=0,
            tempDigital=1,
            lightDigital=0,
            tempAnalog=25,
            windAnalog=10,
            sun1Analog=800,
            dayLightAnalog=1200,
            sun2Analog=900,
            sun3Analog=700
        )
        self.assertIsNotNone(cmd)

    def test_sensim_factory_command(self):
        """Test SenSimFactory command creation."""
        cmd = SenSimFactory(1)
        self.assertIsNotNone(cmd)

    def test_sensim_drive_command(self):
        """Test SenSimDrive command creation."""
        cmd = SenSimDrive(1, SenSimCommandType.STOP)
        self.assertIsNotNone(cmd)

    def test_sensim_set_test_command(self):
        """Test SenSimSetTest command creation."""
        cmd = SenSimSetTest(1, 1)
        self.assertIsNotNone(cmd)

    def test_sensim_get_test_command(self):
        """Test SenSimGetTest command creation."""
        cmd = SenSimGetTest(1)
        self.assertIsNotNone(cmd)

    def test_sensim_store_response(self):
        """Test SenSimStoreResponse creation and properties."""
        # Test with executed = True
        response = SenSimStoreResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimStoreResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_delete_response(self):
        """Test SenSimDeleteResponse creation and properties."""
        # Test with executed = True
        response = SenSimDeleteResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimDeleteResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_get_config_response(self):
        """Test SenSimGetConfigResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test SenSim"),  # name
            (ParameterType.INT, 123),               # senSimId
            (ParameterType.INT, 1),                 # activity
        ]
        response = SenSimGetConfigResponse("test", parameters)
        self.assertEqual(response.name, "Test SenSim")
        self.assertEqual(response.senSimId, 123)
        self.assertTrue(response.activity)

    def test_sensim_set_config_response(self):
        """Test SenSimSetConfigResponse creation and properties."""
        # Test with executed = True
        response = SenSimSetConfigResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimSetConfigResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_set_label_response(self):
        """Test SenSimSetLabelResponse creation and properties."""
        # Test with executed = True
        response = SenSimSetLabelResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimSetLabelResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_set_values_response(self):
        """Test SenSimSetValuesResponse creation and properties."""
        # Test with executed = True
        response = SenSimSetValuesResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimSetValuesResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_get_values_response(self):
        """Test SenSimGetValuesResponse creation and properties."""
        parameters = [
            (ParameterType.STRING, "Test"),  # name/unused
            (ParameterType.INT, 1),          # windDigital
            (ParameterType.INT, 0),          # rainDigital
            (ParameterType.INT, 1),          # tempDigital
            (ParameterType.INT, 0),          # lightDigital
            (ParameterType.INT, 25),         # tempAnalog
            (ParameterType.INT, 10),         # windAnalog
            (ParameterType.INT, 800),        # sun1Analog
            (ParameterType.INT, 1200),       # dayLightAnalog
            (ParameterType.INT, 900),        # sun2Analog
            (ParameterType.INT, 700),        # sun3Analog
        ]
        response = SenSimGetValuesResponse("test", parameters)
        self.assertIsNone(response.sensorState)
        self.assertEqual(response.tempAnalog, 25)
        self.assertEqual(response.windAnalog, 10)
        self.assertEqual(response.sun1Analog, 800)
        self.assertEqual(response.dayLightAnalog, 1200)
        self.assertEqual(response.sun2Analog, 900)
        self.assertEqual(response.sun3Analog, 700)

    def test_sensim_get_ids_response(self):
        """Test SenSimGetIdsResponse creation and properties."""
        response = SenSimGetIdsResponse("test", [(ParameterType.STRING, "AQIDBA==")])
        self.assertIsInstance(response.ids, list)

    def test_sensim_factory_response(self):
        """Test SenSimFactoryResponse creation and properties."""
        # Test with executed = True
        response = SenSimFactoryResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimFactoryResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_drive_response(self):
        """Test SenSimDriveResponse creation and properties."""
        # Test with executed = True
        response = SenSimDriveResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimDriveResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_set_test_response(self):
        """Test SenSimSetTestResponse creation and properties."""
        # Test with executed = True
        response = SenSimSetTestResponse("test", [(ParameterType.INT, 1)])
        self.assertTrue(response.executed)
        
        # Test with executed = False
        response = SenSimSetTestResponse("test", [(ParameterType.INT, 0)])
        self.assertFalse(response.executed)

    def test_sensim_get_test_response(self):
        """Test SenSimGetTestResponse creation and properties."""
        parameters = [
            (ParameterType.INT, 123),  # id
            (ParameterType.INT, 1),    # testMode
        ]
        response = SenSimGetTestResponse("test", parameters)
        self.assertEqual(response.id, 123)
        self.assertTrue(response.testMode)


if __name__ == "__main__":
    unittest.main()
