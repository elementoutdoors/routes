"""Route lines for the sheets, keyed by Ride with GPS route id.

Sources, in order:
1. The Ride Guide build (../dist/r/*.json, written by scripts/build.mjs). This is the living source: it is
   rebuilt from Ride with GPS every hour, so a redrawn route reaches the sheets on the next sheet build.
2. cache/routes.json, a one off Ride with GPS export (how the October 2026 sheets were made). Never committed:
   the routes are a paid product and this repo is public.
"""
import glob, json, os
from paths import ROOT, CACHE

MAX_POINTS = 1500


def _from_ride_guide():
    out = {}
    for f in glob.glob(os.path.join(ROOT, 'dist', 'r', '*.json')):
        try:
            r = json.load(open(f))
        except Exception:
            continue
        if not r.get('rwgps') or not r.get('track'):
            continue
        T = r['track']
        n = len(T['lat']); step = max(1, n // MAX_POINTS)
        idx = list(range(0, n, step))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        out[str(r['rwgps'])] = dict(
            name=r.get('name', ''), desc=r.get('description', ''), dist=r.get('distance', 0), gain=r.get('gain', 0),
            pts=[[T['lat'][i], T['lng'][i], T['ele'][i], T['d'][i]] for i in idx],
            pois=[dict(n=s['name'], d=s.get('text', ''), y=s['lat'], x=s['lng'], t=s.get('kind', '')) for s in r.get('stops', [])],
            cues=[], hero=r.get('hero'), slug=r.get('slug'), version=r.get('version'), source='ride-guide')
    return out


def load_routes():
    routes = _from_ride_guide()
    cached = os.path.join(CACHE, 'routes.json')
    if os.path.exists(cached):
        for k, v in json.load(open(cached)).items():
            routes.setdefault(k, dict(v, source='export'))
    if not routes:
        raise SystemExit('No route lines: run the Ride Guide build (node scripts/build.mjs) or put a Ride with GPS export in ride-sheets/cache/routes.json')
    return routes
