"""People: footsteps, non-verbal voices, work/action sounds and NPC-engine cues."""
import math
import numpy as np
import synthlib as S
import svp_common as C

SR = S.SR
TWO_PI = 2 * math.pi
rng = S.rng
HZ = C.hz


def save(name, x, **kw):
    kw.setdefault('lazy', True); kw.setdefault('group', 'people'); kw.setdefault('max_dist', 40)
    kw.setdefault('weight', 1.0); kw.setdefault('quality', 4)
    bus = kw.pop('bus', 'ppl'); sr = kw.pop('sr', SR)
    if sr == 32000:
        x = C.r32_circ(x) if kw.get('loop') else C.r32(x)
    if kw.get('loop'):
        x = C.seal(x)
    return S.save(name, x, bus, sr=sr, **kw)


def fam(prefix, count, maker, **kw):
    tags = kw.pop('tags', [prefix])
    for i in range(count):
        save('%s_%02d' % (prefix, i + 1), maker(i), variants=count, tags=tags, **kw)


# ============================================================== footsteps
def _thud(n, f, tau, level, r):
    t = np.arange(n) / SR
    return np.sin(TWO_PI * f * t * (1 - 0.3 * np.exp(-t / 0.02))) * np.exp(-t / tau) * level


def tap_sand(r, s):
    n = S.n_of(0.2)
    x = S.bp(S.noise(n, 'white', r), 400, 2800, SR, 2) * S.env_exp(n, 0.045) * S.env_attack(n, 0.008)
    g = S.grains(0.12, lambda t: 260 * math.exp(-t * 8), lambda rr, i: C.tick(0.006, 1200, 4200, rr) * rr.uniform(0.2, 0.8), r)
    y = x * 0.8 + C.fit(g, n) * 0.9 + _thud(n, 90, 0.04, 0.35, r)
    return y * s


def tap_grass(r, s):
    n = S.n_of(0.25)
    x = S.bp(S.noise(n, 'white', r), 500, 2400, SR, 2) * S.env_exp(n, 0.07) * S.env_attack(n, 0.03)
    return (x * 0.6 + _thud(n, 80, 0.05, 0.45, r) + 0.1 * S.lp(S.noise(n, 'pink', r), 600, SR) * S.env_exp(n, 0.1)) * s


def tap_gravel(r, s):
    n = S.n_of(0.25)
    g = S.grains(0.2, lambda t: 650 * math.exp(-t * 7) + 60, lambda rr, i: C.tick(0.009, 1000, 6000, rr) * rr.uniform(0.3, 1.0), r)
    return (C.fit(g, n) * 1.0 + _thud(n, 110, 0.04, 0.4, r)) * s


def tap_wood(r, s):
    f0 = r.uniform(130, 190)
    y = S.impact('plank', f0, 0.8, 0.35, 0.35, seed=int(r.integers(1e6)), thump=0.5)
    n = len(y)
    y += 0.4 * S.modal(f0 * 2.7, 'wood', 0.35, 0.5, r=r)
    return y * s


def tap_rock(r, s):
    n = S.n_of(0.15)
    y = S.modal(r.uniform(1300, 2000), 'stone', 0.15, 0.5, bright=1.2, r=r) * 0.5
    tr = S.hp(S.noise(n, 'white', r), 3000, SR, 3) * S.env_exp(n, 0.004)
    return (y + tr * 0.9 + _thud(n, 130, 0.015, 0.4, r)) * s


def tap_water(r, s):
    n = S.n_of(0.35)
    sp = S.lp(S.noise(n, 'white', r), 2800, SR) * S.env_exp(n, 0.06) * S.env_attack(n, 0.004)
    b = S.grains(0.3, lambda t: 220 * math.exp(-t * 6), lambda rr, i: S.bubble_grain(rr, i, 250, 2400), r)
    return (sp * 0.7 + C.fit(b, n) * 0.9 + _thud(n, 70, 0.06, 0.5, r)) * s


def tap_snow(r, s):
    n = S.n_of(0.25)
    g = S.grains(0.18, lambda t: 380 * math.exp(-t * 7) + 30, lambda rr, i: C.tick(0.006, 2500, 7000, rr) * rr.uniform(0.2, 0.8), r)
    t = np.arange(n) / SR
    f = r.uniform(2400, 3300) * (1 + 0.08 * t / 0.1)
    sq = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.05) * 0.16 * (1 if r.random() < 0.6 else 0.3)
    return (C.fit(g, n) + sq + _thud(n, 85, 0.035, 0.3, r)) * s


def tap_deck(r, s):
    n = S.n_of(0.4)
    y = S.impact('iron', r.uniform(250, 360), 0.4, 0.6, 0.4, seed=int(r.integers(1e6)), thump=0.7)
    return y * s


def tap_metal(r, s):
    y = S.impact('steel', r.uniform(500, 700), 0.35, 0.85, 0.55, seed=int(r.integers(1e6)), thump=0.25)
    return y * s


