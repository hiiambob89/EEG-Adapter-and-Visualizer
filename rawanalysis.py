

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, hilbert, welch, coherence
from scipy.stats import zscore
from tqdm import tqdm
from tkinter import Tk, filedialog

# Custom JSON encoder to handle NumPy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyEncoder, self).default(obj)

# -----------------------------
# Configuration
# -----------------------------
# Will be calculated from data, but default fallback
FS_DEFAULT = 83.33           # Default sampling rate if calculation fails
EPOCH_SECONDS = 5          # Epoch length for PAC/PLV/coherence
OVERLAP_SECONDS = 1        # Overlap between epochs
GAMMA_BAND = (30, 80)      # Gamma range (conservative for 3-channel device)
GAMMA_Z_THRESH = 3.0       # Z-score threshold for gamma bursts
GAMMA_MIN_MS = 50          # Minimum burst duration
PAC_LOW_BANDS = {
    'Theta': (4, 8),
    'Alpha': (8, 13)       # Extended to 13 Hz for standard alpha
}
PAC_HIGH_BAND = (30, 70)   # Gamma band for PAC
PLV_FREQ_BAND = (8, 13)    # Alpha band for PLV
MIN_CHANNELS_FOR_MULTI = 2

PLOT = True

# -----------------------------
# Helper functions
# -----------------------------
def bandpass(data, lowcut, highcut, fs, order=4):
    if lowcut <= 0:
        lowcut = 0.1
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    if high >= 1.0:
        high = 0.999
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data)

def envelope(signal):
    return np.abs(hilbert(signal))

def sliding_epochs(length_s, overlap_s, fs, total_samples):
    step = int((length_s - overlap_s) * fs)
    window = int(length_s * fs)
    idx = []
    i = 0
    while i + window <= total_samples:
        idx.append((i, i + window))
        i += step
    if i < total_samples and (total_samples - i) > int(0.2 * window):
        idx.append((i, total_samples))
    return idx

def detect_gamma_bursts(raw_signal, fs, low=GAMMA_BAND[0], high=GAMMA_BAND[1],
                        z_thresh=GAMMA_Z_THRESH, min_duration_ms=GAMMA_MIN_MS):
    """Detect gamma bursts using envelope z-score method"""
    g = bandpass(raw_signal, low, high, fs, order=4)
    g_env = envelope(g)
    g_z = (g_env - np.nanmean(g_env)) / (np.nanstd(g_env) + 1e-12)
    above = g_z > z_thresh
    bursts = []
    if np.any(above):
        idx = np.where(above)[0]
        starts = [idx[0]]
        ends = []
        for k in range(1, len(idx)):
            if idx[k] != idx[k-1] + 1:
                ends.append(idx[k-1])
                starts.append(idx[k])
        ends.append(idx[-1])
        for s, e in zip(starts, ends):
            duration_ms = (e - s + 1) / fs * 1000.0
            if duration_ms >= min_duration_ms:
                peak_z = np.max(g_z[s:e+1])
                bursts.append({
                    'start': s, 
                    'end': e, 
                    'peak_z': float(peak_z), 
                    'duration_ms': float(duration_ms)
                })
    return bursts, g_env, g_z

def modulation_index_tort(phase_signal, amp_envelope, n_bins=18):
    """Tort et al. (2008) Modulation Index for PAC"""
    bins = np.linspace(-np.pi, np.pi, n_bins+1)
    inds = np.digitize(phase_signal, bins) - 1
    amp_binned = np.zeros(n_bins, dtype=float)
    for i in range(n_bins):
        mask = inds == i
        if np.any(mask):
            amp_binned[i] = np.mean(amp_envelope[mask])
        else:
            amp_binned[i] = 0.0
    amp_binned = amp_binned + 1e-12
    p = amp_binned / np.sum(amp_binned)
    H = -np.sum(p * np.log(p))
    H_max = np.log(n_bins)
    MI = (H_max - H) / H_max
    return MI, p

def compute_plv(phases1, phases2):
    """Compute Phase Locking Value between two phase arrays"""
    complex_phase_diff = np.exp(1j * (phases1 - phases2))
    return np.abs(np.mean(complex_phase_diff))

