#!/usr/bin/env python3
"""Element Outdoors digital business cards.

cards/cards.json is the only source. This script makes, for every card, under site/card/<slug>/:
  index.html        the card page the QR code opens (Save contact, call, email, website, socials, share)
  <name>.vcf        the contact file "Save contact" downloads (vCard 3.0, with the brand logo as the photo)
  qr.svg, qr.png    the QR code for the page (print, email, slides)
  lock-screen.png   a 1179 x 2556 phone wallpaper with the QR code, for showing on a phone screen
and shared files under site/card/assets/ (fonts, logos, photos).
The routes build copies site/ to GitHub Pages, so the cards go live with the next Ride Guide build.

  python3 cards/build.py           rebuild everything
  python3 cards/build.py --check   exit 1 if anything in site/card is missing, stale or hand edited
  python3 cards/build.py --live    also check the published pages, contact files and links

Drift safety: every output is rebuilt from cards.json plus the template and the source images. The text files
must match a fresh build byte for byte; the images carry a fingerprint of their inputs in site/card/manifest.json
and every QR code (on its own and on the lock screen) is decoded and must open its own card.
"""
import base64, hashlib, html, io, json, os, re, shutil, subprocess, sys, tempfile, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wallet
SRC = ROOT / 'cards'
OUT = ROOT / 'site' / 'card'
FONTS = ROOT / 'ride-sheets' / 'assets'
VERSION = '3'   # bump to force every image to be remade

def load():
    return json.loads((SRC / 'cards.json').read_text())

