// ble-adapter.js
// Thin loader: prefer a platform-specific node adapter, fall back to a local mock
const tryRequire = (p) => {
  try {
    return require(p);
  } catch (e) {
    return null;
  }
};

let impl = null;

// Try the Node adapter (which will re-export @abandonware/noble). If it fails
// (native module missing), fall back to the mock adapter so development can continue.
impl = tryRequire('./adapters/node') || tryRequire('./adapters/mock');

if (!impl) {
  throw new Error('No BLE adapter available (tried node and mock)');
}

module.exports = impl;
