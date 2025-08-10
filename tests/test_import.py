import pytest
import os
import sys
import logging

# Add the project root directory to the path so we can import the selve package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the selve package
import selve


def test_import():
    """Test that the selve package can be imported."""
    assert selve is not None
    
    # Test importing some classes from the package
    from selve import Selve
    from selve.device import SelveDevice
    from selve.group import SelveGroup
    from selve.iveo import IveoDevice
    from selve.sender import SelveSender
    from selve.sensor import SelveSensor
    from selve.util.protocol import DeviceType, ServiceState
    
    # Verify the imports worked
    assert Selve is not None
    assert SelveDevice is not None
    assert SelveGroup is not None
    assert IveoDevice is not None
    assert SelveSender is not None
    assert SelveSensor is not None
    assert DeviceType is not None
    assert ServiceState is not None
    
    # Log success
    logging.info("All imports successful")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_import()
    print("Import test passed successfully")
