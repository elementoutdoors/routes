"""The Ride Desk's cards (config/ride-desk.json), as the ride sheets read them.

The Ride Desk page (https://claude.ai/artifact/9XG8MDnUm5k5RCFyXUko18) is the master for each sheet's words: title,
category, sell line, highlights, level, surface, terrain, recommended bike, the note and the photo, plus whether the ride is
on the hire desk iPad and in the booklet (Ben, 18/10/2026). The "Ride Guide settings apply" scheduled task copies the cards
into config/ride-desk.json. Staff sections never come here (they are sealed, see scripts/ride-desk.mjs).
"""
import json, os, re
from paths import ROOT

FILE = os.path.join(ROOT, 'config', 'ride-desk.json')


def cards():
    with open(FILE) as f:
        return json.load(f).get('rides', {})


def text(s):
    """Card text as it goes on the sheet: trimmed, and never markup (a < or > is shown as typed)."""
    return re.sub(r'\s+', ' ', str(s or '')).strip().replace('<', '&lt;').replace('>', '&gt;')


def kick(category):
    """The category pill: the card says "Hinterland gravel · point to point"; the sheet writes the dot as &middot;."""
    return text(category).replace(' · ', ' &middot; ').replace('·', '&middot;')


def stats(card):
    """The sheet's six stat boxes. None is filled from the Ride Guide (distance, climbing, riding time); a card with a
    terrain shows it in place of the climbing (a flat ride says "Flat"). Level, surface and bike only when the card has them."""
    out = [None, ((text(card.get('terrain')), 'Terrain') if text(card.get('terrain')) else None), None]
    if text(card.get('level')): out.append((text(card['level']), 'Level'))
    if text(card.get('surface')): out.append((text(card['surface']), 'Surface'))
    if text(card.get('bike')): out.append((text(card['bike']), text(card.get('bikeNote'))))
    return out


def photo_cfg(all_cards):
    """The photo choice in the shape living.photo_choice reads: "pages" (the Bike On website page whose featured image is
    the default) and "photos" (a photo picked on the card: an upload copied into the repo, a link, or a stop photo)."""
    pages, photos = {}, {}
    for slug, c in all_cards.items():
        if c.get('websitePage'):
            pages[slug] = c['websitePage']
        p = c.get('photo') or {}
        if p.get('source') == 'upload' and p.get('file'):
            photos[slug] = p['file']
        elif p.get('source') in ('link', 'ride') and str(p.get('url') or '').startswith('https://'):
            photos[slug] = p['url']
    return {'pages': pages, 'photos': photos}