SURF = [('sand', tap_sand), ('grass', tap_grass), ('gravel', tap_gravel), ('wood', tap_wood), ('rock', tap_rock),
        ('water', tap_water), ('snow', tap_snow), ('deck', tap_deck), ('metal', tap_metal)]


def render_steps():
    for si, (name, fn) in enumerate(SURF):
        def mk(i, fn=fn, si=si):
            r = rng(2000 + si * 20 + i)
            n = S.n_of(0.55); y = np.zeros(n)
            gap = r.uniform(0.04, 0.09)
            C.place(y, fn(r, 1.0), 0.0)
            C.place(y, fn(r, r.uniform(0.55, 0.8)), gap)
            return S.hp(y, 40, SR, 1)
        for i in range(8):
            save('ppl_step_%s_%02d' % (name, i + 1), mk(i), group='core', lazy=False, max_dist=25, weight=1.0, variants=8,
                 rate=(0.92, 1.08), peak=-6, sr=32000, tags=['step', name], meta=dict(surface=name))


# ============================================================== voices
def breath_sound(r):
    n = S.n_of(1.6); t = np.arange(n) / SR
    x = S.noise(n, 'white', r)
    ins = np.exp(-((t - 0.38) / 0.2) ** 2) * 0.7
    exh = np.exp(-((t - 1.05) / 0.25) ** 2)
    env = ins + exh
    F = 1500 + 400 * (t < 0.7) - 250 * (t >= 0.7)
    y = C.tv_res(x, F, 1.6) + 0.7 * C.tv_res(x, 550, 2) + 0.4 * C.tv_res(x, 2600, 2)
    return S.lp(y, 5000, SR, 2) * env


def grunt(i):
    r = rng(2100 + i); dur = 0.28 + 0.03 * i; n = S.n_of(dur); t = np.arange(n) / SR
    f0 = (120 + 14 * i) * (1.0 - 0.28 * t / dur)
    vw = [('uh', 'a'), ('uh', 'o'), ('uh', 'er'), ('a', 'uh')][i]
    F = [np.interp(t, [0, dur], [VW[0], VW[1]]) for VW in zip(C.VOW[vw[0]], C.VOW[vw[1]])]
    env = np.minimum(1, t / 0.02) * np.exp(-t / (dur * 0.5))
    y = C.vocal(f0, dur, F, r, breath=0.35, tilt=1.3, env=env)
    hf = S.hp(S.noise(n, 'white', r), 400, SR) * np.exp(-t / 0.03) * 0.15
    return S.lp(y + hf * np.std(y), 4500, SR, 2)


def shout_boat(i):
    r = rng(2110 + i); dur = 0.95; n = S.n_of(dur); t = np.arange(n) / SR
    base = [170, 185, 160][i]
    f0 = base * (1 + 0.32 * np.clip(t / 0.7, 0, 1) ** 1.2 - 0.12 * np.clip((t - 0.75) / 0.2, 0, 1))
    key = [0, 0.15, 0.55, 0.8, dur]
    F1 = np.interp(t, key, [450, 520, 760, 800, 620]); F2 = np.interp(t, key, [900, 1000, 1250, 1400, 1250])
    F3 = np.interp(t, key, [2400, 2400, 2450, 2500, 2400])
    env = np.minimum(1, t / 0.05) ** 1.2 * np.exp(-np.maximum(0, t - 0.6) / 0.14)
    y = C.vocal(f0, dur, [F1, F2, F3], r, breath=0.12, tilt=1.2, env=env)
    return C.echo(y, 1.3, 0.22, 2115 + i, 0.8, 1.0)


def shout_help(i):
    r = rng(2120 + i); dur = 0.9; n = S.n_of(dur); t = np.arange(n) / SR
    base = [165, 180, 150][i]
    f0 = np.interp(t, [0, 0.2, 0.3, 0.5, 0.9], [base, base * 1.15, base * 1.05, base * 1.2, base * 0.95])
    key = [0, 0.18, 0.3, 0.45, 0.7, dur]
    F1 = np.interp(t, key, [530, 540, 600, 720, 700, 480]); F2 = np.interp(t, key, [1800, 1840, 1500, 1200, 1100, 1000])
    F3 = np.interp(t, key, [2500, 2500, 2450, 2400, 2400, 2300])
    gate = np.where((t > 0.22) & (t < 0.3), 0.15, 1.0)
    env = np.minimum(1, t / 0.04) * gate * np.exp(-np.maximum(0, t - 0.65) / 0.1)
    y = C.vocal(f0, dur, [F1, F2, F3], r, breath=0.2, tilt=1.25, env=env)
    return C.echo(y, 1.0, 0.18, 2125 + i, 0.8, 0.9)


