"""Weapons pack: gunshots (layered click/crack/body/tail), far shots, echo tails, handling, shells, bullet passes, impacts, battle UI stings.
Footsteps/foley live in gen_weapons_move.py and the ambience beds in gen_weapons_amb.py; render() runs all three.
Cartoon-safe: no gore, no screams, no speech."""
import math
import numpy as np
from scipy import signal
import synthlib as S
import gen_util as U
import svp_common as C
from wpn_common import *

# ------------------------------------------------------------------ guns
GUNS = {
    #            click crack_lo crack_hi ctau   body_hi btau  bgain f0   f1  boom boomtau thump rt60 tail slaps                          dur
    'pistol':  dict(click=.6, clo=1800, chi=9000, ctau=.0018, bhi=1800, btau=.020, bg=.7, f0=220, f1=95, boom=.9, bt=.05, th=.6, rt=.9, tail=.22, slaps=[(.09, .10)], dur=1.3),
    'smg':     dict(click=.5, clo=2500, chi=10000, ctau=.0012, bhi=2500, btau=.014, bg=.6, f0=260, f1=120, boom=.6, bt=.035, th=.4, rt=.7, tail=.20, slaps=[(.07, .08)], dur=1.0),
    'rifle':   dict(click=.7, clo=1500, chi=8500, ctau=.0022, bhi=1500, btau=.035, bg=.8, f0=170, f1=70, boom=1.1, bt=.09, th=.9, rt=1.6, tail=.30, slaps=[(.18, .16), (.42, .08)], dur=2.2),
    'shotgun': dict(click=.4, clo=600, chi=6000, ctau=.0040, bhi=1400, btau=.060, bg=1.2, f0=130, f1=55, boom=1.3, bt=.13, th=1.2, rt=1.3, tail=.26, slaps=[(.12, .12)], dur=1.9),
    'sniper':  dict(click=.8, clo=1200, chi=9000, ctau=.0030, bhi=1600, btau=.050, bg=.9, f0=150, f1=45, boom=1.4, bt=.20, th=1.2, rt=3.0, tail=.35, slaps=[(.15, .25), (.40, .14), (.80, .08)], dur=4.2),
}


def shot_dry(r, p, dur):
    """Dry gunshot: click, crack, body, boom, thump, then soft-clipped for punch."""
    n = n_of(dur); t = np.arange(n) / SR; pj = r.uniform(0.92, 1.08); gj = lambda: r.uniform(0.85, 1.15)
    click = hp(noise(n, 'white', r), 4000) * np.exp(-t / 0.0004) * p['click'] * gj()
    crack = lp(hp(noise(n, 'white', r), p['clo'] * pj, SR, 2), p['chi'] * pj, SR, 3) * np.exp(-t / (p['ctau'] * pj)) * gj() * 1.1
    body = bp(noise(n, 'white', r), 150, p['bhi'] * pj, SR, 2) * np.exp(-t / (p['btau'] * pj)) * p['bg'] * gj()
    f = p['f1'] * pj + (p['f0'] - p['f1']) * pj * np.exp(-t / 0.05)
    boom = np.sin(TWO_PI * np.cumsum(f) / SR + r.uniform(0, 6.28)) * np.exp(-t / (p['bt'] * pj)) * p['boom'] * gj()
    thm = lp(noise(n, 'brown', r), 200, SR, 2) * np.exp(-t / (p['bt'] * 0.7)) * p['th'] * gj()
    return S.soft_clip(click + crack + body * 0.9 + boom + thm * 0.8, 1.7)


