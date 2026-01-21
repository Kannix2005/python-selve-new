"""
Common fixtures for integration tests.
This module provides fixtures that can be reused across different integration test files.
"""

import asyncio
import logging
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from selve import Selve
from selve.device import SelveDevice
from selve.util.protocol import SelveTypes, DeviceType
from selve.commands.command import CommandResultResponse


@pytest.fixture
def logger():
    """Set up logger fixture for tests."""
    logger = logging.getLogger("IntegrationTestLogger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


@pytest.fixture
def event_loop():
    """Create and provide a new event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def mock_serial():
    """Provide a mocked serial interface."""
    with patch('selve.serial.Serial') as mock_serial:
        # Configure mock serial port
        mock_serial_instance = mock_serial.return_value
        mock_serial_instance.is_open = True
        mock_serial_instance.read_until.return_value = b'<methodResponse name="selve.GW.service.ping"></methodResponse>'
        mock_serial_instance.write = MagicMock()
        mock_serial_instance.in_waiting = 0
        mock_serial_instance.readline = MagicMock(return_value=b'<methodResponse name="selve.GW.command.result" result="true"></methodResponse>')
        
        yield mock_serial


@pytest.fixture
async def mock_selve_instance(mock_serial, logger):
    """Provide a mocked Selve instance for testing."""
    # Use the current running loop instead of event_loop fixture
    current_loop = None
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no running loop, create one
        current_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(current_loop)
    
    selve_instance = Selve(port="COM3", discover=False, develop=True,
                         logger=logger, loop=current_loop)
    
    # Set the mocked serial instance
    selve_instance._serial = mock_serial.return_value
    
    # Initialize queues which would normally be set up during setup() method
    selve_instance.txQ = asyncio.Queue()
    selve_instance.rxQ = asyncio.Queue()
    
    # Mock the command execution to avoid real serial communication
    selve_instance.executeCommandSyncWithResponse = AsyncMock()
    mock_response = MagicMock(spec=CommandResultResponse)
    mock_response.name = "selve.GW.command.result"
    mock_response.result = True
    selve_instance.executeCommandSyncWithResponse.return_value = mock_response
    
    # Add devices for testing
    test_device = SelveDevice(1, SelveTypes.DEVICE, DeviceType.SHUTTER)
    test_device.name = "Test Shutter"
    selve_instance.devices = {"device": {1: test_device}}
    
    # Add moveDeviceStop method if it doesn't exist
    if not hasattr(selve_instance, 'moveDeviceStop'):
        from selve.commands.command import CommandStop
        async def mock_move_device_stop(device, type=None):
            await selve_instance.executeCommandSyncWithResponse(CommandStop(device.id, type if type else 0))
            return True
        selve_instance.moveDeviceStop = mock_move_device_stop
    
    yield selve_instance
    
    # Cleanup: stop any running tasks
    await selve_instance.stopWorker()
    # Cancel pending tasks
    if selve_instance._tx_task and not selve_instance._tx_task.done():
        selve_instance._tx_task.cancel()
        try:
            await selve_instance._tx_task
        except asyncio.CancelledError:
            pass
    if selve_instance._dispatch_task and not selve_instance._dispatch_task.done():
        selve_instance._dispatch_task.cancel()
        try:
            await selve_instance._dispatch_task
        except asyncio.CancelledError:
            pass


@pytest.fixture
def test_device(mock_selve_instance):
    """Provide a test device for testing."""
    return mock_selve_instance.devices["device"][1]
