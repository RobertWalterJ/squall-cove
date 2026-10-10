"""
bake.py - run the atmos solver for a steam / mist / fog preset and bake flipbook atlases with lifecycle clips.

    python tools/atmos/bake.py steam_pipe                  # one preset
    python tools/atmos/bake.py steam                       # a family (steam | mist | fog) or a comma list or 'all'
    python tools/atmos/bake.py fog_ground --quick --out _atmos_tmp

Writes to assets/atmos/ (or --out):
    <preset>.webp  <preset>_low.webp          main layer: grey (sRGB) + straight alpha, normal blending
    <preset>_scatter.webp (+ _low)            forward-scatter highlight, grey, half-size, add this when the sun is behind
    <preset>_heat.webp                        steam only: temperature layer for thermal vision, quarter-size
and merges the preset into atmos_atlas.json (frame size, metres per pixel, anchors, clips, wind, lighting, sensors, haze, tile data).

Pipelines: 'life'  start -> sustained loop variants (cross-faded seamless) -> fade / settle
           'shot'  one-shot variants (splashes)
           'strip' tileable fog strip: form, drift loops, linger loops, thin out, fall (time-lapse clips at low fps, crossfade them)
           'blobs' soft fog billboards, loops
"""
import argparse, copy, json, os, sys, time
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import fluid as FL      # noqa: E402
import render as R      # noqa: E402
import presets as PR    # noqa: E402

M_OVER = 6
NVAR = 2
QUICK = False
WEBP = dict(steam=(42, 55), mist=(42, 55), fog=(40, 50))
LOW_SCALE = 0.5
SC_SCALE, SC_LOW_SCALE, HEAT_SCALE = 0.5, 0.25, 0.25


def log(msg):
    print(msg, flush=True)


ss = lambda a, b, x: float(FL.smoothstep(a, b, x))


# ------------------------------------------------------------------------------------------------------
class Renderer:
    def __init__(self, name, air, seed=1):
        self.name = name
        self.p = PR.PRESETS[name]
        self.k = k = self.p["look"]
        self.air = air
        ux, uz = k["up"]
        self.ux, self.uz = ux, uz
        nx, ny, nz = air.grid
        self.H, self.D, self.W = nz * uz, ny, nx * ux
        self.per = air.px
        w3 = R.window3d(self.W, self.D, self.H, self.per, top=k.get("top", (0.55, 0.98)), bottom=k.get("bottom"), xw=k.get("xw", k.get("win_x", 0.2)), yw=k.get("yw", 0.25))
        self.win = np.transpose(w3, (2, 1, 0))[::-1].copy()
        nsc = k.get("noise", ((7, 3.5, 6), (3.5, 1.8, 3), (1.8, 0.9, 1.5)))
        self.mode = k.get("noise_mode", "scroll")
        self.nv = []
        for v in range(3):
            n1 = R.make_noise((self.H, self.D, self.W), seed + 11 + 97 * v, nsc, per_x=self.per)
            if self.mode == "boil":
                n2 = R.make_noise((self.H, self.D, self.W), seed + 53 + 97 * v, nsc, per_x=self.per)
                self.nv.append((n1, n2))
            else:
                self.nv.append((n1,))
        mk = lambda s: R.make_noise((self.H, 1, self.W), s, ((6, 1, 6), (3, 1, 3), (1.5, 1, 1.5)), per_x=self.per)[:, 0, :]
        self.disp = [(mk(seed + 31 + 17 * v), mk(seed + 71 + 17 * v)) for v in range(3)]
        zm = (self.H - 1 - np.arange(self.H) + 0.5) * (air.dx / uz)
        gap = k.get("gap", 0.0)
        z0 = air.vents[0].get("z0", 0.0) if air.vents else 0.0
        self.gapf = (R.smoothstep(z0 + gap, z0 + 2 * gap, zm) if gap > 0 else np.ones(self.H))[:, None, None].astype(np.float32)
        self.dy, self.dz = air.dx, air.dx / uz
        self.dxr = air.dx / ux
        self.is_spray = air.spray is not None
        self.fps_ref = 24.0

    def noise_at(self, var, phase=None, shift=0):
        if self.mode == "boil":
            n1, n2 = self.nv[var]
            ph = 2 * np.pi * (phase or 0.0)
            return np.cos(ph) * n1 + np.sin(ph) * n2
        n = self.nv[var][0]
        return np.roll(n, int(shift), axis=0)

    def frame(self, var, phase=0.0, shift=0, roll_px=0, need_heat=False, trail_span=1 / 24):
        air, k = self.air, self.k
        if self.is_spray:
            V = air.spray.sigma(air, self.ux, blur=k.get("blur", (1.2, 0.6)), trail=k.get("trail", 1), span=trail_span)
        else:
            V = R.upvol(air.sigma_cloud(k["reff"]), np.ones(1, np.float32), self.ux, self.uz, self.per)
        V = V * self.win * self.gapf
        n = self.noise_at(var, phase, shift)
        V = R.shape_density(V, n, k)
        o = R.project(V, self.dy, self.dz, k)
        dn = self.disp[var]
        wa = k.get("warp", 1.0)
        for key in ("alpha", "lum", "scatter"):
            o[key] = R.warp2d(o[key], dn, wa, self.per)
        sf = k.get("soften", 0.9)
        if sf > 0:
            for key in ("alpha", "lum", "scatter"):
                o[key] = ndi_gauss(o[key], sf, self.per)
        if roll_px:
            for key in ("alpha", "lum", "scatter"):
                o[key] = np.roll(o[key], int(roll_px), axis=1)
        if need_heat:
            te = air.th - air.th_amb[None, None, :]
            hv = R.upvol(np.clip(te, 0, None) / self.p["heat"]["th_ref"], np.ones(1, np.float32), self.ux, self.uz, self.per)
            hv = hv * self.win
            h = hv.max(axis=1)
            o["heat"] = np.clip(R.warp2d(h, dn, wa, self.per), 0, 1.2).astype(np.float32)
        o.pop("tau", None)
        return o