def gun_shot(r, name, i=0):
    p = GUNS[name]; dur = p['dur']; n = n_of(dur)
    dry = shot_dry(r, p, dur)
    ir = S.reverb_ir(p['rt'] * r.uniform(0.9, 1.1), 0.9, 0.8, SR, int(r.integers(1, 99999)), 0.015, stereo=False)[:, 0]
    wet = fit(signal.fftconvolve(dry[:n_of(0.25)], ir), n)
    wet = lp(wet, 4200, SR, 2); wet *= p['tail'] * np.max(np.abs(dry)) / (np.max(np.abs(wet)) + 1e-9)
    out = dry * 0.9 + wet
    for dt, lv in p['slaps']:                      # tree-line slap-back echoes
        dt *= r.uniform(0.85, 1.2); k = n_of(0.35); sl = lp(dry[:k], 2600, SR, 2) * np.exp(-np.arange(k) / (0.07 * SR))
        put(out, sl, dt, lv * r.uniform(0.8, 1.1))
    return fade_out(out, 0.15)


def far_shot(r, name, i=0):
    """Distant version: low-passed, softened onset, a few short echoes and a thin rumble."""
    p = GUNS[name]; dry = shot_dry(r, p, 0.7)
    d = lp(dry, r.uniform(1300, 1900), SR, 3)
    d *= np.minimum(1, np.arange(len(d)) / (0.004 * SR)) ** 2
    out = np.zeros(n_of(2.6)); put(out, d, 0.0, 1.0)
    for k, (dt, lv, fc) in enumerate([(0.30, .45, 1300), (0.66, .28, 950), (1.15, .17, 700)]):
        put(out, lp(d, fc, SR, 2), dt * r.uniform(0.9, 1.15), lv)
    rum = lp(noise(len(out), 'brown', r), 180, SR, 2) * np.exp(-np.arange(len(out)) / (0.5 * SR)) * 0.35
    out += rum * np.max(np.abs(d))
    return fade_out(out, 0.2)


def echo_tail(r, i):
    rt = (2.2, 3.1)[i]; n = n_of(rt * 1.25); t = np.arange(n) / SR
    base = lp(noise(n, 'white', r), 2400 - 500 * i, SR, 2) * np.exp(-t / (rt / 6.9)) * np.minimum(1, t / 0.03)
    for k in range(4 + i):
        put(base, lp(noise(n_of(0.2), 'white', r), 1800, SR, 2) * np.exp(-np.arange(n_of(0.2)) / (0.05 * SR)), r.uniform(0.15, rt * 0.7) , r.uniform(0.4, 0.9) * (1 - k / 7))
    return fade_out(S.lp(base, 3000 - 600 * i, SR, 2), 0.2)


def render_guns():
    for name in GUNS:
        fam('wpn_%s_fire' % name, 3, lambda r, i, name=name: gun_shot(r, name, i), 'veh', 'weapons', peak=-3, weight=8, max_dist=300,
            rate=(0.94, 1.06), tags=['weapon', 'gunshot', name])
        fam('wpn_%s_far' % name, 1, lambda r, i, name=name: far_shot(r, name, i), 'veh', 'weapons', peak=-4, weight=5, max_dist=900, gain=0.7,
            rate=(0.95, 1.05), tags=['weapon', 'gunshot', 'far', name])
    for i in range(2):
        save('wpn_gun_echo_tail_%02d' % (i + 1), echo_tail(rng(U.seed_of('echotail', i)), i), 'veh', 'weapons', variants=2, peak=-8, weight=4,
             max_dist=600, rate=(0.95, 1.05), tags=['weapon', 'tail'])


# ------------------------------------------------------------------ handling
def steel_click(r, f=None, tau=0.012, level=1.0):
    f = f or r.uniform(1800, 3200)
    return sumv(pingn(f, tau, 0.1, ((1, 1, 1), (2.76, .5, .6), (5.4, .25, .3)), r=r) * 0.7, tickn(r, 0.002, 2500, 9000) * 0.9) * level


def slide_rasp(r, dur, lo=600, hi=3000, level=0.5, f_up=True):
    n = n_of(dur); t = np.linspace(0, 1, n)
    c = (lo + (hi - lo) * t) if f_up else (hi - (hi - lo) * t)
    y = S.tv_bandpass(noise(n, 'white', r), c, 1.5, 2) * np.sin(np.pi * t) ** 0.7 * level
    return y * (1 + 0.5 * lp(noise(n, 'white', r), 90, SR, 1))


