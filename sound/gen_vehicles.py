"""Vehicles: engines (3 rpm layers each), sails and rigging, horns, bells, sirens, weapons, hull sounds, aircraft."""
import math
import numpy as np
from scipy import signal
import synthlib as S
import svp_common as C

SR = S.SR
TWO_PI = 2 * math.pi
rng = S.rng


def save(name, x, **kw):
    kw.setdefault('bus', 'veh'); kw.setdefault('lazy', True); kw.setdefault('group', 'boats')
    kw.setdefault('max_dist', 200); kw.setdefault('weight', 3.0); kw.setdefault('quality', 4)
    bus = kw.pop('bus')
    if kw.get('loop'):
        x = C.seal(x, kw.get('sr', SR))
    return S.save(name, x, bus, **kw)


def fam(prefix, count, maker, **kw):
    """Render count numbered variants prefix_01.. ; maker(i)->array."""
    tags = kw.pop('tags', [prefix])
    for i in range(count):
        save('%s_%02d' % (prefix, i + 1), maker(i), variants=count, tags=tags, **kw)


# ============================================================== engines
LOOP_L = 5.0
XF = 0.4

ENGINES = {
    'tug': dict(tilt=3.5, cyl=3, stroke=4, rpm=(750, 1200, 1750), rng=(600, 1800), load=(0.85, 0.85, 0.9), rough=0.30, exh=1.0,
                lpc=(650, 1000, 1500), body=[(90, 1.5, 7), (170, 2, 4), (420, 2, 2)], knock=0.30, core=True, seed=100,
                desc='3-cyl diesel chug'),
    'lifeboat': dict(tilt=3.0, cyl=6, stroke=4, rpm=(1000, 2000, 3200), rng=(800, 3400), load=(0.6, 0.7, 0.85), rough=0.12, exh=0.8,
                     lpc=(900, 1500, 2400), body=[(110, 1.5, 4), (300, 2, 3), (900, 2, 2)], knock=0.2, core=False, seed=200,
                     desc='6-cyl fast diesel'),
    'patrol': dict(tilt=3.0, cyl=6, stroke=4, rpm=(900, 1500, 2300), rng=(700, 2500), load=(0.7, 0.75, 0.85), rough=0.14, exh=0.9,
                   lpc=(650, 1300, 2000), body=[(70, 1.5, 6), (140, 2, 4), (320, 2, 2)], knock=0.2, core=False, seed=300,
                   twin=1.011, desc='twin diesel, detuned'),
    'icebreaker': dict(tilt=1.5, cyl=6, stroke=2, rpm=(90, 140, 195), rng=(70, 200), load=(0.95, 0.95, 1.0), rough=0.45, exh=1.0,
                       lpc=(300, 420, 600), body=[(45, 1.2, 8), (85, 1.5, 6), (120, 2, 4)], knock=0.15, core=False, seed=400,
                       desc='heavy slow 2-stroke diesel'),
    'outboard': dict(tilt=2.0, cyl=2, stroke=2, rpm=(2000, 3500, 5500), rng=(1500, 6000), load=(0.75, 0.8, 0.85), rough=0.28, exh=0.7,
                     lpc=(2600, 3800, 5000), body=[(300, 2, 3), (1200, 3, 4), (2400, 3, 3)], knock=0.0, core=True, seed=500,
                     desc='small 2-stroke buzz'),
}


def _aligned_layer(cfg, i, r, f_target=None, count=None, seed=0):
    """One engine render at layer i, with the firing frequency snapped so that the loop length holds an integer number of
    firing cycles (harmonic part is then exactly periodic across the seam). Returns (y_with_xfade, f_fire, rpm_eff)."""
    k = int(XF * SR); n = int(LOOP_L * SR) + k
    per = cfg['cyl'] / (2.0 if cfg['stroke'] == 4 else 1.0)
    f_t = cfg['rpm'][i] / 60.0 * per if f_target is None else f_target
    cnt = count if count is not None else max(1, round(f_t * LOOP_L))
    ff = cnt / LOOP_L
    rpm = ff * 60.0 / per
    t = np.arange(n) / SR
    wob = 0.010 if cfg['stroke'] == 4 else 0.015
    mod = wob * (0.6 * np.sin(TWO_PI * t / LOOP_L + r.uniform(0, 6.28)) + 0.4 * np.sin(TWO_PI * 2 * t / LOOP_L + r.uniform(0, 6.28))
                 + 0.3 * np.sin(TWO_PI * 3 * t / LOOP_L + r.uniform(0, 6.28)))
    rpm_a = rpm * (1 + mod)
    y = S.engine(rpm_a, cfg['cyl'], dur=n / SR, seed=seed, rough=cfg['rough'], exhaust=cfg['exh'], load=cfg['load'][i],
                 stroke=cfg['stroke'])
    ph = TWO_PI * np.cumsum(ff * (1 + mod)) / SR
    return y, ph, ff, rpm


