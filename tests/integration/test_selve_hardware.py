import unittest
import logging
import sys
import asyncio
import os
import time
from serial.tools import list_ports

# Import the Selve package
import selve
from selve.util.protocol import ServiceState


@unittest.skipIf(not os.environ.get('ENABLE_HARDWARE_TESTS'), 
                "Hardware tests are disabled. Set ENABLE_HARDWARE_TESTS=1 to enable.")
class TestSelveHardware(unittest.TestCase):
    """
    Tests for Selve with actual hardware connected.
    These tests require an actual Selve USB gateway to be connected.
    
    To run these tests, set the environment variable ENABLE_HARDWARE_TESTS=1
    """
    
    @classmethod
    def setUpClass(cls):
        # Set up logging
        cls.logger = logging.getLogger("HardwareTestLogger")
        cls.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        cls.logger.addHandler(handler)
        
        # Create a new event loop for the tests
        cls.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls.loop)
        
        # Initialize Selve with auto-discovery
        cls.selve_instance = selve.Selve(port=None, discover=True, develop=False,
                                       logger=cls.logger, loop=cls.loop)
        
        # Setup the connection
        cls.loop.run_until_complete(cls.selve_instance.setup())

    @classmethod
    def tearDownClass(cls):
        # Stop the worker and close the connection
        cls.loop.run_until_complete(cls.selve_instance.stopWorker())
        cls.loop.close()

    def setUp(self):
        """Set up before each test."""
        pass

    def tearDown(self):
        """Clean up after each test."""
        pass

    def test_01_list_ports(self):
        """Test listing available COM ports."""
        ports = self.selve_instance.list_ports()
        self.assertTrue(len(ports) > 0, "No COM ports found. Is the hardware connected?")
        self.logger.info(f"Found COM ports: {ports}")

    def test_02_ping_gateway(self):
        """Test pinging the gateway."""
        result = self.loop.run_until_complete(self.selve_instance.pingGatewayFromWorker())
        self.assertTrue(result, "Failed to ping gateway. Is the gateway powered and connected?")

    def test_03_gateway_state(self):
        """Test getting the gateway state."""
        state = self.loop.run_until_complete(self.selve_instance.gatewayState())
        self.assertIsNotNone(state, "Failed to get gateway state.")
        self.logger.info(f"Gateway state: {state}")

    def test_04_gateway_ready(self):
        """Test if the gateway is ready."""
        is_ready = self.loop.run_until_complete(self.selve_instance.gatewayReady())
        self.assertTrue(is_ready, "Gateway is not ready.")

    def test_05_get_gateway_version(self):
        """Test getting the gateway firmware version and serial number."""
        version = self.loop.run_until_complete(self.selve_instance.getGatewayFirmwareVersion())
        self.assertNotEqual(version, False, "Failed to get gateway firmware version.")
        self.logger.info(f"Gateway firmware version: {version}")
        
        serial = self.loop.run_until_complete(self.selve_instance.getGatewaySerial())
        self.assertNotEqual(serial, False, "Failed to get gateway serial number.")
        self.logger.info(f"Gateway serial number: {serial}")

    def test_06_discover_devices(self):
        """Test discovering connected devices."""
        result = self.loop.run_until_complete(self.selve_instance.discover())
        
        # Check if any devices were found
        devices = getattr(self.selve_instance, 'devices', {})
        self.logger.info(f"Found devices: {devices}")
        
        # This is an informational test - it might not fail if no devices are found
        # but we want to know what was discovered
        if 'device' in devices and devices['device']:
            self.logger.info(f"Found {len(devices['device'])} devices")
            for device_id, device in devices['device'].items():
                self.logger.info(f"Device {device_id}: {device}")
        else:
            self.logger.warning("No devices found. This is not necessarily an error.")
            
        if 'group' in devices and devices['group']:
            self.logger.info(f"Found {len(devices['group'])} groups")
            for group_id, group in devices['group'].items():
                self.logger.info(f"Group {group_id}: {group}")
        else:
            self.logger.warning("No groups found. This is not necessarily an error.")
            
        if 'sender' in devices and devices['sender']:
            self.logger.info(f"Found {len(devices['sender'])} senders")
            for sender_id, sender in devices['sender'].items():
                self.logger.info(f"Sender {sender_id}: {sender}")
        else:
            self.logger.warning("No senders found. This is not necessarily an error.")
            
        if 'sensor' in devices and devices['sensor']:
            self.logger.info(f"Found {len(devices['sensor'])} sensors")
            for sensor_id, sensor in devices['sensor'].items():
                self.logger.info(f"Sensor {sensor_id}: {sensor}")
        else:
            self.logger.warning("No sensors found. This is not necessarily an error.")

    @unittest.skip("This test controls actual devices and is skipped by default")
    def test_07_control_device(self):
        """
        Test controlling a device (move up, down, stop).
        
        WARNING: This test will control actual devices. Only enable if you're sure!
        To run this test, remove the @unittest.skip decorator.
        """
        # Get devices
        devices = getattr(self.selve_instance, 'devices', {}).get('device', {})
        if not devices:
            self.skipTest("No devices found to control")
        
        # Get the first device
        device_id = list(devices.keys())[0]
        device = devices[device_id]
        self.logger.info(f"Controlling device: {device}")
        
        # Move device up
        self.logger.info("Moving device up...")
        self.loop.run_until_complete(self.selve_instance.moveDeviceUp(device))
        time.sleep(3)  # Wait for movement
        
        # Stop device
        self.logger.info("Stopping device...")
        self.loop.run_until_complete(self.selve_instance.moveDeviceStop(device))
        time.sleep(1)  # Wait for stop
        
        # Move device down
        self.logger.info("Moving device down...")
        self.loop.run_until_complete(self.selve_instance.moveDeviceDown(device))
        time.sleep(3)  # Wait for movement
        
        # Stop device
        self.logger.info("Stopping device...")
        self.loop.run_until_complete(self.selve_instance.moveDeviceStop(device))

    @unittest.skip("This test controls actual groups and is skipped by default")
    def test_08_control_group(self):
        """
        Test controlling a group (move up, down, stop).
        
        WARNING: This test will control actual devices. Only enable if you're sure!
        To run this test, remove the @unittest.skip decorator.
        """
        # Get groups
        groups = getattr(self.selve_instance, 'devices', {}).get('group', {})
        if not groups:
            self.skipTest("No groups found to control")
        
        # Get the first group
        group_id = list(groups.keys())[0]
        group = groups[group_id]
        self.logger.info(f"Controlling group: {group}")
        
        # Move group up
        self.logger.info("Moving group up...")
        self.loop.run_until_complete(self.selve_instance.moveGroupUp(group))
        time.sleep(3)  # Wait for movement
        
        # Stop group
        self.logger.info("Stopping group...")
        self.loop.run_until_complete(self.selve_instance.moveGroupStop(group))
        time.sleep(1)  # Wait for stop
        
        # Move group down
        self.logger.info("Moving group down...")
        self.loop.run_until_complete(self.selve_instance.moveGroupDown(group))
        time.sleep(3)  # Wait for movement
        
        # Stop group
        self.logger.info("Stopping group...")
        self.loop.run_until_complete(self.selve_instance.moveGroupStop(group))


if __name__ == "__main__":
    unittest.main()
