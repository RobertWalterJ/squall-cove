"""UI sounds, hold-tool loops and music (pads, tension/storm layers, stingers). Key: D minor pentatonic (D F G A C)."""
import math
import numpy as np
import synthlib as S
import svp_common as C

SR = S.SR
TWO_PI = 2 * math.pi
rng = S.rng
HZ = C.hz


def save(name, x, **kw):
    kw.setdefault('lazy', False); kw.setdefault('group', 'core'); kw.setdefault('max_dist', 0)
    kw.setdefault('weight', 1.0); kw.setdefault('quality', 4)
    bus = kw.pop('bus', 'ui'); sr = kw.pop('sr', SR); circ = kw.pop('circ', False); maxdur = kw.pop('maxdur', None)
    if maxdur:
        x = C.trim(x, maxdur, min(0.2, maxdur * 0.3))
    if sr == 32000:
        x = C.r32_circ(x) if (circ or kw.get('loop')) else C.r32(x)
    if kw.get('loop'):
        x = C.seal(x, 32000 if sr == 32000 else SR)
    return S.save(name, x, bus, sr=sr, **kw)


# ============================================================== UI one-shots
def airy(r, d=0.012, lo=1800, hi=4800, level=0.25):
    return S.lp(C.tick(d, lo, hi, r), 5200, SR, 2) * level


def seq(items, total, tick_level=0.0, seed=1):
    r = rng(seed); y = np.zeros(S.n_of(total))
    for t0, m, d, k, v in items:
        C.place(y, C.soft_note(HZ(m), d, k, v), t0)
        if tick_level:
            C.place(y, airy(r, level=tick_level), t0)
    return S.lp(y, 6500, SR, 2)


def swish(r, d, f0, f1, level=0.25):
    n = S.n_of(d); t = np.arange(n) / SR
    c = f0 * (f1 / f0) ** (t / d)
    x = S.tv_bandpass(S.noise(n, 'white', r), c, 1.4, 2)
    return x * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 1.5 * level


