// The Ride Desk: one card per ride on the Ride Desk page (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18), the master
// for everything about a ride that is not the route line, the cues or the places it passes (Ride with GPS), the place
// stories (the Story Library) or the numbers worked out from the line (Ben, 18/10/2026).
//
// Where the Ride Desk's data lives in this repo (written by the "Ride Guide settings apply" scheduled task, never by hand):
//   config/ride-desk.json              every card's public fields, plus the few Claude keeps (link rev, activity, website page)
//   config/ride-desk-private.enc.json  the staff section of every card and each route's Ride with GPS privacy code, sealed so
//                                      only the build can open it (this repo is public)
//   config/ride-desk-key.json          the two public keys: "build" (the build's, made from ROUTE_SECRETS keySalt; anything
//                                      sealed to it only the build can open) and "desk" (the Ride Desk's; its private half is
//                                      in the page's private/keys record, so the settings task can open the links the build
//                                      seals to it)
//
// Usage (from the settings task and the weekly check):
//   node scripts/ride-desk.mjs apply <db dir> [--assets <dir>]   copy the saved cards into the config files above
//   node scripts/ride-desk.mjs published <db dir> <out dir>        the page's published/rides and published/stories records
//   node scripts/ride-desk.mjs links <db dir> <out file>           the page's routes/links record from the build's links.enc.json
//   node scripts/ride-desk.mjs check <db dir>                      the weekly drift check (prints JSON)
//   node scripts/ride-desk.mjs scan <db dir> <scan.json> <out dir> new rides from a Ride with GPS scan (scripts/push/ride-desk-scan.js):
//                                      <out dir>/rides/<slug>.json (new cards), private/codes.json (if a code is new), desk/scan.json
// <db dir> is an ArtifactData "list" saved with out_dir: <db dir>/rides/<slug>.json, <db dir>/private/codes.json, and so on.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
export const DESK_URL = 'https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18';
const SITE = (process.env.SITE_BASE || 'https://elementoutdoors.github.io/routes/').replace(/\/?$/, '/');
const PUBLIC_FILE = 'config/ride-desk.json', PRIVATE_FILE = 'config/ride-desk-private.enc.json', KEY_FILE = 'config/ride-desk-key.json';

export const TYPES = ['scenic', 'mtb', 'gravel', 'road', 'hinterlandMtb', 'hinterlandGravel', 'walk', 'kayak'];
export const CATEGORIES = ['Scenic from the shop', 'Beach from the shop', 'Mountain bike from the shop', 'Gravel from the shop', 'Road from the shop',
  'Hinterland gravel · point to point', 'Hinterland mountain bike · point to point'];
// Ben's fields on the card. Public ones go in config/ride-desk.json; staff ones only ever in the sealed file.
export const PUBLIC_FIELDS = ['live', 'ipad', 'status', 'brand', 'type', 'stories', 'gpx', 'appName', 'title', 'category', 'sellLine', 'highlights',
  'level', 'surface', 'terrain', 'bike', 'bikeNote', 'sheetNote', 'description', 'photo'];
export const STAFF_FIELDS = ['suits', 'notFor', 'timeToAllow', 'soldAs', 'bikes', 'startFinish', 'staffNotes'];
// Claude's fields: the link rev (bump it to replace a ride's link, code and QR code), the activity behind a fallback riding
// speed, the Bike On website page whose photo is the default, and where the ride came from.
export const CLAUDE_FIELDS = ['rwgps', 'rev', 'activity', 'websitePage', 'found', 'rwgpsName', '_note'];
export const LABELS = { appName: 'Name in the app', title: 'Title', category: 'Category', sellLine: 'Sell line', highlights: 'Highlights',
  level: 'Level', surface: 'Surface', terrain: 'Terrain', bike: 'Recommended bike', bikeNote: 'Bike, second line', sheetNote: 'Note on the sheet',
  description: 'Ride description', photo: 'Photo', brand: 'Brand', type: 'Type', suits: 'Who it suits', notFor: 'Not for',
  timeToAllow: 'Time to allow', soldAs: 'Sold as', bikes: 'Bikes to hire', startFinish: 'Start and finish', staffNotes: 'Staff notes' };
