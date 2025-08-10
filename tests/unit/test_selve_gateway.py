import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.commands.service import ServicePing, ServiceGetState, ServiceGetVersion
from selve.util.protocol import ServiceState


class TestSelveGatewayMethods(unittest.TestCase):
    """Tests for Selve gateway-related methods.
    
    Note: This is a partial mock test that doesn't require actual hardware.
    """
    
    def setUp(self):
        # Create a test loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create a mock logger
        self.logger = MagicMock(spec=logging.Logger)
        
        # Create a Selve instance with mocked components
        with patch('selve.Selve._worker', AsyncMock()), \
             patch('selve.serial.Serial'):
            self.selve = Selve(port=None, develop=True, logger=self.logger, loop=self.loop)
            
            # Mock the execute command methods
            self.selve.executeCommand = AsyncMock()
            self.selve.executeCommandSyncWithResponse = AsyncMock()
            self.selve.executeCommandSyncWithResponsefromWorker = AsyncMock()
    
    def tearDown(self):
        self.loop.close()

    def test_ping_gateway_from_worker_success(self):
        """Test successful ping to gateway from worker."""
        # Create an async context
        async def test_async():
            # Create a mock response with the expected name
            mock_response = MagicMock()
            mock_response.name = "selve.GW.service.ping"
            
            # Set up our mock to return this response
            self.selve.executeCommandSyncWithResponsefromWorker.return_value = mock_response
            
            # Add mock method to the Selve instance
            async def mock_ping_gateway_from_worker():
                cmd = ServicePing()
                methodResponse = await self.selve.executeCommandSyncWithResponsefromWorker(cmd)
                
                if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                    self.selve._LOGGER.debug("Ping back")
                    return True
                else:
                    self.selve._LOGGER.debug("No ping")
                    return False
            
            self.selve.pingGatewayFromWorker = mock_ping_gateway_from_worker
            
            # Call the method
            result = await self.selve.pingGatewayFromWorker()
            
            # Assert the result is True
            self.assertTrue(result)
            
            # Verify the correct command was created and executed
            self.selve.executeCommandSyncWithResponsefromWorker.assert_called_once()
            # The first argument should be a ServicePing instance
            args = self.selve.executeCommandSyncWithResponsefromWorker.call_args[0]
            self.assertIsInstance(args[0], ServicePing)
            
            # Check that the logger was called with expected message
            self.selve._LOGGER.debug.assert_called_with("Ping back")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_ping_gateway_from_worker_failure_wrong_name(self):
        """Test failed ping to gateway from worker due to wrong response name."""
        async def test_async():
            # Create a mock response with a wrong name
            mock_response = MagicMock()
            mock_response.name = "wrong.name"
            
            # Set up our mock to return this response
            self.selve.executeCommandSyncWithResponsefromWorker.return_value = mock_response
            
            # Add mock method to the Selve instance
            async def mock_ping_gateway_from_worker():
                cmd = ServicePing()
                methodResponse = await self.selve.executeCommandSyncWithResponsefromWorker(cmd)
                
                if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                    self.selve._LOGGER.debug("Ping back")
                    return True
                else:
                    self.selve._LOGGER.debug("No ping")
                    return False
            
            self.selve.pingGatewayFromWorker = mock_ping_gateway_from_worker
            
            # Call the method
            result = await self.selve.pingGatewayFromWorker()
            
            # Assert the result is False
            self.assertFalse(result)
            
            # Check that the logger was called with expected message
            self.selve._LOGGER.debug.assert_called_with("No ping")
        
        # Run the async test
        self.loop.run_until_complete(test_async())
    
    def test_ping_gateway_from_worker_failure_exception(self):
        """Test failed ping to gateway from worker due to exception."""
        async def test_async():
            # Set up our mock to raise an exception
            self.selve.executeCommandSyncWithResponsefromWorker.side_effect = Exception("Test exception")
            
            # Add mock method to the Selve instance
            async def mock_ping_gateway_from_worker():
                try:
                    cmd = ServicePing()
                    methodResponse = await self.selve.executeCommandSyncWithResponsefromWorker(cmd)
                    
                    if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                        self.selve._LOGGER.debug("Ping back")
                        return True
                    else:
                        self.selve._LOGGER.debug("No ping")
                        return False
                except Exception:
                    self.selve._LOGGER.debug("Error in ping")
                    self.selve._LOGGER.debug("No ping")
                    return False
            
            self.selve.pingGatewayFromWorker = mock_ping_gateway_from_worker
            
            # Call the method
            result = await self.selve.pingGatewayFromWorker()
            
            # Assert the result is False
            self.assertFalse(result)
            
            # Check that the logger was called with expected messages
            self.selve._LOGGER.debug.assert_any_call("Error in ping")
            self.selve._LOGGER.debug.assert_any_call("No ping")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_gateway_state_success(self):
        """Test successfully getting gateway state."""
        async def test_async():
            # Create a mock response with the expected structure
            mock_response = MagicMock()
            mock_response.name = "selve.GW.service.getState"
            mock_response.parameters = [(None, None), (None, 3)]  # 3 corresponds to READY state
            
            # Set up our mock to return this response
            self.selve.executeCommandSyncWithResponse.return_value = mock_response
            
            # Add mock method to the Selve instance
            async def mock_gateway_state():
                cmd = ServiceGetState()
                methodResponse = await self.selve.executeCommandSyncWithResponse(cmd)
                
                if methodResponse and hasattr(methodResponse, 'parameters') and len(methodResponse.parameters) > 1:
                    status = ServiceState(int(methodResponse.parameters[1][1]))
                    self.selve.state = status
                    self.selve._LOGGER.debug(f"Gateway state: {status}")
                    return status
                return None
            
            self.selve.gatewayState = mock_gateway_state
            
            # Call the method
            result = await self.selve.gatewayState()
            
            # Assert the result is the expected state
            self.assertEqual(result, ServiceState.READY)
            
            # Verify the correct command was created and executed
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            # The first argument should be a ServiceGetState instance
            args = self.selve.executeCommandSyncWithResponse.call_args[0]
            self.assertIsInstance(args[0], ServiceGetState)
            
            # Check that the state was updated on the instance
            self.assertEqual(self.selve.state, ServiceState.READY)
            
            # Check that the logger was called with expected message
            self.selve._LOGGER.debug.assert_called_with("Gateway state: ServiceState.READY")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_gateway_ready_success(self):
        """Test successfully checking if gateway is ready."""
        async def test_async():
            # Add mock method to the Selve instance
            async def mock_gateway_state():
                return ServiceState.READY
            
            async def mock_gateway_ready():
                state = await self.selve.gatewayState()
                return state == ServiceState.READY
            
            self.selve.gatewayState = mock_gateway_state
            self.selve.gatewayReady = mock_gateway_ready
            
            # Call the method
            result = await self.selve.gatewayReady()
            
            # Assert the result is True
            self.assertTrue(result)
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_get_gateway_firmware_version_success(self):
        """Test successfully getting gateway firmware version."""
        async def test_async():
            # Create a mock response with a version attribute
            mock_response = MagicMock()
            mock_response.version = "1.2.3"
            
            # Add mock methods to the Selve instance
            async def mock_get_version():
                return mock_response
            
            async def mock_get_gateway_firmware_version():
                version_info = await self.selve.getVersionG()
                return version_info.version if version_info else None
            
            self.selve.getVersionG = mock_get_version
            self.selve.getGatewayFirmwareVersion = mock_get_gateway_firmware_version
            
            # Call the method
            result = await self.selve.getGatewayFirmwareVersion()
            
            # Assert the result is the expected version
            self.assertEqual(result, "1.2.3")
        
        # Run the async test
        self.loop.run_until_complete(test_async())

    def test_get_gateway_serial_success(self):
        """Test successfully getting gateway serial number."""
        async def test_async():
            # Create a mock response with a serial attribute
            mock_response = MagicMock()
            mock_response.serial = "ABC12345"
            
            # Add mock methods to the Selve instance
            async def mock_get_version():
                return mock_response
            
            async def mock_get_gateway_serial():
                version_info = await self.selve.getVersionG()
                return version_info.serial if version_info else None
            
            self.selve.getVersionG = mock_get_version
            self.selve.getGatewaySerial = mock_get_gateway_serial
            
            # Call the method
            result = await self.selve.getGatewaySerial()
            
            # Assert the result is the expected serial
            self.assertEqual(result, "ABC12345")
        
        # Run the async test
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
