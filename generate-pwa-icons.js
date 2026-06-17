#!/usr/bin/env node
// Generates solid-color PNG icons for PWA manifest using only Node built-ins.
const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

function u32be(n) {
  const b = Buffer.alloc(4);
  b.writeUInt32BE(n, 0);
  return b;
}

function crc32(buf) {
  let c = 0xFFFFFFFF;
  const t = [];
  for (let n = 0; n < 256; n++) {
    let v = n;
    for (let k = 0; k < 8; k++) v = (v & 1) ? (0xEDB88320 ^ (v >>> 1)) : (v >>> 1);
    t[n] = v;
  }
  for (let i = 0; i < buf.length; i++) c = (c >>> 8) ^ t[(c ^ buf[i]) & 0xFF];
  return (c ^ 0xFFFFFFFF) >>> 0;
}

function chunk(type, data) {
  const tb = Buffer.from(type, 'ascii');
  return Buffer.concat([u32be(data.length), tb, data, u32be(crc32(Buffer.concat([tb, data])))]);
}

function makePNG(w, h, topR, topG, topB, botR, botG, botB) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = chunk('IHDR', Buffer.concat([u32be(w), u32be(h), Buffer.from([8, 2, 0, 0, 0])]));

  const rows = [];
  for (let y = 0; y < h; y++) {
    const t = y / (h - 1);
    const r = Math.round(topR + (botR - topR) * t);
    const g = Math.round(topG + (botG - topG) * t);
    const b = Math.round(topB + (botB - topB) * t);
    const row = Buffer.alloc(1 + w * 3);
    row[0] = 0;
    for (let x = 0; x < w; x++) { row[1 + x*3] = r; row[2 + x*3] = g; row[3 + x*3] = b; }
    rows.push(row);
  }
  const idat = chunk('IDAT', zlib.deflateSync(Buffer.concat(rows)));
  const iend = chunk('IEND', Buffer.alloc(0));
  return Buffer.concat([sig, ihdr, idat, iend]);
}

// Brand gradient: #1e40af → #1e3a5f (top to bottom)
const [tR, tG, tB] = [0x1e, 0x40, 0xaf];
const [bR, bG, bB] = [0x1e, 0x3a, 0x5f];

const out = path.join(__dirname, 'ui/public');
fs.writeFileSync(path.join(out, 'pwa-192x192.png'), makePNG(192, 192, tR, tG, tB, bR, bG, bB));
fs.writeFileSync(path.join(out, 'pwa-512x512.png'), makePNG(512, 512, tR, tG, tB, bR, bG, bB));
fs.writeFileSync(path.join(out, 'apple-touch-icon.png'), makePNG(180, 180, tR, tG, tB, bR, bG, bB));
console.log('PWA icons written to ui/public/');