// What a card needs before it is complete. Live in the Ride Guide: what the app and staff use. On the iPad: the sheet too.
export const NEEDED_LIVE = ['appName', 'description', 'brand', 'type', 'suits', 'notFor', 'timeToAllow', 'soldAs', 'bikes', 'startFinish', 'staffNotes'];
export const NEEDED_IPAD = ['title', 'category', 'sellLine', 'highlights', 'level', 'surface', 'bike', 'bikeNote', 'sheetNote', 'description'];

const readJson = (p, d) => { try { return JSON.parse(fs.readFileSync(path.isAbsolute(p) ? p : path.join(ROOT, p), 'utf8')); } catch (e) { if (d !== undefined) return d; throw e; } };
const writeJson = (p, o) => { const f = path.isAbsolute(p) ? p : path.join(ROOT, p); fs.mkdirSync(path.dirname(f), { recursive: true }); fs.writeFileSync(f, JSON.stringify(o, null, 1) + '\n'); };
const str = v => (typeof v === 'string' ? v.replace(/\r/g, '').trim() : '');
export const defaultActivity = type => (['mtb', 'gravel', 'road'].includes(type) ? 'bike' : type === 'walk' ? 'walk' : type === 'kayak' ? 'kayak' : 'ebike');
export const defaultCategory = type => ({ scenic: 'Scenic from the shop', mtb: 'Mountain bike from the shop', gravel: 'Gravel from the shop', road: 'Road from the shop',
  hinterlandGravel: 'Hinterland gravel · point to point', hinterlandMtb: 'Hinterland mountain bike · point to point' }[type] || '');
export const isTest = slug => /test/i.test(slug || '');

// ---------- the fields, cleaned the same way everywhere (page, settings task, build, check) ----------
export function cleanPublic(c) {
  const o = {};
  o.live = c.live === true; o.ipad = c.ipad === true; o.status = c.status === 'new' ? 'new' : 'ready';
  o.brand = c.brand === 'beo' ? 'beo' : c.brand === 'bikeon' ? 'bikeon' : '';
  o.type = TYPES.includes(c.type) ? c.type : '';
  o.stories = c.stories === true; o.gpx = c.gpx === true;
  for (const k of ['appName', 'title', 'category', 'sellLine', 'level', 'surface', 'terrain', 'bike', 'bikeNote', 'sheetNote', 'description']) o[k] = str(c[k]);
  const hl = Array.isArray(c.highlights) ? c.highlights.map(str) : [];
  o.highlights = [0, 1, 2, 3].map(i => hl[i] || '');
  const p = c.photo && typeof c.photo === 'object' ? c.photo : {};
  const src = ['website', 'upload', 'link', 'ride'].includes(p.source) ? p.source : 'website';
  o.photo = { source: src };
  if (src === 'upload') o.photo.asset = str(p.asset);
  if (src === 'link' || src === 'ride') o.photo.url = /^https:\/\//.test(str(p.url)) ? str(p.url) : '';
  return o;
}
export function cleanStaff(c) {
  const s = (c && c.staff) || c || {}, o = {};
  for (const k of STAFF_FIELDS) o[k] = str(s[k]);
  return o;
}
const canonDeep = o => JSON.stringify(o, (k, v) => (v && typeof v === 'object' && !Array.isArray(v) ? Object.fromEntries(Object.keys(v).sort().map(x => [x, v[x]])) : v));
// A short fingerprint of what the card says, for the "Ride Desk data differs from what the build published" check.
export function fingerprints(pub, staff) {
  const p = cleanPublic(pub);
  const h = s => crypto.createHash('sha256').update(s).digest('hex').slice(0, 12);
  return { pub: h(JSON.stringify(PUBLIC_FIELDS.map(k => p[k]))), staff: h(JSON.stringify(STAFF_FIELDS.map(k => cleanStaff(staff)[k]))) };
}
// Fields a card still needs (labels), for the page, the build and the weekly check.
export function missingFields(pub, staff) {
  const p = cleanPublic(pub), s = cleanStaff(staff), out = [];
  const empty = (k) => k === 'highlights' ? p.highlights.some(x => !x) : !(p[k] !== undefined ? p[k] : s[k]);
  if (p.live) for (const k of NEEDED_LIVE) if (empty(k)) out.push(LABELS[k]);
  if (p.ipad) for (const k of NEEDED_IPAD) if (empty(k) && !out.includes(LABELS[k])) out.push(LABELS[k]);
  if (p.ipad && p.photo.source === 'upload' && !p.photo.asset) out.push('Photo');
  if (p.ipad && ['link', 'ride'].includes(p.photo.source) && !p.photo.url) out.push('Photo');
  return out;
}

