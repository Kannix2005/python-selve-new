#!/usr/bin/env python3
"""
Einfacher Port-Test für Hardware-Verfügbarkeit
"""
import serial
import serial_asyncio
import asyncio
from serial.tools import list_ports


def test_port_access():
    """Test if COM16 can be accessed"""
    print("Test Port-Zugriff auf COM16...")
    
    # List all ports
    ports = list_ports.comports()
    print(f"Verfügbare Ports: {[p.device for p in ports]}")
    
    # Check if COM16 exists
    com16_found = any(p.device == 'COM16' for p in ports)
    if not com16_found:
        print("✗ COM16 nicht gefunden")
        return False
    
    print("✓ COM16 gefunden")
    
    # Test sync access
    try:
        with serial.Serial('COM16', 115200, timeout=1) as ser:
            print("✓ Synchroner Zugriff erfolgreich")
            sync_ok = True
    except PermissionError:
        print("✗ Synchroner Zugriff verweigert")
        sync_ok = False
    except Exception as e:
        print(f"✗ Synchroner Zugriff Fehler: {e}")
        sync_ok = False
    
    # Test async access
    async def test_async():
        try:
            reader, writer = await serial_asyncio.open_serial_connection(
                url='COM16', baudrate=115200)
            writer.close()
            await writer.wait_closed()
            print("✓ Asynchroner Zugriff erfolgreich")
            return True
        except PermissionError:
            print("✗ Asynchroner Zugriff verweigert")
            return False
        except Exception as e:
            print(f"✗ Asynchroner Zugriff Fehler: {e}")
            return False
    
    async_ok = asyncio.run(test_async())
    
    return sync_ok and async_ok


if __name__ == "__main__":
    print("=" * 40)
    success = test_port_access()
    print("=" * 40)
    print(f"Ergebnis: {'✓ Port zugänglich' if success else '✗ Port nicht zugänglich'}")
