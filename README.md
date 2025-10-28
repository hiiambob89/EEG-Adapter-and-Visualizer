# Serenibrain EEG Monitoring System

Real-time EEG data streaming and analysis from Serenibrain TH21A headband.

## Quick Start

1. **Stream EEG Data**
   ```bash
   python live_eeg_stream.py
   ```
   This will connect to your Serenibrain headband and display real-time brainwave analysis.

## Features

- ✅ Live EEG streaming from 3 channels
- ✅ Real-time band power analysis (Delta, Theta, Alpha, Beta, Gamma)
- ✅ Relaxation and Focus metrics
- ✅ Signal quality monitoring (SNR)
- ✅ 250 Hz sampling rate with ~25 packets/second

## System Architecture

### Core Files
- `live_eeg_stream.py` - Main streaming application with BLE communication
- `process.py` - Signal processing and band power analysis

### Folders
- `docs/` - Research documentation and guides
- `tools/` - Analysis utilities
- `archive/` - Historical test files and logs
- `web/` - Web monitoring interface (in development)

## Device Information

**Serenibrain TH21A**
- My specific Device: `F6:82:59:5D:CC:5D`
### GATT services & characteristics

- Service (data): `8653000a-43e6-47b7-9cb0-5fc21d4ae340`  
- Notify (data notify): `8653000b-43e6-47b7-9cb0-5fc21d4ae340`  
- Write (control/command): `8653000c-43e6-47b7-9cb0-5fc21d4ae340`

Note: these UUIDs are what I observed on my TH21A (Device: `F6:82:59:5D:CC:5D`). They are may be consistent for the same model and firmware but are not guaranteed across different models or firmware versions — always verify on your unit.

Quick verification
- Use nRF Connect (mobile/desktop) to inspect advertised services and characteristics.
- Or run a small Bleak check:

```python
from bleak import BleakClient, BleakScanner
import asyncio

addr = "F6:82:59:5D:CC:5D"
async def main():
   dev = await BleakScanner.find_device_by_address(addr, timeout=5.0)
   async with BleakClient(dev) as client:
      for svc in client.services:
         print(svc.uuid)
         for ch in svc.characteristics:
            print("  ", ch.uuid, ch.properties)

asyncio.run(main())
```

If you get different UUIDs, update the UUIDs used in `live_eeg_stream.py`.

## Requirements

### System Requirements
- Python 3.8+
- Windows 10/11 with Bluetooth support

### Python Dependencies

**Core EEG Streaming:**
```bash
pip install bleak numpy scipy
```

**Data Analysis (dataanalysis.py):**
```bash
pip install pandas matplotlib scipy
```

**Web Dashboard (Optional):**
```bash
pip install fastapi uvicorn websockets python-multipart
```

**Complete Installation (All Features):**
```bash
# Install all dependencies at once
pip install bleak numpy scipy pandas matplotlib fastapi uvicorn websockets python-multipart
```

**Or use requirements files:**
```bash
# Core streaming and analysis
pip install bleak numpy scipy pandas matplotlib

# Add web server
pip install -r web/requirements.txt
```

### Complete Dependency List
- `bleak` - Bluetooth Low Energy communication
- `numpy` - Numerical computing for signal processing
- `scipy` - Scientific computing (FFT, filtering, band power analysis)
- `pandas` - Data analysis and CSV handling
- `matplotlib` - Plotting and visualization
- `fastapi` - Web framework for dashboard server
- `uvicorn` - ASGI server for FastAPI
- `websockets` - WebSocket support for real-time streaming
- `python-multipart` - File upload support for web server

## Usage

### 1. Command-Line EEG Streaming

Stream EEG data directly to the console:
```bash
python live_eeg_stream.py
```

### 2. Web Dashboard (Real-Time Visualization)

The web dashboard provides real-time visualization with:
- Live brainwave graphs (Delta, Theta, Alpha, Beta, Gamma)
- Relaxation and Focus metrics
- Band power analysis
- CSV recording with filtered voltage data
- Optional "Locked In" focus alerts (toggleable)

**Start the web server:**
```bash
cd web
python server.py
```

Then open your browser to:
```
http://localhost:8000
```

**Web Dashboard Controls:**
- **Start Streaming**: Connects to your Serenibrain headband and begins data flow
- **Stop Streaming**: Disconnects from the headband
- **Start Recording CSV**: Records EEG data with band-filtered voltages (matches official app format)
- **Enable Focus Alerts**: Toggle motivational alerts for focus levels (disabled by default)

The dashboard will automatically detect and connect to your Serenibrain device.

## Next Steps

Building web-based real-time monitoring dashboard in `web/` folder.
