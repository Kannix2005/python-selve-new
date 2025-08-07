"""
Debug script to test the async serial connection directly
"""
import asyncio
import serial_asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

async def test_async_connection():
    """Test async connection to COM16"""
    try:
        print("Testing async connection to COM16...")
        
        # Same parameters as Selve class
        serial_params = {
            'baudrate': 115200,
            'bytesize': 8,  # serial.EIGHTBITS
            'parity': 'N',  # serial.PARITY_NONE  
            'stopbits': 1,  # serial.STOPBITS_ONE
            'timeout': 1.0
        }
        
        reader, writer = await serial_asyncio.open_serial_connection(
            url='COM16', **serial_params
        )
        
        print("✓ Async connection opened successfully")
        
        # Send ping command
        ping_command = b'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>selve.GW.service.ping</methodName><array><string></string></array></methodCall>\n'
        
        print("Sending ping command...")
        writer.write(ping_command)
        await writer.drain()
        
        print("Waiting for response...")
        # Read multiple lines since the response might be multi-line
        full_response = ""
        try:
            while True:
                response_data = await asyncio.wait_for(
                    reader.readuntil(b'\n'), timeout=1.0
                )
                line = response_data.decode('utf-8', errors='ignore').strip()
                full_response += line + "\n"
                print(f"Received line: {line}")
                
                # Check if we have a complete response
                if '</methodResponse>' in line:
                    break
        except asyncio.TimeoutError:
            print("No more data")
        
        print(f"Full response:\n{full_response}")
        
        if 'selve.GW.service.ping' in full_response:
            print("✓ Selve Gateway responded correctly!")
            result = True
        else:
            print("⚠ Unexpected response")
            result = False
            
        writer.close()
        await writer.wait_closed()
        
        return result
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    print("Async Serial Connection Debug")
    print("=" * 40)
    
    result = asyncio.run(test_async_connection())
    
    if result:
        print("\n🎉 Async connection works!")
    else:
        print("\n❌ Async connection failed")
