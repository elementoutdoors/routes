# Full stories: how to write and keep them

The full stories in config/stories.json are what the natural voice reads when a rider taps "Hear the full story" on a stop. Each one is a spoken version of that place's section on the ride story blogs:

- Bike On: https://bikeon.com.au/noosa-self-guided-rides-what-you-will-see/
- By Earth and Ocean: https://byearthandocean.com.au/noosa-hinterland-self-guided-rides-places/

A stop gets a story when its Ride with GPS link points at one of those pages with an anchor (for example #lake-doonella). One story per place, used by both brands.

## Writing for the ear
- About a minute when read aloud: 100 to 180 words, in 3 or 4 short paragraphs. Each paragraph is recorded on its own, so keep each under about 600 characters.
- Short sentences, one idea each. No brackets, semicolons, lists of more than three things, or footnote style detail.
- Spell out units in words (metres, kilometres, hectares). Years as digits are fine. Round where the exact figure adds nothing ("about 600 acres").
- Facts only from the blog section (and its sources in the ride stories doc). Never add a fact, date or number that is not there.
- House rules: Australian spelling. No em or en dashes between words. Say "Noosa Everglades system" in full; Lake Weyba is its southern end ("southern gateway"); the "one of only two everglades in the world" line is always "often described as". Aboriginal place name meanings only as the sources give them ("is said to mean", "is often translated as" where they differ). Be respectful about Kabi Kabi sites and history.
- No directions like "on your left": riders come from both ways.
- Names the voice says wrongly are fixed in config/speech.json "names" (a respelling), not in the story text. listen.html on the site plays every name.

## Keeping them in step with the blogs
The nightly build reads both blogs and fingerprints each place's section. health.json "stories" lists:
- stale: the blog section changed since the story was written. Rewrite the story from the section as it is now, then set that blog's entry in the story's "src" to the fingerprint in health.json stories.current ("<brand>#<key>").
- unchecked: a story with no fingerprint yet for that blog. If the story still matches the section, just record the fingerprint.
- missing: a stop links to a place that has no story. Write one (title, paras) from the blog section and record its fingerprint.
- noSection: a stop links to an anchor the blog does not have. Fix the link in Ride with GPS or the anchor on the blog.
A rewritten story is re-recorded and re-translated by itself (the build records it, the weekly check translates the new paragraphs).

## The places record (from 11/10/2026)
The blogs are not the last word on a place. The record of truth for places is the "Places record" tab of the ride stories doc
(https://claude.ai/code/artifact/a698e78e-221d-4f1c-8658-d58461c85558): the facts Ben approved and his rulings. Safety, price and
product lines in any stop or story (tides, the ferry, recovery fees, e-Bike rules) follow the Element Outdoors Product Truth.

`config/place-record.json` holds the agreed text of every place's blog section ("sections", key `brand#anchor`) and of every
Ride with GPS stop summary that links to one ("stops", key `brand#anchor|Pin name`). The nightly build compares the live blogs and
Ride with GPS with it and lists each difference in health.json "places"; `scripts/check.mjs` passes them on as "placeChanges",
each with before and after. Change the record only with `scripts/place-record.mjs`, never by hand.

### Deciding each difference (weekly check)
Read the Places record tab first (rulings and house rules), and the Product Truth for anything about safety, price or product.
- Wording only: same facts, said differently, reordered, shortened, or colour added with no new date, number or name.
  Agree it: `node scripts/place-record.mjs accept <section|stop> "<id>"`. For a blog section, also rewrite the story as above.
  Then check the place's stop summaries and the other brand's section for the same anchor still agree with it on facts.
- A change of fact: a date, year, number, height, distance, name or spelling, who did something, what a place is, a hard fact added
  or taken away, or anything that contradicts a ruling or the Product Truth. Do not agree it. Open a card on the Ride Story Review
  page (below), then `node scripts/place-record.mjs pending <section|stop> "<id>" <card id>`. While a stop summary is pending
  the app keeps the agreed summary; while a section is pending its story is not rewritten. Commit "Places record (weekly check)".
- New (in "unrecorded"): check it against the place's blog section, its stop summaries and the rulings. Consistent: agree it.
  A contradiction: card, and record it only once Ben has ruled.
- Gone (in "gone"): a pin taken off or a section removed. If it was clearly meant (Ben said so, or the place was renamed and
  the new one is listed as new), `drop` it. Otherwise Needs Ben.
- A difference that matches the "after" of a card already applied is agreed straight away.
House style slips in a stop summary (a dash between words, "on your left", "ahead") are wording: propose the fix on a card in the
"House style" group so it goes through with his other clicks; never leave them silently.

### The Ride Story Review page
https://claude.ai/artifact/XSdaNvQMw8tYpaqSiBz7Tp (shared database, written with ArtifactData).
- Collection "cards", one document per card id (kebab case, unique):
  `{ id, group, title, why, opened, ids: ["<what>:<id>", ...], options: [ { key: "a"|"b", label, says, where, then: [ { where, before, after } ] } ], note, status: "open"|"applied", applied }`.
  Option "a" is the agreed (or blog) version, "b" the new (or stop) version. `says` quotes the fact exactly. `then` lists every
  change that choosing it needs, with exact before and after text, including the story in config/stories.json when it changes.
- Collection "decisions", written by the page: `{ choice: "a"|"b"|"other", note, title, updatedAt }`. "other" means his note says
  what is right; apply that.
- After a decision: make every change in the chosen option's `then` (or the note). Stories and the record: in the repo.
  Ride with GPS: edit the POI Library pin (it changes on every ride) in Ben's Ride with GPS session in Chrome on his laptop.
  After any pin edit, republish every Ride with GPS Experience whose publish_status is "updates" (GET /experiences.json?club_id=15663,
  then POST /experiences/<id>/publish.json with the page's CSRF token, in Ben's Ride with GPS session), so riders on the Ride with
  GPS app get it too.
  Blogs: edit through the WordPress REST API in a Chrome signed in to that site (change the same words in content and in the
  _elementor_data meta), then open the post in Elementor and save it once the editor has loaded every section. As of 11/10/2026
  only the upstairs Chrome is signed in to bikeon.com.au, and none to byearthandocean.com.au; ask Ben to sign in. Then `accept` each
  id once the live text matches, set the card's status to "applied" with the date, and, if the ruling settles a fact that could
  come up again, add it to the Rulings list on the Places record tab. No Chrome on this run: leave the card decided and
  unapplied; it is applied on the next run. A decision older than two weeks still unapplied = Needs Ben.