// ---------- keys and sealing ----------
const X25519_PKCS8 = Buffer.from('302e020100300506032b656e04220420', 'hex');
const privFromSeed = seed => crypto.createPrivateKey({ key: Buffer.concat([X25519_PKCS8, seed]), format: 'der', type: 'pkcs8' });
const pubOf = priv => crypto.createPublicKey(priv).export({ format: 'jwk' }).x;
// The build's key pair, made from the route secrets' keySalt, so nothing new has to be pasted into GitHub.
export function buildKeys(keySalt) {
  const priv = privFromSeed(crypto.createHmac('sha256', String(keySalt)).update('ride-desk sealed v1').digest());
  return { priv, pub: pubOf(priv) };
}
export function deskKeysFrom(privB64) { const priv = privFromSeed(Buffer.from(privB64, 'base64url')); return { priv, pub: pubOf(priv) }; }
export function newDeskKeys() { const seed = crypto.randomBytes(32); const k = deskKeysFrom(seed.toString('base64url')); return { ...k, privB64: seed.toString('base64url') }; }
const kdf = (shared, epk, pub) => Buffer.from(crypto.hkdfSync('sha256', shared, Buffer.from(epk + '.' + pub), Buffer.from('ride-desk v1'), 32));
export function seal(obj, pubX) {
  const pub = crypto.createPublicKey({ key: { kty: 'OKP', crv: 'X25519', x: pubX }, format: 'jwk' });
  const eph = crypto.generateKeyPairSync('x25519');
  const epk = eph.publicKey.export({ format: 'jwk' }).x;
  const key = kdf(crypto.diffieHellman({ privateKey: eph.privateKey, publicKey: pub }), epk, pubX);
  const iv = crypto.randomBytes(12), c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const plain = Buffer.from(JSON.stringify(obj));
  const data = Buffer.concat([c.update(plain), c.final(), c.getAuthTag()]);
  return { v: 1, alg: 'X25519-HKDF-SHA256-A256GCM', to: pubX, epk, iv: iv.toString('base64'), data: data.toString('base64'),
    sum: crypto.createHash('sha256').update(plain).digest('hex').slice(0, 16) };
}
export function unseal(env, priv) {
  const pubX = pubOf(priv);
  if (env.to !== pubX) throw new Error('sealed for a different key');
  const epk = crypto.createPublicKey({ key: { kty: 'OKP', crv: 'X25519', x: env.epk }, format: 'jwk' });
  const key = kdf(crypto.diffieHellman({ privateKey: priv, publicKey: epk }), env.epk, pubX);
  const raw = Buffer.from(env.data, 'base64'), iv = Buffer.from(env.iv, 'base64');
  const d = crypto.createDecipheriv('aes-256-gcm', key, iv);
  d.setAuthTag(raw.subarray(raw.length - 16));
  return JSON.parse(Buffer.concat([d.update(raw.subarray(0, raw.length - 16)), d.final()]).toString('utf8'));
}

