// A plain page to read the Story Library: library.html on the Ride Guide site (not indexed). Read only; the library
// itself is changed in library/ in the repo.
const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const BRAND = { bikeon: 'Bike On blog', beo: 'By Earth and Ocean blog' };
const KIND = { place: 'Places', stop: 'Kayak tour stops', wildlife: 'Wildlife' };
// blog paragraphs are trusted library HTML limited to links, bold and italics
const safeHtml = s => String(s || '').replace(/<(?!\/?(a|strong|em|b|i)\b)[^>]*>/gi, '').replace(/\son\w+="[^"]*"/gi, '');

function entry(e) {
  const parts = [];
  for (const [b, s] of Object.entries(e.blog || {})) parts.push(`<h4>${BRAND[b] || b}: ${esc(s.heading)}</h4>${(s.paras || []).map(p => `<p>${safeHtml(p)}</p>`).join('')}`);
  for (const [b, pins] of Object.entries(e.pins || {})) for (const p of pins) parts.push(`<h4>Ride with GPS pin (${b === 'beo' ? 'By Earth and Ocean' : 'Bike On'}): ${esc(p.name)}</h4><p class="said">${esc(p.text)}</p>`);
  if ((e.story || []).length) parts.push(`<h4>Spoken story</h4>${e.story.map(p => `<p class="said">${esc(p)}</p>`).join('')}`);
  if (e.talk) parts.push(`<h4>Guide talking points${e.tours ? ', stop ' + Object.values(e.tours).join(', ') : ''}</h4><ul>${(e.talk.points || []).map(p => `<li>${esc(p)}</li>`).join('')}</ul>${e.talk.detail ? `<p>${esc(e.talk.detail)}</p>` : ''}`);
  if (e.card) {
    const c = e.card;
    parts.push(`<h4>Wildlife card</h4>${c.photo_url ? `<img src="${esc(c.photo_url)}" alt="${esc(c.name)}" loading="lazy">` : ''}`
      + `<p><em>${esc(c.scientific_name || '')}</em>${c.local_name ? ' · ' + esc(c.local_name) : ''}${c.conservation ? ' · ' + esc(c.conservation) : ''}</p>`
      + `<p>${esc(c.description || '')}</p>${(c.detail || []).map(d => d.items ? `<ul>${d.items.map(i => `<li>${esc(i)}</li>`).join('')}</ul>` : `<p>${esc(String(d.text || '').replace(/\*\*/g, ''))}</p>`).join('')}`
      + (c.how_to_spot ? `<p><strong>How to spot:</strong> ${esc(c.how_to_spot)}</p>` : ''));
  }
  const used = [e.blog && Object.keys(e.blog).map(b => BRAND[b]).join(', '), e.pins && 'Ride Guide and Ride with GPS', (e.story || []).length && 'natural voice and Know Noosa', e.card && 'EO Crew wildlife card', e.talk && 'EO Crew tour manual'].filter(Boolean).join(' · ');
  return `<details id="${esc(e.key)}" data-k="${esc((e.title + ' ' + e.key).toLowerCase())}"><summary><span>${esc(e.title)}</span><small>${esc(used)}</small></summary><div class="body">${parts.join('')}<p class="meta">Key ${esc(e.key)} · updated ${esc(e.updated || '')}</p></div></details>`;
}

export function libraryPage(lib) {
  const groups = Object.keys(KIND).map(k => {
    const list = lib.entries.filter(e => e.kind === k).sort((a, b) => a.title.localeCompare(b.title));
    return list.length ? `<h2>${KIND[k]} <small>${list.length}</small></h2>${list.map(entry).join('')}` : '';
  }).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<title>Story Library</title><style>
:root{--ink:#1d2b36;--muted:#5d6b75;--line:#dde3e7;--bg:#f7f9fa;--card:#fff;--accent:#0f6e56}
@media (prefers-color-scheme:dark){:root{--ink:#e8edf0;--muted:#a3b0b8;--line:#2e3a42;--bg:#12181c;--card:#1a2228;--accent:#5dcaa5}}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:32px 0 8px}h2 small{color:var(--muted);font-weight:400}
.lead{color:var(--muted);margin:0 0 16px}input{width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;margin:8px 0}summary{cursor:pointer;padding:12px 14px;display:flex;flex-direction:column;gap:2px}
summary span{font-weight:600}summary small{color:var(--muted)}.body{padding:0 14px 12px}h4{margin:16px 0 4px;font-size:14px;color:var(--accent)}
.said{border-left:3px solid var(--line);padding-left:10px}img{max-width:220px;border-radius:8px}.meta{color:var(--muted);font-size:13px}a{color:var(--accent)}
</style></head><body><main><h1>Story Library</h1>
<p class="lead">Every Element Outdoors story in one place: the blog sections, the lines read out at each pin, the spoken stories, the kayak talking points and the wildlife cards. The blogs, the Ride Guide, Ride with GPS and EO Crew are all copies of this. ${lib.entries.length} entries, built ${esc(lib.built.slice(0, 10))}.</p>
<input id="q" type="search" placeholder="Find a place or animal" aria-label="Find a place or animal">${groups}</main>
<script>(function(){var h=decodeURIComponent(location.hash.slice(1));var d=h&&document.getElementById(h);if(d&&d.tagName==='DETAILS'){d.open=true;d.scrollIntoView();}})();document.getElementById('q').addEventListener('input',e=>{const q=e.target.value.toLowerCase().trim();document.querySelectorAll('details').forEach(d=>{d.style.display=!q||d.dataset.k.includes(q)?'':'none'})})</script></body></html>`;
}
