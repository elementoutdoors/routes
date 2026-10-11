// Out and back rides: which time past a stop it is read.
//
// The build works out every time the route passes each stop (s.runs, distances along the route). Then:
// - A story stop is read once. Normally on the first pass. When two or more story stops sit close together and the
//   route passes them again later (out and back), they are shared out: the first on the way out, the next on the way back.
// - A caution is read every time the route passes it (s.ds), because most warnings matter in both directions.
//   A caution about a hill or a descent is only read where the route goes downhill from it, so a "Steep descent"
//   warning on an out and back road is said on the way down, not on the way up.
// Facilities, the finish and stops off the route are left as they are.

const STORY = { info: 1, view: 1, park: 1, turn: 1 };
const DOWNHILL_NAME = /\b(steep|descent|descending|downhill|hill)\b/i;
const SAME_PLACE_METRES = 100;     // passes closer than this are the same pass (a turnaround right at the stop)
const CLUSTER_METRES = 250;        // story stops this close along the route are shared out between passes
const DOWNHILL_LOOK_METRES = 250;  // how far ahead to look for the drop
const DOWNHILL_DROP_METRES = 6;    // drop over that distance that counts as going downhill

function eleAt(T, d) {
  let lo = 0, hi = T.d.length - 1;
  if (d <= T.d[0]) return T.ele[0];
  if (d >= T.d[hi]) return T.ele[hi];
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (T.d[m] <= d) lo = m; else hi = m; }
  const f = (d - T.d[lo]) / ((T.d[hi] - T.d[lo]) || 1);
  return T.ele[lo] + (T.ele[hi] - T.ele[lo]) * f;
}

function distinct(runs) {
  const out = [];
  for (const d of [...runs].sort((a, b) => a - b)) if (!out.length || d - out[out.length - 1] >= SAME_PLACE_METRES) out.push(d);
  return out;
}

export function planPasses(T, stops) {
  const notes = [];
  // cautions: every pass, or only the downhill passes for a hill or descent warning
  for (const s of stops) {
    if (s.kind !== 'caution' || !s.runs || !s.runs.length) continue;
    let ds = distinct(s.runs);
    if (ds.length > 1 && DOWNHILL_NAME.test(s.name)) {
      const down = ds.filter(d => eleAt(T, d) - eleAt(T, d + DOWNHILL_LOOK_METRES) >= DOWNHILL_DROP_METRES);
      if (down.length && down.length < ds.length) { ds = down; notes.push(`caution "${s.name}" is read on the way down only`); }
    }
    s.d = ds[0];
    if (ds.length > 1) s.ds = ds;
  }
  // story stops: share a close group out between the passes
  const stories = stops.filter(s => STORY[s.kind] && s.runs && s.runs.length).sort((a, b) => a.runs[0] - b.runs[0]);
  let group = [];
  const flush = () => {
    if (group.length > 1) {
      let k = 0;
      for (const s of group) {
        const ds = distinct(s.runs);
        if (ds.length < 2) continue;
        const pick = ds[k % ds.length];
        if (pick !== s.d) notes.push(`stop "${s.name}" is read on pass ${(k % ds.length) + 1} of ${ds.length}`);
        s.d = pick; k++;
      }
    }
    group = [];
  };
  for (const s of stories) {
    if (group.length && s.runs[0] - group[group.length - 1].runs[0] > CLUSTER_METRES) flush();
    group.push(s);
  }
  flush();
  for (const s of stops) delete s.runs;
  return notes;
}
