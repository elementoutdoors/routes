"""Route lines and numbers for the sheets, keyed by Ride with GPS route id, from the Ride Guide build.

The build (scripts/build.mjs) writes dist/health.json, dist/rides.json, dist/r/<key>.json and qr/links.json, qr/codes.json.
It is rebuilt from Ride with GPS every hour, so a redrawn route reaches the sheets on the next build. Only live rides
are here (the same set as the QR cards), without the test route. Route lines are never committed: the routes are a
paid product and this repo is public.
"""
import json, os, re
from paths import ROOT, DIST, QR

MAX_POINTS = 1500


def _read(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        if default is not None:
            return default
        raise


def load_routes():
    links = _read(os.path.join(QR, 'links.json'))
    codes = _read(os.path.join(QR, 'codes.json'))
    health = _read(os.path.join(DIST, 'health.json'))
    listed = {r['slug']: r for r in _read(os.path.join(DIST, 'rides.json'), {'rides': []})['rides']}
    cfg = {r['slug']: r for r in _read(os.path.join(ROOT, 'config', 'routes.json'))['routes']}
    out = {}
    for h in health['routes']:
        s = h['slug']
        if not h.get('ok') or s not in links:
            continue
        lr = listed.get(s, {})
        if lr.get('test') or re.search(r'test', s, re.I):
            continue
        key = links[s].split('#', 1)[1]
        try:
            r = _read(os.path.join(DIST, 'r', f'{key}.json'))
        except Exception:
            continue
        T = r.get('track')
        if not T or not T.get('lat'):
            continue
        n = len(T['lat']); step = max(1, n // MAX_POINTS)
        idx = list(range(0, n, step))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        ele = T.get('ele') or [0] * n
        rw = str(r.get('rwgps') or cfg.get(s, {}).get('rwgps') or s)
        out[rw] = dict(
            name=r.get('name', ''), desc=r.get('description', ''), dist=r.get('distance', 0), gain=r.get('gain', 0),
            pts=[[T['lat'][i], T['lng'][i], ele[i], T['d'][i]] for i in idx],
            line=[[T['lng'][i], T['lat'][i]] for i in range(n)],
            pois=[dict(n=p['name'], d=p.get('text', ''), y=p['lat'], x=p['lng'], t=p.get('kind', '')) for p in r.get('stops', [])],
            hero=r.get('hero'), slug=s, version=r.get('version'), type=r.get('type') or cfg.get(s, {}).get('type') or '',
            brand=((r.get('brand') or {}).get('id') or cfg.get(s, {}).get('brand') or 'bikeon'),
            riding_minutes=lr.get('riding_minutes'), link=links[s], code=codes.get(s, ''), source='ride-guide')
    if not out:
        raise SystemExit('No route lines: run the Ride Guide build first (node scripts/build.mjs)')
    return out
