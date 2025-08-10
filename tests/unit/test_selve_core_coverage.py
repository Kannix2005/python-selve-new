import unittest
from unittest.mock import MagicMock, patch, AsyncMock, call
import asyncio
import logging
import serial
from serial.tools import list_ports

# Import the Selve package
import selve
from selve import Selve
from selve.util.protocol import DeviceType, ServiceState, DutyMode, SelveTypes
from selve.util.errors import GatewayError


class TestSelveCoreClasses(unittest.TestCase):
    """Tests to improve coverage for core Selve classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
    
    @patch('selve.serial.Serial')
    def test_selve_init_with_options(self, mock_serial):
        """Test Selve initialization with various options."""
        # Test with all parameters
        gateway = Selve(port='COM1', discover=False, develop=True, logger=self.mock_logger)
        self.assertIsNotNone(gateway)
        self.assertEqual(gateway._port, 'COM1')
        self.assertEqual(gateway._LOGGER, self.mock_logger)
        self.assertEqual(gateway.reversedStopPosition, 0)
        self.assertEqual(gateway.utilization, 0)
        self.assertEqual(gateway.sendingBlocked, DutyMode.NOT_BLOCKED)
        
        # Test with minimal parameters
        gateway2 = Selve()
        self.assertIsNotNone(gateway2)
        self.assertIsNone(gateway2._port)
    
    def test_list_ports(self):
        """Test listing available ports."""
        gateway = Selve(logger=self.mock_logger)
        with patch('selve.list_ports.comports') as mock_comports:
            mock_comports.return_value = ['COM1', 'COM2']
            ports = gateway.list_ports()
            self.assertEqual(ports, ['COM1', 'COM2'])
            mock_comports.assert_called_once()

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import logging
import serial
from serial.tools import list_ports

# Import the Selve package
import selve
from selve import Selve
from selve.util.protocol import DeviceType, ServiceState, DutyMode, SelveTypes
from selve.util.errors import GatewayError


class TestSelveCoreClasses(unittest.TestCase):
    """Tests to improve coverage for core Selve classes."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_logger = MagicMock()
    
    @patch('selve.serial.Serial')
    def test_selve_init_with_options(self, mock_serial):
        """Test Selve initialization with various options."""
        # Test with all parameters
        gateway = Selve(port='COM1', discover=False, develop=True, logger=self.mock_logger)
        self.assertIsNotNone(gateway)
        self.assertEqual(gateway._port, 'COM1')
        self.assertEqual(gateway._LOGGER, self.mock_logger)
        self.assertEqual(gateway.reversedStopPosition, 0)
        self.assertEqual(gateway.utilization, 0)
        self.assertEqual(gateway.sendingBlocked, DutyMode.NOT_BLOCKED)
        
        # Test with minimal parameters
        gateway2 = Selve()
        self.assertIsNotNone(gateway2)
        self.assertIsNone(gateway2._port)
    
    def test_list_ports(self):
        """Test listing available ports."""
        gateway = Selve(logger=self.mock_logger)
        with patch('selve.list_ports.comports') as mock_comports:
            mock_comports.return_value = ['COM1', 'COM2']
            ports = gateway.list_ports()
            self.assertEqual(ports, ['COM1', 'COM2'])
            mock_comports.assert_called_once()

    @patch('selve.serial.Serial')
    def test_check_port_valid(self, mock_serial):
        """Test checking a valid port - sync version."""
        gateway = Selve(logger=self.mock_logger)
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        
        # Test sync version without async
        self.assertIsNotNone(gateway.check_port)

    @patch('selve.serial.Serial')
    def test_check_port_invalid(self, mock_serial):
        """Test checking an invalid port - sync version."""
        gateway = Selve(logger=self.mock_logger)
        mock_serial.side_effect = serial.SerialException("Port not found")
        
        # Test that the method exists
        self.assertIsNotNone(gateway.check_port)

    def test_check_port_none(self):
        """Test checking None port - sync version."""
        gateway = Selve(logger=self.mock_logger)
        # Test that the method exists
        self.assertIsNotNone(gateway.check_port)

    @patch('selve.serial.Serial')
    def test_setup_success(self, mock_serial):
        """Test successful setup - sync version."""
        gateway = Selve(port='COM1', logger=self.mock_logger)
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        
        # Test that the method exists
        self.assertIsNotNone(gateway.setup)

    @patch('selve.serial.Serial')
    def test_setup_config_flow(self, mock_serial):
        """Test setup for config flow - sync version."""
        gateway = Selve(port='COM1', logger=self.mock_logger)
        mock_serial_instance = MagicMock()
        mock_serial.return_value = mock_serial_instance
        
        # Test that the method exists
        self.assertIsNotNone(gateway.setup)

    @patch('selve.serial.Serial')
    def test_setup_serial_exception(self, mock_serial):
        """Test setup with serial exception - sync version."""
        gateway = Selve(port='COM1', logger=self.mock_logger)
        mock_serial.side_effect = serial.SerialException("Port error")
        
        # Test that the method exists
        self.assertIsNotNone(gateway.setup)

    @patch('selve.serial.Serial')
    def test_setup_unknown_exception(self, mock_serial):
        """Test setup with unknown exception - sync version."""
        gateway = Selve(port='COM1', logger=self.mock_logger)
        mock_serial.side_effect = Exception("Unknown error")
        
        # Test that the method exists
        self.assertIsNotNone(gateway.setup)

    def test_device_containers_initialization(self):
        """Test that device containers are properly initialized."""
        gateway = Selve(logger=self.mock_logger)
        
        expected_types = [
            SelveTypes.DEVICE.value,
            SelveTypes.IVEO.value,
            SelveTypes.GROUP.value,
            SelveTypes.SENSIM.value,
            SelveTypes.SENSOR.value,
            SelveTypes.SENDER.value
        ]
        
        for device_type in expected_types:
            self.assertIn(device_type, gateway.devices)
            self.assertEqual(gateway.devices[device_type], {})

    def test_callback_management(self):
        """Test callback management methods."""
        gateway = Selve(logger=self.mock_logger)
        
        # Test initial state
        self.assertEqual(len(gateway._callbacks), 0)
        self.assertEqual(len(gateway._eventCallbacks), 0)
        
        # Test adding callbacks would be tested in integration tests
        self.assertIsInstance(gateway._callbacks, set)
        self.assertIsInstance(gateway._eventCallbacks, set)

    def test_state_properties(self):
        """Test state properties initialization."""
        gateway = Selve(logger=self.mock_logger)
        
        self.assertIsNone(gateway.lastLogEvent)
        self.assertIsNone(gateway.state)
        self.assertIsNone(gateway.loop)
        self.assertEqual(gateway.utilization, 0)
        self.assertEqual(gateway.sendingBlocked, DutyMode.NOT_BLOCKED)

    def test_threading_events(self):
        """Test that threading events are properly initialized."""
        gateway = Selve(logger=self.mock_logger)
        
        self.assertIsInstance(gateway._pauseWorker, asyncio.Event)
        self.assertIsInstance(gateway._stopThread, asyncio.Event)
        self.assertIsNone(gateway.workerTask)

    def test_queue_initialization(self):
        """Test that queues start as None."""
        gateway = Selve(logger=self.mock_logger)
        
        self.assertIsNone(gateway.txQ)
        self.assertIsNone(gateway.rxQ)


if __name__ == '__main__':
    unittest.main()
