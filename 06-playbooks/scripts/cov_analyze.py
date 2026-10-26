#!/usr/bin/env python3
"""T1-32 pilot: do the variants of a parametrized test execute the same product code on the action step?

Inputs
  run dir      steps.jsonl from steps-reporter.js (test and step wall-clock intervals)
  index.jsonl  one line per web request, written by the container's prepend.php
  sigs dir     <sha1>.json.gz = {file: "1-5,9"} executed lines of one request
Method
  tests with the same (spec file, QaseID) are variants of one loop. Each top-level test.step is a phase.
  A request belongs to the phase whose [start, end] contains its start time. Per phase and route
  (method + path with ids replaced) the executed lines of all its requests are united.
  A variant is run twice (--repeat-each=2): lines seen in both runs are "stable", lines seen in either
  are "possible". Run-to-run difference of one variant is the noise floor.
  Variant A differs from B on a route if A has a stable line that B never executed (possible set of B).
Usage: cov_analyze.py <run dir> <index.jsonl> <sigs dir> <out dir>
"""
import collections, glob, gzip, json, os, re, sys

run_dir, index_f, sigs_dir, out_dir = sys.argv[1:5]
os.makedirs(out_dir, exist_ok=True)
GRACE = 0.05  # s, request start may precede step start by clock rounding

def expand(ranges):
    s = set()
    for part in ranges.split(','):
        if not part:
            continue
        a, _, b = part.partition('-')
        s.update(range(int(a), int(b or a) + 1))
    return s

_sig_cache = {}
def lines_of(sig):
    if sig not in _sig_cache:
        d = json.load(gzip.open(os.path.join(sigs_dir, sig + '.json.gz'), 'rt'))
        _sig_cache[sig] = {f: expand(r) for f, r in d.items() if f.startswith('src/')}
    return _sig_cache[sig]

def route(method, path):
    p = re.sub(r'/[0-9a-f]{8}-[0-9a-f-]{27}', '/{uuid}', path)
    p = re.sub(r'/\d+', '/{id}', p)
    return f'{method} {p}'

# ---- steps -> phases per (test, rep)
tests = {}
for l in open(os.path.join(run_dir, 'steps.jsonl')):
    o = json.loads(l)
    key = (o['test'], o.get('rep', 0))
    t = tests.setdefault(key, {'steps': [], 'status': None})
    if o['k'] == 'test-begin':
        t.update(qase=o['qase'], file=os.path.basename(o['file']), project=o['project'])
    elif o['k'] == 'test-end':
        t['status'] = o['status']
    elif o['k'] == 'step' and o['cat'] == 'test.step' and o['parent'] is None:
        t['steps'].append(o)
for t in tests.values():
    t['steps'].sort(key=lambda s: s['t0'])

# ---- requests -> phases
reqs = [json.loads(l) for l in open(index_f)]
reqs = [r for r in reqs if r['m'] != 'OPTIONS' and r.get('ts')]
reqs.sort(key=lambda r: r['ts'])
import bisect
tss = [r['ts'] for r in reqs]
for key, t in tests.items():
    t['phase'] = []  # per step: {route: set((file, line))}, plus counts
    for s in t['steps']:
        lo = bisect.bisect_left(tss, s['t0'] - GRACE)
        hi = bisect.bisect_right(tss, s['t0'] + s['d'] + GRACE)
        by = collections.defaultdict(set)
        n = collections.Counter()
        for r in reqs[lo:hi]:
            rt = route(r['m'], r['u'])
            n[rt] += 1
            for f, ls in lines_of(r['s']).items():
                by[rt].update((f, x) for x in ls)
        t['phase'].append({'title': s['title'], 'routes': by, 'n': n})

# ---- group variants
groups = collections.defaultdict(lambda: collections.defaultdict(list))
for (name, rep), t in tests.items():
    if t.get('qase') is None:
        continue
    groups[(t['file'], t['qase'])][name].append((rep, t))

def label(names):
    toks = [n.split(' > ')[-1].split(' ') for n in names]
    pre = len(os.path.commonprefix(toks))
    suf = len(os.path.commonprefix([x[::-1] for x in toks]))
    return {n: ' '.join(t[pre:len(t) - suf]) or n for n, t in zip(names, toks)}