def render_ui():
    U = dict(peak=-10, sr=32000, rate=(0.97, 1.03), tags=['ui'], maxdur=0.7)
    r = rng(3000)
    save('ui_tap', seq([(0, 74, 0.14, 'marimba', 0.9)], 0.16, 0.3, 1), **U)
    save('ui_select', seq([(0, 69, 0.18, 'marimba', 0.8), (0.045, 74, 0.2, 'marimba', 0.9)], 0.28, 0.25, 2), **U)
    save('ui_deselect', seq([(0, 74, 0.16, 'marimba', 0.7), (0.05, 69, 0.2, 'marimba', 0.7)], 0.28, 0.2, 3), **U)
    y = seq([(0, 62, 0.35, 'marimba', 1.0), (0.0, 50, 0.3, 'sine', 0.35)], 0.4, 0.3, 4)
    C.place(y, np.sin(TWO_PI * 130 * np.arange(S.n_of(0.08)) / SR) * S.env_exp(S.n_of(0.08), 0.02) * 0.4, 0.0)
    save('ui_place', y, **U)
    y = swish(r, 0.16, 3800, 800, 0.35)
    y = np.pad(y, (0, S.n_of(0.3))); C.place(y, C.soft_note(HZ(57), 0.3, 'marimba', 0.7), 0.05)
    save('ui_erase', S.lp(y, 6000, SR), **U)
    save('ui_error', seq([(0, 50, 0.2, 'marimba', 0.9), (0.09, 48, 0.28, 'marimba', 0.9)], 0.4, 0.15, 5), **U)
    y = swish(r, 0.18, 800, 3200, 0.25); y = np.pad(y, (0, S.n_of(0.3)))
    C.place(y, C.soft_note(HZ(69), 0.2, 'marimba', 0.7), 0.06); C.place(y, C.soft_note(HZ(74), 0.3, 'marimba', 0.8), 0.14)
    save('ui_open', y, **U)
    y = swish(r, 0.18, 3200, 800, 0.2); y = np.pad(y, (0, S.n_of(0.3)))
    C.place(y, C.soft_note(HZ(74), 0.2, 'marimba', 0.6), 0.0); C.place(y, C.soft_note(HZ(69), 0.3, 'marimba', 0.6), 0.08)
    save('ui_close', y, **U)
    save('ui_tab', seq([(0, 81, 0.08, 'marimba', 0.7)], 0.1, 0.2, 6), **U)
    save('ui_toggle_on', seq([(0, 74, 0.14, 'marimba', 0.8), (0.07, 81, 0.2, 'marimba', 0.9)], 0.3, 0.2, 7), **U)
    save('ui_toggle_off', seq([(0, 69, 0.14, 'marimba', 0.7), (0.07, 65, 0.2, 'marimba', 0.7)], 0.3, 0.15, 8), **U)
    save('ui_slider_tick', seq([(0, 86, 0.04, 'marimba', 0.5)], 0.06, 0.35, 9), peak=-12, sr=32000, rate=(0.8, 1.4), tags=['ui'],
         meta=dict(note='play at rate 0.8-1.4 across the slider range, rate-limit to one per 60 ms'))
    save('ui_toast_info', S.lp(C.echo(seq([(0, 81, 0.6, 'bell', 0.8)], 0.7), 0.8, 0.15, 10, 0.7, 0.5), 5500), **U)
    save('ui_toast_good', S.lp(C.echo(seq([(0, 77, 0.4, 'bell', 0.7), (0.08, 81, 0.4, 'bell', 0.7), (0.16, 86, 0.6, 'bell', 0.8)], 0.8), 0.8, 0.15, 11, 0.7, 0.5), 5500), **U)
    save('ui_toast_warn', S.lp(C.echo(seq([(0, 67, 0.3, 'bell', 0.8), (0.17, 67, 0.4, 'bell', 0.7)], 0.7), 0.8, 0.12, 12, 0.7, 0.5), 5000), **U)
    d = seq([(0, 62, 0.7, 'bell', 0.9), (0.0, 69, 0.7, 'bell', 0.6), (0.2, 62, 0.5, 'bell', 0.5), (0.2, 69, 0.5, 'bell', 0.35)], 0.7)
    save('ui_toast_alert', S.lp(d, 4500), **U)
    y = swish(r, 0.12, 1500, 4500, 0.3); y = np.pad(y, (0, S.n_of(0.3))); C.place(y, C.soft_note(HZ(65), 0.25, 'marimba', 0.6), 0.04)
    save('ui_log_open', y, **U)
    save('ui_try_done', seq([(0, 74, 0.2, 'marimba', 0.8), (0.1, 81, 0.25, 'marimba', 0.8), (0.2, 86, 0.5, 'bell', 0.6)], 0.7, 0.15, 13), **U)
    y = seq([(0, 62, 0.3, 'marimba', 0.7), (0.08, 69, 0.3, 'marimba', 0.7), (0.16, 74, 0.3, 'marimba', 0.7), (0.24, 77, 0.5, 'marimba', 0.75),
             (0.3, 86, 0.7, 'bell', 0.35)], 0.7, 0.1, 14)
    save('ui_new_world', C.echo(y, 1.0, 0.18, 14, 0.7, 0.5)[:S.n_of(0.7)], **U)
    y = np.pad(swish(r, 0.15, 2500, 600, 0.2), (0, S.n_of(0.25)))
    C.place(y, C.soft_note(HZ(74), 0.18, 'marimba', 0.7), 0.0); C.place(y, C.soft_note(HZ(65), 0.25, 'marimba', 0.7), 0.07)
    save('ui_undo', y, **U)


