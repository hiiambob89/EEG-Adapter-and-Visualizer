"""
Quick test of packet decoding and band power calculation
"""

from process import decode_serenibrain_packet, calculate_band_powers, print_decoded_packet, analyze_eeg_packet, print_eeg_analysis

# Test packets from your logs
packet1 = "44-41-54-41-00-01-00-03-20-00-00-00-54-48-32-31-41-00-00-00-00-00-00-01-00-00-00-01-00-00-00-0A-00-00-00-02-00-00-00-18-00-00-00-0C"
packet2 = "44-41-54-41-00-02-00-03-50-00-00-00-D1-3E-FD-00-00-00-00-7C-3E-FD-00-00-01-00-B6-3E-FD-00-00-02-00-8C-3E-FD-00-00-03-00-7A-3E-FD-00-00-04-00-8B-3E-FD-00-00-05-00-BF-3E-FD-00-00-06-00-B6-3E-FD-00-00-07-00-7E-3E-FD-00-00-08-00-99-3E-FD-00-00-09-00-21-10-E0-71-C6-87-F6-41-00-00"

print("="*70)
print("TESTING PACKET DECODER")
print("="*70)

print("\n### Test 1: Status Packet ###")
decoded1 = decode_serenibrain_packet(packet1, adc_scale=100.0)
print_decoded_packet(decoded1)

print("\n### Test 2: EEG Data Packet ###")
decoded2 = decode_serenibrain_packet(packet2, adc_scale=100.0)
print_decoded_packet(decoded2)

print("\n### Test 3: Band Power Analysis ###")
analysis = analyze_eeg_packet(decoded2)
if analysis:
    print_eeg_analysis(analysis)
else:
    print("Not enough samples in single packet for full analysis")
    print("(This is normal - live streaming accumulates packets)")

print("\n### Test 4: Updated calculate_band_powers with Welch ###")
if decoded2['samples']:
    ch0_samples = [s['voltage_uv'] for s in decoded2['samples'] if s['channel'] == 0]
    if len(ch0_samples) >= 10:
        try:
            # Test with Welch (250 Hz sampling rate - device spec)
            result_welch = calculate_band_powers(ch0_samples, sampling_rate=250.0, use_welch=True)
            print(f"\nWelch method - Channel 0 (250 Hz):")
            print(f"  Delta: {result_welch['band_ratios']['delta']:.1f}%")
            print(f"  Theta: {result_welch['band_ratios']['theta']:.1f}%")
            print(f"  Alpha: {result_welch['band_ratios']['alpha']:.1f}%")
            print(f"  SNR: {result_welch['snr_db']:.1f} dB")
            
            # Test with FFT
            result_fft = calculate_band_powers(ch0_samples, sampling_rate=250.0, use_welch=False)
            print(f"\nFFT method - Channel 0 (250 Hz):")
            print(f"  Delta: {result_fft['band_ratios']['delta']:.1f}%")
            print(f"  Theta: {result_fft['band_ratios']['theta']:.1f}%")
            print(f"  Alpha: {result_fft['band_ratios']['alpha']:.1f}%")
            print(f"  SNR: {result_fft['snr_db']:.1f} dB")
            
        except Exception as e:
            print(f"Error in band calculation: {e}")

print("\n" + "="*70)
print("ALL TESTS COMPLETE")
print("="*70)
print("\nReady for live streaming!")
print("\nRun: python live_eeg_stream.py")
print("Or:  python live_eeg_stream.py --scan-only")
print("="*70)
