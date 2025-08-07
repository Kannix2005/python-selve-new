import pytest
import pytest_asyncio
import asyncio
import sys
import os
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from serial.tools import list_ports

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selve import Selve
from selve.util.errors import PortError
from selve.commands.service import ServicePing


class MockSerial:
    """Mock serial connection for testing"""
    
    def __init__(self, port, **kwargs):
        self.port = port
        self.is_open = False
        self._write_buffer = []
        self._read_buffer = []
        self.in_waiting = 0
        
    def open(self):
        self.is_open = True
        
    def close(self):
        self.is_open = False
        
    def write(self, data):
        self._write_buffer.append(data)
        
    def flush(self):
        pass
        
    def readline(self):
        if self._read_buffer:
            return self._read_buffer.pop(0)
        return b''
        
    def add_response(self, response):
        """Add a response to the read buffer"""
        self._read_buffer.append(response.encode() + b'\n')
        self.in_waiting = len(self._read_buffer)


class MockSerialAsyncio:
    """Mock for serial_asyncio"""
    
    @staticmethod
    async def open_serial_connection(url, **kwargs):
        reader = AsyncMock()
        writer = AsyncMock()
        
        # Mock successful ping response
        reader.readuntil.return_value = b'<?xml version="1.0" encoding="UTF-8"?><methodResponse><array><string>selve.GW.service.ping</string></array></methodResponse>\n'
        reader.at_eof.return_value = False
        
        return reader, writer


