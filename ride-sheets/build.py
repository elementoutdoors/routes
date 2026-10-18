"""The living ride sheets and rides booklet, run by the site build after every Ride Guide build.

One A4 landscape sheet per live ride (both brands, from sheet.py) and the combined booklet (booklet.py), kept up to date
by themselves. Route codes and links are never public, so they are only published locked with EO Crew's public key:
dist/booklet.enc.json (the whole booklet, with the page of each ride) and dist/ride-sheets/<slug>.enc.json (one sheet).

Living rules (what each sheet was built from is kept in STATE/manifest.json, with a changelog):
  3D map       drawn again only when the route line changes a lot (length by more than 2 percent, or any part more than
               100 m from the line the map was drawn from), or the map's own settings in rides.py change. Cue, stop and
               story edits, or a line nudged a few metres, keep the map.
  ride story   always the ride's current description in the Ride Guide; a change is logged.
  numbers      always the latest distance, climbing and riding time; a change of 0.5 km or 25 m climbing is logged.
  photo        the ride's website photo (config/booklet-photos.json), fetched again only when it or the mapping changes.
The sheets and booklet are made again whenever anything on a sheet changed.

python3 ride-sheets/build.py           build what changed and publish the locked files into dist/
python3 ride-sheets/build.py --plan    print none, sheets or maps (what this run needs installed), and stop
Options: --force (make every sheet again), --redraw-maps, --only <rid,...>, --map-budget SECONDS.
A failure never stops the site build: the last good locked files are kept and published.
"""
import argparse, datetime, glob, hashlib, json, os, re, shutil, sys, time, traceback
from zoneinfo import ZoneInfo
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import ROOT, STATE, OUT, DIST
import living as L

TZ = ZoneInfo('Australia/Brisbane')
BOOKLET = 'Ride sheets booklet.pdf'
LOCKED = os.path.join(STATE, 'locked')
CODE_FILES = ['sheet.py', 'booklet.py', 'rides.py', 'textfit.py', 'check.py']


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
        try: self.photo_cfg = json.load(open(os.path.join(ROOT, 'config', 'booklet-photos.json')))
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
        if self.a.force or self.booklet_inputs(ins) != self.m.get('booklet_inputs') or not os.path.exists(os.path.join(LOCKED, 'booklet.enc.json')):
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
        changed = self.a.force or bi != self.m.get('booklet_inputs') or not os.path.exists(os.path.join(LOCKED, 'booklet.enc.json'))
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
                    self.log(rid, 'no photo found: placeholder shown (set one in config/booklet-photos.json)')
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
        import sheet, booklet, check
        M = self.m['rides']
        args = ['--ignore-certificate-errors']
        res = sheet.shoot(self.order, launch_args=args)
        problems = check.check(res)
        self.m['problems'] = problems
        for p in problems:
            print('ride sheets: CHECK', p)
        if any('QR code' in p or 'route code missing' in p for p in problems):
            print('ride sheets: a QR code or route code check failed, so the last good booklet is kept')
            return False
        for rid in self.order:
            M[rid]['story_printed'] = res[rid]['story']
            M[rid]['fit'] = res[rid]['check']
        pdf = os.path.join(OUT, BOOKLET)
        pages, page_of = booklet.make({rid: res[rid]['pdf'] for rid in self.order}, pdf, launch_args=args)
        built = now().isoformat(timespec='seconds')
        os.makedirs(os.path.join(LOCKED, 'ride-sheets'), exist_ok=True)
        index = []
        for rid in self.order:
            e = M[rid]; e['page'] = page_of[rid]
            index.append({'slug': e['slug'], 'title': e['title'], 'brand': self.RIDES[rid]['brand'], 'kind': booklet.group_of(rid),
                          'page': page_of[rid], 'updated': e.get('updated'), 'sheet': f'ride-sheets/{e["slug"]}.enc.json'})
            L.seal(res[rid]['pdf'], {'built': built, 'kind': 'ride-sheet', 'slug': e['slug'], 'title': e['title'],
                                     'file': sheet.fname(rid) + '.pdf', 'updated': e.get('updated')},
                   os.path.join(LOCKED, 'ride-sheets', e['slug'] + '.enc.json'))
        for f in glob.glob(os.path.join(LOCKED, 'ride-sheets', '*.enc.json')):
            if os.path.basename(f)[:-9] not in {M[r]['slug'] for r in self.order} and not self.a.only:
                os.remove(f)
        L.seal(pdf, {'built': built, 'title': 'Bike On and By Earth and Ocean ride sheets', 'file': BOOKLET, 'pages': pages,
                     'rides': index, 'photo_placeholders': self.m['placeholders']['photo'], 'maps_to_come': self.m['placeholders']['map'],
                     'changelog': self.m['changelog'][-200:]}, os.path.join(LOCKED, 'booklet.enc.json'))
        self.m['built'], self.m['pages'] = built, pages
        print(f'ride sheets: made {len(self.order)} sheets and a {pages} page booklet, locked', flush=True)
        return True


def publish(dist):
    """Copy the locked files into the site. A plain sheet or booklet never goes on the site."""
    if not os.path.isdir(dist):
        return
    if os.path.exists(os.path.join(LOCKED, 'booklet.enc.json')):
        shutil.copyfile(os.path.join(LOCKED, 'booklet.enc.json'), os.path.join(dist, 'booklet.enc.json'))
        d = os.path.join(dist, 'ride-sheets'); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        for f in glob.glob(os.path.join(LOCKED, 'ride-sheets', '*.enc.json')):
            shutil.copyfile(f, os.path.join(d, os.path.basename(f)))
        print('ride sheets: published booklet.enc.json and', len(os.listdir(d)), 'locked sheets')
    for dp, _, fs in os.walk(dist):
        for f in fs:
            if f.lower().endswith('.pdf'):
                os.remove(os.path.join(dp, f)); print('ride sheets: removed a plain PDF from the site:', f)


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
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'changed={"true" if changed else "false"}\n')


if __name__ == '__main__':
    main()
