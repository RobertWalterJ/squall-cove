"""Copy the rendered assets and the merged manifest into ../audio (served at audio/<id>.ogg). Run after render_all.py."""
import os, json, glob, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, 'out'); DST = os.path.join(os.path.dirname(HERE), 'audio')
os.makedirs(DST, exist_ok=True)
merged = {}
for f in sorted(glob.glob(os.path.join(OUT, 'manifest.*.json'))):
    if f.endswith('manifest.json'): continue
    try: merged.update(json.load(open(f, encoding='utf-8')))
    except Exception as e: print('skipping fragment being written:', os.path.basename(f))
n = 0
for id_ in list(merged):
    src = os.path.join(OUT, id_ + '.ogg')
    if not os.path.exists(src): merged.pop(id_); continue
    shutil.copy2(src, os.path.join(DST, id_ + '.ogg')); n += 1
RULES = [('amb_battle', 'weapons'), ('amb_farm', 'weather'), ('amb_town', 'weather'), ('amb_quay', 'weather'),
         ('wpn_', 'weapons'), ('imp_', 'weapons'), ('ui_flag_', 'weapons'), ('ui_tickets_low', 'weapons'), ('ui_respawn', 'weapons'), ('ui_victory', 'weapons'), ('ui_defeat', 'weapons'), ('ui_hitmarker', 'weapons'), ('ui_kill', 'weapons'),
         ('step_', 'people'), ('foley_', 'people'),
         ('amb_', 'core'), ('ui_', 'core'), ('hold_', 'core'), ('water_splash_', 'core'), ('water_wake', 'core'), ('water_object_in', 'core'), ('npc_', 'core'), ('mat_wood_knock', 'core'), ('mat_stone_tock', 'core'),
         ('mat_wood_crack', 'core'), ('mat_glass_shatter', 'core'), ('ppl_step_grass', 'core'), ('ppl_step_sand', 'core'), ('ppl_step_wood', 'core'), ('ppl_step_deck', 'core'), ('ppl_step_water', 'core'), ('ppl_stone_place', 'core'),
         ('veh_eng_', 'boats'), ('veh_heli', 'aircraft'), ('veh_prop', 'aircraft'), ('veh_bomber', 'aircraft'), ('veh_water_drop', 'aircraft'), ('veh_gun', 'weapons'), ('veh_mg', 'weapons'), ('veh_', 'boats'),
         ('wx_', 'weather'), ('mus_', 'music'), ('ppl_', 'people'), ('water_', 'water'), ('fire_', 'fx'), ('elec_', 'fx'), ('heat_', 'fx'), ('cold_', 'fx'), ('mat_', 'mat'), ('grain_', 'mat'), ('lava_', 'mat'), ('pile_', 'mat'), ('glass_', 'mat'), ('furnace_', 'fx'), ('seed_', 'fx'), ('sprout_', 'fx'), ('quake_', 'fx'), ('rubble_', 'mat')]
for id_, e in merged.items():
    for pre, g in RULES:
        if id_.startswith(pre): e['group'] = g; e['lazy'] = g != 'core'; break
import collections
sz = collections.Counter(); 
for id_, e in merged.items(): sz[e['group']] += os.path.getsize(os.path.join(DST, id_ + '.ogg')) if os.path.exists(os.path.join(DST, id_ + '.ogg')) else 0
print({k: round(v / 1048576.0, 2) for k, v in sz.items()})
json.dump(dict(version=1, assets=merged), open(os.path.join(DST, 'manifest.json'), 'w', encoding='utf-8'))
tot = sum(os.path.getsize(os.path.join(DST, f)) for f in os.listdir(DST)) / 1048576.0
print('deployed %d assets, %.1f MB' % (n, tot))