def mag_out(r, i):
    bt = r.uniform(0.9, 1.1)
    return mix(0.5, [(steel_click(r, 2400 * bt, 0.014), 0.0, 1.0), (slide_rasp(r, 0.14, 500, 2200, 0.5), 0.05, 1.0),
                     (thump(n_of(0.1), 130 * bt, 0.03, 0.5), 0.2, 0.7), (tickn(r, 0.004, 800, 3500, 0.5), 0.23, 0.6)])


def mag_in(r, i):
    bt = r.uniform(0.9, 1.1)
    return mix(0.5, [(slide_rasp(r, 0.12, 400, 1800, 0.45), 0.0, 1.0), (thump(n_of(0.12), 110 * bt, 0.035, 0.9), 0.11, 1.0),
                     (steel_click(r, 2000 * bt, 0.018, 1.2), 0.115, 1.0), (steel_click(r, 3100 * bt, 0.008, 0.6), 0.2, 0.7)])


def reload_bolt(r, i):
    bt = r.uniform(0.9, 1.1)
    return mix(0.7, [(steel_click(r, 1700 * bt, 0.02, 1.0), 0.0, 1.0), (slide_rasp(r, 0.17, 500, 2600, 0.55, True), 0.04, 1.0),
                     (steel_click(r, 2600 * bt, 0.012, 0.8), 0.24, 1.0), (slide_rasp(r, 0.12, 400, 2000, 0.5, False), 0.30, 0.9),
                     (thump(n_of(0.12), 95 * bt, 0.04, 1.1), 0.42, 1.0), (steel_click(r, 1500 * bt, 0.025, 1.3), 0.425, 1.0)])


def pump_shotgun(r, i):
    bt = r.uniform(0.9, 1.1)
    def clack(f):
        return sumv(thump(n_of(0.14), 120 * bt, 0.04, 1.0), steel_click(r, f * bt, 0.025, 1.2), pingn(f * 0.55 * bt, 0.05, 0.25, ((1, .5, 1), (2.4, .3, .5)), r=r) * 0.5)
    return mix(0.75, [(clack(1500), 0.0, 1.0), (slide_rasp(r, 0.06, 500, 1500, 0.35), 0.12, 1.0), (clack(1900), 0.25, 1.0)])


def dry_click(r, i):
    return sumv(steel_click(r, r.uniform(2800, 3800), 0.006, 1.0)[:n_of(0.1)], thump(n_of(0.1), 180, 0.01, 0.2))


def draw(r, i):
    n = n_of(0.45); t = np.linspace(0, 1, n)
    cloth = S.tv_bandpass(noise(n, 'white', r), 1200 + 1500 * t, 1.6, 2) * np.sin(np.pi * t) ** 1.2 * 0.5
    leather = lp(noise(n, 'white', r), 700, SR, 2) * np.sin(np.pi * np.clip(t * 1.6, 0, 1)) * 0.5
    return cloth + leather + mix(0.45, [(steel_click(r, 2200, 0.012, 0.8), 0.28, 1.0), (thump(n_of(0.1), 140, 0.03, 0.5), 0.29, 1.0)])


def knife_swish(r, i):
    n = n_of(0.3); t = np.linspace(0, 1, n)
    f0 = r.uniform(4200, 5200); c = f0 * (1.0 - 0.55 * t ** 0.8)
    w = S.tv_bandpass(noise(n, 'white', r), c, 1.0, 2) * np.sin(np.pi * t) ** 1.8
    ring = pingn(r.uniform(4000, 5500), 0.06, 0.3, ((1, .2, 1), (2.7, .1, .5)), r=r)[:n] * np.exp(-t * 1.5) * 0.4
    return w + ring * np.sin(np.pi * np.clip(t * 3, 0, 1)) * 0.8


