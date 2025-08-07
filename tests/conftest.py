"""
Conftest file for pytest configuration and shared fixtures
"""
import pytest
import pytest_asyncio
import asyncio
import logging
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selve import Selve


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing"""
    logger = Mock(spec=logging.Logger)
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_serial_port():
    """Mock serial port info"""
    port = Mock()
    port.device = 'COM3'
    port.description = 'USB Serial Port'
    port.vid = 0x1234
    port.pid = 0x5678
    return port


@pytest.fixture
def mock_serial_ports(mock_serial_port):
    """Mock list of serial ports"""
    return [mock_serial_port]


@pytest.fixture
def mock_list_ports(mock_serial_ports):
    """Mock serial.tools.list_ports"""
    with patch('selve.list_ports') as mock:
        mock.comports.return_value = mock_serial_ports
        yield mock


@pytest.fixture
def mock_serial():
    """Mock serial module"""
    with patch('selve.serial') as mock_module:
        # Create mock serial class
        mock_serial_class = Mock()
        mock_serial_instance = Mock()
        
        # Configure mock serial instance
        mock_serial_instance.is_open = True
        mock_serial_instance.in_waiting = 0
        mock_serial_instance.open = Mock()
        mock_serial_instance.close = Mock()
        mock_serial_instance.write = Mock()
        mock_serial_instance.flush = Mock()
        mock_serial_instance.readline = Mock(return_value=b'')
        
        # Configure mock serial class
        mock_serial_class.return_value = mock_serial_instance
        mock_module.Serial = mock_serial_class
        
        # Mock constants
        mock_module.EIGHTBITS = 8
        mock_module.PARITY_NONE = 'N'
        mock_module.STOPBITS_ONE = 1
        mock_module.SerialException = Exception
        
        yield mock_module


@pytest.fixture
def mock_serial_asyncio():
    """Mock serial_asyncio module"""
    async def mock_open_serial_connection(url, **kwargs):
        reader = AsyncMock()
        writer = AsyncMock()
        
        # Configure reader
        reader.at_eof.return_value = False
        reader.readuntil.return_value = b'test_response\n'
        
        # Configure writer
        writer.write = Mock()
        writer.drain = AsyncMock()
        writer.close = Mock()
        writer.wait_closed = AsyncMock()
        
        return reader, writer
    
    with patch('selve.serial_asyncio') as mock_module:
        mock_module.open_serial_connection = mock_open_serial_connection
        yield mock_module


@pytest.fixture
def mock_untangle():
    """Mock untangle XML parser"""
    with patch('selve.untangle') as mock_module:
        mock_result = Mock()
        mock_result.methodResponse.array.string = [Mock()]
        mock_result.methodResponse.array.string[0].cdata = "test_response"
        
        mock_module.parse.return_value = mock_result
        yield mock_module


@pytest.fixture
async def basic_selve_instance(mock_logger, mock_serial, mock_list_ports):
    """Create a basic Selve instance for testing"""
    selve = Selve(logger=mock_logger)
    yield selve
    
    # Cleanup
    try:
        await selve.stopGateway()
    except:
        pass


@pytest.fixture
async def connected_selve_instance(mock_logger, mock_serial_asyncio, mock_list_ports):
    """Create a Selve instance with mocked connection"""
    selve = Selve(port='COM3', logger=mock_logger)
    
    # Mock connection components
    selve._reader = AsyncMock()
    selve._writer = AsyncMock()
    selve._reader.at_eof.return_value = False
    selve._writer.write = Mock()
    selve._writer.drain = AsyncMock()
    
    yield selve
    
    # Cleanup
    try:
        await selve.stopGateway()
    except:
        pass


@pytest.fixture
def selve_instance(mock_logger, mock_serial, mock_list_ports):
    """Create a standard Selve instance for unit testing"""
    selve = Selve(port='COM3', logger=mock_logger)
    
    # Initialize basic attributes for testing
    selve._connected = False
    selve._running = False
    selve._worker_task = None
    selve._reader = None
    selve._writer = None
    selve._callbacks = set()
    selve._event_callbacks = set()
    
    # Mock devices dictionary if it doesn't exist
    if not hasattr(selve, 'devices'):
        from selve.util import SelveTypes
        selve.devices = {device_type.value: {} for device_type in SelveTypes}
    
    return selve


@pytest_asyncio.fixture
async def async_selve_instance(mock_logger, mock_serial, mock_list_ports):
    """Create a standard Selve instance for async unit testing"""
    selve = Selve(port='COM3', logger=mock_logger)
    
    # Initialize basic attributes for testing
    selve._connected = False
    selve._running = False
    selve._worker_task = None
    selve._reader = None
    selve._writer = None
    selve._callbacks = set()
    selve._event_callbacks = set()
    
    # Mock devices dictionary if it doesn't exist
    if not hasattr(selve, 'devices'):
        from selve.util import SelveTypes
        selve.devices = {device_type.value: {} for device_type in SelveTypes}
    
    yield selve
    
    # Cleanup
    try:
        if hasattr(selve, '_worker_task') and selve._worker_task:
            selve._worker_task.cancel()
        await selve.stopGateway()
    except:
        pass


# Hardware test fixtures (only available when hardware is present)
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "hardware: mark test as requiring hardware"
    )
    config.addinivalue_line(
        "markers", "stress: mark test as stress test (slow)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle markers"""
    # Skip hardware tests if no hardware available
    skip_hardware = pytest.mark.skip(reason="No hardware available")
    
    # Check if we should skip hardware tests
    hardware_available = os.environ.get('SELVE_TEST_PORT') or _detect_hardware()
    
    for item in items:
        if "hardware" in item.keywords and not hardware_available:
            item.add_marker(skip_hardware)


def _detect_hardware():
    """Detect if hardware is available for testing"""
    try:
        from serial.tools import list_ports
        
        ports = list_ports.comports()
        for port in ports:
            if any(keyword in port.description.lower() for keyword in 
                   ['usb', 'serial', 'cp210', 'ftdi', 'ch340']):
                return True
    except:
        pass
    return False


# Async test utilities
@pytest.fixture
def anyio_backend():
    """Use asyncio backend for anyio tests"""
    return 'asyncio'


# Test data fixtures
@pytest.fixture
def sample_device_response():
    """Sample device response XML"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <methodResponse>
        <array>
            <string>selve.GW.device.getValues</string>
            <int>1</int>
            <string>Test Device</string>
            <int>0</int>
            <int>50</int>
            <int>0</int>
        </array>
    </methodResponse>'''


@pytest.fixture
def sample_ping_response():
    """Sample ping response XML"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <methodResponse>
        <array>
            <string>selve.GW.service.ping</string>
        </array>
    </methodResponse>'''


@pytest.fixture
def sample_error_response():
    """Sample error response XML"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
    <methodResponse>
        <fault>
            <array>
                <string>Error message</string>
                <int>-1</int>
            </array>
        </fault>
    </methodResponse>'''