def whistle(i):
    r = rng(2130 + i); dur = [0.55, 0.75, 0.9][i]; n = S.n_of(dur); t = np.arange(n) / SR
    f = (2850 + 80 * i) * (1 - 0.02 * t / dur) + 120 * np.exp(-((t - dur * 0.85) / 0.05) ** 2) * (i == 2)
    ph = TWO_PI * np.cumsum(f) / SR
    trill = 1 - 0.5 * (0.5 + 0.5 * np.sin(TWO_PI * (34 + 3 * i) * t))
    y = (np.sin(ph) + 0.12 * np.sin(2 * ph)) * trill
    y += 0.12 * S.bp(S.noise(n, 'white', r), 2400, 3600, SR, 2)
    env = np.minimum(1, t / 0.025) * np.minimum(1, (dur - t) / 0.06)
    return y * env


def laugh(i):
    r = rng(2140 + i); n = S.n_of(1.1); y = np.zeros(n)
    base = [190, 215, 170][i]; cnt = 4 + (i == 1)
    t0 = 0.03
    for j in range(cnt):
        d = 0.11 + 0.01 * r.random()
        s = C.syllable(base * (1 - 0.05 * j) * r.uniform(0.97, 1.03), d, 'a', r, breath=0.3, glide=-0.1)
        C.place(y, s, t0, 0.8 * (0.88 ** j))
        t0 += d + r.uniform(0.07, 0.11) + 0.012 * j
    return S.lp(y, 4500, SR, 2)


def cough(i):
    r = rng(2150 + i); n = S.n_of(0.9); y = np.zeros(n)
    t0 = 0.02
    for j in range(2 + (i == 2)):
        d = 0.16 - 0.02 * j; m = S.n_of(d); t = np.arange(m) / SR
        f0 = (130 + 15 * i) * (1 - 0.3 * t / d)
        v = C.glottal(f0, m, r, 1.0, jitter=0.03)
        ex = v + 0.8 * S.noise(m, 'white', r)
        F = [np.interp(t, [0, d], [560, 700]), np.interp(t, [0, d], [1500, 1250]), 2500]
        y_ = sum(a * C.tv_res(ex, f, f_ / b) for a, f, f_, b in zip(C.FAMP, F, [np.mean(F[0]), np.mean(F[1]), 2500], C.BW))
        y_ = y_ * np.minimum(1, t / 0.008) * np.exp(-t / (d * 0.4))
        C.place(y, y_, t0, 1.0 - 0.25 * j)
        t0 += d + r.uniform(0.12, 0.2)
    return S.lp(y, 5000, SR, 2)


def shiver():
    r = rng(2160); L = 2.4; k = int(0.3 * SR); n = S.n_of(L) + k; t = np.arange(n) / SR
    am_f = round(9.0 * L) / L
    am = (0.5 + 0.5 * np.sin(TWO_PI * am_f * t + 0.3 * np.sin(TWO_PI * 2 * t / L))) ** 2
    x = S.noise(n, 'white', r)
    y = C.tv_res(x, 700, 2.0) + 0.8 * C.tv_res(x, 1600, 2.5) + 0.4 * C.tv_res(x, 2600, 3)
    v = C.glottal(125 + 10 * np.sin(TWO_PI * t / L), n, r, 1.5)
    v = C.tv_res(v, 600, 6) + 0.5 * C.tv_res(v, 1150, 8)
    y = (y * 0.8 + v * 0.35 * np.std(y) / (np.std(v) + 1e-9)) * am * (0.7 + 0.3 * S.smooth_random(n, 1.2, r, 1.0))
    return S.make_loop(S.lp(y, 5000, SR, 2), 0.3)


def murmur(L, rate, seed, speakers):
    r = rng(seed); xf = 0.8; n = S.n_of(L + xf); y = np.zeros(n)
    base = r.uniform(95, 230, speakers)
    vows = list(C.VOW.keys())
    t = 0.0
    sp_env = [S.smooth_random(n, 0.35, r, 1.0) for _ in range(speakers)]
    while t < L + xf - 0.3:
        t += r.exponential(1.0 / rate)
        sp = int(r.integers(speakers))
        d = r.uniform(0.07, 0.2)
        f0 = base[sp] * r.uniform(0.85, 1.25)
        s = C.syllable(f0, d, vows[int(r.integers(len(vows)))], r, breath=0.12, glide=r.uniform(-0.12, 0.1))
        idx = min(n - 1, int(t * SR))
        C.place(y, s, t, r.uniform(0.35, 1.0) * (0.15 + sp_env[sp][idx]))
    y = S.hp(S.lp(y, 3300, SR, 2), 170, SR, 2)
    y = y + 0.05 * np.std(y) * S.lp(S.noise(n, 'pink', r), 800, SR)
    return S.make_loop(y, xf)


def radio_squelch_one(r, d=0.3):
    n = S.n_of(d); t = np.arange(n) / SR
    x = S.bp(S.noise(n, 'white', r), 600, 3400, SR, 2)
    return S.soft_clip(x * 2, 1.5) * (np.exp(-t / (d * 0.28)) * np.minimum(1, t / 0.002)) * 0.9


