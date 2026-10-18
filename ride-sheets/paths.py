"""Where the ride sheet builder keeps things. Everything is relative to this folder, so it runs anywhere."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                      # the routes repo (Ride Guide)
ASSETS = os.path.join(HERE, 'assets')             # fonts, logos, cover photos (committed)
CACHE = os.path.join(HERE, 'cache')               # map tiles and the route export (never committed)
OUT = os.path.join(HERE, 'out')                   # every render and output (never committed)
for d in (CACHE, OUT):
    os.makedirs(d, exist_ok=True)
