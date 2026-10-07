#!/usr/bin/env python3
"""Squall Cove real-place map pipeline (open data only).

  python realmap.py build lemnos_myrina 39.8715 25.0640 [--size 768]
  python realmap.py scan  scan_mudros   39.8800 25.2700 --size 3072   (preview only)
  python realmap.py check lemnos_myrina                               (validate an asset + capture points)

Game conventions (matched to index.html: TN=257, TH=128, CELL=3 on battle maps):
  grid cell (i,j) -> world x = (j-128)*cell, z = (i-128)*cell ; x east, z SOUTH ; origin = map centre
  heights row-major  h[i*257+j]  (i = row = z index).  Sea level 0 m.

Data: OpenStreetMap contributors (ODbL), Mapzen terrain tiles (SRTM, GMTED, NED, etc.)
"""
import sys, os, io, json, math, time, base64, hashlib, argparse
import urllib.request, urllib.parse, urllib.error
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
PREV = os.path.join(HERE, 'preview')
ASSETS = os.path.normpath(os.path.join(HERE, '..', '..', 'assets'))
UA = 'SquallCoveMapTool/1.0 (personal game)'
ATTR_OSM = 'Map data (c) OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).'
ATTR_DEM = 'Terrain data from Mapzen terrain tiles (SRTM, GMTED, NED, etc.)'
ATTRIBUTION = ATTR_OSM + ' ' + ATTR_DEM
R_EARTH = 6371008.8
N = 257
os.makedirs(CACHE, exist_ok=True); os.makedirs(PREV, exist_ok=True)

# ---------------------------------------------------------------- projection
class Proj:
    """Local equirectangular frame: x east, z south, metres, origin at (lat0,lon0)."""
    def __init__(s, lat0, lon0):
        s.lat0, s.lon0 = lat0, lon0
        s.kx = math.radians(1) * R_EARTH * math.cos(math.radians(lat0)); s.kz = math.radians(1) * R_EARTH
    def fwd(s, lat, lon): return ((lon - s.lon0) * s.kx, -(lat - s.lat0) * s.kz)
    def inv(s, x, z): return (s.lat0 - np.asarray(z) / s.kz, s.lon0 + np.asarray(x) / s.kx)

# ---------------------------------------------------------------- http + cache
_last = [0.0]
def http(url, data=None, headers=None, binary=False, wait=0.0, tries=4):
    h = {'User-Agent': UA}; h.update(headers or {})
    for t in range(tries):
        dt = time.time() - _last[0]
        if dt < wait: time.sleep(wait - dt)
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=120) as r: b = r.read()
            _last[0] = time.time(); return b if binary else b.decode('utf8')
        except Exception as e:
            _last[0] = time.time(); print('   http retry', t, url[:70], e); time.sleep(6 * (t + 1))
    raise RuntimeError('network failure ' + url)

def cached(name, fn, binary=False):
    p = os.path.join(CACHE, name)
    if os.path.exists(p):
        return open(p, 'rb').read() if binary else open(p, encoding='utf8').read()
    v = fn(); open(p, 'wb' if binary else 'w', **({} if binary else {'encoding': 'utf8'})).write(v); return v

# ---------------------------------------------------------------- DEM
def merc_px(lat, lon, z):
    n = 256 * 2 ** z
    x = (np.asarray(lon) + 180.0) / 360.0 * n
    la = np.radians(lat)
    y = (1 - np.log(np.tan(la) + 1 / np.cos(la)) / math.pi) / 2 * n
    return x, y

