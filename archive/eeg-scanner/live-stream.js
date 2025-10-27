/**
 * Live EEG streaming from Serenibrain headband via Bluetooth LE
 * Node.js version using @abandonware/noble
 */

const noble = require('@abandonware/noble');
const { spawn } = require('child_process');
const path = require('path');

class EEGStreamProcessor {
    constructor(options = {}) {
        this.windowDuration = options.windowDuration || 6.0;
        this.samplingRate = options.samplingRate || 250.0;  // Device spec: 250 Hz
        this.adcScale = options.adcScale || 100.0;
        
        this.channelBuffers = new Map(); // channel -> array of {time, voltage}
        this.maxBufferSamples = Math.floor(this.windowDuration * this.samplingRate * 1.5);
        
        this.packetCount = 0;
        this.sampleCount = 0;
        this.startTime = null;
        this.lastAnalysisTime = new Map();
        this.analysisInterval = 2000; // ms
    }
    
    processPacket(data) {
        try {
            const packet = this.decodePacket(data);
            
            if (packet.packetType === 1) {
                console.log(`\n[Status] Device: ${packet.deviceModel || 'Unknown'}`);
                return;
            }
            
            if (packet.packetType !== 2 || !packet.samples || packet.samples.length === 0) {
                return;
            }
            
            this.packetCount++;
            const currentTime = Date.now();
            
            if (!this.startTime) {
                this.startTime = currentTime;
            }
            
            // Add samples to buffers
            for (const sample of packet.samples) {
                const ch = sample.channel;
                
                if (!this.channelBuffers.has(ch)) {
                    this.channelBuffers.set(ch, []);
                    this.lastAnalysisTime.set(ch, currentTime);
                }
                
                const buffer = this.channelBuffers.get(ch);
                buffer.push({ time: currentTime, voltage: sample.voltageUv });
                
                // Trim buffer if too large
                if (buffer.length > this.maxBufferSamples) {
                    buffer.shift();
                }
                
                this.sampleCount++;
            }
            
            // Check if analysis needed
            for (const [ch, lastTime] of this.lastAnalysisTime.entries()) {
                if (currentTime - lastTime >= this.analysisInterval) {
                    this.analyzeChannel(ch);
                    this.lastAnalysisTime.set(ch, currentTime);
                }
            }
            
            // Progress update
            if (this.packetCount % 10 === 0) {
                const elapsed = (currentTime - this.startTime) / 1000;
                const rate = this.packetCount / elapsed;
                console.log(`[${this.packetCount.toString().padStart(4)}  pkts] ${this.sampleCount.toString().padStart(5)} samples | ` +
                           `${rate.toFixed(1)} pkt/s | ${this.channelBuffers.size} channels`);
            }
            
        } catch (err) {
            console.error('Error processing packet:', err.message);
        }
    }
    
    decodePacket(data) {
        if (data.length < 12) {
            throw new Error(`Packet too short: ${data.length} bytes`);
        }
        
        const header = data.toString('ascii', 0, 4);
        const packetType = data[5];
        const numChannels = data[7];
        const payloadSize = data.readUInt32LE(8);
        
        const result = {
            header,
            packetType,
            numChannels,
            payloadSize,
            samples: []
        };
        
        if (packetType === 1) {
            result.deviceModel = data.toString('ascii', 12, 17).replace(/\0/g, '');
            return result;
        }
        
        if (packetType === 2) {
            let offset = 12;
            
            while (offset + 7 <= data.length - 10) {
                // Read 24-bit signed integer (little-endian)
                let value = data[offset] | (data[offset + 1] << 8) | (data[offset + 2] << 16);
                
                // Sign extension
                if (value & 0x800000) {
                    value = value - 0x1000000;
                }
                
                const sampleIdx = data.readUInt16LE(offset + 4);
                const channel = sampleIdx % numChannels;
                const voltageUv = value / this.adcScale;
                
                result.samples.push({
                    sampleNumber: result.samples.length,
                    sampleIndex: sampleIdx,
                    channel,
                    rawValue: value,
                    voltageUv,
                    rawHex: data.slice(offset, offset + 7).toString('hex')
                });
                
                offset += 7;
            }
        }
        
        return result;
    }
    
