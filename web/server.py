"""
FastAPI WebSocket server for real-time EEG streaming
Streams data from Serenibrain headband to web dashboard
"""
import asyncio
import json
from datetime import datetime
from typing import List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import sys
import os

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bleak import BleakClient, BleakScanner
from process import decode_serenibrain_packet, calculate_band_powers

app = FastAPI()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

# EEG streaming state
eeg_client = None
is_streaming = False
channel_buffers = {0: [], 1: [], 2: []}
last_analysis_time = 0


class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"Client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                dead_connections.append(connection)
        
        # Clean up dead connections
        for conn in dead_connections:
            if conn in self.active_connections:
                self.active_connections.remove(conn)


manager = ConnectionManager()


def notification_handler(sender, data):
    """Handle incoming EEG data packets"""
    global channel_buffers, last_analysis_time
    
    try:
        # Decode packet
        packet = decode_serenibrain_packet(data)
        
        if packet['packet_type'] == 2 and packet['samples']:
            timestamp = datetime.now().isoformat()
            
            # Add samples to buffers
            for sample in packet['samples']:
                ch = sample['channel']
                if ch not in channel_buffers:
                    channel_buffers[ch] = []
                channel_buffers[ch].append(sample['voltage_uv'])
                
                # Keep last 6 seconds (250 Hz * 6 = 1500 samples)
                if len(channel_buffers[ch]) > 1500:
                    channel_buffers[ch].pop(0)
            
            # Send raw sample update
            asyncio.create_task(manager.broadcast({
                'type': 'samples',
                'timestamp': timestamp,
                'data': packet['samples']
            }))
            
            # Perform band analysis every 2 seconds
            current_time = asyncio.get_event_loop().time()
            if current_time - last_analysis_time >= 2.0:
                last_analysis_time = current_time
                
                # Analyze each channel
                analysis_results = {}
                for ch, voltages in channel_buffers.items():
                    if len(voltages) >= 250:  # At least 1 second of data
                        try:
                            analysis = calculate_band_powers(voltages)
                            analysis_results[ch] = {
                                'band_powers': analysis['band_powers'],
                                'band_ratios': analysis['band_ratios'],
                                'snr_db': analysis['snr_db'],
                                'relaxation_score': analysis['relaxation_score'],
                                'attention_score': analysis['attention_score'],
                                'signal_quality': analysis['signal_quality'],
                                'dominant_band': analysis['dominant_band']
                            }
                        except Exception as e:
                            print(f"Analysis error for channel {ch}: {e}")
                
                if analysis_results:
                    asyncio.create_task(manager.broadcast({
                        'type': 'analysis',
                        'timestamp': timestamp,
                        'data': analysis_results
                    }))
    
    except Exception as e:
        print(f"Error processing packet: {e}")


async def start_eeg_stream():
    """Connect to EEG device and start streaming"""
    global eeg_client, is_streaming, channel_buffers
    
    if is_streaming:
        return {"status": "already_streaming"}
    
    # Find device
    print("Scanning for Serenibrain device...")
    devices = await BleakScanner.discover(timeout=10.0)
    
    device = None
    for d in devices:
        name = d.name or ""
        if "serenibrain" in name.lower() or "th21a" in name.lower():
            device = d
            print(f"Found device: {d.name} ({d.address})")
            break
    
    if not device:
        return {"status": "error", "message": "Device not found"}
    
    try:
        # Connect to device
        eeg_client = BleakClient(device)
        await eeg_client.connect()
        
        # Find EEG service characteristics
        notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
        write_char = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"
        
        # Subscribe to notifications
        await eeg_client.start_notify(notify_char, notification_handler)
        
        # Send 4-command initialization sequence
        CMD_INIT = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05])
        CMD_PLAY = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01])
        CMD_STOP = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03])
        CMD_KEEP_ALIVE = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02])
        
        await eeg_client.write_gatt_char(write_char, CMD_INIT)
        await asyncio.sleep(0.1)
        await eeg_client.write_gatt_char(write_char, CMD_PLAY)
        await asyncio.sleep(0.1)
        await eeg_client.write_gatt_char(write_char, CMD_STOP)
        await asyncio.sleep(0.1)
        await eeg_client.write_gatt_char(write_char, CMD_KEEP_ALIVE)
        
        # Start keep-alive loop
        async def keep_alive_loop():
            while is_streaming:
                try:
                    await asyncio.sleep(1.0)
                    if eeg_client and eeg_client.is_connected:
                        await eeg_client.write_gatt_char(write_char, CMD_KEEP_ALIVE, response=False)
                except:
                    break
        
        asyncio.create_task(keep_alive_loop())
        
        is_streaming = True
        channel_buffers = {0: [], 1: [], 2: []}
        
        return {"status": "streaming", "device": device.name}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def stop_eeg_stream():
    """Stop EEG streaming"""
    global eeg_client, is_streaming
    
    if not is_streaming:
        return {"status": "not_streaming"}
    
    try:
        if eeg_client and eeg_client.is_connected:
            notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
            await eeg_client.stop_notify(notify_char)
            await eeg_client.disconnect()
        
        is_streaming = False
        eeg_client = None
        
        return {"status": "stopped"}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/")
async def get_index():
    """Serve the main dashboard"""
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# Mount audio directory for serving audio files
audio_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "audio")
if os.path.exists(audio_path):
    app.mount("/audio", StaticFiles(directory=audio_path), name="audio")
    print(f"Serving audio files from: {audio_path}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time data"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_json()
            
            if data['command'] == 'start':
                result = await start_eeg_stream()
                await websocket.send_json({'type': 'status', 'data': result})
            
            elif data['command'] == 'stop':
                result = await stop_eeg_stream()
                await websocket.send_json({'type': 'status', 'data': result})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on server shutdown"""
    await stop_eeg_stream()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