def _shape(y, ph, cfg, i, r):
    y = S.lp(y, cfg['lpc'][i], SR, 2)
    y = S.spectral_tilt(y, cfg['tilt'])
    for f, q, g in cfg['body']:
        y = S.peak_eq(y, f, q, g)
    if cfg['knock'] > 0:
        gate = np.maximum(0, np.sin(ph - 0.4)) ** 24
        kn = S.bp(S.noise(len(y), 'white', r), 1200, 3200, SR, 1) * gate
        y = y + kn * cfg['knock'] * (0.6 + 0.5 * i) * np.std(y) * 2.0
    return y


def build_engine(key):
    cfg = ENGINES[key]; r = rng(cfg['seed']); layers = []; info = []
    for i in range(3):
        y, ph, ff, rpm = _aligned_layer(cfg, i, r, seed=cfg['seed'] + i)
        if cfg.get('twin'):
            f2 = ff * cfg['twin']
            cnt2 = round(f2 * LOOP_L)
            if cnt2 == round(ff * LOOP_L): cnt2 += 4        # make sure the two engines beat (about 0.8 Hz)
            y2, ph2, ff2, _ = _aligned_layer(cfg, i, r, count=cnt2, seed=cfg['seed'] + 17 + i)
            y2 = _shape(y2, ph2, cfg, i, r)
            y = _shape(y, ph, cfg, i, r)
            y = 0.62 * y + 0.62 * y2 * (np.std(y) / (np.std(y2) + 1e-9))
        else:
            y = _shape(y, ph, cfg, i, r)
        layers.append(y); info.append((ff, rpm))
    # shared body: mid carries some of the low layer, hi some of the mid layer (keeps timbre family consistent for crossfades)
    body0 = S.lp(layers[0], 220, SR, 2)
    layers[1] = layers[1] + 0.30 * np.std(layers[1]) / (np.std(body0) + 1e-9) * body0
    body1 = S.lp(layers[1], 260, SR, 2)
    layers[2] = layers[2] + 0.18 * np.std(layers[2]) / (np.std(body1) + 1e-9) * body1
    return layers, info


def render_engines():
    names = ['lo', 'mid', 'hi']
    thr = [(0.0, 0.40), (0.25, 0.78), (0.60, 1.0)]
    lufs = [-25.0, -24.0, -22.5]
    for key in ENGINES:
        cfg = ENGINES[key]
        layers, info = build_engine(key)
        for i in range(3):
            y = S.make_loop(layers[i], XF)
            rpm_lo = cfg['rng'][0]; rpm_hi = cfg['rng'][1]
            meta = dict(engine=key, layer=names[i], rpm=cfg['rpm'][i], rpmRange=[rpm_lo, rpm_hi], throttleRange=list(thr[i]),
                        rateRange=[0.8, 1.25] if i < 2 else [0.85, 1.15], firingHz=round(info[i][0], 2),
                        cyl=cfg['cyl'], stroke=cfg['stroke'],
                        note='crossfade lo/mid/hi by throttle; playbackRate = targetRpm / meta.rpm clamped to rateRange')
            save('veh_eng_%s_%s' % (key, names[i]), y, loop=True, target_lufs=lufs[i], rate=(0.8, 1.25), weight=4.0,
                 lazy=not cfg['core'], group='core' if cfg['core'] else 'boats', quality=3, meta=meta, tags=['engine', key])


