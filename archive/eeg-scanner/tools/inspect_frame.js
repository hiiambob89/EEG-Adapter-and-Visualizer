#!/usr/bin/env node
'use strict';

// Small helper to inspect a DATA frame hex payload.
// Usage:
//   node tools/inspect_frame.js            # uses embedded example from log
//   node tools/inspect_frame.js <hex...>   # provide hex string (dashes/spaces allowed)

const controlNames = {
  0x00: 'NUL', 0x01: 'SOH', 0x02: 'STX', 0x03: 'ETX', 0x04: 'EOT', 0x05: 'ENQ', 0x06: 'ACK',
  0x07: 'BEL', 0x08: 'BS',  0x09: 'TAB', 0x0A: 'LF',  0x0B: 'VT',  0x0C: 'FF',  0x0D: 'CR',
  0x10: 'DLE', 0x11: 'DC1', 0x12: 'DC2', 0x13: 'DC3', 0x14: 'DC4', 0x18: 'CAN'
};

function cleanHex(s) {
  return s.replace(/[^0-9A-Fa-f]/g, '');
}

// Example payload from log.txt (the short one the user converted)
const example = '44-41-54-41-00-01-00-03-20-00-00-00-54-48-32-31-41-00-00-00-00-00-00-01-00-00-00-01-00-00-00-0A-00-00-00-02-00-00-00-18-00-00-00-0C';

const arg = process.argv[2];
const hexInput = arg ? arg : example;
const cleaned = cleanHex(hexInput);
if (cleaned.length % 2 !== 0) {
  console.error('Provided hex has odd length. Input:', hexInput);
  process.exit(2);
}
const buf = Buffer.from(cleaned, 'hex');

function escapedView(b) {
  return Array.from(b).map(x => {
    if (x >= 0x20 && x <= 0x7E) return String.fromCharCode(x);
    return '\\x' + x.toString(16).padStart(2, '0');
  }).join('');
}

console.log('Using payload (hex):', buf.toString('hex').match(/.{1,2}/g).join(' '));
console.log('Length:', buf.length, 'bytes');
console.log('\nEscaped view (printable chars shown, controls as \\xNN):');
console.log(escapedView(buf));

// Find zero-terminated / contiguous printable ASCII runs
function findAsciiRuns(b) {
  const runs = [];
  let i = 0;
  while (i < b.length) {
    while (i < b.length && b[i] === 0) i++;
    let j = i;
    while (j < b.length && b[j] >= 0x20 && b[j] <= 0x7E) j++;
    if (j > i) runs.push({offset: i, str: b.toString('ascii', i, j)});
    i = j + 1;
  }
  return runs;
}

const runs = findAsciiRuns(buf);
console.log('\nASCII runs found:');
if (runs.length === 0) console.log('  (none)');
runs.forEach(r => console.log('  @' + r.offset + ':', r.str));

// Show 32-bit little-endian ints (common in these frames)
console.log('\n32-bit LE uints at 4-byte aligned offsets:');
for (let off = 0; off + 4 <= buf.length; off += 4) {
  const v = buf.readUInt32LE(off);
  console.log('  @' + off.toString().padStart(3, ' ') + ':', v, '(0x' + v.toString(16) + ')');
}

// Show 16-bit (signed/unsigned) at 2-byte aligned offsets as extra info
console.log('\n16-bit LE (signed / unsigned) at 2-byte aligned offsets:');
for (let off = 0; off + 2 <= buf.length; off += 2) {
  const s = buf.readInt16LE(off);
  const u = buf.readUInt16LE(off);
  console.log('  @' + off.toString().padStart(3, ' ') + ':', s.toString().padStart(6,' '), '/', u.toString().padStart(6,' '));
}

// Print byte table with control names
console.log('\nByte table: index hex dec char/control');
for (let i = 0; i < buf.length; i++) {
  const b = buf[i];
  const ch = (b >= 0x20 && b <= 0x7E) ? String.fromCharCode(b) : (controlNames[b] || ('\\x' + b.toString(16).padStart(2,'0')));
  console.log(i.toString().padStart(3,' '), ' ', b.toString(16).padStart(2,'0'), ' ', b.toString().padStart(3,' '), ' ', ch);
}

// Small heuristic parse: header + optional device string + sequence of uint32 values
if (buf.length >= 4) {
  const hdr = buf.toString('ascii', 0, 4);
  console.log('\nHeuristic parse:');
  console.log('  header:', hdr);
  // try to find printable device id after some zeros
  const maybeDevice = runs.find(r => r.str && r.str.length >= 3);
  if (maybeDevice) console.log('  device/string:', maybeDevice.str, '@' + maybeDevice.offset);

  // After header, scan for 4-byte LE uints and list them as fields (skip the header area)
  const fields = [];
  for (let off = 4; off + 4 <= buf.length; off += 4) {
    fields.push({offset: off, value: buf.readUInt32LE(off)});
  }
  console.log('  fields (uint32 LE):', fields.map(f => `@${f.offset}:${f.value}`).join(' '));
}

console.log('\nDone. If you want JSON output or a different endianness/sizes, rerun with a hex argument or ask me to adapt the script.');
