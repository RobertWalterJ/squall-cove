"""Re-render only the Vulcan per-surface hits with a lower ceiling (-4.5 dB) because short transients decoded at up to -0.1 dBFS.
Writes manifest fragment ac130imp2; deploy_imp merges both fragments."""
import sys, json, os, shutil
import gen_heavy as H
H.CEIL_DB = -4.5
import synthlib as S
import gen_ac130_imp as G


def main():
    S.set_manifest('ac130imp2')
    for sf, mk in G.V_MAKERS.items():
        G.reg('ac130_vulcan_hit_' + sf, mk, 4, 'hit', 'mat', weight=4, max_dist=250, tags=['impact', 'ac130', 'vulcan', sf])
    here = os.path.dirname(os.path.abspath(__file__)); dst = os.path.join(os.path.dirname(here), 'audio')
    mp = os.path.join(dst, 'manifest.json'); man = json.load(open(mp, encoding='utf-8'))
    for frag_name in ('ac130imp', 'ac130imp2'):       # imp2 last so it overrides the first vulcan_hit entries
        frag = json.load(open(os.path.join(here, 'out', 'manifest.%s.json' % frag_name), encoding='utf-8'))
        for id_, e in frag.items():
            shutil.copy2(os.path.join(here, 'out', id_ + '.ogg'), os.path.join(dst, id_ + '.ogg')); man['assets'][id_] = e
    json.dump(man, open(mp, 'w', encoding='utf-8')); print('deployed')


main()
