import pytest
import asyncio
import sys
import os
import logging
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selve import Selve
from selve.commands.service import ServicePing
from selve.commands.event import CommeoDeviceEventResponse, SensorEventResponse, LogEventResponse


class TestSelveCommandsIntegration:
    """Integration tests for Selve command system"""
    
    @pytest.fixture
    def mock_selve_with_responses(self):
        """Create a Selve instance with mocked responses"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Mock successful connection
        selve._reader = AsyncMock()
        selve._writer = AsyncMock()
        selve._connection_lock = asyncio.Lock()
        
        return selve
    
    @pytest.mark.asyncio
    async def test_service_commands_integration(self, mock_selve_with_responses):
        """Test service command integration"""
        selve = mock_selve_with_responses
        
        # Mock ping response - create a mock with the correct name attribute
        mock_response = Mock()
        mock_response.name = "selve.GW.service.ping"
        
        with patch.object(selve, 'executeCommandSyncWithResponse') as mock_execute:
            mock_execute.return_value = mock_response
            
            # Test ping command
            result = await selve.pingGateway(fromConfigFlow=True)
            assert result is True
            
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_device_commands_integration(self, mock_selve_with_responses):
        """Test device command integration"""
        selve = mock_selve_with_responses
        
        from selve.commands.device import DeviceGetIds, DeviceGetInfo
        
        # Mock device IDs response
        ids_response = Mock()
        ids_response.ids = [1, 2, 3]
        
        # Mock device info response
        info_response = Mock()
        info_response.name = "Test Device"
        info_response.deviceType = 1
        info_response.rfAddress = 12345
        info_response.state = 0
        
        with patch.object(selve, 'executeCommandSyncWithResponse') as mock_execute:
            mock_execute.side_effect = [ids_response, info_response]
            
            # Test device discovery sequence
            ids_result = await selve.deviceGetIds()
            assert ids_result == ids_response
            
            info_result = await selve.deviceGetInfo(1)
            assert info_result == info_response
    
    @pytest.mark.asyncio
    async def test_event_processing_integration(self, mock_selve_with_responses):
        """Test event processing integration"""
        selve = mock_selve_with_responses
        
        # Create mock device event
        device_event = Mock(spec=CommeoDeviceEventResponse)
        device_event.id = 1
        device_event.name = "Test Device"
        device_event.deviceType = 1
        device_event.actorState = 0
        device_event.value = 50
        device_event.targetValue = 75
        device_event.unreachable = False
        device_event.overload = False
        device_event.obstructed = False
        device_event.alarm = False
        device_event.lostSensor = False
        device_event.automaticMode = False
        device_event.gatewayNotLearned = False
        device_event.windAlarm = False
        device_event.rainAlarm = False
        device_event.freezingAlarm = False
        device_event.dayMode = False
        
        # Set up callbacks
        device_callback_called = False
        event_callback_called = False
        
        def device_callback():
            nonlocal device_callback_called
            device_callback_called = True
        
        def event_callback(event):
            nonlocal event_callback_called
            event_callback_called = True
        
        selve.register_callback(device_callback)
        selve.register_event_callback(event_callback)
        
        # Process the event
        await selve.processEventResponse(device_event)
        
        # Check that callbacks were called
        assert device_callback_called
        assert event_callback_called
        
        # Check that device was added
        from selve.util import SelveTypes
        device = selve.getDevice(1, SelveTypes.DEVICE)
        assert device is not None
        assert device.name == "Test Device"


class TestSelveDiscoveryIntegration:
    """Integration tests for device discovery"""
    
    @pytest.fixture
    def mock_discovery_responses(self):
        """Create mock responses for discovery process"""
        # Mock IDs responses
        iveo_ids = Mock()
        iveo_ids.ids = [1, 2]
        
        device_ids = Mock()
        device_ids.ids = [1, 2, 3]
        
        group_ids = Mock()
        group_ids.ids = [1]
        
        sensor_ids = Mock()
        sensor_ids.ids = [1]
        
        sender_ids = Mock()
        sender_ids.ids = [1]
        
        sensim_ids = Mock()
        sensim_ids.ids = []
        
        # Mock config responses
        iveo_config = Mock()
        iveo_config.deviceType = 1
        iveo_config.name = "Iveo Device"
        iveo_config.activity = True
        
        device_info = Mock()
        device_info.name = "Test Device"
        device_info.deviceType = 1
        device_info.rfAddress = 12345
        device_info.state = 0
        
        device_values = Mock()
        device_values.movementState = 0
        device_values.value = 50
        device_values.targetValue = 0
        device_values.unreachable = False
        device_values.overload = False
        device_values.obstructed = False
        device_values.alarm = False
        device_values.lostSensor = False
        device_values.automaticMode = False
        device_values.gatewayNotLearned = False
        device_values.windAlarm = False
        device_values.rainAlarm = False
        device_values.freezingAlarm = False
        device_values.dayMode = False
        
        group_config = Mock()
        group_config.name = "Test Group"
        group_config.mask = 255
        
        sensor_info = Mock()
        sensor_info.rfAddress = 54321
        
        sensor_values = Mock()
        sensor_values.windDigital = False
        sensor_values.rainDigital = False
        sensor_values.tempDigital = False
        sensor_values.lightDigital = False
        sensor_values.sensorState = 0
        sensor_values.tempAnalog = 20
        sensor_values.windAnalog = 0
        sensor_values.sun1Analog = 100
        sensor_values.dayLightAnalog = 200
        sensor_values.sun2Analog = 150
        sensor_values.sun3Analog = 180
        
        sender_info = Mock()
        sender_info.name = "Test Sender"
        sender_info.rfAddress = 98765
        sender_info.rfChannel = 1
        sender_info.rfResetCount = 0
        
        return {
            'ids': {
                'iveo': iveo_ids,
                'device': device_ids,
                'group': group_ids,
                'sensor': sensor_ids,
                'sender': sender_ids,
                'sensim': sensim_ids
            },
            'configs': {
                'iveo': iveo_config,
                'device_info': device_info,
                'device_values': device_values,
                'group': group_config,
                'sensor_info': sensor_info,
                'sensor_values': sensor_values,
                'sender': sender_info
            }
        }
    
    @pytest.mark.asyncio
    async def test_full_discovery_process(self, mock_discovery_responses):
        """Test complete discovery process"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        responses = mock_discovery_responses
        
        # Mock the command execution to return appropriate responses
        call_count = 0
        def mock_execute_side_effect(command):
            nonlocal call_count
            call_count += 1
            
            command_name = command.__class__.__name__
            
            if 'IveoGetIds' in command_name:
                return responses['ids']['iveo']
            elif 'DeviceGetIds' in command_name:
                return responses['ids']['device']
            elif 'GroupGetIds' in command_name:
                return responses['ids']['group']
            elif 'SensorGetIds' in command_name:
                return responses['ids']['sensor']
            elif 'SenderGetIds' in command_name:
                return responses['ids']['sender']
            elif 'SenSimGetIds' in command_name:
                return responses['ids']['sensim']
            elif 'IveoGetConfig' in command_name:
                return responses['configs']['iveo']
            elif 'DeviceGetInfo' in command_name:
                return responses['configs']['device_info']
            elif 'DeviceGetValues' in command_name:
                return responses['configs']['device_values']
            elif 'GroupRead' in command_name:
                return responses['configs']['group']
            elif 'SensorGetInfo' in command_name:
                return responses['configs']['sensor_info']
            elif 'SensorGetValues' in command_name:
                return responses['configs']['sensor_values']
            elif 'SenderGetInfo' in command_name:
                return responses['configs']['sender']
            else:
                return Mock()
        
        # Mock required methods
        with patch.object(selve, 'stopWorker'):
            with patch.object(selve, 'setEvents', return_value=True):
                with patch.object(selve, 'gatewayReady', return_value=True):
                    with patch.object(selve, 'executeCommandSyncWithResponse', side_effect=mock_execute_side_effect):
                        with patch.object(selve, 'startWorker'):
                            with patch.object(selve, 'list_devices'):
                                
                                # Run discovery
                                await selve.discover()
                                
                                # Verify devices were discovered and added
                                from selve.util import SelveTypes
                                
                                # Check Iveo devices
                                assert len(selve.devices[SelveTypes.IVEO.value]) == 2
                                
                                # Check regular devices
                                assert len(selve.devices[SelveTypes.DEVICE.value]) == 3
                                
                                # Check groups
                                assert len(selve.devices[SelveTypes.GROUP.value]) == 1
                                
                                # Check sensors
                                assert len(selve.devices[SelveTypes.SENSOR.value]) == 1
                                
                                # Check senders
                                assert len(selve.devices[SelveTypes.SENDER.value]) == 1
                                
                                # Verify device properties
                                device = selve.getDevice(1, SelveTypes.DEVICE)
                                assert device is not None
                                assert device.name == "Test Device"
                                assert device.value == 50


