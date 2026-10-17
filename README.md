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
- A stop that links to a place on the ride story blogs (Bike On and By Earth and Ocean) has a "Hear the full story" button:
  about a minute on that place, written to be heard (`config/stories.json`), in the natural voice. Directions and the next
  stop cut in over it. The nightly build fingerprints each blog section and reports any story that is out of step in
  `health.json` ("stories"); the weekly check rewrites it. Brief: `config/STORY_BRIEF.md`.
- The places record (`config/place-record.json`) holds the agreed text of every place's blog section and every stop summary that
  links to it. The build lists every difference in `health.json` ("places"). Wording changes are agreed by the weekly check; a
  change of fact goes to Ben on the Ride Story Review page, and until he rules the app keeps the agreed stop summary. Tool:
  `scripts/place-record.mjs`. Rules: `config/STORY_BRIEF.md`, "The places record".
- How written text is said aloud (abbreviations such as St, Rd and Mt, units, and respellings for names the voice gets
  wrong) is in `config/speech.json`, used by the natural voice and the phone voice. Its "pronounce" list gives the natural
  voice the exact sound of a word as IPA (Noosa is NOO-suh), sent to Google with each line; the build reports it if Google
  ever refuses one. `listen.html` on the site plays every
  place name so names can be checked by ear.
- An offer can be set to "finish" (`showAt`): it is not shown at the start, comes up in the last 1.5 km and sits on the
  finish card. Used for Land and Sea Brewery, over the road from the shop.

## Staff ride list

Each build also publishes `rides.json`: every live ride's name, description, brand, type, riding time, distance, climbing, stops, cautions and single track sections (and `test` for a test route), with no keys, codes or route line. The EO Crew staff app reads it for the Ride Guide manual (EO-HI-10), so a ride added here shows up in the manual by itself. Who a ride suits is written in the ride's Ride with GPS description.

## Staff file for EO Crew (codes, QR codes and screenshots)

The EO Crew Ride Guide manual (EO-HI-10) shows every ride's QR code, route code and link, and six Ride Guide screenshots,
kept up to date by themselves. Route codes are never public, so these go out locked:

- Each build writes `staff.enc.json` (every live ride's name, brand, type, route code and link) and the workflow adds
  `staff-screens.enc.json` (six phone screenshots of the Kids & Family ride, retaken at 3am, on every change and on
  demand by `scripts/staff_screens.py`, kept on the `staff-screens` branch). Both are locked with EO Crew's public key,
  `config/staff-key.pem` (`scripts/staff_bundle.mjs`): a public key can only lock, so only EO Crew's server can open them.
- EO Crew makes the QR codes itself from the links. Its key lives only in EO Crew; to replace it, delete EO Crew's
  RideGuideKey record and copy the new key from https://element-crew-connect.base44.app/functions/rideGuide into
  `config/staff-key.pem`.
- Check without opening anything: https://element-crew-connect.base44.app/functions/rideGuide?check=1 gives counts only.
- A screenshot failure keeps the last set and never stops the build.

## Ride counts

An indicative count of how often each map is used, shown on the Ride Guide Settings page (17/10/2026). The app sends one
anonymous tick the first time a route is opened on a phone, and one when a ride reaches the finish card (75% of the ride
ridden on that phone). A tick is the route, the event, the date and a random id: nothing about the rider. Ticks wait on
the phone until there is signal; staff check links and test drives never count. They go to the Apps Script counter in
`config/counter.json` (code: `scripts/ride-counts.gs`), which writes them to the Google Sheet "Ride Guide ride counts"
and counts each id once. The counter's web address gives the totals per route (open on purpose, Ben 17/10/2026: route names
and numbers only, the sheet stays private); the "Ride Guide settings apply" task copies them to the settings page nightly. The weekly route check (`scripts/check.mjs`) confirms the counter is in the app
and answering.

## The Story Library

Every story, blog section, pin line, kayak talking point and wildlife card is written once, in `library/`. The build reads it, publishes it as `library.json` (read by the EO Crew staff app) and `library.html` (to read), and lists any live blog section or Ride with GPS pin that differs from it. See `library/README.md`.