# ============================================================== hold loops
def lgrains(L, rate, fn, r, amp=None):
    n = S.n_of(L); y = np.zeros(n); cnt = r.poisson(rate * L)
    for i, tm in enumerate(r.uniform(0, L, cnt)):
        C.circ_place(y, fn(r, i), tm, 1.0 if amp is None else amp(tm))
    return y


def sinc(f, L, t, ph=0.0):
    return np.sin(TWO_PI * (round(f * L) / L) * t + ph)


def render_holds():
    L = 4.0; n = S.n_of(L); t = np.arange(n) / SR
    def per(freq_cycles, ph=0.0): return 0.5 + 0.5 * np.sin(TWO_PI * freq_cycles * t / L + ph)
    def pn(lo, hi, slope, r): return C.pnoise(n, C.band_shape(lo, hi, slope), r)
    recipes = {}

    def heat(r):
        y = pn(150, 1800, -4, r) * (0.4 + 0.6 * per(1)) * 0.5
        y += 0.5 * sinc(HZ(50), L, t, 0.3) * per(2) + 0.3 * sinc(HZ(57), L, t, 1.0) * per(3, 1)
        y += 0.15 * pn(2500, 6500, -3, r) * per(5, 2) ** 2
        return y
    def cold(r):
        y = pn(2500, 6500, -2, r) * 0.18 * (0.6 + 0.4 * per(1.0, 1))
        y += 0.12 * sinc(HZ(86), L, t, 0.4) * per(2)
        y += lgrains(L, 1.5, lambda rr, i: C.soft_note(HZ(rr.choice([81, 84, 86, 89, 93])), 0.9, 'bell', 0.35), r)
        return y + 0.12 * pn(200, 900, -6, r)
    def water(r):
        y = lgrains(L, 45, lambda rr, i: S.bubble_grain(rr, i, 250, 1600) * 0.7, r)
        return y + pn(300, 2500, -6, r) * 0.25 * (0.6 + 0.4 * per(2, 1))
    def charge(r):
        y = (sinc(120, L, t) + 0.5 * sinc(240, L, t, 1) + 0.3 * sinc(360, L, t, 2)) * 0.5
        y += 0.35 * sinc(121.5, L, t, 0.7) * (0.5 + 0.5 * per(1))
        y += 0.1 * sinc(2000, L, t) * per(3, 0.5) + 0.06 * sinc(3000, L, t, 1) * per(5)
        y += lgrains(L, 9, lambda rr, i: C.tick(0.006, 1800, 6000, rr) * 0.5, r, amp=lambda tm: 0.3 + 0.7 * (0.5 + 0.5 * math.sin(TWO_PI * tm / L)))
        return y
    def electricity(r):
        y = sum((1.0 / h) * sinc(100 * h, L, t, h) for h in range(1, 10)) * 0.5
        y = S.lp(y, 1400, SR, 2)
        y += lgrains(L, 28, lambda rr, i: C.tick(0.008, 1500, 6000, rr) * rr.uniform(0.2, 0.9) * 0.5, r)
        return y + 0.06 * pn(2000, 6000, 0, r) * per(7, 1)
    def fire(r):
        y = lgrains(L, 55, lambda rr, i: C.tick(0.012, 500, 4200, rr) * rr.uniform(0.2, 1.0) * 0.7, r)
        flick = 0.6 + 0.2 * np.sin(TWO_PI * 3 * t / L + 1) + 0.2 * np.sin(TWO_PI * 7 * t / L + 2)
        return y + pn(60, 700, -6, r) * 0.45 * flick
    def lava(r):
        y = lgrains(L, 5, lambda rr, i: S.bubble_grain(rr, i, 70, 320) * 2.0, r)
        y += pn(40, 300, -3, r) * 0.45 * (0.7 + 0.3 * per(2))
        return y + 0.05 * pn(1500, 4500, -3, r)
    def sand(r):
        y = lgrains(L, 160, lambda rr, i: C.tick(0.007, 1500, 6000, rr) * rr.uniform(0.2, 0.8) * 0.5, r)
        return y + pn(1500, 6000, -3, r) * 0.18
    def earth(r):
        y = lgrains(L, 28, lambda rr, i: S.lp(rr.standard_normal(int(0.03 * SR)), 900, SR) * np.exp(-np.arange(int(0.03 * SR)) / (0.008 * SR)) * rr.uniform(0.3, 1.0) * 1.5, r)
        return y + pn(80, 900, -5, r) * 0.3
    def rock(r):
        y = lgrains(L, 12, lambda rr, i: S.modal(rr.uniform(900, 2600), 'stone', 0.1, 0.3, r=rr) * 0.5 + C.fit(C.tick(0.004, 1500, 5000, rr) * 0.4, S.n_of(0.1)), r)
        return y + pn(300, 2500, -6, r) * 0.08
    def metal(r):
        y = lgrains(L, 9, lambda rr, i: S.modal(rr.uniform(2000, 5000), 'steel', 0.25, 0.06, r=rr) * 0.4, r)
        return y + 0.07 * sinc(HZ(62), L, t, 1) * per(1) + pn(500, 3000, -6, r) * 0.05
    def seed(r):
        y = lgrains(L, 30, lambda rr, i: C.tick(0.006, 2000, 5500, rr) * rr.uniform(0.2, 0.8) * 0.5, r)
        y += lgrains(L, 1.0, lambda rr, i: C.soft_note(HZ(rr.choice([74, 77, 79, 81, 84])), 0.5, 'marimba', 0.25), r)
        return y + pn(1000, 4500, -4, r) * 0.05

    for i, (name, fn) in enumerate([('heat', heat), ('cold', cold), ('water', water), ('lightning_charge', charge), ('electricity', electricity),
                                    ('fire', fire), ('lava', lava), ('sand', sand), ('earth', earth), ('rock', rock), ('metal', metal), ('seed', seed)]):
        y = S.lp(fn(rng(3100 + i)), 7000, SR, 2)
        save('hold_' + name, y, loop=True, target_lufs=-30, peak=-12, rate=(0.97, 1.03), tags=['hold'], quality=3, sr=32000, circ=True,
             meta=dict(tool=name, note='start on press, fade out on release (80 ms); level can follow tool strength'))