def ndi_gauss(a, s, per):
    from scipy import ndimage as ndi
    return ndi.gaussian_filter(a, s, mode=("nearest", "wrap" if per else "nearest"))


def new_clip(name, stage, variant, fps, loop, **kw):
    return dict(name=name, stage=stage, variant=variant, fps=fps, loop=loop, frames=[], stats=[], **kw)


def record(air, rend, clip, n, fps, var, loop_phase=False, nloop=None, frame_s=None, need_heat=False, u_ref=0.0, log_every=8, t_start=None):
    """advance the sim and render n frames. frame_s overrides the sim time per frame (time-lapse clips)."""
    dt = air.dt
    ft = frame_s if frame_s else 1.0 / fps
    spf = max(1, int(round(ft / dt)))
    k = rend.k
    sc = k.get("scroll", 1)
    P_ = rend.H
    Tloop = (nloop or 32) / fps
    for i in range(n):
        for _ in range(spf):
            air.step()
        if loop_phase:
            shift = -(i * sc * P_) // (nloop or 32)
            phase = (i % (nloop or 32)) / float(nloop or 32)
        else:
            tt = air.t if t_start is None else air.t - t_start
            shift = -int(tt * sc * P_ / Tloop)
            phase = (tt / Tloop) % 1.0
        roll = -int(round(u_ref * air.t / rend.dxr)) if u_ref else 0
        o = rend.frame(var, phase=phase, shift=shift, roll_px=roll, need_heat=need_heat, trail_span=ft)
        clip["frames"].append(o)
        if air.vents or True:
            te = air.th - air.th_amb[None, None, :]
            hot = te > 4.0
            clip["stats"].append(dict(w_hot=float(air.w[hot].mean()) if hot.any() else 0.0,
                                      hot_h=float(air.zc[np.where(hot.any((0, 1)))[0].max()]) if hot.any() else 0.0,
                                      hot_r=float(np.sqrt(hot.any(2).sum() * air.dx ** 2 / np.pi)) if hot.any() else 0.0,
                                      lw=float(air.ql.sum() * FL.RHO_A * air.dx ** 3)))
        if i % log_every == 0:
            log(f"   {clip['name']} {i}/{n}  t={air.t:.1f}s  frame {o['alpha'].shape[1]}x{o['alpha'].shape[0]}  amax {o['alpha'].max():.2f}")


def crossfade(frames, n, m):
    out = []
    for i in range(n):
        if i < m:
            w = i / m
            w = w * w * (3 - 2 * w)
            out.append({k: (1 - w) * frames[n + i][k] + w * frames[i][k] for k in frames[i]})
        else:
            out.append(frames[i])
    return out


def make_loop(raw, var, n, m, mirror=False, name=None, stage="loop"):
    c = new_clip(name or f"loop_{'abc'[var]}", stage, var, raw["fps"], True)
    c["frames"] = crossfade(raw["frames"], n, m)
    c["stats"] = raw["stats"][:n]
    if mirror:
        c["frames"] = [{k: f[:, ::-1].copy() for k, f in fr.items()} for fr in c["frames"]]
    return c


