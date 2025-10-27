#!/usr/bin/env node
// eeg_analyze.js
// Read a log (nRF Connect export or scan_notifications.log), extract hex notification
// payloads and try several decoding heuristics to help reverse-engineer the packet.

const fs = require('fs');
const path = require('path');

function hexToBuffer(hex) {
  const cleaned = hex.replace(/[^0-9a-fA-F]/g, '');
  return Buffer.from(cleaned, 'hex');
}

function toFloat32LE(buf, offset) {
  try { return buf.readFloatLE(offset); } catch (e) { return null; }
}

function toInt16LE(buf, offset) {
  try { return buf.readInt16LE(offset); } catch (e) { return null; }
}

function stats(arr) {
  const n = arr.length;
  if (n === 0) return {};
  const mean = arr.reduce((s,x)=>s+x,0)/n;
  const sd = Math.sqrt(arr.reduce((s,x)=>s+(x-mean)*(x-mean),0)/n);
  return {n, mean, sd};
}

function tryDecodeFloat32s(buf, align=0, max=12) {
  const out = [];
  for (let off=align; off+4 <= buf.length && out.length < max; off+=4) {
    const v = toFloat32LE(buf, off);
    if (v === null) break;
    out.push(v);
  }
  return out;
}

function tryDecodeInt16s(buf, align=0, max=24) {
  const out = [];
  for (let off=align; off+2 <= buf.length && out.length < max; off+=2) {
    const v = toInt16LE(buf, off);
    if (v === null) break;
    out.push(v);
  }
  return out;
}

function tryDecodePairsFloat32Uint16(buf, align=0, max=8) {
  const out = [];
  let off = align;
  while (off + 6 <= buf.length && out.length < max) {
    const f = toFloat32LE(buf, off);
    const u = buf.readUInt16LE(off+4);
    out.push([f,u]);
    off += 6;
  }
  return out;
}

function extractHexes(text) {
  const regex = /([0-9A-Fa-f]{2}(?:[- ]?[0-9A-Fa-f]{2})+)/g;
  const matches = [];
  let m;
  while ((m = regex.exec(text)) !== null) {
    // filter out too short matches
    const hex = m[1];
    if (hex.replace(/[^0-9a-fA-F]/g,'').length >= 8) matches.push(hex);
  }
  return matches;
}

function findDATAblocks(buf) {
  const sig = Buffer.from('44415441','hex'); // 'DATA'
  const idxs = [];
  for (let i=0;i+sig.length<=buf.length;i++) {
    let ok = true;
    for (let j=0;j<sig.length;j++) if (buf[i+j] !== sig[j]) { ok=false; break; }
    if (ok) idxs.push(i);
  }
  return idxs;
}

// Main
const input = process.argv[2] || path.join(__dirname, 'log.txt');
if (!fs.existsSync(input)) {
  console.error('Input file not found:', input);
  process.exit(1);
}

const raw = fs.readFileSync(input, 'utf8');
const hexes = extractHexes(raw);
if (hexes.length === 0) {
  console.error('No hex payloads found in input. Make sure you exported a raw log from nRF Connect or used scan_notifications.log.');
  process.exit(1);
}

console.log('Found', hexes.length, 'hex blobs. Showing analysis for the first 8 blobs.');

for (let i=0;i<Math.min(8, hexes.length); i++) {
  const hex = hexes[i].replace(/[^0-9a-fA-F]/g,'');
  const buf = Buffer.from(hex,'hex');
  console.log('--- Blob', i+1, 'len=', buf.length);
  // find DATA signature inside
  const idxs = findDATAblocks(buf);
  if (idxs.length>0) {
    console.log('  Found DATA signature at offsets:', idxs);
  }
  // show raw prefix
  console.log('  raw hex prefix:', buf.slice(0,40).toString('hex'));

  // Try float32 decodings with different alignments
  for (let align=0; align<4; align++) {
    const floats = tryDecodeFloat32s(buf, align, 10);
    if (floats.length>0) {
      const s = stats(floats.filter(f=>Number.isFinite(f)));
      console.log(`  float32 align=${align} -> n=${floats.length} sample[0..4]=${floats.slice(0,5).map(x=>x.toFixed(6))} stats=${JSON.stringify(s)}`);
    }
  }

  // Try int16
  for (let align=0; align<2; align++) {
    const ints = tryDecodeInt16s(buf, align, 12);
    if (ints.length>0) {
      const s = stats(ints);
      console.log(`  int16 align=${align} -> n=${ints.length} sample[0..6]=${ints.slice(0,7)} stats=${JSON.stringify(s)}`);
    }
  }

  // Try float32+uint16 pairs
  for (let align=0; align<3; align++) {
    const pairs = tryDecodePairsFloat32Uint16(buf, align, 8);
    if (pairs.length>0) {
      console.log(`  float32+u16 align=${align} -> n=${pairs.length} first=${pairs.slice(0,4).map(p=>`[${p[0].toFixed(6)},${p[1]}]`)}`);
    }
  }

}

console.log('\nHeuristics complete. If you want, run with a single hex blob (full payload) as input:');
console.log('  node eeg_analyze.js path/to/your_blob.txt');

console.log('\nNext steps: if one decoding looks plausible (float32 arrays with small magnitudes), I can create a parser that extracts channel streams and writes CSV or starts a websocket server. Paste one representative hex blob here if you want me to parse it now.');
