import pytest
import logging
import sys
import asyncio
import nest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Stub out serialx before any selve import so the protobuf/aioesphomeapi
# version conflict in serialx's optional esphome platform never fires.
_serialx_mock = MagicMock()
_serialx_mock.Parity = MagicMock()
_serialx_mock.Parity.NONE = "N"
_serialx_mock.open_serial_connection = AsyncMock(
    return_value=(MagicMock(), MagicMock())
)
sys.modules.setdefault("serialx", _serialx_mock)
sys.modules.setdefault("serialx.platforms", MagicMock())
sys.modules.setdefault("serialx.platforms.serial_esphome", MagicMock())

# Ermöglicht das Ausführen von async-Funktionen in einem bereits laufenden Event-Loop
# Dies ist wichtig für die Integration-Tests
nest_asyncio.apply()


@pytest.fixture(scope='session')
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def logger():
    """Set up a logger that can be used for tests."""
    logger = logging.getLogger("TestLogger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


@pytest.fixture
def mock_serial():
    """Mock the SerialTransport for testing."""
    with patch('selve.util.serial_transport.SerialTransport') as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        mock_instance.is_open = True
        mock_instance.ensure_open = AsyncMock()
        mock_instance.start_reader = AsyncMock()
        mock_instance.stop_reader = AsyncMock()
        mock_instance.write = AsyncMock()
        mock_instance.shutdown = AsyncMock()
        yield mock


@pytest.fixture
def mock_list_ports():
    """Mock the _comports function."""
    with patch('selve._comports') as mock:
        # Create a mock port
        mock_port = MagicMock()
        mock_port.device = "COM3"
        mock.return_value = [mock_port]
        yield mock


@pytest.fixture
def mock_selve(event_loop, logger, mock_serial, mock_list_ports):
    """Create a mocked Selve instance."""
    from selve import Selve
    
    # Patch the required methods
    with patch.object(Selve, 'executeCommandSyncWithResponsefromWorker') as mock_execute, \
         patch.object(Selve, 'executeCommandSyncWithResponse') as mock_execute_sync, \
         patch.object(Selve, 'check_port') as mock_check_port:
        
        # Configure mocks
        mock_check_port.return_value = asyncio.Future()
        mock_check_port.return_value.set_result(True)
        
        mock_execute.return_value = asyncio.Future()
        mock_response = MagicMock()
        mock_response.name = "selve.GW.service.ping"
        mock_execute.return_value.set_result(mock_response)
        
        mock_execute_sync.return_value = asyncio.Future()
        mock_execute_sync.return_value.set_result(mock_response)
        
        # Create the Selve instance
        selve_instance = Selve(port="COM3", discover=False, develop=True,
                              logger=logger, loop=event_loop)
        
        yield selve_instance
