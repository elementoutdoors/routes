// Story Library -> ride story blog. Paste into the javascript tool on a wp-admin page of the blog being changed
// (bikeon.com.au or byearthandocean.com.au, signed in), with ITEMS set to that brand's entries from
// `node scripts/library.mjs plan` (its "blog" list, filtered to the brand). It changes the same words in the post content
// and in the Elementor data, then the runbook opens the post in Elementor and saves once every section has loaded.
// Returns what it did. Nothing is changed unless every item is found.
// Version 1 (11/10/2026).
const ITEMS = [];   // <- paste the plan's blog items for this brand here
const SLUG = { 'bikeon.com.au': 'noosa-self-guided-rides-what-you-will-see', 'byearthandocean.com.au': 'noosa-hinterland-self-guided-rides-places' }[location.host.replace(/^www\./, '')];
const nonce = window.wpApiSettings && wpApiSettings.nonce;
if (!nonce) throw new Error('not signed in to WordPress on this site');
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const sectionHtml = it => `<h3 id="${it.key}" style="scroll-margin-top:120px">${esc(it.heading)}</h3>` + it.paras.map(p => `<p>${p}</p>`).join('');
// The section is the h3 with the place's id and the paragraphs straight after it (never the "Area n of 8" label).
function findSection(html, key) {
  const m = html.match(new RegExp(`<h3[^>]*\\bid="${key}"[^>]*>[\\s\\S]*?<\\/h3>`));
  if (!m) return null;
  let end = m.index + m[0].length;
  const re = /\s*<p\b([^>]*)>[\s\S]*?<\/p>/y;
  for (;;) { re.lastIndex = end; const p = re.exec(html); if (!p || /bo-eb|bo-ride-it/.test(p[1])) break; end = re.lastIndex; }
  return { start: m.index, end };
}
// A new section goes straight after the section it follows, or at the end of its area (before the next "Area" label or h2).
function insertAt(html, it) {
  if (it.after) { const s = findSection(html, it.after); if (s) return s.end; }
  const a = html.match(new RegExp(`<h2[^>]*\\bid="${it.area}"[^>]*>`));
  if (!a) return -1;
  const rest = html.slice(a.index + a[0].length);
  const next = rest.search(/<p class="bo-eb"|<h2\b/);
  return next < 0 ? html.length : a.index + a[0].length + next;
}
function apply(html, it) {
  if (it.action === 'replace') { const s = findSection(html, it.key); return s ? html.slice(0, s.start) + sectionHtml(it) + html.slice(s.end) : null; }
  if (findSection(html, it.key)) return null;   // already there
  const at = insertAt(html, it); return at < 0 ? null : html.slice(0, at) + sectionHtml(it) + html.slice(at);
}
const post = (await (await fetch(`/wp-json/wp/v2/posts?slug=${SLUG}&context=edit&_fields=id,content,meta`, { headers: { 'X-WP-Nonce': nonce } })).json())[0];
let content = post.content.raw;
const data = JSON.parse(post.meta._elementor_data);
const widgets = []; (function walk(els) { for (const e of els) { if (e.settings && typeof e.settings.editor === 'string') widgets.push(e); walk(e.elements || []); } })(data);
const done = [], failed = [];
for (const it of ITEMS) {
  const c2 = apply(content, it);
  const w = widgets.find(x => findSection(x.settings.editor, it.action === 'replace' ? it.key : it.after || '\u0000'))
    || (it.action === 'insert' && widgets.find(x => new RegExp(`id="${it.area}"`).test(x.settings.editor)));
  const e2 = w ? apply(w.settings.editor, it) : null;
  if (c2 === null || e2 === null) { failed.push(it.key); continue; }
  content = c2; w.settings.editor = e2; done.push(`${it.action} ${it.key}`);
}
if (failed.length) JSON.stringify({ changed: false, failed, note: 'nothing saved; a section could not be found in the post or in its Elementor data' });
else {
  const r = await fetch(`/wp-json/wp/v2/posts/${post.id}`, { method: 'POST', headers: { 'X-WP-Nonce': nonce, 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, meta: { _elementor_data: JSON.stringify(data) } }) });
  JSON.stringify({ changed: r.ok, status: r.status, post: post.id, done, next: `open /wp-admin/post.php?post=${post.id}&action=elementor, wait for every section, then $e.run('document/save/update', {force: true})` });
}
