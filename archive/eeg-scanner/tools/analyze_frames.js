#!/usr/bin/env node
'use strict';

// Analyze tools/frames.jsonl (created by parse_all_frames.js)
// Produce summary of frame lengths, device counts, and per-offset variability

const fs = require('fs');
const path = require('path');

const framesPath = path.join(__dirname, 'frames.jsonl');
if (!fs.existsSync(framesPath)) {
  console.error('Missing', framesPath, '- run parse_all_frames.js first');
  process.exit(2);
}

const lines = fs.readFileSync(framesPath, 'utf8').trim().split(/\r?\n/).filter(Boolean);
const frames = lines.map(l => JSON.parse(l));
const N = frames.length;
console.log('Loaded', N, 'frames from', framesPath);

// Frame length histogram
const lenCounts = new Map();
let maxLen = 0;
frames.forEach(f => { lenCounts.set(f.bytes, (lenCounts.get(f.bytes) || 0) + 1); if (f.bytes > maxLen) maxLen = f.bytes; });
console.log('\nFrame lengths (bytes):');
[...lenCounts.entries()].sort((a,b)=>b[1]-a[1]).forEach(([len,c]) => console.log(`  ${len}: ${c}`));

// Device/id counts (from asciiRuns)
const devCounts = new Map();
frames.forEach(f => {
  const dev = f.device || '(unknown)';
  devCounts.set(dev, (devCounts.get(dev)||0)+1);
});
console.log('\nDevice strings (heuristic):');
[...devCounts.entries()].sort((a,b)=>b[1]-a[1]).slice(0,20).forEach(([d,c]) => console.log(`  ${d}: ${c}`));

// For per-offset statistics we'll consider offsets up to maxLen-4 for 4-byte reads
const uint32Stats = {}; // off -> {count, sum, sumsq, uniques: Map}
const float32Stats = {};
const int16Stats = {};

function ensure(o, idx) { if (!o[idx]) o[idx] = {count:0, sum:0, sumsq:0, uniques:new Map()}; return o[idx]; }

frames.forEach(f => {
  const hex = f.hex;
  const buf = Buffer.from(hex, 'hex');
  // uint32/float32
  for (let off=0; off+4<=buf.length; off+=4) {
    const u = buf.readUInt32LE(off);
    const fl = buf.readFloatLE(off);
    const s = ensure(uint32Stats, off);
    s.count++; s.sum += u; s.sumsq += u*u; s.uniques.set(u, (s.uniques.get(u)||0)+1);
    const sf = ensure(float32Stats, off);
    sf.count++; sf.sum += fl; sf.sumsq += fl*fl; sf.uniques.set(String(fl), (sf.uniques.get(String(fl))||0)+1);
  }
  // int16
  for (let off=0; off+2<=buf.length; off+=2) {
    const si = buf.readInt16LE(off);
    const s = ensure(int16Stats, off);
    s.count++; s.sum += si; s.sumsq += si*si; s.uniques.set(si, (s.uniques.get(si)||0)+1);
  }
});

function finalizeStats(obj) {
  const out = [];
  for (const offStr of Object.keys(obj)) {
    const off = parseInt(offStr,10);
    const st = obj[off];
    const mean = st.sum / st.count;
    const variance = (st.sumsq / st.count) - (mean*mean);
    const std = Math.sqrt(Math.max(0, variance));
    out.push({offset: off, count: st.count, uniques: st.uniques.size, mean, std});
  }
  return out.sort((a,b)=>b.std - a.std);
}

const uint32Summary = finalizeStats(uint32Stats);
const float32Summary = finalizeStats(float32Stats);
const int16Summary = finalizeStats(int16Stats);

console.log('\nTop 10 offsets by uint32 stddev:');
uint32Summary.slice(0,10).forEach(s => console.log(`  @${s.offset}: std=${s.std.toFixed(3)}, uniques=${s.uniques}, present=${s.count}/${N}`));

console.log('\nTop 10 offsets by float32 stddev:');
float32Summary.slice(0,10).forEach(s => console.log(`  @${s.offset}: std=${s.std.toFixed(6)}, uniques=${s.uniques}, present=${s.count}/${N}`));

console.log('\nTop 12 offsets by int16 stddev:');
int16Summary.slice(0,12).forEach(s => console.log(`  @${s.offset}: std=${s.std.toFixed(3)}, uniques=${s.uniques}, present=${s.count}/${N}`));

// Suggest candidate sample offsets: high stddev and present in many frames
function candidates(summary, thresholdStd, minPresentFrac) {
  return summary.filter(s => s.std >= thresholdStd && (s.count / N) >= minPresentFrac).slice(0,20);
}

const candUint32 = candidates(uint32Summary, 1000, 0.5);
const candFloat32 = candidates(float32Summary, 0.1, 0.5);
const candInt16 = candidates(int16Summary, 50, 0.5);

console.log('\nCandidate offsets (uint32 std>=1000):', candUint32.map(c=>c.offset));
console.log('Candidate offsets (float32 std>=0.1):', candFloat32.map(c=>c.offset));
console.log('Candidate offsets (int16 std>=50):', candInt16.map(c=>c.offset));

// Save a small CSV of top int16 offsets for manual plotting if desired
const topIntOffsets = int16Summary.slice(0,6).map(x=>x.offset);
const csvPath = path.join(__dirname, 'top_int16_samples.csv');
{
  const hdr = ['frame_index','bytes', ...topIntOffsets.map(o=>`off_${o}`)].join(',') + '\n';
  const linesOut = [hdr];
  frames.forEach(f=>{
    const buf = Buffer.from(f.hex,'hex');
    const vals = topIntOffsets.map(o => (o+2<=buf.length ? buf.readInt16LE(o) : ''));
    linesOut.push([f.index, f.bytes, ...vals].join(',') + '\n');
  });
  fs.writeFileSync(csvPath, linesOut.join(''));
  console.log('\nWrote example CSV of top int16 offsets to', csvPath);
}

console.log('\nDone. If you want, I can produce plots or try interpreting top offsets as EEG channels (scaling, sign, sample rate heuristics).');
