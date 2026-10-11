// Keeps config/place-record.json, the agreed text of every ride story place (see scripts/places.mjs).
// Used by the weekly check after it has decided a difference listed in health.json "places".
// <what> is section or stop. <id> is "brand#anchor" for a section, "brand#anchor|Pin name" for a stop.
//
//   node scripts/place-record.mjs accept <what> <id>         take the live text as agreed (closes its card)
//   node scripts/place-record.mjs accept --all-unrecorded     record everything not in the record yet
//   node scripts/place-record.mjs pending <what> <id> <card>  a card is open: hold the agreed text
//   node scripts/place-record.mjs clear <what> <id>           card closed without taking the live text
//   node scripts/place-record.mjs drop <what> <id>            removed for good from the blog or the rides
//   node scripts/place-record.mjs show <what> <id>
// Options: --health <file or url> (default: the live site's health.json). Never edit the texts by hand.
import fs from 'node:fs';
import path from 'node:path';
import { fp } from './places.mjs';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const FILE = path.join(ROOT, 'config/place-record.json');
const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); if (i < 0) return d; const v = args[i + 1]; args.splice(i, 2); return v; };
const healthSrc = opt('--health', 'https://elementoutdoors.github.io/routes/health.json');
const [cmd, what, id, card] = args;

const rec = JSON.parse(fs.readFileSync(FILE, 'utf8'));
rec.sections = rec.sections || {}; rec.stops = rec.stops || {};
const today = new Date(Date.now() + 10 * 3600e3).toISOString().slice(0, 10);   // Brisbane date
const map = w => w === 'section' ? rec.sections : rec.stops;
const sortObj = o => Object.fromEntries(Object.keys(o).sort().map(k => [k, o[k]]));
const save = () => { rec.sections = sortObj(rec.sections); rec.stops = sortObj(rec.stops); fs.writeFileSync(FILE, JSON.stringify(rec, null, 1) + '\n'); };
const fail = (m, c = 1) => { console.error(m); process.exit(c); };
async function health() {
  const t = /^https?:/.test(healthSrc) ? await (await fetch(healthSrc, { cache: 'no-store' })).text() : fs.readFileSync(healthSrc, 'utf8');
  const h = JSON.parse(t);
  if (!h.places) fail('health.json has no "places" report yet (the build that adds it has not run)');
  return h.places;
}
const put = (w, i, text) => { map(w)[i] = { text, hash: fp(text), agreed: today }; };

if (cmd === 'accept' && what === '--all-unrecorded') {
  const p = await health();
  p.unrecorded.forEach(u => put(u.what, u.id, u.text));
  save(); console.log(`recorded ${p.unrecorded.length}`);
} else {
  if (!['section', 'stop'].includes(what) || !id) fail('usage: <accept|pending|clear|drop|show> <section|stop> <id> (see the top of this file)', 2);
  const r = map(what)[id];
  if (cmd === 'accept') {
    const p = await health();
    const hit = p.changed.find(c => c.what === what && c.id === id), nu = p.unrecorded.find(c => c.what === what && c.id === id);
    if (!hit && !nu) fail(`${what} ${id}: no difference listed in health.json (already agreed?)`);
    put(what, id, hit ? hit.after : nu.text);
    save(); console.log(`agreed ${what} ${id}`);
  } else if (cmd === 'pending') {
    if (!r) fail(`${what} ${id} is not in the record`);
    if (!card) fail('give the card id', 2);
    r.pending = card; save(); console.log(`holding ${what} ${id} for card ${card}`);
  } else if (cmd === 'clear') {
    if (r) delete r.pending; save(); console.log(`cleared ${what} ${id}`);
  } else if (cmd === 'drop') {
    delete map(what)[id]; save(); console.log(`dropped ${what} ${id}`);
  } else if (cmd === 'show') {
    console.log(JSON.stringify(r || null, null, 1));
  } else fail('unknown command', 2);
}
