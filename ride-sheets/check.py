"""Check every final sheet: QR decodes to the right experience, banned spellings absent, no em dashes."""
import os, re, sys, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rides import RIDES, ORDER_SHOP, ORDER_HINT
from sheet import fname
from paths import OUT
HERE = os.path.dirname(os.path.abspath(__file__))
BANNED = ['Mary Magic', 'Rock Pools', 'Mount Mothar', 'Mother Mountain', 'Wondum', 'ride time', 'Ride time', '—', 'shuttle bus', 'navigation unit', 'E-bike', 'ebike', 'e-bike ']
det = cv2.QRCodeDetector()
bad = 0
for rid in ORDER_SHOP + ORDER_HINT:
    c = RIDES[rid]
    img = cv2.imread(os.path.join(OUT, 'final', fname(rid) + '.png'))
    h, w = img.shape[:2]
    crop = img[int(h * .6):, int(w * .8):]
    val, *_ = det.detectAndDecode(crop)
    ok = val == c['qr'][0]
    left = img[int(h * .6):, :int(w * .25)]
    hh = left.shape[0]
    apps = [det.detectAndDecode(left[:hh // 2])[0], det.detectAndDecode(left[hh // 2:])[0]]
    ok = ok and apps == ['https://apps.apple.com/au/app/id893687399', 'https://play.google.com/store/apps/details?id=com.ridewithgps.mobile']
    txt = open(os.path.join(OUT, c['slug'], 'sheet.html')).read()
    txt = re.sub(r'data:[^"\')]+', '', txt)
    hits = [b for b in BANNED if b in txt]
    if not ok or hits:
        bad += 1
    print(('OK ' if ok and not hits else 'BAD'), c['title'][:34].ljust(34), c['qr'][1], 'qr=' + ('match' if ok else repr((val, apps))), hits or '')
print('problems:', bad)
sys.exit(1 if bad else 0)
