"""
sim.py - reduced 3D combustion solver for Squall Cove fire sprites.

A small, honest, REDUCED model inspired by (not a reproduction of) the multi-species
approach of "Fire-X: Extinguishing Fire with Stoichiometric Heat Release"
(Wrede et al., SIGGRAPH Asia 2025). Numpy + scipy only.

What is modelled (per cell, on a regular grid, SI units, dx in metres):
  u,v,w   velocity                 stable-fluids: MacCormack advection, buoyancy,
                                   vorticity confinement, linear drag, spectral
                                   (FFT) pressure projection, sponge boundaries
  theta   normalised temperature   (T - 300 K) / 1700 K, 0 = ambient, 1 = about 2000 K
  F       fuel vapour              (air-equivalent mass fraction; pure vapour = 1)
  O       oxidiser                 normalised to ambient air = 1 (nitrogen is the
                                   implicit inert remainder, not stored)
  P       burned products          CO2 + water vapour lumped; only used for visible
                                   steam / damp-smoke condensation
  S       soot                     inception when fuel-rich, hot and old enough
                                   (residence-time proxy), oxidised in hot air
  A       fuel age (s)             residence time since leaving the vent; delays
                                   soot inception so the base of a flame stays
                                   clean / blue and it turns sooty / orange higher up
Reaction (stoichiometric, mixing limited):  F + s O -> (1+s) P,  heat release
  proportional to burnt fuel,  d(theta) = s * theta_ad * burnt  (so a stoichiometric
  mixture reaches the adiabatic theta_ad).  Ignition needs theta > t_ign (smooth),
  so flames self-quench where entrainment and radiation cool the gas below it.
  Radiative cooling ~ theta^3 (stronger when sooty).  Optional water spray: heat
  sink plus steam, and a fuel-starvation factor, driven by water(t) in [0, 1].

What is NOT modelled: real thermochemistry/kinetics, compressibility / thermal
expansion, radiative transfer between cells, turbulence below the grid scale (the
baker adds a procedural sub-grid detail field), real fuel decomposition. Parameters
are tuned by eye against the look of real fires, not fitted to measurements.
"""
import numpy as np
from scipy import ndimage as ndi
import scipy.fft as sfft
from concurrent.futures import ThreadPoolExecutor
_POOL = ThreadPoolExecutor(4)

GRID = (32, 32, 48)  # nx, ny, nz  (z is up). Coarse on purpose: see MODEL-NOTES-FIRE-BAKED.md
DT = 1.0 / 48.0

