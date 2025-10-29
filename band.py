import pandas as pd
import numpy as np
import json

# -----------------------------
# CONFIGURATION
# -----------------------------
CSV_PATH = "C:\\Users\\kaden\\Downloads\\finalfinal.csv"  # replace with your CSV path
WINDOW_SEC = 10             # period length for summarizing (seconds)
FS = 83.33                      # sampling rate in Hz

# -----------------------------
# LOAD CSV
# -----------------------------
df = pd.read_csv(CSV_PATH).fillna(0)

# Ensure time column in seconds
df['Time_s'] = df['Practice Timestamp (ms)'] / 1000.0

# Detect CSV type
is_powers_csv = 'Delta Power (µV²)' in df.columns
is_filtered_csv = 'Delta Brainwave Voltage(µV)' in df.columns

if is_powers_csv:
    print("📊 Detected: Band Powers CSV (spectral analysis)")
    BANDS = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
    band_suffix = ' Power (µV²)'
    percent_suffix = ' %'
elif is_filtered_csv:
    print("📊 Detected: Filtered Voltages CSV (time-domain)")
    BANDS = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma', 'SMR']
    band_suffix = ' Brainwave Voltage(µV)'
    percent_suffix = None
else:
    print("❌ Unknown CSV format!")
    exit(1)

# -----------------------------
# SPLIT INTO PERIODS
# -----------------------------
window_samples = int(WINDOW_SEC * FS)
num_periods = int(np.ceil(len(df) / window_samples))

summary = []

for i in range(num_periods):
    start = i * window_samples
    end = min((i + 1) * window_samples, len(df))
    period_df = df.iloc[start:end]

    stats = {
        'Period': i,
        'Start_s': float(period_df['Time_s'].iloc[0]),
        'End_s': float(period_df['Time_s'].iloc[-1])
    }

    # Process band data
    for band in BANDS:
        col = f"{band}{band_suffix}"
        if col in period_df.columns:
            vals = period_df[col].values
            stats[f'{band}_mean'] = float(np.mean(vals))
            stats[f'{band}_std']  = float(np.std(vals))
            stats[f'{band}_max']  = float(np.max(vals))
        else:
            stats[f'{band}_mean'] = stats[f'{band}_std'] = stats[f'{band}_max'] = 0.0
    
    # Add percentages if powers CSV
    if is_powers_csv and percent_suffix:
        for band in BANDS:
            col = f"{band}{percent_suffix}"
            if col in period_df.columns:
                vals = period_df[col].values
                stats[f'{band}_percent_mean'] = float(np.mean(vals))
            else:
                stats[f'{band}_percent_mean'] = 0.0
    
    # Add relaxation/focus scores if powers CSV
    if is_powers_csv:
        if 'Relaxation Score' in period_df.columns:
            stats['Relaxation_mean'] = float(np.mean(period_df['Relaxation Score'].values))
            stats['Relaxation_std'] = float(np.std(period_df['Relaxation Score'].values))
        if 'Focus Score' in period_df.columns:
            stats['Focus_mean'] = float(np.mean(period_df['Focus Score'].values))
            stats['Focus_std'] = float(np.std(period_df['Focus Score'].values))

    summary.append(stats)

# -----------------------------
# PRINT PASTE-READY JSON
# -----------------------------
print(json.dumps(summary, indent=2))