# ------------------------------------------------------------------------------------------------------
def make_air(name, seed, supply=None, sched=None, overrides=None):
    p = PR.PRESETS[name]
    P = dict(p["sim"])
    if overrides:
        P.update(overrides)
    if sched:
        P["sched"] = sched
    air = FL.Air(P, seed, supply)
    if "spray" in p:
        sp = p["spray"]
        air.spray = FL.Spray(copy.deepcopy(sp["emitters"]), seed, sp.get("nmax", 60000), sp.get("rh", 0.7), sp.get("rmin", 6e-6), sp.get("eddy", 0.0), 0.0, sp.get("coupling", 1.0))
    return air


def run_life(name, seed=0):
    p = PR.PRESETS[name]
    c = p["clip"]
    nloop = c["n_loop"] if not QUICK else 12
    mo = M_OVER if not QUICK else 4
    nvar = NVAR if not QUICK else 2
    st = dict(fade=None)
    pu = c.get("punch")

    def supply(t):
        up = ss(0.0, c["ramp"], t)
        if pu:
            up *= 1.0 + pu[1] * float(np.exp(-t / pu[0])) * 1.0 - 0.0
        if st["fade"] is not None:
            up *= 1.0 - ss(st["fade"], st["fade"] + c["fade_s"], t)
        return up

    air = make_air(name, seed, supply)
    rend = Renderer(name, air, seed + 1)
    heat = p["family"] == "steam"
    clips = []
    t0 = time.time()
    cl = new_clip("start", "start", 0, c["stage_fps"], False)
    record(air, rend, cl, c["n_start"] if not QUICK else 6, c["stage_fps"], 0, need_heat=heat, nloop=c["n_loop"])
    clips.append(cl)
    while air.t < c["warm"]:
        air.step()
    log(f"[{name}] developed at t={air.t:.1f}s ({time.time() - t0:.0f}s)")
    loops = []
    for v in range(nvar):
        raw = new_clip("raw", "loop", v, c["fps"], True)
        record(air, rend, raw, nloop + mo, c["fps"], v, loop_phase=True, nloop=nloop, need_heat=heat)
        loops.append(make_loop(raw, v, nloop, mo, mirror=False))
    st["fade"] = air.t
    cl = new_clip("settle" if p["family"] == "mist" else "fade", "fade", 0, c["stage_fps"], False)
    record(air, rend, cl, c["n_fade"] if not QUICK else 6, c["stage_fps"], 0, need_heat=heat, nloop=c["n_loop"])
    clips.append(cl)
    order = {"start": 0, "loop": 1, "fade": 2}
    allc = loops + clips
    allc.sort(key=lambda x: (order[x["stage"]], x["variant"]))
    return air, rend, allc


def run_shot(name, seed=0):
    p = PR.PRESETS[name]
    c = p["clip"]
    n = c["n_shot"] if not QUICK else 12
    clips = []
    rend = None
    for v in range(c["nvar"] if not QUICK else 2):
        air = make_air(name, seed + v + 1)
        rend = Renderer(name, air, seed + 1) if rend is None else rend
        rend.air = air
        cl = new_clip(f"splash_{'abc'[v]}", "shot", v, c["fps"], False)
        record(air, rend, cl, n, c["fps"], v, nloop=n)
        clips.append(cl)
    return air, rend, clips


def stage_sched(state):
    return lambda t: state["fn"](t)


