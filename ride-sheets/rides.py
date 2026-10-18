"""Content and map labels for every ride map sheet. Facts follow the Product Truth (4 Oct 2026)."""
import json, math, os, re
from paths import HERE
from routes_data import load_routes
R = load_routes()
PLACES = json.load(open(os.path.join(HERE, 'places.json')))

SHOP = (-26.40793, 153.04347)
BLUE, GOLD = '#2F86E6', '#F5CA3A'
QR = {
    'scenic': ('https://ridewithgps.com/experiences/57462?app_code=9RUP2', '9RUP2', 'Scenic'),
    'mtb': ('https://ridewithgps.com/experiences/57461?app_code=TX2YF', 'TX2YF', 'Mountain Bike'),
    'gravel': ('https://ridewithgps.com/experiences/57492?app_code=PN9CR', 'PN9CR', 'Gravel'),
    'road': ('https://ridewithgps.com/experiences/57460?app_code=82BZT', '82BZT', 'Road'),
    'hgravel': ('https://ridewithgps.com/experiences/48408?app_code=DY84T', 'DY84T', 'Hinterland Gravel'),
    'hmtb': ('https://ridewithgps.com/experiences/48426?app_code=CRUHL', 'CRUHL', 'Hinterland MTB'),
}


def L(n, y, x, pri=2, kind='place', **kw):
    return dict(n=n, y=y, x=x, pri=pri, kind=kind, **kw)


def near_route(rid, y, x):
    """Snap a point to the nearest route point."""
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


# ---------------- ride content ----------------
SHOP_NOTE_BIKE = {'cruiser': ('e-Bike', 'Cruiser'), 'fat': ('Fat tyre', 'e-Bike only'), 'emtb': ('eMTB', 'or dual suspension'),
                  'gravel': ('Gravel bike', 'or hardtail'), 'road': ('Road bike', 'Premium BMC')}

RIDES = {}


def shop(rid, slug, title, kick, qr, sub, paras, hl, stats, note, photos, labels, nauto=5, peak=None, extra=(), **kw):
    lab = [L('Start and finish: Bike On', *SHOP, pri=0, kind='start', down=True)] + labels
    lab += auto(rid, lab, nauto, extra)
    RIDES[rid] = dict(slug=slug, title=title, kick=kick, qr=QR[qr], sub=sub, paras=paras, hl=hl, stats=stats, note=note,
                      photos=photos, labels=lab, style='bikeon', color=BLUE, peak=peak, brand='bikeon', **kw)


# Photo picks per ride, by Digital Assets library file name. Not printed since 7/10/2026 (the app QR cards took their place);
# kept as the shortlist for the Ride Guide edition's ride photo.
HIRE = K = ''

