"""
Extract and analyze BLE activation command from bugreport.

This script will:
1. Extract btsnoop_hci.log from the bugreport
2. Parse it to find write commands to characteristic 8653000c
3. Show the activation command
"""

import zipfile
import struct
import os

def parse_btsnoop(filename):
    """Parse btsnoop_hci.log and find BLE writes."""
    print(f"Parsing {filename}...")
    
    with open(filename, 'rb') as f:
        # Read btsnoop header
        header = f.read(16)
        if header[:8] != b'btsnoop\x00':
            print("❌ Not a valid btsnoop file!")
            return
        
        print("✓ Valid btsnoop file")
        print("\nSearching for ATT Write commands...")
        
        packet_num = 0
        writes_found = []
        
        while True:
            # Read packet record header (24 bytes in btsnoop v1)
            record_header = f.read(24)
            if len(record_header) < 24:
                break
            
            # Parse record header
            orig_len, incl_len, flags, drops, timestamp = struct.unpack('>IIIIQ', record_header)
            
            # Read packet data
            packet_data = f.read(incl_len)
            if len(packet_data) < incl_len:
                break
            
            packet_num += 1
            
            # Look for ATT Write Request (0x12) or Write Command (0x52)
            # HCI ACL data starts after HCI header
            if len(packet_data) > 10:
                # Skip HCI header (4 bytes: type + handle + length)
                # Then L2CAP header (4 bytes: length + channel)
                # ATT opcode is next
                
                try:
                    # Check if this might be ATT data (L2CAP channel 0x0004)
                    if len(packet_data) >= 9:
                        # Basic parsing - look for ATT opcodes
                        for i in range(len(packet_data) - 1):
                            if packet_data[i] in [0x12, 0x52]:  # Write Request or Write Command
                                # Extract handle and value
                                if i + 3 < len(packet_data):
                                    handle = struct.unpack('<H', packet_data[i+1:i+3])[0]
                                    value = packet_data[i+3:i+20]  # Get up to 17 bytes of value
                                    
                                    hex_value = ' '.join(f'{b:02X}' for b in value[:20])
                                    writes_found.append({
                                        'packet': packet_num,
                                        'opcode': 'Write Request' if packet_data[i] == 0x12 else 'Write Command',
                                        'handle': f'0x{handle:04X}',
                                        'value': value,
                                        'hex': hex_value
                                    })
                                    
                except:
                    pass
        
        print(f"\n✓ Processed {packet_num} packets")
        print(f"✓ Found {len(writes_found)} write operations\n")
        
        if writes_found:
            print("="*70)
            print("BLE WRITE COMMANDS FOUND:")
            print("="*70)
            for w in writes_found:
                print(f"\nPacket #{w['packet']}:")
                print(f"  Operation: {w['opcode']}")
                print(f"  Handle: {w['handle']}")
                print(f"  Value: {w['hex']}")
                
                # Try to interpret as ASCII
                try:
                    ascii_str = bytes([b for b in w['value'] if 32 <= b < 127]).decode('ascii')
                    if ascii_str:
                        print(f"  ASCII: \"{ascii_str}\"")
                except:
                    pass
            
            print("\n" + "="*70)
            print("LIKELY ACTIVATION COMMAND:")
            print("="*70)
            print("\nLook for writes that happen BEFORE the first data notification.")
            print("The activation command is probably one of the early writes above.")
            print("\nTo test it in Python:")
            for w in writes_found[:5]:  # Show first 5
                print(f"\n  await client.write_gatt_char(WRITE_CHAR, bytearray([{', '.join(f'0x{b:02X}' for b in w['value'][:10])}]))")
        else:
            print("❌ No write commands found in log!")
            print("\nPossible reasons:")
            print("  1. Log didn't capture the connection sequence")
            print("  2. Device doesn't require write command (auto-streams)")
            print("  3. Need to check raw log manually")

def main():
    # Check if bugreport.zip exists
    if os.path.exists('bugreport.zip'):
        print("Extracting btsnoop_hci.log from bugreport...")
        try:
            with zipfile.ZipFile('bugreport.zip', 'r') as z:
                # Find the btsnoop file
                btsnoop_files = [f for f in z.namelist() if 'btsnoop' in f.lower()]
                
                if btsnoop_files:
                    print(f"Found: {btsnoop_files[0]}")
                    z.extract(btsnoop_files[0])
                    
                    # Rename to simpler name
                    extracted_path = btsnoop_files[0]
                    if os.path.exists(extracted_path):
                        os.rename(extracted_path, 'btsnoop_hci.log')
                        print("✓ Extracted to btsnoop_hci.log\n")
                        
                        parse_btsnoop('btsnoop_hci.log')
                else:
                    print("❌ No btsnoop file found in bugreport!")
                    print("Available files:")
                    for name in z.namelist()[:20]:
                        print(f"  - {name}")
        except Exception as e:
            print(f"❌ Error extracting: {e}")
    
    elif os.path.exists('btsnoop_hci.log'):
        parse_btsnoop('btsnoop_hci.log')
    
    else:
        print("❌ No bugreport.zip or btsnoop_hci.log found!")
        print("\nRun this after bugreport completes.")

if __name__ == "__main__":
    main()
