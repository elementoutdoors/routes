// Story Library -> Ride with GPS POI Library pins. Paste into the javascript tool on any ridewithgps.com page in Ben's
// signed-in Ride with GPS session (By Earth and Ocean organisation 15663), with ITEMS set to the "pins" list from
// `node scripts/library.mjs plan` (each item carries the Ride with GPS ids of rides that show the pin).
// Changes only the pin's description (the line read aloud) and only on POI Library pins, then republishes every
// Experience, so riders on the Ride with GPS app hear the same words as the Ride Guide.
// Version 1 (11/10/2026).
const ITEMS = [];   // <- paste the plan's pins list here
const CLUB = 15663;
const token = document.querySelector('meta[name=csrf-token]').content;
const H = { 'X-CSRF-Token': token, 'Content-Type': 'application/json', Accept: 'application/json' };
const done = [], failed = [];
for (const it of ITEMS) {
  let pin = null;
  for (const id of it.rwgps || []) {
    const r = await (await fetch(`/routes/${id}.json`)).json();
    pin = ((r.route || r).points_of_interest || []).find(p => p.name === it.name && p.parent_type === 'Club' && (p.url || '').includes('#' + it.key));
    if (pin) break;
  }
  if (!pin) { failed.push(`${it.brand} "${it.name}": no POI Library pin with that name and link on its rides`); continue; }
  const res = await fetch(`/organizations/${CLUB}/points_of_interest/${pin.id}.json`, { method: 'PATCH', headers: H, body: JSON.stringify({ point_of_interest: { description: it.text } }) });
  const j = await res.json().catch(() => ({}));
  ((j.point_of_interest || {}).description === it.text) ? done.push(`${it.brand} "${it.name}" (${pin.id})`) : failed.push(`${it.brand} "${it.name}": save returned ${res.status}`);
}
const exps = await (await fetch(`/experiences.json?club_id=${CLUB}`)).json();
const republished = [];
// every Experience, not only those flagged: the flag does not always show pin changes on its rides (15/10/2026)
for (const e of (exps.results || exps.experiences || exps)) {
  const r = await fetch(`/experiences/${e.id}/publish.json`, { method: 'POST', headers: H, body: '{}' });
  republished.push(`${e.id}:${r.status}`);
}
JSON.stringify({ done, failed, republished });
