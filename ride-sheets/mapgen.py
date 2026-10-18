"""Build the 3D map scene for one ride and render it to an image.

python3 mapgen.py <route_id> ...   (reads rides.py for labels and style; writes STATE/maps/<slug>/map.jpg)

Camera: tries every heading and three tilts and keeps the one that shows the route largest, preferring a view looking
north, then east. Terrain: AWS Terrain Tiles. Imagery: Queensland Government aerial basemap; open ocean from
Sentinel-2 cloudless 2016 by EOX (CC BY 4.0). Rendered with Three.js in headless Chromium (render.html, shot.py).
"""
import json, math, os, sys, subprocess
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from geo import merc, unmerc, mosaic, crop_box, dem, cam_basis, project, fit_camera, ground_hits

from paths import HERE, STATE
from textfit import h1pt
Image.MAX_IMAGE_PIXELS = None

BLEED, BIND = 0, 0
RW, RH = 2400, 1002   # 297 x 124 mm map band, 8.08 px per mm
ASPECT = RW / RH
PITCH, VFOV = 42.0, 40.0
FITBOX = (-0.86, 0.86, -0.38, 0.50)
LON_OCEAN = 153.095


def yaw_penalty(yaw):
    fn = math.cos(math.radians(yaw)); fe = math.sin(math.radians(yaw))
    return 1.0 + 0.18 * (1 - fn) + (0.06 * -fe if fe < 0 else 0)


