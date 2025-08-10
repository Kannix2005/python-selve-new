"""
Comprehensive coverage tests for selve/__init__.py - Part 3
Focuses on _create_response method and specific response types
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from selve import Selve
from selve.util.errors import *
from selve.util import CommeoServiceCommand, CommeoParamCommand, CommeoDeviceCommand


class TestSelveResponseCreation:
    """Test the _create_response method and its various response types"""
    
    def test_create_response_service_ping(self):
        """Test _create_response for service ping command"""
        selve = Selve(logger=Mock())
        
        # Mock array with string parameters
        mock_array = Mock()
        mock_array.string = [Mock(), Mock()]
        mock_array.string[0].cdata = "selve.GW." + str(CommeoServiceCommand.PING.value)
        mock_array.string[1].cdata = "response_data"
        
        # Mock hasattr to return True for string, False for int and base64
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array)
            # Should return a ServicePingResponse
            assert response is not None
            
    def test_create_response_service_getstate(self):
        """Test _create_response for service getstate command"""
        selve = Selve(logger=Mock())
        
        mock_array = Mock()
        mock_array.string = [Mock()]
        mock_array.string[0].cdata = "selve.GW." + str(CommeoServiceCommand.GETSTATE.value)
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array, "selve.GW." + str(CommeoServiceCommand.GETSTATE.value))
            assert response is not None
            
    def test_create_response_service_getversion(self):
        """Test _create_response for service getversion command"""
        selve = Selve(logger=Mock())
        
        mock_array = Mock()
        # ServiceGetVersionResponse expects 7 parameters: serial, major, minor, patch, spec_major, spec_minor, build
        mock_array.string = [Mock() for _ in range(7)]
        mock_array.string[0].cdata = "12345"  # serial
        mock_array.string[1].cdata = "1"      # version major
        mock_array.string[2].cdata = "0"      # version minor
        mock_array.string[3].cdata = "0"      # version patch
        mock_array.string[4].cdata = "2"      # spec major
        mock_array.string[5].cdata = "1"      # spec minor
        mock_array.string[6].cdata = "100"    # build number
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array, "selve.GW." + str(CommeoServiceCommand.GETVERSION.value))
            assert response is not None
            # The response object should have these attributes
            response_attrs = [a for a in dir(response) if not a.startswith('_')]
            assert 'serial' in response_attrs
            assert 'version' in response_attrs
            
    def test_create_response_param_setforward(self):
        """Test _create_response for param setforward command"""
        selve = Selve(logger=Mock())
        
        mock_array = Mock()
        mock_array.string = [Mock()]
        mock_array.string[0].cdata = "selve.GW." + str(CommeoParamCommand.SETFORWARD.value)
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array, "selve.GW." + str(CommeoParamCommand.SETFORWARD.value))
            assert response is not None
            
    def test_create_response_param_getforward(self):
        """Test _create_response for param getforward command"""
        selve = Selve(logger=Mock())
        
        mock_array = Mock()
        # ParamGetForwardResponse expects at least 1 parameter for forwarding value
        mock_array.string = [Mock()]
        mock_array.string[0].cdata = "1"  # forwarding value (0 or 1)
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array, "selve.GW." + str(CommeoParamCommand.GETFORWARD.value))
            assert response is not None
            # The response object should have the forwarding attribute
            response_attrs = [a for a in dir(response) if not a.startswith('_')]
            assert 'forwarding' in response_attrs
            
    def test_create_response_device_scanstart(self):
        """Test _create_response for device scanstart command"""
        selve = Selve(logger=Mock())
        
        mock_array = Mock()
        mock_array.string = [Mock()]
        mock_array.string[0].cdata = "selve.GW." + str(CommeoDeviceCommand.SCANSTART.value)
        
        with patch('builtins.hasattr', side_effect=lambda obj, attr: attr == 'string'):
            response = selve._create_response(mock_array, "selve.GW." + str(CommeoDeviceCommand.SCANSTART.value))
            assert response is not None


class TestSelveUtilityMethods:
    """Test utility and helper methods"""
    
    def test_port_parameter_none(self):
        """Test handling of None port parameter"""
        selve = Selve(port=None, logger=Mock())
        assert selve._port is None
        
    def test_develop_parameter_false(self):
        """Test handling of develop parameter set to False"""
        selve = Selve(develop=False, logger=Mock())
        # develop parameter should not affect basic initialization
        assert selve._callbacks is not None
        
    def test_loop_parameter(self):
        """Test handling of loop parameter"""
        mock_loop = Mock()
        selve = Selve(loop=mock_loop, logger=Mock())
        assert selve.loop == mock_loop
        
    def test_initial_state_values(self):
        """Test that initial state values are set correctly"""
        selve = Selve(logger=Mock())
        
        assert selve.utilization == 0
        assert selve.lastLogEvent is None
        assert selve.state is None
        assert selve.reversedStopPosition == 0
        assert selve.workerTask is None
        assert selve._serial is None
        
    def test_write_and_read_locks(self):
        """Test that write and read locks are initialized"""
        selve = Selve(logger=Mock())
        
        assert selve._writeLock is not None
        assert selve._readLock is not None
        # These are asyncio.Lock objects
        assert hasattr(selve._writeLock, 'acquire')
        assert hasattr(selve._readLock, 'acquire')
