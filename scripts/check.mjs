// Route health check, run weekly by the Element Outdoors drift check.
// Reads the live health.json, then checks that the site was rebuilt recently, every route opens,
// every stop and offer link still works, every photo loads, and nothing is untranslated.
// Prints a JSON report. Exit code 0 = all good, 1 = something needs attention.
// Version 5 (11/10/2026): also checks the full stories (every linked place has one, none out of step with its blog section, the blogs can be read) and listen.html.
// Version 4 (10/10/2026): also checks the natural voice (recording running, inside the monthly cap, recordings load). v3: every typed route code. v2: real browser user agent, redirects to another page count as broken, 403 noted not failed.
// Usage: node scripts/check.mjs [siteBase]   (route links are read from qr/links.json when present)
import fs from 'node:fs';

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
  (st.missing || []).forEach(k => issues.push(`full stories: no story for ${k} (write one, see config/STORY_BRIEF.md)`));
  (st.stale || []).forEach(k => issues.push(`full stories: blog section ${k} has changed, rewrite its story (config/STORY_BRIEF.md)`));
  (st.unchecked || []).forEach(k => issues.push(`full stories: ${k} has no blog fingerprint yet (config/STORY_BRIEF.md)`));
  (st.noSection || []).forEach(k => issues.push(`full stories: a stop links to ${k} but the blog has no such section`));
  (st.unread || []).forEach(k => notes.push(`full stories: could not read blog (${k})`));
}
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
if (h.problems.some(p => /^settings:/.test(p))) notes.push('a value in config/settings.json was out of range and the default was used');

console.log(JSON.stringify({ ok: !issues.length, built: h.built, routes: h.routes.map(r => `${r.slug}: ${r.source}, ${r.cues} cues, ${r.stops} stops`), issues, notes }, null, 1));
process.exit(issues.length ? 1 : 0);
