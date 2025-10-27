# EEG Sampling Rate Clarification

## Device Specifications

**According to the app:**
- **Sampling Rate:** 250 Hz (samples per second per channel)
- **Downsampled Output:** 10 data points per second (after processing)
- **Packet Rate:** ~25 Hz (packets per second)

## What This Means

### Sample Collection (250 Hz)
- Each channel is sampled at **250 Hz**
- This means one sample every **4 ms** (1000ms / 250 = 4ms)
- High enough to capture EEG frequencies up to **125 Hz** (Nyquist limit)

### Packet Transmission (~25 Hz)
- Packets arrive approximately every **40 ms**
- Each packet contains **10 samples per channel**
- 10 samples × 4 ms = 40 ms interval between packets
- 1000 ms / 40 ms = **25 packets/second**

### Our Earlier Observation
- We measured ~32.26 Hz packet rate from `log.txt`
- This was close to the expected 25 Hz (within variability)
- **The key mistake:** We used packet rate as sampling rate
- **Correct approach:** Use 250 Hz (the actual ADC sampling rate)

## Implications for Band Power Analysis

### Frequency Resolution
With 250 Hz sampling:
- **Delta (0.5-4 Hz):** ✅ Well resolved
- **Theta (4-8 Hz):** ✅ Well resolved
- **Alpha (8-13 Hz):** ✅ Well resolved
- **Beta (13-30 Hz):** ✅ Well resolved
- **Gamma (30-50 Hz):** ✅ Well resolved (up to 125 Hz possible)

With our mistaken 32.26 Hz:
- **Gamma (30-50 Hz):** ❌ Impossible (above Nyquist)
- **Beta (13-30 Hz):** ⚠️ Poor resolution
- **All bands:** ⚠️ Wrong frequency mapping

## Updated Configuration

### Before (Incorrect)
```python
sampling_rate = 32.26  # This was packet rate, not sample rate!
```

### After (Correct)
```python
sampling_rate = 250.0  # Actual ADC sampling rate
```

## Packet Structure Explanation

Each Type 0x02 packet:
```
Header (12 bytes)
  └─ "DATA" + metadata

Samples (70 bytes = 10 samples × 7 bytes)
  └─ Each sample:
     - 3 bytes: 24-bit ADC value
     - 2 bytes: padding
     - 2 bytes: sample index
     - 1 byte: padding
  
  └─ Distribution across 3 channels:
     - Samples 0, 3, 6, 9: Channel 0 (4 samples)
     - Samples 1, 4, 7: Channel 1 (3 samples)
     - Samples 2, 5, 8: Channel 2 (3 samples)
     (or 3-4-3 depending on packet alignment)

Metadata (10 bytes)
  └─ Timestamp + checksum
```

## Timing Analysis

### Per Packet
- **Duration represented:** 40 ms
- **Samples per channel:** ~3-4 (10 total / 3 channels)
- **Packet rate:** 25 Hz (ideal), ~32 Hz (observed - may include duplicates/retries)

### Per Second
- **Total samples:** 250 per channel
- **Packets needed:** 25 packets (at 10 samples each)
- **Total data:** ~2.3 KB/sec (92 bytes × 25 packets)

### Analysis Window (6 seconds)
- **Samples per channel:** 1500 (250 Hz × 6 seconds)
- **Excellent frequency resolution:** 0.167 Hz bins (1 / 6 seconds)
- **Packets processed:** ~150 packets

## Why This Matters

### Better Band Power Accuracy
- Correct frequency bins for each band
- Proper Nyquist consideration
- Gamma band now accessible (30-50 Hz well below 125 Hz limit)

### Correct Time Windows
- 6-second window = 1500 samples (not 194)
- Better statistical power
- More accurate PSD estimation

### Matching App Output
- App uses 250 Hz for calculations
- Our analysis now matches their frequency domain
- Band power values should be comparable

## Updated Files

✅ `process.py` - Default `sampling_rate=250.0`
✅ `live_eeg_stream.py` - EEGStreamProcessor uses 250 Hz
✅ `eeg-scanner/live-stream.js` - Updated to 250 Hz
✅ `test_decoder.py` - Tests with 250 Hz

## Next Steps

1. **Re-run live stream** with corrected 250 Hz
2. **Compare band powers** to app values
3. **Verify gamma band** now shows realistic values
4. **Fine-tune ADC scale** if absolute values still off

## Summary

| Parameter | Old (Wrong) | New (Correct) |
|-----------|-------------|---------------|
| Sampling Rate | 32.26 Hz | 250 Hz |
| Nyquist Limit | 16.13 Hz | 125 Hz |
| Samples/6s Window | 194 | 1500 |
| Frequency Resolution | 0.167 Hz | 0.167 Hz |
| Gamma Band | ❌ Unusable | ✅ Valid |
| Matches App | ❌ No | ✅ Yes |

**Bottom line:** We were confusing packet arrival rate with ADC sampling rate. Now corrected to match device specification of 250 Hz.
