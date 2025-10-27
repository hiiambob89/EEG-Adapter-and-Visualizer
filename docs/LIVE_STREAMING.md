# Serenibrain EEG Live Streaming

Real-time EEG data acquisition and processing from Serenibrain headband via Bluetooth LE.

## Features

- **Live BLE streaming** from 3-electrode EEG headband
- **Real-time band power analysis** (Delta, Theta, Alpha, Beta, Gamma)
- **Sliding window processing** with configurable buffer sizes
- **Dual implementation**: Python (Bleak) and Node.js (Noble)
- **Automatic device discovery** and connection
- **Per-channel analysis** with SNR quality metrics

## Quick Start

### Python Version (Recommended)

**Install dependencies:**
```bash
# Activate virtual environment
.venv\Scripts\activate

# Install required packages (already done)
pip install bleak numpy scipy
```

**Run:**
```bash
# Auto-scan and connect
python live_eeg_stream.py

# Scan only
python live_eeg_stream.py --scan-only

# Specify device address
python live_eeg_stream.py --address XX:XX:XX:XX:XX:XX

# Stream for 30 seconds
python live_eeg_stream.py --duration 30
```

**Options:**
- `--address ADDR` - BLE device address (auto-detected if omitted)
- `--uuid UUID` - Notification characteristic UUID (auto-detected)
- `--duration SEC` - Stream duration in seconds (default: indefinite)
- `--scan-only` - Only scan for devices, don't connect

### Node.js Version

**Install dependencies:**
```bash
cd eeg-scanner
npm install @abandonware/noble
```

**Run:**
```bash
# Auto-scan and connect
node live-stream.js

# Scan only
node live-stream.js --scan-only
```

**Note:** Node.js version provides basic stats but delegates FFT analysis to Python.

## Output

### Real-time Console Output

```
Scanning for Serenibrain device (timeout: 10.0s)...
Found device: Serenibrain TH21A (XX:XX:XX:XX:XX:XX)

Connected to XX:XX:XX:XX:XX:XX
Subscribing to characteristic: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

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
  Delta   : 83.2% ████████████████████████████████████████
  Theta   :  9.1% ████
  Alpha   :  4.3% ██
  Beta    :  3.2% █
  Gamma   :  0.2% 
```

### Analysis Intervals

- **Progress updates**: Every 10 packets (~0.3 seconds)
- **Band power analysis**: Every 2 seconds per channel
- **Buffer size**: 6 seconds × 32.26 Hz ≈ 194 samples per channel

## Architecture

### Data Flow

```
BLE Device (TH21A)
    ↓
BLE Notifications (92-byte packets, ~32 Hz)
    ↓
decode_serenibrain_packet() → Extract 24-bit samples
    ↓
Channel Buffers (circular deque, 6-second window)
    ↓
calculate_band_powers() → Welch PSD + band integration
    ↓
Real-time console output + metrics
```

### Packet Format

**Type 0x01 (Status):**
- 44 bytes
- Contains device model ("TH21A")
- Sent once at connection

**Type 0x02 (EEG Data):**
- 92 bytes (typical)
- 10 samples × 7 bytes each
- Sample format: `[int24_le (3 bytes)] [padding (2 bytes)] [sample_idx (2 bytes)]`
- Channel assignment: `sample_idx % num_channels`

### Band Power Calculation

**Method:** Welch's periodogram (recommended) or Hamming-windowed FFT

**Frequency Bands:**
- Delta: 0.5-4 Hz
- Theta: 4-8 Hz
- Alpha: 8-13 Hz (relaxation indicator)
- Beta: 13-30 Hz (focus indicator)
- Gamma: 30-50 Hz (limited at 32 Hz Nyquist)

**Metrics:**
- Absolute power (µV²)
- Relative power (%)
- SNR (dB) - top 20% of spectrum as noise
- Relaxation score: alpha/beta ratio × 20
- Focus score: beta/(alpha+theta) × 30

## Configuration

### In `live_eeg_stream.py`:

```python
processor = EEGStreamProcessor(
    window_duration=6.0,      # Seconds of data for analysis
    sampling_rate=32.26,      # Measured from logs
    adc_scale=100.0          # Raw int24 → µV conversion
)
```

### In `process.py`:

```python
def calculate_band_powers(voltages, sampling_rate=32.26, use_welch=True):
    # use_welch=True: Better for short segments (recommended)
    # use_welch=False: Direct FFT (faster but noisier)
```

## Troubleshooting

### "No Serenibrain device found"
1. Ensure headband is powered on
2. Check Bluetooth is enabled
3. Try manual address: `--address XX:XX:XX:XX:XX:XX`
4. Use `--scan-only` to list all BLE devices

### "No notification characteristic found"
- Device may use custom UUIDs
- Run with debug to see all characteristics
- Manually specify with `--uuid`

### Low SNR or noisy data
- Check electrode contact quality
- Reduce movement artifacts
- Increase `window_duration` for better frequency resolution
- Verify `adc_scale` matches device specs

### Python "bleak" import error
```bash
pip install bleak
```

### Node.js "noble" issues (Windows)
- Requires Visual Studio Build Tools
- Alternative: Use Python version

## Advanced Usage

### Export to CSV

Modify `_analyze_channel()` to write results to file:

```python
import csv

with open('eeg_bands.csv', 'a', newline='') as f:
    writer = csv.writer(f)
    writer.writerow([
        timestamp, channel_id,
        analysis['band_ratios']['delta'],
        analysis['band_ratios']['theta'],
        # ... etc
    ])
```

### Real-time Visualization

Integrate with matplotlib animation:

```python
from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots()
# Update plot in _analyze_channel()
```

### WebSocket Streaming

Add Flask-SocketIO to broadcast to web dashboard:

```python
from flask_socketio import SocketIO, emit

socketio.emit('eeg_update', {
    'channel': channel_id,
    'bands': analysis['band_ratios']
})
```

## Files

- `live_eeg_stream.py` - Python live streamer (main implementation)
- `eeg-scanner/live-stream.js` - Node.js alternative
- `process.py` - Packet decoder + band power calculator
- `eeg-scanner/tools/` - Offline analysis tools for `log.txt`

## Next Steps

1. **Calibrate ADC scale** - Measure known signal to determine exact µV conversion
2. **Validate band powers** - Compare against app-reported values
3. **Build UI dashboard** - Real-time web visualization
4. **Add recording** - Save raw data + analysis to database
5. **Implement filters** - Notch filter for 50/60 Hz line noise
6. **Multi-session analysis** - Aggregate stats over time

## References

- Bleak (Python BLE): https://github.com/hbldh/bleak
- Noble (Node.js BLE): https://github.com/abandonware/noble
- Welch's method: `scipy.signal.welch`
- EEG band definitions: Standard clinical ranges
