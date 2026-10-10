# Applies the small FW hooks to index.html (idempotent: a hook already applied is skipped). Run from anywhere.
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
exec(open(os.path.join(HERE, 'hooklist.py'), encoding='utf-8').read())
raw = open(os.path.join(ROOT, 'index.html'), 'rb').read().decode('utf-8'); crlf = '\r\n' in raw
s = raw.replace('\r\n', '\n'); bad = 0
for name, old, new in HOOKS:
    if new in s: print('  already', name); continue
    n = s.count(old)
    if n != 1: print('  PROBLEM', name, 'found', n); bad += 1; continue
    s = s.replace(old, new); print('  applied', name)
if bad: sys.exit('some hooks failed; index.html not written')
if crlf: s = s.replace('\n', '\r\n')
open(os.path.join(ROOT, 'index.html'), 'wb').write(s.encode('utf-8'))
