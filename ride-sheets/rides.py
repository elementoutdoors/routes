"""Each ride sheet's 3D map settings (Claude's): the place names pinned on the map, how many names come from the gazetteer,
the high point label and the camera angle where one was chosen. Ported from the Branding Bob ride sheets (4 to 7 Oct 2026).

Everything a sheet says comes from the Ride Desk (Ben, 18/10/2026; ride-sheets/desk.py reads config/ride-desk.json):
  title, category, sell line, highlights, level, surface, terrain, recommended bike, the note and the photo, and whether
  the ride is on the hire desk iPad and in the booklet (a ride switched off is not in rides.json, so it gets no sheet).
From the Ride Guide build every time: the ride story (the card's description), distance, climbing and riding time.
A live ride with no map settings here still gets a sheet (listed as generic in the manifest), with a map labelled from
the gazetteer alone.
"""
import json, math, os, re
from paths import HERE
from routes_data import load_routes
import desk
R = load_routes()
CARDS = desk.cards()
PLACES = json.load(open(os.path.join(HERE, 'places.json')))

SHOP = (-26.40793, 153.04347)
BLUE, GOLD = '#2F86E6', '#F5CA3A'
RIDING_NOTE = 'Riding time is time on the bike. Allow extra for stops and breaks.'


def L(n, y, x, pri=2, kind='place', **kw):
    return dict(n=n, y=y, x=x, pri=pri, kind=kind, **kw)


def near_route(rid, y, x):
    """Snap a point to the nearest route point."""
    if rid not in R:
        return y, x
    best = min(R[rid]['pts'], key=lambda p: (p[0] - y) ** 2 + ((p[1] - x) * .9) ** 2)
    return best[0], best[1]


def S(rid, n, y, x, pri=2, **kw):
    y, x = near_route(rid, y, x)
    return L(n, y, x, pri, **kw)


# ---------------- automatic place names from the Queensland gazetteer ----------------
def norm(n):
    n = re.sub(r'\s*\(.*?\)', '', n).strip()
    if n.isupper():
        n = n.title()
    n = n.replace('Mount Mothar', 'Mothar Mountain').replace('Mcdonnald Lake', 'Lake Macdonald')
    n = re.sub(r'^Mount ', 'Mt ', n)
    if n == 'Boreen':
        n = 'Boreen Point'
    n = n.replace(' And ', ' and ')
    return n


TYPES = {'MT': (1, 2.0), 'PEAK': (1, 1.5), 'LAKE': (1, 3.5), 'RES': (1, 2.0), 'POPL': (2, 1.6), 'LOOK': (2, 0.8),
         'BCH': (2, 0.5), 'WRFL': (3, 1.0), 'PARK': (3, 2.0), 'FRST': (4, 0.6), 'LOCB': (4, 0.6)}
SKIP = {'Noosa', 'Peregian', 'Carura', 'Eerwah', 'Duke Reservoir', 'Tinbeerwah', 'Federal', 'Bridges', 'Tandur'}


def auto(rid, have, n, extra_types=(), skip=()):
    if rid not in R:
        return []
    pts = R[rid]['pts'][::2]
    span = max(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts)) * 105
    have_names = {h['n'].split(': ')[-1].lower() for h in have}
    seen, cands = set(), []
    for p in PLACES:
        t = p['type']
        if t not in TYPES:
            continue
        name = norm(p['place_name'])
        if name in SKIP or name in skip or (t == 'PARK' and 'National Park' not in name) or (t == 'FRST' and ('State Forest' not in name or name[-1].isdigit() or name.startswith('Tewantin'))):
            continue
        if t == 'LOCB' and p['currency'] != 'Y':
            continue
        if t == 'BCH' and 'BCH' not in extra_types:
            continue
        pri, lim = TYPES[t]
        if t in ('MT', 'PEAK'):
            lim = max(lim, 0.07 * span)
        y, x = p['latitude_dd'], p['longitude_dd']
        d = min(math.hypot((y - a) * 111, (x - b) * 99.6) for a, b, *_ in pts)
        if d > lim:
            continue
        cands.append((pri + d / lim * 0.8, name, y, x, t))
    cands.sort()
    out = []
    for sc, name, y, x, t in cands:
        key = name.lower()
        if key in seen or any(key in h or h in key for h in have_names):
            continue
        if any(math.hypot((y - h['y']) * 111, (x - h['x']) * 99.6) < 1.0 for h in have + out):
            continue
        seen.add(key)
        out.append(L(name, y, x, pri=4 + len(out) * 0.1, fit=False))
        if len(out) >= n:
            break
    return out