// ---------- reading the Ride Desk in the build ----------
// Returns every card as a route entry (the shape config/routes.json had, plus the card), the staff sections and the
// privacy codes. keySalt opens the sealed file; without it (or if it will not open) staff and codes are empty and say why.
export function loadDesk(root, keySalt) {
  const pubFile = JSON.parse(fs.readFileSync(path.join(root, PUBLIC_FILE), 'utf8'));
  const problems = [], keys = readJson(path.join(root, KEY_FILE), {});
  let staff = {}, privacy = {}, sealedOk = false, bk = null;
  if (keySalt) {
    bk = buildKeys(keySalt);
    if (keys.build !== bk.pub) problems.push(`ride desk: ${KEY_FILE} "build" is not this build's key (${bk.pub}); the settings task seals for the wrong key. Put this key in the file`);
    const env = readJson(path.join(root, PRIVATE_FILE), null);
    if (env) {
      try { const o = unseal(env, bk.priv); staff = o.staff || {}; privacy = o.privacy || {}; sealedOk = true; }
      catch (e) { problems.push(`ride desk: ${PRIVATE_FILE} could not be opened (${e.message}); staff notes are left out of staff.enc.json until the settings task seals it again`); }
    } else problems.push(`ride desk: ${PRIVATE_FILE} is missing, so staff notes are not in staff.enc.json`);
  }
  const entries = Object.entries(pubFile.rides || {}).map(([slug, r]) => {
    const c = cleanPublic(r);
    return Object.assign({}, c, { slug, rwgps: Number(r.rwgps), rev: r.rev || 1, activity: r.activity || defaultActivity(c.type), active: c.live,
      websitePage: r.websitePage || null, found: r.found || null, rwgpsName: r.rwgpsName || '', photoFile: r.photo && r.photo.file || null });
  });
  return { entries, staff, privacy, sealedOk, problems, deskRev: pubFile.deskRev || 0, buildPub: bk && bk.pub, deskPub: keys.desk || null };
}

// ---------- the settings task's side ----------
function dbDocs(dir, coll) {
  const d = path.join(dir, coll);
  if (!fs.existsSync(d)) return {};
  return Object.fromEntries(fs.readdirSync(d).filter(f => f.endsWith('.json')).map(f => [f.slice(0, -5), readJson(path.join(d, f))]));
}
async function siteJson(file) {
  const r = await fetch(SITE + file + '?t=' + Date.now(), { cache: 'no-store' });
  if (!r.ok) throw new Error(`${file}: ${r.status}`);
  return r.json();
}

