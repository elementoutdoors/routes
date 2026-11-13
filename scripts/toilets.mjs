// Public toilets for the Ride Guide maps (Ben, 13/11/2026): a small toilet icon on the riding map, nothing spoken, no pop-up.
// Source: the National Public Toilet Map (Australian Government, data.gov.au, Creative Commons Attribution 3.0 Australia),
// updated monthly. This script downloads the latest file, keeps the toilets inside the riding area and writes
// config/toilets.json. The build then puts on each ride the toilets within config/toilets.json "nearMetres" of its line.
// Run by the 3am build (it commits the file when it changes) and by hand: node scripts/toilets.mjs
// Drift guards: a download that fails, or that has far fewer toilets than last time, keeps the old file and exits 1;
// the build flags a ride that leaves the area, and the weekly check flags the file if it is more than 60 days old.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const FILE = path.join(ROOT, 'config', 'toilets.json');
const DATASET = '553b3049-2b8b-46a2-95e6-640d7986a8c1';
const old = fs.existsSync(FILE) ? JSON.parse(fs.readFileSync(FILE, 'utf8')) : null;
// Riding area: Noosa, the hinterland and Gympie, with room to spare. A ride outside it is flagged by the build.
const AREA = (old && old.area) || { south: -26.85, north: -25.85, west: 152.35, east: 153.25 };
const NEAR = (old && old.nearMetres) || 150;

function parseCsv(text) {
  const rows = []; let row = [], f = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true;
    else if (c === ',') { row.push(f); f = ''; }
    else if (c === '\n') { row.push(f.replace(/\r$/, '')); rows.push(row); row = []; f = ''; }
    else f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  const head = rows.shift().map(h => h.replace(/^﻿/, '').trim());
  return rows.filter(r => r.length === head.length).map(r => Object.fromEntries(head.map((h, i) => [h, r[i]])));
}
const yes = v => /^(true|yes|1)$/i.test(String(v || '').trim());
const hours = h => String(h || '').replace(/^\s*open:\s*/i, '').replace(/\s+/g, ' ').trim();

async function main() {
  const meta = await (await fetch(`https://data.gov.au/data/api/3/action/package_show?id=${DATASET}`)).json();
  const res = (meta.result.resources || []).find(r => /csv/i.test(r.format || '') || /\.csv$/i.test(r.url || ''));
  if (!res) throw new Error('no CSV in the National Public Toilet Map dataset');
  const csv = await (await fetch(res.url)).text();
  const all = parseCsv(csv);
  if (all.length < 10000) throw new Error(`only ${all.length} toilets in the national file (expected over 20,000)`);
  const toilets = [];
  for (const r of all) {
    const lat = +r.Latitude, lng = +r.Longitude;
    if (!(lat > AREA.south && lat < AREA.north && lng > AREA.west && lng < AREA.east)) continue;
    if (yes(r.KeyRequired)) continue;   // locked (MLAK key) toilets are no use to riders
    toilets.push({ id: String(r.FacilityID), n: (r.Name || 'Public toilet').trim(), h: hours(r.OpeningHours), lat: +lat.toFixed(6), lng: +lng.toFixed(6) });
  }
  toilets.sort((a, b) => a.id.localeCompare(b.id, 'en', { numeric: true }));
  const was = old ? old.toilets.length : 0;
  if (was && toilets.length < was * 0.7) throw new Error(`toilets in the area dropped from ${was} to ${toilets.length}; kept the old file`);
  const out = {
    note: 'Written by scripts/toilets.mjs from the National Public Toilet Map. Do not edit by hand; change area or nearMetres and rerun.',
    source: 'National Public Toilet Map, Australian Government (data.gov.au), CC BY 3.0 AU',
    sourceFile: res.url, sourceUpdated: res.last_modified || res.created || null,
    fetched: new Date().toISOString().slice(0, 10), area: AREA, nearMetres: NEAR, toilets
  };
  // unchanged: leave the file alone (no daily commits), but refresh the date about monthly so the weekly check can tell it is running
  const same = old && JSON.stringify(old.toilets) === JSON.stringify(toilets) && old.sourceFile === out.sourceFile
    && (Date.now() - new Date(old.fetched).getTime()) < 25 * 86400000;
  if (same) { console.log(`toilets: no change (${toilets.length} in the area)`); return; }
  fs.writeFileSync(FILE, JSON.stringify(out, null, 1) + '\n');
  console.log(`toilets: ${toilets.length} in the area (was ${was}), from ${res.url}`);
}
main().catch(e => { console.error('toilets: ' + e.message); process.exit(1); });
