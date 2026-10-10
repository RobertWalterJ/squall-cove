"""
fluid.py - reduced moist-air solver + droplet spray for Squall Cove steam, mist and fog sprites.

The flow numerics (stable fluids: MacCormack semi-Lagrangian advection, spectral FFT pressure projection,
vorticity confinement, linear drag, sponge) are copied from tools/fire/sim.py (not imported, so that folder can
change freely). The physics on top is new:

  th   temperature excess over the reference temperature T0 (kelvin)
  qe   water-vapour excess over the ambient background humidity (kg per kg of air)
  ql   liquid water (cloud / steam / fog droplets, kg per kg of air); optical density comes from it
  Saturation adjustment: vapour above the Clausius-Clapeyron saturation value condenses (adding latent heat,
  so condensing steam becomes MORE buoyant); subsaturated air evaporates the droplets (cooling the air).
  Buoyancy b = th/T0 + 0.608 qe - ql   (hot, moist air is light; liquid water load and cold air are heavy).
  Optional: stable ambient profile (inversion lid), ground cooling / heating / moistening schedules,
  slope drainage (dense fluid slides downhill), droplet fall speed, wind profile used for advection.

Spray: Lagrangian droplet parcels with a size distribution, Stokes drag with a Reynolds correction (relaxation
time tau, terminal velocity), gravity, evaporation (d(r^2)/dt law), eddy random walk, and two-way drag onto the air.
Parcels carry real mass, so the extinction coefficient comes out in 1/m (1.5 m / (rho_w r) per volume).

NOT modelled: real turbulence below the grid scale (the baker adds procedural detail), droplet collisions and
breakup, salt, radiative transfer, true microphysics (CCN, droplet growth), compressibility.
"""
import numpy as np
from scipy import ndimage as ndi
import scipy.fft as sfft
from concurrent.futures import ThreadPoolExecutor

_POOL = ThreadPoolExecutor(4)
PAD = 3
G = 9.81
LV, CP, RV = 2.5e6, 1005.0, 461.5
LC = LV / CP
RHO_W = 1000.0
RHO_A = 1.2
MU_A = 1.8e-5


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def qsat(T, p=101325.0):
    T = np.minimum(T, 372.0)
    es = 611.2 * np.exp(17.67 * (T - 273.15) / (T - 29.65))
    es = np.minimum(es, 0.92 * p)
    return 0.622 * es / (p - es)


