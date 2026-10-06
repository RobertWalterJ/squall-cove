"""Run every generator module, merge the manifest, run the QA. Usage: python render_all.py [module ...]"""
import os, sys, json, glob, importlib, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
MODULES = ['gen_ambience', 'gen_weather', 'gen_water', 'gen_materials', 'gen_fire_electric', 'gen_vehicles', 'gen_people', 'gen_ui_music']

def main():
    want = sys.argv[1:] or MODULES
    for name in want:
        if not os.path.exists(os.path.join(HERE, name + '.py')): print('skip (not written yet):', name); continue
        t0 = time.time(); m = importlib.import_module(name); m.render(); print('%-18s %.1fs' % (name, time.time() - t0))
    merged = {}
    for f in sorted(glob.glob(os.path.join(HERE, 'out', 'manifest.*.json'))):
        if f.endswith('manifest.json'): continue
        merged.update(json.load(open(f, encoding='utf-8')))
    json.dump(dict(version=1, assets=merged), open(os.path.join(HERE, 'out', 'manifest.json'), 'w', encoding='utf-8'), indent=1)
    print('manifest: %d assets' % len(merged))
    import analyze; analyze.main()

if __name__ == '__main__': main()
