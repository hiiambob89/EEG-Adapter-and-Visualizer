# Capture BLE Commands via ADB

## Prerequisites
1. Android phone with USB debugging enabled
2. ADB installed on Windows
3. Serenibrain app installed on phone

## Steps to Capture BLE Traffic

### 1. Enable Bluetooth HCI Snoop Log on Android
1. On your Android phone, go to **Settings** → **Developer Options**
2. Find **Enable Bluetooth HCI snoop log** and turn it ON
3. If you don't see Developer Options:
   - Go to **Settings** → **About Phone**
   - Tap **Build Number** 7 times to enable Developer Mode

### 2. Connect Phone via USB
```powershell
# Check if phone is connected
adb devices
```

### 3. Clear Old Logs
```powershell
# Clear previous Bluetooth logs
adb shell rm /sdcard/btsnoop_hci.log
adb shell rm /data/misc/bluetooth/logs/btsnoop_hci.log
```

### 4. Reproduce the Connection
1. **Power cycle the EEG headband** (turn off, turn on)
2. **Open Serenibrain app** and connect to the device
3. **Wait for data to start streaming**
4. **Disconnect the app**

### 5. Pull the Log File
```powershell
# Pull the HCI log (location varies by Android version)
adb pull /sdcard/btsnoop_hci.log btsnoop_hci.log

# If that doesn't work, try:
adb shell su -c "cp /data/misc/bluetooth/logs/btsnoop_hci.log /sdcard/"
adb pull /sdcard/btsnoop_hci.log btsnoop_hci.log
```

### 6. Analyze with Wireshark
1. Install Wireshark: https://www.wireshark.org/download.html
2. Open `btsnoop_hci.log` in Wireshark
3. Apply filter: `btatt`
4. Look for:
   - **Write Request** or **Write Command** to handle `0x????` (we need to find the handle for `8653000c`)
   - The **value** being written is the activation command!

## Alternative: Real-time Logging
```powershell
# Real-time log streaming (requires root)
adb shell su -c "cat /data/misc/bluetooth/logs/btsnoop_hci.log" > btsnoop_hci.log
```

## What to Look For

In Wireshark, find packets like:
- **ATT Write Request** or **ATT Write Command**
- **Destination Handle**: Should correspond to characteristic `8653000c`
- **Value**: This is the activation command!

Example:
```
ATT Write Request
  Handle: 0x001e
  Value: 01
```

The "Value" field is what we need!

## Troubleshooting

If `btsnoop_hci.log` doesn't exist:
- Some phones store it in `/data/log/bt/btsnoop_hci.log`
- Try: `adb shell find /sdcard -name "btsnoop*"`
- Try: `adb shell find /data -name "btsnoop*"` (requires root)
