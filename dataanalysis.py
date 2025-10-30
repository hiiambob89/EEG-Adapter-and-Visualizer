import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt
from tkinter import Tk, filedialog

# -----------------------------
# Configuration
# -----------------------------
MINUTES_PER_PERIOD = 1  # How many minutes in each analysis period
FS_FALLBACK = 83.33     # Fallback sampling rate if detection fails

# -----------------------------
# Helper: Bandpass filter
# -----------------------------
def bandpass(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    if nyq <= 0:
        raise ValueError("Sampling rate must be positive for bandpass filter")

    low = max(lowcut, 0.1) / nyq
    high_freq = min(highcut, nyq * 0.99)
    if high_freq <= lowcut:
        high_freq = min(lowcut * 1.25, nyq * 0.99)
    high = high_freq / nyq

    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data)

# -----------------------------
# Load CSV
# -----------------------------
Tk().withdraw()
csv_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
if not csv_path:
    raise SystemExit("No CSV selected")

df = pd.read_csv(csv_path)
df = df.replace(r'^\s*$', np.nan, regex=True)

time_col = None
for candidate in ['Practice Timestamp (ms)', 'timestamp_ms', 'timestamp', 'Time (s)', 'Time (min)']:
    if candidate in df.columns:
        time_col = candidate
        break

if time_col is None:
    raise SystemExit("No timestamp column found in CSV")

time_numeric = pd.to_numeric(df[time_col], errors='coerce')

if 'min' in time_col.lower():
    df['Time (min)'] = time_numeric
    df['Time (s)'] = time_numeric * 60.0
elif 'ms' in time_col.lower():
    df['Time (s)'] = time_numeric / 1000.0
    df['Time (min)'] = df['Time (s)'] / 60.0
else:
    df['Time (s)'] = time_numeric
    df['Time (min)'] = df['Time (s)'] / 60.0

df = df.sort_values('Time (s)').reset_index(drop=True)

time_diffs = df['Time (s)'].diff().dropna()
time_diffs = time_diffs[time_diffs > 0]
if not time_diffs.empty:
    fs_estimate = 1.0 / time_diffs.median()
else:
    fs_estimate = FS_FALLBACK

print(f"Estimated sampling rate: {fs_estimate:.2f} Hz")

bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma', 'SMR']
fs = fs_estimate

# -----------------------------
# Apply filter
# -----------------------------
filtered_df = df.copy()
for band in bands:
    col = f'{band} Brainwave Voltage(µV)'
    # Typical EEG band ranges in Hz
    ranges = {
        'Delta': (0.5, 4),
        'Theta': (4, 8),
        'Alpha': (8, 12),
        'Beta': (12, 30),
        'Gamma': (30, 45),
        'SMR': (12, 15)
    }
    low, high = ranges[band]
    series = pd.to_numeric(df[col], errors='coerce')
    filled = series.interpolate(limit_direction='both')
    if filled.isna().all():
        filtered_df[col] = series
        continue
    filtered_values = bandpass(filled.values, low, high, fs)
    filtered_values = np.where(series.isna(), np.nan, filtered_values)
    filtered_df[col] = filtered_values

# -----------------------------
# Compute absolute values
# -----------------------------
for df_use in [df, filtered_df]:
    for band in bands:
        vals = pd.to_numeric(df_use[f'{band} Brainwave Voltage(µV)'], errors='coerce')
        df_use[f'{band}_abs'] = vals.abs()

# -----------------------------
# Period analysis
# -----------------------------
total_time = df['Time (min)'].max()
period_duration = MINUTES_PER_PERIOD
num_periods = int(np.ceil(total_time / period_duration))

def analyze(df_use, label="Raw"):
    print(f"\n\n===== {label} DATA ANALYSIS =====")
    period_data = []
    for i in range(num_periods):
        start = i * period_duration
        end = (i + 1) * period_duration
        period_df = df_use[(df_use['Time (min)'] >= start) & (df_use['Time (min)'] < end)]
        print(f"\nPeriod {i+1}: {start:.1f}-{end:.1f} min ({len(period_df)} samples)")
        stats = {}
        for band in bands:
            vals = pd.to_numeric(period_df[f'{band}_abs'], errors='coerce')
            if vals.dropna().empty:
                stats[band] = np.nan
                print(f"  {band:6}: insufficient data")
                continue
            mean_val = np.nanmean(vals)
            std_val = np.nanstd(vals)
            max_val = np.nanmax(vals)
            stats[band] = mean_val
            print(f"  {band:6}: Mean={mean_val:.3f} µV  Std={std_val:.3f}  Max={max_val:.3f}")
        # Ratios
        epsilon = 1e-10
        theta_vals = pd.to_numeric(period_df['Theta_abs'], errors='coerce')
        beta_vals = pd.to_numeric(period_df['Beta_abs'], errors='coerce')
        delta_vals = pd.to_numeric(period_df['Delta_abs'], errors='coerce')
        alpha_vals = pd.to_numeric(period_df['Alpha_abs'], errors='coerce')

        theta_beta = np.nanmean(theta_vals / (beta_vals + epsilon)) if not theta_vals.dropna().empty else np.nan
        delta_alpha = np.nanmean(delta_vals / (alpha_vals + epsilon)) if not delta_vals.dropna().empty else np.nan
        stats['theta_beta'] = theta_beta
        stats['delta_alpha'] = delta_alpha
        print(f"  Theta/Beta ratio: {theta_beta:.3f}" if not np.isnan(theta_beta) else "  Theta/Beta ratio: n/a")
        print(f"  Delta/Alpha ratio: {delta_alpha:.3f}" if not np.isnan(delta_alpha) else "  Delta/Alpha ratio: n/a")
        period_data.append(stats)
    return period_data

