"""
Verify Serenibrain EEG sampling rate and data processing
"""
import asyncio
import time
from bleak import BleakClient, BleakScanner
from process import decode_serenibrain_packet

# Track packets and samples
packet_times = []
sample_counts = []
total_samples = 0
start_time = None

def notification_handler(sender, data):
    global packet_times, sample_counts, total_samples, start_time
    
    if start_time is None:
        start_time = time.time()
    
    current_time = time.time() - start_time
    packet_times.append(current_time)
    
    try:
        packet = decode_serenibrain_packet(data)
        if packet['packet_type'] == 2:
            num_samples = len(packet['samples'])
            sample_counts.append(num_samples)
            total_samples += num_samples
            
            # Print every 10th packet
            if len(packet_times) % 10 == 0:
                elapsed = current_time
                packet_rate = len(packet_times) / elapsed if elapsed > 0 else 0
                sample_rate = total_samples / elapsed if elapsed > 0 else 0
                
                print(f"\n[Packet {len(packet_times)}] @ {elapsed:.1f}s")
                print(f"  Packet rate: {packet_rate:.2f} pkt/s")
                print(f"  Sample rate: {sample_rate:.2f} samples/s")
                print(f"  Samples/packet: {num_samples}")
                print(f"  Total samples: {total_samples}")
                
                # Show sample details from this packet
                if packet['samples']:
                    channels = {}
                    for sample in packet['samples']:
                        ch = sample['channel']
                        if ch not in channels:
                            channels[ch] = 0
                        channels[ch] += 1
                    print(f"  Channel distribution: {channels}")
    
    except Exception as e:
        print(f"Error decoding packet: {e}")


async def verify_sampling_rate(duration=30):
    """Connect and verify sampling rate for specified duration"""
    global packet_times, sample_counts, total_samples, start_time
    
    # Reset counters
    packet_times = []
    sample_counts = []
    total_samples = 0
    start_time = None
    
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
        print("Device not found!")
        return
    
    print(f"\nConnecting to {device.name}...")
    
    async with BleakClient(device) as client:
        print("Connected!")
        
        notify_char = "8653000b-43e6-47b7-9cb0-5fc21d4ae340"
        write_char = "8653000c-43e6-47b7-9cb0-5fc21d4ae340"
        
        # Subscribe to notifications
        await client.start_notify(notify_char, notification_handler)
        
        # Send 4-command initialization sequence
        print("\nSending initialization sequence...")
        CMD_INIT = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05])
        CMD_PLAY = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01])
        CMD_STOP = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03])
        CMD_KEEP_ALIVE = bytearray([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02])
        
        await client.write_gatt_char(write_char, CMD_INIT)
        await asyncio.sleep(0.1)
        await client.write_gatt_char(write_char, CMD_PLAY)
        await asyncio.sleep(0.1)
        await client.write_gatt_char(write_char, CMD_STOP)
        await asyncio.sleep(0.1)
        await client.write_gatt_char(write_char, CMD_KEEP_ALIVE)
        
        print(f"\n{'='*70}")
        print(f"MONITORING FOR {duration} SECONDS")
        print(f"{'='*70}")
        
        # Keep-alive loop
        async def keep_alive():
            while True:
                await asyncio.sleep(1.0)
                try:
                    await client.write_gatt_char(write_char, CMD_KEEP_ALIVE, response=False)
                except:
                    break
        
        keep_alive_task = asyncio.create_task(keep_alive())
        
        # Monitor for specified duration
        await asyncio.sleep(duration)
        
        keep_alive_task.cancel()
        await client.stop_notify(notify_char)
        
        # Final analysis
        print(f"\n{'='*70}")
        print("FINAL ANALYSIS")
        print(f"{'='*70}")
        
        total_time = packet_times[-1] if packet_times else 0
        avg_packet_rate = len(packet_times) / total_time if total_time > 0 else 0
        avg_sample_rate = total_samples / total_time if total_time > 0 else 0
        
        print(f"\nTotal packets: {len(packet_times)}")
        print(f"Total samples: {total_samples}")
        print(f"Duration: {total_time:.2f}s")
        print(f"\nAverage packet rate: {avg_packet_rate:.2f} pkt/s")
        print(f"Average sample rate: {avg_sample_rate:.2f} samples/s")
        
        if sample_counts:
            avg_samples_per_packet = sum(sample_counts) / len(sample_counts)
            print(f"Average samples per packet: {avg_samples_per_packet:.1f}")
        
        # Calculate per-channel sampling rate
        if total_samples > 0:
            num_channels = 3  # TH21A has 3 channels
            per_channel_rate = avg_sample_rate / num_channels
            print(f"\nPer-channel sample rate: {per_channel_rate:.2f} samples/s")
            print(f"Expected: ~83.33 Hz (250 Hz / 3 channels)")
        
        # Analyze packet timing consistency
        if len(packet_times) > 1:
            intervals = [packet_times[i] - packet_times[i-1] 
                        for i in range(1, len(packet_times))]
            avg_interval = sum(intervals) / len(intervals)
            print(f"\nAverage packet interval: {avg_interval*1000:.1f}ms")
            print(f"Expected: ~40ms (25 pkt/s)")
            
            # Check for timing consistency
            import statistics
            if len(intervals) > 2:
                stdev = statistics.stdev(intervals)
                print(f"Packet interval std dev: {stdev*1000:.2f}ms")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify EEG sampling rate")
    parser.add_argument("--duration", type=int, default=30, 
                       help="Monitoring duration in seconds (default: 30)")
    
    args = parser.parse_args()
    
    asyncio.run(verify_sampling_rate(duration=args.duration))
