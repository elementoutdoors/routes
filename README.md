# Ride Guide

Public route pages for Element Outdoors self-guided tours. A customer scans a QR code, the route opens in their
phone's browser with the map, spoken and written directions, stops and partner offers. No app, no account.

## How it works

- Ride with GPS is the source of truth for the line, the cues and which places a ride passes (POI Library pins), in the
  By Earth and Ocean organisation account.
- The Ride Desk (below) is the master for everything else about a ride: whether it is live, its brand, type, name in the
  app, description, ride sheet words, photo and staff notes.
- Every night (3:07am Brisbane), every hour from 6am to 8pm, on every change here, and on demand, GitHub Actions runs
  `scripts/build.mjs`. It pulls every ride switched on on the Ride Desk from Ride with GPS, adds the card, offers, brand
  and translations, and publishes the site to GitHub Pages.
- If Ride with GPS fails or returns broken data, the last good copy of that route stays live.
- Each route lives at a secret address. The QR code carries the key; the app removes it from the address bar,
  so a copied link does not open the route. Search engines are told not to index the site.
- Opening a route saves it to the phone, with the map around it, so it keeps working with no signal.
- Each route also has a 6-character route code (printed on its QR card). Typing it on the home page reopens the route,
  and "Save to my phone" shows the code and adds the route to the home screen.
- Route page layout (10/11/2026): "Saved to your phone. Works with no signal." sits under the distance, climbing and time,
  and only Start riding is pinned to the bottom; the rest scrolls with the page. The route page scrolls as a normal page
  (html.page-scroll) so iPhone Safari shrinks its address bar as the rider scrolls.
- Full screen while riding: Start riding asks the browser for full screen, so Android and desktop hide the address bar
  (the ride screen never scrolls, so the browser would otherwise keep it). iPhone browsers can't do this for a web page;
  there only a home screen icon removes it. End ride leaves full screen.
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

## The Ride Desk (18/10/2026)

The Ride Desk page (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18, formerly the Ride Guide Settings page) holds one card
per ride, plus the partner offers and rider settings. Where everything about a ride lives:

| What | Master | How it gets here |
| --- | --- | --- |
| Route line, cues, which places a ride passes | Ride with GPS | The build reads it |
| Place stories (spoken story, blog section, pin line) | The Story Library, `library/` | The build reads it |
| Distance, climbing, riding time | Worked out from the line and the speed for the ride's type | The build |
| Live in the Ride Guide; on the hire desk iPad and in the booklet; brand, type, stories, GPX; name in the app; description; title, category, sell line, four highlights, level, surface, terrain, recommended bike, sheet note; photo | The ride's Ride Desk card | `config/ride-desk.json` |
| Who it suits, not for, time to allow, sold as, bikes to hire, start and finish, staff notes | The ride's Ride Desk card | `config/ride-desk-private.enc.json` (sealed) |
| Map place names and camera angle on the ride sheets | Claude | `ride-sheets/rides.py` |

- The page saves cards in its own data; the scheduled task "Ride Guide settings apply" copies them here with
  `node scripts/ride-desk.mjs apply` (when Ben presses Save, and nightly at 2:41am). Never edit `config/ride-desk.json`
  or the sealed file by hand: change the card.
- The staff section and each route's Ride with GPS privacy code are sealed to the build's own key (made from
  `ROUTE_SECRETS` keySalt, public half in `config/ride-desk-key.json` and at `desk-key.json`), so this public repo never
  shows them and nothing new has to be pasted into GitHub when a ride is added. The build opens them; `health.json`
  "desk" says whether it could.
- New rides: once a day the "Ride Guide settings apply" task (its nightly 2:41am run, step 10) runs
  `scripts/push/ride-desk-scan.js` in Ben's Ride with GPS session in Chrome on bens-pc and `node scripts/ride-desk.mjs scan`: a route in the organisation account with no card becomes a
  "New, hidden" card, with its name, description and privacy code. Ben fills it in and switches it on.
- Each build publishes, with no keys, codes or route line: `desk.json` (per card a fingerprint of what the build used and
  any empty fields; per built ride its numbers, the places it passes in ride order with their Story Library entry, and stop
  photos to pick from), `desk-key.json`, and `links.enc.json` (each live ride's link and route code, sealed to the Ride
  Desk's key, so the settings task can fill the page's private routes/links record by itself). The settings task copies
  these onto the page (`node scripts/ride-desk.mjs published` and `links`, and photo previews with
  `scripts/ride_desk_thumbs.py`).
