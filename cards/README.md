# Digital business cards

Ben's digital business cards. Someone scans the QR code on Ben's phone, the card opens in their browser, and
"Save contact" adds him to their phone with the brand logo as the contact picture.

| Card | Opens at |
| --- | --- |
| Ben de Vaus, Director, Bike On | https://elementoutdoors.github.io/routes/card/ben-bikeon/ |
| Ben de Vaus, Director, By Earth and Ocean | https://elementoutdoors.github.io/routes/card/ben-beo/ |
| Ben de Vaus, Head Coach / Director, Bike On MTB Coaching | https://elementoutdoors.github.io/routes/card/ben-mtb/ |
| Matt Watts, General Manager, Bike On | https://elementoutdoors.github.io/routes/card/matt-bikeon/ |
| Matt Watts, General Manager, By Earth and Ocean | https://elementoutdoors.github.io/routes/card/matt-beo/ |
| Matt Watts, General Manager, Element Outdoors | https://elementoutdoors.github.io/routes/card/matt-eo/ |

Each card folder also holds `lock-screen.png` (1179 x 2556, set as the phone's lock screen to show the QR code),
`qr.png` and `qr.svg` (for print, slides and email) and the contact file itself.

## Changing a card

Change `cards/cards.json`, nothing else, and push. The cards workflow (`.github/workflows/cards.yml`) checks the
change, and the site build publishes it within the hour. The web address of a card never changes, so printed or
saved QR codes keep working after any change of details.

- New card (for example Matt, or a guide): add a person under `people` if needed and a line under `cards` with a
  new `slug`. Run `python3 cards/build.py`, commit `cards/` and `site/card/`.
- Never edit anything in `site/card/` by hand. It is rebuilt from `cards.json` and a hand edit is undone by the check.
- Images live in `cards/assets/` (sources). The page uses copies resized by the build.

## How it stays right

- `python3 cards/build.py --check` rebuilds everything in memory and compares: the pages, contact files and QR
  SVGs must match byte for byte, the lock screens and QR PNGs must have been made from the current details
  (fingerprint in `site/card/manifest.json`), and every QR code is decoded and must open its own card.
- `python3 cards/build.py --live` also checks the published pages and contact files match this repo, and that
  the websites and social links on the cards still answer.
- The workflow runs the check on every change and every Monday at 7:23am Brisbane. Anything stale or edited by
  hand is rebuilt and committed by the workflow itself. If the live site is behind, it starts the site build and
  checks again. It only fails when it cannot fix the problem itself (a website or social link that has gone).
- The weekly "Element Outdoors drift checks" task reads this workflow's last run (Drift Check Register row
  "Digital business cards") and also checks the card details against the business facts (phones, address,
  hours, emails, titles).

## Notes

- Bike On logo: made from the vector Bike Hire logo (`ride-sheets/assets/bikeon-logo.svg`) with the BIKE HIRE line
  and the strapline erased, the same way the "Main Logo, No Text" email signature logo was made. Nothing redrawn.
- Bike On MTB Coaching logo: the email signature copy (340 px wide), the only copy outside OneDrive. If the full
  size `BikeOn-MTB-Coaching-LS-BlueBlack.png` (3508 x 1662) is ever put in `cards/assets/logo-bikeon-mtb.png`, the
  next build uses it.
- Photos: Bike On = professional gravel shoot HinterlandGravel-039 and Element Outdoors = HinterlandGravel-041 (1600 px copies of the OneDrive originals, credit By Earth and Ocean, Noosa); Ben's MTB card = Ben coaching (Program-Feature-4 on bikeon.com.au, his pick); By Earth and Ocean = guided kayak photo from byearthandocean.com.au. A card can carry its own `photo`, `photo_focus` and `photo_size` (for example `200% auto` to zoom in).
- Element Outdoors card: elementoutdoors.com.au is not a business website, so the card lists both brand websites and both brands' socials instead. Logo is the 240 px signature copy.
- A person without a `mobile` (Matt) gets no mobile row; Call rings the shop.
- Colours: Bike On brand kit (site blue for structure, Trail Orange for Save contact); By Earth and Ocean designer
  palette (Deep Navy, Sunlit Gold).
