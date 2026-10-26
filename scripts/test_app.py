"""End to end check of the Ride Guide app in a phone-sized headless browser.
Usage: python3 scripts/test_app.py <base_url> <route_key> <outdir>
Simulates GPS along the route and records spoken text, screenshots and console errors."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

base, key, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
route = None

SPEECH_STUB = """
window.__said = [];
if (window.__LANG) {}

Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak: function(u){ window.__said.push((u.lang||'')+': '+u.text); }, cancel: function(){},
  getVoices: function(){ return [{lang:'en-AU',localService:true,name:'x'},{lang:'de-DE',localService:true,name:'y'},{lang:'ja-JP',localService:true,name:'z'}]; }, onvoiceschanged:null } });
Object.defineProperty(window, 'SpeechSynthesisUtterance', { configurable: true, value: function(t){ this.text=t; } });
"""

with sync_playwright() as p:
    proxy = os.environ.get('HTTPS_PROXY')
    b = p.chromium.launch(proxy={'server': proxy, 'bypass': '<-loopback>,localhost,127.0.0.1'} if proxy else None,
                          args=['--ignore-certificate-errors'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True,
                        geolocation={'latitude': -26.4078, 'longitude': 153.0434, 'accuracy': 10}, permissions=['geolocation'],
                        locale='en-AU', ignore_https_errors=True)
    ctx.add_init_script(SPEECH_STUB)
    lang = os.environ.get('TEST_LANG')
    if lang: ctx.add_init_script("try{localStorage.setItem('rg.settings', JSON.stringify({lang:'%s'}))}catch(e){}" % lang)
    page = ctx.new_page()
    errors = []
    page.on('console', lambda m: errors.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.goto(f'{base}#{key}')
    page.wait_for_selector('body.view-route', timeout=20000)
    time.sleep(6)
    print('URL after load:', page.url)
    page.screenshot(path=f'{out}/1-route.png')
    route = page.evaluate(f"fetch('r/{key}.json').then(r=>r.json())")
    # no offer card on the ride page since 16/10/2026: offers are opened from the Offers list while riding
    if page.is_visible('#route-offers .offer-strip'):
        page.click('#route-offers .offer-strip'); time.sleep(0.6)
        page.screenshot(path=f'{out}/2-offer.png')
        page.click('#sheet-close'); time.sleep(0.3)
    page.click('#start-btn'); time.sleep(1)
    if page.is_visible('text=I understand'): page.click('text=I understand')
    time.sleep(1)
    page.screenshot(path=f'{out}/3-ride-start.png')

    T = route['track']
    n = len(T['d'])
    shots = {int(n * 0.12): '4-ride-a', int(n * 0.45): '5-ride-b'}
    step = max(1, n // 160)
    for i in range(0, n, step):
        ctx.set_geolocation({'latitude': T['lat'][i], 'longitude': T['lng'][i], 'accuracy': 8})
        time.sleep(0.12)
        for k, name in shots.items():
            if abs(i - k) < step:
                if page.is_visible('#sheet'):
                    page.screenshot(path=f'{out}/{name}-sheet.png'); page.click('#sheet-close'); time.sleep(0.3)
                page.screenshot(path=f'{out}/{name}.png')
        if page.is_visible('#sheet') and i < n - 5:
            page.click('#sheet-close')
    # off route test
    for _ in range(4):
        ctx.set_geolocation({'latitude': T['lat'][n // 2] + 0.003, 'longitude': T['lng'][n // 2] + 0.003, 'accuracy': 8}); time.sleep(0.4)
        ctx.set_geolocation({'latitude': T['lat'][n // 2] + 0.0031, 'longitude': T['lng'][n // 2] + 0.003, 'accuracy': 8}); time.sleep(0.4)
    page.screenshot(path=f'{out}/5b-off-route.png')
    ctx.set_geolocation({'latitude': T['lat'][-1], 'longitude': T['lng'][-1], 'accuracy': 8})
    time.sleep(1.5)
    page.screenshot(path=f'{out}/6-finish.png')
    said = page.evaluate('window.__said')
    page.click('#sheet-close') if page.is_visible('#sheet') else None
    page.click('#btn-ride-settings'); time.sleep(0.5)
    page.screenshot(path=f'{out}/7-settings.png', full_page=False)
    print('SAID', len(said))
    for s in said[:40]: print('  ', s)
    print('  ...')
    for s in said[-12:]: print('  ', s)
    print('ERRORS', len(errors))
    for e in errors[:20]: print('  ', e)
    b.close()
