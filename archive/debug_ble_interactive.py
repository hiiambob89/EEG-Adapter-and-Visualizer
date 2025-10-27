"""
Interactive BLE debugger - explore and test device characteristics
"""

import asyncio
from bleak import BleakClient

async def explore_device(address):
    """Interactive exploration of BLE device"""
    
    print(f"Connecting to {address}...")
    
    async with BleakClient(address, timeout=20.0) as client:
        print(f"✓ Connected!\n")
        
        # List all services and characteristics
        services_data = []
        
        for service in client.services:
            print(f"\n{'='*70}")
            print(f"SERVICE: {service.uuid}")
            print(f"  {service.description}")
            
            for char in service.characteristics:
                props = ', '.join(char.properties)
                print(f"\n  CHAR: {char.uuid}")
                print(f"    Properties: {props}")
                
                char_info = {
                    'service': service.uuid,
                    'uuid': char.uuid,
                    'properties': char.properties,
                    'description': char.description
                }
                
                # Try to read if readable
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    Read: {value.hex()}")
                        char_info['read_value'] = value.hex()
                    except Exception as e:
                        print(f"    Read error: {e}")
                
                services_data.append(char_info)
        
        # Find notify characteristics
        notify_chars = [c for c in services_data if 'notify' in c['properties']]
        write_chars = [c for c in services_data if 'write' in c['properties'] or 'write-without-response' in c['properties']]
        
        print(f"\n{'='*70}")
        print(f"\nSUMMARY:")
        print(f"  Notify characteristics: {len(notify_chars)}")
        print(f"  Writable characteristics: {len(write_chars)}")
        
        if notify_chars:
            print(f"\nNotify characteristics:")
            for i, c in enumerate(notify_chars):
                print(f"  [{i}] {c['uuid']} - {c['description']}")
        
        if write_chars:
            print(f"\nWritable characteristics:")
            for i, c in enumerate(write_chars):
                print(f"  [{i}] {c['uuid']} - {c['description']}")
        
        # Test each notify characteristic
        if notify_chars:
            print(f"\n{'='*70}")
            print("TESTING NOTIFY CHARACTERISTICS")
            print(f"{'='*70}\n")
            
            for i, char_info in enumerate(notify_chars):
                print(f"\nTesting [{i}] {char_info['uuid']}...")
                
                received = [0]
                
                def handler(sender, data):
                    received[0] += 1
                    if received[0] <= 3:  # Show first 3 packets
                        print(f"  Packet {received[0]}: {len(data)} bytes - {data.hex()[:60]}...")
                
                try:
                    # Try sending start commands to common writable characteristics
                    if write_chars:
                        print(f"  Trying to activate streaming...")
                        for write_char in write_chars[:2]:  # Try first 2 writable chars
                            try:
                                # Common start commands
                                for cmd in [b'\x01', b'\x01\x00', bytes([0x01, 0x01])]:
                                    await client.write_gatt_char(write_char['uuid'], cmd, response=False)
                                    await asyncio.sleep(0.1)
                            except:
                                pass
                    
                    await client.start_notify(char_info['uuid'], handler)
                    print(f"  Subscribed. Waiting 3 seconds...")
                    await asyncio.sleep(3)
                    await client.stop_notify(char_info['uuid'])
                    
                    if received[0] > 0:
                        print(f"  ✓✓✓ SUCCESS! Received {received[0]} packets")
                        print(f"\n  Use this UUID: {char_info['uuid']}")
                    else:
                        print(f"  No data received")
                        
                except Exception as e:
                    print(f"  Error: {e}")
        
        print(f"\n{'='*70}")
        print("\nTo use in live_eeg_stream.py:")
        if notify_chars:
            print(f"  python live_eeg_stream.py --address {address} --uuid {notify_chars[0]['uuid']}")
        print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_ble_interactive.py <device_address>")
        print("\nExample:")
        print("  python debug_ble_interactive.py XX:XX:XX:XX:XX:XX")
        sys.exit(1)
    
    address = sys.argv[1]
    asyncio.run(explore_device(address))
