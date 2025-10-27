// adapters/node.js
// Thin wrapper that exports the existing noble module. This require may fail
// if native modules haven't been built; the top-level loader handles fallback.
try {
  module.exports = require('@abandonware/noble');
} catch (e) {
  // rethrow so caller can decide to fallback
  throw e;
}
