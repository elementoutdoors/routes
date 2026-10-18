"""Render one map scene (out/<slug>[/print]/scene.json) to PNG in headless Chromium.
Serves this folder on a free local port for the page, so nothing else needs to be running.
python3 shot.py out/<slug> out/<slug>/map.png"""
import functools, http.server, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
rel, dest = sys.argv[1], sys.argv[2]
D = json.load(open(os.path.join(HERE, rel, 'scene.json')))

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=HERE)
Handler.log_message = lambda *a, **k: None
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
port = srv.server_address[1]

with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    pg = b.new_page(viewport={'width': D['rw'], 'height': D['rh']}, device_scale_factor=1.5)
    pg.on('pageerror', lambda e: print('err', e))
    pg.on('console', lambda m: print('console', m.text) if m.type in ('error', 'warning') else None)
    pg.goto(f'http://127.0.0.1:{port}/render.html?d={rel}')
    pg.wait_for_function('window.DONE===true', timeout=300000)
    pg.wait_for_timeout(300)
    pg.locator('#wrap').screenshot(path=dest)
    print('placed', pg.evaluate('window.PLACED'))
    b.close()
srv.shutdown()