// apply: the saved cards (db rides/*) and privacy codes (db private/codes) into config/ride-desk.json and the sealed file.
// A card's uploaded photo is copied in from --assets <dir> (files named <asset id>.<ext>, saved by the task with the
// Artifact tool) as config/ride-photos/<slug>.<ext>. Prints what changed and anything the task must still do.
async function apply(dbDir, assetsDir) {
  const cards = dbDocs(dbDir, 'rides');
  const codes = (dbDocs(dbDir, 'private').codes || {}).codes || {};
  const file = readJson(PUBLIC_FILE);
  const before = JSON.stringify(file);
  const report = { changed: [], added: [], photos: [], needAssets: [], problems: [] };
  const staff = {};
  for (const [slug, card] of Object.entries(cards)) {
    if (!/^[a-z0-9-]+$/.test(slug)) { report.problems.push(`card ${slug}: not a usable name`); continue; }
    const old = file.rides[slug];
    const pub = cleanPublic(card);
    const keep = old ? Object.fromEntries(CLAUDE_FIELDS.filter(k => old[k] !== undefined).map(k => [k, old[k]])) : {};
    if (!old) {
      if (!card.rwgps) { report.problems.push(`card ${slug}: no Ride with GPS route`); continue; }
      Object.assign(keep, { rwgps: Number(card.rwgps), rev: 1, activity: defaultActivity(pub.type), found: card.found || null, rwgpsName: str(card.rwgpsName) });
      report.added.push(slug);
    }
    if (old && pub.type && old.type && old.type !== pub.type) keep.activity = defaultActivity(pub.type);
    // photo: an upload is copied into the repo so the sheets can use it
    if (pub.photo.source === 'upload' && pub.photo.asset) {
      const was = old && old.photo && old.photo.asset === pub.photo.asset && old.photo.file && fs.existsSync(path.join(ROOT, old.photo.file)) ? old.photo.file : null;
      if (was) pub.photo.file = was;
      else {
        const f = assetsDir && fs.existsSync(assetsDir) ? fs.readdirSync(assetsDir).find(x => x.startsWith(pub.photo.asset + '.')) : null;
        if (f) {
          const ext = (path.extname(f) || '.jpg').toLowerCase();
          const rel = `config/ride-photos/${slug}${ext}`;
          fs.mkdirSync(path.join(ROOT, 'config/ride-photos'), { recursive: true });
          for (const x of fs.readdirSync(path.join(ROOT, 'config/ride-photos'))) if (x.startsWith(slug + '.')) fs.rmSync(path.join(ROOT, 'config/ride-photos', x));
          fs.copyFileSync(path.join(assetsDir, f), path.join(ROOT, rel));
          pub.photo.file = rel; report.photos.push(slug);
        } else { report.needAssets.push({ slug, asset: pub.photo.asset }); if (old && old.photo) pub.photo = old.photo; }
      }
    }
    const next = {};   // always the same key order, so an unchanged card never rewrites the file
    for (const k of CLAUDE_FIELDS) if (keep[k] !== undefined) next[k] = keep[k];
    for (const k of PUBLIC_FIELDS) next[k] = pub[k];
    if (!old || canonDeep(old) !== canonDeep(next)) { if (old) report.changed.push(slug); file.rides[slug] = next; }
    staff[slug] = cleanStaff(card);
  }
  // rides on the desk that were removed from the page's data are kept (never deleted here); a ride is switched off instead
  for (const slug of Object.keys(file.rides)) if (!cards[slug]) report.problems.push(`card ${slug} is in ${PUBLIC_FILE} but not on the Ride Desk; left as it is`);
  const deskRev = Math.max(0, ...Object.values(cards).map(c => Number(c.rev) || 0));
  if (deskRev > (file.deskRev || 0)) file.deskRev = deskRev;
  if (JSON.stringify(file) !== before) { file.updated = new Date().toISOString(); writeJson(PUBLIC_FILE, file); report.wrotePublic = true; }
  // sealed: staff sections and privacy codes, only when they changed (the envelope's sum is of the plain text)
  const keys = readJson(KEY_FILE, {});
  if (!keys.build) report.problems.push(`${KEY_FILE} has no build key yet: the staff notes are not sealed (the first build after this change publishes it at ${SITE}desk-key.json)`);
  else {
    const privacy = Object.fromEntries(Object.entries(codes).filter(([, v]) => typeof v === 'string' && /^[A-Za-z0-9]{8,64}$/.test(v)));
    const plain = { staff: Object.fromEntries(Object.keys(staff).sort().map(k => [k, staff[k]])), privacy: Object.fromEntries(Object.keys(privacy).sort().map(k => [k, privacy[k]])) };
    const sum = crypto.createHash('sha256').update(JSON.stringify(plain)).digest('hex').slice(0, 16);
    const old = readJson(PRIVATE_FILE, null);
    if (!old || old.sum !== sum || old.to !== keys.build) { writeJson(PRIVATE_FILE, seal(plain, keys.build)); report.wrotePrivate = true; }
  }
  console.log(JSON.stringify(report, null, 1));
}

// published: what the build worked out for each card (numbers, places in ride order with their Story Library entry, photos to
// pick from, the fingerprints it used) as the page's published/rides record, and the Story Library stories it points at as
// published/stories. Written by the settings task, read by the page.
async function published(dbDir, outDir) {
  const desk = await siteJson('desk.json');
  let photos = {}; try { photos = await siteJson('ride-sheets/photos.json'); } catch (e) {}
  const rides = {};
  for (const [slug, r] of Object.entries(desk.rides || {})) rides[slug] = Object.assign({}, r, { photo: photos.rides && photos.rides[slug] || null });
  for (const [slug, c] of Object.entries(desk.cards || {})) if (rides[slug]) rides[slug].fp = c.fp;
  const out = { built: desk.built, deskRev: desk.deskRev || 0, rides };
  const stories = { built: desk.built, stories: desk.stories || {} };
  fs.mkdirSync(path.join(outDir, 'published'), { recursive: true });
  const old = dbDocs(dbDir, 'published');
  const same = (a, b) => JSON.stringify(a && { ...a, built: 0 }) === JSON.stringify(b && { ...b, built: 0 });
  const write = [];
  if (!same(old.rides, out)) { writeJson(path.join(outDir, 'published', 'rides.json'), out); write.push('published/rides'); }
  if (!same(old.stories, stories)) { writeJson(path.join(outDir, 'published', 'stories.json'), stories); write.push('published/stories'); }
  console.log(JSON.stringify({ write, rides: Object.keys(rides).length, bytes: JSON.stringify(out).length }));
}

