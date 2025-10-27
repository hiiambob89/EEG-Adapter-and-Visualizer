"""
Analyze btsnoop log to find stream control commands (start/stop/pause)

This enhanced analyzer will:
1. Parse all BLE write commands with timestamps
2. Group commands by timing to identify start/stop/pause sequences
3. Look for patterns in the command data
4. Identify which commands trigger streaming
"""

import struct
import sys
from datetime import datetime, timedelta

def parse_btsnoop_detailed(filename):
    """Parse btsnoop_hci.log with detailed timing and packet analysis."""
    print(f"\n{'='*70}")
    print(f"ANALYZING BLUETOOTH LOG: {filename}")
    print(f"{'='*70}\n")
    
    with open(filename, 'rb') as f:
        # Read btsnoop header
        header = f.read(16)
        if header[:8] != b'btsnoop\x00':
            print("❌ Not a valid btsnoop file!")
            return
        
        version = struct.unpack('>I', header[8:12])[0]
        data_link = struct.unpack('>I', header[12:16])[0]
        print(f"[OK] Valid btsnoop file (version {version}, datalink type {data_link})")
        
        packet_num = 0
        writes = []
        notifications = []
        sessions = []
        base_timestamp = None
        
        while True:
            # Read packet record header (24 bytes)
            record_header = f.read(24)
            if len(record_header) < 24:
                break
            
            # Parse record header
            orig_len, incl_len, flags, drops, timestamp_us = struct.unpack('>IIIIQ', record_header)
            
            # Read packet data
            packet_data = f.read(incl_len)
            if len(packet_data) < incl_len:
                break
            
            packet_num += 1
            
            # Convert timestamp (microseconds since epoch)
            if base_timestamp is None:
                base_timestamp = timestamp_us
            
            relative_time = (timestamp_us - base_timestamp) / 1_000_000.0  # Convert to seconds
            
            # Parse HCI packet
            if len(packet_data) < 1:
                continue
            
            hci_type = packet_data[0]
            
            # HCI ACL Data (0x02)
            if hci_type == 0x02 and len(packet_data) >= 9:
                try:
                    # HCI ACL header: type(1) + handle(2) + length(2) = 5 bytes
                    # L2CAP header: length(2) + channel(2) = 4 bytes
                    # ATT data starts at byte 9
                    
                    if len(packet_data) < 10:
                        continue
                    
                    # Look for ATT opcodes
                    att_offset = 9
                    if att_offset < len(packet_data):
                        opcode = packet_data[att_offset]
                        
                        # ATT Write Request (0x12) or Write Command (0x52)
                        if opcode in [0x12, 0x52]:
                            if att_offset + 3 <= len(packet_data):
                                handle = struct.unpack('<H', packet_data[att_offset+1:att_offset+3])[0]
                                value = packet_data[att_offset+3:]
                                
                                writes.append({
                                    'packet': packet_num,
                                    'time': relative_time,
                                    'opcode': 'Write Request' if opcode == 0x12 else 'Write Command',
                                    'handle': handle,
                                    'value': value,
                                    'hex': ' '.join(f'{b:02X}' for b in value)
                                })
                        
                        # ATT Handle Value Notification (0x1B) - EEG data packets
                        elif opcode == 0x1B:
                            if att_offset + 3 <= len(packet_data):
                                handle = struct.unpack('<H', packet_data[att_offset+1:att_offset+3])[0]
                                value = packet_data[att_offset+3:]
                                
                                notifications.append({
                                    'packet': packet_num,
                                    'time': relative_time,
                                    'handle': handle,
                                    'length': len(value),
                                    'preview': ' '.join(f'{b:02X}' for b in value[:16])
                                })
                
                except Exception as e:
                    pass
        
        print(f"\n[OK] Processed {packet_num} total packets")
        print(f"[OK] Found {len(writes)} write operations")
        print(f"[OK] Found {len(notifications)} data notifications\n")
        
        # Analyze write commands
        if writes:
            print(f"{'='*70}")
            print("WRITE COMMANDS (chronological order)")
            print(f"{'='*70}\n")
            
            for i, w in enumerate(writes):
                print(f"[{i+1}] Time: {w['time']:8.3f}s | Packet #{w['packet']:4d}")
                print(f"    Handle: 0x{w['handle']:04X} | {w['opcode']}")
                print(f"    Value:  {w['hex']}")
                
                # Try ASCII interpretation
                try:
                    ascii_chars = ''.join(chr(b) if 32 <= b < 127 else '.' for b in w['value'])
                    if any(c != '.' for c in ascii_chars):
                        print(f"    ASCII:  {ascii_chars}")
                except:
                    pass
                print()
        
        # Analyze notification patterns
        if notifications:
            print(f"\n{'='*70}")
            print("DATA NOTIFICATIONS (EEG streaming)")
            print(f"{'='*70}\n")
            
            # Group notifications into streaming sessions
            sessions = []
            current_session = []
            last_time = -1
            
            for notif in notifications:
                # If gap > 2 seconds, start new session
                if last_time > 0 and (notif['time'] - last_time) > 2.0:
                    if current_session:
                        sessions.append(current_session)
                    current_session = []
                
                current_session.append(notif)
                last_time = notif['time']
            
            if current_session:
                sessions.append(current_session)
            
            print(f"Detected {len(sessions)} streaming session(s):\n")
            
            for i, session in enumerate(sessions):
                start_time = session[0]['time']
                end_time = session[-1]['time']
                duration = end_time - start_time
                packet_count = len(session)
                rate = packet_count / duration if duration > 0 else 0
                
                print(f"Session {i+1}:")
                print(f"  Start:    {start_time:8.3f}s")
                print(f"  End:      {end_time:8.3f}s")
                print(f"  Duration: {duration:8.3f}s")
                print(f"  Packets:  {packet_count}")
                print(f"  Rate:     {rate:.1f} pkts/s")
                print(f"  First packet preview: {session[0]['preview']}")
                print()
        
        # Cross-reference writes with streaming sessions
        if writes and notifications:
            print(f"\n{'='*70}")
            print("COMMAND-TO-STREAM CORRELATION")
            print(f"{'='*70}\n")
            
            # For each streaming session, find the write command(s) that preceded it
            for i, session in enumerate(sessions):
                session_start = session[0]['time']
                
                print(f"Session {i+1} started at {session_start:.3f}s")
                print(f"Commands sent within 5 seconds before streaming:\n")
                
                # Find writes within 5 seconds before session start
                preceding_writes = [w for w in writes if session_start - 5.0 <= w['time'] < session_start]
                
                if preceding_writes:
                    for w in preceding_writes:
                        time_before = session_start - w['time']
                        print(f"  [{time_before:.3f}s before] Handle 0x{w['handle']:04X}:")
                        print(f"    {w['hex']}")
                else:
                    print(f"  [!] No writes found in the 5 seconds before streaming")
                
                # Check if session ended (look for writes after session)
                session_end = session[-1]['time']
                next_session_start = sessions[i+1][0]['time'] if i+1 < len(sessions) else float('inf')
                
                # Find writes between session end and next session (or within 5s after)
                stop_writes = [w for w in writes if session_end <= w['time'] < min(session_end + 5.0, next_session_start)]
                
                if stop_writes:
                    print(f"\nCommands sent after session ended ({session_end:.3f}s):\n")
                    for w in stop_writes:
                        time_after = w['time'] - session_end
                        print(f"  [{time_after:.3f}s after] Handle 0x{w['handle']:04X}:")
                        print(f"    {w['hex']}")
                
                print()
        
        # Summary and recommendations
        print(f"\n{'='*70}")
        print("ANALYSIS SUMMARY")
        print(f"{'='*70}\n")
        
        if len(sessions) > 0:
            print(f"[OK] Found {len(sessions)} streaming session(s)")
            print(f"[OK] Total EEG packets received: {len(notifications)}")
            
            # Find unique write patterns
            unique_writes = {}
            for w in writes:
                key = (w['handle'], w['hex'])
                if key not in unique_writes:
                    unique_writes[key] = []
                unique_writes[key].append(w['time'])
            
            print(f"\nUnique write commands ({len(unique_writes)} total):\n")
            for (handle, hex_val), times in sorted(unique_writes.items()):
                print(f"  Handle 0x{handle:04X}: {hex_val}")
                print(f"    Sent {len(times)} time(s) at: {', '.join(f'{t:.1f}s' for t in times)}")
            
            print(f"\n{'='*70}")
            print("RECOMMENDATIONS:")
            print(f"{'='*70}\n")
            print("1. The command(s) sent RIGHT BEFORE streaming starts are likely the START command")
            print("2. Commands sent AFTER streaming stops are likely the STOP command")
            print("3. If you paused, look for commands between streaming sessions")
            print("4. Test these commands in your live streaming code\n")
        else:
            print("[!] No streaming sessions detected!")
            print("This could mean:")
            print("  - The device auto-streams without a command")
            print("  - The log didn't capture data notifications")
            print("  - Need to enable notification subscription first\n")


def main():
    import os
    
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    else:
        filename = 'btsnoop_hci.log'
    
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        print("\nUsage: python analyze_stream_commands.py [btsnoop_hci.log]")
        sys.exit(1)
    
    parse_btsnoop_detailed(filename)


if __name__ == "__main__":
    main()