# --- Scenic and beach ---
shop('52416633', 'mt-tinbeerwah', 'Mt Tinbeerwah Ride', 'Scenic from the shop', 'scenic',
     'Fire tower lookout with 360 degree views, then a flowing descent',
     ['Leave the shop on the wetland paths around Lake Doonella, cross Tewantin National Park and climb a quiet road to the fire tower on Mt Tinbeerwah, 265 m above Noosa. The 360 degree view takes in the Noosa Everglades system, the coast and, on a clear day, the Glass House Mountains.',
      'Then it is a fun descent back through the forest, a coffee or a swim by the Noosa River, and the birdlife of Lake Weyba before you roll home.'],
     ['Fire tower lookout', 'Lake Doonella wetlands', 'Tewantin National Park', 'Noosa River cafes'],
     [('40 km', 'Distance'), ('420 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Moderate', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     'Experience time includes stops and the walk up to the lookout.',
     [K + 'SummitToSeaEbike-044.jpg', K + 'SummitToSeaEbike-040.jpg', K + 'SummitToSeaEbike-005.jpg'],
     [L('Mt Tinbeerwah Lookout', -26.38965, 152.9744, 1), L('Tewantin National Park', -26.40061, 153.00101), L('Lake Doonella', -26.40142, 153.0377),
      L('Noosa River', -26.39776, 153.05701), L('Lake Weyba', -26.42165, 153.0718)], nauto=4, peak='Lookout car park')

shop('52202908', 'pirate-park-kids', 'Pirate Park Kids Ride', 'Scenic from the shop', 'scenic',
     'Flat river paths to the pirate ship playground, ice creams on the way',
     ['A short, flat family loop on paths straight from the shop. Follow the Lake Doonella wetlands to the Noosa River, then ride the riverside paths to Pirate Park, the adventure playground the kids will talk about all week.',
      'There is time for a good play, an ice cream by the river and a look at the boats along the foreshore before the easy roll home past the Weyba Creek mangroves.'],
     ['Pirate Park playground', 'Noosa River foreshore', 'Lake Doonella wetlands', 'Weyba Creek mangroves'],
     [('16 km', 'Distance'), ('Flat', 'Terrain'), ('2 to 3 hrs', 'Experience time'), ('Family', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'or kids bikes')],
     'Experience time includes playtime at Pirate Park and an ice cream stop.',
     [HIRE + 'BikeOnHire-049.jpg', HIRE + 'BikeOnHire-008.jpg', HIRE + 'BikeOnHire-044.jpg'],
     [L('Pirate Park', -26.39783, 153.05618, 1), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.3935, 153.0470),
      L('Weyba Creek mangroves', -26.40735, 153.07463), L('Noosa Marina', -26.39409, 153.04077, 3)], nauto=4, peak=None)

shop('52186029', 'full-noosa', 'The Full Noosa Ride', 'Scenic from the shop', 'scenic',
     'Every Noosa highlight in one loop, Main Beach to Laguna Lookout',
     ['Follow the Lake Doonella wetlands and the Noosa River esplanade out to the Noosa Spit, then into Noosa National Park, where the bikes wait at the racks and the coastal track is on foot. Back on the bike, Hastings Street is made for a coffee stop.',
      'The e-Bike makes light work of the climb to Laguna Lookout and its views over the bay and hinterland, before an easy run past the calm shores of Lake Weyba and home on flat paths.'],
     ['Noosa Spit and river', 'Noosa National Park', 'Hastings Street cafes', 'Laguna Lookout'],
     [('34 km', 'Distance'), ('290 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Relaxed', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     'Experience time includes stops at Hastings Street, the national park walk and Laguna Lookout.',
     [K + 'NoosaScenery-001.jpg', HIRE + 'BikeOnHire-046.jpg', HIRE + 'BikeOnHire-014.jpg'],
     [L('Noosa National Park', -26.38146, 153.09879, 1), L('Laguna Lookout', -26.39101, 153.096, 1), L('Noosa Spit', -26.3814, 153.08042),
      L('Hastings Street', -26.3878, 153.0875, 3), L('Lake Weyba', -26.42165, 153.0718), L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)],
     nauto=3, peak='Laguna Lookout')

shop('52219299', 'noosa-surf-beaches', 'Noosa Surf Beaches Ride', 'Scenic from the shop', 'scenic',
     'Gentle coast riding through Sunshine, Marcus and Peregian Beach',
     ['Head east from the shop past the Weyba Creek mangroves to Sunshine Beach, then follow the coastal paths south through Sunrise, Castaways and Marcus Beach, with the national park on one side and the surf just over the dunes.',
      'Turn around at Peregian Beach village for a coffee and a walk on the sand, then cruise home along the coast with the hinterland ranges ahead of you.'],
     ['Sunshine Beach', 'Castaways and Marcus', 'Peregian Beach village', 'Weyba Creek mangroves'],
     [('37 km', 'Distance'), ('330 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Relaxed', 'Level'), ('Sealed', 'Surface'), ('e-Bike', 'Cruiser')],
     'Experience time includes beach stops and a coffee in Peregian Beach village.',
     [HIRE + 'BikeOnHire-046.jpg', HIRE + 'BikeOnHire-011.jpg', HIRE + 'BikeOnHire-001.jpg'],
     [S('52219299', 'Peregian Beach', -26.48136, 153.09676, 1), L('Lake Weyba', -26.43, 153.075)], nauto=6, peak=None, extra=('BCH',))

shop('52201147', 'noosa-north-shore-beach', 'Noosa North Shore Beach Ride', 'Beach from the shop', 'scenic',
     'Ferry across and ride open beach between the dunes and the Pacific',
     ['Ride the river paths from the shop to the Tewantin ferry, cross to the Noosa North Shore and roll straight onto a wild stretch of sand, with the dunes on one side and the open Pacific on the other.',
      'The beach is a gazetted road and the riding is flat and easy, but it needs firm sand around low tide, so the tide sets your start time. Turn for home when you are ready and stop at the river cafes on the way back.'],
     ['North Shore ferry', 'Open beach riding', 'Dunes and ocean views', 'Noosa River cafes'],
     [('31 km', 'Distance'), ('Flat', 'Terrain'), ('3 to 4 hrs', 'Experience time'), ('Relaxed', 'Level'), ('Paths & sand', 'Surface'), ('Fat tyre', 'e-Bike only')],
     'Experience time includes the ferry and beach time. Tide dependent. No swimming: the beach is unpatrolled.',
     [K + 'NthShoreBeachRide-015.jpg', K + 'NthShoreBeachRide-011.jpg', K + 'NthShoreBeachRide-017.jpg'],
     [L('North Shore ferry', -26.3732, 153.03909, 1), L('Beach access', -26.35464, 153.06484, 1), S('52201147', 'Noosa North Shore beach', -26.335, 153.064, 1),
      L('Lake Doonella', -26.40142, 153.0377), L('Noosa River', -26.39776, 153.05701, 3)], nauto=4, peak=None, yaw=285)

# --- Mountain bike ---
shop('52417417', 'wooroi-wetlands-mtb', 'Wooroi & Wetlands MTB Ride', 'Mountain bike from the shop', 'mtb',
     'Flowing green and blue singletrack, home through the wetlands',
     ['Our easy mountain bike loop, straight from the shop. Dirt paths lead to the Wooroi picnic ground in Tewantin National Park, then flowing green and gentle blue trails: Wooroi Track, Glider and Indy, a short climb on Gyndier Drive and a run down Secrets.',
      'Home is on sealed paths past the Lake Doonella wetlands. Mellow gradients and plenty of places to stop, but it still needs practised bike skills, so it is not a ride for novices.'],
     ['Wooroi picnic ground', 'Glider and Indy', 'The Secrets descent', 'Lake Doonella wetlands'],
     [('25 km', 'Distance'), ('245 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Moderate', 'Level'), ('Trail & path', 'Surface'), ('eMTB', 'or dual suspension')],
     'Experience time includes stops at the Wooroi picnic ground. Secrets is ridden descending only.',
     [K + 'WooroiEMTB-093.jpg', K + 'WooroiEMTB-001.jpg', K + 'WooroiEMTB-004.jpg'],
     [L('Wooroi picnic ground', -26.4002, 153.00976, 1), S('52417417', 'Secrets', -26.4030, 153.0020), S('52417417', 'Glider', -26.40973, 153.00291),
      S('52417417', 'Gyndier Drive', -26.4008, 153.0005, 3), L('Lake Doonella', -26.40142, 153.0377), L('Tewantin National Park', -26.4125, 152.9975, 3, fit=False)],
     nauto=2, peak=None)

shop('57376755', 'lake-weyba-tewantin-forest', 'Lake Weyba and Tewantin Forest Loop', 'Mountain bike from the shop', 'mtb',
     'Forest tracks through koala country and along Lake Weyba',
     ['Into Tewantin National Park from the shop, then fire trails and the gravel back roads of Doonan down to Weyba Downs and the lakeside path on the western shore of Lake Weyba, the southern end of the Noosa Everglades system.',
      'Round the south of the lake on the Annie Drive trail, head back through the forest on the Monak Road gravel and fire trail, and pick up the shared paths home. Nearly two thirds of the ride is on dirt.'],
     ['Lake Weyba foreshore', 'Tewantin National Park', 'Forest fire trails', 'Weyba Downs'],
     [('41 km', 'Distance'), ('360 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Relaxed', 'Level'), ('Mixed dirt', 'Surface'), ('eMTB', 'or dual suspension')],
     'Experience time includes foreshore stops. The lakeside path can be sandy or wet.',
     [HIRE + 'BikeOnHire-047.jpg', K + 'StingraysEverglades-135.jpg', K + 'NoosaScenery-003.jpg'],
     [L('Lake Weyba', -26.445, 153.068, 1), S('57376755', 'Lakeside path', -26.4485, 153.05414), S('57376755', 'Annie Drive trail', -26.46465, 153.06406, 3),
      S('57376755', 'Monak Road', -26.4705, 153.058, 3), L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377)],
     nauto=4, peak=None)

shop('57358075', 'tewantin-mtb-trails', 'Tewantin MTB Trails', 'Mountain bike from the shop', 'mtb',
     'Trailblazer, Waterfall, Glider and two runs down Secrets',
     ['A bigger day on the Tewantin National Park (Wooroi) trail network, straight from the shop. The Powerline Track leads in to Crosscut, Trailblazer, Day Dream, Waterfall and Glider, then a climb up Gyndier Drive to Turn 10.',
      'Steeper pinches, faster descents and more technical singletrack than our easy loop, with two runs down Secrets before the Powerline Track brings you home. Newer to mountain biking? Start with Wooroi & Wetlands.'],
     ['Trailblazer and Waterfall', 'Two runs down Secrets', 'Turn 10', 'About 80% dirt'],
     [('25 km', 'Distance'), ('330 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Advanced', 'Level'), ('Singletrack', 'Surface'), ('eMTB', 'or dual suspension')],
     'Experience time includes trail stops. Secrets is descending only, so expect riders from above.',
     [K + 'WooroiEMTB-072.jpg', K + 'WooroiEMTB-003.jpg', K + 'WooroiEMTB-002.jpg'],
     [S('57358075', 'Trailblazer', -26.4125, 152.9960, 1), S('57358075', 'Waterfall', -26.40913, 153.00136), S('57358075', 'Secrets', -26.4030, 153.0020),
      S('57358075', 'Turn 10', -26.40412, 152.99175), S('57358075', 'Crosscut', -26.4160, 153.0062, 3), S('57358075', 'Powerline Track', -26.4118, 153.0200, 3),
      L('Wooroi picnic ground', -26.4002, 153.00976, 3), L('Lake Doonella', -26.40142, 153.0377, 4)], nauto=1, peak=None)

# --- Gravel ---
GH = lambda rid: S(rid, 'Garmin Hill', -26.4019, 152.9930, 1)
shop('55391957', 'ringtail-loop', 'Ringtail Loop', 'Gravel from the shop', 'gravel',
     'Climb Garmin Hill, then a fast forest gravel descent',
     ['A hinterland gravel loop straight from the shop. Climb Garmin Hill, the car free climb Noosa Triathlon racers know well, then cross the Tinbeerwah high country to Lake Macdonald.',
      'Ringtail Creek Road is the reward: about 5 km of gravel, mostly downhill through tall forest. The quiet streets of Cooroibah and the McKinnon Drive path bring you home past Lake Cooroibah and Lake Doonella.'],
     ['Garmin Hill climb', 'Tinbeerwah high country', 'Ringtail Creek Road', 'Lake Cooroibah'],
     [('41 km', 'Distance'), ('390 m', 'Climbing'), ('2.5 to 3.5 hrs', 'Experience time'), ('Moderate', 'Level'), ('Mostly sealed', 'Surface'), ('Gravel bike', 'or hardtail')],
     'Experience time includes stops and breaks. Gravel changes with the weather, so ride to the conditions.',
     [K + 'HinterlandGravel-049.jpg', K + 'HinterlandGravel-051.jpg', K + 'HinterlandGravel-021.jpg'],
     [GH('55391957'), S('55391957', 'Ringtail Creek Road', -26.3505, 152.940, 1)], nauto=7, peak=None)

shop('55391935', 'yurol-forest-loop', 'Yurol Forest Loop', 'Gravel from the shop', 'gravel',
     'Farmland, tall timber and forest gravel with no traffic lights',
     ['A longer hinterland gravel loop from the shop. Climb Garmin Hill, cross the Tinbeerwah high country to Lake Macdonald, then ride farm gravel on Hamilton and Kennedys Roads.',
      'The heart of the ride is almost 12 km of unbroken forest gravel through the Yurol and Ringtail forests on Porters Firebreak and Ringtail Creek Road, before the flat run home through Cooroibah.'],
     ['Garmin Hill climb', 'Lake Macdonald farmland', '12 km of forest gravel', 'Ringtail Creek Road'],
     [('53 km', 'Distance'), ('520 m', 'Climbing'), ('3 to 4 hrs', 'Experience time'), ('Moderate', 'Level'), ('17 km gravel', 'Surface'), ('Gravel bike', 'or hardtail')],
     'Experience time includes stops and breaks. The gravel roads are shared with cars and farm vehicles, so keep left.',
     [K + 'HinterlandGravel-040.jpg', K + 'HinterlandGravel-052.jpg', K + 'HinterlandGravel-017.jpg'],
     [GH('55391935'), S('55391935', 'Porters Firebreak', -26.3700, 152.888, 1), S('55391935', 'Ringtail Creek Road', -26.3505, 152.940, 2),
      S('55391935', 'Kennedys Road', -26.378, 152.900, 3)], nauto=6, peak=None)

# --- Road ---
shop('57344785', 'noosa-tri-sampler', 'Noosa Tri Sampler', 'Road from the shop', 'road',
     'The Noosa Tri bike course and Garmin Hill, coffee in Cooroy',
     ['Ride sections of the Noosa Triathlon bike course straight from the shop. Along the river on Gympie Terrace to Tewantin, out Cooroy Noosa Road and up the 3 km Gyndier Drive climb, Garmin Hill.',
      'Roll on into Cooroy and turn at the Maple Street roundabout, where the cafes are, then enjoy the run back down the range and home via Beckmans Road.'],
     ['Noosa Tri bike course', 'Garmin Hill climb', 'Cooroy cafes', 'Gympie Terrace riverside'],
     [('41 km', 'Distance'), ('340 m', 'Climbing'), ('2 to 3 hrs', 'Experience time'), ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     'Experience time includes a coffee stop in Cooroy. Narrow shoulders on Cooroy Noosa Road.',
     [K + 'HinterlandGravel-047.jpg', K + 'HinterlandGravel-056.jpg', K + 'BiosphereTrailsEMTB-V062.jpg'],
     [GH('57344785'), S('57344785', 'Cooroy turnaround', -26.41737, 152.91048, 1), S('57344785', 'Gympie Terrace', -26.3930, 153.0560, 3)], nauto=6, peak='Sunrise Road')

shop('57344784', 'lakes-ride-garmin-hill', 'Lakes Ride with Garmin Hill', 'Road from the shop', 'road',
     'Garmin Hill, Mt Tinbeerwah and lakeside Boreen Point',
     ['A big road day from the shop. Climb Garmin Hill and Tinbeerwah Road to the Mt Tinbeerwah lookout, the high point of the ride, then lock the bike and walk the short track to the top for 360 degree views.',
      'Back down the range, head north past Lake Cooroibah to Boreen Point on Lake Cootharaba, loop the village and come home a different way through the Cootharaba farmland. Most of the climbing is in the first 20 km.'],
     ['Mt Tinbeerwah lookout', 'Boreen Point', 'Lake Cootharaba', 'Cootharaba farmland'],
     [('71 km', 'Distance'), ('640 m', 'Climbing'), ('3.5 to 4.5 hrs', 'Experience time'), ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     'Experience time includes the walk to the lookout and a stop at Boreen Point.',
     [K + 'SummitToSeaEbike-040.jpg', K + 'SummitToSeaEbike-044.jpg', K + 'HinterlandGravel-047.jpg'],
     [L('Mt Tinbeerwah lookout', -26.38712, 152.97332, 1), GH('57344784'), L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)],
     nauto=6, peak='Mt Tinbeerwah lookout')

shop('57347327', 'coolum-coast', 'Coolum Coast Ride', 'Road from the shop', 'road',
     'Down the coast road past Mt Coolum to Mudjimba',
     ['A coastal road ride straight from the shop. David Low Way runs south between Noosa National Park and the beach, past the villages of Castaways, Marcus, Peregian and Coolum.',
      'Past Mt Coolum and Marcoola, loop through Twin Waters and back up Mudjimba Esplanade beside the beach, then ride the coast road home with Peregian Beach village just off the road for a coffee.'],
     ['David Low Way', 'Mt Coolum', 'Mudjimba Esplanade', 'Peregian Beach coffee'],
     [('71 km', 'Distance'), ('530 m', 'Climbing'), ('3.5 to 4.5 hrs', 'Experience time'), ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     'Experience time includes a coffee stop at Peregian Beach. The route stays on the road the whole way.',
     [HIRE + 'BikeOnHire-046.jpg', HIRE + 'BikeOnHire-011.jpg', K + 'SummitToSeaEbike-157.jpg'],
     [L('Mudjimba', -26.61861, 153.0925, 1), L('Mt Coolum', -26.565, 153.0889, 1), L('Twin Waters', -26.63, 153.08361, 3)], nauto=8, peak=None, extra=('BCH',))

shop('57344787', 'pomona-loop', 'Pomona Loop', 'Road from the shop', 'road',
     'The big one: Pomona under Mt Cooroora, then over to Kin Kin',
     ['The big one: an 80 km hinterland road loop from the shop. Climb Garmin Hill, ride on through Tinbeerwah and Lake Macdonald to Cooroy, then north beside the railway and state forest to Pomona at the foot of Mt Cooroora.',
      'The Pomona Kin Kin Road climbs over the range at Pinbarren, the high point of the loop, and drops into Kin Kin. Quiet roads through Cootharaba and Cooroibah bring you back to Tewantin. Long gaps between towns, so start early.'],
     ['Pomona and Mt Cooroora', 'Over the range at Pinbarren', 'Kin Kin village', 'Cootharaba farmland'],
     [('80 km', 'Distance'), ('680 m', 'Climbing'), ('4 to 5 hrs', 'Experience time'), ('Moderate', 'Level'), ('Sealed', 'Surface'), ('Road bike', 'Premium BMC')],
     'Experience time includes stops in Cooroy, Pomona and Kin Kin.',
     [K + 'HinterlandGravel-061.jpg', K + 'HinterlandGravel-059.jpg', K + 'HinterlandGravel-V012.jpg'],
     [GH('57344787'), L('Pomona', -26.3625, 152.85639, 1), L('Kin Kin', -26.26333, 152.87333, 1)], nauto=7, peak='Pinbarren')


# ---------------- Hinterland, By Earth and Ocean ----------------
NAMED = {'Woondum National Park': (-26.28889, 152.81083), 'Pomona': (-26.3625, 152.85639), 'Kin Kin': (-26.26333, 152.87333),
         'Cooran': (-26.33528, 152.82306), 'Mt Cooroora': (-26.37139, 152.83806), 'Mt Tinbeerwah': (-26.39028, 152.97528),
         'Lake Weyba': (-26.445, 153.068), 'Lake Cootharaba': (-26.2667, 153.0167)}
FIN = L('Finish: the shop, Noosaville', *SHOP, pri=0, kind='finish', down=True)


def hint(rid, kind, title, sub, paras, hl, level, time, surface, photos, labels=(), nauto=9, peak=None, skip=()):
    r = R[rid]
    start = (r['pts'][0][0], r['pts'][0][1])
    sname = 'Start: Pomona' if start[0] < -26.36 else 'Start: James McKane Lookout'
    lab = [L(sname, *start, pri=0, kind='start'), FIN] + list(labels)
    text = ' '.join(paras + hl + [sub])
    for n, (y, x) in NAMED.items():
        if n in text and not any(n.lower() in l['n'].lower() for l in lab):
            lab.append(L(n, y, x, pri=1.5, fit=False))
    lab += auto(rid, lab, nauto, skip=skip)
    km = round(r['dist'] / 1000)
    climb = round(r['gain'] / 10) * 10
    gravel = kind == 'gravel'
    RIDES[rid] = dict(slug=re.sub(r'[^a-z0-9]+', '-', (title + (' gravel' if gravel else ' mtb')).lower()).strip('-'),
                      title=title, kick=('Hinterland gravel' if gravel else 'Hinterland mountain bike') + ' &middot; point to point',
                      qr=QR['hgravel' if gravel else 'hmtb'], sub=sub, paras=paras, hl=hl,
                      stats=[(f'{km} km', 'Distance'), (f'{climb:,} m', 'Climbing'), (time, 'Experience time'), (level, 'Level'), (surface, 'Surface'),
                             ('Gravel bike' if gravel else 'Mountain bike', 'Bring or hire')],
                      note='Experience time is an estimate, including the drive to the start and stops. Hire bikes back by 4pm.',
                      photos=photos, labels=lab, ex=2.0, style='beo', color=GOLD, peak=peak, brand='beo')


# Mothar Mountain rock pools, Boulder Creek and Woondum Creek junction (aussiebushwalking.com); both Rockpools routes pass within 70 m
ROCKPOOLS = L('Mothar Mountain rock pools', -26.262034, 152.796458, 1)
HG = lambda n: K + f'HinterlandGravel-{n}.jpg'
BT = lambda n: K + f'BiosphereTrailsEMTB-{n}.jpg'

hint('55105098', 'gravel', 'Pomona to Noosa', 'Country town to coast on smooth gravel and quiet roads',
     ['We drop you in Pomona, under Mt Cooroora, and you ride home to the shop. A gentle point to point that descends gradually from the hinterland on quiet sealed roads, smooth gravel, forest sections and parts of the Noosa Trail Network.',
      'The landscape changes all the way: country town, forest lined gravel, then the waterways and coastal feel of Noosa and the Lake Doonella wetlands. Lower gravel sections can turn soft or muddy after rain.'],
     ['Pomona and Mt Cooroora', 'Noosa Trail Network', 'Forest lined gravel', 'Lake Doonella wetlands'],
     'Relaxed', '3 to 4 hrs', 'Gravel & road', [HG('038'), HG('V012'), HG('059')])

hint('55105149', 'gravel', 'Treetops to Tewantin', 'Forest gravel and country lanes from the high country to the river',
     ['Start high in the hinterland at James McKane Lookout near Cooran and link flowing gravel roads, forest access tracks and quiet country lanes as you descend steadily toward Noosa.',
      'Farmland, bushland, rolling hills and rainforest lined gravel give big views and a real sense of journey. One of the most enjoyable and accessible gravel rides under 50 km in the region.'],
     ['James McKane Lookout', 'Rainforest lined gravel', 'Rolling hills and farmland', 'A steady descent to Tewantin'],
     'Relaxed', '4 to 5 hrs', 'Gravel & road', [HG('040'), HG('017'), HG('051')])

hint('54657933', 'gravel', 'The Cooroora Traverse', 'The Cooroora Trail, big hinterland views and rewarding descents',
     ['From the high country near Cooran, quiet gravel roads and sections of the Cooroora Trail carry you through farmland, forest and open countryside before the long run down toward Noosa.',
      'Mostly off road on the Noosa Trail Network: smooth gravel, forest trails and some rougher sections with roots and rocks. A shorter scenic ride with a step up in terrain, and wet weather makes it much harder.'],
     ['The Cooroora Trail', 'Views across the ranges', 'Rewarding descents', 'Noosa Trail Network'],
     'Moderate', '4 to 5 hrs', 'Mostly trail', [HG('036'), HG('052'), HG('041')])

hint('54989491', 'gravel', 'Mary Valley Bound', 'Open Mary Valley country and new angles on Mt Cooroora',
     ['Begin in the forests around Woondum National Park and descend gradually on quiet hinterland roads toward Cooran and Pomona, then out into the wide open landscapes of the Mary Valley.',
      'Smooth gravel, quiet sealed backroads, farmland, creek crossings and ever changing views of Mt Cooroora, before the cooler forest of Ringtail and Yurol carries you back toward Noosa.'],
     ['Woondum National Park', 'Mary Valley farmland', 'Mt Cooroora views', 'Ringtail and Yurol forests'],
     'Relaxed', '4.5 to 5.5 hrs', 'Gravel & road', [HG('042'), HG('039'), HG('038')])

hint('55104485', 'gravel', 'Magic Mary', 'A full day of Mary Valley gravel, with lunch in Pomona',
     ['A longer hinterland gravel ride for a complete day on the bike: forest sections, quiet sealed backroads, smooth gravel, open farmland and rolling hills across the broader Mary Valley and Noosa Hinterland.',
      'Shaded forest corridors give way to open rural valleys and peaceful country roads, with new views of Mt Cooroora. Pomona makes a natural lunch stop. The challenge is the distance, not the terrain.'],
     ['Mary Valley country', 'Lunch in Pomona', 'Mt Cooroora views', 'Shaded forest corridors'],
     'Relaxed', '6 to 7 hrs', 'Gravel & road', [HG('041'), HG('057'), HG('049')])

hint('55360460', 'gravel', 'Forests, Farms & Foreshore', 'Rainforest to Lake Weyba: the whole region in one big day',
     ['A true adventure that packs the whole region into one ride: subtropical forest and remote management tracks, rolling farmland and wide valleys, then the shores of Lake Weyba and the Noosa foreshore.',
      'This is not a gentle gravel cruise. Big climbs, rough management tracks and a long day. Some sections turn very soft, rutted or impassable after rain, so dry conditions are strongly recommended.'],
     ['Towering eucalypt forest', 'Views of the hinterland peaks', 'Lake Weyba shores', 'Noosa foreshore'],
     'Challenging', '6 to 7 hrs', 'Rough gravel', [HG('039'), HG('022'), HG('051')],
     labels=[L('Lake Weyba', -26.445, 153.068, 1)])

hint('54989036', 'gravel', 'Valleys & Vistas', 'A full day of remote gravel, ridgelines and long views',
     ['Around the landscapes of Woondum National Park, this 100 km route links remote gravel roads, rolling climbs and scenic descents through forest, farmland and open ridgelines before returning toward Noosa.',
      'Mostly sealed roads and good gravel with occasional rough patches. It is challenging for the distance and climbing more than the surface, and more approachable than the region\'s expedition style routes.'],
     ['Woondum National Park', 'Open ridgelines', 'Remote backroads', 'Big hinterland views'],
     'Moderate', '6 to 7 hrs', 'Gravel & road', [HG('V001'), HG('042'), HG('010')])

hint('55105004', 'gravel', 'Through Lake Country', 'Woondum forests east to Boreen Point and Lake Cootharaba',
     ['Our longest gravel ride. Cross the forests around Woondum National Park, then head east to Boreen Point and the shores of Lake Cootharaba before the route turns for Noosa.',
      'Gravel roads, rolling climbs, remote forest and open lake country make it one of the most varied rides in the region. Challenging for the distance and climbing, on mostly good gravel and quiet roads.'],
     ['Woondum forests', 'Boreen Point', 'Lake Cootharaba', 'Open lake country'],
     'Moderate', 'About 7 hrs', 'Gravel & road', [HG('046'), HG('017'), HG('021')],
     labels=[L('Boreen Point', -26.28444, 152.99333, 1), L('Lake Cootharaba', -26.2667, 153.0167, 1)])

hint('54987451', 'gravel', 'Rockpools & Ridgelines', 'Remote, rugged and steep: the wildest gravel in the hinterland',
     ['Through the rugged country around Woondum National Park, Beenham Valley and Ringtail Forest, this 100 km ride takes remote gravel roads, steep climbs and isolated forest tracks back toward Noosa.',
      'Expect long climbs, technical descents and changing terrain between forest, ridgelines and valleys. Experienced riders only, and not in or just after wet weather. A hardtail or flat bar gravel bike suits it best.'],
     ['Woondum National Park', 'Beenham Valley', 'Ringtail Forest', 'Remote ridgelines'],
     'Challenging', '6.5 to 7 hrs', 'Rough gravel', [HG('V002'), HG('049'), HG('050')],
     labels=[ROCKPOOLS], skip=('Mt Boulder',))

# mountain bike
hint('54672630', 'mtb', 'Peak to Peak', 'Mt Cooroora to Mt Tinbeerwah on forest tracks and gravel',
     ['One of the most achievable rides in our collection, linking two Noosa icons, Mt Cooroora and Mt Tinbeerwah. Gravel roads, management tracks and forest trails wind through dense forest and quiet countryside.',
      'Less climbing and gentler gradients than our other hinterland routes, with smoother surfaces and regular views of the volcanic peaks. A great introduction to point to point riding on the Noosa Trail Network.'],
     ['Mt Cooroora', 'Mt Tinbeerwah', 'Forest trails', 'Volcanic peak views'],
     'Intermediate', '3 to 4 hrs', 'Trail & gravel', [BT('020'), BT('038'), BT('V067')])

hint('55408442', 'mtb', 'Country Towns & Canopies', 'A big opening descent, then Cooran, Pomona and the forest',
     ['Builds on Peak to Peak with a longer journey. Start high in the hinterland and use all that height for some fantastic descending on the way to Noosa, through the country towns of Cooran and Pomona.',
      'Gravel roads, management tracks and forest trails through dense forest, open farmland and quiet rural country. The opening descent is a highlight, and there is an easier alternative if you prefer.'],
     ['The opening descent', 'Cooran and Pomona', 'Volcanic peak views', 'Forest canopy trails'],
     'Intermediate', '4 to 5 hrs', 'Trail & gravel', [BT('010'), BT('186'), BT('V062')])

hint('55404690', 'mtb', 'Everglades Vistas', 'Kin Kin ridgelines with views over the Noosa Everglades',
     ['Deep into the Kin Kin hinterland, through some of the most spectacular and lesser known country in the Noosa Biosphere: dense forest, rolling farmland and remote ridgelines.',
      'Viewpoints look out over the wilderness of the Noosa Everglades, and several long descents balance the climbing. Not highly technical, but the distance, climbing and remote country suit fitter, experienced riders.'],
     ['Noosa Everglades views', 'Kin Kin hinterland', 'Remote ridgelines', 'Long descents'],
     'Advanced', '5 to 6 hrs', 'Trail & gravel', [BT('023'), BT('V066'), BT('212')])

hint('54660724', 'mtb', 'Forest, Farms & Noosa', 'Woondum ridgelines and two of the network\'s best descents',
     ['Deeper into the Noosa Hinterland and the rugged country around Woondum National Park. Gravel roads, management tracks and forest trails cross dense forest, rolling farmland and remote ridgelines.',
      'Two of the network\'s most exciting descents, longer and steeper, need confidence on natural surfaces and good speed control. Some of the widest views on the network, across valleys and volcanic peaks.'],
     ['Woondum National Park', 'Two big descents', 'Ridgeline views', 'Rolling farmland'],
     'Advanced', '5 to 6 hrs', 'Trail & gravel', [BT('019'), BT('V057'), BT('030')])

hint('55404891', 'mtb', 'Rockpools & Ridgelines', 'Woondum descents, the Mothar Mountain rock pools and Kin Kin ridgelines',
     ['One of the most challenging and rewarding rides in our collection. A dramatic descent through the forests of Woondum National Park takes you down to the Mothar Mountain rock pools.',
      'Then climb back over the range, cross the farmland around Kin Kin and a run of ridgelines with views across the Noosa Biosphere. Big climbs and big descents for experienced, fit riders.'],
     ['Mothar Mountain rock pools', 'The Woondum descent', 'Kin Kin farmland', 'Ridgeline panoramas'],
     'Advanced', '6 to 7 hrs', 'Trail & gravel', [BT('022'), BT('V069'), BT('V056')],
     labels=[ROCKPOOLS], skip=('Mt Boulder',))

ORDER_SHOP = ['52202908', '52186029', '52219299', '52201147', '52416633', '52417417', '57376755', '57358075',
              '55391957', '55391935', '57344785', '57344784', '57347327', '57344787']
ORDER_HINT = ['55105098', '55105149', '54657933', '54989491', '55104485', '55360460', '54989036', '55105004', '54987451',
              '54672630', '55408442', '55404690', '54660724', '55404891']

if __name__ == '__main__':
    for k in ORDER_SHOP + ORDER_HINT:
        r = RIDES[k]
        print(k, r['slug'], '|', ', '.join(l['n'] for l in r['labels']))
