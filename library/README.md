# Story Library

The one place every Element Outdoors story is written. Everything else is a copy made from it:

| Copy | How it follows the library | When |
| --- | --- | --- |
| Ride Guide app (stops, full stories, natural voice, 8 languages) | The build reads the library directly | Every push and every night, 3:07am |
| EO Crew: Know Noosa | Copies the spoken stories and recordings (stories-voice.json) | Daily |
| EO Crew: wildlife cards, the kayak talking points in the tour manual, and Kabi Kabi Country and Noosa facts (Places and stories) | Copies them from library.json on the Ride Guide site, read only in the app | Daily |
| Bike On and By Earth and Ocean ride story blogs | Pushed through Chrome (scripts/push/blog.js) | In the session that changes the library, and the weekly check puts back any difference |
| Ride with GPS POI Library pins (the line read out on arrival) | Pushed through Chrome (scripts/push/pins.js), then Experiences republished | Same as the blogs |
| config/stories.json, config/place-record.json | Generated (`node scripts/library.mjs generate`), never edited | With every library change |

Read it as a page: https://elementoutdoors.github.io/routes/library.html

## What is in it

One JSON file per entry, named by its key.

- `places/`: a place on our rides. `blog` holds each brand's blog section (heading, the area it sits in, the section it follows, paragraphs as HTML with links only). `pins` holds each brand's Ride with GPS POI Library pins (name, and the text read aloud on arrival). `story` is the full spoken story, about a minute, written to be heard (config/STORY_BRIEF.md). A pin can carry its own `story` when the entry's story would not make sense at that spot (Weyba Creek mangroves: beside the bridge, not on it). Ben, 15/10/2026: these spot versions are spoken only and never go on a blog; the blog keeps the one section in `blog`.
- `stops/`: a stop on a guided or self guided tour that is not on a blog, such as the Stingrays and Everglades kayak stops. `tours` gives the tour and stop number, `talk` holds the guide notes shown in the EO Crew guide manual: need to know (points, engage: how to engage the group at the stop, say_it) and nice to know for senior guides (detail, detail_blocks), `story` the spoken story, `origin` where it came from.
- `info/`: information that isn't spoken or blogged (12/11/2026): `group` is `kabi-kabi` (Kabi Kabi Country: history, language, place names) or `noosa-facts` (the fun facts guides chat about). `info` holds `points` (need to know) and `detail_blocks` (nice to know), plus `order` within its group and `sources`. An info entry never has a story, blog or pins (the loader refuses one), so it can never change the Ride Guide, the blogs or the pins. EO Crew shows these in Resources, Places and stories, and in the manuals.
- `wildlife/`: an animal. `card` holds the EO Crew wildlife card (name, scientific and local names, group, description, detail, how to spot, conservation, photo, source). `story_key` names the place or stop story its talking points come from.

Every entry has `key`, `kind`, `title`, `status` (live, draft or retired) and `updated` (the Brisbane date of the last change). `lint_ok` lists house rule findings Ben has accepted for that entry.

## Changing a story (any session)