# the ride story, from the ride's description: textfit.story (house spellings in textfit.house_style)
from textfit import story, house_style


def clean_title(name):
    return re.sub(r'\s+Self[- ]Guided Tour\b', '', name or '').strip()


# ---------------- ride content: words from the Ride Desk, map settings here ----------------
RIDES = {}


def words(rid):
    """The sheet's words from the ride's Ride Desk card (desk.py)."""
    c = CARDS.get(R[rid]['slug'], {})
    return dict(title=desk.text(c.get('title')) or clean_title(R[rid]['name']), kick=desk.kick(c.get('category')),
                sub=desk.text(c.get('sellLine')), hl=[desk.text(h) for h in (c.get('highlights') or []) if desk.text(h)],
                stats=desk.stats(c), note=desk.text(c.get('sheetNote')) or RIDING_NOTE)


def shop(rid, slug, labels, nauto=5, peak=None, extra=(), **kw):
    """A ride from the shop: map settings (slug names the map in the cache; keep it, or the map is drawn again)."""
    if rid not in R:
        return
    w = words(rid)
    lab = [L('Start and finish: Bike On', *SHOP, pri=0, kind='start', down=True)] + labels
    lab += auto(rid, lab, nauto, extra)
    RIDES[rid] = dict(slug=slug, **w, labels=lab, curated_labels=labels, style='bikeon', color=BLUE, peak=peak, brand='bikeon', group=w['kick'], **kw)


# Stats: Distance, Climbing and Riding time are filled in from the Ride Guide build (None); the rest come from the card.
DATA = None

# --- Scenic and beach ---
shop('52416633', 'mt-tinbeerwah',
     [L('Mt Tinbeerwah Lookout', -26.38965, 152.9744, 1), L('Tewantin National Park', -26.40061, 153.00101), L('Lake Doonella', -26.40142, 153.0377),
      L('Noosa River', -26.39776, 153.05701), L('Lake Weyba', -26.42165, 153.0718)], nauto=4, peak='Lookout car park')

shop('52202908', 'pirate-park-kids',
     [L('Pirate Park', -26.39783, 153.05618, 1), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.3935, 153.0470),
      L('Weyba Creek mangroves', -26.40735, 153.07463), L('Noosa Marina', -26.39409, 153.04077, 3)], nauto=4, peak=None)

shop('52186029', 'full-noosa',
     [L('Noosa National Park', -26.38146, 153.09879, 1), L('Laguna Lookout', -26.39101, 153.096, 1), L('Noosa Spit', -26.3814, 153.08042),
      L('Hastings Street', -26.3878, 153.0875, 3), L('Lake Weyba', -26.42165, 153.0718), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)],
     nauto=3, peak='Laguna Lookout')

shop('52219299', 'noosa-surf-beaches',
     [S('52219299', 'Peregian Beach', -26.48136, 153.09676, 1), L('Lake Weyba', -26.43, 153.075)], nauto=6, peak=None, extra=('BCH',))

shop('52201147', 'noosa-north-shore-beach',
     [L('North Shore ferry', -26.3732, 153.03909, 1), L('Beach access', -26.35464, 153.06484, 1), S('52201147', 'Noosa North Shore beach', -26.335, 153.064, 1),
      L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)], nauto=4, peak=None, yaw=285)

# --- Mountain bike ---
shop('52417417', 'wooroi-wetlands-mtb',
     [L('Wooroi picnic ground', -26.4002, 153.00976, 1), S('52417417', 'Secrets', -26.4030, 153.0020), S('52417417', 'Glider', -26.40973, 153.00291),
      S('52417417', 'Gyndier Drive', -26.4008, 153.0005, 3), L('Lake Doonella', -26.40142, 153.0377), L('Tewantin National Park', -26.4125, 152.9975, 3, fit=False)],
     nauto=2, peak=None)

shop('57376755', 'lake-weyba-tewantin-forest',
     [L('Lake Weyba', -26.445, 153.068, 1), S('57376755', 'Lakeside path', -26.4485, 153.05414), S('57376755', 'Annie Drive trail', -26.46465, 153.06406, 3),
      S('57376755', 'Monak Road', -26.4705, 153.058, 3), L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377)],
     nauto=4, peak=None)