# -----------------------------
# Load CSV file
# -----------------------------
Tk().withdraw()
csv_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
if not csv_path:
    raise SystemExit("No CSV selected")

print(f"Loading {csv_path}...")
df = pd.read_csv(csv_path)

# -----------------------------
# CRITICAL: Detect and calculate actual sampling rate
# -----------------------------
print("\n=== DETECTING SAMPLING RATE ===")

# Find timestamp column
timestamp_col = None
for col in df.columns:
    if 'timestamp' in col.lower():
        timestamp_col = col
        break

if timestamp_col:
    # Convert to seconds
    timestamps = pd.to_numeric(df[timestamp_col], errors='coerce')
    if 'ms' in timestamp_col.lower():
        df['Time (s)'] = timestamps / 1000.0
    else:
        df['Time (s)'] = timestamps
    
    # Calculate actual sampling rate from timestamps
    time_diffs = df['Time (s)'].diff().dropna()
    median_diff = time_diffs.median()
    calculated_fs = 1.0 / median_diff if median_diff > 0 else FS_DEFAULT
    
    print(f"Timestamp column: {timestamp_col}")
    print(f"Median time between samples: {median_diff*1000:.2f} ms")
    print(f"Calculated sampling rate: {calculated_fs:.2f} Hz")
    
    # Sanity check
    if 200 < calculated_fs < 300:
        FS = calculated_fs
        print(f"✓ Using calculated FS = {FS:.2f} Hz")
    else:
        FS = FS_DEFAULT
        print(f"⚠ Calculated FS seems wrong, using default FS = {FS} Hz")
else:
    # Fallback: assume uniform sampling
    FS = FS_DEFAULT
    df['Time (s)'] = np.arange(len(df)) / FS
    print(f"⚠ No timestamp column found, assuming FS = {FS} Hz")

df['Time (min)'] = df['Time (s)'] / 60.0
total_samples = len(df)
total_time_s = df['Time (s)'].max() - df['Time (s)'].min()

print(f"\n=== DATA SUMMARY ===")
print(f"Total samples: {total_samples}")
print(f"Duration: {total_time_s:.1f} seconds ({total_time_s/60:.1f} minutes)")
print(f"Sampling rate: {FS:.2f} Hz")
print(f"Nyquist frequency: {FS/2:.2f} Hz")

# -----------------------------
# Identify channel columns
# -----------------------------
print("\n=== DETECTING CHANNELS ===")
channel_cols = []
for col in df.columns:
    col_lower = col.lower()
    if ('channel' in col_lower or 'ch' in col_lower) and 'µv' in col_lower:
        channel_cols.append(col)

if len(channel_cols) == 0:
    # Fallback: look for numeric columns that aren't timestamps
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) and 'time' not in col.lower():
            channel_cols.append(col)

channels = channel_cols
print(f"Detected channels: {channels}")
print(f"Number of channels: {len(channels)}")

if len(channels) == 0:
    raise SystemExit("ERROR: No channel columns detected!")

# -----------------------------
# Prepare channel data
# -----------------------------
print("\n=== PREPARING CHANNEL DATA ===")
channel_data = {}
for ch in channels:
    raw = pd.to_numeric(df[ch], errors='coerce').fillna(0).values
    channel_data[ch] = raw
    
    # Diagnostics
    non_zero = np.sum(raw != 0)
    mean_val = np.nanmean(raw)
    std_val = np.nanstd(raw)
    print(f"{ch}:")
    print(f"  Non-zero samples: {non_zero}/{len(raw)} ({100*non_zero/len(raw):.1f}%)")
    print(f"  Mean: {mean_val:.2f} µV")
    print(f"  Std: {std_val:.2f} µV")
    print(f"  Range: [{np.nanmin(raw):.2f}, {np.nanmax(raw):.2f}] µV")

# -----------------------------
# Create band envelope columns for all channels
# -----------------------------
print("\n=== COMPUTING BAND ENVELOPES ===")
for ch in channels:
    ch_data = channel_data[ch]
    for band, (low, high) in {
        'Delta': (0.5, 4),
        'Theta': (4, 8),
        'Alpha': (8, 13),
        'Beta': (13, 30),
        'Gamma': (30, 80),
        'SMR': (12, 15)
    }.items():
        colname = f"{ch}__{band}_env"
        try:
            filt = bandpass(ch_data, low, high, FS, order=4)
            env = envelope(filt)
            df[colname] = env
        except Exception as e:
            print(f"  Warning: Failed to compute {colname}: {e}")
            df[colname] = np.zeros(len(ch_data))

