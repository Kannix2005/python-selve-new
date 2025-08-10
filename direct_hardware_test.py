import logging
import sys
import asyncio
import os
import argparse
from serial.tools import list_ports

# Add the project root directory to the path so we can import the selve package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Import the selve package
from selve import Selve
from selve.util.protocol import ServiceState, DeviceType, SelveTypes


async def direct_hardware_test(port=None, discover=True):
    """Direct hardware test with the Selve gateway."""
    # Set up logging
    logger = logging.getLogger("DirectHardwareTestLogger")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Create a new event loop
    loop = asyncio.get_event_loop()
    
    try:
        # Check for available ports
        available_ports = []
        for port_info in list_ports.comports():
            available_ports.append(port_info.device)
        
        print(f"Available COM ports: {available_ports}")
        
        # Create the Selve instance
        print(f"Creating Selve instance with port={port}, discover={discover}")
        selve_instance = Selve(port=port, discover=discover, develop=True, logger=logger, loop=loop)
        
        # Setup the connection
        print("Setting up connection...")
        await selve_instance.setup()
        
        # Test ping
        print("\nTesting ping...")
        result = await selve_instance.pingGatewayFromWorker()
        print(f"Ping result: {result}")
        
        if not result:
            print("Failed to ping gateway. Check connection and try again.")
            await selve_instance.stopWorker()
            return
        
        # Get gateway state
        print("\nGetting gateway state...")
        state = await selve_instance.gatewayState()
        print(f"Gateway state: {state}")
        
        # Check if gateway is ready
        print("\nChecking if gateway is ready...")
        is_ready = await selve_instance.gatewayReady()
        print(f"Gateway ready: {is_ready}")
        
        # Get gateway version
        print("\nGetting gateway version...")
        version = await selve_instance.getGatewayFirmwareVersion()
        print(f"Gateway firmware version: {version}")
        
        # Get gateway serial number
        print("\nGetting gateway serial number...")
        serial = await selve_instance.getGatewaySerial()
        print(f"Gateway serial number: {serial}")
        
        # Discover devices
        print("\nDiscovering devices...")
        await selve_instance.discover()
        
        # Print discovered devices
        devices = getattr(selve_instance, 'devices', {})
        
        if 'device' in devices and devices['device']:
            print(f"\nFound {len(devices['device'])} devices:")
            for device_id, device in devices['device'].items():
                print(f"  Device {device_id}: {device}")
                print(f"    Name: {device.name}")
                print(f"    Type: {device.device_type.name}")
                print(f"    Sub-type: {device.device_sub_type.name}")
                print(f"    State: {device.state}")
                print(f"    Value: {device.value}")
                print(f"    Target: {device.targetValue}")
            
            # Ask if user wants to control a device
            print("\nDo you want to control a device? (y/n)")
            choice = input().strip().lower()
            if choice == 'y':
                # Ask which device to control
                print("\nEnter the device ID to control:")
                device_id_str = input().strip()
                try:
                    device_id = int(device_id_str)
                    if device_id in devices['device']:
                        device = devices['device'][device_id]
                        print(f"Controlling device {device_id}: {device.name}")
                        
                        # Control loop
                        while True:
                            print("\nActions:")
                            print("1. Move Up")
                            print("2. Move Down")
                            print("3. Stop")
                            print("4. Get Device Info")
                            print("5. Back to main menu")
                            
                            action = input("Select action (1-5): ").strip()
                            
                            if action == '1':
                                print("Moving up...")
                                await selve_instance.moveDeviceUp(device)
                            elif action == '2':
                                print("Moving down...")
                                await selve_instance.moveDeviceDown(device)
                            elif action == '3':
                                print("Stopping...")
                                await selve_instance.moveDeviceStop(device)
                            elif action == '4':
                                print("\nDevice Info:")
                                print(f"  Name: {device.name}")
                                print(f"  Type: {device.device_type.name}")
                                print(f"  Sub-type: {device.device_sub_type.name}")
                                print(f"  State: {device.state}")
                                print(f"  Value: {device.value}")
                                print(f"  Target: {device.targetValue}")
                            elif action == '5':
                                break
                            else:
                                print("Invalid choice. Please try again.")
                    else:
                        print(f"No device with ID {device_id} found.")
                except ValueError:
                    print("Invalid device ID. Please enter a number.")
        else:
            print("\nNo devices found.")
        
        if 'group' in devices and devices['group']:
            print(f"\nFound {len(devices['group'])} groups:")
            for group_id, group in devices['group'].items():
                print(f"  Group {group_id}: {group}")
                print(f"    Name: {group.name}")
            
            # Ask if user wants to control a group
            print("\nDo you want to control a group? (y/n)")
            choice = input().strip().lower()
            if choice == 'y':
                # Ask which group to control
                print("\nEnter the group ID to control:")
                group_id_str = input().strip()
                try:
                    group_id = int(group_id_str)
                    if group_id in devices['group']:
                        group = devices['group'][group_id]
                        print(f"Controlling group {group_id}: {group.name}")
                        
                        # Control loop
                        while True:
                            print("\nActions:")
                            print("1. Move Up")
                            print("2. Move Down")
                            print("3. Stop")
                            print("4. Get Group Info")
                            print("5. Back to main menu")
                            
                            action = input("Select action (1-5): ").strip()
                            
                            if action == '1':
                                print("Moving up...")
                                await selve_instance.moveGroupUp(group)
                            elif action == '2':
                                print("Moving down...")
                                await selve_instance.moveGroupDown(group)
                            elif action == '3':
                                print("Stopping...")
                                await selve_instance.moveGroupStop(group)
                            elif action == '4':
                                print("\nGroup Info:")
                                print(f"  Name: {group.name}")
                                print(f"  Type: {group.device_type.name}")
                                print(f"  Sub-type: {group.device_sub_type.name}")
                            elif action == '5':
                                break
                            else:
                                print("Invalid choice. Please try again.")
                    else:
                        print(f"No group with ID {group_id} found.")
                except ValueError:
                    print("Invalid group ID. Please enter a number.")
        else:
            print("\nNo groups found.")
        
        # Clean up
        print("\nCleaning up...")
        await selve_instance.stopWorker()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
    print("\nTest completed!")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Direct hardware test with the Selve gateway.')
    parser.add_argument('-p', '--port', help='COM port to use (e.g., COM3)')
    parser.add_argument('-d', '--discover', action='store_true', help='Enable auto-discovery of port')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level)
    
    try:
        # Use port if specified, otherwise use auto-discovery
        port = args.port
        discover = True if port is None or args.discover else False
        
        asyncio.run(direct_hardware_test(port, discover))
    except KeyboardInterrupt:
        print("Test interrupted by user.")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
