# Full stories: how to write and keep them

Every story lives in the Story Library (library/, read library/README.md first). The full story in each library entry is what the natural voice reads when a rider taps "Hear the full story" on a stop, and what staff read and hear in EO Crew's Know Noosa. config/stories.json is generated from the library and never edited.

A place's story is a spoken version of that place's section on the ride story blogs, and both are kept in the same library entry:

- Bike On: https://bikeon.com.au/noosa-self-guided-rides-what-you-will-see/
- By Earth and Ocean: https://byearthandocean.com.au/noosa-hinterland-self-guided-rides-places/

A stop gets a story when its Ride with GPS link points at one of those pages with an anchor (for example #lake-doonella). One story per place, used by both brands.

## Writing for the ear
- About a minute when read aloud: 100 to 180 words, in 3 or 4 short paragraphs. Each paragraph is recorded on its own, so keep each under about 600 characters.
- Short sentences, one idea each. No brackets, semicolons, lists of more than three things, or footnote style detail.
- Spell out units in words (metres, kilometres, hectares). Years as digits are fine. Round where the exact figure adds nothing ("about 600 acres").
- Facts only from the library entry (its blog section, and the sources in the ride stories doc). Never add a fact, date or number that is not there.
- House rules: Australian spelling. No em or en dashes between words. Say "Noosa Everglades system" in full; Lake Weyba is its southern end ("southern gateway"); the "one of only two everglades in the world" line is always "often described as". Aboriginal place name meanings only as the sources give them ("is said to mean", "is often translated as" where they differ). Be respectful about Kabi Kabi sites and history.
- No directions like "on your left": riders come from both ways.
- Names the voice says wrongly are fixed in config/speech.json, never in the story text: "pronounce" (the exact sound as IPA, for the natural voice, first choice; Noosa is there) or "names" (a respelling, also used by the phone voice). listen.html on the site plays every name.

## Keeping everything in step (from 11/10/2026)
The library is the master. When a blog section changes in the library, its story and pin lines are rewritten in the same entry, in the same change. The nightly build compares the live blogs and Ride with GPS pins with the library (health.json "places", made from the generated config/place-record.json) and fingerprints each blog section against its story ("stories"):
- A live blog section or pin that differs from the library: someone edited the copy. Put the library version back (scripts/push, library/README.md). If the edit looks like a deliberate change of fact, also open a Ride Story Review card so Ben can rule on adding it to the library.
- missing: a stop links to a place with no story. Write one in the library entry from its blog section.
- noSection: a stop links to an anchor the blog does not have. Fix the link in Ride with GPS, or push the library section to the blog.
- New on the blog or the rides but not in the library ("unrecorded" with no entry): add it to the library if Ben meant it, else remove it.
Facts in the library follow the Product Truth (safety, price, product) and the rulings on the Places record tab of the ride stories doc (https://claude.ai/code/artifact/a698e78e-221d-4f1c-8658-d58461c85558). A change of fact goes to Ben as a review card before it enters the library.

## The Ride Story Review page
https://claude.ai/artifact/XSdaNvQMw8tYpaqSiBz7Tp (shared database, written with ArtifactData).
- Collection "cards", one document per card id (kebab case, unique):
  `{ id, group, title, why, opened, ids: ["<what>:<id>", ...], options: [ { key: "a"|"b", label, says, where, then: [ { where, before, after } ] } ], note, status: "open"|"applied", applied }`.
  Option "a" is the agreed (or blog) version, "b" the new (or stop) version. `says` quotes the fact exactly. `then` lists every
  change that choosing it needs, with exact before and after text, including the library entry (blog section, pin line, story) when it changes.
- Collection "decisions", written by the page: `{ choice: "a"|"b"|"other", note, title, updatedAt }`. "other" means his note says
  what is right; apply that.
- After a decision: make every change in the chosen option's `then` (or the note) in the Story Library entry, generate, commit and push, then push the blogs and pins (library/README.md).
  Ride with GPS: edit the POI Library pin (it changes on every ride) in Ben's Ride with GPS session in Chrome on bens-pc (his always-on Azure PC).
  After any pin edit, republish every Ride with GPS Experience whose publish_status is "updates" (GET /experiences.json?club_id=15663,
  then POST /experiences/<id>/publish.json with the page's CSRF token, in Ben's Ride with GPS session), so riders on the Ride with
  GPS app get it too.
  Blogs: edit through the WordPress REST API in a Chrome signed in to that site (change the same words in content and in the
  _elementor_data meta), then open the post in Elementor and save it once the editor has loaded every section. As of 11/10/2026
  the upstairs Chrome is signed in to both bikeon.com.au and byearthandocean.com.au WordPress; if a site asks to log in, ask Ben to sign in. Once `node scripts/library.mjs plan` shows them in step, set the card's status to "applied" with the date, and, if the ruling settles a fact that could
  come up again, add it to the Rulings list on the Places record tab. No Chrome on this run: leave the card decided and
  unapplied; it is applied on the next run. A decision older than two weeks still unapplied = Needs Ben.

## Stories with no blog
Some stories are not on either blog: the Stingrays and Everglades Kayak Tour stops (kabi-kabi-country, noosa-private-airport, noosa-everglades, keyser-creek, weyba-mangroves, stingray-sanctuary). They live in library/stops/ with the guide talking points shown in the EO Crew tour manual, and carry "origin" (where the facts come from: the tour manual EO-TR-11 and the What's Up Down Under episode with guide Matt Smith) and an empty "src". The nightly fingerprint check only looks at blog sections, so these are never reported stale or unchecked. They follow the same writing rules, plus the Product Truth kayak wording ("Weyba is understood to mean place of stingrays", "often described as one of only two everglades systems", never "protected", stingrays often seen never guaranteed, bull sharks are guide knowledge only and stay out of stories). Change them only from their origin, with Ben.

## Every story is recorded, and published for EO Crew
Every story in the library is recorded in the natural voice (English), whether or not a ride stop links to it. The build publishes stories-voice.json on the site: each story's title, origin and paragraphs, with the recording for each paragraph (null until recorded). The EO Crew staff app (Know Noosa) reads that file nightly, so staff read and hear exactly what riders hear. Do not rename a library key without telling the EO Crew project: tours and quizzes there link to stories by key. scripts/check.mjs checks stories-voice.json each week.
