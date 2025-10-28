import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
from tkinter import Tk, filedialog

# -----------------------------
# Configuration
# -----------------------------
MINUTES_PER_PERIOD = 1  # How many minutes in each analysis period

# -----------------------------
# Helper: Bandpass filter
# -----------------------------
def bandpass(data, lowcut, highcut, fs, order=4):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
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
df['Practice Timestamp (ms)'] = pd.to_numeric(df['Practice Timestamp (ms)'], errors='coerce')
df = df.fillna(0)
df['Time (min)'] = df['Practice Timestamp (ms)'] / 60000

bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma', 'SMR']
fs = 234  # Verified sampling rate

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
    filtered_df[col] = bandpass(df[col].values, low, high, fs)

# -----------------------------
# Compute absolute values
# -----------------------------
for df_use in [df, filtered_df]:
    for band in bands:
        df_use[f'{band}_abs'] = df_use[f'{band} Brainwave Voltage(µV)'].abs()

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
            vals = period_df[f'{band}_abs'].values
            mean_val = np.mean(vals)
            std_val = np.std(vals)
            max_val = np.max(vals)
            stats[band] = mean_val
            print(f"  {band:6}: Mean={mean_val:.3f} µV  Std={std_val:.3f}  Max={max_val:.3f}")
        # Ratios
        epsilon = 1e-10
        theta_beta = np.mean(period_df['Theta_abs'] / (period_df['Beta_abs'] + epsilon))
        delta_alpha = np.mean(period_df['Delta_abs'] / (period_df['Alpha_abs'] + epsilon))
        stats['theta_beta'] = theta_beta
        stats['delta_alpha'] = delta_alpha
        print(f"  Theta/Beta ratio: {theta_beta:.3f}")
        print(f"  Delta/Alpha ratio: {delta_alpha:.3f}")
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
        raw = df_raw[f'{band}_abs'].values
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
        filt = df_filt[f'{band}_abs'].values
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
        raw = df_raw[f'{band}_abs'].values
        filt = df_filt[f'{band}_abs'].values
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

