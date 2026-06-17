#!/usr/bin/env node
// Renders the AlphaForge SVG logo into PWA PNG icons using only Node built-ins.
// SVG viewBox: 0 0 48 48 — all coordinates below are in that space.
const zlib = require('zlib');
const fs = require('fs');
const path = require('path');

// ── PNG encoder (RGBA, color type 6) ─────────────────────────────────────────
function u32be(n) { const b = Buffer.alloc(4); b.writeUInt32BE(n, 0); return b; }

function crc32(buf) {
  const t = [];
  for (let n = 0; n < 256; n++) {
    let v = n;
    for (let k = 0; k < 8; k++) v = (v & 1) ? (0xEDB88320 ^ (v >>> 1)) : (v >>> 1);
    t[n] = v;
  }
  let c = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) c = (c >>> 8) ^ t[(c ^ buf[i]) & 0xFF];
  return (c ^ 0xFFFFFFFF) >>> 0;
}

function pchunk(type, data) {
  const tb = Buffer.from(type, 'ascii');
  return Buffer.concat([u32be(data.length), tb, data, u32be(crc32(Buffer.concat([tb, data])))]);
}

function encodePNG(w, h, rgba) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = pchunk('IHDR', Buffer.concat([u32be(w), u32be(h), Buffer.from([8, 6, 0, 0, 0])]));
  const rows = [];
  for (let y = 0; y < h; y++) {
    const row = Buffer.alloc(1 + w * 4);
    row[0] = 0;
    for (let x = 0; x < w; x++) {
      const s = (y * w + x) * 4;
      row[1 + x*4] = rgba[s]; row[2 + x*4] = rgba[s+1];
      row[3 + x*4] = rgba[s+2]; row[4 + x*4] = rgba[s+3];
    }
    rows.push(row);
  }
  return Buffer.concat([sig, ihdr, pchunk('IDAT', zlib.deflateSync(Buffer.concat(rows))), pchunk('IEND', Buffer.alloc(0))]);
}

// ── Geometry helpers ──────────────────────────────────────────────────────────
function inRRect(x, y, x0, y0, w, h, r) {
  const dx = Math.max(x0 + r - x, 0, x - (x0 + w - r));
  const dy = Math.max(y0 + r - y, 0, y - (y0 + h - r));
  return dx * dx + dy * dy <= r * r;
}

function distSeg(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1, l2 = dx*dx + dy*dy;
  if (!l2) return Math.hypot(px - x1, py - y1);
  const t = Math.max(0, Math.min(1, ((px-x1)*dx + (py-y1)*dy) / l2));
  return Math.hypot(px - x1 - t*dx, py - y1 - t*dy);
}

function inTri(px, py, x1, y1, x2, y2, x3, y3) {
  const s = (p, q, a, b, c, d) => (p - d) * (b - d) - (a - d) * (q - d);
  const d1 = s(px,py,x1,y1,x2,y2), d2 = s(px,py,x2,y2,x3,y3), d3 = s(px,py,x3,y3,x1,y1);
  return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
}

// ── Sample the full logo at SVG coordinate (u, v) ────────────────────────────
// Returns [r, g, b, a] — a=0 means transparent (outside rounded rect)
function sample(u, v) {
  let r = 0, g = 0, b = 0, a = 0;

  // Rounded rect background: gradient #1e40af → #1e3a5f top-to-bottom
  if (inRRect(u, v, 0, 0, 48, 48, 11)) {
    const t = v / 48;
    r = 0x1e;
    g = Math.round(0x40 + (0x3a - 0x40) * t);
    b = Math.round(0xaf + (0x5f - 0xaf) * t);
    a = 255;
  }

  // White V-lines (stroke-width 3.5 → half-width 1.75)
  if (distSeg(u, v, 13, 38, 24, 13) < 1.75) { r = 255; g = 255; b = 255; a = 255; }
  if (distSeg(u, v, 24, 13, 35, 38) < 1.75) { r = 255; g = 255; b = 255; a = 255; }
  // White crossbar (stroke-width 3 → half-width 1.5)
  if (distSeg(u, v, 18, 28, 30, 28) < 1.5)  { r = 255; g = 255; b = 255; a = 255; }

  // Amber circle at apex (24, 13) r=3.5
  if (Math.hypot(u - 24, v - 13) < 3.5) { r = 0xf5; g = 0x9e; b = 0x0b; a = 255; }

  // Amber stem line (24,9)→(24,5) stroke-width 2.5 → half 1.25
  if (distSeg(u, v, 24, 9, 24, 5) < 1.25) { r = 0xf5; g = 0x9e; b = 0x0b; a = 255; }

  // Amber arrowhead triangle (24,2),(21,7),(27,7)
  if (inTri(u, v, 24, 2, 21, 7, 27, 7)) { r = 0xf5; g = 0x9e; b = 0x0b; a = 255; }

  return [r, g, b, a];
}

