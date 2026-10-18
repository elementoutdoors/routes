"""Build the A4 landscape ride sheet (HTML, PNG, PDF) for one ride from rides.py, the Ride Guide data and its 3D map.

Ride Guide edition (18/10/2026): where the App Store and Google Play cards were there is now a photo of the ride, and the
scan panel carries the ride's own Ride Guide QR code with its 6 character route code (never Ride with GPS). The ride
story, distance, climbing and riding time come from the Ride Guide build every time.
"""
import base64, io, json, math, os, re, sys
from html import escape as html_escape
import qrcode
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import ASSETS, ROOT, STATE, OUT
from rides import RIDES, R, story, clean_title
from textfit import h1pt

# Static Montserrat weights (Latin subset): PDFs embed these as small TrueType fonts, where the variable font
# becomes a much larger Type 3 font on every page. montserrat.woff2 (variable) stays for the map labels.
FONT_CSS = ''.join('@font-face{font-family:"Montserrat";src:url(data:font/ttf;base64,'
                   + base64.b64encode(open(os.path.join(ASSETS, f'montserrat-{w}.ttf'), 'rb').read()).decode()
                   + f') format("truetype");font-weight:{w};font-display:block}}' for w in (500, 600, 700, 800, 900))
IMG_Q = 82          # JPEG quality for the map and photo inside the sheets
MAP_MAX_W = 2400    # the map is at most this many pixels wide in a sheet (297 mm, about 205 dpi)
SCREEN_MAP_W = 1800  # the single sheets EO Crew shows on the iPad: a lighter map (about 155 dpi), same layout
MAP_BYTES = {MAP_MAX_W: 760_000, SCREEN_MAP_W: 430_000}   # most a map may weigh in each copy
PHOTO_BYTES = 110_000
PHOTO_ASPECT = 58 / 73   # the photo box under the map: 58 mm wide, about 73 mm tall


def _img_tag(path, cls, alt, box=380):   # the logos print at 30 to 40 mm wide: 380 px is about 250 dpi
    im = Image.open(path); im.thumbnail((box, box))
    b = io.BytesIO(); im.save(b, 'PNG', optimize=True)
    return f'<img class="{cls}" src="data:image/png;base64,{base64.b64encode(b.getvalue()).decode()}" alt="{alt}">'


def _first(*paths):
    return next(p for p in paths if os.path.exists(p))


# Logos: the original artwork if it is in assets/ (bikeon-logo.svg, beo-badge.png), otherwise the web versions.
if os.path.exists(os.path.join(ASSETS, 'bikeon-logo.svg')):
    _logo = open(os.path.join(ASSETS, 'bikeon-logo.svg')).read()
    LOGO_BIKEON = _logo[_logo.index('<svg'):].replace('<svg ', '<svg class="logo" role="img" aria-label="Bike On Bike Hire" ', 1)
else:
    LOGO_BIKEON = _img_tag(_first(os.path.join(ASSETS, 'bikeon-logo.png'), os.path.join(ROOT, 'site', 'assets', 'logo-bikeon.png')), 'logo', 'Bike On')
LOGO_BEO = _img_tag(_first(os.path.join(ASSETS, 'beo-badge.png'), os.path.join(ROOT, 'site', 'assets', 'logo-beo.png')), 'logo badge', 'By Earth and Ocean')

SITE = 'elementoutdoors.github.io/routes'
PRIVACY = "For riders on this ride only. Please don't share this code."

THEMES = {
    'bikeon': dict(brand='#0C5AA9', ink='#231F20', paper='#FFFFFF', tint='#EEF3FA', grey='#5B6168', kickbg='#0C5AA9', kickfg='#FFFFFF',
                   dot='#0C5AA9', code='#FFFFFF', prof='#0C5AA9', peak='#0C5AA9', axis='#C9D6E6', grid='#E3EAF3'),
    'beo': dict(brand='#182B3D', ink='#292929', paper='#FAF8F4', tint='#F3EEE9', grey='#5E6266', kickbg='#F5CA3A', kickfg='#182B3D',
                dot='#E26327', code='#F5CA3A', prof='#203B52', peak='#E26327', axis='#D9D2C8', grid='#E8E2D9'),
}


