#!/bin/sh
G="C:/Users/Robert Walter-Joseph/Code Projects/squall-cove-large"
"$G/../squall-cove/_tools/blender-4.2.9-windows-x64/blender.exe" -b --python "$G/blender/battle/build_battle.py" -- "$G/assets" "$G/blender/review/battle" "$@" 2>&1 | grep -E "MODEL|GLB|Saved|Error|error|Traceback|File |assert|DONE|Exception|line "
