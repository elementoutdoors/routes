"""Printable QR cards for every route (A4, six per page). Usage: python3 scripts/qr_cards.py"""
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
cw, ch = 95 * mm, 88 * mm
mx, my = (W - 2 * cw) / 2, (H - 3 * ch) / 2
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
    if n and n % 6 == 0: c.showPage()
    i = n % 6
    x, y = mx + (i % 2) * cw, H - my - (i // 2 + 1) * ch
    b = brands[cfg[r['slug']]['brand']]
    navy, line, accent = HexColor(b['colors']['primary']), HexColor(b['colors']['line']), HexColor(b['colors']['accent'])
    # cut guide
    c.setStrokeColor(HexColor('#D5DAE0')); c.setDash(2, 3); c.rect(x, y, cw, ch); c.setDash()
    pad = 6 * mm
    # header band
    c.setFillColor(navy); c.rect(x + pad, y + ch - pad - 13 * mm, cw - 2 * pad, 13 * mm, stroke=0, fill=1)
    c.setFillColor(HexColor('#FFFFFF')); c.setFont('M900', 10)
    c.drawString(x + pad + 4 * mm, y + ch - pad - 5.6 * mm, b['wordmark'][0])
    c.setFillColor(line); c.drawString(x + pad + 4 * mm, y + ch - pad - 10.2 * mm, b['wordmark'][1])
    c.setFillColor(accent); c.setFont('M700', 7.5)
    c.drawRightString(x + cw - pad - 4 * mm, y + ch - pad - 7.8 * mm, 'SELF GUIDED RIDE')
    # QR
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=1, box_size=10)
    q.add_data(links[r['slug']]); q.make(fit=True)
    img = q.make_image(fill_color=b['colors']['primary'], back_color='white').convert('RGB')
    buf = io.BytesIO(); img.save(buf, 'PNG'); buf.seek(0)
    qs = 46 * mm
    c.drawImage(ImageReader(buf), x + pad, y + pad + 6 * mm, qs, qs)
    img.save(f"{ROOT}/qr/{r['slug']}.png")
    # text
    tx, tw = x + pad + qs + 4 * mm, cw - 2 * pad - qs - 4 * mm
    ty = y + ch - pad - 20 * mm
    c.setFillColor(HexColor(b['colors']['ink'])); c.setFont('M900', 11.5)
    name = r['name'].replace(' Self-Guided Tour', '').replace(' Self Guided Tour', '')
    for ln in wrap(name, 'M900', 11.5, tw):
        c.drawString(tx, ty, ln); ty -= 13.5
    c.setFont('M700', 9); c.setFillColor(line)
    c.drawString(tx, ty - 1, f"{r['distance'] / 1000:.1f} km"); ty -= 16
    c.setFont('M500', 7.6); c.setFillColor(HexColor('#3B3F45'))
    for para in ['Scan with your phone camera to open the map and directions.',
                 'Turn your sound up for spoken directions and keep the screen facing you on the handlebar mount.']:
        for ln in wrap(para, 'M500', 7.6, tw):
            c.drawString(tx, ty, ln); ty -= 9.8
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
    c.drawString(tx, y + pad + 7 * mm, 'Help: ' + b['phone'])
c.save()
print('cards:', len(routes))
