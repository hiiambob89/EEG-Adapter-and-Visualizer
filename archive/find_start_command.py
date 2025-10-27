"""
Bruteforce common start commands to activate EEG streaming
"""

import asyncio
from bleak import BleakClient

# Common start/stop commands used by EEG devices
COMMON_COMMANDS = [
    # Single byte commands
    (b'\x01', "Start (0x01)"),
    (b'\x02', "Start (0x02)"),
    (b'\x03', "Start (0x03)"),
    (b'\xff', "Start (0xFF)"),
    (b'\x00', "Stop (0x00)"),
    
    # Two byte commands
    (b'\x01\x00', "Start + NULL"),
    (b'\x01\x01', "Start + Start"),
    (b'\x02\x01', "0x02 0x01"),
    (b'\x03\x01', "0x03 0x01"),
    
    # Common protocol commands
    (b'START', "ASCII START"),
    (b'start', "ASCII start"),
    (b'STREAM', "ASCII STREAM"),
    
    # Based on your log format (DATA packets)
    (b'DATA\x01', "DATA + 0x01"),
    (b'DATA\x02', "DATA + 0x02"),
    
    # Multi-byte sequences
    (b'\x01\x00\x00\x00', "Start (4 bytes)"),
    (b'\x02\x00\x00\x00', "0x02 (4 bytes)"),
]

async def test_commands(address):
    """Try various commands to activate streaming"""
    
    write_char = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"  # Your writable char
    notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"  # Your notify char
    
    async with BleakClient(address, timeout=20.0) as client:
        print(f"✓ Connected to {address}\n")
        
        for cmd, desc in COMMON_COMMANDS:
            print(f"{'='*70}")
            print(f"Testing: {desc}")
            print(f"Command: {cmd.hex()}")
            print(f"{'='*70}")
            
            received = [0]
            packets = []
            
            def handler(sender, data):
                received[0] += 1
                packets.append(data)
                if received[0] <= 5:
                    print(f"  ✓ Packet {received[0]}: {len(data)} bytes - {data.hex()[:80]}")
            
            try:
                # Subscribe to notifications
                await client.start_notify(notify_char, handler)
                
                # Send the command
                print(f"\nSending command...")
                await client.write_gatt_char(write_char, cmd, response=False)
                
                # Wait for data
                print(f"Waiting 2 seconds for response...")
                await asyncio.sleep(2)
                
                # Stop notifications
                await client.stop_notify(notify_char)
                
                if received[0] > 0:
                    print(f"\n✓✓✓ SUCCESS! Received {received[0]} packets ✓✓✓")
                    print(f"\nWorking command:")
                    print(f"  Hex: {cmd.hex()}")
                    print(f"  Description: {desc}")
                    print(f"\nFirst packet preview:")
                    if packets:
                        print(f"  {packets[0].hex()}")
                    
                    # Try to decode first packet
                    try:
                        from process import decode_serenibrain_packet
                        decoded = decode_serenibrain_packet(packets[0])
                        print(f"\n  Decoded: Type 0x{decoded['packet_type']:02X}, "
                              f"{len(decoded.get('samples', []))} samples")
                    except Exception as e:
                        print(f"  Decode attempt: {e}")
                    
                    print("\n" + "="*70)
                    
                    # Ask if we should continue testing
                    print("\n✓ FOUND WORKING COMMAND!")
                    return cmd
                else:
                    print(f"  No data received")
                
                # Small delay between tests
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"  Error: {e}")
        
        print(f"\n{'='*70}")
        print("No working command found in common set")
        print("\nNext steps:")
        print("  1. Sniff BLE traffic from phone app using nRF Connect or similar")
        print("  2. Look for writes to 8653000c-43e6-47b7-9cb0-5fc21d4ae340")
        print("  3. Check if device needs to be in specific state (worn, etc)")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python find_start_command.py <device_address>")
        print("\nExample:")
        print("  python find_start_command.py F6:82:59:5D:CC:5D")
        sys.exit(1)
    
    address = sys.argv[1]
    asyncio.run(test_commands(address))
