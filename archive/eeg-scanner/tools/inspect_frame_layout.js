#!/usr/bin/env node
'use strict';

// Inspect int16 layout of a representative frame (prefer 92-byte frames)
// Prints int16 at each 2-byte offset and shows candidate offsets across first N frames.

const fs = require('fs');
const path = require('path');

const framesPath = path.join(__dirname, 'frames.jsonl');
if (!fs.existsSync(framesPath)) { console.error('Missing', framesPath); process.exit(2); }
const lines = fs.readFileSync(framesPath,'utf8').trim().split(/\r?\n/).filter(Boolean);
const frames = lines.map(l=>JSON.parse(l));

// prefer a frame with bytes==92
let rep = frames.find(f=>f.bytes===92) || frames[0];
const repBuf = Buffer.from(rep.hex,'hex');
console.log('Representative frame index', rep.index, 'bytes', rep.bytes);

console.log('\nInt16 values in representative frame:');
for (let off=0; off+2<=repBuf.length; off+=2) {
  const v = repBuf.readInt16LE(off);
  process.stdout.write(off.toString().padStart(3)+' : '+v.toString().padStart(7));
  if ((off/2+1) % 4 === 0) process.stdout.write('\n'); else process.stdout.write('  ');
}

// Candidate offsets from prior analysis (common top int16 offsets found)
const candidates = [18,60,72,58,44,30];
const showFrames = Math.min(20, frames.length);
console.log('\n\nShowing candidate offsets across first', showFrames, 'frames:');
process.stdout.write('frame'.padStart(6));
candidates.forEach(o => process.stdout.write(('off_'+o).padStart(12)));
process.stdout.write('\n');
for (let i=0;i<showFrames;i++){
  const f = frames[i];
  const buf = Buffer.from(f.hex,'hex');
  process.stdout.write(String(i).padStart(6));
  candidates.forEach(o=>{
    const val = (o+2<=buf.length) ? buf.readInt16LE(o) : NaN;
    process.stdout.write(String(val).padStart(12));
  });
  process.stdout.write('\n');
}

// Try to detect grouping: see if consecutive groups of 3 int16 values appear repeatedly
console.log('\nAttempting grouping detection (look for stride of 6 bytes per sample, 3 channels):');
const maxOff = repBuf.length - 6;
for (let start=0; start<=maxOff; start+=2) {
  // check first 3 groups (samples) at start, start+6, start+12
  if (start+12 > repBuf.length) break;
  const g1 = [repBuf.readInt16LE(start), repBuf.readInt16LE(start+2), repBuf.readInt16LE(start+4)];
  const g2 = [repBuf.readInt16LE(start+6), repBuf.readInt16LE(start+8), repBuf.readInt16LE(start+10)];
  const g3 = (start+18<=repBuf.length) ? [repBuf.readInt16LE(start+12), repBuf.readInt16LE(start+14), repBuf.readInt16LE(start+16)] : null;
  // simple heuristic: groups look non-zero and similar magnitude
  const nonZero = arr=>arr.every(x=>x!==0);
  if (nonZero(g1) && nonZero(g2) && g3 && nonZero(g3)) {
    console.log('Possible 3x-sample groups starting at offset', start, 'groups:', g1, g2, g3);
  }
}

console.log('\nDone. If you want, I can extract all candidate groups across every frame and reconstruct multi-channel time series.');