raw_stats = analyze(df, label="Raw")
filtered_stats = analyze(filtered_df, label="Filtered")

# -----------------------------
# Plotting
# -----------------------------
# Define consistent colors for each band
band_colors = {
    'Delta': '#1f77b4',   # Blue
    'Theta': '#ff7f0e',   # Orange
    'Alpha': '#2ca02c',   # Green
    'Beta': '#d62728',    # Red
    'Gamma': '#9467bd',   # Purple
    'SMR': '#8c564b'      # Brown
}

def plot_bands(df_use, title="EEG Bands", normalize=True):
    plt.figure(figsize=(12,6))
    for band in bands:
        y = df_use[f'{band}_abs'].values
        if normalize:
            y = y / (np.max(y)+1e-10)
        plt.plot(df_use['Time (min)'], y, label=band, color=band_colors[band])
    plt.xlabel("Time (min)")
    plt.ylabel("Normalized Amplitude" if normalize else "µV")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.show()

plot_bands(df, title="Raw EEG Bands (Normalized)")
plot_bands(filtered_df, title="Filtered EEG Bands (Normalized)")

# -----------------------------
# Separate Raw and Filtered plots with consistent coloring
# -----------------------------
def plot_raw_separate(df_raw, normalize=True):
    """Plot raw data only"""
    plt.figure(figsize=(14,6))
    
    for band in bands:
        raw = pd.to_numeric(df_raw[f'{band}_abs'], errors='coerce').interpolate(limit_direction='both').fillna(0).values
        if normalize:
            raw = raw / (np.max(raw)+1e-10)
        
        # Compute mean and std over small rolling window for smoothness
        window = 50
        raw_mean = pd.Series(raw).rolling(window, min_periods=1).mean()
        raw_std  = pd.Series(raw).rolling(window, min_periods=1).std()
        
        t = df_raw['Time (min)']
        
        # Raw line + envelope with consistent color
        plt.plot(t, raw_mean, label=f"{band}", linestyle='-', color=band_colors[band])
        plt.fill_between(t, raw_mean-raw_std, raw_mean+raw_std, alpha=0.2, color=band_colors[band])
    
    plt.xlabel("Time (min)")
    plt.ylabel("Normalized Amplitude" if normalize else "µV")
    plt.title("Raw EEG Bands (with Rolling Mean & Std)")
    plt.legend()
    plt.grid(True)
    plt.show()

def plot_filtered_separate(df_filt, normalize=True):
    """Plot filtered data only"""
    plt.figure(figsize=(14,6))
    
    for band in bands:
        filt = pd.to_numeric(df_filt[f'{band}_abs'], errors='coerce').interpolate(limit_direction='both').fillna(0).values
        if normalize:
            filt = filt / (np.max(filt)+1e-10)
        
        # Compute mean and std over small rolling window for smoothness
        window = 50
        filt_mean = pd.Series(filt).rolling(window, min_periods=1).mean()
        filt_std  = pd.Series(filt).rolling(window, min_periods=1).std()
        
        t = df_filt['Time (min)']
        
        # Filtered line + envelope with consistent color
        plt.plot(t, filt_mean, label=f"{band}", linestyle='-', color=band_colors[band])
        plt.fill_between(t, filt_mean-filt_std, filt_mean+filt_std, alpha=0.2, color=band_colors[band])
    
    plt.xlabel("Time (min)")
    plt.ylabel("Normalized Amplitude" if normalize else "µV")
    plt.title("Filtered EEG Bands (with Rolling Mean & Std)")
    plt.legend()
    plt.grid(True)
    plt.show()

# -----------------------------
# Overlay raw vs filtered plot
# -----------------------------
def plot_raw_vs_filtered(df_raw, df_filt, normalize=True):
    plt.figure(figsize=(14,7))
    
    for band in bands:
        raw = pd.to_numeric(df_raw[f'{band}_abs'], errors='coerce').interpolate(limit_direction='both').fillna(0).values
        filt = pd.to_numeric(df_filt[f'{band}_abs'], errors='coerce').interpolate(limit_direction='both').fillna(0).values
        if normalize:
            raw = raw / (np.max(raw)+1e-10)
            filt = filt / (np.max(filt)+1e-10)
        
        # Compute mean and std over small rolling window for smoothness
        window = 50
        raw_mean = pd.Series(raw).rolling(window, min_periods=1).mean()
        raw_std  = pd.Series(raw).rolling(window, min_periods=1).std()
        filt_mean = pd.Series(filt).rolling(window, min_periods=1).mean()
        filt_std  = pd.Series(filt).rolling(window, min_periods=1).std()
        
        t = df_raw['Time (min)']
        
        # Raw line + envelope with consistent color
        plt.plot(t, raw_mean, label=f"{band} Raw", linestyle='-', color=band_colors[band], alpha=0.7)
        plt.fill_between(t, raw_mean-raw_std, raw_mean+raw_std, alpha=0.15, color=band_colors[band])
        
        # Filtered line + envelope with consistent color (dashed)
        plt.plot(t, filt_mean, label=f"{band} Filtered", linestyle='--', color=band_colors[band])
        plt.fill_between(t, filt_mean-filt_std, filt_mean+filt_std, alpha=0.15, color=band_colors[band])
    
    plt.xlabel("Time (min)")
    plt.ylabel("Normalized Amplitude" if normalize else "µV")
    plt.title("Raw vs Filtered EEG Bands")
    plt.legend()
    plt.grid(True)
    plt.show()

# Call all plotting functions
plot_raw_separate(df)
plot_filtered_separate(filtered_df)
plot_raw_vs_filtered(df, filtered_df)