1. Content comes from Ben (voice notes, rulings) or research he has asked for. Facts follow the Product Truth for anything about safety, price or product, and the rulings on the Places record tab of the ride stories doc (https://claude.ai/code/artifact/a698e78e-221d-4f1c-8658-d58461c85558). A change of fact Ben has not given or ruled on goes to him first as a card on the Ride Story Review page (https://claude.ai/artifact/XSdaNvQMw8tYpaqSiBz7Tp), never straight into the library.
2. Edit the entry's file. Keep every copy of the same fact in step inside the entry: if a blog section changes, rewrite the spoken story and the pin line to match, for both brands. Set `updated`.
3. `node scripts/library.mjs lint` (house rules) and `node scripts/library.mjs generate`, then commit "Story Library: <what changed>" and push. The Ride Guide rebuilds in about 3 minutes; EO Crew picks it up within a day.
4. Push to the blogs and pins: wait for the rebuild, run `node scripts/library.mjs plan`, then in Chrome on bens-pc (Ben's always-on Azure PC, Claude in Chrome browser ID 128575f4-462a-4686-8143-f8ec12e40336; signed in to the Bike On WordPress as of 15/10/2026). Ben's laptop and the upstairs computer are fallbacks only:
   - Blogs: open a wp-admin page of the blog, paste scripts/push/blog.js with ITEMS set to that brand's plan items, run it, then open the post in Elementor, wait until every section has loaded and run `$e.run('document/save/update', {force: true})`. Check the live page shows the new section.
   - Pins: on ridewithgps.com in Ben's session, paste scripts/push/pins.js with ITEMS set to the plan's pins list and run it. It saves the pin text and republishes the Experiences.
   - Run `plan` again after the next rebuild: `inStep: true` means done.
   - A new pin (a new place on a ride) is still placed by hand in the POI Library and added to its rides (see the ride stories doc); then add it to the entry's `pins`.
5. Update the ride stories doc if the change settles a ruling.

No git push in the session (a scheduled task whose push is refused): save the changed files on github.com in Chrome on bens-pc instead, straight to main. Open https://github.com/elementoutdoors/routes/upload/main/<folder>, give the page's file input the changed files straight from the session's clone with the file_upload tool (it only accepts files inside the session's working directory), choose "Commit directly to the main branch" and commit (library/ first, the generated config/ files last). Then check each file on raw.githubusercontent.com matches byte for byte. Never type a file into the web editor: it adds brackets and indents as you type. Ben's Desk computer task (on bens-pc) does this for any Story Library card the cloud task could not save.

No Chrome in the session: commit the library change anyway. The Ride Guide and EO Crew follow it, and the weekly Story Library check pushes the blogs and pins from bens-pc.

## Changes made in EO Crew (the Story Library editor)

Since 6/11/2026 Ben and the managers change stories in EO Crew (Resources > Story Library, or "Change this story" on a place, a wildlife card or a kayak talking point). EO Crew can't write to GitHub, so each change waits there as a StoryEdit record (Base44 app EO Crew, id 6abba75b48155c78238d4cba) and EO Crew shows it straight away; the daily EO Crew sync leaves that entry alone while the edit is open (status Pending or Needs Ben). The nightly "Ride Guide settings apply" scheduled task (2:41am Brisbane, cloud) brings them into the library, step 11 of its prompt, by this procedure:

1. With the Base44 connector, query StoryEdit with status Pending (oldest first). None: done. For each, `changes` holds the whole editable part of the entry: a stop `{talk: {points, engage, say_it, detail, detail_blocks}, story}`, a place `{story, blog: {brand: {heading, paras}}, pins: {brand: [{name, text, story?}]}}`, a wildlife entry `{card: {other_names, scientific_name, local_name, group, description, detail, how_to_spot, conservation}}`, an info entry `{info: {points, detail_blocks}}`. `parts` names what differs, `note` says why, `by_name` who.
2. If the entry's `updated` in the library is newer than the edit's `base_updated`, someone changed the library since: apply only the parts the edit changed, and if the library also changed one of those same parts, do not choose between them; treat it as a finding (step 4).
3. Check the new wording against the Product Truth (Claude Docs export as markdown, container {"kind":"project","id":"12524029-f8f9-4a76-ae91-53744c3a843b"}, file "f57659f5-3277"; note its rev) and the rulings in the ride stories doc, following the product-truth-review rules: only real contradictions of a position count (times, prices, ages, group sizes, safety rules, product and place names, house spellings, the Noosa Everglades system wording). Different wording of the same position is fine. Also run `node scripts/library.mjs lint` after writing (step 5): a new house rule finding in the changed text is a finding.
4. A finding: do not write that edit. Update the StoryEdit (update_entities, query by id): status "Needs Ben", check_note one plain sentence (what it says, what the Product Truth says), desk_card "story-edit-<key>". Put a decide card on Ben's Desk (ArtifactData, url https://claude.ai/artifact/YGE5oznqmZ26StQaAuKRTd, collection cards, id = desk_card; skip if it exists and is open): area "Story Library", kind "decide", title "<entry title>: a story change disagrees with the Product Truth", where "Story Library: <key> (<part>)", now (the new words, short), rule (the Product Truth position), proposed (the words changed to agree), choices ["My wording is right: update the Product Truth", "Product Truth is right: use the proposed words"], and apply (the next sentence, word for word, so the desk task knows what to do). When Ben answers, the desk task either changes the Product Truth (with a change log line) and sets the StoryEdit back to Pending, or puts the proposed words into the StoryEdit's changes and sets it back to Pending; the next nightly run takes it.
5. No finding: write `changes` into library/<kind folder>/<key>.json (stops: talk.points, talk.engage, talk.detail, talk.detail_blocks, talk.say_it only when not empty, story; places: story, each blog brand's heading and paras, each pin's text and story by name; wildlife: the card fields listed; info: info.points and info.detail_blocks). Keep every other field. Set `updated` to today (Brisbane). Keep the copies in step inside the entry, as for any change (Changing a story, step 2): if a place's spoken story changed a fact and its blog and pin weren't changed with it, carry the same fact into them with the smallest wording change; if that can't be done cleanly, it is a finding (step 4) asking Ben to write the blog line. Run lint and generate, commit "Story Library: <title> (EO Crew change by <by_name>)" with the note in the body, push.
6. After the Ride Guide rebuild (about 4 minutes), check https://elementoutdoors.github.io/routes/library.json (no cache) shows the entry's new `updated` and wording. Then update the StoryEdit: status "In the library", commit (short sha), done_at now, check_note "In the library <date>, checked against Product Truth rev <n>". Not live after 12 minutes: leave it Pending (tomorrow's run tries again; EO Crew Health lists an edit still waiting after 36 hours).
7. The blogs and Ride with GPS pins follow through the weekly Story Library check, which pushes whatever the library holds.

Ben's rule of 6/11/2026: every story change, wherever it's made, goes through the Product Truth check before it is in the library.

## Never

- Edit config/stories.json, config/place-record.json, a blog section, a pin's text or an EO Crew wildlife card or kayak talking point directly. Those edits are overwritten by the library. Change the library.
- Put a fact in the library that contradicts the Product Truth or a ruling.
- Use em or en dashes between words, left or right directions, or "one of only two everglades" without "often described as" (`lint` catches these).

## Checks

- Every build: the committed generated files match the library (else health.json problem), house rule findings are listed in health.json "library".
- Weekly, Drift Check Register "Story Library": live blogs and pins match the library (the run puts the library version back), EO Crew is in step, house rule findings and contradictions with the Product Truth go to Ben as review cards.
- Weekly, Product Truth check: the library is one of the things reviewed against the Product Truth: every place story, blog section, pin line, kayak talking point (points, how to engage, say it, nice to know) and wildlife card.
- Nightly, the Ride Guide settings apply task: every change made in EO Crew's Story Library editor is checked against the Product Truth before it goes in (above).
- Hourly, EO Crew Health on Ben's Desk: an EO Crew story change still not in the library after 36 hours, or held for Ben.
