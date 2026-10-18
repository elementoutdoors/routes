"""Build the A4 landscape ride sheet (HTML, PNG, PDF) for one ride from rides.py and its rendered map."""
import base64, io, json, math, os, sys
import qrcode
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
from paths import ASSETS, OUT
sys.path.insert(0, HERE)
from rides import RIDES, R

FONT = base64.b64encode(open(os.path.join(ASSETS, 'montserrat.woff2'), 'rb').read()).decode()
_logo = open(os.path.join(ASSETS, 'bikeon-logo.svg')).read()
LOGO_BIKEON = _logo[_logo.index('<svg'):].replace('<svg ', '<svg class="logo" role="img" aria-label="Bike On Bike Hire" ', 1)
_b = Image.open(os.path.join(ASSETS, 'beo-badge.png'))
_b.thumbnail((720, 720)); _bb = io.BytesIO(); _b.save(_bb, 'PNG', optimize=True)
LOGO_BEO = f'<img class="logo badge" src="data:image/png;base64,{base64.b64encode(_bb.getvalue()).decode()}" alt="By Earth and Ocean">'

APPSTORE = 'https://apps.apple.com/au/app/id893687399'
PLAY = 'https://play.google.com/store/apps/details?id=com.ridewithgps.mobile'

THEMES = {
    'bikeon': dict(brand='#0C5AA9', ink='#231F20', paper='#FFFFFF', tint='#EEF3FA', grey='#5B6168', kickbg='#0C5AA9', kickfg='#FFFFFF',
                   dot='#0C5AA9', code='#FFFFFF', prof='#0C5AA9', peak='#0C5AA9', axis='#C9D6E6', grid='#E3EAF3'),
    'beo': dict(brand='#182B3D', ink='#292929', paper='#FAF8F4', tint='#F3EEE9', grey='#5E6266', kickbg='#F5CA3A', kickfg='#182B3D',
                dot='#E26327', code='#F5CA3A', prof='#203B52', peak='#E26327', axis='#D9D2C8', grid='#E8E2D9'),
}


def h1pt(title):
    return round(min(30, 200 / (len(title) * 0.8 * 0.3528)), 1)


def b64img(im, q=86):
    b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=q, optimize=True)
    return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()


def photo(p, w=900):
    im = Image.open(p); im.thumbnail((w, w)); return b64img(im)


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


