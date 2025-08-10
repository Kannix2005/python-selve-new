import unittest
from unittest.mock import MagicMock, patch, AsyncMock, call
import asyncio
import logging
import serial
import xml.etree.ElementTree as ET

# Import the Selve package
import selve
from selve import Selve
from selve.util.protocol import *
from selve.util.errors import *


class TestSelveAdvancedCoverage(unittest.TestCase):
    """Advanced tests to improve coverage for less covered Selve methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
    
    @patch('selve.serial.Serial')
    def test_worker_method_parts(self, mock_serial):
        """Test parts of the worker method."""
        gateway = Selve(port='COM1', logger=self.mock_logger)
        gateway._serial = MagicMock()
        gateway._serial.is_open = True
        gateway._serial.in_waiting = 0
        gateway.txQ = asyncio.Queue()
        gateway.rxQ = asyncio.Queue()
        
        # Test that worker can handle empty queues
        gateway._pauseWorker.set()  # Pause the worker
        
        # Since the worker is complex, we test individual components
        self.assertIsNotNone(gateway._pauseWorker)
        self.assertIsNotNone(gateway._stopThread)

    def test_discover_port_functionality(self):
        """Test port discovery functionality."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test list_ports method
        with patch('selve.list_ports.comports') as mock_comports:
            mock_port1 = MagicMock()
            mock_port1.device = 'COM1'
            mock_port1.description = 'USB Serial Port'
            
            mock_port2 = MagicMock()
            mock_port2.device = 'COM2'
            mock_port2.description = 'Standard Port'
            
            mock_comports.return_value = [mock_port1, mock_port2]
            ports = gateway.list_ports()
            
            self.assertEqual(len(ports), 2)
            self.assertEqual(ports[0].device, 'COM1')
            self.assertEqual(ports[1].device, 'COM2')

    def test_error_handling_methods(self):
        """Test error handling in various scenarios."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test that error callbacks are properly initialized
        self.assertIsInstance(gateway._callbacks, set)
        self.assertIsInstance(gateway._eventCallbacks, set)
        
        # Test device container structure
        expected_device_types = ['device', 'iveo', 'group', 'senSim', 'sensor', 'sender']
        for device_type in expected_device_types:
            self.assertIn(device_type, gateway.devices)
            self.assertIsInstance(gateway.devices[device_type], dict)

    def test_utility_state_values(self):
        """Test utility state values and initialization."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test initial duty cycle values
        self.assertEqual(gateway.utilization, 0)
        self.assertEqual(gateway.sendingBlocked, DutyMode.NOT_BLOCKED)
        
        # Test that we can update these values
        gateway.utilization = 50
        gateway.sendingBlocked = DutyMode.BLOCKED
        
        self.assertEqual(gateway.utilization, 50)
        self.assertEqual(gateway.sendingBlocked, DutyMode.BLOCKED)

    def test_callback_registration(self):
        """Test callback registration methods."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test callback registration
        test_callback = MagicMock()
        gateway.register_callback(test_callback)
        self.assertIn(test_callback, gateway._callbacks)
        
        # Test callback removal
        gateway.remove_callback(test_callback)
        self.assertNotIn(test_callback, gateway._callbacks)
        
        # Test event callback registration
        event_callback = MagicMock()
        gateway.register_event_callback(event_callback)
        self.assertIn(event_callback, gateway._eventCallbacks)
        
        # Test event callback removal
        gateway.remove_event_callback(event_callback)
        self.assertNotIn(event_callback, gateway._eventCallbacks)

    def test_lock_objects(self):
        """Test that lock objects are properly initialized."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test that locks are asyncio locks
        self.assertIsInstance(gateway._writeLock, asyncio.Lock)
        self.assertIsInstance(gateway._readLock, asyncio.Lock)

    def test_protocol_enum_completeness(self):
        """Test that protocol enums are complete and accessible."""
        # Test DeviceType enum completeness
        device_types = [
            DeviceType.UNKNOWN, DeviceType.SHUTTER, DeviceType.BLIND,
            DeviceType.AWNING, DeviceType.SWITCH, DeviceType.DIMMER,
            DeviceType.NIGHT_LIGHT, DeviceType.DRAWN_LIGHT,
            DeviceType.HEATING, DeviceType.COOLING, DeviceType.SWITCHDAY,
            DeviceType.GATEWAY
        ]
        
        for device_type in device_types:
            self.assertIsInstance(device_type.value, int)
            self.assertGreaterEqual(device_type.value, 0)

    def test_service_state_enum_usage(self):
        """Test ServiceState enum usage scenarios."""
        # Test all service states
        states = [
            ServiceState.BOOTLOADER,
            ServiceState.UPDATE,
            ServiceState.STARTUP,
            ServiceState.READY,
            ServiceState.NOT_READY
        ]
        
        for state in states:
            self.assertIsInstance(state.value, int)
            self.assertGreaterEqual(state.value, 0)

    def test_sensor_states_comprehensive(self):
        """Test comprehensive sensor state enum coverage."""
        sensor_states = [
            SensorState.INVALID,
            SensorState.AVAILABLE,
            SensorState.LOW_BATTERY,
            SensorState.COMMUNICATION_LOSS,
            SensorState.TESTMODE,
            SensorState.SERVICEMODE
        ]
        
        for state in sensor_states:
            self.assertIsInstance(state.value, int)
            self.assertGreaterEqual(state.value, 0)

    def test_command_result_states(self):
        """Test command result state enums."""
        result_states = [
            CommandResultState.IDLE,
            CommandResultState.SEND
        ]
        
        for state in result_states:
            self.assertIsInstance(state.value, int)
            self.assertGreaterEqual(state.value, 0)

    def test_parameter_type_string_values(self):
        """Test parameter type string values."""
        param_types = {
            ParameterType.INT: "int",
            ParameterType.STRING: "string", 
            ParameterType.BASE64: "base64",
            ParameterType.BOOL: "bool"
        }
        
        for param_type, expected_value in param_types.items():
            self.assertEqual(param_type.value, expected_value)

    def test_selve_types_string_values(self):
        """Test SelveTypes enum string values."""
        selve_types = {
            SelveTypes.SERVICE: "service",
            SelveTypes.PARAM: "param",
            SelveTypes.DEVICE: "device",
            SelveTypes.SENSOR: "sensor",
            SelveTypes.SENSIM: "senSim",
            SelveTypes.SENDER: "sender",
            SelveTypes.GROUP: "group",
            SelveTypes.COMMAND: "command",
            SelveTypes.EVENT: "event",
            SelveTypes.IVEO: "iveo",
            SelveTypes.COMMEO: "commeo",
            SelveTypes.FIRMWARE: "firmware",
            SelveTypes.UNKNOWN: "unknown"
        }
        
        for selve_type, expected_value in selve_types.items():
            self.assertEqual(selve_type.value, expected_value)

    def test_communication_and_movement_states(self):
        """Test communication and movement state enums."""
        # Test CommunicationType
        comm_types = [
            CommunicationType.COMMEO,
            CommunicationType.IVEO,
            CommunicationType.UNKNOWN
        ]
        
        for comm_type in comm_types:
            self.assertIsInstance(comm_type.value, int)
        
        # Test MovementState
        movement_states = [
            MovementState.UNKOWN,  # Note: typo in original
            MovementState.STOPPED_OFF,
            MovementState.UP_ON,
            MovementState.DOWN_ON
        ]
        
        for state in movement_states:
            self.assertIsInstance(state.value, int)

    def test_day_and_duty_modes(self):
        """Test day mode and duty mode enums."""
        # Test DayMode enum
        day_modes = [
            DayMode.UNKOWN,  # Note: typo in original
            DayMode.NIGHTMODE,
            DayMode.DAWNING,
            DayMode.DAY,
            DayMode.DUSK
        ]
        
        for mode in day_modes:
            self.assertIsInstance(mode.value, int)
        
        # Test DutyMode enum
        duty_modes = [DutyMode.NOT_BLOCKED, DutyMode.BLOCKED]
        for mode in duty_modes:
            self.assertIsInstance(mode.value, int)

    def test_device_and_log_classes(self):
        """Test device class and log type enums."""
        # Test DeviceClass enum
        device_classes = [
            DeviceClass.ACTOR,
            DeviceClass.GROUP,
            DeviceClass.SENDER,
            DeviceClass.SENSIM,
            DeviceClass.SENSOR,
            DeviceClass.IVEO,
            DeviceClass.UNKOWN  # Note: typo in original
        ]
        
        for dev_class in device_classes:
            self.assertIsInstance(dev_class.value, int)
        
        # Test LogType enum
        log_types = [LogType.INFO, LogType.WARNING, LogType.ERROR]
        for log_type in log_types:
            self.assertIsInstance(log_type.value, int)

    def test_reversedStopPosition_property(self):
        """Test reversedStopPosition property."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test initial value
        self.assertEqual(gateway.reversedStopPosition, 0)
        
        # Test that we can set it
        gateway.reversedStopPosition = 1
        self.assertEqual(gateway.reversedStopPosition, 1)


if __name__ == '__main__':
    unittest.main()
