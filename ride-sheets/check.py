"""Check every finished sheet: its QR code opens that ride in the Ride Guide, there are no other QR codes (no app store
or Ride with GPS codes), the route code is printed, and the words keep the house rules (no banned spellings, no dashes
between words), and the elevation profile is not flat on a ride that climbs. check(results) -> {rid: [(blocking, problem)]}:
a blocking problem holds that sheet back and keeps its previous one. python3 check.py <rid> ... checks sheets already made."""
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


def read_qr(crop):
    """Read the scan panel's QR code. OpenCV's reader misses some codes at one size and reads them at another, so try
    a few sizes, with a white margin, and both of its readers."""
    import cv2
    readers = [cv2.QRCodeDetector()] + ([cv2.QRCodeDetectorAruco()] if hasattr(cv2, 'QRCodeDetectorAruco') else [])
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    for scale in (1.0, 0.5, 0.35, 0.7, 0.25):
        im = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale != 1.0 else gray
        _, bw = cv2.threshold(im, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        for cand in (im, bw):
            pad = cv2.copyMakeBorder(cand, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
            for rd in readers:
                try:
                    val, *_ = rd.detectAndDecode(pad)
                except Exception:
                    val = ''
                if val:
                    return val
    return ''


FLAT_CLIMB_M, FLAT_RANGE_M = 40, 10   # a ride that climbs more than this must show at least this much on its profile


def profile_range(rid):
    """Lowest and highest point of the elevation profile as the sheet plots it (the same smoothing as sheet.profile)."""
    es = [p[2] for p in R[rid]['pts']]
    sm = [sum(es[max(0, i - 2):i + 3]) / len(es[max(0, i - 2):i + 3]) for i in range(len(es))]
    return min(sm), max(sm)


def check_one(rid, png, html_path):
    """[(blocking, problem)] for one sheet. A blocking problem holds the sheet back and keeps the previous one."""
    import cv2
    probs = []
    img = cv2.imread(png)
    if img is None:
        return [(True, 'no sheet picture')]
    h, w = img.shape[:2]
    val = read_qr(img[int(h * .6):, int(w * .8):])
    if val != R[rid]['link']:
        probs.append((True, f'QR code does not open the ride ({"unreadable" if not val else "wrong link"})'))
    others = [v for v in decode_all(img[:, :int(w * .78)]) if v]
    if others:
        probs.append((True, 'extra QR code on the sheet'))
    txt = re.sub(r'data:[^"\')]+', '', open(html_path).read())
    if R[rid]['code'] and R[rid]['code'] not in txt:
        probs.append((True, 'route code missing'))
    lo, hi = profile_range(rid)
    gain = R[rid]['gain'] or 0
    print(f'profile {R[rid]["slug"]}: min {lo:.0f} m, max {hi:.0f} m, climbing {gain} m', flush=True)
    if gain > FLAT_CLIMB_M and hi - lo < FLAT_RANGE_M:
        probs.append((True, f'elevation profile is flat ({lo:.0f} to {hi:.0f} m) but the ride climbs {gain} m'))
    words = re.sub(r'<style>.*?</style>|<script>.*?</script>', '', txt, flags=re.S)
    hits = [b for b in BANNED if b in words]
    if hits:
        probs.append((False, 'house style: ' + ', '.join(hits)))
    return probs


def check(results):
    """{rid: [(blocking, problem)]} for every sheet that has a problem."""
    out = {}
    for rid, r in results.items():
        p = check_one(rid, r['png'], os.path.join(OUT, RIDES[rid]['slug'], 'sheet.html'))
        if p:
            out[rid] = p
    return out


if __name__ == '__main__':
    from sheet import fname
    res = {rid: dict(png=os.path.join(OUT, 'final', fname(rid) + '.png')) for rid in sys.argv[1:]}
    p = check(res)
    for rid, items in p.items():
        for blocking, msg in items:
            print(rid, 'HOLD' if blocking else 'note', msg)
    sys.exit(1 if p else 0)
