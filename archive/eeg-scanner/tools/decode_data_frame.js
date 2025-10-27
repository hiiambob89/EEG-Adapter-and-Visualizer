const fs = require('fs');
const path = require('path');

const logPath = path.join(__dirname, '..', 'log.txt');
const txt = fs.readFileSync(logPath, 'utf8');

// Find all occurrences that contain the DATA signature (44-41-54-41)
const reAll = /\(0x\)\s*([0-9A-Fa-f\- ]*44-41-54-41[0-9A-Fa-f\- ]*)/gm;
let match;
const matches = [];
while ((match = reAll.exec(txt)) !== null) {
  matches.push(match[1].trim());
}
if (matches.length === 0) {
  console.error('No DATA frame found in log.txt');
  process.exit(2);
}

// Pick the longest payload (most bytes) - usually the sensor frames are longer
matches.sort((a, b) => b.replace(/[^0-9A-Fa-f]/g, '').length - a.replace(/[^0-9A-Fa-f]/g, '').length);
const hexStr = matches[0].replace(/\s+/g, '');
// hexStr currently like 44-41-54-41... possibly with dashes; remove non-hex
const cleaned = hexStr.replace(/[^0-9A-Fa-f]/g, '');
if (cleaned.length % 2 !== 0) {
  console.error('Odd-length hex payload, aborting');
  process.exit(3);
}

const buf = Buffer.from(cleaned, 'hex');
console.log('Found DATA frame, byteLength =', buf.length);
console.log('Hex:', buf.toString('hex').match(/.{1,2}/g).join(' '));

// Print byte-by-byte with offsets
console.log('\nBytes (offset: hex):');
for (let i = 0; i < buf.length; i += 16) {
  const slice = buf.slice(i, i + 16);
  const hex = slice.toString('hex').match(/.{1,2}/g).join(' ');
  console.log(i.toString().padStart(3, ' '), ':', hex);
}

// ASCII header
const header = buf.slice(0, 4).toString('ascii');
console.log('\nHeader ASCII:', header);

// Try decoding float32 LE at every 4-byte aligned offset >=4
console.log('\nfloat32 LE at 4-byte-aligned offsets (offset, value):');
for (let off = 4; off + 4 <= buf.length; off += 4) {
  try {
    const v = buf.readFloatLE(off);
    // show values that look reasonable or all (we'll show all but format)
    console.log(off.toString().padStart(3, ' '), ':', v.toFixed(6));
  } catch (e) {
    // ignore
  }
}

// Try decoding int16 LE at every 2-byte aligned offset >=4
console.log('\nint16 LE at 2-byte-aligned offsets (offset, value):');
for (let off = 4; off + 2 <= buf.length; off += 2) {
  const v = buf.readInt16LE(off);
  const u = buf.readUInt16LE(off);
  console.log(off.toString().padStart(3, ' '), ':', v.toString().padStart(6, ' '), '(u:', u.toString().padStart(6, ' '), ')');
}

// Show last 12 bytes as possible footer metadata
const foot = buf.slice(Math.max(0, buf.length - 12));
console.log('\nLast 12 bytes (possible footer):', foot.toString('hex').match(/.{1,2}/g).join(' '));

console.log('\nFull buffer for further offline analysis available at tools/decode_data_frame.js');
