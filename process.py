import struct
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
from collections import deque


class EEGBuffer:
    """
    Buffer for accumulating EEG samples across multiple packets
    Manages separate buffers for each channel
    """
    def __init__(self, buffer_duration=4.0, sampling_rate=78.0):
        """
        Args:
            buffer_duration: Duration in seconds to buffer
            sampling_rate: Per-channel sampling rate in Hz
        """
        self.sampling_rate = sampling_rate
        self.buffer_size = int(buffer_duration * sampling_rate)
        self.channels = {0: deque(maxlen=self.buffer_size),
                        1: deque(maxlen=self.buffer_size),
                        2: deque(maxlen=self.buffer_size)}
        self.total_samples = 0
        
    def add_packet(self, packet_data):
        """Add samples from a decoded packet"""
        if packet_data['packet_type'] != 2:
            return
        
        for sample in packet_data['samples']:
            ch = sample['channel']
            voltage = sample['voltage_uv']
            self.channels[ch].append(voltage)
            self.total_samples += 1
    
    def get_channel_data(self, channel):
        """Get buffered data for a specific channel"""
        return list(self.channels[channel])
    
    def is_ready_for_analysis(self, min_duration=2.0):
        """Check if we have enough data for analysis"""
        min_samples = int(min_duration * self.sampling_rate)
        return all(len(buf) >= min_samples for buf in self.channels.values())
    
    def analyze_all_channels(self):
        """Analyze all channels and return results"""
        if not self.is_ready_for_analysis():
            return None
        
        results = {}
        for ch in [0, 1, 2]:
            voltages = self.get_channel_data(ch)
            if len(voltages) >= 156:  # Minimum for good analysis
                results[ch] = calculate_band_powers(voltages, self.sampling_rate)
        
        return results
    
    def get_stats(self):
        """Get buffer statistics"""
        return {
            'total_samples': self.total_samples,
            'buffer_size': self.buffer_size,
            'channel_lengths': {ch: len(buf) for ch, buf in self.channels.items()},
            'ready_for_analysis': self.is_ready_for_analysis()
        }




