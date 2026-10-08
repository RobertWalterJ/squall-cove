src = open('gen_ac130_imp.py', encoding='utf-8').read()
a = src.index('def v_metal'); b = src.index('def v_water')
NEW = '''SQ_LOG = []      # (element length ms) of every metal squeak element generated (for the QA report)
PING_TAUS = []


def v_metal(r, i):
    """Heavy punch, then many very short variable-length squeaks (10-60 ms, rising or falling, 6-13 kHz), plus a bright inharmonic
    ping cluster (3-9 kHz, decays over roughly 80-200 ms) like struck sheet metal."""
    pj = r.uniform(0.92, 1.08); d = 0.36
    parts = [(punch(r, pj, 1.25, 180, 75, 0.02), 0.0), (crack(r, 0.02, 3500, 12000, 0.0012, 0.9), 0.002)]
    # ping cluster: 4-5 slightly inharmonic partials, 3-9 kHz
    base = r.uniform(3000, 4200); ratios = [1.0, r.uniform(1.38, 1.5), r.uniform(1.85, 2.05), r.uniform(2.3, 2.55), r.uniform(2.6, 2.95)]
    tau = r.uniform(0.022, 0.04); PING_TAUS.append(tau)
    n = n_of(0.3); t = tt(n); ping = np.zeros(n)
    for k, q in enumerate(ratios):
        f = min(base * q, 9000.0)
        ping += np.sin(TWO_PI * f * t + r.uniform(0, 6.28)) * np.exp(-t / (tau * (1.0 - 0.12 * k))) * (1.0 - 0.12 * k)
    ping *= np.minimum(1, t / 0.0006)
    parts.append((ping * 0.45, 0.004))
    # squeaks
    for _ in range(int(r.integers(5, 10))):
        L = float(np.exp(r.uniform(math.log(0.010), math.log(0.060)))); SQ_LOG.append(L * 1000)
        f0 = r.uniform(6000, 12500); f1 = f0 * (r.uniform(0.45, 0.8) if r.random() < 0.5 else r.uniform(1.25, 1.7))
        parts.append((zip_short(r, min(f0, 13000), min(f1, 13500), L, r.uniform(0.35, 0.8)), r.uniform(0.004, 0.15)))
    return place(d, parts)


'''
src = src[:a] + NEW + src[b:]
src = src.replace("names = ['dirt', 'dirt', 'dirt', 'concrete', 'concrete', 'metal', 'dirt', 'water'] if i == 2 else ['dirt', 'dirt', 'concrete', 'dirt', 'metal', 'dirt', 'dirt', 'concrete']",
                  "names = ['metal', 'dirt', 'metal', 'concrete', 'metal', 'dirt', 'water', 'metal'] if i == 2 else ['metal', 'dirt', 'concrete', 'metal', 'metal', 'dirt', 'concrete', 'metal']")
open('gen_ac130_imp.py', 'w', encoding='utf-8').write(src)
print('ok')
