#!/usr/bin/env node
'use strict';

// Extract DATA frames with their timestamps from log.txt
// Writes tools/frames_with_time.jsonl and prints summary (count, duration, median dt)

const fs = require('fs');
const path = require('path');

const logPath = path.join(__dirname, '..', 'log.txt');
const outPath = path.join(__dirname, 'frames_with_time.jsonl');
const txt = fs.readFileSync(logPath, 'utf8');

// The log contains lines like:
// A\t10:14:23.595\t"(0x) 44-41-54-41-..." received
// We'll match time and the hex payload.
const re = /([A-Z])\s*\t?(\d{2}:\d{2}:\d{2}\.\d{3})\s*\t?"\(0x\)\s*([0-9A-Fa-f\- ]*44-41-54-41[0-9A-Fa-f\- ]*)"\s*received/gm;
let m;
const frames = [];
while ((m = re.exec(txt)) !== null) {
  const level = m[1];
  const timestr = m[2];
  const hex = m[3].replace(/\s+/g, ' ');
  // parse timestr into Date using today's date
  const today = new Date();
  const [hh, mm, ssms] = timestr.split(':');
  const [ss, ms] = ssms.split('.');
  const dt = new Date(today.getFullYear(), today.getMonth(), today.getDate(), parseInt(hh), parseInt(mm), parseInt(ss), parseInt(ms));
  frames.push({time: dt.toISOString(), ts: dt.getTime(), hex});
}

if (frames.length === 0) {
  console.error('No DATA frames found with timestamps');
  process.exit(2);
}

// compute deltas between consecutive frames (in seconds)
const deltas = [];
for (let i=1;i<frames.length;i++) deltas.push((frames[i].ts - frames[i-1].ts)/1000);
function median(arr){ if(arr.length===0) return 0; const s=arr.slice().sort((a,b)=>a-b); const mid=Math.floor(s.length/2); return s.length%2? s[mid] : (s[mid-1]+s[mid])/2; }
const med = median(deltas);
const totalSec = (frames[frames.length-1].ts - frames[0].ts)/1000;

// write JSONL
const out = fs.createWriteStream(outPath, {flags:'w'});
frames.forEach((f,idx)=> out.write(JSON.stringify({index: idx, time: f.time, ts: f.ts, hex: f.hex})+'\n'));
out.end(()=>{
  console.log('Wrote', outPath, 'with', frames.length, 'frames');
  console.log('Duration (sec):', totalSec.toFixed(3));
  console.log('Median inter-frame dt (sec):', med.toFixed(4));
  console.log('Estimated frames/sec:', (med>0? (1/med).toFixed(3): 'inf'));
});