def render_handling():
    kw = dict(bus='veh', group='weapons', peak=-5, weight=3, max_dist=40, rate=(0.94, 1.06), tags=['weapon', 'handling'])
    for name, mk in [('wpn_reload_mag_out', mag_out), ('wpn_reload_mag_in', mag_in), ('wpn_reload_bolt', reload_bolt), ('wpn_pump_shotgun', pump_shotgun),
                     ('wpn_dry_click', dry_click), ('wpn_draw', draw), ('wpn_knife_swish', knife_swish)]:
        fam(name, 2, mk, **kw)


# ------------------------------------------------------------------ shell casings
def shell_cast(r, surface, i):
    n = n_of(1.1); out = np.zeros(n); f = r.uniform(3800, 5200) * (1.2 if surface == 'metal' else 1.0)
    tau = dict(concrete=0.05, dirt=0.012, metal=0.12)[surface]
    nb = dict(concrete=int(r.integers(4, 7)), dirt=int(r.integers(1, 3)), metal=int(r.integers(5, 8)))[surface]
    t0 = 0.0; gap = r.uniform(0.07, 0.11); lv = 1.0
    for k in range(nb):
        fj = f * r.uniform(0.9, 1.12)
        ping = pingn(fj, tau, 0.5, ((1, 1, 1), (2.32, .55, .6), (4.1, .3, .35), (0.5, .3, 1.4)), r=r)
        hit = tickn(r, 0.0015, 2500, 9000, 0.9)
        if surface == 'dirt':
            ping = lp(ping, 3200, SR, 2) * 0.5; hit = sumv(lp(hit, 2500, SR, 2) * 0.5, thump(n_of(0.05), 160, 0.012, 0.4))
        elif surface == 'metal':
            ping = sumv(ping, 0.5 * pingn(fj * 0.37, 0.18, 0.6, ((1, 1, 1), (2.45, .5, .6)), r=r))
        put(out, sumv(ping * 0.8, hit), t0, lv)
        t0 += gap; gap *= r.uniform(0.55, 0.7); lv *= r.uniform(0.5, 0.65)
    if surface != 'dirt':   # short roll scrape
        g = U.ticks(0.25, lambda t: 90 * math.exp(-t * 7), r, 2500, 8000, 0.002)
        put(out, g, t0 + 0.02, 0.18)
    return fade_out(out[:n_of(0.9 if surface != 'dirt' else 0.5)], 0.12)


def render_shells():
    for s in ('concrete', 'dirt', 'metal'):
        fam('wpn_shell_' + s, 3, lambda r, i, s=s: shell_cast(r, s, i), 'mat', 'weapons', peak=-8, weight=1, max_dist=35, rate=(0.92, 1.08),
            tags=['weapon', 'shell', s], meta={'surface': s})


# ------------------------------------------------------------------ bullet passes
def whiz(r, i):
    n = n_of(0.6); t = np.arange(n) / SR
    crack = lp(hp(noise(n, 'white', r), 2600, SR, 2), 12000, SR, 2) * np.exp(-t / 0.0014) * 1.0
    f0 = r.uniform(3600, 5200); f1 = r.uniform(1000, 1600); tc = r.uniform(0.07, 0.12)
    c = f1 + (f0 - f1) * np.exp(-t / tc)                                   # doppler-ish falling whip
    whip = S.tv_bandpass(noise(n, 'white', r), c, 0.9, 2) * np.exp(-t / (tc * 1.8)) * np.minimum(1, t / 0.004)
    tone = np.sin(TWO_PI * np.cumsum(c * 0.5) / SR) * np.exp(-t / (tc * 1.2)) * 0.18
    low = lp(noise(n, 'pink', r), 500, SR, 2) * np.exp(-t / 0.06) * 0.25
    return S.soft_clip(crack * 0.9 + whip * 0.9 + tone + low, 1.4)


