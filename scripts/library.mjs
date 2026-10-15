// Version 1 (11/10/2026).
// The Story Library: the one place every Element Outdoors story is written (library/, see library/README.md).
// Everything else is a copy made from it:
//   config/stories.json      spoken stories for the Ride Guide and EO Crew   (generate)
//   config/place-record.json the text the blogs and Ride with GPS pins must show (generate)
//   site library.json        everything, for EO Crew wildlife cards and kayak talking points (build)
//   the two ride story blogs and the Ride with GPS pins                         (plan, then pushed through Chrome)
//
//   node scripts/library.mjs generate [--check]   write (or check) the generated config files
//   node scripts/library.mjs plan [--health f]     what the live blogs and pins need, to match the library (JSON)
//   node scripts/library.mjs lint                  house rule slips in the library text (JSON)
//   node scripts/library.mjs import <workdir>      one-off: built the library from the blogs, stories, pins and EO Crew (11/10/2026)
import fs from 'node:fs';
import path from 'node:path';
import { fp } from './places.mjs';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const LIB = path.join(ROOT, 'library');
export const KINDS = { place: 'places', wildlife: 'wildlife', stop: 'stops' };
export const BLOGS = {
  bikeon: 'https://bikeon.com.au/noosa-self-guided-rides-what-you-will-see/',
  beo: 'https://byearthandocean.com.au/noosa-hinterland-self-guided-rides-places/'
};

// ---------- text helpers (match scripts/places.mjs exactly, so fingerprints agree with the live blogs) ----------
const decodeEnt = t => t.replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
  .replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
export const plain = t => decodeEnt(String(t || '').replace(/<[^>]+>/g, '')).replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim();
export const blogText = paras => (paras || []).map(plain).filter(Boolean).join('\n');
const today = () => new Date(Date.now() + 10 * 3600e3).toISOString().slice(0, 10);

// ---------- reading the library ----------
export function loadLibrary(root = ROOT) {
  const lib = path.join(root, 'library');
  const entries = {};
  for (const [kind, dir] of Object.entries(KINDS)) {
    const d = path.join(lib, dir);
    if (!fs.existsSync(d)) continue;
    for (const f of fs.readdirSync(d).filter(f => f.endsWith('.json')).sort()) {
      const e = JSON.parse(fs.readFileSync(path.join(d, f), 'utf8'));
      if (e.key !== f.replace(/\.json$/, '')) throw new Error(`library/${dir}/${f}: key "${e.key}" does not match the file name`);
      if (e.kind !== kind) throw new Error(`library/${dir}/${f}: kind "${e.kind}" in the ${dir} folder`);
      if (entries[e.key]) throw new Error(`library: key "${e.key}" is used twice`);
      entries[e.key] = e;
    }
  }
  return entries;
}
const live = e => (e.status || 'live') === 'live';

