"""
bake.py - run sim.py for a fire type and bake flipbook atlases with lifecycle clips.

    python tools/fire/bake.py campfire                # one type
    python tools/fire/bake.py all                     # every type (skips ones already in fire_atlas.json unless --force)
    python tools/fire/bake.py campfire --force

Per type it writes (assets/fire/):
    fire_<t>_flame.webp  fire_<t>_smoke.webp  fire_<t>_heat.png     (full size)
    fire_<t>_flame_low.webp fire_<t>_smoke_low.webp                 (half-size frames for phones)
and merges the type into fire_atlas.json (clips, frame ranges, fps, loop flags, light data).

Pipeline per 'life' type (one scripted lifecycle run of the 3D solver):
    ignite (supply 0.06 -> 0.22, 1.5 s) -> growth (0.22 -> 1, 3 s) -> settle -> three windows of the developed fire
    (each becomes one seamless looping variant: crossfaded seam, variant 1 mirrored, each with its own detail noise)
    -> decay (supply 1 -> 0.03, 3 s) ; plus a branch copy of the developed sim that is hit by water spray (extinguish).
'tile' types are periodic in x (tileable left-right) and only have loops. 'shot' types are one-shot clips.

Rendering (orthographic along y): emission-absorption ray march. Soot incandescence (blackbody-like ramp of the
temperature), blue chemiluminescence from the lean/premixed part of the reaction, orange from the rich part,
soot absorbs. Fields are masked by a soft 3D window (alpha reaches exactly zero well inside the domain), upsampled
smoothly, and modulated by a scrolling periodic noise volume plus a small 2D warp (cosmetic sub-grid detail).
"""
import argparse, copy, json, os, sys, time
import numpy as np
from scipy import ndimage as ndi
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import sim as S  # noqa: E402
import presets as PR  # noqa: E402

N_LOOP, M_OVER = 24, 8          # loop frames at 24 fps, cross-fade overlap
LOOP_FPS = 24
STAGE_FPS = 8
STAGE_FRAMES = dict(ignite=10, growth=20, decay=20, extinguish=12)
UP_F, UP_S = 3, 2               # render upsampling of the sim grid: flame, smoke/heat
NVAR = 3
WEBP_Q = dict(flame=28, smoke=50)
LOW_SCALE = 0.5


def log(msg):
    print(msg, flush=True)


# ------------------------------------------------------------------------------------------
def planck_rgb(tc):
    """Approximate colour of a blackbody at tc kelvin (Tanner Helland fit), 0..1."""
    t = np.asarray(tc, float) / 100.0
    r = np.where(t <= 66, 255.0, 329.698727446 * np.power(np.maximum(t - 60, 1e-3), -0.1332047592))
    g = np.where(t <= 66, 99.4708025861 * np.log(np.maximum(t, 1)) - 161.1195681661,
                 288.1221695283 * np.power(np.maximum(t - 60, 1e-3), -0.0755148492))
    b = np.where(t >= 66, 255.0, np.where(t <= 19, 0.0, 138.5177312231 * np.log(np.maximum(t - 10, 1)) - 305.0447927307))
    return np.clip(np.stack([r, g, b], -1) / 255.0, 0, 1)


LUT = planck_rgb(950.0 + 1900.0 * np.linspace(0, 1.15, 256)).astype(np.float32)


def lut_rgb(th):
    return LUT[np.clip((th * (255 / 1.15)).astype(np.int32), 0, 255)]


def make_noise(shape, seed):
    rng = np.random.default_rng(seed)
    out = 0
    for sig, wgt in (((9, 4, 7), 1.0), ((4.5, 2, 3.5), 0.75), ((2.2, 1, 1.8), 0.45)):
        r = rng.standard_normal(shape).astype(np.float32)
        r = ndi.gaussian_filter(r, sig, mode="wrap")
        r /= r.std() + 1e-6
        out = out + wgt * r
    out /= out.std()
    return out.astype(np.float32)


def window3d(nx, ny, nz, periodic, carried=False):
    ss_ = S.smoothstep
    x = (np.arange(nx) + 0.5) / nx
    y = (np.arange(ny) + 0.5) / ny
    z = (np.arange(nz) + 0.5) / nz
    wx = np.ones(nx) if periodic else ss_(0.0, 0.22, np.minimum(x, 1 - x))
    if carried:   # head near the left edge, long tail to the right
        wx = ss_(0.0, 0.07, x) * ss_(0.0, 0.34, 1 - x)
    wy = ss_(0.0, 0.25, np.minimum(y, 1 - y))
    wz = 1.0 - ss_(0.45, 0.93, z)           # taper the top: smoke thins out instead of stopping at a line
    return (wx[:, None, None] * wy[None, :, None] * wz[None, None, :]).astype(np.float32)


