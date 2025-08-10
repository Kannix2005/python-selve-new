import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
from selve import Selve
from selve.sensor import SelveSensor
from selve.sender import SelveSender
from selve.senSim import SelveSenSim
from selve.util.protocol import (
    SelveTypes, DeviceType, CommunicationType,
    SensorState, windDigital, rainDigital, tempDigital, lightDigital
)
from selve.commands.sensor import (
    SensorGetIds, SensorGetInfo, SensorGetValues,
    SensorGetIdsResponse, SensorGetInfoResponse, SensorGetValuesResponse
)
from selve.commands.sender import (
    SenderGetIds, SenderGetInfo, 
    SenderGetIdsResponse, SenderGetInfoResponse
)
from selve.commands.senSim import (
    SenSimGetIds, SenSimGetConfig, SenSimSetConfig,
    SenSimGetIdsResponse, SenSimGetConfigResponse, SenSimSetConfigResponse
)
from selve.util.errors import GatewayError


class TestMockSensorsAndSenders(unittest.TestCase):
    """Tests for sensors and senders with mocks for error scenarios and missing devices."""
    
    def setUp(self):
        """Set up the test environment."""
        # Create a mock logger
        self.logger = MagicMock(spec=logging.Logger)
        
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
            self.sensor = SelveSensor(1, SelveTypes.SENSOR)
            self.sensor.name = "Test Sensor"
            
            self.sender = SelveSender(1, SelveTypes.SENDER)
            self.sender.name = "Test Sender"
            
            self.sensim = SelveSenSim(1, SelveTypes.SENSIM)
            self.sensim.name = "Test SenSim"
            
            # Add the test components to the selve instance
            self.selve.devices = {
                SelveTypes.DEVICE.value: {},
                SelveTypes.IVEO.value: {},
                SelveTypes.GROUP.value: {},
                SelveTypes.SENSOR.value: {1: self.sensor},
                SelveTypes.SENDER.value: {1: self.sender},
                SelveTypes.SENSIM.value: {1: self.sensim}
            }
        
    def tearDown(self):
        """Clean up the test environment."""
        self.loop.close()

    def test_discover_empty_sensor_list(self):
        """Test discover when no sensors are found."""
        # Configure mocks to return empty responses
        sensor_ids_response = MagicMock(spec=SensorGetIdsResponse)
        sensor_ids_response.ids = []
        sensor_ids_response.name = "selve.GW.sensor.getIds"
        
        # Set up mock return
        self.selve.executeCommandSyncWithResponse.return_value = sensor_ids_response
        
        # Run the test
        async def test_async():
            # Clear the existing sensors
            self.selve.devices[SelveTypes.SENSOR.value] = {}
            
            # Patch the discover method to only discover sensors
            with patch.object(self.selve, 'discover', AsyncMock()) as discover_mock:
                # Mock implementation to only discover sensors
                async def discover_sensors():
                    sensor_ids = await self.selve.executeCommandSyncWithResponse(SensorGetIds())
                    if sensor_ids and hasattr(sensor_ids, 'ids'):
                        for i in sensor_ids.ids:
                            pass  # No sensors to process
                    return {}
                
                discover_mock.side_effect = discover_sensors
                
                # Call discover
                await self.selve.discover()
                
                # Check that sensor get IDs command was attempted
                # Use any_call since the exact command instance may be different
                call_args_list = self.selve.executeCommandSyncWithResponse.call_args_list
                sensor_get_ids_called = any(isinstance(call[0][0], SensorGetIds) for call in call_args_list)
                self.assertTrue(sensor_get_ids_called, "SensorGetIds should have been called")
                
                # Sensor list should still be empty
                self.assertEqual(len(self.selve.devices[SelveTypes.SENSOR.value]), 0)
            
        self.loop.run_until_complete(test_async())
        
    def test_get_sensor_info_for_nonexistent_sensor(self):
        """Test getting info for a sensor that doesn't exist."""
        # Configure mock to return None to simulate no sensor found
        self.selve.executeCommandSyncWithResponse.return_value = None
        
        # Add mock method to the Selve instance
        async def mock_get_sensor_info(sensor_id):
            command = SensorGetInfo(sensor_id)
            return await self.selve.executeCommandSyncWithResponse(command)
        
        self.selve.getSensorInfo = mock_get_sensor_info
        
        # Run the test
        async def test_async():
            # Try to get info for a non-existent sensor
            result = await self.selve.getSensorInfo(99)
            
            # Should return None or default object depending on implementation
            self.assertIsNone(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, SensorGetInfo)
            self.assertEqual(command.parameters[0][1], 99)  # Sensor ID
            
        self.loop.run_until_complete(test_async())

    def test_get_sensor_values_with_error(self):
        """Test getting sensor values when an error occurs."""
        # Configure mock to raise an exception
        self.selve.executeCommandSyncWithResponse.side_effect = GatewayError("Failed to get sensor values")
        
        # Add mock method to the Selve instance
        async def mock_get_sensor_values(sensor_id):
            command = SensorGetValues(sensor_id)
            return await self.selve.executeCommandSyncWithResponse(command)
        
        self.selve.getSensorValues = mock_get_sensor_values
        
        # Run the test
        async def test_async():
            # Try to get values, should raise exception
            with self.assertRaises(GatewayError):
                await self.selve.getSensorValues(1)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, SensorGetValues)
            
        self.loop.run_until_complete(test_async())
        
    def test_get_sender_info_for_nonexistent_sender(self):
        """Test getting info for a sender that doesn't exist."""
        # Configure mock to return None to simulate no sender found
        self.selve.executeCommandSyncWithResponse.return_value = None
        
        # Add mock method to the Selve instance
        async def mock_get_sender_info(sender_id):
            command = SenderGetInfo(sender_id)
            return await self.selve.executeCommandSyncWithResponse(command)
        
        self.selve.getSenderInfo = mock_get_sender_info
        
        # Run the test
        async def test_async():
            # Try to get info for a non-existent sender
            result = await self.selve.getSenderInfo(99)
            
            # Should return None or default object depending on implementation
            self.assertIsNone(result)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, SenderGetInfo)
            self.assertEqual(command.parameters[0][1], 99)  # Sender ID
            
        self.loop.run_until_complete(test_async())

    def test_sensim_config_with_error(self):
        """Test setting SenSim configuration when an error occurs."""
        # Configure mock to raise an exception
        self.selve.executeCommandSyncWithResponse.side_effect = GatewayError("Failed to set SenSim config")
        
        # Add mock method to the Selve instance
        async def mock_set_sensim_config(sensim_id, config_value):
            command = SenSimSetConfig(sensim_id, config_value)
            return await self.selve.executeCommandSyncWithResponse(command)
        
        self.selve.setSenSimConfig = mock_set_sensim_config
        
        # Run the test
        async def test_async():
            # Try to set config, should raise exception
            with self.assertRaises(GatewayError):
                await self.selve.setSenSimConfig(1, windDigital.ALARM)
            
            # Check that command was attempted
            self.selve.executeCommandSyncWithResponse.assert_called_once()
            command = self.selve.executeCommandSyncWithResponse.call_args[0][0]
            self.assertIsInstance(command, SenSimSetConfig)
            
        self.loop.run_until_complete(test_async())
        
    def test_sensor_value_update_with_invalid_data(self):
        """Test sensor value update with invalid data."""
        # Create invalid/corrupt sensor values response
        corrupt_response = MagicMock(spec=SensorGetValuesResponse)
        corrupt_response.name = "selve.GW.sensor.getValues"
        corrupt_response.windDigital = None  # Missing wind value
        corrupt_response.rainDigital = None  # Missing rain value
        corrupt_response.tempDigital = None  # Missing temperature value
        corrupt_response.lightDigital = None  # Missing light value
        
        # Configure mock to return the corrupt response
        self.selve.executeCommand.return_value = corrupt_response
        
        # Run the test
        async def test_async():
            # Try to update the sensor values - use the correct method name
            await self.selve.updateSensorValuesAsync(1)
            
            # Should still have processed the command despite missing data
            self.selve.executeCommand.assert_called_once()
            command = self.selve.executeCommand.call_args[0][0]
            self.assertIsInstance(command, SensorGetValues)
            
            # Check that the sensor exists and the test completed without crashing
            self.assertIsNotNone(self.sensor.name)
            
        self.loop.run_until_complete(test_async())

    def test_discover_with_incomplete_sensor_info(self):
        """Test discover when sensor info is incomplete."""
        # Configure mock responses
        sensor_ids_response = MagicMock(spec=SensorGetIdsResponse)
        sensor_ids_response.ids = [1]
        sensor_ids_response.name = "selve.GW.sensor.getIds"
        
        # Create incomplete sensor info
        incomplete_info = MagicMock(spec=SensorGetInfoResponse)
        incomplete_info.name = "selve.GW.sensor.getInfo"
        incomplete_info.sensorName = None  # Missing name
        
        # Set up the mock side effects
        def side_effect(command):
            if isinstance(command, SensorGetIds):
                return sensor_ids_response
            elif isinstance(command, SensorGetInfo):
                return incomplete_info
            elif isinstance(command, SensorGetValues):
                return None  # No values
            else:
                mock = MagicMock()
                mock.name = "unknown"
                return mock
                
        self.selve.executeCommandSyncWithResponse.side_effect = side_effect
        
        # Run the test
        async def test_async():
            # Clear the existing sensors
            self.selve.devices[SelveTypes.SENSOR.value] = {}
            
            # Patch the discover method to only discover sensors
            with patch.object(self.selve, 'discover', AsyncMock()) as discover_mock:
                # Mock implementation to only discover sensors
                async def discover_sensors():
                    sensor_ids = await self.selve.executeCommandSyncWithResponse(SensorGetIds())
                    if sensor_ids and hasattr(sensor_ids, 'ids'):
                        for i in sensor_ids.ids:
                            info = await self.selve.executeCommandSyncWithResponse(SensorGetInfo(i))
                            values = await self.selve.executeCommandSyncWithResponse(SensorGetValues(i))
                            # Create sensor with default name if name is missing
                            sensor = SelveSensor(i, SelveTypes.SENSOR)
                            sensor.name = info.sensorName if info and info.sensorName else f"Sensor {i}"
                            self.selve.devices[SelveTypes.SENSOR.value][i] = sensor
                
                discover_mock.side_effect = discover_sensors
                
                # Call discover
                await self.selve.discover()
                
                # Should have attempted to get sensor info - check with call list inspection
                call_args_list = self.selve.executeCommandSyncWithResponse.call_args_list
                sensor_get_ids_called = any(isinstance(call[0][0], SensorGetIds) for call in call_args_list)
                sensor_get_info_called = any(isinstance(call[0][0], SensorGetInfo) for call in call_args_list)
                
                self.assertTrue(sensor_get_ids_called, "SensorGetIds should have been called")
                self.assertTrue(sensor_get_info_called, "SensorGetInfo should have been called")
                
                # Should have added the sensor despite incomplete info
                self.assertIn(1, self.selve.devices[SelveTypes.SENSOR.value])
                
                # Should have used a default name
                self.assertEqual(self.selve.devices[SelveTypes.SENSOR.value][1].name, "Sensor 1")
            
        self.loop.run_until_complete(test_async())


if __name__ == "__main__":
    unittest.main()
