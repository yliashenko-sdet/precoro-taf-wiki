#!/usr/bin/env python3
"""Які ендпоінти зі списку Swagger згадані в API-клієнті TAF (евристика по шляху)."""
import re, sys, os, collections
lst, repo = sys.argv[1], sys.argv[2]
lines = open(lst, encoding='utf-8').read().split('\n')
eps = [(lines[i], lines[i+1].strip()) for i in range(len(lines)-1) if re.match(r'^(GET|POST|PUT|PATCH|DELETE)$', lines[i]) and lines[i+1].startswith('/api/')]
src = ''
for d in ('src/api', 'src/ui/web/utilities', 'src/ui/web/tests/fixtures'):
    for root, _, files in os.walk(os.path.join(repo, d)):
        for f in files:
            if f.endswith('.ts'): src += open(os.path.join(root, f), encoding='utf-8').read() + '\n'
norm = re.sub(r'\$\{[^}]+\}', '{x}', src)
missing = []
for verb, path in eps:
    p = re.sub(r'\{[^}]+\}', '{x}', path[4:])
    if not re.search(re.escape(p).replace(r'\{x\}', r'\{x\}') + r'(?![A-Za-z_-])', norm): missing.append((verb, path))
print(f"endpoints {len(eps)} referenced {len(eps)-len(missing)} missing {len(missing)}")
print(collections.Counter(m[1].split('/')[2].lower() for m in missing).most_common(12))
for verb, path in missing:
    if re.search(r'mass-|approve-review|_import$|/pay$|receive_all|take_over|manual_complete|/send$|/revise$', path): print(verb, path)
