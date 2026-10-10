"""Builds assets/lights_pack.glb (+ .b64.txt + lights_pack.manifest.json). Pure python + numpy.
usage: python blender/lights/build_lights.py [game dir]"""
import sys, os, json, base64
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.abspath(os.path.join(HERE, '..', '..'))
from lights_lib import *
import pieces_a as A, pieces_b as B

def roots():
    return [A.light_tower(True), A.light_tower(False), A.floodlight_pole(2), A.floodlight_pole(4), A.floodlight_wall(), A.floodlight_roof(),
            A.lamp_cobra(), A.lamp_harbour(), A.lamp_bollard(), A.string_lights_8m(), A.string_lights_span(),
            B.generator_small(), B.generator_medium(), B.generator_large(), B.cable_straight_4m(), B.cable_90(), B.cable_sag_6m(), B.cable_reel(),
            B.junction_box(), B.junction_box_dist(), B.searchlight_ground(), B.spotlight_tripod(),
            B.vehicle_headlights(), B.vehicle_taillights(), B.vehicle_lightbar(), B.materials_ref()]

def walk(n, path, out):
    for k in n.kids:
        if k.extras: out.append({'node': k.name, 'parent': n.name, 'pos': [round(x, 3) for x in k.t], 'extras': k.extras})
        walk(k, path, out)

if __name__ == '__main__':
    rs = roots()
    # each root is its own named top-level scene node
    out = build_glb(rs)
    names = [r.name for r in rs]; assert len(names) == len(set(names))
    open(os.path.join(GAME, 'assets', 'lights_pack.glb'), 'wb').write(out)
    b64 = base64.b64encode(out)
    open(os.path.join(GAME, 'assets', 'lights_pack.glb.b64.txt'), 'wb').write(b64)
    man = {'pieces': {}}
    for r in rs:
        em = []; walk(r, [], em)
        man['pieces'][r.name] = {'tris': tri_count(r), 'empties': em}
    json.dump(man, open(os.path.join(GAME, 'assets', 'lights_pack.manifest.json'), 'w'), indent=1)
    print('glb bytes', len(out), 'b64', len(b64))
    for r in rs: print('%-26s %5d tris' % (r.name, tri_count(r)))
