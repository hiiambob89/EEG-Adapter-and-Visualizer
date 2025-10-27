# APK Analysis Guide

## Method 1: Online Decompiler (Easiest)
1. Go to http://www.javadecompilers.com/apk
2. Upload your APK
3. Wait for decompilation
4. Search for keywords like:
   - "8653000c" (write characteristic UUID)
   - "writeCharacteristic"
   - "BluetoothGatt"
   - "START" or "STREAM"
   - "0x01" or "0x02"

## Method 2: JADX (Local, Better)
1. Download JADX from: https://github.com/skylot/jadx/releases
2. Extract and run `jadx-gui.bat`
3. Open your APK file
4. Search for the same keywords

## What to Look For

Once decompiled, search for files containing BLE code:
- Files with "Bluetooth", "BLE", "Gatt" in the name
- Look for `writeCharacteristic()` calls
- Look for the write characteristic UUID: `8653000c-43e6-47b7-9cb0-5fc21d4ae340`
- Check what byte array is being written

## Common Patterns

The activation code will look something like:
```java
characteristic.setValue(new byte[]{0x01});
gatt.writeCharacteristic(characteristic);
```

Or:
```java
characteristic.setValue("START".getBytes());
```

Or:
```java
byte[] command = {0x44, 0x41, 0x54, 0x41, 0x01}; // "DATA\x01"
```

Save the byte sequence you find!
