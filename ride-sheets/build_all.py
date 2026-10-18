"""Build every ride map output in one go, in the right order, with the checks.

python3 build_all.py                      all 28 rides, everything
python3 build_all.py 52416633 55105004    only these rides (by Ride with GPS id); books and gallery still rebuilt whole
python3 build_all.py --skip-maps          reuse the 3D renders, rebuild sheets, books and exports (text or layout change)
python3 build_all.py --deliver "<folder>" also lay the files out as the OneDrive "Map Files" folder at <folder>

Steps: 3D maps (screen) > 3D maps (print, with bleed) > sheets (PNG, PDF) > checks > map JPEGs > print books > gallery
"""
import os, shutil, subprocess, sys
from paths import HERE, OUT

args = [a for a in sys.argv[1:]]
skip_maps = '--skip-maps' in args
deliver = None
if '--deliver' in args:
    deliver = args[args.index('--deliver') + 1]
ids = [a for a in args if a.isdigit()]

sys.path.insert(0, HERE)
from rides import ORDER_SHOP, ORDER_HINT
ALL = ORDER_SHOP + ORDER_HINT
ids = ids or ALL


def run(cmd, env=None):
    print('>>', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=HERE, env=dict(os.environ, **(env or {})))


if not skip_maps:
    run([sys.executable, 'mapgen.py'] + ids)
    run([sys.executable, 'mapgen.py'] + ids, env={'MODE': 'print'})
run([sys.executable, 'sheet.py'] + ids)
run([sys.executable, 'check.py'])          # exits non zero on a wrong QR code or banned spelling
run([sys.executable, 'maptops.py'])
run([sys.executable, 'print_book.py', 'bikeon', 'beo'])
run([sys.executable, 'gallery.py'])

if deliver:
    from sheet import fname
    from print_book import BOOKS
    sub = {'pdf': '2 Ride sheets PDF (A4, for screens and office printing)', 'jpg': '3 Ride sheets JPEG', 'map': '4 3D map JPEGs'}
    from PIL import Image
    for rid in ALL:
        brand = 'Bike On' if rid in ORDER_SHOP else 'By Earth and Ocean'
        f = fname(rid)
        for k in sub:
            os.makedirs(os.path.join(deliver, sub[k], brand), exist_ok=True)
        shutil.copy(os.path.join(OUT, 'final', f + '.pdf'), os.path.join(deliver, sub['pdf'], brand, f + '.pdf'))
        Image.open(os.path.join(OUT, 'final', f + '.png')).convert('RGB').save(
            os.path.join(deliver, sub['jpg'], brand, f + '.jpg'), quality=92, optimize=True)
        m = f.replace(' Ride Map', ' 3D Map') + '.jpg'
        shutil.copy(os.path.join(OUT, 'maptops', m), os.path.join(deliver, sub['map'], brand, m))
    pb = os.path.join(deliver, '1 Print ready flip books'); os.makedirs(pb, exist_ok=True)
    for b in BOOKS.values():
        shutil.copy(os.path.join(OUT, 'print', b['file'] + '.pdf'), pb)
    shutil.copy(os.path.join(HERE, 'Printer brief.txt'), pb)
    print('Delivered to', deliver)
