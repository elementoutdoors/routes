// Natural voice for the Ride Guide.
// Every line the app speaks is recorded once per language with Google's natural voices (Chirp 3 HD) and published
// with the site. The app plays the recording when it has one and falls back to the phone's own voice when it does not.
//
// Recordings are kept between builds in the voice cache (the voice-cache branch, checked out at VOICE_CACHE), so only new
// or changed lines are ever paid for. A monthly character cap keeps use inside Google's free allowance: once the month's cap
// is reached, the remaining lines wait for next month and the phone voice covers them in the meantime.
//
// Env: GOOGLE_TTS_KEY (Text-to-Speech only key), VOICE_CACHE (folder, default .voice-cache).
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const VOICE_LANGS = { en: 'en-AU', de: 'de-DE', fr: 'fr-FR', es: 'es-ES', it: 'it-IT', nl: 'nl-NL', zh: 'cmn-CN', ja: 'ja-JP', ko: 'ko-KR' };
const ORDER = ['en', 'de', 'fr', 'es', 'it', 'nl', 'zh', 'ja', 'ko'];
const MAX_BYTES = 4800;   // Google's limit is 5000 bytes of text per request

// How written text is said aloud (config/speech.json): abbreviations, units and symbols, plus respellings for names
// the voice gets wrong. The screen keeps the written text. The app applies the same rules to the phone voice.
let SPEECH = { rules: [], names: {}, pronounce: {} };
export function loadSpeech(root) {
  try { SPEECH = JSON.parse(fs.readFileSync(path.join(root, 'config', 'speech.json'), 'utf8')); } catch (e) { SPEECH = { rules: [], names: {}, pronounce: {} }; }
  SPEECH.rules = (SPEECH.rules || []).filter(r => { try { new RegExp(r.find, 'g'); return true; } catch (e) { return false; } });
  SPEECH.names = SPEECH.names || {};
  SPEECH.pronounce = Object.fromEntries(Object.entries(SPEECH.pronounce || {}).filter(([k, x]) => !k.startsWith('_') && x && typeof x.ipa === 'string' && x.ipa));
  return SPEECH;
}
// Exact pronunciations for the natural voice (speech.json "pronounce": a word, its IPA, the languages it applies to, and a
// respelling used only if Google refuses the pronunciation). Sent to Google with each line that contains the word, so the
// written text never changes. Version 1 (11/10/2026, Ben: the voice said Noosa as "Nysa").
// whole word in Latin script (Chinese, Japanese and Korean text runs straight on from a name, so only Latin letters count)
const wordRe = w => new RegExp('(^|[^\\p{Script=Latin}])' + w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?![\\p{Script=Latin}])', 'u');
// A language can have its own IPA (Google checks the sounds against that language) or only a respelling ("ipa": null),
// where Google wants another spelling system (Chinese pinyin, Japanese kana) or refuses the sounds.
export function pronunciations(lang, spoken) {
  return Object.entries(SPEECH.pronounce).filter(([w, x]) => (!x.langs || x.langs.includes(lang)) && wordRe(w).test(spoken)).map(([w, x]) => {
    const o = Object.assign({ ipa: x.ipa, respell: x.respell || null }, (x.lang || {})[lang] || {});
    return { phrase: w, ipa: o.ipa || null, respell: o.respell || null };
  });
}
function respelled(text, prons) {
  for (const p of prons) if (p.respell) text = text.replace(new RegExp(wordRe(p.phrase).source, 'gu'), (m, pre) => pre + p.respell);
  return text;
}
export function speakable(lang, text) {
  let t = String(text || '');
  for (const r of SPEECH.rules) if (!r.langs || r.langs.includes(lang)) t = t.replace(new RegExp(r.find, 'g'), r.say);
  for (const [n, say] of Object.entries(SPEECH.names)) t = t.replace(new RegExp('\\b' + n.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b', 'g'), say);
  return t.trim();
}

// Spoken lines that are not route content. Every say(...) line in site/app.js must be here or in TEMPLATES;
// the build checks this and reports any gap in health.json.
export const PHRASES = [
  "Let's ride. Follow the line on the map and listen for directions.",
  'Welcome back. Picking up where you left off.',
  'Your ride is paused. Tap Resume when you are ready to keep going.',
  'Ride paused. Directions are off until you tap Resume.',
  'Ride resumed.',
  'Back on route.',
  'You may be riding the route backwards. Check the arrows on the line.',
  "You're off the route. Please use the map on your screen to make your way back to the route line. If you're taking a break, tap Pause.",
  'Caution.',
  'Then',
  'You have reached a point of interest.',
  'You have finished the ride. Thanks for riding with us.',
  'Voice on.',
  'Keep this screen open while you ride. Locking your phone stops the directions.',
  'Directions stopped while your phone was locked. Keep this screen open while you ride.'
];
// Lines with a distance in them. "full" is recorded for every distance the app can say; "near" only for distances up to 3 km / 2 miles.
export const TEMPLATES = [
  { t: 'In {dist},', range: 'full' },
  { t: "You're still off the route. The route line is {dist} away.", range: 'near' },
  { t: 'The start of the route is {dist} away. Head to the green marker.', range: 'near' }
];
export const NAME_TEMPLATES = ['Rider offer nearby: {name}', 'Rider offer when you get back: {name}'];
export const UNIT_STRINGS = ['{n} metres', '{n} kilometre', '{n} kilometres', '{n} feet', '{n} mile', '{n} miles'];

// Same hash as the app (site/app.js voiceHash): two FNV-1a 32-bit passes over the UTF-16 code units.
export function voiceHash(s) {
  let a = 0x811c9dc5, b = 0x01000193 ^ 0x5bd1e995;
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    a ^= c; a = Math.imul(a, 0x01000193) >>> 0;
    b ^= c; b = Math.imul(b, 0x01000193) >>> 0; b ^= b >>> 13;
  }
  return (a >>> 0).toString(16).padStart(8, '0') + (b >>> 0).toString(16).padStart(8, '0');
}
const fill = (s, o) => s.replace(/\{(\w+)\}/g, (_, k) => (o[k] != null ? o[k] : ''));
const num = n => String(n);   // matches JS number-to-string in the app

// Every distance phrase the app can produce (mirrors distParts in site/app.js)
function distancePhrases(tr, range) {
  const out = [];
  const T = s => tr(s);
  // metric (metres are tagged so the common turn warnings can be recorded first)
  for (let r = 10; r <= 90; r += 10) out.push({ d: fill(T('{n} metres'), { n: r }), m: r });
  for (let r = 100; r <= 950; r += 50) out.push({ d: fill(T('{n} metres'), { n: r }), m: r });
  out.push(fill(T('{n} kilometre'), { n: 1 }));
  const kmTop = range === 'full' ? 9.9 : 3;
  for (let k = 11; k <= kmTop * 10 + 0.001; k++) { const v = Math.round(k) / 10; out.push(fill(T(v === 1 ? '{n} kilometre' : '{n} kilometres'), { n: num(v) })); }
  if (range === 'full') for (let k = 10; k <= 30; k++) out.push(fill(T('{n} kilometres'), { n: k }));
  // imperial
  for (let f = 10; f <= 530; f += 10) out.push(fill(T('{n} feet'), { n: f }));
  const miTop = range === 'full' ? 9.9 : 2;
  for (let m = 1; m <= miTop * 10 + 0.001; m++) { const v = Math.round(m) / 10; out.push(fill(T(v === 1 ? '{n} mile' : '{n} miles'), { n: num(v) })); }
  if (range === 'full') for (let m = 10; m <= 30; m++) out.push(fill(T('{n} miles'), { n: m }));
  const seen = new Set();
  return out.map(x => (typeof x === 'string' ? { d: x, m: null } : x)).filter(x => !seen.has(x.d) && seen.add(x.d));
}

// Lines to record, highest priority first, as { lang, text, group }
export function wantedLines({ routes, i18n, langs, stories }) {
  const tr = l => s => (l === 'en' ? s : (i18n[l] && i18n[l][s]) || s);
  const has = (l, s) => l === 'en' || !!(i18n[l] && i18n[l][s]);
  const groups = { phrases: [], common: [], cues: [], names: [], templates: [], stories: [], full: [] };
  const all = ['en', ...langs];
  for (const l of all) {
    for (const p of PHRASES) if (has(l, p)) groups.phrases.push({ lang: l, text: tr(l)(p) });
    for (const tp of TEMPLATES) {
      if (!has(l, tp.t)) continue;
      for (const { d, m } of distancePhrases(tr(l), tp.range)) {
        const text = fill(tr(l)(tp.t), { dist: d });
        const common = tp.t === 'In {dist},' && m != null && m >= 20 && m <= 400;
        (common ? groups.common : groups.templates).push({ lang: l, text });
      }
    }
    const partners = new Set(routes.flatMap(r => (r.offers || []).map(o => o.partner)));
    for (const tp of NAME_TEMPLATES) if (has(l, tp)) for (const n of partners) groups.templates.push({ lang: l, text: fill(tr(l)(tp), { name: n }), src: tp });
  }
  // route content: translated where a translation exists, otherwise the app speaks the English with the English voice
  for (const r of routes) {
    for (const l of all) {
      const say = s => { if (!s) return null; return has(l, s) || l === 'en' ? { lang: l, text: tr(l)(s) } : null; };
      r.cues.forEach(c => { const x = say(c.n); if (x) groups.cues.push(x); });
      r.stops.forEach(s => { const x = say(s.name); if (x) groups.names.push(x); const y = say(s.text); if (y) groups.stories.push(y);
        (s.story || []).forEach(p => { const z = say(p); if (z) groups.full.push(z); }); });
    }
  }
  // every full story in config/stories.json, in English, linked to a ride stop or not, so other apps (EO Crew staff app)
  // can play the same recordings; published in stories-voice.json
  for (const st of Object.values(stories || {})) for (const p of (st && Array.isArray(st.paras) ? st.paras : [])) {
    const text = String(p || '').trim(); if (text) groups.full.push({ lang: 'en', text });
  }
  const out = [], seen = new Set();
  for (const g of ['phrases', 'common', 'cues', 'names', 'templates', 'stories', 'full']) {
    const list = groups[g].slice().sort((a, b) => ORDER.indexOf(a.lang) - ORDER.indexOf(b.lang));
    for (const x of list) {
      const text = (x.text || '').trim(); if (!text) continue;
      const k = x.lang + '|' + text; if (seen.has(k)) continue;
      seen.add(k); out.push({ lang: x.lang, text, group: g, src: x.src });
    }
  }
  return out;
}

async function api(url, body, key) {
  for (let attempt = 0; attempt < 5; attempt++) {
    const res = await fetch(url + (url.includes('?') ? '&' : '?') + 'key=' + encodeURIComponent(key),
      body ? { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) } : {});
    if (res.ok) return res.json();
    const text = await res.text();
    if (res.status === 429 || res.status >= 500) { await new Promise(r => setTimeout(r, 1500 * (attempt + 1) ** 2)); continue; }
    const err = new Error(`Google Text-to-Speech ${res.status}: ${text.slice(0, 300)}`); err.status = res.status; throw err;
  }
  throw new Error('Google Text-to-Speech kept refusing (rate limit or outage)');
}