- A ride switched off for the iPad is left out of `rides.json`, the ride sheets, the booklet and the locked index, and stays
  in `staff.enc.json`.
- Checks: `node scripts/ride-desk.mjs check <db dir>` (weekly, Drift Check Register, Ride Guide routes tab) lists a card
  the build did not publish (it re-runs the settings task), a live ride with empty fields, an iPad ride with no photo, a new
  ride left hidden more than 14 days, and a scan more than 3 days old.

## Staff ride list

Each build also publishes `rides.json`: every ride switched on for the hire desk iPad, with its name, description, brand, type, riding time, distance, climbing, stops, cautions and single track sections (and `test` for a test route), and its Ride Desk sheet words (title, category, sell line, highlights, level, surface, terrain, bike), with no keys, codes or route line. The EO Crew staff app reads it for its customer lists and the Ride Guide manual (EO-HI-10), so a ride switched on shows up there by itself.

## Staff file for EO Crew (codes, QR codes and screenshots)

The EO Crew Ride Guide manual (EO-HI-10) shows every ride's QR code, route code and link, and numbered screenshots of
every Ride Guide screen and of the Ride Desk, kept up to date by themselves. Route codes are never public, so these go out locked:

- Each build writes `staff.enc.json` (every live ride's name, brand, type, route code and link, plus its Ride Desk title,
  iPad switch and staff section: suits, notFor, timeToAllow, soldAs, bikes, startFinish, staffNotes) and the workflow adds
  `staff-screens.enc.json` (about 30 screenshots, retaken at 3am, on every change and on demand by
  `scripts/staff_screens.py`, kept on the `staff-screens` branch: every app screen on the Kids & Family ride with a
  simulated GPS, and the Ride Desk built from `ride-desk/` with made-up data; each has numbered markers, a `group`
  (setup, riding, stops, finish, settings, desk) and `keys` saying what each number is). Both are locked with EO Crew's public key,
  `config/staff-key.pem` (`scripts/staff_bundle.mjs`): a public key can only lock, so only EO Crew's server can open them.
- EO Crew makes the QR codes itself from the links. Its key lives only in EO Crew; to replace it, delete EO Crew's
  RideGuideKey record and copy the new key from https://element-crew-connect.base44.app/functions/rideGuide into
  `config/staff-key.pem`.
- Check without opening anything: https://element-crew-connect.base44.app/functions/rideGuide?check=1 gives counts only.
- A screenshot failure keeps the last set and never stops the build.

## The Ride Guide manual (EO Crew)

One document in EO Crew (Base44 app 6abba75b48155c78238d4cba): EO-HI-10 "Ride Guide: the app, our rides and the Ride
Desk", in three parts: Part 1 for everyone, Part 2 for managers (the Ride Desk) and Part 3 the technical appendix (Ben,
20 Oct 2026: one manual; EO-HI-10.1 and 10.2 are superseded). Each part is a level 1 section with its sections under it
at level 2. EO Crew holds the words (managers can edit them); `manual/build_manual.py` is the version Claude wrote. They stay
right by themselves:

- Pictures: `{"type": "ride_screens", "group": "<group>"}` blocks show the screenshots above, retaken every night.
- QR codes, route codes, the ride list and staff notes are live blocks (`ride_qr`, `ride_list`).
- Words: `node scripts/manual_facts.mjs --check` compares what the manual describes (phone settings, languages, app
  controls and wording, Ride Desk sections, fields and settings, setting keys, build schedule and steps, the screenshot
  list) with `manual/written.json`, which also says which EO Crew sections each fact feeds. The weekly check
  (`scripts/check.mjs`, "manual") lists any change; the drift check rewrites those sections in EO Crew, then runs
  `--accept` and pushes. Change the app, the Ride Desk or the build in any session and the next weekly check catches it.

## The Ride Desk page source

`ride-desk/page/` holds the Ride Desk page in parts; `python3 ride-desk/build.py` joins them into `ride-desk/ride-desk.html`,
which Claude publishes to https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18. `ride-desk/mock.js` stands in for the page's
database when the screenshots are taken.

## Map follow, battery and long gaps between directions (26/10/2026)

