src = open('gen_ac130_imp.py', encoding='utf-8').read()


def cut(src, start, end):
    a = src.index(start); b = src.index(end, a)
    return a, b


NEWLIB = '''def chips(r, dur, t0, rate0, tau, lo=1500, hi=7000, lvl=1.0, dull=0.12):
    """Real concrete/gravel debris: dry hard fragments. Irregular broadband noise bursts (0.7-5 ms, fast decay, bandpassed lo-hi),
    random timing and level, occasional 2-3 chip skitters, and a few very small dull damped 'tok' bits (fixed pitch, no sweeps)."""
    out = np.zeros(n_of(dur)); t = t0
    while t < dur - 0.03:
        t += r.exponential(1.0 / max(rate0, 1.0))
        if t >= dur - 0.03: break
        if r.random() > math.exp(-(t - t0) / tau): continue
        for j in range(int(r.integers(1, 4)) if r.random() < 0.3 else 1):
            tj = t + j * r.uniform(0.001, 0.008); g = lvl * (r.uniform(0.08, 1.0) ** 1.6)
            k = int(r.uniform(0.0007, 0.005) * SR); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.22))
            c = r.uniform(lo * 1.3, hi * 0.7); x = bp(x, max(lo, c * 0.6), min(hi, c * 1.5), SR, 2)
            put(out, x * g, tj, 1.0)
            if r.random() < dull:
                m = int(r.uniform(0.003, 0.008) * SR); tx = np.arange(m) / SR
                put(out, np.sin(TWO_PI * r.uniform(500, 1500) * tx) * np.exp(-tx / r.uniform(0.002, 0.004)) * g * 0.25, tj, 1.0)
    return out


def sprinkle(r, dur, t0, rate0, tau, lvl=1.0, lo=3500, hi=10000, gmin=0.04, gmax=0.6):
    """Tiny light droplets: very short quiet high ticks at random times, slowly thinning out (rate0 * exp(-(t-t0)/tau))."""
    out = np.zeros(n_of(dur)); t = t0
    while t < dur - 0.02:
        t += r.exponential(1.0 / max(rate0, 1.0))
        if t >= dur - 0.02: break
        if r.random() > math.exp(-(t - t0) / tau): continue
        k = int(r.uniform(0.0006, 0.002) * SR); x = r.standard_normal(k) * np.exp(-np.arange(k) / (k * 0.25))
        c = r.uniform(lo * 1.2, hi * 0.8); x = bp(x, max(lo, c * 0.7), min(hi, c * 1.4), SR, 2)
        put(out, x * lvl * (r.uniform(gmin, gmax) ** 1.5), t, 1.0)
    return out


def spray(r, dur, rise, hold, fall, lo, hi, lvl=1.0):
    """Spray column: soft broadband hiss that swells, holds and falls back, with irregular flutter."""
    n = n_of(dur); t = tt(n)
    env = np.where(t < rise, np.sin(np.clip(t / rise, 0, 1) * math.pi / 2) ** 2, np.where(t < rise + hold, 1.0, np.exp(-(t - rise - hold) / fall)))
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * env * slowmod(n, 14, r, 0.6) * lvl


def slap(r, dur, tau, fc=800, lvl=1.0):
    """Dull water slap: low-passed noise, quick decay."""
    n = n_of(dur); t = tt(n)
    return unit(lp(noise(n, 'white', r), fc, SR, 2)) * np.exp(-t / tau) * np.minimum(1, t / 0.0015) * lvl


'''
a = src.index('def v_dirt')
src = src[:a] + NEWLIB + src[a:]

# Vulcan concrete: dry chips instead of grit
a, b = cut(src, 'def v_concrete', 'SQ_LOG = []')
src = src[:a] + '''def v_concrete(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.4, 190, 70, 0.018), 0.0), (crack(r, 0.03, 3000, 12000, 0.0015, 1.3), 0.003),
                        (chips(r, 0.24, 0.006, 420, 0.07, 1500, 7000, 1.0), 0.0), (zip_short(r, r.uniform(9500, 12500), 4000, r.uniform(0.04, 0.075), 0.6), 0.015)])


''' + src[b:]