// Chosen voice per language: the configured Chirp 3 HD voice, or the first Chirp 3 HD voice Google offers for it.
async function pickVoices(key, want, notes) {
  const out = {};
  for (const [l, code] of Object.entries(VOICE_LANGS)) {
    try {
      const v = await api(`https://texttospeech.googleapis.com/v1/voices?languageCode=${code}`, null, key);
      const names = (v.voices || []).map(x => x.name);
      const chirp = names.filter(n => n.startsWith(code + '-Chirp3-HD-'));
      const chosen = chirp.find(n => n.endsWith('-' + want)) || chirp[0] || null;
      if (!chosen) { notes.push(`no natural voice for ${l} (${code}); phone voice used`); continue; }
      if (!chosen.endsWith('-' + want)) notes.push(`${l}: voice ${want} not offered, using ${chosen}`);
      // The tag (the folder recordings are published under) also carries this language's speech rules, so when how a line
      // is said changes (a new rule or respelling, which re-records the line), its address changes too and phones fetch the
      // new recording instead of keeping the old one they saved (Ben heard old years read out, 11/10/2026).
      const say = JSON.stringify({ rules: SPEECH.rules.filter(r => !r.langs || r.langs.includes(l)), names: SPEECH.names,
        pronounce: Object.entries(SPEECH.pronounce).filter(([, x]) => !x.langs || x.langs.includes(l)) });
      out[l] = { lang: l, code, name: chosen, tag: crypto.createHash('sha1').update(chosen + '|' + say).digest('hex').slice(0, 6) };
    } catch (e) { notes.push(`${l}: could not list voices (${e.message})`); if (e.status === 400 || e.status === 403) throw e; }
  }
  return out;
}

