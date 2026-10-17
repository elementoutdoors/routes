// Route health check, run weekly by the Element Outdoors drift check.
// Reads the live health.json, then checks that the site was rebuilt recently, every route opens,
// every stop and offer link still works, every photo loads, and nothing is untranslated.
// Prints a JSON report. Exit code 0 = all good, 1 = something needs attention.
// Version 7 (11/10/2026): also checks stories-voice.json (every full story published for the EO Crew staff app, with its recordings loading).
// Version 8 (11/10/2026): the Story Library (library/) is the master. Every live blog section or pin that differs from it is listed in "push" (from scripts/library.mjs plan) for the run to put back; house rule findings in the library are listed in "houseRules" for Ben.
// Version 6 (11/10/2026): also checks the places record (health.json "places"): every blog section and stop summary that differs from the agreed text, with before and after in "placeChanges" for the weekly check to decide; a story whose blog change is waiting on Ben is a note, not an issue.
// Version 5 (11/10/2026): also checks the full stories (every linked place has one, none out of step with its blog section, the blogs can be read) and listen.html.
// Version 4 (10/10/2026): also checks the natural voice (recording running, inside the monthly cap, recordings load). v3: every typed route code. v2: real browser user agent, redirects to another page count as broken, 403 noted not failed.
// Version 9 (17/10/2026): also checks the ride counter is built into the app and answering.
// Usage: node scripts/check.mjs [siteBase]   (route links are read from qr/links.json when present)
import fs from 'node:fs';
import { loadLibrary, plan as libraryPlan } from './library.mjs';

const BASE = (process.argv[2] || 'https://elementoutdoors.github.io/routes/').replace(/\/?$/, '/');
const issues = [], notes = [];

const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0 Safari/537.36';
const norm = u => { const x = new URL(u); return (x.host.replace(/^www\./, '') + x.pathname.replace(/\/+$/, '')).toLowerCase(); };
// status code, plus where the link really lands (a page that now redirects somewhere else is a dead link)
async function status(url, method = 'HEAD') {
  try {
    let r = await fetch(url, { method, redirect: 'follow', headers: { 'User-Agent': UA } });
    if ((r.status === 405 || r.status === 403 || r.status === 404) && method === 'HEAD') r = await fetch(url, { redirect: 'follow', headers: { 'User-Agent': UA } });
    return { code: r.status, moved: r.url && norm(r.url) !== norm(url) ? r.url : null };
  } catch (e) { return { code: 0, moved: null }; }
}

const res = await fetch(BASE + 'health.json', { cache: 'no-store' });
if (!res.ok) { console.log(JSON.stringify({ ok: false, issues: ['health.json not reachable: ' + res.status] })); process.exit(1); }
const h = await res.json();

const ageH = (Date.now() - new Date(h.built).getTime()) / 3600000;
if (ageH > 50) issues.push(`site last rebuilt ${Math.round(ageH)} hours ago (nightly rebuild may be failing)`);
h.problems.forEach(p => issues.push(p));
h.routes.forEach(r => r.warnings.filter(w => /from the route/.test(w)).forEach(w => notes.push(`${r.slug}: ${w}`)));
Object.entries(h.untranslatedTotal || {}).forEach(([l, n]) => { if (n) issues.push(`${n} strings not yet translated into ${l}`); });
(h.cueWording || []).forEach(c => issues.push(`direction still reads like cue sheet shorthand, add a rule or fix in config/cue-wording.json: "${c}"`));
// Version 9 (16/10/2026): direction check. Every flagged direction (away from the turn, a repeat, or bare) that Ben has not
// ruled on goes to the Directions Review page as a card; "bare" ones only where a named road or path is there (the run
// looks it up). Rulings he has made but Claude has not applied yet are listed as issues.
const dirs = h.directions || [];
const unruled = dirs.filter(x => !x.ruled);
if (unruled.length) notes.push(`directions: ${unruled.length} flagged directions without a ruling (${['offTurn', 'noTurn', 'repeat', 'bare'].map(k => `${unruled.filter(x => x.issue === k).length} ${k}`).join(', ')}); add cards to the Directions Review page, https://claude.ai/artifact/N62KfoVeKyuq4DLfZ114qw (cards collection; a map picture per card uploaded as an asset; bare ones only where a named road or path is there and it differs from the road before the turn), and apply Ben's rulings from its rulings collection: move, reword or remove in Ride with GPS through Ben's session, republish the Experiences, record keep rulings in config/direction-rulings.json, then set applied on the card`);
dirs.filter(x => x.ruled && x.ruled !== 'keep').forEach(x => issues.push(`direction ruled "${x.ruled}" but not applied yet: ${x.slug} at ${x.d} m, "${x.n}"`));
const directionFlags = unruled;

