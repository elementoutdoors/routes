// Public toilets for the Ride Guide maps (Ben, 13/11/2026): a small toilet icon on the riding map, nothing spoken, no pop-up.
// Source (since 13/11/2026 evening): the base map itself. Ben found the National Public Toilet Map positions did not match the
// toilet icons drawn on the map underneath, so the toilets are now read from the same OpenFreeMap tiles the map draws
// (OpenStreetMap data, poi layer, class "toilets"), and our icons sit exactly on the map's own.
// This script reads every zoom 14 tile in the riding area and writes config/toilets.json. The build then puts on each ride
// the toilets within config/toilets.json "nearMetres" of its line.
// It only downloads when OpenFreeMap publishes a new map version (or the file is over 25 days old), so the toilets follow
// the base map's own updates. Run by the 3am build (commits the file when it changes) and by hand: node scripts/toilets.mjs
// Drift guards: a failed download, too many failed tiles, or far fewer toilets than last time keeps the old file and exits 1;
// the build flags a ride that leaves the area; the weekly check flags the file if it is over 60 days old.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeTile } from './mvt.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FILE = path.join(ROOT, 'config', 'toilets.json');
const old = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE, 'utf8')) : null;
const AREA = (old && old.area) || { south: -26.85, north: -25.85, west: 152.35, east: 153.25 };
const NEAR = (old && old.nearMetres) || 150;
const FORCE = process.argv.includes('--force');
const Z = 14, N = 2 ** Z;
const tx = lng => Math.floor((lng + 180) / 360 * N);
const ty = lat => { const r = lat * Math.PI / 180; return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * N); };
const hav = (a, b, c, d) => { const R = 6371000, r = Math.PI / 180, x = Math.sin((c - a) * r / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin((d - b) * r / 2) ** 2; return 2 * R * Math.asin(Math.sqrt(x)); };

async function getTile(url, tries = 3) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url);
      if (r.status === 204 || r.status === 404) return Buffer.alloc(0);   // empty sea or bush
      if (r.ok) return Buffer.from(await r.arrayBuffer());
    } catch (e) { /* retry */ }
    await new Promise(res => setTimeout(res, 1000 * (i + 1)));
  }
  return null;
}

async function main() {
  const tj = await (await fetch('https://tiles.openfreemap.org/planet')).json();
  const tpl = tj.tiles[0];
  const ageDays = old && old.fetched ? (Date.now() - new Date(old.fetched).getTime()) / 86400000 : 999;
  if (!FORCE && old && old.mapVersion === tpl && ageDays < 25 && old.toilets.length) { console.log(`toilets: base map unchanged (${old.toilets.length} toilets)`); return; }
  const jobs = [];
  for (let x = tx(AREA.west); x <= tx(AREA.east); x++) for (let y = ty(AREA.north); y <= ty(AREA.south); y++) jobs.push([x, y]);
  const found = []; let failed = 0, next = 0;
  async function worker() {
    while (next < jobs.length) {
      const [x, y] = jobs[next++];
      const buf = await getTile(tpl.replace('{z}', Z).replace('{x}', x).replace('{y}', y));
      if (!buf) { failed++; continue; }
      if (!buf.length) continue;
      const poi = decodeTile(buf).find(l => l.name === 'poi');
      if (!poi) continue;
      for (const f of poi.features) {
        if (f.props.class !== 'toilets' && f.props.subclass !== 'toilets') continue;
        const [px, py] = f.pts[0] || [];
        if (px == null) continue;
        const lng = (x + px / poi.extent) / N * 360 - 180;
        const lat = Math.atan(Math.sinh(Math.PI * (1 - 2 * (y + py / poi.extent) / N))) * 180 / Math.PI;
        if (lat < AREA.south || lat > AREA.north || lng < AREA.west || lng > AREA.east) continue;
        found.push({ n: (f.props['name:en'] || f.props.name || '').trim(), lat: +lat.toFixed(6), lng: +lng.toFixed(6) });
      }
    }
  }
  await Promise.all(Array.from({ length: 16 }, worker));
  if (failed > jobs.length * 0.02) throw new Error(`${failed} of ${jobs.length} map tiles failed to download; kept the old file`);
  // the same toilet can sit in two tiles' buffers: keep one per 5 m
  found.sort((a, b) => a.lat - b.lat || a.lng - b.lng);
  const toilets = [];
  for (const t of found) if (!toilets.some(o => hav(o.lat, o.lng, t.lat, t.lng) < 5)) toilets.push(t);
  const was = old ? old.toilets.length : 0;
  if (toilets.length < 50) throw new Error(`only ${toilets.length} toilets found in the area; kept the old file`);
  if (was && old.mapVersion && toilets.length < was * 0.7) throw new Error(`toilets in the area dropped from ${was} to ${toilets.length}; kept the old file`);
  const out = {
    note: 'Written by scripts/toilets.mjs from the base map tiles. Do not edit by hand; change area or nearMetres and rerun with --force.',
    source: 'Base map (OpenFreeMap, OpenStreetMap contributors), poi layer class toilets',
    mapVersion: tpl, fetched: new Date().toISOString().slice(0, 10), tiles: jobs.length,
    area: AREA, nearMetres: NEAR, toilets
  };
  fs.writeFileSync(FILE, JSON.stringify(out, null, 1) + '\n');
  console.log(`toilets: ${toilets.length} in the area (was ${was}) from ${jobs.length} tiles, map ${tpl}`);
}
main().catch(e => { console.error('toilets: ' + e.message); process.exit(1); });
