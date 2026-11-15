"""QR code images for the booking emails (Ben, 15/11/2026).

Every live ride's QR code as a PNG at dist/q/<name>.png, where name = first 24 hex of sha256("email-qr:" + customer link).
The customer link carries the route's secret key, so the file name can't be guessed and nothing here lists them.
Checkfront item email text (the "Your ride app" block, built in the Bike On project from the Ride Desk's routes/links)
points at these files. A ride's QR file changes only when its link does (a rev bump on the Ride Desk); the weekly
"Ride map packs" drift check confirms every emailed QR still loads and still matches the ride's current link.
Usage (in the build, after scripts/build.mjs has written qr/links.json): python3 scripts/email_qr.py"""
import hashlib, json, os, sys
import qrcode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
links = json.load(open(os.path.join(ROOT, 'qr', 'links.json')))
out = os.path.join(ROOT, 'dist', 'q')
os.makedirs(out, exist_ok=True)

def name(link):
    return hashlib.sha256(('email-qr:' + link).encode()).hexdigest()[:24]

n = 0
for slug, link in sorted(links.items()):
    q = qrcode.QRCode(border=2, box_size=8, error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(link); q.make(fit=True)
    q.make_image(fill_color='#073665', back_color='white').save(os.path.join(out, name(link) + '.png'))
    n += 1
print(f'Email QR codes: {n}')
