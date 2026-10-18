"""Gallery page of every ride map sheet, published as an artifact with the sheet images as files."""
import os, sys, json, html
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rides import RIDES, ORDER_SHOP, ORDER_HINT
from sheet import fname
from paths import OUT

G = os.path.join(OUT, 'gallery'); os.makedirs(os.path.join(G, 'img'), exist_ok=True)
files = {}


def card(rid):
    c = RIDES[rid]
    src = os.path.join(OUT, 'final', fname(rid) + '.png')
    im = Image.open(src).convert('RGB'); im.thumbnail((1800, 1800))
    name = c['slug'] + '.jpg'
    im.save(os.path.join(G, 'img', name), quality=82, optimize=True, progressive=True)
    files['img/' + name] = os.path.join(G, 'img', name)
    kick = c['kick'].replace('&middot;', '·')
    stats = ' · '.join(s[0] for s in c['stats'][:3])
    return f'''<li><button class="sheet" type="button" data-full="img/{name}" aria-label="Open the {html.escape(c['title'])} sheet">
<img src="img/{name}" alt="{html.escape(c['title'])} ride map sheet" loading="lazy" width="1800" height="1273"></button>
<div class="cap"><span class="kick">{html.escape(kick)}</span><b>{html.escape(c['title'])}</b><span class="num">{html.escape(stats)}</span></div></li>'''


shop = ''.join(card(r) for r in ORDER_SHOP)
hint = ''.join(card(r) for r in ORDER_HINT)
page = f'''<title>Ride Map Sheets</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;800;900&display=swap">
<style>
/* Layout: proof wall of A4 sheets in two brand groups; tap a sheet to see it large. */
:root{{
  --bg:#E7EAEE; --surface:#FFFFFF; --fg:#1E2329; --muted:#5A6470; --rule:#CDD3DB;
  --bikeon:#0C5AA9; --beo:#182B3D; --gold:#F5CA3A; --scrim:rgba(14,18,24,.88);
  --f:"Montserrat",Arial,Helvetica,sans-serif;
}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#15191E;--surface:#1F252C;--fg:#E8ECF0;--muted:#A3ADB8;--rule:#323A43;--bikeon:#5C9BE0;--beo:#F5CA3A;color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#15191E;--surface:#1F252C;--fg:#E8ECF0;--muted:#A3ADB8;--rule:#323A43;--bikeon:#5C9BE0;--beo:#F5CA3A;color-scheme:dark}}
body{{background:var(--bg);color:var(--fg);font-family:var(--f);margin:0}}
.wrap{{max-width:1240px;margin:0 auto;padding-inline:16px;padding-block:32px 64px;display:grid;gap:40px}}
header{{display:grid;gap:8px;max-width:70ch}}
h1{{margin:0;font-weight:900;font-size:clamp(26px,4vw,38px);line-height:1.05;text-wrap:balance}}
header p{{margin:0;color:var(--muted);font-weight:500;line-height:1.5}}
section{{display:grid;gap:16px}}
h2{{margin:0;display:flex;flex-wrap:wrap;align-items:baseline;gap:6px 12px;font-weight:800;font-size:20px;padding-bottom:10px;border-bottom:2px solid var(--rule)}}
h2 small{{font-weight:600;font-size:13px;color:var(--muted)}}
.s-bikeon h2{{border-color:var(--bikeon)}} .s-beo h2{{border-color:var(--beo)}}
ul{{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:24px 20px}}
li{{display:grid;gap:10px;min-width:0}}
.sheet{{all:unset;cursor:zoom-in;display:block;border-radius:4px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.12),0 8px 24px rgba(0,0,0,.12);background:var(--surface)}}
.sheet:focus-visible{{outline:3px solid var(--bikeon);outline-offset:3px}}
.sheet img{{display:block;width:100%;height:auto;aspect-ratio:297/210;object-fit:cover}}
.cap{{display:grid;gap:3px;min-width:0}}
.cap b{{font-weight:800;font-size:15px}}
.kick{{font-size:10.5px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:var(--bikeon)}}
.s-beo .kick{{color:var(--muted)}}
.num{{font-size:12.5px;color:var(--muted);font-weight:600;font-variant-numeric:tabular-nums}}
.box{{position:fixed;inset:0;background:var(--scrim);display:grid;place-items:center;padding:16px;z-index:10;cursor:zoom-out}}
.box img{{max-width:100%;max-height:100%;width:auto;height:auto;border-radius:3px;box-shadow:0 10px 40px rgba(0,0,0,.5)}}
@media (prefers-reduced-motion:no-preference){{.box{{animation:f .15s ease-out}}@keyframes f{{from{{opacity:.6}}}}}}
</style>
<div class="wrap">
<header><h1>Ride map sheets</h1><p>One A4 landscape sheet per self guided ride, for showing customers in the shop. Fourteen shop rides in the Bike On style, fourteen hinterland point to point rides in the By Earth and Ocean style. Tap a sheet to see it large.</p></header>
<section class="s-bikeon"><h2>Bike On <small>Self guided rides from the shop</small></h2><ul>{shop}</ul></section>
<section class="s-beo"><h2>By Earth and Ocean <small>Hinterland gravel and mountain bike, point to point</small></h2><ul>{hint}</ul></section>
</div>
<div class="box" id="box" hidden><img id="boxImg" alt=""></div>
<script>
const box=document.getElementById('box'),bi=document.getElementById('boxImg');
document.querySelectorAll('.sheet').forEach(b=>b.addEventListener('click',()=>{{bi.src=b.dataset.full;bi.alt=b.querySelector('img').alt;box.hidden=false;}}));
box.addEventListener('click',()=>{{box.hidden=true;}});
addEventListener('keydown',e=>{{if(e.key==='Escape')box.hidden=true;}});
</script>
'''
open(os.path.join(G, 'index.html'), 'w').write(page)
json.dump(files, open(os.path.join(G, 'files.json'), 'w'), indent=0)
print(len(files), sum(os.path.getsize(p) for p in files.values()) // 1024, 'KB')
