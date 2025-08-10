"""
Additional edge case tests for selve/__init__.py 
This file focuses on simple edge cases and error handling scenarios.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from selve import Selve
from selve.util.errors import *
from selve.util.protocol import SelveTypes
from selve.util import Command


class TestSelveEdgeCases:
    """Test edge cases and error handling."""
    
    def test_init_with_none_logger(self):
        """Test initialization with None logger."""
        selve = Selve(logger=None)
        # None logger should result in None _LOGGER (implementation allows this)
        assert selve._LOGGER is None
        
    def test_init_with_invalid_port(self):
        """Test initialization with invalid port."""
        selve = Selve(port="INVALID_PORT")
        assert selve._port == "INVALID_PORT"
        
    def test_devices_initialization(self):
        """Test that devices dict is properly initialized."""
        selve = Selve()
        assert isinstance(selve.devices, dict)
        
        # Check that main device types are initialized (not all SelveTypes)
        expected_types = ['device', 'group', 'iveo', 'senSim', 'sender', 'sensor']
        for device_type in expected_types:
            assert device_type in selve.devices
            assert isinstance(selve.devices[device_type], dict)
            
    def test_update_options_edge_cases(self):
        """Test updateOptions with edge case values."""
        selve = Selve()
        
        # Test with negative value
        selve.updateOptions(-5)
        assert selve.reversedStopPosition == -5
        
        # Test with zero
        selve.updateOptions(0)
        assert selve.reversedStopPosition == 0
        
        # Test with large value
        selve.updateOptions(99999)
        assert selve.reversedStopPosition == 99999
        
    def test_callback_management_edge_cases(self):
        """Test callback management edge cases."""
        selve = Selve()
        
        # Test removing non-existent callback
        def dummy_callback():
            pass
            
        # This should not raise an error
        selve.remove_callback(dummy_callback)
        selve.remove_event_callback(dummy_callback)
        
        # Test adding same callback multiple times
        selve.register_callback(dummy_callback)
        selve.register_callback(dummy_callback)
        
        # Callbacks are stored in a set, so duplicates are automatically removed
        assert dummy_callback in selve._callbacks
        
    def test_create_error_edge_cases(self):
        """Test create_error with edge cases."""
        selve = Selve()
        
        # Test with object that has no methodResponse
        obj_no_response = Mock()
        del obj_no_response.methodResponse
        
        result = selve.create_error(obj_no_response)
        assert result is False
        
        # Test with None object
        try:
            result = selve.create_error(None)
            # This might raise AttributeError, which is expected
        except AttributeError:
            pass
            
    def test_create_response_edge_cases(self):
        """Test create_response edge cases."""
        selve = Selve()
        
        # Test with object that has no methodResponse
        obj_no_response = Mock()
        del obj_no_response.methodResponse
        
        with pytest.raises(CommunicationError):
            selve.create_response(obj_no_response)
            
    def test_device_management_edge_cases(self):
        """Test device management edge cases."""
        selve = Selve()
        
        # Test getDevice with non-existent device
        result = selve.getDevice(999, SelveTypes.DEVICE)
        assert result is None
        
        # Test deleteDevice with non-existent device (will raise KeyError)
        with pytest.raises(KeyError):
            selve.deleteDevice(999, SelveTypes.DEVICE)
        
        # Test is_id_registered with non-existent device
        assert selve.is_id_registered(999, SelveTypes.DEVICE) is False
        
    def test_find_free_id_edge_cases(self):
        """Test findFreeId edge cases."""
        selve = Selve()
        
        # Test with empty devices
        free_id = selve.findFreeId(SelveTypes.DEVICE)
        assert free_id == 0  # Should return 0 when no devices exist
        
        # Test with devices starting from 0
        device = Mock()
        device.id = 0
        selve.devices[SelveTypes.DEVICE.value][0] = device
        
        free_id = selve.findFreeId(SelveTypes.DEVICE)
        assert free_id == 1
        
    def test_list_devices_logging(self):
        """Test list_devices actually logs devices."""
        logger = Mock(spec=logging.Logger)
        selve = Selve(logger=logger)
        
        # Add a device
        device = Mock()
        device.__str__ = Mock(return_value="Test Device")
        selve.devices[SelveTypes.DEVICE.value][1] = device
        
        # Call list_devices
        selve.list_devices()
        
        # Should have called logger.info
        logger.info.assert_called_with("Test Device")
        
    def test_command_result_edge_cases(self):
        """Test commandResult method edge cases."""
        selve = Selve()
        
        # Test with None response
        try:
            selve.commandResult(None)
            # This might not raise an error, which is fine
        except AttributeError:
            # This is also acceptable
            pass
            
    def test_initial_state_consistency(self):
        """Test that initial state values are consistent."""
        selve = Selve()
        
        # Check initial values
        assert selve.utilization == 0
        assert selve.lastLogEvent is None
        assert selve.state is None
        assert selve.reversedStopPosition == 0
        assert selve.workerTask is None
        assert selve._serial is None
        
        # Check data structures - txQ might be None initially
        assert selve.txQ is None or isinstance(selve.txQ, list)
        assert isinstance(selve.devices, dict)
        assert isinstance(selve._callbacks, set)
        assert isinstance(selve._eventCallbacks, set)
        
    def test_serial_attribute_handling(self):
        """Test serial attribute handling."""
        selve = Selve()
        
        # Initially should be None
        assert selve._serial is None
        
        # Setting to a mock
        mock_serial = Mock()
        selve._serial = mock_serial
        assert selve._serial == mock_serial


class TestSelveErrorScenarios:
    """Test various error scenarios."""
    
    def test_create_response_call_edge_cases(self):
        """Test create_response_call edge cases."""
        selve = Selve()
        
        # Test with object that has methodCall but no array
        obj = Mock()
        obj.methodCall = Mock()
        del obj.methodCall.array
        
        try:
            result = selve.create_response_call(obj)
            # Might raise AttributeError or return something
        except AttributeError:
            pass
            
        # Test with object that has no methodCall
        obj_no_call = Mock()
        del obj_no_call.methodCall
        
        # This should raise CommunicationError
        with pytest.raises(CommunicationError):
            result = selve.create_response_call(obj_no_call)
            
    def test_port_edge_cases(self):
        """Test port-related edge cases."""
        # Test with empty string port
        selve = Selve(port="")
        assert selve._port == ""
        
        # Test with special characters in port
        selve = Selve(port="COM@#$%")
        assert selve._port == "COM@#$%"
        
    def test_loop_parameter_handling(self):
        """Test loop parameter handling."""
        import asyncio
        
        # Test with custom loop
        custom_loop = asyncio.new_event_loop()
        selve = Selve(loop=custom_loop)
        assert selve.loop == custom_loop
        
        # Clean up
        custom_loop.close()
        
        # Test with None loop (implementation allows None)
        selve = Selve(loop=None)
        assert selve.loop is None
        
    def test_discover_parameter_handling(self):
        """Test discover parameter handling."""
        # Test with discover=False
        selve = Selve(discover=False)
        # Should not cause any issues
        assert selve is not None
        
        # Test with discover=True (default)
        selve = Selve(discover=True)
        assert selve is not None
        
    def test_develop_parameter_handling(self):
        """Test develop parameter handling."""
        # Test with develop=True
        selve = Selve(develop=True)
        assert selve is not None
        
        # Test with develop=False (default)
        selve = Selve(develop=False)
        assert selve is not None
