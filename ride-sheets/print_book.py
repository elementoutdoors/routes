"""Print ready flip books: one per brand. Cover plus one page per ride, each page A4 landscape with 3 mm bleed
(303 x 216 mm), 12 mm wire binding zone along the top edge. Also writes trim preview PNGs for checking."""
import os, sys, io
from PIL import Image, ImageDraw
from pypdf import PdfWriter
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rides import RIDES, ORDER_SHOP, ORDER_HINT
from paths import ASSETS, OUT as OUTROOT
import sheet
from sheet import THEMES, FONT, LOGO_BIKEON, LOGO_BEO, b64img, to_print

OUT = os.path.join(OUTROOT, 'print'); os.makedirs(OUT, exist_ok=True)
WARN = ("<b>Please don't record your ride.</b> Recording in the app drains your phone battery fast. Use it for navigation only, "
        "because we are unable to recover riders whose phone battery goes flat.")

BOOKS = {
    'bikeon': dict(file='Bike On Ride Maps Flip Book (print ready)', ids=ORDER_SHOP, theme='bikeon', logo=LOGO_BIKEON,
                   photo=os.path.join(ASSETS, 'cover-bikeon.jpg'), kick='Self guided rides from the shop', h1='Ride maps',
                   sub='Fourteen rides around Noosa, all starting and finishing at the shop',
                   foot='Every ride starts and finishes at the shop. Hire bikes back by 4pm.'),
    'beo': dict(file='By Earth and Ocean Hinterland Ride Maps Flip Book (print ready)', ids=ORDER_HINT, theme='beo', logo=LOGO_BEO,
                photo=os.path.join(ASSETS, 'cover-beo.jpg'), kick='Hinterland point to point rides', h1='Ride maps',
                sub='Gravel and mountain bike rides from the hinterland back to Noosa',
                foot='We drive you and your bike to the start, and you ride back to the shop. Hire bikes back by 4pm.'),
}


def group_of(rid):
    k = RIDES[rid]['kick'].replace('&middot;', '·')
    return k.split(' from the shop')[0].replace('Hinterland ', '').split(' ·')[0].capitalize()


def cover(book):
    T = THEMES[book['theme']]
    im = Image.open(book['photo']); im.thumbnail((3000, 3000)); photo = b64img(im, 88)
    groups = {}
    for n, rid in enumerate(book['ids'], 1):
        groups.setdefault(group_of(rid), []).append((n, rid))
    cols = ''
    for g, items in groups.items():
        rows = ''.join(f'<li><span class="n">{n}</span><span class="t">{RIDES[r]["title"]}</span>'
                       f'<span class="m">{RIDES[r]["stats"][0][0]} &middot; {RIDES[r]["stats"][3][0]}</span></li>' for n, r in items)
        two = len(items) > 5
        cols += f'<section class="grp{" wide" if two else ""}"><h2>{g}</h2><ul{" class=two" if two else ""}>{rows}</ul></section>'
    tab = ('.tab{top:15mm;right:13mm;padding:3.5mm 4mm 3mm}.logo{width:40mm}' if book['theme'] == 'bikeon'
           else '.tab{top:15mm;right:13mm;padding:3mm 3.5mm 3mm}.logo{width:30mm}')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{book['file']}</title><style>
