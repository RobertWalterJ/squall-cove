#!/bin/bash
# Rebuild every asset class: GLBs + contact sheets. Usage: ./run_all.sh [part1|part2|all]
set -e
cd "$(dirname "$0")"
part=${1:-all}
if [[ $part == part1 || $part == all ]]; then
  blender -b --python build_boats.py -- 1 2 3 4 > /dev/null 2>&1
  PGMOD=pg_cargo PGOUT=cargo PGCOLS=6 PGGAP=0.6 blender -b --python build_generic.py -- 1 2 3 > /dev/null 2>&1
  PGMOD=pg_cargo PGTYPES=CONTAINER_TYPES PGOUT=containers PGCOLS=4 PGGAP=1.0 blender -b --python build_generic.py -- 1 2 3 4 > /dev/null 2>&1
fi
if [[ $part == part2 || $part == all ]]; then
  for g in structures marine; do blender -b --python build_harbour.py -- $g > /dev/null 2>&1; done
  PGMOD=pg_nature PGTYPES=VEG_TYPES PGOUT=vegetation PGCOLS=6 PGGAP=0.5 blender -b --python build_generic.py -- 1 2 3 4 > /dev/null 2>&1
  mv out/vegetation/sheet.png out/vegetation/sheet_trees.png; mv out/vegetation/report.json out/vegetation/report_trees.json
  PGMOD=pg_nature PGTYPES=GROUND_TYPES PGOUT=vegetation PGCOLS=6 PGGAP=0.3 blender -b --python build_generic.py -- 1 2 3 4 5 6 > /dev/null 2>&1
  mv out/vegetation/sheet.png out/vegetation/sheet_ground.png; mv out/vegetation/report.json out/vegetation/report_ground.json
  PGMOD=pg_nature PGTYPES=ROCK_TYPES PGOUT=rocks PGCOLS=6 PGGAP=0.5 blender -b --python build_generic.py -- 1 2 3 4 5 6 > /dev/null 2>&1
fi
