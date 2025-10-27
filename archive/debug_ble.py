"""
Debug version of live_eeg_stream.py - tries all notify characteristics
"""

import asyncio
from bleak import BleakScanner, BleakClient
from process import decode_serenibrain_packet

async def test_all_characteristics(device_address):
    """Test all notify characteristics to find the right one"""
    
    async with BleakClient(device_address) as client:
        print(f"\nConnected to {device_address}")
        print("\nDiscovering all services and characteristics...")
        
        notify_chars = []
        
        for service in client.services:
            print(f"\n{'='*70}")
            print(f"Service: {service.uuid}")
            print(f"  Description: {service.description}")
            
            for char in service.characteristics:
                props = ', '.join(char.properties)
                print(f"\n  Characteristic: {char.uuid}")
                print(f"    Properties: {props}")
                print(f"    Description: {char.description}")
                
                if "notify" in char.properties:
                    notify_chars.append((service.uuid, char.uuid, char.description))
                    print(f"    ✓ Can notify")
                
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"    Read value: {value.hex()}")
                    except Exception as e:
                        print(f"    Read failed: {e}")
        
        print(f"\n{'='*70}")
        print(f"\nFound {len(notify_chars)} notify characteristic(s)")
        
        if not notify_chars:
            print("No notify characteristics found!")
            return
        
        # Test each notify characteristic
        for i, (service_uuid, char_uuid, desc) in enumerate(notify_chars):
            print(f"\n{'='*70}")
            print(f"Testing characteristic {i+1}/{len(notify_chars)}")
            print(f"Service: {service_uuid}")
            print(f"Char: {char_uuid}")
            print(f"Description: {desc}")
            print(f"{'='*70}")
            
            packet_count = [0]  # Use list to allow modification in closure
            
            def handler(sender, data):
                packet_count[0] += 1
                print(f"\n[Packet {packet_count[0]}] Received {len(data)} bytes")
                print(f"Hex: {data.hex()}")
                
                # Try to decode
                try:
                    packet = decode_serenibrain_packet(data)
                    print(f"✓ Valid packet! Type: 0x{packet['packet_type']:02X}")
                    if packet['packet_type'] == 2:
                        print(f"  Samples: {len(packet['samples'])}")
                except Exception as e:
                    print(f"✗ Decode failed: {e}")
            
            try:
                await client.start_notify(char_uuid, handler)
                print("Subscribed! Waiting 5 seconds for data...")
                await asyncio.sleep(5)
                await client.stop_notify(char_uuid)
                
                print(f"\nResult: Received {packet_count[0]} packets")
                
                if packet_count[0] > 0:
                    print(f"\n✓✓✓ THIS IS THE RIGHT CHARACTERISTIC! ✓✓✓")
                    print(f"Use: --uuid {char_uuid}")
                    return char_uuid
                else:
                    print("No data received from this characteristic")
                    
            except Exception as e:
                print(f"Error testing characteristic: {e}")
        
        print("\n" + "="*70)
        print("No characteristic produced data!")
        print("\nPossible issues:")
        print("  1. Device needs to be turned on/activated")
        print("  2. Device may need a write command to start streaming")
        print("  3. Device may only transmit when worn/electrodes connected")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug BLE characteristics")
    parser.add_argument("--address", required=True, help="Device BLE address")
    
    args = parser.parse_args()
    
    await test_all_characteristics(args.address)


if __name__ == "__main__":
    asyncio.run(main())