def upvol(f, win, up, periodic):
    """sim field (nx,ny,nz) -> volume V[z (top first), y, x] upsampled by `up` in x and z, smooth, tileable if periodic."""
    v = np.transpose(f.astype(np.float32) * win, (2, 1, 0))[::-1]
    v = np.repeat(np.repeat(v, up, axis=0), up, axis=2)
    return ndi.gaussian_filter(v, (up * 0.5, 0, up * 0.5), mode=("nearest", "nearest", "wrap" if periodic else "nearest"))


def warp2d(img, dn, amp, periodic):
    H, W = img.shape[:2]
    pad = 3 if periodic else 0
    if periodic:
        img = np.pad(img, ((0, 0), (pad, pad)) + ((0, 0),) * (img.ndim - 2), mode="wrap")
    dy = amp * dn[0][:H, :W]
    dx = amp * dn[1][:H, :W]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    coords = np.stack([np.clip(yy + dy, 0, H - 1), np.clip(xx + dx + pad, 0, W + 2 * pad - 1)])
    if img.ndim == 2:
        return ndi.map_coordinates(img, coords, order=1, mode="nearest")
    return np.stack([ndi.map_coordinates(img[..., c], coords, order=1, mode="nearest") for c in range(img.shape[2])], -1)


class Renderer:
    def __init__(self, name, grid, seed=1):
        self.name, self.grid = name, grid
        self.k = PR.LOOK[name]
        self.per = bool(S.PRESETS[name].get("periodic"))
        nx, ny, nz = grid
        self.carried = PR.META[name]["kind"] == "carried"
        self.win = window3d(nx, ny, nz, self.per, self.carried)
        self.shape_f = (nz * UP_F, ny, nx * UP_F)
        self.shape_s = (nz * UP_S, ny, nx * UP_S)
        self.noise_f = [make_noise(self.shape_f, seed + 7 + 101 * v) for v in range(NVAR)]
        self.noise_s = [make_noise(self.shape_s, seed + 13 + 211 * v) for v in range(NVAR)]
        mk = lambda sh, s: make_noise((sh[0], 1, sh[2]), s)[:, 0, :]
        self.disp_f = [(mk(self.shape_f, seed + 31 + 17 * v), mk(self.shape_f, seed + 53 + 17 * v)) for v in range(NVAR)]
        self.disp_s = [(mk(self.shape_s, seed + 71 + 17 * v), mk(self.shape_s, seed + 97 + 17 * v)) for v in range(NVAR)]
        self.tint = np.array(self.k.get("tint", (1, 1, 1)), np.float32)
        self.period_f, self.period_s = self.shape_f[0], self.shape_s[0]

    # px of noise scroll for a loop frame index / for a time in seconds
    def shift_loop(self, i, period, scroll):
        return -(i * scroll * period) // N_LOOP

    def shift_time(self, t, period, scroll):
        return -int(t * scroll * period * LOOP_FPS / N_LOOP)

    def flame(self, f, var, shift):
        k = self.k
        th, Sm, R, Rb = (upvol(f[n], self.win, UP_F, self.per) for n in ("th", "S", "R", "Rb"))
        n = np.roll(self.noise_f[var], int(shift), axis=0)
        am = k["noise"]
        thm = np.clip(th * (1 + 0.22 * am * n) + 0.03 * am * n * (th > 0.05), 0, 1.15)
        Sx = np.clip(Sm, 0, None) * np.clip(1 + 0.9 * am * n, 0.05, None)
        g = S.smoothstep(0.15, 0.42, thm) * thm ** 3
        col = lut_rgb(thm) * self.tint
        Es = k["cs"] * Sx[..., None] * g[..., None] * col
        mod = np.clip(1 + 0.7 * am * n, 0.1, None)
        Rm, Rbm = np.clip(R, 0, None) * mod, np.clip(Rb, 0, None) * mod
        blue = np.array([0.16, 0.38, 1.0], np.float32)
        Eb = k["cb"] * Rbm[..., None] * blue * 0.35
        Eo = k["co"] * np.clip(Rm - Rbm, 0, None)[..., None] * col * 0.35
        E = Es + Eb + Eo
        tau = k["ka"] * Sx + 0.02 * np.linalg.norm(E, axis=-1)
        cum = np.cumsum(tau, axis=1) - tau
        I = (E * np.exp(-cum)[..., None]).sum(axis=1)
        I = warp2d(I, self.disp_f[var], k["warp"], self.per)
        out = 1 - np.exp(-k["expo"] * I)
        thsum = float((E.sum(-1) * th).sum() / max(E.sum(), 1e-6))
        return out.astype(np.float32), float(E.sum()), thsum

    def smoke(self, f, var, shift):
        k = self.k
        Sm, P, th = (upvol(f[n], self.win, UP_S, self.per) for n in ("S", "P", "th"))
        n = np.roll(self.noise_s[var], int(shift), axis=0)
        Sx = np.clip(Sm, 0, None) * np.clip(1 + 0.8 * k["noise"] * n, 0.05, None)
        steam = k["smoke_pv"] * np.clip(P, 0, None) * (1 - S.smoothstep(0.08, 0.30, th)) * np.clip(1 + 0.6 * n, 0.1, None)
        dens = Sx + steam
        tau = k["smoke_k"] * dens
        above = np.cumsum(tau, axis=0) - tau
        shade = 0.30 + 0.70 * np.exp(-0.55 * above)
        alb = (k["smoke_albedo"] * Sx + 0.88 * steam) / np.maximum(dens, 1e-6)
        cum = np.cumsum(tau, axis=1) - tau
        contrib = (1 - np.exp(-tau)) * np.exp(-cum)
        glow_k = k.get("smoke_glow", 0.0)
        col = (alb * shade)[..., None] * np.ones(3, np.float32)
        if glow_k > 0:
            # flames light the underside of the plume: warm tint from the local temperature plus an under-light that fades with height
            H = tau.shape[0]
            zi = ((H - 1 - np.arange(H)) / H)[:, None, None]
            gl = glow_k * (np.clip(th, 0, 1) ** 1.2 + 0.35 * np.exp(-zi / 0.18) * np.clip(th.max(), 0, 1) ** 0.5)
            col = col + gl[..., None] * np.array([1.0, 0.42, 0.10], np.float32) * 0.9
        rgb = warp2d((contrib[..., None] * col).sum(axis=1), self.disp_s[var], 0.8, self.per)
        alpha = warp2d(contrib.sum(axis=1), self.disp_s[var], 0.8, self.per)
        return np.concatenate([np.clip(rgb, 0, 1.5), np.clip(alpha, 0, 1)[..., None]], -1).astype(np.float32)

    def heat(self, f):
        th = upvol(f["th"], self.win, UP_S, self.per)
        return np.clip(th.max(axis=1), 0, 1.15).astype(np.float32)