# ============================================================== music
L_M = 40.0


class Pad:
    def __init__(self, seed):
        self.r = rng(seed); self.n = S.n_of(L_M); self.t = np.arange(self.n) / SR
        self.out = np.zeros((self.n, 2))

    def env(self, m, ph, floor=0.15):
        return floor + (1 - floor) * (0.5 - 0.5 * np.cos(TWO_PI * (m * self.t / L_M + ph)))

    def voice(self, midi, amp, pan=0.0, m=1, ph=0.0, floor=0.15, partials=(), pen=None, det=(0.0, 0.075, -0.1)):
        f0 = HZ(midi); e = self.env(m, ph, floor) * amp
        gl = math.cos((pan + 1) * math.pi / 4); gr = math.sin((pan + 1) * math.pi / 4)
        for ch, g in ((0, gl), (1, gr)):
            y = np.zeros(self.n)
            for d in det:
                f = round((f0 + d) * L_M) / L_M
                y += np.sin(TWO_PI * f * self.t + self.r.uniform(0, 6.28)) * (1.0 if d == 0 else 0.7)
            for k, (h, pa) in enumerate(partials):
                f = round(f0 * h * L_M) / L_M
                y += pa * (pen if pen is not None else 1.0) * np.sin(TWO_PI * f * self.t + self.r.uniform(0, 6.28))
            self.out[:, ch] += y * e * g

    def noise(self, lo, hi, slope, amp, env=None, shape=None):
        for ch in range(2):
            x = C.pnoise(self.n, C.band_shape(lo, hi, slope), self.r)
            if env is not None: x = x * env
            self.out[:, ch] += x * amp

    def event(self, x, t0, amp=1.0, pan=0.0):
        gl = math.cos((pan + 1) * math.pi / 4); gr = math.sin((pan + 1) * math.pi / 4)
        C.circ_place(self.out[:, 0], x, t0, amp * gl); C.circ_place(self.out[:, 1], x, t0, amp * gr)

    def finish(self, name, rt=4.0, wet=0.35, lufs=-28.0, lp=8000, meta=None, peak=-6):
        y = C.circ_reverb(self.out, rt, wet, 5)
        y = np.stack([S.lp(y[:, c], lp, SR, 2) for c in range(2)], axis=1)
        pk = np.max(np.abs(y)); y = y / (pk + 1e-9) * 0.5
        save(name, y, bus='mus', loop=True, target_lufs=lufs, peak=peak, lazy=True, group='music', weight=1.0, sr=32000, circ=True,
             quality=3, rate=(1.0, 1.0), tags=['music'], meta=meta)


