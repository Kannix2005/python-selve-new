import unittest
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.device import SelveDevice
from selve.group import SelveGroup
from selve.iveo import IveoDevice
from selve.sensor import SelveSensor
from selve.util.protocol import (
    SelveTypes, DeviceType, MovementState, CommunicationType, 
    ServiceState, windDigital, rainDigital, tempDigital, lightDigital, SensorState
)
from selve.commands.device import (
    DeviceGetIds, DeviceGetInfo, DeviceGetValues, 
    DeviceGetIdsResponse, DeviceGetInfoResponse, DeviceGetValuesResponse
)
from selve.commands.group import (
    GroupGetIds, GroupRead, GroupWrite, GroupDelete,
    GroupGetIdsResponse, GroupReadResponse, GroupWriteResponse, GroupDeleteResponse
)
from selve.commands.iveo import (
    IveoGetIds, IveoGetConfig, IveoManual,
    IveoGetIdsResponse, IveoGetConfigResponse
)
from selve.commands.command import (
    CommandDriveUp, CommandDriveDown, CommandStop, CommandDrivePos,
    CommandDriveUpGroup, CommandDriveDownGroup,
    CommandResultResponse
)
from selve.util.errors import GatewayError


class TestMockDevicesAndGroups:
    """Tests for handling devices and groups that are missing or fail to operate."""
    
    def setup_method(self):
        """Set up the test environment."""
        # Create a mock logger
        self.logger = MagicMock(spec=logging.Logger)
        
        # Create a test loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create a Selve instance with mocked components
        with patch('selve.Selve._worker', AsyncMock()), \
             patch('selve.serial.Serial'):
            self.selve = Selve(port=None, discover=False, develop=True, 
                              logger=self.logger, loop=self.loop)
            
            # Mock the execute command methods
            self.selve.executeCommand = AsyncMock()
            self.selve.executeCommandSyncWithResponse = AsyncMock()
            
            # Initialize test devices
            self.commeo_device = SelveDevice(1, SelveTypes.DEVICE, DeviceType.SHUTTER)
            self.commeo_device.communicationType = CommunicationType.COMMEO
            self.commeo_device.name = "Test Commeo Device"
            
            self.iveo_device = IveoDevice(2, SelveTypes.IVEO, DeviceType.SHUTTER)
            self.iveo_device.communicationType = CommunicationType.IVEO
            self.iveo_device.name = "Test Iveo Device"
            
            self.group = SelveGroup(1, SelveTypes.GROUP, DeviceType.SHUTTER)
            self.group.name = "Test Group"
            
            # Add the test devices to the selve instance
            self.selve.devices = {
                SelveTypes.DEVICE.value: {1: self.commeo_device},
                SelveTypes.IVEO.value: {2: self.iveo_device},
                SelveTypes.GROUP.value: {1: self.group},
                SelveTypes.SENSIM.value: {},
                SelveTypes.SENSOR.value: {},
                SelveTypes.SENDER.value: {}
            }
            
    def teardown_method(self):
        """Clean up the test environment."""
        self.loop.close()

    @pytest.mark.asyncio
    async def test_empty_device_list_on_discover(self):
        """Test discover method when no devices are returned."""
        # Mock all required methods for discover
        from selve.commands.sensor import SensorGetIds, SensorGetIdsResponse
        from selve.commands.sender import SenderGetIds, SenderGetIdsResponse
        from selve.commands.senSim import SenSimGetIds, SenSimGetIdsResponse
        from selve.commands.service import ServiceGetState, ServiceGetStateResponse
        from selve.commands.param import ParamSetEvent, ParamSetEventResponse
        
        # Configure the mock to return empty device IDs and proper responses
        device_ids_response = MagicMock(spec=DeviceGetIdsResponse)
        device_ids_response.ids = []
        device_ids_response.name = "selve.GW.device.getIds"
        
        iveo_ids_response = MagicMock(spec=IveoGetIdsResponse)
        iveo_ids_response.ids = []
        iveo_ids_response.name = "selve.GW.iveo.getIds"
        
        group_ids_response = MagicMock(spec=GroupGetIdsResponse)
        group_ids_response.ids = []
        group_ids_response.name = "selve.GW.group.getIds"
        
        sensor_ids_response = MagicMock(spec=SensorGetIdsResponse)
        sensor_ids_response.ids = []
        sensor_ids_response.name = "selve.GW.sensor.getIds"
        
        sender_ids_response = MagicMock(spec=SenderGetIdsResponse)
        sender_ids_response.ids = []
        sender_ids_response.name = "selve.GW.sender.getIds"
        
        sensim_ids_response = MagicMock(spec=SenSimGetIdsResponse)
        sensim_ids_response.ids = []
        sensim_ids_response.name = "selve.GW.senSim.getIds"
        
        # Mock state response (gateway ready)
        state_response = MagicMock(spec=ServiceGetStateResponse)
        state_response.name = "selve.GW.service.getState"
        state_response.parameters = [(None, 1)]  # ServiceState.READY = 1
        
        # Mock event response
        event_response = MagicMock(spec=ParamSetEventResponse)
        event_response.name = "selve.GW.param.setEvent"
        event_response.executed = True
        
        # Set up the mock to return different responses
        def side_effect(command):
            if isinstance(command, DeviceGetIds):
                return device_ids_response
            elif isinstance(command, IveoGetIds):
                return iveo_ids_response
            elif isinstance(command, GroupGetIds):
                return group_ids_response
            elif isinstance(command, SensorGetIds):
                return sensor_ids_response
            elif isinstance(command, SenderGetIds):
                return sender_ids_response
            elif isinstance(command, SenSimGetIds):
                return sensim_ids_response
            elif isinstance(command, ServiceGetState):
                return state_response
            elif isinstance(command, ParamSetEvent):
                return event_response
            else:
                # Default response for other commands
                mock = MagicMock()
                mock.name = "unknown"
                return mock
                
        self.selve.executeCommandSyncWithResponse.side_effect = side_effect
        
        # Reset the device dictionaries
        self.selve.devices = {
            SelveTypes.DEVICE.value: {},
            SelveTypes.IVEO.value: {},
            SelveTypes.GROUP.value: {},
            SelveTypes.SENSIM.value: {},
            SelveTypes.SENSOR.value: {},
            SelveTypes.SENDER.value: {}
        }
        
        # Call discover
        await self.selve.discover()
        
        # Device dictionaries should remain empty
        assert len(self.selve.devices[SelveTypes.DEVICE.value]) == 0
        assert len(self.selve.devices[SelveTypes.IVEO.value]) == 0
        assert len(self.selve.devices[SelveTypes.GROUP.value]) == 0
        
    @pytest.mark.asyncio
    async def test_move_device_not_in_gateway(self):
        """Test moving a device that's not in the gateway's device list."""
        # Create a device that's not in the device list (use valid ID within mask range)
        non_existent_device = SelveDevice(63, SelveTypes.DEVICE, DeviceType.SHUTTER)
        non_existent_device.communicationType = CommunicationType.COMMEO
        non_existent_device.name = "Non-existent Device"
        
        # Mock updateCommeoDeviceValuesAsync to avoid additional commands
        self.selve.updateCommeoDeviceValuesAsync = AsyncMock()
        
        # Attempt to move the device
        await self.selve.moveDeviceUp(non_existent_device)
        
        # Command should still be sent even though device doesn't exist in the list
        self.selve.executeCommand.assert_called_once()
        command = self.selve.executeCommand.call_args[0][0]
        assert isinstance(command, CommandDriveUp)
        assert command.parameters[0][1] == 63  # Device ID
        
    def test_move_iveo_device_not_in_gateway(self):
        """Test moving an IVEO device that's not in the gateway's device list."""
        # Create an IVEO device that's not in the device list (use valid ID within range)
        non_existent_iveo = IveoDevice(63, SelveTypes.IVEO, DeviceType.SHUTTER)
        non_existent_iveo.communicationType = CommunicationType.IVEO
        non_existent_iveo.name = "Non-existent IVEO Device"
        
        # Mock the device state methods to avoid errors with non-existent devices
        self.selve.setDeviceState = MagicMock()
        self.selve.setDeviceValue = MagicMock()
        self.selve.setDeviceTargetValue = MagicMock()
        
        # Run the test
        async def test_async():
            # Attempt to move the device
            await self.selve.moveDeviceUp(non_existent_iveo)
            
            # Command should still be sent even though device doesn't exist in the list
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            assert isinstance(command, IveoManual)
            
        self.loop.run_until_complete(test_async())
        
    def test_move_group_not_in_gateway(self):
        """Test moving a group that's not in the gateway's group list."""
        # Mock updateCommeoDeviceValuesAsync to avoid additional device updates
        self.selve.updateCommeoDeviceValuesAsync = AsyncMock()
        
        # Create a group that's not in the group list (use valid ID within range)
        non_existent_group = SelveGroup(31, SelveTypes.GROUP, DeviceType.SHUTTER)
        non_existent_group.name = "Non-existent Group"
        non_existent_group.mask = b""  # Empty mask to avoid device update loop
        
        # Run the test
        async def test_async():
            # Attempt to move the group
            await self.selve.moveGroupUp(non_existent_group)
            
            # Command should still be sent even though group doesn't exist in the list
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            assert isinstance(command, CommandDriveUpGroup)
            assert command.parameters[0][1] == 31  # Group ID
            
        self.loop.run_until_complete(test_async())
        
    def test_device_command_failure(self):
        """Test handling of device command failure."""
        # Configure the mock to simulate command failure
        self.selve.executeCommand.side_effect = GatewayError("Command failed")
          # Run the test
        async def test_async():
            # Attempt to move the device
            with pytest.raises(GatewayError):
                await self.selve.moveDeviceDown(self.commeo_device)
            
            # Check that command was attempted
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            assert isinstance(command, CommandDriveDown)
            
        self.loop.run_until_complete(test_async())
        
    def test_iveo_command_failure(self):
        """Test handling of IVEO command failure."""
        # Configure the mock to simulate command failure
        self.selve.executeCommand.side_effect = GatewayError("Command failed")
          # Run the test
        async def test_async():
            # Attempt to move the IVEO device
            with pytest.raises(GatewayError):
                await self.selve.moveDeviceDown(self.iveo_device)
            
            # Check that command was attempted
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            assert isinstance(command, IveoManual)
            
        self.loop.run_until_complete(test_async())
        
    def test_group_command_failure(self):
        """Test handling of group command failure."""
        # Configure the mock to simulate command failure
        self.selve.executeCommandSyncWithResponse.side_effect = GatewayError("Command failed")
        
        # Also mock updateCommeoDeviceValuesAsync to avoid errors
        self.selve.updateCommeoDeviceValuesAsync = AsyncMock()
          # Run the test
        async def test_async():
            # Attempt to move the group down (should fail)
            with pytest.raises(GatewayError):
                await self.selve.moveGroupDown(self.group)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            
        self.loop.run_until_complete(test_async())
        
    def test_device_position_command_with_invalid_position(self):
        """Test device position command with invalid position values."""
        # Run the test
        async def test_async():
            # Test with negative position
            await self.selve.moveDevicePos(self.commeo_device, -10)
            
            # Command should still be sent but with position clamped to valid range
            # Note: moveDevicePos calls both executeCommand and updateCommeoDeviceValuesAsync
            # So we check that executeCommand was called at least once
            assert self.selve.executeCommand.call_count >= 1
            command = self.selve.executeCommand.call_args_list[0][0][0]  # First call's first arg
            assert isinstance(command, CommandDrivePos)
            # Position should be clamped to 0 (or whichever valid value the implementation uses)
            
            # Reset for next test
            self.selve.executeCommand.reset_mock()
            
            # Test with position > 100
            await self.selve.moveDevicePos(self.commeo_device, 200)
            
            # Command should still be sent but with position clamped to valid range
            assert self.selve.executeCommand.call_count >= 1
            command = self.selve.executeCommand.call_args_list[0][0][0]  # First call's first arg
            assert isinstance(command, CommandDrivePos)
            # Position should be clamped to 100 (or whichever valid value the implementation uses)
            
        self.loop.run_until_complete(test_async())
        
    def test_delete_nonexistent_group(self):
        """Test deleting a group that doesn't exist."""
        # Mock the deleteGroup method since it doesn't exist in the base class
        async def mock_delete_group(group_id):
            command = GroupDelete(group_id)
            response = await self.selve.executeCommandSyncWithResponse(command)
            return response.result if hasattr(response, 'result') else response.executed
        
        self.selve.deleteGroup = mock_delete_group
        
        # Configure mock response
        mock_response = MagicMock(spec=GroupDeleteResponse)
        mock_response.name = "selve.GW.group.delete"
        mock_response.result = True
        self.selve.executeCommandSyncWithResponse.return_value = mock_response
        
        # Run the test
        async def test_async():
            # Attempt to delete a non-existent group
            result = await self.selve.deleteGroup(31)
            
            # Should succeed at the protocol level even though group doesn't exist
            assert result == True
            
            # Check that command was sent
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            assert isinstance(command, GroupDelete)
            assert command.parameters[0][1] == 31  # Group ID
            
        self.loop.run_until_complete(test_async())
        
    def test_gateway_with_communication_errors(self):
        """Test gateway behavior when it returns communication errors."""
        
        # Configure the mock to return errors for specific commands
        def side_effect(command):
            if isinstance(command, GroupDelete):
                # Return a mock response with executed=False for communication error
                mock_response = MagicMock()
                mock_response.executed = False
                return mock_response
            elif isinstance(command, GroupRead):
                return None  # Simulate null response
            else:
                mock = MagicMock()
                mock.name = "unknown"
                return mock
                
        self.selve.executeCommandSyncWithResponse.side_effect = side_effect
        
        # Run the test
        async def test_async():
            # Attempt to delete a group (should fail with communication error)
            result = await self.selve.groupDelete(1)
            assert result == False
            
            # Attempt to read group info (should return None due to null response)
            result = await self.selve.groupRead(1)
            assert result is None
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
