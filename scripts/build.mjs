// Builds the Ride Guide site into dist/.
// Pulls every active route from Ride with GPS (the source of truth), adds offers, brand and translations,
// and writes one data file per route under a secret key. Never deletes a working route because of a bad sync:
// if Ride with GPS fails or returns broken data, the last good copy from the live site is kept.
//
// Usage: node scripts/build.mjs [--offline]   (--offline reads cache/<id>.json instead of Ride with GPS)
// Secrets: env ROUTE_SECRETS (JSON) or .secrets.json: { keySalt, privacy: { <rwgpsId>: <privacy code> } }
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { buildVoice } from './voice.mjs';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const OFFLINE = process.argv.includes('--offline');
const SITE_BASE = (process.env.SITE_BASE || 'https://elementoutdoors.github.io/routes/').replace(/\/?$/, '/');
const LIVE_BASE = process.env.LIVE_BASE || SITE_BASE;
const LANGS = ['de', 'fr', 'es', 'it', 'nl', 'zh', 'ja', 'ko'];

const readJson = (p, d) => { try { return JSON.parse(fs.readFileSync(path.join(ROOT, p), 'utf8')); } catch (e) { if (d !== undefined) return d; throw e; } };
const secrets = process.env.ROUTE_SECRETS ? JSON.parse(process.env.ROUTE_SECRETS) : readJson('.secrets.json');
const cfg = readJson('config/routes.json');
const brands = readJson('config/brands.json');
const offersCfg = readJson('config/offers.json');
const storiesCfg = readJson('config/stories.json', { blogs: {}, stories: {} });
const i18n = Object.fromEntries(LANGS.map(l => [l, readJson(`config/i18n/${l}.json`, {})]));

// Behaviour settings: every value checked against a safe range; anything wrong falls back to the default.
const SETTINGS_RULES = {
  announce: { firstWarningMetres: [160, 60, 400], turnMetres: [35, 10, 80], cautionWarningMetres: [120, 60, 400],
    skipFirstWarningIfCuesCloserThanMetres: [110, 0, 300], mergeNextCueWithinMetres: [90, 0, 250] },
  offRoute: { metres: [50, 25, 150], readings: [3, 1, 10], repeatSeconds: [60, 20, 600] },
  stops: { triggerMetres: [60, 20, 200], cautionWarningMetres: [90, 30, 300] },
  screen: { keepScreenOn: [true], batterySaver: [false], readStoriesAloud: [true], wakeBeforeTurnMetres: [250, 80, 1000], blackoutAfterSeconds: [20, 5, 120] },
  speeds: { ebike: [15, 3, 40], bike: [13, 3, 40], walk: [4.5, 1, 10], kayak: [5, 1, 15] }
};
function loadSettings(problems) {
  const raw = readJson('config/settings.json', {});
  const out = {};
  for (const [group, keys] of Object.entries(SETTINGS_RULES)) {
    out[group] = {};
    for (const [k, [def, min, max]] of Object.entries(keys)) {
      const v = raw[group] && raw[group][k];
      let ok = typeof def === 'boolean' ? typeof v === 'boolean' : (typeof v === 'number' && isFinite(v) && v >= min && v <= max);
      if (v === undefined) ok = false;
      out[group][k] = ok ? v : def;
      if (!ok && v !== undefined) problems.push(`settings: ${group}.${k} = ${JSON.stringify(v)} is not allowed, using ${def}`);
    }
  }
  return out;
}

