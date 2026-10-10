"""Pack Blender-rendered fire layers into looping atlases (WebP), half-size 'low' versions, spread tiles,
ember atlases, the JSON descriptor and the preview sheet.

  python pack_atlas.py WORKDIR GAMEDIR [preset ...]

Reads WORKDIR/<preset>/{flame,smoke,heat}.npy (float16, frames x H x W x 4, premultiplied linear RGBA from
Cycles) + meta.json. Crossfades the tail into the head for a seamless loop, regrades flame hue to a
blackbody-like ramp (blue premixed zones keep their hue), blurs Monte Carlo grain out of smoke/heat,
fades alpha to zero inside the frame on every side (no box edges), and writes straight-alpha WebP.
"""
import sys, os, json, math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

LOOP = 56
COLS = 8
FPS = 24

META = {
    'campfire': dict(light=(1.0, 0.55, 0.22), intensity=2.2, smoke_tone=0.55, desc='campfire / burning barrel (flames 0.8 to 1.2 m)', fuel='wood', haze=(0.45, 0.9, 3.0, 2.0)),
    'gas':      dict(light=(0.55, 0.7, 1.0), intensity=1.4, smoke_tone=0.8, desc='gas burner / jet flame, blue base turning orange', fuel='gas', haze=(0.3, 0.4, 2.0, 2.5)),
    'pool':     dict(light=(1.0, 0.5, 0.18), intensity=3.0, smoke_tone=0.32, desc='sooty fuel / oil pool fire, 3 m across', fuel='liquid', glow=0.35, haze=(0.9, 2.2, 9.0, 3.5)),
    'vehicle':  dict(light=(1.0, 0.5, 0.18), intensity=4.0, smoke_tone=0.38, desc='vehicle fire with a hot engine bay', fuel='vehicle', glow=0.3, haze=(0.85, 2.6, 8.0, 3.2)),
    'building': dict(light=(1.0, 0.48, 0.16), intensity=7.0, smoke_tone=0.42, desc='building fire: window flames and a roof fire', fuel='structure', glow=0.12, haze=(1.0, 5.0, 16.0, 4.0)),
    'grass':    dict(light=(1.0, 0.52, 0.2), intensity=2.0, smoke_tone=0.6, desc='grass / brush fire front, flames 0.3 to 1.5 m', fuel='grass', tile=True, sgain=3.5, haze=(0.35, 3.0, 1.2, 1.2)),
    'fireball': dict(light=(1.0, 0.72, 0.38), intensity=20.0, smoke_tone=0.35, desc='explosion fireball, 8 m class, one-shot 3 s (flash, expansion, rising bubble with smoke head, residue)', fuel='explosion', oneshot=True, sgain=1.4, glow=0.25, haze=(1.0, 10.0, 24.0, 5.0)),
    'trail_slow': dict(light=(1.0, 0.55, 0.2), intensity=0.8, smoke_tone=0.6, desc='carried flame, slow (about 5 m/s relative air), flame bent back along +X', fuel='debris', sgain=1.5, haze=(0.15, 0.5, 1.0, 2.0)),
    'trail_med':  dict(light=(1.0, 0.55, 0.2), intensity=1.0, smoke_tone=0.6, desc='carried flame, medium (about 11 m/s), flame bent back along +X', fuel='debris', sgain=1.5, haze=(0.2, 0.6, 1.2, 2.0)),
    'trail_fast': dict(light=(1.0, 0.55, 0.2), intensity=1.2, smoke_tone=0.6, desc='carried flame, fast (about 20 m/s), long streaming tail along +X', fuel='debris', sgain=1.5, haze=(0.25, 0.8, 1.5, 2.0)),
    'tree':     dict(light=(1.0, 0.5, 0.18), intensity=5.0, smoke_tone=0.4, desc='burning tree: crown and trunk fire (8 by 12 m frame)', fuel='tree', glow=0.1, haze=(0.8, 3.5, 12.0, 3.5)),
}
VARIANTS = [dict(name='A', offset=0, flip=False), dict(name='B', offset=19, flip=True),
            dict(name='C', offset=37, flip=False), dict(name='D', offset=11, flip=True)]
