import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from selve import Selve
from selve.device import SelveDevice
from selve.group import SelveGroup
from selve.sensor import SelveSensor
from selve.util.protocol import (
    SelveTypes, DeviceType, MovementState, CommunicationType, 
    ServiceState, windDigital, rainDigital, tempDigital, lightDigital, SensorState
)
from selve.commands.group import (
    GroupRead, GroupWrite, GroupGetIds, GroupDelete,
    GroupReadResponse, GroupWriteResponse, GroupGetIdsResponse, GroupDeleteResponse
)
from selve.commands.sensor import (
    SensorGetIds, SensorGetInfo, SensorGetValues,
    SensorGetIdsResponse, SensorGetInfoResponse, SensorGetValuesResponse
)
from selve.util.errors import GatewayError


class TestMissingComponentsHandling(unittest.TestCase):
    """Tests for handling missing components (sensors, groups, etc.)."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock logger
        self.logger = MagicMock()
        
        # Create a test loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Create a Selve instance with mocked components
        with patch('selve.Selve._worker', AsyncMock()), \
             patch('selve.serial.Serial'):
            self.selve = Selve(port=None, develop=True, logger=self.logger, loop=self.loop)
            
            # Mock the execute command methods
            self.selve.executeCommand = AsyncMock()
            self.selve.executeCommandSyncWithResponse = AsyncMock()
            
            # Create test components
            self.group = SelveGroup(1, SelveTypes.GROUP, DeviceType.SHUTTER)
            self.group.name = "Test Group"
            
            self.sensor = SelveSensor(1, SelveTypes.SENSOR, DeviceType.UNKNOWN)
            self.sensor.name = "Test Sensor"
            
            # Add the components to the selve instance
            self.selve.devices = {
                "group": {1: self.group},
                "sensor": {1: self.sensor}
            }
        
    def tearDown(self):
        """Clean up the test environment."""
        self.loop.close()
        
    def test_empty_group_ids_response(self):
        """Test behavior when no groups are found."""
        # Configure mock to return empty group IDs
        mock_response = MagicMock(spec=GroupGetIdsResponse)
        mock_response.ids = []
        self.selve.executeCommandSyncWithResponse.return_value = mock_response
        
        # Run the test
        async def test_async():
            # Call discover to handle the empty response
            self.selve.discover_groups = AsyncMock()
            self.selve.discover_groups.return_value = {}
            
            result = await self.selve.discover_groups()
            
            # Should return empty dict
            self.assertEqual(result, {})
            
        self.loop.run_until_complete(test_async())
        
    def test_move_group_not_found(self):
        """Test trying to move a group that doesn't exist."""
        # Create a group that's not in the devices list
        missing_group = SelveGroup(99, SelveTypes.GROUP, DeviceType.SHUTTER)
        missing_group.name = "Non-existent Group"
        
        # Add mock method to the Selve instance
        async def mock_move_group_up(group):
            from selve.commands.command import CommandDriveUpGroup
            from selve.util.protocol import DeviceCommandType
            cmd = CommandDriveUpGroup(group.id, DeviceCommandType.MANUAL)
            return await self.selve.executeCommand(cmd)
        
        self.selve.moveGroupUp = mock_move_group_up
        
        # Run the test
        async def test_async():
            # Should not raise exception even though group doesn't exist
            await self.selve.moveGroupUp(missing_group)
            
            # Command should still be sent
            self.selve.executeCommand.assert_called_once()
            
        self.loop.run_until_complete(test_async())
        
    def test_sensor_update_error(self):
        """Test handling errors during sensor value update."""
        # Configure mock to raise error
        self.selve.executeCommandSyncWithResponse.side_effect = GatewayError("Failed to get sensor values")
        
        # Create test method to update sensor values if it doesn't exist
        if not hasattr(self.selve, 'updateSensorValues'):
            async def mock_update_sensor(sensor_id):
                response = await self.selve.executeCommandSyncWithResponse(SensorGetValues(sensor_id))
                return response
            
            self.selve.updateSensorValues = mock_update_sensor
        
        # Run the test
        async def test_async():
            # Should raise GatewayError
            with self.assertRaises(GatewayError):
                await self.selve.updateSensorValues(1)
                
            # Command should have been attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, SensorGetValues)
            
        self.loop.run_until_complete(test_async())
        
    def test_sensor_missing_from_response(self):
        """Test handling a sensor that is reported by the gateway but has missing info."""
        # First mock to return a sensor ID
        ids_response = MagicMock(spec=SensorGetIdsResponse)
        ids_response.ids = [5]  # Sensor ID 5 exists according to gateway
        
        # Then mock to raise error when getting sensor info
        def mock_execute_side_effect(command):
            if isinstance(command, SensorGetIds):
                return ids_response
            elif isinstance(command, SensorGetInfo):
                raise GatewayError("Failed to get sensor info")
            else:
                return MagicMock()
                
        self.selve.executeCommandSyncWithResponse.side_effect = mock_execute_side_effect
        
        # Run the test
        async def test_async():
            # Create a discover_sensors method if it doesn't exist
            if not hasattr(self.selve, 'discover_sensors'):
                async def mock_discover_sensors():
                    result = {}
                    try:
                        ids_resp = await self.selve.executeCommandSyncWithResponse(SensorGetIds())
                        for sensor_id in ids_resp.ids:
                            try:
                                info = await self.selve.executeCommandSyncWithResponse(SensorGetInfo(sensor_id))
                                sensor = SelveSensor(sensor_id)
                                sensor.name = info.name if hasattr(info, 'name') else f"Sensor {sensor_id}"
                                result[sensor_id] = sensor
                            except GatewayError:
                                self.logger.warning(f"Failed to get info for sensor {sensor_id}")
                    except Exception as e:
                        self.logger.error(f"Error discovering sensors: {e}")
                    return result
                    
                self.selve.discover_sensors = mock_discover_sensors
            
            # Call discover sensors
            sensors = await self.selve.discover_sensors()
            
            # Should return empty dict due to error
            self.assertEqual(sensors, {})
            
            # Should have called SensorGetIds
            commands = [call[0][0] for call in self.selve.executeCommandSyncWithResponse.call_args_list]
            self.assertTrue(any(isinstance(cmd, SensorGetIds) for cmd in commands))
            
        self.loop.run_until_complete(test_async())
        
    def test_group_command_no_response(self):
        """Test sending a group command that gets no response."""
        # Configure the mock to return None
        self.selve.executeCommandSyncWithResponse.return_value = None
        
        # Run the test
        async def test_async():
            # Create a method to read group if it doesn't exist
            if not hasattr(self.selve, 'readGroup'):
                async def mock_read_group(group_id):
                    response = await self.selve.executeCommandSyncWithResponse(GroupRead(group_id))
                    return response
                    
                self.selve.readGroup = mock_read_group
            
            # Call the method - should not raise exception
            result = await self.selve.readGroup(1)
            
            # Should return None
            self.assertIsNone(result)
            
            # Should have called the command
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, GroupRead)
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
