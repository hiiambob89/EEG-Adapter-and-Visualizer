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
- Device: `F6:82:59:5D:CC:5D`
- Service: `8653000a-43e6-47b7-9cb0-5fc21d4ae340`
- Notify: `8653000b-43e6-47b7-9cb0-5fc21d4ae340`
- Write: `8653000c-43e6-47b7-9cb0-5fc21d4ae340`

## Requirements

- Python 3.8+
- Windows 10/11 with Bluetooth support
- Python packages: `bleak`, `numpy`, `scipy`

```bash
pip install bleak numpy scipy
```

## Next Steps

Building web-based real-time monitoring dashboard in `web/` folder.
