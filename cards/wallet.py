"""Apple Wallet and Google Wallet passes for the digital business cards (used by cards/build.py).

Apple: one signed .pkpass per card (store card layout: logo, brand photo strip, name, title, QR code that opens the
card page, contact details on the back), signed with the pass certificate from the Element Outdoors Apple Developer
account. Google: one generic pass per card, kept up to date in Google Wallet through the Wallet API, and a Save to
Google Wallet link (a JWT signed by the service account) that carries the whole pass, so the link works on its own.

The two private keys live only in cards/wallet/keys.enc.json, sealed to the Ride Guide build key, so only the GitHub
build (ROUTE_SECRETS) can sign. Everything else here is public: the pass certificate, the Apple intermediate, the
service account certificate (to check signatures) and the badges.

Nothing in a pass is hand made: it is all worked out from cards.json, so --check can rebuild the expected contents
and compare them with what is published.
"""
import base64, hashlib, io, json, os, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request, zipfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
ROOT = SRC.parent
W = SRC / 'wallet'
APPLE_CERT = W / 'apple-pass-cert.pem'
WWDR = W / 'AppleWWDRCAG4.pem'
GOOGLE_CERT = W / 'google-sa-cert.pem'
GOOGLE_LINKS = W / 'google-links.json'
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
CERT_WARN_DAYS = 45


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else str(b).encode()).hexdigest()[:16]


def wcfg(cfg):
    return cfg.get('wallet') or {}


def apple_on(cfg):
    a = wcfg(cfg).get('apple') or {}
    return bool(a.get('passTypeIdentifier') and a.get('teamIdentifier') and APPLE_CERT.exists())


def google_on(cfg):
    g = wcfg(cfg).get('google') or {}
    return bool(g.get('issuerId') and g.get('serviceAccountEmail') and GOOGLE_CERT.exists())


_SECRETS = None
def secrets():
    """The private keys: CARDS_WALLET_KEYS (a JSON file path or JSON) for a local run, else unsealed with ROUTE_SECRETS."""
    global _SECRETS
    if _SECRETS is not None:
        return _SECRETS
    raw = os.environ.get('CARDS_WALLET_KEYS')
    try:
        if raw:
            _SECRETS = json.loads(Path(raw).read_text()) if Path(raw).exists() else json.loads(raw)
        elif os.environ.get('ROUTE_SECRETS') and (W / 'keys.enc.json').exists():
            out = subprocess.run(['node', str(SRC / 'wallet-unseal.mjs')], cwd=ROOT, capture_output=True, text=True, check=True)
            _SECRETS = json.loads(out.stdout)
        else:
            _SECRETS = {}
    except Exception as e:
        print('note: wallet keys could not be opened:', e)
        _SECRETS = {}
    return _SECRETS


def hex_rgb(h):
    h = h.lstrip('#')
    return f'rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})'


def wc_logo_chip(b):
    return bool((b.get('wallet') or {}).get('logo_chip'))


def colours(v):
    b = v['brand_data']
    wc = b.get('wallet') or {}
    c = b['colors']
    return {'bg': wc.get('bg', '#FFFFFF'), 'fg': wc.get('fg', c['dark']), 'label': wc.get('label', c['primary'])}


# ---------------------------------------------------------------- images

def _png(im):
    buf = io.BytesIO()
    im.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


def _png_photo(im):
    """Apple only takes PNG; a 256 colour dithered PNG keeps a photo strip small with no visible loss at strip size."""
    from PIL import Image
    return _png(im.convert('RGB').quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG))


def _jpg(im, q=84):
    buf = io.BytesIO()
    im.convert('RGB').save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
    return buf.getvalue()


