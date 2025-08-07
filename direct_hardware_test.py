#!/usr/bin/env python3
"""
Direkter Hardware-Test ohne pytest
"""
import sys
import os
import asyncio
import logging
import pytest

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from selve import Selve
from selve.util.errors import PortError


@pytest.mark.asyncio
async def test_hardware_direct():
    """Direct hardware test without pytest"""
    print("=" * 50)
    print("Direkter Hardware-Test")
    print("=" * 50)
    
    # Setup logger
    logger = logging.getLogger('selve_test')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Test COM16 directly
    port = 'COM16'
    print(f"Teste Selve Gateway auf {port}...")
    
    try:
        # Create Selve instance
        selve = Selve(port=port, logger=logger, discover=False)
        print("✓ Selve instance erstellt")
        
        # Setup connection with timeout
        setup_task = asyncio.create_task(selve.setup(discover=False, fromConfigFlow=True))
        try:
            await asyncio.wait_for(setup_task, timeout=10.0)
            print("✓ Verbindung hergestellt")
        except asyncio.TimeoutError:
            print("✗ Verbindungs-Timeout")
            setup_task.cancel()
            return False
        
        # Test ping
        ping_result = await selve.pingGateway(fromConfigFlow=True)
        if ping_result:
            print("✓ Gateway ping erfolgreich")
            
            # Test version
            try:
                version = await selve.getGatewayFirmwareVersion()
                print(f"✓ Gateway Version: {version}")
            except Exception as e:
                print(f"⚠ Version konnte nicht abgerufen werden: {e}")
            
            # Test state
            try:
                state = await selve.gatewayState()
                print(f"✓ Gateway State: {state}")
            except Exception as e:
                print(f"⚠ State konnte nicht abgerufen werden: {e}")
                
        else:
            print("✗ Gateway ping fehlgeschlagen")
        
        # Cleanup
        await selve.stopGateway()
        print("✓ Verbindung geschlossen")
        
        return ping_result
        
    except PortError as e:
        print(f"✗ Port-Fehler: {e}")
        return False
    except Exception as e:
        print(f"✗ Allgemeiner Fehler: {e}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_hardware_direct())
    print("=" * 50)
    if result:
        print("✓ Hardware-Test ERFOLGREICH")
    else:
        print("✗ Hardware-Test FEHLGESCHLAGEN")
    print("=" * 50)
