"""
Simple test - just connect and wait for data with extended timeout
"""

import asyncio
from bleak import BleakClient
from process import decode_serenibrain_packet

async def wait_for_stream(address):
    notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
    
    async with BleakClient(address, timeout=30.0) as client:
        print(f"✓ Connected to {address}\n")
        
        received = [0]
        
        def handler(sender, data):
            received[0] += 1
            print(f"\n[Packet {received[0]}] {len(data)} bytes: {data.hex()[:80]}")
            
            try:
                decoded = decode_serenibrain_packet(data)
                print(f"  Type: 0x{decoded['packet_type']:02X}, Samples: {len(decoded.get('samples', []))}")
            except Exception as e:
                print(f"  Decode error: {e}")
        
        print("Subscribing to notifications...")
        await client.start_notify(notify_char, handler)
        
        print("\n" + "="*70)
        print("WAITING FOR DATA (30 seconds)")
        print("="*70)
        print("\nMake sure device is:")
        print("  - Powered on")
        print("  - Worn (electrodes touching skin)")
        print("  - Not connected to phone app")
        print("\nWaiting...\n")
        
        for i in range(30):
            await asyncio.sleep(1)
            if received[0] > 0 and i >= 5:
                print(f"\n✓ Receiving data! Got {received[0]} packets")
                break
            elif i % 5 == 0 and i > 0:
                print(f"  {i}s elapsed, {received[0]} packets received...")
        
        await client.stop_notify(notify_char)
        
        if received[0] == 0:
            print(f"\n⚠ No data after 30 seconds")
            print(f"\nTrying to send start command...")
            
            # Try one more time with a command
            write_char = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"
            await client.start_notify(notify_char, handler)
            
            print(f"Sending 0x01...")
            await client.write_gatt_char(write_char, b'\x01', response=False)
            await asyncio.sleep(2)
            
            print(f"Sending 0x02...")
            await client.write_gatt_char(write_char, b'\x02', response=False)
            await asyncio.sleep(2)
            
            print(f"Sending 0x01 0x01...")
            await client.write_gatt_char(write_char, b'\x01\x01', response=False)
            await asyncio.sleep(2)
            
            await client.stop_notify(notify_char)
            
            if received[0] > 0:
                print(f"\n✓ Got {received[0]} packets after commands!")
            else:
                print(f"\nStill no data. Device may need:")
                print(f"  - Specific activation from phone app")
                print(f"  - Electrode contact detection")
                print(f"  - Button press on device")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_wait_test.py <address>")
        sys.exit(1)
    
    asyncio.run(wait_for_stream(sys.argv[1]))