def swell(f, dur, att, tau, sr=SR):
    n = S.n_of(dur); t = np.arange(n) / sr
    return np.sin(TWO_PI * f * t) * np.minimum(1, t / att) ** 2 * np.exp(-t / tau)


def render_pads():
    # dawn: open fifths, brightness swell
    p = Pad(4000); b = p.env(1, -0.15, 0.1)
    p0 = [(2, 0.4), (3, 0.2)]
    for midi, pan, m, ph, a in [(50, -0.3, 1, 0.0, 1.0), (57, 0.3, 2, 0.3, 0.9), (62, -0.5, 1, 0.5, 0.7), (69, 0.5, 3, 0.1, 0.55), (74, 0.0, 2, 0.7, 0.35)]:
        p.voice(midi, a * 0.5, pan, m, ph, 0.25, partials=p0, pen=1.0)
    p.noise(1200, 7000, -3, 0.06, env=b ** 1.5)
    p.noise(120, 900, -4, 0.08, env=p.env(1, 0.4, 0.5))
    p.finish('mus_pad_dawn', 4.5, 0.4, meta=dict(time='dawn', chord='D A D A D open fifths', note='crossfade 6-10 s between pads on time of day'))

    # day: major pentatonic, warm and sparse
    p = Pad(4010)
    for midi, pan, m, ph, a in [(50, -0.2, 1, 0.0, 1.0), (57, 0.2, 1, 0.5, 0.7), (54, 0.0, 2, 0.25, 0.35)]:
        p.voice(midi, a * 0.5, pan, m, ph, 0.5, partials=[(2, 0.25)])
    for k, (tm, midi, pan) in enumerate([(2.0, 69, -0.3), (7.5, 71, 0.4), (12.0, 66, -0.1), (17.0, 74, 0.3), (23.0, 64, -0.4), (28.5, 69, 0.2),
                                         (33.0, 71, -0.2), (37.0, 74, 0.5)]):
        p.event(swell(HZ(midi), 6.0, 0.35, 1.6), tm, 0.22, pan)
    p.noise(300, 3500, -6, 0.04, env=p.env(2, 0.1, 0.4))
    p.finish('mus_pad_day', 3.5, 0.35, meta=dict(time='day', chord='D major pentatonic', note='sparse, warm'))

    # dusk: suspended, mellow
    p = Pad(4020)
    for midi, pan, m, ph, a in [(50, -0.3, 1, 0.0, 1.0), (55, 0.3, 1, 0.33, 0.8), (57, -0.1, 2, 0.6, 0.7), (62, 0.4, 1, 0.8, 0.5), (60, -0.4, 1, 0.15, 0.45)]:
        p.voice(midi, a * 0.5, pan, m, ph, 0.2, partials=[(2, 0.2)], det=(0.0, 0.1, -0.075))
    trem = 0.85 + 0.15 * np.sin(TWO_PI * 8 * p.t / L_M)
    p.out *= trem[:, None]
    p.noise(150, 1400, -5, 0.07, env=p.env(1, 0.6, 0.4))
    p.finish('mus_pad_dusk', 4.5, 0.4, lp=5000, meta=dict(time='dusk', chord='D sus4 add C', note='mellow'))

    # night: low, dark, sparse bells
    p = Pad(4030)
    for midi, pan, m, ph, a in [(38, -0.2, 1, 0.0, 1.0), (45, 0.2, 1, 0.5, 0.8), (50, 0.0, 2, 0.2, 0.35)]:
        p.voice(midi, a * 0.5, pan, m, ph, 0.4, det=(0.0, 0.05, -0.075))
    for tm, midi, pan, v in [(4.0, 74, -0.4, 0.5), (13.0, 69, 0.5, 0.4), (21.5, 77, -0.2, 0.35), (30.0, 72, 0.3, 0.45)]:
        p.event(C.soft_note(HZ(midi), 8.0, 'bell', v, decay=2.0), tm, 0.16, pan)
    p.noise(60, 500, -6, 0.04, env=p.env(1, 0.3, 0.5))
    p.finish('mus_pad_night', 6.0, 0.5, lp=3500, lufs=-30, meta=dict(time='night', note='very low, dark, sparse bells'))