def radio_click_one(r):
    n = S.n_of(0.1); t = np.arange(n) / SR
    c = S.bp(S.noise(n, 'white', r) * np.exp(-t / 0.002), 800, 4500, SR, 1) * 1.2
    c += 0.5 * np.sin(TWO_PI * r.uniform(1100, 1500) * t) * np.exp(-t / 0.006)
    return c


def radio_chatter():
    r = rng(2170); L = 12.0; xf = 0.8; n = S.n_of(L + xf); y = np.zeros(n); t = 0.2
    vows = ['a', 'e', 'i', 'o', 'u', 'ae', 'uh', 'er']
    while t < L + xf - 1.0:
        talk = r.uniform(1.2, 3.2); f_base = r.choice([105, 120, 190, 210]) * r.uniform(0.95, 1.05)
        C.place(y, radio_click_one(r), t, 0.7)
        tt = t + 0.12
        while tt < t + talk:
            for _ in range(int(r.integers(2, 5))):
                d = r.uniform(0.07, 0.17)
                s = C.syllable(f_base * r.uniform(0.85, 1.3), d, vows[int(r.integers(len(vows)))], r, breath=0.1, glide=r.uniform(-0.1, 0.1))
                C.place(y, s, tt, r.uniform(0.6, 1.0)); tt += d * r.uniform(0.9, 1.1)
            tt += r.uniform(0.05, 0.25)
        C.place(y, radio_squelch_one(r, 0.22), tt, 0.5)
        t = tt + r.uniform(0.7, 2.2)
    y = S.bp(S.soft_clip(y / (np.max(np.abs(y)) + 1e-9), 2.5), 300, 3000, SR, 2)
    st = S.hp(S.noise(n, 'white', r), 1200, SR) * 0.06 * np.std(y) * (0.6 + 0.4 * S.smooth_random(n, 6, r, 1.0))
    cr = S.grains(n / SR, lambda tt_: 6, lambda rr, i: C.tick(0.003, 1000, 5000, rr) * rr.uniform(0.2, 0.8), r) * np.std(y) * 1.2
    y = S.bp(y + st * 3 + cr, 300, 3000, SR, 2)
    return S.make_loop(y, xf)


# ============================================================== actions
def camera_shutter(i):
    r = rng(2200 + i); n = S.n_of(0.25); y = np.zeros(n)
    c1 = C.tick(0.006, 1800, 6000, r) * 1.0
    C.place(y, c1, 0.0, 1.0)
    C.place(y, S.modal(r.uniform(1400, 1900), 'plastic', 0.06, 0.8, r=r), 0.0, 0.3)
    g = r.uniform(0.045, 0.07)
    C.place(y, C.tick(0.008, 1000, 4500, r), g, 0.8)
    C.place(y, S.modal(r.uniform(900, 1300), 'plastic', 0.07, 0.8, r=r), g, 0.3)
    C.place(y, _thud(S.n_of(0.04), 160, 0.01, 0.4, r), g, 1.0)
    return y


def shovel(i):
    r = rng(2210 + i); n = S.n_of(0.8); t = np.arange(n) / SR; y = np.zeros(n)
    g = S.grains(0.3, lambda tt: 160, lambda rr, k: C.tick(0.008, 700, 4000, rr) * rr.uniform(0.2, 0.9), r)
    sc = S.tv_bandpass(S.noise(n, 'white', r), 800 + 1200 * np.clip(t / 0.3, 0, 1), 2.0, 2)[:S.n_of(0.3)] * np.sin(np.pi * np.linspace(0, 1, S.n_of(0.3))) ** 1.2
    C.place(y, sc, 0.0, 0.7); C.place(y, g, 0.0, 0.8)
    t1 = 0.3 + 0.03 * i
    C.place(y, S.modal(r.uniform(650, 900), 'steel', 0.1, 0.15, r=r), t1, 0.3)
    C.place(y, _thud(S.n_of(0.2), 85, 0.05, 1.0, r), t1, 0.9)
    C.place(y, S.lp(S.noise(S.n_of(0.3), 'white', r), 1800, SR) * S.env_exp(S.n_of(0.3), 0.07), t1 + 0.05, 0.5)
    return y


def hammer(i):
    r = rng(2220 + i); n = S.n_of(0.6); y = np.zeros(n)
    t0 = 0.0
    for j in range(2):
        a = S.impact('wood', r.uniform(650, 950), 0.25, 0.8, 0.15, seed=2220 + i * 3 + j) * 0.8
        b = S.modal(r.uniform(2100, 3000), 'steel', 0.15, 0.1, r=r) * 0.35
        C.place(y, a, t0, 1.0 - 0.15 * j); C.place(y, b, t0, 0.7)
        t0 += r.uniform(0.16, 0.22)
    return y