# lifecycle descriptors are parametric curves over the loop atlas (see MODEL-NOTES-FIRE-BLENDER.md)
CLIPS = [
    dict(name='ignite', source='loop', duration=1.5, loop=False, scaleY=[0.12, 1.0], scaleX=[0.45, 1.0], flameGain=[0.0, 1.0], smokeGain=[0.0, 0.6], erosion=[0.55, 0.0]),
    dict(name='growth', source='loop', duration=6.0, loop=False, scaleY=[1.0, 1.0], scaleX=[1.0, 1.0], flameGain=[1.0, 1.0], smokeGain=[0.6, 1.0], erosion=[0.0, 0.0], note='scale the whole sprite with fuel load / area over this time'),
    dict(name='developed', source='loop', duration=2.333, loop=True, scaleY=[1.0, 1.0], scaleX=[1.0, 1.0], flameGain=[1.0, 1.0], smokeGain=[1.0, 1.0], erosion=[0.0, 0.0]),
    dict(name='decay', source='loop', duration=8.0, loop=False, scaleY=[1.0, 0.25], scaleX=[1.0, 0.7], flameGain=[1.0, 0.25], smokeGain=[1.0, 0.35], erosion=[0.0, 0.6], embers=True, note='fuel fades; switch to the embers atlas and thin smoke'),
    dict(name='extinguish', source='loop', duration=1.2, loop=False, scaleY=[1.0, 0.05], scaleX=[1.0, 0.8], flameGain=[1.0, 0.0], smokeGain=[1.0, 2.2], erosion=[0.0, 0.9], steam=True, note='water: flame erodes fast, smoke layer brightens to steam for about 2 s, then thins'),
]
SMOKE_ALPHA_GAIN = 2.0
FLAME_EXPOSURE = 1.0
HEAT_GAIN = 1.0

# ---------------------------------------------------------------- tone mapping
RAMP_L = np.array([0.0, 0.18, 0.40, 0.65, 0.85, 1.0])
RAMP_C = np.array([[0, 0, 0], [0.30, 0.02, 0.0], [0.85, 0.11, 0.0], [1.0, 0.36, 0.03], [1.0, 0.60, 0.12], [1.0, 0.82, 0.34]])

def crossfade_loop(a, n, x):
    out = a[:n].astype(np.float32).copy()
    for i in range(x):
        w = (i + 1) / (x + 1)
        out[i] = (1 - w) * a[n + i].astype(np.float32) + w * a[i].astype(np.float32)
    return out

def tm_flame(f):
    rgb = f[..., :3] * FLAME_EXPOSURE
    rgb = rgb * (1 + rgb / 9.0) / (1 + rgb)
    rgb = np.clip(rgb, 0, 1) ** (1 / 2.2)
    L = rgb.max(axis=-1)
    Lg = np.clip(L * 0.92, 0, 1)
    ramp = np.stack([np.interp(Lg, RAMP_L, RAMP_C[:, c]) for c in range(3)], axis=-1)
    bl = np.clip((rgb[..., 2] - 0.6 * rgb[..., 0]) / (L + 1e-4) * 2.0, 0, 1)[..., None]
    out = ramp * (1 - bl) + rgb * bl
    return np.concatenate([out, out.max(axis=-1, keepdims=True)], axis=-1)

def blur_t(s, sigma_xy, sigma_t):
    return gaussian_filter(s, sigma=(sigma_t, sigma_xy, sigma_xy, 0), mode=('wrap', 'nearest', 'nearest', 'nearest'))

