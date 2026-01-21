"""
Integration tests for the Selve gateway initialization and connection handling.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from selve import Selve
from selve.commands.service import ServicePing
from selve.util.errors import PortError


@pytest.mark.integration
class TestSelveGatewayIntegration:
    """Test the initialization and connection handling of the Selve gateway."""
    
    @pytest.mark.asyncio
    async def test_gateway_setup_with_valid_port(self, mock_serial, logger):
        """Test successful setup with a valid port."""
        # Configure mock to return successful ping
        mock_instance = mock_serial.return_value
        mock_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        
        # Create Selve instance with the current running loop
        selve = Selve(port="COM3", discover=False, develop=True, 
                     logger=logger, loop=asyncio.get_running_loop())
        
        # Mock the executeCommandSyncWithResponse to return ping and version responses
        with patch.object(selve, 'executeCommandSyncWithResponse') as mock_exec:
            mock_ping_response = MagicMock()
            mock_ping_response.name = "selve.GW.service.ping"
            
            mock_version_response = MagicMock()
            mock_version_response.name = "selve.GW.service.getVersion"
            
            # Return ping first, then version
            mock_exec.side_effect = [mock_ping_response, mock_version_response]
            
            # Call setup
            await selve.setup(discover=False, fromConfigFlow=True)
            
            # Verify port was set correctly
            assert selve._port == "COM3"
            
            # Verify serial was initialized
            assert selve._serial is not None
    
    @pytest.mark.asyncio
    async def test_gateway_setup_with_invalid_port(self, mock_serial, logger):
        """Test setup with an invalid port."""
        # Configure mock to simulate port error
        mock_serial.side_effect = [Exception("Port error")]
        
        # Create Selve instance with invalid port
        selve = Selve(port="INVALID", discover=False, develop=True, 
                     logger=logger, loop=asyncio.get_running_loop())
        
        # Setup should try other ports
        with pytest.raises(PortError):
            await selve.setup(discover=False, fromConfigFlow=True)
    
    @pytest.mark.asyncio
    async def test_gateway_ping(self, mock_serial, mock_selve_instance):
        """Test pinging the gateway."""
        # Configure mock to return successful ping
        mock_response = MagicMock()
        mock_response.name = "selve.GW.service.ping"
        mock_selve_instance.executeCommandSyncWithResponse.return_value = mock_response
        
        # Call pingGateway
        result = await mock_selve_instance.pingGateway()
        
        # Verify ping was successful
        assert result is True
        
        # Verify the correct command was executed
        mock_selve_instance.executeCommandSyncWithResponse.assert_called_once()
        command_arg = mock_selve_instance.executeCommandSyncWithResponse.call_args[0][0]
        assert isinstance(command_arg, ServicePing)
    
    @pytest.mark.asyncio
    async def test_gateway_recovery(self, mock_serial, mock_selve_instance):
        """Test that the recovery method can be called successfully."""
        # Directly test the recover method with mocked components
        with patch.object(mock_selve_instance, '_LOGGER') as mock_logger:
            with patch('asyncio.sleep', return_value=None):  # Skip the sleep delay
                with patch('selve.serial.Serial') as mock_serial_class:
                    # Configure the mock serial to succeed
                    mock_serial_instance = MagicMock()
                    mock_serial_instance.is_open = True
                    mock_serial_class.return_value = mock_serial_instance
                    
                    # Mock _probe_port to return True immediately
                    mock_selve_instance._probe_port = AsyncMock(return_value=True)
                    mock_selve_instance._port = "COM3"
                    
                    # Call recover directly
                    await mock_selve_instance.recover()
                    
                    # Verify logger was called (indicating recover ran)
                    mock_logger.info.assert_called_with("(Selve Worker): Recover serial connection")
                    mock_logger.debug.assert_any_call("(Selve Worker): Waiting 5 seconds before trying...")
                    mock_logger.debug.assert_any_call("(Selve Worker): Recovering")