def build(rid, cfg, out, R):
    os.makedirs(out, exist_ok=True)
    r = R[rid]
    pts = np.array([p[:3] for p in r['pts']], float)
    la, lo = pts[:, 0], pts[:, 1]
    latc, lonc = (la.min() + la.max()) / 2, (lo.min() + lo.max()) / 2
    mxc, myc = merc(latc, lonc)
    K = 40075.017 * math.cos(math.radians(latc))           # km per mercator unit at this latitude

    def xz(lat, lon):
        mx, my = merc(lat, lon); return (mx - mxc) * K, (my - myc) * K

    XZ = np.array([xz(a, b) for a, b in zip(la, lo)])
    span = np.ptp(XZ, 0).max()
    # exaggeration grows gently with the size of the map so hills still read on big rides
    EX = cfg.get('ex') or 3.2 * max(0.75, min(1.0, (span / 10.5) ** 0.45))
    P = np.c_[XZ[:, 0], pts[:, 2] / 1000 * EX, XZ[:, 1]]
    # include label anchors in the fit so names near the edge stay in frame
    anchors = [xz(l['y'], l['x']) for l in cfg['labels'] if l.get('fit', True)]
    Pfit = np.r_[P, np.c_[np.array(anchors)[:, 0], np.full(len(anchors), P[:, 1].mean()), np.array(anchors)[:, 1]]] if anchors else P

    yaws = [cfg['yaw']] if 'yaw' in cfg else list(range(0, 360, 10))
    pitches = [cfg['pitch']] if 'pitch' in cfg else [42.0, 50.0, 58.0]
    best = None
    for pitch in pitches:
        for yaw in yaws:
            t, d = fit_camera(Pfit, yaw, pitch, VFOV, ASPECT, FITBOX)
            sc = d * yaw_penalty(yaw) * (1 + 0.012 * (pitch - 42))
            if best is None or sc < best[0]:
                best = (sc, yaw, t, d, pitch)
    if 'yaw' not in cfg:
        y0, p0 = best[1], best[4]
        for yaw in np.arange(y0 - 7.5, y0 + 7.6, 2.5):
            t, d = fit_camera(Pfit, yaw, p0, VFOV, ASPECT, FITBOX)
            sc = d * yaw_penalty(yaw) * (1 + 0.012 * (p0 - 42))
            if sc < best[0]:
                best = (sc, yaw, t, d, p0)
    _, yaw, t, d, PITCH_ = best
    d *= cfg.get('zoom', 1.0)
    cam = cam_basis(t, yaw, PITCH_, d)

    # ground footprint of the frame, plus margin
    G = ground_hits(cam, VFOV, ASPECT, [(-1.06, -1.06), (1.06, -1.06), (1.06, 1.06), (-1.06, 1.06), (0, 1.06)])
    gx0, gx1 = G[:, 0].min(), G[:, 0].max(); gz0, gz1 = G[:, 2].min(), G[:, 2].max()
    m = 0.03 * max(gx1 - gx0, gz1 - gz0)
    gx0 -= m; gx1 += m; gz0 -= m; gz1 += m
    mx0, mx1 = mxc + gx0 / K, mxc + gx1 / K
    my0, my1 = myc + gz0 / K, myc + gz1 / K
    Wkm, Hkm = gx1 - gx0, gz1 - gz0

    # terrain
    zdem = 13 if Wkm < 45 else 12
    him, hbox = dem(mx0, my0, mx1, my1, zdem)
    GX = 720; GY = max(2, int(GX * Hkm / Wkm))
    hcrop = crop_box(him.convert('F'), hbox, mx0, my0, mx1, my1, (GX + 1, GY + 1))
    g = np.clip(np.asarray(hcrop, dtype=np.float64), 0, None)
    from scipy.ndimage import gaussian_filter; g = gaussian_filter(g, 0.6)
    hs = g / 1000 * EX

    def height(x, z):
        u = (x - gx0) / Wkm * GX; v = (z - gz0) / Hkm * GY
        x0 = int(min(max(u, 0), GX - 1)); y0 = int(min(max(v, 0), GY - 1)); fx = min(max(u - x0, 0), 1); fy = min(max(v - y0, 0), 1)
        return float(hs[y0, x0] * (1 - fx) * (1 - fy) + hs[y0, x0 + 1] * fx * (1 - fy) + hs[y0 + 1, x0] * (1 - fx) * fy + hs[y0 + 1, x0 + 1] * fx * fy)

    # imagery
    zi = max(12, min(17, int(math.floor(math.log2(12000 / ((mx1 - mx0) * 256))))))
    TW = 8192 if Wkm >= Hkm else int(8192 * Wkm / Hkm)
    TH = int(TW * Hkm / Wkm)
    if TH > 8192:
        TH = 8192; TW = int(8192 * Wkm / Hkm)
    q, qhave, qbox = mosaic('qld', zi, mx0, my0, mx1, my1)
    qi = crop_box(q, qbox, mx0, my0, mx1, my1, (TW, TH))
    qh = crop_box(qhave.convert('L'), qbox, mx0, my0, mx1, my1, (TW // 4, TH // 4))
    del q, qhave
    ze = min(zi, 14)
    e, _, ebox = mosaic('eox', ze, mx0, my0, mx1, my1)
    ei = crop_box(e, ebox, mx0, my0, mx1, my1, (TW, TH))
    del e
    # ocean: east of the coast where EOX shows water (dark, blue leaning); also anywhere QLD has no tile
    sw, sh = TW // 4, TH // 4
    es = np.asarray(ei.resize((sw, sh), Image.BILINEAR)).astype(np.float32)
    lons = np.array([unmerc(mx0 + (i + .5) / sw * (mx1 - mx0), my0)[1] for i in range(sw)])
    lats = np.array([unmerc(mx0, my0 + (j + .5) / sh * (my1 - my0))[0] for j in range(sh)])
    LO, LA = np.meshgrid(lons, lats)
    region = (LO > LON_OCEAN) | ((LA > -26.385) & (LO > 153.06))
    qs = np.asarray(qi.resize((sw, sh), Image.BILINEAR)).astype(np.float32)
    water = (es[..., 2] > es[..., 0] + 6) & (es[..., 2] > es[..., 1] - 3) & (es.mean(2) < 120)
    mask = np.maximum((region & water).astype(np.float32), 1 - np.asarray(qh, np.float32) / 255)
    mimg = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)).resize((TW, TH), Image.BILINEAR)
    ei = ei.point(lambda v: min(255, int(v * 1.25 + 4)))
    sat = Image.composite(ei, qi, mimg)
    del ei, qi
    sat = ImageEnhance.Brightness(sat).enhance(1.05)
    sat = ImageEnhance.Contrast(sat).enhance(1.15)
    sat = ImageEnhance.Color(sat).enhance(1.12)
    sat.save(os.path.join(out, 'sat.jpg'), quality=90)

    # route on the terrain
    lift = 0.0045 * d
    route = [[round(x - (gx0 + gx1) / 2, 4), round(height(x, z) + lift * 0.4, 4), round(z - (gz0 + gz1) / 2, 4)] for x, z in XZ]
    off = np.array([(gx0 + gx1) / 2, 0, (gz0 + gz1) / 2])
    labels = []
    for l in cfg['labels']:
        x, z = xz(l['y'], l['x'])
        labels.append(dict(l, p=[round(x - off[0], 4), round(height(x, z), 4), round(z - off[2], 4)]))
    c = cam[0] - off; tt = np.array(t) - off
    scene = dict(W=Wkm, H=Hkm, GX=GX, GY=GY, h=[round(float(v), 4) for v in hs.flatten()],
                 route=route, labels=labels, cam=dict(x=c[0], y=c[1], z=c[2], tx=tt[0], ty=tt[1], tz=tt[2], fov=VFOV),
                 radius=0.0042 * d, fog=[1.05 * d, 2.2 * d], color=cfg['color'], style=cfg['style'],
                 zones=cfg.get('zones', []), rw=RW, rh=RH, bleed=BLEED, bind=BIND,
                 title=cfg['title'], kick=cfg['kick'], sub=cfg['sub'], h1px=h1pt(cfg['title']) * 0.3528 * 2400 / 297)
    json.dump(scene, open(os.path.join(out, 'scene.json'), 'w'))
    info = dict(yaw=float(yaw), pitch=PITCH_, d=float(d), EX=EX, Wkm=Wkm, Hkm=Hkm, zi=zi, tex=(TW, TH), span=float(span))
    json.dump(info, open(os.path.join(out, 'info.json'), 'w'))
    return info


def render(out):
    """Render the scene in headless Chromium, keep the picture as a high quality JPEG and drop the working files."""
    png = os.path.join(out, 'map.png')
    subprocess.run([sys.executable, os.path.join(HERE, 'shot.py'), out, png], check=True)
    Image.open(png).convert('RGB').save(os.path.join(out, 'map.jpg'), quality=93, optimize=True)
    for f in ('map.png', 'sat.jpg', 'scene.json'):
        try: os.remove(os.path.join(out, f))
        except OSError: pass


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    from rides import RIDES, R
    for rid in sys.argv[1:]:
        cfg = RIDES[rid]
        out = os.path.join(STATE, 'maps', cfg['slug'])
        print(rid, build(rid, cfg, out, R))
        render(out)
