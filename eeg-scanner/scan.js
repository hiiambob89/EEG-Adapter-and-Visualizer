// scan.js - improved BLE scanner + notifier logger
const noble = require('@abandonware/noble');
const fs = require('fs');
const LOG_FILE = __dirname + '/scan_notifications.log';

// Target device address (TH21A) - override with env TARGET_ADDR if needed
const TARGET_ADDR = (process.env.TARGET_ADDR || 'f6:82:59:5d:cc:5d').toLowerCase();
let connectedPeripheral = null;

async function startScan() {
  try {
    await noble.startScanningAsync([], true);
    console.log('Started scanning (allowDuplicates=true)');
  } catch (err) {
    console.error('Failed to start scanning:', err);
  }
}

noble.on('stateChange', async (state) => {
  console.log('BLE state:', state);
  if (state === 'poweredOn') {
    await startScan();
  } else {
    try { await noble.stopScanningAsync(); } catch (e) {}
    console.log('Stopped scanning');
  }
});

process.on('SIGINT', async () => {
  console.log('\nSIGINT received — shutting down');
  try {
    if (connectedPeripheral && connectedPeripheral.state === 'connected') {
      await connectedPeripheral.disconnectAsync();
      console.log('Disconnected from peripheral');
    }
    await noble.stopScanningAsync();
  } catch (e) {}
  process.exit(0);
});

noble.on('discover', async (peripheral) => {
  try {
    const adv = peripheral.advertisement || {};
    const name = adv.localName || 'unknown';
    const id = (peripheral.address || peripheral.id || '').toLowerCase();
    console.log(`Discovered: ${name} [${id}] RSSI=${peripheral.rssi}`);
    console.log('  ManufacturerData:', adv.manufacturerData ? adv.manufacturerData.toString('hex') : null);
    console.log('  ServiceUUIDs:', adv.serviceUuids);

    const isTarget = id && id === TARGET_ADDR;
    const looksLikeTarget = name && name.toLowerCase().includes('th21a');

    if (isTarget || looksLikeTarget) {
      console.log('==> Target device found:', name, id);
      // Stop scanning while we connect
      try { await noble.stopScanningAsync(); } catch (e) {}

      peripheral.on('disconnect', async () => {
        console.log('Disconnected from', id);
        connectedPeripheral = null;
        // Restart scanning so we can reconnect or pick up new devices
        await startScan();
      });

      try {
        console.log('Connecting to', id);
        await peripheral.connectAsync();
        connectedPeripheral = peripheral;
        console.log('Connected. Discovering services/characteristics...');

        const { services, characteristics } = await peripheral.discoverAllServicesAndCharacteristicsAsync();
        services.forEach(s => console.log('Service:', s.uuid));
        characteristics.forEach(c => console.log('  Char:', c.uuid, 'props=', c.properties));

        // Subscribe to notification characteristics (try all notify/indicate)
        for (const c of characteristics) {
          if (c.properties.includes('notify') || c.properties.includes('indicate')) {
            console.log('Subscribing to', c.uuid);
            c.on('data', (data, isNotification) => {
              const hex = data.toString('hex');
              const ts = new Date().toISOString();
              const line = `${ts} NOTIFY ${c.uuid} | ${hex} | len=${data.length}\n`;
              console.log(line.trim());
              try {
                fs.appendFileSync(LOG_FILE, line);
              } catch (e) {
                console.warn('Failed to append to log file:', e.message);
              }
            });
            try { await c.subscribeAsync(); } catch (e) { console.warn('Subscribe failed for', c.uuid, e.message); }
          }
        }

        console.log('Ready — waiting for notifications. Press Ctrl+C to exit.');
      } catch (err) {
        console.error('Connect/discover error:', err);
        try { await peripheral.disconnectAsync(); } catch (e) {}
        connectedPeripheral = null;
        await startScan();
      }
    }
  } catch (err) {
    console.error('Discover handler error:', err);
  }
});