class Air:
    def __init__(self, P, seed=0, supply=None):
        self.P = P
        self.nx, self.ny, self.nz = self.grid = tuple(P["grid"])
        self.dx = P["dx"]
        self.dt = P.get("dt", 1.0 / 48.0)
        self.px = bool(P.get("periodic", False))
        self.fmode = ("wrap", "nearest", "nearest") if self.px else "nearest"
        self.rng = np.random.default_rng(seed * 101 + 7)
        self.supply = supply
        self.T0 = P.get("T0", 285.0)
        self.t = 0.0
        sh = self.grid
        z = lambda: np.zeros(sh, np.float32)
        self.u, self.v, self.w = z(), z(), z()
        self.th, self.qe, self.ql = z(), z(), z()
        zc = (np.arange(self.nz) + 0.5) * self.dx
        self.zc = zc
        # ambient profiles (functions of height)
        self.th_amb = np.asarray(P["th_amb"](zc) if callable(P.get("th_amb")) else np.zeros(self.nz) + P.get("th_amb", 0.0), np.float32)
        rh = P["rh"](zc) if callable(P.get("rh")) else np.zeros(self.nz) + P.get("rh", 0.6)
        self.qb = (np.asarray(rh) * qsat(self.T0 + self.th_amb)).astype(np.float32)
        self.th += self.th_amb[None, None, :]
        wind = P.get("wind", 0.0)
        self.Uz = np.asarray(wind(zc) if callable(wind) else np.zeros(self.nz) + wind, np.float32)
        self.idx = np.indices(sh).astype(np.float32)
        self._masks()
        self._spectral()
        self.noise = [np.zeros(sh, np.float32) for _ in range(3)]
        self.vent_phase = self.rng.uniform(0, 6.283, (len(self.vents), 4))
        self.vent_freq = self.rng.uniform(0.7, 3.0, (len(self.vents), 4))
        self.spray = None
        self.cool_prof = np.exp(-zc / P.get("force_h", 1.0)).astype(np.float32)[None, None, :]
        self.patch = None
        if P.get("patch"):   # smooth random 2D field in (x, y): patchy cooling / moistening
            r = ndi.gaussian_filter(self.rng.standard_normal((self.nx, self.ny)), P["patch"], mode="wrap" if self.px else "nearest")
            r = r / (r.std() + 1e-6)
            self.patch = (1.0 + P.get("patch_amp", 0.5) * r).clip(0.1, None).astype(np.float32)[:, :, None]

    # ---- setup ---------------------------------------------------------------------------
    def _masks(self):
        nx, ny, nz = self.grid
        dx = self.dx
        X, Y, Zc = np.meshgrid((np.arange(nx) - nx / 2 + 0.5) * dx, (np.arange(ny) - ny / 2 + 0.5) * dx, (np.arange(nz) + 0.5) * dx, indexing="ij")
        self.X, self.Y, self.Zc = X.astype(np.float32), Y.astype(np.float32), Zc.astype(np.float32)
        L = nx * dx
        self.vents = []
        self.vent_masks = []
        for v in self.P.get("vents", []):
            v = dict(v)
            seed_j = self.rng.uniform(-1, 1, 3)
            v["x"] = v.get("x", 0.0) + (seed_j[0] * v.get("jit", 0.0))
            v["y"] = v.get("y", 0.0) + (seed_j[1] * v.get("jit", 0.0))
            rx, ry = v["rx"], v.get("ry", v["rx"])
            if v.get("line"):   # periodic line along x with uneven strength
                pat = np.zeros_like(X)
                for k, ph in zip((1, 2, 3, 5, 8), self.rng.uniform(0, 6.283, 5)):
                    pat += np.cos(2 * np.pi * k * (X + L / 2) / L + ph) / k ** 0.5
                pat = 0.7 + 0.3 * pat / (np.abs(pat).max() + 1e-6)
                d = np.abs(Y - v["y"]) / ry
                m = np.clip(1.4 - d, 0, 1) ** 1.5 * pat
            else:
                dxv = X - v["x"]
                if self.px:
                    dxv = np.mod(dxv + L / 2, L) - L / 2
                d = np.sqrt((dxv / rx) ** 2 + ((Y - v["y"]) / ry) ** 2)
                m = np.clip(1.4 - d, 0, 1) ** 1.5
            zt = v.get("dz", 1.6 * dx)
            m = m * np.exp(-(((Zc - v.get("z0", 0.0)) / zt) ** 2))
            self.vents.append(v)
            self.vent_masks.append(m.astype(np.float32))
        ix, iy, iz = np.arange(nx), np.arange(ny), np.arange(nz)
        side = lambda i, n, w: np.clip((w - np.minimum(i, n - 1 - i)) / w, 0, 1)
        wd = max(3, int(round(0.14 * nx)))
        wt = max(5, int(round(0.25 * nz)))
        sx, sy = side(ix, nx, wd)[:, None, None], side(iy, ny, max(3, int(0.14 * ny)))[None, :, None]
        top = np.clip((iz - (nz - wt)) / float(wt), 0, 1)[None, None, :]
        if self.px:
            sx = sx * 0
        self.sponge = (np.maximum(np.maximum(sx, sy), top).astype(np.float32)) ** 1.5
        self.solid = (np.arange(nz) < 1)[None, None, :] * np.ones((nx, ny, 1), bool)
        # noise forcing profile (churn) and horizontal drainage
        self.churn_prof = np.exp(-((self.zc / self.P.get("churn_h", 1e9)) ** 2))[None, None, :].astype(np.float32) if "churn_h" in self.P else 1.0

    def _spectral(self):
        nx, ny, nz = self.grid
        kx = np.fft.fftfreq(nx) * 2 * np.pi
        ky = np.fft.fftfreq(ny) * 2 * np.pi
        kz = np.fft.rfftfreq(nz) * 2 * np.pi
        self.kx = kx[:, None, None].astype(np.float32)
        self.ky = ky[None, :, None].astype(np.float32)
        self.kz = kz[None, None, :].astype(np.float32)
        k2 = self.kx ** 2 + self.ky ** 2 + self.kz ** 2
        k2[0, 0, 0] = 1.0
        self.ik2 = (1.0 / k2).astype(np.float32)

    # ---- numerics (from tools/fire/sim.py) -----------------------------------------------
    def _adv_coords(self, dt, extra_w=0.0):
        s = dt / self.dx
        vel = np.stack([self.u + self.Uz[None, None, :], self.v, self.w - extra_w])
        hi = np.array(self.grid, np.float32).reshape(3, 1, 1, 1) - 1.0
        back = self.idx - s * vel
        fwd = self.idx + s * vel
        if self.px:
            for c in (back, fwd):
                c[0] = np.mod(c[0], self.nx) + PAD
                c[1:] = np.clip(c[1:], 0.0, hi[1:])
            return back, fwd
        return np.clip(back, 0.0, hi), np.clip(fwd, 0.0, hi)

    def _grad(self, f):
        if self.px:
            return [0.5 * (np.roll(f, -1, 0) - np.roll(f, 1, 0)), np.gradient(f, axis=1), np.gradient(f, axis=2)]
        return np.gradient(f)

    def _samp(self, f, c):
        if self.px:
            f = np.concatenate([f[-PAD:], f, f[:PAD]], 0)
        nx = self.nx
        cuts = np.linspace(0, nx, 5).astype(int)
        out = np.empty((nx,) + f.shape[1:], np.float32)

        def job(i):
            a, b = cuts[i], cuts[i + 1]
            out[a:b] = ndi.map_coordinates(f, c[:, a:b], order=1, mode="nearest", prefilter=False)
        list(_POOL.map(job, range(4)))
        return out

    def _advect(self, f, back, fwd, mac=True):
        a = self._samp(f, back)
        if not mac:
            return a
        b = self._samp(a, fwd)
        r = a + 0.5 * (f - b)
        r = np.clip(r, min(float(f.min()), float(a.min())), max(float(f.max()), float(a.max())))
        return r.astype(np.float32)

    def _project(self):
        uh = sfft.rfftn(self.u, workers=4)
        vh = sfft.rfftn(self.v, workers=4)
        wh = sfft.rfftn(self.w, workers=4)
        c = (self.kx * uh + self.ky * vh + self.kz * wh) * self.ik2
        uh -= self.kx * c
        vh -= self.ky * c
        wh -= self.kz * c
        s = self.grid
        self.u = sfft.irfftn(uh, s=s, workers=4).astype(np.float32)
        self.v = sfft.irfftn(vh, s=s, workers=4).astype(np.float32)
        self.w = sfft.irfftn(wh, s=s, workers=4).astype(np.float32)

    def _vorticity(self, dt, vc):
        gu, gv, gw = self._grad(self.u), self._grad(self.v), self._grad(self.w)
        ox, oy, oz = gw[1] - gv[2], gu[2] - gw[0], gv[0] - gu[1]
        mag = ndi.gaussian_filter(np.sqrt(ox * ox + oy * oy + oz * oz), 0.7, mode=self.fmode)
        gm = self._grad(mag)
        n = np.sqrt(gm[0] ** 2 + gm[1] ** 2 + gm[2] ** 2) + 1e-6
        nx_, ny_, nz_ = gm[0] / n, gm[1] / n, gm[2] / n
        sc = vc * 20.0 * min(dt, 1.0 / 48.0)
        self.u += sc * (ny_ * oz - nz_ * oy)
        self.v += sc * (nz_ * ox - nx_ * oz)
        self.w += sc * (nx_ * oy - ny_ * ox)

    def _noise_step(self, dt, tc=0.5, sig=1.6):
        a = np.exp(-dt / tc)
        for i in range(3):
            fresh = ndi.gaussian_filter(self.rng.standard_normal(self.grid).astype(np.float32), sig, mode=self.fmode)
            fresh /= fresh.std() + 1e-6
            self.noise[i] = a * self.noise[i] + np.sqrt(1 - a * a) * fresh

    def _flicker(self, i, v):
        amp, fl = v.get("amp", 1.0), v.get("flick", 0.0)
        f = 0.0
        ph, fr = self.vent_phase[i], self.vent_freq[i] * v.get("freq", 1.0)
        for j in range(4):
            f += np.sin(self.t * fr[j] * (1.0 + 0.7 * j) + ph[j]) / (1.0 + j)
        a = max(0.0, amp * (1.0 + 0.55 * fl * f / 1.9))
        if v.get("gate"):          # intermittent puffs: raised-cosine gate with random timing
            g = np.sin(self.t * fr[0] * 1.3 + ph[1]) + 0.6 * np.sin(self.t * fr[2] * 0.9 + ph[3])
            a *= float(smoothstep(-0.2, 0.7, g))
        if v.get("t0") is not None:
            a *= float(smoothstep(v["t0"], v["t0"] + v.get("tr", 0.3), self.t))
        if v.get("t1") is not None:
            a *= 1.0 - float(smoothstep(v["t1"], v["t1"] + v.get("tf", 0.5), self.t))
        return a

    # ---- thermodynamics ---------------------------------------------------------------------
    def _thermo(self, dt):
        P = self.P
        T = self.T0 + self.th
        qv = self.qb[None, None, :] + self.qe
        ql = self.ql
        for _ in range(3):
            qs = qsat(T)
            f = 1.0 + LC * qs * LV / (RV * T * T)
            c = np.maximum((qv - qs) / f, 0)
            ql = ql + c
            qv = qv - c
            T = T + LC * c
        qs = qsat(T)
        f = 1.0 + LC * qs * LV / (RV * T * T)
        ev = np.minimum(ql, np.maximum((qs - qv) / f, 0)) * (1.0 - np.exp(-dt / P.get("tau_evap", 1.0)))
        ql = ql - ev
        qv = qv + ev
        T = T - LC * ev
        self.th = (T - self.T0).astype(np.float32)
        self.qe = (qv - self.qb[None, None, :]).astype(np.float32)
        self.ql = np.maximum(ql, 0).astype(np.float32)

    # ---- one step ------------------------------------------------------------------------------
    def step(self):
        P, dt = self.P, self.dt
        sup = float(self.supply(self.t)) if self.supply else 1.0
        sched = P.get("sched")                      # t -> dict of scalar controls (cool, moist, churn, vt, slope, buoy, ...)
        ctl = sched(self.t) if sched else {}
        self._noise_step(dt, P.get("noise_tc", 0.5), P.get("noise_sig", 1.6))
        # vents
        for i, (m, v) in enumerate(zip(self.vent_masks, self.vents)):
            a = self._flicker(i, v) * sup * float(v["sched"](self.t) if v.get("sched") else 1.0)
            if a < 0.01:
                continue
            rate = min(1.0, v.get("rate", 10.0) * dt)
            mr = m * rate
            if v.get("th") is not None:
                self.th += (self.th_amb[None, None, :] + v["th"] * a - self.th) * mr
            if v.get("qe") is not None:
                self.qe += (v["qe"] * a - self.qe) * mr
            if v.get("ql"):
                self.ql += (v["ql"] * a - self.ql) * mr
            for ax, key in ((self.w, "w"), (self.u, "u"), (self.v, "v")):
                if v.get(key) is not None:
                    ax += (v[key] * a - ax) * m * min(1.0, 6.0 * dt)
            tb = v.get("turb", 0.3) * max(abs(v.get("w", 0.0)), abs(v.get("u", 0.0)), 0.3) * dt * 8
            self.u += tb * self.noise[0] * m
            self.v += tb * self.noise[1] * m
            self.w += tb * 0.6 * self.noise[2] * m
        # ground cooling / heating / moistening (fog formation, burn-off), patchy in x, y
        cp_ = self.cool_prof if ctl.get("force_h") is None else np.exp(-self.zc / ctl["force_h"]).astype(np.float32)[None, None, :]
        pr = cp_ if self.patch is None else cp_ * self.patch
        if ctl.get("cool"):
            self.th -= ctl["cool"] * dt * pr
        if ctl.get("moist"):
            self.qe += ctl["moist"] * dt * pr
        # forces
        b = (self.th - self.th_amb[None, None, :]) / self.T0 + 0.608 * self.qe - self.ql
        b = b * ctl.get("buoy", P.get("buoy", 1.0))
        self.w += dt * G * b
        slope = ctl.get("slope", P.get("slope", 0.0))
        if slope:
            self.u += dt * G * slope * (-np.minimum(b, 0.0)) * 8.0   # dense (negative-buoyancy) fluid slides along +x
        ch = ctl.get("churn", P.get("churn", 0.0))
        if ch:
            cp = self.churn_prof
            self.u += dt * ch * self.noise[0] * cp
            self.v += dt * ch * self.noise[1] * cp
            self.w += dt * ch * 0.5 * self.noise[2] * cp
        if self.spray is not None:
            self.spray.step(self, dt, sup)
        damp = 1.0 - dt * P.get("drag", 0.2)
        self.u *= damp
        self.v *= damp
        self.w *= damp
        if P.get("vc", 0.4) > 0:
            self._vorticity(dt, P.get("vc", 0.4))
        sp = 1.0 - np.clip(self.sponge * 10.0 * dt, 0, 0.9)
        self.u *= sp
        self.v *= sp
        self.w *= sp
        self.u[self.solid] = 0
        self.v[self.solid] = 0
        self.w[self.solid] = 0
        self._project()
        self.u[self.solid] = 0
        self.v[self.solid] = 0
        self.w[self.solid] = 0
        # advection (liquid also falls)
        back, fwd = self._adv_coords(dt)
        nu, nv, nw = (self._advect(f, back, fwd) for f in (self.u, self.v, self.w))
        self.th = self._advect(self.th, back, fwd)
        self.qe = self._advect(self.qe, back, fwd)
        vt = ctl.get("vt", P.get("vt", 0.0))
        if vt > 0:
            bq, fq = self._adv_coords(dt, extra_w=vt)
            self.ql = np.maximum(self._advect(self.ql, bq, fq), 0)
        else:
            self.ql = np.maximum(self._advect(self.ql, back, fwd), 0)
        self.u, self.v, self.w = nu, nv, nw
        # mixing: a small constant part plus a turbulent part proportional to the local speed (entrainment)
        kt = P.get("kt", 0.0)
        d = P.get("diff", 0.06)
        if kt > 0:
            spd = np.sqrt(self.u ** 2 + self.v ** 2 + self.w ** 2)
            d = np.minimum(d + kt * spd * dt / self.dx, P.get("dmax", 0.4)).astype(np.float32)
        for name in ("th", "qe", "ql"):
            f = getattr(self, name)
            setattr(self, name, (f + d * (ndi.uniform_filter(f, 3, mode=self.fmode) - f)).astype(np.float32))
        if kt > 0:
            for name in ("u", "v", "w"):
                f = getattr(self, name)
                setattr(self, name, (f + 0.5 * d * (ndi.uniform_filter(f, 3, mode=self.fmode) - f)).astype(np.float32))
        self._thermo(dt)
        # open boundaries relax to ambient
        k = np.clip(self.sponge * P.get("sponge_rate", 4.0) * dt, 0, 0.9)
        self.th += (self.th_amb[None, None, :] - self.th) * k
        self.qe *= 1 - k
        self.ql *= 1 - np.clip(self.sponge * P.get("sponge_rate", 4.0) * 1.5 * dt, 0, 0.9)
        # ambient cooling to the surroundings (mixing with far field)
        mc = P.get("mixc", 0.0)
        if mc:
            self.th += (self.th_amb[None, None, :] - self.th) * mc * dt
            self.qe *= 1 - mc * dt
        self.t += dt

    # ---- readout ---------------------------------------------------------------------------------
    def sigma_cloud(self, reff):
        """extinction coefficient (1/m) of the liquid field: 1.5 * LWC / (rho_w * r_eff)"""
        return 1.5 * (self.ql * RHO_A) / (RHO_W * reff)


