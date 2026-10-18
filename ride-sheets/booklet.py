"""The combined rides booklet: for each brand a cover with the rides grouped by kind and their page numbers, then that
brand's ride sheets. A4 landscape, the same size as the sheets. Adapted from the Branding Bob flip books (print_book.py);
the "Please don't record your ride" warning is gone because the Ride Guide does not record (Ben, 18/10/2026).
make(sheets, path) -> (pages, {rid: page})"""
import base64, io, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import ASSETS, OUT
from rides import RIDES, ORDER_SHOP, ORDER_HINT
from sheet import THEMES, FONT, LOGO_BIKEON, LOGO_BEO, b64img, stats_for, photo_path, map_path

NUM = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen',
       'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen', 'Twenty']
BOOKS = {
    'bikeon': dict(ids=lambda: ORDER_SHOP, theme='bikeon', logo=LOGO_BIKEON, photo='cover-bikeon.jpg', kick='Self guided rides from the shop',
                   h1='Ride maps', sub=lambda n: f'{NUM[n] if n < len(NUM) else n} rides around Noosa from the shop',
                   foot='Every ride starts at the shop. Hire bikes back by 4pm.'),
    'beo': dict(ids=lambda: ORDER_HINT, theme='beo', logo=LOGO_BEO, photo='cover-beo.jpg', kick='Hinterland point to point rides',
                h1='Ride maps', sub=lambda n: 'Gravel and mountain bike rides from the hinterland back to Noosa',
                foot='We drive you and your bike to the start, and you ride back to the shop. Hire bikes back by 4pm.'),
}


def group_of(rid):
    k = RIDES[rid]['kick'].replace('&middot;', '·')
    return k.split(' from the shop')[0].replace('Hinterland ', '').split(' ·')[0].capitalize()


def ordered(key):
    """The brand's rides grouped by kind, in the order the kinds first appear."""
    ids = BOOKS[key]['ids']()
    groups = []
    for rid in ids:
        if group_of(rid) not in groups:
            groups.append(group_of(rid))
    return sorted(ids, key=lambda r: (groups.index(group_of(r)), ids.index(r)))


def cover_photo(key, ids):
    p = os.path.join(ASSETS, BOOKS[key]['photo'])
    if os.path.exists(p):
        return p
    for rid in ids:
        for q in (photo_path(RIDES[rid]), map_path(RIDES[rid])):
            if os.path.exists(q):
                return q
    return None


def cover(key, page_of):
    book = BOOKS[key]; T = THEMES[book['theme']]
    ids = [r for r in ordered(key) if r in page_of]
    pp = cover_photo(key, ids)
    photo = f'<img src="{b64img(Image.open(pp), 86, 3000)}" alt="">' if pp else ''
    groups = {}
    for rid in ids:
        groups.setdefault(group_of(rid), []).append(rid)
    cols = ''
    for g, items in groups.items():
        rows = ''.join(f'<li><span class="n">{page_of[r]}</span><span class="t">{RIDES[r]["title"]}</span>'
                       f'<span class="m">{stats_for(r)[0][0]} &middot; {next((b for b, s in stats_for(r) if s == "Level"), stats_for(r)[2][0])}</span></li>' for r in items)
        two = len(items) > 5
        cols += f'<section class="grp{" wide" if two else ""}"><h2>{g}</h2><ul{" class=two" if two else ""}>{rows}</ul></section>'
    tab = ('.tab{top:0;right:10mm;padding:3.5mm 4mm 3mm}.logo{width:40mm}' if book['theme'] == 'bikeon'
           else '.tab{top:0;right:10mm;padding:3mm 3.5mm 3mm}.logo{width:30mm}')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{book['h1']}</title><style>