def ricochet(r, i):
    n = n_of(0.9); t = np.arange(n) / SR
    tick = tickn(r, 0.002, 2500, 9000, 1.0, n) + thump(n, 220, 0.01, 0.2)
    scrape = bp(noise(n, 'white', r), 2500, 9000, SR, 2) * np.exp(-t / 0.012) * 0.6
    f0 = r.uniform(3200, 4200); f1 = r.uniform(500, 900); tc = r.uniform(0.16, 0.26)
    f = f1 + (f0 - f1) * np.exp(-t / tc); f = f * (1 + 0.025 * np.sin(TWO_PI * 38 * t))     # warbling 'pee-yow'
    ph = TWO_PI * np.cumsum(f) / SR
    pew = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)) * np.exp(-t / (tc * 1.6)) * np.minimum(1, t / 0.003)
    ring = pingn(r.uniform(1500, 2300), 0.08, 0.9, ((1, .5, 1), (2.76, .3, .6), (5.4, .15, .3)), r=r)[:n] * 0.5
    return S.soft_clip(tick * 0.8 + scrape + pew * 0.55 + ring, 1.3)


def render_passes():
    fam('wpn_whiz', 3, whiz, 'veh', 'weapons', peak=-5, weight=4, max_dist=60, rate=(0.93, 1.07), tags=['weapon', 'bullet-pass'])
    fam('wpn_ricochet', 3, ricochet, 'veh', 'weapons', peak=-5, weight=4, max_dist=80, rate=(0.93, 1.07), tags=['weapon', 'ricochet'])


# ------------------------------------------------------------------ impacts
def imp_dirt(r, i):
    n = n_of(0.45)
    y = thump(n, r.uniform(90, 130), 0.05, 1.0) + lp(noise(n, 'white', r), 1400, SR, 2) * edec(n, 0.03) * 0.7
    g = fit(U.ticks(0.3, lambda t: 120 * math.exp(-t * 9), r, 800, 3500, 0.004), n) * 0.3
    return y + g


def imp_concrete(r, i):
    n = n_of(0.5)
    y = tickn(r, 0.003, 1500, 8000, 1.0, n)
    y = y + fit(S.modal(r.uniform(700, 1300), 'stone', 0.25, 1.0, 1.0, r=r), n) * 0.45 + thump(n, 120, 0.02, 0.5)
    y += bp(noise(n, 'white', r), 2000, 6000, SR, 1) * edec(n, 0.05) * 0.25
    y += fit(U.ticks(0.3, lambda t: 160 * math.exp(-t * 12), r, 2500, 9000, 0.002), n) * 0.35
    return y


def imp_wood(r, i):
    n = n_of(0.55)
    y = fit(S.modal(r.uniform(180, 300), 'plank', 0.45, 0.7, 1.0, r=r), n) * 0.8 + tickn(r, 0.003, 800, 4500, 0.9, n) + thump(n, 100, 0.04, 0.7)
    return y


def imp_metal(r, i):
    n = n_of(0.9); f = r.uniform(650, 1150)
    y = fit(S.modal(f, 'steel', 0.8, 0.35, 1.0, r=r), n) * 0.5 + fit(S.modal(f * 1.9, 'iron', 0.5, 0.5, 1.0, r=r), n) * 0.3
    y += tickn(r, 0.002, 3000, 10000, 1.0, n) + thump(n, 200, 0.015, 0.3)
    return y


def imp_glass(r, i):
    n = n_of(1.0)
    y = tickn(r, 0.002, 3000, 11000, 0.9, n) + fit(S.modal(r.uniform(1800, 2800), 'glass', 0.5, 0.35, 1.1, r=r), n) * 0.5
    y += fit(U.pings(0.7, lambda t: 70 * math.exp(-t * 3.5), r, 2500, 7500, 0.07), n) * 0.45
    return y


def imp_sand(r, i):
    n = n_of(0.4)
    y = bp(noise(n, 'white', r), 300, 2600, SR, 2) * edec(n, 0.05) * np.minimum(1, np.arange(n) / (0.004 * SR)) * 0.9 + thump(n, 85, 0.05, 0.7)
    y += fit(U.ticks(0.3, lambda t: 220 * math.exp(-t * 10), r, 1200, 4200, 0.004), n) * 0.45
    return y