# =================================================================================================
class Spray:
    """Lagrangian droplet parcels. emitters: list of dicts, see presets.py."""

    def __init__(self, emitters, seed=0, nmax=60000, rh=0.7, rmin=6e-6, eddy=0.0, floor=0.0, coupling=1.0):
        self.em = emitters
        self.rng = np.random.default_rng(seed * 31 + 5)
        self.rh, self.rmin, self.eddy, self.floor, self.coupling = rh, rmin, eddy, floor, coupling
        self.nmax = nmax
        self.pos = np.zeros((0, 3), np.float32)
        self.vel = np.zeros((0, 3), np.float32)
        self.r = np.zeros(0, np.float32)
        self.m = np.zeros(0, np.float32)
        self.age = np.zeros(0, np.float32)

    def _emit(self, air, dt, sup):
        rng = self.rng
        P_, V_, R_, M_ = [], [], [], []
        for e in self.em:
            a = sup * float(e["sched"](air.t) if e.get("sched") else 1.0)
            if a <= 0.001:
                continue
            n = int(rng.poisson(e["pps"] * a * dt))
            if n <= 0:
                continue
            n = min(n, max(0, self.nmax - len(self.r)))
            if n <= 0:
                continue
            c = np.array(e["pos"], np.float32)
            ps = np.array(e.get("pos_sigma", (0.02, 0.02, 0.02)), np.float32)
            p = c + rng.standard_normal((n, 3)).astype(np.float32) * ps
            if e.get("ring"):                                     # crown / ring emitter
                th_ = rng.uniform(0, 2 * np.pi, n)
                rr = e["ring"] * (1 + 0.15 * rng.standard_normal(n))
                p[:, 0] = c[0] + rr * np.cos(th_)
                p[:, 1] = c[1] + rr * np.sin(th_)
            if e.get("line"):                                     # emitter along x between line[0], line[1]
                p[:, 0] = c[0] + rng.uniform(e["line"][0], e["line"][1], n)
            sp = np.maximum(e["speed"][0] + e["speed"][1] * rng.standard_normal(n), 0.05).astype(np.float32)
            if e.get("radial"):
                az = rng.uniform(0, 2 * np.pi, n)
                el = np.radians(np.clip(e["elev"][0] + e["elev"][1] * rng.standard_normal(n), 3, 88))
                d = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], 1)
                if e.get("ring"):   # outward from the ring
                    d[:, 0] = np.cos(el) * np.cos(th_)
                    d[:, 1] = np.cos(el) * np.sin(th_)
            else:
                ax = np.array(e["axis"], np.float32)
                ax = ax / np.linalg.norm(ax)
                sg = np.array(e.get("spread", (0.2, 0.2, 0.2)), np.float32)
                d = ax + rng.standard_normal((n, 3)).astype(np.float32) * sg
                d = d / np.linalg.norm(d, axis=1, keepdims=True)
            v = d * sp[:, None]
            # droplet radius: log-normal by parcel
            r = np.exp(np.log(e["r"][0]) + e["r"][1] * rng.standard_normal(n)).astype(np.float32)
            r = np.clip(r, 8e-6, 2.5e-3)
            mass = (e["flux"] * a * dt / n) * np.ones(n, np.float32)
            P_.append(p)
            V_.append(v)
            R_.append(r)
            M_.append(mass)
        if P_:
            self.pos = np.concatenate([self.pos] + P_)
            self.vel = np.concatenate([self.vel] + V_)
            self.r = np.concatenate([self.r] + R_)
            self.m = np.concatenate([self.m] + M_)
            self.age = np.concatenate([self.age, np.zeros(sum(len(x) for x in R_), np.float32)])

    def step(self, air, dt, sup):
        self._emit(air, dt, sup)
        n = len(self.r)
        if n == 0:
            return
        dx = air.dx
        # air velocity at the parcels
        ci = np.stack([self.pos[:, 0] / dx + air.nx / 2 - 0.5, self.pos[:, 1] / dx + air.ny / 2 - 0.5, self.pos[:, 2] / dx - 0.5])
        ci[0] = np.clip(ci[0], 0, air.nx - 1) if not air.px else np.mod(ci[0], air.nx)
        ci[1] = np.clip(ci[1], 0, air.ny - 1)
        ci[2] = np.clip(ci[2], 0, air.nz - 1)
        ua = np.stack([ndi.map_coordinates(f, ci, order=1, mode="nearest" if not air.px else "grid-wrap", prefilter=False) for f in (air.u, air.v, air.w)], 1)
        ua[:, 0] += np.interp(self.pos[:, 2], air.zc, air.Uz)
        rel = self.vel - ua
        sp = np.linalg.norm(rel, axis=1)
        r = self.r.astype(np.float64)
        tau0 = 2.0 * RHO_W * r * r / (9.0 * MU_A)
        Re = 2.0 * r * sp * RHO_A / MU_A
        tau = (tau0 / (1.0 + 0.15 * Re ** 0.687)).astype(np.float32)
        decay = np.exp(-dt / tau)
        gv = np.array([0, 0, -G], np.float32)
        vt_ = tau[:, None] * gv[None, :]
        newv = ua + vt_ + (self.vel - ua - vt_) * decay[:, None]
        # two-way drag: momentum given to the air (per cell), mass-weighted
        if self.coupling > 0:
            force = (self.vel - newv) * (self.m / dt)[:, None]    # change of parcel momentum = impulse onto the air (minus gravity share)
            force = force + (self.m[:, None] * gv[None, :])        # remove gravity: only the aerodynamic part acts on the air
            cell = (np.clip(np.round(ci[0]), 0, air.nx - 1).astype(np.int64) * air.ny + np.clip(np.round(ci[1]), 0, air.ny - 1).astype(np.int64)) * air.nz + np.clip(np.round(ci[2]), 0, air.nz - 1).astype(np.int64)
            tot = air.nx * air.ny * air.nz
            vol = RHO_A * dx ** 3
            acc = []
            for k in range(3):
                acc.append(np.bincount(cell, weights=force[:, k], minlength=tot).reshape(air.grid) / vol)
            lim = 25.0
            air.u += dt * np.clip(acc[0], -lim, lim).astype(np.float32) * self.coupling
            air.v += dt * np.clip(acc[1], -lim, lim).astype(np.float32) * self.coupling
            air.w += dt * np.clip(acc[2], -lim, lim).astype(np.float32) * self.coupling
        self.vel = newv.astype(np.float32)
        self.pos = self.pos + self.vel * dt
        if self.eddy > 0:
            self.pos += (self.rng.standard_normal((n, 3)) * np.sqrt(2 * self.eddy * dt)).astype(np.float32) * np.array([1, 1, 0.7], np.float32)
        # evaporation: d(r^2)/dt = -6.4e-10 (1 - RH)
        r2 = np.maximum(self.r ** 2 - 6.4e-10 * (1 - self.rh) * dt * (1.0 + 0.3 * np.minimum(sp, 10)), 0)
        rn = np.sqrt(r2)
        self.m = (self.m * (rn / np.maximum(self.r, 1e-9)) ** 3).astype(np.float32)
        self.r = rn.astype(np.float32)
        self.age += dt
        L2x = air.nx * dx / 2
        L2y = air.ny * dx / 2
        keep = (self.r > self.rmin) & (self.pos[:, 2] > self.floor) & (self.pos[:, 2] < air.nz * dx * 0.97) & (np.abs(self.pos[:, 1]) < L2y * 0.95)
        if air.px:
            self.pos[:, 0] = np.mod(self.pos[:, 0] + L2x, 2 * L2x) - L2x
        else:
            keep &= np.abs(self.pos[:, 0]) < L2x * 0.95
        if not keep.all():
            self.pos, self.vel, self.r, self.m, self.age = self.pos[keep], self.vel[keep], self.r[keep], self.m[keep], self.age[keep]

    def sigma(self, air, up, shape=None, blur=(1.1, 0.5), trail=1, span=1 / 24):
        """splat parcels into an extinction-coefficient volume V[z(top first), y, x] (1/m) at `up` times the grid in x and z"""
        nx, ny, nz = air.grid
        H, D, W = nz * up, ny, nx * up
        vol = np.zeros(H * D * W, np.float32)
        for jt in range(trail if len(self.r) else 0):
            dxr = air.dx / up
            back = (span * jt / max(trail - 1, 1)) if trail > 1 else 0.0
            pp = self.pos - self.vel * back
            x = (pp[:, 0] / dxr + W / 2 - 0.5).astype(np.float64)
            y = (pp[:, 1] / air.dx + D / 2 - 0.5).astype(np.float64)
            z = (pp[:, 2] / dxr - 0.5).astype(np.float64)
            wgt = (1.5 * self.m / (RHO_W * np.maximum(self.r, 1e-6)) / (dxr * air.dx * dxr) / trail).astype(np.float64)
            x0, y0, z0 = np.floor(x).astype(int), np.floor(y).astype(int), np.floor(z).astype(int)
            fx, fy, fz = x - x0, y - y0, z - z0
            zt = lambda zz: H - 1 - zz     # top-first
            for dxi in (0, 1):
                for dyi in (0, 1):
                    for dzi in (0, 1):
                        w_ = wgt * (fx if dxi else 1 - fx) * (fy if dyi else 1 - fy) * (fz if dzi else 1 - fz)
                        xi, yi, zi = x0 + dxi, y0 + dyi, z0 + dzi
                        if air.px:
                            xi = np.mod(xi, W)
                        ok = (xi >= 0) & (xi < W) & (yi >= 0) & (yi < D) & (zi >= 0) & (zi < H)
                        idx = (zt(zi[ok]) * D + yi[ok]) * W + xi[ok]
                        vol += np.bincount(idx, weights=w_[ok], minlength=H * D * W).astype(np.float32)
        vol = vol.reshape(H, D, W)
        return ndi.gaussian_filter(vol, (blur[0], blur[1], blur[0]), mode=("nearest", "nearest", "wrap" if air.px else "nearest"))