const sha = s => crypto.createHash('sha1').update(s).digest('hex');
// Short code a rider can type to reopen a route (no look-alike characters).
const CODE_CHARS = 'ACDEFGHJKMNPQRTUVWXY34679';
export function routeCode(slug, rev) {
  const b = crypto.createHmac('sha256', secrets.keySalt).update(`code:${slug}:${rev || 1}`).digest();
  let c = ''; for (let i = 0; i < 6; i++) c += CODE_CHARS[b[i] % CODE_CHARS.length];
  return c;
}
// Whether a page lets itself be shown inside the app (checked on every build, so it never drifts).
const frameCache = new Map();
async function frameable(url) {
  if (!url) return false;
  if (frameCache.has(url)) return frameCache.get(url);
  let ok = false;
  try {
    const r = await fetch(url, { redirect: 'follow', headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0 Safari/537.36' } });
    const xfo = (r.headers.get('x-frame-options') || '').toLowerCase();
    const csp = (r.headers.get('content-security-policy') || '').toLowerCase();
    const fa = (csp.match(/frame-ancestors([^;]*)/) || [])[1];
    ok = r.ok && new URL(r.url).protocol === 'https:' && !xfo && !(fa && !/\*/.test(fa));
  } catch (e) { ok = false; }
  frameCache.set(url, ok);
  return ok;
}
export function gpxKey(slug, rev) {
  return crypto.createHmac('sha256', secrets.keySalt).update(`gpx:${slug}:${rev || 1}`).digest('base64url').slice(0, 22);
}
// GPX for bike computers: the route line only (no stops, offers or tour text).
function gpxFile(route) {
  const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const T = route.track, pts = [];
  for (let i = 0; i < T.lat.length; i++) pts.push(`<trkpt lat="${T.lat[i]}" lon="${T.lng[i]}"><ele>${T.ele[i]}</ele></trkpt>`);
  return `<?xml version="1.0" encoding="UTF-8"?>\n<gpx version="1.1" creator="Ride Guide (${esc(route.brand.name)})" xmlns="http://www.topografix.com/GPX/1/1">\n<metadata><name>${esc(route.name)}</name></metadata>\n<trk><name>${esc(route.name)}</name><trkseg>\n${pts.join('\n')}\n</trkseg></trk>\n</gpx>\n`;
}
export function routeKey(slug, rev) {
  return crypto.createHmac('sha256', secrets.keySalt).update(`${slug}:${rev || 1}`).digest('base64url').slice(0, 22);
}

// ---------- geometry ----------
const DEG = Math.PI / 180;
function hav(a, b, c, d) {
  const dLat = (c - a) * DEG, dLng = (d - b) * DEG;
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(a * DEG) * Math.cos(c * DEG) * Math.sin(dLng / 2) ** 2;
  return 6371000 * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}
function projAll(T, lat, lng) {
  // distance from point to every segment, with along-route distance
  const kx = 111320 * Math.cos(lat * DEG), ky = 110540, out = [];
  for (let i = 0; i < T.lat.length - 1; i++) {
    const ax = (T.lng[i] - lng) * kx, ay = (T.lat[i] - lat) * ky, bx = (T.lng[i + 1] - lng) * kx, by = (T.lat[i + 1] - lat) * ky;
    const dx = bx - ax, dy = by - ay, l2 = dx * dx + dy * dy;
    const t = l2 > 0 ? Math.max(0, Math.min(1, -(ax * dx + ay * dy) / l2)) : 0;
    const px = ax + t * dx, py = ay + t * dy;
    out.push({ dist: Math.hypot(px, py), d: T.d[i] + t * (T.d[i + 1] - T.d[i]) });
  }
  return out;
}
function passes(T, lat, lng, maxDist) {
  // each separate time the route passes within maxDist, the closest point of that pass
  const runs = []; let run = null, nearest = null;
  for (const p of projAll(T, lat, lng)) {
    if (!nearest || p.dist < nearest.dist) nearest = p;
    if (p.dist <= maxDist) { if (!run || p.dist < run.dist) run = p; }
    else if (run) { runs.push(run); run = null; }
  }
  if (run) runs.push(run);
  return { runs, nearest };
}

// Offers for a route: every active, in-date offer the route passes within its radius, plus any set to allRoutes.
// d is how far along the route it is passed (null for an allRoutes offer the route never goes near).
function offersFor(T, slug) {
  const out = [];
  for (const o of offersCfg.offers) {
    if (!o.active || (o.validUntil && new Date(o.validUntil + 'T23:59:59+10:00') < new Date())) continue;
    if ((o.hideOn || []).includes(slug)) continue;
    if (typeof o.lat !== 'number' || typeof o.lng !== 'number') continue;   // location not worked out yet (flagged in health)
    const { runs } = passes(T, o.lat, o.lng, o.radius || 400);
    if (!runs.length && !o.allRoutes) continue;
    const cond = [].concat(o.conditions || []).filter(Boolean);
    out.push({ id: o.id, partner: o.partner, logo: o.logo || null, headline: o.headline, alt: o.alt || null, about: o.about || null, how: o.how || null, phone: o.phone || null,
      fin: o.showAt === 'finish',
      conditions: cond.length ? cond : null, address: o.address || null, url: o.url || null, lat: o.lat, lng: o.lng,
      d: runs.length ? Math.round(runs[0].d) : null, validUntil: o.validUntil || null });
  }
  return out;
}

// ---------- full stories ----------
// A stop whose link points at a place on one of the ride story blogs gets that place's full story (written to be heard,
// config/stories.json), played when the rider taps Hear the full story.
const normUrl = u => { try { const x = new URL(u); return (x.host.replace(/^www\./, '') + x.pathname.replace(/\/+$/, '')).toLowerCase(); } catch (e) { return ''; } };
const BLOGS = Object.entries(storiesCfg.blogs || {}).map(([brand, url]) => ({ brand, url, n: normUrl(url) }));
function storyKey(url) {
  if (!url || !url.includes('#')) return null;
  const b = BLOGS.find(x => x.n === normUrl(url.split('#')[0]));
  return b ? { brand: b.brand, key: url.split('#')[1] } : null;
}
function attachStories(route, report) {
  for (const s of route.stops) {
    delete s.story;
    const k = storyKey(s.url); if (!k) continue;
    report.linked.add(k.brand + '#' + k.key);
    const st = (storiesCfg.stories || {})[k.key];
    if (st && Array.isArray(st.paras) && st.paras.length) s.story = st.paras.map(p => String(p).trim()).filter(Boolean);
    else report.missing.add(k.brand + '#' + k.key);
  }
}
// Each blog section as plain text: the paragraphs between a place's heading and the next heading.
const decode = t => t.replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
  .replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const plain = t => decode(t.replace(/<[^>]+>/g, '')).replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').replace(/\s+/g, ' ').trim();
export function blogSections(html) {
  const out = {};
  const heads = [...html.matchAll(/<h([23])\b[^>]*>/gi)].map(m => ({ at: m.index, end: m.index + m[0].length, tag: m[0], level: m[1] }));
  heads.forEach((h, i) => {
    const id = (h.tag.match(/\bid=["']([^"']+)["']/) || [])[1];
    if (!id || h.level !== '3') return;
    const chunk = html.slice(h.end, i + 1 < heads.length ? heads[i + 1].at : html.length);
    const paras = [...chunk.matchAll(/<p\b([^>]*)>([\s\S]*?)<\/p>/gi)].filter(m => !/bo-eb/.test(m[1])).map(m => plain(m[2])).filter(Boolean);
    out[id] = paras.join('\n');
  });
  return out;
}
async function watchBlogs(report) {
  for (const b of BLOGS) {
    try {
      const r = await fetch(b.url, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0 Safari/537.36' } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const secs = blogSections(await r.text());
      report.sections[b.brand] = Object.keys(secs).length;
      for (const [key, text] of Object.entries(secs)) {
        const h = sha(text).slice(0, 12);
        report.current[b.brand + '#' + key] = h;
        const st = (storiesCfg.stories || {})[key];
        if (!st) continue;
        const was = (st.src || {})[b.brand];
        if (!was) report.unchecked.push(b.brand + '#' + key);
        else if (was !== h) report.stale.push(b.brand + '#' + key);
      }
      for (const lk of report.linked) if (lk.startsWith(b.brand + '#') && !secs[lk.split('#')[1]]) report.noSection.push(lk);
    } catch (e) { report.unread.push(`${b.brand}: ${e.message || e}`); }
  }
}

// ---------- transform ----------
const CUE_TYPES = { 'left': 'left', 'right': 'right', 'slight left': 'slight-left', 'slight right': 'slight-right', 'sharp left': 'sharp-left',
  'sharp right': 'sharp-right', 'straight': 'straight', 'uturn': 'uturn', 'u turn': 'uturn', 'danger': 'danger', 'generic': 'generic' };
// Ride with GPS pin icon -> what the app does with it (see the "Stops" guide in the project doc).
// caution: a warning, shown and spoken before the rider gets there. Story icons: pop up and are read when the rider arrives.
// Facility icons (toilet, food, drink, service): shown on the map and in the Stops list only, never popped up or spoken.
const POI_KINDS = {
  caution: 'caution',
  generic: 'info', monument: 'info', library: 'info', trailhead: 'info', ferry: 'info', geocache: 'info', start: 'info',
  segment_start: 'info', segment_end: 'info', control: 'info',
  viewpoint: 'view', summit: 'view',
  park: 'park', camping: 'park', swimming: 'park',
  stop: 'turn', finish: 'finish',
  restroom: 'toilet', shower: 'toilet',
  food: 'food', coffee: 'food', convenience_store: 'food',
  bar: 'drink', winery: 'drink',
  water: 'service', parking: 'service', gas: 'service', transit: 'service', atm: 'service', shopping: 'service', lodging: 'service',
  bike_shop: 'service', bike_parking: 'service', bikeshare: 'service', hospital: 'service', first_aid: 'service', aid_station: 'service', rest_stop: 'service'
};
const clean = s => (s || '').replace(/\r/g, '').replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
const photoUrl = id => `https://ridewithgps.com/photos/${id}/large.jpg`;

function validate(r) {
  const problems = [];
  if (!r || !Array.isArray(r.track_points) || r.track_points.length < 50) problems.push('track missing or too short');
  if (!(r && r.distance > 500)) problems.push('distance under 500 m');
  if (!r || !Array.isArray(r.course_points) || r.course_points.length < 1) problems.push('no cues');
  return problems;
}

function transform(entry, r) {
  const tp = r.track_points.filter(p => typeof p.x === 'number' && typeof p.y === 'number' && typeof p.d === 'number');
  const T = { lng: [], lat: [], ele: [], d: [] };
  let last = -1;
  for (const p of tp) {
    if (p.d <= last) continue;   // keep distances strictly increasing
    T.lng.push(+p.x.toFixed(6)); T.lat.push(+p.y.toFixed(6)); T.ele.push(Math.round(p.e || 0)); T.d.push(Math.round(p.d)); last = p.d;
  }
  const distance = T.d[T.d.length - 1];
  const cues = r.course_points
    .map(c => ({ d: Math.round(c.d), t: CUE_TYPES[(c.t || 'generic').toLowerCase()] || 'generic', n: clean(c.n) }))
    .filter(c => c.n && c.d >= 0 && c.d <= distance + 50)
    .sort((a, b) => a.d - b.d);

  const activeOffers = offersCfg.offers.filter(o => o.active && (!o.validUntil || new Date(o.validUntil + 'T23:59:59+10:00') >= new Date()));
  const offerNames = activeOffers.map(o => (o.matchPoi || '').toLowerCase()).filter(Boolean);
  const stops = [], warnings = [];
  for (const p of r.points_of_interest || []) {
    const name = clean(p.name);
    if (!name) continue;
    if (offerNames.some(n => name.toLowerCase().includes(n))) continue;   // replaced by an offer card
    let kind = POI_KINDS[p.poi_type_name] || 'info';
    const isFinish = kind === 'finish' || /review|enjoyed|thank/i.test(name) || /g\.page\/r\//.test(p.url || '');
    if (isFinish) kind = 'finish';
    const { runs, nearest } = passes(T, p.lat, p.lng, 60);
    let d;
    if (runs.length) d = isFinish ? runs[runs.length - 1].d : runs[0].d;
    let off = 0;
    if (!runs.length) { d = nearest ? nearest.d : 0; off = nearest ? Math.round(nearest.dist) : 0; if (off > 300) warnings.push(`stop "${name}" is ${off} m from the route`); }
    if (isFinish) d = Math.max(d, distance - 1);
    stops.push({
      id: String(p.id), kind, name, text: clean(p.description), url: p.url || null,
      lat: +p.lat.toFixed(6), lng: +p.lng.toFixed(6), d: Math.round(d), off,
      photos: (p.photo_ids || []).slice(0, 6).map(photoUrl), lib: p.parent_type === 'Club'
    });
  }
  // A POI Library pin replaces the ride's own old copy of the same place (same name, within 400 m). The copy is left out
  // of the app and listed in health.json as safe to delete in Ride with GPS. A pin named "DELETE ME..." is always left out.
  const superseded = [];
  const libPins = stops.filter(o => o.lib);
  for (let i = stops.length - 1; i >= 0; i--) {   // first pass: old copies a library pin replaces, and DELETE ME pins
    const s = stops[i];
    const libTwin = !s.lib && libPins.find(o => o.name.toLowerCase() === s.name.toLowerCase() && hav(o.lat, o.lng, s.lat, s.lng) < 400);
    if (/^delete me/i.test(s.name) || libTwin) { superseded.push({ id: s.id, name: s.name, reason: libTwin ? 'library pin ' + libTwin.id + ' replaces it' : 'named DELETE ME' }); stops.splice(i, 1); }
  }
  for (let i = stops.length - 1; i >= 0; i--) {   // second pass: the same pin twice
    const s = stops[i];
    if (stops.find((o, j) => j < i && o.name === s.name && hav(o.lat, o.lng, s.lat, s.lng) < 40)) stops.splice(i, 1);
  }
  stops.forEach(s => { delete s.lib; });
  stops.sort((a, b) => a.d - b.d);

  const offers = offersFor(T, entry.slug);

  const brandId = brands[entry.brand] ? entry.brand : 'beo';
  const brand = Object.assign({ id: brandId }, brands[brandId]);
  const version = sha(JSON.stringify([T.d, T.lat, cues.map(c => c.d), stops.map(s => s.d)])).slice(0, 8);
  const route = {
    slug: entry.slug, name: clean(r.name), description: clean(r.description), activity: entry.activity || 'ebike',
    distance, gain: Math.round(r.elevation_gain || 0), brand, version,
    hero: r.highlighted_photo_id ? photoUrl(r.highlighted_photo_id) : null,
    track: T, cues, stops, offers, updated: r.updated_at || null
  };
  return { route, warnings, superseded };
}

// strings in a route that need translating
function routeStrings(route) {
  const s = new Set([route.name, route.description]);
  route.cues.forEach(c => s.add(c.n));
  route.stops.forEach(p => { s.add(p.name); s.add(p.text); (p.story || []).forEach(x => s.add(x)); });
  route.offers.forEach(o => { s.add(o.headline); s.add(o.alt); s.add(o.about); s.add(o.how); [].concat(o.conditions || []).forEach(c => s.add(c)); });
  s.delete(''); s.delete(null); s.delete(undefined);
  return [...s];
}

// UI strings: every literal passed to tu(...) in app.js, plus data-t attributes in index.html
function uiStrings() {
  const js = fs.readFileSync(path.join(ROOT, 'site/app.js'), 'utf8');
  const html = fs.readFileSync(path.join(ROOT, 'site/index.html'), 'utf8');
  const out = new Set();
  let i = 0;
  while ((i = js.indexOf('tu(', i)) !== -1) {
    if (/[A-Za-z0-9_$.]/.test(js[i - 1] || '')) { i += 3; continue; }
    let depth = 0, j = i + 2, start = j;
    for (; j < js.length; j++) {
      const ch = js[j];
      if (ch === '\'' || ch === '"') {
        let k = j + 1, lit = '';
        while (k < js.length && js[k] !== ch) { if (js[k] === '\\') { lit += js[k + 1]; k += 2; } else lit += js[k++]; }
        if (depth === 1) out.add(lit);
        j = k; continue;
      }
      if (ch === '(') depth++;
      else if (ch === ')') { depth--; if (depth === 0) break; }
    }
    i = j;
  }
  for (const m of html.matchAll(/data-t="([^"]+)"/g)) out.add(m[1]);
  // object keys that look like identifiers are not UI text
  return [...out].filter(s => s && !/^[a-z]+$/.test(s));
}

async function fetchRoute(entry) {
  if (OFFLINE) return readJson(`cache/${entry.rwgps}.json`);
  const code = secrets.privacy[String(entry.rwgps)];
  const url = `https://ridewithgps.com/routes/${entry.rwgps}.json${code ? `?privacy_code=${code}` : ''}`;
  const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
  if (!res.ok) throw new Error(`Ride with GPS answered ${res.status}`);
  const j = await res.json();
  fs.mkdirSync(path.join(ROOT, 'cache'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, `cache/${entry.rwgps}.json`), JSON.stringify(j));
  return j;
}
async function fetchLive(key) {
  try { const r = await fetch(`${LIVE_BASE}r/${key}.json`, { cache: 'no-store' }); return r.ok ? await r.json() : null; } catch (e) { return null; }
}

function copyDir(src, dst, build) {
  fs.mkdirSync(dst, { recursive: true });
  for (const f of fs.readdirSync(src)) {
    const s = path.join(src, f), d = path.join(dst, f);
    if (fs.statSync(s).isDirectory()) { copyDir(s, d, build); continue; }
    if (/\.(html|js|css|webmanifest)$/.test(f)) fs.writeFileSync(d, fs.readFileSync(s, 'utf8').replaceAll('__BUILD__', build));
    else fs.copyFileSync(s, d);
  }
}

async function main() {
  const now = new Date();
  const build = now.toISOString().slice(0, 16).replace(/[-:T]/g, '').slice(2);   // yymmddhhmm
  const dist = path.join(ROOT, 'dist');
  fs.rmSync(dist, { recursive: true, force: true });
  copyDir(path.join(ROOT, 'site'), dist, build);
  fs.mkdirSync(path.join(dist, 'r'), { recursive: true });

  // UI translations
  const ui = uiStrings();
  const uiOut = {};
  const missing = Object.fromEntries(LANGS.map(l => [l, new Set()]));
  for (const l of LANGS) {
    uiOut[l] = {};
    for (const s of ui) { if (i18n[l][s]) uiOut[l][s] = i18n[l][s]; else missing[l].add(s); }
  }
  fs.writeFileSync(path.join(dist, 'ui.json'), JSON.stringify(uiOut));

  const health = { built: now.toISOString(), build, routes: [], offers: [], problems: [] };
  const settings = loadSettings(health.problems);
  health.settings = settings;
  const links = {}, codes = {};
  const storyReport = { stories: Object.keys(storiesCfg.stories || {}).length, linked: new Set(), missing: new Set(), stale: [], unchecked: [], noSection: [], unread: [], sections: {}, current: {} };
  fs.mkdirSync(path.join(dist, 'c'), { recursive: true });
  fs.mkdirSync(path.join(dist, 'g'), { recursive: true });
  const built = [];
  for (const entry of cfg.routes.filter(r => r.active)) {
    const key = routeKey(entry.slug, entry.rev);
    links[entry.slug] = `${SITE_BASE}#${key}`;
    const code = routeCode(entry.slug, entry.rev);
    codes[entry.slug] = code;
    fs.writeFileSync(path.join(dist, 'c', `${code}.json`), JSON.stringify({ k: key }));
    const h = { slug: entry.slug, rwgps: entry.rwgps, brand: entry.brand, ok: false, source: null, warnings: [] };
    if (!brands[entry.brand]) health.problems.push(`${entry.slug}: brand "${entry.brand}" is not set up, showing By Earth and Ocean`);
    let route = null;
    try {
      const raw = await fetchRoute(entry);
      const r = raw.route || raw;
      const problems = validate(r);
      if (problems.length) throw new Error('bad data from Ride with GPS: ' + problems.join(', '));
      const t = transform(entry, r);
      route = t.route; h.warnings.push(...t.warnings); h.source = 'ridewithgps';
      if (t.superseded.length) h.pinsToDelete = t.superseded;   // old copies the app now leaves out; safe to delete in Ride with GPS
    } catch (e) {
      h.warnings.push(String(e.message || e));
      const prev = OFFLINE ? null : await fetchLive(key);
      if (prev) { route = prev; delete route.key; const bid = brands[entry.brand] ? entry.brand : 'beo'; route.brand = Object.assign({ id: bid }, brands[bid]); h.source = 'previous'; h.warnings.push('kept the last good copy'); }
    }
    if (!route) { h.ok = false; health.problems.push(`${entry.slug}: no route data`); health.routes.push(h); continue; }

    // offers always come from config/offers.json, even when the route itself is the last good copy
    route.offers = offersFor(route.track, entry.slug);

    attachStories(route, storyReport);

    // translations for this route
    const strings = routeStrings(route);
    route.i18n = {};
    for (const l of LANGS) {
      route.i18n[l] = {};
      for (const s of strings) { if (i18n[l][s]) route.i18n[l][s] = i18n[l][s]; else missing[l].add(s); }
    }
    route.code = code;
    route.settings = settings;
    route.gpx = null;
    if (entry.gpx) {
      const gname = `g/${gpxKey(entry.slug, entry.rev)}.gpx`;
      fs.writeFileSync(path.join(dist, gname), gpxFile(route));
      route.gpx = gname;
    }
    for (const x of [...route.stops, ...route.offers]) x.frame = await frameable(x.url);
    built.push({ key, route });   // written after the voice step adds its recordings
    Object.assign(h, { ok: true, name: route.name, version: route.version, distance: route.distance, gpx: !!route.gpx, cues: route.cues.length,
      stops: route.stops.length, offers: route.offers.map(o => o.id),
      links: [...new Set(route.stops.map(s => s.url).filter(Boolean).concat(route.offers.map(o => o.url).filter(Boolean), Object.values((route.brand && route.brand.reviews) || {})))],
      photos: [...new Set(route.stops.flatMap(s => s.photos))],
      untranslated: Object.fromEntries(LANGS.map(l => [l, strings.filter(s => !i18n[l][s]).length])) });
    if (h.source !== 'ridewithgps') health.problems.push(`${entry.slug}: using last good copy (${h.warnings[0]})`);
    health.routes.push(h);
  }
  // Same place, different story: a story stop copied onto several rides instead of shared from the POI Library drifts apart.
  {
    const variants = (readJson('config/stop-variants.json', {}).variants) || {};
    const byName = new Map();
    for (const b of built) for (const st of b.route.stops) {
      if (st.kind === 'caution' || st.kind === 'finish' || (!st.text && !st.url)) continue;
      if ((variants[st.name.toLowerCase()] || []).includes(b.route.slug)) continue;   // a deliberate version for this ride
      const k = ((b.route.brand && b.route.brand.id) || '') + '|' + st.name.toLowerCase();   // each brand has its own wording and blog
      if (!byName.has(k)) byName.set(k, []);
      byName.get(k).push({ slug: b.route.slug, id: st.id, sig: (st.text || '') + '|' + (st.url || '') });
    }
    health.sharedStops = [];
    for (const [name, list] of byName) {
      const ids = new Set(list.map(x => x.id)), sigs = new Set(list.map(x => x.sig));
      const label = name.split('|')[1];
      if (list.length > 1) health.sharedStops.push({ name: label, brand: name.split('|')[0], rides: list.map(x => x.slug), pins: ids.size });
      if (sigs.size > 1) health.problems.push(`stop "${label}" has a different story or link on ${list.map(x => x.slug).join(', ')}; make them match (ideally one POI Library pin added to each ride), or list the ride in config/stop-variants.json if it is meant to differ`);
    }
  }

  // natural voice recordings, then the route files
  try {
    await buildVoice({ routes: built.map(b => b.route), i18n, langs: LANGS, dist, appSource: fs.readFileSync(path.join(ROOT, 'site/app.js'), 'utf8'),
      health, allRoutesOk: health.routes.every(r => r.ok && r.source === 'ridewithgps') });
  } catch (e) { health.problems.push('voice step failed: ' + (e.message || e)); fs.writeFileSync(path.join(dist, 'voice.json'), '{}'); }
  for (const b of built) fs.writeFileSync(path.join(dist, 'r', `${b.key}.json`), JSON.stringify(b.route));

  await watchBlogs(storyReport);
  health.stories = Object.assign({}, storyReport, { linked: [...storyReport.linked].sort(), missing: [...storyReport.missing].sort() });

  for (const o of offersCfg.offers) {
    const expired = o.validUntil && new Date(o.validUntil + 'T23:59:59+10:00') < now;
    if (o.active && (typeof o.lat !== 'number' || typeof o.lng !== 'number')) health.problems.push(`offer ${o.id} has no location yet`);
    health.offers.push({ id: o.id, partner: o.partner, active: o.active && !expired, expired: !!expired, lat: o.lat, lng: o.lng, radius: o.radius || 400, showAt: o.showAt === 'finish' ? 'finish' : 'anywhere',
      onRoutes: health.routes.filter(r => (r.offers || []).includes(o.id)).map(r => r.slug) });
    if (o.active && !expired && !health.routes.some(r => (r.offers || []).includes(o.id))) health.problems.push(`offer ${o.id} is not near any route`);
    if (o.logo && !fs.existsSync(path.join(ROOT, 'site', o.logo))) health.problems.push(`offer ${o.id}: logo ${o.logo} is missing, card shows the name instead`);
  }
  health.untranslatedTotal = Object.fromEntries(LANGS.map(l => [l, missing[l].size]));
  fs.writeFileSync(path.join(dist, 'health.json'), JSON.stringify(health, null, 1));

  // for the translation step and QR codes (not published)
  const missingOut = JSON.stringify(Object.fromEntries(LANGS.map(l => [l, [...missing[l]].sort()])), null, 1);
  fs.writeFileSync(path.join(ROOT, 'i18n-missing.json'), missingOut);
  fs.writeFileSync(path.join(dist, 'i18n-missing.json'), missingOut);   // published so the weekly check can translate without the secrets
  fs.mkdirSync(path.join(ROOT, 'qr'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'qr', 'links.json'), JSON.stringify(links, null, 1));
  fs.writeFileSync(path.join(ROOT, 'qr', 'codes.json'), JSON.stringify(codes, null, 1));

  console.log(JSON.stringify({ build, routes: health.routes.map(r => [r.slug, r.ok, r.source, r.cues, r.stops, r.offers, r.warnings]), problems: health.problems, untranslated: health.untranslatedTotal }, null, 1));
  if (health.routes.some(r => !r.ok)) process.exitCode = 2;
}
main().catch(e => { console.error(e); process.exit(1); });
