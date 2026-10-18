"""What each ride sheet says that the Ride Guide data does not: title, category, sell line, highlights, level,
surface, bike, the note, and the place names pinned on the 3D map (with the camera angle where one was chosen).
Ported from the Branding Bob ride sheets (4 to 7 Oct 2026; facts follow the Product Truth, 4 Oct 2026).

Comes from the Ride Guide build every time, so it follows Ride with GPS by itself (Ben, 18/10/2026):
  the ride story (the ride's description), distance, climbing and riding time.
A live ride that has no entry here still gets a sheet, made from the Ride Guide data alone (listed in the manifest).
"""
import json, math, os, re
from paths import HERE
from routes_data import load_routes
R = load_routes()
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


# ---------------- ride content ----------------
RIDES = {}


def shop(rid, slug, title, kick, sub, hl, stats, note, labels, nauto=5, peak=None, extra=(), **kw):
    if rid not in R:
        return
    lab = [L('Start and finish: Bike On', *SHOP, pri=0, kind='start', down=True)] + labels
    lab += auto(rid, lab, nauto, extra)
    RIDES[rid] = dict(slug=slug, title=title, kick=kick, sub=sub, hl=hl, stats=stats, note=note, labels=lab,
                      curated_labels=labels, style='bikeon', color=BLUE, peak=peak, brand='bikeon', group=kick, **kw)


# Stats: Distance, Climbing and Riding time are filled in from the Ride Guide build (DATA); the rest are as written.
DATA = None

# --- Scenic and beach ---
shop('52416633', 'mt-tinbeerwah', 'Mt Tinbeerwah Ride', 'Scenic from the shop',
     'Fire tower lookout with 360 degree views, then a flowing descent',
     ['Fire tower lookout', 'Lake Doonella wetlands', 'Tewantin National Park', 'Noosa River cafes'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     RIDING_NOTE + ' Allow time for the walk up to the lookout.',
     [L('Mt Tinbeerwah Lookout', -26.38965, 152.9744, 1), L('Tewantin National Park', -26.40061, 153.00101), L('Lake Doonella', -26.40142, 153.0377),
      L('Noosa River', -26.39776, 153.05701), L('Lake Weyba', -26.42165, 153.0718)], nauto=4, peak='Lookout car park')

shop('52202908', 'pirate-park-kids', 'Pirate Park Kids Ride', 'Scenic from the shop',
     'Flat river paths to the pirate ship playground, ice creams on the way',
     ['Pirate Park playground', 'Noosa River foreshore', 'Lake Doonella wetlands', 'Weyba Creek mangroves'],
     [DATA, ('Flat', 'Terrain'), DATA, ('Family', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'or kids bikes')],
     RIDING_NOTE + ' Allow time for Pirate Park and an ice cream.',
     [L('Pirate Park', -26.39783, 153.05618, 1), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.3935, 153.0470),
      L('Weyba Creek mangroves', -26.40735, 153.07463), L('Noosa Marina', -26.39409, 153.04077, 3)], nauto=4, peak=None)