def stone_place(i):
    r = rng(2230 + i); n = S.n_of(1.0); y = np.zeros(n)
    sc = S.tv_bandpass(S.noise(S.n_of(0.22), 'white', r), 1200 + 800 * np.linspace(0, 1, S.n_of(0.22)), 1.8, 2)
    sc *= np.sin(np.pi * np.linspace(0, 1, S.n_of(0.22))) ** 1.5
    C.place(y, sc, 0.0, 0.5)
    t1 = 0.18 + 0.02 * i
    C.place(y, S.impact('stone', r.uniform(320, 520), 1.6, 0.5, 0.7, seed=2230 + i, thump=1.6), t1, 1.0)
    return y


def axe(i):
    r = rng(2240 + i); n = S.n_of(0.9); y = np.zeros(n)
    sw = S.tv_bandpass(S.noise(S.n_of(0.2), 'white', r), 400 + 1600 * np.linspace(0, 1, S.n_of(0.2)), 1.6, 2)
    sw *= np.sin(np.pi * np.linspace(0, 1, S.n_of(0.2))) ** 1.5
    C.place(y, sw, 0.0, 0.35)
    t1 = 0.2
    C.place(y, S.impact('wood', r.uniform(160, 260), 1.2, 0.7, 0.6, seed=2240 + i, thump=1.0), t1, 1.0)
    C.place(y, S.bp(S.noise(S.n_of(0.1), 'white', r), 600, 3500, SR, 1) * S.env_exp(S.n_of(0.1), 0.012), t1, 0.6)
    return y


def pat(i):
    r = rng(2250 + i); n = S.n_of(0.7); y = np.zeros(n); t0 = 0.0
    for j in range(int(r.integers(2, 4))):
        m = S.n_of(0.15)
        p = S.lp(S.noise(m, 'white', r), 1400, SR) * S.env_exp(m, 0.03) * 0.6 + _thud(m, r.uniform(80, 120), 0.04, 0.9, r)
        C.place(y, p, t0, 1.0 - 0.1 * j); t0 += r.uniform(0.12, 0.2)
    return y


def haul(i):
    r = rng(2260 + i); dur = 0.5 + 0.05 * i; n = S.n_of(dur); t = np.arange(n) / SR
    f0 = (105 + 8 * i) * (1 + 0.1 * np.sin(np.pi * t / dur) - 0.1 * t / dur)
    F = [np.interp(t, [0, dur], [C.VOW['uh'][k], C.VOW[['a', 'uh', 'o', 'er'][i]][k]]) for k in range(3)]
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 0.9
    y = C.vocal(f0, dur, F, r, breath=0.4, tilt=1.25, env=env)
    # rough effort modulation
    y *= 1 + 0.3 * np.sin(TWO_PI * 38 * t)
    return S.lp(y, 4500, SR, 2)


def slosh(i):
    r = rng(2270 + i); n = S.n_of(1.3); t = np.arange(n) / SR; y = np.zeros(n)
    C.place(y, S.modal(r.uniform(95, 135), 'barrel', 0.6, 0.5, r=r) * 0.7, 0.0)
    env = np.exp(-((t - 0.35) / 0.25) ** 2) + 0.6 * np.exp(-((t - 0.8) / 0.25) ** 2)
    b = S.grains(1.3, lambda tt: 120 * (0.2 + (np.exp(-((tt - 0.35) / 0.25) ** 2) + 0.6 * np.exp(-((tt - 0.8) / 0.25) ** 2))),
                 lambda rr, k: S.bubble_grain(rr, k, 150, 1300), r)
    y += b * 0.9 + S.lp(S.noise(n, 'white', r), 700 + 300 * i, SR) * env * 0.4
    return y


def radio_click(i):
    r = rng(2280 + i)
    return radio_click_one(r)


def radio_squelch(i):
    r = rng(2290 + i)
    return radio_squelch_one(r, 0.28 + 0.03 * i)


def binoc():
    r = rng(2300); n = S.n_of(0.14); y = np.zeros(n)
    C.place(y, C.tick(0.005, 1200, 4000, r) + 0.5 * S.modal(1500, 'plastic', 0.04, 0.8, r=r), 0.0)
    C.place(y, C.tick(0.004, 1500, 5000, r) * 0.7, 0.045)
    return y


def cast(i):
    r = rng(2310 + i); n = S.n_of(1.2); t = np.arange(n) / SR; y = np.zeros(n)
    z = S.tv_bandpass(S.noise(n, 'white', r), 1400 + 2600 * np.clip(t / 0.6, 0, 1), 1.0, 2) * np.sin(np.pi * np.clip(t / 0.6, 0, 1)) ** 1.5 * (t < 0.6)
    y += z * 0.5
    C.place(y, C.tick(0.006, 900, 3500, r), 0.0, 0.7)
    t1 = 0.65 + 0.03 * i
    b = S.grains(0.2, lambda tt: 90, lambda rr, k: S.bubble_grain(rr, k, 300, 1800), r)
    C.place(y, b, t1, 0.7)
    C.place(y, S.lp(S.noise(S.n_of(0.2), 'white', r), 2000, SR) * S.env_exp(S.n_of(0.2), 0.04), t1, 0.5)
    return y