shop('57358075', 'tewantin-mtb-trails',
     [S('57358075', 'Trailblazer', -26.4125, 152.9960, 1), S('57358075', 'Waterfall', -26.40913, 153.00136), S('57358075', 'Secrets', -26.4030, 153.0020),
      S('57358075', 'Turn 10', -26.40412, 152.99175), S('57358075', 'Crosscut', -26.4160, 153.0062, 3), S('57358075', 'Powerline Track', -26.4118, 153.0200, 3),
      L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377, 4)], nauto=1, peak=None)

# --- Gravel ---
GH = lambda rid: S(rid, 'Garmin Hill', -26.4019, 152.9930, 1)
shop('55391957', 'ringtail-loop',
     [GH('55391957'), S('55391957', 'Ringtail Creek Road', -26.3505, 152.940, 1)], nauto=7, peak=None)

shop('55391935', 'yurol-forest-loop',
     [GH('55391935'), S('55391935', 'Porters Firebreak', -26.3700, 152.888, 1), S('55391935', 'Ringtail Creek Road', -26.3505, 152.940, 2),
      S('55391935', 'Kennedys Road', -26.378, 152.900, 3)], nauto=6, peak=None)

# --- Road ---
shop('57344785', 'noosa-tri-sampler',
     [GH('57344785'), S('57344785', 'Cooroy turnaround', -26.41737, 152.91048, 1), S('57344785', 'Gympie Terrace', -26.3930, 153.0560, 3)], nauto=6, peak='Sunrise Road')

shop('57344784', 'lakes-ride-garmin-hill',
     [L('Mt Tinbeerwah lookout', -26.38712, 152.97332, 1), GH('57344784'), L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)],
     nauto=6, peak='Mt Tinbeerwah lookout')

shop('57347327', 'coolum-coast',
     [L('Mudjimba', -26.61861, 153.0925, 1), L('Mt Coolum', -26.565, 153.0889, 1), L('Twin Waters', -26.63, 153.08361, 3)], nauto=8, peak=None, extra=('BCH',))

shop('57344787', 'pomona-loop',
     [GH('57344787'), L('Pomona', -26.3625, 152.85639, 1), L('Kin Kin', -26.26333, 152.87333, 1)], nauto=7, peak='Pinbarren')


# ---------------- Hinterland, By Earth and Ocean ----------------
NAMED = {'Woondum National Park': (-26.28889, 152.81083), 'Pomona': (-26.3625, 152.85639), 'Kin Kin': (-26.26333, 152.87333),
         'Cooran': (-26.33528, 152.82306), 'Mt Cooroora': (-26.37139, 152.83806), 'Mt Tinbeerwah': (-26.39028, 152.97528),
         'Lake Weyba': (-26.445, 153.068), 'Lake Cootharaba': (-26.2667, 153.0167)}
FIN = L('Finish: the shop, Noosaville', *SHOP, pri=0, kind='finish', down=True)


def hint(rid, slug, labels=(), nauto=9, peak=None, skip=()):
    """A hinterland point to point ride: map settings (slug names the map in the cache; keep it, or the map is drawn again)."""
    if rid not in R:
        return
    r, w = R[rid], words(rid)
    start = (r['pts'][0][0], r['pts'][0][1])
    sname = 'Start: Pomona' if start[0] < -26.36 else 'Start: James McKane Lookout'
    lab = [L(sname, *start, pri=0, kind='start'), FIN] + list(labels)
    text = ' '.join([r['desc']] + w['hl'] + [w['sub']])
    for n, (y, x) in NAMED.items():
        if n in text and not any(n.lower() in l['n'].lower() for l in lab):
            lab.append(L(n, y, x, pri=1.5, fit=False))
    lab += auto(rid, lab, nauto, skip=skip)
    gravel = 'gravel' in w['kick'].lower()
    RIDES[rid] = dict(slug=slug, **w, labels=lab, curated_labels=list(labels), ex=2.0, style='beo', color=GOLD, peak=peak, brand='beo',
                      group='Hinterland gravel' if gravel else 'Hinterland mountain bike')


# Mothar Mountain rock pools, Boulder Creek and Woondum Creek junction (aussiebushwalking.com); both Rockpools routes pass within 70 m
ROCKPOOLS = L('Mothar Mountain rock pools', -26.262034, 152.796458, 1)

