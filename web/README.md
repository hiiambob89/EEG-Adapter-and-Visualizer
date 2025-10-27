# EEG Web Monitoring Interface

Real-time web dashboard for Serenibrain EEG data visualization with beautiful D3.js charts!

## Features

✅ **Live Brainwave Visualization**
- Real-time band power analysis
- Delta, Theta, Alpha, Beta, Gamma tracking
- 3-channel EEG support

✅ **Interactive Charts**
- Band ratios (horizontal bar chart)
- Band powers over time (line chart)
- Relaxation vs Focus trends (dual line chart)
- Frequency spectrum (bar chart)

✅ **Mental State Metrics**
- Relaxation score (0-100)
- Focus/Attention score (0-100)
- Signal quality indicator
- Dominant brainwave band

✅ **Channel Selection**
- Switch between Channel 0, 1, 2
- Independent analysis per channel

## Tech Stack

- **Backend**: FastAPI with WebSocket
- **Frontend**: Vanilla JS + D3.js v7
- **Real-time**: WebSocket communication
- **Styling**: Modern gradient design with glassmorphism

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Dashboard

1. **Start the server:**
```bash
cd web
python server.py
```

2. **Open your browser:**
```
http://localhost:8000
```

3. **Click "Start Streaming"** to connect to your Serenibrain headband

## How It Works

1. Server connects to Serenibrain device via Bluetooth
2. Sends 4-command initialization sequence
3. Streams real-time EEG data via WebSocket
4. Browser receives updates every 2 seconds
5. D3.js renders beautiful visualizations

## Charts Explained

### Band Ratios
Shows current percentage distribution of brainwave frequencies

### Band Powers Over Time
Historical view of all 5 frequency bands (last 100 seconds)

### Relaxation vs Focus
Tracks your mental state over time:
- **Blue line**: Relaxation (high alpha, low beta)
- **Orange line**: Focus (high beta, moderate alpha)

### Frequency Spectrum
Current absolute power in each frequency band (µV²)

## Troubleshooting

**No data streaming?**
- Make sure headband is powered on
- Close Serenibrain phone app
- Device should not be paired in Windows Bluetooth settings

**WebSocket errors?**
- Check console for errors
- Restart server
- Try different browser (Chrome/Edge recommended)

**Charts not updating?**
- Select correct channel (0, 1, or 2)
- Wait 2 seconds for first analysis
- Check browser console for JavaScript errors
