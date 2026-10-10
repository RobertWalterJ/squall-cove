"""Composes docs/lights_preview_sheet.png from the tile renders (blender/review/lights/*_{3q,front,side}.png) and the night render.
usage: python blender/lights/make_sheet.py [game dir] [--tiles-only]"""
import sys, os, glob
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
GAME = next((a for a in sys.argv[1:] if not a.startswith('--')), os.path.abspath(os.path.join(HERE, '..', '..')))
REV = os.path.join(GAME, 'blender', 'review', 'lights'); OUT = os.path.join(GAME, 'docs', 'lights_preview_sheet.png')
ORDER = ['light_tower', 'light_tower_lowered', 'floodlight_pole_2', 'floodlight_pole_4', 'floodlight_wall', 'floodlight_roof', 'lamp_cobra', 'lamp_harbour',
         'lamp_bollard', 'string_lights_8m', 'string_lights_span_8m', 'generator_small', 'generator_medium', 'generator_large', 'cableseg_straight_4m',
         'cableseg_90', 'cableseg_sag_6m', 'cablereel', 'junction_box', 'junction_box_dist', 'searchlight_ground', 'spotlight_tripod',
         'vehicle_headlights', 'vehicle_taillights', 'vehicle_lightbar']
try: F = ImageFont.truetype('arial.ttf', 17); FB = ImageFont.truetype('arialbd.ttf', 22)
except Exception: F = FB = ImageFont.load_default()
COLS = 5; T = 360; INS = 128
night = os.path.join(REV, 'night.png')
nimg = Image.open(night).convert('RGB') if os.path.exists(night) and '--tiles-only' not in sys.argv else None
W = COLS * T; rows = (len(ORDER) + COLS - 1) // COLS
nh = int(W * nimg.height / nimg.width) if nimg else 0
sheet = Image.new('RGB', (W, nh + 40 + rows * (T + 4)), (24, 26, 28)); d = ImageDraw.Draw(sheet)
y0 = 0
if nimg:
    sheet.paste(nimg.resize((W, nh), Image.LANCZOS), (0, 0)); d.text((12, 8), 'NIGHT SCENE (Cycles, lamp_on emissive, spot light at every lightpt_*)', font=FB, fill=(255, 235, 190)); y0 = nh
d.text((12, y0 + 8), 'PIECES: 3/4 view, inset = front view (lens shown lit)', font=FB, fill=(220, 220, 220)); y0 += 40
for i, nm in enumerate(ORDER):
    x, y = (i % COLS) * T, y0 + (i // COLS) * (T + 4)
    p = os.path.join(REV, nm + '_3q.png')
    if os.path.exists(p): sheet.paste(Image.open(p).convert('RGB').resize((T, T), Image.LANCZOS), (x, y))
    q = os.path.join(REV, nm + '_front.png')
    if os.path.exists(q):
        ins = Image.open(q).convert('RGB').resize((INS, INS), Image.LANCZOS); sheet.paste(ins, (x + T - INS - 2, y + T - INS - 2))
        d.rectangle([x + T - INS - 2, y + T - INS - 2, x + T - 3, y + T - 3], outline=(20, 20, 20))
    d.rectangle([x, y, x + 8 * len(nm) + 14, y + 24], fill=(20, 20, 20)); d.text((x + 6, y + 3), nm, font=F, fill=(255, 255, 255))
sheet.save(OUT); print('wrote', OUT, sheet.size)
