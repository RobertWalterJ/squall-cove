"""One-off: rewrite the Vulcan hit makers (punch + short bright squeak), add punch to Bofors cores, split render/deploy by part."""
src = open('gen_ac130_imp.py', encoding='utf-8').read()
a = src.index('def v_dirt'); b = src.index('V_MAKERS = dict')
NEW = '''def punch(r, pj=1.0, lvl=1.0, f0=170.0, f1=62.0, tau=0.022):
    """Heavy low front: fast-attack 60-180 Hz sub drop plus a short low-mid slap, about 70 ms, tight tail."""
    return sumv(sub(0.07, f0 * pj, f1 * pj, 0.006, tau, 0.0004, 0.2), body(r, 0.03, 320, 0.008, 0.9, 70) * 0.8) * lvl


def zip_short(r, f0, f1, dur, lvl=1.0):
    """Brief pitch-falling zip (20 to 80 ms) with a very fast decay."""
    n = n_of(dur); t = tt(n); f = f1 + (f0 - f1) * np.exp(-t / (dur * 0.35)); ph = TWO_PI * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / (dur * 0.28)) * np.minimum(1, t / 0.0006) * lvl


def hiss_short(r, dur, lo, hi, lvl=1.0):
    n = n_of(dur); t = tt(n)
    return unit(bp(noise(n, 'white', r), lo, hi, SR, 2)) * np.exp(-t / (dur * 0.3)) * np.minimum(1, t / 0.0006) * lvl


def grit(r, k, t0, t1, lvl=1.0, lo=4000, hi=11000):
    out = np.zeros(n_of(t1 + 0.02))
    for _ in range(k):
        put(out, tickn(r, r.uniform(0.001, 0.003), r.uniform(lo, lo * 1.5), r.uniform(hi * 0.8, hi), r.uniform(0.5, 1.0) * lvl), r.uniform(t0, t1), 1.0)
    return out


def place(d, parts):
    buf = np.zeros(n_of(d))
    for x, t in parts: put(buf, x, t, 1.0)
    return buf


def v_dirt(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.6), 0.0), (body(r, 0.08, 900, 0.02, 0.45, 150), 0.01), (hiss_short(r, 0.06, 4500, 11500, 0.7), 0.012),
                        (grit(r, 7, 0.012, 0.11, 0.9), 0.0), (zip_short(r, r.uniform(7500, 10500), 3500, r.uniform(0.03, 0.05), 0.3), 0.02)])


def v_concrete(r, i):
    pj = r.uniform(0.92, 1.08)
    return place(0.25, [(punch(r, pj, 1.4, 190, 70, 0.018), 0.0), (crack(r, 0.03, 3000, 12000, 0.0015, 1.3), 0.003),
                        (grit(r, 8, 0.008, 0.1, 1.0, 4500, 12000), 0.0), (zip_short(r, r.uniform(9500, 12500), 4000, r.uniform(0.04, 0.075), 0.7), 0.015)])


def v_metal(r, i):
    pj = r.uniform(0.92, 1.08); f = r.uniform(2200, 3800)
    ping = fit(pingn(f, 0.018, 0.08, ((1, 1.0, 1.0), (2.76, 0.5, 0.6), (5.4, 0.3, 0.35)), None, r), n_of(0.08))
    return place(0.3, [(punch(r, pj, 1.25, 180, 75, 0.02), 0.0), (crack(r, 0.02, 3500, 12000, 0.0012, 0.9), 0.002), (ping * 0.8, 0.008),
                       (zip_short(r, r.uniform(10000, 12500), 5000, r.uniform(0.04, 0.07), 0.8), 0.012), (zip_short(r, r.uniform(8000, 10500), 4500, 0.035, 0.5), 0.03 + 0.01 * (i % 3))])


def v_water(r, i):
    pj = r.uniform(0.92, 1.08)
    bub = fit(U.bubble(r, 1500, 3500), n_of(0.06)) * 0.9
    return place(0.25, [(punch(r, pj, 1.3, 140, 55, 0.022), 0.0), (hiss_short(r, 0.07, 5000, 11500, 0.7), 0.01), (bub, 0.015),
                        (grit(r, 4, 0.02, 0.11, 0.6, 5000, 11000), 0.0)])


def v_person(r, i):
    pj = r.uniform(0.92, 1.08)      # cartoon thump + cloth slap; no vocal, no gore
    return place(0.25, [(punch(r, pj, 1.8, 130, 58, 0.03), 0.0), (body(r, 0.08, 700, 0.025, 0.7, 120), 0.004), (tickn(r, 0.004, 2000, 6500, 0.5, n_of(0.02)), 0.006)])


'''
src = src[:a] + NEW + src[b:]
# shorter zings for the Bofors set too
src = src.replace("dur = dur or r.uniform(0.12, 0.35)", "dur = dur or r.uniform(0.05, 0.14)")
# punch + bright crack in Bofors core
src = src.replace("    return sumv(fit(s, n_of(d)), c)\n", "    return sumv(fit(s, n_of(d)), c, punch(r, pj, 1.1, 150, 55, 0.03), crack(r, 0.03, 3000, 12000, 0.002, 0.9))\n", 1)
# render split by part
ra = src.index('def render():'); rb = src.index('def deploy():')
REND = '''PART = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ('v', 'b') else 'vb'


def render():
    if 'v' in PART:
        S.set_manifest('ac130imp_v'); H.CEIL_DB = -4.5
        for sf, mk in V_MAKERS.items():
            reg('ac130_vulcan_hit_' + sf, mk, 4, 'hit', 'mat', weight=4, max_dist=250, tags=['impact', 'ac130', 'vulcan', sf])
        reg('ac130_vulcan_stitch', m_stitch, 3, 'loop', 'mat', far=dict(stem='ac130_vulcan_stitch_far', count=3, lp=900, delay=0.1, rt=0.8, wet=0.4, fc=700),
            weight=6, max_dist=500, tags=['impact', 'ac130', 'vulcan', 'stitch'])
    if 'b' in PART:
        S.set_manifest('ac130imp_b'); H.CEIL_DB = -2.2
        for sf, mk in B_MAKERS.items():
            reg('ac130_bofors_hit_' + sf, mk, 4, 'fire', 'mat', far=dict(stem='ac130_bofors_hit_%s_far' % sf, count=3, lp=650, delay=0.15, rt=1.4, wet=0.6, fc=550),
                weight=8, max_dist=600, tags=['impact', 'ac130', 'bofors', '40mm', sf])


'''
src = src[:ra] + REND + src[rb:]
src = src.replace("import gen_ac130 as A", "import gen_ac130 as A\nimport gen_heavy as H")
src = src.replace("manifest.ac130imp.json", "manifest.ac130imp_%s.json' % PART[0] + '")
open('gen_ac130_imp.py', 'w', encoding='utf-8').write(src)
print('patched')