def run_strip(name, seed=0):
    p = PR.PRESETS[name]
    P0 = p["sim"]
    stg = p["stages"]
    c = p["clip"]
    k = p["look"]
    dt = P0["dt"]
    fr_s = c.get("frame_s", None)
    state = dict(fn=lambda t: {})
    churn0 = P0.get("churn", 0.0)
    tl = {}

    def fn_form(t):
        f = stg["form"]
        r = ss(0.0, 0.25, t / f["t"])
        return dict(cool=f["cool"] * r * (1 - ss(0.75, 1.0, t / f["t"])) + f["hold"] * ss(0.75, 1.0, t / f["t"]), moist=f.get("moist", 0) * r, churn=churn0)

    def hold(churn_m, t_extra=None):
        f = stg["form"]
        return lambda t: dict(cool=f["hold"], moist=f.get("moist", 0) * 0.5, churn=churn0 * churn_m)

    air = make_air(name, seed, sched=stage_sched(state))
    rend = Renderer(name, air, seed + 1)
    nloop = c["n_loop"] if not QUICK else 12
    mo = M_OVER if not QUICK else 4
    nst = c["n_stage"] if not QUICK else 4
    nli = c["n_linger"] if not QUICK else 6
    u_ref = k.get("u_ref", 0.0)
    clips = []
    t0 = time.time()

    def steps_for(T):
        return int(round(T / dt))

    # ---- form: cooling ramps, fog thickens (time-lapse: the whole stage is spread over nst frames)
    state["fn"] = fn_form
    T = stg["form"]["t"]
    spf_form = max(1, steps_for(T / nst))
    cl = new_clip("form", "form", 0, c["stage_fps"], False, sim_s_per_frame=round(spf_form * dt, 3), interpolate=True)
    for i in range(nst):
        for _ in range(spf_form):
            air.step()
        cl["frames"].append(rend.frame(0, phase=(i / 12.0) % 1.0, roll_px=-int(round(u_ref * air.t / rend.dxr)) if u_ref else 0))
        cl["stats"].append(dict(lw=float(air.ql.sum())))
    clips.append(cl)
    log(f"[{name}] form done t={air.t:.0f}s ({time.time() - t0:.0f}s)")
    # ---- drift: developed fog, a couple of seamless loop windows
    state["fn"] = hold(1.0)
    for _ in range(steps_for(stg["drift"]["t"])):
        air.step()
    fs = fr_s or max(dt, 0.5)
    loopsd = []
    for v in range(2):
        raw = new_clip("raw", "loop", v, c["fps"], True)
        record(air, rend, raw, nloop + mo, c["fps"], v, loop_phase=True, nloop=nloop, frame_s=fs, u_ref=u_ref)
        lp = make_loop(raw, v, nloop, mo, mirror=False, name=f"drift_{'ab'[v]}", stage="drift")
        lp["sim_s_per_frame"] = fs
        loopsd.append(lp)
    log(f"[{name}] drift done ({time.time() - t0:.0f}s)")
    # ---- linger: churn damped, nearly static
    state["fn"] = hold(stg["linger"]["churn"])
    for _ in range(steps_for(20.0)):
        air.step()
    raw = new_clip("raw", "loop", 0, c["linger_fps"], True)
    record(air, rend, raw, nli + mo // 2, c["linger_fps"], 2, loop_phase=True, nloop=nli, frame_s=fs * 1.5, u_ref=u_ref * 0.3)
    lg = make_loop(raw, 2, nli, mo // 2, name="linger", stage="linger")
    lg["sim_s_per_frame"] = fs * 1.5
    # ---- thin out / burn off: warming evaporates the fog
    T = stg["thin"]["t"]
    state["fn"] = lambda t, t0_=air.t, f_=stg["thin"], h_=stg["form"]["hold"]: dict(cool=h_ - (h_ + f_["heat"]) * ss(0.0, 0.3, (t - t0_) / f_["t"]), churn=churn0 * 0.7)
    spf = max(1, steps_for(T / nst))
    th_ = new_clip("thin", "thin", 0, c["stage_fps"], False, sim_s_per_frame=round(spf * dt, 3), interpolate=True)
    for i in range(nst):
        for _ in range(spf):
            air.step()
        th_["frames"].append(rend.frame(0, phase=(i / 12.0 + 0.3) % 1.0, roll_px=-int(round(u_ref * air.t / rend.dxr)) if u_ref else 0))
        th_["stats"].append(dict(lw=float(air.ql.sum())))
    log(f"[{name}] thin done ({time.time() - t0:.0f}s)")
    # ---- fall: a deeper fog sinks and flattens (separate run)
    fa = stg["fall"]
    st2 = dict(fn=lambda t: {})
    air2 = make_air(name, seed + 5, sched=stage_sched(st2))
    rend.air = air2
    pre = fa["pre"]
    st2["fn"] = lambda t, pre=pre: dict(cool=pre["cool"] * ss(0.0, 0.25, t / pre["t"]), churn=churn0, force_h=fa["force_h"])
    for _ in range(steps_for(pre["t"])):
        air2.step()
    tf0 = air2.t
    st2["fn"] = lambda t: dict(cool=-0.002, churn=churn0 * 0.6, vt=fa["vt"], force_h=fa["force_h"])
    spf = max(1, steps_for(fa["t"] / nst))
    fl = new_clip("fall", "fall", 0, c["stage_fps"], False, sim_s_per_frame=round(spf * dt, 3), interpolate=True)
    for i in range(nst):
        for _ in range(spf):
            air2.step()
        fl["frames"].append(rend.frame(0, phase=(i / 12.0 + 0.6) % 1.0, roll_px=-int(round(u_ref * air2.t / rend.dxr)) if u_ref else 0))
        fl["stats"].append(dict(lw=float(air2.ql.sum())))
    log(f"[{name}] fall done ({time.time() - t0:.0f}s)")
    order = {"form": 0, "drift": 1, "linger": 2, "thin": 3, "fall": 4}
    allc = [clips[0]] + loopsd + [lg, th_, fl]
    return air, rend, allc


def run_blobs(name, seed=0):
    p = PR.PRESETS[name]
    b = p["blobs"]
    clips = []
    nv = b["nvar"] if not QUICK else 1
    n = b["n"] if not QUICK else 6
    mo = 4 if not QUICK else 2
    air = rend = None
    for tname, tp in b["types"].items():
        for v in range(nv):
            air = make_air(name, seed + 31 * v + len(tname))
            if rend is None:
                rend = Renderer(name, air, seed + 1)
            rend.air = air
            nx, ny, nz = air.grid
            rr = air.rng
            # an irregular ellipsoid of saturated fog
            r = np.array(tp["r"])
            sh = ndi_noise(air, rr)
            d = np.sqrt((air.X / (r[0] * (1 + 0.25 * sh))) ** 2 + (air.Y / (r[1] * (1 + 0.25 * sh))) ** 2 + ((air.Zc - tp["z"]) / (r[2] * (1 + 0.2 * sh))) ** 2)
            m = np.clip(1.25 - d, 0, 1) ** 1.3
            qs = FL.qsat(air.T0 + air.th)
            air.qe += (qs - air.qb[None, None, :]) * m
            air.ql += tp["amp"] * m
            for _ in range(int(8 / air.dt)):
                air.step()
            raw = new_clip("raw", "loop", v, b["fps"], True)
            fsx = 0.8
            record(air, rend, raw, n + mo, b["fps"], v, loop_phase=True, nloop=n, frame_s=fsx)
            lp = make_loop(raw, v, n, mo, mirror=False, name=f"{tname}_{'ab'[v]}", stage="blob")
            lp["blob_type"] = tname
            lp["sim_s_per_frame"] = fsx
            clips.append(lp)
            log(f"[{name}] blob {tname} {v} done")
    return air, rend, clips


def ndi_noise(air, rng):
    from scipy import ndimage as ndi
    r = ndi.gaussian_filter(rng.standard_normal(air.grid), 3.0)
    return (r / (r.std() + 1e-6)).astype(np.float32)


# ------------------------------------------------------------------------------------------------------
def encode(arr, path, q, aq, rgba):
    if rgba:
        Image.fromarray(arr, "RGBA").save(path, "WEBP", quality=q, method=6, alpha_quality=aq, exact=False)
    else:
        g = arr[..., 0] if arr.ndim == 3 else arr
        Image.fromarray(g, "L").convert("RGB").save(path, "WEBP", quality=q, method=6)
    return os.path.getsize(path)


def write_preset(name, air, rend, clips, outdir, seed):
    p = PR.PRESETS[name]
    k = p["look"]
    fam = p["family"]
    per = air.px
    strip = p["kind"] == "strip"
    allf = [f for c in clips for f in c["frames"]]
    n = len(allf)
    H, W = allf[0]["alpha"].shape
    if strip:
        x0, x1, y0, y1 = 0, W, 0, H
    else:
        x0, x1, y0, y1 = R.bbox([f["alpha"] for f in allf], 0.006, 4, periodic=False)
    fw, fh = x1 - x0, y1 - y0
    dith = None
    rng = np.random.default_rng(7)
    q, aq = WEBP[fam]
    if k.get("quality"):
        q, aq = k["quality"]
    main, scat, heat = [], [], []
    for f in allf:
        a = f["alpha"][y0:y1, x0:x1]
        l = f["lum"][y0:y1, x0:x1]
        d = (rng.random(a.shape) - 0.5) * 1.1 if k.get("dither", True) else None
        a8 = R.to8(a, d)
        l8 = R.to8(R.srgb(l), None if d is None else (rng.random(a.shape) - 0.5))
        l8 = np.where(a8 < 3, 0, l8).astype(np.uint8)
        main.append(np.stack([l8, l8, l8, a8], -1))
        scat.append(R.to8(f["scatter"][y0:y1, x0:x1])[..., None])
        if "heat" in f:
            heat.append(R.to8(np.round(np.power(np.clip(f["heat"][y0:y1, x0:x1], 0, 1), 0.8) * 32) / 32)[..., None])
    cols = R.atlas_cols(n, fw, fh)
    files, sizes = {}, {}
    tag = {"": 1.0, "_low": LOW_SCALE}
    for t, sc in tag.items():
        fr = main if sc == 1 else [R.resize_u8(m, sc) for m in main]
        at, rows = R.make_atlas(fr, cols)
        at[at[..., 3] < 3] = 0
        pth = os.path.join(outdir, f"{name}{t}.webp")
        sizes["main" + t] = encode(at, pth, q, aq, True)
        files["main" + t] = dict(file=os.path.basename(pth), frame_px=[fr[0].shape[1], fr[0].shape[0]], cols=cols, rows=rows)
    for t, sc in (("", SC_SCALE), ("_low", SC_LOW_SCALE)):
        fr = [R.resize_u8(m, sc) for m in scat]
        at, rows = R.make_atlas(fr, cols)
        pth = os.path.join(outdir, f"{name}_scatter{t}.webp")
        sizes["scatter" + t] = encode(at, pth, 35, 0, False)
        files["scatter" + t] = dict(file=os.path.basename(pth), frame_px=[fr[0].shape[1], fr[0].shape[0]], cols=cols, rows=rows)
    if heat:
        fr = [R.resize_u8(m, HEAT_SCALE) for m in heat]
        at, rows = R.make_atlas(fr, cols)
        pth = os.path.join(outdir, f"{name}_heat.webp")
        sizes["heat"] = encode(at, pth, 40, 0, False)
        files["heat"] = dict(file=os.path.basename(pth), frame_px=[fr[0].shape[1], fr[0].shape[0]], cols=cols, rows=rows)
    ux, uz = k["up"]
    mpx_x, mpx_z = air.dx / ux, air.dx / uz
    # anchors: emitter position inside the cropped frame (u, v from top-left, 0..1)
    ex, ey, ez = 0.0, 0.0, 0.0
    if air.vents:
        ex, ez = air.vents[0]["x"], air.vents[0].get("z0", 0.0)
    elif air.spray and air.spray.em:
        ex, ez = air.spray.em[0]["pos"][0], air.spray.em[0]["pos"][2]
    px_x = (ex / mpx_x + W / 2) - x0
    px_y = (H - ez / mpx_z) - y0
    anchor = [round(float(px_x / fw), 4), round(float(px_y / fh), 4)]
    if strip:
        anchor = [0.5, 1.0]
    layer = lambda key, extra=None: None
    layers = {}
    layers["main"] = dict(files["main"], low=files["main_low"], m_per_px=[round(mpx_x, 5), round(mpx_z, 5)], low_m_per_px=[round(mpx_x / LOW_SCALE, 5), round(mpx_z / LOW_SCALE, 5)],
                          size_m=[round(fw * mpx_x, 3), round(fh * mpx_z, 3)], anchor=anchor, bytes=sizes["main"], low_bytes=sizes["main_low"],
                          encoding="WebP lossy RGBA; rgb = grey, sRGB-encoded (use an sRGB texture); alpha = straight (non-premultiplied) coverage",
                          blend="normal: (SRC_ALPHA, ONE_MINUS_SRC_ALPHA); or premultiply on load and use (ONE, ONE_MINUS_SRC_ALPHA)")
    layers["scatter"] = dict(files["scatter"], low=files["scatter_low"], scale=SC_SCALE, bytes=sizes["scatter"], low_bytes=sizes["scatter_low"],
                             encoding="grey WebP, same frame order as main at 0.5x size (low: 0.25x); value = forward-scatter strength 0..1",
                             blend="additive on top of main: out += sunColour * scatter * sunBacklight * gain; mask with the main alpha so it never extends past the sprite")
    if heat:
        layers["heat"] = dict(files["heat"], scale=HEAT_SCALE, bytes=sizes["heat"],
                              encoding="grey WebP at 0.25x; heat = (value/255)^(1/0.8); 1.0 = th_ref kelvin above ambient", th_ref_k=p["heat"]["th_ref"])
    # clips
    desc, fi = [], 0
    for c in clips:
        nf = len(c["frames"])
        d = dict(name=c["name"], stage=c["stage"], variant=c["variant"], loop=c["loop"], fps=c["fps"], first=fi, count=nf, duration_s=round(nf / c["fps"], 3))
        for extra in ("sim_s_per_frame", "interpolate", "blob_type"):
            if extra in c:
                d[extra] = c[extra]
        desc.append(d)
        fi += nf
    # seam statistics on the first loop clip
    lc = ([c for c in clips if c["loop"]] or clips)[0]
    la = [f["alpha"] for f in lc["frames"]]
    dd = lambda a, b: float(np.abs(a - b).mean() * 255)
    adj = float(np.mean([dd(la[i], la[i + 1]) for i in range(len(la) - 1)]))
    seam = dd(la[-1], la[0])
    tile = None
    if strip:
        e = [dd(f["alpha"][:, 0], f["alpha"][:, -1]) for f in lc["frames"]]
        a0 = [dd(f["alpha"][:, 0], f["alpha"][:, 1]) for f in lc["frames"]]
        tile = dict(tileable_x=True, wrap_edge_diff=round(float(np.mean(e)), 3), neighbour_column_diff=round(float(np.mean(a0)), 3), frame_w_m=round(W * mpx_x, 2),
                    bottom_fade_frac=k.get("bottom"), note="left and right edges are neighbours in the simulation (periodic), so strips tile seamlessly; the bottom edge sits on the ground and fades to 0")
    # physical stats for haze + wind
    ds = [s for c in clips if (c["loop"] or p["kind"] == "shot") for s in c["stats"]]
    w_hot = float(np.mean([s["w_hot"] for s in ds])) if ds else 0.0
    hot_h = float(np.percentile([s["hot_h"] for s in ds], 75)) if ds else 0.0
    hot_r = float(np.mean([s["hot_r"] for s in ds])) if ds else 0.0
    info = dict(title=p["title"], family=fam, kind=p["kind"], size_note=p["size_note"], variants=len([c for c in clips if c["loop"] or c["stage"] in ("shot",)]),
                domain_m=[round(air.nx * air.dx, 3), round(air.ny * air.dx, 3), round(air.nz * air.dx, 3)], layers=layers, clips=desc, anchor_note="anchor = [u, v] of the emitter / ground contact inside a frame, from the top-left corner",
                sim=dict(seed=seed, dx_m=air.dx, dt_s=air.dt, grid=list(air.grid), periodic=bool(per), T0_K=air.T0, ambient_rh=p["sim"].get("rh") if not callable(p["sim"].get("rh")) else "profile"),
                seam=dict(mean_adjacent_diff=round(adj, 3), loop_point_diff=round(seam, 3)), tile=tile, game=copy.deepcopy(p["game"]))
    info["game"]["wind"]["note_base"] = info["game"]["wind"].get("note")
    info["lighting"] = info["game"].pop("light")
    fa = fam
    if fam == "steam":
        info["sensors"] = dict(thermal=dict(mode="emit", layer="heat", note="steam is bright in thermal view: draw the heat layer through a white-hot palette, scaled by the alpha; the visible fog is irrelevant to the sensor", brightness=1.0),
                               night_vision=dict(mode="soft", note="steam is a soft grey cloud; add the scatter layer at 0.5 where IR illuminators hit it"))
        haze_shape = p["heat"].get("shape", "default")
        info["haze"] = dict(strength=p["heat"]["strength"], radius_m=round(max(hot_r, air.vents[0]["rx"] * 1.3), 2), height_m=round(max(hot_h, 0.5), 2), rise_speed_mps=round(max(w_hot, 0.3), 2), shape=haze_shape,
                            clear_gap_m=round(k.get("gap", 0) * 2 + air.vents[0].get("z0", 0), 3),
                            note="attach a DIST.haze source above the vent: strength, radius_m and height_m (the invisible hot gas is hotter than the visible plume), drifting up at rise_speed_mps; fade with the stage (start ramps in, fade ramps out)")
    elif fam == "mist" and p["kind"] != "strip":
        info["sensors"] = dict(thermal=dict(mode="cold", alpha_gain=0.06, note="droplets are at ambient temperature: nearly invisible in thermal view; may show as a faint cool smudge (alpha x 0.06, dark)"),
                               night_vision=dict(mode="scatter", note="droplets scatter IR illuminator light: draw main at 0.6 plus the scatter layer at 1.0, slightly bloomed"))
    else:
        info["sensors"] = dict(thermal=dict(mode="faint_cool", alpha_gain=0.10, note="fog is faint and cool in thermal view: alpha x 0.10 in the cold end of the palette; it slightly blurs what is behind it"),
                               night_vision=dict(mode="wash_out", note="fog scatters the illuminator back: add scatter x 0.8 plus alpha x 0.35 as a uniform veil and lower the contrast of what is behind it by alpha x 0.5"))
    if fam == "fog" or p["kind"] == "strip":
        info["state_machine"] = STATE_MACHINE
        info["fog"] = dict(u_ref_mps=k.get("u_ref", 0.0), scroll_note="the mean drift u_ref is baked OUT of the frames (the fog is Galilean-stabilised so loops are seamless): scroll the strip at u_ref plus the game wind to restore the motion",
                           layer_heights_m=p["game"].get("layer_heights_m"), bottom_fade_frac=k.get("bottom"), vertical_note="frame bottom = ground level; sink the quad about 5 to 10 percent of its height into the ground")
        info["fog"]["sim_s_per_frame"] = {c["name"]: c.get("sim_s_per_frame") for c in clips if c.get("sim_s_per_frame")}
    info["mirror_variants"] = dict(note="every loop clip may also be drawn mirrored (scale.x = -1) for twice as many looks; variants above are distinct simulation windows")
    info["wind_baked"] = p["sim"].get("wind") if not callable(p["sim"].get("wind")) else "profile"
    log(f"[{name}] main {sizes['main'] / 1024:.0f} KB (low {sizes['main_low'] / 1024:.0f}), scatter {sizes['scatter'] / 1024:.0f} (low {sizes['scatter_low'] / 1024:.0f})"
        + (f", heat {sizes['heat'] / 1024:.0f}" if heat else "") + f"; frame {fw}x{fh}px {n} frames, size {fw * mpx_x:.2f}x{fh * mpx_z:.2f} m; seam {seam:.2f} vs adj {adj:.2f}")
    info["bytes_total"] = int(sum(v for kk, v in sizes.items()))
    info["bytes_full"] = int(sum(v for kk, v in sizes.items() if "low" not in kk))
    return info


STATE_MACHINE = dict(
    states=["form", "drift", "linger", "thin", "fall"],
    description="form: cooling air makes fog thicken (play 'form' once, 8 key frames, cross-fade between them, then switch to 'drift'). drift: the normal moving fog (loop 'drift_a'/'drift_b'). "
                "linger: a calm period, nearly static slow churn (loop 'linger'). thin: burn-off, sun warms the air and the fog thins and breaks up (play 'thin' once, fade out at the end, delete the sprite). "
                "fall: the fog sinks and flattens (play 'fall' once, then hold its last frame as a thin low layer, then 'linger').",
    transitions=[dict(frm="form", to="drift", on="clip_end"), dict(frm="drift", to="linger", on="weather calms / wind below 1 m/s"), dict(frm="linger", to="drift", on="wind rises"),
                 dict(frm="drift", to="thin", on="sun / heat"), dict(frm="linger", to="thin", on="sun / heat"), dict(frm="drift", to="fall", on="air cools / still evening"), dict(frm="fall", to="linger", on="clip_end")],
    crossfade="clips are different sims: cross-fade 0.5 to 1.5 s when switching; key-frame clips (form, thin, fall) play at 1 to 2 fps with interpolate: true (blend adjacent frames)")


def merge_json(outdir, name, info):
    ap = os.path.join(outdir, "atmos_atlas.json")
    data = {"version": 1, "note": "Baked by tools/atmos/bake.py (reduced moist-air solver; see MODEL-NOTES-ATMOS.md)", "presets": {}}
    if os.path.exists(ap):
        try:
            data = json.load(open(ap))
        except Exception:
            pass
    data["presets"][name] = info
    data["presets"] = {k: data["presets"][k] for k in PR.ORDER if k in data["presets"]}
    with open(ap, "w") as fh:
        json.dump(data, fh, separators=(",", ":"))


def bake(name, seed=0, outdir=None):
    outdir = outdir or os.path.join(ROOT, "assets", "atmos")
    os.makedirs(outdir, exist_ok=True)
    kind = PR.PRESETS[name]["kind"]
    t0 = time.time()
    run = {"life": run_life, "shot": run_shot, "strip": run_strip, "blobs": run_blobs}[kind]
    air, rend, clips = run(name, seed)
    t1 = time.time() - t0
    log(f"[{name}] sim+render {t1:.0f}s")
    info = write_preset(name, air, rend, clips, outdir, seed)
    info["bake_seconds"] = round(t1)
    merge_json(outdir, name, info)
    log(f"[{name}] done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", help="a preset, a comma list, a family (steam|mist|fog) or 'all'")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    QUICK = a.quick
    if a.preset == "all":
        names = PR.ORDER
    elif a.preset in ("steam", "mist", "fog"):
        names = [n for n in PR.ORDER if n.startswith(a.preset + "_") or (a.preset == "mist" and n.startswith(("splash", "spray")))]
    else:
        names = a.preset.split(",")
    import traceback
    for nm in names:
        try:
            bake(nm, a.seed, a.out)
        except Exception:
            log(f"[{nm}] FAILED")
            traceback.print_exc()
            sys.stdout.flush()
    print("done", flush=True)
