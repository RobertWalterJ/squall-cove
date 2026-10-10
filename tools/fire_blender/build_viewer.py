"""Build docs/fireb_viewer.html: the template with fireb_atlas.json embedded inline (fetch is blocked on file://).
  python build_viewer.py [GAMEDIR]
"""
import sys, os, json
here = os.path.dirname(os.path.abspath(__file__))
game = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(here, '..', '..'))
atlas = json.load(open(os.path.join(game, 'assets', 'fire_blender', 'fireb_atlas.json')))
html = open(os.path.join(here, 'viewer_template.html'), encoding='utf-8').read()
html = html.replace('/*ATLAS_JSON*/null', json.dumps(atlas, separators=(',', ':')))
os.makedirs(os.path.join(game, 'docs'), exist_ok=True)
open(os.path.join(game, 'docs', 'fireb_viewer.html'), 'w', encoding='utf-8').write(html)
print('wrote docs/fireb_viewer.html', len(html), 'bytes')
