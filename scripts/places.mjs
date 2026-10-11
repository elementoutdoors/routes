// The places record: the agreed text of every place on the ride story blogs and its Ride with GPS stop summary.
//
// Why: a blog section or a stop summary can be edited at any time. A change in wording flows straight through, but a
// change of fact (a date, a name, a number, what a place is) must not silently overwrite what Ben approved. The
// record (config/place-record.json) holds the last agreed text of each, per brand. The build compares the live
// blog and Ride with GPS against it every night and lists every difference in health.json "places"; the weekly
// check decides each one (config/STORY_BRIEF.md, "The places record").
//
// A difference with a card open on the Ride Story Review page is "pending". While a stop summary is pending, the
// app keeps reading the agreed summary from the record, so riders never hear an unruled change.
//
// Places are "<brand>#<anchor>", for example "bikeon#lake-doonella". Brand is the blog the stop's link points at.
import crypto from 'node:crypto';

export const fp = s => crypto.createHash('sha1').update(s || '').digest('hex').slice(0, 12);

export const normUrl = u => { try { const x = new URL(u); return (x.host.replace(/^www\./, '') + x.pathname.replace(/\/+$/, '')).toLowerCase(); } catch (e) { return ''; } };

export function blogList(blogs) { return Object.entries(blogs || {}).map(([brand, url]) => ({ brand, url, n: normUrl(url) })); }

// The blog place a stop links to: { brand, key, place: "brand#key" }, or null.
export function placeOf(blogs, url) {
  if (!url || !url.includes('#')) return null;
  const b = blogs.find(x => x.n === normUrl(url.split('#')[0]));
  if (!b) return null;
  const key = url.split('#')[1];
  return { brand: b.brand, key, place: b.brand + '#' + key };
}

// Each blog section as plain text: the paragraphs between a place's heading and the next heading.
const decode = t => t.replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
  .replace(/&nbsp;/g, ' ').replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
const plain = t => decode(t.replace(/<[^>]+>/g, '')).replace(/[‘’]/g, "'").replace(/[“”]/g, '"').replace(/\s+/g, ' ').trim();
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

// Read both blogs. Returns { sections: { "brand#key": text }, counts: { brand: n }, unread: [] }.
export async function readBlogs(blogs) {
  const out = { sections: {}, counts: {}, unread: [] };
  for (const b of blogs) {
    try {
      const r = await fetch(b.url, { headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0 Safari/537.36' } });
      if (!r.ok) throw new Error('HTTP ' + r.status);
      const secs = blogSections(await r.text());
      out.counts[b.brand] = Object.keys(secs).length;
      for (const [k, t] of Object.entries(secs)) out.sections[b.brand + '#' + k] = t;
    } catch (e) { out.unread.push(`${b.brand}: ${e.message || e}`); }
  }
  return out;
}

// Record layout: sections { "brand#key": entry } and stops { "brand#key|Pin name": entry },
// entry = { text, hash, agreed (date), pending (card id, while Ben decides) }. A place can have several pins
// (Mt Tinbeerwah has a welcome pin and a summit pin), so stops are kept per pin name.
export const stopId = (place, name) => place + '|' + name;

// Compare the live blog sections and stop summaries with the record.
// stops: { "brand#key|Pin name": { place, name, text, rides: [slug] } } as Ride with GPS has them now (before any hold).
// unreadBrands: brands whose blog could not be read this time (their sections are not judged).
export function comparePlaces(record, sections, stops, unreadBrands = []) {
  const recS = (record && record.sections) || {}, recP = (record && record.stops) || {};
  const rep = { recorded: { sections: Object.keys(recS).length, stops: Object.keys(recP).length }, changed: [], unrecorded: [], gone: [], held: [] };
  const usedPlaces = new Set(Object.values(stops).map(s => s.place));
  const look = (what, id, now, extra) => {
    const r = (what === 'section' ? recS : recP)[id];
    if (r && typeof r.text === 'string') {
      if (fp(now) !== r.hash) rep.changed.push(Object.assign({ what, id, before: r.text, after: now, pending: r.pending || null }, extra));
    } else rep.unrecorded.push(Object.assign({ what, id, text: now }, extra));
  };
  for (const [place, text] of Object.entries(sections)) {
    // only places the rides use or the record already holds; other headings on the blog are not places
    if (usedPlaces.has(place) || recS[place]) look('section', place, text, { place });
  }
  for (const [id, s] of Object.entries(stops)) look('stop', id, s.text, { place: s.place, name: s.name, rides: s.rides });
  for (const id of Object.keys(recS)) if (sections[id] === undefined && !unreadBrands.includes(id.split('#')[0])) rep.gone.push({ what: 'section', id });
  for (const id of Object.keys(recP)) if (!stops[id]) rep.gone.push({ what: 'stop', id });
  return rep;
}

// While a stop summary has a card open, the app keeps the agreed summary. Returns the stop ids held on this route.
export function holdStops(route, record, blogs, isVariant) {
  const held = [];
  const recP = (record && record.stops) || {};
  for (const s of route.stops) {
    const p = placeOf(blogs, s.url);
    if (!p || isVariant(s)) continue;
    const id = stopId(p.place, s.name), r = recP[id];
    if (!r || !r.pending || typeof r.text !== 'string') continue;
    if ((s.text || '') !== r.text) { s.text = r.text; held.push(id); }
  }
  return held;
}
