# Updated Live Streaming Code - Ready to Test! 🚀

## What Changed

Both `live_eeg_stream.py` and `live-stream.js` have been updated with the discovered stream control commands from the Bluetooth log analysis.

## New Features

### Stream Control Commands
✅ **START command**: `CTRL 00 03 00 05` - Triggers streaming  
✅ **STOP command**: `CTRL 00 03 00 03` - Stops streaming  
✅ **Keep-alive**: `CTRL 00 05 00 02` - Sent every 1 second (optional)  
✅ **Alternative START**: `CTRL 00 04 00 01` - Backup start command  

### Automatic Features
- Auto-detects both notify AND write characteristics
- Sends START command automatically after connection
- Falls back to alternative START if no data received
- Optional keep-alive heartbeat (enabled if streaming works)
- Sends STOP command on disconnect
- Better error messages and troubleshooting

## How to Test

### Python Version
```powershell
# Scan for device
python live_eeg_stream.py --scan-only

# Stream with auto-detection
python live_eeg_stream.py --address <YOUR_DEVICE_ADDRESS>

# Stream with specific characteristics (if needed)
python live_eeg_stream.py --address <ADDRESS> --uuid <NOTIFY_UUID> --write-uuid <WRITE_UUID>

# Stream for 30 seconds
python live_eeg_stream.py --address <ADDRESS> --duration 30
```

### Node.js Version
```powershell
cd eeg-scanner

# Scan for device
node live-stream.js --scan-only

# Stream with auto-detection
node live-stream.js
```

## What to Expect

### Success Scenario:
```
Connecting to XX:XX:XX:XX:XX:XX...
Connected!
Found notify characteristic: 0000XXXX-...
Found write characteristic: 0000XXXX-...
[OK] Subscribed to notifications

Sending START command...
[OK] START command sent: CTRL 00 03 00 05

======================================================================
STREAMING EEG DATA - Press Ctrl+C to stop
======================================================================

Waiting for data...
[OK] Keep-alive enabled (1s interval)
[  10 pkts]    50 samples | 25.0 pkt/s | 2 channels
[  20 pkts]   100 samples | 25.1 pkt/s | 2 channels
...
```

### If No Data Received:
```
[!] No packets received, trying alternative START command...
[OK] Alternative START sent: CTRL 00 04 00 01
[!] Still no data - continuing to wait...
```

### On Stop:
```
^C
Stopping stream...
[OK] STOP command sent

STREAM STATISTICS
======================================================================
Total Packets: 1234
Total Samples: 6170
Duration: 49.2s
Packet Rate: 25.1 pkt/s
Channels: 2
```

## Troubleshooting

### No characteristics found?
- Make sure device is powered on and in pairing mode
- Try running as administrator (Windows)
- Check Bluetooth is enabled

### Commands sent but no data?
- Device might need to be activated via the app first
- Battery might be low
- Try disconnecting/reconnecting

### Connection fails?
- Make sure no other app is connected to the headband
- Close the Serenibrain app if it's running
- Restart Bluetooth on your PC

## Next Steps

Once streaming works:
1. ✅ Verify packet rate (~25 pkt/s expected)
2. ✅ Check data format (should start with "DATA")
3. ✅ Decode the data packets to extract EEG samples
4. ✅ Implement real-time FFT for frequency band analysis
5. ✅ Build visualization dashboard

## Command Reference

### All Control Commands
```python
# Enable notifications (CCCD)
[0x01, 0x00]

# Start streaming (primary)
[0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05]

# Start streaming (alternative)
[0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01]

# Keep-alive / heartbeat
[0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02]

# Stop streaming
[0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03]
```

All commands use ASCII "CTRL" prefix (0x43 0x54 0x52 0x4C) followed by command parameters.

Good luck testing! 🎉