# ------------------------------------------------------------------------------------------
class Clip(dict):
    pass


def new_clip(name, stage, variant, fps, loop):
    return Clip(name=name, stage=stage, variant=variant, fps=fps, loop=loop, flame=[], smoke=[], heat=[], lum=[], mth=[])


def record_frames(sim, rend, clip, nframes, fps, var, loop_phase=False):
    """Record nframes of the running sim into the clip. Smoke every 2nd frame, heat every 4th."""
    spf = int(round(1.0 / (fps * S.DT)))
    for i in range(nframes):
        fields = S.record(sim, spf)
        if loop_phase:
            sf = rend.shift_loop(i % N_LOOP, rend.period_f, rend.k["scroll"])
            ss_ = rend.shift_loop(i % N_LOOP, rend.period_s, 1)
        else:
            sf = rend.shift_time(sim.t, rend.period_f, rend.k["scroll"])
            ss_ = rend.shift_time(sim.t, rend.period_s, 1)
        rgb, lum, mth = rend.flame(fields, var, sf)
        clip["flame"].append(rgb)
        clip["lum"].append(lum)
        clip["mth"].append(mth)
        hot = sim.th > 0.3
        clip.setdefault("wr", []).append(float(sim.w[hot].mean()) if hot.any() else 0.0)
        if i % 2 == 0:
            clip["smoke"].append(rend.smoke(fields, var, ss_))
        if i % 4 == 0:
            clip["heat"].append(rend.heat(fields))
        if i % 8 == 0:
            log(f"   {clip['name']} frame {i}/{nframes}  t={sim.t:.1f}s")


def crossfade(frames, n, m):
    out = []
    for i in range(n):
        if i < m:
            w = i / m
            w = w * w * (3 - 2 * w)
            out.append((1 - w) * frames[n + i] + w * frames[i])
        else:
            out.append(frames[i])
    return out