// natural voice: the build records new lines each night; check it is running, inside its cap, and the recordings load
const v = h.voice;
if (!v) issues.push('natural voice: no voice report in health.json (voice step not running)');
else {
  if ((v.notes || []).some(n => /GOOGLE_TTS_KEY not set/.test(n))) issues.push('natural voice: the Google key is missing from the build (GitHub secret GOOGLE_TTS_KEY)');
  if (v.charsThisMonth > v.cap) issues.push(`natural voice: ${v.charsThisMonth} characters used this month, over the ${v.cap} cap`);
  if (v.credit && v.credit.usedUsd > v.credit.usd + 1) issues.push(`natural voice: about US$${v.credit.usedUsd} of Google Cloud credit used, over the US$${v.credit.usd} allowance`);
  if (v.waiting) notes.push(`natural voice: ${v.waiting} of ${v.lines} lines still to record (phone voice covers them until then)`);
  if (v.failed) notes.push(`natural voice: ${v.failed} recordings failed in the last build`);
  try {
    const m = await (await fetch(BASE + 'voice.json', { cache: 'no-store' })).json();
    for (const [l, x] of Object.entries(m)) {
      if (l.startsWith('_')) continue;   // _say: speech rules, not recordings
      const sample = (x.pre || x.h || [])[0];
      if (!sample) { notes.push(`natural voice: no recordings yet for ${l}`); continue; }
      const s = await status(`${BASE}v/${x.tag}/${sample}.mp3`, 'GET');
      if (s.code !== 200) issues.push(`natural voice: ${l} recordings not loading (${s.code})`);
    }
  } catch (e) { issues.push('natural voice: voice.json not reachable'); }
}

// full stories: every stop linked to a blog place has a story, and each story still matches its blog section
const st = h.stories;
if (!st) issues.push('full stories: no stories report in health.json');
else {
  (st.missing || []).forEach(k => issues.push(`full stories: no story for ${k} (write one in its library entry, see config/STORY_BRIEF.md)`));
  (st.stale || []).forEach(k => notes.push(`full stories: live blog section ${k} differs from the library (put back by the push step)`));
  (st.unchecked || []).forEach(k => issues.push(`full stories: ${k} has no blog fingerprint (the library entry has a story but no blog section for that brand)`));
  (st.noSection || []).forEach(k => issues.push(`full stories: a stop links to ${k} but the blog has no such section`));
  (st.unread || []).forEach(k => notes.push(`full stories: could not read blog (${k})`));
}
// stories-voice.json: every full story (linked to a ride or not) with its recordings, read by the EO Crew staff app (Know Noosa)
try {
  const sv = await (await fetch(BASE + 'stories-voice.json', { cache: 'no-store' })).json();
  const all = Object.entries(sv.stories || {});
  if (!all.length) issues.push('stories-voice.json: no stories published');
  const waitingParas = all.reduce((n, [, x]) => n + (x.paras || []).filter(p => !p.a).length, 0);
  if (waitingParas) notes.push(`stories-voice.json: ${waitingParas} story paragraphs still to record (EO Crew uses the phone voice until then)`);
  const sample = all.flatMap(([, x]) => x.paras || []).find(p => p.a);
  if (sample) { const s = await status(BASE + sample.a, 'GET'); if (s.code !== 200) issues.push(`stories-voice.json: story recordings not loading (${s.code})`); }
} catch (e) { issues.push('stories-voice.json not reachable (EO Crew Know Noosa reads it)'); }
// Story Library: the live blogs and Ride with GPS pins must say what the library says (library/README.md).
const placeChanges = [];   // kept for older runbooks; the push list replaces it
let push = { blog: [], pins: [], notInLibrary: [], gone: [] }, houseRules = [];
const pl = h.places;
if (!pl) issues.push('story library: no places report in health.json');
else {
  try {
    push = libraryPlan(loadLibrary(), pl, JSON.parse(fs.readFileSync(new URL('../config/routes.json', import.meta.url), 'utf8')).routes);
    push.blog.forEach(b => issues.push(`story library: ${b.brand} blog section ${b.key} differs from the library, push it (scripts/push/blog.js)`));
    push.pins.forEach(p => issues.push(`story library: ${p.brand} pin "${p.name}" differs from the library, push it (scripts/push/pins.js)`));
    push.notInLibrary.forEach(n => issues.push(`story library: ${n.what} ${n.id} is live but not in the library (add it to the library if Ben meant it, else remove it)`));
    push.gone.forEach(g => issues.push(`story library: ${g.what === 'stop' ? 'pin' : 'blog section'} ${g.id} is in the library but on no ride or blog`));
  } catch (e) { issues.push('story library: could not be read (' + (e.message || e) + ')'); }
}
houseRules = (h.library || {}).houseRules || [];
if (!h.library) issues.push('story library: not built (health.json has no "library" report)');
houseRules.forEach(r => issues.push(`story library house rule: ${r.key} (${r.where}): ${r.why}`));
{ const s = await status(BASE + 'listen.html', 'GET'); if (s.code !== 200) issues.push(`voice check page listen.html not loading (${s.code})`); }

