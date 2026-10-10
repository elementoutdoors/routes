# Ride Guide

Public route pages for Element Outdoors self-guided tours. A customer scans a QR code, the route opens in their
phone's browser with the map, spoken and written directions, stops and partner offers. No app, no account.

## How it works

- Ride with GPS is the source of truth. The line, cues and stops are edited there, in the By Earth and Ocean
  organisation account, exactly as before.
- Every night (3:07am Brisbane), on every change here, and on demand, GitHub Actions runs `scripts/build.mjs`.
  It pulls each route in `config/routes.json` from Ride with GPS, adds the offers, brand and translations,
  and publishes the site to GitHub Pages.
- If Ride with GPS fails or returns broken data, the last good copy of that route stays live.
- Each route lives at a secret address. The QR code carries the key; the app removes it from the address bar,
  so a copied link does not open the route. Search engines are told not to index the site.
- Opening a route saves it to the phone, with the map around it, so it keeps working with no signal.
- Each route also has a 6-character route code (printed on its QR card). Typing it on the home page reopens the route,
  and "Save to my phone" shows the code and adds the route to the home screen.
- "More about this place" pages that allow it open inside the app with a Back to my ride bar, so the ride keeps running.
  The build checks every link each night to decide.

## Changing things

| Change | Where |
| --- | --- |
| Cue wording, stops, the route line | Ride with GPS. Live by the next morning, or run the workflow by hand. |
| Add or remove a route | `config/routes.json`, plus the route's Ride with GPS privacy code in the `ROUTE_SECRETS` secret |
| Partner offers | `config/offers.json` (set `validUntil` and it hides itself after that date) |
| When turns are announced, close-together turns, off-route sensitivity, stop pop-ups, screen defaults | The Ride Guide Settings page (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18). Saving it starts the "Ride Guide settings apply" scheduled task, which writes `config/settings.json` here. Every value is range-checked and falls back to its default. |
| Which brand each map uses (By Earth and Ocean or Bike On) | The Ride Guide Settings page; the task writes `brand` in `config/routes.json`. The map then shows that brand's logo and colours. |
| Brand colours, logos, phone numbers | `config/brands.json` and `site/assets/` (use the normal By Earth and Ocean header logo, not the reversed one) |
| Translations | `config/i18n/<lang>.json`. New or changed English text is listed in `i18n-missing.json` after a build and in `health.json`; the weekly drift check fills the gaps. Brief: `config/TRANSLATION_BRIEF.md` |
| A route's QR code needs replacing | Bump its `rev` in `config/routes.json`. The old code stops working. |

## Checks

- `dist/health.json` (published as `health.json`) lists every route, where its data came from, broken stops,
  untranslated text and offers that are not near any route.
- `scripts/check.mjs` runs from the Element Outdoors Drift Check Register each week: site rebuilt recently,
  every QR code opens its route, links and photos work, nothing untranslated.
- A failed nightly build emails the GitHub account owner.

## Local work

```
node scripts/build.mjs --offline   # build from cache/ instead of Ride with GPS
python3 scripts/test_app.py http://localhost:8765/ <route key> <outdir>   # simulated ride in a phone-sized browser
```
Secrets for local builds live in `.secrets.json` (never committed): `{ "keySalt": "...", "privacy": { "<rwgps id>": "<privacy code>" } }`.
