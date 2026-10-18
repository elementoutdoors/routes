"""Small text helpers shared by the sheet, the map render and the checks (no third party packages)."""
import re


def h1pt(title):
    return round(min(30, 200 / (len(title) * 0.8 * 0.3528)), 1)


FIXES = [('\\s*[\u2014\u2013]\\s*', ', '), (r'\b[Ee]-?[Bb]ike(s?)\b', r'e-Bike\1'), (r'\bMary Magic\b', 'Magic Mary'),
         (r'\bWondum\b', 'Woondum'), (r'\bMount Mothar\b', 'Mothar Mountain'), (r'\bMother Mountain\b', 'Mothar Mountain'),
         (r'\bRock Pools\b', 'rock pools'), (r'\b[Rr]ide time\b', 'riding time')]


def house_style(text):
    """House spellings and no dashes between words (the checks in check.py look for the same things)."""
    for a, b in FIXES:
        text = re.sub(a, b, text)
    return text


def story(desc, names, limit=640):
    """The ride's description as up to two paragraphs: a first line that only repeats the ride's name is left out."""
    norm_ = lambda s: re.sub(r'[^a-z0-9]+', ' ', s.lower()).strip()
    paras = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', (desc or '').replace('\r', '').strip()) if p.strip()]
    while paras and len(paras[0]) < 90 and (norm_(paras[0]) in [norm_(n) for n in names] or not re.search(r'[.!?]$', paras[0]) and len(paras) > 1 and len(paras[0].split()) < 12):
        paras = paras[1:]
    for i, p in enumerate(paras):   # a lead in to a list ("Before you roll:") ends the story
        if p.endswith(':') or re.match(r'^[-*\u2022]', p):
            paras = paras[:i]; break
    paras = [house_style(p) for p in paras]
    out, used = [], 0
    for p in paras:
        if used + len(p) <= limit:
            out.append(p); used += len(p)
        else:
            room = limit - used
            cut = [m.end() for m in re.finditer(r'[.!?](?=\s)', p[:room])]
            if cut and cut[-1] > 60:
                out.append(p[:cut[-1]])
            break
        if len(out) == 2:
            break
    return out
