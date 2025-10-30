import json
import numpy as np
import pandas as pd

# -----------------------------
# CONFIGURATION
# -----------------------------
CSV_PATH = "C:\\Users\\kaden\\Downloads\\finalfinal.csv"  # replace with your CSV path
WINDOW_SEC = 10             # period length for summarizing (seconds)
FS_FALLBACK = 83.33         # fallback per-channel sampling rate in Hz

# -----------------------------
# LOAD CSV
# -----------------------------
df = pd.read_csv(CSV_PATH)

# Normalise empty strings to NaN so we don't treat missing values as zeros
df = df.replace(r'^\s*$', np.nan, regex=True)

# Ensure we have a usable time axis in seconds
time_col = None
for candidate in ['Practice Timestamp (ms)', 'timestamp_ms', 'timestamp', 'Time (s)', 'Time_s']:
    if candidate in df.columns:
        time_col = candidate
        break

if time_col is None:
    raise SystemExit("No timestamp column found in CSV")

time_series = pd.to_numeric(df[time_col], errors='coerce')
if 'ms' in time_col.lower():
    df['Time_s'] = time_series / 1000.0
else:
    df['Time_s'] = time_series

df = df.sort_values('Time_s').reset_index(drop=True)

# Derive effective sampling rate from time deltas (ignoring zeros for sparse data)
time_diffs = df['Time_s'].diff().dropna()
time_diffs = time_diffs[time_diffs > 0]
if not time_diffs.empty:
    effective_fs = 1.0 / time_diffs.median()
else:
    effective_fs = FS_FALLBACK

print(f"Detected sampling rate ≈ {effective_fs:.2f} Hz (fallback {FS_FALLBACK} Hz if sparse)")

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
    raise SystemExit("❌ Unknown CSV format!")

# -----------------------------
# SPLIT INTO PERIODS (TIME-BASED SO SPARSE DATA WORKS)
# -----------------------------
total_duration = df['Time_s'].max() - df['Time_s'].min()
num_periods = int(np.ceil(total_duration / WINDOW_SEC)) if WINDOW_SEC > 0 else 0
if num_periods == 0 and not df.empty:
    num_periods = 1

summary = []

for i in range(num_periods):
    window_start = df['Time_s'].min() + i * WINDOW_SEC
    window_end = window_start + WINDOW_SEC

    period_df = df[(df['Time_s'] >= window_start) & (df['Time_s'] < window_end)]

    if period_df.empty:
        summary.append({
            'Period': i,
            'Start_s': float(window_start),
            'End_s': float(window_end),
            'Samples': 0
        })
        continue

    stats = {
        'Period': i,
        'Start_s': float(period_df['Time_s'].iloc[0]),
        'End_s': float(period_df['Time_s'].iloc[-1]),
        'Samples': int(len(period_df))
    }

    # Process band data
    for band in BANDS:
        col = f"{band}{band_suffix}"
        if col in period_df.columns:
            vals = pd.to_numeric(period_df[col], errors='coerce')
            if vals.dropna().empty:
                stats[f'{band}_mean'] = None
                stats[f'{band}_std'] = None
                stats[f'{band}_max'] = None
            else:
                stats[f'{band}_mean'] = float(vals.mean(skipna=True))
                stats[f'{band}_std'] = float(vals.std(skipna=True))
                stats[f'{band}_max'] = float(vals.max(skipna=True))
        else:
            stats[f'{band}_mean'] = stats[f'{band}_std'] = stats[f'{band}_max'] = None
    
    # Add percentages if powers CSV
    if is_powers_csv and percent_suffix:
        for band in BANDS:
            col = f"{band}{percent_suffix}"
            if col in period_df.columns:
                vals = pd.to_numeric(period_df[col], errors='coerce')
                stats[f'{band}_percent_mean'] = float(vals.mean(skipna=True)) if not vals.dropna().empty else None
            else:
                stats[f'{band}_percent_mean'] = None
    
    # Add relaxation/focus scores if powers CSV
    if is_powers_csv:
        if 'Relaxation Score' in period_df.columns:
            relax = pd.to_numeric(period_df['Relaxation Score'], errors='coerce')
            stats['Relaxation_mean'] = float(relax.mean(skipna=True)) if not relax.dropna().empty else None
            stats['Relaxation_std'] = float(relax.std(skipna=True)) if not relax.dropna().empty else None
        if 'Focus Score' in period_df.columns:
            focus = pd.to_numeric(period_df['Focus Score'], errors='coerce')
            stats['Focus_mean'] = float(focus.mean(skipna=True)) if not focus.dropna().empty else None
            stats['Focus_std'] = float(focus.std(skipna=True)) if not focus.dropna().empty else None

    summary.append(stats)

# -----------------------------
# PRINT PASTE-READY JSON
# -----------------------------
print(json.dumps(summary, indent=2))