- Touching or dragging the map stops it following the rider; it follows again by itself 15 seconds after the last touch
  (`followMap`, REFOLLOW_MS), or at once with the locate button.
- Battery: the map is not moved while battery saver has the screen blacked out or the page is hidden, nor for moves under
  4 m; when the black screen lifts the map jumps straight back to the rider.
- Following the rider along the route (map matching, 26/10/2026): once riding, each GPS fix is matched first to the
  stretch just behind and ahead of the last position (`nearIn`), picking the place closest to where the rider should be
  by now, and a stretch running against the rider's direction of travel is avoided. Only when that fails is the whole
  route searched, and a jump far ahead (over 300 m) or back (over 60 m) is taken only when a second fix agrees. Found on
  the Mt Tinbeerwah up and back: one wobbly fix at the summit car park, where the way up and the way down are 25 m apart,
  could put the rider on the way up and the app then said "riding backwards" all the way down. A direction read straight
  after a stop (`after`) is kept until the stop has been read.
- Turn arounds (26/10/2026, all routes checked): the app finds every point where a route comes straight back the way it
  went (`tipsOf`, from the line itself; single track left out). The position only crosses to the way back once the rider
  has been within 50 m of the turn around (`tipGuard`), so a wobbly fix can no longer skip the U-turn direction or give
  "riding backwards" there. A rider who turns back early is moved to the same spot on the way back after going back
  about 50 m, and the way back directions carry on. A direction the rider is still within 60 m of is said even if a fix
  has moved the position past it (`nearCue`). Found with wobbly GPS rides of every out and back: the Hill Road U-turn
  (Valleys and Vistas, Through Lake Country, Rockpools and Ridgelines) and the Mt Tinbeerwah lookout on the Lakes Ride
  were usually never said.
- Battery saver is on by default for every ride (Ben, 27/10/2026; config/settings.json screen.batterySaver and the Ride
  Desk). A rider can still turn it off in Settings. A stop card that opened by itself closes again once the stop has been
  read and nothing has been touched for the blackout time (`autoCloseStop`), so the screen can go black again. A card the
  rider opened from the map or the Stops list stays open.
- Battery (27/10/2026): the whole route is only searched when the stretch just ridden doesn't match (`cands`), instead
  of on every GPS reading.
- More than 2 km to the next direction (FAR_CUE): the riding screen shows "Follow the route" and "Next direction in X"
  instead of naming a turn that is a long way off. Found on Mt Tinbeerwah, where the climb showed the turn for the way
  back down. Spoken warnings are unchanged.
- Map direction (Ben, 4/11/2026; riders said the map did not turn the way they were facing): the map now turns so the
  way the rider is going is at the top, by default. On the route the direction comes from the route line just ahead
  (`routeBearingAt`), off the route from the way the rider has been moving, and it is held while stopped or paused and
  only turns for a change of more than 15 degrees (`TURN_MIN`), so it stays steady on a bar mount. The phone's compass is
  not used (iPhone asks permission for it in a web page, and it swings with the handlebar). The rider sits a little below
  the middle so more of the way ahead shows (`AHEAD_SHIFT`). Riders can choose "North at the top" in Settings (Map
  direction, setting `mapUp`) or tap the compass button above the voice button, which also shows where north is.
  Hand rotation stays off. The route page map is always north up.

## Screen at turns, battery and the Do not lock your screen card (13/11/2026)

Riders said that with battery saver on the screen did not come back on near turns and they had to tap it or turn it back
on, and that the battery still drained fast. What was found, by riding the six scenic rides and the test route in a
phone-sized browser with simulated GPS (18 km/h, nobody tapping; again at 25 km/h with wobbly GPS), and what changed:

- Black at the turn. The map lit at the Ride Desk wake distance (100 m) and went black again about 5 m before the turn,
  the moment the direction after it became the next one (`nextCueIndex`). It was black at the turn itself on 233 of 387
  directions. Now (`litForTurn`, `saverTick`) the map is lit from the wake distance until the rider is 50 m past the
  turn (`SAVER_AFTER_M`; 30 seconds at most if they stop there, and it also holds while they are within 50 m of the
  turn itself, for turn arounds). After the change: black at the turn on 0 of 387, with clean and with wobbly GPS.
