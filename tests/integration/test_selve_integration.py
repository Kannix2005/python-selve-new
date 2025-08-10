import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
import sys
from selve import Selve
from selve.util.protocol import ServiceState


class TestSelveIntegration(unittest.TestCase):
    """Integration tests for Selve class with mocked hardware."""
    
    @classmethod
    def setUpClass(cls):
        # Set up logging
        cls.logger = logging.getLogger("TestLogger")
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
        
        # Setup mock port
        mock_port = MagicMock()
        mock_port.device = "COM3"
        self.mock_list_ports.return_value = [mock_port]
        
        # Create the Selve instance with mock hardware
        self.selve = Selve(port="COM3", discover=False, develop=True, 
                          logger=self.logger, loop=self.loop)

    def tearDown(self):
        """Clean up mocks."""
        self.mock_serial_patcher.stop()
        self.mock_list_ports_patcher.stop()

    def test_list_ports(self):
        """Test listing available serial ports."""
        ports = self.selve.list_ports()
        self.assertEqual(len(ports), 1)
        # Check the device attribute of the port object
        self.assertEqual(ports[0].device, "COM3")

    def test_setup_and_ping(self):
        """Test setting up the connection and pinging the gateway."""
        # Mock the setup responses
        mock_instance = self.mock_serial.return_value
        mock_instance.is_open = True
        mock_instance.in_waiting = 0
        mock_instance.readline.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        mock_instance.write = MagicMock()
        mock_instance.flush = MagicMock()
        
        # Mock a successful ping response
        ping_response = MagicMock()
        ping_response.name = "selve.GW.service.ping"
        
        # Mock executeCommandSyncWithResponse to return successful ping
        self.selve.executeCommandSyncWithResponse = AsyncMock(return_value=ping_response)
        self.selve.executeCommandSyncWithResponsefromWorker = AsyncMock(return_value=ping_response)
        
        # Test setup and ping
        async def run_test():
            await self.selve.setup()
            # Test ping from worker
            result = await self.selve.pingGatewayFromWorker()
            self.assertTrue(result)
        
        # Run the test
        self.loop.run_until_complete(run_test())

    def test_gateway_state_ready(self):
        """Test checking if gateway is in READY state."""
        # Mock gateway state response
        mock_state_response = MagicMock()
        mock_state_response.name = "selve.GW.service.getState"
        mock_state_response.parameters = [(None, 3)]  # 3 is READY state - corrected value
        
        # Mock the executeCommandSyncWithResponse method
        self.selve.executeCommandSyncWithResponse = AsyncMock(return_value=mock_state_response)
        
        async def run_test():
            # Get gateway state
            state = await self.selve.gatewayState()
            self.assertEqual(state, ServiceState.READY)
            
            # Check if gateway is ready
            is_ready = await self.selve.gatewayReady()
            self.assertTrue(is_ready)
        
        # Run the test
        self.loop.run_until_complete(run_test())

    def test_get_gateway_version(self):
        """Test getting gateway version information."""
        # Mock version response
        mock_version_response = MagicMock()
        mock_version_response.name = "selve.GW.service.getVersion"
        mock_version_response.serial = "123456"
        mock_version_response.version = "1.2.3"
        
        # Mock the executeCommandSyncWithResponse method
        self.selve.executeCommandSyncWithResponse = AsyncMock(return_value=mock_version_response)
        
        async def run_test():
            # Get version directly
            version_response = await self.selve.getVersionG()
            self.assertEqual(version_response, mock_version_response)
            
            # Get firmware version
            firmware = await self.selve.getGatewayFirmwareVersion()
            self.assertEqual(firmware, "1.2.3")
            
            # Get serial number
            serial = await self.selve.getGatewaySerial()
            self.assertEqual(serial, "123456")
        
        # Run the test
        self.loop.run_until_complete(run_test())


if __name__ == "__main__":
    unittest.main()
