"""Draws keyboard diagrams (one PNG per mode) from a key table. Run: python tools/make_keyboard_png.py [outdir]
Colour groups also carry text on every key, so colour is never the only signal."""
import sys, os, textwrap
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'docs')
os.makedirs(OUT, exist_ok=True)
FD = r'C:\Windows\Fonts'
def font(n, s):
    for f in (n, 'arial.ttf'):
        try: return ImageFont.truetype(os.path.join(FD, f), s)
        except Exception: pass
    return ImageFont.load_default()
FB, FS, FT, FL = font('arialbd.ttf', 17), font('arial.ttf', 12), font('arialbd.ttf', 30), font('arial.ttf', 15)

CAT = {1: ('Move and look', (214, 232, 248), (55, 138, 221)), 2: ('Fire and use', (250, 224, 214), (216, 90, 48)),
       3: ('Squad', (214, 242, 230), (29, 158, 117)), 4: ('Command and map', (250, 236, 208), (186, 117, 23)),
       5: ('Tools and weapons', (232, 230, 252), (127, 119, 221)), 6: ('System', (236, 234, 226), (136, 135, 128))}

MODES = {
 'overview': ('Overview (god mode)', {
  'w': (1, 'Pan up'), 'a': (1, 'Pan left'), 's': (1, 'Pan down'), 'd': (1, 'Pan right'), 'q': (1, 'Turn left'), 'e': (1, 'Turn right'),
  'z': (1, 'Zoom out'), 'x': (1, 'Zoom in'), '1': (5, 'Select tool'), '2': (5, 'Place tool'), '3': (5, 'Land tool'), '4': (5, 'Sky tool'),
  'esc': (6, 'Stand down / menu'), ';': (6, 'Pause or resume the clock'), 't': (4, 'Command (Shift+T: Plan tab)'), 'l': (4, 'Tactical map'), 'j': (2, 'Jump in'), 'k': (2, 'Watch next'), 'o': (2, 'Gunship station'),
  'p': (6, 'Side pane'), '`': (6, 'Cheat prompt (or Enter then /)'), 'enter': (6, 'Cheat prompt: Enter, then /'), '/': (6, 'Enter, then / opens the prompt'), 'v': (1, 'Drop into first person'), 'h': (1, 'Take the helm'), 'n': (1, 'Next boat'),
  'r': (2, 'Rain crates'), 'f': (2, 'Fire mode'), 'b': (4, 'Box-select mode'), 'g': (2, 'Drop carried'), 'del': (6, 'Remove selected'),
  '[': (6, 'Drop height down'), ']': (6, 'Drop size up'), '5': (3, 'Recall group 5'), '6': (3, 'Recall group 6'), '7': (3, 'Recall group 7'),
  '8': (3, 'Recall group 8'), '9': (3, 'Recall group 9'), 'shift': (4, 'Shift+drag: box-select'), 'ctrl': (4, 'Ctrl+A: select all; Ctrl+5-9 saves group')}),
 'firstperson': ('First person', {
  'w': (1, 'Walk forward'), 'a': (1, 'Step left'), 's': (1, 'Walk back'), 'd': (1, 'Step right'), 'shift': (1, 'Run'), 'space': (1, 'Jump / stand up'),
  'c': (1, 'Crouch'), 'p': (1, 'Lie prone'), 'r': (2, 'Reload'), 'e': (2, 'Use: pick up, board, climb, man a gun'), 'g': (2, 'Drop carried'),
  'q': (2, 'Jump overboard'), 'h': (1, 'Take the helm'), 'f': (2, 'Set down a sandbag'), 'x': (3, 'Squad follow / hold'), 'z': (3, 'Squad move to crosshair'),
  'n': (3, 'Hold: squad order ring'), 'i': (3, 'Ping a spot or enemy'), 'j': (3, 'Squad mount up / get out'), 'm': (4, 'Quick map (Shift+M corner map)'),
  'u': (3, 'Heal me'), 'k': (3, 'Squad hold / free fire'), 't': (4, 'Command (Shift+T: Plan tab)'), 'l': (4, 'Tactical map'), 'b': (2, 'Detonate charges'),
  'y': (3, 'Swap to nearest friend'), ';': (6, 'Pause or resume the clock'), '.': (2, 'Torch on or off (vehicle: headlights)'), ',': (2, 'Throw a chemical light (Shift: handheld flare)'), 'v': (6, 'Back to overview'), 'esc': (6, 'Back to overview'), 'tab': (6, 'Back to overview'), 'o': (6, 'Back to overview'),
  '`': (6, 'Cheat prompt (or Enter then /)'), 'enter': (6, 'Cheat prompt: Enter, then /'), '/': (6, 'Enter, then / opens the prompt'), '1': (5, 'Tool 1'), '2': (5, 'Tool 2'), '3': (5, 'Tool 3'), '4': (5, 'Tool 4'), '5': (5, 'Tool 5'), '6': (5, 'Tool 6'),
  '7': (5, 'Tool 7'), '8': (5, 'Tool 8 / squad order 8'), '9': (5, 'Tool 9'), '0': (5, 'Grenade'), '-': (5, 'Charge')}),
 'station': ('Gunship station', {
  '1': (2, 'Howitzer (ready-up ~2 s)'), '2': (2, '40 mm cannon (~1 s, 15 rounds)'), '3': (2, 'Vulcan (instant; right mouse fires it any time)'), 'space': (2, 'Fire chosen gun (also left mouse button)'), 'enter': (2, 'Fire chosen gun'),
  'w': (1, 'Slew up (the mouse aims too)'), 'a': (1, 'Slew left'), 's': (1, 'Slew down'), 'd': (1, 'Slew right'), 'q': (2, 'Swap howitzer / 40 mm'), 'e': (4, 'Zoom in (wheel up too)'), '[': (4, 'Zoom out (wheel down too)'), ']': (4, 'Zoom in'),
  '-': (4, 'Zoom out (keypad -)'), '=': (4, 'Zoom in (+ or keypad +)'), '4': (5, 'Thermal'), '5': (5, 'Night vision'), '6': (5, 'Colour'), '7': (5, 'Night colour green / white'), 'v': (5, 'Next view'), 'shift': (4, 'Hold: aim finer'),
  't': (3, 'Track target / release lock (hold the mouse still on a target to lock and follow it; move the mouse to release)'), 'm': (3, 'Change sensor'), 'c': (3, 'Free or recapture the cursor (buttons clickable)'), ',': (3, 'Mouse slower'), '.': (3, 'Mouse faster'), 'esc': (6, 'Leave station, release the mouse')}),
}
ROWS = [['esc', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'del'], ['tab', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']'],
        ['caps', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'enter'], ['shift', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'shift'], ['ctrl', 'alt', 'space', 'alt', 'ctrl']]
