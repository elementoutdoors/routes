"""Check every finished sheet: its QR code opens that ride in the Ride Guide, there are no other QR codes (no app store
or Ride with GPS codes), the route code is printed, and the words keep the house rules (no banned spellings, no dashes
between words). check(results) -> list of problems; python3 check.py <rid> ... checks sheets already made."""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import OUT
from rides import RIDES, R

BANNED = ['Mary Magic', 'Rock Pools', 'Mount Mothar', 'Mother Mountain', 'Wondum', 'ride time', 'Ride time', '\u2014', '\u2013',
          'shuttle bus', 'navigation unit', 'E-bike', 'ebike', 'e-bike ', 'ridewithgps', 'Ride with GPS', 'apps.apple.com', 'play.google.com']


def decode_all(img):
    import cv2
    det = cv2.QRCodeDetector()
    ok, vals, *_ = det.detectAndDecodeMulti(img)
    return [v for v in (vals if ok else []) if v]


def check_one(rid, png, html_path):
    import cv2
    probs = []
    img = cv2.imread(png)
    if img is None:
        return [f'{rid}: no sheet picture']
    h, w = img.shape[:2]
    crop = img[int(h * .6):, int(w * .8):]
    val, *_ = cv2.QRCodeDetector().detectAndDecode(crop)
    if val != R[rid]['link']:
        probs.append(f'{rid}: QR code does not open the ride ({"unreadable" if not val else "wrong link"})')
    others = [v for v in decode_all(img[:, :int(w * .78)]) if v]
    if others:
        probs.append(f'{rid}: extra QR code on the sheet')
    txt = re.sub(r'data:[^"\')]+', '', open(html_path).read())
    if R[rid]['code'] and R[rid]['code'] not in txt:
        probs.append(f'{rid}: route code missing')
    words = re.sub(r'<style>.*?</style>|<script>.*?</script>', '', txt, flags=re.S)
    hits = [b for b in BANNED if b in words]
    if hits:
        probs.append(f'{rid}: house style: ' + ', '.join(hits))
    return probs


def check(results):
    out = []
    for rid, r in results.items():
        out += check_one(rid, r['png'], os.path.join(OUT, RIDES[rid]['slug'], 'sheet.html'))
    return out


if __name__ == '__main__':
    from sheet import fname
    res = {rid: dict(png=os.path.join(OUT, 'final', fname(rid) + '.png')) for rid in sys.argv[1:]}
    p = check(res)
    print('\n'.join(p) or 'all good')
    sys.exit(1 if p else 0)
