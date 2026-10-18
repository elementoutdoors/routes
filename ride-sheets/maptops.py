"""Export the top map band of every sheet (map, labels, title, logo, credit) as a JPEG."""
import os, sys, io
from PIL import Image
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rides import RIDES, ORDER_SHOP, ORDER_HINT
from sheet import fname
from paths import OUT as OUTROOT
OUT = os.path.join(OUTROOT, 'maptops'); os.makedirs(OUT, exist_ok=True)
with sync_playwright() as pw:
    b = pw.chromium.launch(); pg = b.new_page(viewport={'width': 1200, 'height': 900}, device_scale_factor=3)
    for rid in ORDER_SHOP + ORDER_HINT:
        c = RIDES[rid]
        pg.goto('file://' + os.path.join(OUTROOT, c['slug'], 'sheet.html')); pg.wait_for_timeout(400)
        png = pg.locator('.map').screenshot()
        im = Image.open(io.BytesIO(png)).convert('RGB')
        name = fname(rid).replace(' Ride Map', ' 3D Map') + '.jpg'
        im.save(os.path.join(OUT, name), quality=90, optimize=True, progressive=True)
        print(name, im.size, os.path.getsize(os.path.join(OUT, name)) // 1024, 'KB')
    b.close()
