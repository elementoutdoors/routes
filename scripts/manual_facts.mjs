// The facts the Ride Guide manual in EO Crew is written against (EO-HI-10, one document: Part 1 for staff, Part 2 for
// managers, Part 3 the technical appendix), read straight from the code, so a change to the app, the Ride Desk or the
// build that the manual describes is noticed. The pictures in the manual retake themselves every night
// (scripts/staff_screens.py); the words do not, so this is how the words are kept honest.
//
//   node scripts/manual_facts.mjs            print the facts as they are now
//   node scripts/manual_facts.mjs --check    compare with manual/written.json: {ok, changed: [{fact, added, removed, sections}]}
//   node scripts/manual_facts.mjs --accept   after the manual has been brought into line: record today's facts
//
// manual/written.json holds the facts the manual was last checked against, which manual sections each fact feeds,
// and the EO Crew document, part and section ids. The weekly drift check (Drift Check Register, Ride Guide routes tab, Manual step) runs
// --check; for each changed fact it rewrites the named sections in EO Crew, then runs --accept and pushes.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const read = (f) => fs.readFileSync(path.join(ROOT, f), 'utf8');
const uniq = (a) => [...new Set(a)];
const all = (re, s, g = 1) => [...s.matchAll(re)].map((m) => m[g]);

export function facts() {
  const app = read('site/app.js'), html = read('site/index.html');
  const settingsFn = app.slice(app.indexOf('function openSettings'), app.indexOf('// ---------- staff check'));
  const groups = read('ride-desk/page/groups.js'), main = read('ride-desk/page/main.js');
  const desk = read('scripts/ride-desk.mjs'), settings = JSON.parse(read('config/settings.json'));
  const wf = read('.github/workflows/build.yml'), screens = read('scripts/staff_screens.py');
  const listOf = (name) => { const m = desk.match(new RegExp(`export const ${name} = \\[([^\\]]*)\\]`)); return m ? all(/'([^']+)'/g, m[1]) : []; };
  return {
    // what riders can change on the phone (EO-HI-10, Settings on the phone)
    phoneSettings: uniq(all(/tu\('([^']+)'\)/g, settingsFn)),
    languages: all(/\['(\w\w)', '[^']+'\]/g, app.slice(app.indexOf('var LANGS'), app.indexOf('var LANGS') + 600)),
    // the buttons and panels on the app's screens (EO-HI-10, The app screen by screen)
    appControls: uniq(all(/id="([\w-]+)"/g, html)),
    // everything the app says or shows in its own words (wording changes a manual may quote)
    appWords: uniq(all(/tu\(['"]((?:[^'"\\]|\\.)+)['"]\)/g, app)).sort(),
    // the Ride Desk (EO-HI-10 Part 2)
    deskCardSections: all(/el\("h3", null, "([^"]+)"\)/g, main),
    deskSettings: all(/label: "([^"]+)"/g, groups),
    deskFields: { public: listOf('PUBLIC_FIELDS'), staff: listOf('STAFF_FIELDS') },
    // rider settings that exist (not their values: those are Ben's to change any day and are shown live on the Ride Desk)
    settingKeys: Object.fromEntries(Object.entries(settings).filter(([k]) => !k.startsWith('_')).map(([g, v]) => [g, Object.keys(v).filter((k) => !k.startsWith('_'))])),
    // how and when the site is built (EO-HI-10 Part 3)
    buildSchedule: all(/cron: '([^']+)'/g, wf),
    buildSteps: all(/- name: (.+)/g, wf).map((s) => s.trim()),
    // the manual's pictures
    screens: uniq(all(/'(\d\d\w?-[\w-]+\.jpg)'/g, screens)),
  };
}

function diff(a, b) {
  const flat = (x) => (Array.isArray(x) ? x.map(String) : x && typeof x === 'object' ? Object.entries(x).flatMap(([k, v]) => flat(v).map((s) => `${k}: ${s}`)) : [String(x)]);
  const A = new Set(flat(a)), B = new Set(flat(b));
  return { added: [...B].filter((x) => !A.has(x)), removed: [...A].filter((x) => !B.has(x)) };
}

const WRITTEN = path.join(ROOT, 'manual', 'written.json');
const arg = process.argv[2];
if (arg === '--check' || arg === '--accept') {
  const now = facts();
  const w = JSON.parse(fs.readFileSync(WRITTEN, 'utf8'));
  if (arg === '--accept') {
    w.facts = now; w.checkedOn = new Date().toISOString().slice(0, 10);
    fs.writeFileSync(WRITTEN, JSON.stringify(w, null, 1) + '\n');
    console.log(JSON.stringify({ ok: true, accepted: w.checkedOn }));
  } else {
    const changed = [];
    for (const k of Object.keys(now)) {
      const d = diff((w.facts || {})[k], now[k]);
      if (d.added.length || d.removed.length) changed.push({ fact: k, ...d, sections: (w.feeds || {})[k] || [] });
    }
    console.log(JSON.stringify({ ok: !changed.length, checkedOn: w.checkedOn, changed }, null, 1));
  }
} else if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  console.log(JSON.stringify(facts(), null, 1));
}
