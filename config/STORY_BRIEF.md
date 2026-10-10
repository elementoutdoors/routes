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
