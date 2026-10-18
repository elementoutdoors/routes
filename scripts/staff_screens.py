"""Screenshots for the Ride Guide manuals in EO Crew (EO-HI-10 for staff, EO-HI-10.1 for managers), taken every night.

Every screen of the app on a phone-sized browser, ridden on a real ride with a simulated GPS, and the Ride Desk with
made-up data. Each screenshot has numbered markers (Bike On colours) and a key saying what each number is, so the
manual's pictures and words always match the app as it is. Retaken by the build, so a change to the app or the Ride Desk
shows in the manual the next morning.

Usage: python3 scripts/staff_screens.py <base_url> <outdir>   (after a build; reads qr/links.json and dist/)
Writes JPEGs and screens.json ({ride, taken, screens: [{file, group, title, caption, keys: [[n, text]]}]}) to <outdir>.
They show a live ride, so they are only ever published locked (scripts/staff_bundle.mjs).
Groups: setup (getting a customer going), riding, stops, finish, settings (the phone's settings), desk (the Ride Desk).
The list of screens is also what the manual's drift check fingerprints (scripts/manual_facts.mjs).
"""
import json, os, subprocess, sys, tempfile, time
from playwright.sync_api import sync_playwright

base, out = sys.argv[1].rstrip('/') + '/', sys.argv[2]
SLUG = os.environ.get('SCREENS_RIDE', 'kids-and-family')
STOP = os.environ.get('SCREENS_STOP', 'Lake Doonella')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(out, exist_ok=True)
link = json.load(open(f'{ROOT}/qr/links.json'))[SLUG]
key = link.split('#', 1)[1]
ONLY = set(filter(None, os.environ.get('SCREENS_ONLY', '').split(',')))   # for testing: take only these files

QUIET = """
Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak: function(){}, cancel: function(){}, getVoices: function(){ return [{lang:'en-AU',localService:true,name:'x'}]; }, onvoiceschanged:null } });
Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: function(t){ this.text=t; } });
HTMLMediaElement.prototype.play = function(){ return Promise.resolve(); };
"""

# Numbered markers drawn over the page: a black circle with a white ring (Bike On black), and a Bike On blue box round
# the thing it points at. marks: [[n, css selector or "text:<words>", where]] where = tl, tr, l, r (side of the box).
MARK = """(marks) => {
  document.querySelectorAll('.zz-mark').forEach(e => e.remove());
  const found = [];
  // the shortest visible element whose text starts with the words: as written first (so a label wins over an
  // upper case badge saying the same thing), then ignoring case (headings drawn in capitals)
  const byText = (t) => {
    const vis = [...document.querySelectorAll('body *')].filter(e => e.offsetParent !== null && e.children.length < 4 && !e.classList.contains('zz-mark'));
    const pick = (f) => vis.filter(e => f((e.innerText || '').trim())).sort((a, b) => (a.innerText || '').length - (b.innerText || '').length)[0];
    return pick(x => x.startsWith(t)) || pick(x => x.toLowerCase().startsWith(t.toLowerCase()));
  };
  for (const [n, sel, where] of marks) {
    const el = sel.startsWith('text:') ? byText(sel.slice(5)) : [...document.querySelectorAll(sel)].find(e => e.getClientRects().length);
    if (!el) continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    found.push(n);
    const box = document.createElement('div'); box.className = 'zz-mark';
    Object.assign(box.style, { position: 'fixed', left: (r.left - 3) + 'px', top: (r.top - 3) + 'px', width: (r.width + 6) + 'px', height: (r.height + 6) + 'px',
      border: '3px solid #0C5AA9', borderRadius: '10px', boxShadow: '0 0 0 2px rgba(255,255,255,.9)', zIndex: 2147483646, pointerEvents: 'none' });
    document.body.appendChild(box);
    const c = document.createElement('div'); c.className = 'zz-mark'; c.textContent = n;
    const s = 28, w = where || 'tl';
    let x = w.includes('r') ? r.right - s * 0.35 : r.left - s * 0.65, y = r.top - s * 0.65;
    if (w === 'l') { x = r.left - s - 4; y = r.top + r.height / 2 - s / 2; }
    if (w === 'r') { x = r.right + 4; y = r.top + r.height / 2 - s / 2; }
    x = Math.max(2, Math.min(innerWidth - s - 2, x)); y = Math.max(2, Math.min(innerHeight - s - 2, y));
    Object.assign(c.style, { position: 'fixed', left: x + 'px', top: y + 'px', width: s + 'px', height: s + 'px', borderRadius: '50%',
      background: '#231F20', color: '#fff', border: '2px solid #fff', boxShadow: '0 1px 4px rgba(0,0,0,.5)', font: '800 14px/24px Montserrat, Arial, sans-serif',
      textAlign: 'center', zIndex: 2147483647, pointerEvents: 'none' });
    document.body.appendChild(c);
  }
  return found;
}"""