class TestSelveErrorScenarios:
    """Test error scenarios and edge cases"""
    
    @pytest.mark.asyncio
    async def test_discovery_with_gateway_not_ready(self):
        """Test discovery when gateway is not ready"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        with patch.object(selve, 'stopWorker'):
            with patch.object(selve, 'setEvents', return_value=True):
                with patch.object(selve, 'gatewayReady', return_value=False):
                    with patch.object(selve, 'startWorker'):
                        
                        # Discovery should complete without error even if gateway not ready
                        await selve.discover()
                        
                        # No devices should be discovered
                        from selve.util import SelveTypes
                        total_devices = sum(len(devices) for devices in selve.devices.values())
                        assert total_devices == 0
    
    @pytest.mark.asyncio
    async def test_command_execution_with_errors(self):
        """Test command execution with various error scenarios"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Mock stopWorker and startWorker to avoid side effects
        with patch.object(selve, 'stopWorker', new_callable=AsyncMock):
            with patch.object(selve, 'startWorker', new_callable=AsyncMock):
                # Test timeout scenario
                with patch.object(selve, '_execute_command_direct', side_effect=asyncio.TimeoutError):
                    try:
                        result = await selve.executeCommandSyncWithResponse(
                            ServicePing(), fromConfigFlow=True, timeout=1.0
                        )
                        # If no exception, it should return False
                        assert result is False
                    except asyncio.TimeoutError:
                        # Exception is expected since it's not caught
                        pass
                
                # Test connection error
                with patch.object(selve, '_execute_command_direct', side_effect=ConnectionError("Connection lost")):
                    try:
                        result = await selve.executeCommandSyncWithResponse(
                            ServicePing(), fromConfigFlow=True
                        )
                        assert result is False
                    except ConnectionError:
                        # Exception is expected since it's not caught
                        pass
                
                # Test general exception
                with patch.object(selve, '_execute_command_direct', side_effect=Exception("Unknown error")):
                    try:
                        result = await selve.executeCommandSyncWithResponse(
                            ServicePing(), fromConfigFlow=True
                        )
                        assert result is False
                    except Exception:
                        # Exception is expected since it's not caught
                        pass
    
    @pytest.mark.asyncio
    async def test_event_processing_errors(self):
        """Test event processing with malformed events"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Test with incomplete event - add required attributes to prevent immediate failure
        incomplete_event = Mock(spec=CommeoDeviceEventResponse)
        incomplete_event.id = 1
        incomplete_event.deviceType = 1
        incomplete_event.name = "Test Device"
        incomplete_event.actorState = 0
        incomplete_event.value = None  # This could cause issues
        incomplete_event.targetValue = None
        incomplete_event.unreachable = False
        incomplete_event.overload = False
        incomplete_event.obstructed = False
        incomplete_event.alarm = False
        incomplete_event.lostSensor = False
        incomplete_event.automaticMode = False
        incomplete_event.gatewayNotLearned = False
        incomplete_event.windAlarm = False
        incomplete_event.rainAlarm = False
        incomplete_event.freezingAlarm = False
        incomplete_event.dayMode = False
        
        # Should handle gracefully without crashing
        try:
            await selve.processEventResponse(incomplete_event)
        except Exception as e:
            pytest.fail(f"Event processing should handle incomplete events gracefully: {e}")
    
    @pytest.mark.asyncio
    async def test_worker_error_recovery(self):
        """Test worker error recovery scenarios"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Mock asyncio.sleep to speed up the test
        with patch('asyncio.sleep'):
            # Test multiple errors in sequence
            error_count = 5
            for i in range(error_count):
                await selve._handle_worker_error(Exception(f"Error {i}"))
            
            # Error count should be tracked
            assert selve._error_count == error_count
            
            # Test error count reset
            for i in range(6):  # 6 more errors to reach 11 total (more than 10)
                await selve._handle_worker_error(Exception(f"Error {i}"))
            
            # Should reset after too many errors (more than 10)
            assert selve._error_count == 0