// old ride copies a POI Library pin has replaced: harmless (the app leaves them out), listed so they can be deleted in Ride with GPS
{ const n = h.routes.reduce((a, r) => a + ((r.pinsToDelete || []).length), 0); if (n) notes.push(`${n} old Ride with GPS pins can be deleted (replaced by POI Library pins; list in the project doc "Ride Guide pins to delete")`); }

const links = new Set(), photos = new Set();
h.routes.forEach(r => { (r.links || []).forEach(u => links.add(u)); (r.photos || []).forEach(u => photos.add(u)); });
for (const u of links) {
  const s = await status(u);
  if (s.code === 403 || s.code === 429) notes.push(`could not check (site blocks checkers, ${s.code}): ${u}`);
  else if (s.code === 0 || s.code >= 400) issues.push(`link not working (${s.code || 'no answer'}): ${u}`);
  else if (s.moved && !/\/(r|review)\b|g\.page|google\./.test(u + s.moved)) issues.push(`link now goes somewhere else: ${u} lands on ${s.moved}`);
}
for (const u of photos) { const s = await status(u, 'GET'); if (s.code === 0 || s.code >= 400) issues.push(`photo not loading (${s.code || 'no answer'}): ${u}`); }

// every QR link opens its route (only possible where the private link list is available)
if (fs.existsSync('qr/links.json')) {
  const q = JSON.parse(fs.readFileSync('qr/links.json', 'utf8'));
  for (const [slug, url] of Object.entries(q)) {
    const key = url.split('#')[1];
    const s = await status(`${BASE}r/${key}.json`, 'GET');
    if (s.code !== 200) issues.push(`QR code for ${slug} does not open its route (${s.code})`);
  }
}

// every typed route code opens the same route as its QR code
if (fs.existsSync('qr/codes.json') && fs.existsSync('qr/links.json')) {
  const q = JSON.parse(fs.readFileSync('qr/links.json', 'utf8'));
  const c = JSON.parse(fs.readFileSync('qr/codes.json', 'utf8'));
  for (const [slug, code] of Object.entries(c)) {
    try {
      const r = await fetch(`${BASE}c/${code}.json`, { cache: 'no-store' });
      const k = r.ok ? (await r.json()).k : null;
      if (!q[slug] || k !== q[slug].split('#')[1]) issues.push(`route code ${code} for ${slug} does not open its route`);
    } catch (e) { issues.push(`route code ${code} for ${slug} could not be checked`); }
  }
}
// ride counts (17/10/2026): the build put the counter address in the app, and the counter answers
if (!(h.counter && h.counter.on)) issues.push('ride counts: the app has no counter address, so rides are not being counted (config/counter.json)');
else {
  try {
    const cu = JSON.parse(fs.readFileSync('config/counter.json', 'utf8')).url;
    const r = await fetch(cu, { redirect: 'follow' });
    const j = r.ok ? await r.json().catch(() => null) : null;
    if (!j || j.error !== 'not allowed') issues.push(`ride counts: the counter is not answering as expected (${r.status})`);
  } catch (e) { issues.push('ride counts: the counter could not be reached (' + (e.message || e) + ')'); }
}
if (h.problems.some(p => /^settings:/.test(p))) notes.push('a value in config/settings.json was out of range and the default was used');

console.log(JSON.stringify({ ok: !issues.length, built: h.built, routes: h.routes.map(r => `${r.slug}: ${r.source}, ${r.cues} cues, ${r.stops} stops`), issues, notes, push, houseRules, placeChanges, directionFlags }, null, 1));
process.exit(issues.length ? 1 : 0);
