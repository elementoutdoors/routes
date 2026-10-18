"""Where the ride sheet builder keeps things. Everything is relative to this folder, so it runs anywhere.

ASSETS  fonts and logos (committed)
CACHE   map tiles (never committed, safe to delete)
STATE   what the living build keeps between runs: the 3D maps, ride photos, manifest and the locked booklet
        (qr/booklet, kept in the Actions cache; never committed)
OUT     plain sheets and booklet, which carry the route codes (qr/ride-sheets; never published, committed or cached)
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                         # the routes repo (Ride Guide)
ASSETS = os.path.join(HERE, 'assets')
CACHE = os.environ.get('RIDE_SHEETS_CACHE') or os.path.join(HERE, 'cache')
STATE = os.environ.get('RIDE_SHEETS_STATE') or os.path.join(ROOT, 'qr', 'booklet')
OUT = os.environ.get('RIDE_SHEETS_OUT') or os.path.join(ROOT, 'qr', 'ride-sheets')
DIST = os.environ.get('RIDE_SHEETS_DIST') or os.path.join(ROOT, 'dist')
QR = os.environ.get('RIDE_SHEETS_QR') or os.path.join(ROOT, 'qr')
for d in (CACHE, STATE, OUT):
    os.makedirs(d, exist_ok=True)
