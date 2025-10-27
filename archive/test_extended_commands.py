"""
Extended activation command test - tries more patterns based on common EEG device protocols.
"""

import asyncio
import sys
from bleak import BleakClient

DEVICE_ADDRESS = "F6:82:59:5D:CC:5D"
NOTIFY_CHAR = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
WRITE_CHAR = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"

packet_count = 0

def notification_handler(sender, data):
    global packet_count
    packet_count += 1
    hex_str = ' '.join(f'{b:02X}' for b in data[:40])
    print(f"  ✓✓✓ PACKET {packet_count}! Length: {len(data)}, Data: {hex_str}...")

async def try_command(client, name, data, wait_time=3):
    """Try a single command."""
    global packet_count
    packet_count = 0
    
    print(f"\n[{name}]")
    hex_str = ' '.join(f'{b:02X}' for b in data)
    print(f"  Writing: {hex_str}")
    
    try:
        await client.write_gatt_char(WRITE_CHAR, data, response=True)
        print(f"  Waiting {wait_time}s...")
        
        for i in range(wait_time):
            await asyncio.sleep(1)
            if packet_count > 0:
                print(f"  ✓✓✓ SUCCESS! Data flowing! ({packet_count} packets in {i+1}s)")
                return True
        
        print(f"  No data ({packet_count} packets)")
        return False
        
    except Exception as e:
        print(f"  ❌ Write failed: {e}")
        return False

async def main():
    print("="*70)
    print("EXTENDED BLE ACTIVATION TEST")
    print("="*70)
    
    # Commands to try based on common EEG/medical device patterns
    commands = [
        # Single byte commands
        ("0x00", bytearray([0x00])),
        ("0x01", bytearray([0x01])),
        ("0x02", bytearray([0x02])),
        ("0x03", bytearray([0x03])),
        ("0x04", bytearray([0x04])),
        ("0xFF", bytearray([0xFF])),
        
        # Two-byte commands (little-endian and big-endian)
        ("0x0100", bytearray([0x01, 0x00])),
        ("0x0001", bytearray([0x00, 0x01])),
        ("0x0200", bytearray([0x02, 0x00])),
        ("0x0002", bytearray([0x00, 0x02])),
        ("0x0300", bytearray([0x03, 0x00])),
        ("0x0003", bytearray([0x00, 0x03])),
        
        # Four-byte commands
        ("0x01000000", bytearray([0x01, 0x00, 0x00, 0x00])),
        ("0x02000000", bytearray([0x02, 0x00, 0x00, 0x00])),
        ("0x03000000", bytearray([0x03, 0x00, 0x00, 0x00])),
        
        # DATA prefix commands (based on packet format)
        ("DATA+0x01", bytearray(b'DATA\x01')),
        ("DATA+0x02", bytearray(b'DATA\x02')),
        ("DATA+0x03", bytearray(b'DATA\x03')),
        
        # Common text commands
        ("START", bytearray(b'START')),
        ("start", bytearray(b'start')),
        ("STREAM", bytearray(b'STREAM')),
        ("stream", bytearray(b'stream')),
        ("BEGIN", bytearray(b'BEGIN')),
        ("begin", bytearray(b'begin')),
        ("ON", bytearray(b'ON')),
        ("on", bytearray(b'on')),
        
        # Hex sequences that might match packet headers
        ("0x44414541", bytearray([0x44, 0x41, 0x45, 0x41])),  # "DATA" as seen in packets
        ("0x4441544101", bytearray([0x44, 0x41, 0x54, 0x41, 0x01])),
        ("0x4441544102", bytearray([0x44, 0x41, 0x54, 0x41, 0x02])),
        
        # Common medical device commands
        ("0xAA", bytearray([0xAA])),
        ("0x55", bytearray([0x55])),
        ("0xAA55", bytearray([0xAA, 0x55])),
        ("0x55AA", bytearray([0x55, 0xAA])),
    ]
    
    print(f"\nConnecting to {DEVICE_ADDRESS}...")
    
    try:
        async with BleakClient(DEVICE_ADDRESS, timeout=15.0) as client:
            print(f"✓ Connected!\n")
            
            # Set up notification handler
            await client.start_notify(NOTIFY_CHAR, notification_handler)
            print("✓ Notifications enabled\n")
            
            successful = []
            
            for name, data in commands:
                success = await try_command(client, name, data, wait_time=3)
                if success:
                    successful.append(name)
                    # If we find a working command, try it a few more times to confirm
                    print(f"\n  ⚠ CONFIRMING: Trying {name} again...")
                    await asyncio.sleep(2)
                    await try_command(client, f"{name} (retry)", data, wait_time=5)
                
                await asyncio.sleep(0.5)  # Small delay between commands
            
            await client.stop_notify(NOTIFY_CHAR)
            
            print("\n" + "="*70)
            print("RESULTS")
            print("="*70)
            
            if successful:
                print(f"\n✓✓✓ SUCCESSFUL COMMANDS:")
                for cmd in successful:
                    print(f"  - {cmd}")
                print("\nWe found the activation command!")
            else:
                print("\n❌ No commands triggered streaming")
                print("\nPossible reasons:")
                print("  1. App uses encrypted/obfuscated command")
                print("  2. Requires specific sequence of commands")
                print("  3. Device state-dependent (needs button press, etc.)")
                print("  4. Command is in native compiled code we can't easily extract")
                print("\nRecommendation: Try nRF Connect to manually write these commands")
                print("and see if any work there.")
            
            return 0 if successful else 1
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