# ============================================================== hover (noise-dominated)
def render_hover():
    r = rng(600); k = int(XF * SR); n = int(LOOP_L * SR) + k; t = np.arange(n) / SR
    rps = (24.0, 34.0, 46.0)           # fan revolutions per second
    layers = []
    for i, rv in enumerate(rps):
        bpf = round(12 * rv * LOOP_L) / LOOP_L          # 12 blades, snapped to integer cycles per loop
        mod = 1 + 0.05 * np.sin(TWO_PI * t / LOOP_L + r.uniform(0, 6)) + 0.03 * np.sin(TWO_PI * 3 * t / LOOP_L + r.uniform(0, 6))
        ph = TWO_PI * bpf * np.cumsum(mod) / SR
        tone = sum((1.0 / h) * np.sin(h * ph + r.uniform(0, 6.28)) for h in (1, 2, 3, 4, 5))
        w = S.noise(n, 'pink', r)
        roar = S.tv_bandpass(w, 500 + 900 * i, 3.6, 2) * (1 + 0.25 * S.smooth_random(n, 4, r, 1.0))
        roar += 0.8 * S.lp(w, 250, SR, 2)
        # turbine whine
        wf = round((1500 + 500 * i) * LOOP_L) / LOOP_L
        whine = np.sin(TWO_PI * wf * t + 0.5 * np.sin(TWO_PI * 2 * t / LOOP_L)) * (0.04 + 0.02 * i)
        eng = S.lp(S.engine(1500 + 500 * i, 4, dur=n / SR, seed=610 + i, load=0.8), 400, SR, 2) * 0.35
        y = roar * (0.9 + 0.3 * i) + tone * (0.55 + 0.25 * i) * np.std(roar) * 0.55 + whine * np.std(roar) * 2 + eng * np.std(roar)
        y = S.lp(y, 5500 + 1000 * i, SR, 2)
        layers.append(y)
    layers[1] = layers[1] + 0.25 * np.std(layers[1]) / np.std(S.lp(layers[0], 300)) * S.lp(layers[0], 300)
    names = ['lo', 'mid', 'hi']; thr = [(0.0, 0.40), (0.25, 0.78), (0.60, 1.0)]; lufs = [-25.0, -24.0, -22.5]
    for i in range(3):
        y = S.make_loop(layers[i], XF)
        save('veh_eng_hover_%s' % names[i], y, loop=True, target_lufs=lufs[i], rate=(0.8, 1.25), weight=4.0, quality=3,
             meta=dict(engine='hover', layer=names[i], rpm=int(rps[i] * 60), rpmRange=[1200, 3000], throttleRange=list(thr[i]),
                       rateRange=[0.8, 1.25], bladePassHz=12 * rps[i], note='noise-dominated; blade-pass tone rises with fan rpm'),
             tags=['engine', 'hover'])


# ============================================================== boat misc
def render_boat_misc():
    # prop wash loop
    r = rng(700); k = int(0.5 * SR); n = int(5.0 * SR) + k; t = np.arange(n) / SR
    w = S.lp(S.noise(n, 'pink', r), 1100, SR, 2)
    am = 0.7 + 0.3 * np.sin(TWO_PI * 11 * t + 0.5 * np.sin(TWO_PI * 0.7 * t))
    bub = S.grains(n / SR, lambda tt: 90, lambda rr, ii: S.bubble_grain(rr, ii, 200, 1400), r, amp_fn=lambda tt: 0.5)
    y = w * am * (1 + 0.4 * S.smooth_random(n, 1.5, r, 1.0)) + bub[:n] * 0.9 + 0.5 * S.lp(S.noise(n, 'brown', r), 150, SR, 2)
    save('veh_prop_wash_loop', S.make_loop(y, 0.5), loop=True, target_lufs=-26, quality=3, tags=['water'])

    # sail luff loop: irregular cloth flutter
    r = rng(710); n = int(4.6 * SR); t = np.arange(n) / SR
    rate = 9 + 4 * S.smooth_random(n, 0.8, r, 1.0)
    flut = np.abs(np.sin(np.cumsum(TWO_PI * rate / SR / 2))) ** 3
    flut = flut * (0.5 + 0.5 * S.smooth_random(n, 5, r, 1.0))
    cloth = S.tv_bandpass(S.noise(n, 'white', r), 900 + 800 * S.smooth_random(n, 1.2, r), 3.0, 2)
    y = cloth * flut + 0.3 * S.lp(S.noise(n, 'pink', r), 300, SR) * flut
    y *= 0.6 + 0.4 * S.smooth_random(n, 0.6, r, 1.0)
    save('veh_sail_luff', S.make_loop(y, 0.6), loop=True, target_lufs=-27, quality=3, tags=['sail'])

    # sail flap
    def sail_flap(i):
        r = rng(720 + i); n = int(1.0 * SR); y = np.zeros(n)
        t0 = 0.02; gap = r.uniform(0.07, 0.11)
        for j in range(r.integers(4, 7)):
            c = S.bp(S.noise(int(0.12 * SR), 'white', r), r.uniform(250, 500), r.uniform(1800, 3200), SR, 1)
            c *= S.env_exp(len(c), r.uniform(0.02, 0.035)) * S.env_attack(len(c), 0.002)
            C.place(y, c, t0, (0.85 ** j) * r.uniform(0.7, 1.0))
            C.place(y, S.lp(S.noise(int(0.12 * SR), 'white', r), 160, SR) * S.env_exp(int(0.12 * SR), 0.03) * 1.5, t0, 0.5 * 0.85 ** j)
            t0 += gap * (1 + 0.15 * j) * r.uniform(0.85, 1.2)
        return y
    fam('veh_sail_flap', 4, sail_flap, quality=4, tags=['sail'])

    # sheet creak: stick-slip rope on block
    def creak(i):
        r = rng(730 + i); n = int(0.9 * SR); t = np.arange(n) / SR
        slip = 55 + 35 * np.sin(TWO_PI * (1.4 + 0.5 * i) * t / 0.9 + r.uniform(0, 6)) + 30 * t
        ph = TWO_PI * np.cumsum(slip) / SR
        src = (np.mod(ph / TWO_PI, 1.0) * 2 - 1) * (0.6 + 0.4 * np.sin(TWO_PI * 3.1 * t))
        f1 = r.uniform(520, 900) * (1 + 0.15 * np.sin(TWO_PI * 1.1 * t + r.uniform(0, 6)))
        y = C.tv_res(src, f1, 14) + 0.6 * C.tv_res(src, f1 * 2.4, 18) + 0.25 * S.noise(n, 'white', r) * 0.1
        env = np.sin(np.pi * np.clip(t / 0.9, 0, 1)) ** 0.8
        return y * env
    fam('veh_sheet_creak', 4, creak, tags=['rigging'])

    # rope rattle against mast
    def rattle(i):
        r = rng(740 + i); n = int(0.9 * SR)
        def rg(rr, ii):
            kk = int(0.05 * SR); out = np.zeros(kk); x = C.tick(0.007, 1500, 5500, rr); out[:len(x)] += x
            return out + 0.4 * S.modal(rr.uniform(700, 1400), 'plastic', 0.05, 0.5, r=rr)[:kk]
        y = S.grains(n / SR, lambda tt: 34 + 25 * math.sin(tt * 6 + i), rg, r)
        return y * (0.4 + 0.6 * S.smooth_random(len(y), 5, r, 1.0))
    fam('veh_rope_rattle', 4, rattle, tags=['rigging'])

    # hull creak: slow low stick-slip
    def hull_creak(i):
        r = rng(750 + i); n = int(1.8 * SR); t = np.arange(n) / SR
        slip = 28 + 22 * np.sin(TWO_PI * (0.8 + 0.2 * i) * t + r.uniform(0, 6)) + 10 * t
        ph = TWO_PI * np.cumsum(slip) / SR
        src = (np.mod(ph / TWO_PI, 1.0) * 2 - 1) ** 3
        f1 = r.uniform(140, 260) * (1 + 0.25 * np.sin(TWO_PI * 0.6 * t + r.uniform(0, 6)))
        y = C.tv_res(src, f1, 9) + 0.7 * C.tv_res(src, f1 * 1.9, 12) + 0.3 * C.tv_res(src, f1 * 3.3, 12)
        y += 0.15 * S.lp(S.noise(n, 'brown', r), 120)
        return y * np.sin(np.pi * np.clip(t / 1.8, 0, 1)) ** 1.2
    fam('veh_hull_creak', 4, hull_creak, tags=['hull'])