// Same but only foreground elements (no background) — used for maskable
function sampleFg(u, v) {
  if (distSeg(u, v, 13, 38, 24, 13) < 1.75) return [255, 255, 255, 255];
  if (distSeg(u, v, 24, 13, 35, 38) < 1.75) return [255, 255, 255, 255];
  if (distSeg(u, v, 18, 28, 30, 28) < 1.5)  return [255, 255, 255, 255];
  if (Math.hypot(u - 24, v - 13) < 3.5)      return [0xf5, 0x9e, 0x0b, 255];
  if (distSeg(u, v, 24, 9, 24, 5) < 1.25)    return [0xf5, 0x9e, 0x0b, 255];
  if (inTri(u, v, 24, 2, 21, 7, 27, 7))       return [0xf5, 0x9e, 0x0b, 255];
  return [0, 0, 0, 0];
}

// ── Render standard icon (transparent outside rounded rect) ──────────────────
function renderIcon(size) {
  const SS = 3; // 3×3 super-sampling for smooth edges
  const rgba = new Uint8Array(size * size * 4);
  for (let py = 0; py < size; py++) {
    for (let px = 0; px < size; px++) {
      let sr = 0, sg = 0, sb = 0, sa = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const u = ((px + (sx + 0.5) / SS) / size) * 48;
          const v = ((py + (sy + 0.5) / SS) / size) * 48;
          const [r, g, b, a] = sample(u, v);
          sr += r; sg += g; sb += b; sa += a;
        }
      }
      const n = SS * SS, i = (py * size + px) * 4;
      rgba[i]   = Math.round(sr / n);
      rgba[i+1] = Math.round(sg / n);
      rgba[i+2] = Math.round(sb / n);
      rgba[i+3] = Math.round(sa / n);
    }
  }
  return encodePNG(size, size, rgba);
}

// ── Render maskable icon (full-bleed bg, logo in 80% safe zone, fully opaque) ─
function renderMaskable(size) {
  const SS = 3, safe = 0.8, margin = (1 - safe) / 2;
  const rgba = new Uint8Array(size * size * 4);
  for (let py = 0; py < size; py++) {
    for (let px = 0; px < size; px++) {
      let sr = 0, sg = 0, sb = 0;
      for (let sy = 0; sy < SS; sy++) {
        for (let sx = 0; sx < SS; sx++) {
          const nx = (px + (sx + 0.5) / SS) / size;
          const ny = (py + (sy + 0.5) / SS) / size;

          // Full-bleed gradient background
          const t = ny;
          let r = 0x1e, g = Math.round(0x40 + (0x3a - 0x40) * t), b = Math.round(0xaf + (0x5f - 0xaf) * t);

          // Logo foreground drawn inside safe zone
          if (nx >= margin && nx <= 1 - margin && ny >= margin && ny <= 1 - margin) {
            const lu = ((nx - margin) / safe) * 48;
            const lv = ((ny - margin) / safe) * 48;
            const [fr, fg, fb, fa] = sampleFg(lu, lv);
            if (fa > 0) { r = fr; g = fg; b = fb; }
          }

          sr += r; sg += g; sb += b;
        }
      }
      const n = SS * SS, i = (py * size + px) * 4;
      rgba[i]   = Math.round(sr / n);
      rgba[i+1] = Math.round(sg / n);
      rgba[i+2] = Math.round(sb / n);
      rgba[i+3] = 255;
    }
  }
  return encodePNG(size, size, rgba);
}

const out = path.join(__dirname, 'ui/public');
const icons = {
  'pwa-192x192.png':          () => renderIcon(192),
  'pwa-512x512.png':          () => renderIcon(512),
  'pwa-512x512-maskable.png': () => renderMaskable(512),
  'apple-touch-icon.png':     () => renderMaskable(180),
};
for (const [name, gen] of Object.entries(icons)) {
  const buf = gen();
  fs.writeFileSync(path.join(out, name), buf);
  console.log(`  ${name}: ${buf.length} bytes`);
}
console.log('Done.');