def reel_loop():
    r = rng(2320); L = 4.0; n = S.n_of(L); y = np.zeros(n); t = np.arange(n) / SR
    cps = round(15 * L) / L
    for k in range(int(cps * L)):
        c = C.tick(0.004, 1500, 5500, r)
        C.circ_place(y, c, k / cps, r.uniform(0.6, 1.0))
    whirr = np.sin(TWO_PI * round(120 * L) / L * t) + 0.5 * np.sin(TWO_PI * round(240 * L) / L * t)
    y += S.bp(whirr, 100, 1200, SR, 1) * 0.15
    y += C.pnoise(n, C.band_shape(800, 4000, -3), r) * 0.04
    return y


# ============================================================== NPC cues
def seq(items, total, kind='bell', r_wet=0.0, rt=1.2, seed=1):
    """items: (t, midi, dur, kind, vel). Mono phrase with optional echo."""
    y = np.zeros(S.n_of(total))
    for it in items:
        t0, m, d, k, v = it
        C.place(y, C.soft_note(HZ(m), d, k, v), t0)
    if r_wet > 0:
        y = C.echo(y, rt, r_wet, seed, 0.7, 0.6)
    return C.trim(y, total, min(0.5, total * 0.3))


def render_npc():
    N = lambda **kw: dict(group='people', lazy=True, bus='ui', max_dist=0, weight=2.0, peak=-6, **kw)
    save('npc_report_blip', seq([(0, 81, 0.25, 'marimba', 0.9), (0.075, 86, 0.3, 'marimba', 0.8)], 0.5), **N(rate=(0.97, 1.03), sr=32000))
    save('npc_decoy_blip', seq([(0, 81, 0.25, 'sine', 0.9), (0.085, 84.0 - 0.25, 0.32, 'sine', 0.75)], 0.55) * 1.0, **N(rate=(0.97, 1.03), sr=32000))
    save('npc_unmask_sting', seq([(0, 62, 0.4, 'bell', 0.7), (0.13, 65, 0.4, 'bell', 0.7), (0.26, 69, 0.4, 'bell', 0.75),
                                  (0.39, 74, 0.7, 'bell', 0.8), (0.65, 77, 1.4, 'bell', 0.55), (0.65, 81, 1.4, 'bell', 0.5),
                                  (0.65, 50, 1.4, 'tri', 0.35)], 2.2, r_wet=0.25, seed=21), **N(sr=32000))
    save('npc_courier_caught_sting', seq([(0, 69, 0.4, 'tri', 0.8), (0.18, 65, 0.4, 'tri', 0.8), (0.36, 62, 0.9, 'tri', 0.9),
                                          (0.5, 50, 1.2, 'bell', 0.6)], 1.8, r_wet=0.2, seed=22), **N(sr=32000))
    save('npc_contraband_seized_sting', seq([(0, 50, 1.2, 'bell', 0.8), (0, 57, 1.2, 'bell', 0.55), (0.4, 55, 0.9, 'tri', 0.6),
                                             (0.8, 50, 1.2, 'bell', 0.8), (0.8, 38, 1.2, 'tri', 0.5)], 2.2, r_wet=0.2, seed=23), **N(sr=32000))
    save('npc_trust_up', seq([(0, 65, 0.3, 'marimba', 0.8), (0.09, 69, 0.3, 'marimba', 0.8), (0.18, 74, 0.5, 'marimba', 0.9)], 0.8, r_wet=0.15, seed=24), **N(sr=32000))
    save('npc_trust_down', seq([(0, 74, 0.3, 'tri', 0.7), (0.12, 69, 0.3, 'tri', 0.7), (0.24, 65, 0.5, 'tri', 0.75)], 0.9, r_wet=0.15, seed=25), **N(sr=32000))

    def drop(i):
        r = rng(2400 + i); n = S.n_of(0.5)
        y = _thud(n, 78 - 5 * i, 0.07 + 0.01 * i, 1.0, r) + 0.5 * S.lp(S.noise(n, 'white', r), 1800, SR) * S.env_exp(n, 0.07 + 0.02 * i) * S.env_attack(n, 0.004)
        return y
    fam('npc_drop_thud_sand', 4, drop, max_dist=40, weight=2.0, rate=(0.92, 1.06), tags=['npc'])

    def cover(i):
        r = rng(2410 + i); n = S.n_of(0.9); y = np.zeros(n); t0 = 0.0
        for j in range(int(r.integers(2, 4))):
            m = S.n_of(0.28)
            sw = S.lp(S.hp(S.noise(m, 'white', r), 500, SR), 3500, SR) * np.sin(np.pi * np.linspace(0, 1, m)) ** 1.3
            sw += C.fit(S.grains(0.25, lambda tt: 150, lambda rr, k: C.tick(0.006, 1000, 4000, rr) * rr.uniform(0.2, 0.7), r), m)
            C.place(y, sw, t0, 0.6); t0 += r.uniform(0.17, 0.25)
        C.place(y, _thud(S.n_of(0.1), 100, 0.03, 0.5, r), t0 + 0.05)
        return y
    fam('npc_stash_cover', 4, cover, max_dist=30, weight=1.5, tags=['npc'])

    wl = C.winch_loop(4.0, rng(2420), 7, 60, level=1.0)
    save('npc_salvage_winch_loop', S.lp(wl, 3000, SR, 2), loop=True, target_lufs=-28, max_dist=80, weight=2.0, quality=3, tags=['npc'])

    r = rng(2430)
    coin = seq([(0, 86, 0.9, 'bell', 0.9), (0.075, 93, 0.8, 'bell', 0.7)], 1.0)
    C.place(coin, C.tick(0.004, 3000, 7000, r), 0.0, 0.4)
    save('npc_salvage_sold_coin', coin, **N(rate=(0.97, 1.03), sr=32000))
    save('npc_circle_done_fanfare', seq([(0, 62, 0.4, 'marimba', 0.8), (0.13, 69, 0.4, 'marimba', 0.8), (0.26, 74, 0.4, 'marimba', 0.8),
                                         (0.39, 77, 0.4, 'marimba', 0.8), (0.65, 74, 1.6, 'bell', 0.7), (0.65, 77, 1.6, 'bell', 0.6),
                                         (0.65, 81, 1.6, 'bell', 0.55), (0.65, 50, 1.6, 'tri', 0.35)], 2.5, r_wet=0.25, seed=26), **N(sr=32000))

    def topple(i):
        r = rng(2440 + i); n = S.n_of(1.5); y = np.zeros(n); t0 = 0.0; f = r.uniform(180, 240); gap = 0.22
        for j in range(4):
            C.place(y, S.impact('wood', f * (0.82 ** j), 1.0 + 0.2 * j, 0.5, 0.5, seed=2440 + i * 7 + j, thump=0.9), t0, 1.0 - 0.1 * j)
            t0 += gap; gap *= 0.7
        cl = S.grains(1.0, lambda tt: 90 * math.exp(-tt * 2) + 5, lambda rr, k: C.tick(0.01, 500, 3500, rr) * rr.uniform(0.2, 0.7), r)
        C.place(y, cl, 0.5, 0.5)
        return y
    fam('npc_sabotage_topple', 4, topple, max_dist=60, weight=3.0, tags=['npc'])

    save('npc_site_taken_sting', seq([(0, 65, 0.6, 'bell', 0.8), (0.3, 62, 0.6, 'bell', 0.8), (0.65, 57, 1.2, 'bell', 0.85),
                                      (0.65, 45, 1.4, 'tri', 0.45)], 2.0, r_wet=0.25, seed=27), **N(sr=32000))
    r = rng(2450)
    dev = seq([(0, 62, 0.5, 'marimba', 0.7), (0, 69, 0.5, 'marimba', 0.6), (0.25, 65, 0.5, 'marimba', 0.7), (0.25, 72, 0.5, 'marimba', 0.6),
               (0.55, 74, 1.0, 'bell', 0.6)], 1.7, r_wet=0.2, seed=28)
    C.place(dev, C.tick(0.006, 1200, 4000, r), 0.0, 0.5)
    save('npc_developer_arrive', dev, **N(sr=32000))

    rl = rng(2460); L = 4.0; k = int(0.4 * SR); n = S.n_of(L) + k; t = np.arange(n) / SR
    cnt = round(700 / 60 * 2 * L); ff = cnt / L; rpm = ff * 60 / 2
    mod = 0.01 * np.sin(TWO_PI * t / L + 1)
    e = S.engine(rpm * (1 + mod), 4, dur=n / SR, seed=2460, rough=0.25, exhaust=0.8, load=0.5)
    e = S.peak_eq(S.lp(e, 420, SR, 2), 80, 1.5, 5)
    save('npc_smuggler_arrive_low_engine', S.make_loop(e, 0.4), loop=True, target_lufs=-30, max_dist=150, weight=3.0, quality=3, tags=['npc'],
         meta=dict(fadeInS=2.5, note='quiet idle; runtime fades gain in over 2-3 s as the boat approaches, rate 0.9-1.1'), rate=(0.9, 1.1))

    save('npc_rescue_success', seq([(0, 62, 0.4, 'marimba', 0.7), (0.12, 67, 0.4, 'marimba', 0.7), (0.24, 69, 0.4, 'marimba', 0.75),
                                    (0.36, 74, 0.4, 'marimba', 0.8), (0.48, 77, 0.5, 'marimba', 0.8), (0.62, 81, 1.8, 'bell', 0.75),
                                    (0.62, 74, 1.8, 'bell', 0.55), (0.62, 50, 1.8, 'tri', 0.3)], 2.8, r_wet=0.25, seed=29), **N(sr=32000))
    save('npc_rescue_start_alert', seq([(0, 69, 0.3, 'tri', 0.8), (0.2, 74, 0.3, 'tri', 0.8), (0.4, 69, 0.3, 'tri', 0.8), (0.6, 74, 0.5, 'tri', 0.85)], 1.4,
                                       r_wet=0.15, seed=30), **N(sr=32000))
    save('npc_threat_alert', seq([(0, 62, 0.3, 'tri', 0.9), (0.28, 62, 0.3, 'tri', 0.9), (0.56, 57, 0.6, 'tri', 1.0), (0.56, 50, 0.6, 'tri', 0.5)], 1.4,
                                 r_wet=0.15, seed=31), **N(sr=32000))
    t = np.arange(S.n_of(3.0)) / SR
    d = seq([(0, 50, 2.6, 'bell', 0.8), (0.1, 55, 2.4, 'bell', 0.5), (0.2, 57, 2.4, 'bell', 0.5)], 3.0)
    d *= 0.75 + 0.25 * np.sin(TWO_PI * 5.5 * t)
    d += 0.5 * np.sin(TWO_PI * HZ(38) * t) * np.minimum(1, t / 0.8) * np.exp(-t / 1.8)
    save('npc_disaster_alert', C.trim(C.echo(d, 1.4, 0.25, 32, 0.7, 0.7), 2.6, 0.6), **N(sr=32000))


