"""Printable QR cards for every route (A4, four per page), each with a map of the route line on top.
Usage: python3 scripts/route_maps.py && python3 scripts/qr_cards.py"""
import json, os, glob, io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import HexColor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for w in ('500', '700', '900'):
    pdfmetrics.registerFont(TTFont('M' + w, f'{ROOT}/fonts/Montserrat-{w}.ttf'))
links = json.load(open(f'{ROOT}/qr/links.json'))
codes = json.load(open(f'{ROOT}/qr/codes.json'))
health = json.load(open(f'{ROOT}/dist/health.json'))
brands = json.load(open(f'{ROOT}/config/brands.json'))
cfg = {r['slug']: r for r in json.load(open(f'{ROOT}/config/routes.json'))['routes']}
routes = [r for r in health['routes'] if r['ok'] and r['slug'] in links]

W, H = A4
cw, ch = 95 * mm, 136 * mm
mx, my = (W - 2 * cw) / 2, (H - 2 * ch) / 2
PER = 4
c = canvas.Canvas(f'{ROOT}/qr/Ride Guide QR cards.pdf', pagesize=A4)
c.setTitle('Ride Guide QR cards')

def wrap(text, font, size, width):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= width: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

for n, r in enumerate(routes):
    if n and n % PER == 0: c.showPage()
    i = n % PER
    x, y = mx + (i % 2) * cw, H - my - (i // 2 + 1) * ch
    b = brands[cfg[r['slug']]['brand']]
    navy, line, accent = HexColor(b['colors']['primary']), HexColor(b['colors']['line']), HexColor(b['colors']['accent'])
    # cut guide
    c.setStrokeColor(HexColor('#D5DAE0')); c.setDash(2, 3); c.rect(x, y, cw, ch); c.setDash()
    pad = 6 * mm
    # header: brand logo on white, brand colour rule underneath
    logo = ImageReader(f"{ROOT}/site/{b['logo']}") if b.get('logo') else None
    hy = y + ch - pad - 13 * mm
    if logo:
        lw, lh = logo.getSize(); h = 12 * mm; w = lw * h / lh
        c.drawImage(logo, x + pad, hy, w, h, mask='auto')
    else:
        c.setFillColor(navy); c.setFont('M900', 10); c.drawString(x + pad, hy + 6 * mm, ' '.join(b['wordmark']))
    c.setFillColor(navy); c.setFont('M800' if False else 'M900', 7.5)
    c.drawRightString(x + cw - pad, hy + 4.5 * mm, 'SELF GUIDED RIDE')
    c.setFillColor(line); c.rect(x + pad, hy - 1.6 * mm, cw - 2 * pad, 0.9 * mm, stroke=0, fill=1)
    # map of the route line (made by scripts/route_maps.py)
    mw, mh = cw - 2 * pad, 44 * mm
    my_ = hy - 4 * mm - mh
    mp = f"{ROOT}/qr/maps/{r['slug']}.png"
    if os.path.exists(mp):
        c.saveState(); pth = c.beginPath(); pth.roundRect(x + pad, my_, mw, mh, 2.5 * mm); c.clipPath(pth, stroke=0, fill=0)
        c.drawImage(ImageReader(mp), x + pad, my_, mw, mh); c.restoreState()
        c.setStrokeColor(HexColor('#D5DAE0')); c.setLineWidth(0.6); c.roundRect(x + pad, my_, mw, mh, 2.5 * mm, stroke=1, fill=0)
        c.setFont('M500', 4.6); c.setFillColor(HexColor('#6B7178'))
        c.drawRightString(x + cw - pad, my_ - 2.4 * mm, 'Map: OpenFreeMap, data © OpenStreetMap contributors')
    else:
        print('no map picture for', r['slug'], '(run scripts/route_maps.py)')
    # QR
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1, box_size=10)
    q.add_data(links[r['slug']]); q.make(fit=True)
    img = q.make_image(fill_color=b['colors']['primary'], back_color='white').convert('RGB')
    buf = io.BytesIO(); img.save(buf, 'PNG'); buf.seek(0)
    qs = 46 * mm
    qy = my_ - 6 * mm - qs
    c.drawImage(ImageReader(buf), x + pad, qy, qs, qs)
    img.save(f"{ROOT}/qr/{r['slug']}.png")
    # text
    tx, tw = x + pad + qs + 4 * mm, cw - 2 * pad - qs - 4 * mm
    ty = qy + qs - 3 * mm
    c.setFillColor(HexColor(b['colors']['ink'])); c.setFont('M900', 11.5)
    name = r['name'].replace(' Self-Guided Tour', '').replace(' Self Guided Tour', '')
    for ln in wrap(name, 'M900', 11.5, tw):
        c.drawString(tx, ty, ln); ty -= 13.5
    c.setFont('M700', 9); c.setFillColor(line)
    c.drawString(tx, ty - 1, f"{r['distance'] / 1000:.1f} km"); ty -= 16
    paras = ['Scan with your phone camera to open the map and directions.',
             'Turn your sound up for spoken directions and keep the screen facing you on the handlebar mount.']
    floor = y + pad + 6 * mm   # keep clear of the route code bar
    fs = 7.6
    while fs > 6 and sum(len(wrap(pa, 'M500', fs, tw)) * fs * 1.29 + 3 for pa in paras) > ty - floor: fs -= 0.2
    c.setFont('M500', fs); c.setFillColor(HexColor('#3B3F45'))
    for para in paras:
        for ln in wrap(para, 'M500', fs, tw):
            c.drawString(tx, ty, ln); ty -= fs * 1.29
        ty -= 3
    # route code, for getting back in without the QR code
    c.setFillColor(HexColor(b['colors']['sand'])); c.roundRect(x + pad, y + pad - 3 * mm, cw - 2 * pad, 7 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor(b['colors']['ink'])); c.setFont('M500', 7)
    c.drawString(x + pad + 3 * mm, y + pad - 0.6 * mm, 'Route code')
    c.setFont('M900', 10); c.setFillColor(navy)
    c.drawString(x + pad + 18 * mm, y + pad - 0.8 * mm, ' '.join(codes[r['slug']]))
    c.setFont('M500', 6.4); c.setFillColor(HexColor('#3B3F45'))
    c.drawRightString(x + cw - pad - 3 * mm, y + pad - 0.6 * mm, 'elementoutdoors.github.io/routes')
    c.setFont('M700', 7.6); c.setFillColor(HexColor(b['colors']['ink']))
    c.drawString(x + pad + 1.5 * mm, qy - 3.6 * mm, 'Help: ' + b['phone'])
c.save()
print('cards:', len(routes))