@font-face{{font-family:"Montserrat";src:url(data:font/woff2;base64,{FONT}) format("woff2");font-weight:100 900}}
:root{{--brand:{T['brand']};--ink:{T['ink']};--paper:{T['paper']};--tint:{T['tint']};--grey:{T['grey']};--f:"Montserrat",Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0}}
@page{{size:303mm 216mm;margin:0}}
.sheet{{width:303mm;height:216mm;background:var(--paper);color:var(--ink);font-family:var(--f);position:relative;overflow:hidden;display:flex;flex-direction:column;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.hero{{position:relative;height:127mm;flex:none;overflow:hidden}}
.hero>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.tab{{position:absolute;background:var(--paper);border-radius:2.5mm;z-index:2}}.logo{{display:block;height:auto}}{tab}
.title{{position:absolute;left:13mm;bottom:7mm;color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.65),0 1px 3px rgba(0,0,0,.5)}}
.kick{{display:inline-block;margin:0 0 3mm;padding:2mm 3.6mm;border-radius:5mm;background:{T['kickbg']};color:{T['kickfg']};font:800 8.5pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;text-shadow:none}}
h1{{margin:0;font:900 48pt/0.95 var(--f);text-transform:uppercase}}
.title p{{margin:2.5mm 0 0;font:600 13pt/1.3 var(--f)}}
.body{{flex:1;padding:7mm 13mm 9mm;display:flex;flex-direction:column;gap:5mm;min-height:0}}
.cols{{display:flex;gap:7mm;flex-wrap:wrap}}
.grp{{flex:1 1 0;min-width:44mm}}.grp.wide{{flex:2 1 0}}ul.two{{grid-template-columns:1fr 1fr;column-gap:6mm}}
h2{{margin:0 0 2mm;font:800 7.5pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;color:var(--brand);padding-bottom:1.6mm;border-bottom:.4mm solid var(--brand)}}
ul{{list-style:none;margin:0;padding:0;display:grid;gap:1.6mm}}
li{{display:grid;grid-template-columns:5mm 1fr;column-gap:1.5mm;align-items:baseline}}
.n{{font:900 8pt/1 var(--f);color:var(--brand)}}
.t{{font:700 8.6pt/1.2 var(--f)}}
.m{{grid-column:2;font:500 6.8pt/1.2 var(--f);color:var(--grey)}}
.foot{{margin-top:auto;display:flex;gap:6mm;align-items:stretch}}
.foot p{{margin:0;font:500 7.6pt/1.4 var(--f)}}
.warn{{flex:1.4;display:flex;gap:3mm;align-items:center;border:.4mm solid var(--brand);border-radius:2mm;padding:2.6mm 3.4mm}}
.warn i{{flex:none;width:6.5mm;height:6.5mm;border-radius:50%;background:var(--brand);color:#fff;font:900 10pt/1 var(--f);font-style:normal;display:grid;place-items:center}}
.note{{flex:1;display:flex;align-items:center;background:var(--tint);border-radius:2mm;padding:2.6mm 3.4mm}}
.credit{{position:absolute;right:6mm;bottom:1.6mm;color:rgba(255,255,255,.8);font:500 4.6pt/1 var(--f)}}
</style></head><body><section class="sheet">
<div class="hero"><img src="{photo}" alt=""><div class="tab">{book['logo']}</div>
<div class="title"><p class="kick">{book['kick']}</p><h1>{book['h1']}</h1><p>{book['sub']}</p></div></div>
<div class="body"><div class="cols">{cols}</div>
<div class="foot"><div class="note"><p>{book['foot']} Each page has the codes to get the free Ride with GPS app and that ride's maps.</p></div>
<div class="warn"><i aria-hidden="true">!</i><p>{WARN}</p></div></div></div>
</section></body></html>'''


def preview(png_bytes, path):
    """Draw the trim (3 mm in) and the binding zone (12 mm below trim) for checking."""
    im = Image.open(io.BytesIO(png_bytes)).convert('RGB'); W, H = im.size; px = W / 303
    d = ImageDraw.Draw(im)
    b = 3 * px
    d.rectangle([b, b, W - b, H - b], outline=(255, 0, 255), width=4)
    d.line([b, b + 12 * px, W - b, b + 12 * px], fill=(0, 200, 255), width=4)
    d.rectangle([b + 5 * px, b + 5 * px, W - b - 5 * px, H - b - 5 * px], outline=(0, 255, 0), width=2)
    im.thumbnail((1800, 1800)); im.save(path, quality=85)


def make(key, only=None):
    from playwright.sync_api import sync_playwright
    book = BOOKS[key]
    os.makedirs(os.path.join(OUT, 'pages'), exist_ok=True)
    pages = []
    with sync_playwright() as pw:
        br = pw.chromium.launch(); pg = br.new_page(viewport={'width': 1200, 'height': 900}, device_scale_factor=2)
        cp = os.path.join(OUT, 'pages', f'{key}-00-cover.html'); open(cp, 'w').write(cover(book))
        items = [('00-cover', cp)]
        for n, rid in enumerate(book['ids'], 1):
            if only and rid not in only:
                continue
            items.append((f'{n:02d}-{RIDES[rid]["slug"]}', sheet.build(rid, True, f'{n} / {len(book["ids"])}')))
        for name, p in items:
            pg.goto('file://' + p); pg.wait_for_timeout(400)
            pg.emulate_media(media='print')
            pdf = os.path.join(OUT, 'pages', f'{key}-{name}.pdf')
            pg.pdf(path=pdf, width='303mm', height='216mm', print_background=True, prefer_css_page_size=True)
            pg.emulate_media(media='screen')
            preview(pg.locator('.sheet').screenshot(), os.path.join(OUT, 'pages', f'{key}-{name}-trim.jpg'))
            pages.append(pdf)
        br.close()
    w = PdfWriter()
    for p in pages:
        w.append(p)
    dest = os.path.join(OUT, book['file'] + '.pdf'); w.write(dest)
    print(dest, len(pages), 'pages', round(os.path.getsize(dest) / 2**20, 1), 'MB')
    return dest


if __name__ == '__main__':
    for k in sys.argv[1:]:
        make(k)
