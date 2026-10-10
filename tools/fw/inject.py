# Injects the FW parts (tools/fw/*.js listed in ORDER) into index.html between /*FW-REGION-START*/ and /*FW-REGION-END*/.
# If the region does not exist yet it is created right after the `window.__sc = { senseEnemy, ...};` line.
import re, sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
ORDER = [l.strip() for l in open(os.path.join(HERE, 'ORDER.txt')) if l.strip() and not l.startswith('#')]
raw = open(os.path.join(ROOT, 'index.html'), 'rb').read().decode('utf-8'); crlf = '\r\n' in raw
s = raw.replace('\r\n', '\n')
parts = []
for f in ORDER:
    p = os.path.join(HERE, f)
    if os.path.exists(p): parts.append(open(p, encoding='utf-8').read().strip('\n'))
region = '/*FW-REGION-START*/\n' + '\n'.join(parts) + '\n/*FW-REGION-END*/'
if '/*FW-REGION-START*/' in s:
    a = s.index('/*FW-REGION-START*/'); b = s.index('/*FW-REGION-END*/') + len('/*FW-REGION-END*/')
    s = s[:a] + region + s[b:]
else:
    m = re.search(r'^window\.__sc = \{ senseEnemy.*\};\n', s, re.M)
    if not m: sys.exit('anchor not found')
    s = s[:m.end()] + region + '\n' + s[m.end():]
if crlf: s = s.replace('\n', '\r\n')
open(os.path.join(ROOT, 'index.html'), 'wb').write(s.encode('utf-8'))
print('injected', len(region), 'chars from', len(parts), 'parts')