def cover_crop(im, aspect, h):
    """The middle of the picture at the shape of its box (width / height), h pixels tall: what object-fit cover shows."""
    w0, h0 = im.size
    if w0 / h0 > aspect:
        cw = round(h0 * aspect); im = im.crop(((w0 - cw) // 2, 0, (w0 - cw) // 2 + cw, h0))
    else:
        ch = round(w0 / aspect); im = im.crop((0, (h0 - ch) // 2, w0, (h0 - ch) // 2 + ch))
    if im.height > h:
        im = im.resize((round(h * aspect), h), Image.LANCZOS)
    return im


def b64img(im, q=86, max_w=None, max_bytes=None):
    """JPEG data URL. With max_bytes, the quality steps down from q (to 62), then the picture gets a little smaller, until
    it fits: a busy forest map compresses far less than a coastal one, and the sheet files must stay small."""
    im = im.convert('RGB')
    if max_w and im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    while True:
        b = io.BytesIO(); im.save(b, 'JPEG', quality=q, optimize=True, progressive=True)
        if not max_bytes or b.tell() <= max_bytes or im.width < 1000:
            break
        if q > 62:
            q -= 4
        else:   # very busy pictures (dense forest seen close up) still too heavy: a little smaller, a little better quality
            im = im.resize((round(im.width * .88), round(im.height * .88)), Image.LANCZOS); q = 72
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def qr(data, ink):
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0); q.add_data(data); q.make(fit=True)
    m = q.get_matrix(); n = len(m)
    d = ''.join(f'M{x},{y}h1v1h-1z' for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return f'<svg class="qr" viewBox="0 0 {n} {n}" shape-rendering="crispEdges"><path fill="{ink}" d="{d}"/></svg>'


def nice_step(total, n=4):
    for s in (1, 2, 5, 10, 20, 25, 50, 100):
        if total / s <= n:
            return s
    return 100


def riding_time(minutes):
    if not minutes:
        return ''
    h, m = divmod(int(round(minutes)), 60)
    return f'{m} min' if not h else f'{h} h {m} min'


def stats_for(rid):
    """Distance, climbing and riding time from the Ride Guide build; the rest as written in rides.py."""
    c, r = RIDES[rid], R[rid]
    live = [(f"{round(r['dist'] / 1000)} km", 'Distance'), (f"{round(r['gain'] / 10) * 10:,} m", 'Climbing'),
            (riding_time(r['riding_minutes']) or '-', 'Riding time')]
    out, k = [], 0
    for s in c['stats']:
        if s is None:
            out.append(live[k]); k += 1
        else:
            out.append(s)
            if s[1] == 'Terrain':
                k += 1   # a flat ride shows "Flat" where the climbing would be
    return out


def profile(rid, cfg, T):
    pts = R[rid]['pts']
    km = [p[3] / 1000 for p in pts]; es = [p[2] for p in pts]
    sm = [sum(es[max(0, i - 2):i + 3]) / len(es[max(0, i - 2):i + 3]) for i in range(len(es))]
    total = km[-1]
    emax_raw = max(sm)
    emax = max(100, math.ceil(emax_raw * 1.12 / 100) * 100)
    PW, PH = 300, 80
    X = lambda k: k / total * PW
    Y = lambda e: PH - max(0, e) / emax * PH
    pp = ' '.join(f'{X(k):.1f},{Y(e):.1f}' for k, e in zip(km, sm))
    gl = emax // 2 if emax <= 200 else (emax // 200) * 100
    step = nice_step(total)
    ticks = list(range(0, int(total) + 1, step))
    if total - ticks[-1] < step * 0.45:
        ticks = ticks[:-1]
    tick_svg = ''.join(f'<text x="{X(t):.1f}" y="{PH + 13}" text-anchor="{"start" if t == 0 else "middle"}" class="ax">{t} km</text>' for t in ticks)
    tick_svg += f'<text x="{PW}" y="{PH + 13}" text-anchor="end" class="ax">{round(total)} km</text>'
    pk = max(range(len(sm)), key=lambda i: sm[i])
    flat = emax_raw < 40
    label = cfg.get('peak') or f'High point, {round(es[pk] / 10) * 10} m'
    px, py = X(km[pk]), Y(sm[pk])
    anchor = 'end' if px > PW * 0.62 else 'start'
    lx = px - 6 if anchor == 'end' else px + 6
    peak = '' if flat else (f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{T["peak"]}" stroke="#fff" stroke-width="1.4"/>'
                            f'<text x="{lx:.1f}" y="{max(py - 3, -4):.1f}" text-anchor="{anchor}" class="lb">{label}</text>')
    return f'''<svg class="prof" viewBox="-30 -14 {PW + 40} {PH + 30}" aria-label="Elevation profile">
<line x1="0" y1="{PH}" x2="{PW}" y2="{PH}" stroke="{T['axis']}" stroke-width=".8"/>
<line x1="0" y1="{Y(gl):.1f}" x2="{PW}" y2="{Y(gl):.1f}" stroke="{T['grid']}" stroke-width=".8" stroke-dasharray="3 3"/>
<text x="-5" y="{Y(gl) + 3:.1f}" text-anchor="end" class="ax">{gl} m</text>
<text x="-5" y="{PH + 3}" text-anchor="end" class="ax">0 m</text>
<polygon points="0,{PH} {pp} {PW},{PH}" fill="{T['prof']}" fill-opacity=".16"/>
<polyline points="{pp}" fill="none" stroke="{T['prof']}" stroke-width="2" stroke-linejoin="round"/>
{peak}{tick_svg}
</svg>'''


def map_path(cfg):
    return os.path.join(STATE, 'maps', cfg['slug'], 'map.jpg')


def photo_path(cfg):
    return os.path.join(STATE, 'photos', cfg['slug'] + '.jpg')


def build(rid, story_limit=640, map_q=IMG_Q, map_w=MAP_MAX_W, photo_aspect=PHOTO_ASPECT):
    cfg = RIDES[rid]; T = THEMES[cfg['style']]; r = R[rid]
    out = os.path.join(OUT, cfg['slug']); os.makedirs(out, exist_ok=True)
    mp = map_path(cfg)
    MAP = (f'<img src="{b64img(Image.open(mp), map_q, map_w, MAP_BYTES.get(map_w))}" alt="3D map of the {cfg["title"]} route">' if os.path.exists(mp)
           else '<div class="nomap">3D map to come</div>')
    pp = photo_path(cfg)
    PHOTO = (f'<img src="{b64img(cover_crop(Image.open(pp), photo_aspect, 600), IMG_Q, None, PHOTO_BYTES)}" alt="Riding the {cfg["title"]}">' if os.path.exists(pp)
             else f'<div class="nophoto">{LOGO_BIKEON if cfg["brand"] == "bikeon" else LOGO_BEO}<span>Photo to come</span></div>')
    url, code = r['link'], r['code']
    logo = LOGO_BIKEON if cfg['brand'] == 'bikeon' else LOGO_BEO

    def sz(b):
        w = 22.4 / (len(b) * 0.229)
        return '' if ' ' in b or w >= 10.5 else f' style="font-size:{w:.1f}pt"'
    stats = ''.join(f'<div class="stat"><b{sz(b)}>{b}</b><span>{s}</span></div>' for b, s in stats_for(rid))
    hl = ''.join(f'<li>{h}</li>' for h in cfg['hl'])
    paras_list = story(r['desc'], [r['name'], cfg['title'], clean_title(r['name'])], story_limit)
    nb = lambda p: re.sub(r'(\d) (km|m|hrs|degree)', r'\1&nbsp;\2', html_escape(p))
    paras = ''.join('<p>' + nb(p) + '</p>' for p in paras_list)
    credit = ('Imagery &copy; State of Queensland (Queensland Spatial Imagery). Ocean: Sentinel-2 cloudless 2016 by EOX '
              '(Copernicus Sentinel data 2016). Terrain: AWS Terrain Tiles. Height exaggerated.')
    title = cfg['title']
    tabcss = ('.tab{top:0;right:10mm;padding:3.5mm 4mm 3mm}.logo{width:40mm}' if cfg['brand'] == 'bikeon'
              else '.tab{top:0;right:10mm;padding:3mm 3.5mm 3mm}.logo{width:30mm}')
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} Ride Map</title>
<style>
{FONT_CSS}
/* One A4 landscape ride sheet: 3D route map across the top, the ride story, numbers and scan code underneath. */
:root{{--brand:{T['brand']};--ink:{T['ink']};--paper:{T['paper']};--tint:{T['tint']};--grey:{T['grey']};--dot:{T['dot']};--desk:#D9DEE4;--shadow:rgba(20,30,45,.18);--f:"Montserrat",Arial,sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--desk:#16191D;--shadow:rgba(0,0,0,.55);color-scheme:dark}}}}
:root[data-theme="dark"]{{--desk:#16191D;--shadow:rgba(0,0,0,.55);color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--desk);color:var(--ink);font-family:var(--f);padding:24px 16px 48px}}
.desk{{display:flex;justify-content:center}}
.wrapS{{width:calc(297mm * var(--s,1));height:calc(210mm * var(--s,1));max-width:100%}}
.sheet{{width:297mm;height:210mm;background:var(--paper);transform:scale(var(--s,1));transform-origin:0 0;overflow:hidden;position:relative;display:flex;flex-direction:column;box-shadow:0 1px 2px var(--shadow),0 12px 36px var(--shadow)}}
.map{{position:relative;height:124mm;flex:none;overflow:hidden;background:var(--tint)}}
.map>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.nomap{{position:absolute;inset:0;display:grid;place-items:center;font:700 10pt/1 var(--f);color:var(--grey);letter-spacing:.08em;text-transform:uppercase}}
.tab{{position:absolute;background:var(--paper);border-radius:0 0 2.5mm 2.5mm;z-index:2}}
.logo{{display:block;height:auto}}
{tabcss}
.title{{position:absolute;left:10mm;bottom:5mm;z-index:2;color:#fff;max-width:200mm;text-shadow:0 2px 14px rgba(0,0,0,.65),0 1px 3px rgba(0,0,0,.5)}}
.title h1{{margin:0;font-weight:900;font-size:{h1pt(title)}pt;line-height:1;text-transform:uppercase;letter-spacing:-.005em}}
.title .kick{{display:inline-block;margin:0 0 2.5mm;padding:1.8mm 3.2mm;border-radius:5mm;background:{T['kickbg']};color:{T['kickfg']};font:800 7.5pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;text-shadow:none}}
.title p{{margin:2mm 0 0;font:600 11pt/1.3 var(--f)}}
.credit{{position:absolute;right:3mm;bottom:1.6mm;z-index:2;color:rgba(255,255,255,.85);text-shadow:0 1px 2px rgba(0,0,0,.8);font:500 4.6pt/1 var(--f)}}
.below{{flex:1;display:grid;grid-template-columns:58mm minmax(0,1fr) 86mm 40mm;gap:6mm;padding:6mm 10mm 7mm;min-height:0}}
.photo{{border-radius:2mm;overflow:hidden;background:var(--tint);min-height:0;position:relative}}
.photo>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:fill}}
.nophoto{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3mm;color:var(--grey);font:700 7pt/1 var(--f);letter-spacing:.08em;text-transform:uppercase}}
.nophoto .logo{{width:26mm;opacity:.75}}
.story{{display:flex;flex-direction:column;gap:2.4mm;min-width:0}}
.eyebrow{{font:800 7pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;color:var(--brand);margin:0}}
.story p{{margin:0;font:500 8.4pt/1.48 var(--f)}}
.story ul{{margin:0;padding:0;list-style:none;display:grid;grid-template-columns:1fr 1fr;gap:1.4mm 4mm}}
.story li{{font:600 7.6pt/1.3 var(--f);padding-left:3.4mm;position:relative}}
.story li::before{{content:"";position:absolute;left:0;top:1.1mm;width:1.6mm;height:1.6mm;border-radius:50%;background:var(--dot)}}
.nums{{display:flex;flex-direction:column;gap:3mm;min-width:0}}
.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:1.6mm}}
.stat{{background:var(--tint);border-radius:1.6mm;padding:2.2mm 2.4mm;min-width:0}}
.stat b{{display:block;font:900 10.5pt/1.05 var(--f);color:var(--ink);font-variant-numeric:tabular-nums}}
.stat span{{display:block;margin-top:1mm;font:700 5.8pt/1.1 var(--f);letter-spacing:.08em;text-transform:uppercase;color:var(--grey)}}
.note{{margin:-1mm 0 0;font:500 6.6pt/1.3 var(--f);color:var(--grey)}}
.prof{{width:100%;height:auto;display:block}}
.prof .ax{{font:600 7px var(--f);fill:#6B7480}}
.prof .lb{{font:800 8px var(--f);fill:var(--brand)}}
.scan{{background:var(--brand);color:#fff;border-radius:2.5mm;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.8mm;padding:3mm;text-align:center;text-decoration:none}}
.scan .t{{font:800 6.8pt/1.25 var(--f);text-transform:uppercase;letter-spacing:.04em}}
.qbox{{background:#fff;padding:2mm;border-radius:1.4mm}}
.qr{{width:24mm;height:24mm;display:block}}
.scan small{{font:500 6pt/1 var(--f);opacity:.85}}
.scan .code{{font:900 12pt/1 var(--f);letter-spacing:.14em;color:{T['code']}}}
.scan .site{{font:600 5.2pt/1.2 var(--f);opacity:.85}}
.scan .priv{{font:500 4.8pt/1.25 var(--f);opacity:.75}}
@page{{size:A4 landscape;margin:0}}
@media print{{body{{background:#fff;padding:0}}.wrapS{{width:297mm;height:210mm;max-width:none}}.sheet{{transform:none;box-shadow:none}}*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<main class="desk" id="desk"><div class="wrapS"><section class="sheet" aria-label="{title} ride map sheet">
  <div class="map">
    {MAP}
    <div class="tab">{logo}</div>
    <div class="title"><p class="kick">{cfg['kick']}</p><h1>{title}</h1><p>{cfg['sub']}</p></div>
    <span class="credit">{credit}</span>
  </div>
  <div class="below">
    <div class="photo">{PHOTO}</div>
    <div class="story">
      <p class="eyebrow">The ride</p>
      {paras}
      <ul>{hl}</ul>
    </div>
    <div class="nums">
      <div class="stats">{stats}</div>
      <p class="note">{cfg['note']}</p>
      {profile(rid, cfg, T)}
    </div>
    <a class="scan" href="{url}" target="_blank" rel="noopener"><span class="t">Scan to open<br>this ride</span><span class="qbox">{qr(url, '#231F20')}</span><small>or enter route code</small><span class="code">{code}</span><span class="site">at {SITE}</span><span class="priv">{PRIVACY}</span></a>
  </div>
</section></div></main>
<script>(function(){{var d=document.getElementById('desk');function f(){{var w=297*96/25.4;var s=Math.min(1,Math.min(d.clientWidth,1200)/w);document.documentElement.style.setProperty('--s',s.toFixed(4))}}f();addEventListener('resize',f)}})();</script>
</body></html>'''
    p = os.path.join(out, 'sheet.html')
    open(p, 'w').write(html)
    return p, paras_list


def fname(rid):
    c = RIDES[rid]
    t = c['title'].replace('&', 'and')
    t = t[:-5] if t.endswith(' Ride') else t
    if c['brand'] == 'beo':
        t += ' (Gravel)' if 'gravel' in c['kick'].lower() else ' (MTB)'
    return t + ' Ride Map'


CHECK_JS = '''()=>{const s=document.querySelector('.sheet').getBoundingClientRect();const bad=[];
  document.querySelectorAll('.below *').forEach(e=>{const r=e.getBoundingClientRect();if(r.bottom>s.bottom-2||r.right>s.right+0.5)bad.push(e.className||e.tagName)});
  const st=[...document.querySelectorAll('.stat b')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent);
  const h1=document.querySelector('.title h1');const t=document.querySelector('.title').getBoundingClientRect();
  return {overflow:bad.slice(0,5),stat:st,h1lines:Math.round(h1.getBoundingClientRect().height/parseFloat(getComputedStyle(h1).fontSize)),titleTop:Math.round(t.top-s.top)}}'''


def shoot(rids, launch_args=None):
    """Sheet PNG (3x), A4 PDF (for printing) and a lighter A4 PDF (for screens) per ride, in OUT/final. A ride story too long for its column is shortened a sentence
    at a time until it fits. Returns {rid: {png, pdf, check, story}}."""
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.join(OUT, 'final'), exist_ok=True)
    res = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=launch_args or [])
        pg = b.new_page(viewport={'width': 1200, 'height': 900}, device_scale_factor=3)
        for rid in rids:
            limit = 640
            while True:
                p, story_used = build(rid, limit)
                pg.goto('file://' + p); pg.wait_for_timeout(400)
                chk = pg.evaluate(CHECK_JS)
                if not chk['overflow'] or limit <= 240:
                    break
                limit -= 80
            # The photo box grows a little when the words beside it are long. Cut the photo to the box's exact shape, so
            # the PDF can carry the JPEG as it is (a photo cropped by the page is stored again, uncompressed, and is heavy).
            aspect = pg.evaluate("(()=>{const r=document.querySelector('.photo').getBoundingClientRect();return r.width/r.height})()")
            if abs(aspect - PHOTO_ASPECT) > 0.002:
                p, story_used = build(rid, limit, photo_aspect=aspect)
                pg.goto('file://' + p); pg.wait_for_timeout(400)
                chk = pg.evaluate(CHECK_JS)
            base = os.path.join(OUT, 'final', fname(rid))
            pg.locator('.sheet').screenshot(path=base + '.png')
            pg.emulate_media(media='print')
            pg.pdf(path=base + '.pdf', format='A4', landscape=True, print_background=True, prefer_css_page_size=True)
            # the lighter copy for the iPad: the same sheet with the map at SCREEN_MAP_W
            p, _ = build(rid, limit, map_w=SCREEN_MAP_W, photo_aspect=aspect)
            pg.goto('file://' + p); pg.wait_for_timeout(300)
            pg.pdf(path=base + ' (screen).pdf', format='A4', landscape=True, print_background=True, prefer_css_page_size=True)
            pg.emulate_media(media='screen')
            res[rid] = dict(png=base + '.png', pdf=base + '.pdf', pdf_screen=base + ' (screen).pdf', check=chk, story=story_used)
            print(rid, chk, flush=True)
        b.close()
    return res


if __name__ == '__main__':
    shoot(sys.argv[1:])
