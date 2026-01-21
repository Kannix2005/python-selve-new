import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
import sys

# Import the Selve package
import selve
from selve.util.errors import PortError, CommunicationError, ReadTimeoutError


@pytest.fixture
def logger():
    """Set up logger fixture."""
    logger = logging.getLogger("PortDiscoveryTestLogger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_serial():
    """Mock serial port."""
    with patch('selve.serial.Serial') as mock_serial:
        yield mock_serial


@pytest.fixture
def mock_list_ports():
    """Mock list_ports to return test ports."""
    with patch('selve.list_ports.comports') as mock_list_ports:
        yield mock_list_ports


def test_list_ports_empty(logger, event_loop, mock_serial, mock_list_ports):
    """Test listing ports when no ports are available."""
    # No ports available
    mock_list_ports.return_value = []
    
    # Create selve instance
    selve_instance = selve.Selve(port=None, discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Test listing ports
    ports = selve_instance.list_ports()
    assert len(ports) == 0, "Expected no ports, but got some"


def test_list_ports_multiple(logger, event_loop, mock_serial, mock_list_ports):
    """Test listing multiple available ports."""
    # Create mock ports
    mock_port1 = MagicMock()
    mock_port1.device = "COM1"
    mock_port2 = MagicMock()
    mock_port2.device = "COM2"
    mock_port3 = MagicMock()
    mock_port3.device = "COM3"
    
    # Return multiple ports
    mock_list_ports.return_value = [mock_port1, mock_port2, mock_port3]
    
    # Create selve instance
    selve_instance = selve.Selve(port=None, discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Test listing ports - returns port objects, not device names
    ports = selve_instance.list_ports()
    assert len(ports) == 3, "Expected 3 ports"
    # Check device attributes of port objects
    device_names = [port.device for port in ports]
    assert "COM1" in device_names
    assert "COM2" in device_names
    assert "COM3" in device_names


@pytest.mark.asyncio
async def test_check_port_valid(logger, event_loop, mock_serial, mock_list_ports):
    """Test checking a valid port."""
    # Setup mock serial to successfully connect
    mock_serial_instance = mock_serial.return_value
    mock_serial_instance.is_open = True
    mock_serial_instance.in_waiting = 0
    mock_serial_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
    mock_serial_instance.write = MagicMock()
    mock_serial_instance.flush = MagicMock()
    mock_serial_instance.close = MagicMock()
    
    # Create selve instance with port discovery disabled
    selve_instance = selve.Selve(port=None, discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Mock the pingGateway method to return True for valid port
    with patch.object(selve_instance, 'pingGateway', new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = True
        
        # Test check_port
        result = await selve_instance.check_port("COM1")
        assert result is True, "Expected port to be valid"
        mock_ping.assert_called_once_with(fromConfigFlow=True)


@pytest.mark.asyncio
async def test_check_port_invalid(logger, event_loop, mock_serial, mock_list_ports):
    """Test checking an invalid port that exists but doesn't respond correctly."""
    # Setup mock serial to successfully connect but ping fails
    mock_serial_instance = mock_serial.return_value
    mock_serial_instance.is_open = True
    
    # Create selve instance with port discovery disabled
    selve_instance = selve.Selve(port="COM1", discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Mock the ping method to return False (no proper gateway response)
    selve_instance.pingGatewayFromWorker = AsyncMock(return_value=False)
    
    # Test check_port
    result = await selve_instance.check_port("COM1")
    assert result is False, "Expected port to be invalid"


@pytest.mark.asyncio
async def test_check_port_serial_exception(logger, event_loop, mock_serial, mock_list_ports):
    """Test checking a port that raises a SerialException."""
    # Setup mock serial to raise an exception when opened
    mock_serial.side_effect = selve.SerialException("Test exception")
    
    # Create selve instance with port discovery disabled
    selve_instance = selve.Selve(port=None, discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Test check_port
    result = await selve_instance.check_port("COM1")
    assert result is False, "Expected port to be invalid due to SerialException"


@pytest.mark.asyncio
async def test_auto_discovery(logger, event_loop, mock_serial, mock_list_ports):
    """Test automatic port discovery."""
    # Create mock ports
    mock_port1 = MagicMock()
    mock_port1.device = "COM1"
    mock_port2 = MagicMock()
    mock_port2.device = "COM2"
    
    # Return multiple ports
    mock_list_ports.return_value = [mock_port1, mock_port2]
    
    # Setup mock serial instances  
    call_count = [0]
    def mock_serial_side_effect(port, *args, **kwargs):
        call_count[0] += 1
        logger.debug(f"Creating serial for port: {port} (call #{call_count[0]})")
        if port == "COM1":
            # For COM1, still create a mock but mark it as failed
            mock_instance = MagicMock()
            mock_instance.port = port
            mock_instance.is_open = False  # Mark as not open to indicate failure
            # Raise exception after creating the mock
            raise selve.SerialException("Test exception for COM1")
        # Create a mock instance for COM2
        mock_instance = MagicMock()
        mock_instance.port = port
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        mock_instance.write = MagicMock()
        mock_instance.flush = MagicMock()
        mock_instance.close = MagicMock()
        return mock_instance
        
    mock_serial.side_effect = mock_serial_side_effect
    
    # Create selve instance with no pre-configured port
    selve_instance = selve.Selve(port=None, discover=False, develop=True,
                               logger=logger, loop=event_loop)
    
    # Debug initial state
    logger.debug(f"Initial port: {selve_instance._port}")
    
    # Mock pingGateway to succeed only for COM2
    ping_call_count = [0]
    def ping_side_effect(*args, **kwargs):
        ping_call_count[0] += 1
        logger.debug(f"Ping call #{ping_call_count[0]}, args: {args}, kwargs: {kwargs}")
        # Check if we have a valid serial connection
        if hasattr(selve_instance, '_serial') and selve_instance._serial and hasattr(selve_instance._serial, 'port'):
            port_name = selve_instance._serial.port
            logger.debug(f"Ping for port: {port_name}")
            return port_name == "COM2"  # Only succeed for COM2
        logger.debug("Ping called but no valid serial connection")
        return False
        
    # Mock additional methods to avoid real hardware interactions
    with patch.object(selve_instance, 'pingGateway', new_callable=AsyncMock) as mock_ping:
        with patch.object(selve_instance, 'discover', new_callable=AsyncMock) as mock_discover:
            with patch.object(selve_instance, 'startWorker', new_callable=AsyncMock) as mock_start_worker:
                mock_ping.side_effect = ping_side_effect
                mock_discover.return_value = None
                mock_start_worker.return_value = None
                
                # Test setup with automatic discovery
                await selve_instance.setup(discover=True)
                logger.debug(f"Final port: {selve_instance._port}")
                assert selve_instance._port == "COM2", "Expected to discover COM2 as valid port"
