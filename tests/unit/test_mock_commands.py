import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from selve import Selve
from selve.device import SelveDevice
from selve.iveo import IveoDevice
from selve.util.protocol import SelveTypes, DeviceType, MovementState, CommunicationType
from selve.commands.command import (
    CommandDriveUp, CommandDriveDown, CommandStop, CommandDrivePos1,
    CommandDrivePos2, CommandDrivePos, CommandResultResponse
)
from selve.commands.iveo import IveoManual
from selve.util.errors import GatewayError


class TestMockCommands(unittest.TestCase):
    """Tests for commands using mocks to simulate various gateway conditions."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock logger
        self.logger = MagicMock()
        
        # Create a test loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create a Selve instance with mocked logger and loop
        with patch('selve.Selve._worker', AsyncMock()), \
             patch('selve.serial.Serial'):
            self.selve = Selve(port=None, develop=True, logger=self.logger, loop=self.loop)
            
            # Mock the execute command methods
            self.selve.executeCommand = AsyncMock()
            self.selve.executeCommandSyncWithResponse = AsyncMock()
            
            # Mock the device update method
            self.selve.updateCommeoDeviceValuesAsync = AsyncMock()
            
            # Initialize test devices
            self.commeo_device = SelveDevice(1, SelveTypes.DEVICE, DeviceType.SHUTTER)
            self.commeo_device.communicationType = CommunicationType.COMMEO
            self.commeo_device.name = "Test Commeo Device"
            
            self.iveo_device = IveoDevice(2, SelveTypes.IVEO, DeviceType.SHUTTER)
            self.iveo_device.communicationType = CommunicationType.IVEO
            self.iveo_device.name = "Test Iveo Device"
            
            # Add the test devices to the selve instance
            self.selve.devices = {
                "device": {1: self.commeo_device},
                "iveo": {2: self.iveo_device}
            }
            
    def tearDown(self):
        """Clean up the test environment."""
        self.loop.close()
        
    def test_move_device_up_command_success(self):
        """Test moveDeviceUp with a successful command response."""
        # Set up successful response
        self.selve.executeCommand.return_value = None  # Successful command execution
        
        # Run the test
        async def test_async():
            await self.selve.moveDeviceUp(self.commeo_device)
            
            # Check that the correct command was sent
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, CommandDriveUp)
            self.assertEqual(command.parameters[0][1], 1)  # Device ID
            
            # Check that the device state was updated
            self.assertEqual(self.commeo_device.state, MovementState.UP_ON)
            
            # Check that device values were updated
            self.selve.updateCommeoDeviceValuesAsync.assert_called_once_with(1)
            
        self.loop.run_until_complete(test_async())
        
    def test_move_device_up_command_exception(self):
        """Test moveDeviceUp when the gateway throws an exception."""
        # Set up exception in command execution
        self.selve.executeCommand.side_effect = GatewayError("Failed to communicate with gateway")
        
        # Run the test
        async def test_async():
            # The command should raise an exception
            with self.assertRaises(GatewayError):
                await self.selve.moveDeviceUp(self.commeo_device)
                
            # Check that the command was attempted
            self.selve.executeCommand.assert_called_once()
            
            # The device state should not have changed
            self.assertEqual(self.commeo_device.state, MovementState.UNKOWN)
            
        self.loop.run_until_complete(test_async())
        
    def test_move_device_with_no_devices(self):
        """Test moving a device when the gateway has no devices."""
        # Empty the devices dictionary but maintain structure
        self.selve.devices = {
            SelveTypes.DEVICE.value: {},
            SelveTypes.IVEO.value: {},
            SelveTypes.GROUP.value: {},
            SelveTypes.SENSIM.value: {},
            SelveTypes.SENSOR.value: {},
            SelveTypes.SENDER.value: {}
        }
        
        # Create a temporary device not registered with the gateway (use valid ID within mask range)
        temp_device = SelveDevice(63, SelveTypes.DEVICE, DeviceType.SHUTTER)
        temp_device.communicationType = CommunicationType.COMMEO
        
        # Run the test
        async def test_async():
            # The command should work even though the device isn't registered
            await self.selve.moveDeviceUp(temp_device)
            
            # Check that the command was sent
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, CommandDriveUp)
            self.assertEqual(command.parameters[0][1], 63)  # Device ID
            
        self.loop.run_until_complete(test_async())
        
    def test_move_iveo_device(self):
        """Test moving an IVEO device."""
        # Set up the mock method
        self.selve.setDeviceState = MagicMock()
        self.selve.setDeviceValue = MagicMock()
        self.selve.setDeviceTargetValue = MagicMock()
        
        # Run the test
        async def test_async():
            await self.selve.moveDeviceDown(self.iveo_device)
            
            # Check that the command was sent
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, IveoManual)
            
            # Check that device state was updated properly
            self.selve.setDeviceState.assert_any_call(2, MovementState.DOWN_ON, SelveTypes.IVEO)
            self.selve.setDeviceState.assert_any_call(2, MovementState.STOPPED_OFF, SelveTypes.IVEO)
            self.selve.setDeviceValue.assert_called_with(2, 100, SelveTypes.IVEO)
            self.selve.setDeviceTargetValue.assert_called_with(2, 100, SelveTypes.IVEO)
            
        self.loop.run_until_complete(test_async())
        
    def test_move_device_stop(self):
        """Test stopping a device."""
        # Run the test
        async def test_async():
            await self.selve.stopDevice(self.commeo_device)
            
            # Check that the command was sent
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, CommandStop)
            self.assertEqual(command.parameters[0][1], 1)  # Device ID
            
        self.loop.run_until_complete(test_async())
        
    def test_move_device_position(self):
        """Test moving a device to a specific position."""
        # Mock the moveDevicePos method if it doesn't exist
        if not hasattr(self.selve, 'moveDevicePos'):
            self.selve.moveDevicePos = AsyncMock()
        
        # Run the test
        async def test_async():
            # Test with 50% position
            await self.selve.moveDevicePos(self.commeo_device, 50)
            
            # Check that the command was sent
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, CommandDrivePos)
            self.assertEqual(command.parameters[0][1], 1)  # Device ID
            self.assertEqual(command.parameters[3][1], 32767)  # Position parameter (50% = 32767)
            
        self.loop.run_until_complete(test_async())
        
    def test_move_device_with_command_result_failure(self):
        """Test when moveDevice receives a failed CommandResultResponse."""
        # Set up the command response with success=False
        mock_response = MagicMock(spec=CommandResultResponse)
        mock_response.name = "selve.GW.command.result"
        mock_response.result = False  # Command failed
        
        # Configure executeCommandSyncWithResponse to return our mock
        self.selve.executeCommandSyncWithResponse.return_value = mock_response
        
        # Run the test
        async def test_async():
            # Replace executeCommand with executeCommandSyncWithResponse for this test
            original_execute = self.selve.executeCommand
            self.selve.executeCommand = self.selve.executeCommandSyncWithResponse
            
            try:
                # Execute the command - it should still run but return False
                result = await self.selve.moveDeviceUp(self.commeo_device)
                self.assertFalse(result)
                
                # Check that command was sent
                self.selve.executeCommandSyncWithResponse.assert_called_once()
                command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
                self.assertIsInstance(command, CommandDriveUp)
            finally:
                # Restore original method
                self.selve.executeCommand = original_execute
            
        self.loop.run_until_complete(test_async())
        
    def test_move_non_existent_device_type(self):
        """Test moving a device with an unrecognized communication type."""
        # Create a device with an unknown communication type
        unknown_device = SelveDevice(3, SelveTypes.DEVICE, DeviceType.SHUTTER)
        unknown_device.communicationType = 999  # Invalid communication type
        
        # Run the test
        async def test_async():
            # Should raise an exception because the device is not found in the gateway
            with self.assertRaises(AttributeError):
                await self.selve.moveDeviceUp(unknown_device)
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
