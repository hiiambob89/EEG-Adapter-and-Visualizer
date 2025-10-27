#!/usr/bin/env python3
"""Reconstruct candidate channels from frames_with_time.jsonl and compute band powers.

Assumes frames_with_time.jsonl exists (created by extract_frames_times.js).
Uses candidate int16 offsets [30,44,58] (based on prior analysis). Computes PSD and band power
for the first 6 seconds of data and writes plots to tools/plots/.
"""
import os, json, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
FRAMES_PATH = os.path.join(ROOT, 'frames_with_time.jsonl')
OUTDIR = os.path.join(ROOT, 'plots')
os.makedirs(OUTDIR, exist_ok=True)

if not os.path.exists(FRAMES_PATH):
    print('Missing', FRAMES_PATH, '- run tools/extract_frames_times.js first')
    raise SystemExit(2)

frames = [json.loads(l) for l in open(FRAMES_PATH,'r',encoding='utf8').read().strip().splitlines()]
print('Loaded', len(frames), 'frames')

# candidate offsets (int16) to try as 3 electrodes
offsets = [30,44,58]

times = np.array([f['ts'] for f in frames], dtype=float)/1000.0
dt = np.diff(times)
median_dt = np.median(dt)
fs = 1.0/median_dt if median_dt>0 else None
print(f'Estimated frame rate (median): {fs:.3f} Hz')

# extract channel values (int16) per frame, set to nan if missing
ch_vals = {o: [] for o in offsets}
for f in frames:
    # clean hex string (remove spaces/dashes)
    import re
    cleaned = re.sub(r'[^0-9A-Fa-f]', '', f['hex'])
    buf = bytes.fromhex(cleaned)
    for o in offsets:
        if o+2 <= len(buf):
            # little-endian int16
            v = int.from_bytes(buf[o:o+2],'little',signed=True)
        else:
            v = float('nan')
        ch_vals[o].append(v)

ch_arrays = {o: np.array(ch_vals[o], dtype=float) for o in offsets}

# Build a mask of frames where all channels have data
valid_mask = np.ones(len(frames), dtype=bool)
for o in offsets:
    valid_mask &= ~np.isnan(ch_arrays[o])

if not valid_mask.any():
    print('No frames with all candidate offsets present')
    raise SystemExit(3)

# restrict to frames where all channels present
times_valid = times[valid_mask]
ch_data = np.vstack([ch_arrays[o][valid_mask] for o in offsets])

# choose first 6 seconds window
start_t = times_valid[0]
end_t = start_t + 6.0
window_mask = (times_valid >= start_t) & (times_valid < end_t)
if window_mask.sum() < 8:
    print('Not enough samples in 6s window, using all valid frames')
    window_mask = np.ones_like(times_valid, dtype=bool)

ts = times_valid[window_mask]
data = ch_data[:, window_mask]
N = data.shape[1]
fs_actual = 1.0/np.median(np.diff(ts)) if N>1 else fs
print(f'Using {N} samples over {ts[0]:.3f}..{ts[-1]:.3f} s, fs ~ {fs_actual:.3f} Hz')

# plot time series
plt.figure(figsize=(12,6))
for i,o in enumerate(offsets):
    plt.plot(np.arange(N)/fs_actual, data[i], label=f'off_{o}')
plt.xlabel('seconds')
plt.ylabel('raw int16')
plt.legend()
png_ts = os.path.join(OUTDIR, 'reconstructed_timeseries.png')
plt.tight_layout(); plt.savefig(png_ts)
print('Wrote', png_ts)

# compute PSD via periodogram (rfft)
def compute_psd(x, fs):
    X = np.fft.rfft(x * np.hanning(len(x)))
    psd = (np.abs(X)**2) / (len(x)*fs)
    freqs = np.fft.rfftfreq(len(x), d=1.0/fs)
    return freqs, psd

bands = {
    'delta': (0.5,4),
    'theta': (4,8),
    'alpha': (8,12),
    'beta': (12,30),
    'gamma': (30,100),
    'smr': (12,15)
}

results = {}
for i,o in enumerate(offsets):
    x = data[i]
    # remove mean
    x = x - np.nanmean(x)
    freqs, psd = compute_psd(x, fs_actual)
    total_power = psd.sum()
    band_powers = {}
    for name,(f0,f1) in bands.items():
        mask = (freqs >= f0) & (freqs < f1)
        p = psd[mask].sum()
        band_powers[name] = float(p)
    # normalize
    band_pows_pct = {k:(v/(total_power+1e-12))*100.0 for k,v in band_powers.items()}
    results[o] = {'mean': float(np.mean(data[i])), 'std': float(np.std(data[i])), 'band_power': band_powers, 'band_pct': band_pows_pct}

    # save PSD plot per channel
    plt.figure(figsize=(8,4))
    plt.semilogy(freqs, psd)
    plt.title(f'PSD off_{o}')
    plt.xlabel('Hz'); plt.ylabel('PSD')
    plt.xlim(0, fs_actual/2)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTDIR, f'psd_off_{o}.png'))

print('\nBand power results (absolute and % of total)')
for o in offsets:
    print(f'offset {o}: mean={results[o]["mean"]:.3f} std={results[o]["std"]:.3f}')
    for b in ['delta','theta','alpha','beta','gamma','smr']:
        print(f'  {b}: {results[o]["band_power"][b]:.3e} ({results[o]["band_pct"][b]:.2f}%)')

out_json = os.path.join(OUTDIR, 'band_results.json')
with open(out_json,'w') as fh: json.dump(results, fh, indent=2)
print('\nSaved band power JSON to', out_json)