LAB = {'del': 'Del', 'esc': 'Esc', 'tab': 'Tab', 'caps': 'Caps', 'enter': 'Enter', 'shift': 'Shift', 'ctrl': 'Ctrl', 'alt': 'Alt', 'space': 'Space'}
U, GAP, PAD, TOP = 78, 6, 30, 90
WIDTH = {'space': 5.0, 'shift': 2.0, 'enter': 2.0, 'caps': 1.6, 'tab': 1.4, 'del': 1.4, 'ctrl': 1.3, 'alt': 1.3}

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines[:4]

for fn, (title, keys) in MODES.items():
    W = int(PAD * 2 + 14.4 * (U + GAP)); H = TOP + 5 * (U + GAP) + 110
    im = Image.new('RGB', (W, H), (250, 249, 245)); d = ImageDraw.Draw(im)
    d.text((PAD, 24), 'Squall Cove: ' + title, font=FT, fill=(30, 30, 28))
    y = TOP
    for r in ROWS:
        x = PAD
        for k in r:
            w = int(WIDTH.get(k, 1.0) * U + (WIDTH.get(k, 1.0) - 1) * GAP)
            info = keys.get(k)
            fill, edge = ((255, 255, 255), (190, 188, 180)) if not info else (CAT[info[0]][1], CAT[info[0]][2])
            d.rounded_rectangle([x, y, x + w, y + U], 8, fill=fill, outline=edge, width=2)
            lab = LAB.get(k, k.upper())
            d.text((x + 7, y + 5), lab, font=FB, fill=(40, 40, 38) if info else (150, 148, 140))
            if info:
                for i, ln in enumerate(wrap(d, info[1], FS, w - 12)):
                    d.text((x + 7, y + 28 + i * 13), ln, font=FS, fill=(50, 50, 46))
            x += w + GAP
        y += U + GAP
    lx = PAD
    for c in range(1, 7):
        nm, fill, edge = CAT[c]
        d.rounded_rectangle([lx, y + 18, lx + 18, y + 36], 4, fill=fill, outline=edge, width=2)
        d.text((lx + 26, y + 19), nm, font=FL, fill=(50, 50, 46)); lx += 30 + int(d.textlength(nm, font=FL)) + 40
    d.text((PAD, y + 56), 'Keys with no action in this mode are blank. Every key also carries a text label, so colour is never the only signal.', font=FL, fill=(90, 90, 84))
    p = os.path.join(OUT, 'keyboard_' + fn + '.png'); im.save(p); print(p)