// links: the build seals every live ride's customer link, route code and staff check link to the Ride Desk's key
// (links.enc.json); opened here with the desk's private key (db private/keys) for the page's routes/links record.
async function links(dbDir, outFile) {
  const k = (dbDocs(dbDir, 'private').keys || {}).x25519;
  if (!k) throw new Error('no private/keys record on the Ride Desk');
  const env = await siteJson('links.enc.json');
  const o = unseal(env, deskKeysFrom(k).priv);
  const old = (dbDocs(dbDir, 'routes').links || {}).links || {};
  const next = Object.assign({}, old);
  for (const [slug, v] of Object.entries(o.links || {})) next[slug] = { code: v.code, link: v.link };
  const changed = JSON.stringify(Object.keys(next).sort().map(s => [s, next[s]])) !== JSON.stringify(Object.keys(old).sort().map(s => [s, old[s]]));
  if (changed) writeJson(outFile, { links: next, updatedAt: new Date().toISOString() });
  console.log(JSON.stringify({ changed, rides: Object.keys(next).length }));
}

// scan: new routes in the Ride with GPS organisation account become "New, hidden" cards; codes go to private/codes.
async function scan(dbDir, scanFile, outDir) {
  const s = readJson(scanFile);
  if (s.scan !== 'ride-desk' || !Array.isArray(s.routes)) throw new Error('not a Ride Desk scan');
  const cards = dbDocs(dbDir, 'rides');
  const byId = new Map(Object.entries(cards).map(([slug, c]) => [Number(c.rwgps), slug]));
  const codes = Object.assign({}, (dbDocs(dbDir, 'private').codes || {}).codes || {});
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Australia/Brisbane' });
  const added = [], newCodes = [];
  fs.mkdirSync(path.join(outDir, 'rides'), { recursive: true });
  const taken = new Set(Object.keys(cards));
  for (const r of s.routes) {
    if (r.code && codes[r.id] !== r.code) { codes[r.id] = r.code; newCodes.push(r.id); }
    if (byId.has(Number(r.id))) continue;
    let base = String(r.name || 'ride').toLowerCase().replace(/\bself[- ]guided( tour)?\b/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48) || 'ride';
    let slug = base, n = 2; while (taken.has(slug)) slug = `${base}-${n++}`;
    taken.add(slug);
    // a new card starts from what Ride with GPS has: its name and description (the Ride Desk is the master from then on)
    const card = Object.assign(cleanPublic({ status: 'new', description: r.description || '', sheetNote: 'Riding time is time on the bike. Allow extra for stops and breaks.' }),
      { rwgps: Number(r.id), rwgpsName: r.name || '', appName: r.name || '', found: today,
      rwgpsVisibility: r.visibility, rwgpsDistance: r.distance, rwgpsGain: r.gain, staff: cleanStaff({}) });
    writeJson(path.join(outDir, 'rides', slug + '.json'), card);
    added.push({ slug, rwgps: r.id, name: r.name });
  }
  if (newCodes.length) writeJson(path.join(outDir, 'private', 'codes.json'), { codes, updatedAt: new Date().toISOString() });
  writeJson(path.join(outDir, 'desk', 'scan.json'), { at: s.at, routes: s.routes.length, added: added.map(a => a.slug), checkedAt: new Date().toISOString() });
  console.log(JSON.stringify({ routes: s.routes.length, added, newCodes: newCodes.length }));
}

