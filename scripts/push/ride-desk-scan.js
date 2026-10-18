// Ride Desk: every route in the By Earth and Ocean organisation account on Ride with GPS, for finding new rides.
// Paste into the javascript tool on any ridewithgps.com page in Ben's signed-in Ride with GPS session (organisation 15663).
// Read only: it changes nothing in Ride with GPS. It replaces the page with one line of JSON so get_page_text can read
// it whole (the javascript tool cuts long results): {"scan":"ride-desk","at":...,"routes":[{id,name,visibility,distance,gain,created,updated,code,description}]}
// visibility: 0 public, 1 private, 2 anyone with the link. code is the route's privacy code (the Ride Guide build needs it
// for a ride that is not public). Set KNOWN to the Ride Guide ids that already have a code on the Ride Desk, so only new
// routes are opened for theirs and their description (each route file is large). Version 1 (18/10/2026).
const KNOWN = [];   // <- Ride with GPS ids whose privacy code the Ride Desk already holds
const CLUB = 15663;
const list = await (await fetch(`/clubs/${CLUB}/routes.json?limit=1000`, { headers: { Accept: 'application/json' } })).json();
const routes = [];
for (const r of (list.results || list)) {
  if (r.deleted_at || r.archived_at) continue;
  let code = null, description = null;
  if (!KNOWN.includes(r.id)) try { const one = await (await fetch(`/routes/${r.id}.json`, { headers: { Accept: 'application/json' } })).json(); const o = one.route || one; code = o.privacy_code || null; description = (o.description || '').slice(0, 4000); } catch (e) {}
  routes.push({ id: r.id, name: r.name, visibility: r.visibility, distance: Math.round(r.distance || 0), gain: Math.round(r.elevation_gain || 0),
    created: r.created_at, updated: r.updated_at, code, description });
}
const out = JSON.stringify({ scan: 'ride-desk', v: 1, at: new Date().toISOString(), club: CLUB, routes });
document.body.innerHTML = '';
const pre = document.createElement('pre'); pre.id = 'ride-desk-scan'; pre.textContent = out; document.body.appendChild(pre);
`ride desk scan: ${routes.length} routes, ${routes.filter(r => r.code).length} with a privacy code; read the page with get_page_text`;
