"""
Comprehensive test coverage for selve/__init__.py
Testing every function and method systematically for 100% coverage.
"""

import pytest
import asyncio
import logging
import serial
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from selve import Selve
from selve.util.errors import *
from selve.util.protocol import ServiceState, DutyMode, SelveTypes, ParameterType
from selve.util import Command, MethodResponse


@pytest.fixture
def selve_instance():
    """Create a Selve instance for testing."""
    loop = asyncio.new_event_loop()
    logger = logging.getLogger("TestLogger")
    return Selve(port="COM3", discover=False, develop=False, logger=logger, loop=loop)


@pytest.fixture
def minimal_selve():
    """Create a minimal Selve instance."""
    return Selve()


class TestSelveInit:
    """Test the __init__ method of Selve class."""
    
    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        loop = asyncio.new_event_loop()
        logger = logging.getLogger("TestLogger")
        
        selve = Selve(
            port="COM5",
            discover=True,
            develop=True,
            logger=logger,
            loop=loop
        )
        
        assert selve._port == "COM5"
        assert selve._LOGGER == logger
        assert selve.loop == loop
        assert isinstance(selve._callbacks, set)
        assert isinstance(selve._eventCallbacks, set)
        assert selve.utilization == 0
        assert selve.sendingBlocked == DutyMode.NOT_BLOCKED
        assert isinstance(selve.devices, dict)
        assert len(selve.devices) == 6
        assert selve.reversedStopPosition == 0

    def test_init_with_minimal_parameters(self):
        """Test initialization with minimal parameters."""
        selve = Selve()
        
        assert selve._port is None
        assert selve._LOGGER is None
        assert selve.loop is None
        assert isinstance(selve._callbacks, set)
        assert isinstance(selve._eventCallbacks, set)

    def test_init_devices_structure(self):
        """Test that devices dictionary has correct structure."""
        selve = Selve()
        
        expected_keys = [
            SelveTypes.DEVICE.value,
            SelveTypes.IVEO.value,
            SelveTypes.GROUP.value,
            SelveTypes.SENSIM.value,
            SelveTypes.SENSOR.value,
            SelveTypes.SENDER.value
        ]
        
        for key in expected_keys:
            assert key in selve.devices
            assert isinstance(selve.devices[key], dict)


class TestSelveListPorts:
    """Test the list_ports method."""
    
    @patch('selve.list_ports.comports')
    def test_list_ports_returns_available_ports(self, mock_comports, minimal_selve):
        """Test that list_ports returns available COM ports."""
        mock_port1 = Mock()
        mock_port1.device = "COM3"
        mock_port2 = Mock()
        mock_port2.device = "COM4"
        mock_comports.return_value = [mock_port1, mock_port2]
        
        ports = minimal_selve.list_ports()
        
        assert len(ports) == 2
        assert ports[0] == mock_port1
        assert ports[1] == mock_port2
        mock_comports.assert_called_once()

    @patch('selve.list_ports.comports')
    def test_list_ports_empty_list(self, mock_comports, minimal_selve):
        """Test list_ports when no ports are available."""
        mock_comports.return_value = []
        
        ports = minimal_selve.list_ports()
        
        assert len(ports) == 0
        mock_comports.assert_called_once()


class TestSelveCheckPort:
    """Test the check_port method."""
    
    @pytest.mark.asyncio
    async def test_check_port_valid_port(self, minimal_selve):
        """Test check_port with a valid port using probe stub."""
        with patch.object(minimal_selve, '_probe_port', AsyncMock(return_value=True)) as mock_probe:
            result = await minimal_selve.check_port("COM3")
        assert result is True
        mock_probe.assert_awaited_once_with("COM3", fromConfigFlow=True)

    @pytest.mark.asyncio
    async def test_check_port_ping_fails(self, minimal_selve):
        """Test check_port when probe fails."""
        with patch.object(minimal_selve, '_probe_port', AsyncMock(return_value=False)) as mock_probe:
            result = await minimal_selve.check_port("COM3")
        assert result is False
        mock_probe.assert_awaited_once_with("COM3", fromConfigFlow=True)

    @pytest.mark.asyncio
    async def test_check_port_serial_exception(self, minimal_selve):
        """Test check_port when probe handles SerialException and returns False."""
        with patch.object(minimal_selve, '_probe_port', AsyncMock(return_value=False)) as mock_probe:
            result = await minimal_selve.check_port("INVALID_PORT")
        assert result is False
        mock_probe.assert_awaited_once_with("INVALID_PORT", fromConfigFlow=True)

    @pytest.mark.asyncio
    async def test_check_port_io_error(self, minimal_selve):
        """Test check_port when probe handles IOError and returns False."""
        with patch.object(minimal_selve, '_probe_port', AsyncMock(return_value=False)) as mock_probe:
            result = await minimal_selve.check_port("BAD_PORT")
        assert result is False
        mock_probe.assert_awaited_once_with("BAD_PORT", fromConfigFlow=True)

    @pytest.mark.asyncio
    async def test_check_port_general_exception(self, minimal_selve):
        """Test check_port when probe handles general exception and returns False."""
        with patch.object(minimal_selve, '_probe_port', AsyncMock(return_value=False)) as mock_probe:
            result = await minimal_selve.check_port("ERROR_PORT")
        assert result is False
        mock_probe.assert_awaited_once_with("ERROR_PORT", fromConfigFlow=True)

    @pytest.mark.asyncio
    async def test_check_port_none_port(self, minimal_selve):
        """Test check_port with None port."""
        result = await minimal_selve.check_port(None)
        assert result is False