def make_loop(raw, var):
    """raw clip with N_LOOP+M_OVER frames -> seamless loop clip"""
    c = new_clip(f"loop_{'abc'[var]}", "loop", var, LOOP_FPS, True)
    c["flame"] = crossfade(raw["flame"], N_LOOP, M_OVER)
    c["lum"] = list(crossfade([np.array(x) for x in raw["lum"]], N_LOOP, M_OVER))
    c["mth"] = list(crossfade([np.array(x) for x in raw["mth"]], N_LOOP, M_OVER))
    c["smoke"] = crossfade(raw["smoke"], N_LOOP // 2, M_OVER // 2)
    c["heat"] = crossfade(raw["heat"], N_LOOP // 4, M_OVER // 4)
    if var == 1:   # mirrored variant: different silhouette from the same physics
        c["flame"] = [f[:, ::-1].copy() for f in c["flame"]]
        c["smoke"] = [f[:, ::-1].copy() for f in c["smoke"]]
        c["heat"] = [f[:, ::-1].copy() for f in c["heat"]]
    return c


# ------------------------------------------------------------------------------------------
def ss(a, b, x):
    return float(S.smoothstep(a, b, x))


def run_life(name, seed, rend_seed):
    sched = {"decay_t0": None}

    def supply(t):
        if t < 1.5:
            return 0.06 + 0.16 * ss(0.0, 1.5, t)
        if t < 4.5:
            return 0.22 + 0.78 * ss(1.5, 4.5, t)
        d0 = sched["decay_t0"]
        if d0 is None or t < d0:
            return 1.0
        return 1.0 - 0.97 * ss(d0, d0 + 3.0, t)

    sim = S.Sim(name, seed, supply=supply)
    rend = Renderer(name, sim.grid, rend_seed)
    clips = []
    t0 = time.time()
    c = new_clip("ignite", "ignite", 0, STAGE_FPS, False)
    record_frames(sim, rend, c, STAGE_FRAMES["ignite"], STAGE_FPS, 0)
    clips.append(c)
    c = new_clip("growth", "growth", 0, STAGE_FPS, False)
    record_frames(sim, rend, c, STAGE_FRAMES["growth"], STAGE_FPS, 0)
    clips.append(c)
    t_dev = max(4.5, sim.p["warm"])
    while sim.t < t_dev:
        sim.step()
    log(f"[{name}] developed at t={sim.t:.1f}s ({time.time() - t0:.0f}s)")
    branch = None
    loops = []
    for v in range(NVAR):
        if v == 1:
            branch = copy.deepcopy(sim)
        raw = new_clip("raw", "loop", v, LOOP_FPS, True)
        record_frames(sim, rend, raw, N_LOOP + M_OVER, LOOP_FPS, v, loop_phase=True)
        loops.append(make_loop(raw, v))
    sched["decay_t0"] = sim.t
    c = new_clip("decay", "decay", 0, STAGE_FPS, False)
    record_frames(sim, rend, c, STAGE_FRAMES["decay"], STAGE_FPS, 0)
    clips.append(c)
    tb = branch.t
    branch.water = lambda t: ss(0.0, 0.7, t - tb - 0.15)
    c = new_clip("extinguish", "extinguish", 0, STAGE_FPS, False)
    record_frames(branch, rend, c, STAGE_FRAMES["extinguish"], STAGE_FPS, 0)
    clips.append(c)
    order = {"ignite": 0, "growth": 1, "loop": 2, "decay": 3, "extinguish": 4}
    allc = loops + clips
    allc.sort(key=lambda c: (order[c["stage"]], c["variant"]))
    return sim, rend, allc


def run_tile(name, seed, rend_seed):
    sim = S.Sim(name, seed)
    rend = Renderer(name, sim.grid, rend_seed)
    while sim.t < sim.p["warm"]:
        sim.step()
    loops = []
    for v in range(NVAR):
        raw = new_clip("raw", "loop", v, LOOP_FPS, True)
        record_frames(sim, rend, raw, N_LOOP + M_OVER, LOOP_FPS, v, loop_phase=True)
        loops.append(make_loop(raw, v))
    return sim, rend, loops


def run_shot(name, seed, rend_seed):
    clips = []
    rend = None

    def supply(t):
        return ss(0.0, 0.12, t) * (1.0 - ss(0.35, 0.75, t))
    for v in range(NVAR):
        sim = S.Sim(name, seed + v + 1, supply=supply)
        rend = rend or Renderer(name, sim.grid, rend_seed)
        c = new_clip(f"{name}_{'abc'[v]}", "shot", v, LOOP_FPS, False)
        record_frames(sim, rend, c, 20, LOOP_FPS, v)
        clips.append(c)
    return sim, rend, clips


def run_blast(name, seed, rend_seed):
    """Explosion: fireball (24 fps, 2 s) -> rising plume (8 fps, 3 s) -> low burning residue loop. Two variants (two sims)."""
    clips = []
    rend = None

    def supply(t):
        return 0.3 * ss(1.5, 3.0, t)      # the residue vents light up after the blast
    for v in range(2):
        sim = S.Sim(name, v, supply=supply)
        rend = rend or Renderer(name, sim.grid, rend_seed)
        c = new_clip(f"fireball_{'ab'[v]}", "fireball", v, LOOP_FPS, False)
        record_frames(sim, rend, c, 48, LOOP_FPS, v)
        clips.append(c)
        c = new_clip(f"plume_{'ab'[v]}", "plume", v, STAGE_FPS, False)
        record_frames(sim, rend, c, 24, STAGE_FPS, v)
        clips.append(c)
        while sim.t < 8.0:
            sim.step()
        raw = new_clip("raw", "loop", v, LOOP_FPS, True)
        record_frames(sim, rend, raw, N_LOOP + M_OVER, LOOP_FPS, v, loop_phase=True)
        lp = make_loop(raw, v)
        lp["name"], lp["stage"] = f"residue_{'ab'[v]}", "residue"
        clips.append(lp)
    order = {"fireball": 0, "plume": 1, "residue": 2}
    clips.sort(key=lambda c: (order[c["stage"]], c["variant"]))
    return sim, rend, clips


# ------------------------------------------------------------------------------------------
def srgb(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def to8(x):
    return np.clip(np.round(x * 255), 0, 255).astype(np.uint8)


def bbox(frames, thr, margin, periodic, mult=2):
    H, W = frames[0].shape[:2]
    any_ = np.zeros((H, W), bool)
    for f in frames:
        any_ |= f > thr
    ys = np.where(any_.any(axis=1))[0]
    xs = np.where(any_.any(axis=0))[0]
    if len(ys) == 0:
        return 0, W, 0
    y0 = max(0, ys.min() - margin)
    if periodic:
        x0, x1 = 0, W
    else:
        half = max(W // 2 - xs.min(), xs.max() + 1 - W // 2) + margin
        half = min(W // 2, int(np.ceil(half / mult) * mult))
        x0, x1 = W // 2 - half, W // 2 + half
    h = int(np.ceil((H - y0) / mult) * mult)
    return x0, x1, max(0, H - h)


def bbox_free(frames, thr, margin, mult=2):
    H, W = frames[0].shape[:2]
    any_ = np.zeros((H, W), bool)
    for f in frames:
        any_ |= f > thr
    ys = np.where(any_.any(axis=1))[0]
    xs = np.where(any_.any(axis=0))[0]
    if len(ys) == 0:
        return 0, W, 0, H
    x0, x1 = max(0, xs.min() - margin), min(W, xs.max() + 1 + margin)
    y0, y1 = max(0, ys.min() - margin), min(H, ys.max() + 1 + margin)
    x1 = x0 + int(np.ceil((x1 - x0) / mult) * mult)
    y1 = y0 + int(np.ceil((y1 - y0) / mult) * mult)
    return x0, min(x1, W), y0, min(y1, H)


def atlas_cols(n, fw, fh):
    return int(max(1, round(np.sqrt(n * fh / fw))))


def make_atlas(frames, cols):
    n = len(frames)
    h, w, ch = frames[0].shape
    rows = (n + cols - 1) // cols
    at = np.zeros((rows * h, cols * w, ch), np.uint8)
    for i, im in enumerate(frames):
        r, c = divmod(i, cols)
        at[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    return at, rows


def resize_frames(frames, scale):
    out = []
    for f in frames:
        h, w, ch = f.shape
        nh, nw = max(2, int(round(h * scale / 2) * 2)), max(2, int(round(w * scale / 2) * 2))
        out.append(np.stack([np.asarray(Image.fromarray(f[..., c]).resize((nw, nh), Image.BOX)) for c in range(ch)], -1))
    return out


def save_webp(arr, path, quality, exact, alpha_q=70):
    Image.fromarray(arr, "RGBA").save(path, "WEBP", quality=quality, method=5, alpha_quality=alpha_q, exact=exact)
    return os.path.getsize(path)


def write_type(name, sim, rend, clips, outdir, seed):
    meta = PR.META[name]
    per = rend.per
    has_flame = meta.get("flame", True)
    flames = [f for c in clips for f in c["flame"]]
    smokes = [f for c in clips for f in c["smoke"]]
    heats = [f for c in clips for f in c["heat"]]
    # ---- flame ----
    free = meta["kind"] == "carried"
    if free:
        fx0, fx1, fy0, fy1 = bbox_free([f.max(-1) for f in flames], 0.02, 6)
    else:
        fx0, fx1, fy0 = bbox([f.max(-1) for f in flames], 0.02, 6, per)
        fy1 = None
    fl8 = []
    for f in flames:
        a = f.max(-1)[fy0:fy1, fx0:fx1]
        straight = np.where(a[..., None] > 1e-4, f[fy0:fy1, fx0:fx1] / np.maximum(a[..., None], 1e-4), 0.0)
        fl8.append(to8(np.concatenate([srgb(np.clip(straight, 0, 1)), a[..., None]], -1)))   # sRGB colour, linear alpha, straight (not premultiplied)
    fh, fw = fl8[0].shape[:2]
    # ---- smoke ----
    if free:
        sx0, sx1, sy0, sy1 = bbox_free([s[..., 3] for s in smokes], 0.012, 4)
    else:
        sx0, sx1, sy0 = bbox([s[..., 3] for s in smokes], 0.012, 4, per)
        sy1 = None
    sm8 = []
    for s in smokes:
        a = s[..., 3][sy0:sy1, sx0:sx1]
        rgb = s[..., :3][sy0:sy1, sx0:sx1]
        col = np.where(a[..., None] > 1e-4, rgb / np.maximum(a[..., None], 1e-4), 0.0)
        sm8.append(np.concatenate([to8(srgb(np.clip(col, 0, 1))), (to8(a) // 4 * 4)[..., None]], -1))   # 6-bit alpha: the lossless alpha channel is most of the file
    sh, sw = sm8[0].shape[:2]
    # ---- heat ----
    if free:
        hx0, hx1, hy0, hy1 = bbox_free(heats, 0.05, 3)
    else:
        hx0, hx1, hy0 = bbox(heats, 0.05, 3, per)
        hy1 = None
    ht8 = [to8(np.round(np.power(np.clip(h[hy0:hy1, hx0:hx1], 0, 1), 0.8) * 40) / 40)[..., None] for h in heats]
    hh, hw = ht8[0].shape[:2]
    files = {}
    sizes = {}
    for tag, scale in (("", 1.0), ("_low", LOW_SCALE)):
        if has_flame:
            fr = fl8 if scale == 1 else resize_frames(fl8, scale)
            cols = atlas_cols(len(fr), fr[0].shape[1], fr[0].shape[0])
            at, rows = make_atlas(fr, cols)
            p = os.path.join(outdir, f"fire_{name}_flame{tag}.webp")
            at[at[..., 3] < 3] = 0
            sizes["flame" + tag] = save_webp(at, p, WEBP_Q["flame"], False, 45)
            files["flame" + tag] = dict(file=os.path.basename(p), frame_px=[fr[0].shape[1], fr[0].shape[0]], cols=cols, rows=rows)
        fr = sm8 if scale == 1 else resize_frames(sm8, scale)
        cols = atlas_cols(len(fr), fr[0].shape[1], fr[0].shape[0])
        at, rows = make_atlas(fr, cols)
        p = os.path.join(outdir, f"fire_{name}_smoke{tag}.webp")
        sizes["smoke" + tag] = save_webp(at, p, WEBP_Q["smoke"], False, 100)
        files["smoke" + tag] = dict(file=os.path.basename(p), frame_px=[fr[0].shape[1], fr[0].shape[0]], cols=cols, rows=rows)
    cols = atlas_cols(len(ht8), hw, hh)
    at, rows = make_atlas(ht8, cols)
    p = os.path.join(outdir, f"fire_{name}_heat.webp")
    Image.fromarray(at[..., 0], "L").convert("RGB").save(p, "WEBP", quality=75, method=5)
    sizes["heat"] = os.path.getsize(p)
    files["heat"] = dict(file=os.path.basename(p), frame_px=[hw, hh], cols=cols, rows=rows)

    dx = sim.dx
    mf, ms = dx / UP_F, dx / UP_S
    layers = {}
    if has_flame:
        layers["flame"] = dict(files["flame"], low=files["flame_low"], m_per_px=round(mf, 5), low_m_per_px=round(mf / LOW_SCALE, 5),
                               size_m=[round(fw * mf, 3), round(fh * mf, 3)], anchor=[0.5, 1.0],
                               blend="straight alpha, sRGB colour, linear alpha: normal blending (SRC_ALPHA, ONE_MINUS_SRC_ALPHA) or additive (SRC_ALPHA, ONE)", bytes=sizes["flame"], low_bytes=sizes["flame_low"])
    layers["smoke"] = dict(files["smoke"], low=files["smoke_low"], m_per_px=round(ms, 5), low_m_per_px=round(ms / LOW_SCALE, 5),
                           size_m=[round(sw * ms, 3), round(sh * ms, 3)], anchor=[0.5, 1.0], blend="normal, straight alpha, grey RGB", bytes=sizes["smoke"],
                           low_bytes=sizes["smoke_low"])
    layers["heat"] = dict(files["heat"], m_per_px=round(ms, 5), size_m=[round(hw * ms, 3), round(hh * ms, 3)], anchor=[0.5, 1.0],
                          encoding="8-bit; heat = (value/255)^(1/0.8); 1.0 = about 2000 K, 0 = ambient", bytes=sizes["heat"])
    desc = []
    fi = si = hi = 0
    for c in clips:
        nf, ns, nh = len(c["flame"]), len(c["smoke"]), len(c["heat"])
        d = dict(name=c["name"], stage=c["stage"], variant=c["variant"], loop=c["loop"], fps=c["fps"], duration_s=round(nf / c["fps"], 3),
                 flame=dict(first=fi, count=nf, fps=c["fps"]), smoke=dict(first=si, count=ns, fps=c["fps"] / 2),
                 heat=dict(first=hi, count=nh, fps=c["fps"] / 4))
        if not has_flame:
            d.pop("flame")
        desc.append(d)
        fi += nf
        si += ns
        hi += nh
    lc0 = [c for c in clips if c["stage"] in ("loop", "shot", "fireball") and c["variant"] == 0][0]
    lum = np.array(lc0["lum"])
    mean_lum = float(lum.mean()) + 1e-9
    pw = lum / mean_lum
    pw_s = np.convolve(np.concatenate([pw[-2:], pw, pw[:2]]), [0.25, 0.5, 0.25], mode="same")[2:-2]
    pw_s = pw_s / pw_s.mean()
    mt = float(np.average(lc0["mth"], weights=np.maximum(lum, 1e-6)))
    lc = planck_rgb(950.0 + 1900.0 * mt)
    lc = lc / lc.max() * np.array(rend.tint)
    light = dict(color=[round(float(x), 3) for x in lc], mean_theta=round(mt, 3), mean_kelvin_visible=round(950 + 1900 * mt), intensity_rel=round(mean_lum, 2),
                 range_m=round(max(fh * mf, 1.0) * 3.0, 2), flicker=[round(float(x), 3) for x in pw_s],
                 stage_energy={c["name"]: [round(float(x) / mean_lum, 3) for x in c["lum"]] for c in clips if c["stage"] not in ("loop",)},
                 color_by_heat=[[h] + [round(float(x), 3) for x in (planck_rgb(950.0 + 1900.0 * h) / planck_rgb(950.0 + 1900.0 * h).max())] for h in (0.35, 0.5, 0.65, 0.8, 1.0)])
    # heat-haze descriptor for the game's DIST sources
    flame_h = layers["flame"]["size_m"][1] if has_flame else layers["smoke"]["size_m"][1] * 0.4
    flame_w = layers["flame"]["size_m"][0] if has_flame else layers["smoke"]["size_m"][0] * 0.4
    em_spread = max(abs(v[0]) + v[2] for v in S.PRESETS[name]["vents"])
    shape = meta.get("haze_shape", "default")
    dom = PR.domain_m(name)
    if shape == "tall":
        hz_h, hz_r = min(2.4 * flame_h, dom[2] * 0.9), max(0.45 * flame_w, em_spread * 1.3)
    elif shape == "wide":
        hz_h, hz_r = 0.9 * flame_h, (dom[0] * 0.5 if per else max(0.6 * flame_w, em_spread * 1.6))
    else:
        hz_h, hz_r = 1.6 * flame_h, max(0.3 * flame_w, em_spread * 1.4)
    wr = float(np.mean(lc0.get("wr", [0.0])))
    haze = dict(strength=meta.get("haze", 0.5), radius_m=round(float(hz_r), 2), height_m=round(float(hz_h), 2), rise_speed_mps=round(max(wr, 0.3), 2), shape=shape,
                note="attach a DIST.haze source: strength, radius_m, height_m (haze volume), drift upward at rise_speed_mps; scale strength by the stage energy")
    lf = lc0["flame"]
    dd = lambda a, b: float(np.abs(a - b).mean() * 255)
    adj = float(np.mean([dd(lf[i], lf[i + 1]) for i in range(len(lf) - 1)]))
    seam = dd(lf[-1], lf[0])
    anchors = {}
    if free:   # the burning head: anchor each layer's frame at the head so the game can orient/stretch about it
        v0 = S.PRESETS[name]["vents"][0]
        nx_, ny_, nz_ = sim.grid
        for lay, up, (x0_, y0_, w_, h_) in (("flame", UP_F, (fx0, fy0, fw, fh)), ("smoke", UP_S, (sx0, sy0, sw, sh)), ("heat", UP_S, (hx0, hy0, hw, hh))):
            hx_ = (v0[0] / dx + nx_ / 2) * up
            hy_ = nz_ * up - (v0[4] / dx) * up
            anchors[lay] = [round((hx_ - x0_) / w_, 4), round((hy_ - y0_) / h_, 4)]
        for lay in layers:
            layers[lay]["anchor"] = anchors[lay]
        layers[next(iter(layers))]["orientation"] = "frame x axis = flame tail direction (tail to +x). Rotate the quad so +x points opposite to the object's velocity; anchor = burning head."
    info = dict(title=meta["title"], kind=meta["kind"], size_note=meta["size_note"], domain_m=PR.domain_m(name), has_flame=has_flame, tile=bool(per),
                variants=NVAR, layers=layers, clips=desc,
                emitter=dict(radius_m=round(float(max(v[2] for v in S.PRESETS[name]["vents"])), 3),
                             spread_m=round(float(max(abs(v[0]) + v[2] for v in S.PRESETS[name]["vents"])), 3)),
                light=light, haze=haze, seam=dict(mean_adjacent_diff=round(adj, 3), loop_point_diff=round(seam, 3)),
                sim=dict(seed=seed, dx_m=dx, grid=list(sim.grid), stoich_s=S.PRESETS[name]["s"], periodic=bool(per)))
    log(f"[{name}] flame {sizes.get('flame', 0) / 1024:.0f} KB (low {sizes.get('flame_low', 0) / 1024:.0f}), smoke {sizes['smoke'] / 1024:.0f} (low {sizes['smoke_low'] / 1024:.0f}), "
        f"heat {sizes['heat'] / 1024:.0f}; flame {fw}x{fh}px smoke {sw}x{sh}px; seam {seam:.2f} vs adj {adj:.2f}")
    return info


def merge_json(outdir, name, info):
    ap = os.path.join(outdir, "fire_atlas.json")
    data = {"version": 2, "note": "Baked by tools/fire/bake.py (reduced combustion model; see MODEL-NOTES-FIRE-BAKED.md)", "presets": {}}
    if os.path.exists(ap):
        try:
            old = json.load(open(ap))
            if old.get("version") == 2:
                data = old
        except Exception:
            pass
    data["version"] = 2
    data["presets"][name] = info
    base = data["presets"].get("campfire", {}).get("light", {}).get("intensity_rel")
    if base:
        for p in data["presets"].values():
            p["light"]["intensity_vs_campfire"] = round(p["light"]["intensity_rel"] / base, 2)
    with open(ap, "w") as fh_:
        json.dump(data, fh_, separators=(",", ":"))


ORDER = ["campfire", "pool", "vehicle", "building", "tree_crown", "tree_trunk", "grass", "front_lead", "front_body", "front_trail"]


def bake(name, seed=1, outdir=None, force=False):
    outdir = outdir or os.path.join(ROOT, "assets", "fire")
    os.makedirs(outdir, exist_ok=True)
    ap = os.path.join(outdir, "fire_atlas.json")
    if not force and os.path.exists(ap):
        have = json.load(open(ap)).get("presets", {})
        if name in have and have[name].get("version_tag") == 2:
            log(f"[{name}] already baked, skipping (use --force)")
            return
    kind = PR.META[name]["kind"]
    t0 = time.time()
    run = {"life": run_life, "tile": run_tile, "carried": run_tile, "shot": run_shot, "blast": run_blast}[kind]
    sim, rend, clips = run(name, 0, seed)
    log(f"[{name}] sim+render {time.time() - t0:.0f}s")
    info = write_type(name, sim, rend, clips, outdir, seed)
    info["version_tag"] = 2
    merge_json(outdir, name, info)
    log(f"[{name}] done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", help="a fire type name, a comma list, or 'all'")
    ap.add_argument("--seed", type=int, default=1, help="render-noise seed")
    ap.add_argument("--out", default=None)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    names = (ORDER + [t for t in PR.TYPES if t not in ORDER]) if a.preset == "all" else a.preset.split(",")
    for nm in names:
        bake(nm, a.seed, a.out, a.force)
    print("done", flush=True)