# ============================================================== horns, bells, sirens
def horn(freqs, dur, att, rel, seed, hmax=10, tilt=0.8, breath=0.05, droop=0.0, rise=0.03, rise_t=0.06):
    r = rng(seed); n = S.n_of(dur); t = np.arange(n) / SR; y = np.zeros(n)
    for fi, f in enumerate(freqs):
        for det in (-0.004, 0.0, 0.004):
            ff = f * (1 + det) * (1 - rise * np.exp(-t / rise_t)) * (1 - droop * np.clip((t - (dur - rel * 1.5)) / rel, 0, 1))
            ph = TWO_PI * np.cumsum(ff) / SR
            for h in range(1, hmax + 1):
                if f * h > 7000: break
                y += (h ** -tilt) * np.sin(h * ph + r.uniform(0, 6.28)) * (1 if det == 0 else 0.6)
    env = np.minimum(1, t / att) ** 1.5 * np.minimum(1, np.maximum(0, (dur - t) / rel)) ** 1.2
    nz = S.bp(S.noise(n, 'white', r), freqs[0] * 1.5, 3500, SR, 1)
    y = y * env + breath * np.std(y) * nz * (env * 0.5 + 0.5 * np.exp(-t / 0.08)) * 0.8
    y = S.peak_eq(y, freqs[0] * 3.2, 1.2, 4)
    return S.lp(y, 4800, SR, 2)


