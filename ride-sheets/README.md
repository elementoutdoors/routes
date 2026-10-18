# Ride map sheets and flip books

One A4 landscape sheet per self guided ride: a 3D map of the route with place names across the top, and the ride
story, numbers, elevation profile and QR codes underneath. 14 Bike On shop rides and 14 By Earth and Ocean hinterland
point to point rides. The same sheets make the two print ready counter flip books.

Made 4 to 7 October 2026 in the Branding Bob project, moved here on 18 October 2026 so it lives next to the Ride Guide
and can be kept up to date from it.

## What it makes

| Output | Where (in `out/`, never committed) | OneDrive (Digital Assets\Canva - Graphics Files\Map Files) |
| --- | --- | --- |
| Sheet per ride, PNG and A4 PDF | `final/` | `2 Ride sheets PDF (A4, for screens and office printing)`, `3 Ride sheets JPEG` |
| 3D map band per ride (map, place names, title, logo, credit), JPEG 3372 x 1407 | `maptops/` | `4 3D map JPEGs` |
| Two flip books, cover plus 14 rides, 303 x 216 mm (A4 plus 3 mm bleed) | `print/` | `1 Print ready flip books` (with `Printer brief.txt`) |
| Gallery of every sheet (published as an artifact) | `gallery/` | |

Folders inside each OneDrive section: `Bike On` and `By Earth and Ocean`. File names: `<Ride> Ride Map` and
`<Ride> 3D Map`, with `(Gravel)` or `(MTB)` on the hinterland ones. A rebuild overwrites the same names.

## How to rebuild

```
cd ride-sheets
npm install                                   # three.js for the 3D renders (once)
pip install playwright qrcode pillow numpy scipy requests pypdf opencv-python-headless && python3 -m playwright install chromium
python3 build_all.py                          # everything, all 28 rides (about 40 minutes, mostly the 3D renders)
python3 build_all.py 52416633                 # one ride, by Ride with GPS id (books and gallery still rebuilt)
python3 build_all.py --skip-maps              # text or layout change only: reuse the 3D renders (a few minutes)
python3 build_all.py --deliver "<OneDrive>\Digital Assets\Canva - Graphics Files\Map Files"
```

`build_all.py` runs, in order: 3D maps (screen) > 3D maps (print, with bleed) > sheets > checks > map JPEGs >
print books > gallery, and stops if a check fails.

Route lines come from the Ride Guide build (`../dist/r/*.json`, after `node scripts/build.mjs`) when it is there,
otherwise from `cache/routes.json` (the October 2026 Ride with GPS export, kept off GitHub because the routes are a
paid product and this repo is public). See `routes_data.py`.

## What to edit

| Change | File |
| --- | --- |
| A ride's title, sell line, description, highlights, stats, note, category | `rides.py` (one block per ride). Stats and levels follow the Product Truth. |
| Place names on a map | `rides.py`: the ride's `labels` (curated pins, from the route's stops or a cited source), plus automatic names from the Queensland gazetteer (`places.json`); `skip` drops a gazetteer name that crowds a key pin |
| Camera angle for a ride | `rides.py`: `yaw` (0 looks north, 90 east, 270 west) and optionally `pitch`; otherwise chosen automatically |
| Mountain height | `rides.py` `ex`: 2 on every By Earth and Ocean map; shop maps scale with map size, capped at 3.2 (`mapgen.py`) |
| Colours, logos, fonts, layout | `sheet.py` (`THEMES`, CSS), `assets/` |
| Ride with GPS app links and ride map QR codes | `sheet.py` (`APPSTORE`, `PLAY`) and `rides.py` (`QR`); shared with the ride menu |
| Flip book covers, contents, battery warning | `print_book.py` |
| Printer spec | `Printer brief.txt` |

After any change: run `build_all.py` (with `--skip-maps` if no map changed), look at the gallery, then `--deliver` to
OneDrive. Then update the Branding Bob project doc `claude/bike-on-ride-map-sheets-2026-10-04.md` if a rule changed.