// ---------- the generated copies ----------
export function storiesFrom(entries) {
  const stories = {};
  for (const e of Object.values(entries)) {
    if (!live(e) || !(e.story || []).length) continue;
    const src = {};
    for (const [b, s] of Object.entries(e.blog || {})) if ((s.paras || []).length) src[b] = fp(blogText(s.paras));
    stories[e.key] = Object.assign({ title: e.title, paras: e.story }, Object.keys(src).length ? { src } : {}, e.origin ? { origin: e.origin } : {});
  }
  // A pin can carry its own version of the full story (pins.<brand>[].story) for a spot where the entry's story would not
  // make sense, such as a stop beside the bridge rather than on it. Pin stories are spoken only; they never go to a blog.
  const pinStories = {};
  for (const e of Object.values(entries)) {
    if (!live(e)) continue;
    for (const pins of Object.values(e.pins || {})) for (const p of pins || []) if (Array.isArray(p.story) && p.story.length) pinStories[p.name] = { key: e.key, paras: p.story };
  }
  return {
    pinStories,
    _about: 'GENERATED from the Story Library (library/, see library/README.md) by scripts/library.mjs. Never edit this file: change the library and run node scripts/library.mjs generate. Full stories, written to be heard; src is the fingerprint of the library blog text each story was written from; a story with an origin instead (the kayak tour stops) has no blog. Every story, linked to a ride or not, is recorded in the natural voice and published with its recordings in stories-voice.json for the EO Crew staff app.',
    blogs: BLOGS, stories
  };
}
export function recordFrom(entries) {
  const sections = {}, stops = {};
  for (const e of Object.values(entries)) {
    if (!live(e)) continue;
    const day = e.updated || today();
    for (const [b, s] of Object.entries(e.blog || {})) {
      if (!(s.paras || []).length) continue;
      const text = blogText(s.paras);
      sections[`${b}#${e.key}`] = { text, hash: fp(text), agreed: day };
    }
    for (const [b, pins] of Object.entries(e.pins || {})) for (const p of pins || []) {
      if (typeof p.text !== 'string') continue;
      stops[`${b}#${e.key}|${p.name}`] = { text: p.text, hash: fp(p.text), agreed: day };
    }
  }
  const sortObj = o => Object.fromEntries(Object.keys(o).sort().map(k => [k, o[k]]));
  return {
    _about: 'GENERATED from the Story Library (library/) by scripts/library.mjs. The text every ride story blog section and Ride with GPS stop summary must show. The nightly build lists each live difference in health.json "places"; the weekly Story Library check puts the library version back. Never edit this file.',
    sections: sortObj(sections), stops: sortObj(stops)
  };
}
// Everything, for the site (EO Crew reads wildlife cards and kayak talking points from it).
export function compiled(entries) {
  const out = [];
  for (const e of Object.values(entries).sort((a, b) => a.key.localeCompare(b.key))) {
    if (!live(e)) continue;
    const x = JSON.parse(JSON.stringify(e));
    for (const s of Object.values(x.blog || {})) s.text = blogText(s.paras);
    x.fingerprint = fp(JSON.stringify(e));
    out.push(x);
  }
  return { _about: 'The Element Outdoors Story Library, compiled by the Ride Guide build from library/ in github.com/elementoutdoors/routes. Read only: change the library, never this copy.', built: new Date().toISOString(), blogs: BLOGS, entries: out };
}
const stable = o => JSON.stringify(o, null, 1) + '\n';
export function generatedFiles(entries) {
  return { 'config/stories.json': stable(storiesFrom(entries)), 'config/place-record.json': stable(recordFrom(entries)) };
}
// Committed copies that differ from what the library makes (ignores the agreed date, which only records when text was set).
export function generatedDrift(entries, root = ROOT) {
  const out = [];
  const strip = s => s.replace(/"agreed": "[0-9-]+"/g, '');
  for (const [f, want] of Object.entries(generatedFiles(entries))) {
    const p = path.join(root, f);
    const have = fs.existsSync(p) ? fs.readFileSync(p, 'utf8') : '';
    if (strip(have) !== strip(want)) out.push(f);
  }
  return out;
}

