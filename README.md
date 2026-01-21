# python-selve-new

[![PyPI version](https://badge.fury.io/py/python-selve-new.svg)](https://pypi.org/project/python-selve-new/)
[![License: GPL v2+](https://img.shields.io/badge/License-GPL%20v2%2B-blue.svg)](https://www.gnu.org/licenses/gpl-2.0)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

Python library for interfacing with Selve devices (roller shutters, awnings, blinds) via the USB-RF Gateway. This is a complete rewrite of the original library with improved async support, comprehensive testing, and production-ready stability.

## Description

This library provides a Python interface to control Selve devices through their USB-RF Gateway. It implements the complete Selve protocol for communication with:

- **Devices**: Roller shutters, awnings, and blinds with individual or group control
- **Sensors**: Temperature, wind, and light sensors for automated control
- **Iveo Controllers**: Wall-mounted and remote controllers
- **Transmitters**: RF transmitters for integration with other systems

The library features full async/await support, automatic device discovery, event handling, and robust error recovery. It's designed for integration into home automation systems like Home Assistant.

## Features

- **Async Architecture**: Built on asyncio for non-blocking operation
- **Auto-Discovery**: Automatically finds USB-RF Gateway and configured devices
- **Device Management**: Control individual devices or groups
- **Position Control**: Precise positioning with percentage-based commands
- **Event System**: Subscribe to device state changes and sensor readings
- **Error Handling**: Robust error recovery and connection management
- **Comprehensive API**: Full coverage of Selve protocol commands
- **Type Safety**: Fully typed for better IDE support and fewer errors
- **Well Tested**: 350+ unit and integration tests for production stability

### Supported Device Types

- Roller shutters (Commeo, Iveo)
- Awnings
- Venetian blinds
- Group controls
- senSim sensors (wind, sun, temperature)
- Iveo remote controllers
- RF transmitters

## Installation

```bash
pip install python-selve-new
```

## Usage

### Basic Example

```python
import asyncio
from selve import Selve

async def main():
    # Initialize and discover devices
    gateway = Selve()
    await gateway.setup()
    
    # Get all devices
    devices = gateway.discover_devices()
    print(f"Found {len(devices)} devices")
    
    # Control a device
    device = gateway.device(0)  # Get device by ID
    await device.open()         # Fully open
    await asyncio.sleep(5)
    await device.set_position(50)  # Move to 50%
    await asyncio.sleep(5)
    await device.close()        # Fully close
    
    # Cleanup
    await gateway.stopWorker()

asyncio.run(main())
```

### Advanced Usage

```python
import asyncio
from selve import Selve

async def on_state_change(device):
    """Callback when device state changes"""
    print(f"Device {device.id} changed to position {device.target_value}")

async def main():
    # Initialize with specific port
    gateway = Selve(port="/dev/ttyUSB0")
    await gateway.setup()
    
    # Register callback for state changes
    gateway.register_callback(on_state_change)
    
    # Discover all device types
    devices = gateway.discover_devices()
    groups = gateway.discover_groups()
    sensors = gateway.discover_sensors()
    
    print(f"Devices: {len(devices)}")
    print(f"Groups: {len(groups)}")
    print(f"Sensors: {len(sensors)}")
    
    # Control a group of devices
    if groups:
        group = gateway.group(0)
        await group.set_position(75)
    
    # Read sensor values
    for sensor in sensors:
        print(f"Sensor {sensor.id}: {sensor.value}")
    
    # Keep running to receive events
    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    finally:
        await gateway.stopWorker()

asyncio.run(main())
```

### Device Control Methods

```python
# Position control
await device.open()              # Fully open (0%)
await device.close()             # Fully close (100%)
await device.stop()              # Stop movement
await device.set_position(50)    # Move to 50%

# State queries
position = device.target_value   # Current target position
state = device.state            # Current state (IDLE, MOVING, etc.)

# Device info
name = device.name              # Device name
device_type = device.type       # Device type
```

## Home Assistant Integration

This library is used by the [homeassistant-selve](https://github.com/Kannix2005/homeassistant-selve) integration to provide native Selve device support in Home Assistant.

**Features in Home Assistant:**
- Automatic device discovery
- Cover entities for shutters, awnings, and blinds
- Position control with slider
- Sensor entities for environmental data
- Group control support
- Event-driven updates

To use in Home Assistant, install the custom integration:

1. Install via HACS (recommended) or manually copy the integration
2. Add to configuration.yaml:
   ```yaml
   selve:
     port: /dev/ttyUSB0  # or auto-detect
   ```
3. Restart Home Assistant
4. Devices appear as cover entities

See [homeassistant-selve](https://github.com/Kannix2005/homeassistant-selve) for full documentation.

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run integration tests (requires hardware or mocks)
pytest tests/integration/ -m "not hardware"

# Run with coverage
pytest --cov=selve --cov-report=html
```

### Project Structure

```
selve/
├── __init__.py          # Main Selve class
├── device.py            # Device control
├── group.py             # Group control
├── sensor.py            # Sensor handling
├── gateway.py           # Gateway communication
├── commands/            # Protocol command implementations
└── util/                # Utilities and protocol handling

tests/
├── unit/                # Unit tests (337 tests)
└── integration/         # Integration tests (24 tests)
```

## Requirements

- Python 3.9 or higher
- pyserial >= 3.4
- untangle >= 1.1.1

## License

This project is licensed under the GNU General Public License v2.0 or later (GPLv2+).

## Credits

- **Author**: Stefan Altheimer (me@stefan-altheimer.de)
- **Original Library**: Based on concepts from the original python-selve
- **Protocol**: Implements the Selve USB-RF Gateway protocol

## Support

- Report issues: [GitHub Issues](https://github.com/Kannix2005/python-selve-new/issues)
- Home Assistant integration: [homeassistant-selve](https://github.com/Kannix2005/homeassistant-selve)
