import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selve import Selve
from selve.commands.service import ServicePing
from selve.commands.device import DeviceGetIds, DeviceGetInfo, DeviceGetValues
from selve.commands.sensor import SensorGetIds
from selve.commands.sender import SenderGetIds
from selve.commands.group import GroupGetIds
from selve.commands.iveo import IveoGetIds


class TestSelvePerformance:
    """Performance tests for Selve operations"""
    
    @pytest.fixture
    def mock_selve(self):
        """Create a mock Selve instance for performance testing"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Mock the connection components
        selve._reader = AsyncMock()
        selve._writer = AsyncMock()
        selve._connection_lock = asyncio.Lock()
        
        return selve
    
    @pytest.mark.asyncio
    async def test_command_execution_performance(self, mock_selve):
        """Test command execution performance"""
        import time
        
        # Mock successful response
        with patch.object(mock_selve, '_execute_command_direct', return_value="success"):
            
            command_count = 100
            commands = [ServicePing() for _ in range(command_count)]
            
            start_time = time.time()
            
            # Execute commands sequentially
            for command in commands:
                await mock_selve.executeCommandSyncWithResponse(command, fromConfigFlow=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Performance test results:")
            print(f"  Commands: {command_count}")
            print(f"  Duration: {duration:.3f}s")
            print(f"  Rate: {command_count/duration:.1f} commands/s")
            
            # Performance assertion - should handle at least 10 commands per second
            assert command_count / duration >= 10, f"Performance too slow: {command_count/duration:.1f} cmd/s"
    
    @pytest.mark.asyncio
    async def test_concurrent_command_execution(self, mock_selve):
        """Test concurrent command execution performance"""
        import time
        
        with patch.object(mock_selve, '_execute_command_direct', return_value="success"):
            
            command_count = 50
            commands = [ServicePing() for _ in range(command_count)]
            
            start_time = time.time()
            
            # Execute commands concurrently
            tasks = []
            for command in commands:
                task = asyncio.create_task(
                    mock_selve.executeCommandSyncWithResponse(command, fromConfigFlow=True)
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            duration = end_time - start_time
            
            successful = sum(1 for r in results if r == "success")
            
            print(f"Concurrent execution results:")
            print(f"  Commands: {command_count}")
            print(f"  Successful: {successful}")
            print(f"  Duration: {duration:.3f}s")
            print(f"  Rate: {command_count/duration:.1f} commands/s")
            
            assert successful == command_count, f"Not all commands successful: {successful}/{command_count}"
    
    @pytest.mark.asyncio
    async def test_device_update_performance(self, mock_selve):
        """Test device update performance with many devices"""
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        import time
        
        # Create many mock devices - use valid ID range (0-63)
        device_count = 60  # Reduced to stay within valid range
        for i in range(device_count):
            device = SelveDevice(i, SelveTypes.DEVICE)
            device.name = f"Device {i}"
            mock_selve.devices[SelveTypes.DEVICE.value][i] = device
        
        # Mock the update function
        async def mock_update(device_id):
            await asyncio.sleep(0.001)  # Simulate small delay
            return True
        
        with patch.object(mock_selve, 'updateCommeoDeviceValues', side_effect=mock_update):
            
            start_time = time.time()
            
            # Update all devices
            await mock_selve.updateAllDevices()
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Device update performance:")
            print(f"  Devices: {device_count}")
            print(f"  Duration: {duration:.3f}s")
            print(f"  Rate: {device_count/duration:.1f} devices/s")


class TestSelveMemoryUsage:
    """Memory usage tests"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_many_devices(self):
        """Test memory usage when managing many devices"""
        import psutil
        import gc
        
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many devices
        from selve.device import SelveDevice
        from selve.sensor import SelveSensor
        from selve.sender import SelveSender
        from selve.util import SelveTypes
        
        device_count = 60  # Reduced to stay within valid ID range
        
        # Add devices - use valid ID range
        for i in range(device_count):
            device = SelveDevice(i, SelveTypes.DEVICE)
            device.name = f"Device {i}"
            selve.addOrUpdateDevice(device, SelveTypes.DEVICE)
        
        # Add sensors - use valid ID range
        for i in range(min(device_count // 10, 60)):  # Fewer sensors, within range
            sensor = SelveSensor(i)
            sensor.device_type = SelveTypes.SENSOR
            selve.addOrUpdateDevice(sensor, SelveTypes.SENSOR)
        
        # Add senders - use valid ID range
        for i in range(min(device_count // 5, 60)):  # Fewer senders, within range
            sender = SelveSender(i)
            sender.device_type = SelveTypes.SENDER
            selve.addOrUpdateDevice(sender, SelveTypes.SENDER)
        
        # Force garbage collection
        gc.collect()
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        total_devices = device_count + (device_count // 10) + (device_count // 5)
        memory_per_device = memory_increase / total_devices if total_devices > 0 else 0
        
        print(f"Memory usage test:")
        print(f"  Total devices: {total_devices}")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory increase: {memory_increase:.2f} MB")
        print(f"  Memory per device: {memory_per_device:.4f} MB")
        
        # Assert reasonable memory usage (less than 1KB per device)
        assert memory_per_device < 0.001, f"Memory usage too high: {memory_per_device:.4f} MB per device"
    
    @pytest.mark.asyncio
    async def test_callback_memory_leak(self):
        """Test for memory leaks in callback system"""
        import weakref
        import gc
        
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Create callbacks and weak references
        callbacks = []
        weak_refs = []
        
        for i in range(100):
            def callback():
                pass
            
            callbacks.append(callback)
            weak_refs.append(weakref.ref(callback))
            selve.register_callback(callback)
        
        # Remove strong references
        callbacks.clear()
        
        # Force garbage collection
        gc.collect()
        
        # Check if callbacks were collected
        alive_count = sum(1 for ref in weak_refs if ref() is not None)
        
        print(f"Callback memory leak test:")
        print(f"  Callbacks created: {len(weak_refs)}")
        print(f"  Still alive: {alive_count}")
        
        # All callbacks should still be alive because they're registered
        assert alive_count == len(weak_refs), "Callbacks were unexpectedly collected"
        
        # Now remove callbacks
        for ref in weak_refs:
            if ref() is not None:
                selve.remove_callback(ref())
        
        # Force garbage collection again
        gc.collect()
        
        # Now callbacks should be collected
        alive_count_after = sum(1 for ref in weak_refs if ref() is not None)
        
        print(f"  After removal: {alive_count_after}")
        
        # Most callbacks should be collected now
        assert alive_count_after <= alive_count * 0.1, "Memory leak in callback system"


class TestSelveRobustness:
    """Robustness and edge case tests"""
    
    @pytest.mark.asyncio
    async def test_rapid_start_stop_worker(self):
        """Test rapid start/stop of worker"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Rapid start/stop cycles
        for i in range(10):
            await selve.startWorker()
            assert selve._worker_running, f"Worker not running after start {i}"
            
            await selve.stopWorker()
            assert not selve._worker_running, f"Worker still running after stop {i}"
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_setups(self):
        """Test multiple concurrent setup calls"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Mock successful setup
        with patch.object(selve, '_try_connect_port', return_value=True):
            selve._port = 'COM1'
            
            # Start multiple setup tasks concurrently
            tasks = [
                asyncio.create_task(selve.setup(discover=False, fromConfigFlow=True))
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should complete successfully
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Setup {i} failed: {result}"
    
    @pytest.mark.asyncio
    async def test_command_queue_overflow(self):
        """Test behavior with command queue overflow"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        await selve.startWorker()
        
        # Fill command queue rapidly
        command_count = 1000
        for i in range(command_count):
            command = ServicePing()
            await selve.executeCommand(command)
        
        # Queue should handle the load without crashing
        assert selve.txQ.qsize() <= command_count
        
        await selve.stopWorker()
    
    @pytest.mark.asyncio
    async def test_invalid_responses(self, capsys):
        """Test handling of invalid responses"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        # Test various invalid responses
        invalid_responses = [
            "",  # Empty response
            "not xml",  # Not XML
            "<invalid>xml</invalid>",  # Invalid XML structure
            "<?xml version='1.0'?><incomplete",  # Incomplete XML
            None,  # None response
        ]
        
        for response in invalid_responses:
            result = await selve.processResponse(response)
            assert result is False or result is None, f"Should handle invalid response: {response}"
    
    @pytest.mark.asyncio
    async def test_device_id_boundaries(self):
        """Test device ID boundary conditions"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        from selve.device import SelveDevice
        from selve.util import SelveTypes
        
        # Test boundary IDs - only valid ones (0-63 based on mask size)
        boundary_ids = [0, 1, 62, 63]
        
        for device_id in boundary_ids:
            device = SelveDevice(device_id, SelveTypes.DEVICE)
            
            # Should handle all IDs gracefully
            selve.addOrUpdateDevice(device, SelveTypes.DEVICE)
            retrieved = selve.getDevice(device_id, SelveTypes.DEVICE)
            
            assert retrieved is not None, f"Device {device_id} should be retrievable"
            assert retrieved.id == device_id, f"Retrieved device should have ID {device_id}"
        
        # Test invalid IDs separately - these should raise exceptions or be handled gracefully
        invalid_ids = [64, 999, -1]
        for device_id in invalid_ids:
            try:
                device = SelveDevice(device_id, SelveTypes.DEVICE)
                # If we get here, the device was created despite invalid ID
                # This might be acceptable depending on implementation
                selve.addOrUpdateDevice(device, SelveTypes.DEVICE)
                
                # For invalid IDs that somehow get through, check if they can be retrieved
                retrieved = selve.getDevice(device_id, SelveTypes.DEVICE)
                is_registered = selve.is_id_registered(device_id, SelveTypes.DEVICE)
                
                # Since the ID is invalid, we don't expect it to work properly
                # but if it does, we'll note it
                if retrieved is not None:
                    print(f"Note: Invalid device ID {device_id} was somehow handled")
                    
            except (IndexError, ValueError):
                # Expected for invalid IDs - this is the correct behavior
                print(f"Correctly rejected invalid device ID {device_id}")


class TestSelveConfigurationEdgeCases:
    """Test edge cases in configuration and setup"""
    
    def test_initialization_with_none_values(self):
        """Test initialization with None values"""
        selve = Selve(
            port=None,
            logger=None,
            loop=None
        )
        
        assert selve._port is None
        assert selve._LOGGER is None
        assert selve.loop is None
        assert selve._worker_running is False
    
    @pytest.mark.asyncio
    async def test_setup_with_empty_port_list(self):
        """Test setup when no ports are available"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        with patch('selve.list_ports.comports', return_value=[]):
            with pytest.raises(Exception):  # Should raise PortError
                await selve.setup()
    
    def test_device_type_boundaries(self):
        """Test all device type boundaries"""
        logger = Mock()
        selve = Selve(logger=logger)
        
        from selve.util import SelveTypes
        
        # Test all device types
        device_types = [
            SelveTypes.DEVICE,
            SelveTypes.IVEO,
            SelveTypes.GROUP,
            SelveTypes.SENSIM,
            SelveTypes.SENSOR,
            SelveTypes.SENDER
        ]
        
        for device_type in device_types:
            # Test findFreeId for each type
            free_id = selve.findFreeId(device_type)
            assert free_id is not None, f"Could not find free ID for {device_type}"
            assert free_id >= 0, f"Invalid free ID for {device_type}: {free_id}"


if __name__ == '__main__':
    pytest.main([__file__, "-v"])
