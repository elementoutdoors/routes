"""Small photo previews for the Ride Desk cards (the page cannot load pictures from other websites).

For each ride sheet's current photo (ride-sheets/photos.json on the Ride Guide site), a 160 x 120 JPEG as a data address,
kept in the page's published/thumbs record. A photo is fetched again only when its address changes. Uploaded photos need
no preview here: the page shows them from its own store.

Usage: python3 scripts/ride_desk_thumbs.py <db dir> <out dir>
  <db dir>/published/thumbs.json   the record as it is now (from an ArtifactData list with out_dir), if any
  writes <out dir>/published/thumbs.json only when something changed, and prints what it did.
Needs Pillow (pip install pillow).
"""
import base64, io, json, os, sys, time, urllib.request

SITE = os.environ.get('SITE_BASE', 'https://elementoutdoors.github.io/routes/').rstrip('/') + '/'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0 Safari/537.36 elementoutdoors-ride-desk/1.0'


def get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
        return r.read()


def thumb(data):
    from PIL import Image
    im = Image.open(io.BytesIO(data)); im.load(); im = im.convert('RGB')
    w, h = im.size; want = 4 / 3
    if w / h > want:
        nw = int(h * want); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / want); im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((160, 120), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, 'JPEG', quality=55, optimize=True, progressive=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def main(db_dir, out_dir):
    try:
        old = json.load(open(os.path.join(db_dir, 'published', 'thumbs.json'))).get('rides', {})
    except Exception:
        old = {}
    photos = json.loads(get(SITE + 'ride-sheets/photos.json?t=%d' % time.time())).get('rides', {})
    rides, fetched, failed = {}, [], []
    for slug, p in sorted(photos.items()):
        src, url = p.get('source') or 'placeholder', p.get('url')
        o = old.get(slug) or {}
        if not url:
            rides[slug] = {'source': src, 'src': None, 'img': None}
        elif o.get('src') == url and o.get('img'):
            rides[slug] = dict(o, source=src)
        else:
            try:
                rides[slug] = {'source': src, 'src': url, 'img': thumb(get(url))}; fetched.append(slug)
            except Exception as e:
                failed.append(f'{slug}: {e}')
                rides[slug] = o if o.get('img') else {'source': src, 'src': url, 'img': None}
    changed = json.dumps(rides, sort_keys=True) != json.dumps(old, sort_keys=True)
    if changed:
        os.makedirs(os.path.join(out_dir, 'published'), exist_ok=True)
        out = {'rides': rides, 'updatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        json.dump(out, open(os.path.join(out_dir, 'published', 'thumbs.json'), 'w'))
    print(json.dumps({'write': ['published/thumbs'] if changed else [], 'fetched': fetched, 'failed': failed,
                      'bytes': len(json.dumps(rides))}))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