// One recording. Google refuses very long sentences in some languages; those are recorded a sentence (or clause) at a time
// and the pieces joined, which MP3 allows.
async function synth(text, vc, key, depth = 0, prons = null, stat = null) {
  const all = prons || pronunciations(vc.lang, text);
  text = respelled(text, all.filter(p => !p.ipa));   // respelling only, for this language
  prons = all.filter(p => p.ipa);
  const input = { text };
  if (prons.length) input.customPronunciations = { pronunciations: prons.map(p => ({ phrase: p.phrase, phoneticEncoding: 'PHONETIC_ENCODING_IPA', pronunciation: p.ipa })) };
  try {
    const res = await api('https://texttospeech.googleapis.com/v1/text:synthesize',
      { input, voice: { languageCode: vc.code, name: vc.name }, audioConfig: { audioEncoding: 'MP3' } }, key);
    return Buffer.from(res.audioContent, 'base64');
  } catch (e) {
    // Google refused the pronunciation (it is a preview feature): say the respelling instead, and report it
    if (e.status === 400 && prons.length && !/too long/i.test(e.message)) {
      if (stat) {
        stat.pronRefused = (stat.pronRefused || 0) + 1;
        const by = stat.pronRefusedBy = stat.pronRefusedBy || {};
        by[vc.lang] = by[vc.lang] || { lines: 0, error: e.message.replace(/\s+/g, ' ').replace(/^.*?"message": ?"/, '').slice(0, 160) };
        by[vc.lang].lines++;
      }
      const res = await api('https://texttospeech.googleapis.com/v1/text:synthesize',
        { input: { text: respelled(text, prons) }, voice: { languageCode: vc.code, name: vc.name }, audioConfig: { audioEncoding: 'MP3' } }, key);
      return Buffer.from(res.audioContent, 'base64');
    }
    if (!(e.status === 400 && /too long/i.test(e.message)) || depth > 2) throw e;
    const re = depth === 0 ? /[^.!?\u3002\uff01\uff1f]+[.!?\u3002\uff01\uff1f]*/g : /[^,;:\uff0c\u3001\uff1b\uff1a]+[,;:\uff0c\u3001\uff1b\uff1a]*/g;
    const parts = (text.match(re) || [text]).map(x => x.trim()).filter(Boolean);
    if (parts.length < 2) {   // no punctuation to split on: cut in half at a space or in the middle
      const mid = Math.floor(text.length / 2), sp = text.lastIndexOf(' ', mid);
      const at = sp > 10 ? sp : mid; parts.splice(0, parts.length, text.slice(0, at).trim(), text.slice(at).trim());
    }
    const bufs = [];
    for (const p of parts) bufs.push(await synth(p, vc, key, depth + 1, null, stat));
    return Buffer.concat(bufs);
  }
}

export async function buildVoice({ routes, i18n, langs, dist, appSource, health, allRoutesOk, stories }) {
  loadSpeech(path.dirname(dist));
  const cfg = (() => { try { return JSON.parse(fs.readFileSync(path.join(path.dirname(dist), 'config', 'voice.json'), 'utf8')); } catch (e) { return {}; } })();
  const want = cfg.voice || 'Aoede';
  const freeCap = Math.min(Number(cfg.monthlyCharacterCap) || 900000, 980000);
  const runMinutes = Number(cfg.maxMinutesPerBuild) || 35;
  const cacheDir = path.resolve(process.env.VOICE_CACHE || path.join(path.dirname(dist), '.voice-cache'));
  fs.mkdirSync(cacheDir, { recursive: true });
  const ledgerFile = path.join(cacheDir, 'ledger.json');
  const ledger = (() => { try { return JSON.parse(fs.readFileSync(ledgerFile, 'utf8')); } catch (e) { return { months: {} }; } })();
  const month = new Date().toISOString().slice(0, 7);
  ledger.months[month] = ledger.months[month] || 0;
  // Credit allowance (Ben, 11/10/2026): while Google Cloud trial credits last (creditAllowance.until, Brisbane date), the cap
  // rises so a set amount of credit (creditAllowance.usd, at US$30 per million characters past the free million each month)
  // finishes the recordings early. Once that amount is used, or the date passes, the cap drops back to the free cap by itself.
  const ca = cfg.creditAllowance || {};
  const today = new Date(Date.now() + 10 * 3600e3).toISOString().slice(0, 10);
  const FREE = 1000000, PER_M = 30;
  let cap = freeCap, credit;
  if (ca.until && today <= ca.until && Number(ca.usd) > 0 && (!ca.from || month >= ca.from.slice(0, 7))) {
    const allowChars = Math.min(Number(ca.usd), 100) / PER_M * 1e6;
    const usedBefore = Object.entries(ledger.months).filter(([m]) => m !== month && (!ca.from || m >= ca.from.slice(0, 7))).reduce((t, [, c]) => t + Math.max(0, c - FREE), 0);
    const left = Math.max(0, allowChars - usedBefore);
    cap = Math.min(Math.max(freeCap, FREE + left), 3000000);
    const usedNow = usedBefore + Math.max(0, ledger.months[month] - FREE);
    credit = { usd: Number(ca.usd), until: ca.until, usedUsd: Math.round(usedNow * PER_M / 1e6 * 100) / 100 };
  }
  const v = { voice: want, cap, credit, month, charsThisMonth: ledger.months[month], recorded: 0, recordedChars: 0, waiting: 0, failed: 0, notes: [], langs: {} };
  health.voice = v;

  // every spoken UI line in the app must be covered
  const covered = new Set([...PHRASES, ...TEMPLATES.map(t => t.t), ...NAME_TEMPLATES, ...UNIT_STRINGS]);
  const spoken = new Set();
  for (const line of appSource.split('\n')) {
    if (!/\bsay(Content|Parts)?\(/.test(line)) continue;
    for (const m of line.matchAll(/tu\((['"])((?:\\.|(?!\1).)*)\1\)/g)) spoken.add(m[2].replace(/\\'/g, "'"));
  }
  for (const s of spoken) if (!covered.has(s)) health.problems.push(`voice: spoken line "${s}" is not set up for recording (scripts/voice.mjs)`);

  const key = process.env.GOOGLE_TTS_KEY;
  const lines = wantedLines({ routes, i18n, langs, stories });
  v.lines = lines.length;
  let voices = {};
  if (!key) v.notes.push('GOOGLE_TTS_KEY not set: nothing new recorded, existing recordings still published');
  else {
    try { voices = await pickVoices(key, want, v.notes); }
    catch (e) { health.problems.push(`voice: ${e.message}`); }
  }
  // voices used before (from the cache) still serve their recordings when the API is unreachable
  const known = ledger.voices || {};
  for (const l of Object.keys(VOICE_LANGS)) if (!voices[l] && known[l]) voices[l] = known[l];
  ledger.voices = Object.assign({}, known, voices);

  // recordings are keyed by what is actually said (and any exact pronunciation sent with it), so changing a speech rule
  // re-records only the lines it changes
  const fileFor = (l, text) => { const sp = speakable(l, text), pr = pronunciations(l, sp);
    return path.join(cacheDir, voices[l].name, crypto.createHash('sha1').update(sp + (pr.length ? '|ipa2:' + pr.map(p => p.phrase + '=' + (p.ipa || '~' + p.respell)).join(';') : '')).digest('hex') + '.mp3'); };
  const todo = lines.filter(x => voices[x.lang] && !fs.existsSync(fileFor(x.lang, x.text)));
  const started = Date.now();
  let stop = !key || !Object.keys(voices).length;
  let i = 0;
  async function worker() {
    while (!stop && i < todo.length) {
      const x = todo[i++];
      const spoken = speakable(x.lang, x.text);
      const bytes = Buffer.byteLength(spoken);
      if (bytes > MAX_BYTES) { v.notes.push(`too long to record (${x.lang}): ${x.text.slice(0, 60)}...`); continue; }
      if (ledger.months[month] + spoken.length > cap) { stop = true; break; }
      if (Date.now() - started > runMinutes * 60000) { stop = true; break; }
      ledger.months[month] += spoken.length;   // counted before the call so a crash never undercounts
      try {
        const audio = await synth(spoken, Object.assign({ lang: x.lang }, voices[x.lang]), key, 0, null, v);
        const f = fileFor(x.lang, x.text);
        fs.mkdirSync(path.dirname(f), { recursive: true });
        fs.writeFileSync(f, audio);
        v.recorded++; v.recordedChars += spoken.length;
      } catch (e) {
        v.failed++;
        if (e.status === 400 && /API key|PERMISSION|billing/i.test(e.message)) { stop = true; health.problems.push(`voice: ${e.message}`); }
        else if (v.failed <= 5) v.notes.push(`could not record (${x.lang}) "${x.text.slice(0, 40)}": ${e.message.slice(0, 120)}`);
        if (v.failed > 50) { stop = true; health.problems.push('voice: more than 50 recordings failed in one build'); }
      }
      if (v.recorded % 200 === 0) fs.writeFileSync(ledgerFile, JSON.stringify(ledger, null, 1));
    }
  }
  await Promise.all(Array.from({ length: 6 }, worker));
  fs.writeFileSync(ledgerFile, JSON.stringify(ledger, null, 1));
  v.charsThisMonth = ledger.months[month];
  for (const [l, x] of Object.entries(v.pronRefusedBy || {})) health.problems.push(`voice: Google refused the exact pronunciation on ${x.lines} ${l} lines (config/speech.json "pronounce"), so they use the respelling: ${x.error}`);
  v.pronounce = Object.keys(SPEECH.pronounce);

  // publish what exists: dist/v/<tag>/<hash>.mp3, a manifest of the general lines, and each route's own list
  const have = new Map();   // lang -> Set(hash)
  for (const x of lines) {
    if (!voices[x.lang]) { v.waiting++; continue; }
    const f = fileFor(x.lang, x.text);
    if (!fs.existsSync(f)) { v.waiting++; continue; }
    const h = voiceHash(x.lang + '|' + x.text);
    const out = path.join(dist, 'v', voices[x.lang].tag, h + '.mp3');
    if (!fs.existsSync(out)) { fs.mkdirSync(path.dirname(out), { recursive: true }); fs.copyFileSync(f, out); }
    if (!have.has(x.lang)) have.set(x.lang, new Set());
    have.get(x.lang).add(h);
  }
  const general = {};
  for (const [l, vc] of Object.entries(voices)) {
    const set = have.get(l) || new Set();
    general[l] = { tag: vc.tag, h: [], pre: [] };
    v.langs[l] = { voice: vc.name, recordings: set.size };
    for (const x of lines) if (x.lang === l && (x.group === 'phrases' || x.group === 'common' || x.group === 'templates')) {
      const h = voiceHash(l + '|' + x.text); if (!set.has(h)) continue;
      general[l].h.push(h);
      if (x.group !== 'templates' || /\{name\}/.test(x.src || '')) general[l].pre.push(h);   // saved to the phone for offline riding
    }
    general[l].pre = [...new Set(general[l].pre)];
    general[l].h = [...new Set(general[l].h)];
  }
  general._say = { rules: SPEECH.rules.map(r => ({ find: r.find, say: r.say, langs: r.langs })), names: SPEECH.names };   // for the phone voice
  fs.writeFileSync(path.join(dist, 'voice.json'), JSON.stringify(general));
  listenPage({ routes, dist, voices, have });
  storiesVoice({ stories, dist, voices, have });
  // per route: recordings for its own cues, stop names and stories
  for (const r of routes) {
    r.voice = {};
    const texts = new Set([...r.cues.map(c => c.n), ...r.stops.flatMap(s => [s.name, s.text, ...(s.story || [])])].filter(Boolean));
    for (const [l, set] of have) {
      const hs = [];
      for (const s of texts) {
        const t = (l === 'en' ? s : (i18n[l] && i18n[l][s]) || null);
        if (!t) continue;
        const h = voiceHash(l + '|' + t.trim()); if (set.has(h)) hs.push(h);
      }
      if (hs.length) r.voice[l] = hs;
    }
  }
  // prune recordings nothing uses any more (a changed or deleted line), so the cache does not grow forever
  const used = new Set(lines.filter(x => voices[x.lang]).map(x => fileFor(x.lang, x.text)));
  let pruned = 0;
  if (allRoutesOk) for (const vname of fs.readdirSync(cacheDir)) {
    const d = path.join(cacheDir, vname);
    if (!fs.statSync(d).isDirectory() || vname.startsWith('.')) continue;
    for (const f of fs.readdirSync(d)) { const p = path.join(d, f); if (!used.has(p)) { fs.rmSync(p); pruned++; } }
  }
  v.pruned = pruned;
  if (v.waiting && key) v.notes.push(`${v.waiting} lines still to record; the phone voice covers them until then (monthly cap ${cap} characters)`);
  return v;
}

// stories-voice.json: every full story in config/stories.json with the English recording for each paragraph (null until
// recorded), for other apps that play the same stories in the same voice (EO Crew's Know Noosa). Text and audio both come
// from here, so nothing is copied by hand.
function storiesVoice({ stories, dist, voices, have }) {
  const en = voices.en, set = have.get('en') || new Set();
  const out = { _about: 'Every full story from config/stories.json with its natural voice recording per paragraph (null until recorded). Paths are relative to the site. Built by scripts/voice.mjs.', voice: en ? en.name : null, built: new Date().toISOString(), stories: {} };
  for (const [key, st] of Object.entries(stories || {})) {
    if (!st || !Array.isArray(st.paras)) continue;
    const paras = st.paras.map(p => String(p || '').trim()).filter(Boolean).map(t => {
      const h = voiceHash('en|' + t);
      return { t, a: en && set.has(h) ? `v/${en.tag}/${h}.mp3` : null };
    });
    out.stories[key] = { title: st.title || key, origin: st.origin || null, paras };
  }
  fs.writeFileSync(path.join(dist, 'stories-voice.json'), JSON.stringify(out));
}

// listen.html: every place name and the start of every full story in English, with its recording, so Ben can check how
// names are said. Fixes go in config/speech.json "pronounce" (IPA) or "names" (respelling). Not linked from the app and not indexed.
function listenPage({ routes, dist, voices, have }) {
  const en = voices.en, set = have.get('en') || new Set();
  const esc = t => String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const clip = t => { if (!en || !t) return null; const h = voiceHash('en|' + t.trim()); return set.has(h) ? `v/${en.tag}/${h}.mp3` : null; };
  const rows = new Map();
  for (const r of routes) for (const s of r.stops) {
    if (s.kind === 'caution' || s.kind === 'finish' || rows.has(s.name)) continue;
    rows.set(s.name, { name: s.name, story: (s.story || [])[0] || null });
  }
  const list = [...rows.values()].sort((a, b) => a.name.localeCompare(b.name));
  const audio = u => (u ? `<audio controls preload="none" src="${u}"></audio>` : '<span class="w">not recorded yet</span>');
  const body = list.map(x => `<li><b>${esc(x.name)}</b>${audio(clip(x.name))}${x.story ? `<p>${esc(x.story)}</p>${audio(clip(x.story))}` : ''}</li>`).join('\n');
  fs.writeFileSync(path.join(dist, 'listen.html'), `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Ride Guide voice check</title>
<style>body{font:16px/1.5 system-ui,sans-serif;margin:0 auto;max-width:760px;padding:16px;color:#1d2430;background:#fff}li{margin:0 0 20px}audio{display:block;width:100%;max-width:420px;margin:6px 0}p{margin:6px 0 0;color:#4a5363}.w{display:block;color:#9a5b00;font-size:14px}</style></head><body>
<h1>Ride Guide voice check</h1><p>How the natural voice says each place name, and the start of each full story. Tell Claude any name that sounds wrong and how it should sound.</p><ol>
${body}
</ol></body></html>`);
}
