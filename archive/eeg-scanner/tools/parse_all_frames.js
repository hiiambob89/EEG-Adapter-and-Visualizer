#!/usr/bin/env node
'use strict';

// Scan log.txt for DATA frames and produce a JSONL file with parsed fields
// Outputs: tools/frames.jsonl

const fs = require('fs');
const path = require('path');

const logPath = path.join(__dirname, '..', 'log.txt');
const outPath = path.join(__dirname, 'frames.jsonl');
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

function cleanHex(s) { return s.replace(/[^0-9A-Fa-f]/g, ''); }
function findAsciiRuns(buf) {
  const runs = [];
  let i = 0;
  while (i < buf.length) {
    while (i < buf.length && buf[i] === 0) i++;
    let j = i;
    while (j < buf.length && buf[j] >= 0x20 && buf[j] <= 0x7E) j++;
    if (j > i) runs.push({offset: i, str: buf.toString('ascii', i, j)});
    i = j + 1;
  }
  return runs;
}

function extractNumbers(buf) {
  const uint32 = [];
  const float32 = [];
  const int16 = [];
  for (let off = 0; off + 4 <= buf.length; off += 4) {
    uint32.push({offset: off, value: buf.readUInt32LE(off)});
    try { float32.push({offset: off, value: buf.readFloatLE(off)}); } catch (e) { float32.push({offset: off, value: null}); }
  }
  for (let off = 0; off + 2 <= buf.length; off += 2) {
    int16.push({offset: off, s: buf.readInt16LE(off), u: buf.readUInt16LE(off)});
  }
  return {uint32, float32, int16};
}

// We'll write one JSON object per frame
const out = fs.createWriteStream(outPath, {flags: 'w'});

matches.forEach((m, idx) => {
  const cleaned = cleanHex(m);
  if (cleaned.length % 2 !== 0) {
    console.warn('Skipping odd-length hex at match', idx);
    return;
  }
  const buf = Buffer.from(cleaned, 'hex');
  const header = buf.length >= 4 ? buf.toString('ascii', 0, 4) : null;
  const asciiRuns = findAsciiRuns(buf);
  const numbers = extractNumbers(buf);

  // Heuristics: try to guess payload area (after header and first NUL run)
  let device = null;
  if (asciiRuns.length > 0) {
    // prefer the first printable run that's not 'DATA'
    const c = asciiRuns.find(r => r.str && r.str !== 'DATA');
    if (c) device = c.str;
  }

  const obj = {
    index: idx,
    bytes: buf.length,
    header,
    device,
    hex: buf.toString('hex'),
    asciiRuns,
    uint32: numbers.uint32,
    float32: numbers.float32,
    int16: numbers.int16
  };

  out.write(JSON.stringify(obj) + '\n');
});

out.end(() => {
  console.log('Wrote', outPath, 'with', matches.length, 'frames');
  // Print a short summary of the first frame for quick inspection
  const lines = fs.readFileSync(outPath, 'utf8').trim().split(/\r?\n/);
  if (lines.length > 0) {
    const first = JSON.parse(lines[0]);
    console.log('\nFirst frame summary:');
    console.log(' index:', first.index);
    console.log(' bytes:', first.bytes);
    console.log(' header:', first.header);
    console.log(' device (heuristic):', first.device);
    console.log(' asciiRuns:', first.asciiRuns.map(r=>`${r.offset}:${r.str}`).join(' | '));
    console.log(' uint32 sample (first 6):', first.uint32.slice(0,6).map(x=>`@${x.offset}:${x.value}`));
    console.log(' float32 sample (first 6):', first.float32.slice(0,6).map(x=>`@${x.offset}:${x.value}`));
  }
});