# Vulcan water: heavy short thump + light droplet scatter (more=True for the stitch)
a, b = cut(src, 'def v_water', 'V_MAKERS = dict')
src = src[:a] + '''def v_water(r, i, more=False):
    pj = r.uniform(0.92, 1.08)
    parts = [(punch(r, pj, 1.5, 140, 52, 0.022), 0.0), (slap(r, 0.07, 0.02, 900, 0.7), 0.002), (hiss_short(r, 0.04, 3500, 11000, 0.45), 0.008),
             (sprinkle(r, 0.22, 0.0, 90, 0.07, 0.3), 0.02)]
    if more:
        parts += [(sprinkle(r, 0.65, 0.0, 170, 0.28, 0.35), 0.03), (sprinkle(r, 0.65, 0.0, 380, 0.25, 0.12, 3000, 8000), 0.03)]
    return place(0.7 if more else 0.25, parts)


''' + src[b:]

# stitch: more scatter on the water hits, two water hits in variant 03
src = src.replace("h = V_MAKERS[nm](r, k)", "h = v_water(r, k, True) if nm == 'water' else V_MAKERS[nm](r, k)")
src = src.replace("['metal', 'dirt', 'metal', 'concrete', 'metal', 'dirt', 'water', 'metal'] if i == 2", "['metal', 'dirt', 'water', 'concrete', 'metal', 'dirt', 'water', 'metal'] if i == 2")

# Bofors concrete: dry chips
src = src.replace("debris(r, d, 0.1, 140, 0.45, 1500, 8000, 0.25, 0.7),", "chips(r, d, 0.05, 260, 0.45, 1500, 7000, 0.9),")

# Bofors water and howitzer water
a, b = cut(src, 'def b_water', 'B_MAKERS = dict')
src = src[:a] + '''def b_water(r, i):
    d = 1.5; pj = r.uniform(0.92, 1.08)
    A_ = sumv(punch(r, pj, 1.3, 110, 45, 0.035), slap(r, 0.25, 0.05, 700, 0.9), body(r, 0.3, 350, 0.06, 0.6, 60), crack(r, 0.04, 2500, 11000, 0.003, 0.7))
    B_ = place(d, [(hiss_short(r, 0.12, 2500, 10000, 0.6), 0.01), (spray(r, 0.9, 0.05, 0.08, 0.28, 2500, 9000, 0.25), 0.05),
                   (sprinkle(r, 1.4, 0.0, 230, 0.5, 0.35), 0.05), (sprinkle(r, 1.4, 0.0, 500, 0.4, 0.12, 3000, 8000), 0.05)])
    return sumv(A_, B_)


def h_water(r, i):
    """105 mm into water: heavy fast-dissipating thump, then a big splash and a spray column falling back as sprinkles."""
    d = 4.2; pj = r.uniform(0.92, 1.08)
    A_ = sumv(sub(2.0, 72 * pj, 27 * pj, 0.12, 0.5, 0.004, 0.1), sub(1.2, 48 * pj, 30 * pj, 0.3, 0.4, 0.014, 0.0) * 0.6, slap(r, 0.5, 0.12, 700, 1.0),
              crack(r, 0.05, 300, 3500, 0.006, 0.7), body(r, 0.6, 300, 0.1, 0.9, 50))
    B_ = place(d, [(hiss_short(r, 0.3, 2000, 9500, 0.8), 0.02), (spray(r, 2.6, 0.25, 0.35, 0.9, 1800, 8000, 0.3), 0.05),
                   (sprinkle(r, 3.8, 0.0, 260, 1.4, 0.4), 0.1), (sprinkle(r, 3.8, 0.0, 600, 1.2, 0.12, 3000, 8000), 0.1)])
    return sumv(fit(A_, n_of(d)), B_)


''' + src[b:]
src = src.replace("B_MAKERS = dict(dirt=b_dirt, concrete=b_concrete, metal=b_metal, water=b_water)", "B_MAKERS = dict(dirt=b_dirt, concrete=b_concrete, metal=b_metal, water=b_water)")
open('gen_ac130_imp.py', 'w', encoding='utf-8').write(src)
print('ok')
