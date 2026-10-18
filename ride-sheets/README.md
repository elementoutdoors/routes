# Ride sheets and rides booklet

One A4 landscape sheet per live self guided ride: a 3D map of the route with place names across the top, then a photo
of the ride, the ride story, numbers, elevation profile and the ride's Ride Guide QR code with its route code. Bike On
shop rides and By Earth and Ocean hinterland point to point rides. The same sheets make the combined booklet: for each
brand a cover listing its rides by kind with page numbers, then the sheets.

Made 4 to 7 October 2026 in the Branding Bob project, moved here on 18 October 2026. The same day it became the living
Ride Guide edition (Ben, 18/10/2026): it runs after every site build and keeps itself up to date from the Ride Guide.

## What changed from the October sheets

- A photo of the ride where the App Store and Google Play cards were. The app QR codes are gone.
- The scan panel carries the ride's Ride Guide QR code (its private link) and 6 character route code, never Ride with
  GPS. "For riders on this ride only. Please don't share this code." is printed under it.
- The ride story is the ride's current description in the Ride Guide data, so it follows Ride with GPS by itself.
- Distance, climbing and riding time come from the Ride Guide build every time. The time shown is the Ride Guide's
  riding time (it changes with the ride and the speed for its type), so the note says to allow extra for stops.
- The booklet covers no longer carry the "Please don't record your ride" warning: that was for the Ride with GPS app,
  and the Ride Guide does not record.
- No print ready flip books with bleed: the October flip books stay in OneDrive (Map Files\1 Print ready flip books).

## What it makes

| Output | Where | Who sees it |
| --- | --- | --- |
| Sheet per ride, PNG (3x) and A4 PDF | `qr/ride-sheets/final/` on the runner | Only locked: `ride-sheets/<slug>.enc.json` on the site |
| The booklet, both brands, covers and sheets | `qr/ride-sheets/Ride sheets booklet.pdf` on the runner | Only locked: `booklet.enc.json` on the site |
| 3D map per ride | `qr/booklet/maps/<slug>/map.jpg` | Kept in the Actions cache, never committed |
| Ride photos | `qr/booklet/photos/<slug>.jpg` | Kept in the Actions cache |
| What each sheet was built from, changelog | `qr/booklet/manifest.json` | Kept in the Actions cache, and the changelog goes inside `booklet.enc.json` |

The locked files use EO Crew's public key and the same envelope as `staff.enc.json` (`scripts/staff_bundle.mjs`): only
EO Crew's server can open them. Inside: `b64` (the PDF) and, for the booklet, `rides` (each ride's slug, title, brand,
kind, page and the date its sheet last changed), `photo_placeholders`, `maps_to_come` and the latest `changelog`.

## How it keeps itself up to date (`build.py`)

| Part of a sheet | Rule |
| --- | --- |
| 3D map | Drawn again only when the route line changes a lot: its length by more than 2 percent, or any part more than 100 m from the line the map was drawn from (a simplified copy is kept in the manifest). Also when the ride's map settings or title in `rides.py` change, or `MAP_VERSION` in `living.py` is bumped. Cue, stop and story edits, or a line nudged a few metres, keep the map. |
| Ride story | Always the ride's current Ride Guide description (a first line that only repeats the name is left out; at most two paragraphs, shortened a sentence at a time if it would not fit). House spellings are applied (e-Bike, Woondum, Mothar Mountain, no dashes between words). A new description is logged. |
| Distance, climbing, riding time | Always the latest. A change of 0.5 km or 25 m climbing is logged. |
| Photo | The featured image of the ride's Bike On website page (same slug or name, or `pages` in `config/booklet-photos.json`), else the ride's Ride with GPS highlighted photo, else a placeholder. `photos` in that file overrides any ride. Fetched again only when the choice or the website image changes. |
| QR and route code | Always the ride's current link and code. A change (after a `rev` bump) is logged. |
| Everything else | Title, category, sell line, highlights, level, surface, bike, note and map place names, from `rides.py`. |

