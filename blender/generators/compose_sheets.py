"""Compose the vessel contact sheet and the to-scale lineup from ccg_review.py renders (PIL).
  python compose_sheets.py RENDER_DIR OUT_DIR
RENDER_DIR holds <key>_3q.png and <key>_side.png; OUT_DIR gets vessels_contact_sheet.png and vessels_to_scale.png."""
import sys, os
from PIL import Image, ImageDraw, ImageFont

RD, OD = sys.argv[1], sys.argv[2]
os.makedirs(OD, exist_ok=True)
# key, display name, length m, role
VESSELS = [
    ('petrel', 'Petrel', 4.2, 'dinghy'), ('kestrel', 'Kestrel', 7.9, 'keelboat'), ('bollard', 'Bollard', 9.4, 'harbour tug'),
    ('bay_class', 'Bay class', 19.0, 'lifeboat'), ('hovercraft', 'Hovercraft', 28.5, 'air cushion vehicle'), ('hero_class', 'Hero class', 42.8, 'patrol vessel'),
    ('sir_john_franklin', 'Sir John Franklin', 63.4, 'fisheries science'), ('martha_l_black', 'Martha L. Black', 83.0, 'light icebreaker'),
    ('capt_molly_kool', 'Capt. Molly Kool', 83.7, 'icebreaker'), ('terry_fox', 'Terry Fox', 88.0, 'icebreaker'),
    ('pierre_radisson', 'Pierre Radisson', 98.3, 'icebreaker'), ('donjek_aops', 'Donjek', 103.6, 'Arctic patrol ship'),
    ('louis_st_laurent', 'Louis S. St-Laurent', 119.8, 'heavy icebreaker'), ('arpatuuq', 'Arpatuuq', 138.5, 'polar icebreaker'),
]
def font(sz, bold=False):
    for f in (('calibrib.ttf' if bold else 'calibri.ttf'), 'segoeuib.ttf' if bold else 'segoeui.ttf', 'arial.ttf'):
        try: return ImageFont.truetype(f, sz)
        except Exception: pass
    return ImageFont.load_default()
BG = (236, 233, 227); INK = (31, 29, 29); MUTE = (125, 110, 110); RED = (204, 34, 41)

# ---- contact sheet: every vessel fitted to its own cell, so shapes compare
cols, cw, ch = 4, 760, 600
rows = (len(VESSELS) + cols - 1) // cols
head = 150
sheet = Image.new('RGB', (cols * cw, head + rows * ch), BG); d = ImageDraw.Draw(sheet)
d.text((40, 34), 'Squall Cove vessels', font=font(64, True), fill=INK)
d.text((42, 108), f'{len(VESSELS)} hulls: 3 harbour and sailing boats, 11 Canadian Coast Guard vessels. Each is scaled to fit its cell; length is under each name.', font=font(26), fill=MUTE)
for i, (k, name, L, role) in enumerate(VESSELS):
    im = Image.open(os.path.join(RD, k + '_3q.png')).convert('RGB')
    # crop the empty margin around the render so small boats are not tiny
    bg = Image.new('RGB', im.size, im.getpixel((2, 2)))
    from PIL import ImageChops
    bb = ImageChops.difference(im, bg).convert('L').point(lambda v: 255 if v > 14 else 0).getbbox()
    if bb: im = im.crop((max(0, bb[0] - 20), max(0, bb[1] - 20), min(im.width, bb[2] + 20), min(im.height, bb[3] + 20)))
    s = min((cw - 50) / im.width, (ch - 150) / im.height); im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    x0, y0 = (i % cols) * cw, head + (i // cols) * ch
    sheet.paste(im, (x0 + (cw - im.width) // 2, y0 + 20 + (ch - 150 - im.height) // 2))
    d.text((x0 + 36, y0 + ch - 112), name, font=font(40, True), fill=INK)
    d.text((x0 + 38, y0 + ch - 62), f'{L:g} m  /  {role}', font=font(28), fill=RED)
sheet.save(os.path.join(OD, 'vessels_contact_sheet.png')); print('contact sheet', sheet.size)

# ---- to-scale lineup: side views at one scale, waterline aligned, bow to the left, two columns (small half, large half)
from PIL import ImageChops
PXM = 8.0                                   # pixels per metre
items = []
for k, name, L, role in VESSELS:
    im = Image.open(os.path.join(RD, k + '_side.png')).convert('RGB')
    bgc = im.getpixel((2, 2)); mask = ImageChops.difference(im, Image.new('RGB', im.size, bgc)).convert('L').point(lambda v: 255 if v > 14 else 0)
    pxm0 = im.width / (1.06 * L)           # the review camera frames length * 1.06 across the width
    wl = None                              # waterline: first row where the dark boot-topping band covers most of the width
    for y in range(im.height):
        row = [im.getpixel((x, y)) for x in range(0, im.width, 6)]
        if sum(1 for r in row if r[0] < 70 and r[1] < 70 and r[2] < 70) / len(row) > 0.3: wl = y; break
    if wl is None: wl = int(im.height * 0.7)
    s_ = PXM / pxm0; sz = (max(1, int(im.width * s_)), max(1, int(im.height * s_)))
    items.append((im.resize(sz, Image.LANCZOS), mask.resize(sz, Image.LANCZOS), int(wl * s_), name, L, role))
items.sort(key=lambda t: t[4])
above = max(it[2] for it in items); below = 26; rowh = above + below + 78
half = (len(items) + 1) // 2; cols_ = [items[:half], items[half:]]
colw = [max(it[0].width for it in c) + 90 for c in cols_]
Wd = sum(colw) + 40; Ht = 130 + rowh * half + 20
lineup = Image.new('RGB', (Wd, Ht), BG); d = ImageDraw.Draw(lineup)
d.text((40, 24), 'Squall Cove vessels to scale', font=font(54, True), fill=INK)
d.text((42, 88), 'Side views at one scale, bows to the left, waterlines aligned. Faint verticals every 10 m.', font=font(24), fill=MUTE)
x0 = 20
for ci, col in enumerate(cols_):
    for m in range(0, int(colw[ci] / PXM), 10):
        d.line([(x0 + 30 + int(m * PXM), 126), (x0 + 30 + int(m * PXM), Ht - 14)], fill=(224, 220, 212), width=1)
    for i, (im, mk, wl, name, L, role) in enumerate(col):
        y0 = 130 + i * rowh
        top = y0 + above - wl
        lineup.paste(im.crop((0, 0, im.width, wl + below)), (x0 + 30, top), mk.crop((0, 0, im.width, wl + below)))
        d.line([(x0 + 30, y0 + above), (x0 + colw[ci] - 30, y0 + above)], fill=(176, 170, 162), width=1)
        d.text((x0 + 34, y0 + above + below + 6), name, font=font(28, True), fill=INK)
        d.text((x0 + 34 + int(d.textlength(name, font=font(28, True))) + 14, y0 + above + below + 9), f'{L:g} m  /  {role}', font=font(24), fill=RED)
        d.rectangle([x0 + 30, y0 + above + below + 46, x0 + 30 + int(L * PXM), y0 + above + below + 50], fill=RED)
    x0 += colw[ci]
lineup.save(os.path.join(OD, 'vessels_to_scale.png')); print('to scale', lineup.size)