def tm_smoke(s, tone, gain=1.0, glow=0.0):
    a = np.clip(s[..., 3:4] * SMOKE_ALPHA_GAIN * gain, 0, 1)
    rgb = np.clip(s[..., :3], 0, None)
    rgb = rgb * (1 + rgb / 4.0) / (1 + rgb)
    straight = np.where(s[..., 3:4] > 1e-4, rgb / np.maximum(s[..., 3:4], 1e-4), 0)
    straight = np.clip(straight, 0, 1) ** (1 / 2.2)
    lum = straight.mean(axis=-1, keepdims=True) * tone
    straight = np.repeat(lum, 3, axis=-1) * np.array([1.0, 0.98, 0.95])
    if glow > 0:   # soot lit orange from the flames below: subtle emissive tint near the base fading to near-black above
        y = np.linspace(0, 1, s.shape[-3])[None, :, None, None]
        base = ss((y - 0.45) / 0.55)                  # 1 at the bottom, 0 above 45% of the frame height
        straight = straight + glow * base * np.array([1.0, 0.42, 0.10])
    return np.concatenate([np.clip(straight, 0, 1) * a, a], axis=-1)

def tm_heat(h, norm):
    g = np.clip(h[..., :3].mean(axis=-1, keepdims=True) / norm * HEAT_GAIN, 0, 1) ** 0.6
    return np.concatenate([g, g, g, g], axis=-1)

def ss(t):
    t = np.clip(t, 0, 1); return t * t * (3 - 2 * t)

def window(fh, fw, side=0.09, top=0.14, bottom=0.0):
    """Soft alpha window so nothing touches the frame edge (framing, not a mask on content)."""
    x = np.linspace(0, 1, fw)[None, :]; y = np.linspace(0, 1, fh)[:, None]
    w = ss(x / side) * ss((1 - x) / side) * ss(y / top)
    if bottom > 0: w = w * ss((1 - y) / bottom)
    return w[..., None]

def apply_window(a, **kw):
    return a * window(a.shape[1], a.shape[2], **kw)

