import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
import sys
from selve import Selve
from selve.util.protocol import ServiceState


@pytest.fixture
def logger():
    """Set up logging."""
    test_logger = logging.getLogger("TestLogger")
    test_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    test_logger.addHandler(handler)
    return test_logger


@pytest.fixture
async def selve_instance(event_loop, logger):
    """Set up mock serial port and Selve instance."""
    with patch('selve.serial.Serial') as mock_serial, \
         patch('selve.list_ports.comports') as mock_list_ports:
        
        # Setup mock port
        mock_port = MagicMock()
        mock_port.device = "COM3"
        mock_list_ports.return_value = [mock_port]
        
        # Create the Selve instance with mock hardware
        selve = Selve(port="COM3", discover=False, develop=True, 
                     logger=logger, loop=event_loop)
        
        yield selve
        
        # Cleanup tasks
        try:
            await selve.stopWorker()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_list_ports(selve_instance):
    """Test listing available serial ports."""
    ports = selve_instance.list_ports()
    assert len(ports) == 1
    # Check the device attribute of the port object
    assert ports[0].device == "COM3"


@pytest.mark.asyncio
async def test_setup_and_ping(selve_instance):
    """Test setting up the connection and pinging the gateway."""
    with patch('selve.serial.Serial') as mock_serial:
        # Mock the setup responses
        mock_instance = mock_serial.return_value
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        mock_instance.write = MagicMock()
        mock_instance.flush = MagicMock()
        
        # Mock a successful ping response
        ping_response = MagicMock()
        ping_response.name = "selve.GW.service.ping"
        
        # Mock a successful version response for _probe_port
        version_response = MagicMock()
        version_response.name = "selve.GW.service.getVersion"
        
        # Mock executeCommandSyncWithResponse to return successful ping and version
        selve_instance.executeCommandSyncWithResponse = AsyncMock(side_effect=[ping_response, version_response])
        selve_instance.executeCommandSyncWithResponsefromWorker = AsyncMock(return_value=ping_response)
        
        await selve_instance.setup()
        # Test ping from worker
        result = await selve_instance.pingGatewayFromWorker()
        assert result is True


@pytest.mark.asyncio
async def test_gateway_state_ready(selve_instance):
    """Test checking if gateway is in READY state."""
    # Mock gateway state response
    mock_state_response = MagicMock()
    mock_state_response.name = "selve.GW.service.getState"
    mock_state_response.parameters = [(None, 3)]  # 3 is READY state - corrected value
    
    # Mock the executeCommandSyncWithResponse method
    selve_instance.executeCommandSyncWithResponse = AsyncMock(return_value=mock_state_response)
    
    # Get gateway state
    state = await selve_instance.gatewayState()
    assert state == ServiceState.READY
    
    # Check if gateway is ready
    is_ready = await selve_instance.gatewayReady()
    assert is_ready is True


@pytest.mark.asyncio
async def test_get_gateway_version(selve_instance):
    """Test getting gateway version information."""
    # Mock version response
    mock_version_response = MagicMock()
    mock_version_response.name = "selve.GW.service.getVersion"
    mock_version_response.serial = "123456"
    mock_version_response.version = "1.2.3"
    
    # Mock the executeCommandSyncWithResponse method
    selve_instance.executeCommandSyncWithResponse = AsyncMock(return_value=mock_version_response)
    
    # Get version directly
    version_response = await selve_instance.getVersionG()
    assert version_response == mock_version_response
    
    # Get firmware version
    firmware = await selve_instance.getGatewayFirmwareVersion()
    assert firmware == "1.2.3"
    
    # Get serial number
    serial = await selve_instance.getGatewaySerial()
    assert serial == "123456"