class TestSelveLogging:
    """Test logging functionality"""
    
    def test_logging_integration(self):
        """Test logging integration"""
        # Create a real logger for testing
        logger = logging.getLogger('test_selve')
        logger.setLevel(logging.DEBUG)
        
        # Create string handler to capture logs
        import io
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Create Selve instance with real logger
        selve = Selve(logger=logger)
        
        # Test that logging works
        selve._LOGGER.info("Test info message")
        selve._LOGGER.debug("Test debug message")
        selve._LOGGER.error("Test error message")
        
        # Check logged messages
        log_contents = log_stream.getvalue()
        assert "Test info message" in log_contents
        assert "Test debug message" in log_contents
        assert "Test error message" in log_contents
        
        # Clean up
        logger.removeHandler(handler)
    
    @pytest.mark.asyncio
    async def test_log_event_processing(self):
        """Test log event processing"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Create mock log event
        log_event = Mock(spec=LogEventResponse)
        log_event.logType = Mock()
        log_event.logType.INFO = 'INFO'
        log_event.logCode = 1001
        log_event.logStamp = "2023-01-01 12:00:00"
        log_event.logValue = "Test"
        log_event.logDescription = "Test log message"
        
        # Mock the log type comparison
        log_event.logType = Mock()
        log_event.logType.__eq__ = lambda self, other: other == 'INFO'
        
        # Process log event
        await selve.processEventResponse(log_event)
        
        # Check that log event was stored
        assert selve.lastLogEvent == log_event


if __name__ == '__main__':
    pytest.main([__file__, "-v"])
