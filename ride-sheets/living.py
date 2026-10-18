"""The living document rules for the ride sheets and booklet, and the photo lookup (see build.py).
Standard library only, so the hourly build can decide whether anything changed without installing anything."""
import hashlib, html, io, json, math, os, re, subprocess, tempfile, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP_VERSION = 1            # bump when the map look changes: every map is drawn again once
RULES = {
    'map_length_change_pct': 2.0,     # map redrawn when the route length changes by more than this
    'map_moved_m': 100,               # ... or any point of the new line is further than this from the old line
    'details_logged_km': 0.5,         # changelog entry when distance changes by this much
    'details_logged_gain_m': 25,      # ... or climbing by this much
}
LINE_KEEP_M = 12                      # tolerance of the simplified copy of the line kept in the manifest
WEBSITE_API = 'https://bikeon.com.au/wp-json/wp/v2/bike_rides?per_page=100&_embed=wp:featuredmedia'
UA = 'Element Outdoors ride sheets (+https://elementoutdoors.github.io/routes/)'


# ---------- geometry ----------
def hav(a, b):
    """metres between two [lng, lat] points"""
    p1, p2 = math.radians(a[1]), math.radians(b[1])
    x = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(b[0] - a[0]) / 2) ** 2
    return 2 * 6371000 * math.asin(min(1, math.sqrt(x)))


def length_m(coords):
    return sum(hav(coords[i - 1], coords[i]) for i in range(1, len(coords)))


class Flat:
    """local flat projection in metres around a latitude (accurate to well under a metre over a ride)"""
    def __init__(self, lat0):
        self.kx, self.ky = 111320 * math.cos(math.radians(lat0)), 110540

    def xy(self, c):
        return (c[0] * self.kx, c[1] * self.ky)


def simplify(coords, tol=LINE_KEEP_M):
    """Douglas-Peucker in metres; keeps the first and last point"""
    if len(coords) < 3: return [list(c) for c in coords]
    f = Flat(sum(c[1] for c in coords) / len(coords)); P = [f.xy(c) for c in coords]
    keep = [False] * len(P); keep[0] = keep[-1] = True
    stack = [(0, len(P) - 1)]
    while stack:
        a, b = stack.pop()
        best, bi = -1, -1
        for i in range(a + 1, b):
            d = seg_dist(P[i], P[a], P[b])
            if d > best: best, bi = d, i
        if best > tol:
            keep[bi] = True; stack += [(a, bi), (bi, b)]
    return [[round(coords[i][0], 5), round(coords[i][1], 5)] for i in range(len(P)) if keep[i]]


