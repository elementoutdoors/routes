"""Render one map scene (<dir>/scene.json and sat.jpg, written by mapgen.py) to PNG in headless Chromium.
Serves a small folder (the page, its font and the scene) on a free local port, so nothing else needs to be running.
python3 shot.py <scene dir> <out.png>"""
import functools, http.server, json, os, socketserver, sys, tempfile, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
scene_dir, dest = os.path.abspath(sys.argv[1]), sys.argv[2]
D = json.load(open(os.path.join(scene_dir, 'scene.json')))

# three.js is fetched once into the tile cache, so the render itself needs no network
sys.path.insert(0, HERE)
from paths import CACHE
THREE = os.path.join(CACHE, 'three-0.169.0.module.js')
if not os.path.exists(THREE):
    import requests
    r = requests.get('https://cdn.jsdelivr.net/npm/three@0.169.0/build/three.module.js', timeout=60); r.raise_for_status()
    open(THREE + '.tmp', 'wb').write(r.content); os.replace(THREE + '.tmp', THREE)

web = tempfile.mkdtemp(prefix='ride-map-')
for name, target in (('render.html', os.path.join(HERE, 'render.html')), ('assets', os.path.join(HERE, 'assets')), ('scene', scene_dir),
                     ('three.module.js', THREE)):
    os.symlink(target, os.path.join(web, name))

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


Handler = functools.partial(Quiet, directory=web)
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-proxy-server'])
    pg = b.new_page(viewport={'width': D['rw'], 'height': D['rh']}, device_scale_factor=1.5)
    pg.on('pageerror', lambda e: print('err', e))
    pg.on('console', lambda m: print('console', m.text) if m.type in ('error', 'warning') else None)
    pg.on('response', lambda r: print('http', r.status, r.request.method, r.url[:120]) if r.status >= 400 else None)
    pg.goto(f'http://127.0.0.1:{port}/render.html?d=scene')
    pg.wait_for_function('window.DONE===true', timeout=300000)
    pg.wait_for_timeout(300)
    pg.locator('#wrap').screenshot(path=dest)
    print('placed', pg.evaluate('window.PLACED'))
    b.close()
srv.shutdown()