# -----------------------------
# Epoching
# -----------------------------
epoch_windows = sliding_epochs(EPOCH_SECONDS, OVERLAP_SECONDS, FS, total_samples)
print(f"\n=== EPOCHING ===")
print(f"Created {len(epoch_windows)} epochs of {EPOCH_SECONDS}s (overlap {OVERLAP_SECONDS}s)")

# -----------------------------
# Per-epoch analysis: PAC, gamma bursts
# -----------------------------
print("\n=== ANALYZING EPOCHS ===")
results = {
    'epochs': [],
    'gamma_bursts': [],
    'plv': {},
    'coherence': {},
    'metadata': {
        'sampling_rate_hz': float(FS),
        'duration_s': float(total_time_s),
        'num_channels': len(channels),
        'channel_names': channels
    }
}

for ei, (start, end) in enumerate(tqdm(epoch_windows, desc="Processing epochs")):
    epoch_report = {
        'epoch_idx': ei,
        'start_sample': int(start),
        'end_sample': int(end),
        'start_time_s': float(start / FS),
        'end_time_s': float(end / FS),
    }
    
    # Use first channel for PAC/gamma analysis
    if len(channels) >= 1:
        ref = channel_data[channels[0]][start:end]
        
        # Gamma burst detection
        bursts, g_env, g_z = detect_gamma_bursts(
            ref, FS, 
            low=GAMMA_BAND[0], 
            high=GAMMA_BAND[1],
            z_thresh=GAMMA_Z_THRESH, 
            min_duration_ms=GAMMA_MIN_MS
        )
        epoch_report['gamma_burst_count'] = len(bursts)
        
        # PAC analysis
        pac_results = {}
        for low_name, (low_f1, low_f2) in PAC_LOW_BANDS.items():
            try:
                low_filtered = bandpass(ref, low_f1, low_f2, FS, order=4)
                low_phase = np.angle(hilbert(low_filtered))
                high_filtered = bandpass(ref, PAC_HIGH_BAND[0], PAC_HIGH_BAND[1], FS, order=4)
                high_env = envelope(high_filtered)
                MI, dist = modulation_index_tort(low_phase, high_env, n_bins=18)
                pac_results[low_name] = float(MI)
            except Exception as e:
                print(f"  Warning: PAC failed for {low_name} in epoch {ei}: {e}")
                pac_results[low_name] = 0.0
        
        epoch_report['pac'] = pac_results
    
    results['epochs'].append(epoch_report)

# -----------------------------
# Whole-session gamma burst detection
# -----------------------------
print("\n=== DETECTING GAMMA BURSTS (FULL SESSION) ===")
for ch in channels:
    bursts, g_env, g_z = detect_gamma_bursts(
        channel_data[ch], FS,
        low=GAMMA_BAND[0], 
        high=GAMMA_BAND[1],
        z_thresh=GAMMA_Z_THRESH, 
        min_duration_ms=GAMMA_MIN_MS
    )
    print(f"{ch}: {len(bursts)} gamma bursts detected")
    results['gamma_bursts'].append({'channel': ch, 'bursts': bursts})

