#!/usr/bin/env python3
"""Validate a map asset and its capture points.   python check.py lemnos_myrina
Capture points live in points_<id>.json: [{id, type, side(blue|red|None), x, z}, ...]  (game metres, x east, z south)."""
import sys, os, json, base64, math
import numpy as np
from scipy import ndimage
import realmap as R

def load(mid):
    d = json.load(open(os.path.join(R.ASSETS, f'map_{mid}.json'), encoding='utf8'))
    h = np.frombuffer(base64.b64decode(d['h']), dtype='<f4').reshape(R.N, R.N)
    return d, h

def sample(h, cell, x, z):
    fx, fz = x / cell + 128, z / cell + 128; j, i = int(math.floor(fx)), int(math.floor(fz)); a, b = fx - j, fz - i
    return (h[i, j] * (1 - a) + h[i, j + 1] * a) * (1 - b) + (h[i + 1, j] * (1 - a) + h[i + 1, j + 1] * a) * b

def seg_dist(px, pz, p):
    best = 1e9
    for k in range(0, len(p) - 2, 2):
        ax, az, bx, bz = p[k], p[k + 1], p[k + 2], p[k + 3]; dx, dz = bx - ax, bz - az; L = dx * dx + dz * dz
        t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (pz - az) * dz) / L)); best = min(best, math.hypot(px - ax - t * dx, pz - az - t * dz))
    return best

def snap(mid, radius=150, maxslope=13):
    """Move each capture point to the nearest flat, dry, main-component cell (max slope within 12 m < maxslope, >= 1.5 m above sea)."""
    d, h = load(mid); cell = d['cell_m']; sl = R.slope_deg(h, cell)
    r = max(1, int(12 / cell)); mx = ndimage.maximum_filter(sl, size=2 * r + 1)
    ok = (h > 1.5) & (mx < maxslope)
    lab, n = ndimage.label((h > 0.05) & (sl < 30)); main = np.argmax(np.bincount(lab.ravel())[1:]) + 1
    ok &= lab == main
    from PIL import Image, ImageDraw
    im = Image.new('L', (R.N, R.N), 0); dr = ImageDraw.Draw(im)
    for b in d['buildings']: dr.polygon([((b['p'][k] / cell) + 128, (b['p'][k + 1] / cell) + 128) for k in range(0, len(b['p']), 2)], fill=1)
    for hb in d['harbour']:
        if hb['k'] not in ('quay',): dr.line([((hb['p'][k] / cell) + 128, (hb['p'][k + 1] / cell) + 128) for k in range(0, len(hb['p']), 2)], fill=1, width=1)
    bm = ndimage.binary_dilation(np.asarray(im).astype(bool), iterations=max(1, int(6 / cell)))
    ok &= ~bm
    pf = os.path.join(R.HERE, f'points_{mid}.json'); pts = json.load(open(pf))
    taken = []
    for p in pts:
        ii, jj = np.nonzero(ok)
        X = (jj - 128) * cell; Z = (ii - 128) * cell
        dist = np.hypot(X - p['x'], Z - p['z'])
        for q in taken: dist = np.where(np.hypot(X - q[0], Z - q[1]) < 60, 1e9, dist)
        k = int(dist.argmin())
        if dist[k] < radius:
            p['x'], p['z'] = float(round(X[k], 0)), float(round(Z[k], 0))
        else: print('  could not snap', p['id'])
        taken.append((p['x'], p['z']))
    json.dump(pts, open(pf, 'w'), indent=0); print('snapped', len(pts), 'points')

def main(mid):
    d, h = load(mid); cell = d['cell_m']
    print(mid, 'size', d['size_m'], 'cell', cell, 'h range', float(h.min()), float(h.max()), 'json KB', os.path.getsize(os.path.join(R.ASSETS, f'map_{mid}.json')) // 1024)
    sl = R.slope_deg(h, cell); land = h > 0.05
    walk = land & (sl < 30)
    lab, n = ndimage.label(walk)
    pf = os.path.join(R.HERE, f'points_{mid}.json')
    if not os.path.exists(pf): return
    pts = json.load(open(pf)); ok = True
    for p in pts:
        j, i = int(round(p['x'] / cell + 128)), int(round(p['z'] / cell + 128))
        hh = sample(h, cell, p['x'], p['z']); s = sl[i, j]
        # slope in a 15 m radius
        r = int(15 / cell); win = sl[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1]
        rd = min([seg_dist(p['x'], p['z'], rr['p']) for rr in d['roads'] if rr['c'] not in ('footway', 'path', 'steps')] + [1e9])
        water_near = (h[max(0, i - r):i + r + 1, max(0, j - r):j + r + 1] <= 0.05).mean()
        comp = lab[i, j]
        p['_comp'] = int(comp)
        flag = []
        if hh <= 0.3: flag.append('WET')
        if win.max() > 20: flag.append('steep>20deg(15m)')
        if comp == 0: flag.append('not-walkable')
        print(f"  {p['id']:<4}{p['type']:<11}{str(p.get('side')):<5} x={p['x']:>7.0f} z={p['z']:>7.0f}  h={hh:5.1f} m  slope={s:4.1f} (max15m {win.max():4.1f})  road={rd:5.0f} m  water15={water_near:.2f}  comp={comp}  {' '.join(flag)}")
        ok &= not flag
    comps = {p['_comp'] for p in pts}
    print('  all points in one walkable component' if len(comps) == 1 else f'  WARNING: points span components {comps}', '| clean' if ok else '| has flags')
    d2 = [p for p in pts]
    R.render_preview(os.path.join(R.PREV, f'{mid}_points.png'), h, h <= 0, {k: d[k] for k in ('landcover', 'water_lines', 'harbour', 'aeroways', 'roads', 'buildings', 'towers')},
                     d['size_m'], cell, ppm=2.0, points=d2, title=mid + ' capture points (blue/red)')

if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[2] == 'snap': snap(sys.argv[1])
    main(sys.argv[1])
