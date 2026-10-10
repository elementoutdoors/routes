# Translation brief for Ride Guide

Ride Guide is a phone web app for self-guided e-bike tours around Noosa, Queensland, Australia, run by By Earth and Ocean.
Riders hear directions spoken by their phone's voice and read them on screen while riding, so translations must be
short, natural and easy to understand when heard once.

## Input and output
- Input: `i18n-missing.json` in the repo root. The key for your language holds a list of English strings.
- Output: `config/i18n/<lang>.json`, a JSON object mapping each English string, copied exactly as the key, to its translation.
  If the file already exists, keep its entries and add the new ones.
- Write the file with Python (`json.dump(obj, f, ensure_ascii=False, indent=1)`) so quoting is always valid.

## Rules
1. Keep every placeholder in braces exactly as it is: `{n}`, `{dist}`, `{time}`, `{name}`, `{text}`, `{h}`, `{m}`.
2. Keep proper names unchanged: street and road names (Venture Drive, Gateway Drive, Cooroy Noosa Road), places
   (Lake Doonella, Lake Weyba, Noosa Spit, Noosa North Shore, Mt Tinbeerwah, Tewantin), businesses and brands
   (Land and Sea Brewery, Flightschool Noosa, By Earth and Ocean, Bike On, Ride Guide). You may add a short generic word
   for clarity where the language needs it (for example a word for "street" before or after the name), never replace the name.
3. Directions are spoken instructions to a cyclist. Use the natural imperative your language uses for navigation.
4. Safety, legal and money text (caution notes, ferry fees, tide warnings, damage and cleaning charges) must be translated
   completely and faithfully. Do not shorten, soften or leave anything out.
5. Unit strings: translate the unit word (`{n} metres` -> the word for metres). Keep numbers as placeholders.
6. Do not use em dashes or en dashes between words. Use a comma, colon or full stop instead.
7. Keep line breaks (`\n`) where the English has them.
8. If an English string has a typo (for example "Welcom"), translate the intended meaning.
9. Language notes: `zh` is Simplified Chinese (mainland). `ja` uses polite but concise forms suited to navigation.
   `ko` uses polite forms (하세요 style). `de`, `fr`, `es`, `it`, `nl` use the informal-polite register common in
   consumer apps for that language (de: "Sie" is fine for safety text; be consistent within the file).
10. Translate every string. Do not leave any value in English unless it is only a proper name.

## Check before you finish
Run a Python check that: the output parses as JSON; every English string from the input list is a key; every placeholder in
a key appears in its value; no value is empty; no value contains an em dash (U+2014) or en dash (U+2013) between words.
Fix anything that fails, then report a one-line summary (count translated, and any strings you were unsure about).
