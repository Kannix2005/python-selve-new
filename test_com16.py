"""
Simple script to test what's actually connected to COM16
"""
import serial
import time
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_com16():
    """Test what device is connected to COM16"""
    try:
        print("Testing COM16...")
        ser = serial.Serial(
            port='COM16',
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2.0
        )
        
        print(f"✓ Successfully opened COM16")
        print(f"Port: {ser.port}")
        print(f"Baudrate: {ser.baudrate}")
        print(f"Is open: {ser.is_open}")
        
        # Try to send a Selve ping command
        ping_command = b'<?xml version="1.0" encoding="UTF-8"?><methodCall><methodName>selve.GW.service.ping</methodName><array><string></string></array></methodCall>\n'
        
        print(f"\nSending Selve ping command...")
        ser.write(ping_command)
        ser.flush()
        
        print("Waiting for response...")
        time.sleep(1)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"Response received: {response}")
            
            # Check if it's a Selve response
            if b'selve.GW.service.ping' in response:
                print("✓ This appears to be a Selve Gateway!")
                return True
            else:
                print("⚠ Device responded but not with Selve protocol")
                print(f"Raw response: {response}")
        else:
            print("⚠ No response received")
            
        ser.close()
        return False
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("USB Device Test for COM16")
    print("=" * 40)
    
    result = test_com16()
    
    if result:
        print("\n🎉 Selve Gateway detected on COM16!")
    else:
        print("\n📄 COM16 is not a Selve Gateway")
        print("This is expected if you have a different USB device connected.")
        print("Hardware tests will be skipped, which is the correct behavior.")
