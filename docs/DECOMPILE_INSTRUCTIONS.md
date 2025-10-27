# Quick APK Decompilation Steps

Since we have the APK extracted, here's the fastest way to find the BLE command:

## Option 1: Use JADX (Recommended)
1. Download JADX: https://github.com/skylot/jadx/releases/latest
   - Get `jadx-gui-1.5.0.exe` or the .zip for Windows
2. Run JADX GUI
3. Open: `SereniBrain_extracted\com.HNNK.NingNao.apk`
4. Wait for decompilation
5. Use the search function (Ctrl+Shift+F) to search for:
   - `8653000c` (write characteristic UUID)
   - `writeCharacteristic`
   - `setValue`

## Option 2: Online Decompiler
1. Go to: https://www.apkdecompilers.com/
2. Upload: `SereniBrain_extracted\com.HNNK.NingNao.apk`
3. Download the decompiled source
4. Search for the same keywords

## What We're Looking For

In the decompiled code, look for something like:

```java
// Example 1: Simple byte write
characteristic.setValue(new byte[]{0x01});

// Example 2: String write
characteristic.setValue("START");

// Example 3: Multiple bytes
byte[] cmd = {0x44, 0x41, 0x54, 0x41, 0x01}; // "DATA" + 0x01
characteristic.setValue(cmd);
```

## Files to Check
Look in files with names containing:
- `Bluetooth`
- `BLE`
- `Gatt`
- `Device`
- `Connection`
- `Service`

The package name is `com.HNNK.NingNao` so the Java files will be in that package structure.
