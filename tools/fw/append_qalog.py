import os
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
p = os.path.join(ROOT, 'QA-LOG.md'); raw = open(p, 'rb').read().decode('utf-8'); crlf = '\r\n' in raw; s = raw.replace('\r\n', '\n')
entry = open(os.path.join(HERE, 'qa-log-entry.md'), encoding='utf-8').read()
head = '## 2026-10-10 realistic baked fire wired in'
if head in s: s = s[:s.index('\n' + head)] if ('\n' + head) in s else s
s = s.rstrip('\n') + '\n' + entry.rstrip('\n') + '\n'
if crlf: s = s.replace('\n', '\r\n')
open(p, 'wb').write(s.encode('utf-8')); print('qa-log updated')
