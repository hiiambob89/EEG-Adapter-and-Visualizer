#!/usr/bin/env python3
"""Plot the CSV produced by analyze_frames.js (top_int16_samples.csv).

Saves PNG(s) to tools/plots/ and prints basic stats.

Run: python tools/plot_top_int16.py
"""
import os
import csv
import math
from statistics import mean, stdev
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = os.path.dirname(__file__)
CSV = os.path.join(ROOT, 'top_int16_samples.csv')
OUTDIR = os.path.join(ROOT, 'plots')
os.makedirs(OUTDIR, exist_ok=True)

if not os.path.exists(CSV):
    print('Missing', CSV, '- run tools/analyze_frames.js first')
    raise SystemExit(2)

# Read CSV headers
with open(CSV, 'r', newline='') as fh:
    reader = csv.reader(fh)
    hdr = next(reader)
    rows = list(reader)

print('CSV columns:', hdr)
print('Frames in CSV:', len(rows))

# columns: frame_index, bytes, off_X ...
ch_names = hdr[2:]
channels = {name: [] for name in ch_names}
frames = []

for r in rows:
    frames.append(int(r[0]))
    for i, name in enumerate(ch_names, start=2):
        val = r[i]
        channels[name].append(int(val) if val != '' else None)

# Trim channels to contiguous data (drop trailing Nones)
for name, vals in channels.items():
    # convert None to nan for plotting
    channels[name] = [float(v) if v is not None else float('nan') for v in vals]

# Choose a window to plot: full length may be large; use first 1000 samples or full
MAX_PTS = 1000
n = min(len(rows), MAX_PTS)
xs = list(range(n))

plt.figure(figsize=(12, 6))
for name in ch_names:
    plt.plot(xs, channels[name][:n], label=name)
plt.xlabel('frame index')
plt.ylabel('raw int16 value')
plt.title('Top int16 offsets (first %d frames)' % n)
plt.legend(loc='upper right', fontsize='small')
out_png = os.path.join(OUTDIR, 'top_int16_first_%d.png' % n)
plt.tight_layout()
plt.savefig(out_png)
print('Wrote plot to', out_png)

# Also produce per-channel basic stats (mean/std) on full data
stats_path = os.path.join(OUTDIR, 'top_int16_stats.txt')
with open(stats_path, 'w') as fh:
    for name in ch_names:
        vals = [v for v in channels[name] if not math.isnan(v)]
        if len(vals) == 0:
            fh.write(f"{name}: no data\n")
            continue
        m = mean(vals)
        s = stdev(vals) if len(vals) > 1 else 0.0
        fh.write(f"{name}: n={len(vals)}, mean={m:.3f}, std={s:.3f}\n")
        print(f"{name}: n={len(vals)}, mean={m:.3f}, std={s:.3f}")

print('Wrote stats to', stats_path)