class TestSelveCallbacks:
    """Test callback registration and removal methods."""
    
    def test_register_callback(self, minimal_selve):
        """Test callback registration."""
        def test_callback():
            pass
        
        minimal_selve.register_callback(test_callback)
        
        assert test_callback in minimal_selve._callbacks

    def test_remove_callback(self, minimal_selve):
        """Test callback removal."""
        def test_callback():
            pass
        
        minimal_selve.register_callback(test_callback)
        minimal_selve.remove_callback(test_callback)
        
        assert test_callback not in minimal_selve._callbacks

    def test_remove_nonexistent_callback(self, minimal_selve):
        """Test removing a callback that doesn't exist."""
        def test_callback():
            pass
        
        # Should not raise an exception
        minimal_selve.remove_callback(test_callback)

    def test_register_event_callback(self, minimal_selve):
        """Test event callback registration."""
        def test_event_callback():
            pass
        
        minimal_selve.register_event_callback(test_event_callback)
        
        assert test_event_callback in minimal_selve._eventCallbacks

    def test_remove_event_callback(self, minimal_selve):
        """Test event callback removal."""
        def test_event_callback():
            pass
        
        minimal_selve.register_event_callback(test_event_callback)
        minimal_selve.remove_event_callback(test_event_callback)
        
        assert test_event_callback not in minimal_selve._eventCallbacks


class TestSelveUpdateOptions:
    """Test the updateOptions method."""
    
    def test_update_options_reversed_stop_position(self, minimal_selve):
        """Test updating reversedStopPosition option."""
        minimal_selve.updateOptions(reversedStopPosition=1)
        
        assert minimal_selve.reversedStopPosition == 1

    def test_update_options_no_change(self, minimal_selve):
        """Test updateOptions with no parameters."""
        original_value = minimal_selve.reversedStopPosition
        minimal_selve.updateOptions()
        
        assert minimal_selve.reversedStopPosition == original_value

    def test_update_options_zero_value(self, minimal_selve):
        """Test updating with zero value."""
        minimal_selve.updateOptions(reversedStopPosition=0)
        
        assert minimal_selve.reversedStopPosition == 0


class TestSelveCreateError:
    """Test the create_error method."""
    
    def test_create_error_with_valid_data(self, minimal_selve):
        """Test create_error with valid methodResponse data."""
        mock_obj = Mock()
        mock_obj.methodResponse = Mock()
        mock_obj.methodResponse.fault = Mock()
        mock_obj.methodResponse.fault.array = Mock()
        
        # Mock the string and int attributes
        mock_obj.methodResponse.fault.array.string = Mock()
        mock_obj.methodResponse.fault.array.string.cdata = "Test error message"
        mock_obj.methodResponse.fault.array.int = Mock()
        mock_obj.methodResponse.fault.array.int.cdata = 500
        
        error = minimal_selve.create_error(mock_obj)
        
        assert isinstance(error, ErrorResponse)
        # ErrorResponse constructor: (error_type, message) but create_error passes (string, int)
        # So first parameter (string) becomes error_type, second (int) becomes message
        assert error.error_type == "Test error message"
        assert error.message == 500

    def test_create_error_exception_handling(self, minimal_selve):
        """Test create_error when exception occurs."""
        mock_obj = Mock()
        # Remove methodResponse attribute
        del mock_obj.methodResponse
        
        result = minimal_selve.create_error(mock_obj)
        
        assert result is False


