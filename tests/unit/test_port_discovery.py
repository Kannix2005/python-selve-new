import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
import sys

# Import the Selve package
import selve
from selve.util.errors import PortError, CommunicationError, ReadTimeoutError


class TestSelvePortDiscovery(unittest.TestCase):
    """Tests for Selve port discovery and initialization."""
    
    @classmethod
    def setUpClass(cls):
        # Set up logging
        cls.logger = logging.getLogger("PortDiscoveryTestLogger")
        cls.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        cls.logger.addHandler(handler)
        
        # Create a new event loop for the tests
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)

    @classmethod
    def tearDownClass(cls):
        cls.loop.close()

    def setUp(self):
        """Set up mock serial port and other mocks."""
        self.mock_serial_patcher = patch('selve.serial.Serial')
        self.mock_serial = self.mock_serial_patcher.start()
        
        # Mock list_ports to return test ports
        self.mock_list_ports_patcher = patch('selve.list_ports.comports')
        self.mock_list_ports = self.mock_list_ports_patcher.start()

    def tearDown(self):
        """Clean up mocks."""
        self.mock_serial_patcher.stop()
        self.mock_list_ports_patcher.stop()

    def test_list_ports_empty(self):
        """Test listing ports when no ports are available."""
        # No ports available
        self.mock_list_ports.return_value = []
        
        # Create selve instance
        selve_instance = selve.Selve(port=None, discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Test listing ports
        ports = selve_instance.list_ports()
        self.assertEqual(len(ports), 0, "Expected no ports, but got some")

    def test_list_ports_multiple(self):
        """Test listing multiple available ports."""
        # Create mock ports
        mock_port1 = MagicMock()
        mock_port1.device = "COM1"
        mock_port2 = MagicMock()
        mock_port2.device = "COM2"
        mock_port3 = MagicMock()
        mock_port3.device = "COM3"
        
        # Return multiple ports
        self.mock_list_ports.return_value = [mock_port1, mock_port2, mock_port3]
        
        # Create selve instance
        selve_instance = selve.Selve(port=None, discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Test listing ports - returns port objects, not device names
        ports = selve_instance.list_ports()
        self.assertEqual(len(ports), 3, "Expected 3 ports")
        # Check device attributes of port objects
        device_names = [port.device for port in ports]
        self.assertIn("COM1", device_names)
        self.assertIn("COM2", device_names)
        self.assertIn("COM3", device_names)

    def test_check_port_valid(self):
        """Test checking a valid port."""
        # Setup mock serial to successfully connect
        mock_serial_instance = self.mock_serial.return_value
        mock_serial_instance.is_open = True
        mock_serial_instance.in_waiting = 0  # Add missing attribute
        mock_serial_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        mock_serial_instance.write = MagicMock()
        mock_serial_instance.flush = MagicMock()
        mock_serial_instance.close = MagicMock()
        
        # Create selve instance with port discovery disabled
        selve_instance = selve.Selve(port=None, discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Mock the pingGateway method to return True for valid port
        with patch.object(selve_instance, 'pingGateway', new_callable=AsyncMock) as mock_ping:
            mock_ping.return_value = True
            
            # Test check_port
            async def test_async():
                result = await selve_instance.check_port("COM1")
                self.assertTrue(result, "Expected port to be valid")
                mock_ping.assert_called_once_with(fromConfigFlow=True)
            
            # Run the async test
            self.loop.run_until_complete(test_async())

    def test_check_port_invalid(self):
        """Test checking an invalid port that exists but doesn't respond correctly."""
        # Setup mock serial to successfully connect but ping fails
        mock_serial_instance = self.mock_serial.return_value
        mock_serial_instance.is_open = True
        
        # Create selve instance with port discovery disabled
        selve_instance = selve.Selve(port="COM1", discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Mock the ping method to return False (no proper gateway response)
        selve_instance.pingGatewayFromWorker = AsyncMock(return_value=False)
        
        # Test check_port
        async def test_async():
            result = await selve_instance.check_port("COM1")
            self.assertFalse(result, "Expected port to be invalid")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_check_port_serial_exception(self):
        """Test checking a port that raises a SerialException."""
        # Setup mock serial to raise an exception when opened
        self.mock_serial.side_effect = selve.SerialException("Test exception")
        
        # Create selve instance with port discovery disabled
        selve_instance = selve.Selve(port=None, discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Test check_port
        async def test_async():
            result = await selve_instance.check_port("COM1")
            self.assertFalse(result, "Expected port to be invalid due to SerialException")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_auto_discovery(self):
        """Test automatic port discovery."""
        # Create mock ports
        mock_port1 = MagicMock()
        mock_port1.device = "COM1"
        mock_port2 = MagicMock()
        mock_port2.device = "COM2"
        
        # Return multiple ports
        self.mock_list_ports.return_value = [mock_port1, mock_port2]
        
        # Setup mock serial instances  
        call_count = [0]
        def mock_serial_side_effect(port, *args, **kwargs):
            call_count[0] += 1
            self.logger.debug(f"Creating serial for port: {port} (call #{call_count[0]})")
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
            
        self.mock_serial.side_effect = mock_serial_side_effect
        
        # Create selve instance with no pre-configured port
        selve_instance = selve.Selve(port=None, discover=False, develop=True,
                                   logger=self.logger, loop=self.loop)
        
        # Debug initial state
        self.logger.debug(f"Initial port: {selve_instance._port}")
        
        # Mock pingGateway to succeed only for COM2
        ping_call_count = [0]
        def ping_side_effect(*args, **kwargs):
            ping_call_count[0] += 1
            self.logger.debug(f"Ping call #{ping_call_count[0]}, args: {args}, kwargs: {kwargs}")
            # Check if we have a valid serial connection
            if hasattr(selve_instance, '_serial') and selve_instance._serial and hasattr(selve_instance._serial, 'port'):
                port_name = selve_instance._serial.port
                self.logger.debug(f"Ping for port: {port_name}")
                return port_name == "COM2"  # Only succeed for COM2
            self.logger.debug("Ping called but no valid serial connection")
            return False
            
        # Mock additional methods to avoid real hardware interactions
        with patch.object(selve_instance, 'pingGateway', new_callable=AsyncMock) as mock_ping:
            with patch.object(selve_instance, 'discover', new_callable=AsyncMock) as mock_discover:
                with patch.object(selve_instance, 'startWorker', new_callable=AsyncMock) as mock_start_worker:
                    mock_ping.side_effect = ping_side_effect
                    mock_discover.return_value = None
                    mock_start_worker.return_value = None
                    
                    # Test setup with automatic discovery
                    async def test_async():
                        await selve_instance.setup(discover=True)
                        self.logger.debug(f"Final port: {selve_instance._port}")
                        self.assertEqual(selve_instance._port, "COM2", "Expected to discover COM2 as valid port")
                    
                    # Run the async test
                    self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