def sha(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
    return h.hexdigest()[:16]

def esc(s):
    return html.escape(str(s), quote=True)

# ---------------------------------------------------------------- card data

def card_view(cfg, c):
    p = cfg['people'][c['person']]
    b = dict(cfg['brands'][c['brand']])
    s = cfg['shared']
    for k in ('photo', 'photo_focus', 'photo_size'):   # a card may use its own photo (e.g. Ben coaching)
        if c.get(k): b[k] = c[k]
    if 'websites' not in b:
        b['websites'] = [{'label': 'Website', 'value': b['website_label'], 'url': b['website'], 'sub': b.get('website_sub', '')}]
    b.setdefault('footer', s['group_line'])
    full = f"{p['first']} {p['last']}".strip()   # a business card (no person) has the brand as first name and no last
    return {
        **c, 'person_data': p, 'brand_data': b, 'shared': s,
        'name': full,
        'url': cfg['base_url'] + c['slug'] + '/',
        'vcf_name': re.sub(r'[^a-z0-9]+', '-', (full if full == b['name'] else f"{full} {b['name']}").lower()).strip('-') + '.vcf',
    }

# ---------------------------------------------------------------- vCard

def vfold(line):
    """Fold a vCard line at 75 octets (RFC 6350 3.2)."""
    raw = line.encode('utf-8')
    if len(raw) <= 75:
        return line
    out, cur = [], b''
    for ch in line:
        e = ch.encode('utf-8')
        limit = 75 if not out else 74
        if len(cur) + len(e) > limit:
            out.append(cur.decode('utf-8')); cur = b''
        cur += e
    out.append(cur.decode('utf-8'))
    return '\r\n '.join(out)

def vesc(s):
    return str(s).replace('\\', '\\\\').replace(',', '\\,').replace(';', '\\;').replace('\n', '\\n')

def contact_photo(brand):
    """Square JPEG of the brand logo on white, for the contact's picture."""
    from PIL import Image
    logo = Image.open(SRC / 'assets' / brand['logo']).convert('RGBA')
    size, pad = 480, 44
    canvas = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    logo.thumbnail((size - 2 * pad, size - 2 * pad), Image.LANCZOS)
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    buf = io.BytesIO()
    canvas.convert('RGB').save(buf, 'JPEG', quality=86, optimize=True)
    return buf.getvalue()

def vcard(v):
    p, b, s = v['person_data'], v['brand_data'], v['shared']
    a = s['address']
    lines = [
        'BEGIN:VCARD', 'VERSION:3.0',
        f"N:{vesc(p['last'])};{vesc(p['first'])};;;" if not p.get('company') else 'N:;;;;',
        f"FN:{vesc(v['name'])}",
    ] + (['X-ABShowAs:COMPANY'] if p.get('company') else []) + [
        f"ORG:{vesc(b['name'])}",
        f"TITLE:{vesc(v['title'])}",
    ] + ([f"TEL;TYPE=CELL,VOICE,pref:{p['mobile_e164']}"] if p.get('mobile_e164') else []) + [
        f"TEL;TYPE=WORK,VOICE{'' if p.get('mobile_e164') else ',pref'}:{s['shop_phone_e164']}",
        f"EMAIL;TYPE=INTERNET,WORK,pref:{v['email']}",
    ] + [f"URL;TYPE=WORK:{w['url']}" for w in b['websites']] + [
        f"ADR;TYPE=WORK:;;{vesc(a['street'])};{vesc(a['locality'])};{vesc(a['region'])};{vesc(a['postcode'])};{vesc(a['country'])}",
    ]
    for so in b['social']:
        lines.append(f"X-SOCIALPROFILE;TYPE={so['type']}:{so['url']}")
    lines.append(f"NOTE:{vesc(v['tagline'] + '. ' + b['footer'] + '. Shop ' + s['shop_phone'] + ', ' + s['hours'] + '.')}")
    lines.append('PHOTO;ENCODING=b;TYPE=JPEG:' + base64.b64encode(contact_photo(b)).decode())
    lines.append(f"X-EO-CARD:{v['slug']}")
    lines.append('END:VCARD')
    return '\r\n'.join(vfold(l) for l in lines) + '\r\n'

# ---------------------------------------------------------------- QR

def qr_svg(url, color, scale=10, border=4):
    import segno
    q = segno.make(url, error='q', micro=False)
    buf = io.BytesIO()
    q.save(buf, kind='svg', scale=scale, border=border, dark=color, light='#FFFFFF', xmldecl=False, svgns=True, title=None, nl=True)
    return buf.getvalue().decode()

def qr_png(url, color, scale=24, border=4):
    import segno
    q = segno.make(url, error='q', micro=False)
    buf = io.BytesIO()
    q.save(buf, kind='png', scale=scale, border=border, dark=color, light='#FFFFFF')
    return buf.getvalue()

def qr_decode_png(png_bytes):
    """Every QR code found in an image (OpenCV)."""
    import cv2, numpy as np
    img = cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
    det = cv2.QRCodeDetector()
    ok, texts, _, _ = det.detectAndDecodeMulti(img)
    found = [t for t in (texts if ok else []) if t]
    if not found:
        t, _, _ = det.detectAndDecode(img)
        if t: found = [t]
    return found

# ---------------------------------------------------------------- icons (simple line icons, 24 x 24)

ICON = {
    'phone': '<path d="M5 3h3l2 5-2.5 1.5a11 11 0 0 0 7 7L16 14l5 2v3a2 2 0 0 1-2 2A17 17 0 0 1 3 5a2 2 0 0 1 2-2z"/>',
    'shop': '<path d="M3 9l1.5-5h15L21 9"/><path d="M4 9v11h16V9"/><path d="M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M10 20v-6h4v6"/>',
    'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    'web': '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18z"/>',
    'pin': '<path d="M12 21s-7-6.2-7-12a7 7 0 0 1 14 0c0 5.8-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    'instagram': '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none"/>',
    'facebook': '<path d="M14 8h3V4h-3a4 4 0 0 0-4 4v3H7v4h3v6h4v-6h3l1-4h-4V8z"/>',
    'youtube': '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.5v5l4.5-2.5z" fill="currentColor"/>',
    'save': '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/><path d="M5 21h14"/>',
    'share': '<path d="M12 15V3"/><path d="M7 8l5-5 5 5"/><path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"/>',
    'chev': '<path d="M9 6l6 6-6 6"/>',
}

def icon(name, cls='i'):
    return f'<svg class="{cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</svg>'

# ---------------------------------------------------------------- page

def wallet_block(v, wl):
    if not wl.get('apple') and not wl.get('google'):
        return ''
    parts = []
    if wl.get('apple'):
        parts.append(f'<a class="wb" href="{esc(wl["apple"])}"><img src="../assets/add-to-apple-wallet.svg" alt="Add to Apple Wallet" width="110" height="34"></a>')
    if wl.get('google'):
        parts.append(f'<a class="wb" href="{esc(wl["google"])}" target="_blank" rel="noopener"><img src="../assets/add-to-google-wallet.svg" alt="Add to Google Wallet" width="164" height="34"></a>')
    return ('<section class="share wallet"><h2>Keep it in your phone wallet</h2><p>Shows the QR code from your lock screen</p>'
            f'<div class="wbs">{"".join(parts)}</div></section>')

def page(v, asset_names, wl=None):
    wl = wl or {}
    p, b, s = v['person_data'], v['brand_data'], v['shared']
    c = b['colors']
    a = s['address']
    rows = ([('phone', 'Mobile', p['mobile'], 'tel:' + p['mobile_e164'], '')] if p.get('mobile_e164') else []) + [
        ('shop', 'Shop', s['shop_phone'], 'tel:' + s['shop_phone_e164'], s['hours']),
        ('mail', 'Email', v['email'], 'mailto:' + v['email'], ''),
    ] + ([] if b.get('our_brands') else [('web', w['label'], w['value'], w['url'], w.get('sub', '')) for w in b['websites']]) + [
        ('pin', 'Visit the shop', f"{a['street']}, {a['locality']} {a['region']} {a['postcode']}", s['maps_url'], ''),
    ]
    row_html = []
    for ic, label, value, href, sub in rows:
        ext = '' if href.startswith(('tel:', 'mailto:')) else ' target="_blank" rel="noopener"'
        subline = f'<span class="sub">{esc(sub)}</span>' if sub else ''
        row_html.append(
            f'<a class="row" href="{esc(href)}"{ext}>{icon(ic)}<span class="txt"><span class="lab">{esc(label)}</span>'
            f'<span class="val">{esc(value)}</span>{subline}</span></a>')
    social = ''.join(
        f'<a class="soc" href="{esc(so["url"])}" target="_blank" rel="noopener" aria-label="{esc(so.get("aria") or (b["name"] + " on " + so["label"]))}">{icon(so["type"])}<span>{esc(so["label"])}</span></a>'
        for so in b['social'])
    title_line = f"{v['title']}, {b['name']}"
    if len(b['websites']) == 1:
        quick_web = f'<a href="{esc(b["websites"][0]["url"])}" target="_blank" rel="noopener">{icon("web")}Website</a>'
    else:
        quick_web = f'<a href="#{"brands" if b.get("our_brands") else "links"}">{icon("web")}Websites</a>'
    desc = f"{v['name']}, {title_line}. {v['tagline']}."
    brands_html = ''
    if b.get('our_brands'):   # Element Outdoors cards: a tile per brand, each opening that brand's site
        tiles = ''.join(
            f'<a class="btile" href="{esc(t["url"])}" target="_blank" rel="noopener"><img src="../assets/{esc(t["logo"])}" alt="{esc(t["name"])}" loading="lazy">'
            f'<b>{esc(t["name"])}</b><span>{esc(t["sub"])}</span></a>' for t in b['our_brands'])
        brands_html = f'<section class="brands" id="brands" aria-label="Our brands"><h2>Our brands</h2><div class="bgrid">{tiles}</div></section>\n'
    qr = qr_svg(v['url'], c['qr'], scale=1, border=2)
    qr = re.sub(r'<svg[^>]*>', '<svg class="qr" viewBox="0 0 %s %s" role="img" aria-label="QR code for this card" xmlns="http://www.w3.org/2000/svg">' % qr_dims(v['url']), qr, count=1)
    logo_w, logo_h = asset_names['logo_size']
    return f'''<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(v['name'])} | {esc(b['name'])}</title>
<meta name="description" content="{esc(desc)}">
<meta name="robots" content="noindex">
<meta name="theme-color" content="{c['dark']}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{esc(v['name'])}, {esc(title_line)}">
<meta property="og:description" content="{esc(v['tagline'])}">
<meta property="og:image" content="{esc(v['url'])}../assets/{asset_names['photo']}">
<link rel="icon" href="../assets/{asset_names['icon']}">
<link rel="apple-touch-icon" href="../assets/{asset_names['icon']}">
<link rel="preload" href="../assets/montserrat-800.woff2" as="font" type="font/woff2" crossorigin>
<style>
@font-face{{font-family:Montserrat;font-weight:500;font-display:swap;src:url(../assets/montserrat-500.woff2) format("woff2")}}
@font-face{{font-family:Montserrat;font-weight:700;font-display:swap;src:url(../assets/montserrat-700.woff2) format("woff2")}}
@font-face{{font-family:Montserrat;font-weight:800;font-display:swap;src:url(../assets/montserrat-800.woff2) format("woff2")}}
:root{{--primary:{c['primary']};--action:{c['action']};--action-text:{c['action_text']};--dark:{c['dark']};--ground:{c['ground']};--line:{c['line']};--ink:{c['ink']};--muted:{c['muted']};color-scheme:light}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%;background:var(--dark)}}
body{{margin:0;font-family:Montserrat,"Helvetica Neue",Arial,sans-serif;font-weight:500;color:var(--ink);background:var(--ground);min-height:100vh;min-height:100dvh}}
.wrap{{max-width:460px;margin:0 auto;background:var(--ground);min-height:100vh;min-height:100dvh;padding-bottom:calc(28px + env(safe-area-inset-bottom))}}
.hero{{position:relative;height:210px;background:var(--dark) url(../assets/{asset_names['photo']}) {b['photo_focus']}/{b.get('photo_size', 'cover')} no-repeat}}
.hero::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 45%,rgba(0,0,0,.28))}}
.card{{position:relative;z-index:1;margin:-64px 16px 0;background:#fff;border-radius:18px;box-shadow:0 10px 30px rgba(20,30,45,.14),0 1px 0 rgba(20,30,45,.04);padding:22px 20px 20px;text-align:center}}
.logo{{display:block;margin:0 auto 14px;height:auto;max-width:72%;max-height:118px;width:auto}}
h1{{margin:0;font-weight:800;font-size:28px;line-height:1.15;letter-spacing:-.01em;color:var(--dark)}}
.role{{margin:6px 0 0;font-weight:700;font-size:15px;color:var(--primary)}}
.org{{margin:2px 0 0;font-weight:700;font-size:14px;color:var(--dark)}}
.tag{{margin:8px auto 0;max-width:30ch;font-size:14px;line-height:1.45;color:var(--muted)}}
.save{{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;margin:20px 0 0;padding:16px 18px;border:0;border-radius:12px;background:var(--action);color:var(--action-text);font:800 17px/1 Montserrat,"Helvetica Neue",Arial,sans-serif;text-decoration:none;box-shadow:0 4px 12px rgba(0,0,0,.12);-webkit-tap-highlight-color:transparent}}
.save:active{{transform:translateY(1px)}}
.save .i{{width:22px;height:22px}}
.quick{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}}
.quick a{{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 4px;border-radius:12px;background:var(--ground);color:var(--dark);text-decoration:none;font-weight:700;font-size:13px}}
.quick .i{{width:22px;height:22px;color:var(--primary)}}
.list{{margin:16px 16px 0;background:#fff;border-radius:18px;overflow:hidden;box-shadow:0 1px 0 rgba(20,30,45,.04),0 4px 16px rgba(20,30,45,.06)}}
.row{{display:flex;align-items:center;gap:14px;padding:14px 16px;color:var(--ink);text-decoration:none;border-top:1px solid var(--line);-webkit-tap-highlight-color:transparent}}
.row:first-child{{border-top:0}}
.row .i{{flex:none;width:22px;height:22px;color:var(--primary)}}
.txt{{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px;text-align:left}}
.lab{{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}}
.val{{font-size:15.5px;font-weight:700;color:var(--dark);overflow-wrap:anywhere}}
.sub{{font-size:13px;color:var(--muted)}}
.socials{{display:grid;grid-template-columns:repeat({2 if len(b['social']) == 4 else (min(len(b['social']), 3) or 1)},1fr);gap:8px;margin:16px 16px 0}}
.soc{{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 4px;border-radius:14px;background:#fff;color:var(--dark);text-decoration:none;font-weight:700;font-size:13px;box-shadow:0 1px 0 rgba(20,30,45,.04),0 3px 10px rgba(20,30,45,.06)}}
.soc .i{{width:22px;height:22px;color:var(--primary)}}
.share{{margin:22px 16px 0;padding:20px;background:#fff;border-radius:18px;text-align:center;box-shadow:0 1px 0 rgba(20,30,45,.04),0 4px 16px rgba(20,30,45,.06)}}
.share h2{{margin:0 0 4px;font-size:16px;font-weight:800;color:var(--dark)}}
.share p{{margin:0 0 14px;font-size:13px;color:var(--muted)}}
.qr{{display:block;width:200px;height:200px;margin:0 auto;shape-rendering:crispEdges}}
.sharebtn{{display:inline-flex;align-items:center;gap:8px;margin-top:14px;padding:11px 18px;border:2px solid var(--primary);border-radius:999px;background:#fff;color:var(--primary);font:700 14px/1 Montserrat,"Helvetica Neue",Arial,sans-serif;cursor:pointer}}
.sharebtn .i{{width:18px;height:18px}}
.wallet .wbs{{display:flex;flex-wrap:wrap;justify-content:center;gap:12px;align-items:center}}
.wb img{{display:block;height:44px;width:auto}}
.foot{{margin:22px 16px 0;text-align:center;font-size:12px;color:var(--muted)}}
.toast{{position:fixed;left:50%;bottom:calc(24px + env(safe-area-inset-bottom));transform:translateX(-50%);background:var(--dark);color:#fff;padding:10px 16px;border-radius:999px;font-size:14px;font-weight:700;opacity:0;transition:opacity .2s;pointer-events:none}}
.toast.on{{opacity:1}}
a:focus-visible,button:focus-visible{{outline:3px solid var(--primary);outline-offset:2px}}
.brands{{margin:16px 16px 0;padding:18px 16px 16px;background:#fff;border-radius:18px;box-shadow:0 1px 0 rgba(20,30,45,.04),0 4px 16px rgba(20,30,45,.06)}}
.brands h2{{margin:0 0 12px;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);text-align:center}}
.bgrid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.btile{{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;gap:6px;padding:14px 8px 12px;border-radius:14px;background:var(--ground);text-decoration:none;color:var(--dark);text-align:center}}
.btile img{{height:62px;width:auto;max-width:100%;object-fit:contain;margin-bottom:2px}}
.btile b{{font-size:13px;font-weight:700}}
.btile span{{font-size:11.5px;color:var(--muted);line-height:1.35}}
</style>
</head>
<body>
<div class="wrap">
<div class="hero" role="img" aria-label="{esc(b['name'])}"></div>
<main class="card">
<img class="logo" src="../assets/{asset_names['logo']}" width="{logo_w}" height="{logo_h}" alt="{esc(b['logo_alt'])}">
<h1>{esc(v['name'])}</h1>
<p class="role">{esc(v['title'])}</p>
{'' if v['name'] == b['name'] else f'<p class="org">{esc(b["name"])}</p>'}
<p class="tag">{esc(v['tagline'])}</p>
<a class="save" href="{esc(v['vcf_name'])}">{icon('save')}Save contact</a>
<div class="quick">
<a href="tel:{p.get('mobile_e164') or s['shop_phone_e164']}">{icon('phone')}Call</a>
<a href="mailto:{esc(v['email'])}">{icon('mail')}Email</a>
{quick_web}
</div>
</main>
{brands_html}<nav class="list" id="links" aria-label="Contact details">
{chr(10).join(row_html)}
</nav>
<div class="socials">{social}</div>
<section class="share">
<h2>Share this card</h2>
<p>Scan with a phone camera</p>
{qr}
<button class="sharebtn" type="button" id="share">{icon('share')}Send the link</button>
</section>
{wallet_block(v, wl)}
<p class="foot">{esc(b['footer'])}</p>
</div>
<div class="toast" id="toast" role="status"></div>
<script>
(function(){{
  var url={json.dumps(v['url'])}, title={json.dumps(v['name'] + ', ' + b['name'])};
  var t=document.getElementById('toast');
  function toast(m){{t.textContent=m;t.classList.add('on');setTimeout(function(){{t.classList.remove('on')}},1800)}}
  document.getElementById('share').addEventListener('click',function(){{
    if(navigator.share){{navigator.share({{title:title,url:url}}).catch(function(){{}});return}}
    if(navigator.clipboard){{navigator.clipboard.writeText(url).then(function(){{toast('Link copied')}},function(){{prompt('Copy this link',url)}});return}}
    prompt('Copy this link',url);
  }});
}})();
</script>
</body>
</html>
'''

def qr_dims(url):
    import segno
    q = segno.make(url, error='q', micro=False)
    w, h = q.symbol_size(scale=1, border=2)
    return (w, h)

# ---------------------------------------------------------------- lock screen

def lock_html(v, asset_dir):
    """Phone wallpaper, 393 x 852 points (rendered at 3x = 1179 x 2556). The top third stays clear for the clock
    and the panel ends well above the torch and camera buttons and the notification stack."""
    b, c = v['brand_data'], v['brand_data']['colors']
    qr = qr_svg(v['url'], c['qr'], scale=1, border=0)
    w, h = qr_dims_border(v['url'], 0)
    qr = re.sub(r'<svg[^>]*>', f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:100%;display:block;shape-rendering:crispEdges">', qr, count=1)
    fonts = ''.join(f'@font-face{{font-family:M;font-weight:{wt};src:url("file://{asset_dir}/montserrat-{wt}.woff2")}}' for wt in (500, 700, 800))
    return f'''<!doctype html><html><head><meta charset="utf-8"><style>{fonts}
*{{box-sizing:border-box}}html,body{{margin:0;width:393px;height:852px;overflow:hidden}}
body{{font-family:M,sans-serif;background:{c['dark']};position:relative}}
.ph{{position:absolute;inset:0 0 auto 0;height:400px;background:url("file://{asset_dir}/{b['photo']}") {b['photo_focus']}/cover}}
.ph::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,.38) 0%,rgba(0,0,0,.08) 40%,{c['dark']} 100%)}}
.panel{{position:absolute;left:40px;right:40px;top:296px;background:#fff;border-radius:26px;padding:18px 20px 16px;box-shadow:0 18px 40px rgba(0,0,0,.28)}}
.head{{display:flex;align-items:center;gap:14px}}
.logo{{flex:none;display:block;max-width:118px;max-height:58px;width:auto;height:auto}}
.who{{min-width:0}}
.n{{font-weight:800;font-size:19px;color:{c['dark']};line-height:1.15}}
.r{{font-weight:700;font-size:12px;color:{c['primary']};margin-top:3px;line-height:1.25}}
.o{{font-weight:700;font-size:12px;color:{c['muted']};margin-top:1px;line-height:1.25}}
.qr{{width:236px;height:236px;margin:16px auto 0}}
.s{{text-align:center;font-weight:800;font-size:14px;color:{c['dark']};margin-top:12px}}
.f{{position:absolute;left:0;right:0;top:712px;text-align:center;color:rgba(255,255,255,.72);font-weight:500;font-size:11px}}
</style></head><body><div class="ph"></div><div class="panel">
<div class="head"><img class="logo" src="file://{asset_dir}/{b['logo']}"><div class="who">
<div class="n">{esc(v['name'])}</div><div class="r">{esc(v['title'])}</div><div class="o">{esc(b['name'])}</div></div></div>
<div class="qr">{qr}</div>
<div class="s">Scan to save my details</div>
</div><div class="f">{esc(b['footer'])}</div></body></html>'''

def qr_dims_border(url, border):
    import segno
    q = segno.make(url, error='q', micro=False)
    return q.symbol_size(scale=1, border=border)

def render_lockscreens(views, asset_dir):
    from playwright.sync_api import sync_playwright
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page(viewport={'width': 393, 'height': 852}, device_scale_factor=3)
        for v in views:
            f = Path(tempfile.mkdtemp()) / 'lock.html'
            f.write_text(lock_html(v, asset_dir))
            pg.goto(f.as_uri()); pg.wait_for_timeout(300)
            pg.evaluate('document.fonts.ready')
            out[v['slug']] = pg.screenshot(type='png')
        br.close()
    return out

# ---------------------------------------------------------------- assets

def font_woff2(weight):
    from fontTools.ttLib import TTFont
    f = TTFont(FONTS / f'montserrat-{weight}.ttf', recalcTimestamp=False)
    f.flavor = 'woff2'
    buf = io.BytesIO(); f.save(buf)
    return buf.getvalue()

def web_logo(name):
    """Logo resized for the page: at most 720 px wide, so it stays sharp on 3x phone screens."""
    from PIL import Image
    im = Image.open(SRC / 'assets' / name).convert('RGBA')
    if im.width > 720:
        im = im.resize((720, round(im.height * 720 / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'PNG', optimize=True)
    return buf.getvalue(), im.size

def web_photo(name):
    from PIL import Image
    im = Image.open(SRC / 'assets' / name).convert('RGB')
    if im.width > 1200:
        im = im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=80, optimize=True, progressive=True)
    return buf.getvalue()

def icon_png(brand):
    from PIL import Image
    logo = Image.open(SRC / 'assets' / brand['logo']).convert('RGBA')
    size = 180
    canvas = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    logo.thumbnail((size - 24, size - 24), Image.LANCZOS)
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    buf = io.BytesIO(); canvas.convert('RGB').save(buf, 'PNG', optimize=True)
    return buf.getvalue()

# ---------------------------------------------------------------- build

def build(dest, with_images=True, previous=None):
    """Write every output into dest. Images are only remade when their inputs changed (or always if previous is None)."""
    cfg = load()
    views = [card_view(cfg, c) for c in cfg['cards']]
    slugs = [v['slug'] for v in views]
    assert len(set(slugs)) == len(slugs), 'two cards share a slug'
    (dest / 'assets').mkdir(parents=True, exist_ok=True)
    files = {}
    for wt in (500, 700, 800):
        files[f'assets/montserrat-{wt}.woff2'] = font_woff2(wt)
    brand_assets = {}
    for key, b in cfg['brands'].items():
        logo_bytes, size = web_logo(b['logo'])
        files[f'assets/{b["logo"]}'] = logo_bytes
        files[f'assets/icon-{key}.png'] = icon_png(b)
        brand_assets[key] = {'logo': b['logo'], 'logo_size': size, 'icon': f'icon-{key}.png'}
    for logo in sorted({t['logo'] for b in cfg['brands'].values() for t in b.get('our_brands', [])} - {b['logo'] for b in cfg['brands'].values()}):
        files[f'assets/{logo}'] = web_logo(logo)[0]
    for photo in sorted({v['brand_data']['photo'] for v in views}):
        files[f'assets/{photo}'] = web_photo(photo)
    manifest = {'_about': 'Written by cards/build.py. Do not edit.', 'cards': {}}
    template_hash = sha((SRC / 'build.py').read_bytes() + (SRC / 'wallet.py').read_bytes())
    apple_on, google_on = wallet.apple_on(cfg), wallet.google_on(cfg)
    glinks = wallet.google_links() if google_on else {}
    if apple_on or google_on:
        files['assets/add-to-apple-wallet.svg'] = (SRC / 'wallet' / 'add-to-apple-wallet.svg').read_bytes()
        files['assets/add-to-google-wallet.svg'] = (SRC / 'wallet' / 'add-to-google-wallet.svg').read_bytes()
    if google_on:
        for v in views:
            files.update(wallet.g_images(v))
    for v in views:
        key = v['brand']
        wl = {'apple': wallet.apple_name(v) if apple_on else None,
              'google': wallet.save_url(glinks[v['slug']]['jwt']) if google_on and v['slug'] in glinks else None}
        files[f"{v['slug']}/index.html"] = page(v, {**brand_assets[key], 'photo': v['brand_data']['photo']}, wl).encode()
        files[f"{v['slug']}/{v['vcf_name']}"] = vcard(v).encode()
        files[f"{v['slug']}/qr.svg"] = qr_svg(v['url'], v['brand_data']['colors']['qr']).encode()
        img_inputs = sha(VERSION, template_hash, json.dumps(v, sort_keys=True, default=str),
                         (SRC / 'assets' / v['brand_data']['logo']).read_bytes(), (SRC / 'assets' / v['brand_data']['photo']).read_bytes())
        manifest['cards'][v['slug']] = {'url': v['url'], 'vcf': v['vcf_name'], 'brand': v['brand_data']['name'], 'title': v['title'],
                                        'email': v['email'], 'images': img_inputs}
        if apple_on:
            manifest['cards'][v['slug']]['apple'] = wallet.apple_fingerprint(v, cfg)
    for rel, data in files.items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_bytes(data)
    if with_images:
        need = [v for v in views if not previous or previous.get('cards', {}).get(v['slug'], {}).get('images') != manifest['cards'][v['slug']]['images']
                or not (OUT / v['slug'] / 'lock-screen.png').exists() or not (OUT / v['slug'] / 'qr.png').exists()]
        for v in views:
            if v not in need:   # carry the existing images over unchanged
                for f in ('qr.png', 'lock-screen.png'):
                    shutil.copyfile(OUT / v['slug'] / f, dest / v['slug'] / f)
        if need:
            locks = render_lockscreens(need, str((dest / 'assets').resolve()))
            for v in need:
                (dest / v['slug'] / 'qr.png').write_bytes(qr_png(v['url'], v['brand_data']['colors']['qr']))
                (dest / v['slug'] / 'lock-screen.png').write_bytes(locks[v['slug']])
        if apple_on:   # Apple Wallet passes: re-signed only when their contents changed, and only where the key is
            key = wallet.secrets().get('apple_key_pem')
            for v in views:
                name, fp = wallet.apple_name(v), manifest['cards'][v['slug']]['apple']
                old = OUT / v['slug'] / name
                same = previous and previous.get('cards', {}).get(v['slug'], {}).get('apple') == fp and old.exists()
                if same or (old.exists() and not key):
                    shutil.copyfile(old, dest / v['slug'] / name)
                    if not same:
                        manifest['cards'][v['slug']]['apple'] = previous.get('cards', {}).get(v['slug'], {}).get('apple', 'stale') if previous else 'stale'
                elif key:
                    (dest / v['slug'] / name).write_bytes(wallet.apple_sign(wallet.apple_files(v, cfg), key))
                else:
                    manifest['cards'][v['slug']]['apple'] = 'missing'
    (dest / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return views, manifest

def verify_images(root, views):
    problems = []
    for v in views:
        for f in ('qr.png', 'lock-screen.png'):
            pth = root / v['slug'] / f
            if not pth.exists():
                problems.append(f'{v["slug"]}/{f} is missing'); continue
            found = qr_decode_png(pth.read_bytes())
            if v['url'] not in found:
                problems.append(f'{v["slug"]}/{f}: QR code reads {found or "nothing"}, should open {v["url"]}')
    return problems

def tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

def check():
    """Compare site/card with a fresh build. Returns a list of problems."""
    problems = []
    prev = json.loads((OUT / 'manifest.json').read_text()) if (OUT / 'manifest.json').exists() else {}
    tmp = Path(tempfile.mkdtemp())
    views, manifest = build(tmp, with_images=False)
    have, want = tree(OUT) if OUT.exists() else {}, tree(tmp)
    for rel, data in want.items():
        if rel not in have: problems.append(f'{rel} is missing')
        elif have[rel] != data: problems.append(f'{rel} is out of date or was edited by hand')
    cfg = load()
    expected_images = {f"{v['slug']}/{f}" for v in views for f in ('qr.png', 'lock-screen.png')}
    if wallet.apple_on(cfg):
        expected_images |= {f"{v['slug']}/{wallet.apple_name(v)}" for v in views}
    for rel in have:
        if rel not in want and rel not in expected_images:
            problems.append(f'{rel} should not be there (no card makes it)')
    for slug, m in manifest['cards'].items():
        if prev.get('cards', {}).get(slug, {}).get('images') != m['images']:
            problems.append(f'{slug}: the QR and lock screen images were made from older details')
    problems += verify_images(OUT, views)
    problems += check_wallet(cfg, views)
    return problems

def check_wallet(cfg, views):
    problems = []
    if wallet.apple_on(cfg):
        days, end = wallet.cert_days_left(wallet.APPLE_CERT)
        if days < wallet.CERT_WARN_DAYS:
            problems.append(f'Apple Wallet pass certificate ends {end} ({days} days): renew it in the Apple Developer account')
        for v in views:
            pk = OUT / v['slug'] / wallet.apple_name(v)
            if not pk.exists():
                problems.append(f"{v['slug']}: Apple Wallet pass is missing"); continue
            problems += wallet.apple_verify(pk.read_bytes(), v, cfg)
    if wallet.google_on(cfg):
        links = wallet.google_links()
        for v in views:
            jwt = links.get(v['slug'], {}).get('jwt')
            why = wallet.g_jwt_ok(jwt, wallet.g_payload(cfg, v)) if jwt else 'it is missing'
            if why:
                problems.append(f"{v['slug']}: the Save to Google Wallet link needs re-signing: {why}")
    return problems

def live():
    """Published pages and contact files must match this repo, and every outward link must answer."""
    problems, warnings = [], []
    cfg = load()
    views = [card_view(cfg, c) for c in cfg['cards']]
    ua = {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'}
    def get(url):
        req = urllib.request.Request(url, headers=ua)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(), r.headers.get('Content-Type', '')
    for v in views:
        rels = ['index.html', v['vcf_name'], 'qr.svg', 'qr.png', 'lock-screen.png']
        if wallet.apple_on(cfg): rels.append(wallet.apple_name(v))
        if wallet.google_on(cfg): rels.append(wallet.g_image_names(v)['hero'])
        for rel in rels:
            url = v['url'] + ('' if rel == 'index.html' else rel)
            try:
                st, body, ctype = get(url + ('?check' if rel == 'index.html' else ''))
            except Exception as e:
                problems.append(f'{url} does not open ({e})'); continue
            local = (OUT / v['slug'] / rel).read_bytes()
            if body != local:
                problems.append(f'{url} is not the current version yet')
            if rel.endswith('.pkpass') and 'application/vnd.apple.pkpass' not in ctype:
                problems.append(f'{url} is served as {ctype!r}, so iPhones will not open it as a pass')
        links = [w['url'] for w in v['brand_data']['websites']] + [so['url'] for so in v['brand_data']['social']]
        for u in links:
            try:
                st, _, _ = get(u)
                if st >= 400: (problems if 'facebook' not in u and 'instagram' not in u else warnings).append(f'{u} answered {st}')
            except urllib.error.HTTPError as e:
                if e.code == 404 or ('facebook' not in u and 'instagram' not in u and 'youtube' not in u):
                    problems.append(f'{u} answered {e.code}')
                else:
                    warnings.append(f'{u} answered {e.code} (social sites often refuse robots)')
            except Exception as e:
                warnings.append(f'{u} could not be reached ({e})')
    if wallet.google_on(cfg):
        p3, notes = wallet.google_sync(cfg, views, fix=True)
        problems += p3; warnings += notes
    return problems, warnings

def main():
    args = sys.argv[1:]
    if '--google-sync' in args:
        cfg = load()
        if not wallet.google_on(cfg):
            print('Google Wallet not set up yet'); return
        probs, notes = wallet.google_sync(cfg, [card_view(cfg, c) for c in cfg['cards']], fix=True)
        for n in notes: print(n)
        if probs:
            print('GOOGLE WALLET NEEDS FIXING:'); [print(' -', p) for p in probs]; sys.exit(1)
        print('Google Wallet passes OK'); return
    if '--check' in args or '--live' in args:
        problems = check() if '--check' in args else []
        warnings = []
        if '--live' in args:
            p2, warnings = live(); problems += p2
        for w in warnings: print('note:', w)
        if problems:
            print('CARDS NEED FIXING:'); [print(' -', p) for p in problems]; sys.exit(1)
        print('Cards OK'); return
    prev = json.loads((OUT / 'manifest.json').read_text()) if (OUT / 'manifest.json').exists() else None
    cfg = load()
    if wallet.google_on(cfg):
        changed, missing = wallet.refresh_google_links(cfg, [card_view(cfg, c) for c in cfg['cards']])
        if changed: print('Save to Google Wallet links re-signed:', ', '.join(changed))
        if missing: print('note: no Google key here, these links stay as they are until the GitHub build signs them:', ', '.join(missing))
    tmp = Path(tempfile.mkdtemp()) / 'card'
    views, _ = build(tmp, with_images=True, previous=prev)
    if OUT.exists(): shutil.rmtree(OUT)
    shutil.copytree(tmp, OUT)
    problems = verify_images(OUT, views) + check_wallet(cfg, views)
    if problems:
        print('BUILT BUT CHECKS FAILED:'); [print(' -', p) for p in problems]; sys.exit(1)
    print('Built', len(views), 'cards:'); [print(' ', v['url']) for v in views]

if __name__ == '__main__':
    main()
