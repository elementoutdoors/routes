// Direction check (Ben, 16/10/2026). The app says each direction twice: a warning ahead and "Turn right here ..." at the
// turn itself, so a direction has to sit where the line actually turns. The build flags, per route:
//   offTurn   a left or right direction placed after the turn in the line by more than 15 m (the "here" call would come
//             as or after riders reach the turn), or before it by more than 25 m (the call would come well before it)
//   noTurn    a turn left or right with no turn in the line within 50 m of it (keep, bear and stay directions excepted:
//             a fork or a path beside the road need not bend the line)
//   repeat    two directions within 40 m of each other that say the same thing, or two bare ones ("Turn right", "Turn right")
//   bare      a bare direction ("Turn right", "Keep left") with no road or path named
// Each flag has a key; Ben's ruling on the Directions Review page is kept in config/direction-rulings.json, and a flag he
// has ruled "keep as is" is not raised again while the direction stays the same.
const R = 6371000;
const rad = x => x * Math.PI / 180;
function bearing(lat1, lng1, lat2, lng2) {
  const y = Math.sin(rad(lng2 - lng1)) * Math.cos(rad(lat2));
  const x = Math.cos(rad(lat1)) * Math.sin(rad(lat2)) - Math.sin(rad(lat1)) * Math.cos(rad(lat2)) * Math.cos(rad(lng2 - lng1));
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360;
}
const turnDiff = (a, b) => { let d = b - a; while (d > 180) d -= 360; while (d < -180) d += 360; return d; };

// position on the line at distance d
export function at(T, d) {
  let lo = 0, hi = T.d.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T.d[m] <= d) lo = m; else hi = m; }
  const f = T.d[hi] === T.d[lo] ? 0 : Math.max(0, Math.min(1, (d - T.d[lo]) / (T.d[hi] - T.d[lo])));
  return { lat: T.lat[lo] + (T.lat[hi] - T.lat[lo]) * f, lng: T.lng[lo] + (T.lng[hi] - T.lng[lo]) * f };
}
// heading change at distance d, comparing the line 15 m before with the line 15 m after (left negative, right positive)
function turnAt(T, d) {
  const a = at(T, d - 15), b = at(T, d), c = at(T, d + 15);
  return turnDiff(bearing(a.lat, a.lng, b.lat, b.lng), bearing(b.lat, b.lng, c.lat, c.lng));
}
const SIDE = { left: -1, 'slight-left': -1, 'sharp-left': -1, right: 1, 'slight-right': 1, 'sharp-right': 1 };
const BARE = /^(turn|bear|keep|veer)\s+((sharp|slight)\s+)?(left|right)\.?$/i;

export const keyOf = (slug, c, issue) => `${slug}|${issue}|${c.n}|${Math.round(c.d / 25) * 25}`;

export function checkDirections(slug, route, rulings = {}) {
  const T = route.track, cues = route.cues, out = [];
  const total = T.d[T.d.length - 1];
  const push = (c, i, issue, detail, extra = {}) => {
    const key = keyOf(slug, c, issue);
    const r = rulings[key];
    if (r && r.ruling === 'keep' && r.n === c.n) return;   // Ben kept it as it is
    const p = at(T, c.d);
    out.push(Object.assign({ key, slug, route: route.name, i, d: c.d, n: c.n, t: c.t, issue, detail, lat: +p.lat.toFixed(6), lng: +p.lng.toFixed(6), ruled: r ? r.ruling : null }, extra));
  };
  const dup = (a, b) => a && b && a.t !== 'danger' && b.t !== 'danger' && Math.abs(b.d - a.d) < 40 && (a.n === b.n || (BARE.test(a.n) && BARE.test(b.n)));
  cues.forEach((c, i) => {
    if (c.t === 'danger' || c.d < 30 || c.d > total - 20) return;
    const twin = dup(cues[i - 1], c) || dup(c, cues[i + 1]);   // a repeat: its own card covers it
    const side = SIDE[c.t];
    if (side) {
      // where, within 50 m, the line turns most sharply in the direction's own way
      let best = null;
      for (let x = Math.max(0, c.d - 50); x <= Math.min(total, c.d + 50); x += 3) {
        const a = turnAt(T, x) * side;
        if (!best || a > best.a) best = { a, x };
      }
      const need = /slight/.test(c.t) ? 15 : 30;
      if (!best || best.a < need) { if (!/^(keep|bear|stay|continue|follow|veer)\b/i.test(c.n) && !/roundabout/i.test(c.n)) push(c, i, 'noTurn', 'The line does not turn ' + (side < 0 ? 'left' : 'right') + ' within 50 m of this direction, so the "here" call may not match the real turn.'); }
      // only a real turn ("Turn left/right ...", not slight) is checked for position, and only when the sharpest bend
      // found is a clear turn away from the edge of the search (otherwise it is likely a different bend)
      else if (!twin && /^turn\b/i.test(c.n) && !/slight/.test(c.t) && best.a >= 45 && Math.abs(best.x - c.d) < 42 && (best.x - c.d > 25 || c.d - best.x > 15)) {
        const off = Math.round(best.x - c.d), tp = at(T, best.x);
        push(c, i, 'offTurn', `This direction sits ${Math.abs(off)} m ${off > 0 ? 'before' : 'after'} the turn in the line, so riders would hear "here" ${off > 0 ? 'too early' : 'too late'}.`,
          { turn: { d: Math.round(best.x), lat: +tp.lat.toFixed(6), lng: +tp.lng.toFixed(6), off } });
      }
    }
    const nx = cues[i + 1];
    if (dup(c, nx))
      push(nx, i + 1, 'repeat', `"${nx.n}" comes ${nx.d - c.d} m after "${c.n}", so riders hear two directions almost on top of each other.`, { prev: { i, d: c.d, n: c.n } });
    if (BARE.test(c.n) && !twin) push(c, i, 'bare', 'No road or path is named in this direction.');
  });
  return out;
}