## How a sheet is made

1. Camera (`mapgen.py`, `geo.py`): tries every heading and three tilts and keeps the one that shows the route
   largest, preferring a view looking north, then east.
2. Terrain: AWS Terrain Tiles, zoom 13 (12 for very large maps).
3. Imagery: Queensland Government aerial basemap at the sharpest zoom that fits an 8192 px texture (zoom 14 to 17).
   Open ocean is filled from Sentinel-2 cloudless 2016 by EOX (CC BY 4.0); never the 2018 and later layers
   (CC BY-NC-SA). Tiles are cached in `cache/`.
4. Render (`render.html`, `shot.py`): Three.js in headless Chromium. The route is one tube in one colour (Bike On
   #2F86E6, By Earth and Ocean #F5CA3A). Labels are placed so they never overlap each other, the title or the logo.
5. Sheet (`sheet.py`): HTML at A4 landscape, rendered to PNG (3x) and PDF.
6. Print (`MODE=print python3 mapgen.py`, `print_book.py`): maps rendered at bleed size, the top 12 mm kept clear for
   wire binding, the logo tab dropped below it, page numbers added, and a trim preview written for checking.
7. Checks (`check.py`): all three QR codes on every sheet decode to the right links (App Store, Google Play, the
   ride's Ride with GPS experience), no banned spellings (Mary Magic, Rock Pools, Mount Mothar, Mother Mountain,
   Wondum, ride time) and no em dashes.
8. Credit on every map: "Imagery © State of Queensland (Queensland Spatial Imagery). Ocean: Sentinel-2 cloudless
   2016 by EOX (Copernicus Sentinel data 2016). Terrain: AWS Terrain Tiles. Height exaggerated." Keep it on any reuse.

## Ben's rules for these sheets

- The route is one clean line in a single colour. No fade over the map.
- Sharp imagery: the Queensland aerial photography, never 10 m satellite imagery.
- The time is "Experience time", never "Ride time", and the sheet says what it includes.
- Every sheet shows its category pill (Scenic, Beach, Mountain bike, Gravel, Road from the shop; Hinterland gravel or
  mountain bike, point to point).
- A good variety of place names. Named places are pinned from a source or the route's own stops, never guessed from
  the track (the Mothar Mountain rock pools, 4/10/2026).
- By Earth and Ocean mountains at 2 times height (4/10/2026).
- The app QR codes replaced the photos (7/10/2026): iPhone code on the left of its card, Android code on the right of
  its card, ride map code at the other end of the sheet as step 2.
- No prices on printed material. No em dashes.

## Next: the Ride Guide edition (planned 18/10/2026)

A second version of every sheet that follows the Ride Guide ride and keeps itself current:

- Where the App Store and Google Play cards are, a photo from the ride: the ride's Ride with GPS highlighted photo
  (`hero` in the Ride Guide build), falling back to its first stop photo, then the shortlist in `rides.py`.
- The QR code and code panel become the ride's Ride Guide QR (its secret link, `qr/links.json`) and 6 character
  route code (`qr/codes.json`), so a customer scans straight into the Ride Guide ride. No app needed.
- Numbers (distance, climbing, riding time) come from the Ride Guide build every time.
- The 3D map re-renders only when the route is notably rebuilt (the route line moves more than about 75 m anywhere,
  or the distance changes by more than 2 percent). Fingerprints of the line and the labels are kept with the renders.
- The words come from a ride card per ride in the Story Library, seeded from `rides.py`. When the ride's Ride with GPS
  description changes, the build flags the card as out of step and the weekly check rewrites it, the same way the
  ride stories work.
- Runs in GitHub Actions after the nightly build, with the route secrets. Because the QR codes carry the secret keys,
  the sheets are never published on the site or committed: they go out as a private workflow artifact and the
  bens-pc task copies them into OneDrive, with a Ben's Desk card naming any pages that changed and need reprinting.
- Added to the weekly route check in the Drift Check Register: every live ride has a sheet, and each sheet matches
  its route version and ride card.
