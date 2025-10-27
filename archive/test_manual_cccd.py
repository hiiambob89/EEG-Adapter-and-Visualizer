"""
Test manually writing to CCCD (Client Characteristic Configuration Descriptor).

Sometimes automatic notification enabling doesn't work - this forces the descriptor write.
"""

import asyncio
import sys
from bleak import BleakClient

DEVICE_ADDRESS = "F6:82:59:5D:CC:5D"
NOTIFY_CHAR = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
CCCD_UUID = "00002902-0000-1000-8000-00805f9b34fb"  # Standard CCCD UUID

packet_count = 0

def notification_handler(sender, data):
    global packet_count
    packet_count += 1
    hex_str = ' '.join(f'{b:02X}' for b in data[:20])
    print(f"✓ Packet {packet_count}: {hex_str}...")

async def main():
    print("Connecting...")
    
    async with BleakClient(DEVICE_ADDRESS, timeout=15.0) as client:
        print(f"✓ Connected to {DEVICE_ADDRESS}")
        
        # Get the characteristic and its CCCD descriptor
        char = None
        for service in client.services:
            for c in service.characteristics:
                if c.uuid.lower() == NOTIFY_CHAR.lower():
                    char = c
                    break
        
        if not char:
            print("❌ Characteristic not found!")
            return 1
        
        print(f"Found characteristic: {char.uuid}")
        print(f"Properties: {char.properties}")
        print(f"Descriptors: {[d.uuid for d in char.descriptors]}")
        
        # Find CCCD descriptor
        cccd = None
        for desc in char.descriptors:
            if desc.uuid.lower() == CCCD_UUID.lower():
                cccd = desc
                break
        
        if cccd:
            print(f"\nFound CCCD descriptor: {cccd.uuid}")
            
            # Method 1: Manual CCCD write
            print("\n--- Method 1: Manual CCCD Write ---")
            try:
                # Write 0x0100 to enable notifications (0x0200 for indications, 0x0300 for both)
                await client.write_gatt_descriptor(cccd.handle, bytearray([0x01, 0x00]))
                print("✓ CCCD written manually (0x0100 for notifications)")
            except Exception as e:
                print(f"❌ CCCD write failed: {e}")
            
            # Set up notification handler
            await client.start_notify(NOTIFY_CHAR, notification_handler)
            print("✓ Notification handler registered")
        else:
            print("\n⚠ No CCCD descriptor found, using standard start_notify")
            await client.start_notify(NOTIFY_CHAR, notification_handler)
        
        print("\nWaiting 30 seconds for data...")
        for i in range(30):
            await asyncio.sleep(1)
            if i % 5 == 4:
                print(f"  [{i+1}s] Packets: {packet_count}")
        
        print(f"\n{'✓' if packet_count > 0 else '❌'} Total packets: {packet_count}")
        
        return 0 if packet_count > 0 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