// ---------- house rules (reported to the truth review, never fixed silently) ----------
const RULES = [
  { re: /\w\s*[—–]\s*\w/, why: 'a dash between words (house style: no em or en dashes)' },
  { re: /\bon your (left|right)\b|\b(turn|look) (left|right)\b/i, why: 'left or right directions (riders and paddlers come from both ways)' },
  { re: /one of only two (everglade|everglades)/i, test: t => !/often described as one of only two/i.test(t), why: '"one of only two everglades" must be "often described as"' },
  { re: /\bDonella\b/, why: 'spelling: Lake Doonella' },
  { re: /\bMother Mountain\b/, why: 'spelling: Mothar Mountain' },
  { re: /\bdriver'?s? licen[cs]e\b/i, test: t => !/drivers licence/.test(t), why: 'house spelling: drivers licence' },
  { re: /\bNoosa Everglades\b(?! system)/, test: t => !/Noosa Everglades system/.test(t), why: 'say "Noosa Everglades system" in full' }
];
export function lint(entries) {
  const out = [];
  const look = (key, where, t) => { const ok = (entries[key].lint_ok || []); for (const r of RULES) if (r.re.test(t) && (!r.test || r.test(t)) && !ok.includes(r.why)) out.push({ key, where, why: r.why, text: t.slice(0, 200) }); };
  for (const e of Object.values(entries)) {
    (e.story || []).forEach((p, i) => look(e.key, `story ${i + 1}`, p));
    for (const [b, s] of Object.entries(e.blog || {})) look(e.key, `blog ${b}`, blogText(s.paras));
    for (const [b, pins] of Object.entries(e.pins || {})) (pins || []).forEach(p => look(e.key, `pin ${b} "${p.name}"`, p.text || ''));
    if (e.card) look(e.key, 'wildlife card', [e.card.description, e.card.how_to_spot, ...(e.card.detail || []).map(d => d.text || (d.items || []).join(' '))].join(' '));
    if (e.talk) look(e.key, 'kayak talking points', [...(e.talk.points || []), e.talk.detail || ''].join(' '));
  }
  return out;
}

// ---------- what the live blogs and pins need (from the nightly health.json "places" report) ----------
export function plan(entries, places, routes = []) {
  const blog = [], pins = [], notInLibrary = [], gone = [];
  const rw = slugs => (slugs || []).map(sl => (routes.find(r => r.slug === sl) || {}).rwgps).filter(Boolean);
  const byPlace = id => { const [b, rest] = id.split('#'); const [key, name] = rest.split('|'); return { b, key, name, e: entries[key] }; };
  for (const c of [...(places.changed || []), ...(places.unrecorded || [])]) {
    const { b, key, name, e } = byPlace(c.id);
    if (c.what === 'section') {
      const s = e && e.blog && e.blog[b];
      if (!s) { notInLibrary.push({ what: 'blog section', id: c.id, live: c.after || c.text }); continue; }
      blog.push({ brand: b, url: BLOGS[b], key, action: 'replace', heading: s.heading, paras: s.paras, live: c.after || c.text });
    } else {
      const p = e && ((e.pins || {})[b] || []).find(x => x.name === name);
      if (!p) { notInLibrary.push({ what: 'Ride with GPS pin', id: c.id, live: c.after || c.text, rides: c.rides }); continue; }
      pins.push({ brand: b, key, name, text: p.text, live: c.after || c.text, rides: c.rides, rwgps: rw(c.rides) });
    }
  }
  for (const g of places.gone || []) {
    const { b, key, name, e } = byPlace(g.id);
    if (g.what === 'section') { const s = e && e.blog && e.blog[b]; if (s) blog.push({ brand: b, url: BLOGS[b], key, action: 'insert', heading: s.heading, area: s.area, after: s.after, paras: s.paras }); else gone.push(g); }
    else gone.push(Object.assign({ name }, g));   // a pin missing from every ride: Needs Ben (which rides should carry it)
  }
  return { blog, pins, notInLibrary, gone };
}

// ---------- one-off import (11/10/2026) ----------
function sectionsHtml(html) {
  const out = {};
  const heads = [...html.matchAll(/<h([23])\b[^>]*>([\s\S]*?)<\/h\1>/gi)].map(m => ({ at: m.index, end: m.index + m[0].length, tag: m[0], level: m[1], inner: m[2] }));
  let area = null, prev = null, order = 0;
  heads.forEach((h, i) => {
    const id = (h.tag.match(/\bid=["']([^"']+)["']/) || [])[1];
    if (h.level === '2') { area = id || area; prev = null; return; }
    if (!id) return;
    const chunk = html.slice(h.end, i + 1 < heads.length ? heads[i + 1].at : html.length);
    const paras = [...chunk.matchAll(/<p\b([^>]*)>([\s\S]*?)<\/p>/gi)].filter(m => !/bo-eb/.test(m[1])).map(m => cleanHtml(m[2])).filter(p => plain(p));
    out[id] = { heading: plain(h.inner), area, after: prev, order: order++, paras };
    prev = id;
  });
  return out;
}
// Keep only links, bold and italics; plain characters instead of entities; straight quotes (WordPress curls them on the page).
function cleanHtml(s) {
  let t = s.replace(/<(?!\/?(a|strong|em|b|i)\b)[^>]+>/gi, '');
  t = t.replace(/<a\b[^>]*\bhref=["']([^"']+)["'][^>]*>/gi, (_, href) => `<a href="${decodeEnt(href)}"${/^https?:\/\/(www\.)?(bikeon|byearthandocean)\.com\.au/.test(decodeEnt(href)) ? '' : ' target="_blank" rel="noopener"'}>`);
  t = t.replace(/&#(\d+);|&#x([0-9a-f]+);/gi, (m, d, x) => { const c = String.fromCodePoint(d ? +d : parseInt(x, 16)); return c === '<' || c === '>' || c === '&' ? m : c; });
  t = t.replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim();
  return t;
}
const slug = s => s.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
function write(e) {
  const dir = path.join(LIB, KINDS[e.kind]);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, e.key + '.json'), JSON.stringify(e, null, 1) + '\n');
}
function importAll(work) {
  const stories = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/stories.json'), 'utf8')).stories;
  const record = JSON.parse(fs.readFileSync(path.join(ROOT, 'config/place-record.json'), 'utf8'));
  const blogs = { bikeon: sectionsHtml(fs.readFileSync(path.join(work, 'bikeon.html'), 'utf8')), beo: sectionsHtml(fs.readFileSync(path.join(work, 'beo.html'), 'utf8')) };
  const day = '2026-10-11';
  const keys = new Set([...Object.keys(stories), ...Object.keys(blogs.bikeon), ...Object.keys(blogs.beo)]);
  const report = { places: 0, wildlife: 0, stops: 0, mismatches: [] };
  for (const key of [...keys].sort()) {
    const e = { key, kind: 'place', title: (stories[key] || {}).title || (blogs.bikeon[key] || blogs.beo[key]).heading, status: 'live', updated: day, blog: {}, pins: {}, story: (stories[key] || {}).paras || [] };
    for (const b of ['bikeon', 'beo']) {
      const s = blogs[b][key];
      if (!s) continue;
      e.blog[b] = { heading: s.heading, area: s.area, after: s.after, paras: s.paras };
      const rec = record.sections[`${b}#${key}`];
      if (rec && rec.text !== blogText(s.paras)) report.mismatches.push(`${b}#${key}: live blog differs from the agreed text`);
    }
    for (const [id, r] of Object.entries(record.stops)) {
      const [pl, name] = id.split('|'); const [b, k] = pl.split('#');
      if (k !== key) continue;
      (e.pins[b] = e.pins[b] || []).push({ name, text: r.text });
    }
    if (!Object.keys(e.pins).length) delete e.pins;
    e.sources = 'Research, sources and Ben\'s rulings: ride stories doc https://claude.ai/code/artifact/a698e78e-221d-4f1c-8658-d58461c85558';
    write(e); report.places++;
  }
  // EO Crew wildlife cards
  const wl = JSON.parse(fs.readFileSync(path.join(work, 'wildlife.json'), 'utf8')).entities;
  const FIELDS = ['name', 'other_names', 'scientific_name', 'local_name', 'group', 'description', 'detail', 'how_to_spot', 'conservation', 'photo_url', 'photo_focus', 'photo_width', 'photo_height', 'photo_credit', 'source'];
  for (const w of wl) {
    const card = {}; FIELDS.forEach(f => { if (w[f] !== undefined && w[f] !== null && w[f] !== '') card[f] = w[f]; });
    const e = { key: slug(w.name), kind: 'wildlife', title: w.name, status: w.status === 'Published' ? 'live' : 'draft', updated: day, card, eocrew_id: w.id };
    if (w.place_key) e.story_key = w.place_key;
    write(e); report.wildlife++;
  }
  // Stingrays and Everglades kayak tour stops (EO-TR-11 talking points)
  const secs = JSON.parse(fs.readFileSync(path.join(work, 'stingrays-manual.json'), 'utf8')).entities;
  // the spoken stories for these stops were already written (config/stories.json, origin: the manual), so the stop takes the story's key
  const KEY = { 1: 'kabi-kabi-country', 2: 'noosa-private-airport', 3: 'noosa-everglades', 4: 'keyser-creek', 5: 'weyba-mangroves', 6: 'stingray-sanctuary' };
  for (const s of secs) {
    const m = s.title.match(/^6\.(\d) Stop (\d): (.+)$/);
    if (!m) continue;
    const tp = (s.blocks || []).find(b => b.type === 'talking_point');
    if (!tp || !KEY[m[2]]) continue;
    const e = { key: KEY[m[2]], kind: 'stop', title: m[3], status: 'live', updated: day,
      tours: { 'stingrays-everglades': +m[2] },
      talk: { points: tp.touch_points || [], detail: tp.detail || '', detail_blocks: tp.detail_blocks || [] },
      story: [], eocrew: { document_id: s.document_id, section_id: s.id } };
    const st = stories[e.key];
    if (st) { e.title = st.title; e.story = st.paras; e.origin = st.origin; e.talk.stop_title = m[3]; fs.rmSync(path.join(LIB, 'places', e.key + '.json'), { force: true }); report.places--; }
    write(e); report.stops++;
  }
  return report;
}

