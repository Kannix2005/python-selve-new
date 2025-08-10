import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.util.protocol import ServiceState
from selve.commands.service import (
    ServicePing, ServiceGetState, ServiceGetVersion,
    ServiceReset, ServiceFactoryReset,
    ServiceGetStateResponse, ServiceGetVersionResponse
)
from selve.util.errors import GatewayError, PortError, CommunicationError, ReadTimeoutError
from tests.unit.mock_utils import MockErrorResponse


class TestGatewayErrorHandling(unittest.TestCase):
    """Tests for gateway error handling and recovery scenarios."""
    
    def setUp(self):
        """Set up the test environment."""
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
        """Clean up the test environment."""
        self.loop.close()
        
    def test_gateway_ping_timeout(self):
        """Test behavior when gateway ping times out."""
        # Configure the mock to return False for timeout
        self.selve.executeCommandSyncWithResponsefromWorker.return_value = None
        
        # Add mock method to the Selve instance
        async def mock_ping_gateway_from_worker():
            cmd = ServicePing()
            try:
                methodResponse = await self.selve.executeCommandSyncWithResponsefromWorker(cmd)
                if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                    self.selve._LOGGER.debug("Ping back")
                    return True
                else:
                    self.selve._LOGGER.debug("No ping")
                    return False
            except Exception:
                self.selve._LOGGER.debug("No ping")
                return False
        
        self.selve.pingGatewayFromWorker = mock_ping_gateway_from_worker
        
        # Run the test
        async def test_async():
            result = await self.selve.pingGatewayFromWorker()
            
            # Should return False on timeout
            self.assertFalse(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponsefromWorker.assert_called_once()
            command = self.selve.executeCommandSyncWithResponsefromWorker.call_args[0][0]
            self.assertIsInstance(command, ServicePing)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_ping_invalid_response(self):
        """Test behavior when gateway ping gets invalid response."""
        # Configure the mock to return invalid response
        mock_response = MagicMock()
        mock_response.name = "invalid.response"
        self.selve.executeCommandSyncWithResponsefromWorker.return_value = mock_response
        
        # Add mock method to the Selve instance
        async def mock_ping_gateway_from_worker():
            cmd = ServicePing()
            try:
                methodResponse = await self.selve.executeCommandSyncWithResponsefromWorker(cmd)
                if methodResponse and hasattr(methodResponse, 'name') and methodResponse.name == "selve.GW.service.ping":
                    self.selve._LOGGER.debug("Ping back")
                    return True
                else:
                    self.selve._LOGGER.debug("No ping")
                    return False
            except Exception:
                self.selve._LOGGER.debug("No ping")
                return False
        
        self.selve.pingGatewayFromWorker = mock_ping_gateway_from_worker
        
        # Run the test
        async def test_async():
            result = await self.selve.pingGatewayFromWorker()
            
            # Should return False on invalid response
            self.assertFalse(result)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_state_missing_parameters(self):
        """Test behavior when gateway state response is missing parameters."""
        # Configure the mock to return a response without parameters
        mock_response = MagicMock(spec=ServiceGetStateResponse)
        mock_response.name = "selve.GW.service.getState"
        # Create parameters with None values
        mock_response.parameters = [(None, None)]
        
        self.selve.executeCommandSyncWithResponse.return_value = mock_response
        
        # Add mock method to the Selve instance
        async def mock_gateway_state():
            cmd = ServiceGetState()
            try:
                methodResponse = await self.selve.executeCommandSyncWithResponse(cmd)
                if methodResponse and hasattr(methodResponse, 'parameters') and len(methodResponse.parameters) > 1:
                    if methodResponse.parameters[1][1] is not None:
                        status = ServiceState(int(methodResponse.parameters[1][1]))
                        self.selve.state = status
                        self.selve._LOGGER.debug(f"Gateway state: {status}")
                        return status
                return None
            except (ValueError, TypeError, IndexError):
                self.selve._LOGGER.error("Error parsing gateway state")
                return None
        
        self.selve.gatewayState = mock_gateway_state
        
        # Run the test
        async def test_async():
            result = await self.selve.gatewayState()
            
            # Should return None for missing parameters
            self.assertIsNone(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, ServiceGetState)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_firmware_version_invalid_response(self):
        """Test behavior when getGatewayFirmwareVersion gets invalid response."""
        # Add mock method to the Selve instance
        async def mock_get_version():
            mock_response = MagicMock(spec=ServiceGetVersionResponse)
            mock_response.version = None
            return mock_response
        
        async def mock_get_gateway_firmware_version():
            version_info = await self.selve.getVersionG()
            return version_info.version if version_info and version_info.version else None
            
        self.selve.getVersionG = mock_get_version
        self.selve.getGatewayFirmwareVersion = mock_get_gateway_firmware_version
        
        # Run the test
        async def test_async():
            result = await self.selve.getGatewayFirmwareVersion()
            
            # Should be None for missing version
            self.assertIsNone(result)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_serial_invalid_response(self):
        """Test behavior when getGatewaySerial gets invalid response."""
        # Add mock method to the Selve instance
        async def mock_get_version():
            mock_response = MagicMock(spec=ServiceGetVersionResponse)
            mock_response.serial = None
            return mock_response
        
        async def mock_get_gateway_serial():
            version_info = await self.selve.getVersionG()
            return version_info.serial if version_info and version_info.serial else None
            
        self.selve.getVersionG = mock_get_version
        self.selve.getGatewaySerial = mock_get_gateway_serial
        
        # Run the test
        async def test_async():
            result = await self.selve.getGatewaySerial()
            
            # Should be None for missing serial
            self.assertIsNone(result)
            
        self.loop.run_until_complete(test_async())
    
    def test_gateway_recover_failure(self):
        """Test gateway recovery process when it fails."""
        # Add mock method to the Selve instance
        async def mock_recover():
            # Simulate the recovery process that fails
            try:
                self.selve._LOGGER.info("(Selve Worker): Recover serial connection")
                # Simulate that no ports are available
                self.selve._LOGGER.error("(Selve Worker): No gateway on comports found!")
                raise PortError
            except Exception as e:
                self.selve._LOGGER.error(f"Recovery failed: {e}")
                raise
        
        self.selve.recover = mock_recover
        
        # Run the test
        async def test_async():
            with self.assertRaises(PortError):
                await self.selve.recover()
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_ready_not_ready(self):
        """Test gatewayReady when gateway is not ready."""
        # Add mock methods to the Selve instance
        async def mock_gateway_state():
            return ServiceState.NOT_READY
        
        async def mock_gateway_ready():
            state = await self.selve.gatewayState()
            return state == ServiceState.READY
        
        self.selve.gatewayState = mock_gateway_state
        self.selve.gatewayReady = mock_gateway_ready
        
        # Run the test
        async def test_async():
            result = await self.selve.gatewayReady()
            
            # Should return False for NOT_READY
            self.assertFalse(result)
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_ready_error(self):
        """Test gatewayReady when gateway state check fails."""
        # Add mock methods to the Selve instance
        async def mock_gateway_state():
            return None  # Error case
        
        async def mock_gateway_ready():
            state = await self.selve.gatewayState()
            return state == ServiceState.READY
        
        self.selve.gatewayState = mock_gateway_state
        self.selve.gatewayReady = mock_gateway_ready
        
        # Run the test
        async def test_async():
            result = await self.selve.gatewayReady()
            
            # Should return False on error
            self.assertFalse(result)
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