## Changing things

| Change | Where |
| --- | --- |
| Cue wording, stops, the route line | Ride with GPS. Live by the next morning, or run the workflow by hand. |
| Add or remove a route | `config/routes.json`, plus the route's Ride with GPS privacy code in the `ROUTE_SECRETS` secret |
| Partner offers | The Ride Guide Settings page (`config/offers.json` underneath; `validUntil` hides it after that date, `showAt` "finish" keeps it for the end of the ride) |
| Any story, blog section, pin line, kayak talking point or wildlife card | The Story Library, `library/` (read `library/README.md`). `config/stories.json` and `config/place-record.json` are generated from it. |
| How a word or name is said aloud | `config/speech.json` |
| When turns are announced, close-together turns, off-route sensitivity, stop pop-ups, screen defaults | The Ride Guide Settings page (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18). Saving it starts the "Ride Guide settings apply" scheduled task, which writes `config/settings.json` here. Every value is range-checked and falls back to its default. |
| Which brand each map uses (By Earth and Ocean or Bike On) | The Ride Guide Settings page; the task writes `brand` in `config/routes.json`. The map then shows that brand's logo and colours. |
| Whether a ride announces its points of interest by default | The Ride Guide Settings page; the task writes `stories` in `config/routes.json` (Ben, 15/10/2026: scenic and mountain bike rides on, except Tewantin MTB Trails; road and gravel rides off). With stories on, a rider reaching a point of interest gets its card and a short spoken overview, with Hear the full story on the card. With stories off, points of interest are not announced at all (no card, nothing spoken); directions, cautions, welcome pins and turnarounds always are. Riders can switch it in the map's Settings; their choice is kept for that ride only. A ride with no `stories` value is reported in `health.json` and uses the screen default. |
| Riding time on a ride page | Each route's `type` in `config/routes.json` (scenic, mtb, gravel, road, hinterlandMtb, hinterlandGravel) picks its average speed, set per type on the Ride Guide Settings page (`speeds` in `config/settings.json`; Ben, 17/10/2026: different rides need different speeds). Distance comes from the route line. A route with no `type` is reported in `health.json` and uses its activity speed. `rides.json` carries each ride's `type` and `riding_minutes` for the EO Crew manual. |
| Brand colours, logos, phone numbers | `config/brands.json` and `site/assets/` (use the normal By Earth and Ocean header logo, not the reversed one) |
| Translations | `config/i18n/<lang>.json`. New or changed English text is listed in `i18n-missing.json` after a build and in `health.json`; the weekly drift check fills the gaps. Brief: `config/TRANSLATION_BRIEF.md` |
| A route's QR code needs replacing | Bump its `rev` in `config/routes.json`. The old code stops working. |

## Checks

- `dist/health.json` (published as `health.json`) lists every route, where its data came from, broken stops,
  untranslated text and offers that are not near any route.
- `scripts/check.mjs` runs from the Element Outdoors Drift Check Register each week: site rebuilt recently,
  every QR code opens its route, links and photos work, nothing untranslated, stories and the places record in step.
- Phones: the route and voice.json are fetched fresh whenever there is signal; recordings and logos are kept on the phone.
  Recordings live under a folder tag that includes the speech rules, so a re-recorded line gets a new address. When the app
  comes back to the screen with no ride under way it fetches the latest route and recordings and loads a new app version.
  The build publishes `files.json` (a fingerprint of every recording and logo) and flags in health.json any recording that
  changed at the same address.
- A failed nightly build emails the GitHub account owner.

## Local work

```
node scripts/build.mjs --offline   # build from cache/ instead of Ride with GPS
python3 scripts/test_app.py http://localhost:8765/ <route key> <outdir>   # simulated ride in a phone-sized browser
```
Secrets for local builds live in `.secrets.json` (never committed): `{ "keySalt": "...", "privacy": { "<rwgps id>": "<privacy code>" } }`.