def calculate_band_powers(voltages, sampling_rate=100):
    """
    Calculate brainwave band powers using FFT
    
    Args:
        voltages: List of voltage values in microvolts
        sampling_rate: Sampling rate in Hz (default 100 Hz per channel)
    
    Returns:
        Dictionary with band powers and metrics
    """
    # Convert to numpy array and remove DC offset
    data = np.array(voltages)
    data = data - np.mean(data)
    
    # Apply Hamming window to reduce spectral leakage
    window = np.hamming(len(data))
    data_windowed = data * window
    
    # Perform FFT
    N = len(data)
    fft_values = fft(data_windowed)
    fft_freqs = fftfreq(N, 1/sampling_rate)
    
    # Get positive frequencies only
    positive_freqs = fft_freqs[:N//2]
    power_spectrum = np.abs(fft_values[:N//2])**2 / N
    
    # Define frequency bands (in Hz)
    # Note: With 78 Hz sampling, Nyquist = 39 Hz
    # Gamma band limited to avoid aliasing
    bands = {
        'delta': (0.5, 4),
        'theta': (4, 8),
        'alpha': (8, 13),
        'beta': (13, 30),
        'gamma': (30, 38)  # Limited by Nyquist frequency
    }
    
    # Calculate power in each band
    band_powers = {}
    for band_name, (low_freq, high_freq) in bands.items():
        # Find indices for this frequency band
        band_indices = np.where((positive_freqs >= low_freq) & (positive_freqs <= high_freq))[0]
        
        if len(band_indices) > 0:
            # Sum power in this band
            band_power = np.sum(power_spectrum[band_indices])
            band_powers[band_name] = band_power
        else:
            band_powers[band_name] = 0.0
    
    # Calculate total power
    total_power = sum(band_powers.values())
    
    # Calculate percentage ratios
    band_ratios = {}
    for band_name, power in band_powers.items():
        if total_power > 0:
            band_ratios[band_name] = (power / total_power) * 100
        else:
            band_ratios[band_name] = 0.0
    
    # Calculate signal quality metrics
    signal_power = np.var(data)  # Signal variance
    
    # Estimate noise (high frequency content above 50 Hz)
    noise_indices = np.where(positive_freqs > 50)[0]
    if len(noise_indices) > 0:
        noise_power = np.sum(power_spectrum[noise_indices])
    else:
        noise_power = 0.01  # Small value to avoid division by zero
    
    # Signal-to-Noise Ratio (in dB)
    snr_db = 10 * np.log10(signal_power / (noise_power + 1e-10))
    
    # Apply 1/f normalization to account for pink noise law
    # Lower frequencies naturally have more power in EEG
    norm_delta = band_powers['delta'] / 10.0   # Delta is huge, scale down significantly
    norm_theta = band_powers['theta'] / 3.0    # Theta is big, scale down moderately
    norm_alpha = band_powers['alpha'] / 2.0    # Alpha is moderate, scale down slightly
    norm_beta = band_powers['beta'] * 1.0      # Beta is baseline, no scaling
    norm_gamma = band_powers['gamma'] * 5.0    # Gamma is tiny, scale up significantly
    
    # Attention/Focus score (high beta + gamma vs delta + theta)
    # Higher when fast waves dominate (alert, focused)
    attention_numerator = norm_beta + norm_gamma
    attention_denominator = attention_numerator + norm_delta + norm_theta
    attention_score = (attention_numerator / (attention_denominator + 1e-10)) * 200
    attention_score = min(100, max(0, attention_score))
    
    # Relaxation score (high alpha + moderate theta vs beta + delta)
    # Higher when calm but awake (relaxed awareness)
    relax_numerator = norm_alpha + 0.5 * norm_theta
    relax_denominator = relax_numerator + norm_beta + 0.3 * norm_delta
    relaxation_score = (relax_numerator / (relax_denominator + 1e-10)) * 200
    relaxation_score = min(100, max(0, relaxation_score))
    
    # Meditation score (high alpha + theta, low beta)
    # Higher when deeply calm (meditative state)
    meditation_numerator = norm_alpha + norm_theta
    meditation_denominator = meditation_numerator + norm_beta + 0.2 * norm_delta
    meditation_score = (meditation_numerator / (meditation_denominator + 1e-10)) * 180
    meditation_score = min(100, max(0, meditation_score))
    
    # Drowsiness score (high delta + theta, low alpha + beta)
    # Higher when slow waves dominate (sleepy, unfocused)
    drowsy_numerator = norm_delta + norm_theta
    drowsy_denominator = drowsy_numerator + norm_alpha + norm_beta
    drowsiness_score = (drowsy_numerator / (drowsy_denominator + 1e-10)) * 150
    drowsiness_score = min(100, max(0, drowsiness_score))
    
    return {
        'band_powers': band_powers,
        'band_ratios': band_ratios,
        'total_power': total_power,
        'snr_db': snr_db,
        'relaxation_score': relaxation_score,
        'attention_score': attention_score,
        'meditation_score': meditation_score,
        'drowsiness_score': drowsiness_score,
        'signal_quality': 'Good' if snr_db > 10 else 'Fair' if snr_db > 5 else 'Poor',
        'dominant_band': max(band_powers.items(), key=lambda x: x[1])[0]
    }


def analyze_eeg_packet(packet_data):
    """
    Perform complete EEG analysis on a decoded packet
    
    Args:
        packet_data: Decoded packet dictionary
    
    Returns:
        Dictionary with per-channel analysis
    """
    if packet_data['packet_type'] != 2 or not packet_data['samples']:
        return None
    
    # Group samples by channel
    channels = {}
    for sample in packet_data['samples']:
        ch = sample['channel']
        if ch not in channels:
            channels[ch] = []
        channels[ch].append(sample['voltage_uv'])
    
    # Analyze each channel
    channel_analysis = {}
    for ch, voltages in channels.items():
        # Need enough samples for meaningful frequency analysis
        # At 78 Hz, need at least 2 seconds = 156 samples
        if len(voltages) >= 156:
            analysis = calculate_band_powers(voltages)
            channel_analysis[ch] = analysis
        else:
            print(f"Channel {ch}: Only {len(voltages)} samples (need 156+ for analysis)")
    
    return channel_analysis


def print_eeg_analysis(channel_analysis):
    """Pretty print EEG analysis results"""
    if not channel_analysis:
        print("\nNot enough data for frequency analysis")
        return
    
    print(f"\n{'='*70}")
    print("EEG FREQUENCY BAND ANALYSIS")
    print(f"{'='*70}")
    
    for ch, analysis in sorted(channel_analysis.items()):
        print(f"\n--- Channel {ch} ---")
        print(f"Signal Quality: {analysis['signal_quality']} (SNR: {analysis['snr_db']:.1f} dB)")
        print(f"Dominant Band: {analysis['dominant_band'].upper()}")
        
        print(f"\nMental State Scores:")
        print(f"  Relaxation:  {analysis['relaxation_score']:5.1f}/100  ", end="")
        print('█' * int(analysis['relaxation_score'] / 5))
        print(f"  Attention:   {analysis['attention_score']:5.1f}/100  ", end="")
        print('█' * int(analysis['attention_score'] / 5))
        print(f"  Meditation:  {analysis['meditation_score']:5.1f}/100  ", end="")
        print('█' * int(analysis['meditation_score'] / 5))
        print(f"  Drowsiness:  {analysis['drowsiness_score']:5.1f}/100  ", end="")
        print('█' * int(analysis['drowsiness_score'] / 5))
        
        print(f"\nBand Powers (absolute):")
        for band, power in analysis['band_powers'].items():
            print(f"  {band.capitalize():8s}: {power:12.2f} µV²")
        
        print(f"\nBand Ratios (percentage):")
        for band, ratio in analysis['band_ratios'].items():
            bar_length = int(ratio / 2)  # Scale to fit display
            bar = '█' * bar_length
            print(f"  {band.capitalize():8s}: {ratio:5.1f}% {bar}")
    
    print(f"\n{'='*70}\n")


def decode_serenibrain_packet(hex_string):
    """
    Decode Serenibrain Bluetooth EEG packets
    
    Args:
        hex_string: Hex string like "44-41-54-41-00-02..." or raw bytes
    
    Returns:
        Dictionary with decoded data
    """
    # Convert hex string to bytes if needed
    if isinstance(hex_string, str):
        # Remove dashes and spaces
        hex_string = hex_string.replace('-', '').replace(' ', '')
        data = bytes.fromhex(hex_string)
    else:
        data = hex_string
    
    # Parse header
    header = data[0:4].decode('ascii')
    packet_type = data[5]  # Second byte of the type field
    num_channels = data[7]  # Second byte of the channels field
    payload_size = struct.unpack('<I', data[8:12])[0]  # Little-endian uint32
    
    result = {
        'header': header,
        'packet_type': packet_type,
        'num_channels': num_channels,
        'payload_size': payload_size,
        'samples': []
    }
    
    # Type 0x01: Status/Info packet
    if packet_type == 1:
        device_model = data[12:17].decode('ascii', errors='ignore')
        result['device_model'] = device_model
        result['raw_data'] = [struct.unpack('<I', data[i:i+4])[0] 
                              for i in range(24, min(len(data), 40), 4)]
        return result
    
    # Type 0x02: EEG Data Stream
    elif packet_type == 2:
        offset = 12
        
        # Pattern analysis: Looking at multiple packets, it seems like
        # samples are grouped by channel, not interleaved
        samples = []
        sample_num = 0
        
        while offset + 7 <= len(data) - 10:  # Leave last 10 bytes for metadata
            # Read first 3 bytes as signed 24-bit integer (little-endian)
            raw_value_bytes = data[offset:offset+3]
            
            # Combine 3 bytes into signed 24-bit value
            value = raw_value_bytes[0] | (raw_value_bytes[1] << 8) | (raw_value_bytes[2] << 16)
            
            # Sign extension for 24-bit signed integer
            if value & 0x800000:
                value = value - 0x1000000
            
            # Next 4 bytes contain padding and sample info
            # Bytes 3-4: 0x00 0x00
            # Bytes 5-6: sample index (little-endian)
            sample_idx = struct.unpack('<H', data[offset+4:offset+6])[0]
            
            # Byte 6: appears to be 0x00 (channel marker or padding)
            channel_byte = data[offset+6]
            
            # Determine channel based on sample_idx
            # With 3 channels, samples might be: Ch0, Ch1, Ch2, Ch0, Ch1, Ch2...
            channel = sample_idx % num_channels
            
            # Voltage conversion - try scale of 100
            voltage_uv = value / 100.0
            
            samples.append({
                'sample_number': sample_num,
                'sample_index': sample_idx,
                'channel': channel,
                'raw_value': value,
                'voltage_uv': voltage_uv,
                'raw_hex': data[offset:offset+7].hex()
            })
            
            offset += 7
            sample_num += 1
        
        result['samples'] = samples
        
        # Last 10 bytes are metadata/timestamp
        if len(data) >= 10:
            result['metadata'] = data[-10:].hex()
            
            # Try to decode as timestamp (last 8 bytes might be double timestamp)
            try:
                timestamp = struct.unpack('<d', data[-10:-2])[0]
                result['timestamp'] = timestamp
            except:
                pass
        
        return result
    
    return result


def print_decoded_packet(packet_data):
    """Pretty print decoded packet"""
    print(f"\n{'='*60}")
    print(f"Header: {packet_data['header']}")
    print(f"Packet Type: 0x{packet_data['packet_type']:02X}")
    print(f"Channels: {packet_data['num_channels']}")
    print(f"Payload Size: {packet_data['payload_size']} bytes")
    
    if packet_data['packet_type'] == 1:
        print(f"Device Model: {packet_data.get('device_model', 'N/A')}")
        print(f"Raw Data: {packet_data.get('raw_data', [])}")
    
    elif packet_data['packet_type'] == 2:
        print(f"\nEEG Samples ({len(packet_data['samples'])} samples):")
        print(f"{'#':<4} {'SampIdx':<8} {'Ch':<4} {'Raw':<10} {'Voltage (µV)':<15} {'Raw Hex'}")
        print("-" * 70)
        
        for sample in packet_data['samples']:
            print(f"{sample['sample_number']:<4} "
                  f"{sample['sample_index']:<8} "
                  f"{sample['channel']:<4} "
                  f"{sample['raw_value']:<10} "
                  f"{sample['voltage_uv']:<15.2f} "
                  f"{sample['raw_hex']}")
        
        # Group by channel for statistics
        channels = {}
        for sample in packet_data['samples']:
            ch = sample['channel']
            if ch not in channels:
                channels[ch] = []
            channels[ch].append(sample['voltage_uv'])
        
        print(f"\nPer-Channel Statistics:")
        for ch in sorted(channels.keys()):
            voltages = channels[ch]
            print(f"  Channel {ch}: Min={min(voltages):.2f}µV, Max={max(voltages):.2f}µV, "
                  f"Avg={sum(voltages)/len(voltages):.2f}µV, Samples={len(voltages)}")
        
        if 'timestamp' in packet_data:
            print(f"\nTimestamp: {packet_data['timestamp']}")
        if 'metadata' in packet_data:
            print(f"Metadata: {packet_data['metadata']}")
    
    print(f"{'='*60}\n")


# Example usage with your data
if __name__ == "__main__":
    # Type 1 packet (status)
    packet1 = "44-41-54-41-00-01-00-03-20-00-00-00-54-48-32-31-41-00-00-00-00-00-00-01-00-00-00-01-00-00-00-0A-00-00-00-02-00-00-00-18-00-00-00-0C"
    
    # Type 2 packet (EEG data)
    packet2 = "44-41-54-41-00-02-00-03-50-00-00-00-D1-3E-FD-00-00-00-00-7C-3E-FD-00-00-01-00-B6-3E-FD-00-00-02-00-8C-3E-FD-00-00-03-00-7A-3E-FD-00-00-04-00-8B-3E-FD-00-00-05-00-BF-3E-FD-00-00-06-00-B6-3E-FD-00-00-07-00-7E-3E-FD-00-00-08-00-99-3E-FD-00-00-09-00-21-10-E0-71-C6-87-F6-41-00-00"
    
    print("\n=== PACKET TYPE 1 (Status/Info) ===")
    decoded1 = decode_serenibrain_packet(packet1)
    print_decoded_packet(decoded1)
    
    print("\n=== PACKET TYPE 2 (EEG Data) ===")
    decoded2 = decode_serenibrain_packet(packet2)
    print_decoded_packet(decoded2)
    
    print("\n" + "="*70)
    print("DEMONSTRATING BUFFER USAGE")
    print("="*70)
    
    # Create buffer for 4 seconds of data
    buffer = EEGBuffer(buffer_duration=4.0, sampling_rate=78.0)
    
    # Simulate adding packets (in real usage, you'd add packets as they arrive)
    print("\nAdding single packet to buffer...")
    buffer.add_packet(decoded2)
    
    stats = buffer.get_stats()
    print(f"\nBuffer stats after 1 packet:")
    print(f"  Total samples: {stats['total_samples']}")
    print(f"  Per channel: {stats['channel_lengths']}")
    print(f"  Ready for analysis: {stats['ready_for_analysis']}")
    
    # Calculate how many packets needed
    packets_needed = int(np.ceil(156 * 3 / 10))  # 156 samples/channel, 3 channels, 10 samples/packet
    print(f"\nNeed ~{packets_needed} packets (minimum 2 sec) for reliable analysis")
    print(f"Recommended: ~{int(np.ceil(312 * 3 / 10))} packets (4 sec) for best results")
    
    # Show what real-time usage looks like
    print("\n" + "="*70)
    print("REAL-TIME USAGE EXAMPLE")
    print("="*70)
    print("""
# Initialize buffer
buffer = EEGBuffer(buffer_duration=4.0, sampling_rate=78.0)

# In your Bluetooth receive loop:
while receiving_data:
    packet_hex = receive_bluetooth_packet()
    decoded = decode_serenibrain_packet(packet_hex)
    buffer.add_packet(decoded)
    
    # Check if we have enough data every ~1 second
    if buffer.is_ready_for_analysis():
        analysis = buffer.analyze_all_channels()
        print_eeg_analysis(analysis)
        
        # Or access specific metrics:
        if analysis:
            ch0_alpha = analysis[0]['band_ratios']['alpha']
            ch0_relaxation = analysis[0]['relaxation_score']
            print(f"Alpha: {ch0_alpha:.1f}%, Relaxation: {ch0_relaxation:.1f}")
""")
    
    # Show summary statistics for EEG data
    if decoded2['samples']:
        voltages = [s['voltage_uv'] for s in decoded2['samples']]
        print(f"\nOverall Voltage Statistics:")
        print(f"  Min: {min(voltages):.2f} µV")
        print(f"  Max: {max(voltages):.2f} µV")
        print(f"  Avg: {sum(voltages)/len(voltages):.2f} µV")
        print(f"  Range: {max(voltages) - min(voltages):.2f} µV")
        
        print(f"\nNote: The large DC offset (~-1800uV) is normal for EEG.")
        print(f"      Your app likely removes this offset for display.")
        print(f"      To match app display: subtract the average from each sample.")
