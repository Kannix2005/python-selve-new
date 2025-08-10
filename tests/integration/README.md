# Integration Tests for Python-Selve

This directory contains integration tests for the Python-Selve library. These tests validate the interaction between different components of the system without requiring actual hardware.

## Test Files

- `test_device_integration.py`: Tests for device movement commands (up, down, stop, and position)
- `test_selve_gateway_integration.py`: Tests for gateway initialization and connection handling
- `test_selve_integration.py`: Other integration tests for the Selve system

## Common Test Fixtures

Common test fixtures are defined in `conftest.py`. These fixtures provide:

- Mocked serial port for simulating hardware communication
- Mocked Selve instance with pre-configured devices
- Test devices for use in tests
- Event loop for async tests
- Logger for debugging

## Running Tests

You can run the integration tests using:

```bash
# Run all integration tests
python -m pytest tests/integration

# Run specific integration tests
python -m pytest tests/integration/test_device_integration.py
python -m pytest tests/integration/test_selve_gateway_integration.py
```

Alternatively, use the provided batch files:

```bash
# Run integration tests only
run_integration_tests.bat

# Run all tests including integration tests
run_all_tests.bat
```

## Writing New Tests

When adding new integration tests:

1. Use the fixtures from `conftest.py` where possible
2. Mock hardware-dependent components
3. Test both success and error scenarios
4. Handle edge cases like timeouts and connection errors