The sheets and booklet are made again whenever anything on a sheet changes, or this folder's sheet code changes. A new
map draws within a time budget (20 minutes a run); any left wait for the next hourly run and show "3D map to come".
Every sheet is checked before anything is published (`check.py`): its QR code opens that ride, there is no other QR
code, the route code is printed and the words keep the house rules. A wrong QR code keeps the last good booklet.

## What to edit

| Change | File |
| --- | --- |
| A ride's title, sell line, highlights, level, surface, bike, note, category | `rides.py` (one block per ride). Levels follow the Product Truth. |
| The ride story | The ride's description in Ride with GPS. It reaches the sheet on the next build. |
| Place names on a map | `rides.py`: the ride's `labels` (curated pins, from the route's stops or a cited source), plus automatic names from the Queensland gazetteer (`places.json`); `skip` drops a gazetteer name that crowds a key pin |
| Camera angle for a ride | `rides.py`: `yaw` (0 looks north, 90 east, 270 west) and optionally `pitch`; otherwise chosen automatically |
| Mountain height | `rides.py` `ex`: 2 on every By Earth and Ocean map; shop maps scale with map size, capped at 3.2 (`mapgen.py`) |
| A ride's photo | `config/booklet-photos.json` |
| Colours, logos, fonts, layout | `sheet.py` (`THEMES`, CSS), `booklet.py` (covers), `assets/` |
| A new live ride | Nothing at first: it gets a sheet from the Ride Guide data alone (listed as `generic` in the manifest). Add its block to `rides.py` for its title, highlights, level and place names. |

## Run it locally

```
pip install playwright qrcode pillow numpy scipy requests pypdf opencv-python-headless && python3 -m playwright install chromium
node scripts/build.mjs --offline                 # the Ride Guide build (needs .secrets.json)
python3 ride-sheets/build.py                     # what changed; --force makes every sheet again, --redraw-maps every map
python3 ride-sheets/build.py --only 52202908     # just these rides (by Ride with GPS id), for trying things out
python3 ride-sheets/test_living.py               # the change rules
```

## How a 3D map is made

1. Camera (`mapgen.py`, `geo.py`): tries every heading and three tilts and keeps the one that shows the route
   largest, preferring a view looking north, then east.
2. Terrain: AWS Terrain Tiles, zoom 13 (12 for very large maps).
3. Imagery: Queensland Government aerial basemap at the sharpest zoom that fits an 8192 px texture (zoom 14 to 17).
   Open ocean is filled from Sentinel-2 cloudless 2016 by EOX (CC BY 4.0); never the 2018 and later layers
   (CC BY-NC-SA). Tiles are cached in `cache/` for the run.
4. Render (`render.html`, `shot.py`): Three.js 0.169 in headless Chromium. The route is one tube in one colour (Bike On
   #2F86E6, By Earth and Ocean #F5CA3A). Labels are placed so they never overlap each other, the title or the logo.
5. Credit on every map: "Imagery © State of Queensland (Queensland Spatial Imagery). Ocean: Sentinel-2 cloudless
   2016 by EOX (Copernicus Sentinel data 2016). Terrain: AWS Terrain Tiles. Height exaggerated." Keep it on any reuse.

No keys are needed: AWS Terrain Tiles, the Queensland imagery service and EOX are open. Route lines come only from the
Ride Guide build (`dist/r/*.json`) and are never committed, because the routes are a paid product and this repo is public.

## Ben's rules for these sheets

- The route is one clean line in a single colour. No fade over the map.
- Sharp imagery: the Queensland aerial photography, never 10 m satellite imagery.
- The time is the Ride Guide riding time, and the note says to allow extra for stops (18/10/2026; it was
  "Experience time" on the October sheets).
- The ride story follows the ride's description in the Ride Guide by itself (18/10/2026).
- Every sheet shows its category pill (Scenic, Beach, Mountain bike, Gravel, Road from the shop; Hinterland gravel or
  mountain bike, point to point).
- A good variety of place names. Named places are pinned from a source or the route's own stops, never guessed from
  the track (the Mothar Mountain rock pools, 4/10/2026).
- By Earth and Ocean mountains at 2 times height (4/10/2026).
- A photo of the ride and the Ride Guide QR code, no app codes (18/10/2026).
- No prices on printed material. No em dashes.
