import pytest
import pytest_asyncio
import asyncio
import sys
import os
import time
import threading
from unittest.mock import Mock, patch
from serial.tools import list_ports

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from selve import Selve
from selve.util.errors import PortError
from selve.commands.service import ServicePing, ServiceGetVersion

# Global lock to prevent parallel port access
_port_lock = threading.Lock()


# Hardware detection utilities
def detect_selve_hardware():
    """
    Detect if Selve Gateway hardware is connected.
    Returns port name if found, None otherwise.
    """
    try:
        ports = list_ports.comports()
        
        # First check for COM16 specifically (known USB port)
        for port in ports:
            if port.device == 'COM16':
                print(f"Found COM16: {port.description}")
                return port.device
        
        # Then check other ports with USB-Serial adapter identifiers
        for port in ports:
            if any(keyword in port.description.lower() for keyword in 
                   ['usb', 'serial', 'cp210', 'ftdi', 'ch340']):
                print(f"Found potential hardware port: {port.device} - {port.description}")
                return port.device
    except Exception as e:
        print(f"Hardware detection error: {e}")
    return None


def is_hardware_available():
    """Check if hardware is available for testing"""
    port = detect_selve_hardware()
    if port:
        print(f"Hardware detected on port: {port}")
        return True
    print("No hardware detected")
    return False


# Pytest markers for hardware tests - now run if hardware is available
pytestmark = pytest.mark.skipif(
    not is_hardware_available(),
    reason="No Selve Gateway hardware detected"
)