def stable_possible(runs, i, rt):
    sets = [r[1]['phase'][i]['routes'].get(rt, set()) for r in runs if i < len(r[1]['phase'])]
    sets = [s for s in sets if s is not None]
    if not sets:
        return set(), set()
    return set.intersection(*sets), set.union(*sets)

def by_file(lines):
    c = collections.Counter(f for f, _ in lines)
    return dict(c.most_common(6))

report = []
for (file, qase), variants in sorted(groups.items()):
    names = sorted(variants)
    lab = label(names)
    status = {n: [r[1]['status'] for r in variants[n]] for n in names}
    ok = [n for n in names if all(s == 'passed' for s in status[n]) and len(variants[n]) >= 1]
    g = {'file': file, 'qase': qase, 'variants': {n: lab[n] for n in names}, 'status': status, 'steps': []}
    nsteps = max(len(r[1]['steps']) for n in names for r in variants[n])
    for i in range(nsteps):
        titles = {lab[n]: variants[n][0][1]['steps'][i]['title'] for n in names if i < len(variants[n][0][1]['steps'])}
        routes = set()
        for n in ok:
            for r in variants[n]:
                if i < len(r[1]['phase']):
                    routes.update(r[1]['phase'][i]['routes'])
        step = {'i': i, 'titles': titles, 'routes': []}
        for rt in sorted(routes):
            present = [n for n in ok if any(i < len(r[1]['phase']) and rt in r[1]['phase'][i]['routes'] for r in variants[n])]
            sp = {n: stable_possible(variants[n], i, rt) for n in present}
            # noise: lines in a variant's possible set but not in its stable set
            noise = {lab[n]: len(sp[n][1] - sp[n][0]) for n in present}
            diffs = {}
            for a in present:
                for b in present:
                    if a == b:
                        continue
                    only = sp[a][0] - sp[b][1]
                    if only:
                        diffs[f'{lab[a]} > {lab[b]}'] = {'lines': len(only), 'files': by_file(only)}
            step['routes'].append({'route': rt, 'in_variants': len(present), 'of': len(ok), 'noise': noise,
                                   'diffs': diffs, 'lines': {lab[n]: len(sp[n][1]) for n in present}})
        g['steps'].append(step)
    report.append(g)

json.dump(report, open(os.path.join(out_dir, 'coverage_report.json'), 'w'), indent=1, default=list)

# ---- markdown summary
def non_get(rt):
    return not rt.startswith('GET ')
lines = ['# T1-32 pilot: coverage by variant', '']
for g in report:
    lines += [f"## {g['file']} QaseID {g['qase']}: {len(g['variants'])} variants", '',
              'Variants: ' + '; '.join(g['variants'].values()), '']
    bad = [n for n, s in g['status'].items() if not all(x == 'passed' for x in s)]
    if bad:
        lines += ['Not passed (excluded from comparison): ' + '; '.join(g['variants'][n] + ' ' + str(g['status'][n]) for n in bad), '']
    for st in g['steps']:
        t = sorted(set(st['titles'].values()))
        lines.append(f"### step {st['i']}: {t[0] if len(t) == 1 else ' | '.join(t[:3])}")
        diff_routes = [r for r in st['routes'] if r['diffs']]
        same_routes = [r for r in st['routes'] if not r['diffs']]
        lines.append(f"routes {len(st['routes'])}: identical {len(same_routes)}, differing {len(diff_routes)}")
        for r in diff_routes:
            top = sorted(r['diffs'].items(), key=lambda kv: -kv[1]['lines'])[:3]
            lines.append(f"- {r['route']} (in {r['in_variants']}/{r['of']}, noise max {max(r['noise'].values() or [0])}): " +
                         '; '.join(f"{k}: {v['lines']} lines {v['files']}" for k, v in top))
        lines.append('')
open(os.path.join(out_dir, 'coverage_report.md'), 'w').write('\n'.join(lines))
print('groups', len(report), '->', os.path.join(out_dir, 'coverage_report.md'))