# -----------------------------
# Multi-channel analysis: PLV and coherence
# -----------------------------
if len(channels) >= MIN_CHANNELS_FOR_MULTI:
    print("\n=== COMPUTING PLV AND COHERENCE ===")
    import itertools
    pairs = list(itertools.combinations(channels, 2))
    plv_results = {f"{a}__{b}": [] for a, b in pairs}
    coh_results = {f"{a}__{b}": [] for a, b in pairs}
    
    for (start, end) in tqdm(epoch_windows, desc="Multi-channel metrics"):
        for a, b in pairs:
            sig_a = channel_data[a][start:end]
            sig_b = channel_data[b][start:end]
            
            try:
                # PLV in alpha band
                a_band = bandpass(sig_a, PLV_FREQ_BAND[0], PLV_FREQ_BAND[1], FS, order=4)
                b_band = bandpass(sig_b, PLV_FREQ_BAND[0], PLV_FREQ_BAND[1], FS, order=4)
                a_phase = np.angle(hilbert(a_band))
                b_phase = np.angle(hilbert(b_band))
                plv_val = compute_plv(a_phase, b_phase)
                plv_results[f"{a}__{b}"].append(float(plv_val))
                
                # Coherence
                f_coh, Cxy = coherence(sig_a, sig_b, fs=FS, nperseg=min(256, len(sig_a)))
                band_mask = (f_coh >= PLV_FREQ_BAND[0]) & (f_coh <= PLV_FREQ_BAND[1])
                if np.any(band_mask):
                    mean_coh = float(np.nanmean(Cxy[band_mask]))
                else:
                    mean_coh = float(np.nanmean(Cxy))
                coh_results[f"{a}__{b}"].append(mean_coh)
            except Exception as e:
                print(f"  Warning: Failed PLV/coherence for {a}-{b}: {e}")
                plv_results[f"{a}__{b}"].append(0.0)
                coh_results[f"{a}__{b}"].append(0.0)
    
    results['plv'] = plv_results
    results['coherence'] = coh_results
    
    # Print summary
    print("\nPLV Summary (mean across epochs):")
    for pair, values in plv_results.items():
        print(f"  {pair}: {np.mean(values):.3f}")

# -----------------------------
# Per-minute analysis
# -----------------------------
print("\n=== PER-MINUTE BAND POWER ANALYSIS ===")
MINUTES_PER_PERIOD = 1
num_periods = int(np.ceil(df['Time (min)'].max() / MINUTES_PER_PERIOD))

period_data = []
for i in range(num_periods):
    start_min = i * MINUTES_PER_PERIOD
    end_min = (i + 1) * MINUTES_PER_PERIOD
    period_df = df[(df['Time (min)'] >= start_min) & (df['Time (min)'] < end_min)]
    
    print(f"\nPeriod {i+1}: {start_min:.1f}-{end_min:.1f} min ({len(period_df)} samples)")
    
    stats = {}
    for band in ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma', 'SMR']:
        env_cols = [c for c in df.columns if c.endswith(f"__{band}_env")]
        if len(env_cols) > 0:
            # Average across all channels
            vals = np.mean([period_df[c].values for c in env_cols], axis=0)
        else:
            vals = np.zeros(len(period_df))
        
        mean_val = np.nanmean(vals) if len(vals) > 0 else 0.0
        std_val = np.nanstd(vals) if len(vals) > 0 else 0.0
        max_val = np.nanmax(vals) if len(vals) > 0 else 0.0
        stats[band] = float(mean_val)
        print(f"  {band:6s}: Mean={mean_val:.4f} µV  Std={std_val:.4f}  Max={max_val:.4f}")
    
    # Ratios
    theta_beta = stats['Theta'] / (stats['Beta'] + 1e-10)
    delta_alpha = stats['Delta'] / (stats['Alpha'] + 1e-10)
    stats['theta_beta_ratio'] = float(theta_beta)
    stats['delta_alpha_ratio'] = float(delta_alpha)
    print(f"  Theta/Beta ratio: {theta_beta:.6f}")
    print(f"  Delta/Alpha ratio: {delta_alpha:.6f}")
    
    period_data.append(stats)

results['period_analysis'] = period_data

# -----------------------------
# Save results
# -----------------------------
out_base = os.path.splitext(os.path.basename(csv_path))[0]
out_dir = os.path.join(os.path.dirname(csv_path), f"{out_base}_analysis")
os.makedirs(out_dir, exist_ok=True)

print(f"\n=== SAVING RESULTS ===")
print(f"Output directory: {out_dir}")

# Save JSON
json_path = os.path.join(out_dir, "analysis_results.json")
with open(json_path, "w") as f:
    json.dump(results, f, indent=2, cls=NumpyEncoder)
print(f"✓ Saved: {json_path}")

# Save epoch summary CSV
epoch_summary = []
for e in results['epochs']:
    rec = {
        'epoch_idx': e.get('epoch_idx'),
        'start_time_s': e.get('start_time_s'),
        'end_time_s': e.get('end_time_s'),
        'gamma_burst_count': e.get('gamma_burst_count', 0),
    }
    pac = e.get('pac', {})
    for k, v in pac.items():
        rec[f'pac_{k}'] = v
    epoch_summary.append(rec)

