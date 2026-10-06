"""Texture atlas layouts shared by the Blender model code (pg_cormorant, pg_cl415) and the livery painter (air_tex.py).
No PIL or bpy in here, so both sides can import it.

Every aircraft has one 2048 x 2048 colour atlas. Regions are rectangles of the atlas that hold a flat projection of the aircraft:
  side views (x, z), looking at the starboard (-Y) and port (+Y) sides with the nose toward the right of the picture for starboard;
  top view (x, y); belly view (x, y); and small parts (sponsons, tail surfaces, wings).
A layout maps 3D points to (u, v) with v = 0 at the BOTTOM of the image (Blender convention).
"""

ATLAS = 2048


class Region:
    """A rectangle of the atlas (pixel box, y down) showing world coordinates (a0..a1, b0..b1)."""
    def __init__(self, name, box, a_rng, b_rng, flip_a=False, flip_b=False):
        self.name = name; self.box = box; self.a0, self.a1 = a_rng; self.b0, self.b1 = b_rng; self.flip_a = flip_a; self.flip_b = flip_b

    def px(self, a, b):
        """world (a, b) -> pixel (x, y) in the atlas image (y down)."""
        ta = (a - self.a0) / (self.a1 - self.a0); tb = (b - self.b0) / (self.b1 - self.b0)
        if self.flip_a: ta = 1 - ta
        if self.flip_b: tb = 1 - tb
        x0, y0, x1, y1 = self.box
        return x0 + ta * (x1 - x0), y0 + tb * (y1 - y0)

    def uv(self, a, b):
        x, y = self.px(a, b)
        x0, y0, x1, y1 = self.box; m = 1.5
        x = min(max(x, x0 + m), x1 - m); y = min(max(y, y0 + m), y1 - m)
        return x / ATLAS, 1.0 - y / ATLAS

    def scale(self):
        """pixels per metre along a (and b)."""
        x0, y0, x1, y1 = self.box
        return abs(x1 - x0) / abs(self.a1 - self.a0), abs(y1 - y0) / abs(self.b1 - self.b0)


def _hull_regions(x0, x1, zmax, ymax, rows):
    """side views at one scale; rows: dict of pixel rows."""
    W = ATLAS; S = W / (x1 - x0)
    zr = zmax * S
    out = {}
    # starboard: nose to the right  (u grows with x); picture top is zmax
    out['sb'] = Region('sb', (0, rows['sb'], W, rows['sb'] + zr), (x0, x1), (zmax, 0.0))
    # port: nose to the left
    out['pt'] = Region('pt', (0, rows['pt'], W, rows['pt'] + zr), (x0, x1), (zmax, 0.0), flip_a=True)
    yr = 2 * ymax * S
    # top: nose right, port (+Y) at the top of the picture
    out['top'] = Region('top', (0, rows['top'], W, rows['top'] + yr), (x0, x1), (ymax, -ymax))
    # belly: looking up, nose right, starboard (-Y) at the top
    out['bot'] = Region('bot', (0, rows['bot'], W, rows['bot'] + yr), (x0, x1), (-ymax, ymax))
    return out


# ---------------------------------------------------------------- CH-149 Cormorant
COR_X0, COR_X1 = -10.9, 9.6
_cs = ATLAS / (COR_X1 - COR_X0)
_zr = int(5.9 * _cs)
_yr = int(2 * 1.7 * _cs)
COR_ROWS = dict(sb=0, pt=_zr, top=2 * _zr, bot=2 * _zr + _yr)
COR = _hull_regions(COR_X0, COR_X1, 5.9, 1.7, COR_ROWS)
_r0 = 2 * _zr + 2 * _yr
# sponsons: 4.6 m long strips, 0.9 m tall
COR['sp_sb'] = Region('sp_sb', (0, _r0, 470, _r0 + 100), (-3.5, 1.1), (1.5, 0.45))
COR['sp_pt'] = Region('sp_pt', (500, _r0, 970, _r0 + 100), (-3.5, 1.1), (1.5, 0.45), flip_a=True)
# solid patches for small parts (centre pixel): yellow, red, dark, grey
COR_SOLID = dict(yellow=(1100, _r0 + 20), red=(1140, _r0 + 20), dark=(1180, _r0 + 20), grey=(1220, _r0 + 20), white=(1260, _r0 + 20))
# tailplane / stabiliser strips
COR['stab'] = Region('stab', (1300, _r0, 1700, _r0 + 100), (-1.8, 1.8), (-11.2, -8.6))

# ---------------------------------------------------------------- Canadair CL-415
CL_X0, CL_X1 = -10.3, 10.4
_ks = ATLAS / (CL_X1 - CL_X0)
_zr2 = int(4.4 * _ks)            # hull side z 0..4.4 (hull top at 3.9)
_yr2 = int(2 * 1.9 * _ks)
CL_ROWS = dict(sb=0, pt=_zr2, top=2 * _zr2, bot=2 * _zr2 + _yr2)
CL = _hull_regions(CL_X0, CL_X1, 4.4, 1.9, CL_ROWS)
_q0 = 2 * _zr2 + 2 * _yr2
# fin sides (x -10.1..-4.6, z 2.9..9.3 at about 49 px/m); the second side is the first one mirrored
CL['fin'] = Region('fin', (0, _q0, 270, _q0 + 315), (-10.1, -4.6), (9.3, 2.9))
CL['fin2'] = Region('fin2', (280, _q0, 550, _q0 + 315), (-10.1, -4.6), (9.3, 2.9), flip_a=True)
# tailplane (a = y, b = x), nacelle sides (a = x, b = z)
CL['tail'] = Region('tail', (560, _q0, 800, _q0 + 80), (-4.9, 4.9), (-6.5, -9.7))
CL['nac_sb'] = Region('nac_sb', (560, _q0 + 90, 800, _q0 + 158), (-1.6, 5.6), (4.7, 3.0))
CL['nac_pt'] = Region('nac_pt', (560, _q0 + 168, 800, _q0 + 236), (-1.6, 5.6), (4.7, 3.0), flip_a=True)
# wing top / bottom: a = y (-14.6..14.6), b = x (leading edge at the top row)
CL['wtop'] = Region('wtop', (810, _q0, 2040, _q0 + 181), (-14.6, 14.6), (4.2, -0.1))
CL['wbot'] = Region('wbot', (810, _q0 + 186, 2040, _q0 + 367), (-14.6, 14.6), (4.2, -0.1))
CL_SOLID = dict(orange=(40, 2030), white=(80, 2030), green=(120, 2030), dark=(160, 2030), grey=(200, 2030), hull=(240, 2030))