- The voice and the map. The first spoken warning comes at the early warning distance (160 m) and the map lights at the
  wake distance (100 m), both Ben's settings on the Ride Desk, so for about 12 seconds the voice has spoken and the
  screen is still black (it shows the direction and the distance in white). That is left as he set it. Setting the wake
  distance past the early warning (170 m) makes them coincide, for about 9 more minutes of lit screen on Full Noosa.
- A warning card that never closed. A caution stop with notes opens its card by itself (Beach access on North Shore,
  Steep Hill on Mt Tinbeerwah). It was left out of the 27/10/2026 rule that a card which opened by itself closes once it
  has been read, so the screen stayed lit for the rest of the ride: 17 km of North Shore, 25 km of Mt Tinbeerwah. It now
  closes like any other (`autoCloseStop`). A card the rider opened still stays open.
- Stopped without pausing. A rider stopped beside a turn or off the route kept the screen lit for as long as they
  stood there. After a minute without moving (`SAVER_STILL_MS`, `noteMoved`) the screen goes black; rolling again lights
  it at once. A rider who has not reached the route yet keeps the map lit.
- The black screen is fully black (`.saver`; it was 94% black with the map showing through, so no pixel was ever off)
  and the map and ride controls under it are not drawn (`body.saver-on`). The ridden line and the blue dot are left
  alone while it is up (`mapUnseen`) and brought up to date when it lifts (`hideSaver`). In a minute of black screen
  the map used to be redrawn 127 times and the ridden line 30 times; now neither is touched.
- Map drawing while lit. The map glided to each new position over 0.8 s, with a GPS reading every second, so it was
  animating for 48 seconds of every minute (about 3,000 redraws a minute in the test). It now steps to each position
  and only eases a change of direction (`followMap`, `TURN_MS`): under 3 seconds of animation and about 250 redraws a
  minute in the same test. Labels switch rather than fade (`fadeDuration: 0`), the map is drawn at no more than twice
  the screen's base size (`pixelRatio`; 1170 by 2532 became 780 by 1688 on a 3x phone), the ridden line is redrawn
  every 4 s, not 1.5 s (`DONE_EVERY_MS`), and the progress bar no longer animates.
- Progress is saved every 5 s or when a direction or stop is given, not on every reading (`saveProgress`), and at once
  when the page is hidden or closed.
- Keeping the phone awake (`requestWake`). The browser's Screen Wake Lock was asked for at Start riding and when the page
  came back, and nowhere else, so a lock the phone took back any other way stayed lost and the phone locked itself. It
  is now asked for again when it is released, on a full screen change, on every GPS reading (every 10 s after a
  refusal) and on every tap (some phones only grant it again from a tap). It is let go at the finish, so a phone left on
  the finish card can lock as usual.
- A GPS blip is not "location is off" (`startGps`, `LOC_QUIET_MS`). Since 12/11/2026 a "no position" answer from the
  phone showed the "Location is off on this phone" banner, which also lit the screen for the blackout time. A phone
  that is giving readings and misses one (under trees, between buildings) has not had location turned off, so the
  banner now only comes up if no reading follows within 8 seconds, or at once when there has been no reading at all.
  Found because the test browser reports a miss before every reading, which kept the screen lit for good.
