"""Tile fetching, mosaics, camera maths for the ride map sheets."""
import io, math, os, json
from concurrent.futures import ThreadPoolExecutor
import numpy as np, requests
from PIL import Image
from paths import CACHE

URLS = {
    'dem': 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
    'qld': 'https://spatial-img.information.qld.gov.au/arcgis/rest/services/Basemaps/LatestStateProgram_AllUsers/ImageServer/tile/{z}/{y}/{x}',
    'eox': 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{z}/{y}/{x}.jpg',  # 2016, CC BY 4.0
}
S = requests.Session()
S.headers['User-Agent'] = 'Element Outdoors ride sheets (+https://elementoutdoors.github.io/routes/)'


def merc(lat, lon):
    return (lon + 180) / 360, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2


def unmerc(mx, my):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * my)))), mx * 360 - 180


def fetch(layer, z, x, y):
    p = os.path.join(CACHE, layer, str(z), str(x), f'{y}')
    if os.path.exists(p):
        return p if os.path.getsize(p) else None
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for _ in range(3):
        try:
            r = S.get(URLS[layer].format(z=z, x=x, y=y), timeout=30)
            if r.status_code == 200 and r.content:
                open(p, 'wb').write(r.content); return p
            if r.status_code == 404:
                open(p, 'wb').close(); return None
        except Exception:
            pass
    return None


def mosaic(layer, z, mx0, my0, mx1, my1):
    """Tiles covering a mercator box. Returns RGB(A) image and the exact mercator box it covers."""
    n = 2 ** z
    tx0, ty0 = int(mx0 * n), int(my0 * n)
    tx1, ty1 = int(mx1 * n), int(my1 * n)
    jobs = [(x, y) for y in range(ty0, ty1 + 1) for x in range(tx0, tx1 + 1)]
    with ThreadPoolExecutor(16) as ex:
        paths = list(ex.map(lambda t: fetch(layer, z, *t), jobs))
    W, H = (tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256
    mode = 'RGB'
    out = Image.new(mode, (W, H), (0, 0, 0))
    have = Image.new('L', (W, H), 0)
    for (x, y), p in zip(jobs, paths):
        if not p:
            continue
        try:
            im = Image.open(p).convert('RGB')
        except Exception:
            continue
        out.paste(im, ((x - tx0) * 256, (y - ty0) * 256))
        have.paste(255, ((x - tx0) * 256, (y - ty0) * 256, (x - tx0 + 1) * 256, (y - ty0 + 1) * 256))
    box = (tx0 / n, ty0 / n, (tx1 + 1) / n, (ty1 + 1) / n)
    return out, have, box


def crop_box(im, box, mx0, my0, mx1, my1, size=None):
    bx0, by0, bx1, by1 = box
    W, H = im.size
    c = ((mx0 - bx0) / (bx1 - bx0) * W, (my0 - by0) / (by1 - by0) * H,
         (mx1 - bx0) / (bx1 - bx0) * W, (my1 - by0) / (by1 - by0) * H)
    if size is None:
        size = (max(1, round(c[2] - c[0])), max(1, round(c[3] - c[1])))
    return im.transform(size, Image.EXTENT, c, Image.BICUBIC)


def dem(mx0, my0, mx1, my1, z=13):
    im, have, box = mosaic('dem', z, mx0, my0, mx1, my1)
    a = np.asarray(im).astype(np.float64)
    h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
    him = Image.fromarray(h.astype(np.float32), mode='F')
    return him, box


# ---------- camera ----------
def cam_basis(t, yaw, pitch, d):
    """yaw: forward direction angle on the ground, 0 = north (-z), 90 = east (+x)."""
    f = np.array([math.sin(math.radians(yaw)), 0, -math.cos(math.radians(yaw))])
    c = np.array(t) - f * d * math.cos(math.radians(pitch)) + np.array([0, d * math.sin(math.radians(pitch)), 0])
    F = np.array(t) - c; F /= np.linalg.norm(F)
    R = np.cross(F, [0, 1, 0]); R /= np.linalg.norm(R)
    U = np.cross(R, F)
    return c, F, R, U, f


def project(P, cam, vfov, aspect):
    c, F, R, U, _ = cam
    v = P - c
    zc = v @ F
    th = math.tan(math.radians(vfov) / 2)
    return np.stack([(v @ R) / (zc * th * aspect), (v @ U) / (zc * th), zc], 1)


def fit_camera(P, yaw, pitch, vfov, aspect, box):
    """Distance and target so points P (n,3) fill box (x0,x1,y0,y1) in NDC."""
    x0, x1, y0, y1 = box
    t = P.mean(0).copy(); t[1] = 0
    d = np.ptp(P[:, [0, 2]], 0).max() * 1.2 + 0.5
    th = math.tan(math.radians(vfov) / 2)
    for _ in range(60):
        cam = cam_basis(t, yaw, pitch, d)
        q = project(P, cam, vfov, aspect)
        if (q[:, 2] <= 0).any():
            d *= 1.5; continue
        s = max((q[:, 0].max() - q[:, 0].min()) / (x1 - x0), (q[:, 1].max() - q[:, 1].min()) / (y1 - y0))
        cx = (q[:, 0].max() + q[:, 0].min()) / 2 - (x0 + x1) / 2
        cy = (q[:, 1].max() + q[:, 1].min()) / 2 - (y0 + y1) / 2
        zm = np.median(q[:, 2])
        _, F, R, U, f = cam
        t = t + R * cx * zm * th * aspect + f * cy * zm * th / math.sin(math.radians(pitch))
        d *= s ** 0.8
        if abs(s - 1) < 0.002 and abs(cx) < 0.002 and abs(cy) < 0.002:
            break
    return t, d


def ground_hits(cam, vfov, aspect, ndc_pts, y=0.0):
    c, F, R, U, _ = cam
    th = math.tan(math.radians(vfov) / 2)
    out = []
    for nx, ny in ndc_pts:
        dirv = F + R * nx * th * aspect + U * ny * th
        if dirv[1] >= -1e-6:
            dirv[1] = -0.05
        k = (y - c[1]) / dirv[1]
        out.append(c + dirv * k)
    return np.array(out)
