# Story Library

The one place every Element Outdoors story is written. Everything else is a copy made from it:

| Copy | How it follows the library | When |
| --- | --- | --- |
| Ride Guide app (stops, full stories, natural voice, 8 languages) | The build reads the library directly | Every push and every night, 3:07am |
| EO Crew: Know Noosa | Copies the spoken stories and recordings (stories-voice.json) | Daily |
| EO Crew: wildlife cards and the kayak talking points in the tour manual | Copies them from library.json on the Ride Guide site, read only in the app | Daily |
| Bike On and By Earth and Ocean ride story blogs | Pushed through Chrome (scripts/push/blog.js) | In the session that changes the library, and the weekly check puts back any difference |
| Ride with GPS POI Library pins (the line read out on arrival) | Pushed through Chrome (scripts/push/pins.js), then Experiences republished | Same as the blogs |
| config/stories.json, config/place-record.json | Generated (`node scripts/library.mjs generate`), never edited | With every library change |

Read it as a page: https://elementoutdoors.github.io/routes/library.html

## What is in it

One JSON file per entry, named by its key.

- `places/`: a place on our rides. `blog` holds each brand's blog section (heading, the area it sits in, the section it follows, paragraphs as HTML with links only). `pins` holds each brand's Ride with GPS POI Library pins (name, and the text read aloud on arrival). `story` is the full spoken story, about a minute, written to be heard (config/STORY_BRIEF.md).
- `stops/`: a stop on a guided or self guided tour that is not on a blog, such as the Stingrays and Everglades kayak stops. `tours` gives the tour and stop number, `talk` holds the guide talking points (points, detail, detail_blocks) shown in the EO Crew tour manual, `story` the spoken story, `origin` where it came from.
- `wildlife/`: an animal. `card` holds the EO Crew wildlife card (name, scientific and local names, group, description, detail, how to spot, conservation, photo, source). `story_key` names the place or stop story its talking points come from.

Every entry has `key`, `kind`, `title`, `status` (live, draft or retired) and `updated` (the Brisbane date of the last change). `lint_ok` lists house rule findings Ben has accepted for that entry.

## Changing a story (any session)

1. Content comes from Ben (voice notes, rulings) or research he has asked for. Facts follow the Product Truth for anything about safety, price or product, and the rulings on the Places record tab of the ride stories doc (https://claude.ai/code/artifact/a698e78e-221d-4f1c-8658-d58461c85558). A change of fact Ben has not given or ruled on goes to him first as a card on the Ride Story Review page (https://claude.ai/artifact/XSdaNvQMw8tYpaqSiBz7Tp), never straight into the library.
2. Edit the entry's file. Keep every copy of the same fact in step inside the entry: if a blog section changes, rewrite the spoken story and the pin line to match, for both brands. Set `updated`.
3. `node scripts/library.mjs lint` (house rules) and `node scripts/library.mjs generate`, then commit "Story Library: <what changed>" and push. The Ride Guide rebuilds in about 3 minutes; EO Crew picks it up within a day.
4. Push to the blogs and pins: wait for the rebuild, run `node scripts/library.mjs plan`, then in Chrome on Ben's laptop (both WordPress sites are signed in on the upstairs computer as of 11/10/2026; use whichever is):
   - Blogs: open a wp-admin page of the blog, paste scripts/push/blog.js with ITEMS set to that brand's plan items, run it, then open the post in Elementor, wait until every section has loaded and run `$e.run('document/save/update', {force: true})`. Check the live page shows the new section.
   - Pins: on ridewithgps.com in Ben's session, paste scripts/push/pins.js with ITEMS set to the plan's pins list and run it. It saves the pin text and republishes the Experiences.
   - Run `plan` again after the next rebuild: `inStep: true` means done.
   - A new pin (a new place on a ride) is still placed by hand in the POI Library and added to its rides (see the ride stories doc); then add it to the entry's `pins`.
5. Update the ride stories doc if the change settles a ruling.

No git push in the session (a scheduled task whose push is refused): save the changed files on github.com in Chrome on Ben's laptop instead, straight to main. Open https://github.com/elementoutdoors/routes/upload/main/<folder>, give the page's file input the changed files straight from the session's clone with the file_upload tool (it only accepts files inside the session's working directory), choose "Commit directly to the main branch" and commit (library/ first, the generated config/ files last). Then check each file on raw.githubusercontent.com matches byte for byte. Never type a file into the web editor: it adds brackets and indents as you type. Ben's Desk "laptop fixes" task does this for any Story Library card the cloud task could not save.

No Chrome in the session: commit the library change anyway. The Ride Guide and EO Crew follow it, and the weekly Story Library check pushes the blogs and pins from Ben's laptop.

## Never

- Edit config/stories.json, config/place-record.json, a blog section, a pin's text or an EO Crew wildlife card or kayak talking point directly. Those edits are overwritten by the library. Change the library.
- Put a fact in the library that contradicts the Product Truth or a ruling.
- Use em or en dashes between words, left or right directions, or "one of only two everglades" without "often described as" (`lint` catches these).

## Checks

- Every build: the committed generated files match the library (else health.json problem), house rule findings are listed in health.json "library".
- Weekly, Drift Check Register "Story Library": live blogs and pins match the library (the run puts the library version back), EO Crew is in step, house rule findings and contradictions with the Product Truth go to Ben as review cards.
- Weekly, Product Truth check: the library is one of the things reviewed against the Product Truth.