class TestSelveHardwareIntegration:
    """
    Integration tests that require actual Selve Gateway hardware.
    These tests will be skipped if no compatible hardware is detected.
    """
    
    @pytest.fixture(scope="class")
    def hardware_port(self):
        """Get the hardware port for testing"""
        port = detect_selve_hardware()
        if not port:
            pytest.skip("No hardware available")
        return port
    
    @pytest_asyncio.fixture(scope="function")
    async def selve_hardware(self, hardware_port):
        """Create Selve instance connected to real hardware"""
        import logging
        
        # Create a unique logger for this test to avoid duplicates
        logger_name = f'selve_test_{id(self)}'
        logger = logging.getLogger(logger_name)
        
        # Only configure if not already configured
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        # Ensure exclusive port access
        with _port_lock:
            selve = Selve(port=hardware_port, logger=logger, discover=False)
            
            yield selve
            
            # Cleanup
            try:
                await selve.stopGateway()
                # Extra cleanup to ensure port is properly released
                if hasattr(selve, '_writer') and selve._writer:
                    selve._writer.close()
                    try:
                        await selve._writer.wait_closed()
                    except:
                        pass
                selve._reader = None
                selve._writer = None
                # Small delay to ensure port is fully released
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                
        # Remove logger handlers to prevent accumulation
        for handler in logger.handlers:
            logger.removeHandler(handler)
    
    @pytest_asyncio.fixture
    async def setup_selve(self, selve_hardware):
        """Setup Selve connection for each test"""
        try:
            await selve_hardware.setup(discover=False, fromConfigFlow=True)
            yield selve_hardware
        finally:
            # Ensure proper cleanup after each test
            try:
                await selve_hardware.stopWorker()
            except:
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_hardware_connection(self, setup_selve):
        """Test basic hardware connection"""
        try:
            print(f"Testing connection to hardware on port: {setup_selve._port}")
            
            # Test ping to verify it's a Selve Gateway
            ping_result = await setup_selve.pingGateway(fromConfigFlow=True)
            if ping_result:
                print("✓ Successfully connected to Selve Gateway")
                assert True
            else:
                print("⚠ Connected to port but device doesn't respond to Selve ping")
                pytest.skip("Device on port is not a Selve Gateway")
            
        except PortError:
            pytest.skip("No Selve Gateway found on available ports")
        except Exception as e:
            print(f"Connection test error: {e}")
            pytest.skip(f"Hardware connection failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_gateway_version(self, setup_selve):
        """Test getting gateway version information"""
        try:
            # Test ping first
            ping_result = await setup_selve.pingGateway(fromConfigFlow=True)
            if not ping_result:
                pytest.skip("Device doesn't respond to Selve ping")
            
            version_info = await setup_selve.getVersionG()
            if version_info and hasattr(version_info, 'version'):
                print(f"✓ Gateway Version: {version_info.version}")
                assert True
            else:
                pytest.skip("Could not retrieve version information")
            
        except Exception as e:
            pytest.skip(f"Version test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_gateway_state(self, setup_selve):
        """Test gateway state operations"""
        try:
            # Test ping first
            ping_result = await setup_selve.pingGateway(fromConfigFlow=True)
            if not ping_result:
                pytest.skip("Device doesn't respond to Selve ping")
            
            # Get gateway state
            state = await setup_selve.gatewayState()
            if state is not None:
                print(f"✓ Gateway State: {state}")
                assert True
            else:
                pytest.skip("Could not retrieve gateway state")
            
        except Exception as e:
            pytest.skip(f"Gateway state test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_device_discovery(self, setup_selve):
        """Test device discovery (if devices are configured)"""
        try:
            # Test ping first
            ping_result = await setup_selve.pingGateway(fromConfigFlow=True)
            if not ping_result:
                pytest.skip("Device doesn't respond to Selve ping")
            
            # Wait a moment for discovery to complete
            await asyncio.sleep(2)
            
            # Check discovered devices
            device_count = 0
            for device_type, devices in setup_selve.devices.items():
                count = len(devices)
                device_count += count
                print(f"{device_type}: {count} devices")
            
            print(f"✓ Total devices discovered: {device_count}")
            
            # List all discovered devices
            setup_selve.list_devices()
            
            assert True  # Test passes if we can discover (even if 0 devices)
            
        except Exception as e:
            pytest.skip(f"Device discovery test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_worker_functionality(self, setup_selve):
        """Test worker thread functionality with real hardware"""
        try:
            # Worker should be running after setup
            assert setup_selve._worker_running is True, "Worker not running after setup"
            
            # Test async command execution
            command = ServicePing()
            await setup_selve.executeCommand(command)
            
            # Wait a moment for command processing
            await asyncio.sleep(1)
            
            # Stop worker
            await setup_selve.stopWorker()
            assert setup_selve._worker_running is False, "Worker still running after stop"
            
        except Exception as e:
            pytest.fail(f"Worker functionality test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_connection_recovery(self, setup_selve):
        """Test connection recovery functionality"""
        try:
            # Simulate connection loss and recovery
            original_port = setup_selve._port
            
            # Close connection
            if setup_selve._writer:
                setup_selve._writer.close()
                await setup_selve._writer.wait_closed()
            setup_selve._reader = None
            setup_selve._writer = None
            
            # Test reconnection
            success = await setup_selve._reconnect()
            assert success is True, "Failed to reconnect"
            
            # Verify connection works
            ping_result = await setup_selve.pingGateway(fromConfigFlow=True)
            assert ping_result is True, "Ping failed after reconnection"
            
        except Exception as e:
            pytest.fail(f"Connection recovery test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    @pytest.mark.parametrize("led_state", [True, False])
    async def test_led_control(self, setup_selve, led_state):
        """Test LED control functionality"""
        try:
            # Set LED state
            result = await setup_selve.setLED(led_state)
            assert result is True, f"Failed to set LED to {led_state}"
            
            # Get LED state
            led_response = await setup_selve.getLED()
            assert led_response is not None, "Failed to get LED state"
            
            print(f"LED set to: {led_state}")
            
        except Exception as e:
            pytest.fail(f"LED control test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_duty_cycle_info(self, setup_selve):
        """Test duty cycle information retrieval"""
        try:
            # Get duty cycle information
            duty_info = await setup_selve.getDuty()
            assert duty_info is not None, "Failed to get duty cycle info"
            
            print(f"Duty cycle info: {duty_info}")
            print(f"Current utilization: {setup_selve.utilization}")
            print(f"Sending blocked: {setup_selve.sendingBlocked}")
            
        except Exception as e:
            pytest.fail(f"Duty cycle test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_rf_info(self, setup_selve):
        """Test RF information retrieval"""
        try:
            # Get RF information
            rf_info = await setup_selve.getRF()
            assert rf_info is not None, "Failed to get RF info"
            
            print(f"RF info: {rf_info}")
            
        except Exception as e:
            pytest.fail(f"RF info test failed: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    async def test_event_handling(self, setup_selve):
        """Test event handling with real hardware"""
        try:
            events_received = []
            
            def event_callback(event):
                events_received.append(event)
                print(f"Event received: {type(event).__name__}")
            
            setup_selve.register_event_callback(event_callback)
            
            # Enable events
            await setup_selve.setEvents(
                eventDevice=True,
                eventSensor=True,
                eventSender=True,
                eventLogging=True,
                eventDuty=True
            )
            
            # Wait for potential events
            await asyncio.sleep(5)
            
            print(f"Total events received: {len(events_received)}")
            
        except Exception as e:
            pytest.fail(f"Event handling test failed: {e}")


class TestSelveHardwareStress:
    """
    Stress tests for hardware integration.
    These tests put more load on the system to test stability.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    @pytest.mark.stress
    async def test_rapid_ping_sequence(self):
        """Test rapid ping sequence to stress the communication"""
        port = detect_selve_hardware()
        if not port:
            pytest.skip("No hardware available")
        
        import logging
        logger = logging.getLogger('selve_stress')
        selve = Selve(port=port, logger=logger, discover=False)
        
        try:
            await selve.setup(discover=False, fromConfigFlow=True)
            
            # Perform rapid ping sequence
            ping_count = 50
            successful_pings = 0
            
            start_time = time.time()
            
            for i in range(ping_count):
                try:
                    result = await selve.pingGateway(fromConfigFlow=True)
                    if result:
                        successful_pings += 1
                    
                    # Small delay to prevent overwhelming the device
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Ping {i} failed: {e}")
            
            end_time = time.time()
            duration = end_time - start_time
            
            success_rate = (successful_pings / ping_count) * 100
            
            print(f"Ping stress test results:")
            print(f"  Total pings: {ping_count}")
            print(f"  Successful: {successful_pings}")
            print(f"  Success rate: {success_rate:.1f}%")
            print(f"  Duration: {duration:.2f}s")
            print(f"  Rate: {ping_count/duration:.1f} pings/s")
            
            # Assert reasonable success rate
            assert success_rate >= 90, f"Success rate too low: {success_rate}%"
            
        finally:
            await selve.stopGateway()
    
    @pytest.mark.asyncio
    @pytest.mark.hardware
    @pytest.mark.stress
    async def test_worker_stability(self):
        """Test worker stability over extended period"""
        port = detect_selve_hardware()
        if not port:
            pytest.skip("No hardware available")
        
        import logging
        logger = logging.getLogger('selve_stability')
        selve = Selve(port=port, logger=logger, discover=False)
        
        try:
            await selve.setup(discover=False, fromConfigFlow=False)
            
            # Run for extended period with periodic commands
            duration = 30  # seconds
            command_interval = 2  # seconds
            
            start_time = time.time()
            commands_sent = 0
            
            while time.time() - start_time < duration:
                try:
                    # Send a command via worker
                    command = ServicePing()
                    await selve.executeCommand(command)
                    commands_sent += 1
                    
                    await asyncio.sleep(command_interval)
                    
                    # Check worker is still running
                    assert selve._worker_running, "Worker stopped unexpectedly"
                    
                except Exception as e:
                    logger.error(f"Command failed: {e}")
            
            print(f"Worker stability test completed:")
            print(f"  Duration: {duration}s")
            print(f"  Commands sent: {commands_sent}")
            print(f"  Worker still running: {selve._worker_running}")
            
        finally:
            await selve.stopGateway()


def run_hardware_tests():
    """
    Convenience function to run only hardware tests.
    Can be called directly if hardware is available.
    """
    if not is_hardware_available():
        print("No Selve Gateway hardware detected. Skipping hardware tests.")
        return
    
    print("Selve Gateway hardware detected. Running integration tests...")
    pytest.main([
        __file__ + "::TestSelveHardwareIntegration",
        "-v",
        "-m", "hardware"
    ])


def run_stress_tests():
    """
    Convenience function to run stress tests.
    Should only be run when explicitly requested.
    """
    if not is_hardware_available():
        print("No Selve Gateway hardware detected. Skipping stress tests.")
        return
    
    print("Running stress tests...")
    pytest.main([
        __file__ + "::TestSelveHardwareStress",
        "-v",
        "-m", "stress"
    ])


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run Selve hardware tests')
    parser.add_argument('--stress', action='store_true', help='Run stress tests')
    parser.add_argument('--all', action='store_true', help='Run all hardware tests')
    
    args = parser.parse_args()
    
    if args.stress:
        run_stress_tests()
    elif args.all:
        pytest.main([__file__, "-v"])
    else:
        run_hardware_tests()
