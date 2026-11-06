"""Render angled open-book close-up mockups of Look Up, Fin! spreads.

Run from the site folder:  python3 tools/render_mockups.py
Writes public/art/mock-*.jpg
"""
import math
import numpy as np
import cv2

ART = "public/art/"
P = 1400  # page texture size (square 8.5 x 8.5 book)


def load(name):
    return cv2.imread(ART + name + ".jpg").astype(np.float32) / 255.0  # BGR


def square(img, x0=None):
    h, w = img.shape[:2]
    s = min(h, w)
    if x0 is None:
        x0 = (w - s) // 2
    y0 = (h - s) // 2
    return cv2.resize(img[y0:y0 + s, x0:x0 + s], (P, P), interpolation=cv2.INTER_AREA)


def halves(img):
    """Split a 2:1 spread painting into left and right square pages."""
    h, w = img.shape[:2]
    left = cv2.resize(img[:, : w // 2], (P, P), interpolation=cv2.INTER_AREA)
    right = cv2.resize(img[:, w // 2:], (P, P), interpolation=cv2.INTER_AREA)
    return left, right


# ---------- book geometry (units: page width = 1) ----------
ZC = 0.012      # cover board top
TB = 0.010      # page block thickness at the spine
A, K = 0.030, 0.065   # rise of the pages out of the gutter
B = 0.030       # gentle dome across each page
M = 0.022       # cover overhang


def f(a):
    return TB + A * (1 - np.exp(-a / K)) + B * np.sin(np.pi * a)


def fp(a):
    return A / K * np.exp(-a / K) + B * np.pi * np.cos(np.pi * a)


_aa = np.linspace(0, 1, 4001)
_ss = np.concatenate([[0], np.cumsum(np.sqrt(1 + fp(_aa[1:]) ** 2) * np.diff(_aa))])
S1 = _ss[-1]


def arclen(a):
    return np.interp(a, _aa, _ss)


def wood_table(X, Y, seed=7):
    """Pale, sunlit beech: one continuous panel, soft long grain running along X,
    peachy-blush tone (Montessori-style). X, Y are table-plane coords."""
    rng = np.random.default_rng(seed)
    x0, x1, y0, y1 = -5.0, 5.0, -4.0, 6.0
    nx, ny = 1000, 4000  # slow along the grain, faster across it

    def fbm(octaves):
        acc = np.zeros((ny, nx), np.float32)
        amp, tot = 1.0, 0.0
        for gx, gy in octaves:
            n = rng.standard_normal((gy, gx)).astype(np.float32)
            acc += amp * cv2.resize(n, (nx, ny), interpolation=cv2.INTER_CUBIC)
            tot += amp
            amp *= 0.5
        return acc / tot

    warp = fbm([(4, 18), (8, 40), (16, 90)])        # big lazy waves in the grain
    fine = fbm([(40, 1400), (80, 2600)])            # faint fibre texture
    u = ((X - x0) / (x1 - x0) * (nx - 1)).astype(np.float32)
    v = ((Y - y0) / (y1 - y0) * (ny - 1)).astype(np.float32)
    w = cv2.remap(warp, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    fn = cv2.remap(fine, u, v, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    # long, soft growth lines; low contrast like beech
    phase = (Y * 16.0 + w * 3.0) * np.pi
    lines = (0.5 + 0.5 * np.sin(phase)) ** 6 + 0.35 * (0.5 + 0.5 * np.sin(phase * 2.3 + 1.1)) ** 10
    light = np.array([0.735, 0.835, 0.93], np.float32)   # BGR ~ rgb(237,213,187)
    dark = np.array([0.62, 0.735, 0.865], np.float32)    # BGR ~ rgb(221,187,158)
    mix = np.clip(0.35 * lines + 0.07 * fn + 0.08, 0, 1)
    col = light[None, None, :] * (1 - mix[..., None]) + dark[None, None, :] * mix[..., None]
    col *= np.array([0.83, 0.86, 0.90], np.float32)  # ~15% deeper, a little richer in the warm channels
    return col.astype(np.float32)


def render(tex, out_w, out_h, target, az, el, dist, focal, roll, focus, light=(-0.45, -0.35, 1.0),
           blur_k=1.0, seed=1, ss=1.25, table="white"):
    rng = np.random.default_rng(seed)
    W, H = int(out_w * ss), int(out_h * ss)
    fpx = focal * ss
    T = np.array(target, np.float64)
    az, el, roll = map(math.radians, (az, el, roll))
    C = T + dist * np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    F = T - C
    F /= np.linalg.norm(F)
    R = np.cross(F, [0, 0, 1.0])
    R /= np.linalg.norm(R)
    U = np.cross(R, F)

    jj, ii = np.meshgrid(np.arange(W, dtype=np.float32) - W / 2, np.arange(H, dtype=np.float32) - H / 2)
    cr, sr = math.cos(roll), math.sin(roll)
    px = (cr * jj - sr * ii) / fpx
    py = (sr * jj + cr * ii) / fpx
    d = F[None, None, :] + px[..., None] * R[None, None, :] - py[..., None] * U[None, None, :]
    d = (d / np.linalg.norm(d, axis=2, keepdims=True)).astype(np.float32)
    dx, dy, dz = d[..., 0], d[..., 1], d[..., 2]
    Cx, Cy, Cz = (np.float32(v) for v in C)

    INF = np.float32(1e9)
    best = np.full((H, W), INF, np.float32)
    mat = np.zeros((H, W), np.uint8)  # 0 table,1 page,2 block,3 cover top,4 cover edge

    # ---- page surface: march then bisect ----
    zmax = ZC + TB + A + B
    t0 = (zmax - Cz) / dz
    t1 = (ZC - Cz) / dz
    g = lambda t: Cz + t * dz - (ZC + f(np.minimum(np.abs(Cx + t * dx), 1.0)))
    steps = 120
    lo = t0.copy()
    glo = g(lo)
    found = np.zeros((H, W), bool)
    tl, th = t0.copy(), t0.copy()
    for k in range(1, steps + 1):
        t = t0 + (t1 - t0) * (k / steps)
        gt = g(t)
        hit = (~found) & (glo > 0) & (gt <= 0)
        tl[hit], th[hit] = lo[hit], t[hit]
        found |= hit
        lo, glo = t, gt
    for _ in range(22):
        mid = (tl + th) / 2
        pos = g(mid) > 0
        tl = np.where(pos, mid, tl)
        th = np.where(pos, th, mid)
    tp = (tl + th) / 2
    X, Y = Cx + tp * dx, Cy + tp * dy
    ok = found & (np.abs(X) <= 1) & (Y >= 0) & (Y <= 1) & (tp > 0)
    upd = ok & (tp < best)
    best[upd], mat[upd] = tp[upd], 1
    pageX, pageY = X, Y

    # ---- page block faces ----
    def face(t, cond, m):
        nonlocal best, mat
        u = cond & (t > 0) & (t < best)
        best[u], mat[u] = t[u], m

    with np.errstate(divide="ignore", invalid="ignore"):
        t = (0 - Cy) / dy
        X, Z = Cx + t * dx, Cz + t * dz
        face(t, (np.abs(X) <= 1) & (Z >= ZC) & (Z <= ZC + f(np.minimum(np.abs(X), 1))), 2)
        blockFrontZ, blockFrontX = Z, X
        for sx in (-1.0, 1.0):
            t = (sx - Cx) / dx
            Y, Z = Cy + t * dy, Cz + t * dz
            face(t, (Y >= 0) & (Y <= 1) & (Z >= ZC) & (Z <= ZC + f(1.0)), 2)
        # cover top
        t = (ZC - Cz) / dz
        X, Y = Cx + t * dx, Cy + t * dy
        face(t, (np.abs(X) <= 1 + M) & (Y >= -M) & (Y <= 1 + M), 3)
        coverX, coverY = X, Y
        # cover edges
        t = (-M - Cy) / dy
        X, Z = Cx + t * dx, Cz + t * dz
        face(t, (np.abs(X) <= 1 + M) & (Z >= 0) & (Z <= ZC), 4)
        for sx in (-1.0, 1.0):
            t = (sx * (1 + M) - Cx) / dx
            Y, Z = Cy + t * dy, Cz + t * dz
            face(t, (Y >= -M) & (Y <= 1 + M) & (Z >= 0) & (Z <= ZC), 4)
        # table
        tt = (0 - Cz) / dz
    tableX, tableY = Cx + tt * dx, Cy + tt * dy
    tab = mat == 0
    best[tab] = np.where(tt[tab] > 0, tt[tab], 50)

    L = np.array(light, np.float32)
    L /= np.linalg.norm(L)
    img = np.zeros((H, W, 3), np.float32)

    # ---- pages ----
    m1 = mat == 1
    aX = np.clip(np.abs(pageX), 0, 1)
    s = arclen(aX) / S1
    U_ = np.where(pageX < 0, P * (1 - s), P + P * s).astype(np.float32)
    V_ = ((1 - pageY) * P).astype(np.float32)
    samp = cv2.remap(tex, U_, V_, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    sg = np.sign(pageX)
    slope = sg * fp(aX)
    nrm = np.stack([-slope, np.zeros_like(slope), np.ones_like(slope)], -1)
    nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    lam = np.clip((nrm * L).sum(-1), 0, 1)
    shade = 0.66 + 0.42 * lam
    ao = 1 - 0.62 * np.exp(-aX / 0.022) - 0.10 * np.exp(-aX / 0.10)
    # soft sheen where the paper turns toward the light
    sheen = 0.05 * np.clip(lam - 0.9, 0, 1) / 0.1
    paper = 1 + 0.025 * (rng.standard_normal((H, W)).astype(np.float32))
    paper = cv2.GaussianBlur(paper, (0, 0), 0.8)
    pg = samp * (shade * ao * paper)[..., None] + sheen[..., None]
    # paper is never pure white in a photo; lift and cool slightly
    pg = pg * np.array([0.985, 0.975, 0.965], np.float32) + 0.01
    img[m1] = pg[m1]

    # ---- page block edges: stacked sheets ----
    m2 = mat == 2
    zrel = np.clip((blockFrontZ - ZC) / (TB + A + B), 0, 1)
    sheets = 0.9 + 0.07 * np.sin(zrel * 2 * np.pi * 14 + 1.3) + 0.03 * rng.standard_normal((H, W)).astype(np.float32)
    edge = np.array([0.88, 0.92, 0.95], np.float32)[None, None, :] * (sheets * (0.78 + 0.22 * zrel))[..., None]
    img[m2] = edge[m2]

    # ---- cloth cover ----
    cloth_base = np.array([0.66, 0.40, 0.14], np.float32)  # BGR ~ rgb(36,102,168)
    weave = 1 + 0.06 * rng.standard_normal((H, W)).astype(np.float32)
    weave = cv2.GaussianBlur(weave, (0, 0), 0.7)
    m3 = mat == 3
    cov = cloth_base[None, None, :] * (weave * 1.0)[..., None]
    img[m3] = cov[m3]
    m4 = mat == 4
    img[m4] = (cloth_base * 0.62)[None, :] * weave[m4][:, None]

    # ---- table with soft shadow ----
    book = (mat != 0).astype(np.float32)
    sh_off = (int(0.018 * W), int(0.028 * H))
    Mtx = np.float32([[1, 0, sh_off[0]], [0, 1, sh_off[1]]])
    shadow = cv2.warpAffine(book, Mtx, (W, H))
    shadow = cv2.GaussianBlur(shadow, (0, 0), 0.03 * W)
    contact = cv2.GaussianBlur(book, (0, 0), 0.006 * W)
    yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    if table == "dark":
        # deep navy, nearly black (close to the site's --abyss #0a1a30), matte with fine grain
        base = np.array([0.20, 0.115, 0.06], np.float32)  # BGR ~ rgb(15,29,51)
        grain = 1 + 0.05 * cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 1.2)
        ry, rx = np.meshgrid(np.linspace(-1, 1, H), np.linspace(-1, 1, W), indexing="ij")
        pool = (0.78 + 0.32 * np.exp(-((rx * 0.8) ** 2 + (ry * 0.9) ** 2))).astype(np.float32)  # soft light pool
        tablec = base[None, None, :] * (grain * pool)[..., None]
    elif table == "wood":
        tablec = wood_table(tableX.astype(np.float32), tableY.astype(np.float32))
        sy, sx = np.meshgrid(np.linspace(0, 1, H), np.linspace(0, 1, W), indexing="ij")
        sun = np.exp(-(((sx - 0.15) / 0.75) ** 2 + ((sy - 0.05) / 0.8) ** 2)).astype(np.float32)
        tablec = np.minimum(tablec * (0.99 + 0.10 * sun)[..., None], 1.0) + (np.array([0.0, 0.012, 0.03], np.float32) * sun[..., None])
    else:
        tablec = np.array([0.955, 0.985, 1.0], np.float32)[None, None, :] * (0.975 + 0.025 * yy)[..., None]  # BGR: warm white
    tablec = tablec * (1 - 0.16 * shadow - 0.15 * contact)[..., None]
    img[tab] = tablec[tab]

    # ---- depth of field ----
    depth = best
    tf = focus
    coc = np.abs(depth - tf) / depth * blur_k * 60 * ss
    levels = [0, 1.2, 2.5, 4.5, 7.5, 12]
    pyr = [img] + [cv2.GaussianBlur(img, (0, 0), s_ * ss) for s_ in levels[1:]]
    cocb = cv2.GaussianBlur(coc, (0, 0), 3 * ss)
    out = np.zeros_like(img)
    idx = np.interp(cocb, [l * ss for l in levels], np.arange(len(levels)))
    for k in range(len(levels)):
        w = np.clip(1 - np.abs(idx - k), 0, 1)
        out += pyr[k] * w[..., None]

    # light falloff + grain
    vy, vx = np.meshgrid(np.linspace(-1, 1, H), np.linspace(-1, 1, W), indexing="ij")
    vig = 1 - 0.03 * (vx ** 2 + vy ** 2)
    out *= vig[..., None].astype(np.float32)
    out += 0.008 * rng.standard_normal((H, W, 1)).astype(np.float32)
    out = cv2.resize(np.clip(out, 0, 1), (out_w, out_h), interpolation=cv2.INTER_AREA)
    return (out * 255).astype(np.uint8), C


def focus_dist(C, point):
    return float(np.linalg.norm(np.array(point) - C))


def shot(name, tex, **kw):
    target = kw["target"]
    focus_pt = kw.pop("focus_pt", target)
    C = np.array(target) + kw["dist"] * np.array([
        math.cos(math.radians(kw["el"])) * math.sin(math.radians(kw["az"])),
        -math.cos(math.radians(kw["el"])) * math.cos(math.radians(kw["az"])),
        math.sin(math.radians(kw["el"])),
    ])
    if DARK:
        kw["table"] = "dark"
        name = name.replace(".jpg", "-dark.jpg")
    elif WOOD:
        kw["table"] = "wood"
        name = name.replace(".jpg", "-wood.jpg")
    img, _ = render(tex, focus=focus_dist(C, focus_pt), **kw)
    cv2.imwrite(ART + name, img, [cv2.IMWRITE_JPEG_QUALITY, 86, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
    print("wrote", ART + name)


WOOD = False
DARK = False

if __name__ == "__main__":
    import sys
    WOOD = "--wood" in sys.argv
    DARK = "--dark" in sys.argv
    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    nook, quad = load("nook"), load("quadrant")
    deep = load("deep")
    dl, dr = halves(deep)
    hl, hr = halves(load("hideandseek"))

    if not only or "opening" in only:
        # the real typeset spread exported from InDesign (pp. 4-5)
        sp = cv2.imread("exports/Look_Up_Fin_spread_pp04-05.jpg").astype(np.float32) / 255.0
        h, w = sp.shape[:2]
        tex = np.hstack([cv2.resize(sp[:, : w // 2], (P, P), interpolation=cv2.INTER_AREA),
                         cv2.resize(sp[:, w // 2:], (P, P), interpolation=cv2.INTER_AREA)])
        shot("mock-opening.jpg", tex, out_w=2000, out_h=1333,
             target=(0.15, 0.45, 0.04), az=0, el=60, dist=2.4, focal=3300, roll=-12,
             focus_pt=(0.60, 0.34, 0.05), blur_k=0.15, seed=3)

    if not only or "quadrant" in only:
        # pp. 20-21 from the final print PDF: the text page facing the quadrant
        sp = cv2.imread("exports/Look_Up_Fin_spread_pp20-21.jpg").astype(np.float32) / 255.0
        h, w = sp.shape[:2]
        tex = np.hstack([cv2.resize(sp[:, : w // 2], (P, P), interpolation=cv2.INTER_AREA),
                         cv2.resize(sp[:, w // 2:], (P, P), interpolation=cv2.INTER_AREA)])
        shot("mock-quadrant.jpg", tex, out_w=2000, out_h=1333,
             target=(0.31, 0.47, 0.04), az=-10, el=66, dist=2.4, focal=3050, roll=12,
             focus_pt=(0.5, 0.5, 0.04), blur_k=0.0, seed=5)
