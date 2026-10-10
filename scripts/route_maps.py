"""Map pictures of each route (the route line only, no icons) for the printed QR cards.
Usage: python3 scripts/route_maps.py   (after a build; reads qr/links.json and dist/r/*.json, writes qr/maps/<slug>.png)
Needs Playwright with Chromium. Map: OpenFreeMap (OpenStreetMap data)."""
import json, os, sys, time
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
links = json.load(open(f'{ROOT}/qr/links.json'))
os.makedirs(f'{ROOT}/qr/maps', exist_ok=True)
W, H, SCALE = 660, 350, 2.5   # matches the map box on the card (83 x 44 mm), about 500 dpi

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
<style>html,body,#m{margin:0;width:100%%;height:100%%}.maplibregl-ctrl-attrib{display:none}</style></head>
<body><div id="m"></div><script>
var R = %s, coords = R.track.lng.map(function (x, i) { return [x, R.track.lat[i]]; });
var b = new maplibregl.LngLatBounds(); coords.forEach(function (c) { b.extend(c); });
var map = new maplibregl.Map({ container: 'm', style: 'https://tiles.openfreemap.org/styles/liberty', interactive: false,
  bounds: b, fitBoundsOptions: { padding: 26, maxZoom: 15 }, preserveDrawingBuffer: true, attributionControl: false });
map.on('load', function () {
  map.addSource('r', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'LineString', coordinates: coords } } });
  map.addLayer({ id: 'c', type: 'line', source: 'r', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': '#ffffff', 'line-width': 7 } });
  map.addLayer({ id: 'l', type: 'line', source: 'r', layout: { 'line-join': 'round', 'line-cap': 'round' }, paint: { 'line-color': R.brand.colors.line, 'line-width': 4 } });
  map.once('idle', function () { window.__ready = true; });
});
</script></body></html>"""

only = sys.argv[1:]
with sync_playwright() as p:
    proxy = os.environ.get('HTTPS_PROXY')
    br = p.chromium.launch(proxy={'server': proxy} if proxy else None, args=['--ignore-certificate-errors', '--use-gl=swiftshader', '--enable-webgl'])
    ctx = br.new_context(viewport={'width': W, 'height': H}, device_scale_factor=SCALE, ignore_https_errors=True)
    for slug, link in links.items():
        if only and slug not in only: continue
        key = link.split('#', 1)[1]
        route = json.load(open(f'{ROOT}/dist/r/{key}.json'))
        page = ctx.new_page()
        page.set_content(PAGE % json.dumps({'track': route['track'], 'brand': route['brand']}))
        page.wait_for_function('window.__ready === true', timeout=60000)
        time.sleep(1.5)
        page.screenshot(path=f'{ROOT}/qr/maps/{slug}.png')
        page.close()
        print('map:', slug)
    br.close()
