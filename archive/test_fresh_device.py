"""
Test streaming from a freshly powered device (no prior app connection).

This script will:
1. Connect to the device
2. Subscribe to notifications
3. Wait patiently for data (60 seconds)
4. Report what happens

Make sure:
- Device is powered off/on freshly
- App is NOT connected
- Device is worn properly (electrode contact)
"""

import asyncio
import sys
from bleak import BleakClient, BleakScanner

DEVICE_ADDRESS = "F6:82:59:5D:CC:5D"
NOTIFY_CHAR = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"

packet_count = 0
start_time = None

def notification_handler(sender, data):
    global packet_count, start_time
    if start_time is None:
        start_time = asyncio.get_event_loop().time()
    
    packet_count += 1
    print(f"✓ Packet {packet_count} received! ({len(data)} bytes) - Time: {asyncio.get_event_loop().time() - start_time:.1f}s")
    
    # Show first few bytes
    hex_str = ' '.join(f'{b:02X}' for b in data[:20])
    print(f"  Data: {hex_str}...")

async def main():
    print("=" * 70)
    print("FRESH DEVICE TEST")
    print("=" * 70)
    print()
    print("Prerequisites:")
    print("  ✓ Device has been powered off and back on")
    print("  ✓ App is NOT connected")
    print("  ✓ Device is worn with good electrode contact")
    print()
    print(f"Connecting to {DEVICE_ADDRESS}...")
    
    try:
        async with BleakClient(DEVICE_ADDRESS, timeout=15.0) as client:
            print(f"✓ Connected!")
            print()
            
            # Subscribe
            print(f"Subscribing to notifications on {NOTIFY_CHAR}...")
            await client.start_notify(NOTIFY_CHAR, notification_handler)
            print("✓ Subscribed!")
            print()
            
            print("Waiting for data (60 seconds)...")
            print("If device requires electrode contact, make sure it's worn properly.")
            print()
            
            # Wait 60 seconds
            for i in range(60):
                await asyncio.sleep(1)
                if i % 10 == 9:
                    print(f"  [{i+1}s] Still waiting... (packets received: {packet_count})")
            
            print()
            print("=" * 70)
            print("RESULTS")
            print("=" * 70)
            print(f"Total packets received: {packet_count}")
            
            if packet_count == 0:
                print()
                print("❌ NO DATA RECEIVED")
                print()
                print("Possible reasons:")
                print("  1. Device requires app activation first (persistent state)")
                print("  2. Electrode contact detection prevents streaming")
                print("  3. Device button press needed to start")
                print("  4. Device is in standby/sleep mode")
                print()
                print("Next steps:")
                print("  - Try connecting with app first, then disconnect app")
                print("  - Check if device has a button to press")
                print("  - Ensure very good skin contact with electrodes")
            else:
                print()
                print("✓ SUCCESS! Device is streaming.")
                avg_rate = packet_count / 60.0
                print(f"  Average rate: {avg_rate:.1f} packets/second")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0 if packet_count > 0 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
