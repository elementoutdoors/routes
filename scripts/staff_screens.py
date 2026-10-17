"""Screenshots of the Ride Guide for staff (the EO Crew Ride Guide manual, EO-HI-10), taken on a phone-sized browser.
Usage: python3 scripts/staff_screens.py <base_url> <outdir>   (after a build; reads qr/links.json)
Writes six JPEGs and screens.json to <outdir>. They show a live ride, so they are only published locked (staff_bundle.mjs)."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

base, out = sys.argv[1].rstrip('/') + '/', sys.argv[2]
SLUG = os.environ.get('SCREENS_RIDE', 'kids-and-family')
STOP = os.environ.get('SCREENS_STOP', 'Lake Doonella')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(out, exist_ok=True)
link = json.load(open(f'{ROOT}/qr/links.json'))[SLUG]
key = link.split('#', 1)[1]

SCREENS = [
    ('01-home.jpg', 'Home page', 'What a customer sees when they open the Ride Guide without a ride: scan the QR code, or type a route code.'),
    ('02-route.jpg', 'Route page', 'A ride\'s page: map, distance, climbing, riding time, stops, directions and Start riding.'),
    ('03-stop.jpg', 'Stop card', 'A stop popping up while riding: Listen, Hear the full story, More about this place and Back to my ride.'),
    ('04-story.jpg', 'Story playing', 'The same stop with the full story playing. Stop the story turns it off.'),
    ('05-place.jpg', 'Story page', 'More about this place, open inside the Ride Guide, with Back to my ride and the next turn on top.'),
    ('06-finish.jpg', 'Finish card', 'The finish card: You made it, How was your ride? and the rider offers.'),
]
QUIET = """
Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak: function(){}, cancel: function(){}, getVoices: function(){ return [{lang:'en-AU',localService:true,name:'x'}]; }, onvoiceschanged:null } });
Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: function(t){ this.text=t; } });
HTMLMediaElement.prototype.play = function(){ return Promise.resolve(); };
"""
taken = []

def shot(page, i):
    f, title, caption = SCREENS[i]
    page.screenshot(path=f'{out}/{f}', type='jpeg', quality=72)
    taken.append({'file': f, 'title': title, 'caption': caption})
    print('took', f)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        geolocation={'latitude': -26.4078, 'longitude': 153.0434, 'accuracy': 10}, permissions=['geolocation'], locale='en-AU')
    ctx.add_init_script(QUIET)
    # staff test drives never count in the ride counts
    ctx.route('**/script.google.com/**', lambda r: r.abort())
    ctx.route('**/script.googleusercontent.com/**', lambda r: r.abort())
    page = ctx.new_page()
    page.goto(base)
    page.wait_for_selector('#v-home', state='visible', timeout=20000); time.sleep(2)
    shot(page, 0)
    page.goto(f'{base}#{key}')
    page.wait_for_selector('body.view-route', timeout=20000); time.sleep(6)
    shot(page, 1)
    route = page.evaluate(f"fetch('r/{key}.json').then(r=>r.json())")
    page.click('#start-btn'); time.sleep(2)
    if page.is_visible('#sheet'): page.click('#sheet-close'); time.sleep(0.3)
    T = route['track']; n = len(T['d']); step = max(1, n // 200)
    got_stop = False
    for i in range(0, n, step):
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8}); time.sleep(0.12)
        if not page.is_visible('#sheet'): continue
        title = page.inner_text('#sheet-title') if page.is_visible('#sheet-title') else ''
        if not got_stop and STOP.lower() in title.lower():
            time.sleep(1); shot(page, 2); got_stop = True
            if page.is_visible('#story-btn'):
                page.click('#story-btn'); time.sleep(1); shot(page, 3)
                page.click('#story-btn'); time.sleep(0.3)
            more = page.get_by_text('More about this place')
            if more.count():
                more.first.click(); time.sleep(6)
                if page.is_visible('#viewer'):
                    shot(page, 4); page.click('#viewer-back'); time.sleep(0.5)
        if page.is_visible('#sheet') and i < n - 5 * step: page.click('#sheet-close'); time.sleep(0.2)
    ctx.set_geolocation({'latitude': T['lat'][-1], 'longitude': T['lng'][-1], 'accuracy': 8}); time.sleep(2)
    if page.is_visible('#sheet'): shot(page, 5)
    b.close()

json.dump({'ride': route.get('name', SLUG), 'taken': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'screens': taken}, open(f'{out}/screens.json', 'w'), indent=1)
print(f'{len(taken)} of {len(SCREENS)} screenshots taken')
if len(taken) < 4: sys.exit(1)