epoch_csv_path = os.path.join(out_dir, "epoch_summary.csv")
pd.DataFrame(epoch_summary).to_csv(epoch_csv_path, index=False)
print(f"✓ Saved: {epoch_csv_path}")

# -----------------------------
# Plotting
# -----------------------------
if PLOT and len(channels) >= 1:
    print("\n=== GENERATING PLOTS ===")
    
    # 1) Gamma envelope with bursts
    ch0 = channels[0]
    sig = channel_data[ch0]
    g_filt = bandpass(sig, GAMMA_BAND[0], GAMMA_BAND[1], FS, order=4)
    g_env = envelope(g_filt)
    t = df['Time (s)'].values
    
    plt.figure(figsize=(14, 5))
    plt.plot(t, g_env, label=f'{ch0} gamma envelope', linewidth=0.5)
    gz = (g_env - np.nanmean(g_env)) / (np.nanstd(g_env) + 1e-12)
    mask = gz > GAMMA_Z_THRESH
    plt.fill_between(t, 0, np.max(g_env)*1.1, where=mask, color='red', alpha=0.3, label='gamma burst')
    plt.xlabel('Time (s)')
    plt.ylabel('Gamma envelope (µV)')
    plt.title(f'Gamma Envelope with Detected Bursts - {ch0}')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plot1_path = os.path.join(out_dir, "gamma_bursts.png")
    plt.savefig(plot1_path, dpi=150)
    print(f"✓ Saved: {plot1_path}")
    plt.close()
    
    # 2) PAC heatmap
    pac_df = pd.DataFrame(epoch_summary)
    if 'pac_Theta' in pac_df.columns or 'pac_Alpha' in pac_df.columns:
        plt.figure(figsize=(10, 5))
        pac_to_plot = []
        labels = []
        for low in PAC_LOW_BANDS.keys():
            col = f'pac_{low}'
            if col in pac_df.columns:
                pac_to_plot.append(pac_df[col].values)
                labels.append(low)
        
        if len(pac_to_plot) > 0:
            pac_mat = np.vstack(pac_to_plot)
            plt.imshow(pac_mat, aspect='auto', interpolation='nearest', cmap='viridis')
            plt.colorbar(label='Modulation Index (MI)')
            plt.yticks(np.arange(len(labels)), labels)
            plt.xlabel('Epoch index')
            plt.ylabel('Low-frequency band')
            plt.title('Phase-Amplitude Coupling (PAC): Low-Freq Phase → Gamma Amplitude')
            plt.tight_layout()
            plot2_path = os.path.join(out_dir, "pac_heatmap.png")
            plt.savefig(plot2_path, dpi=150)
            print(f"✓ Saved: {plot2_path}")
            plt.close()
    
    # 3) PLV bar chart
    if results.get('plv'):
        pairs = list(results['plv'].keys())
        means = [np.mean(results['plv'][p]) for p in pairs]
        
        plt.figure(figsize=(10, 5))
        plt.bar(pairs, means, color='steelblue', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Phase Locking Value (PLV)')
        plt.title('Inter-Channel Phase Locking (Alpha Band, Mean Across Epochs)')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plot3_path = os.path.join(out_dir, "plv_summary.png")
        plt.savefig(plot3_path, dpi=150)
        print(f"✓ Saved: {plot3_path}")
        plt.close()
    
    # 4) Coherence bar chart
    if results.get('coherence'):
        pairs = list(results['coherence'].keys())
        means = [np.mean(results['coherence'][p]) for p in pairs]
        
        plt.figure(figsize=(10, 5))
        plt.bar(pairs, means, color='coral', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.ylabel('Coherence')
        plt.title('Inter-Channel Coherence (Alpha Band, Mean Across Epochs)')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        plot4_path = os.path.join(out_dir, "coherence_summary.png")
        plt.savefig(plot4_path, dpi=150)
        print(f"✓ Saved: {plot4_path}")
        plt.close()

print("\n✓ ANALYSIS COMPLETE!")
print(f"\nResults saved to: {out_dir}")