taken = []


def shot(page, f, group, title, caption, keys=(), marks=None, element=None, quality=62):
    """keys: [(n, selector, text, where)]; numbers with nothing found on screen are left out of the key."""
    if ONLY and f not in ONLY:
        return
    found = page.evaluate(MARK, [[n, sel, where] for n, sel, _, where in keys]) if keys else []
    time.sleep(0.15)
    target = page.locator(element).first if element else page
    target.screenshot(path=f'{out}/{f}', type='jpeg', quality=quality)
    page.evaluate("() => document.querySelectorAll('.zz-mark').forEach(e => e.remove())")
    k = [[n, text] for n, _, text, _ in keys if n in found]
    full = caption + (' ' + ' '.join(f'{n} {t}' for n, t in k) if k else '')
    taken.append({'file': f, 'group': group, 'title': title, 'caption': full, 'keys': k})
    missing = [n for n, *_ in keys if n not in found]
    print('took', f, f'(markers not found: {missing})' if missing else '')


def wait_visible(page, sel, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        if page.is_visible(sel):
            return True
        time.sleep(0.2)
    return False


def close_sheet(page):
    if page.is_visible('#sheet'):
        page.click('#sheet-close'); time.sleep(0.4)


def off_point(T, i, metres):
    """A point this far to the side of the route line at track index i."""
    import math
    j = min(i + 3, len(T['lat']) - 1)
    dlat, dlng = T['lat'][j] - T['lat'][i], (T['lng'][j] - T['lng'][i]) * math.cos(math.radians(T['lat'][i]))
    n = math.hypot(dlat, dlng) or 1
    off = metres / 111320
    return T['lat'][i] + (-dlng / n) * off, T['lng'][i] + (dlat / n) * off / math.cos(math.radians(T['lat'][i]))


# ---------------------------------------------------------------- the app, on a phone
def app_screens(p):
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=1.5, is_mobile=True, has_touch=True,
                        geolocation={'latitude': -26.4078, 'longitude': 153.0434, 'accuracy': 10}, permissions=['geolocation'], locale='en-AU')
    ctx.add_init_script(QUIET)
    # staff screenshots never count in the ride counts
    ctx.route('**/script.google.com/**', lambda r: r.abort())
    ctx.route('**/script.googleusercontent.com/**', lambda r: r.abort())
    page = ctx.new_page()

    page.goto(base)
    page.wait_for_selector('#v-home', state='visible', timeout=20000); time.sleep(2)
    shot(page, '01-home.jpg', 'setup', 'Home page',
         'What a customer sees if they open the Ride Guide without a ride.',
         [(1, '#home-empty', 'Scan the QR code: the ride opens on its own.', 'tl'),
          (2, '#code-form', 'Have a route code? Type the 6 character code and tap Open.', 'tl'),
          (3, '#home-settings', 'Settings: language and units.', 'tl')])

    page.goto(f'{base}#{key}')
    page.wait_for_selector('body.view-route', timeout=20000); time.sleep(7)
    route = page.evaluate(f"fetch('r/{key}.json').then(r=>r.json())")
    shot(page, '02-route.jpg', 'setup', 'Ride page',
         "The ride's own page, opened from its QR code, link or route code.",
         [(1, '#route-wordmark', "The ride's brand: Bike On or By Earth and Ocean.", 'tl'),
          (2, '#route-lang', 'Language (nine to choose from).', 'tl'),
          (3, '#route-units', 'Kilometres or miles.', 'tr'),
          (4, '#route-name', 'Ride name.', 'tl'),
          (5, '.stats', 'Distance, climbing and riding time (time on the bike only, not stops).', 'tl'),
          (6, '#route-stops-btn', 'Stops: every place on the ride.', 'tl'),
          (7, '#route-cues-btn', 'Directions: every turn, in order.', 'tr')])

    page.evaluate("() => { const v = document.querySelector('#v-route'); v.scrollTop = v.scrollHeight; window.scrollTo(0, document.body.scrollHeight); }")
    time.sleep(1)
    shot(page, '03-route-lower.jpg', 'setup', 'Ride page, further down',
         'Before they leave: the description, the saved to phone note and Start riding.',
         [(1, '#route-desc-wrap', 'The ride description.', 'tl'),
          (2, '#offline-note', 'Wait for "Saved to your phone. Works with no signal." before they leave.', 'tl'),
          (3, '#start-btn', 'Start riding: tap it at the shop, then allow location.', 'tl'),
          (4, '#lock-note', 'Locking the phone stops the directions.', 'l'),
          (5, '#keep-btn', 'Getting back to this route: the route code and adding the ride to the home screen.', 'tl'),
          (6, '#call-link', 'Need help? Call us: rings the shop.', 'tl'),
          (7, '#route-settings', 'Settings.', 'tr')])

    page.click('#keep-btn'); time.sleep(1.2)
    # the build serves the site locally: show the address riders actually see
    page.evaluate("() => document.querySelectorAll('#sheet-body .addr').forEach(e => e.textContent = 'elementoutdoors.github.io/routes')")
    shot(page, '04-getting-back.jpg', 'setup', 'Getting back to this route',
         'How a rider gets back to their ride on another day or another phone.',
         [(1, '.code-big', 'Their 6 character route code. Typing it on the home page reopens the ride.', 'tl'),
          (2, '#sheet-body .addr', 'The web address to type it at.', 'tl'),
          (3, 'text:Add it to your home screen', 'Add the ride to the home screen, so it opens like an app.', 'tl')])
    close_sheet(page)

    page.click('#route-settings'); time.sleep(1)
    shot(page, '05-settings.jpg', 'settings', 'Settings, top',
         'Settings, from the ride page or the menu button while riding.',
         [(1, 'text:Metric (km)', 'Kilometres or miles.', 'tl'),
          (2, '.lang-grid', 'Language. Directions, stops and stories change language too.', 'tl')])
    page.evaluate("() => { const b = document.querySelector('#sheet-body'); b.scrollTop = b.scrollHeight; }"); time.sleep(0.6)
    shot(page, '06-settings-lower.jpg', 'settings', 'Settings, further down',
         'The voice, screen and map settings.',
         [(1, '.toggle-row:nth-child(1)', 'Spoken directions on or off. Off still shows them on screen.', 'tl'),
          (2, '.toggle-row:nth-child(2)', 'Natural voice: our recorded voice. Off uses the phone\'s own voice.', 'tl'),
          (3, '.toggle-row:nth-child(3)', 'Chime: a short ding at each turn.', 'tl'),
          (4, '.toggle-row:nth-child(4)', 'Stories: hear a short overview at each place.', 'tl'),
          (5, '.toggle-row:nth-child(5)', 'Battery saver: blacks the screen out between turns.', 'tl'),
          (6, 'text:Satellite', 'Standard or satellite map (satellite needs signal).', 'tl'),
          (7, 'text:Download this ride as a GPX file', 'GPX file for a Garmin or Wahoo (only on some rides).', 'tl')])
    close_sheet(page)

    # Riding: start a little way from the start of the route, so the app shows "head to the start"
    T = route['track']; n = len(T['d'])
    la, ln = off_point(T, 0, 350)
    ctx.set_geolocation({'latitude': la, 'longitude': ln, 'accuracy': 8})
    page.click('#start-btn'); time.sleep(3)
    close_sheet(page)
    ctx.set_geolocation({'latitude': la + 0.00001, 'longitude': ln, 'accuracy': 8}); time.sleep(1.5)
    shot(page, '07-to-start.jpg', 'riding', 'Before reaching the route',
         'Started away from the route. Nothing is wrong: directions start once they reach the line.',
         [(1, '#cue-card', 'How far to the start. Head for the green marker.', 'tl')])

    # ride along to just before a turn, a few hundred metres in
    step = max(1, n // 220)
    cues = route['cues']
    target = next((c['d'] for c in cues if c['d'] > 400), T['d'][n // 5]) - 120
    i = 0
    while i < n and T['d'][i] < target:
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(0.12)
        close_sheet(page)
        i += step
    time.sleep(1.5); close_sheet(page)
    page.evaluate("() => { const b = document.getElementById('banner'); if (b) b.hidden = true; }")
    shot(page, '08-riding.jpg', 'riding', 'Riding',
         'The riding screen. Everything a rider needs is on it; the phone stays in the mount.',
         [(1, '.cue-main', 'Next direction and how far to it. It is also spoken.', 'tl'),
          (2, '#cue-next-text', 'The direction after that.', 'tl'),
          (3, '#cue-repeat', 'Repeat the last thing said.', 'tr'),
          (4, '#btn-voice', 'Voice on or off.', 'l'),
          (5, '#btn-follow', 'Centre the map on me.', 'l'),
          (6, '#btn-ride-settings', 'Settings.', 'l'),
          (7, '.me', 'Where the rider is. The line turns grey behind them.', 'tr'),
          (8, '#remain', 'Distance to go, and time at an easy pace.', 'tl'),
          (9, '#pause-btn', 'Pause: for a coffee, a swim or a detour.', 'tl'),
          (10, '#end-btn', 'End ride.', 'tr'),
          (11, '#b-cues', 'Directions list.', 'tl'),
          (12, '#b-stops', 'Stops list.', 'tl'),
          (13, '#b-offers', 'Rider offers.', 'tr')])

    page.click('#b-cues'); time.sleep(1)
    shot(page, '09-directions.jpg', 'riding', 'Directions list',
         'Every turn in order. The next one is highlighted and the ones ridden are greyed out.',
         [(1, '.list-item.current', 'The next direction.', 'tl')])
    close_sheet(page)
    page.click('#b-stops'); time.sleep(1)
    shot(page, '10-stops.jpg', 'stops', 'Stops list',
         'Every place on the ride with how far along it is. Tap one to read about it or hear its story.',
         [(1, '#sheet-body .list-item', 'A stop. Toilets, cafes and water show here and on the map, but never pop up.', 'tl')])
    close_sheet(page)

    # off route: move well off the line for a few readings
    for k in range(6):
        la, ln = off_point(T, i, 140 + k * 5)
        ctx.set_geolocation({'latitude': la, 'longitude': ln, 'accuracy': 8}); time.sleep(0.9)
    close_sheet(page)
    shot(page, '11-off-route.jpg', 'riding', 'Off route',
         'More than 50 m from the line for a few seconds. The Ride Guide does not give directions back: riders use the map.',
         [(1, '#cue-card', 'Off route, and how far away the line is. Spoken as well.', 'tl'),
          (2, '#pause-btn', 'Stopped on purpose? Tap Pause and the warnings stop.', 'tl')])
    page.click('#pause-btn'); time.sleep(1)
    shot(page, '12-paused.jpg', 'riding', 'Paused',
         'While paused the map still shows where they are, but directions and warnings are off and the screen can sleep.',
         [(1, '#cue-card', 'Ride paused.', 'tl'),
          (2, '#pause-btn', 'Resume carries on from here.', 'tl')])
    page.click('#pause-btn'); time.sleep(0.5)
    for k in range(4):
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(0.6)
    close_sheet(page)

    # battery saver: turn it on from the ride menu, then wait for the screen to black out away from a turn
    page.click('#btn-ride-settings'); time.sleep(0.8)
    page.locator('.toggle-row', has_text='Battery saver').locator('.switch').click(); time.sleep(0.3)
    close_sheet(page)
    far = i
    while far < n - 1 and not any(0 < c['d'] - T['d'][far] < 400 for c in cues) and T['d'][far] - T['d'][i] < 1500:
        far += step
    # a stretch with no turn in the next 400 m
    best = None
    for j in range(i, n, step):
        if not any(-20 < c['d'] - T['d'][j] < 450 for c in cues):
            best = j; break
    j = best or i
    for k in range(i, j + 1, step):
        ctx.set_geolocation({'latitude': T['lat'][k], 'longitude': T['lng'][k], 'accuracy': 8}); time.sleep(0.12)
        close_sheet(page)
    i = j
    page.evaluate("() => { const b = document.getElementById('banner'); if (b) b.hidden = true; }")
    # the saver checks on each GPS reading: keep readings coming while the blackout delay runs out
    for k in range(26):
        ctx.set_geolocation({'latitude': T['lat'][i] + (k % 2) * 0.000005, 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(1)
        if page.is_visible('#saver'):
            break
    shot(page, '13-battery-saver.jpg', 'riding', 'Battery saver',
         'With Battery saver on, the screen goes black between turns (almost no power) and lights up before each turn, at stops and when off route.',
         [(1, '.saver-hint', 'Tap anywhere to wake the screen.', 'tl')])
    if page.is_visible('#saver'):
        page.click('#saver'); time.sleep(0.3)
    page.click('#btn-ride-settings'); time.sleep(0.8)
    page.locator('.toggle-row', has_text='Battery saver').locator('.switch').click(); time.sleep(0.3)
    close_sheet(page)

    # ride on to the stop with a story
    got = False
    while i < n:
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(0.12)
        if page.is_visible('#sheet'):
            title = page.inner_text('#sheet-title') if page.is_visible('#sheet-title') else ''
            if STOP.lower() in title.lower():
                got = True; time.sleep(1.2); break
            close_sheet(page)
        i += step
    if got:
        shot(page, '14-stop.jpg', 'stops', 'Stop card',
             'Pops up as the rider reaches a place, and its name and a short overview are read out (when stories are on).',
             [(1, '.photo-strip', 'Photos of the place.', 'tl'),
              (2, '#sheet-title', 'The place.', 'tl'),
              (3, 'text:Listen', 'Listen: reads the short overview again.', 'tl'),
              (4, '#story-btn', 'Hear the full story: about a minute on this place, in the natural voice.', 'tl'),
              (5, 'text:More about this place', 'More about this place: the place on our blog (needs signal).', 'tl'),
              (6, 'text:Back to my ride', 'Back to my ride.', 'tl')])
        if page.is_visible('#story-btn'):
            page.click('#story-btn'); time.sleep(1)
            shot(page, '15-story.jpg', 'stops', 'Full story playing',
                 'The full story playing. A direction or warning cuts in over it, then it carries on.',
                 [(1, '#story-btn', 'Tap again to stop the story.', 'tl')])
            page.click('#story-btn'); time.sleep(0.3)
        more = page.get_by_text('More about this place')
        if more.count():
            more.first.click(); time.sleep(7)
            if page.is_visible('#viewer'):
                shot(page, '16-place-page.jpg', 'stops', 'More about this place',
                     'Our blog opens inside the Ride Guide, so the ride, GPS and voice keep running underneath.',
                     [(1, '#viewer-back', 'Back to my ride.', 'tl'),
                      (2, '#viewer-cue', 'The next direction stays on top.', 'tl'),
                      (3, '#viewer-ext', 'Open in the browser instead.', 'tr')])
                page.click('#viewer-back'); time.sleep(0.5)
        close_sheet(page)

    page.click('#b-offers'); time.sleep(1)
    shot(page, '17-offers.jpg', 'finish', 'Rider offers',
         "Our partners' offers. Offers marked When you get back come up near the end of the ride and on the finish card.",
         [(1, '#sheet-body .list-item', 'An offer. Tap it for the voucher and how to claim it.', 'tl')])
    items = page.locator('#sheet-body .list-item')
    if items.count():
        items.first.click(); time.sleep(3)
        shot(page, '18-offer.jpg', 'finish', 'Offer card',
             'One offer: where it is, what it is, how to claim it and the conditions.',
             [(1, '.v-map', 'Where the partner is, on the ride.', 'tl'),
              (2, '.v-head', 'The offer.', 'tl'),
              (3, '.v-how', 'How to claim it. Land and Sea needs our voucher card.', 'tl'),
              (4, '.v-conds', 'Conditions.', 'tl')])
    close_sheet(page)

    # ride to the end
    while i < n:
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(0.1)
        if page.is_visible('#sheet') and i < n - 5 * step:
            close_sheet(page)
        i += step
    ctx.set_geolocation({'latitude': T['lat'][-1], 'longitude': T['lng'][-1], 'accuracy': 8}); time.sleep(2.5)
    if page.is_visible('.rate-faces'):
        shot(page, '19-finish.jpg', 'finish', 'Finish card',
             'Comes up once most of the ride (75%) has been ridden on that phone.',
             [(1, '.rate-faces', 'How was your ride? Loved it, It was OK or Not great.', 'tl'),
              (2, 'text:Before you go', 'Offers for the end of the ride.', 'tl')])
        page.locator('.face.good').first.click(); time.sleep(0.8)
        shot(page, '20-finish-loved.jpg', 'finish', 'Loved it',
             'Loved it asks for a Google or Tripadvisor review. It was OK or Not great offers email or a call first, then the same review links.',
             [(1, 'text:Thanks, we are so glad', 'Review links for the ride\'s own brand.', 'tl'),
              (2, '.rate-change', 'Change my answer.', 'tl')])
    b.close()
    return route


# ---------------------------------------------------------------- the Ride Desk, with made-up data
def desk_docs():
    cfg = json.load(open(f'{ROOT}/config/ride-desk.json'))['rides']
    sett = json.load(open(f'{ROOT}/config/settings.json'))
    offers = json.load(open(f'{ROOT}/config/offers.json'))['offers']
    docs = {}
    example = {'suits': 'Example: families and relaxed riders who want flat paths.', 'notFor': 'Example: anyone after a workout.',
               'timeToAllow': 'Example: 2 hours', 'soldAs': 'Example: Kids and Family e-Bike ride', 'bikes': 'Example: Cruiser e-Bikes, kids bikes, carriers',
               'startFinish': 'Example: the shop', 'staffNotes': 'Example: staff notes appear here.'}
    for slug, c in cfg.items():
        d = dict(c); d.pop('_note', None)
        d['staff'] = dict(example)
        docs[f'rides/{slug}'] = d
    groups = {g: {k: v for k, v in sett[g].items() if not k.startswith('_')} for g in ['announce', 'offRoute', 'stops', 'screen', 'speeds']}
    page_offers = []
    for o in offers:
        page_offers.append({'id': o['id'], 'active': o.get('active', True), 'allRoutes': o.get('allRoutes', False), 'showAt': o.get('showAt', 'anywhere'),
                            'partner': o.get('partner', ''), 'logo': o.get('logo', ''), 'headline': o.get('headline', ''), 'alt': o.get('alt') or '',
                            'about': o.get('about') or '', 'how': o.get('how') or '', 'conditions': '\n'.join(o['conditions']) if isinstance(o.get('conditions'), list) else (o.get('conditions') or ''),
                            'phone': o.get('phone') or '', 'where': o.get('where') or o.get('address') or '', 'url': o.get('url') or '', 'radius': o.get('radius', 500),
                            'validUntil': o.get('validUntil') or '', 'hideOn': o.get('hideOn') or [], 'lat': o.get('lat'), 'lng': o.get('lng'), 'onRoutes': []})
    docs['settings/current'] = dict(groups, rev=1, savedAt='2026-10-18T00:00:00Z', offers=page_offers)
    docs['settings/status'] = {'appliedRev': 1, 'appliedAt': '2026-10-18T00:05:00Z', 'result': 'live', 'message': 'Live on the site.'}
    docs['settings/config'] = {'triggerId': 'example'}
    docs['routes/offers'] = {'offers': page_offers}
    docs['routes/links'] = {'links': {s: {'link': 'https://elementoutdoors.github.io/routes/#EXAMPLE-LINK', 'code': 'EXAMPL'} for s in cfg}}
    docs['routes/counts'] = {'ok': True, 'asOf': '2026-10-18', 'startedOn': '2026-10-17',
                             'routes': {SLUG: {'phones': 12, 'phones30': 12, 'rides': 9, 'rides30': 9, 'lastRide': '2026-10-18'}}}
    tmp = tempfile.mkdtemp()
    for k, v in docs.items():
        os.makedirs(os.path.join(tmp, os.path.dirname(k)), exist_ok=True)
        json.dump(v, open(os.path.join(tmp, k + '.json'), 'w'))
    pub = tempfile.mkdtemp()
    env = dict(os.environ, SITE_BASE=base)
    subprocess.run(['node', f'{ROOT}/scripts/ride-desk.mjs', 'published', tmp, pub], check=False, env=env, capture_output=True)
    for d in ['rides', 'stories']:
        f = os.path.join(pub, 'published', d + '.json')
        if os.path.exists(f):
            docs[f'published/{d}'] = json.load(open(f))
    return docs


def desk_screens(p):
    subprocess.run([sys.executable, f'{ROOT}/ride-desk/build.py'], check=True, capture_output=True)
    docs = desk_docs()
    html = ('<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><script>'
            + open(f'{ROOT}/ride-desk/mock.js').read().replace('__DOCS__', json.dumps(docs)) + '</script></head><body>'
            + open(f'{ROOT}/ride-desk/ride-desk.html').read() + '</body></html>')
    f = os.path.join(tempfile.mkdtemp(), 'desk.html'); open(f, 'w').write(html)
    b = p.chromium.launch()
    page = b.new_page(viewport={'width': 760, 'height': 900}, device_scale_factor=1.25, color_scheme='light')
    page.goto('file://' + f); time.sleep(1.5)
    shot(page, '21-desk-top.jpg', 'desk', 'Ride Desk, top',
         'The Ride Desk: every ride, the partner offers and the rider settings on one page (made-up data in these pictures).',
         [(1, '#status', 'Whether the last save is live on the site.', 'tl'),
          (2, '#rideTools', 'Filter the rides (live, hidden, new, needs work) and search.', 'tl'),
          (3, '#cards .ride', 'One card per ride. Tap it to open it.', 'tl')])
    row = page.locator(f'#cards [data-slug="{SLUG}"]')
    if row.count():
        row.locator('.otoggle').first.click(); time.sleep(0.6)
        row.scroll_into_view_if_needed(); time.sleep(0.3)
        page.evaluate("(s) => document.querySelector(`#cards [data-slug=\"${s}\"]`).scrollIntoView({block: 'start'})", SLUG); time.sleep(0.3)
        shot(page, '22-desk-card.jpg', 'desk', 'A ride card, top',
             'Where the ride shows and how it looks in the app.',
             [(1, 'text:Live in the Ride Guide', 'Live in the Ride Guide: off takes the ride out of the app.', 'tl'),
              (2, 'text:Show on the hire desk iPad', 'Show on the hire desk iPad and in the booklet: off for private guide rides.', 'tl'),
              (3, 'text:In the Ride Guide app', 'Name in the app, brand, type, stories on or off, GPX download.', 'tl')])
        for title, f2, text, marks in [
            ('Ride description', '23-desk-description.jpg', 'The ride description riders read on the ride page and in the booklet.',
             [(1, 'text:Ride description', 'The master copy of the description.', 'tl')]),
            ('Ride sheet, iPad and booklet', '24-desk-sheet.jpg', 'What the ride sheet, the iPad and the booklet show.',
             [(1, 'text:Ride sheet, iPad and booklet', 'Title, category, sell line, four highlights, level, surface and bike.', 'tl')]),
            ('Photo', '24b-desk-photo.jpg', 'The photo on the ride sheet, the iPad and in the booklet.',
             [(1, '.photo', 'The Bike On website photo by default, or one of the ride\'s own photos, an upload or a link.', 'tl')]),
            ('For staff', '25-desk-staff.jpg', 'Staff notes, shown to staff in EO Crew.',
             [(1, 'text:For staff', 'Who it suits, not for, time to allow, sold as, staff notes.', 'tl')]),
            ('Places the ride passes', '26-desk-places.jpg', 'Every place on the ride, in ride order, with its story.',
             [(1, 'text:Places the ride passes', 'The places come from Ride with GPS; the stories from the Story Library.', 'tl'),
              (2, 'text:Open in the Story Library', 'Edit a story in the Story Library.', 'tl')])]:
            loc = row.get_by_text(title, exact=False)
            if loc.count():
                loc.first.scroll_into_view_if_needed()
                page.evaluate("(t) => { const e = [...document.querySelectorAll('#cards *')].find(x => x.children.length < 3 && (x.innerText || '').trim().toLowerCase().startsWith(t.toLowerCase())); if (e) { e.scrollIntoView({block: 'start'}); window.scrollBy(0, -16); } }", title)
                time.sleep(0.3)
                shot(page, f2, 'desk', title, text, marks)
    page.evaluate("() => { const e = document.getElementById('offers'); if (e) e.scrollIntoView({block: 'start'}); }"); time.sleep(0.4)
    shot(page, '27-desk-offers.jpg', 'desk', 'Partner offers',
         'Each offer: when riders see it, the deal, how to claim it, where the partner is and which rides show it.',
         [(1, '#offers .offer', 'One offer. Open it to change it.', 'tl'),
          (2, '#addOffer', 'Add an offer.', 'tl')])
    page.evaluate("() => { const e = [...document.querySelectorAll('h2, h3')].find(x => /Spoken turn directions/.test(x.innerText)) || document.getElementById('groups'); if (e) e.scrollIntoView({block: 'start'}); }"); time.sleep(0.4)
    shot(page, '28-desk-settings.jpg', 'desk', 'Rider settings',
         'How the Ride Guide behaves on every phone. Each slider shows what riders will hear.',
         [(1, '#groups', 'Each setting, with an example of what riders hear.', 'tl'),
          (2, '#undo', 'Undo changes: throws away anything not saved yet.', 'tl'),
          (3, '#reset', 'Recommended rider settings: puts our recommended values back (press Save to use them).', 'tl'),
          (4, '#save', 'Save: every change on the page goes live, usually within 10 minutes.', 'tr')])
    b.close()


with sync_playwright() as p:
    route = app_screens(p)
    try:
        desk_screens(p)
    except Exception as e:   # the app pictures matter most: keep them even if the Ride Desk ones fail
        print('Ride Desk screenshots failed:', e)

json.dump({'ride': route.get('name', SLUG), 'taken': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'screens': taken},
          open(f'{out}/screens.json', 'w'), indent=1)
print(f'{len(taken)} screenshots taken')
if len(taken) < 12 and not ONLY:
    sys.exit(1)