# ---------------------------------------------------------------------------------
# Presets. Vents: (x_m, y_m, rx_m, ry_m, z0_m, amp, flick) relative to the domain
# centre (x,y) and floor (z). amp scales that vent's fuel supply, flick is the
# relative strength of its slow random flicker.
# ---------------------------------------------------------------------------------
PRESETS = {
    # (a) campfire / barrel: wood-like pyrolysis vapour, orange diffusion flame, soot
    "campfire": dict(
        dx=0.033, s=5.0, theta_ad=0.80, k=45.0, t_ign=0.20, rad=3.6, rad_soot=5.0,
        beta=13.0, drag=0.55, vc=0.55, diff=0.10,
        F_src=0.3, O_src=0.0, w_src=0.3, src_rate=14.0, pilot=0.62, turb=0.55,
        soot_k=9.0, soot_ox=2.0, delay=(0.04, 0.16), steam=0.0,
        vents=[(-0.10, 0.02, 0.10, 0.08, 0.10, 1.0, 0.6), (0.11, -0.03, 0.09, 0.09, 0.10, 0.85, 0.6),
               (0.0, 0.10, 0.07, 0.06, 0.12, 0.6, 0.8), (0.02, -0.11, 0.07, 0.06, 0.10, 0.55, 0.8)],
        warm=3.2,
    ),
    # (b) gas flame: rich premix (blue base), then diffusion burn-out, turbulent top
    "gas": dict(
        dx=0.025, s=8.0, theta_ad=0.92, k=70.0, t_ign=0.22, rad=2.6, rad_soot=3.0,
        beta=11.0, drag=0.45, vc=0.45, diff=0.08,
        F_src=0.26, O_src=0.46, w_src=1.5, src_rate=30.0, pilot=0.70, turb=0.20,
        soot_k=7.0, soot_ox=3.0, delay=(0.05, 0.18), steam=0.0,
        vents=[(0.0, 0.0, 0.075, 0.075, 0.03, 1.0, 0.25), (0.0, 0.0, 0.045, 0.045, 0.06, 0.6, 0.35)],
        warm=2.6,
    ),
    # (c) fuel pool / burning oil: large, sooty, black smoke head
    "pool": dict(
        dx=0.140, s=7.0, theta_ad=0.78, k=40.0, t_ign=0.22, rad=2.2, rad_soot=4.0,
        beta=10.0, drag=0.30, vc=0.55, diff=0.10,
        F_src=1.0, O_src=0.0, w_src=2.4, src_rate=8.0, pilot=0.60, turb=0.55,
        soot_k=6.0, soot_ox=1.2, delay=(0.15, 0.55), steam=0.0,
        vents=[(0.0, 0.0, 0.75, 0.75, 0.05, 1.0, 0.7), (0.9, 0.1, 0.4, 0.4, 0.05, 0.7, 0.9),
               (-0.85, -0.2, 0.4, 0.4, 0.05, 0.7, 0.9)],
        warm=6.5,
    ),
    # (d) vehicle fire: turbulent, orange-red, heavy smoke; engine bay + cabin + underbody
    "vehicle": dict(
        dx=0.140, s=6.0, theta_ad=0.76, k=40.0, t_ign=0.22, rad=2.4, rad_soot=4.5,
        beta=10.5, drag=0.30, vc=0.65, diff=0.10,
        F_src=1.0, O_src=0.0, w_src=2.2, src_rate=8.0, pilot=0.60, turb=0.9,
        soot_k=5.5, soot_ox=1.3, delay=(0.12, 0.50), steam=0.0,
        vents=[(-1.0, 0.0, 0.45, 0.55, 0.35, 1.0, 1.0), (0.4, 0.0, 0.5, 0.5, 0.45, 0.8, 1.0),
               (1.2, 0.1, 0.3, 0.35, 0.15, 0.5, 1.0), (-0.1, 0.0, 0.4, 0.35, 0.05, 0.45, 0.9)],
        warm=6.5,
    ),
    # (e) building / roof fire: wide, tall, many window and roof vents
    "building": dict(
        dx=0.280, s=6.0, theta_ad=0.78, k=35.0, t_ign=0.22, rad=1.8, rad_soot=3.5,
        beta=9.5, drag=0.22, vc=0.60, diff=0.10,
        F_src=1.0, O_src=0.0, w_src=3.2, src_rate=6.0, pilot=0.60, turb=0.8,
        soot_k=5.0, soot_ox=1.2, delay=(0.2, 0.9), steam=0.0,
        vents=[(-2.5, 0.0, 0.7, 0.8, 0.5, 0.9, 1.0), (-0.85, 0.0, 0.65, 0.8, 0.6, 1.0, 1.0),
               (0.85, 0.0, 0.65, 0.8, 0.5, 0.9, 1.0), (2.5, 0.0, 0.7, 0.8, 0.6, 0.85, 1.0),
               (-1.6, 0.0, 0.9, 0.9, 2.8, 0.7, 1.0), (1.6, 0.0, 0.9, 0.9, 2.7, 0.7, 1.0)],
        warm=9.0,
    ),
}


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Sim:
    def __init__(self, preset, seed=0, grid=GRID, water=None):
        self.name = preset
        self.p = dict(PRESETS[preset])
        self.nx, self.ny, self.nz = self.grid = grid
        self.rng = np.random.default_rng(seed + 1000 * (list(PRESETS).index(preset) + 1))
        self.dx = self.p["dx"]
        self.water = water  # callable t -> 0..1, or None
        self.t = 0.0
        sh = grid
        z = lambda: np.zeros(sh, np.float32)
        self.u, self.v, self.w = z(), z(), z()
        self.th, self.F, self.S, self.P, self.A = z(), z(), z(), z(), z()
        self.O = np.ones(sh, np.float32)
        self.R = z()      # reaction rate this step (1/s of burnt fuel), for rendering
        self.Rb = z()     # same but weighted by "lean / premixed" fraction (blue)
        self.idx = np.indices(sh).astype(np.float32)
        self._init_masks()
        self._init_spectral()
        self.zs = int(min(grid[2], max(v[4] for v in self.p["vents"]) / self.dx + 6))
        self.vent_masks = [m[:, :, :self.zs].copy() for m in self.vent_masks]
        self.noise = [np.zeros((grid[0], grid[1], self.zs), np.float32) for _ in range(3)]
        self.vent_phase = self.rng.uniform(0, 6.283, (len(self.p["vents"]), 4))
        self.vent_freq = self.rng.uniform(0.8, 3.2, (len(self.p["vents"]), 4))

    # ---- setup ---------------------------------------------------------------
    def _init_masks(self):
        nx, ny, nz = self.grid
        dx = self.dx
        X, Y, Zc = np.meshgrid((np.arange(nx) - nx / 2 + 0.5) * dx, (np.arange(ny) - ny / 2 + 0.5) * dx,
                               (np.arange(nz) + 0.5) * dx, indexing="ij")
        self.vent_masks = []
        for (vx, vy, rx, ry, z0, amp, fl) in self.p["vents"]:
            d = np.sqrt(((X - vx) / rx) ** 2 + ((Y - vy) / ry) ** 2)
            # soft-edged disc, a thin layer at height z0 (thickness 2 cells)
            m = np.clip(1.4 - d, 0, 1) ** 1.5 * np.exp(-(((Zc - z0) / (1.6 * dx)) ** 2))
            self.vent_masks.append(m.astype(np.float32))
        # sponge profiles (0 inside, 1 at the open boundary)
        ix, iy, iz = np.arange(nx), np.arange(ny), np.arange(nz)
        side = lambda i, n, w: np.clip((w - np.minimum(i, n - 1 - i)) / w, 0, 1)
        wd = max(4, int(round(9 * nx / 64)))
        wt = max(6, int(round(16 * nz / 96)))
        sx, sy = side(ix, nx, wd)[:, None, None], side(iy, ny, wd)[None, :, None]
        top = np.clip((iz - (nz - wt)) / float(wt), 0, 1)[None, None, :]
        self.sponge = np.maximum(np.maximum(sx, sy), top).astype(np.float32) ** 1.5
        self.solid = (np.arange(nz) < 2)[None, None, :] * np.ones((nx, ny, 1), bool)
        self.Zc = Zc.astype(np.float32)

    def _init_spectral(self):
        nx, ny, nz = self.grid
        kx = np.fft.fftfreq(nx) * 2 * np.pi
        ky = np.fft.fftfreq(ny) * 2 * np.pi
        kz = np.fft.rfftfreq(nz) * 2 * np.pi
        # the last axis uses rfft; build matching k arrays (axis order x, y, z)
        self.kx = kx[:, None, None].astype(np.float32)
        self.ky = ky[None, :, None].astype(np.float32)
        self.kz = kz[None, None, :].astype(np.float32)
        k2 = self.kx ** 2 + self.ky ** 2 + self.kz ** 2
        k2[0, 0, 0] = 1.0
        self.ik2 = (1.0 / k2).astype(np.float32)

    # ---- numerics -----------------------------------------------------------------
    def _adv_coords(self, dt):
        s = dt / self.dx
        vel = np.stack([self.u, self.v, self.w])
        hi = np.array(self.grid, np.float32).reshape(3, 1, 1, 1) - 1.0
        back = np.clip(self.idx - s * vel, 0.0, hi)   # in-range coordinates take scipy's fast path
        fwd = np.clip(self.idx + s * vel, 0.0, hi)
        return back, fwd

    @staticmethod
    def _samp(f, c):
        # slab-parallel trilinear sampling (scipy releases the GIL); 4 threads on purpose
        nx = f.shape[0]
        cuts = np.linspace(0, nx, 5).astype(int)
        out = np.empty(f.shape, np.float32)

        def job(i):
            a, b = cuts[i], cuts[i + 1]
            out[a:b] = ndi.map_coordinates(f, c[:, a:b], order=1, mode="nearest", prefilter=False)
        list(_POOL.map(job, range(4)))
        return out

    def _advect(self, f, back, fwd, mac=True, clamp=True):
        a = self._samp(f, back)
        if not mac:
            return a
        b = self._samp(a, fwd)
        r = a + 0.5 * (f - b)
        if clamp:  # cheap limiter: keep within the range of the field itself
            r = np.clip(r, min(float(f.min()), float(a.min())), max(float(f.max()), float(a.max())))
        return r.astype(np.float32)

    def _project(self):
        ax = (0, 1, 2)
        uh = sfft.rfftn(self.u, workers=4)
        vh = sfft.rfftn(self.v, workers=4)
        wh = sfft.rfftn(self.w, workers=4)
        dv = self.kx * uh + self.ky * vh + self.kz * wh
        c = dv * self.ik2
        uh -= self.kx * c
        vh -= self.ky * c
        wh -= self.kz * c
        s = self.grid
        self.u = sfft.irfftn(uh, s=s, workers=4).astype(np.float32)
        self.v = sfft.irfftn(vh, s=s, workers=4).astype(np.float32)
        self.w = sfft.irfftn(wh, s=s, workers=4).astype(np.float32)

    def _vorticity_confinement(self, dt):
        gu = np.gradient(self.u)
        gv = np.gradient(self.v)
        gw = np.gradient(self.w)
        ox = gw[1] - gv[2]
        oy = gu[2] - gw[0]
        oz = gv[0] - gu[1]
        mag = np.sqrt(ox * ox + oy * oy + oz * oz)
        mag = ndi.gaussian_filter(mag, 0.7)
        gm = np.gradient(mag)
        n = np.sqrt(gm[0] ** 2 + gm[1] ** 2 + gm[2] ** 2) + 1e-6
        nx_, ny_, nz_ = gm[0] / n, gm[1] / n, gm[2] / n
        fx = ny_ * oz - nz_ * oy
        fy = nz_ * ox - nx_ * oz
        fz = nx_ * oy - ny_ * ox
        # vc is a dimensionless strength; vorticity here is in (m/s) per cell
        sc = self.p['vc'] * 20.0 * dt
        self.u += sc * fx
        self.v += sc * fy
        self.w += sc * fz

    def _noise_step(self, dt):
        # AR(1) smooth noise, three components, correlation time ~ 0.12 s
        a = np.exp(-dt / 0.12)
        for i in range(3):
            fresh = ndi.gaussian_filter(self.rng.standard_normal(self.noise[0].shape).astype(np.float32), 1.6)
            fresh /= fresh.std() + 1e-6
            self.noise[i] = a * self.noise[i] + np.sqrt(1 - a * a) * fresh

    def _vent_flicker(self):
        out = []
        for i, (vx, vy, rx, ry, z0, amp, fl) in enumerate(self.p["vents"]):
            ph, fr = self.vent_phase[i], self.vent_freq[i]
            f = 0.0
            for j in range(4):
                f += np.sin(self.t * fr[j] * (1.0 + 0.7 * j) + ph[j]) / (1.0 + j)
            f = f / 1.9
            out.append(max(0.0, amp * (1.0 + 0.55 * fl * f)))
        return out

    # ---- one time step -----------------------------------------------------------
    def step(self, dt=DT):
        p = self.p
        wat = float(self.water(self.t)) if self.water else 0.0
        fl = self._vent_flicker()
        self._noise_step(dt)

        # sources: fuel (and premix oxidiser), hot pilot, vent velocity and turbulence
        starve = 1.0 - 0.95 * smoothstep(0.35, 0.9, wat)  # water + fuel starvation
        zs = slice(0, self.zs)
        F, O, A, th = self.F[:, :, zs], self.O[:, :, zs], self.A[:, :, zs], self.th[:, :, zs]
        U, V, W = self.u[:, :, zs], self.v[:, :, zs], self.w[:, :, zs]
        for m, a in zip(self.vent_masks, fl):
            a = a * starve
            rate = min(1.0, p["src_rate"] * dt)
            if a > 0.01:
                F += (p["F_src"] * a - F) * m * rate
            if p["O_src"] > 0:
                O += (p["O_src"] - O) * m * rate
            A *= (1 - m * 0.9)
            if a > 0.05:
                np.maximum(th, p["pilot"] * m * (0.8 + 0.4 * (self.noise[0] > 0)), out=th)
            W += (p["w_src"] * a - W) * m * min(1.0, 6.0 * dt)
            tb = p["turb"] * p["w_src"] * 1.2 * dt * 8
            U += tb * self.noise[0] * m
            V += tb * self.noise[1] * m
            W += tb * 0.6 * self.noise[2] * m
        self.A += dt * (self.F > 0.01)

        # forces
        self.w += dt * p["beta"] * self.th
        damp = 1.0 - dt * p["drag"]
        self.u *= damp
        self.v *= damp
        self.w *= damp
        self._vorticity_confinement(dt)
        # sponge on velocity, solid floor
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

        # advect everything
        back, fwd = self._adv_coords(dt)
        nu = self._advect(self.u, back, fwd)
        nv = self._advect(self.v, back, fwd)
        nw = self._advect(self.w, back, fwd)
        self.th = np.maximum(self._advect(self.th, back, fwd), 0)
        self.F = np.maximum(self._advect(self.F, back, fwd), 0)
        self.S = np.maximum(self._advect(self.S, back, fwd), 0)
        self.O = np.clip(self._advect(self.O, back, fwd, mac=False), 0, 1)
        self.P = np.maximum(self._advect(self.P, back, fwd, mac=False), 0)
        self.A = np.maximum(self._advect(self.A, back, fwd, mac=False), 0)
        self.u, self.v, self.w = nu, nv, nw

        # explicit diffusion (mixing at sub-grid scale)
        d = p["diff"]
        for name in ("th", "F", "O", "S"):
            f = getattr(self, name)
            setattr(self, name, (1 - d) * f + d * ndi.uniform_filter(f, 3, mode="nearest"))

        # --- chemistry -----------------------------------------------------------
        F, O, th, S = self.F, self.O, self.th, self.S
        s = p["s"]
        ign = smoothstep(p["t_ign"], p["t_ign"] + 0.12, th)
        lim = np.minimum(F, O / s)
        r = lim * (1.0 - np.exp(-p["k"] * dt)) * ign
        # lean / premixed fraction used for the blue chemiluminescence colour:
        # local equivalence ratio phi = F*s/O ; ~1 or leaner = blue, rich = yellow-sooty
        phi = F * s / (O + 1e-3)
        lean = 1.0 / (1.0 + (np.clip(phi, 0, 20) / 1.6) ** 3)
        self.R = (r / dt).astype(np.float32)
        self.Rb = (r / dt * (0.35 + 0.65 * lean)).astype(np.float32)
        F -= r
        O -= s * r
        self.P += (1.0 + s) * r * 0.5
        th += s * p["theta_ad"] * r

        # soot: inception when fuel-rich, hot, and old enough; oxidised in hot air
        rich = np.clip((phi - 1.0) / 2.0, 0, 1)
        delay = smoothstep(p["delay"][0], p["delay"][1], self.A)
        inc = p["soot_k"] * F * smoothstep(0.30, 0.65, th) * rich * delay * dt
        inc = np.minimum(inc, F * 0.5)
        F -= inc * 0.25
        S += inc
        ox = p["soot_ox"] * S * O * smoothstep(0.55, 0.85, th) * dt
        S -= np.minimum(ox, S)

        # radiative cooling (soot radiates more)
        cool = (p["rad"] + p["rad_soot"] * np.clip(S, 0, 1)) * th ** 3 * dt
        th -= np.minimum(cool, th)
        # slow ambient cooling of warm gas by mixing (so hot plume decays smoothly)
        th *= 1.0 - p.get('mixc', 1.2) * dt

        # water spray: heat sink + steam + oxidiser dilution; mask = broad region over the flames
        if wat > 0:
            zz = self.Zc
            region = np.exp(-(((zz - 3.0 * 0.0) - 0.45 * self.nz * self.dx) / (0.45 * self.nz * self.dx)) ** 2)
            sink = wat * 6.0 * region * dt
            ev = np.minimum(th * sink, 0.4 * th)
            th -= ev
            self.P += ev * 1.6
            S *= 1.0 - 0.8 * wat * region * dt

        # open boundaries: relax toward ambient (also removes smoke at the top)
        k = np.clip(self.sponge * 6.0 * dt, 0, 0.9)
        th *= 1 - k
        F *= 1 - k
        S *= 1 - np.clip(self.sponge * 2.2 * dt, 0, 0.9)
        self.P *= 1 - np.clip(self.sponge * 3.0 * dt + 0.45 * dt, 0, 0.9)  # vapour thins out
        O += (1.0 - O) * k
        np.clip(th, 0, 1.15, out=th)
        self.th, self.F, self.O, self.S = th, np.maximum(F, 0), np.clip(O, 0, 1), np.maximum(S, 0)
        self.t += dt

    def snapshot(self, accum):
        """Mean over the accumulated steps of the render fields, float16."""
        return {k: (v / accum["n"]).astype(np.float16) for k, v in accum.items() if k != "n"}


