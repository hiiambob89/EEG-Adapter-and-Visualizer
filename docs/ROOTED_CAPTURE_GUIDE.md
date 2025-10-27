# BLE Capture with Rooted Android Device

## Setup (One-time)
1. Root the device (Magisk is easiest)
2. Install Serenibrain APK on it
3. Enable Developer Options → Bluetooth HCI snoop log
4. Connect via USB and enable USB debugging

## Capture Process

### 1. Clear old logs
```powershell
.\platform-tools\adb.exe shell su -c "rm /data/misc/bluetooth/logs/btsnoop_hci.log"
```

### 2. Power cycle the EEG headband
Turn it off, then back on (fresh start)

### 3. Connect with the app
Open Serenibrain app and connect to the headband

### 4. Wait for data to stream
Let it run for 5-10 seconds

### 5. Pull the log
```powershell
.\platform-tools\adb.exe shell su -c "cp /data/misc/bluetooth/logs/btsnoop_hci.log /sdcard/btsnoop.log"
.\platform-tools\adb.exe pull /sdcard/btsnoop.log btsnoop_hci.log
```

### 6. Analyze it
```powershell
python analyze_btsnoop.py
```

This will show ALL BLE commands the app sent, including the activation command!

## Alternative: Real-time monitoring

If the above doesn't work, you can also use root to monitor in real-time:

```powershell
# Install tcpdump on the device
.\platform-tools\adb.exe shell su -c "which tcpdump || echo 'Need to install tcpdump'"

# Or just tail the log in real-time while connecting
.\platform-tools\adb.exe shell su -c "tail -f /data/misc/bluetooth/logs/btsnoop_hci.log" > btsnoop_hci.log
# (Press Ctrl+C after connection is established)
```

## What We'll Find

The btsnoop_hci.log will contain:
- Connection handshake
- Service discovery
- Notification enabling (CCCD write)
- **THE ACTIVATION COMMAND** ← This is what we need!
- All data packets

Our analyze_btsnoop.py script will extract and show the activation command clearly.

## Recommended Cheap Devices for Rooting

Good options (usually $50-100 used):
- Google Pixel 2/3/4a (easiest to root)
- OnePlus 6/7 (very root-friendly)
- Xiaomi Redmi Note series (unlock bootloader easily)

Avoid: Carrier-locked phones, Samsung (Knox issues)