// check: the weekly drift check for the Ride Desk (Drift Check Register, Ride Guide routes tab).
async function check(dbDir) {
  const cards = dbDocs(dbDir, 'rides'), pubd = (dbDocs(dbDir, 'published').rides) || null;
  const settings = dbDocs(dbDir, 'settings'), status = settings.status || {}, current = settings.current || {};
  const scanDoc = dbDocs(dbDir, 'desk').scan || null;
  const issues = [], fix = [], today = new Date();
  let desk = null; try { desk = await siteJson('desk.json'); } catch (e) { issues.push({ kind: 'site', text: 'desk.json did not load from the Ride Guide site: ' + e.message }); }
  let photos = null; try { photos = (await siteJson('ride-sheets/photos.json')).rides || {}; } catch (e) { issues.push({ kind: 'site', text: 'ride-sheets/photos.json did not load, so ride photos were not checked' }); }
  const applied = (status.appliedRev || 0) >= (current.rev || 0);
  for (const [slug, c] of Object.entries(cards)) {
    if (isTest(slug)) continue;
    const p = cleanPublic(c), name = c.title || c.appName || slug;
    const miss = missingFields(c, c.staff);
    if (miss.length) issues.push({ kind: 'empty', slug, text: `${name}: ${miss.join(', ')} ${miss.length === 1 ? 'is' : 'are'} empty on the Ride Desk` });
    if (photos && p.ipad && p.live) {
      const ph = photos[slug];
      if (!ph || ph.source === 'placeholder') issues.push({ kind: 'photo', slug, text: `${name}: no photo on its ride sheet (the website page has none, and none is picked on the Ride Desk)` });
    }
    if (p.status === 'new' && c.found) {
      const days = Math.floor((today - new Date(c.found + 'T00:00:00+10:00')) / 864e5);
      if (days > 14) issues.push({ kind: 'new', slug, text: `${c.rwgpsName || name}: new on Ride with GPS ${days} days ago and still hidden on the Ride Desk` });
    }
    if (desk && applied) {
      const pc = (desk.cards || {})[slug], built = (desk.rides || {})[slug], f = fingerprints(c, c.staff);
      let why = '';
      if (!pc) why = 'not in the last build at all';
      else if (pc.fp.pub !== f.pub) why = 'its details differ from what the last build used';
      else if (desk.staffOk !== false && pc.fp.staff !== f.staff) why = 'its staff section differs from what the last build used';
      else if (p.live && !built && !isTest(slug)) why = 'switched on, but the Ride Guide could not build it (see health.json)';
      else if (!p.live && built) why = 'switched off, but still in the Ride Guide';
      if (why) { issues.push({ kind: 'differs', slug, text: `${name}: ${why}` }); if (!/could not build/.test(why)) fix.push(slug); }
    }
  }
  if (desk && desk.staffOk === false) issues.push({ kind: 'sealed', text: 'The build could not open the Ride Desk staff notes (config/ride-desk-private.enc.json)' });
  if (!applied) issues.push({ kind: 'pending', text: `Ride Desk rev ${current.rev} saved, rev ${status.appliedRev || 0} live` });
  if (!scanDoc || (today - new Date(scanDoc.at || 0)) > 3 * 864e5) issues.push({ kind: 'scan', text: 'Ride with GPS has not been checked for new rides for more than 3 days' });
  if (pubd && desk && pubd.built !== desk.built && (today - new Date(desk.built)) > 864e5) issues.push({ kind: 'published', text: 'The numbers and places on the Ride Desk are older than the last build' });
  console.log(JSON.stringify({ checked: Object.keys(cards).length, issues, rerunSettingsTask: fix.length > 0 || !applied }, null, 1));
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const [cmd, ...a] = process.argv.slice(2);
  const opt = (n) => { const i = a.indexOf(n); return i >= 0 ? a[i + 1] : null; };
  const run = { apply: () => apply(a[0], opt('--assets')), published: () => published(a[0], a[1]), links: () => links(a[0], a[1]),
    check: () => check(a[0]), scan: () => scan(a[0], a[1], a[2]) }[cmd];
  if (!run) { console.error('usage: node scripts/ride-desk.mjs apply|published|links|check|scan ...'); process.exit(2); }
  run().catch(e => { console.error(e.message || e); process.exit(1); });
}
