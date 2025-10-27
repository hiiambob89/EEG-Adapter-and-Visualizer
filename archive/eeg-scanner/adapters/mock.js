// adapters/mock.js
// Development mock adapter that implements a small subset of the noble API
// used by scan.js. Emits a fake peripheral with a single notifying characteristic.
const EventEmitter = require('events');

class MockCharacteristic extends EventEmitter {
  constructor(uuid) {
    super();
    this.uuid = uuid || '0000ff01-0000-1000-8000-00805f9b34fb';
    this.properties = ['notify'];
    this._interval = null;
  }

  async subscribeAsync() {
    // emit random data every 1s
    if (this._interval) return;
    this._interval = setInterval(() => {
      const buf = Buffer.from(Array.from({ length: 8 }, () => Math.floor(Math.random() * 256)));
      // deliver as notification (isNotification = true)
      this.emit('data', buf, true);
    }, 1000);
  }

  async unsubscribeAsync() {
    if (this._interval) {
      clearInterval(this._interval);
      this._interval = null;
    }
  }
}

class MockPeripheral extends EventEmitter {
  constructor(id, name) {
    super();
    this.id = id || 'mock-01';
    this.address = this.id;
    this.rssi = -42;
    this.advertisement = {
      localName: name || 'TH21A-mock',
      manufacturerData: Buffer.from('0102030405060708', 'hex'),
      serviceUuids: []
    };
    this.state = 'disconnected';
  }

  async connectAsync() {
    this.state = 'connected';
    // small delay
    await new Promise(r => setTimeout(r, 50));
    return;
  }

  async disconnectAsync() {
    this.state = 'disconnected';
    this.emit('disconnect');
  }

  async discoverAllServicesAndCharacteristicsAsync() {
    // return simple arrays that match what scan.js expects
    const char = new MockCharacteristic();
    return { services: [{ uuid: 'mock-svc-01' }], characteristics: [char] };
  }
}

class MockAdapter extends EventEmitter {
  constructor() {
    super();
    this._scanning = false;
    this._discoverInterval = null;
  }

  async startScanningAsync(serviceUUIDs = [], allowDuplicates = false) {
    if (this._scanning) return;
    this._scanning = true;
    // emit poweredOn state and then start emitting discover events
    process.nextTick(() => this.emit('stateChange', 'poweredOn'));

    this._discoverInterval = setInterval(() => {
      const p = new MockPeripheral('f6:82:59:5d:cc:5d', 'TH21A-mock');
      // emit a single discover
      this.emit('discover', p);
    }, 1500);
  }

  async stopScanningAsync() {
    if (!this._scanning) return;
    this._scanning = false;
    if (this._discoverInterval) {
      clearInterval(this._discoverInterval);
      this._discoverInterval = null;
    }
    this.emit('stateChange', 'poweredOff');
  }
}

// Export a single adapter instance to mimic noble's EventEmitter export
module.exports = new MockAdapter();