    analyzeChannel(channelId) {
        const buffer = this.channelBuffers.get(channelId);
        if (!buffer || buffer.length < 10) return;
        
        const voltages = buffer.map(s => s.voltage);
        const windowSamples = Math.floor(this.windowDuration * this.samplingRate);
        const dataToAnalyze = voltages.length > windowSamples 
            ? voltages.slice(-windowSamples)
            : voltages;
        
        if (dataToAnalyze.length < 10) return;
        
        // Simple FFT-free band power approximation (for demo)
        // In production, use the Python script or a JS FFT library
        const mean = dataToAnalyze.reduce((a, b) => a + b, 0) / dataToAnalyze.length;
        const variance = dataToAnalyze.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / dataToAnalyze.length;
        const std = Math.sqrt(variance);
        
        console.log(`\n${'='.repeat(70)}`);
        console.log(`Channel ${channelId} Analysis (${dataToAnalyze.length} samples)`);
        console.log(`${'='.repeat(70)}`);
        console.log(`Mean: ${mean.toFixed(2)} µV | Std: ${std.toFixed(2)} µV | Variance: ${variance.toFixed(2)}`);
        console.log(`Use Python script for detailed band power analysis`);
    }
}

async function scanForDevice(timeout = 10000) {
    return new Promise((resolve, reject) => {
        console.log(`Scanning for Serenibrain device (timeout: ${timeout/1000}s)...`);
        
        const devices = [];
        const timeoutHandle = setTimeout(() => {
            noble.stopScanning();
            
            console.log('\nAvailable devices:');
            devices.forEach(d => {
                console.log(`  ${d.advertisement.localName || 'Unknown'} - ${d.address}`);
            });
            
            const target = devices.find(d => {
                const name = (d.advertisement.localName || '').toLowerCase();
                return name.includes('serenibrain') || name.includes('th21a') || name.includes('eeg');
            });
            
            resolve(target);
        }, timeout);
        
        noble.on('discover', (peripheral) => {
            devices.push(peripheral);
            const name = peripheral.advertisement.localName || 'Unknown';
            if (name.toLowerCase().includes('serenibrain') || 
                name.toLowerCase().includes('th21a') ||
                name.toLowerCase().includes('eeg')) {
                console.log(`Found device: ${name} (${peripheral.address})`);
                clearTimeout(timeoutHandle);
                noble.stopScanning();
                resolve(peripheral);
            }
        });
        
        noble.startScanning([], false);
    });
}