def terrarium_tile(z, x, y):
    url = f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'
    b = cached(f'dem_{z}_{x}_{y}.png', lambda: http(url, binary=True, wait=0.2), binary=True)
    a = np.asarray(Image.open(io.BytesIO(b)).convert('RGB')).astype(np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768

def fetch_dem(lat0, lon0, size_m=768.0, cell_m=None, z=14, margin=4):
    """Metres array (N x N) of elevation, resampled at cell_m (default size/256), z south, x east. Raw (no sea shaping)."""
    cell_m = cell_m or size_m / (N - 1)
    P = Proj(lat0, lon0)
    j = np.arange(N); xs = (j - 128) * cell_m
    X, Z = np.meshgrid(xs, xs)
    lat, lon = P.inv(X, Z)
    px, py = merc_px(lat, lon, z)
    x0, x1 = int(px.min() // 256) - 0, int(px.max() // 256); y0, y1 = int(py.min() // 256), int(py.max() // 256)
    mos = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256))
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            mos[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = terrarium_tile(z, tx, ty)
    # pixel centres at +0.5
    coords = np.array([py - y0 * 256 - 0.5, px - x0 * 256 - 0.5])
    h = ndimage.map_coordinates(mos, coords, order=3, mode='nearest')
    return h

# ---------------------------------------------------------------- OSM
def overpass_queries(S, W, Nn, E, big=None):
    b = f'({S:.6f},{W:.6f},{Nn:.6f},{E:.6f})'
    groups = [
        [f'way["highway"]{b};', f'way["railway"]{b};'],
        [f'way["building"]{b};'],
        [f'way["landuse"]{b};', f'way["natural"]["natural"!="coastline"]{b};', f'way["leisure"~"park|pitch|stadium|garden|marina|golf_course|sports_centre|playground"]{b};'],
        [f'relation["natural"~"water|bay|wood|scrub|beach"]{b};', f'relation["landuse"]{b};', f'relation["building"]{b};'],
        [f'way["waterway"]{b};'], [f'way["man_made"]{b};'], [f'way["aeroway"]{b};'], [f'way["harbour"]{b};'], [f'way["military"]{b};'],
        [f'way["power"~"line|minor_line"]{b};'], [f'way["barrier"~"wall|fence"]{b};'], [f'way["amenity"~"parking|fuel|place_of_worship|school|hospital|townhall|marketplace"]{b};'],
        [f'node["man_made"~"water_tower|tower|lighthouse|mast|chimney|storage_tank|crane|windmill|silo|pier"]{b};', f'node["power"~"tower|generator"]{b};',
         f'node["place"]{b};', f'node["natural"~"peak|cape|bay|beach"]{b};', f'node["aeroway"]{b};', f'node["amenity"~"fuel|place_of_worship|ferry_terminal"]{b};',
         f'node["historic"]{b};', f'node["military"]{b};'],
    ]
    qs = ['[out:json][timeout:120];(' + chr(10).join(g) + ');out geom;' for g in groups]
    bb = '(%.6f,%.6f,%.6f,%.6f)' % big
    qs.append('[out:json][timeout:120];(way["natural"="coastline"]%s;);out geom%s;' % (b, bb))   # geometry clipped to a wider box
    return qs

def fetch_osm_raw(lat0, lon0, size_m, margin=60):
    P = Proj(lat0, lon0); h = size_m / 2 + margin
    S, _ = P.inv(0, h); Nn, _ = P.inv(0, -h); _, W = P.inv(-h, 0); _, E = P.inv(h, 0)
    els = {}
    big = (S - 0.02, W - 0.025, Nn + 0.02, E + 0.025)
    for q in overpass_queries(S, W, Nn, E, big):
        key = hashlib.md5(q.encode()).hexdigest()[:12]
        def go():
            last = None
            for ep in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']:
                try: return http(ep, data=urllib.parse.urlencode({'data': q}).encode(), wait=3.0, tries=2)
                except Exception as e: last = e
            raise last
        try: txt = cached(f'osm_{key}.json', go)
        except Exception as ex: print('   !! group failed, skipped:', q[:90].replace(chr(10), ' '), ex); continue
        for e in json.loads(txt)['elements']: els[(e['type'], e['id'])] = e
        print('   osm group', key, len(els), flush=True)
    return {'elements': list(els.values())}

def join_rings(ways):
    """Join open way geometries (lists of (lat,lon)) into closed rings."""
    ways = [list(w) for w in ways if len(w) >= 2]; rings = []
    key = lambda p: (round(p[0], 7), round(p[1], 7))
    while ways:
        cur = ways.pop()
        grown = True
        while grown and key(cur[0]) != key(cur[-1]):
            grown = False
            for i, w in enumerate(ways):
                if key(w[0]) == key(cur[-1]): cur += w[1:]
                elif key(w[-1]) == key(cur[-1]): cur += w[::-1][1:]
                elif key(w[-1]) == key(cur[0]): cur = w[:-1] + cur
                elif key(w[0]) == key(cur[0]): cur = w[::-1][:-1] + cur
                else: continue
                ways.pop(i); grown = True; break
        rings.append(cur)
    return [r for r in rings if len(r) >= 4 and key(r[0]) == key(r[-1])]

def geom_ll(g): return [(p['lat'], p['lon']) for p in g if p]

LAND_CLASS = {
    # landuse
    ('landuse', 'forest'): 'forest', ('landuse', 'farmland'): 'farmland', ('landuse', 'meadow'): 'grass', ('landuse', 'grass'): 'grass',
    ('landuse', 'orchard'): 'orchard', ('landuse', 'vineyard'): 'vineyard', ('landuse', 'residential'): 'urban', ('landuse', 'commercial'): 'urban',
    ('landuse', 'retail'): 'urban', ('landuse', 'industrial'): 'industrial', ('landuse', 'military'): 'military', ('landuse', 'harbour'): 'harbour',
    ('landuse', 'port'): 'harbour', ('landuse', 'quarry'): 'rock', ('landuse', 'cemetery'): 'cemetery', ('landuse', 'brownfield'): 'bare',
    ('landuse', 'construction'): 'bare', ('landuse', 'farmyard'): 'farmland', ('landuse', 'allotments'): 'farmland', ('landuse', 'religious'): 'urban',
    ('landuse', 'basin'): 'water', ('landuse', 'reservoir'): 'water', ('landuse', 'recreation_ground'): 'grass', ('landuse', 'village_green'): 'grass',
    ('landuse', 'greenfield'): 'grass', ('landuse', 'landfill'): 'bare', ('landuse', 'railway'): 'bare',
    # natural
    ('natural', 'wood'): 'forest', ('natural', 'scrub'): 'scrub', ('natural', 'heath'): 'scrub', ('natural', 'grassland'): 'grass',
    ('natural', 'beach'): 'beach', ('natural', 'sand'): 'beach', ('natural', 'bare_rock'): 'rock', ('natural', 'rock'): 'rock', ('natural', 'scree'): 'rock',
    ('natural', 'cliff'): 'rock', ('natural', 'water'): 'water', ('natural', 'wetland'): 'wetland', ('natural', 'bay'): 'bay', ('natural', 'shingle'): 'beach',
    ('natural', 'fell'): 'scrub', ('natural', 'mud'): 'wetland', ('natural', 'coastline'): None, ('natural', 'tree_row'): None,
    ('leisure', 'park'): 'grass', ('leisure', 'garden'): 'grass', ('leisure', 'pitch'): 'pitch', ('leisure', 'stadium'): 'pitch', ('leisure', 'sports_centre'): 'pitch',
    ('leisure', 'golf_course'): 'grass', ('leisure', 'marina'): 'harbour', ('leisure', 'playground'): 'pitch',
    ('amenity', 'parking'): 'parking', ('aeroway', 'aerodrome'): 'airfield', ('aeroway', 'apron'): 'apron', ('aeroway', 'runway'): 'runway_area',
    ('aeroway', 'taxiway'): 'taxiway_area', ('aeroway', 'helipad'): 'apron',
}

def classify_building(tags):
    b = tags.get('building', 'yes'); name = (tags.get('name', '') + ' ' + tags.get('name:en', '')).lower()
    mil = 'military' in tags
    if b in ('hangar',) or tags.get('aeroway') == 'hangar': return 'hangar'
    if b in ('warehouse', 'industrial', 'factory', 'manufacture', 'storage_tank_building'): return 'warehouse'
    if b in ('silo', 'grain_silo') or tags.get('man_made') == 'silo': return 'silo'
    if b in ('storage_tank',) or tags.get('man_made') == 'storage_tank': return 'fuel_tank'
    if b in ('commercial', 'retail', 'office', 'hotel', 'public', 'civic', 'government', 'hospital', 'school', 'university', 'supermarket', 'kindergarten', 'train_station', 'transportation', 'dormitory'): return 'office'
    if b in ('garage', 'garages', 'shed', 'hut', 'cabin', 'service', 'carport', 'roof', 'greenhouse', 'barn', 'farm_auxiliary', 'stable', 'boathouse', 'kiosk', 'container'): return 'workshop'
    if b in ('bunker',) or mil: return 'bunker' if b == 'bunker' else 'guardhouse'
    if b in ('tower', 'watchtower') or tags.get('man_made') in ('tower', 'watchtower'): return 'watchtower'
    if b in ('church', 'chapel', 'cathedral', 'monastery', 'mosque'): return 'house_c'
    if b in ('apartments', 'residential', 'terrace'): return 'office' if tags.get('building:levels', '1') not in ('1', '2') else 'house_b'
    if b in ('ruins', 'collapsed'): return 'ruin'
    return None   # decided from footprint size by caller (house_a/b/c, workshop)

def poly_area(pts):
    a = 0.0
    for k in range(len(pts)):
        x0, z0 = pts[k]; x1, z1 = pts[(k + 1) % len(pts)]; a += x0 * z1 - x1 * z0
    return a / 2

def min_rect(pts):
    """Min-area bounding rectangle -> (cx, cz, w, d, rot) with w the long side... rot = angle of long axis in radians from +x toward +z."""
    P = np.array(pts);
    if len(P) < 3: return None
    from scipy.spatial import ConvexHull
    try: H = P[ConvexHull(P).vertices]
    except Exception: return None
    best = None
    for k in range(len(H)):
        e = H[(k + 1) % len(H)] - H[k]; L = np.hypot(*e)
        if L < 1e-6: continue
        c, s = e[0] / L, e[1] / L
        u = H @ np.array([c, s]); v = H @ np.array([-s, c])
        w, d = u.max() - u.min(), v.max() - v.min()
        if best is None or w * d < best[0]:
            cu, cv = (u.max() + u.min()) / 2, (v.max() + v.min()) / 2
            best = (w * d, cu * c - cv * s, cu * s + cv * c, w, d, math.atan2(s, c))
    _, cx, cz, w, d, rot = best
    if d > w: w, d = d, w; rot += math.pi / 2
    rot = (rot + math.pi) % math.pi
    return cx, cz, w, d, rot

def num(v, dflt):
    try: return float(str(v).replace('m', '').strip())
    except Exception: return float(dflt)

def rd(v, n=1): return round(float(v), n)
def flat(pts, n=1): return [rd(c, n) for p in pts for c in p]

def clip_poly(pts, xmin, zmin, xmax, zmax):
    def clip(poly, inside, inter):
        out = []
        for i in range(len(poly)):
            a, b = poly[i - 1], poly[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia: out.append(inter(a, b))
                out.append(b)
            elif ia: out.append(inter(a, b))
        return out
    def ix(xc): return lambda a, b: (xc, a[1] + (b[1] - a[1]) * (xc - a[0]) / (b[0] - a[0]))
    def iz(zc): return lambda a, b: (a[0] + (b[0] - a[0]) * (zc - a[1]) / (b[1] - a[1]), zc)
    p = list(pts)
    for ins, itr in [(lambda a: a[0] >= xmin, ix(xmin)), (lambda a: a[0] <= xmax, ix(xmax)), (lambda a: a[1] >= zmin, iz(zmin)), (lambda a: a[1] <= zmax, iz(zmax))]:
        if not p: break
        p = clip(p, ins, itr)
    return p

def clip_line(pts, xmin, zmin, xmax, zmax):
    """Liang-Barsky on each segment, return list of polylines."""
    outs = []; cur = []
    for k in range(len(pts) - 1):
        x0, z0 = pts[k]; x1, z1 = pts[k + 1]; dx, dz = x1 - x0, z1 - z0; t0, t1 = 0.0, 1.0; ok = True
        for p_, q_ in ((-dx, x0 - xmin), (dx, xmax - x0), (-dz, z0 - zmin), (dz, zmax - z0)):
            if p_ == 0:
                if q_ < 0: ok = False; break
            else:
                t = q_ / p_
                if p_ < 0:
                    if t > t1: ok = False; break
                    t0 = max(t0, t)
                else:
                    if t < t0: ok = False; break
                    t1 = min(t1, t)
        if not ok:
            if len(cur) > 1: outs.append(cur)
            cur = []; continue
        a = (x0 + t0 * dx, z0 + t0 * dz); b = (x0 + t1 * dx, z0 + t1 * dz)
        if not cur: cur = [a]
        elif math.hypot(cur[-1][0] - a[0], cur[-1][1] - a[1]) > 1e-6:
            outs.append(cur); cur = [a]
        cur.append(b)
        if t1 < 1.0: outs.append(cur); cur = []
    if len(cur) > 1: outs.append(cur)
    return outs

def simplify(pts, tol):
    """Douglas-Peucker (iterative)."""
    if len(pts) < 3: return pts
    P = np.array(pts); keep = np.zeros(len(P), bool); keep[0] = keep[-1] = True; st = [(0, len(P) - 1)]
    while st:
        a, b = st.pop()
        if b <= a + 1: continue
        d = P[b] - P[a]; L = np.hypot(*d)
        seg = P[a + 1:b] - P[a]
        dist = np.hypot(*seg.T) if L < 1e-9 else np.abs(d[0] * seg[:, 1] - d[1] * seg[:, 0]) / L
        k = int(dist.argmax())
        if dist[k] > tol: keep[a + 1 + k] = True; st += [(a, a + 1 + k), (a + 1 + k, b)]
    return [tuple(p) for p in P[keep]]

HW_WIDTH = {'motorway': 9, 'trunk': 9, 'primary': 8, 'secondary': 7, 'tertiary': 6, 'unclassified': 5, 'residential': 5, 'living_street': 4,
            'service': 3.5, 'track': 3.5, 'path': 1.5, 'footway': 1.5, 'steps': 1.5, 'cycleway': 2, 'pedestrian': 4, 'road': 5, 'bridleway': 1.5}

def process_osm(raw, P, size_m):
    half = size_m / 2; pad = 0.0
    inwin = lambda x, z: -half <= x <= half and -half <= z <= half
    def loc(g): return [P.fwd(*p) for p in geom_ll(g)]
    out = dict(roads=[], buildings=[], landcover=[], coast=[], harbour=[], aeroways=[], towers=[], places=[], barriers=[], power=[], rail=[], water_lines=[], poi=[])
    water_polys = []
    for e in raw['elements']:
        tags = e.get('tags', {}); t = e['type']
        if t == 'way':
            if 'geometry' not in e: continue
            pts = loc(e['geometry'])
            if len(pts) < 2: continue
            closed = len(pts) > 3 and pts[0] == pts[-1]
            if 'highway' in tags and tags.get('area') != 'yes' and tags['highway'] not in ('proposed', 'construction', 'corridor', 'platform'):
                for seg in clip_line(pts, -half, -half, half, half):
                    seg = simplify(seg, 0.6)
                    out['roads'].append(dict(c=tags['highway'], n=tags.get('name:en') or tags.get('name', ''), w=HW_WIDTH.get(tags['highway'], 4),
                                             s=tags.get('surface', ''), br=int('bridge' in tags), tn=int('tunnel' in tags), oneway=int(tags.get('oneway') in ('yes', '1')), p=flat(seg)))
                continue
            if tags.get('natural') == 'coastline':
                out['coast'].append(pts); continue   # clipped later (needed outside window for the land/sea test)
            if tags.get('aeroway') in ('runway', 'taxiway', 'taxilane'):
                for seg in clip_line(pts, -half, -half, half, half):
                    out['aeroways'].append(dict(k=tags['aeroway'], ref=tags.get('ref', ''), w=num(tags.get('width'), 45 if tags['aeroway'] == 'runway' else 18), p=flat(seg)))
                continue
            if tags.get('man_made') in ('pier', 'breakwater', 'groyne', 'quay', 'jetty', 'dyke') or tags.get('harbour') or tags.get('waterway') == 'dock' or tags.get('leisure') == 'marina' and not closed:
                k = tags.get('man_made') or tags.get('waterway') or 'harbour'
                for seg in clip_line(pts, -half, -half, half, half):
                    out['harbour'].append(dict(k=k, n=tags.get('name', ''), w=num(tags.get('width'), 5), p=flat(simplify(seg, 0.5)), closed=int(closed)))
                if not closed: continue
            if tags.get('waterway') in ('river', 'stream', 'canal', 'ditch', 'drain'):
                for seg in clip_line(pts, -half, -half, half, half):
                    out['water_lines'].append(dict(k=tags['waterway'], n=tags.get('name', ''), p=flat(simplify(seg, 0.8))))
                continue
            if 'power' in tags and tags['power'] in ('line', 'minor_line'):
                for seg in clip_line(pts, -half, -half, half, half):
                    out['power'].append(dict(p=flat(simplify(seg, 1.0))))
                continue
            if 'railway' in tags and not closed:
                for seg in clip_line(pts, -half, -half, half, half):
                    out['rail'].append(dict(k=tags['railway'], p=flat(seg)))
                continue
            if tags.get('barrier') in ('wall', 'fence') and not tags.get('building'):
                for seg in clip_line(pts, -half, -half, half, half):
                    out['barriers'].append(dict(k=tags['barrier'], p=flat(simplify(seg, 0.6))))
                continue
            if closed and 'building' in tags and tags.get('building') != 'no':
                add_building(out, pts[:-1], tags, inwin); continue
            if closed and tags.get('man_made') in ('storage_tank', 'silo', 'water_tower', 'tower', 'chimney') and not 'building' in tags:
                cx = np.mean([p[0] for p in pts]); cz = np.mean([p[1] for p in pts])
                if inwin(cx, cz): out['towers'].append(dict(k=tags['man_made'], n=tags.get('name', ''), h=tags.get('height', ''), x=rd(cx), z=rd(cz), r=rd(math.sqrt(abs(poly_area(pts[:-1])) / math.pi))))
                continue
            if closed:
                add_landcover(out, pts[:-1], tags, half, water_polys)
            elif tags.get('natural') in ('cliff',):
                pass
        elif t == 'node':
            x, z = P.fwd(e['lat'], e['lon'])
            if not inwin(x, z): continue
            if 'place' in tags: out['places'].append(dict(k=tags['place'], n=tags.get('name:en') or tags.get('name', ''), x=rd(x), z=rd(z)))
            mm = tags.get('man_made'); pw = tags.get('power')
            if mm in ('water_tower', 'tower', 'lighthouse', 'mast', 'chimney', 'storage_tank', 'crane', 'windmill', 'silo') or pw in ('tower',) or (pw == 'generator' and tags.get('generator:source') == 'wind'):
                out['towers'].append(dict(k=mm or ('wind_turbine' if pw == 'generator' else 'power_tower'), n=tags.get('name', ''), h=tags.get('height', ''), x=rd(x), z=rd(z), r=0))
            elif tags.get('natural') in ('peak', 'cape', 'bay', 'beach'): out['poi'].append(dict(k=tags['natural'], n=tags.get('name:en') or tags.get('name', ''), ele=tags.get('ele', ''), x=rd(x), z=rd(z)))
            elif tags.get('aeroway') or tags.get('amenity') or tags.get('historic') or tags.get('military'):
                out['poi'].append(dict(k=tags.get('aeroway') or tags.get('amenity') or tags.get('historic') or tags.get('military'), n=tags.get('name:en') or tags.get('name', ''), x=rd(x), z=rd(z)))
        elif t == 'relation':
            outer = [geom_ll(m['geometry']) for m in e.get('members', []) if m.get('role') == 'outer' and m['type'] == 'way' and 'geometry' in m]
            inner = [geom_ll(m['geometry']) for m in e.get('members', []) if m.get('role') == 'inner' and m['type'] == 'way' and 'geometry' in m]
            rings = join_rings(outer)
            for r in rings:
                pts = [P.fwd(*p) for p in r][:-1]
                if 'building' in tags: add_building(out, pts, tags, inwin)
                else: add_landcover(out, pts, tags, half, water_polys, holes=[[P.fwd(*p) for p in ih] for ih in join_rings(inner)])
    out['_water_polys'] = water_polys
    return out

def add_building(out, pts, tags, inwin):
    if len(pts) < 3: return
    mr = min_rect(pts)
    if not mr: return
    cx, cz, w, d, rot = mr
    if not inwin(cx, cz): return
    area = abs(poly_area(pts))
    if area < 6: return
    if area > 12000:   # castle/site outlines etc. are not single buildings: keep as a landcover site
        out['landcover'].append(dict(k='site', n=tags.get('name:en') or tags.get('name', ''), a=rd(area, 0), p=flat(simplify(pts + [pts[0]], 1.0)[:-1]))); return
    cat = classify_building(tags)
    lv = tags.get('building:levels'); ht = tags.get('height') or tags.get('building:height')
    try: lv = float(lv) if lv else 0
    except ValueError: lv = 0
    try: ht = float(str(ht).replace('m', '').strip()) if ht else 0
    except ValueError: ht = 0
    out['buildings'].append(dict(t=tags.get('building', 'yes'), m=cat or '', lv=lv, ht=ht, n=tags.get('name:en') or tags.get('name', ''),
                                 cx=rd(cx), cz=rd(cz), w=rd(w), d=rd(d), rot=rd(rot, 3), a=rd(area, 0), p=flat(simplify(pts + [pts[0]], 0.3)[:-1])))

def add_landcover(out, pts, tags, half, water_polys, holes=None):
    cls = None
    for key in ('landuse', 'natural', 'leisure', 'amenity', 'aeroway'):
        if key in tags and (key, tags[key]) in LAND_CLASS:
            cls = LAND_CLASS[(key, tags[key])]
            if cls: break
    if tags.get('waterway') == 'riverbank': cls = 'water'
    if tags.get('natural') == 'water' and tags.get('water') in ('lagoon', 'bay', 'sea') : cls = 'water'
    if not cls: return
    if abs(poly_area(pts)) < 30: return
    if cls in ('water', 'bay'): water_polys.append((pts, cls))
    cp = clip_poly(pts, -half, -half, half, half)
    if len(cp) < 3: return
    out['landcover'].append(dict(k=cls, a=rd(abs(poly_area(pts)), 0), p=flat(simplify(cp + [cp[0]], 0.8)[:-1])))

# ---------------------------------------------------------------- heightfield shaping
def densify(poly, step=2.0):
    P = np.array(poly); pts = []; tans = []
    for k in range(len(P) - 1):
        d = P[k + 1] - P[k]; L = np.hypot(*d)
        if L < 1e-9: continue
        n = max(1, int(L // step)); t = d / L
        for s in range(n):
            pts.append(P[k] + d * (s / n)); tans.append(t)
    return pts, tans

def rasterise_poly(mask, pts, cell, val=True):
    im = Image.new('L', (N, N), 0); dr = ImageDraw.Draw(im)
    dr.polygon([((x / cell) + 128, (z / cell) + 128) for x, z in pts], fill=1)
    mask |= np.asarray(im).astype(bool)

def shape_heights(dem, osm, cell_m, size_m):
    """Return (h, info). Sea at 0, sea floor shaped by distance from shore, land >= 0.25."""
    j = np.arange(N); xs = (j - 128) * cell_m; X, Z = np.meshgrid(xs, xs)
    pts, tans = [], []
    for c in osm['coast']:
        a, b = densify(c, 2.0); pts += a; tans += b
    info = {}
    if pts:
        pts = np.array(pts); tans = np.array(tans); tree = cKDTree(pts)
        dist, idx = tree.query(np.c_[X.ravel(), Z.ravel()])
        q = pts[idx]; t = tans[idx]
        # OSM: land on the left of way direction. Our frame has z SOUTH, so flip z to get a y-north frame.
        px, py = X.ravel() - q[:, 0], -(Z.ravel() - q[:, 1]); tx, ty = t[:, 0], -t[:, 1]
        left = (tx * py - ty * px) > 0
        land = left.reshape(N, N)
        near = dist.reshape(N, N) < 3000
        # trust the coastline only if it is actually near; otherwise fall back to the DEM
        land = np.where(near, land, dem > 0.5)
        info['coast_pts'] = len(pts)
    else:
        land = np.ones((N, N), bool); info['coast_pts'] = 0
    # inland water polygons (lakes, salt pans) become shallow water
    lake = np.zeros((N, N), bool)
    for poly, cls in osm['_water_polys']:
        if cls == 'water' and len(poly) > 3 and abs(poly_area(poly)) > 400: rasterise_poly(lake, poly, cell_m)
    lake &= land   # coastline already handles real sea
    h = dem.copy()
    h = ndimage.gaussian_filter(h, 1.0)
    h = np.maximum(h, 0.25)
    water = (~land) | lake
    d_to_land = ndimage.distance_transform_edt(water) * cell_m         # metres to nearest dry cell
    cap = np.where(lake & land, 2.5, 9.0)
    depth = np.minimum(cap, 0.35 + d_to_land * 0.055)
    # a little deterministic undulation so the sea floor is not a perfect ramp
    rng = np.random.default_rng(7); noise = ndimage.gaussian_filter(rng.standard_normal((N, N)), 8); noise /= max(1e-6, abs(noise).max())
    depth = np.clip(depth * (1 + 0.12 * noise), 0.3, np.minimum(cap, 9.0))
    h = np.where(water, -depth, h)
    sm = ndimage.gaussian_filter(h, 1.0)
    h = np.where(water, np.minimum(sm, -0.2), np.maximum(sm, 0.25))
    info['water_frac'] = float(water.mean()); info['lake_frac'] = float(lake.mean())
    return h.astype(np.float32), water, info

def slope_deg(h, cell):
    gz, gx = np.gradient(h, cell); return np.degrees(np.arctan(np.hypot(gx, gz)))

# ---------------------------------------------------------------- preview
COL = dict(forest=(70, 110, 60), farmland=(190, 185, 120), grass=(150, 180, 100), scrub=(140, 150, 90), orchard=(150, 175, 90), vineyard=(165, 175, 95),
           urban=(215, 205, 195), industrial=(190, 180, 200), military=(180, 150, 150), harbour=(190, 200, 210), rock=(150, 140, 130), beach=(235, 220, 160),
           water=(90, 140, 200), bay=(90, 140, 200), wetland=(120, 170, 150), bare=(200, 185, 150), cemetery=(170, 190, 150), pitch=(130, 190, 120),
           parking=(200, 200, 200), site=(180, 120, 100), airfield=(165, 190, 120), apron=(175, 175, 175), runway_area=(120, 120, 120), taxiway_area=(140, 140, 140))

def hillshade(h, cell, az=315, alt=40):
    gz, gx = np.gradient(h, cell); az = math.radians(az); alt = math.radians(alt)
    slope = np.arctan(2.0 * np.hypot(gx, gz)); aspect = np.arctan2(-gx, gz)   # exaggerated
    return np.clip(math.sin(alt) * np.cos(slope) + math.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)

def render_preview(path, h, water, osm, size_m, cell_m, ppm=2.0, points=None, title=''):
    S = int(size_m * ppm)
    hs = ndimage.zoom(h, S / (N - 1) * (N - 1) / N, order=1) if False else None
    zoom = S / N
    hu = ndimage.zoom(h, zoom, order=1)[:S, :S]; hu = np.pad(hu, ((0, S - hu.shape[0]), (0, S - hu.shape[1])), mode='edge')
    sh = hillshade(hu, size_m / S)
    img = np.zeros((S, S, 3))
    land = hu > 0
    # hypsometric tint
    t = np.clip(hu / 200.0, 0, 1)[..., None]
    img[:] = (np.array([120, 160, 90]) * (1 - t) + np.array([170, 140, 100]) * t)
    dep = np.clip(-hu / 9.0, 0, 1)[..., None]
    sea = np.array([110, 175, 215]) * (1 - dep) + np.array([30, 80, 150]) * dep
    img = np.where(land[..., None], img, sea)
    img = img * (0.55 + 0.6 * sh[..., None])
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); dr = ImageDraw.Draw(im, 'RGBA')
    tp = lambda x, z: ((x + size_m / 2) * ppm, (z + size_m / 2) * ppm)
    pairs = lambda f: [tp(f[k], f[k + 1]) for k in range(0, len(f), 2)]
    for lc in osm['landcover']:
        c = COL.get(lc['k'], (200, 200, 200));
        if lc['k'] in ('water', 'bay'): dr.polygon(pairs(lc['p']), fill=c + (150,))
        else: dr.polygon(pairs(lc['p']), fill=c + (85,))
    for w in osm['water_lines']: dr.line(pairs(w['p']), fill=(70, 120, 200, 255), width=2)
    for hb in osm['harbour']: dr.line(pairs(hb['p']), fill=(60, 60, 60, 255), width=max(2, int(hb['w'] * ppm * 0.7)))
    for a in osm['aeroways']: dr.line(pairs(a['p']), fill=(40, 40, 40, 255) if a['k'] == 'runway' else (90, 90, 90, 255), width=max(2, int(a['w'] * ppm)))
    for r in osm['roads']:
        c = (255, 255, 255, 255) if r['c'] in ('motorway', 'trunk', 'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'service') else (235, 200, 120, 255)
        dr.line(pairs(r['p']), fill=(60, 60, 60, 255), width=max(3, int(r['w'] * ppm * 0.9)) + 2)
        dr.line(pairs(r['p']), fill=c, width=max(1, int(r['w'] * ppm * 0.9)))
    for b in osm['buildings']:
        dr.polygon(pairs(b['p']), fill=(200, 60, 50, 255), outline=(90, 20, 20, 255))
    for tw in osm['towers']:
        x, y = tp(tw['x'], tw['z']); dr.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(255, 220, 0, 255), outline=(0, 0, 0, 255))
    # grid
    try: font = ImageFont.truetype('arial.ttf', 14)
    except Exception: font = ImageFont.load_default()
    step = 100 if size_m <= 1000 else (500 if size_m <= 5000 else 1000)
    for g in range(-int(size_m // 2 // step) * step, int(size_m // 2) + 1, step):
        x, _ = tp(g, 0); dr.line([(x, 0), (x, S)], fill=(0, 0, 0, 70)); dr.text((x + 3, 3), str(g), fill=(0, 0, 0, 255), font=font)
        _, y = tp(0, g); dr.line([(0, y), (S, y)], fill=(0, 0, 0, 70)); dr.text((3, y + 3), str(g), fill=(0, 0, 0, 255), font=font)
    for p in (points or []):
        x, y = tp(p['x'], p['z']); col = {'blue': (30, 80, 255, 255), 'red': (255, 30, 30, 255)}.get(p.get('side'), (255, 255, 255, 255))
        dr.ellipse([x - 9, y - 9, x + 9, y + 9], fill=col, outline=(0, 0, 0, 255), width=2); dr.text((x + 11, y - 8), f"{p['id']}", fill=(0, 0, 0, 255), font=font)
    if title: dr.rectangle([0, S - 22, S, S], fill=(255, 255, 255, 200)); dr.text((6, S - 20), title + '   |   ' + 'OSM contributors (ODbL); Mapzen terrain tiles', fill=(0, 0, 0, 255), font=font)
    im.save(path)

# ---------------------------------------------------------------- build
def pack_h(h): return base64.b64encode(np.ascontiguousarray(h, dtype='<f4').tobytes()).decode('ascii')

def build(mid, lat, lon, size=768.0, scan=False, points=None):
    P = Proj(lat, lon); cell = size / (N - 1)
    print(f'[{mid}] DEM z14 ...'); dem = fetch_dem(lat, lon, size, cell)
    print(f'[{mid}] Overpass ...'); raw = fetch_osm_raw(lat, lon, size)
    osm = process_osm(raw, P, size)
    h, water, info = shape_heights(dem, osm, cell, size)
    sl = slope_deg(h, cell)
    summary = dict(id=mid, centre=[lat, lon], size_m=size, cell_m=round(cell, 4), hmin=float(h.min()), hmax=float(h.max()), water_frac=round(info['water_frac'], 3),
                   slope_gt20=round(float((sl[~water] > 20).mean()), 3), buildings=len(osm['buildings']), roads=len(osm['roads']),
                   road_m=int(sum(sum(math.hypot(r['p'][k + 2] - r['p'][k], r['p'][k + 3] - r['p'][k + 1]) for k in range(0, len(r['p']) - 2, 2)) for r in osm['roads'])),
                   landcover=len(osm['landcover']), towers=len(osm['towers']), aeroways=len(osm['aeroways']), harbour=len(osm['harbour']), coast_pts=info['coast_pts'])
    print('   ', summary)
    render_preview(os.path.join(PREV, f'{mid}.png'), h, water, osm, size, cell, ppm=2.0 if size <= 1000 else 1536 / size, points=points, title=f'{mid}  {size:.0f} m')
    if scan: return summary
    coast = []
    half = size / 2
    for c in osm['coast']:
        for seg in clip_line(c, -half, -half, half, half): coast.append(flat(simplify(seg, 1.0)))
    doc = dict(format='squallcove-realmap/1', id=mid, attribution=ATTRIBUTION, center_lat_lon=[lat, lon], size_m=size, cell_m=round(cell, 4), grid=N,
               coords='x east, z south, metres from centre; heights row-major h[i*257+j], i=z index, j=x index; sea level 0',
               h=pack_h(h), coast=coast,
               roads=osm['roads'], buildings=osm['buildings'], landcover=osm['landcover'], harbour=osm['harbour'], aeroways=osm['aeroways'],
               towers=osm['towers'], places=osm['places'], poi=osm['poi'], barriers=osm['barriers'], power=osm['power'], rail=osm['rail'], water_lines=osm['water_lines'],
               stats=summary)
    out = os.path.join(ASSETS, f'map_{mid}.json')
    s = json.dumps(doc, separators=(',', ':'))
    open(out, 'w', encoding='utf8').write(s)
    print(f'   wrote {out}  {len(s)/1e6:.2f} MB')
    summary['json_mb'] = round(len(s) / 1e6, 2)
    json.dump(summary, open(os.path.join(HERE, f'summary_{mid}.json'), 'w'), indent=1)
    return summary

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('id'); ap.add_argument('lat', nargs='?', type=float); ap.add_argument('lon', nargs='?', type=float)
    ap.add_argument('--size', type=float, default=768.0); a = ap.parse_args()
    if a.cmd == 'build': build(a.id, a.lat, a.lon, a.size)
    elif a.cmd == 'scan': build(a.id, a.lat, a.lon, a.size, scan=True)
