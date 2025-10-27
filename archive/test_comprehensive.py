"""
Comprehensive activation test - tries reads, writes, and various sequences.
"""

import asyncio
import sys
from bleak import BleakClient

DEVICE_ADDRESS = "F6:82:59:5D:CC:5D"
SERVICE_UUID = "8653000a-43e6-47b7-9cb0-5fc21d4ae340"
NOTIFY_CHAR = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
WRITE_CHAR = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"

packet_count = 0

def notification_handler(sender, data):
    global packet_count
    packet_count += 1
    hex_str = ' '.join(f'{b:02X}' for b in data[:30])
    print(f"  ✓✓✓ PACKET {packet_count}! {hex_str}...")

async def try_sequence(client, name, sequence):
    """Try a sequence of operations and check if data flows."""
    global packet_count
    packet_count = 0
    
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"{'='*70}")
    
    # Set up notification handler first
    await client.start_notify(NOTIFY_CHAR, notification_handler)
    
    # Execute the sequence
    for step in sequence:
        action, *params = step
        
        if action == "write":
            char_uuid, data = params
            hex_str = ' '.join(f'{b:02X}' for b in data)
            print(f"  Writing to {char_uuid[-8:]}: {hex_str}")
            try:
                await client.write_gatt_char(char_uuid, data, response=True)
            except Exception as e:
                print(f"    ❌ Write failed: {e}")
        
        elif action == "read":
            char_uuid = params[0]
            print(f"  Reading from {char_uuid[-8:]}...")
            try:
                value = await client.read_gatt_char(char_uuid)
                hex_str = ' '.join(f'{b:02X}' for b in value)
                print(f"    Value: {hex_str}")
            except Exception as e:
                print(f"    ❌ Read failed: {e}")
        
        elif action == "wait":
            duration = params[0]
            print(f"  Waiting {duration}s for data...")
            for _ in range(duration):
                await asyncio.sleep(1)
                if packet_count > 0:
                    print(f"    ✓✓✓ DATA FLOWING! ({packet_count} packets)")
                    break
    
    # Final wait
    print(f"  Final wait (5s)...")
    await asyncio.sleep(5)
    
    await client.stop_notify(NOTIFY_CHAR)
    
    result = "✓ SUCCESS!" if packet_count > 0 else "❌ No data"
    print(f"\nResult: {result} ({packet_count} packets)")
    
    return packet_count > 0

async def main():
    print("Comprehensive Activation Test")
    print("=" * 70)
    
    # Test sequences to try
    sequences = [
        ("No command (baseline)", [
            ("wait", 5),
        ]),
        
        ("Write 0x01", [
            ("write", WRITE_CHAR, bytearray([0x01])),
            ("wait", 3),
        ]),
        
        ("Write 0x02", [
            ("write", WRITE_CHAR, bytearray([0x02])),
            ("wait", 3),
        ]),
        
        ("Write 'DATA' + 0x01", [
            ("write", WRITE_CHAR, bytearray(b'DATA\x01')),
            ("wait", 3),
        ]),
        
        ("Write 'DATA' + 0x02", [
            ("write", WRITE_CHAR, bytearray(b'DATA\x02')),
            ("wait", 3),
        ]),
        
        ("Write 'START'", [
            ("write", WRITE_CHAR, bytearray(b'START')),
            ("wait", 3),
        ]),
        
        ("Write 4-byte: 0x01000000", [
            ("write", WRITE_CHAR, bytearray([0x01, 0x00, 0x00, 0x00])),
            ("wait", 3),
        ]),
        
        ("Write 4-byte: 0x02000000", [
            ("write", WRITE_CHAR, bytearray([0x02, 0x00, 0x00, 0x00])),
            ("wait", 3),
        ]),
        
        ("Write 2-byte: 0x0100", [
            ("write", WRITE_CHAR, bytearray([0x01, 0x00])),
            ("wait", 3),
        ]),
        
        ("Write 2-byte: 0x0001", [
            ("write", WRITE_CHAR, bytearray([0x00, 0x01])),
            ("wait", 3),
        ]),
        
        ("Multiple writes: 0x01, 0x02, 0x03", [
            ("write", WRITE_CHAR, bytearray([0x01])),
            ("wait", 1),
            ("write", WRITE_CHAR, bytearray([0x02])),
            ("wait", 1),
            ("write", WRITE_CHAR, bytearray([0x03])),
            ("wait", 2),
        ]),
    ]
    
    print(f"\nConnecting to {DEVICE_ADDRESS}...")
    
    try:
        async with BleakClient(DEVICE_ADDRESS, timeout=15.0) as client:
            print(f"✓ Connected!\n")
            
            successful = []
            
            for name, sequence in sequences:
                success = await try_sequence(client, name, sequence)
                if success:
                    successful.append(name)
                await asyncio.sleep(1)  # Pause between tests
            
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            
            if successful:
                print(f"\n✓✓✓ SUCCESSFUL METHODS:")
                for name in successful:
                    print(f"  - {name}")
            else:
                print("\n❌ No methods triggered data flow.")
                print("\nThis means:")
                print("  1. Device requires app-specific activation we haven't found")
                print("  2. We need to capture nRF log of fresh app connection")
                print("  3. OR device has button/physical activation needed")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