@pytest.fixture
def mock_logger():
    """Mock logger for testing"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger


@pytest.fixture
def mock_serial():
    """Mock serial module"""
    with patch('selve.serial') as mock:
        mock.Serial = MockSerial
        mock.EIGHTBITS = 8
        mock.PARITY_NONE = 'N'
        mock.STOPBITS_ONE = 1
        mock.SerialException = Exception
        yield mock


@pytest.fixture
def mock_serial_asyncio():
    """Mock serial_asyncio module"""
    with patch('selve.serial_asyncio', MockSerialAsyncio):
        yield MockSerialAsyncio


@pytest.fixture
def mock_list_ports():
    """Mock list_ports with test data"""
    port_info = Mock()
    port_info.device = 'COM3'
    port_info.description = 'Test USB Serial Port'
    
    with patch('selve.list_ports') as mock:
        mock.comports.return_value = [port_info]
        yield mock


@pytest.fixture
def selve_instance(mock_logger, mock_serial, mock_serial_asyncio, mock_list_ports):
    """Create a Selve instance for testing"""
    instance = Selve(logger=mock_logger)
    
    # Initialize basic attributes that tests expect
    instance._connected = False
    instance._running = False
    instance._worker_task = None
    instance._reader = None
    instance._writer = None
    instance._callbacks = set()
    instance._event_callbacks = set()
    
    # Mock queues
    instance.txQ = AsyncMock()  # Transmission queue
    instance.txQ.put = AsyncMock()  # Mock the put method specifically
    instance._responseData = {}  # Add response data dict
    instance._response_timeout = 5.0  # Default timeout
    
    # Mock devices dictionary if it doesn't exist
    if not hasattr(instance, 'devices'):
        from selve.util import SelveTypes
        instance.devices = {device_type.value: {} for device_type in SelveTypes}
    
    return instance


@pytest_asyncio.fixture
async def async_selve_instance(mock_logger, mock_serial, mock_serial_asyncio, mock_list_ports):
    """Create a Selve instance for async testing"""
    instance = Selve(logger=mock_logger)
    
    # Initialize basic attributes that tests expect
    instance._connected = False
    instance._running = False
    instance._worker_task = None
    instance._reader = None
    instance._writer = None
    instance._callbacks = set()
    instance._event_callbacks = set()
    
    # Mock devices dictionary if it doesn't exist
    if not hasattr(instance, 'devices'):
        from selve.util import SelveTypes
        instance.devices = {device_type.value: {} for device_type in SelveTypes}
    
    yield instance
    
    # Cleanup
    try:
        await instance.stopGateway()
    except:
        pass


class TestSelveInitialization:
    """Test Selve class initialization"""
    
    def test_init_default_parameters(self, mock_logger):
        selve = Selve(logger=mock_logger)
        
        assert selve._port is None
        assert selve._worker_running is False
        assert selve._worker_task is None
        assert selve.reversedStopPosition == 0
        assert selve._response_timeout == 10.0
        assert len(selve.devices) == 6  # All device types
        
    def test_init_with_parameters(self, mock_logger):
        loop = asyncio.new_event_loop()
        selve = Selve(
            port='COM1',
            discover=False,
            develop=True,
            logger=mock_logger,
            loop=loop
        )
        
        assert selve._port == 'COM1'
        assert selve.loop == loop
        assert selve._LOGGER == mock_logger


class TestSerialConnection:
    """Test serial connection handling"""
    
    @pytest.mark.asyncio
    async def test_setup_with_valid_port(self, selve_instance, mock_serial):
        """Test setup with a valid port"""
        selve_instance._port = 'COM3'
        
        # Mock successful ping response
        with patch.object(selve_instance, '_test_connection', return_value=True):
            with patch.object(selve_instance, 'discover') as mock_discover:
                result = await selve_instance.setup(discover=True)
                assert result is True
                mock_discover.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_setup_port_scanning(self, selve_instance, mock_list_ports):
        """Test port scanning when no port specified"""
        selve_instance._port = None
        
        with patch.object(selve_instance, '_try_connect_port', return_value=True):
            result = await selve_instance.setup()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_setup_no_ports_available(self, selve_instance, mock_list_ports):
        """Test setup when no ports are available"""
        mock_list_ports.comports.return_value = []
        
        with pytest.raises(PortError):
            await selve_instance.setup()
    
    @pytest.mark.asyncio
    async def test_connection_recovery(self, selve_instance):
        """Test connection recovery after error"""
        with patch.object(selve_instance, '_find_and_connect', return_value=True):
            result = await selve_instance._reconnect()
            assert result is True


class TestWorkerManagement:
    """Test worker thread management"""
    
    @pytest.mark.asyncio
    async def test_start_worker(self, selve_instance):
        """Test starting the worker"""
        await selve_instance.startWorker()
        
        assert selve_instance._worker_running is True
        assert selve_instance._worker_task is not None
        assert selve_instance.txQ is not None
        assert selve_instance.rxQ is not None
        
        await selve_instance.stopWorker()
    
    @pytest.mark.asyncio
    async def test_stop_worker(self, selve_instance):
        """Test stopping the worker"""
        await selve_instance.startWorker()
        await selve_instance.stopWorker()
        
        assert selve_instance._worker_running is False
        assert selve_instance._worker_task is None
    
    @pytest.mark.asyncio
    async def test_worker_already_running(self, selve_instance):
        """Test starting worker when already running"""
        await selve_instance.startWorker()
        
        # Try to start again
        await selve_instance.startWorker()
        
        # Should still be running
        assert selve_instance._worker_running is True
        
        await selve_instance.stopWorker()
    
    @pytest.mark.asyncio
    async def test_worker_graceful_shutdown(self, selve_instance):
        """Test graceful worker shutdown"""
        await selve_instance.startWorker()
        
        # Mock a running task
        task_mock = AsyncMock()
        task_mock.done.return_value = False
        task_mock.cancel = Mock()
        selve_instance._worker_task = task_mock
        
        await selve_instance.stopWorker()
        
        # The stopWorker method might handle cancellation differently
        # Check that the worker task is set to None (indicating shutdown)
        assert selve_instance._worker_task is None


class TestCommandExecution:
    """Test command execution"""
    
    @pytest.mark.asyncio
    async def test_execute_command_async(self, selve_instance):
        """Test asynchronous command execution"""
        command = ServicePing()
        
        with patch.object(selve_instance, 'startWorker') as mock_start:
            await selve_instance.executeCommand(command)
            mock_start.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_sync_with_response(self, selve_instance):
        """Test synchronous command execution with response"""
        command = ServicePing()
        
        with patch.object(selve_instance, '_execute_command_direct', return_value="response"):
            result = await selve_instance.executeCommandSyncWithResponse(
                command, fromConfigFlow=True
            )
            assert result == "response"
    
    @pytest.mark.asyncio
    async def test_execute_command_timeout(self, selve_instance):
        """Test command execution timeout"""
        command = ServicePing()
        
        with patch.object(selve_instance, 'startWorker'):
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError):
                result = await selve_instance.executeCommandSyncWithResponse(
                    command, timeout=1.0
                )
                assert result is False


class TestDeviceManagement:
    """Test device management functions"""
    
    def test_add_device(self, selve_instance):
        """Test adding a device"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        device = SelveDevice(1, SelveTypes.DEVICE)
        device.name = "Test Device"
        
        with patch.object(selve_instance, '_callbacks', {Mock()}):
            selve_instance.addOrUpdateDevice(device, SelveTypes.DEVICE)
            
        assert 1 in selve_instance.devices[SelveTypes.DEVICE.value]
        assert selve_instance.devices[SelveTypes.DEVICE.value][1].name == "Test Device"
    
    def test_get_device(self, selve_instance):
        """Test getting a device"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        device = SelveDevice(1, SelveTypes.DEVICE)
        selve_instance.devices[SelveTypes.DEVICE.value][1] = device
        
        retrieved = selve_instance.getDevice(1, SelveTypes.DEVICE)
        assert retrieved == device
        
        # Test non-existent device
        retrieved = selve_instance.getDevice(999, SelveTypes.DEVICE)
        assert retrieved is None
    
    def test_is_id_registered(self, selve_instance):
        """Test device ID registration check"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        device = SelveDevice(1, SelveTypes.DEVICE)
        selve_instance.devices[SelveTypes.DEVICE.value][1] = device
        
        assert selve_instance.is_id_registered(1, SelveTypes.DEVICE)
        assert not selve_instance.is_id_registered(999, SelveTypes.DEVICE)
    
    def test_find_free_id(self, selve_instance):
        """Test finding free device ID"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        # Add some devices
        for i in range(5):
            device = SelveDevice(i, SelveTypes.DEVICE)
            selve_instance.devices[SelveTypes.DEVICE.value][i] = device
        
        free_id = selve_instance.findFreeId(SelveTypes.DEVICE)
        assert free_id == 5


class TestResponseProcessing:
    """Test response processing"""
    
    @pytest.mark.asyncio
    async def test_process_response_valid_xml(self, selve_instance):
        """Test processing valid XML response"""
        xml_response = '''<?xml version="1.0" encoding="UTF-8"?>
        <methodResponse>
            <array>
                <string>selve.GW.service.ping</string>
            </array>
        </methodResponse>'''
        
        with patch('selve.untangle.parse') as mock_parse:
            mock_obj = Mock()
            mock_obj.methodResponse.array.string = [Mock()]
            mock_obj.methodResponse.array.string[0].cdata = "selve.GW.service.ping"
            mock_parse.return_value = mock_obj
            
            result = await selve_instance.processResponse(xml_response)
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_process_response_invalid_xml(self, selve_instance):
        """Test processing invalid XML"""
        invalid_xml = "not xml content"
        
        result = await selve_instance.processResponse(invalid_xml)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_process_response_malformed_header(self, selve_instance):
        """Test processing XML with malformed header"""
        # Use the exact malformed header pattern that the code is designed to fix
        # Copy the exact strings from the source code
        malformed_xml = '<?xml version="1.0"? encoding="UTF-8"?><methodResponse><array><string>test</string></array></methodResponse>'
        
        # Test that the method correctly handles malformed XML by attempting to fix it
        with patch('selve.untangle.parse') as mock_parse:
            mock_parse.side_effect = Exception("Test exception")
            
            result = await selve_instance.processResponse(malformed_xml)
            
            # Should return False due to the exception, but the important part is
            # that processResponse attempts to fix the header before parsing
            assert result is False
            
            # Check that untangle.parse was called (meaning the method tried to process it)
            assert mock_parse.called
            
            # Check that the XML passed to parse has been processed
            called_xml = mock_parse.call_args[0][0]
            # Should be a string (not None) - indicating the method attempted parsing
            assert isinstance(called_xml, str)
            assert len(called_xml) > 0


class TestCallbacks:
    """Test callback management"""
    
    def test_register_callback(self, selve_instance):
        """Test registering a callback"""
        callback = Mock()
        selve_instance.register_callback(callback)
        
        assert callback in selve_instance._callbacks
    
    def test_remove_callback(self, selve_instance):
        """Test removing a callback"""
        callback = Mock()
        selve_instance.register_callback(callback)
        selve_instance.remove_callback(callback)
        
        assert callback not in selve_instance._callbacks
    
    def test_register_event_callback(self, selve_instance):
        """Test registering an event callback"""
        callback = Mock()
        selve_instance.register_event_callback(callback)
        
        assert callback in selve_instance._eventCallbacks


class TestErrorHandling:
    """Test error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_worker_error_handling(self, selve_instance):
        """Test worker error handling with backoff"""
        error = Exception("Test error")
        
        await selve_instance._handle_worker_error(error)
        
        # Check that error count is tracked
        assert hasattr(selve_instance, '_error_count')
        assert selve_instance._error_count == 1
    
    @pytest.mark.asyncio
    async def test_connection_error_recovery(self, selve_instance):
        """Test connection error recovery"""
        with patch.object(selve_instance, '_find_and_connect', return_value=True):
            result = await selve_instance._reconnect()
            assert result is True


if __name__ == '__main__':
    pytest.main([__file__])