def build(rid, print_=False, page=None):
    cfg = RIDES[rid]; T = THEMES[cfg['style']]
    out = os.path.join(OUT, cfg['slug'])
    MAP = b64img(Image.open(os.path.join(out, 'print', 'map.png') if print_ else os.path.join(out, 'map.png')), 82 if print_ else 80)
    url, code, glabel = cfg['qr']
    logo = LOGO_BIKEON if cfg['brand'] == 'bikeon' else LOGO_BEO
    def sz(b):
        w = 22.4 / (len(b) * 0.229)
        return '' if ' ' in b or w >= 10.5 else f' style="font-size:{w:.1f}pt"'
    stats = ''.join(f'<div class="stat"><b{sz(b)}>{b}</b><span>{s}</span></div>' for b, s in cfg['stats'])
    hl = ''.join(f'<li>{h}</li>' for h in cfg['hl'])
    import re
    paras = ''.join(f'<p>{re.sub(r"(\d) (km|m|hrs|degree)", r"\1&nbsp;\2", p)}</p>' for p in cfg['paras'])
    credit = ('Imagery &copy; State of Queensland (Queensland Spatial Imagery). Ocean: Sentinel-2 cloudless 2016 by EOX '
              '(Copernicus Sentinel data 2016). Terrain: AWS Terrain Tiles. Height exaggerated.')
    title = cfg['title']
    alt = f'3D map of the {title} route'
    tabcss = ('.tab{top:0;right:10mm;padding:3.5mm 4mm 3mm}.logo{width:40mm}' if cfg['brand'] == 'bikeon'
              else '.tab{top:0;right:10mm;padding:3mm 3.5mm 3mm}.logo{width:30mm}')
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} Ride Map</title>
<style>
@font-face{{font-family:"Montserrat";src:url(data:font/woff2;base64,{FONT}) format("woff2");font-weight:100 900;font-display:block}}
/* One A4 landscape ride sheet: 3D route map across the top, the ride story, numbers and scan code underneath. */
:root{{--brand:{T['brand']};--ink:{T['ink']};--paper:{T['paper']};--tint:{T['tint']};--grey:{T['grey']};--dot:{T['dot']};--desk:#D9DEE4;--shadow:rgba(20,30,45,.18);--f:"Montserrat",Arial,sans-serif}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--desk:#16191D;--shadow:rgba(0,0,0,.55);color-scheme:dark}}}}
:root[data-theme="dark"]{{--desk:#16191D;--shadow:rgba(0,0,0,.55);color-scheme:dark}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--desk);color:var(--ink);font-family:var(--f);padding:24px 16px 48px}}
.desk{{display:flex;justify-content:center}}
.wrapS{{width:calc(297mm * var(--s,1));height:calc(210mm * var(--s,1));max-width:100%}}
.sheet{{width:297mm;height:210mm;background:var(--paper);transform:scale(var(--s,1));transform-origin:0 0;overflow:hidden;position:relative;display:flex;flex-direction:column;box-shadow:0 1px 2px var(--shadow),0 12px 36px var(--shadow)}}
.map{{position:relative;height:124mm;flex:none;overflow:hidden}}
.map>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.tab{{position:absolute;background:var(--paper);border-radius:0 0 2.5mm 2.5mm;z-index:2}}
.logo{{display:block;height:auto}}
{tabcss}
.title{{position:absolute;left:10mm;bottom:5mm;z-index:2;color:#fff;max-width:200mm;text-shadow:0 2px 14px rgba(0,0,0,.65),0 1px 3px rgba(0,0,0,.5)}}
.title h1{{margin:0;font-weight:900;font-size:{h1pt(title)}pt;line-height:1;text-transform:uppercase;letter-spacing:-.005em}}
.title .kick{{display:inline-block;margin:0 0 2.5mm;padding:1.8mm 3.2mm;border-radius:5mm;background:{T['kickbg']};color:{T['kickfg']};font:800 7.5pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;text-shadow:none}}
.title p{{margin:2mm 0 0;font:600 11pt/1.3 var(--f)}}
.credit{{position:absolute;right:3mm;bottom:1.6mm;z-index:2;color:rgba(255,255,255,.85);text-shadow:0 1px 2px rgba(0,0,0,.8);font:500 4.6pt/1 var(--f)}}
.below{{flex:1;display:grid;grid-template-columns:58mm minmax(0,1fr) 86mm 40mm;gap:6mm;padding:6mm 10mm 7mm;min-height:0}}
.apps{{display:flex;flex-direction:column;gap:2.4mm;min-height:0}}
.step{{display:flex;align-items:center;gap:2mm;font:800 7pt/1.25 var(--f);letter-spacing:.1em;text-transform:uppercase;color:var(--brand);margin:0}}
.step b{{display:inline-grid;place-items:center;width:4.2mm;height:4.2mm;border-radius:50%;background:var(--brand);color:#fff;font:900 7pt/1 var(--f);letter-spacing:0;flex:none}}
.app{{flex:1;display:flex;align-items:center;gap:3mm;background:var(--tint);border-radius:2mm;padding:2.2mm;text-decoration:none;color:var(--ink);min-height:0}}
.app.right{{flex-direction:row-reverse;text-align:right}}
.app .qbox{{background:#fff;padding:1.6mm;border-radius:1.2mm;flex:none}}
.app .qr{{width:21mm;height:21mm}}
.app .os{{display:block;font:900 12pt/1 var(--f);color:var(--brand)}}
.app .st{{display:block;margin-top:1.2mm;font:700 7pt/1.2 var(--f)}}
.app .hint{{display:block;margin-top:1mm;font:500 6pt/1.25 var(--f);color:var(--grey)}}
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
.scan .sn{{display:grid;place-items:center;width:4.6mm;height:4.6mm;margin:0 auto 1.4mm;border-radius:50%;background:#fff;color:var(--brand);font:900 7.5pt/1 var(--f)}}
.scan small{{font:500 6pt/1 var(--f);opacity:.85}}
.scan .code{{font:900 12pt/1 var(--f);letter-spacing:.14em;color:{T['code']}}}
@page{{size:A4 landscape;margin:0}}
@media print{{body{{background:#fff;padding:0}}.wrapS{{width:297mm;height:210mm;max-width:none}}.sheet{{transform:none;box-shadow:none}}*{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<main class="desk" id="desk"><div class="wrapS"><section class="sheet" aria-label="{title} ride map sheet">
  <div class="map">
    <img src="{MAP}" alt="{alt}">
    <div class="tab">{logo}</div>
    <div class="title"><p class="kick">{cfg['kick']}</p><h1>{title}</h1><p>{cfg['sub']}</p></div>
    <span class="credit">{credit}</span>
  </div>
  <div class="below">
    <div class="apps">
      <p class="step"><b>1</b><span>Get the free<br>Ride with GPS app</span></p>
      <a class="app" href="{APPSTORE}" target="_blank" rel="noopener"><span class="qbox">{qr(APPSTORE, '#231F20')}</span><span><span class="os">iPhone</span><span class="st">App Store</span><span class="hint">Scan this code with your iPhone camera</span></span></a>
      <a class="app right" href="{PLAY}" target="_blank" rel="noopener"><span class="qbox">{qr(PLAY, '#231F20')}</span><span><span class="os">Android</span><span class="st">Google Play</span><span class="hint">Scan this code with your Android camera</span></span></a>
    </div>
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
    <a class="scan" href="{url}" target="_blank" rel="noopener"><span class="t"><span class="sn">2</span>Scan for the<br>{glabel} maps</span><span class="qbox">{qr(url, '#231F20')}</span><small>or enter code</small><span class="code">{code}</span></a>
  </div>
</section></div></main>
<script>(function(){{var d=document.getElementById('desk');function f(){{var w=297*96/25.4;var s=Math.min(1,Math.min(d.clientWidth,1200)/w);document.documentElement.style.setProperty('--s',s.toFixed(4))}}f();addEventListener('resize',f)}})();</script>
</body></html>'''
    if print_:
        html = to_print(html, page)
        p = os.path.join(out, 'print', 'sheet.html')
    else:
        p = os.path.join(out, 'sheet.html')
    open(p, 'w').write(html)
    return p


PRINT_CSS = ('.tab{top:15mm;right:13mm;border-radius:2.5mm}.title{left:13mm}.credit{right:6mm}'
             '.below{padding:6mm 13mm 10mm}'
             '.pg{position:absolute;right:13mm;bottom:4.5mm;font:600 6.5pt/1 var(--f);color:var(--grey);letter-spacing:.04em}')


def to_print(html, page=None):
    """Print master: A4 landscape plus 3 mm bleed (303 x 216 mm). 12 mm wire binding zone along the top edge
    kept clear of text and logos; everything else at least 5 mm inside the trim."""
    reps = [('width:calc(297mm * var(--s,1));height:calc(210mm * var(--s,1))', 'width:calc(303mm * var(--s,1));height:calc(216mm * var(--s,1))'),
            ('.sheet{width:297mm;height:210mm;', '.sheet{width:303mm;height:216mm;'),
            ('.map{position:relative;height:124mm;', '.map{position:relative;height:127mm;'),
            ('@page{size:A4 landscape;margin:0}', '@page{size:303mm 216mm;margin:0}'),
            ('.wrapS{width:297mm;height:210mm;max-width:none}', '.wrapS{width:303mm;height:216mm;max-width:none}'),
            ('var w=297*96/25.4', 'var w=303*96/25.4')]
    for a, b in reps:
        assert a in html, a
        html = html.replace(a, b)
    html = html.replace('</style>', PRINT_CSS + '</style>', 1)
    if page:
        html = html.replace('</section></div></main>', f'<span class="pg">{page}</span></section></div></main>', 1)
    return html


def fname(rid):
    c = RIDES[rid]
    t = c['title'].replace('&', 'and')
    t = t[:-5] if t.endswith(' Ride') else t
    if c['brand'] == 'beo':
        t += ' (Gravel)' if 'gravel' in c['kick'].lower() else ' (MTB)'
    return t + ' Ride Map'


def shoot(rids):
    from playwright.sync_api import sync_playwright
    os.makedirs(os.path.join(OUT, 'final'), exist_ok=True)
    res = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1200, 'height': 900}, device_scale_factor=3)
        for rid in rids:
            p = build(rid)
            pg.goto('file://' + p); pg.wait_for_timeout(400)
            chk = pg.evaluate('''()=>{const s=document.querySelector('.sheet').getBoundingClientRect();const bad=[];
              document.querySelectorAll('.below *').forEach(e=>{const r=e.getBoundingClientRect();if(r.bottom>s.bottom-2||r.right>s.right+0.5)bad.push(e.className||e.tagName)});
              const st=[...document.querySelectorAll('.stat b')].filter(e=>e.scrollWidth>e.clientWidth+1).map(e=>e.textContent);
              const h1=document.querySelector('.title h1');const t=document.querySelector('.title').getBoundingClientRect();
              return {overflow:bad.slice(0,5),stat:st,h1lines:Math.round(h1.getBoundingClientRect().height/parseFloat(getComputedStyle(h1).fontSize)),titleTop:Math.round(t.top-s.top)}}''')
            base = os.path.join(OUT, 'final', fname(rid))
            pg.locator('.sheet').screenshot(path=base + '.png')
            pg.emulate_media(media='print')
            pg.pdf(path=base + '.pdf', format='A4', landscape=True, print_background=True, prefer_css_page_size=True)
            pg.emulate_media(media='screen')
            res[rid] = chk
            print(rid, chk, flush=True)
        b.close()
    return res


if __name__ == '__main__':
    shoot(sys.argv[1:])