def render():
    S.set_manifest('people')
    render_steps()
    save('ppl_breath', breath_sound(rng(2090)), weight=0.5, max_dist=20, sr=32000)
    fam('ppl_grunt_topple', 4, grunt, max_dist=40, weight=2.0, sr=32000, tags=['voice'])
    fam('ppl_shout_boat', 3, shout_boat, max_dist=120, weight=3.0, sr=32000, tags=['voice'])
    fam('ppl_shout_help', 3, shout_help, max_dist=120, weight=3.0, sr=32000, tags=['voice'])
    fam('ppl_whistle_lifeguard', 3, whistle, max_dist=150, weight=3.0, sr=32000, peak=-14, tags=['voice'])
    fam('ppl_laugh_small', 3, laugh, max_dist=30, weight=1.0, sr=32000, tags=['voice'])
    fam('ppl_cough', 3, cough, max_dist=25, weight=1.0, sr=32000, tags=['voice'])
    save('ppl_shiver', shiver(), loop=True, target_lufs=-30, max_dist=15, weight=0.5, sr=32000, quality=3, tags=['voice'])
    save('ppl_murmur_loop_s', murmur(12.0, 7, 2180, 3), loop=True, target_lufs=-30, max_dist=60, weight=1.5, sr=32000, quality=3, tags=['crowd'],
         meta=dict(crowd='small', note='scale gain with people count; lowpass with distance'))
    save('ppl_murmur_loop_m', murmur(12.0, 24, 2185, 8), loop=True, target_lufs=-28, max_dist=90, weight=2.0, sr=32000, quality=3, tags=['crowd'],
         meta=dict(crowd='medium', note='scale gain with people count; lowpass with distance'))
    fam('ppl_camera_shutter', 4, camera_shutter, max_dist=30, weight=1.0, sr=32000, tags=['action'])
    fam('ppl_shovel_dig', 4, shovel, max_dist=45, weight=1.5, tags=['action'])
    fam('ppl_hammer_tap', 4, hammer, max_dist=60, weight=2.0, tags=['action'])
    fam('ppl_stone_place', 4, stone_place, max_dist=70, weight=3.0, tags=['action'])
    fam('ppl_axe_chop', 4, axe, max_dist=70, weight=3.0, tags=['action'])
    fam('ppl_tree_plant_pat', 4, pat, max_dist=30, weight=1.0, sr=32000, tags=['action'])
    fam('ppl_haul_grunt', 4, haul, max_dist=40, weight=1.5, sr=32000, tags=['voice'])
    fam('ppl_drum_slosh', 4, slosh, max_dist=40, weight=1.5, sr=32000, tags=['action'])
    fam('ppl_radio_click', 4, radio_click, max_dist=25, weight=1.0, sr=32000, tags=['radio'])
    fam('ppl_radio_squelch', 4, radio_squelch, max_dist=25, weight=1.0, sr=32000, peak=-9, tags=['radio'])
    save('ppl_radio_chatter_loop', radio_chatter(), loop=True, target_lufs=-30, max_dist=20, weight=1.0, sr=32000, quality=3, tags=['radio'])
    save('ppl_binocular_click', binoc(), max_dist=20, weight=0.5, sr=32000, tags=['action'])
    fam('ppl_fishing_cast', 4, cast, max_dist=40, weight=1.5, sr=32000, tags=['action'])
    save('ppl_fishing_reel', reel_loop(), loop=True, target_lufs=-30, max_dist=30, weight=1.0, sr=32000, quality=3, tags=['action'])
    render_npc()


if __name__ == '__main__':
    render()
