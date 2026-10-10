#!/bin/bash
# usage: run_all.sh WORKDIR preset[:extra,flags] ...   e.g.  run_all.sh /tmp/w tree:--renderonly campfire:--renderonly,--blendonly
# Runs ONE Blender at a time. Each preset logs to WORKDIR/<preset>.log
B="${BLENDER:-C:/Users/Robert Walter-Joseph/Code Projects/squall-cove/_tools/blender-4.2.9-windows-x64/blender.exe}"
HERE="$(cd "$(dirname "$0")" && pwd)"
W="$1"; shift
for spec in "$@"; do
  p="${spec%%:*}"; fl=""; [[ "$spec" == *:* ]] && fl="${spec#*:}" && fl="${fl//,/ }"
  "$B" --background --factory-startup --python "$HERE/bake_fire.py" -- "$p" "$W" --samples 20 $fl > "$W/$p.log" 2>&1
done
