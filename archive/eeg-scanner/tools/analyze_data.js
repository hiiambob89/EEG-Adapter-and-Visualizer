const fs = require('fs');
const path = require('path');
const txt = fs.readFileSync(path.join(__dirname,'..','log.txt'),'utf8');
const m = txt.match(/44415441[0-9A-Fa-f]+/);
if(!m){ console.error('no DATA blob found'); process.exit(1); }
const hex = m[0];
console.log('bytes', hex.length/2);
const buf = Buffer.from(hex,'hex');
console.log('hex:', buf.toString('hex'));
console.log('\nchunks (8 bytes):');
for(let off=8; off<buf.length-4; off+=8){ const chunk = buf.slice(off, Math.min(off+8, buf.length)); console.log(off, chunk.toString('hex')); }
console.log('\nFloat32 LE at offsets:');
for(let i=0;i+4<=buf.length;i+=4){ try{ console.log(i, buf.readFloatLE(i)); } catch(e){ console.log(i, 'err'); } }
console.log('\nUInt16 LE at offsets:');
for(let i=0;i+2<=buf.length;i+=2){ console.log(i, buf.readUInt16LE(i)); }