def render_horns_bells():
    save('veh_horn_short', horn((196, 247), 0.65, 0.05, 0.12, 800), weight=6, rate=(0.92, 1.08), tags=['horn'])
    save('veh_horn_long', horn((196, 247), 2.2, 0.07, 0.35, 801), weight=6, rate=(0.92, 1.08), tags=['horn'])
    fg = horn((98, 104.5), 3.0, 0.35, 0.8, 802, hmax=16, tilt=0.55, droop=0.03, rise=0.04, rise_t=0.15)
    fg = C.trim(C.echo(fg, 2.4, 0.3, 802, 0.8, 0.8), 4.2, 1.0)
    save('veh_foghorn', fg, weight=8, max_dist=400, rate=(0.94, 1.06), tags=['horn'], peak=-4)

    # ship bell: single strike, six second ring
    r = rng(810); n = S.n_of(6.0)
    b = S.modal(520.0, 'bell', 6.0, 1.5, bright=1.0, r=r)
    tr = S.bp(S.noise(n, 'white', r), 1500, 5000, SR, 1) * np.exp(-np.arange(n) / (0.004 * SR)) * 0.4
    b = b + tr
    b = C.echo(b, 1.6, 0.18, 811, 0.7, 0.7)[:n]
    save('veh_ship_bell', b, weight=5, rate=(0.95, 1.05), tags=['bell'], peak=-4)

    # buoy bell: irregular clapper strikes, thin bright
    def buoy(i):
        r = rng(820 + i); f0 = r.uniform(1050, 1500); n = S.n_of(4.0); y = np.zeros(n)
        t = 0.05
        for j in range(r.integers(3, 6)):
            hit = S.modal(f0 * r.uniform(0.98, 1.02), 'bell', 1.6, 0.3, bright=1.25, r=r) * r.uniform(0.35, 1.0)
            C.place(y, hit, t)
            t += r.uniform(0.25, 1.0)
        return S.hp(y, 400, SR, 1)
    fam('veh_buoy_bell', 4, buoy, weight=3, max_dist=300, tags=['bell'])

    def siren(L, fn, harm=2.5, seed=0):
        n = S.n_of(L); t = np.arange(n) / SR
        f = fn(t / L); tot = f.sum() / SR; f = f * (round(tot) / tot)
        ph = TWO_PI * np.cumsum(f) / SR
        y = np.tanh(harm * np.sin(ph)) + 0.25 * np.sin(2 * ph)
        y = S.lp(y, 4200, SR, 2)
        return S.peak_eq(y, 1100, 0.7, 3)
    wail = siren(4.0, lambda u: 650 * (1500 / 650) ** (0.5 - 0.5 * np.cos(TWO_PI * u)))
    save('veh_siren_wail', wail, loop=True, weight=6, target_lufs=-24, tags=['siren'], rate=(0.95, 1.05), quality=3)
    yelp = siren(4.0, lambda u: 700 * (1500 / 700) ** ((np.mod(u * 20, 1.0)) ** 0.8))
    save('veh_siren_yelp', yelp, loop=True, weight=6, target_lufs=-24, tags=['siren'], rate=(0.95, 1.05), quality=3)


