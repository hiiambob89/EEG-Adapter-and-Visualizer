# How to Capture Bluetooth Streaming Commands

## Problem
The current btsnoop_hci.log only contains HCI setup commands (Commands/Events), but no ACL Data packets. We need the ACL Data packets to see the actual BLE write commands and notifications.

## Solution: Proper Capture Procedure

### Step 1: Enable BT Logging
```powershell
.\platform-tools\adb.exe shell settings put secure bluetooth_hci_log 1
```

### Step 2: Restart Bluetooth (to start fresh log)
```powershell
# Turn BT off
.\platform-tools\adb.exe shell cmd bluetooth_manager disable

# Wait 2 seconds
Start-Sleep -Seconds 2

# Turn BT on
.\platform-tools\adb.exe shell cmd bluetooth_manager enable
```

### Step 3: Connect and Stream
1. Open the Serenibrain app
2. Connect to the headband
3. **Start streaming** and let it run for 10-15 seconds
4. **Stop streaming**
5. **Start streaming again** (to see the start command twice)
6. **Let it run for another 10 seconds**
7. **Pause if possible**
8. **Resume if possible**
9. **Stop streaming**

### Step 4: Capture the Log IMMEDIATELY (while still connected)
```powershell
# Copy log from device
.\platform-tools\adb.exe shell "su -c 'cp /data/misc/bluetooth/logs/btsnoop_hci.log /sdcard/bt_streaming.log'"

# Pull to PC
.\platform-tools\adb.exe pull /sdcard/bt_streaming.log .
```

### Step 5: Analyze
```powershell
python analyze_stream_commands.py bt_streaming.log
```

## What We're Looking For

The new log should contain:

1. **HCI ACL Data packets (type 0x02)** - These contain the actual BLE communication
2. **ATT Write Request/Command (0x12/0x52)** - Commands sent TO the headband
3. **ATT Handle Value Notification (0x1B)** - EEG data packets FROM the headband

## Expected Output

You should see packets like:
```
Type: HCI ACL Data
  L2CAP: CID=0x0004 (ATT)
  ATT: Opcode=Write Request
  ATT: Handle=0x????
  ATT: Value=(X bytes) <command bytes>
```

Followed by many:
```
Type: HCI ACL Data
  L2CAP: CID=0x0004 (ATT)
  ATT: Opcode=Handle Value Notification
  ATT: Handle=0x????
  ATT: Value=(X bytes) <EEG data>
```

## Why the Current Log is Empty

The current log only has 117 packets and they're all Commands/Events. This means:
- Either BT was just enabled/disabled without any app connection
- Or the log was captured after disconnection (ACL data was already flushed)
- Or the logging wasn't active during the actual streaming session

## Quick Test

To verify logging is working properly, try this quick test:

```powershell
# Enable logging
.\platform-tools\adb.exe shell settings put secure bluetooth_hci_log 1

# Restart BT
.\platform-tools\adb.exe shell cmd bluetooth_manager disable
Start-Sleep -Seconds 2
.\platform-tools\adb.exe shell cmd bluetooth_manager enable

# Now connect with the app and stream for 10 seconds

# Capture while STILL CONNECTED
.\platform-tools\adb.exe shell "su -c 'cp /data/misc/bluetooth/logs/btsnoop_hci.log /sdcard/test.log'"
.\platform-tools\adb.exe pull /sdcard/test.log .

# Check size - should be much larger (100KB+ if streaming)
ls test.log
```

A proper streaming capture should be **at least 100-500 KB** for a 10-second session.
