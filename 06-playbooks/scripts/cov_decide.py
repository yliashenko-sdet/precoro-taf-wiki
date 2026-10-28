#!/usr/bin/env python3
"""T1-32: decision table per (spec file, QaseID) group from the pool coverage run.
Equivalent variants = pairs classified serialization-only; only full cliques are merged (greedy clique cover).
Joins history veto (divergence.json sites) and nightly durations. Usage: decide.py <classify.txt> <run dir> <out.json>"""
import re, sys, json, os, collections, glob
cls, rundir, out = sys.argv[1:4]
A = os.path.expanduser('~/Work/Precoro/')
div = {(x['file'], x['line']): x for x in json.load(open(A + 'artifacts/param-tests/divergence.json'))['sites']}
sites = []
for x in json.load(open(A + 'artifacts/param-tests/sites.json')):
    d = div.get((x['file'], x['line']))
    if d: sites.append({'file': x['file'], 'qase': x.get('qase', ''), 'verdict': d['verdict']})
# nightly: mean duration by (basename, last title segment), last 14 builds
import statistics
dur = collections.defaultdict(list)
for f in sorted(glob.glob(A + 'stats/raw/nightly/[0-9]*.json'), key=lambda p: int(os.path.basename(p).split('.')[0]))[-14:]:
    if f.endswith('.failures.json'): continue
    for k, st, ms in json.load(open(f)):
        proj, file, title = [x.strip() for x in k.split(' / ', 2)]
        if st == 'pass': dur[(os.path.basename(file), title)].append(ms / 1000)
# run: test names per (file, qase) group
names = collections.defaultdict(dict)
for l in open(os.path.join(rundir, 'steps.jsonl')):
    o = json.loads(l)
    if o['k'] == 'test-begin' and o.get('qase') is not None:
        names[(os.path.basename(o['file']), str(o['qase']))][o['test']] = 1
def veto(file, qase):
    v = [s for s in sites if os.path.basename(s['file']) == file and qase in re.findall(r"\d+", s.get('qase', ''))]
    return v[0]['verdict'] if v else '?'
def mean_dur(file, nms):
    xs = []
    for n in nms:
        title = n.split(' > ')[-1]
        d = dur.get((file, title)) or [x for (f, t), v in dur.items() if f == file and (t.endswith(title) or title.endswith(t)) for x in v]
        if d: xs.append(statistics.mean(d))
    return statistics.mean(xs) if xs else None
grp = None; data = collections.OrderedDict()
for l in open(cls):
    m = re.match(r'## (\S+) QaseID (\S+)', l)
    if m: grp = (m.group(1), m.group(2)); data[grp] = []; continue
    m = re.match(r'(.+?) <> (.+?): (\S+)', l)
    if m and grp: data[grp].append((m.group(1), m.group(2), m.group(3)))
rows = []
for (file, qase), pairs in data.items():
    if not pairs: continue
    vs = sorted({x for a, b, _ in pairs for x in (a, b)})
    eq = {frozenset((a, b)) for a, b, v in pairs if v == 'serialization-only'}
    left = set(vs); cliques = []
    while left:  # greedy clique cover on the equivalence graph
        best = []
        for s in sorted(left):
            c = [s]
            for t in sorted(left):
                if t != s and all(frozenset((t, u)) in eq for u in c): c.append(t)
            if len(c) > len(best): best = c
        cliques.append(best); left -= set(best)
    kept = len(cliques); drop = len(vs) - kept
    nm = list(names.get((file, qase), {}))
    d = mean_dur(file, nm)
    rows.append({'file': file, 'qase': qase, 'variants': len(vs), 'pairs': len(pairs), 'ser_only': len(eq), 'cliques': kept,
                 'drop': drop, 'veto': veto(file, qase), 'mean_s': round(d, 1) if d else None,
                 'cliques_detail': [c for c in cliques if len(c) > 1]})
json.dump(rows, open(out, 'w'), indent=1)
print(f"{'file':34s} {'qase':>5s} var drop veto           mean_s  saved_min")
tv = td = tdc = 0; mins = minc = 0
for r in sorted(rows, key=lambda r: -r['drop']):
    sv = r['drop'] * (r['mean_s'] or 0) / 60
    print(f"{r['file'][:34]:34s} {r['qase']:>5s} {r['variants']:3d} {r['drop']:4d} {r['veto']:14s} {str(r['mean_s']):>6s} {sv:6.1f}")
    tv += r['variants']; td += r['drop']
    mins += sv
    if r['veto'] != 'do-not-touch': tdc += r['drop']; minc += sv
print('variants', tv, 'drop', td, f'({mins:.0f} min)', '| without do-not-touch:', tdc, f'({minc:.0f} min)')
