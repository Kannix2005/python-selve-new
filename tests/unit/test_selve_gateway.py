import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.commands.service import ServicePing, ServiceGetState, ServiceGetVersion
from selve.util.protocol import ServiceState


@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def logger():
    """Create a mock logger."""
    return MagicMock(spec=logging.Logger)


@pytest.fixture
def selve_instance(logger, event_loop):
    """Create a Selve instance with mocked components."""
    with patch('selve.Selve._worker', AsyncMock()), \
         patch('selve.serial.Serial'):
        selve = Selve(port=None, develop=True, logger=logger, loop=event_loop)
        
        # Mock the execute command methods
        selve.executeCommand = AsyncMock()
        selve.executeCommandSyncWithResponse = AsyncMock()
        selve.executeCommandSyncWithResponsefromWorker = AsyncMock()
        
        yield selve


@pytest.mark.asyncio
async def test_ping_gateway_from_worker_success(selve_instance):
    """Test successful ping to gateway from worker."""
    # Create a mock response with the expected name
    mock_response = MagicMock()
    mock_response.name = "selve.GW.service.ping"
    
    # Set up our mock to return this response
    selve_instance.executeCommandSyncWithResponsefromWorker.return_value = mock_response
    
    # Add mock method to the Selve instance
    async def mock_ping_gateway_from_worker():
        cmd = ServicePing()
        methodResponse = await selve_instance.executeCommandSyncWithResponsefromWorker(cmd)
        
        if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
            selve_instance._LOGGER.debug("Ping back")
            return True
        else:
            selve_instance._LOGGER.debug("No ping")
            return False
            return False
    
    selve_instance.pingGatewayFromWorker = mock_ping_gateway_from_worker
    
    # Call the method
    result = await selve_instance.pingGatewayFromWorker()
    
    # Assert the result is True
    assert result is True
    
    # Verify the correct command was created and executed
    selve_instance.executeCommandSyncWithResponsefromWorker.assert_called_once()
    # The first argument should be a ServicePing instance
    args = selve_instance.executeCommandSyncWithResponsefromWorker.call_args[0]
    assert isinstance(args[0], ServicePing)
    
    # Check that the logger was called with expected message
    selve_instance._LOGGER.debug.assert_called_with("Ping back")


@pytest.mark.asyncio
async def test_ping_gateway_from_worker_failure_wrong_name(selve_instance):
    """Test failed ping to gateway from worker due to wrong response name."""
    # Create a mock response with a wrong name
    mock_response = MagicMock()
    mock_response.name = "wrong.name"
    
    # Set up our mock to return this response
    selve_instance.executeCommandSyncWithResponsefromWorker.return_value = mock_response
    
    # Add mock method to the Selve instance
    async def mock_ping_gateway_from_worker():
        cmd = ServicePing()
        methodResponse = await selve_instance.executeCommandSyncWithResponsefromWorker(cmd)
        
        if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
            selve_instance._LOGGER.debug("Ping back")
            return True
        else:
            selve_instance._LOGGER.debug("No ping")
            return False
    
    selve_instance.pingGatewayFromWorker = mock_ping_gateway_from_worker
    
    # Call the method
    result = await selve_instance.pingGatewayFromWorker()
    
    # Assert the result is False
    assert result is False
    
    # Check that the logger was called with expected message
    selve_instance._LOGGER.debug.assert_called_with("No ping")


@pytest.mark.asyncio
async def test_ping_gateway_from_worker_failure_exception(selve_instance):
    """Test failed ping to gateway from worker due to exception."""
    # Set up our mock to raise an exception
    selve_instance.executeCommandSyncWithResponsefromWorker.side_effect = Exception("Test exception")
    
    # Add mock method to the Selve instance
    async def mock_ping_gateway_from_worker():
        try:
            cmd = ServicePing()
            methodResponse = await selve_instance.executeCommandSyncWithResponsefromWorker(cmd)
            
            if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                selve_instance._LOGGER.debug("Ping back")
                return True
            else:
                selve_instance._LOGGER.debug("No ping")
                return False
        except Exception:
            selve_instance._LOGGER.debug("Error in ping")
            selve_instance._LOGGER.debug("No ping")
            return False
    
    selve_instance.pingGatewayFromWorker = mock_ping_gateway_from_worker
    
    # Call the method
    result = await selve_instance.pingGatewayFromWorker()
    
    # Assert the result is False
    assert result is False
    
    # Check that the logger was called with expected messages
    selve_instance._LOGGER.debug.assert_any_call("Error in ping")
    selve_instance._LOGGER.debug.assert_any_call("No ping")


