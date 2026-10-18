"""The living ride sheets and rides booklet, run by the site build after every Ride Guide build.

One A4 landscape sheet per live ride (both brands, from sheet.py) and the combined booklet (booklet.py), kept up to date
by themselves. Route codes and links are never public, so they are only published locked with EO Crew's public key:
dist/booklet.pdf.enc with dist/booklet.key.json (the whole booklet, for printing, envelope v2: raw ciphertext and a key file), dist/ride-sheets/<slug>.enc.json (one sheet each, a lighter copy
for the iPad) and dist/ride-sheets/index.enc.json (a small list for EO Crew: each ride's page, dates, sizes, holds).
Each sheet is checked first (check.py). A sheet with a blocking problem (QR code, route code, a flat elevation profile on
a ride that climbs) is held back: the ride keeps its previous sheet, kept encrypted in the cache, and the reason is logged.

Living rules (what each sheet was built from is kept in STATE/manifest.json, with a changelog):
  3D map       drawn again only when the route line changes a lot (length by more than 2 percent, or any part more than
               100 m from the line the map was drawn from), or the map's own settings in rides.py change. Cue, stop and
               story edits, or a line nudged a few metres, keep the map.
  ride story   always the ride's current description in the Ride Guide; a change is logged.
  numbers      always the latest distance, climbing and riding time; a change of 0.5 km or 25 m climbing is logged.
  photo        the ride's website photo, or the one picked on its Ride Desk card, fetched again only when it changes.
The sheets and booklet are made again whenever anything on a sheet changed.

python3 ride-sheets/build.py           build what changed and publish the locked files into dist/
python3 ride-sheets/build.py --plan    print none, sheets or maps (what this run needs installed), and stop
Options: --force (make every sheet again), --redraw-maps, --only <rid,...>, --map-budget SECONDS.
A failure never stops the site build: the last good locked files are kept and published.
"""
import argparse, datetime, glob, hashlib, json, os, re, shutil, subprocess, sys, time, traceback
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import ROOT, STATE, OUT, DIST
import living as L

TZ = ZoneInfo('Australia/Brisbane')
BOOKLET = 'Ride sheets booklet.pdf'
LOCKED = os.path.join(STATE, 'locked')
BOOKLET_ENC = os.path.join(LOCKED, 'booklet.pdf.enc')     # envelope v2: raw ciphertext of the booklet PDF
BOOKLET_KEY = os.path.join(LOCKED, 'booklet.key.json')    # envelope v2: the wrapped key, iv, size, sha256 and the rides
CODE_FILES = ['sheet.py', 'booklet.py', 'rides.py', 'desk.py', 'textfit.py', 'check.py', 'build.py']


def now():
    return datetime.datetime.now(TZ)


def jhash(obj):
    return L.sha_text(json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str))


