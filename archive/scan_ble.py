"""
Quick BLE device scanner - shows all nearby Bluetooth LE devices
"""

import asyncio
from bleak import BleakScanner

async def scan_devices(duration=5.0):
    print(f"Scanning for BLE devices ({duration}s)...\n")
    
    devices = await BleakScanner.discover(timeout=duration)
    
    if not devices:
        print("No BLE devices found!")
        print("\nTroubleshooting:")
        print("  - Ensure Bluetooth is enabled on this PC")
        print("  - Turn on the EEG headband")
        print("  - Try scanning for longer (increase duration)")
        return
    
    print(f"Found {len(devices)} device(s):\n")
    print(f"{'Name':<30} {'Address':<20} {'RSSI':<6} {'Details'}")
    print("=" * 80)
    
    serenibrain_found = False
    
    for device in devices:
        name = device.name or "(Unknown)"
        address = device.address
        rssi = device.rssi if hasattr(device, 'rssi') else "N/A"
        
        # Highlight potential EEG devices
        is_target = any(keyword in name.lower() for keyword in ['serenibrain', 'th21a', 'eeg', 'brain'])
        marker = " <-- TARGET" if is_target else ""
        
        if is_target:
            serenibrain_found = True
        
        print(f"{name:<30} {address:<20} {rssi!s:<6} {marker}")
    
    print("\n" + "=" * 80)
    
    if serenibrain_found:
        print("\n✓ Serenibrain device detected!")
        print("\nTo connect:")
        print("  python live_eeg_stream.py")
    else:
        print("\n⚠ No Serenibrain device found")
        print("\nIf your device is on:")
        print("  - It may use a different name")
        print("  - Try connecting to any suspicious device:")
        print("    python live_eeg_stream.py --address XX:XX:XX:XX:XX:XX")

if __name__ == "__main__":
    import sys
    
    duration = 5.0
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except:
            print(f"Usage: {sys.argv[0]} [duration_seconds]")
            sys.exit(1)
    
    asyncio.run(scan_devices(duration))
