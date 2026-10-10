// Route health check, run weekly by the Element Outdoors drift check.
// Reads the live health.json, then checks that the site was rebuilt recently, every route opens,
// every stop and offer link still works, every photo loads, and nothing is untranslated.
// Prints a JSON report. Exit code 0 = all good, 1 = something needs attention.
// Version 2 (10/10/2026): real browser user agent, redirects to another page count as broken, 403 noted not failed.
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

console.log(JSON.stringify({ ok: !issues.length, built: h.built, routes: h.routes.map(r => `${r.slug}: ${r.source}, ${r.cues} cues, ${r.stops} stops`), issues, notes }, null, 1));
process.exit(issues.length ? 1 : 0);