def tom(f0, dur, r):
    n = S.n_of(dur); t = np.arange(n) / SR
    f = f0 * (1 + 0.7 * np.exp(-t / 0.05))
    y = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.35)
    y += 0.5 * S.lp(S.noise(n, 'white', r), 400, SR, 2) * np.exp(-t / 0.04)
    return y


def render_layers():
    # tension layer: low pulsing drone + dissonant cluster
    p = Pad(4100)
    pulse = (0.5 + 0.5 * np.sin(TWO_PI * 50 * p.t / L_M)) ** 2
    for midi, a, pan in [(26, 1.0, 0.0), (38, 0.7, 0.0)]:
        p.voice(midi, a * 0.5, pan, 1, 0.0, 0.7, det=(0.0, 0.05))
    p.out *= (0.45 + 0.55 * pulse)[:, None]
    for midi, pan, m, ph in [(57, -0.5, 1, 0.0), (58, 0.5, 2, 0.4), (59, 0.0, 1, 0.7)]:
        p.voice(midi, 0.045, pan, m, ph, 0.1, det=(0.0, 0.1))
    p.noise(80, 600, -4, 0.04, env=p.env(3, 0.2, 0.3))
    y = C.circ_reverb(p.out, 3.0, 0.3, 5)
    y = np.stack([S.lp(y[:, c], 2500, SR, 2) for c in range(2)], axis=1)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.5
    save('mus_tension_layer', y, bus='mus', loop=True, target_lufs=-30, peak=-6, lazy=True, group='music', sr=32000, circ=True, quality=3, rate=(1.0, 1.0),
         tags=['music'], meta=dict(note='mix over a pad as threats rise; pulse 1.25 Hz'))

    # storm layer: rolling toms
    p = Pad(4110); r = p.r
    for midi, a in [(26, 1.0), (33, 0.5)]:
        p.voice(midi, a * 0.4, 0.0, 1, 0.0, 0.7, det=(0.0, 0.05))
    p.voice(51, 0.04, -0.4, 1, 0.1, 0.2, det=(0.0, 0.1)); p.voice(57, 0.04, 0.4, 2, 0.5, 0.2, det=(0.0, 0.1))
    for start in [1.0, 6.5, 12.0, 17.5, 23.0, 28.5, 34.0]:
        cnt = int(r.integers(6, 11)); tm = start; gap = 0.22
        f0 = r.uniform(70, 105)
        for j in range(cnt):
            p.event(tom(f0 * (1 + 0.04 * (j % 3)), 1.2, r), tm, 0.25 * (0.6 + 0.4 * math.sin(math.pi * j / cnt)), r.uniform(-0.5, 0.5))
            tm += gap; gap *= 0.88
        p.event(tom(f0 * 0.8, 2.0, r), tm + 0.05, 0.42, 0.0)
    p.noise(100, 1200, -6, 0.1, env=p.env(3, 0.1, 0.3))
    y = C.circ_reverb(p.out, 3.5, 0.3, 6)
    y = np.stack([S.lp(y[:, c], 3000, SR, 2) for c in range(2)], axis=1)
    y = y / (np.max(np.abs(y)) + 1e-9) * 0.5
    save('mus_storm_layer', y, bus='mus', loop=True, target_lufs=-30, peak=-6, lazy=True, group='music', sr=32000, circ=True, quality=3, rate=(1.0, 1.0),
         tags=['music'], meta=dict(note='mix over a pad in storms; tie level to wind/rain'))