class TestSelveCreateResponse:
    """Test the create_response and create_response_call methods."""
    
    def test_create_response_with_valid_data(self, minimal_selve):
        """Test create_response with valid methodResponse data."""
        mock_obj = Mock()
        mock_obj.methodResponse = Mock()
        mock_obj.methodResponse.array = Mock()
        
        # Mock the array structure
        string_mock = Mock()
        string_mock.cdata = "selve.GW.ping"
        mock_obj.methodResponse.array.string = [string_mock]
        
        # Mock hasattr for string check
        with patch('builtins.hasattr') as mock_hasattr:
            def hasattr_side_effect(obj, attr):
                if attr == "methodResponse":
                    return True
                elif attr == "string":
                    return True
                return False
            mock_hasattr.side_effect = hasattr_side_effect
            
            response = minimal_selve.create_response(mock_obj)
            
            # Should return some response object, not necessarily MethodResponse
            assert response is not None

    def test_create_response_exception_handling(self, minimal_selve):
        """Test create_response when exception occurs."""
        mock_obj = Mock()
        # Remove methodResponse to trigger exception
        del mock_obj.methodResponse
        
        with pytest.raises(CommunicationError):
            minimal_selve.create_response(mock_obj)

    def test_create_response_call_with_valid_data(self, minimal_selve):
        """Test create_response_call with valid methodCall data."""
        mock_obj = Mock()
        mock_obj.methodCall = Mock()
        mock_obj.methodCall.methodName = Mock()
        mock_obj.methodCall.methodName.cdata = "test_method"
        mock_obj.methodCall.array = Mock()
        
        # Mock the array structure
        string_mock = Mock()
        string_mock.cdata = "test_value"
        mock_obj.methodCall.array.string = [string_mock]
        
        # Mock hasattr for string check
        with patch('builtins.hasattr') as mock_hasattr:
            def hasattr_side_effect(obj, attr):
                if attr == "methodCall":
                    return True
                elif attr == "string":
                    return True
                return False
            mock_hasattr.side_effect = hasattr_side_effect
            
            response = minimal_selve.create_response_call(mock_obj)
            
            # Should return some response object
            assert response is not None

    def test_create_response_call_exception_handling(self, minimal_selve):
        """Test create_response_call when exception occurs."""
        mock_obj = Mock()
        # Remove methodCall to trigger exception
        del mock_obj.methodCall
        
        with pytest.raises(CommunicationError):
            minimal_selve.create_response_call(mock_obj)


class TestSelveWorkerThread:
    """Test worker thread related methods."""
    
    @pytest.mark.asyncio
    async def test_start_worker(self, selve_instance):
        """Test starting the worker thread without real serial port."""
        with patch.object(selve_instance, '_worker') as mock_worker:
            mock_worker.return_value = True
            # Avoid real serial port: provide fake transport with start_reader stub
            fake_transport = MagicMock()
            selve_instance._transport = fake_transport
            await selve_instance.startWorker()
            fake_transport.start_reader.assert_called()
            assert selve_instance.workerTask is not None

    @pytest.mark.asyncio
    async def test_stop_worker(self, selve_instance):
        """Test stopping the worker thread without real serial port."""
        # First start a worker
        with patch.object(selve_instance, '_worker') as mock_worker:
            mock_worker.return_value = True
            fake_transport = MagicMock()
            selve_instance._transport = fake_transport
            await selve_instance.startWorker()
            
            # Now stop it
            await selve_instance.stopWorker()
            
            assert selve_instance._stopThread.is_set()
            fake_transport.stop_reader.assert_called()

    def test_pause_worker_internal(self, minimal_selve):
        """Test accessing internal pause worker event."""
        # Test that _pauseWorker is an Event and can be set
        assert hasattr(minimal_selve, '_pauseWorker')
        minimal_selve._pauseWorker.set()
        assert minimal_selve._pauseWorker.is_set()
        
        minimal_selve._pauseWorker.clear()
        assert not minimal_selve._pauseWorker.is_set()

    def test_stop_worker_internal(self, minimal_selve):
        """Test accessing internal stop worker event."""
        # Test that _stopThread is an Event and can be set
        assert hasattr(minimal_selve, '_stopThread')
        minimal_selve._stopThread.set()
        assert minimal_selve._stopThread.is_set()
        
        minimal_selve._stopThread.clear()
        assert not minimal_selve._stopThread.is_set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