- Not done: a backup for phones whose browser has no working wake lock (iPhones before iOS 16.4, and a ride opened from
  a home screen icon before iOS 18.4, where Apple's Safari 18.4 release notes list it as fixed). The usual fix is a
  hidden looping video (the NoSleep.js library). It is third party code that cannot be tested from here on a real
  phone, so it was left for Ben to decide.
- None of this measures real battery use: that needs a ride on a phone. What was measured is how long the screen is lit
  and how much the map is redrawn. Minutes of lit screen per ride, before and after: Full Noosa 32 and 41, Kids and
  Family 17 and 23, Surf Beaches 27 and 37, Mt Tinbeerwah One Way 29 and 37 (up: the map now stays on through every
  turn), Mt Tinbeerwah 95 and 39, North Shore 68 and 32 (down: the stuck card). All six together: 268 and 209 minutes of
  637.

The Do not lock your screen card (Ben, 13/11/2026): a big red card every time a rider taps Start riding or Continue my
ride (`beginRide`, `openLockNote`), after the Before you ride card on a first start. "Read this. Do not lock your
screen. If your phone locks, the app will stop navigating." and, with battery saver on, "The screen goes dark between
turns to save battery. That is normal. Tap the screen to light it up. Do not press the button on the side of your
phone." (a rider who takes the black screen for a sleeping phone and presses the button locks it). The red I understand
button starts the ride. It took the place of the spoken "Keep this screen open while you ride" line at the start of the
ride, which Ben asked to drop; with that line gone the first direction's early warning is no longer crowded out. Staff
check links and Test drive skip the card. In all 9 languages. Change the wording only with Ben. Screenshot 06c.

The build machine (13/11/2026): GitHub moved its "ubuntu-latest" runner to Ubuntu 26.04, whose Python 3.14 cannot install
the pinned Playwright (1.47.0), so the staff screenshot step and any ride sheet rebuild failed. Neither stops the build
(the last good set is kept), so nothing said so. The build job is now pinned to `ubuntu-24.04`. The screenshots are
retaken on every change and by the first scheduled build after the last set is 20 hours old (matching the 3am schedule
by name missed nights). The build publishes `staff-screens.json` (when the set was taken and how many pictures), and the
weekly check (`scripts/check.mjs`, version 12) raises an issue if the set is more than 3 days old.

Staff screenshots (`scripts/staff_screens.py`): the Battery saver picture (13) had been showing a lit map since
27/10/2026, when battery saver became on by default: the script clicked the switch to turn it on, which turned it off.
It now sets the switch to the state it wants (`set_saver`): off for the riding pictures, on for its own picture.

## Before you start notice (11/11/2026)
A red card that comes up first when a ride opens in a browser tab, so riders who are not tech savvy don't lose the map. Points: use a normal tab (not private or incognito), save the map to the home screen (closing the tab loses it, closing the browser app is fine), location must be on (with a live "Location is on/off" line where the browser can tell), charge the phone, and on loops only, ride the loop in one direction. The home screen and location steps sit behind "How?" links. Closing line: if they choose not to and lose the map, they find their own way back. Button: "I've read this. I've done it, or chosen not to." A language picker sits in the notice (the top bar language button is under the backdrop while it is open). It is kept per ride per phone (localStorage rg.notice), and also brings up the phone's location question. Skipped from a home screen icon (standalone) and on ?check links. Wording agreed with Ben 11/11/2026; change it only with him. Code: site/app.js openNotice and needNotice; styles at the end of site/app.css. Screenshot 01b in the staff pictures.

Since 12/11/2026 the notice checks the phone first and shows only what still needs doing: a point the phone confirms is fine becomes a green tick under "Already done on this phone"; a point it knows is wrong turns solid red with the exact problem (private tab, location blocked, battery under 50%); a point it can't tell stays as the normal pink instruction. Checks (noticeChecks): private tab by the detectIncognito library's tests (WebKit storage error, Chromium storage quota, Firefox storage error), location by the Permissions API, battery by getBattery (Android Chrome only; iPhones don't share it). The home screen point always shows in a browser tab (a page can't tell). Add to Home Screen steps are per browser (homeSteps: iPhone Safari including iOS 26's ••• menu, Chrome and Firefox or Edge on iPhone, Samsung Internet, Chrome and others on Android), shared with Getting back to this route. Tapping the button sooner than the notice could be read (5 s per point still to do, 1 s per green tick, 10 s to 25 s) brings up a friendly "That was quick! Did you really read it?" check (openNoticeCheck) with "Busted!" (back to the notice) and a green "Yes, I read it..." button; it shows once. Screenshots 01b and 01c.

Location since 12/11/2026: the notice asks the phone for location as soon as it opens (askLocation), so the phone's own "Allow location?" question comes first. While waiting the point says "Your phone will ask to use your location. Tap Allow."; allowed becomes a green tick; blocked for the page or off on the phone turns red with the steps (locSteps, per phone and browser) showing. On the ride, if location is blocked or off, or there is no fix after 20 seconds, a banner says so ("Can't see the blue dot? ...") and opens the steps with a Reload this page button (openLocHelp); it hides itself once a fix arrives. A rider who taps Don't Allow is not asked again by the phone; the steps are for that case.

## Before you ride (risk card)

Added 20/10/2026 (Ben's wording, checked against the Checkfront waiver "Risk Warning and Acknowledgement" and the
Product Truth). The first time a ride is started on a phone, a "Before you ride" card comes up: own risk, check
conditions and choose a ride to suit fitness and ability, never ride through flood water or flooded creeks (turn back
and use the phone's maps app to find a safe way back), road rules, helmet, and the Queensland rule that the phone is in a
mount while riding. "I understand" starts the ride and is kept per ride on the phone (`rg.risk`). The line "You ride at
your own risk. Read before you ride." under Start riding opens it any time. Resumed rides, Test drive and staff check
links skip it. Safety text: translated in full into every language the same day; change the wording only with Ben.

## Directions to the route and joining a loop part way

Added 20/10/2026 for riders staying somewhere else. "Directions to the route" on the route page offers the nearest point
on the route or the start, and opens Apple Maps (iPhone) or Google Maps with that point set (cycling, walking for walks,
driving for paddles). A web page cannot bring itself back once the maps app is in front, so the rider is asked to come
back; when they do (`checkArrival`, on returning to the page) the app checks where they are: on the route it chimes and
offers "Start riding from here", otherwise "Still on your way?" with the directions again. The pending trip is kept in
`rg.approach` on the phone for 6 hours.

On a loop (start and finish within 300 m, over 2 km), a ride that first locks on more than 500 m from the start or finish
is joined there: the app turns the route round so the join point is the start (`joinedRoute`), the rider rides the whole
loop and the ride (and the finish card) ends back at the join point. The old opening and arrival lines at the real start
and finish are dropped for that ride. "Near the end only" offers come up when passing the partner instead of in the last
1.5 km. Progress remembers the join point, so Continue my ride picks up the same way. One way rides are not turned:
joining part way rides on to the finish. Test drive and staff check links always start at the real start.

## Ride counts

An indicative count of how often each map is used, shown on the Ride Desk (17/10/2026). The app sends one
anonymous tick the first time a route is opened on a phone, and one when a ride reaches the finish card (75% of the ride
ridden on that phone). A tick is the route, the event, the date and a random id: nothing about the rider. Ticks wait on
the phone until there is signal; staff check links and test drives never count. They go to the Apps Script counter in
`config/counter.json` (code: `scripts/ride-counts.gs`), which writes them to the Google Sheet "Ride Guide ride counts"
and counts each id once. The counter's web address gives the totals per route (open on purpose, Ben 17/10/2026: route names
and numbers only, the sheet stays private); the "Ride Guide settings apply" task copies them to the Ride Desk nightly. The weekly route check (`scripts/check.mjs`) confirms the counter is in the app
and answering.

## Ride sheets and rides booklet

`ride-sheets/` makes the printed ride sheets: one A4 landscape sheet per live ride, Bike On and By Earth and Ocean, with
a 3D map of the route and its place names across the top, then a photo of the ride, the ride story, distance, climbing,
riding time, level, surface, bike, an elevation profile and the ride's Ride Guide QR code with its route code. It also
makes the combined booklet: for each brand a cover listing the rides by kind with page numbers, then that brand's sheets.
The layout is the Branding Bob ride sheets (October 2026), with a ride photo where the app store codes were and the Ride
Guide code in place of the Ride with GPS code (Ben, 18/10/2026).

It runs after every build and keeps itself up to date:

- The ride story, distance, climbing and riding time come from the Ride Guide data every time, so a change in Ride with
  GPS reaches the sheets on the next build. A change of 0.5 km or 25 m climbing, or a new description, is logged.
- The 3D map is drawn again only when the route line changes a lot: its length by more than 2 percent, or any part more
  than 100 m from the line the map was drawn from (or its map settings in `ride-sheets/rides.py` change). Cue, stop and
  story edits, or a line nudged a few metres, keep the map.
- The photo is the one on the ride's Ride Desk card: by default the featured image on its Bike On website page, or one
  of the ride's own photos, an upload or a link picked on the card. Fetched again only when it changes. A ride with no
  photo shows a placeholder and is flagged by the weekly check. `ride-sheets/photos.json` on the site says which photo
  each sheet uses.
- The sheet's words (title, category, sell line, highlights, level, surface, terrain, bike, note) come from the Ride Desk
  card. A new ride on the iPad gets a sheet straight away; its map place names are added to `ride-sheets/rides.py`.
- Only rides switched on for the hire desk iPad get a sheet and a place in the booklet.

Route codes and links are never public, so the sheets are only published locked with EO Crew's public key:
`booklet.pdf.enc` with `booklet.key.json` (the whole booklet, for printing; envelope v2: the PDF's raw AES-GCM
ciphertext and a small key file, so EO Crew can open it without holding it twice in memory), `ride-sheets/<slug>.enc.json` (one lighter sheet each, for the
iPad) and `ride-sheets/index.enc.json` (a small list for EO Crew: pages, dates, sizes, photos, sheets held back), next to
`staff.enc.json`. A sheet that fails its checks (QR code, route code, a flat elevation profile on a ride that climbs) is
held back and the ride keeps its previous sheet. The plain sheets are never published or committed. The 3D maps, photos, `manifest.json` (what each
sheet was built from, with a changelog) and the last locked files are kept in the Actions cache, never in the repo. A
failure keeps the last good booklet and never stops the site build. How it works and what to edit:
`ride-sheets/README.md`.

## The Story Library

Every story, blog section, pin line, kayak talking point and wildlife card is written once, in `library/`. The build reads it, publishes it as `library.json` (read by the EO Crew staff app) and `library.html` (to read), and lists any live blog section or Ride with GPS pin that differs from it. See `library/README.md`.

## Changing things

| Change | Where |
| --- | --- |
| Cue wording, stops, the route line | Ride with GPS. Live by the next morning, or run the workflow by hand. |
| Add a ride | Draw it in the By Earth and Ocean organisation account on Ride with GPS. It appears on the Ride Desk as New, hidden within a day; fill in its card and switch it on. |
| Remove a ride | Switch it off on its Ride Desk card. Its link and code stop working. |
| A ride's description, name in the app, brand, type, stories, GPX, sheet words, photo, staff notes | Its Ride Desk card |
| Partner offers | The Ride Desk (`config/offers.json` underneath; `validUntil` hides it after that date, `showAt` "finish" keeps it for the end of the ride) |
| Any story, blog section, pin line, kayak talking point or wildlife card | The Story Library, `library/` (read `library/README.md`). `config/stories.json` and `config/place-record.json` are generated from it. |
| How a word or name is said aloud | `config/speech.json` |
| When turns are announced, close-together turns, off-route sensitivity, stop pop-ups, screen defaults | The Ride Desk (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18). Saving it starts the "Ride Guide settings apply" scheduled task, which writes `config/settings.json` here. Every value is range-checked and falls back to its default. |
| Which brand each map uses (By Earth and Ocean or Bike On) | The ride's Ride Desk card (`brand` in `config/ride-desk.json`). The map then shows that brand's logo and colours. |
| Whether a ride announces its points of interest by default | The ride's Ride Desk card (`stories` in `config/ride-desk.json`; Ben, 15/10/2026: scenic and mountain bike rides on, except Tewantin MTB Trails; road and gravel rides off). With stories on, a rider reaching a point of interest gets its card and a short spoken overview, with Hear the full story on the card. With stories off, points of interest are not announced at all (no card, nothing spoken); directions, cautions, welcome pins and turnarounds always are. Riders can switch it in the map's Settings; their choice is kept for that ride only. A ride with no `stories` value is reported in `health.json` and uses the screen default. |
| Riding time on a ride page | Each ride's type on its Ride Desk card (scenic, mtb, gravel, road, hinterlandMtb, hinterlandGravel) picks its average speed, set per type on the Ride Desk (`speeds` in `config/settings.json`; Ben, 17/10/2026: different rides need different speeds). Distance comes from the route line. A route with no `type` is reported in `health.json` and uses its activity speed. `rides.json` carries each ride's `type` and `riding_minutes` for the EO Crew manual. |
| Brand colours, logos, phone numbers | `config/brands.json` and `site/assets/` (use the normal By Earth and Ocean header logo, not the reversed one) |
| Translations | `config/i18n/<lang>.json`. New or changed English text is listed in `i18n-missing.json` after a build and in `health.json`; the weekly drift check fills the gaps. Brief: `config/TRANSLATION_BRIEF.md` |
| Printed ride sheets and booklet | Words and photo: the Ride Desk card. Map place names, layout: `ride-sheets/` (read `ride-sheets/README.md`). The story is the card's description; the numbers follow the route line. |
| A route's QR code needs replacing | Bump its `rev` in `config/ride-desk.json` (Claude's field; the settings task keeps it). The old code stops working. |

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
