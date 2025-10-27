"""
Raw btsnoop packet inspector - shows all packet details
"""

import struct
import sys

def inspect_btsnoop(filename, max_packets=200):
    """Show raw packet structure for debugging."""
    
    with open(filename, 'rb') as f:
        # Read header
        header = f.read(16)
        print(f"Header: {header.hex()}")
        print(f"  Magic: {header[:8]}")
        print(f"  Version: {struct.unpack('>I', header[8:12])[0]}")
        print(f"  Datalink: {struct.unpack('>I', header[12:16])[0]}")
        print()
        
        packet_num = 0
        
        while packet_num < max_packets:
            # Read record header
            record_header = f.read(24)
            if len(record_header) < 24:
                break
            
            orig_len, incl_len, flags, drops, timestamp = struct.unpack('>IIIIQ', record_header)
            
            # Read packet data
            packet_data = f.read(incl_len)
            if len(packet_data) < incl_len:
                break
            
            packet_num += 1
            
            # Show packet details
            print(f"{'='*70}")
            print(f"Packet #{packet_num}")
            print(f"{'='*70}")
            print(f"  Original Length: {orig_len}")
            print(f"  Included Length: {incl_len}")
            print(f"  Flags: 0x{flags:08X}")
            print(f"  Drops: {drops}")
            print(f"  Timestamp: {timestamp} ({timestamp/1000000:.3f}s)")
            print(f"\n  Raw Data ({len(packet_data)} bytes):")
            
            # Hexdump
            for i in range(0, min(len(packet_data), 128), 16):
                hex_str = ' '.join(f'{b:02X}' for b in packet_data[i:i+16])
                ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in packet_data[i:i+16])
                print(f"    {i:04X}: {hex_str:48s} | {ascii_str}")
            
            if len(packet_data) > 128:
                print(f"    ... ({len(packet_data) - 128} more bytes)")
            
            # Try to identify packet type
            if len(packet_data) > 0:
                first_byte = packet_data[0]
                packet_type = {
                    0x01: "HCI Command",
                    0x02: "HCI ACL Data",
                    0x03: "HCI SCO Data",
                    0x04: "HCI Event",
                    0x05: "HCI ISO Data"
                }.get(first_byte, f"Unknown (0x{first_byte:02X})")
                
                print(f"\n  Type: {packet_type}")
                
                # If ACL data, try to parse
                if first_byte == 0x02 and len(packet_data) >= 9:
                    handle_flags = struct.unpack('<H', packet_data[1:3])[0]
                    handle = handle_flags & 0x0FFF
                    pb_flag = (handle_flags >> 12) & 0x3
                    bc_flag = (handle_flags >> 14) & 0x3
                    data_len = struct.unpack('<H', packet_data[3:5])[0]
                    
                    print(f"  ACL: Handle=0x{handle:03X}, PB={pb_flag}, BC={bc_flag}, Len={data_len}")
                    
                    # L2CAP header
                    if len(packet_data) >= 9:
                        l2cap_len = struct.unpack('<H', packet_data[5:7])[0]
                        l2cap_cid = struct.unpack('<H', packet_data[7:9])[0]
                        print(f"  L2CAP: Length={l2cap_len}, CID=0x{l2cap_cid:04X}")
                        
                        # ATT protocol (CID 0x0004)
                        if l2cap_cid == 0x0004 and len(packet_data) > 9:
                            att_opcode = packet_data[9]
                            att_opcodes = {
                                0x01: "Error Response",
                                0x02: "Exchange MTU Request",
                                0x03: "Exchange MTU Response",
                                0x12: "Write Request",
                                0x13: "Write Response",
                                0x52: "Write Command",
                                0x1B: "Handle Value Notification",
                                0x1D: "Handle Value Indication"
                            }
                            opcode_name = att_opcodes.get(att_opcode, f"Unknown (0x{att_opcode:02X})")
                            print(f"  ATT: Opcode={opcode_name}")
                            
                            # If write or notification, show handle
                            if att_opcode in [0x12, 0x52, 0x1B, 0x1D] and len(packet_data) >= 12:
                                att_handle = struct.unpack('<H', packet_data[10:12])[0]
                                att_value = packet_data[12:]
                                print(f"  ATT: Handle=0x{att_handle:04X}")
                                print(f"  ATT: Value=({len(att_value)} bytes) {att_value[:32].hex()}")
            
            print()
        
        print(f"\nTotal packets inspected: {packet_num}")


if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else 'btsnoop_hci.log'
    max_packets = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    
    inspect_btsnoop(filename, max_packets)