hint('55105098', 'pomona-to-noosa-gravel')
hint('55105149', 'treetops-to-tewantin-gravel')
hint('54657933', 'the-cooroora-traverse-gravel')
hint('54989491', 'mary-valley-bound-gravel')
hint('55104485', 'magic-mary-gravel')
hint('55360460', 'forests-farms-foreshore-gravel', labels=[L('Lake Weyba', -26.445, 153.068, 1)])
hint('54989036', 'valleys-vistas-gravel')
hint('55105004', 'through-lake-country-gravel', labels=[L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)])
hint('54987451', 'rockpools-ridgelines-gravel', labels=[ROCKPOOLS], skip=('Mt Boulder',))
# mountain bike
hint('54672630', 'peak-to-peak-mtb')
hint('55408442', 'country-towns-canopies-mtb')
hint('55404690', 'everglades-vistas-mtb')
hint('54660724', 'forest-farms-noosa-mtb')
hint('55404891', 'rockpools-ridgelines-mtb', labels=[ROCKPOOLS], skip=('Mt Boulder',))

ORDER_SHOP = ['52202908', '52186029', '52219299', '52201147', '52416633', '52417417', '57376755', '57358075',
              '55391957', '55391935', '57344785', '57344784', '57347327', '57344787']
ORDER_HINT = ['55105098', '55105149', '54657933', '54989491', '55104485', '55360460', '54989036', '55105004', '54987451',
              '54672630', '55408442', '55404690', '54660724', '55404891']


# ---------------- a live ride with no map settings above: a sheet from its card and the Ride Guide data ----------------
KICK_BY_TYPE = {'scenic': 'Scenic from the shop', 'mtb': 'Mountain bike from the shop', 'gravel': 'Gravel from the shop',
                'road': 'Road from the shop', 'hinterlandGravel': 'Hinterland gravel &middot; point to point',
                'hinterlandMtb': 'Hinterland mountain bike &middot; point to point'}
TYPE_ORDER = ['scenic', 'mtb', 'gravel', 'road', 'hinterlandGravel', 'hinterlandMtb']



def generic(rid):
    r = R[rid]
    beo = r['brand'] == 'beo'
    w = words(rid)
    if not w['kick']:
        w['kick'] = KICK_BY_TYPE.get(r['type'], 'Self guided ride')
    if not w['sub']:
        first = re.split(r'(?<=[.!?])\s', ' '.join(story(r['desc'], [r['name'], w['title']], 400)) or '')[0]
        w['sub'] = first if len(first) <= 80 else ''
    if not w['hl']:
        w['hl'] = [p['n'] for p in r['pois'] if p['t'] not in ('caution', 'finish', 'toilet', 'turn')][:4]
    if r['pts'] and math.hypot((r['pts'][0][0] - SHOP[0]) * 111, (r['pts'][0][1] - SHOP[1]) * 99.6) < 1.5 and not beo:
        lab = [L('Start and finish: Bike On', *SHOP, pri=0, kind='start', down=True)]
    else:
        lab = [L('Start', r['pts'][0][0], r['pts'][0][1], pri=0, kind='start'), L('Finish', r['pts'][-1][0], r['pts'][-1][1], pri=0, kind='finish', down=True)]
    lab += auto(rid, lab, 6)
    return dict(slug=r['slug'], **w, labels=lab, curated_labels=[], style='beo' if beo else 'bikeon',
                color=GOLD if beo else BLUE, peak=None, brand='beo' if beo else 'bikeon', ex=2.0 if beo else None,
                group=w['kick'], generic=True)


for _rid in R:
    if _rid not in RIDES:
        RIDES[_rid] = generic(_rid)
        (ORDER_HINT if RIDES[_rid]['brand'] == 'beo' else ORDER_SHOP).append(_rid)
ORDER_SHOP = [k for k in ORDER_SHOP if k in RIDES]
ORDER_HINT = [k for k in ORDER_HINT if k in RIDES]


def live_text(rid):
    """The sheet's ride story, from the ride's current description in the Ride Guide data."""
    c, r = RIDES[rid], R[rid]
    return story(r['desc'], [r['name'], c['title'], clean_title(r['name'])])


if __name__ == '__main__':
    for k in ORDER_SHOP + ORDER_HINT:
        r = RIDES[k]
        print(k, r['slug'], '|', r['title'], '|', r['kick'], '|', ', '.join(l['n'] for l in r['labels']))