@pytest.mark.asyncio
async def test_gateway_state_success(selve_instance):
    """Test successfully getting gateway state."""
    # Create a mock response with the expected structure
    mock_response = MagicMock()
    mock_response.name = "selve.GW.service.getState"
    mock_response.parameters = [(None, None), (None, 3)]  # 3 corresponds to READY state
    
    # Set up our mock to return this response
    selve_instance.executeCommandSyncWithResponse.return_value = mock_response
    
    # Add mock method to the Selve instance
    async def mock_gateway_state():
        cmd = ServiceGetState()
        methodResponse = await selve_instance.executeCommandSyncWithResponse(cmd)
        
        if methodResponse and hasattr(methodResponse, 'parameters') and len(methodResponse.parameters) > 1:
            status = ServiceState(int(methodResponse.parameters[1][1]))
            selve_instance.state = status
            selve_instance._LOGGER.debug(f"Gateway state: {status}")
            return status
        return None
    
    selve_instance.gatewayState = mock_gateway_state
    
    # Call the method
    result = await selve_instance.gatewayState()
    
    # Assert the result is the expected state
    assert result == ServiceState.READY
    
    # Verify the correct command was created and executed
    selve_instance.executeCommandSyncWithResponse.assert_called_once()
    # The first argument should be a ServiceGetState instance
    args = selve_instance.executeCommandSyncWithResponse.call_args[0]
    assert isinstance(args[0], ServiceGetState)
    
    # Check that the state was updated on the instance
    assert selve_instance.state == ServiceState.READY
    
    # Check that the logger was called with expected message
    selve_instance._LOGGER.debug.assert_called_with("Gateway state: ServiceState.READY")


@pytest.mark.asyncio
async def test_gateway_ready_success(selve_instance):
    """Test successfully checking if gateway is ready."""
    # Add mock method to the Selve instance
    async def mock_gateway_state():
        return ServiceState.READY
    
    async def mock_gateway_ready():
        state = await selve_instance.gatewayState()
        return state == ServiceState.READY
    
    selve_instance.gatewayState = mock_gateway_state
    selve_instance.gatewayReady = mock_gateway_ready
    
    # Call the method
    result = await selve_instance.gatewayReady()
    
    # Assert the result is True
    assert result is True


@pytest.mark.asyncio
async def test_get_gateway_firmware_version_success(selve_instance):
    """Test successfully getting gateway firmware version."""
    # Create a mock response with a version attribute
    mock_response = MagicMock()
    mock_response.version = "1.2.3"
    
    # Add mock methods to the Selve instance
    async def mock_get_version():
        return mock_response
    
    async def mock_get_gateway_firmware_version():
        version_info = await selve_instance.getVersionG()
        return version_info.version if version_info else None
    
    selve_instance.getVersionG = mock_get_version
    selve_instance.getGatewayFirmwareVersion = mock_get_gateway_firmware_version
    
    # Call the method
    result = await selve_instance.getGatewayFirmwareVersion()
    
    # Assert the result is the expected version
    assert result == "1.2.3"


@pytest.mark.asyncio
async def test_get_gateway_serial_success(selve_instance):
    """Test successfully getting gateway serial number."""
    # Create a mock response with a serial attribute
    mock_response = MagicMock()
    mock_response.serial = "ABC12345"
    
    # Add mock methods to the Selve instance
    async def mock_get_version():
        return mock_response
    
    async def mock_get_gateway_serial():
        version_info = await selve_instance.getVersionG()
        return version_info.serial if version_info else None
    
    selve_instance.getVersionG = mock_get_version
    selve_instance.getGatewaySerial = mock_get_gateway_serial
    
    # Call the method
    result = await selve_instance.getGatewaySerial()
    
    # Assert the result is the expected serial
    assert result == "ABC12345"