def imp_water(r, i):
    n = n_of(0.6)
    sp = lp(hp(noise(n, 'white', r), 400, SR, 1), 4000, SR, 2) * edec(n, 0.05) * np.minimum(1, np.arange(n) / (0.003 * SR))
    pl = fit(U.sweep(r.uniform(280, 420), r.uniform(900, 1300), 0.18, 0.05), n) * 0.5       # rising 'plop'
    bub = fit(U.bubble_cloud(0.4, 400, 2800, 160, 0.09, r), n) * 0.7
    return sp * 0.8 + pl + bub + thump(n, 110, 0.04, 0.4)


def imp_body(r, i):
    """Cartoon thump plus a short comic 'oof' breath. No gore, no scream."""
    n = n_of(0.55); th = thump(n, r.uniform(105, 150), 0.05, 1.0) + lp(noise(n, 'white', r), 900, SR, 2) * edec(n, 0.02) * 0.6
    dur = 0.28; nn = n_of(dur); f0 = r.uniform(115, 150) * np.linspace(1.0, 0.72, nn)
    vow = (r.uniform(430, 520), r.uniform(900, 1100), r.uniform(2200, 2500))
    oof = C.vocal(f0, dur, [np.full(nn, v) for v in vow], r, breath=1.4, env=np.sin(np.pi * np.clip(np.linspace(0, 1, nn) * 1.05, 0, 1)) ** 0.8)
    oof = oof / (np.max(np.abs(oof)) + 1e-9) * 0.6
    f = bp(noise(n_of(0.18), 'white', r), 3000, 7000, SR, 1) * np.sin(np.linspace(0, np.pi, n_of(0.18))) * 0.22
    return mix(0.55, [(th, 0.0, 1.0), (oof, 0.04, 1.0), (f, 0.26, 1.0)])


def imp_ko(r, i):
    n = n_of(1.7); th = thump(n_of(0.3), r.uniform(80, 110), 0.07, 1.2) + lp(noise(n_of(0.3), 'white', r), 800, SR, 2) * edec(n_of(0.3), 0.025) * 0.7
    t = np.arange(n_of(0.7)) / SR
    f = (r.uniform(380, 460) * np.exp(-t / 0.35) + 130) * (1 + 0.08 * np.sin(TWO_PI * 9 * t))        # wobbling 'boing' slide
    boing = np.sin(TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.3) * 0.5 + 0.2 * np.sin(2 * TWO_PI * np.cumsum(f) / SR) * np.exp(-t / 0.15)
    stars = np.zeros(n)
    notes = np.array([76, 81, 84, 88, 91, 93])
    for k in range(int(r.integers(4, 7))):
        fm = C.hz(float(r.choice(notes))) * r.uniform(0.998, 1.002)
        put(stars, pingn(fm, 0.16, 0.6, ((1, 1, 1), (2.01, .3, .5)), r=r), 0.32 + 0.10 * k + r.uniform(-0.01, 0.015), 0.28 * (1 - 0.08 * k))
    return mix(1.7, [(th, 0.0, 1.0), (boing, 0.05, 0.8), (stars, 0.0, 1.0)])


def render_impacts():
    kw = dict(bus='mat', group='weapons', peak=-5, weight=3, max_dist=70, rate=(0.92, 1.08))
    for nm, mk, ex in [('imp_dirt', imp_dirt, {}), ('imp_concrete', imp_concrete, {}), ('imp_wood', imp_wood, {}), ('imp_metal', imp_metal, {}),
                       ('imp_glass', imp_glass, {}), ('imp_sand', imp_sand, {}), ('imp_water', imp_water, {})]:
        fam(nm, 3, mk, tags=['impact', nm[4:]], meta={'surface': nm[4:]}, **kw)
    fam('imp_body', 3, imp_body, tags=['impact', 'body', 'cartoon'], **dict(kw, bus='ppl', max_dist=45))
    fam('imp_ko', 3, imp_ko, tags=['impact', 'ko', 'cartoon'], **dict(kw, bus='ppl', max_dist=45, peak=-6))


