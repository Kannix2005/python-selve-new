#!/usr/bin/env python3
"""
Test der genauen Selve Verbindungsmethode
"""
import asyncio
import serial
import serial_asyncio


async def test_selve_connection_method():
    """Test the exact connection method used by Selve"""
    print("=" * 50)
    print("Test der Selve Verbindungsmethode")
    print("=" * 50)
    
    # Exact parameters from Selve
    _serial_params = {
        'baudrate': 115200,
        'bytesize': serial.EIGHTBITS,
        'parity': serial.PARITY_NONE,
        'stopbits': serial.STOPBITS_ONE,
        'timeout': 1.0
    }
    
    port = 'COM16'
    
    try:
        print(f"Öffne {port} mit serial_asyncio.open_serial_connection...")
        print(f"Parameter: {_serial_params}")
        
        reader, writer = await serial_asyncio.open_serial_connection(
            url=port, **_serial_params
        )
        
        print("✓ Verbindung erfolgreich geöffnet")
        print(f"Reader: {reader}")
        print(f"Writer: {writer}")
        
        # Test write
        test_data = b"hello"
        writer.write(test_data)
        await writer.drain()
        print(f"✓ Test-Daten gesendet: {test_data}")
        
        # Cleanup
        writer.close()
        await writer.wait_closed()
        print("✓ Verbindung geschlossen")
        
        return True
        
    except PermissionError as e:
        print(f"✗ Zugriff verweigert: {e}")
        return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        print(f"Fehler-Typ: {type(e)}")
        return False


if __name__ == "__main__":
    result = asyncio.run(test_selve_connection_method())
    print("=" * 50)
    if result:
        print("✓ Test ERFOLGREICH")
    else:
        print("✗ Test FEHLGESCHLAGEN")
    print("=" * 50)
