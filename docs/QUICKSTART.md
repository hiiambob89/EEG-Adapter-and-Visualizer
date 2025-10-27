# Quick Start - Live EEG Streaming

## 🚀 Ready to Stream!

Your system is now configured for live EEG data acquisition and processing.

## Run Live Streaming (Choose One)

### Option 1: Python (Recommended - Full Analysis)

```bash
# Auto-detect and connect to headband
python live_eeg_stream.py

# Scan for devices only
python live_eeg_stream.py --scan-only

# Connect to specific device
python live_eeg_stream.py --address XX:XX:XX:XX:XX:XX

# Stream for 60 seconds then stop
python live_eeg_stream.py --duration 60
```

### Option 2: Node.js (Alternative)

```bash
cd eeg-scanner
node live-stream.js
```

## Test First

```bash
# Verify decoder works with sample packets
python test_decoder.py
```

## What You'll See

```
Scanning for Serenibrain device...
Found device: Serenibrain TH21A (XX:XX:XX:XX:XX:XX)
Connected!

======================================================================
STREAMING EEG DATA - Press Ctrl+C to stop
======================================================================

[  10 pkts]   300 samples | 32.1 pkt/s | 3 channels
[  20 pkts]   600 samples | 32.3 pkt/s | 3 channels

======================================================================
[14:23:45] Channel 0 Analysis (151 samples)
======================================================================
Signal Quality: Good (SNR: 15.2 dB)
Dominant: DELTA | Relax: 45 | Focus: 12

Band Ratios:
  Delta   : 83.2% ████████████████████████████
  Theta   :  9.1% ████
  Alpha   :  4.3% ██
  Beta    :  3.2% █
  Gamma   :  0.2%
```

## Configuration

Edit in `live_eeg_stream.py` (line ~16):

```python
processor = EEGStreamProcessor(
    window_duration=6.0,    # Seconds per analysis window
    sampling_rate=250.0,    # Device specification: 250 Hz ADC sampling
    adc_scale=100.0        # ADC scaling factor
)
```

Edit analysis interval (line ~25):

```python
self.analysis_interval = 2.0  # Seconds between analyses
```

## Files Created

✅ **`process.py`** - Updated decoder with Welch PSD and configurable parameters
✅ **`live_eeg_stream.py`** - Python live streamer (primary)
✅ **`eeg-scanner/live-stream.js`** - Node.js alternative
✅ **`test_decoder.py`** - Validation tests
✅ **`LIVE_STREAMING.md`** - Full documentation

## Troubleshooting

**"No module named 'bleak'"**
```bash
pip install bleak scipy numpy
```

**"No Serenibrain device found"**
- Turn on headband
- Check Bluetooth enabled
- Try `--scan-only` to see all devices
- Use `--address` to specify manually

**Connection errors**
- Ensure device not connected to phone app
- Only one BLE connection at a time
- Restart Bluetooth on PC

## Next Steps

1. **Run live stream** and verify data quality
2. **Compare band values** to app output (you provided: Delta:-8.51, Theta:0.4, Alpha:-0.56, Beta:0.12, Gamma:0.04, SMR:-0.05)
3. **Calibrate ADC scale** if values differ significantly
4. **Build dashboard** for real-time visualization
5. **Add recording** to save data for offline analysis

## Dependencies Installed

- ✅ `bleak` - Bluetooth LE library
- ✅ `numpy` - Numerical computing
- ✅ `scipy` - Signal processing (FFT, Welch)
- ✅ `matplotlib` - Plotting (from earlier work)

## Full Documentation

See `LIVE_STREAMING.md` for:
- Architecture details
- Packet format specifications
- Advanced configuration
- Export to CSV/visualization
- WebSocket integration examples

---

**Ready!** Turn on your headband and run `python live_eeg_stream.py`