# ------------------------------------------------------------------ battle UI stings
def ui_flag_capture(r=None):
    r = rng(501); notes = [(67, 0.00, 0.28), (72, 0.20, 0.28), (76, 0.40, 0.75)]
    parts = [(brass_note(C.hz(m) * f, d, 0.025, 0.2, 1.0, 0.4 if d > .5 else 0, r), t, 1.0) for m, t, d in notes for f in (1.0, 2.0 ** (-1))]
    parts[-1] = (parts[-1][0], parts[-1][1], 0.6); parts[-2] = (parts[-2][0], parts[-2][1], 0.9)
    parts.append((timpani(110, 0.6, 0.5, r), 0.0, 0.6)); parts.append((pingn(C.hz(88), 0.5, 1.2, ((1, .4, 1), (2.01, .2, .6))), 0.42, 0.5))
    return fade_out(mix(1.4, parts), 0.1)


def ui_flag_lost(r=None):
    r = rng(502); notes = [(71, 0.00, 0.26), (66, 0.22, 0.26), (60, 0.44, 0.8)]
    parts = [(brass_note(C.hz(m), d, 0.04, 0.25, 0.55, 0.3 if d > .5 else 0, r), t, 1.0) for m, t, d in notes]
    parts += [(brass_note(C.hz(m - 12), d, 0.05, 0.25, 0.4, 0, r), t, 0.7) for m, t, d in notes]
    parts.append((timpani(70, 0.9, 0.7, r), 0.44, 0.7))
    return fade_out(mix(1.5, parts), 0.1)


def ui_tickets_low(r=None):
    r = rng(503); n = n_of(1.3); t = np.arange(n) / SR
    base = np.sin(TWO_PI * 73.4 * t) + 0.8 * np.sin(TWO_PI * 103.8 * t) + 0.3 * np.sin(TWO_PI * 147 * t)   # tritone, uneasy
    pulse = 0.55 + 0.45 * np.sin(TWO_PI * 2.6 * t - 1.5) ** 2
    env = np.minimum(1, t / 0.05) * np.exp(-t / 0.9)
    hits = mix(1.3, [(thump(n_of(0.4), 62, 0.12, 1.0), 0.0, 0.9), (thump(n_of(0.4), 62, 0.12, 1.0), 0.42, 0.8), (thump(n_of(0.4), 62, 0.12, 1.0), 0.84, 0.7)])
    air = bp(noise(n, 'white', r), 700, 2500, SR, 1) * np.sin(np.pi * np.clip(t / 1.3, 0, 1)) ** 2 * 0.1
    return fade_out(lp(base, 700, SR, 2) * pulse * env * 0.6 + hits * 0.6 + air, 0.12)


def ui_respawn(r=None):
    r = rng(504); n = n_of(0.9); t = np.linspace(0, 1, n)
    wh = S.tv_bandpass(noise(n, 'white', r), 300 + 2400 * t ** 1.5, 1.4, 2) * np.sin(np.pi * np.clip(t / 0.62, 0, 1)) ** 1.5 * (t < 0.62) * 0.8
    th = thump(n_of(0.35), 78, 0.1, 1.0) + lp(noise(n_of(0.35), 'white', r), 400, SR, 2) * edec(n_of(0.35), 0.04) * 0.5
    return mix(0.9, [(wh, 0.0, 1.0), (th, 0.52, 1.0), (pingn(C.hz(79), 0.25, 0.5, ((1, .25, 1), (2.0, .1, .6))), 0.53, 0.5)])