def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0 if l2 == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def densify(coords, step=25):
    out = [coords[0]]
    for i in range(1, len(coords)):
        a, b = coords[i - 1], coords[i]
        n = int(hav(a, b) // step)
        for k in range(1, n + 1):
            out.append([a[0] + (b[0] - a[0]) * k / (n + 1), a[1] + (b[1] - a[1]) * k / (n + 1)])
        out.append(b)
    return out


def furthest_from(new, old, limit):
    """Largest distance in metres from any point of the new line to the old line. Stops counting at limit * 3
    (enough to say it moved). Uses a grid of the old line's segments so a long ride takes a moment, not minutes."""
    if not old or not new: return float('inf')
    f = Flat(sum(c[1] for c in old) / len(old))
    O = [f.xy(c) for c in old]
    cell = max(limit, 50) * 2
    grid = {}
    for i in range(len(O) - 1 if len(O) > 1 else 1):
        a, b = O[i], O[min(i + 1, len(O) - 1)]
        for gx in range(int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell) + 1):
            for gy in range(int(min(a[1], b[1]) // cell), int(max(a[1], b[1]) // cell) + 1):
                grid.setdefault((gx, gy), []).append(i)
    worst = 0.0
    for c in densify(new):
        p = f.xy(c); gx, gy = int(p[0] // cell), int(p[1] // cell)
        best = float('inf')
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in grid.get((gx + dx, gy + dy), ()):
                    best = min(best, seg_dist(p, O[i], O[min(i + 1, len(O) - 1)]))
        if best == float('inf'):   # nothing within a cell: measure it properly (rare)
            best = min(seg_dist(p, O[i], O[min(i + 1, len(O) - 1)]) for i in range(max(1, len(O) - 1)))
        worst = max(worst, best)
        if worst > limit * 3: break
    return worst


def map_change(prev, coords, has_file):
    """(redraw?, why) for a ride's map, following the living document rule"""
    if not prev or not prev.get('line') or not has_file: return True, 'first map'
    if prev.get('version') != MAP_VERSION: return True, 'map look updated'
    old = decode_line(prev['line'])
    was, now = prev.get('length_m') or length_m(old), length_m(coords)
    pct = abs(now - was) / was * 100 if was else 100
    if pct > RULES['map_length_change_pct']:
        return True, f'route length changed from {was / 1000:.1f} to {now / 1000:.1f} km'
    moved = furthest_from(coords, old, RULES['map_moved_m'])
    if moved > RULES['map_moved_m']:
        return True, f'route line moved by more than {RULES["map_moved_m"]} m (up to {min(moved, RULES["map_moved_m"] * 3):.0f} m)'
    return False, ''


# Google encoded polyline (precision 5, about 1 m): a compact copy of the line in the manifest
def encode_line(coords):
    out, plat, plng = [], 0, 0
    for lng, lat in coords:
        ilat, ilng = round(lat * 1e5), round(lng * 1e5)
        for v in (ilat - plat, ilng - plng):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plng = ilat, ilng
    return ''.join(out)


def decode_line(s):
    coords, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = res = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                res |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            vals.append(~(res >> 1) if res & 1 else res >> 1)
        lat += vals[0]; lng += vals[1]
        coords.append([lng / 1e5, lat / 1e5])
    return coords


def norm_title(s):
    s = html.unescape(s or '').lower().replace('&', ' and ')
    s = re.sub(r'\(.*?\)', ' ', s)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    drop = {'the', 'self', 'guided', 'tour', 'ride', 'mtb', 'from', 'shop', 'e', 'bike', 'ebike'}
    return ' '.join(w for w in s.split() if w not in drop)


# ---------- photos ----------
def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def website_pages():
    """{wp slug: {title, link, image, text}} from the Bike On website ride pages, or None if it could not be read"""
    try:
        items = json.loads(fetch(WEBSITE_API))
    except Exception as e:
        print('booklet: could not read the Bike On website ride pages:', e)
        return None
    pages = {}
    for it in items:
        img = None
        fm = ((it.get('_embedded') or {}).get('wp:featuredmedia') or [{}])[0] or {}
        if fm.get('source_url'):
            img = fm['source_url']
            sizes = (fm.get('media_details') or {}).get('sizes') or {}
            fit = sorted((v for v in sizes.values() if v.get('width', 0) >= 1400 and v.get('source_url')), key=lambda v: v['width'])
            if fit: img = fit[0]['source_url']
        y = it.get('yoast_head_json') or {}
        if not img and y.get('og_image'): img = (y['og_image'][0] or {}).get('url')
        pages[it['slug']] = {'title': html.unescape((it.get('title') or {}).get('rendered', '')), 'link': it.get('link'),
                             'image': img, 'text': y.get('og_description') or y.get('description') or ''}
    return pages


def match_page(ride, pages, cfg_pages):
    """the website ride page for a ride: the Ride Desk card's websitePage, then the same slug, then the same name"""
    if not pages: return None
    want = cfg_pages.get(ride['slug'])
    if want: return want if want in pages else None
    if ride['slug'] in pages: return ride['slug']
    n = norm_title(ride['full_name'] or ride['name'])
    hits = [k for k, p in pages.items() if norm_title(p['title']) == n]
    return hits[0] if len(hits) == 1 else None


def photo_choice(ride, cfg, pages):
    """(source, ref, page) for a ride's photo; ref is a URL or a repo path"""
    over = (cfg.get('photos') or {}).get(ride['slug'])
    if over: return ('override', over, None)
    k = match_page(ride, pages, cfg.get('pages') or {})
    if k and pages[k].get('image'): return ('website', pages[k]['image'], pages[k]['link'])
    if ride.get('hero'): return ('ridewithgps', ride['hero'], None)
    return ('placeholder', None, None)


def save_photo(source, ref, dest):
    """download (or copy) and store as a JPEG no wider than 1800 px. Returns True when saved."""
    from PIL import Image
    data = open(os.path.join(ROOT, ref), 'rb').read() if source == 'override' and not re.match(r'https?://', ref) else fetch(ref, 90)
    im = Image.open(io.BytesIO(data)); im.load()
    im = im.convert('RGB')
    if im.width > 1800: im = im.resize((1800, round(im.height * 1800 / im.width)), Image.LANCZOS)
    tmp = dest + '.tmp'
    im.save(tmp, 'JPEG', quality=84, optimize=True, progressive=True)
    os.replace(tmp, dest)
    return True


def sha_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16] if p and os.path.exists(p) else None


def sha_text(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def write_json(p, obj):
    tmp = p + '.tmp'
    with open(tmp, 'w') as f: json.dump(obj, f, indent=1, ensure_ascii=False)
    os.replace(tmp, p)


def seal(pdf, meta, out):
    """lock the PDF with EO Crew's public key, in the same envelope as staff.enc.json (scripts/staff_bundle.mjs)"""
    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, 'meta.json'); json.dump(meta, open(mp, 'w'))
        tmp = out + '.tmp'
        subprocess.run(['node', os.path.join(ROOT, 'scripts', 'staff_bundle.mjs'), 'booklet', pdf, mp, tmp], check=True)
        env = json.load(open(tmp))
        assert env.get('v') == 1 and env.get('key') and env.get('data') and 'b64' not in env, 'locked file looks wrong'
        os.replace(tmp, out)




def seal_json(obj, out):
    """lock a small JSON document (the index) with EO Crew's public key, in the same envelope as staff.enc.json"""
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'in.json'); json.dump(obj, open(src, 'w'), separators=(',', ':'))
        tmp = out + '.tmp'
        subprocess.run(['node', os.path.join(ROOT, 'scripts', 'staff_bundle.mjs'), 'json', src, tmp], check=True)
        env = json.load(open(tmp))
        assert env.get('v') == 1 and env.get('key') and env.get('data'), 'locked file looks wrong'
        os.replace(tmp, out)


def seal_v2(pdf, meta, out_enc, out_key):
    """Lock a big PDF in envelope v2 (scripts/staff_bundle.mjs): raw AES-256-GCM ciphertext plus a small key file. The
    node step proves the round trip with a throwaway key pair before it writes anything."""
    with tempfile.TemporaryDirectory() as td:
        mp = os.path.join(td, 'meta.json'); json.dump(meta, open(mp, 'w'))
        te, tk = out_enc + '.tmp', out_key + '.tmp'
        subprocess.run(['node', os.path.join(ROOT, 'scripts', 'staff_bundle.mjs'), 'v2', pdf, mp, te, tk], check=True)
        k = json.load(open(tk))
        assert k.get('v') == 2 and k.get('key') and k.get('iv') and k.get('bytes') == os.path.getsize(pdf), 'key file looks wrong'
        assert os.path.getsize(te) == os.path.getsize(pdf) + 16, 'ciphertext is the wrong size'
        assert k['sha256'] == hashlib.sha256(open(pdf, 'rb').read()).hexdigest(), 'sha256 differs'
        os.replace(te, out_enc); os.replace(tk, out_key)