class Build:
    def __init__(self, a):
        self.a = a
        import rides
        self.rides = rides
        self.R, self.RIDES = rides.R, rides.RIDES
        self.order = rides.ORDER_SHOP + rides.ORDER_HINT
        if a.only:
            self.order = [r for r in self.order if r in a.only.split(',')]
        self.today = now().strftime('%Y-%m-%d')
        self.mpath = os.path.join(STATE, 'manifest.json')
        try: self.m = json.load(open(self.mpath))
        except Exception: self.m = {}
        self.m.setdefault('rides', {}); self.m.setdefault('changelog', [])
        import desk
        try: self.photo_cfg = desk.photo_cfg(desk.cards())   # the photo on each Ride Desk card (website page by default)
        except Exception: self.photo_cfg = {}
        self.code_fp = jhash([open(os.path.join(HERE, f)).read() for f in CODE_FILES])
        self._pages = None

    # ---------- what each sheet is built from ----------
    def log(self, rid, what):
        self.m['changelog'].append({'date': self.today, 'ride': self.R[rid]['slug'] if rid in self.R else rid, 'what': what})
        print(f'ride sheets: {self.R[rid]["slug"] if rid in self.R else rid}: {what}', flush=True)

    def look(self, rid):
        c = self.RIDES[rid]
        return jhash([L.MAP_VERSION, c.get('curated_labels'), c['title'], c['kick'], c['sub'], c['color'], c['style'],
                      c.get('yaw'), c.get('pitch'), c.get('zoom'), c.get('ex')])

    def map_file(self, rid):
        return os.path.join(STATE, 'maps', self.RIDES[rid]['slug'], 'map.jpg')

    def map_jobs(self):
        jobs = []
        for rid in self.order:
            prev = self.m['rides'].get(rid, {}).get('map')
            redraw, why = L.map_change(prev, self.R[rid]['line'], os.path.exists(self.map_file(rid)))
            if not redraw and prev and prev.get('look') != self.look(rid):
                redraw, why = True, 'map settings or title changed in rides.py'
            if self.a.redraw_maps:
                redraw, why = True, 'maps redrawn by hand'
            if redraw:
                jobs.append((rid, why))
        return jobs

    def pages(self):
        if self._pages is None:
            self._pages = L.website_pages()
        return self._pages

    def photo_key(self, rid):
        r = self.R[rid]
        ride = dict(slug=r['slug'], name=r['name'], full_name=r['name'], hero=r.get('hero'))
        e = self.m['rides'].get(rid, {})
        if self.pages() is None and (e.get('photo') or {}).get('source') == 'website':
            p = e['photo']; return (p['source'], p['ref'], p.get('page'))
        return L.photo_choice(ride, self.photo_cfg, self.pages())

    def inputs(self, rid):
        c, r = self.RIDES[rid], self.R[rid]
        src, ref, _ = self.photo_key(rid)
        refkey = ref
        if src == 'override' and ref and not re.match(r'https?://', ref):
            refkey = f'{ref}#{L.sha_file(os.path.join(ROOT, ref))}'
        return dict(words=[c['title'], c['kick'], c['sub'], c['hl'], c['note'], c['stats']],
                    numbers=dict(distance_km=round(r['dist'] / 1000, 1), gain_m=r['gain'], riding_minutes=r['riding_minutes']),
                    story=L.sha_text(r['desc'] or ''), photo=f'{src}|{refkey}', code=L.sha_text(r['code'] + '|' + r['link']),
                    map=L.sha_file(self.map_file(rid)))

    def booklet_inputs(self, ins):
        return jhash([self.code_fp, self.order, [ins[r] for r in self.order]])

    def plan(self):
        if self.map_jobs():
            return 'maps'
        ins = {rid: self.inputs(rid) for rid in self.order}
        if self.a.force or self.booklet_inputs(ins) != self.m.get('booklet_inputs') or not os.path.exists(BOOKLET_KEY):
            return 'sheets'
        return 'none'

    # ---------- the run ----------
    def run(self):
        M = self.m['rides']
        live = set(self.order)
        if not self.a.only:
            for rid in [k for k in M if k not in live]:
                self.log(rid, 'taken out (no longer a live ride)'); del M[rid]
        for rid in self.order:
            e = M.setdefault(rid, {})
            if not e.get('added'):
                e['added'] = self.today
                self.log(rid, 'sheet added' + (' (made from the Ride Guide data alone: no words in rides.py yet)' if self.RIDES[rid].get('generic') else ''))
            e['slug'], e['sheet_slug'], e['title'] = self.R[rid]['slug'], self.RIDES[rid]['slug'], self.RIDES[rid]['title']
            e['generic'] = bool(self.RIDES[rid].get('generic'))
        self.maps()
        self.photos()
        self.story_fallbacks()
        ins = {}
        for rid in self.order:
            e, r = M[rid], self.R[rid]
            ins[rid] = i = self.inputs(rid)
            n, base = i['numbers'], e.get('numbers_logged')
            if base and (abs(n['distance_km'] - base['distance_km']) >= L.RULES['details_logged_km'] or abs(n['gain_m'] - base['gain_m']) >= L.RULES['details_logged_gain_m']):
                self.log(rid, f"numbers changed: distance {base['distance_km']} to {n['distance_km']} km, climbing {base['gain_m']} to {n['gain_m']} m")
                e['numbers_logged'] = n
            if not base: e['numbers_logged'] = n
            if e.get('numbers') and e['numbers'] != n: e['numbers_changed_at'] = self.today
            e.setdefault('numbers_changed_at', e.get('added'))
            e['numbers'] = n
            if e.get('story') and e['story'] != i['story']:
                self.log(rid, 'ride story updated' + (' from its Ride with GPS description' if e.get('story_from') == 'ride' else ' (website summary)' if e.get('story_from') == 'website' else ''))
            e['story'] = i['story']
            if e.get('code') and e['code'] != i['code']:
                self.log(rid, 'route code and QR code changed')
            e['code'] = i['code']
            fp = jhash(i)
            if e.get('inputs') != fp: e['updated'] = self.today
            e['inputs'] = fp
        bi = self.booklet_inputs(ins)
        changed = self.a.force or bi != self.m.get('booklet_inputs') or not os.path.exists(BOOKLET_KEY)
        self.m['placeholders'] = {'photo': [M[r]['slug'] for r in self.order if (M[r].get('photo') or {}).get('source') in (None, 'placeholder')],
                                  'map': [M[r]['slug'] for r in self.order if not os.path.exists(self.map_file(r))]}
        self.m['generic'] = [M[r]['slug'] for r in self.order if M[r]['generic']]
        if changed:
            ok = self.make()
            if ok:
                self.m['booklet_inputs'] = bi
        else:
            print('ride sheets: nothing changed, keeping the last booklet')
        self.m['changelog'] = self.m['changelog'][-1000:]
        self.m.update({'v': 1, 'rules': L.RULES, 'map_version': L.MAP_VERSION, 'checked': now().isoformat(timespec='seconds')})
        L.write_json(self.mpath, self.m)
        return changed

    def maps(self):
        jobs = self.map_jobs()
        if not jobs:
            return
        import mapgen
        t0 = time.time()
        M = self.m['rides']
        for rid, why in jobs:
            e = M[rid]
            if time.time() - t0 > self.a.map_budget:
                e['map_pending'] = 'waiting for the next run (time budget)'; continue
            out = os.path.dirname(self.map_file(rid))
            try:
                info = mapgen.build(rid, self.RIDES[rid], out, self.R)
                mapgen.render(out)
                e['map'] = {'version': L.MAP_VERSION, 'drawn': self.today, 'why': why, 'look': self.look(rid),
                            'length_m': round(L.length_m(self.R[rid]['line'])), 'line': L.encode_line(L.simplify(self.R[rid]['line'])),
                            'camera': {k: info[k] for k in ('yaw', 'pitch', 'EX')}}
                e.pop('map_pending', None)
                if why != 'first map':
                    self.log(rid, 'map redrawn: ' + why)
                print(f'ride sheets: map drawn for {e["slug"]} ({round(time.time() - t0)} s so far)', flush=True)
            except Exception as ex:
                traceback.print_exc()
                e['map_pending'] = f'map not drawn: {str(ex).splitlines()[0][:200] if str(ex) else type(ex).__name__}'
                for f in ('sat.jpg', 'scene.json', 'map.png'):
                    try: os.remove(os.path.join(out, f))
                    except OSError: pass

    def photos(self):
        M = self.m['rides']
        os.makedirs(os.path.join(STATE, 'photos'), exist_ok=True)
        for rid in self.order:
            e = M[rid]
            src, ref, page = self.photo_key(rid)
            jpg = os.path.join(STATE, 'photos', self.RIDES[rid]['slug'] + '.jpg')
            refkey = ref
            if src == 'override' and ref and not re.match(r'https?://', ref):
                refkey = f'{ref}#{L.sha_file(os.path.join(ROOT, ref))}'
            old = e.get('photo') or {}
            if src == 'placeholder':
                if old.get('source') != 'placeholder':
                    self.log(rid, 'no photo found: placeholder shown (pick one on its Ride Desk card)')
                e['photo'] = {'source': 'placeholder', 'ref': None, 'key': 'placeholder|None'}
                if os.path.exists(jpg): os.remove(jpg)
            elif old.get('key') != f'{src}|{refkey}' or not os.path.exists(jpg):
                try:
                    L.save_photo(src, ref, jpg)
                    e['photo'] = {'source': src, 'ref': ref, 'page': page, 'key': f'{src}|{refkey}', 'fetched': self.today}
                    self.log(rid, f'photo {"set" if not old else "changed"} ({src})')
                except Exception as ex:
                    print(f'ride sheets: {e["slug"]}: photo could not be fetched ({ex}); keeping the last one')
                    if not os.path.exists(jpg):
                        e['photo'] = {'source': 'placeholder', 'ref': None, 'failed': ref, 'key': 'placeholder|None'}

    def story_fallbacks(self):
        """A ride with no description in Ride with GPS uses the summary on its website ride page until it has one."""
        from textfit import story
        cfg_pages = self.photo_cfg.get('pages') or {}
        for rid in self.order:
            e, r = self.m['rides'][rid], self.R[rid]
            if story(r['desc'], [r['name']]):
                e['story_from'] = 'ride'; continue
            k = L.match_page(dict(slug=r['slug'], name=r['name'], full_name=r['name']), self.pages(), cfg_pages) if self.pages() else None
            text = (self.pages() or {}).get(k, {}).get('text') if k else ''
            if text:
                r['desc'] = text; e['story_from'] = 'website'
            else:
                e['story_from'] = 'none'
            if e.get('story_from_was') != e['story_from']:
                self.log(rid, 'no description in Ride with GPS: ' + ('the website summary is used until it has one' if text else 'the sheet has no ride story until it has one'))
            e['story_from_was'] = e['story_from']

    def make(self):
        """Make every sheet, check it, and lock what passed. A sheet with a blocking problem is held back: the ride keeps
        its previous sheet (kept encrypted in the cache) and the reason is logged and listed in the index."""
        import sheet, booklet, check
        M = self.m['rides']
        args = ['--ignore-certificate-errors']
        res = sheet.shoot(self.order, launch_args=args)
        probs = check.check(res)
        held, use = {}, {}
        for rid in self.order:
            e = M[rid]; slug = e['slug']
            for blocking, msg in probs.get(rid, []):
                print(f'ride sheets: CHECK {slug}: {"HOLD " if blocking else ""}{msg}', flush=True)
            block = [msg for blocking, msg in probs.get(rid, []) if blocking]
            e['notes'] = [msg for blocking, msg in probs.get(rid, []) if not blocking]
            if block:
                prev = vault_get(slug)
                if not e.get('held'):
                    self.log(rid, 'sheet held back: ' + '; '.join(block) + (' (the previous sheet stays)' if prev else ' (no previous sheet to keep)'))
                e['held'] = {'reason': '; '.join(block), 'since': (e.get('held') or {}).get('since') or self.today, 'previous_sheet': bool(prev)}
                held[slug] = e['held']
                if prev:
                    use[rid] = (prev[0], prev[1], False)
            else:
                if e.pop('held', None):
                    self.log(rid, 'sheet no longer held back')
                vault_put(slug, res[rid]['pdf'], res[rid]['pdf_screen'])
                use[rid] = (res[rid]['pdf'], res[rid]['pdf_screen'], True)
                e['story_printed'], e['fit'] = res[rid]['story'], res[rid]['check']
        self.m['held'] = held
        if not use:
            print('ride sheets: every sheet was held back, so the last good booklet is kept')
            return False
        pdf = os.path.join(OUT, BOOKLET)
        pages, page_of = booklet.make({rid: use[rid][0] for rid in self.order if rid in use}, pdf, launch_args=args)
        built = now().isoformat(timespec='seconds')
        os.makedirs(os.path.join(LOCKED, 'ride-sheets'), exist_ok=True)
        rows = []
        for rid in self.order:
            e = M[rid]; e['page'] = page_of.get(rid)
            locked = os.path.join(LOCKED, 'ride-sheets', e['slug'] + '.enc.json')
            if rid in use and (use[rid][2] or not os.path.exists(locked)):
                L.seal(use[rid][1], {'built': built, 'kind': 'ride-sheet', 'slug': e['slug'], 'title': e['title'],
                                     'file': sheet.fname(rid) + '.pdf', 'updated': e.get('updated')}, locked)
            rows.append({'slug': e['slug'], 'title': e['title'], 'brand': self.RIDES[rid]['brand'], 'kind': booklet.group_of(rid),
                         'page': page_of.get(rid), 'updated': e.get('updated'),
                         'sheet': f'ride-sheets/{e["slug"]}.enc.json' if os.path.exists(locked) else None,
                         'sheet_bytes': os.path.getsize(locked) if os.path.exists(locked) else 0,
                         'has_photo': (e.get('photo') or {}).get('source') not in (None, 'placeholder'),
                         'map_redrawn_at': (e.get('map') or {}).get('drawn'), 'details_changed_at': e.get('numbers_changed_at'),
                         'held': bool(e.get('held'))})
        live = {M[r]['slug'] for r in self.order}
        for f in glob.glob(os.path.join(LOCKED, 'ride-sheets', '*.enc.json')):
            if os.path.basename(f)[:-9] not in live and os.path.basename(f) != 'index.enc.json' and not self.a.only:
                os.remove(f)
        L.seal_v2(pdf, {'built_at': built, 'title': 'Bike On and By Earth and Ocean ride sheets', 'file': BOOKLET, 'pages': pages,
                        'rides': rows, 'photo_placeholders': self.m['placeholders']['photo'], 'maps_to_come': self.m['placeholders']['map'],
                        'held': held, 'changelog': self.m['changelog'][-200:]}, BOOKLET_ENC, BOOKLET_KEY)
        if os.path.exists(os.path.join(LOCKED, 'booklet.enc.json')):
            os.remove(os.path.join(LOCKED, 'booklet.enc.json'))   # the v1 booklet: replaced by the v2 files (18/10/2026)
        self.write_index(built, rows, held)
        self.m['built'], self.m['pages'] = built, pages
        print(f'ride sheets: made {len(use)} sheets ({len(held)} held back) and a {pages} page booklet, locked', flush=True)
        for r in rows:
            if rid_of := next((k for k in use if M[k]['slug'] == r['slug']), None):
                print(f"ride sheets: size {r['slug']}: screen PDF {os.path.getsize(use[rid_of][1]) / 1e6:.2f} MB, locked {r['sheet_bytes'] / 1e6:.2f} MB")
                if os.path.getsize(use[rid_of][1]) > 1_000_000:
                    print('ride sheets:   what fills it:', pdf_parts(use[rid_of][1]))
        print('ride sheets: booklet.pdf.enc %d bytes, booklet.key.json %d bytes' % (os.path.getsize(BOOKLET_ENC), os.path.getsize(BOOKLET_KEY)))
        print('ride sheets: sizes: booklet PDF %.1f MB, locked %.1f MB; screen sheets %.2f to %.2f MB, locked %.2f to %.2f MB' % (
            os.path.getsize(pdf) / 1e6, os.path.getsize(BOOKLET_ENC) / 1e6,
            min(os.path.getsize(use[r][1]) for r in use) / 1e6, max(os.path.getsize(use[r][1]) for r in use) / 1e6,
            min(x['sheet_bytes'] for x in rows if x['sheet_bytes']) / 1e6, max(x['sheet_bytes'] for x in rows) / 1e6), flush=True)
        return not held

    def write_index(self, built, rows, held):
        """ride-sheets/index.enc.json: a small locked list for EO Crew's sheet list and health checks."""
        commit = os.environ.get('GITHUB_SHA') or ''
        if not commit:
            try: commit = subprocess.run(['git', '-C', ROOT, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
            except Exception: commit = ''
        idx = {'v': 1, 'built_at': built, 'commit': commit, 'rides': rows,
               'photo_placeholders': self.m['placeholders']['photo'], 'maps_to_come': self.m['placeholders']['map'],
               'held': [dict(slug=k, **v) for k, v in held.items()], 'changelog': self.m['changelog'][-20:]}
        out = os.path.join(LOCKED, 'ride-sheets', 'index.enc.json')
        L.seal_json(idx, out)
        size = os.path.getsize(out)
        print(f'ride sheets: index.enc.json {size / 1024:.1f} KB', flush=True)
        if size > 50 * 1024:
            print('ride sheets: index is over 50 KB; trimming the changelog')
            idx['changelog'] = idx['changelog'][-5:]
            L.seal_json(idx, out)


def pdf_parts(path):
    """The biggest things inside a PDF (for the build log when a sheet is heavier than expected)."""
    try:
        from pypdf import PdfReader
        r = PdfReader(path); parts = []
        for page in r.pages:
            res = page['/Resources']
            for name, ref in (res.get('/XObject') or {}).items():
                o = ref.get_object()
                parts.append((len(o._data or b''), f"{name} {o.get('/Subtype')} {o.get('/Width')}x{o.get('/Height')} {o.get('/Filter')}"))
            for name, ref in (res.get('/Font') or {}).items():
                o = ref.get_object(); fd = None
                for d in (o.get('/DescendantFonts') or []):
                    fd = d.get_object().get('/FontDescriptor')
                ff = (fd.get_object() if fd else {}).get('/FontFile2') if fd else None
                parts.append((len(ff.get_object()._data) if ff else 0, f"{name} {o.get('/BaseFont')} {o.get('/Subtype')}"))
            parts.append((len(page.get_contents().get_data()) if page.get_contents() else 0, 'page content'))
        return '; '.join(f'{d} {b // 1024} KB' for b, d in sorted(parts, reverse=True)[:6])
    except Exception as ex:
        return f'could not read ({ex})'


# ---------- the last good sheets, kept encrypted in the cache so a held back sheet can keep its previous version ----------
def vault_key():
    salt = None
    try: salt = json.loads(os.environ.get('ROUTE_SECRETS') or 'null')['keySalt']
    except Exception: pass
    if not salt:
        try: salt = json.load(open(os.path.join(ROOT, '.secrets.json')))['keySalt']
        except Exception: pass
    if not salt and os.environ.get('RIDE_SHEETS_VAULT_KEY'):
        salt = os.environ['RIDE_SHEETS_VAULT_KEY']   # for trying it out without the route secrets
    if not salt:
        return None
    import hmac
    return hmac.new(salt.encode(), b'ride-sheets last good sheets v1', hashlib.sha256).digest()


def vault_put(slug, pdf, screen):
    key = vault_key()
    if not key:
        return
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    d = os.path.join(STATE, 'good'); os.makedirs(d, exist_ok=True)
    for src, name in ((pdf, f'{slug}.pdf.enc'), (screen, f'{slug}.screen.pdf.enc')):
        iv = os.urandom(12)
        data = AESGCM(key).encrypt(iv, open(src, 'rb').read(), slug.encode())
        tmp = os.path.join(d, name + '.tmp'); open(tmp, 'wb').write(iv + data); os.replace(tmp, os.path.join(d, name))


def vault_get(slug):
    key = vault_key()
    d = os.path.join(STATE, 'good')
    if not key or not os.path.exists(os.path.join(d, f'{slug}.pdf.enc')):
        return None
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    out = []
    for name in (f'{slug}.pdf.enc', f'{slug}.screen.pdf.enc'):
        try:
            raw = open(os.path.join(d, name), 'rb').read()
            plain = AESGCM(key).decrypt(raw[:12], raw[12:], slug.encode())
        except Exception as ex:
            print(f'ride sheets: previous sheet for {slug} could not be opened ({type(ex).__name__})')
            return None
        p = os.path.join(OUT, 'previous', name[:-4]); os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(plain); out.append(p)
    return out


def publish(dist):
    """Copy the locked files into the site. A plain sheet or booklet never goes on the site."""
    if not os.path.isdir(dist):
        return
    if os.path.exists(BOOKLET_KEY) and os.path.exists(BOOKLET_ENC):
        shutil.copyfile(BOOKLET_ENC, os.path.join(dist, 'booklet.pdf.enc'))
        shutil.copyfile(BOOKLET_KEY, os.path.join(dist, 'booklet.key.json'))
    elif os.path.exists(os.path.join(LOCKED, 'booklet.enc.json')):   # only until the first v2 booklet is made
        shutil.copyfile(os.path.join(LOCKED, 'booklet.enc.json'), os.path.join(dist, 'booklet.enc.json'))
    if glob.glob(os.path.join(LOCKED, 'ride-sheets', '*.enc.json')):
        d = os.path.join(dist, 'ride-sheets'); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        for f in glob.glob(os.path.join(LOCKED, 'ride-sheets', '*.enc.json')):
            shutil.copyfile(f, os.path.join(d, os.path.basename(f)))
        print('ride sheets: published', ', '.join(f for f in ('booklet.pdf.enc', 'booklet.key.json', 'booklet.enc.json') if os.path.exists(os.path.join(dist, f))),
              'and', len(os.listdir(d)), 'locked sheets')
    for dp, _, fs in os.walk(dist):
        for f in fs:
            if f.lower().endswith('.pdf'):
                os.remove(os.path.join(dp, f)); print('ride sheets: removed a plain PDF from the site:', f)


def publish_photos(dist):
    """ride-sheets/photos.json (public): which photo each sheet uses, for the Ride Desk card and its weekly check. Web
    addresses only (the website's featured image, a link picked on the card, or a Ride with GPS photo); never a route code."""
    try: m = json.load(open(os.path.join(STATE, 'manifest.json')))
    except Exception: return
    out = {}
    for rid, e in (m.get('rides') or {}).items():
        p = e.get('photo') or {}
        src = p.get('source') or 'placeholder'
        ref = p.get('ref') if re.match(r'https://', str(p.get('ref') or '')) else None
        out[e.get('slug') or rid] = {'source': {'override': 'picked'}.get(src, src), 'url': ref, 'page': p.get('page'), 'fetched': p.get('fetched')}
    os.makedirs(os.path.join(dist, 'ride-sheets'), exist_ok=True)
    L.write_json(os.path.join(dist, 'ride-sheets', 'photos.json'), {'checked': m.get('checked'), 'rides': out})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--redraw-maps', action='store_true')
    ap.add_argument('--only')
    ap.add_argument('--map-budget', type=float, default=float(os.environ.get('BOOKLET_MAP_BUDGET', 1200)))
    a = ap.parse_args()
    changed = False
    try:
        b = Build(a)
        if a.plan:
            print(b.plan()); return
        changed = b.run()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print('ride sheets: something went wrong; the last good booklet is kept')
        if a.plan:
            print('maps'); return
    try:
        publish(DIST)
    except Exception as e:
        print('ride sheets: could not publish:', e)
    try:
        publish_photos(DIST)
    except Exception as e:
        print('ride sheets: could not publish photos.json:', e)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'changed={"true" if changed else "false"}\n')


if __name__ == '__main__':
    main()