def downscale2(a):
    n, h, w, c = a.shape
    return a.reshape(n, h // 2, 2, w // 2, 2, c).mean(axis=(2, 4))

# ---------------------------------------------------------------- packing
def to_straight_u8(f):
    f = np.clip(f, 0, 1).copy()
    a = f[..., 3:4]
    f[..., :3] = np.where(a > 1.0 / 512, f[..., :3] / np.maximum(a, 1e-6), 0)
    return (np.clip(f, 0, 1) * 255 + 0.5).astype(np.uint8)

def atlas(frames, cols=COLS):
    n, fh, fw, _ = frames.shape
    rows = int(math.ceil(n / cols))
    img = np.zeros((rows * fh, cols * fw, 4), np.uint8)
    u = to_straight_u8(frames)
    for i in range(n):
        r, c = divmod(i, cols)
        img[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw] = u[i]
    return img, rows

def save_webp(arr, path, budget, opaque_grey=False):
    if opaque_grey:
        g = arr[..., 3]
        im = Image.fromarray(np.stack([g, g, g], axis=-1), 'RGB')
    else:
        im = Image.fromarray(arr, 'RGBA')
    q = 88
    while True:
        im.save(path, 'WEBP', quality=q, alpha_quality=70, method=4)
        sz = os.path.getsize(path)
        if sz <= budget or q <= 40: return sz, q
        q -= 6

def seam_metric(a):
    d_seam = float(np.abs(a[0] - a[-1]).mean())
    d_norm = float(np.mean([np.abs(a[i] - a[i + 1]).mean() for i in range(len(a) - 1)]))
    return d_seam, d_norm

# ---------------------------------------------------------------- derived: tiles, embers
def make_tiles(F, S, Hh):
    """Seamless left-right tile (half the frame width): tile(x) = s*B(x) + (1-s)*B(x+T), s = x/T, so tile(0) == tile(T)."""
    n, fh, fw, _ = F.shape
    T = fw // 2
    s = ss(np.arange(T) / T)[None, None, :, None]
    def tile(B):
        return s * B[:, :, :T] + (1 - s) * B[:, :, T:2 * T]
    tF, tS, tH = tile(F), tile(S), tile(Hh)
    ramp = ss(np.arange(T) / (T * 0.9))[None, None, :, None]
    return dict(tile=tF, tile_smoke=tS, tile_heat=tH, lead=tF * ramp[:, :, ::-1], trail=tF * ramp)

def make_spot(F):
    """Spot fire clip: the lowest, central flames of the tile at a smaller size (crop)."""
    n, fh, fw, _ = F.shape
    cx = fw // 2
    return np.ascontiguousarray(F[:, fh // 2:, cx - fw // 6:cx + fw // 6])

def make_embers(w=64, h=96, n=48, count=34, seed=3):
    """Sparks/embers rising and cooling: ballistic particles with drag, loop-safe (wrapped time). Not Mantaflow."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, h, w, 4), np.float32)
    life = rng.integers(n // 2, n, count)
    t0 = rng.integers(0, n, count)
    x0 = rng.normal(w / 2, w * 0.07, count); vx = rng.normal(0, 0.45, count)
    vy = rng.uniform(1.0, 2.6, count); wob = rng.uniform(0.1, 0.35, count); ph = rng.uniform(0, 6.28, count)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(n):
        for p in range(count):
            age = (i - t0[p]) % n
            if age >= life[p]: continue
            k = age / life[p]
            px = x0[p] + vx[p] * age + math.sin(age * 0.3 + ph[p]) * wob[p] * age * 0.25
            py = h - 6 - vy[p] * age * (1 - 0.35 * k)
            bright = (1 - k) ** 1.5 * (0.75 + 0.25 * math.sin(age * 1.7 + ph[p]))
            col = np.array([1.0, 0.45 + 0.45 * (1 - k), 0.1 + 0.45 * (1 - k) ** 2]) * bright
            d2 = (xx - px) ** 2 + (yy - py) ** 2
            g = np.exp(-d2 / (2 * (0.9 + 0.5 * (1 - k)) ** 2))
            out[i, :, :, :3] += g[..., None] * col
    out[..., :3] = np.clip(out[..., :3], 0, 1)
    out[..., 3] = out[..., :3].max(axis=-1)
    return out

def make_droplets(w=128, h=96, n=40, count=22, seed=11):
    """Burning spatter / thrown fuel: droplets on gravity arcs with short motion streaks. Not Mantaflow."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, h, w, 4), np.float32)
    x0 = rng.normal(w * 0.2, 3, count); vx = rng.uniform(1.2, 3.4, count); vy = rng.uniform(2.0, 4.6, count)
    t0 = rng.integers(0, 6, count); sz = rng.uniform(0.9, 1.7, count)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(n):
        for p in range(count):
            for sub in range(3):                      # three sub-steps give a short motion streak
                t = i - t0[p] - sub * 0.35
                if t < 0: continue
                px = x0[p] + vx[p] * t; py = h - 6 - (vy[p] * t - 0.11 * t * t)
                if py > h - 5 or px >= w: continue
                k = min(1.0, t / 34.0)
                b = (1 - k) ** 1.2 * (1.0 - 0.3 * sub)
                col = np.array([1.0, 0.5 + 0.35 * (1 - k), 0.12 + 0.3 * (1 - k) ** 2]) * b
                g = np.exp(-((xx - px) ** 2 + (yy - py) ** 2) / (2 * sz[p] ** 2))
                out[i, :, :, :3] += g[..., None] * col
    out[..., :3] = np.clip(out[..., :3], 0, 1)
    out[..., 3] = out[..., :3].max(axis=-1)
    return out

def make_streak(w=96, h=24, n=24, seed=2):
    """Ember streak: bright head at the right, tail streaming left (towards the thrown object's past path)."""
    rng = np.random.default_rng(seed)
    out = np.zeros((n, h, w, 4), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    for i in range(n):
        fl = 0.8 + 0.2 * math.sin(i * 1.9) * (0.6 + 0.4 * rng.random())
        d = (w - 8) - xx
        tail = np.exp(-np.clip(d, 0, None) / 28.0) * (d >= 0)
        wob = np.sin(xx * 0.18 + i * 0.7) * 0.9 * (1 - tail)
        g = np.exp(-((yy - h / 2 - wob) ** 2) / (2 * (1.0 + 0.9 * (1 - tail)) ** 2)) * tail * fl
        head = np.exp(-(((xx - (w - 8)) ** 2) / 6.0 + ((yy - h / 2) ** 2) / 3.0)) * fl
        v = np.clip(g * 0.85 + head, 0, 1)
        out[i, :, :, 0] = v; out[i, :, :, 1] = v ** 1.8 * 0.6 + head * 0.35; out[i, :, :, 2] = v ** 5 * 0.25 + head * 0.2
        out[i, :, :, 3] = np.clip(out[i, :, :, :3].max(axis=-1), 0, 1)
    return out

def make_ember_bed(w=128, h=24, n=40, seed=5):
    """Smouldering burnt-ground strip: slow pulsing ember cells, tileable left-right (wrapped noise)."""
    rng = np.random.default_rng(seed)
    base = gaussian_filter(rng.random((h, w)), sigma=(1.2, 1.6), mode=('nearest', 'wrap'))
    base = (base - base.min()) / (base.max() - base.min())
    ph = gaussian_filter(rng.random((h, w)), sigma=(2, 2), mode=('nearest', 'wrap'))
    ph = (ph - ph.min()) / (ph.max() - ph.min()) * 6.28
    out = np.zeros((n, h, w, 4), np.float32)
    yy = np.linspace(0, 1, h)[:, None]
    for i in range(n):
        pulse = 0.5 + 0.5 * np.sin(2 * math.pi * i / n * 2 + ph)
        v = np.clip((base - 0.55) * 4.0, 0, 1) * (0.35 + 0.65 * pulse) * ss(yy * 3) * ss((1 - yy) * 4)
        out[i, :, :, 0] = v; out[i, :, :, 1] = v ** 1.6 * 0.45; out[i, :, :, 2] = v ** 4 * 0.12
        out[i, :, :, 3] = v
    return out

# ---------------------------------------------------------------- main
def main():
    work, game = sys.argv[1], sys.argv[2]
    presets = sys.argv[3:] or list(META)
    outd = os.path.join(game, 'assets', 'fire_blender'); os.makedirs(outd, exist_ok=True)
    jpath = os.path.join(outd, 'fireb_atlas.json')
    doc = json.load(open(jpath)) if os.path.exists(jpath) else {}
    pres = doc.get('presets', {}); extra = doc.get('extras', {})
    seams = {}
    prev = {}

    def write(name, arr_prem, budget, cols=COLS):
        a, rows = atlas(arr_prem, cols)
        path = os.path.join(outd, name + '.webp')
        sz, q = save_webp(a, path, int(budget), opaque_grey='_heat' in name)
        return dict(file=name + '.webp', bytes=sz, grid=[cols, rows], quality=q)

    for p in presets:
        d = os.path.join(work, p)
        meta = json.load(open(os.path.join(d, 'meta.json')))
        fl = np.load(os.path.join(d, 'flame.npy')).astype(np.float32)
        sm = np.load(os.path.join(d, 'smoke.npy')).astype(np.float32)
        ht = np.load(os.path.join(d, 'heat.npy')).astype(np.float32)
        if META[p].get('oneshot'):
            n, x = fl.shape[0], 0
            fl, sm, ht = fl.astype(np.float32), sm.astype(np.float32), ht.astype(np.float32)
        else:
            n = LOOP if fl.shape[0] >= LOOP else fl.shape[0]
            x = fl.shape[0] - n
            fl = crossfade_loop(fl, n, x); sm = crossfade_loop(sm, n, x); ht = crossfade_loop(ht, n, x)
        norm = float(np.percentile(ht[..., :3].mean(axis=-1), 99.7)) or 1.0
        m = META[p]
        sm = blur_t(sm, 1.3, 1.2); ht = blur_t(ht, 0.8, 0.8)
        F = apply_window(tm_flame(fl), top=0.12); S = apply_window(tm_smoke(sm, m['smoke_tone'], m.get('sgain', 1.0), m.get('glow', 0.0)), top=0.18, side=0.12)
        Hh = apply_window(tm_heat(ht, norm), top=0.16, side=0.10)
        seams[p] = dict(flame=seam_metric(F[..., :3]), smoke=seam_metric(S[..., :3]))
        fwid, fhei = F.shape[2], F.shape[1]
        wb = max(1.0, fwid * fhei / (128 * 192))
        files = {}
        for lay, arr, bud in (('flame', F, 340_000 * wb), ('smoke', S, 150_000 * wb), ('heat', Hh, 100_000 * wb)):
            files[lay] = write('fireb_%s_%s' % (p, lay), arr, bud)
            files[lay + '_low'] = write('fireb_%s_%s_low' % (p, lay), downscale2(arr), bud * 0.45)
        e = fl[..., :3].mean(axis=(1, 2, 3)); e = e / max(e.mean(), 1e-6)
        ep = np.concatenate([e[-1:], e, e[:1]]); e = np.convolve(ep, [0.25, 0.5, 0.25], mode='valid')
        pres[p] = dict(desc=m['desc'], fuel=m['fuel'], frames=int(n), loop=not m.get('oneshot', False), frameSize=[fwid, fhei], lowFrameSize=[fwid // 2, fhei // 2],
                       worldWidth=round(meta['worldW'], 3), worldHeight=round(meta['worldH'], 3),
                       anchor=[0.5, 0.0], light=dict(color=list(m['light']), intensity=m['intensity']),
                       flicker=[round(float(v), 3) for v in e], files=files, variants=VARIANTS, clips=CLIPS, resCells=meta['res'],
                       haze=dict(strength=m['haze'][0], radiusM=m['haze'][1], heightM=m['haze'][2], riseSpeed=m['haze'][3]))
        prev[p] = (F, S, Hh)
        print(p, {k: (v['bytes'], v['quality']) for k, v in files.items()})
        if m.get('tile'):
            tl = make_tiles(F, S, Hh)
            tf = {}
            tf['front'] = write('fireb_%s_tile_front' % p, tl['tile'], 300_000)
            tf['front_smoke'] = write('fireb_%s_tile_smoke' % p, tl['tile_smoke'], 100_000)
            tf['lead'] = write('fireb_%s_tile_lead' % p, tl['lead'], 220_000)
            tf['trail'] = write('fireb_%s_tile_trail' % p, tl['trail'], 220_000)
            sp = make_spot(tl['tile'])
            tf['spot'] = write('fireb_%s_spot' % p, sp, 80_000)
            bed = make_ember_bed()
            tf['burnt_bed'] = write('fireb_%s_burnt_strip' % p, bed, 40_000)
            tw = meta['worldW'] / 2
            extra['spread_' + p] = dict(
                desc='tileable fire-front segment, seamless left-right; lead/trail end pieces; spot fire; smouldering burnt strip',
                tileFrameSize=[tl['tile'].shape[2], tl['tile'].shape[1]], tileWorldWidth=round(tw, 3), worldHeight=round(meta['worldH'], 3),
                spotFrameSize=[sp.shape[2], sp.shape[1]], spotWorldWidth=round(tw * sp.shape[2] / tl['tile'].shape[2], 3),
                burntStripFrameSize=[bed.shape[2], bed.shape[1]], burntStripWorldWidth=2.0, burntStripWorldHeight=round(2.0 * bed.shape[1] / bed.shape[2], 3),
                frames=int(n), burntStripFrames=int(bed.shape[0]), files=tf,
                notes='place tiles side by side along the front; lead piece at advancing ends, trail piece at dying ends; burnt strip behind the front; spot clip for spotting ahead of the front')
            prev[p + '_tile'] = (tl['tile'], tl['tile_smoke'], tl['tile_heat'])
    em = make_embers()
    extra['embers'] = dict(desc='rising sparks and embers (additive); numpy ballistic particles, not Mantaflow', frameSize=[em.shape[2], em.shape[1]],
                           frames=int(em.shape[0]), worldWidth=1.0, worldHeight=1.5, anchor=[0.5, 0.0], files=dict(embers=write('fireb_embers', em, 60_000)))
    dr = make_droplets(); st = make_streak()
    extra['spatter'] = dict(desc='burning spatter / thrown fuel droplets on gravity arcs (additive), numpy, not Mantaflow; thrown towards +X from the left', frameSize=[dr.shape[2], dr.shape[1]],
                            frames=int(dr.shape[0]), loop=False, worldWidth=4.0, worldHeight=3.0, anchor=[0.2, 0.0], files=dict(spatter=write('fireb_spatter', dr, 70_000)))
    extra['ember_streak'] = dict(desc='ember streak: head at right edge, tail streaming left; stretch along the velocity vector', frameSize=[st.shape[2], st.shape[1]],
                                 frames=int(st.shape[0]), loop=True, worldWidth=1.2, worldHeight=0.3, anchor=[1.0, 0.5], files=dict(streak=write('fireb_streak', st, 20_000)))
    total_now = sum(f.stat().st_size for f in os.scandir(outd) if f.name.endswith('.webp'))
    out = dict(fps=FPS, loop=True, alphaMode='straight', format='webp',
               notes='All images are STRAIGHT-alpha WebP. Flame/ember/heat: additive (three.js AdditiveBlending = SRC_ALPHA, ONE) reproduces the render; flame colour is hue-normalised with alpha = brightness. Smoke: NormalBlending. Anchor [0.5,0] = bottom centre of the frame. Per-preset frameSize and grid; *_low files are half size.',
               totalBytes=total_now, presets=pres, extras=extra)
    json.dump(out, open(jpath, 'w'), indent=1)
    print('total bytes on disk (webp)', total_now)
    for k, v in seams.items():
        print('seam', k, 'flame seam %.4f vs typical %.4f' % tuple(v['flame']), '| smoke seam %.4f vs typical %.4f' % tuple(v['smoke']))
    make_preview(prev, game)

def make_preview(prev, game):
    names = list(prev)
    bgs = {'dark': np.array([0.03, 0.04, 0.06]), 'day': np.array([0.62, 0.64, 0.66])}
    blocks = []
    for nm in names:
        F, S, Hh = prev[nm]
        n = F.shape[0]
        fh, fw = F.shape[1:3]
        idx4 = [0, n // 4, n // 2, 3 * n // 4]
        def comp(i, bg):
            c = np.ones((fh, fw, 3)) * bg
            c = S[i][..., :3] + c * (1 - S[i][..., 3:4])
            return c + F[i][..., :3]
        row1 = np.concatenate([comp(i, bgs['dark']) for i in idx4] + [comp(i, bgs['day']) for i in idx4], axis=1)
        seam = [comp(n - 1, bgs['dark']), comp(0, bgs['dark'])]
        row2 = np.concatenate([F[idx4[1]][..., :3], F[idx4[3]][..., :3],
                               S[idx4[1]][..., :3] + 0.5 * (1 - S[idx4[1]][..., 3:4]), S[idx4[3]][..., :3] + 0.5 * (1 - S[idx4[3]][..., 3:4]),
                               np.repeat(Hh[idx4[1]][..., :1], 3, -1), np.repeat(Hh[idx4[3]][..., :1], 3, -1)] + seam, axis=1)
        blocks.append(np.concatenate([row1, np.ones((3, row1.shape[1], 3)) * 0.4, row2, np.ones((10, row1.shape[1], 3)) * 0.35], axis=0))
    wmax = max(b.shape[1] for b in blocks)
    blocks = [np.pad(b, ((0, 0), (0, wmax - b.shape[1]), (0, 0)), constant_values=0.2) for b in blocks]
    sheet = (np.clip(np.concatenate(blocks, axis=0), 0, 1) * 255).astype(np.uint8)
    os.makedirs(os.path.join(game, 'docs'), exist_ok=True)
    Image.fromarray(sheet).save(os.path.join(game, 'docs', 'fireb_preview_sheet.png'), optimize=True)
    print('preview', sheet.shape, 'order:', names)

if __name__ == '__main__':
    main()
