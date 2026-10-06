"""Livery painter for the two aircraft: writes an RGB colour atlas and a tangent-space normal map (panel grooves) for each.
Run with a normal Python that has Pillow and numpy:   python air_tex.py OUT_DIR [cormorant|cl415]
The atlas layouts live in air_layout.py (the Blender code reads the same file, so painted and modelled coordinates agree).
Paint is described in WORLD coordinates (metres) per region, so a stripe at z = 2.28 is at z = 2.28 on the aircraft.
"""
import sys, os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import air_layout as LY

SS = 2                      # supersampling
FD = 'C:/Windows/Fonts/'
def font(name, px):
    for p in (FD + name, FD + 'arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'):
        try: return ImageFont.truetype(p, max(6, int(px)))
        except Exception: pass
    return ImageFont.load_default()

def hexc(h, a=255):
    h = h.lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

MAPLE = [(0.0, 1.0), (0.17, 0.64), (0.40, 0.76), (0.34, 0.36), (0.78, 0.55), (0.66, 0.24), (0.95, 0.10), (0.62, -0.10), (0.68, -0.34), (0.12, -0.28), (0.07, -0.78)]

class Atlas:
    def __init__(self, base):
        W = LY.ATLAS * SS
        self.img = Image.new('RGBA', (W, W), hexc(base)); self.d = ImageDraw.Draw(self.img, 'RGBA')
        self.gro = Image.new('L', (W, W), 0); self.g = ImageDraw.Draw(self.gro)        # groove mask: 255 = groove
        self.W = W

    # ---- helpers
    def P(self, reg, a, b):
        x, y = reg.px(a, b); return (x * SS, y * SS)
    def pm(self, reg):
        sa, sb = reg.scale(); return (sa + sb) / 2 * SS            # pixels per metre (supersampled)
    def clipbox(self, reg):
        x0, y0, x1, y1 = reg.box; return (x0 * SS, y0 * SS, x1 * SS, y1 * SS)

    def fill(self, reg, color, a_rng=None, b_rng=None):
        x0, y0, x1, y1 = self.clipbox(reg)
        if a_rng is not None or b_rng is not None:
            a0, a1 = a_rng or (reg.a0, reg.a1); b0, b1 = b_rng or (reg.b0, reg.b1)
            p, q = self.P(reg, a0, b0), self.P(reg, a1, b1)
            x0, x1 = max(x0, min(p[0], q[0])), min(x1, max(p[0], q[0])); y0, y1 = max(y0, min(p[1], q[1])), min(y1, max(p[1], q[1]))
        self.d.rectangle((x0, y0, x1, y1), fill=color)

    def poly(self, reg, pts, color, clip=True):
        """polygon in world (a, b); painted through a mask so it never leaves the region box"""
        px = [self.P(reg, a, b) for (a, b) in pts]
        x0, y0, x1, y1 = [int(v) for v in self.clipbox(reg)]
        m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).polygon([(x - x0, y - y0) for (x, y) in px], fill=color[3])
        self.img.paste(Image.new('RGBA', m.size, tuple(color[:3]) + (255,)), (x0, y0), m)

    def thick_poly(self, reg, pts, w_m, color, closed=False):
        """a polyline with a width in metres, as a polygon union of segment quads"""
        w = w_m * self.pm(reg) / 2
        P = [self.P(reg, a, b) for (a, b) in pts]
        if closed: P = P + [P[0]]
        for (p, q) in zip(P, P[1:]):
            dx, dy = q[0] - p[0], q[1] - p[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L * w, dx / L * w
            self.d.polygon([(p[0] + nx, p[1] + ny), (q[0] + nx, q[1] + ny), (q[0] - nx, q[1] - ny), (p[0] - nx, p[1] - ny)], fill=color)
            self.d.ellipse((p[0] - w, p[1] - w, p[0] + w, p[1] + w), fill=color); self.d.ellipse((q[0] - w, q[1] - w, q[0] + w, q[1] + w), fill=color)

    def groove(self, reg, pts, w_m=0.012, closed=False, strength=255):
        w = max(1.0, w_m * self.pm(reg))
        P = [self.P(reg, a, b) for (a, b) in pts]
        if closed: P = P + [P[0]]
        self.g.line(P, fill=strength, width=int(round(w)), joint='curve')

    def seam(self, reg, pts, w_m=0.012, closed=False, dark=(70, 50, 8, 95)):
        """a panel line: a thin dark line in the colour and a groove in the normal map"""
        self.thick_poly(reg, pts, w_m, dark, closed)
        self.groove(reg, pts, w_m * 1.4, closed)

    def circle(self, reg, c, r, color):
        x, y = self.P(reg, *c); R = r * self.pm(reg); self.d.ellipse((x - R, y - R, x + R, y + R), fill=color)

    def text(self, reg, c, s, cap_m, color, fnt='arialbd.ttf', anchor='mm', spacing=0.0, rot=0.0):
        px = cap_m * self.pm(reg) / 0.716
        f = font(fnt, px)
        x, y = self.P(reg, *c)
        if rot == 0.0:
            self.d.text((x, y), s, font=f, fill=color, anchor=anchor); return
        bb = self.d.textbbox((0, 0), s, font=f, anchor='lt'); lay = Image.new('RGBA', (bb[2] + 8, bb[3] + 8), (0, 0, 0, 0)); ImageDraw.Draw(lay).text((4, 4), s, font=f, fill=color, anchor='lt')
        lay = lay.rotate(math.degrees(rot), expand=True, resample=Image.BICUBIC); self.img.alpha_composite(lay, (int(x - lay.width / 2), int(y - lay.height / 2)))

    def leaf(self, reg, c, size_m, color, rot=0.0):
        pts = [(c[0] + (px * math.cos(rot) - py * math.sin(rot)) * size_m / 2, c[1] + (px * math.sin(rot) + py * math.cos(rot)) * size_m / 2) for (px, py) in MAPLE + [(-x, y) for (x, y) in reversed(MAPLE[1:-1])]]
        px_ = [self.P(reg, a, b) for (a, b) in pts]; self.d.polygon(px_, fill=color)

    def flag(self, reg, c, w_m, color_red='#d52b1e'):
        """small Canadian flag, centre c"""
        h = w_m / 2; r = hexc(color_red); wh = (245, 245, 245, 255)
        x0, y0 = c[0] - w_m / 2, c[1] - h / 2
        self.poly(reg, [(x0, y0), (x0 + w_m, y0), (x0 + w_m, y0 + h), (x0, y0 + h)], wh)
        q = w_m / 4
        self.poly(reg, [(x0, y0), (x0 + q, y0), (x0 + q, y0 + h), (x0, y0 + h)], r); self.poly(reg, [(x0 + w_m - q, y0), (x0 + w_m, y0), (x0 + w_m, y0 + h), (x0 + w_m - q, y0 + h)], r)
        self.leaf(reg, (c[0], c[1]), h * 0.8, r)

    def roundel(self, reg, c, R):
        blue = hexc('#1f3c88'); red = hexc('#d52b1e')
        self.circle(reg, c, R, blue); self.circle(reg, c, R * 0.84, (245, 245, 245, 255)); self.leaf(reg, c, R * 1.35, red)

    def weather(self, reg, strength=0.10, seed=1, soot=None):
        """soft dirt: low-frequency mottling plus faint vertical streaks (only within the region)"""
        x0, y0, x1, y1 = [int(v) for v in self.clipbox(reg)]
        w, h = x1 - x0, y1 - y0; rnd = np.random.default_rng(seed)
        n = np.zeros((h, w), np.float32)
        for (cells, amp) in ((6, 0.5), (14, 0.3), (40, 0.2)):
            a = rnd.random((max(2, h // (w // cells + 1)) + 2, cells + 2)).astype(np.float32)
            im = Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC); n += amp * np.asarray(im, np.float32) / 255
        st = rnd.random((1, max(8, w // 40))).astype(np.float32)
        im = Image.fromarray((st * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2)); streak = np.asarray(im, np.float32) / 255
        k = 1.0 - strength * (0.8 * n + 0.15 * streak)
        pm = self.pm(reg); rr = random.Random(seed * 7 + 3)                      # panel-to-panel tint jitter
        for _ in range(int(w * h / (pm * pm) / 1.3)):
            rw, rh = rr.uniform(0.5, 1.8) * pm, rr.uniform(0.4, 1.2) * pm
            x0_, y0_ = rr.uniform(-rw / 2, w - rw / 2), rr.uniform(-rh / 2, h - rh / 2)
            k[max(0, int(y0_)):max(0, int(y0_ + rh)), max(0, int(x0_)):max(0, int(x0_ + rw))] *= 1.0 + rr.uniform(-0.045, 0.035)
        reg_px = np.asarray(self.img.crop((x0, y0, x1, y1)), np.float32)
        reg_px[..., :3] *= k[..., None] * (1.0 + 0.0 * n[..., None])
        self.img.paste(Image.fromarray(np.clip(reg_px, 0, 255).astype(np.uint8), 'RGBA'), (x0, y0))

    # ---- output
    def save(self, path_color, path_normal, jpeg_q=86, nstr=2.0):
        W = LY.ATLAS
        col = self.img.resize((W, W), Image.LANCZOS).convert('RGB')
        ao = np.asarray(self.gro.resize((W, W), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3.0)), np.float32) / 255
        ca = np.asarray(col, np.float32) * (1.0 - 0.30 * np.clip(ao * 1.6, 0, 1))[..., None]
        col = Image.fromarray(np.clip(ca, 0, 255).astype(np.uint8), 'RGB')
        col.save(path_color, 'JPEG', quality=jpeg_q, subsampling=0, optimize=True)
        g = self.gro.resize((W, W), Image.LANCZOS).filter(ImageFilter.GaussianBlur(0.9))
        H = 1.0 - np.asarray(g, np.float32) / 255
        dy, dx = np.gradient(H)
        nx, ny, nz = -dx * nstr * 6, dy * nstr * 6, np.ones_like(H)
        L = np.sqrt(nx * nx + ny * ny + nz * nz); nx, ny, nz = nx / L, ny / L, nz / L
        nm = np.stack([(nx * 0.5 + 0.5) * 255, (ny * 0.5 + 0.5) * 255, (nz * 0.5 + 0.5) * 255], -1).astype(np.uint8)
        Image.fromarray(nm, 'RGB').save(path_normal, 'PNG', optimize=True)


# ================================================================ CH-149 Cormorant
YEL = '#f0b412'; YEL_D = '#b98608'; RED = '#b3232b'; DARKG = '#26282a'; WHITE = '#f1efe6'; BLK = '#16181a'

def cormorant(out):
    R = LY.COR; A = Atlas(YEL)
    SB, PT, TOP, BOT = R['sb'], R['pt'], R['top'], R['bot']
    red, white, blk, dg = hexc(RED), hexc(WHITE), hexc(BLK), hexc(DARKG)
    # the sky-side of every region starts as plain SAR yellow (already filled); belly gets a slightly darker, greasy yellow
    A.fill(BOT, hexc('#c9980f'))
    for reg, sd in ((SB, -1), (PT, 1)):
        # ---- red patches
        A.fill(reg, red, (3.0, 7.7), (3.28, 6.0))                                                      # red upper cowl in front of the doghouse and over the cockpit
        A.poly(reg, [(-3.9, 3.62), (-5.75, 3.62), (-6.65, 2.3), (-5.45, 2.3)], red)                       # red diagonal band across the tail cone
        A.poly(reg, [(-3.9, 3.62), (-5.75, 3.62), (-5.75, 3.9), (-3.9, 3.9)], red)
        # ---- engine bay heat shields (dark) on the doghouse sides
        A.poly(reg, [(-2.15, 3.62), (-2.15, 4.45), (-1.4, 4.78), (0.0, 4.9), (0.5, 4.5), (0.5, 3.62)], dg)
        A.poly(reg, [(0.5, 3.62), (0.5, 4.2), (0.9, 4.2), (0.9, 3.62)], dg)
        for k in range(9):                                                                              # cooling louvres on the heat shield
            A.thick_poly(reg, [(-2.0, 3.85 + k * 0.095), (-0.4, 3.85 + k * 0.095)], 0.018, (70, 72, 74, 255)) if k < 8 else None
        # ---- belly strake and the dark lower chine of the nose
        A.poly(reg, [(-1.6, 0.0), (8.9, 0.0), (8.9, 0.42), (-1.6, 0.42)], hexc('#b88a0e'))
        # ---- panel seams
        for xs in (-9.2, -7.9, -6.6, -4.2, -3.2, -1.3, 0.35, 1.75, 3.65, 4.55, 6.0, 7.45):
            A.seam(reg, [(xs, 0.5), (xs, 3.58)], 0.010)
        for zs in (0.9, 1.25, 3.0):
            A.seam(reg, [(-4.3, zs), (8.0, zs)], 0.008)
        for zs in (3.05, 3.5): A.seam(reg, [(-9.4, zs), (-4.2, zs)], 0.009)
        A.seam(reg, [(-10.1, 4.3), (-8.0, 3.7)], 0.009)
        # tail pylon seams
        for (z0, z1) in ((3.4, 4.1), (4.5, 5.1)): A.seam(reg, [(-10.0, z0), (-8.3, z1)], 0.009)
        # ---- rivet lines (dotted)
        for zs in (0.7, 3.35):
            for k in range(0, 160):
                xx = -4.2 + k * 0.078
                A.d.ellipse((*(np.array(A.P(reg, xx, zs)) - 0.9), *(np.array(A.P(reg, xx, zs)) + 0.9)), fill=(90, 62, 8, 140))
        # ---- stripe: thin red, white, red; the Z notch near the cockpit
        zS = 2.28
        path = [(-4.55, zS), (5.55, zS), (6.35, zS), (5.45, 1.3), (7.3, 1.3)]
        for (wm, col) in ((0.115, red), (0.05, white)): A.thick_poly(reg, path, wm, col)
        # ---- doors: cockpit door and crew door on both sides, big sliding door on the starboard side
        cd = [(5.95, 3.35), (7.15, 3.35), (7.15, 0.95), (5.95, 0.95)]
        A.seam(reg, cd, 0.014, closed=True)
        A.seam(reg, [(4.82, 2.85), (5.62, 2.85), (5.62, 1.6), (4.82, 1.6)], 0.012, closed=True)
        if sd < 0:
            sl = [(1.65, 2.95), (3.7, 2.95), (3.7, 0.62), (1.65, 0.62)]
            A.seam(reg, sl, 0.016, closed=True)
            A.seam(reg, [(1.65, 2.7), (3.7, 2.7)], 0.01); A.seam(reg, [(1.65, 0.85), (3.7, 0.85)], 0.01)
            A.thick_poly(reg, [(3.3, 1.7), (3.3, 2.1)], 0.045, hexc('#2a2a2a'))                          # door handle
            A.thick_poly(reg, [(1.1, 3.0), (1.1, 0.7)], 0.02, hexc('#8c6a0a', 140))                        # door track
        else:
            A.seam(reg, [(1.65, 2.95), (3.7, 2.95), (3.7, 0.9), (1.65, 0.9)], 0.011, closed=True)
        # ---- markings
        sdx = 1                     # text reads left to right in the picture on both sides
        A.text(reg, (-0.55 if sd < 0 else -0.55, 3.0), 'Canada', 0.27, blk, 'times.ttf')
        A.flag(reg, (0.28 if sd < 0 else 0.28, 3.18), 0.17)
        A.text(reg, (6.15 if sd < 0 else 6.15, 3.2), 'Canadian', 0.075, blk, 'arial.ttf'); A.text(reg, (6.15, 3.09), 'Forces', 0.075, blk, 'arial.ttf')
        A.text(reg, (6.45, 3.2) if False else (6.62, 3.2), 'Forces', 0.075, blk, 'arial.ttf'); A.text(reg, (6.62, 3.09), 'canadiennes', 0.075, blk, 'arial.ttf')
        A.flag(reg, (5.62, 3.15), 0.15)
        A.text(reg, (6.7, 1.78), '909', 0.3, blk, 'arialbd.ttf')
        A.text(reg, (5.95, 1.04), 'RESCUE', 0.13, blk, 'arialbd.ttf'); A.text(reg, (5.95, 0.86), 'SAUVETAGE', 0.13, blk, 'arialbd.ttf')
        # tail
        A.flag(reg, (-9.0, 4.4), 0.26); A.text(reg, (-9.0, 4.12), '149909', 0.085, blk, 'arial.ttf')
        A.text(reg, (-6.3, 3.0), 'NO STEP', 0.06, hexc('#6a4a08'), 'arialbd.ttf'); A.text(reg, (-0.9, 1.0), 'FUEL', 0.06, hexc('#6a4a08'), 'arialbd.ttf')
        # red beacon light / fuel vent circles and the small red anti-collision lamp mount
        A.circle(reg, (-3.0, 2.25), 0.16, hexc('#c8341e')); A.circle(reg, (-3.0, 2.25), 0.09, hexc('#e66a3a'))
        # hoist doorway frame on the starboard doghouse / cabin roof
        if sd < 0:
            A.seam(reg, [(1.15, 4.55), (2.45, 4.55), (2.45, 3.6), (1.15, 3.6)], 0.012, closed=True)
        for wx in (-1.8, -0.45, 1.1, 2.55, 4.25, 5.2, 6.5):
            for k in range(6):
                A.poly(reg, [(wx - 0.2 + k * 0.03, 2.0 - 0.1 * k), (wx + 0.2 - k * 0.03, 2.0 - 0.1 * k), (wx + 0.15, 0.95 - 0.05 * k), (wx - 0.15, 0.95 - 0.05 * k)], (60, 40, 5, 6))
        A.weather(reg, 0.16, 11 + sd)
    # ---- top view
    A.fill(TOP, hexc(YEL))
    A.fill(TOP, red, (3.0, 7.0), (-2.0, 2.0))                                                          # cockpit roof
    A.poly(TOP, [(6.4, 1.3), (7.95, 0.0), (6.4, -1.3), (6.1, -1.3), (7.6, 0.0), (6.1, 1.3)], red)       # red V chevron at the nose top
    A.poly(TOP, [(-5.75, 2.0), (-3.9, 2.0), (-3.9, -2.0), (-5.75, -2.0)], red)                          # tail cone band over the roof
    A.poly(TOP, [(-2.1, 1.5), (0.5, 1.5), (0.5, -1.5), (-2.1, -1.5)], hexc('#8d760f'))                   # heat staining behind the engine bay
    for xs in (-9.2, -7.9, -6.6, -5.0, -4.2, -3.2, -1.3, 0.35, 1.75, 3.0, 3.65, 4.55, 6.0, 7.0): A.seam(TOP, [(xs, -1.6), (xs, 1.6)], 0.010)
    for ys in (-0.8, 0.0, 0.8): A.seam(TOP, [(-4.0, ys), (7.0, ys)], 0.008)
    A.seam(TOP, [(2.6, -1.1), (3.3, -1.1), (3.3, 1.1), (2.6, 1.1)], 0.01, closed=True)
    A.text(TOP, (-6.9, 0.0), 'NO STEP', 0.07, hexc('#6a4a08'), 'arialbd.ttf')
    A.roundel(TOP, (7.45, 0.0), 0.26)
    A.weather(TOP, 0.18, 21)
    # ---- belly
    for xs in (-9.0, -7.0, -5.5, -4.2, -3.0, -1.6, -0.2, 1.2, 2.6, 4.0, 5.4, 6.8, 7.9): A.seam(BOT, [(xs, -1.6), (xs, 1.6)], 0.012, dark=(50, 34, 6, 170))
    for ys in (-0.9, -0.3, 0.3, 0.9): A.seam(BOT, [(-4.2, ys), (8.3, ys)], 0.01, dark=(50, 34, 6, 170))
    A.poly(BOT, [(-1.8, -1.0), (1.8, -1.0), (1.8, 1.0), (-1.8, 1.0)], hexc('#8c7110'))              # belly equipment bay (dark)
    A.fill(BOT, hexc('#a07a0c'), (-4.2, -0.9), (-0.9, 0.9))
    A.weather(BOT, 0.30, 31)
    # ---- sponsons: SAR red lozenges with the roundel on the outer face
    for reg, sd in ((R['sp_sb'], -1), (R['sp_pt'], 1)):
        A.fill(reg, red)
        A.roundel(reg, (-0.9, 0.97), 0.30)
        A.seam(reg, [(-2.2, 0.5), (-2.2, 1.5)], 0.01, dark=(40, 5, 8, 160)); A.seam(reg, [(0.1, 0.5), (0.1, 1.5)], 0.01, dark=(40, 5, 8, 160))
        A.text(reg, (-2.9, 0.95), 'NO STEP', 0.07, white, 'arialbd.ttf')
        A.weather(reg, 0.12, 41)
    # ---- stabiliser strips, plain yellow with red tips
    A.fill(R['stab'], hexc(YEL)); A.fill(R['stab'], red, (-1.8, -1.55)); A.fill(R['stab'], red, (1.55, 1.8))
    A.weather(R['stab'], 0.12, 51)
    # ---- solid patches
    for nm, col in (('yellow', YEL), ('red', RED), ('dark', DARKG), ('grey', '#6d747b'), ('white', WHITE)):
        x, y = LY.COR_SOLID[nm]; A.d.rectangle(((x - 14) * SS, (y - 14) * SS, (x + 14) * SS, (y + 14) * SS), fill=hexc(col))
    A.save(os.path.join(out, 'cormorant_livery.jpg'), os.path.join(out, 'cormorant_normal.png'))


def cl415(out):
    import air_tex_cl
    air_tex_cl.paint(out)


if __name__ == '__main__':
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    which = sys.argv[2:] or ['cormorant', 'cl415']
    for w in which: globals()[w](out); print('painted', w)