async function streamEEGData(peripheral, duration = null) {
    const processor = new EEGStreamProcessor({
        windowDuration: 6.0,
        samplingRate: 250.0,  // Device specification: 250 Hz
        adcScale: 100.0
    });
    
    // Stream control commands (discovered from BT log analysis)
    const CMD_START_STREAM = Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x05]); // "CTRL" + start
    const CMD_STOP_STREAM = Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x03, 0x00, 0x03]);  // "CTRL" + stop
    const CMD_KEEP_ALIVE = Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x05, 0x00, 0x02]);   // "CTRL" + keepalive
    const CMD_ALT_START = Buffer.from([0x43, 0x54, 0x52, 0x4C, 0x00, 0x04, 0x00, 0x01]);    // Alternative start
    
    return new Promise(async (resolve, reject) => {
        try {
            console.log(`\nConnecting to ${peripheral.advertisement.localName || peripheral.address}...`);
            
            await peripheral.connectAsync();
            console.log('Connected!');
            
            const { services, characteristics } = await peripheral.discoverAllServicesAndCharacteristicsAsync();
            
            // Find notify and write characteristics
            let notifyChar = null;
            let writeChar = null;
            
            for (const char of characteristics) {
                if (char.properties.includes('notify')) {
                    notifyChar = char;
                    console.log(`Found notify characteristic: ${char.uuid}`);
                }
                if (char.properties.includes('write') || char.properties.includes('writeWithoutResponse')) {
                    writeChar = char;
                    console.log(`Found write characteristic: ${char.uuid}`);
                }
            }
            
            if (!notifyChar) {
                throw new Error('No notification characteristic found');
            }
            
            // Subscribe to notifications
            notifyChar.on('data', (data) => {
                processor.processPacket(data);
            });
            
            await notifyChar.subscribeAsync();
            console.log('[OK] Subscribed to notifications');
            
            // Send START command to trigger streaming
            if (writeChar) {
                console.log('\nSending START command...');
                try {
                    await writeChar.writeAsync(CMD_START_STREAM, false);
                    console.log('[OK] START command sent: CTRL 00 03 00 05');
                } catch (err) {
                    console.log(`Warning: Could not send START command: ${err.message}`);
                }
            } else {
                console.log('Warning: No write characteristic found - device may auto-stream');
            }
            
            console.log(`\n${'='.repeat(70)}`);
            console.log('STREAMING EEG DATA - Press Ctrl+C to stop');
            console.log(`${'='.repeat(70)}\n`);
            
            // Wait a moment for data
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Check if we're receiving data
            if (processor.packetCount === 0 && writeChar) {
                console.log('[!] No packets received, trying alternative START command...');
                try {
                    await writeChar.writeAsync(CMD_ALT_START, false);
                    console.log('[OK] Alternative START sent: CTRL 00 04 00 01');
                    await new Promise(resolve => setTimeout(resolve, 2000));
                } catch (err) {
                    console.log(`Could not send alternative command: ${err.message}`);
                }
            }
            
            if (processor.packetCount === 0) {
                console.log('[!] Still no data - continuing to wait...');
            }
            
            // Optional: Keep-alive loop (send every 1 second)
            let keepAliveInterval = null;
            if (writeChar && processor.packetCount > 0) {
                keepAliveInterval = setInterval(async () => {
                    try {
                        await writeChar.writeAsync(CMD_KEEP_ALIVE, false);
                    } catch (err) {
                        // Ignore errors
                    }
                }, 1000);
                console.log('[OK] Keep-alive enabled (1s interval)');
            }
            
            // Cleanup function
            const cleanup = async () => {
                console.log('\n\nStopping stream...');
                
                if (keepAliveInterval) {
                    clearInterval(keepAliveInterval);
                }
                
                // Send STOP command
                if (writeChar) {
                    try {
                        await writeChar.writeAsync(CMD_STOP_STREAM, false);
                        console.log('[OK] STOP command sent');
                    } catch (err) {
                        // Ignore
                    }
                }
                
                await notifyChar.unsubscribeAsync();
                await peripheral.disconnectAsync();
            };
            
            // Handle duration or run indefinitely
            if (duration) {
                setTimeout(async () => {
                    await cleanup();
                    resolve();
                }, duration * 1000);
            } else {
                // Handle Ctrl+C
                process.on('SIGINT', async () => {
                    await cleanup();
                    process.exit(0);
                });
            }
            
        } catch (err) {
            reject(err);
        }
    });
}

// Main
async function main() {
    const args = process.argv.slice(2);
    const scanOnly = args.includes('--scan-only');
    
    noble.on('stateChange', async (state) => {
        if (state === 'poweredOn') {
            try {
                const device = await scanForDevice(10000);
                
                if (scanOnly) {
                    process.exit(0);
                    return;
                }
                
                if (!device) {
                    console.log('\nNo Serenibrain device found!');
                    process.exit(1);
                    return;
                }
                
                await streamEEGData(device);
                
            } catch (err) {
                console.error('Error:', err);
                process.exit(1);
            }
        } else {
            console.log('Bluetooth not ready. State:', state);
        }
    });
}

main();