# ============================================================== weapons and hull
def render_weapons():
    def gun(i):
        r = rng(900 + i); n = S.n_of(2.0); t = np.arange(n) / SR
        crack = S.noise(n, 'white', r) * np.exp(-t / 0.0012)
        crack = S.lp(S.hp(crack, 700, SR, 2), 5200, SR, 4) * 1.1
        tail = S.lp(S.bp(S.noise(n, 'white', r), 300, 3200, SR, 1) * np.exp(-t / (0.04 + 0.01 * i)), 5000, SR, 2) * 0.6
        f = (125 - 8 * i) * np.exp(-t / 0.05) + 52 + 2 * i
        boom = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.17) * 1.3
        thump = S.lp(S.noise(n, 'brown', r), 160, SR, 2) * np.exp(-t / 0.12) * 1.5
        y = crack + tail + boom + thump
        y = C.echo(y, 1.5, 0.32, 905 + i, 0.8, 1.0)
        return S.lp(y, 6000, SR, 3)[:S.n_of(2.2)]
    fam('veh_gun_fire', 4, gun, weight=8, rate=(0.92, 1.08), group='weapons', peak=-3, tags=['weapon'])

    def shell(i):
        r = rng(910 + i); n = S.n_of(1.4); t = np.arange(n) / SR
        env = np.sin(np.pi * np.clip(t / 1.4, 0, 1)) ** 2.2
        c = 3200 - 2100 * (t / 1.4) ** 0.8
        w = S.tv_bandpass(S.noise(n, 'white', r), c, 1.8, 2) * env
        f = 1900 - 900 * (t / 1.4); wh = np.sin(TWO_PI * np.cumsum(f) / SR) * env * 0.12
        low = S.lp(S.noise(n, 'pink', r), 420, SR) * env * 0.6
        return S.lp(w + wh + low, 5800, SR, 2)
    fam('veh_gun_shell_fly', 4, shell, weight=5, group='weapons', tags=['weapon'])

    def mg(i):
        r = rng(920 + i); cnt = int(r.integers(9, 15)); rate = r.uniform(11, 14); n = S.n_of(cnt / rate + 0.9); y = np.zeros(n)
        for j in range(cnt):
            tt = j / rate + r.uniform(-0.006, 0.006) + 0.02
            m = int(0.04 * SR); tm = np.arange(m) / SR
            cr = S.lp(S.hp(S.noise(m, 'white', r) * np.exp(-tm / 0.006), 1100, SR, 2), 5200, SR, 3)
            bd = np.sin(TWO_PI * (95 * np.exp(-tm / 0.02) + 60) * tm) * np.exp(-tm / 0.025) * 0.9
            C.place(y, cr + bd, tt, r.uniform(0.75, 1.0))
        y = C.echo(y, 1.0, 0.22, 925 + i, 0.8, 1.0)
        return S.lp(y, 6000, SR, 2)
    fam('veh_mg_burst', 4, mg, weight=6, group='weapons', tags=['weapon'])

    def hit_l(i):
        r = rng(930 + i)
        y = S.impact('plank', r.uniform(150, 230), 0.7, 0.45, 0.7, seed=930 + i, thump=0.0)
        tb = np.arange(len(y)) / SR
        y += 0.6 * np.sin(TWO_PI * r.uniform(60, 95) * tb + r.uniform(0, 6.28)) * np.exp(-tb / r.uniform(0.05, 0.1))
        return y
    fam('veh_hull_hit_light', 4, hit_l, weight=4, tags=['hull'])

    def hit_h(i):
        r = rng(940 + i)
        y = S.impact('wood', r.uniform(70, 110), 2.2, 0.35, 1.5, seed=940 + i, thump=0.0)
        n = len(y); tb = np.arange(n) / SR
        y += 1.6 * np.sin(TWO_PI * r.uniform(42, 70) * tb * (1 - 0.3 * np.exp(-tb * 25)) + r.uniform(0, 6.28)) * np.exp(-tb / r.uniform(0.12, 0.25))
        cr = S.bp(S.noise(n, 'white', r), 200, 1800, SR, 1) * np.exp(-np.arange(n) / (0.08 * SR))
        return y + 0.5 * cr
    fam('veh_hull_hit_heavy', 4, hit_h, weight=6, tags=['hull'])

    def breach(i):
        r = rng(950 + i); n = S.n_of(1.8); t = np.arange(n) / SR
        crack = S.impact('wood', r.uniform(110, 180), 1.2, 0.8, 0.6, seed=950 + i, thump=1.0)
        y = np.zeros(n); y[:len(crack)] += crack
        spl = S.grains(0.35, lambda tt: 260 * math.exp(-tt * 6), lambda rr, ii: C.tick(0.009, 800, 4500, rr) * 1.2, r)
        C.place(y, spl, 0.0, 0.8)
        g = S.tv_bandpass(S.noise(n, 'white', r), 700 + 900 * np.minimum(1, t / 0.5), 2.6, 2)
        g *= np.minimum(1, t / 0.18) * np.exp(-np.maximum(0, t - 0.5) / 0.7) * 0.7
        bub = S.grains(1.8, lambda tt: 80 * math.exp(-tt * 1.2), lambda rr, ii: S.bubble_grain(rr, ii, 150, 1200), r)
        return y + g + 0.7 * bub
    fam('veh_hull_breach', 4, breach, weight=6, tags=['hull'])

    r = rng(960); n = S.n_of(5.0) + int(0.6 * SR)
    bub = S.grains(n / SR, lambda tt: 22 + 18 * math.sin(tt * 1.3), lambda rr, ii: S.bubble_grain(rr, ii, 90, 700), r)
    y = bub * 1.4 + 0.5 * S.lp(S.noise(n, 'pink', r), 400, SR) * (0.6 + 0.4 * S.smooth_random(n, 1.5, r)) + 0.4 * S.lp(S.noise(n, 'brown', r), 90, SR)
    save('veh_sinking_gurgle', S.make_loop(y, 0.6), loop=True, target_lufs=-26, quality=3, tags=['water'])

    r = rng(965); n = S.n_of(5.0) + int(0.6 * SR)
    cr = S.grains(n / SR, lambda tt: 45 + 40 * (0.5 + 0.5 * math.sin(tt * 1.7)), lambda rr, ii: C.tick(0.012, 700, 4500, rr) * rr.uniform(0.3, 1.2), r)
    roar = S.lp(S.noise(n, 'pink', r), 520, SR, 2) * (0.5 + 0.5 * S.smooth_random(n, 2.0, r)) * 0.7
    pop = S.grains(n / SR, lambda tt: 3.0, lambda rr, ii: S.lp(S.noise(int(0.06 * SR), 'white', rr), 900, SR) * np.exp(-np.arange(int(0.06 * SR)) / (0.012 * SR)) * 1.5, r)
    save('veh_fire_on_boat_loop', S.make_loop(cr + roar + pop, 0.6), loop=True, target_lufs=-25, quality=3, tags=['fire'])

    r = rng(970); n = S.n_of(4.5); t = np.arange(n) / SR
    sp = S.bp(S.noise(n, 'white', r), 900, 6500, SR, 2) * (1 + 0.15 * np.sin(TWO_PI * 5.5 * t) + 0.25 * S.smooth_random(n, 3, r, 1.0))
    sp += 0.5 * S.lp(S.noise(n, 'pink', r), 350, SR)
    save('veh_fire_hose_spray_loop', S.make_loop(S.lp(sp, 7500, SR, 2), 0.5), loop=True, target_lufs=-26, quality=3, tags=['water'])

    wl = C.winch_loop(4.0, rng(980), 10, 80)
    save('veh_winch_loop', wl, loop=True, target_lufs=-26, quality=3, tags=['winch'])

    def chain(i):
        r = rng(990 + i); n = S.n_of(1.6); y = np.zeros(n); t = 0.0
        heavy = S.impact('iron', r.uniform(300, 500), 0.4, 0.8, 0.5, seed=990 + i, thump=0.3)
        C.place(y, heavy, 0.0, 0.8)
        gap = 0.012
        while t < 1.3:
            c = S.impact('iron', r.uniform(900, 2400), 0.11, 0.95, 0.12, seed=int(t * 1000) + i)
            C.place(y, c, t, r.uniform(0.2, 0.7) * (1.2 - t / 1.6)); t += gap * r.uniform(0.6, 1.8); gap *= 1.05
        y += 0.6 * S.lp(S.noise(n, 'pink', r), 500, SR) * np.exp(-np.arange(n) / (0.5 * SR)) * 0.4
        return y
    fam('veh_anchor_chain', 4, chain, tags=['chain'])

    def ice(i):
        r = rng(1000 + i); n = S.n_of(1.4); t = np.arange(n) / SR
        cr = S.grains(1.4, lambda tt: 95 * math.exp(-tt * 1.5) + 8, lambda rr, ii: C.tick(0.014, 500, 3500, rr) * rr.uniform(0.2, 1.0), r)
        cr *= 1.0
        gr = S.lp(S.noise(n, 'brown', r), 160, SR) * np.exp(-t / 0.5) * 1.5
        gr += C.tv_res(S.noise(n, 'white', r), 90 + 40 * np.sin(TWO_PI * 1.5 * t), 14) * np.exp(-t / 0.6) * 0.6
        ic = S.modal(r.uniform(900, 1400), 'ice', 0.4, 0.7, r=r) * 0.2
        y = cr + gr; y[:len(ic)] += ic
        return y
    fam('veh_ice_crunch_hull', 4, ice, weight=5, tags=['ice'])