def run(preset, seed=0, frames=80, fps=24, warm=None, log=print, water=None, grid=GRID):
    """Generator: yields one dict of float16 fields per output frame."""
    sim = Sim(preset, seed, grid, water=water)
    steps_per_frame = int(round(1.0 / (fps * DT)))
    warm = sim.p["warm"] if warm is None else warm
    nwarm = int(warm / DT)
    import time
    t0 = time.time()
    for i in range(nwarm):
        sim.step()
        if i % 40 == 0:
            log(f"[{preset}] warm {i}/{nwarm}  {time.time() - t0:.0f}s  max theta {sim.th.max():.2f}")
    for f in range(frames):
        acc = {"th": 0, "S": 0, "R": 0, "Rb": 0, "P": 0, "n": 0}
        for _ in range(steps_per_frame):
            sim.step()
            acc["th"] = acc["th"] + sim.th
            acc["S"] = acc["S"] + sim.S
            acc["R"] = acc["R"] + sim.R
            acc["Rb"] = acc["Rb"] + sim.Rb
            acc["P"] = acc["P"] + sim.P
            acc["n"] += 1
        if f % 8 == 0:
            log(f"[{preset}] frame {f}/{frames}  {time.time() - t0:.0f}s")
        yield sim.snapshot(acc), sim


if __name__ == "__main__":
    import argparse, time
    ap = argparse.ArgumentParser()
    ap.add_argument("preset", choices=list(PRESETS))
    ap.add_argument("--steps", type=int, default=30)
    a = ap.parse_args()
    sm = Sim(a.preset)
    t0 = time.time()
    for _ in range(a.steps):
        sm.step()
    print(f"{a.steps} steps in {time.time() - t0:.1f}s; max theta {sm.th.max():.2f}, mean soot {sm.S.mean():.4f}")
