"""Checks: far from the start, route code entry, in-app viewer, save-to-phone sheet, offline reopen.
Usage: python3 scripts/test_extras.py <base_url> <route_key> <route_code> <outdir>"""
import os, sys, time
from playwright.sync_api import sync_playwright
base, key, code, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
STUB = """window.__said=[];Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{speak:function(u){window.__said.push(u.text)},cancel:function(){},getVoices:function(){return []},onvoiceschanged:null}});
Object.defineProperty(window,'SpeechSynthesisUtterance',{configurable:true,value:function(t){this.text=t}});"""
with sync_playwright() as p:
    proxy = os.environ.get('HTTPS_PROXY')
    b = p.chromium.launch(proxy={'server': proxy, 'bypass': '<-loopback>,localhost,127.0.0.1'} if proxy else None, args=['--ignore-certificate-errors'])
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, ignore_https_errors=True,
                        geolocation={'latitude': -27.47, 'longitude': 153.02, 'accuracy': 10}, permissions=['geolocation'])
    ctx.add_init_script(STUB)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    # 1. route code on the home page
    pg.goto(base); pg.wait_for_selector('body.view-home', timeout=20000)
    pg.fill('#code-input', 'zzzzzz'); pg.click('#code-form button'); time.sleep(1.5)
    print('bad code message:', pg.inner_text('#code-error'))
    pg.fill('#code-input', code.lower()[:3] + ' ' + code.lower()[3:]); pg.click('#code-form button')
    pg.wait_for_selector('body.view-route', timeout=20000); print('code opened route:', pg.inner_text('#route-name'))
    # wait for offline save
    for _ in range(60):
        if 'done' in (pg.get_attribute('#offline-note', 'class') or ''): break
        time.sleep(1)
    print('offline note:', pg.inner_text('#offline-text'))
    # 2. save to phone sheet
    pg.click('#keep-btn'); time.sleep(0.6); print('keep sheet url has key:', key in pg.url)
    pg.screenshot(path=f'{out}/keep.png'); pg.click('#sheet-close'); time.sleep(0.3); print('url scrubbed again:', key not in pg.url)
    # 3. far from the start (Brisbane)
    pg.click('#start-btn'); time.sleep(3)
    print('said:', pg.evaluate('window.__said'))
    print('cue card:', pg.inner_text('#cue-dist'), '|', pg.inner_text('#cue-text'))
    pg.screenshot(path=f'{out}/far.png')
    # 4. in-app viewer from a stop
    n = None; i = 0
    while True:
        pg.click('#b-stops'); time.sleep(0.4)
        items = pg.query_selector_all('#sheet-body .list-item')
        if i >= len(items): break
        items[i].click(); time.sleep(0.4); i += 1
        link = pg.query_selector('#sheet-body a.linkrow')
        if link and 'byearthandocean' in (link.get_attribute('href') or ''):
            link.click(); break
        pg.click('#sheet-close'); time.sleep(0.2)
    time.sleep(4)
    print('viewer open:', pg.is_visible('#viewer'), 'pages:', len(ctx.pages), 'still riding:', pg.evaluate("document.body.className"))
    pg.screenshot(path=f'{out}/viewer.png')
    pg.click('#viewer-back'); time.sleep(0.6); print('viewer closed:', not pg.is_visible('#viewer'), pg.evaluate("document.body.className"))
    pg.click('#end-btn'); time.sleep(0.5)
    # 5. offline: reopen the site with no network
    ctx.set_offline(True)
    pg2 = ctx.new_page(); pg2.on('pageerror', lambda e: errs.append('offline: ' + str(e)))
    pg2.goto(base); time.sleep(6)
    print('offline reopen view:', pg2.evaluate('document.body.className'), '|', pg2.inner_text('#route-name') if pg2.is_visible('#route-name') else '')
    pg2.screenshot(path=f'{out}/offline.png')
    print('errors:', errs)
    b.close()
