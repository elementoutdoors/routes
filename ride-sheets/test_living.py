"""Checks for the ride sheets' living document rules (living.py). No network or browser needed.
Usage: python3 ride-sheets/test_living.py"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import living as B


def line(n=400, lat0=-26.40, lng0=153.0, step_m=50):
    """a wiggly test line about n * step_m long"""
    out = []
    for i in range(n):
        d = i * step_m
        out.append([lng0 + d / (111320 * math.cos(math.radians(lat0))), lat0 + 0.002 * math.sin(i / 15)])
    return out


def shift(coords, metres_north, frm=0, to=None):
    to = len(coords) if to is None else to
    return [[c[0], c[1] + (metres_north / 110540 if frm <= i < to else 0)] for i, c in enumerate(coords)]


def entry(coords):
    return {'version': B.MAP_VERSION, 'line': B.encode_line(B.simplify(coords)), 'length_m': round(B.length_m(coords))}


def test_polyline_round_trip():
    c = B.simplify(line())
    back = B.decode_line(B.encode_line(c))
    assert len(back) == len(c) and all(abs(a[0] - b[0]) < 2e-5 and abs(a[1] - b[1]) < 2e-5 for a, b in zip(c, back))


def test_simplify_keeps_shape():
    c = line()
    s = B.simplify(c)
    assert len(s) < len(c)
    assert B.furthest_from(c, s, 100) <= B.LINE_KEEP_M + 1


def test_same_line_keeps_map():
    c = line()
    assert B.map_change(entry(c), c, True) == (False, '')


def test_minor_change_keeps_map():
    c = line()
    small = shift(c, 30, 100, 140)            # a stretch nudged 30 m: a cue or turn point tidied
    redraw, why = B.map_change(entry(c), small, True)
    assert not redraw, why


def test_detour_redraws_map():
    c = line()
    big = shift(c, 400, 150, 190)             # a stretch moved 400 m: a new way through
    redraw, why = B.map_change(entry(c), big, True)
    assert redraw and ('moved' in why or 'length' in why), why


def test_length_change_redraws_map():
    c = line()
    longer = c + [[c[-1][0] + k * 0.0006, c[-1][1]] for k in range(1, 30)]   # about 1.8 km more
    redraw, why = B.map_change(entry(c), longer, True)
    assert redraw and 'length' in why, why


def test_missing_file_or_new_style_redraws():
    c = line()
    assert B.map_change(entry(c), c, False)[0]
    old = dict(entry(c), version=B.MAP_VERSION - 1)
    assert B.map_change(old, c, True)[0]
    assert B.map_change(None, c, True)[0]


def test_story_and_house_style():
    import textfit as T
    s = T.story('Ringtail Loop\n\nA hinterland gravel loop on e-bikes. Climb hard—then descend.\n\n' + 'More words here. ' * 60, ['Ringtail Loop'])
    assert s[0].startswith('A hinterland') and 'e-Bikes' in s[0] and '—' not in s[0], s
    assert sum(len(p) for p in s) <= 640 and len(s) <= 2
    assert T.story('', ['X']) == []
    assert T.house_style('Ride time on the Wondum trail') == 'riding time on the Woondum trail'


def test_matching():
    pages = {'the-full-noosa-ride': {'title': 'The Full Noosa Ride'}, 'wooroi-wetlands': {'title': 'Wooroi &#038; Wetlands MTB Ride'},
             'pirate-park-kids-ride': {'title': 'Pirate Park Kids Ride'}, 'ringtail-loop': {'title': 'Ringtail Loop'}}
    r = lambda slug, name: {'slug': slug, 'name': name, 'full_name': name}
    assert B.match_page(r('full-noosa', 'Full Noosa Self-Guided Tour'), pages, {}) == 'the-full-noosa-ride'
    assert B.match_page(r('wooroi-and-wetlands', 'Wooroi & Wetlands'), pages, {}) == 'wooroi-wetlands'
    assert B.match_page(r('ringtail-loop', 'Ringtail Loop'), pages, {}) == 'ringtail-loop'
    assert B.match_page(r('kids-and-family', 'Kids & Family Self-Guided Tour'), pages, {}) is None
    assert B.match_page(r('kids-and-family', 'Kids & Family Self-Guided Tour'), pages, {'kids-and-family': 'pirate-park-kids-ride'}) == 'pirate-park-kids-ride'
    assert B.match_page(r('peak-to-peak', 'Peak to Peak (Intermediate)'), pages, {}) is None


def test_photo_choice_order():
    ride = {'slug': 'ringtail-loop', 'name': 'Ringtail Loop', 'full_name': 'Ringtail Loop', 'hero': 'https://example.com/h.jpg'}
    pages = {'ringtail-loop': {'title': 'Ringtail Loop', 'image': 'https://example.com/w.jpg', 'link': 'https://example.com/p'}}
    assert B.photo_choice(ride, {'photos': {'ringtail-loop': 'site/x.jpg'}}, pages)[0] == 'override'
    assert B.photo_choice(ride, {}, pages)[:2] == ('website', 'https://example.com/w.jpg')
    assert B.photo_choice(ride, {}, {})[0] == 'ridewithgps'
    assert B.photo_choice(dict(ride, hero=None), {}, {})[0] == 'placeholder'


if __name__ == '__main__':
    n = 0
    for k, f in list(globals().items()):
        if k.startswith('test_'):
            f(); n += 1; print('ok', k)
    print(f'{n} checks passed')