@font-face{{font-family:"Montserrat";src:url(data:font/woff2;base64,{FONT}) format("woff2");font-weight:100 900}}
:root{{--brand:{T['brand']};--ink:{T['ink']};--paper:{T['paper']};--tint:{T['tint']};--grey:{T['grey']};--f:"Montserrat",Arial,sans-serif}}
*{{box-sizing:border-box}}body{{margin:0}}
@page{{size:A4 landscape;margin:0}}
.sheet{{width:297mm;height:210mm;background:var(--paper);color:var(--ink);font-family:var(--f);position:relative;overflow:hidden;display:flex;flex-direction:column;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
.hero{{position:relative;height:124mm;flex:none;overflow:hidden;background:var(--tint)}}
.hero>img{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}}
.tab{{position:absolute;background:var(--paper);border-radius:0 0 2.5mm 2.5mm;z-index:2}}.logo{{display:block;height:auto}}{tab}
.title{{position:absolute;left:10mm;bottom:7mm;color:#fff;text-shadow:0 2px 14px rgba(0,0,0,.65),0 1px 3px rgba(0,0,0,.5)}}
.kick{{display:inline-block;margin:0 0 3mm;padding:2mm 3.6mm;border-radius:5mm;background:{T['kickbg']};color:{T['kickfg']};font:800 8.5pt/1 var(--f);letter-spacing:.14em;text-transform:uppercase;text-shadow:none}}
h1{{margin:0;font:900 48pt/0.95 var(--f);text-transform:uppercase}}
.title p{{margin:2.5mm 0 0;font:600 13pt/1.3 var(--f)}}
.body{{flex:1;padding:7mm 10mm 9mm;display:flex;flex-direction:column;gap:5mm;min-height:0}}
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
.note{{flex:1;display:flex;align-items:center;background:var(--tint);border-radius:2mm;padding:2.6mm 3.4mm}}
.priv{{flex:none;display:flex;align-items:center;border:.4mm solid var(--brand);border-radius:2mm;padding:2.6mm 3.4mm}}
</style></head><body><section class="sheet">
<div class="hero">{photo}<div class="tab">{book['logo']}</div>
<div class="title"><p class="kick">{book['kick']}</p><h1>{book['h1']}</h1><p>{book['sub'](len(ids))}</p></div></div>
<div class="body"><div class="cols">{cols}</div>
<div class="foot"><div class="note"><p>{book['foot']} Each page has the QR code and route code that open that ride in the Ride Guide. The numbers are the page numbers.</p></div>
<div class="priv"><p>For staff and riders on these rides only. Please don't share the codes.</p></div></div></div>
</section></body></html>'''


def make(sheets, path, launch_args=None):
    """sheets: {rid: pdf path}. Writes the combined booklet to path."""
    from playwright.sync_api import sync_playwright
    from pypdf import PdfWriter
    plan, page = [], 1
    page_of = {}
    for key in ('bikeon', 'beo'):
        ids = [r for r in ordered(key) if r in sheets]
        if not ids:
            continue
        plan.append((key, ids)); page += 1
        for rid in ids:
            page_of[rid] = page; page += 1
    os.makedirs(os.path.join(OUT, 'covers'), exist_ok=True)
    w = PdfWriter()
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=launch_args or [])
        pg = b.new_page(viewport={'width': 1200, 'height': 900})
        for key, ids in plan:
            cp = os.path.join(OUT, 'covers', f'{key}.html')
            open(cp, 'w').write(cover(key, page_of))
            pg.goto('file://' + cp); pg.wait_for_timeout(300)
            cpdf = os.path.join(OUT, 'covers', f'{key}.pdf')
            pg.pdf(path=cpdf, format='A4', landscape=True, print_background=True, prefer_css_page_size=True)
            pg.locator('.sheet').screenshot(path=os.path.join(OUT, 'covers', f'{key}.png'))
            w.append(cpdf)
            for rid in ids:
                w.append(sheets[rid])
        b.close()
    w.add_metadata({'/Title': 'Bike On and By Earth and Ocean ride sheets', '/Author': 'Element Outdoors',
                    '/Subject': "For staff and riders on these rides only. Please don't share the codes."})
    with open(path, 'wb') as f:
        w.write(f)
    return page - 1, page_of