# ============================================================== aircraft
def render_aircraft():
    L = 4.0; k = int(0.5 * SR); n = int(L * SR) + k; t = np.arange(n) / SR; r = rng(1100)
    # helicopter rotor: blade pass 18 Hz (4 blades, 4.5 rev/s)
    bp = 18.0; ph = TWO_PI * bp * t
    th = sum(((h ** -0.85) / (1 + (h * bp / 420.0) ** 2)) * np.cos(h * ph - 0.25 * h) for h in range(1, 40))
    rev = 0.85 + 0.15 * np.cos(TWO_PI * 4.5 * t + 0.4) + 0.06 * np.cos(TWO_PI * 9 * t)
    slap_gate = np.maximum(0, np.cos(ph - 0.3)) ** 10
    slap = S.bp(S.noise(n, 'white', r), 350, 2400, SR, 1) * slap_gate * 0.45
    whine = 0.05 * np.sin(TWO_PI * 1900 * t + 0.6 * np.sin(TWO_PI * 0.5 * t)) + 0.03 * np.sin(TWO_PI * 2860 * t)
    wash = S.lp(S.noise(n, 'pink', r), 900, SR) * 0.25
    y = th * rev * 0.55 + slap * np.std(th) + whine * np.std(th) * 1.5 + wash * np.std(th)
    y = S.lp(y, 5500, SR, 2)
    save('veh_heli_rotor_loop', S.make_loop(y, 0.5), loop=True, target_lufs=-22, weight=6, group='aircraft', rate=(0.9, 1.1), quality=3,
         meta=dict(bladePassHz=18, note='rate scales blade pass; keep 0.9-1.1'), tags=['heli'])

    t2 = np.arange(n) / SR; r = rng(1110)
    vib = 0.6 * np.sin(TWO_PI * 2 * t2 / L * 2)
    w = (np.sin(TWO_PI * 2200 * t2 + vib) + 0.6 * np.sin(TWO_PI * 3300 * t2 + 0.5 * vib) + 0.25 * np.sin(TWO_PI * 4400 * t2))
    nz = S.bp(S.noise(n, 'white', r), 1500, 5000, SR, 2) * 0.35
    w = (w * (0.8 + 0.2 * np.sin(TWO_PI * 2 * t2 / L + 1)) + nz)
    save('veh_heli_whine_loop', S.make_loop(S.lp(w, 6500, SR, 2), 0.5), loop=True, target_lufs=-30, weight=3, group='aircraft', quality=3,
         tags=['heli'])

    r = rng(1120)
    wsh = S.tv_bandpass(S.noise(n, 'pink', r), 900, 3.5, 2) + 0.7 * S.lp(S.noise(n, 'pink', r), 300, SR)
    wsh *= (0.75 + 0.25 * np.cos(TWO_PI * 18 * t2)) * (0.7 + 0.3 * S.smooth_random(n, 0.8, r, 1.0))
    save('veh_heli_wash_loop', S.make_loop(wsh, 0.5), loop=True, target_lufs=-26, weight=4, group='aircraft', quality=3, tags=['heli'])

    def prop_engine(seed, f_fire, cyl, blades_hz, gain_blade, lpc, load, shape_bp):
        r = rng(seed); n = int(L * SR) + k
        cnt = round(f_fire * L); ff = cnt / L; rpm = ff * 60 / (cyl / 2)
        tt = np.arange(n) / SR
        mod = 0.008 * (np.sin(TWO_PI * tt / L + 1) + 0.5 * np.sin(TWO_PI * 3 * tt / L + 2))
        y = S.engine(rpm * (1 + mod), cyl, dur=n / SR, seed=seed, rough=0.1, exhaust=0.5, load=load)
        bf = round(blades_hz * L) / L
        blade = sum((1.0 / h) * np.sin(h * TWO_PI * bf * tt + 0.3 * h) for h in (1, 2, 3)) * (0.8 + 0.2 * np.sin(TWO_PI * bf * tt))
        air = S.bp(S.noise(n, 'pink', r), 200, 2500, SR, 1) * (0.7 + 0.3 * np.cos(TWO_PI * bf * tt)) * 0.5
        y = S.lp(y, lpc, SR, 2) + gain_blade * blade * np.std(y) + air * np.std(y)
        return S.lp(S.peak_eq(y, shape_bp, 1.0, 3), 4200, SR, 2)
    ps = prop_engine(1130, 80, 4, 80, 0.5, 1800, 0.7, 400)
    save('veh_prop_small_loop', S.make_loop(ps, 0.5), loop=True, target_lufs=-24, weight=5, group='aircraft', rate=(0.85, 1.2), quality=3,
         meta=dict(rpm=2400, note='rate follows throttle 0.85-1.2'), tags=['prop'])
    pb = prop_engine(1140, 101.25, 9, 33.75, 0.9, 1200, 0.9, 200)
    save('veh_prop_big_loop', S.make_loop(pb, 0.5), loop=True, target_lufs=-24, weight=6, group='aircraft', rate=(0.85, 1.2), quality=3,
         meta=dict(rpm=1350, note='radial engine with three-blade prop thrum'), tags=['prop'])

    def bomber(i):
        r = rng(1150 + i); n = S.n_of(4.0); tt = np.arange(n) / SR; y = np.zeros(n)
        for e in range(4):
            rpm = 1500 + 17 * e * (1 + 0.1 * i) + 25 * i
            y += S.engine(rpm, 6, dur=4.0, seed=1150 + 10 * i + e, rough=0.15, exhaust=0.5, load=0.75)
        y = S.lp(y, 1500, SR, 2) + 0.6 * S.bp(S.noise(n, 'pink', r), 150, 2200, SR, 1) * np.std(y)
        env = 0.03 + np.exp(-((tt - 2.0 - 0.1 * (i - 1.5)) / (0.85 + 0.08 * i)) ** 2)
        cut = 450 + 3200 * np.exp(-((tt - 2.0) / 1.0) ** 2)
        y = S.tv_filter(y, cut, 'lp', 2) * env
        return y
    fam('veh_bomber_pass', 4, bomber, weight=8, max_dist=500, group='aircraft', quality=3, tags=['flyover'])

    def drop(i):
        r = rng(1160 + i); n = S.n_of(1.8); tt = np.arange(n) / SR
        env = np.sin(np.pi * np.clip(tt / 0.9, 0, 1)) ** 2 * (tt < 0.9)
        w = S.tv_bandpass(S.noise(n, 'white', r), 2200 - 1500 * np.clip(tt / 0.9, 0, 1), 2.2, 2) * env
        w += 0.5 * S.lp(S.noise(n, 'pink', r), 500, SR) * env
        t1 = 0.85 + 0.02 * i
        sp = S.lp(S.noise(n, 'white', r), 2800 - 400 * i, SR, 2) * np.where(tt >= t1, np.exp(-(tt - t1) / 0.22), 0) * 1.4
        th = np.sin(TWO_PI * 70 * (tt - t1)) * np.where(tt >= t1, np.exp(-(tt - t1) / 0.16), 0) * 1.0
        bub = S.grains(1.8, lambda x: 60 if x > t1 else 0.01, lambda rr, ii: S.bubble_grain(rr, ii, 200, 1200), r) * 0.5
        return w * 0.8 + sp + th + bub
    fam('veh_water_drop_whoosh', 4, drop, weight=6, group='aircraft', tags=['aircraft'])


def render():
    S.set_manifest('vehicles')
    render_engines()
    render_hover()
    render_boat_misc()
    render_horns_bells()
    render_weapons()
    render_aircraft()


if __name__ == '__main__':
    render()
