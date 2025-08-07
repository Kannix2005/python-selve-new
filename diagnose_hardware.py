#!/usr/bin/env python3
"""
Direkte Hardware-Test ohne pytest - zur Diagnose von Port-Problemen
"""
import sys
import os
import asyncio
import time
import serial
import serial_asyncio
from serial.tools import list_ports

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from selve import Selve
from selve.util.errors import PortError


def detect_hardware():
    """Detect available ports"""
    print("Verfügbare COM-Ports:")
    ports = list_ports.comports()
    for port in ports:
        print(f"  {port.device}: {port.description}")
    
    # Check for COM16 specifically
    for port in ports:
        if port.device == 'COM16':
            print(f"\n✓ COM16 gefunden: {port.description}")
            return port.device
    
    print("\n⚠ COM16 nicht gefunden")
    return None


def test_sync_serial(port):
    """Test synchronous serial connection"""
    print(f"\nTeste synchrone Verbindung zu {port}...")
    try:
        with serial.Serial(port, 115200, timeout=2) as ser:
            print(f"✓ Synchrone Verbindung erfolgreich geöffnet")
            print(f"  Port: {ser.port}")
            print(f"  Baudrate: {ser.baudrate}")
            print(f"  Ist offen: {ser.is_open}")
            
            # Test ping command
            ping_cmd = b"\x19\x05\x01\x71\x02\xF7\xA4"
            print(f"Sende Ping-Kommando: {ping_cmd.hex()}")
            ser.write(ping_cmd)
            
            # Wait for response
            time.sleep(0.2)
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"✓ Antwort erhalten: {response.hex()}")
                return True
            else:
                print("⚠ Keine Antwort auf Ping")
                return False
                
    except PermissionError as e:
        print(f"✗ Zugriff verweigert: {e}")
        return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


async def test_async_serial(port):
    """Test asynchronous serial connection"""
    print(f"\nTeste asynchrone Verbindung zu {port}...")
    try:
        reader, writer = await serial_asyncio.open_serial_connection(
            url=port, baudrate=115200)
        
        print(f"✓ Asynchrone Verbindung erfolgreich geöffnet")
        
        # Test ping command
        ping_cmd = b"\x19\x05\x01\x71\x02\xF7\xA4"
        print(f"Sende Ping-Kommando: {ping_cmd.hex()}")
        writer.write(ping_cmd)
        await writer.drain()
        
        # Wait for response
        try:
            response = await asyncio.wait_for(reader.read(100), timeout=2.0)
            print(f"✓ Antwort erhalten: {response.hex()}")
            return True
        except asyncio.TimeoutError:
            print("⚠ Timeout - keine Antwort auf Ping")
            return False
        finally:
            writer.close()
            await writer.wait_closed()
            
    except PermissionError as e:
        print(f"✗ Zugriff verweigert: {e}")
        return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


async def test_selve_connection(port):
    """Test Selve library connection"""
    print(f"\nTeste Selve-Bibliothek mit {port}...")
    try:
        import logging
        logger = logging.getLogger('selve_test')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)
        
        selve = Selve(port=port, logger=logger, discover=False)
        await selve.setup(discover=False, fromConfigFlow=True)
        
        ping_result = await selve.pingGateway(fromConfigFlow=True)
        if ping_result:
            print("✓ Selve Gateway erfolgreich erreicht")
            
            # Try to get version
            version = await selve.getGatewayVersion()
            if version:
                print(f"Gateway Version: {version}")
            
            await selve.stopGateway()
            return True
        else:
            print("⚠ Gerät antwortet nicht auf Selve-Ping")
            await selve.stopGateway()
            return False
            
    except PortError as e:
        print(f"✗ Port-Fehler: {e}")
        return False
    except Exception as e:
        print(f"✗ Fehler: {e}")
        return False


async def main():
    """Main test function"""
    print("Hardware-Diagnose Tool")
    print("=" * 50)
    
    # Detect hardware
    port = detect_hardware()
    if not port:
        print("Kein geeigneter Port gefunden!")
        return
    
    # Test different connection methods
    sync_ok = test_sync_serial(port)
    async_ok = await test_async_serial(port)
    selve_ok = await test_selve_connection(port)
    
    print("\n" + "=" * 50)
    print("ZUSAMMENFASSUNG:")
    print(f"Synchrone Verbindung:  {'✓' if sync_ok else '✗'}")
    print(f"Asynchrone Verbindung: {'✓' if async_ok else '✗'}")
    print(f"Selve-Bibliothek:      {'✓' if selve_ok else '✗'}")
    
    if sync_ok and async_ok and selve_ok:
        print("\n✓ Alle Tests erfolgreich - Hardware ist bereit für Tests!")
    elif sync_ok and async_ok:
        print("\n⚠ Port funktioniert, aber Selve-Protokoll Probleme")
    elif sync_ok:
        print("\n⚠ Port funktioniert synchron, aber async Probleme")
    else:
        print("\n✗ Port-Zugriff fehlgeschlagen - Port möglicherweise belegt")


if __name__ == "__main__":
    asyncio.run(main())