def ui_victory(r=None):
    r = rng(505); P = [(67, 0.0, 0.2), (72, 0.2, 0.2), (76, 0.4, 0.2), (79, 0.6, 0.5)]
    parts = [(brass_note(C.hz(m), d, 0.02, 0.15, 1.0, 0, r), t, 1.0) for m, t, d in P]
    parts += [(brass_note(C.hz(m), d, 0.02, 0.15, 0.8, 0, r), t, 0.6) for m, t, d in [(m - 12, t, d) for m, t, d in P]]
    for m, g in [(60, 0.8), (64, 0.7), (67, 0.7), (72, 0.8), (79, 0.5)]:         # held C major chord, swelling then decaying
        parts.append((brass_note(C.hz(m), 2.9, 0.12, 1.2, 1.0, 1.0, r) * np.exp(-np.arange(n_of(2.9)) / SR / 2.4), 1.05, g))
    parts += [(timpani(98, 1.4, 0.9, r), 0.0, 0.7), (timpani(98, 1.8, 1.0, r), 1.05, 0.9)]
    for k, m in enumerate([96, 100, 103, 108, 100, 105]):                          # bell shimmer
        parts.append((pingn(C.hz(m), 0.5, 1.6, ((1, .4, 1), (2.76, .1, .4))), 1.1 + 0.12 * k, 0.28))
    return fade_out(mix(4.0, parts), 0.08)


def ui_defeat(r=None):
    r = rng(506); P = [(58, 0.0, 0.55), (56, 0.5, 0.55), (55, 1.0, 0.7)]
    parts = [(brass_note(C.hz(m), d, 0.08, 0.3, 0.45, 0.4, r), t, 0.9) for m, t, d in P]
    parts += [(brass_note(C.hz(m - 12), d, 0.1, 0.3, 0.3, 0, r), t, 0.6) for m, t, d in P]
    for m, g in [(48, 0.9), (55, 0.7), (51, 0.6), (60, 0.35)]:                     # low C minor resolve
        parts.append((pad_note(C.hz(m), 2.6, 0.35, 1.2, 0.7) * np.exp(-np.arange(n_of(2.6)) / SR / 2.1), 1.45, g))
    parts += [(timpani(70, 1.6, 0.8, r), 1.45, 0.8), (timpani(70, 1.0, 0.4, r), 0.0, 0.4)]
    return fade_out(lp(mix(4.0, parts), 3500, SR, 2), 0.08)


def ui_hitmarker(r=None):
    r = rng(507); n = n_of(0.12)
    return pingn(2300, 0.012, 0.12, ((1, 1, 1), (2.0, .3, .5))) * 0.8 + tickn(r, 0.001, 3000, 9000, 0.8, n)


def ui_kill(r=None):
    r = rng(508)
    t1 = sumv(pingn(2300, 0.014, 0.12, ((1, 1, 1), (2.0, .3, .5))) * 0.8, tickn(r, 0.001, 3000, 9000, 0.7))
    t2 = sumv(pingn(3100, 0.02, 0.16, ((1, 1, 1), (2.0, .35, .5))) * 0.9, tickn(r, 0.001, 3500, 10000, 0.7))
    return mix(0.3, [(t1, 0.0, 0.8), (t2, 0.1, 1.0)])


def render_ui():
    kw = dict(bus='ui', group='weapons', weight=6, max_dist=1000, rate=(1.0, 1.0), tags=['ui', 'battle'])
    for nm, fn, pk in [('ui_flag_capture', ui_flag_capture, -5), ('ui_flag_lost', ui_flag_lost, -6), ('ui_tickets_low', ui_tickets_low, -7),
                       ('ui_respawn', ui_respawn, -6), ('ui_victory', ui_victory, -5), ('ui_defeat', ui_defeat, -6),
                       ('ui_hitmarker', ui_hitmarker, -7), ('ui_kill', ui_kill, -7)]:
        save(nm, fn(), peak=pk, **kw)


def render():
    S.set_manifest('weapons')
    render_guns(); render_handling(); render_shells(); render_passes(); render_impacts(); render_ui()
    import gen_weapons_move, gen_weapons_amb
    gen_weapons_move.render(); gen_weapons_amb.render()


if __name__ == '__main__':
    render()
