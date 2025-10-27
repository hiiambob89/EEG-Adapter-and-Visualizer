"""
Monitor BLE characteristic for writes (run while using phone app)
This will show what commands the app sends
"""

import asyncio
from bleak import BleakClient
import time

async def monitor_device(address, duration=60):
    """Monitor device and log all activity"""
    
    notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
    write_char = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"
    
    print(f"Connecting to {address}...")
    
    async with BleakClient(address, timeout=20.0) as client:
        print(f"✓ Connected!\n")
        print(f"{'='*70}")
        print(f"MONITORING MODE - {duration} seconds")
        print(f"{'='*70}")
        print(f"\nInstructions:")
        print(f"  1. This script is now listening")
        print(f"  2. Open your phone app")
        print(f"  3. Connect to the device from the app")
        print(f"  4. Press START/RECORD in the app")
        print(f"  5. Watch below for packets\n")
        print(f"{'='*70}\n")
        
        packet_count = [0]
        start_time = time.time()
        
        def handler(sender, data):
            packet_count[0] += 1
            elapsed = time.time() - start_time
            
            print(f"[{elapsed:6.2f}s] Packet {packet_count[0]:4d}: {len(data):3d} bytes")
            print(f"         Hex: {data.hex()}")
            
            # Try to decode
            try:
                from process import decode_serenibrain_packet
                decoded = decode_serenibrain_packet(data)
                print(f"         Type: 0x{decoded['packet_type']:02X}, "
                      f"Samples: {len(decoded.get('samples', []))}")
            except:
                pass
            
            print()
        
        # Subscribe to notifications
        await client.start_notify(notify_char, handler)
        print(f"Subscribed to notify characteristic")
        print(f"Waiting for packets...\n")
        
        # Monitor for specified duration
        try:
            await asyncio.sleep(duration)
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        
        await client.stop_notify(notify_char)
        
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        print(f"Total packets received: {packet_count[0]}")
        print(f"Duration: {time.time() - start_time:.1f}s")
        
        if packet_count[0] > 0:
            print(f"\n✓ Device is streaming!")
            print(f"The device appears to stream automatically when connected.")
        else:
            print(f"\n⚠ No packets received")
            print(f"\nPossible reasons:")
            print(f"  1. App needs to send a command first (check phone app)")
            print(f"  2. Device streams to only one connection at a time")
            print(f"  3. Device needs specific activation sequence")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python monitor_ble.py <device_address> [duration_seconds]")
        print("\nExample:")
        print("  python monitor_ble.py F6:82:59:5D:CC:5D 60")
        sys.exit(1)
    
    address = sys.argv[1]
    duration = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    asyncio.run(monitor_device(address, duration))