def cover(img, w, h, focus='50% 50%', size='cover'):
    """Crop img to w x h the way CSS background-size / background-position would."""
    from PIL import Image
    iw, ih = img.size
    s = max(w / iw, h / ih)
    if size and size.endswith('% auto'):
        s = max(s, (w * float(size.split('%')[0]) / 100) / iw)
    sw, sh = round(iw * s), round(ih * s)
    im = img.resize((sw, sh), Image.LANCZOS)
    fx, fy = [float(p.strip('%')) / 100 for p in focus.split()]
    x, y = round((sw - w) * fx), round((sh - h) * fy)
    return im.crop((x, y, x + w, y + h))


def fit_logo(path, max_w, max_h, bg=None, pad=0, square=None):
    from PIL import Image
    logo = Image.open(path).convert('RGBA')
    logo.thumbnail((max_w - 2 * pad, max_h - 2 * pad), Image.LANCZOS)
    if square:
        canvas = Image.new('RGBA', (square, square), bg or (0, 0, 0, 0))
        canvas.alpha_composite(logo, ((square - logo.width) // 2, (square - logo.height) // 2))
        return canvas
    if bg:
        canvas = Image.new('RGBA', (logo.width + 2 * pad, logo.height + 2 * pad), bg)
        canvas.alpha_composite(logo, (pad, pad))
        return canvas
    return logo


def photo(v):
    from PIL import Image
    return Image.open(SRC / 'assets' / v['brand_data']['photo']).convert('RGB')


FONTS = ROOT / 'ride-sheets' / 'assets'


def logo_chip(name, cw, ch, scale, radius=6):
    """A logo centred on a white rounded chip, so dark or coloured artwork reads on any brand colour."""
    from PIL import Image, ImageDraw
    c = Image.new('RGBA', (int(cw), int(ch)), (0, 0, 0, 0))
    m = Image.new('L', c.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, c.width - 1, c.height - 1), radius=radius * scale, fill=255)
    c.paste(Image.new('RGBA', c.size, (255, 255, 255, 255)), (0, 0), m)
    lg = Image.open(SRC / 'assets' / name).convert('RGBA')
    pad = 4 * scale
    lg.thumbnail((int(c.width - 2 * pad), int(c.height - 2 * pad)), Image.LANCZOS)
    c.alpha_composite(lg, ((c.width - lg.width) // 2, (c.height - lg.height) // 2))
    return c


def name_strip(v, scale):
    """The photo strip: the name and title in Montserrat on a brand dark panel at the left, and the photo at the
    right, shown at the strip's full height so the riders and bikes stay whole, fading into the panel."""
    from PIL import Image, ImageDraw, ImageFont
    b, wc = v['brand_data'], v['brand_data'].get('wallet') or {}
    w, h = 375 * scale, 123 * scale
    src = Image.open(SRC / 'assets' / v['wallet_photo']).convert('RGB') if v.get('wallet_photo') else photo(v)
    x0, y0, x1, y1 = v.get('wallet_crop') or wc.get('crop') or (0, 0, 1, 1)   # the part of the photo to show
    iw, ih = src.size
    box = [round(x0 * iw), round(y0 * ih), round(x1 * iw), round(y1 * ih)]
    pw = round((box[2] - box[0]) * h / (box[3] - box[1]))
    maxw = round(w * 0.62)
    if pw > maxw:   # too wide for the space: trim the sides evenly
        trim = (box[2] - box[0]) * (1 - maxw / pw) / 2
        box = [round(box[0] + trim), box[1], round(box[2] - trim), box[3]]
        pw = maxw
    pic = src.crop(box).resize((pw, h), Image.LANCZOS).convert('RGBA')
    fade = Image.new('L', (pw, h))
    ramp = round(pw * float(v.get('wallet_fade') or 0.42))   # a narrow portrait crop needs a shorter fade
    fade.paste(255, (ramp, 0, pw, h))
    for x in range(ramp):
        t = x / ramp
        fade.paste(round(255 * t * t * (3 - 2 * t)), (x, 0, x + 1, h))
    pic.putalpha(fade)
    im = Image.new('RGBA', (w, h), wc.get('panel') or b['colors']['dark'])
    im.alpha_composite(pic, (w - pw, 0))
    d = ImageDraw.Draw(im)
    left = 44 * scale   # Wallet trims about 28 points off each side of the strip on a phone, so the text sits inside that
    size = 23
    while True:
        nf = ImageFont.truetype(str(FONTS / 'montserrat-800.ttf'), size * scale)
        if d.textlength(v['name'], font=nf) <= 140 * scale or size <= 14:
            break
        size -= 1
    title = v['title'].upper()
    tf = ImageFont.truetype(str(FONTS / 'montserrat-700.ttf'), 10.5 * scale)
    track = 1.1 * scale
    nH = nf.getbbox('H'); tH = tf.getbbox('H')
    gap = 7 * scale
    block = (nH[3] - nH[1]) + gap + (tH[3] - tH[1])
    row = b.get('our_brands') or []
    top = (h - block) / 2 if not row else 20 * scale   # with a logo row the name sits higher
    if row:   # Element Outdoors: a white chip per brand logo under the name
        cw, chh, cg = 42 * scale, 30 * scale, 5 * scale
        for i, t in enumerate(row):
            im.alpha_composite(logo_chip(t['logo'], cw, chh, scale), (int(left + i * (cw + cg)), int(h - chh - 15 * scale)))
    if v['name']:
        d.text((left, top - nH[1]), v['name'], font=nf, fill='#FFFFFF')
    accent = wc.get('accent') or b['colors']['action']
    tx, ty = left, top + (nH[3] - nH[1]) + gap - tH[1]
    for ch in title:
        d.text((tx, ty), ch, font=tf, fill=accent)
        tx += d.textlength(ch, font=tf) + track
    return im.convert('RGB')


def brand_icon(v, size):
    from PIL import Image
    canvas = Image.new('RGBA', (size, size), (255, 255, 255, 255))
    logo = Image.open(SRC / 'assets' / v['brand_data']['logo']).convert('RGBA')
    logo.thumbnail((int(size * 0.86), int(size * 0.86)), Image.LANCZOS)
    canvas.alpha_composite(logo, ((size - logo.width) // 2, (size - logo.height) // 2))
    return canvas.convert('RGB')


# ---------------------------------------------------------------- Apple

def apple_name(v):
    return v['vcf_name'][:-4] + '.pkpass'


def back_fields(v):
    p, b, s = v['person_data'], v['brand_data'], v['shared']
    a = s['address']
    f = [{'key': 'card', 'label': 'Save my contact', 'value': v['url']}]   # first, so a shared pass saves the contact in one tap
    if p.get('mobile'):
        f.append({'key': 'mobile', 'label': 'Mobile', 'value': p['mobile']})
    f.append({'key': 'shop', 'label': 'Shop', 'value': f"{s['shop_phone']}\n{s['hours']}"})
    f.append({'key': 'email', 'label': 'Email', 'value': v['email']})
    for i, w in enumerate(b['websites']):
        f.append({'key': f'web{i}', 'label': w['label'] if len(b['websites']) > 1 else 'Website', 'value': w['url']})
    f.append({'key': 'address', 'label': 'Visit the shop', 'value': f"{a['street']}, {a['locality']} {a['region']} {a['postcode']}"})
    for i, so in enumerate(b['social']):
        f.append({'key': f'social{i}', 'label': so.get('aria') or f"{b['name']} on {so['label']}", 'value': so['url']})
    f.append({'key': 'about', 'label': b['name'], 'value': f"{v['tagline']}. {b['footer']}."})
    return f


def apple_files(v, cfg):
    """Every file of the pass except manifest.json and signature, worked out from the card. Deterministic."""
    a = wcfg(cfg)['apple']
    p, b, s = v['person_data'], v['brand_data'], v['shared']
    col = colours(v)
    # One tidy row under the photo: two short fields only (the name and title are set in the photo strip).
    aux = []
    if p.get('mobile'):
        aux.append({'key': 'm', 'label': 'MOBILE', 'value': p['mobile']})
    aux.append({'key': 's', 'label': 'SHOP', 'value': s['shop_phone']})
    if len(aux) < 2:   # no mobile: the shop address takes the second place
        aux.append({'key': 'a', 'label': s['address']['locality'].upper(), 'value': s['address'].get('short') or s['address']['street']})
    pj = {
        'formatVersion': 1,
        'passTypeIdentifier': a['passTypeIdentifier'],
        'teamIdentifier': a['teamIdentifier'],
        'serialNumber': v['slug'],
        'organizationName': b['name'],
        'description': f"{v['name']}, {v['title']}, {b['name']}",
        'backgroundColor': hex_rgb(col['bg']),
        'foregroundColor': hex_rgb(col['fg']),
        'labelColor': hex_rgb(col['label']),
        'sharingProhibited': True,   # a shared pass only copies the QR; people share the card link instead, which saves the contact
        'storeCard': {
            'headerFields': [{'key': 'web', 'label': 'WEBSITE', 'value': b['website_label']}] if b.get('website_label') else [],
            'secondaryFields': aux,
            'backFields': back_fields(v),
        },
        'barcodes': [{'format': 'PKBarcodeFormatQR', 'message': v['url'], 'messageEncoding': 'iso-8859-1',
                      'altText': 'Scan to save my details'}],
    }
    files = {'pass.json': json.dumps(pj, indent=1, ensure_ascii=False).encode()}
    logo_path = SRC / 'assets' / b['logo']
    for scale, suf in ((1, ''), (2, '@2x'), (3, '@3x')):
        if wc_logo_chip(b):
            lg = fit_logo(logo_path, 146 * scale, 38 * scale)
            files[f'logo{suf}.png'] = _png(logo_chip(b['logo'], lg.width + 14 * scale, 46 * scale, scale, radius=8))
        else:
            files[f'logo{suf}.png'] = _png(fit_logo(logo_path, 160 * scale, 50 * scale))
        files[f'icon{suf}.png'] = _png(brand_icon(v, 29 * scale))
        files[f'strip{suf}.png'] = _png_photo(name_strip(v, scale))
    return files


def apple_fingerprint(v, cfg):
    files = apple_files(v, cfg)
    return sha(b''.join(k.encode() + sha(files[k]).encode() for k in sorted(files)) + APPLE_CERT.read_bytes())


def apple_sign(files, key_pem):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import pkcs7
    manifest = {k: hashlib.sha1(files[k]).hexdigest() for k in sorted(files)}
    mbytes = json.dumps(manifest, indent=1).encode()
    cert = x509.load_pem_x509_certificate(APPLE_CERT.read_bytes())
    wwdr = x509.load_pem_x509_certificate(WWDR.read_bytes())
    key = serialization.load_pem_private_key(key_pem.encode(), None)
    sig = (pkcs7.PKCS7SignatureBuilder().set_data(mbytes).add_signer(cert, key, hashes.SHA256()).add_certificate(wwdr)
           .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary]))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted({**files, 'manifest.json': mbytes, 'signature': sig}.items()):
            zi = zipfile.ZipInfo(name, ZIP_TIME); zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    return buf.getvalue()


def apple_verify(pkpass, v, cfg):
    """Problems with a published pass: contents must match the card, the manifest and signature must hold."""
    probs = []
    try:
        z = zipfile.ZipFile(io.BytesIO(pkpass))
        got = {n: z.read(n) for n in z.namelist()}
    except Exception as e:
        return [f'{v["slug"]}: the Apple Wallet pass will not open ({e})']
    want = apple_files(v, cfg)
    for k, data in want.items():
        if got.get(k) != data:
            probs.append(f'{v["slug"]}: Apple Wallet pass {k} is out of date')
    extra = set(got) - set(want) - {'manifest.json', 'signature'}
    if extra:
        probs.append(f'{v["slug"]}: Apple Wallet pass has files no card makes: {sorted(extra)}')
    try:
        man = json.loads(got['manifest.json'])
        for k, h in man.items():
            if hashlib.sha1(got.get(k, b'')).hexdigest() != h:
                probs.append(f'{v["slug"]}: Apple Wallet pass manifest does not match {k}')
        with tempfile.TemporaryDirectory() as d:
            Path(d, 'm').write_bytes(got['manifest.json']); Path(d, 's').write_bytes(got['signature'])
            r = subprocess.run(['openssl', 'smime', '-verify', '-binary', '-inform', 'DER', '-in', f'{d}/s', '-content', f'{d}/m',
                                '-noverify', '-certfile', str(WWDR), '-signer', f'{d}/signer.pem', '-out', '/dev/null'],
                               capture_output=True, text=True)
            if r.returncode != 0:
                probs.append(f'{v["slug"]}: Apple Wallet pass signature does not verify ({r.stderr.strip()[:120]})')
            elif Path(d, 'signer.pem').read_bytes().strip() != APPLE_CERT.read_bytes().strip() and \
                    _der(Path(d, 'signer.pem').read_bytes()) != _der(APPLE_CERT.read_bytes()):
                probs.append(f'{v["slug"]}: Apple Wallet pass was signed with a different certificate')
    except Exception as e:
        probs.append(f'{v["slug"]}: Apple Wallet pass could not be checked ({e})')
    return probs


def _der(pem):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization
    return x509.load_pem_x509_certificate(pem).public_bytes(serialization.Encoding.DER)


def cert_days_left(path):
    from cryptography import x509
    import datetime
    c = x509.load_pem_x509_certificate(path.read_bytes())
    end = c.not_valid_after_utc
    return (end - datetime.datetime.now(datetime.timezone.utc)).days, end.date().isoformat()


# ---------------------------------------------------------------- Google

def g_id(cfg, v):
    return f"{wcfg(cfg)['google']['issuerId']}.card-{v['slug']}"


def g_class_id(cfg):
    return f"{wcfg(cfg)['google']['issuerId']}.business-card"


def loc(text):
    return {'defaultValue': {'language': 'en-AU', 'value': text}}


def g_image_names(v):
    return {'logo': f"wallet-logo-{v['brand']}.png", 'wide': f"wallet-wide-{v['brand']}.png", 'hero': 'wallet-hero.jpg'}


def g_images(v):
    """Images Google Wallet shows, published next to the card (Google fetches them when the pass is saved)."""
    b = v['brand_data']
    col = colours(v)
    logo_path = SRC / 'assets' / b['logo']
    n = g_image_names(v)
    from PIL import Image
    wide = fit_logo(logo_path, 1280, 400, pad=24)
    wide_canvas = Image.new('RGBA', (1280, 400), (0, 0, 0, 0))
    wide_canvas.alpha_composite(wide, ((1280 - wide.width) // 2, (400 - wide.height) // 2))
    return {
        f"assets/{n['logo']}": _png(brand_icon(v, 660)),
        f"assets/{n['wide']}": _png(wide_canvas),
        f"{v['slug']}/{n['hero']}": _jpg(name_strip({**v, 'name': '', 'title': ''}, 3).resize((1032, 336), Image.LANCZOS)),
    }


def g_object(cfg, v):
    p, b, s = v['person_data'], v['brand_data'], v['shared']
    col = colours(v)
    base = cfg['base_url']
    n = g_image_names(v)
    first = p['first']
    texts = []
    if p.get('mobile'):
        texts.append({'id': 'mobile', 'header': 'Mobile', 'body': p['mobile']})
    texts += [{'id': 'shop', 'header': 'Shop', 'body': f"{s['shop_phone']}, {s['hours']}"},
              {'id': 'email', 'header': 'Email', 'body': v['email']}]
    uris = [{'id': 'call', 'uri': 'tel:' + (p.get('mobile_e164') or s['shop_phone_e164']),
             'description': f'Call {first}' if p.get('mobile_e164') else 'Call the shop'},
            {'id': 'email', 'uri': 'mailto:' + v['email'], 'description': f'Email {first}'}]
    for i, w in enumerate(b['websites']):
        uris.append({'id': f'web{i}', 'uri': w['url'], 'description': w['label'] if len(b['websites']) > 1 else w['value']})
    uris.append({'id': 'map', 'uri': s['maps_url'], 'description': 'Visit the shop'})
    for i, so in enumerate(b['social']):
        uris.append({'id': f'social{i}', 'uri': so['url'], 'description': so.get('aria') or f"{b['name']} on {so['label']}"})
    uris.append({'id': 'card', 'uri': v['url'], 'description': 'Full card and save my contact'})
    return {
        'id': g_id(cfg, v), 'classId': g_class_id(cfg), 'state': 'ACTIVE',
        'cardTitle': loc(b['name']), 'header': loc(v['name']), 'subheader': loc(v['title']),
        'hexBackgroundColor': col['bg'],
        'logo': {'sourceUri': {'uri': base + 'assets/' + n['logo']}, 'contentDescription': loc(b['name'])},
        'wideLogo': {'sourceUri': {'uri': base + 'assets/' + n['wide']}, 'contentDescription': loc(b['name'])},
        'heroImage': {'sourceUri': {'uri': v['url'] + n['hero']}, 'contentDescription': loc(b['name'])},
        'barcode': {'type': 'QR_CODE', 'value': v['url'], 'alternateText': 'Scan to save my details'},
        'textModulesData': texts,
        'linksModuleData': {'uris': uris},
    }


def g_class(cfg):
    return {'id': g_class_id(cfg)}


def _b64u(b):
    return base64.urlsafe_b64encode(b).rstrip(b'=').decode()


def g_payload(cfg, v):
    g = wcfg(cfg)['google']
    return {'iss': g['serviceAccountEmail'], 'aud': 'google', 'typ': 'savetowallet', 'iat': g.get('iat', 1793000000),
            'origins': ['https://elementoutdoors.github.io'],
            'payload': {'genericClasses': [g_class(cfg)], 'genericObjects': [g_object(cfg, v)]}}


def g_jwt(payload, key_pem):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    key = serialization.load_pem_private_key(key_pem.encode(), None)
    head = _b64u(json.dumps({'alg': 'RS256', 'typ': 'JWT'}, separators=(',', ':')).encode())
    body = _b64u(json.dumps(payload, separators=(',', ':'), sort_keys=True).encode())
    sig = key.sign(f'{head}.{body}'.encode(), padding.PKCS1v15(), hashes.SHA256())
    return f'{head}.{body}.{_b64u(sig)}'


def g_jwt_ok(jwt, payload):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    try:
        head, body, sig = jwt.split('.')
        if json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4))) != json.loads(json.dumps(payload)):
            return 'its pass details are out of date'
        pub = x509.load_pem_x509_certificate(GOOGLE_CERT.read_bytes()).public_key()
        pub.verify(base64.urlsafe_b64decode(sig + '=' * (-len(sig) % 4)), f'{head}.{body}'.encode(), padding.PKCS1v15(), hashes.SHA256())
        return ''
    except Exception as e:
        return f'it does not verify ({e.__class__.__name__})'


def save_url(jwt):
    return 'https://pay.google.com/gp/v/save/' + jwt


def google_links():
    return json.loads(GOOGLE_LINKS.read_text()) if GOOGLE_LINKS.exists() else {}


def refresh_google_links(cfg, views):
    """Re-sign any Save to Google Wallet link whose pass details changed. Needs the Google key."""
    links = google_links()
    key = secrets().get('google_key_pem')
    changed, missing = [], []
    for v in views:
        pl = g_payload(cfg, v)
        cur = links.get(v['slug'], {}).get('jwt')
        if cur and not g_jwt_ok(cur, pl):
            continue
        if not key:
            missing.append(v['slug']); continue
        links[v['slug']] = {'jwt': g_jwt(pl, key)}
        changed.append(v['slug'])
    for slug in [s for s in links if s not in {v['slug'] for v in views}]:
        links.pop(slug); changed.append(slug)
    if changed:
        GOOGLE_LINKS.write_text(json.dumps(links, indent=1, sort_keys=True) + '\n')
    return changed, missing


# Google Wallet API: keeps every saved pass current (a Save link only creates a pass the first time).
def _token(key_pem, email):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    now = int(time.time())
    claims = {'iss': email, 'scope': 'https://www.googleapis.com/auth/wallet_object.issuer', 'aud': 'https://oauth2.googleapis.com/token',
              'iat': now, 'exp': now + 3000}
    key = serialization.load_pem_private_key(key_pem.encode(), None)
    head = _b64u(b'{"alg":"RS256","typ":"JWT"}'); body = _b64u(json.dumps(claims).encode())
    sig = _b64u(key.sign(f'{head}.{body}'.encode(), padding.PKCS1v15(), hashes.SHA256()))
    data = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': f'{head}.{body}.{sig}'}).encode()
    with urllib.request.urlopen(urllib.request.Request('https://oauth2.googleapis.com/token', data=data), timeout=30) as r:
        return json.load(r)['access_token']


def _api(token, method, path, body=None):
    url = 'https://walletobjects.googleapis.com/walletobjects/v1/' + path
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, (json.loads(e.read() or b'{}') if e.code != 404 else {})


def _same(want, have):
    if isinstance(want, dict):
        return isinstance(have, dict) and all(_same(v, have.get(k)) for k, v in want.items())
    if isinstance(want, list):
        return isinstance(have, list) and len(want) == len(have) and all(_same(a, b) for a, b in zip(want, have))
    return want == have


def google_sync(cfg, views, fix=True):
    """Every card's Google Wallet class and object must match cards.json; fix=True puts right what differs."""
    g = wcfg(cfg)['google']
    key = secrets().get('google_key_pem')
    if not key:
        return [], ['Google Wallet: no key here, the API check runs in the GitHub build']
    probs, notes = [], []
    try:
        tok = _token(key, g['serviceAccountEmail'])
    except Exception as e:
        return [f'Google Wallet: could not sign in with the service account ({e})'], []
    st, have = _api(tok, 'GET', 'genericClass/' + g_class_id(cfg))
    if st == 404 and fix:
        st, have = _api(tok, 'POST', 'genericClass', g_class(cfg)); notes.append('Google Wallet: class created')
    if st >= 300:
        probs.append(f'Google Wallet: class {g_class_id(cfg)} answered {st} {str(have)[:160]}')
    for v in views:
        want = g_object(cfg, v)
        st, have = _api(tok, 'GET', 'genericObject/' + want['id'])
        if st == 404:
            if fix:
                st, have = _api(tok, 'POST', 'genericObject', want); notes.append(f"Google Wallet: {v['slug']} created")
        elif st < 300 and not _same(want, have):
            if fix:
                st, have = _api(tok, 'PUT', 'genericObject/' + want['id'], want); notes.append(f"Google Wallet: {v['slug']} updated")
            else:
                probs.append(f"Google Wallet: {v['slug']} differs from cards.json")
        if st >= 300 and 'Image cannot be loaded' in str(have) and os.environ.get('GITHUB_EVENT_NAME') == 'push':
            # a new card's images are not on the site until the site build finishes; the cards run that follows
            # the site build (workflow_run) syncs it then
            notes.append(f"Google Wallet: {v['slug']} waits for the site build to publish its images")
        elif st >= 300:
            probs.append(f"Google Wallet: {v['slug']} answered {st} {str(have)[:160]}")
    return probs, notes