shop('52186029', 'full-noosa', 'The Full Noosa Ride', 'Scenic from the shop',
     'Every Noosa highlight in one loop, Main Beach to Laguna Lookout',
     ['Noosa Spit and river', 'Noosa National Park', 'Hastings Street cafes', 'Laguna Lookout'],
     [DATA, DATA, DATA, ('Relaxed', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     RIDING_NOTE + ' Allow time for Hastings Street, the national park walk and Laguna Lookout.',
     [L('Noosa National Park', -26.38146, 153.09879, 1), L('Laguna Lookout', -26.39101, 153.096, 1), L('Noosa Spit', -26.3814, 153.08042),
      L('Hastings Street', -26.3878, 153.0875, 3), L('Lake Weyba', -26.42165, 153.0718), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)],
     nauto=3, peak='Laguna Lookout')

shop('52219299', 'noosa-surf-beaches', 'Noosa Surf Beaches Ride', 'Scenic from the shop',
     'Gentle coast riding through Sunshine, Marcus and Peregian Beach',
     ['Sunshine Beach', 'Castaways and Marcus', 'Peregian Beach village', 'Weyba Creek mangroves'],
     [DATA, DATA, DATA, ('Relaxed', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     RIDING_NOTE + ' Allow time for beach stops and a coffee in Peregian Beach village.',
     [S('52219299', 'Peregian Beach', -26.48136, 153.09676, 1), L('Lake Weyba', -26.43, 153.075)], nauto=6, peak=None, extra=('BCH',))

shop('52201147', 'noosa-north-shore-beach', 'Noosa North Shore Beach Ride', 'Beach from the shop',
     'Ferry across and ride open beach between the dunes and the Pacific',
     ['North Shore ferry', 'Open beach riding', 'Dunes and ocean views', 'Noosa River cafes'],
     [DATA, ('Flat', 'Terrain'), DATA, ('Relaxed', 'Level'), ('Paths & sand', 'Surface'), ('Fat tyre', 'e-Bike only')],
     RIDING_NOTE + ' Allow time for the ferry. Tide dependent. No swimming: the beach is unpatrolled.',
     [L('North Shore ferry', -26.3732, 153.03909, 1), L('Beach access', -26.35464, 153.06484, 1), S('52201147', 'Noosa North Shore beach', -26.335, 153.064, 1),
      L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)], nauto=4, peak=None, yaw=285)

# --- Mountain bike ---
shop('52417417', 'wooroi-wetlands-mtb', 'Wooroi & Wetlands MTB Ride', 'Mountain bike from the shop',
     'Flowing green and blue singletrack, home through the wetlands',
     ['Wooroi picnic ground', 'Glider and Indy', 'The Secrets descent', 'Lake Doonella wetlands'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Trail & path', 'Surface'), ('eMTB', 'or dual suspension')],
     RIDING_NOTE + ' Secrets is ridden descending only.',
     [L('Wooroi picnic ground', -26.4002, 153.00976, 1), S('52417417', 'Secrets', -26.4030, 153.0020), S('52417417', 'Glider', -26.40973, 153.00291),
      S('52417417', 'Gyndier Drive', -26.4008, 153.0005, 3), L('Lake Doonella', -26.40142, 153.0377), L('Tewantin National Park', -26.4125, 152.9975, 3, fit=False)],
     nauto=2, peak=None)

shop('57376755', 'lake-weyba-tewantin-forest', 'Lake Weyba and Tewantin Forest Loop', 'Mountain bike from the shop',
     'Forest tracks through koala country and along Lake Weyba',
     ['Lake Weyba foreshore', 'Tewantin National Park', 'Forest fire trails', 'Weyba Downs'],
     [DATA, DATA, DATA, ('Relaxed', 'Level'), ('Mixed dirt', 'Surface'), ('eMTB', 'or dual suspension')],
     RIDING_NOTE + ' The lakeside path can be sandy or wet.',
     [L('Lake Weyba', -26.445, 153.068, 1), S('57376755', 'Lakeside path', -26.4485, 153.05414), S('57376755', 'Annie Drive trail', -26.46465, 153.06406, 3),
      S('57376755', 'Monak Road', -26.4705, 153.058, 3), L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377)],
     nauto=4, peak=None)

shop('57358075', 'tewantin-mtb-trails', 'Tewantin MTB Trails', 'Mountain bike from the shop',
     'Trailblazer, Waterfall, Glider and two runs down Secrets',
     ['Trailblazer and Waterfall', 'Two runs down Secrets', 'Turn 10', 'About 80% dirt'],
     [DATA, DATA, DATA, ('Advanced', 'Level'), ('Singletrack', 'Surface'), ('eMTB', 'or dual suspension')],
     RIDING_NOTE + ' Secrets is descending only, so expect riders from above.',
     [S('57358075', 'Trailblazer', -26.4125, 152.9960, 1), S('57358075', 'Waterfall', -26.40913, 153.00136), S('57358075', 'Secrets', -26.4030, 153.0020),
      S('57358075', 'Turn 10', -26.40412, 152.99175), S('57358075', 'Crosscut', -26.4160, 153.0062, 3), S('57358075', 'Powerline Track', -26.4118, 153.0200, 3),
      L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377, 4)], nauto=1, peak=None)

# --- Gravel ---
GH = lambda rid: S(rid, 'Garmin Hill', -26.4019, 152.9930, 1)
shop('55391957', 'ringtail-loop', 'Ringtail Loop', 'Gravel from the shop',
     'Climb Garmin Hill, then a fast forest gravel descent',
     ['Garmin Hill climb', 'Tinbeerwah high country', 'Ringtail Creek Road', 'Lake Cooroibah'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Mostly sealed', 'Surface'), ('Gravel bike', 'or hardtail')],
     RIDING_NOTE + ' Gravel changes with the weather, so ride to the conditions.',
     [GH('55391957'), S('55391957', 'Ringtail Creek Road', -26.3505, 152.940, 1)], nauto=7, peak=None)

shop('55391935', 'yurol-forest-loop', 'Yurol Forest Loop', 'Gravel from the shop',
     'Farmland, tall timber and forest gravel with no traffic lights',
     ['Garmin Hill climb', 'Lake Macdonald farmland', '12 km of forest gravel', 'Ringtail Creek Road'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('17 km gravel', 'Surface'), ('Gravel bike', 'or hardtail')],
     RIDING_NOTE + ' The gravel roads are shared with cars and farm vehicles, so keep left.',
     [GH('55391935'), S('55391935', 'Porters Firebreak', -26.3700, 152.888, 1), S('55391935', 'Ringtail Creek Road', -26.3505, 152.940, 2),
      S('55391935', 'Kennedys Road', -26.378, 152.900, 3)], nauto=6, peak=None)

# --- Road ---
shop('57344785', 'noosa-tri-sampler', 'Noosa Tri Sampler', 'Road from the shop',
     'The Noosa Tri bike course and Garmin Hill, coffee in Cooroy',
     ['Noosa Tri bike course', 'Garmin Hill climb', 'Cooroy cafes', 'Gympie Terrace riverside'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     RIDING_NOTE + ' Narrow shoulders on Cooroy Noosa Road.',
     [GH('57344785'), S('57344785', 'Cooroy turnaround', -26.41737, 152.91048, 1), S('57344785', 'Gympie Terrace', -26.3930, 153.0560, 3)], nauto=6, peak='Sunrise Road')

shop('57344784', 'lakes-ride-garmin-hill', 'Lakes Ride with Garmin Hill', 'Road from the shop',
     'Garmin Hill, Mt Tinbeerwah and lakeside Boreen Point',
     ['Mt Tinbeerwah lookout', 'Boreen Point', 'Lake Cootharaba', 'Cootharaba farmland'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     RIDING_NOTE + ' Allow time for the walk to the lookout and a stop at Boreen Point.',
     [L('Mt Tinbeerwah lookout', -26.38712, 152.97332, 1), GH('57344784'), L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)],
     nauto=6, peak='Mt Tinbeerwah lookout')

shop('57347327', 'coolum-coast', 'Coolum Coast Ride', 'Road from the shop',
     'Down the coast road past Mt Coolum to Mudjimba',
     ['David Low Way', 'Mt Coolum', 'Mudjimba Esplanade', 'Peregian Beach coffee'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     RIDING_NOTE + ' The route stays on the road the whole way.',
     [L('Mudjimba', -26.61861, 153.0925, 1), L('Mt Coolum', -26.565, 153.0889, 1), L('Twin Waters', -26.63, 153.08361, 3)], nauto=8, peak=None, extra=('BCH',))

shop('57344787', 'pomona-loop', 'Pomona Loop', 'Road from the shop',
     'The big one: Pomona under Mt Cooroora, then over to Kin Kin',
     ['Pomona and Mt Cooroora', 'Over the range at Pinbarren', 'Kin Kin village', 'Cootharaba farmland'],
     [DATA, DATA, DATA, ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     RIDING_NOTE + ' Long gaps between towns, so start early.',
     [GH('57344787'), L('Pomona', -26.3625, 152.85639, 1), L('Kin Kin', -26.26333, 152.87333, 1)], nauto=7, peak='Pinbarren')


# ---------------- Hinterland, By Earth and Ocean ----------------
NAMED = {'Woondum National Park': (-26.28889, 152.81083), 'Pomona': (-26.3625, 152.85639), 'Kin Kin': (-26.26333, 152.87333),
         'Cooran': (-26.33528, 152.82306), 'Mt Cooroora': (-26.37139, 152.83806), 'Mt Tinbeerwah': (-26.39028, 152.97528),
         'Lake Weyba': (-26.445, 153.068), 'Lake Cootharaba': (-26.2667, 153.0167)}
FIN = L('Finish: the shop, Noosaville', *SHOP, pri=0, kind='finish', down=True)


def hint(rid, kind, title, sub, hl, level, surface, labels=(), nauto=9, peak=None, skip=()):
    if rid not in R:
        return
    r = R[rid]
    start = (r['pts'][0][0], r['pts'][0][1])
    sname = 'Start: Pomona' if start[0] < -26.36 else 'Start: James McKane Lookout'
    lab = [L(sname, *start, pri=0, kind='start'), FIN] + list(labels)
    text = ' '.join([r['desc']] + hl + [sub])
    for n, (y, x) in NAMED.items():
        if n in text and not any(n.lower() in l['n'].lower() for l in lab):
            lab.append(L(n, y, x, pri=1.5, fit=False))
    lab += auto(rid, lab, nauto, skip=skip)
    gravel = kind == 'gravel'
    RIDES[rid] = dict(slug=re.sub(r'[^a-z0-9]+', '-', (title + (' gravel' if gravel else ' mtb')).lower()).strip('-'),
                      title=title, kick=('Hinterland gravel' if gravel else 'Hinterland mountain bike') + ' &middot; point to point',
                      sub=sub, hl=hl, stats=[DATA, DATA, DATA, (level, 'Level'), (surface, 'Surface'),
                                             ('Gravel bike' if gravel else 'Mountain bike', 'Bring or hire')],
                      note='Riding time is time on the bike. Allow extra for stops and the drive to the start. Hire bikes back by 4pm.',
                      labels=lab, curated_labels=list(labels), ex=2.0, style='beo', color=GOLD, peak=peak, brand='beo',
                      group='Hinterland gravel' if gravel else 'Hinterland mountain bike')


# Mothar Mountain rock pools, Boulder Creek and Woondum Creek junction (aussiebushwalking.com); both Rockpools routes pass within 70 m
ROCKPOOLS = L('Mothar Mountain rock pools', -26.262034, 152.796458, 1)

hint('55105098', 'gravel', 'Pomona to Noosa', 'Country town to coast on smooth gravel and quiet roads',
     ['Pomona and Mt Cooroora', 'Noosa Trail Network', 'Forest lined gravel', 'Lake Doonella wetlands'], 'Relaxed', 'Gravel & road')
hint('55105149', 'gravel', 'Treetops to Tewantin', 'Forest gravel and country lanes from the high country to the river',
     ['James McKane Lookout', 'Rainforest lined gravel', 'Rolling hills and farmland', 'A steady descent to Tewantin'], 'Relaxed', 'Gravel & road')
hint('54657933', 'gravel', 'The Cooroora Traverse', 'The Cooroora Trail, big hinterland views and rewarding descents',
     ['The Cooroora Trail', 'Views across the ranges', 'Rewarding descents', 'Noosa Trail Network'], 'Moderate', 'Mostly trail')
hint('54989491', 'gravel', 'Mary Valley Bound', 'Open Mary Valley country and new angles on Mt Cooroora',
     ['Woondum National Park', 'Mary Valley farmland', 'Mt Cooroora views', 'Ringtail and Yurol forests'], 'Relaxed', 'Gravel & road')
hint('55104485', 'gravel', 'Magic Mary', 'A full day of Mary Valley gravel, with lunch in Pomona',
     ['Mary Valley country', 'Lunch in Pomona', 'Mt Cooroora views', 'Shaded forest corridors'], 'Relaxed', 'Gravel & road')
hint('55360460', 'gravel', 'Forests, Farms & Foreshore', 'Rainforest to Lake Weyba: the whole region in one big day',
     ['Towering eucalypt forest', 'Views of the hinterland peaks', 'Lake Weyba shores', 'Noosa foreshore'], 'Challenging', 'Rough gravel',
     labels=[L('Lake Weyba', -26.445, 153.068, 1)])
hint('54989036', 'gravel', 'Valleys & Vistas', 'A full day of remote gravel, ridgelines and long views',
     ['Woondum National Park', 'Open ridgelines', 'Remote backroads', 'Big hinterland views'], 'Moderate', 'Gravel & road')
hint('55105004', 'gravel', 'Through Lake Country', 'Woondum forests east to Boreen Point and Lake Cootharaba',
     ['Woondum forests', 'Boreen Point', 'Lake Cootharaba', 'Open lake country'], 'Moderate', 'Gravel & road',
     labels=[L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)])
hint('54987451', 'gravel', 'Rockpools & Ridgelines', 'Remote, rugged and steep: the wildest gravel in the hinterland',
     ['Woondum National Park', 'Beenham Valley', 'Ringtail Forest', 'Remote ridgelines'], 'Challenging', 'Rough gravel',
     labels=[ROCKPOOLS], skip=('Mt Boulder',))
# mountain bike
hint('54672630', 'mtb', 'Peak to Peak', 'Mt Cooroora to Mt Tinbeerwah on forest tracks and gravel',
     ['Mt Cooroora', 'Mt Tinbeerwah', 'Forest trails', 'Volcanic peak views'], 'Intermediate', 'Trail & gravel')
hint('55408442', 'mtb', 'Country Towns & Canopies', 'A big opening descent, then Cooran, Pomona and the forest',
     ['The opening descent', 'Cooran and Pomona', 'Volcanic peak views', 'Forest canopy trails'], 'Intermediate', 'Trail & gravel')
hint('55404690', 'mtb', 'Everglades Vistas', 'Kin Kin ridgelines with views over the Noosa Everglades',
     ['Noosa Everglades views', 'Kin Kin hinterland', 'Remote ridgelines', 'Long descents'], 'Advanced', 'Trail & gravel')
hint('54660724', 'mtb', 'Forest, Farms & Noosa', 'Woondum ridgelines and two of the network\'s best descents',
     ['Woondum National Park', 'Two big descents', 'Ridgeline views', 'Rolling farmland'], 'Advanced', 'Trail & gravel')
hint('55404891', 'mtb', 'Rockpools & Ridgelines', 'Woondum descents, the Mothar Mountain rock pools and Kin Kin ridgelines',
     ['Mothar Mountain rock pools', 'The Woondum descent', 'Kin Kin farmland', 'Ridgeline panoramas'], 'Advanced', 'Trail & gravel',
     labels=[ROCKPOOLS], skip=('Mt Boulder',))

ORDER_SHOP = ['52202908', '52186029', '52219299', '52201147', '52416633', '52417417', '57376755', '57358075',
              '55391957', '55391935', '57344785', '57344784', '57347327', '57344787']
ORDER_HINT = ['55105098', '55105149', '54657933', '54989491', '55104485', '55360460', '54989036', '55105004', '54987451',
              '54672630', '55408442', '55404690', '54660724', '55404891']


# ---------------- a live ride with no entry above: a sheet from the Ride Guide data alone ----------------
KICK_BY_TYPE = {'scenic': 'Scenic from the shop', 'mtb': 'Mountain bike from the shop', 'gravel': 'Gravel from the shop',
                'road': 'Road from the shop', 'hinterlandGravel': 'Hinterland gravel &middot; point to point',
                'hinterlandMtb': 'Hinterland mountain bike &middot; point to point'}
TYPE_ORDER = ['scenic', 'mtb', 'gravel', 'road', 'hinterlandGravel', 'hinterlandMtb']


def clean_title(name):
    return re.sub(r'\s+Self[- ]Guided Tour\b', '', name or '').strip()


def generic(rid):
    r = R[rid]
    beo = r['brand'] == 'beo'
    title = clean_title(r['name'])
    first = re.split(r'(?<=[.!?])\s', ' '.join(story(r['desc'], [r['name'], title], 400)) or '')[0]
    sub = first if len(first) <= 80 else ''
    stops = [p['n'] for p in r['pois'] if p['t'] not in ('caution', 'finish', 'toilet', 'turn')][:4]
    if r['pts'] and math.hypot((r['pts'][0][0] - SHOP[0]) * 111, (r['pts'][0][1] - SHOP[1]) * 99.6) < 1.5 and not beo:
        lab = [L('Start and finish: Bike On', *SHOP, pri=0, kind='start', down=True)]
    else:
        lab = [L('Start', r['pts'][0][0], r['pts'][0][1], pri=0, kind='start'), L('Finish', r['pts'][-1][0], r['pts'][-1][1], pri=0, kind='finish', down=True)]
    lab += auto(rid, lab, 6)
    return dict(slug=r['slug'], title=title, kick=KICK_BY_TYPE.get(r['type'], 'Self guided ride'), sub=sub, hl=stops,
                stats=[DATA, DATA, DATA], note=RIDING_NOTE, labels=lab, curated_labels=[], style='beo' if beo else 'bikeon',
                color=GOLD if beo else BLUE, peak=None, brand='beo' if beo else 'bikeon', ex=2.0 if beo else None,
                group=KICK_BY_TYPE.get(r['type'], 'Other rides'), generic=True)


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
        print(k, r['slug'], '|', ', '.join(l['n'] for l in r['labels']))
