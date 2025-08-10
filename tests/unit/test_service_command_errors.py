import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.util.protocol import (
    SelveTypes, DeviceType, ServiceState
)
from selve.commands.service import (
    ServicePing, ServiceGetState, ServiceGetVersion, 
    ServiceReset, ServiceFactoryReset,
    ServicePingResponse, ServiceGetStateResponse, ServiceGetVersionResponse,
    ServiceFactoryResetResponse
)
from selve.util.errors import (
    GatewayError, PortError, CommunicationError, 
    ReadTimeoutError
)
from tests.unit.mock_utils import MockErrorResponse


class TestServiceCommandErrors(unittest.TestCase):
    """Tests for service commands when gateway is not properly configured or responds with errors."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock logger
        self.logger = MagicMock(spec=logging.Logger)
        
        # Create a test loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Patch serial and worker to avoid actual hardware access
        self.worker_patcher = patch('selve.Selve._worker', AsyncMock())
        self.serial_patcher = patch('selve.serial.Serial')
        self.worker_mock = self.worker_patcher.start()
        self.serial_mock = self.serial_patcher.start()
        
        # Create a Selve instance with mocked components
        self.selve = Selve(port="COM99", discover=False, develop=True, 
                          logger=self.logger, loop=self.loop)
        
        # Mock the execute command methods
        self.selve.executeCommandSyncWithResponse = AsyncMock()
        self.selve._executeCommandSyncWithResponse = AsyncMock()
        
    def tearDown(self):
        """Clean up the test environment."""
        self.worker_patcher.stop()
        self.serial_patcher.stop()
        self.loop.close()
        
    def test_ping_gateway_timeout(self):
        """Test pinging the gateway when it times out."""
        # Configure the mock to time out
        self.selve.executeCommandSyncWithResponse.return_value = False
        
        # Run the test
        async def test_async():
            result = await self.selve.pingGateway()
            
            # Should return False indicating failure
            self.assertFalse(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServicePing)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_state_with_invalid_response(self):
        """Test getting gateway state when it returns an invalid response."""
        # Create an invalid response object
        invalid_response = MagicMock()
        invalid_response.name = "wrong.response.name"  # Not the expected response name
        
        # Configure the mock to return the invalid response
        self.selve.executeCommandSyncWithResponse.return_value = invalid_response
        
        # Run the test
        async def test_async():
            # Should return None for invalid response
            result = await self.selve.gatewayState()
            self.assertIsNone(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServiceGetState)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_ready_when_not_ready(self):
        """Test gateway ready check when gateway is not ready."""
        # Create a response indicating gateway is not ready
        not_ready_response = MagicMock(spec=ServiceGetStateResponse)
        not_ready_response.name = "selve.GW.service.getState"
        not_ready_response.state = ServiceState.NOT_READY
        
        # Configure the mock to return the not ready response
        self.selve.executeCommandSyncWithResponse.return_value = not_ready_response
        
        # Run the test
        async def test_async():
            result = await self.selve.gatewayReady()
            
            # Should return False indicating gateway is not ready
            self.assertFalse(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServiceGetState)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_reset_with_communication_error(self):
        """Test gateway reset when a communication error occurs."""
        # Configure the mock to raise a communication error
        self.selve.executeCommandSyncWithResponse.side_effect = CommunicationError("Connection lost")
        
        # Run the test
        async def test_async():
            # Should raise the exception
            with self.assertRaises(CommunicationError):
                await self.selve.resetGateway()
                
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServiceReset)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_factory_reset_with_error_response(self):
        """Test factory reset when an error response is received."""
        # Create an error response
        error_response = MockErrorResponse("Reset failed", "Gateway refused factory reset")
        
        # Configure the mock to return the error response
        self.selve.executeCommandSyncWithResponse.return_value = error_response
        
        # Mock gatewayState to return READY immediately to avoid infinite loop
        self.selve.gatewayState = AsyncMock(return_value=ServiceState.READY)
        
        # Run the test
        async def test_async():
            # Should return False for error response
            result = await self.selve.factoryResetGateway()
            self.assertFalse(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServiceFactoryReset)
            
        self.loop.run_until_complete(test_async())
        
    def test_get_gateway_version_with_no_serial_connection(self):
        """Test getting gateway version when there's no serial connection."""
        # Set serial to None to simulate no connection
        self.selve._serial = None
        
        # Mock getVersionG to return False (indicating failure)
        self.selve.getVersionG = AsyncMock(return_value=False)
        
        # Run the test
        async def test_async():
            # Should return False when no connection is available
            result = await self.selve.getGatewayFirmwareVersion()
            self.assertFalse(result)
            
        self.loop.run_until_complete(test_async())
        
    def test_get_gateway_version_with_timeout(self):
        """Test getting gateway version when a timeout occurs."""
        # Mock getVersionG to return False (indicating timeout)
        self.selve.getVersionG = AsyncMock(return_value=False)
        
        # Run the test
        async def test_async():
            # Should return False for timeout
            result = await self.selve.getGatewayFirmwareVersion()
            self.assertFalse(result)
            
            # Check that getVersionG was called
            self.selve.getVersionG.assert_called_once()
            
        self.loop.run_until_complete(test_async())
        
    def test_ping_sequence_with_multiple_failures(self):
        """Test the ping sequence with multiple failures before success."""
        # Configure mock to fail twice then succeed
        ping_responses = [False, False, True]
        
        def side_effect(*args, **kwargs):
            if len(ping_responses) > 0:
                return ping_responses.pop(0)
            return False
            
        self.selve.pingGateway = AsyncMock(side_effect=side_effect)
        
        # Run the test
        async def test_async():
            # Set up a method that tries to ping multiple times
            async def try_ping_until_success(max_attempts=5):
                for _ in range(max_attempts):
                    if await self.selve.pingGateway():
                        return True
                return False
                
            # Should eventually succeed
            result = await try_ping_until_success()
            self.assertTrue(result)
            
            # Should have been called 3 times (2 failures, 1 success)
            self.assertEqual(self.selve.pingGateway.call_count, 3)
            
        self.loop.run_until_complete(test_async())
        
    def test_service_command_with_port_error(self):
        """Test service command when a port error occurs."""
        # Configure the mock to raise a port error
        self.selve.executeCommandSyncWithResponse.side_effect = PortError("Invalid port")
        
        # Run the test
        async def test_async():
            # Should raise the exception
            with self.assertRaises(PortError):
                await self.selve.gatewayState()
                
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