def sting_stereo(x, rt=1.6, wet=0.3, seed=40, total=3.5):
    ir = S.reverb_ir(rt, 0.7, 0.7, SR, seed, 0.015, stereo=True)
    return C.trim(S.convolve(x, ir, wet), total, 0.8)


def render_stings():
    M = dict(bus='mus', lazy=True, group='music', peak=-6, sr=32000, weight=1.0, rate=(1.0, 1.0), tags=['sting'], quality=4)

    def sq(items, total):
        y = np.zeros(S.n_of(total))
        for t0, m, d, k, v in items: C.place(y, C.soft_note(HZ(m), d, k, v), t0)
        return y
    y = sq([(0, 77, 1.8, 'bell', 0.7), (0.16, 81, 1.8, 'bell', 0.7), (0.32, 86, 2.4, 'bell', 0.8), (0.32, 74, 2.4, 'bell', 0.35)], 2.8)
    sh = S.hp(S.noise(S.n_of(2.8), 'white', rng(41)), 3000, SR) * np.exp(-np.arange(S.n_of(2.8)) / (0.5 * SR)) * 0.02
    save('mus_sting_discovery', sting_stereo(S.lp(y + sh, 7000, SR, 2), 2.0, 0.35, 41, 3.2), **M)
    y = sq([(0, 62, 0.5, 'marimba', 0.8), (0.18, 69, 0.5, 'marimba', 0.8), (0.36, 74, 0.5, 'marimba', 0.8), (0.54, 77, 0.6, 'marimba', 0.8),
            (0.8, 74, 2.4, 'bell', 0.7), (0.8, 77, 2.4, 'bell', 0.6), (0.8, 81, 2.4, 'bell', 0.55), (0.8, 84, 2.4, 'bell', 0.35), (0.8, 50, 2.4, 'tri', 0.3)], 3.4)
    save('mus_sting_success', sting_stereo(y, 2.0, 0.3, 42, 3.8), **M)
    y = sq([(0, 62, 0.8, 'tri', 0.8), (0.5, 57, 0.8, 'tri', 0.8), (1.0, 53, 0.9, 'tri', 0.8), (1.5, 50, 1.8, 'tri', 0.9), (1.5, 38, 2.0, 'bell', 0.7), (1.5, 45, 2.0, 'bell', 0.35)], 3.6)
    save('mus_sting_loss', sting_stereo(y, 2.5, 0.35, 43, 4.0), **M)
    n = S.n_of(3.6); t = np.arange(n) / SR
    pad = sum(swell(HZ(m), 3.6, 0.9, 1.4) * a for m, a in [(57, 0.6), (62, 0.8), (65, 0.5)])
    y = pad * 0.5 + sq([(0.9, 69, 1.6, 'bell', 0.8), (1.15, 74, 2.2, 'bell', 0.8)], 3.6)
    save('mus_sting_arrival', sting_stereo(y, 2.2, 0.35, 44, 3.8), **M)


def render():
    S.set_manifest('ui_music')
    render_ui()
    render_holds()
    render_pads()
    render_layers()
    render_stings()


if __name__ == '__main__':
    render()
