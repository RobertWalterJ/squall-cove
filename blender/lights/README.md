# blender/lights

Lighting asset pack for Squall Cove (`assets/lights_pack.glb`). `MODEL-NOTES-LIGHTS.md` at the repo root lists node names, pivots, the `lightpt_*` and `cable_*` tables and how to instance them.

    python blender/lights/build_lights.py       # writes assets/lights_pack.glb, .glb.b64.txt, lights_pack.manifest.json
    python blender/lights/verify_lights.py      # names, bounds, tris, lightpt beam directions, floating-island check, size
    python blender/lights/build_lights_fx.py    # assets/lights_fx_* (cone mesh + texture, beam glow, flare, pool, wet smear)
    python blender/lights/make_docs.py          # regenerates MODEL-NOTES-LIGHTS.md from the manifest
    blender -b --factory-startup -P blender/lights/render_lights.py -- tiles <ABSOLUTE out dir> 360
    blender -b --factory-startup -P blender/lights/render_lights.py -- night <ABSOLUTE out png> 1600 760 40
    python blender/lights/make_sheet.py         # docs/lights_preview_sheet.png

Files: `lights_lib.py` (geometry, scene graph, GLB writer, shared parts), `pieces_a.py` (tower, poles, wall/roof, lamp posts, string lights), `pieces_b.py` (generators, cables, junction boxes, searchlights, vehicle lights). Python + numpy (+ scipy for verify). Blender is used for previews only; give it absolute paths (a relative path lands on the drive root).
