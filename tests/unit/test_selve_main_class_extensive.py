import asyncio
import threading
import logging
import sys
import os
from queue import Queue
import pytest
from unittest.mock import MagicMock, patch, AsyncMock, Mock

# Import the Selve package
import selve
from selve import Selve
from selve.util import Command
from selve.util.errors import *
from selve.util.protocol import ServiceState


class TestSelveMainClassExtensive:
    """Extensive tests to improve coverage for the main Selve class."""

    def test_selve_init_with_all_parameters(self):
        """Test Selve initialization with all parameters."""
        logger = logging.getLogger("TestLogger")
        loop = asyncio.new_event_loop()
        
        selve_instance = Selve(
            port="COM3", 
            discover=False, 
            develop=True, 
            logger=logger,
            loop=loop
        )
        
        assert selve_instance._port == "COM3"
        assert selve_instance._LOGGER == logger
        assert selve_instance.loop == loop
        
        loop.close()

    def test_selve_init_with_minimal_parameters(self):
        """Test Selve initialization with minimal parameters."""
        selve_instance = Selve()
        
        assert selve_instance._port is None
        assert selve_instance._callbacks is not None

    def test_list_ports_method(self):
        """Test the list_ports method."""
        selve_instance = Selve()
        
        with patch('selve.list_ports.comports') as mock_comports:
            mock_port = Mock()
            mock_port.device = "COM3"
            mock_comports.return_value = [mock_port]
            
            ports = selve_instance.list_ports()
            assert ports == [mock_port]

    @pytest.mark.asyncio
    @patch('selve.serial.Serial')
    async def test_check_port_valid(self, mock_serial):
        """Test check_port with a valid port using probe stub and logger."""
        selve_instance = Selve()
        selve_instance._LOGGER = Mock()
        
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance
        
        with patch.object(selve_instance, '_probe_port', AsyncMock(return_value=True)) as mock_probe:
            result = await selve_instance.check_port("COM3")
        assert result is True
        mock_probe.assert_awaited_once_with("COM3", fromConfigFlow=True)

    @pytest.mark.asyncio
    @patch('selve.serial.Serial')
    async def test_check_port_invalid(self, mock_serial):
        """Test check_port with an invalid port."""
        mock_logger = Mock()
        selve_instance = Selve(logger=mock_logger)
        
        mock_serial.side_effect = Exception("Port not found")
        
        result = await selve_instance.check_port("INVALID_PORT")
        assert result is False

    def test_register_and_remove_callback(self):
        """Test callback registration and removal."""
        selve_instance = Selve()
        
        def test_callback():
            pass
        
        # Test registration
        selve_instance.register_callback(test_callback)
        assert test_callback in selve_instance._callbacks
        
        # Test removal
        selve_instance.remove_callback(test_callback)
        assert test_callback not in selve_instance._callbacks

    def test_register_and_remove_event_callback(self):
        """Test event callback registration and removal."""
        selve_instance = Selve()
        
        def test_event_callback():
            pass
        
        # Test registration
        selve_instance.register_event_callback(test_event_callback)
        assert test_event_callback in selve_instance._eventCallbacks
        
        # Test removal
        selve_instance.remove_event_callback(test_event_callback)
        assert test_event_callback not in selve_instance._eventCallbacks

    def test_update_options(self):
        """Test updateOptions method."""
        selve_instance = Selve()
        
        selve_instance.updateOptions(reversedStopPosition=1)
        assert selve_instance.reversedStopPosition == 1

    @pytest.mark.asyncio
    @patch('selve.serial.Serial')
    async def test_setup_with_valid_port(self, mock_serial):
        """Test setup with a valid port."""
        mock_logger = Mock()
        selve_instance = Selve(port="COM3", logger=mock_logger)
        
        mock_serial_instance = Mock()
        mock_serial_instance.is_open = True
        mock_serial.return_value = mock_serial_instance
        
        with patch.object(selve_instance, '_probe_port', AsyncMock(return_value=True)) as mock_probe, \
             patch.object(selve_instance, 'discover', return_value=None), \
             patch.object(selve_instance, 'startWorker', return_value=None):

            await selve_instance.setup(discover=True)
            mock_probe.assert_awaited_once_with("COM3", fromConfigFlow=False)

    @pytest.mark.asyncio
    async def test_setup_with_unknown_exception(self):
        """Test setup when unknown exception occurs."""
        mock_logger = Mock()
        selve_instance = Selve(port="COM3", logger=mock_logger)
        
        with patch('selve.list_ports.comports', return_value=[]):
            with patch('selve.serial.Serial', side_effect=RuntimeError("Unknown error")):
                with pytest.raises(Exception):  # Expect PortError to be raised
                    await selve_instance.setup()

    def test_create_error_method(self):
        """Test create_error method."""
        selve_instance = Selve()
        
        # Test with valid methodResponse
        mock_obj = Mock()
        mock_obj.methodResponse = Mock()
        mock_obj.methodResponse.fault = Mock()
        mock_obj.methodResponse.fault.array = Mock()
        mock_obj.methodResponse.fault.array.string = Mock()
        mock_obj.methodResponse.fault.array.string.cdata = "Test error"
        mock_obj.methodResponse.fault.array.int = Mock()
        mock_obj.methodResponse.fault.array.int.cdata = 123
        
        error = selve_instance.create_error(mock_obj)
        assert isinstance(error, ErrorResponse)
        # ErrorResponse constructor takes (error_type, message), so code is error_type and message is message
        assert error.error_type == "Test error"  # First parameter
        assert error.message == 123  # Second parameter
        
        # Test without methodResponse
        mock_obj_invalid = Mock()
        del mock_obj_invalid.methodResponse
        
        error = selve_instance.create_error(mock_obj_invalid)
        assert error is False

    def test_create_response_method(self):
        """Test create_response method."""
        selve_instance = Selve()
        
        mock_obj = Mock()
        mock_obj.methodName = "test.method"
        mock_obj.array = Mock()
        
        with patch.object(selve_instance, '_create_response', return_value="test_response"):
            response = selve_instance.create_response(mock_obj)
            assert response == "test_response"

    def test_create_response_call_method(self):
        """Test create_response_call method."""
        selve_instance = Selve()
        
        mock_obj = Mock()
        mock_obj.methodName = "test.method"
        mock_obj.params = Mock()
        mock_obj.params.array = Mock()
        
        with patch.object(selve_instance, '_create_response', return_value="test_response"):
            response = selve_instance.create_response_call(mock_obj)
            assert response == "test_response"
