"""
Live EEG streaming from Serenibrain headband via Bluetooth LE
Decodes packets in real-time and computes band powers on sliding windows
"""

import asyncio
import struct
import time
from collections import deque
from datetime import datetime
import numpy as np
from bleak import BleakScanner, BleakClient
from process import decode_serenibrain_packet, calculate_band_powers


class EEGStreamProcessor:
    """Handles live EEG data streaming and analysis"""
    
    def __init__(self, window_duration=6.0, sampling_rate=250.0, adc_scale=100.0):
        """
        Args:
            window_duration: Seconds of data to analyze for band powers
            sampling_rate: Expected sample rate in Hz (250 Hz per device spec)
            adc_scale: ADC conversion factor
        """
        self.window_duration = window_duration
        self.sampling_rate = sampling_rate
        self.adc_scale = adc_scale
        
        # Buffer for each channel (circular buffer)
        self.channel_buffers = {}  # channel_id -> deque of (timestamp, voltage_uv)
        self.max_buffer_samples = int(window_duration * sampling_rate * 1.5)  # 1.5x for safety
        
        # Statistics
        self.packet_count = 0
        self.sample_count = 0
        self.start_time = None
        self.last_analysis_time = {}  # channel_id -> timestamp of last analysis
        self.analysis_interval = 2.0  # Analyze every 2 seconds
        
    def process_packet(self, data):
        """Process incoming BLE notification packet"""
        try:
            # Decode packet
            packet = decode_serenibrain_packet(data, adc_scale=self.adc_scale)
            
            if packet['packet_type'] == 1:
                # Status packet
                print(f"\n[Status] Device: {packet.get('device_model', 'Unknown')}")
                return
            
            if packet['packet_type'] != 2 or not packet['samples']:
                return
            
            self.packet_count += 1
            current_time = time.time()
            
            if self.start_time is None:
                self.start_time = current_time
            
            # Add samples to channel buffers
            for sample in packet['samples']:
                ch = sample['channel']
                voltage = sample['voltage_uv']
                
                # Initialize buffer for new channel
                if ch not in self.channel_buffers:
                    self.channel_buffers[ch] = deque(maxlen=self.max_buffer_samples)
                    self.last_analysis_time[ch] = current_time
                
                # Add sample with timestamp
                self.channel_buffers[ch].append((current_time, voltage))
                self.sample_count += 1
            
            # Check if it's time to analyze
            for ch in self.channel_buffers:
                if current_time - self.last_analysis_time[ch] >= self.analysis_interval:
                    self._analyze_channel(ch, current_time)
                    self.last_analysis_time[ch] = current_time
            
            # Print progress every 10 packets
            if self.packet_count % 10 == 0:
                elapsed = current_time - self.start_time
                rate = self.packet_count / elapsed if elapsed > 0 else 0
                print(f"[{self.packet_count:4d} pkts] {self.sample_count:5d} samples | "
                      f"{rate:.1f} pkt/s | {len(self.channel_buffers)} channels")
        
        except Exception as e:
            print(f"Error processing packet: {e}")
    
    def _analyze_channel(self, channel_id, current_time):
        """Analyze band powers for a channel"""
        buffer = self.channel_buffers[channel_id]
        
        if len(buffer) < 10:
            return
        
        # Extract voltages from buffer (ignore timestamps for now)
        voltages = [v for _, v in buffer]
        
        # Only analyze if we have enough data
        window_samples = int(self.window_duration * self.sampling_rate)
        if len(voltages) < min(10, window_samples // 2):
            return
        
        try:
            # Calculate band powers
            analysis = calculate_band_powers(
                voltages[-window_samples:] if len(voltages) > window_samples else voltages,
                sampling_rate=self.sampling_rate,
                use_welch=True
            )
            
            # Print results
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"\n{'='*70}")
            print(f"[{timestamp}] Channel {channel_id} Analysis ({len(voltages)} samples)")
            print(f"{'='*70}")
            print(f"Signal Quality: {analysis['signal_quality']} (SNR: {analysis['snr_db']:.1f} dB)")
            print(f"Dominant: {analysis['dominant_band'].upper()} | "
                  f"Relax: {analysis['relaxation_score']:.0f} | "
                  f"Focus: {analysis['attention_score']:.0f}")
            
            print(f"\nBand Ratios:")
            for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']:
                ratio = analysis['band_ratios'][band]
                bar = '█' * int(ratio / 2)
                print(f"  {band.capitalize():8s}: {ratio:5.1f}% {bar}")
            
        except Exception as e:
            print(f"Error analyzing channel {channel_id}: {e}")
    
    def get_statistics(self):
        """Return streaming statistics"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        return {
            'packets': self.packet_count,
            'samples': self.sample_count,
            'duration': elapsed,
            'packet_rate': self.packet_count / elapsed if elapsed > 0 else 0,
            'channels': len(self.channel_buffers),
            'buffer_sizes': {ch: len(buf) for ch, buf in self.channel_buffers.items()}
        }


async def find_serenibrain_device(timeout=10.0):
    """Scan for Serenibrain EEG headband"""
    print(f"Scanning for Serenibrain device (timeout: {timeout}s)...")
    
    devices = await BleakScanner.discover(timeout=timeout)
    
    # Look for device with "Serenibrain" or "TH21A" in name
    for device in devices:
        name = device.name or ""
        if "serenibrain" in name.lower() or "th21a" in name.lower() or "eeg" in name.lower():
            print(f"Found device: {device.name} ({device.address})")
            return device
    
    # If not found by name, show all devices
    print("\nAvailable devices:")
    for device in devices:
        print(f"  {device.name or 'Unknown'} - {device.address}")
    
    return None


async def stream_eeg_data(device_address, characteristic_uuid=None, write_char_uuid=None, duration=None):
    """
    Connect to device and stream EEG data
    
    Args:
        device_address: BLE device address or name
        characteristic_uuid: UUID of notification characteristic (None = auto-detect)
        write_char_uuid: UUID of write characteristic for commands (None = auto-detect)
        duration: How long to stream in seconds (None = indefinite)
    """
    processor = EEGStreamProcessor(
        window_duration=6.0,
        sampling_rate=77.88,  # Per-channel rate: 233.65 Hz total / 3 channels
        adc_scale=100.0
    )
    
    # Stream control commands (discovered from BT log analysis)
    CMD_START_STREAM = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05])  # "CTRL" + start
    CMD_STOP_STREAM = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03])   # "CTRL" + stop
    CMD_KEEP_ALIVE = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02])    # "CTRL" + keepalive
    
    def notification_handler(sender, data):
        """Called when BLE notification arrives"""
        processor.process_packet(data)
    
    async with BleakClient(device_address) as client:
        print(f"\nConnected to {device_address}")
        
        # Auto-detect characteristics if not provided
        if characteristic_uuid is None or write_char_uuid is None:
            print("\nDiscovering services and characteristics...")
            notify_chars = []
            write_chars = []
            
            # Known Serenibrain EEG service UUID
            eeg_service_uuid = "8653000a-43e6-47b7-9cb0-5fc21d4ae340"
            
            for service in client.services:
                print(f"\nService: {service.uuid}")
                is_eeg_service = service.uuid.lower() == eeg_service_uuid.lower()
                
                for char in service.characteristics:
                    props = ','.join(char.properties)
                    print(f"  Char: {char.uuid} - {props}")
                    
                    # Look for notify characteristic (prioritize EEG service)
                    if "notify" in char.properties:
                        if is_eeg_service:
                            notify_chars.insert(0, char.uuid)  # Put EEG service first
                            print(f"  -> Found EEG notify characteristic (PRIORITY)")
                        else:
                            notify_chars.append(char.uuid)
                            print(f"  -> Found notify characteristic")
                    
                    # Look for write characteristic (prioritize EEG service)
                    if "write" in char.properties or "write-without-response" in char.properties:
                        if is_eeg_service:
                            write_chars.insert(0, char.uuid)  # Put EEG service first
                            print(f"  -> Found EEG write characteristic (PRIORITY)")
                        else:
                            write_chars.append(char.uuid)
                            print(f"  -> Found write characteristic")
            
            if characteristic_uuid is None:
                if notify_chars:
                    characteristic_uuid = notify_chars[0]
                    print(f"\nUsing notify characteristic: {characteristic_uuid}")
                else:
                    print("\nError: No notification characteristic found!")
                    return
            
            if write_char_uuid is None:
                if write_chars:
                    write_char_uuid = write_chars[0]
                    print(f"Using write characteristic: {write_char_uuid}")
                else:
                    print("Warning: No write characteristic found - streaming may not start!")
        
        # Subscribe to notifications
        print(f"\nSubscribing to notifications on {characteristic_uuid}...")
        try:
            await client.start_notify(characteristic_uuid, notification_handler)
            print("[OK] Subscribed to notifications")
        except Exception as e:
            print(f"Error subscribing: {e}")
            return
        
        # CRITICAL 4-COMMAND INITIALIZATION SEQUENCE (discovered from BT log analysis)
        # This exact sequence is required to trigger streaming!
        if write_char_uuid:
            print(f"\n{'='*70}")
            print("SENDING 4-COMMAND INITIALIZATION SEQUENCE")
            print(f"{'='*70}")
            
            try:
                # Command 1: INIT/START
                print("\n[1/4] Sending INIT command (CTRL 00 03 00 05)...")
                await client.write_gatt_char(write_char_uuid, CMD_START_STREAM)
                await asyncio.sleep(0.1)
                print("      ✓ INIT command sent")
                
                # Command 2: PLAY/RESUME
                CMD_PLAY = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01])
                print("\n[2/4] Sending PLAY command (CTRL 00 04 00 01)...")
                await client.write_gatt_char(write_char_uuid, CMD_PLAY)
                await asyncio.sleep(0.1)
                print("      ✓ PLAY command sent")
                
                # Command 3: STOP/RESET (counterintuitive but REQUIRED!)
                print("\n[3/4] Sending STOP/RESET command (CTRL 00 03 00 03)...")
                await client.write_gatt_char(write_char_uuid, CMD_STOP_STREAM)
                await asyncio.sleep(0.1)
                print("      ✓ STOP/RESET command sent")
                
                # Command 4: KEEP-ALIVE (triggers actual streaming)
                print("\n[4/4] Sending KEEP-ALIVE command (CTRL 00 05 00 02)...")
                await client.write_gatt_char(write_char_uuid, CMD_KEEP_ALIVE)
                await asyncio.sleep(0.1)
                print("      ✓ KEEP-ALIVE command sent")
                
                print(f"\n{'='*70}")
                print("✓ INITIALIZATION COMPLETE - Waiting for data stream...")
                print(f"{'='*70}\n")
                
            except Exception as e:
                print(f"\n✗ Error during initialization: {e}")
                print("Continuing anyway - device may still stream...")
        else:
            print("\nWarning: No write characteristic - cannot send commands!")
        
        # Wait for data to start flowing
        await asyncio.sleep(2)
        
        if processor.packet_count == 0:
            print("\n[!] WARNING: No packets received after initialization!")
            print("Troubleshooting:")
            print("  1. Device may be in sleep mode - try power cycling")
            print("  2. Check battery level")
            print("  3. Make sure device is not connected to phone app")
            print("\nContinuing to wait...")
        else:
            print(f"\n✓ SUCCESS! Receiving data ({processor.packet_count} packets so far)")
        
        # Start keep-alive loop (send every 1 second to maintain stream)
        keep_alive_task = None
        if write_char_uuid:
            async def send_keep_alive():
                try:
                    while True:
                        await asyncio.sleep(1.0)
                        await client.write_gatt_char(write_char_uuid, CMD_KEEP_ALIVE, response=False)
                except:
                    pass
            
            keep_alive_task = asyncio.create_task(send_keep_alive())
            print("[OK] Keep-alive loop started (1s interval)\n")
        
        print(f"{'='*70}")
        print("STREAMING EEG DATA - Press Ctrl+C to stop")
        print(f"{'='*70}\n")
        
        try:
            # Stream for specified duration or indefinitely
            if duration:
                await asyncio.sleep(duration)
            else:
                # Run until interrupted
                while True:
                    await asyncio.sleep(1)
        
        except KeyboardInterrupt:
            print("\n\nStopping stream...")
        
        finally:
            # Cancel keep-alive
            if keep_alive_task:
                keep_alive_task.cancel()
            
            # Send STOP command
            if write_char_uuid:
                try:
                    await client.write_gatt_char(write_char_uuid, CMD_STOP_STREAM)
                    print("[OK] STOP command sent")
                except:
                    pass
            
            # Stop notifications
            await client.stop_notify(characteristic_uuid)
            
            # Print final statistics
            stats = processor.get_statistics()
            print(f"\n{'='*70}")
            print("STREAM STATISTICS")
            print(f"{'='*70}")
            print(f"Total Packets: {stats['packets']}")
            print(f"Total Samples: {stats['samples']}")
            print(f"Duration: {stats['duration']:.1f}s")
            print(f"Packet Rate: {stats['packet_rate']:.1f} pkt/s")
            print(f"Channels: {stats['channels']}")
            print(f"Buffer Sizes: {stats['buffer_sizes']}")
            print(f"{'='*70}\n")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stream live EEG data from Serenibrain headband")
    parser.add_argument("--address", help="Device BLE address (auto-detect if not provided)")
    parser.add_argument("--uuid", help="Characteristic UUID for notifications")
    parser.add_argument("--write-uuid", help="Characteristic UUID for write commands")
    parser.add_argument("--duration", type=float, help="Stream duration in seconds (default: indefinite)")
    parser.add_argument("--scan-only", action="store_true", help="Only scan for devices, don't connect")
    
    args = parser.parse_args()
    
    # Always scan to get device object (required for Windows BLE)
    if args.scan_only:
        await find_serenibrain_device(timeout=10.0)
        return
    
    # Use the existing scan function to find device
    device = await find_serenibrain_device(timeout=10.0)
    
    if not device:
        print("\nNo Serenibrain device found!")
        if args.address:
            print(f"Could not find device with address: {args.address}")
        return
    
    # If address was specified, verify it matches
    if args.address:
        target_addr = args.address.upper().replace('-', ':')
        device_addr = device.address.upper().replace('-', ':')
        if device_addr != target_addr:
            print(f"\nWarning: Found device {device.address} but requested {args.address}")
            print("Proceeding with found device...")
    
    # Start streaming with device object (with retry logic for Windows BLE flakiness)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\nConnection attempt {attempt + 1}/{max_retries}...")
            await stream_eeg_data(
                device_address=device,  # Pass device object, not address string!
                characteristic_uuid=args.uuid,
                write_char_uuid=args.write_uuid,
                duration=args.duration
            )
            break  # Success!
        except Exception as e:
            print(f"\nAttempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in 2 seconds...")
                await asyncio.sleep(2)
            else:
                print(f"\nAll {max_retries} attempts failed. Please:")
                print("  1. Make sure device is powered on")
                print("  2. Device is in range")
                print("  3. Not connected to another app")
                raise


if __name__ == "__main__":
    asyncio.run(main())