// ---------- command line ----------
if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const opt = (n, d) => { const i = args.indexOf(n); if (i < 0) return d; const v = args[i + 1]; args.splice(i, 2); return v; };
  const cmd = args[0];
  if (cmd === 'import') { console.log(JSON.stringify(importAll(path.resolve(args[1] || '.')), null, 1)); }
  else if (cmd === 'generate') {
    const entries = loadLibrary();
    if (args.includes('--check')) { const d = generatedDrift(entries); console.log(JSON.stringify({ ok: !d.length, outOfStep: d })); process.exit(d.length ? 1 : 0); }
    for (const [f, t] of Object.entries(generatedFiles(entries))) {
      const p = path.join(ROOT, f);
      // keep the agreed dates already recorded where the text has not changed
      if (f.endsWith('place-record.json') && fs.existsSync(p)) {
        const old = JSON.parse(fs.readFileSync(p, 'utf8')), nu = JSON.parse(t);
        for (const w of ['sections', 'stops']) for (const [id, r] of Object.entries(nu[w])) if (old[w] && old[w][id] && old[w][id].hash === r.hash) r.agreed = old[w][id].agreed;
        fs.writeFileSync(p, stable(nu));
      } else fs.writeFileSync(p, t);
    }
    console.log('generated config/stories.json and config/place-record.json from', Object.keys(entries).length, 'library entries');
  } else if (cmd === 'lint') { const l = lint(loadLibrary()); console.log(JSON.stringify(l, null, 1)); process.exit(l.length ? 1 : 0); }
  else if (cmd === 'plan') {
    const src = opt('--health', 'https://elementoutdoors.github.io/routes/health.json');
    const h = JSON.parse(/^https?:/.test(src) ? await (await fetch(src, { cache: 'no-store' })).text() : fs.readFileSync(src, 'utf8'));
    const p = plan(loadLibrary(), h.places || {}, JSON.parse(fs.readFileSync(path.join(ROOT, 'config/routes.json'), 'utf8')).routes);
    console.log(JSON.stringify(Object.assign({ built: h.built, inStep: !p.blog.length && !p.pins.length && !p.notInLibrary.length && !p.gone.length }, p), null, 1));
  } else { console.error('usage: node scripts/library.mjs <generate [--check]|plan [--health f]|lint|import dir>'); process.exit(2); }
}
