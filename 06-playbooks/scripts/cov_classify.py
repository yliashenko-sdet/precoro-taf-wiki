#!/usr/bin/env python3
"""T1-32: classify the lines that differ between two variants by their role.

Per pair of variants of one loop (same spec file + QaseID), on the action step's write requests
(POST/PUT/PATCH/DELETE), the lines one variant executed (in both repeats) and the other never did are
split into:
  serialization  Transformers/*, and entity lines that are plain accessors (return $this->x; getX)
  access         Voter classes (who may see / do it)
  data           Repository classes (query building)
  logic          everything else (services, handlers, entity methods with branches)
A pair with no `logic` and no `data` lines differs only in how the response is built.
Usage: cov_classify.py <run dir> <index.jsonl> <sigs dir> <product repo> [--lines]
"""
import re, sys
sys.argv_orig = list(sys.argv)
args = [a for a in sys.argv[1:] if not a.startswith('--')]
show = '--lines' in sys.argv
run_dir, index_f, sigs_dir, PROD = args[:4]
sys.argv = ['x', run_dir, index_f, sigs_dir, '/tmp/cov_classify_unused']
exec(open(__file__.rsplit('/', 1)[0] + '/cov_analyze.py').read().split('# ---- group variants')[0])

ACCESSOR = re.compile(r'^\s*(return\s+\$this->\w+(\s*\?\?\s*[^;]+)?;|return\s+self::\w+(\(\))?\[?[^;]*;|(public|protected)\s+(static\s+)?function\s+(get|is|has)\w*\(.*\)(:\s*\??\S+)?\s*\{?\s*|\}|\{|case\s+.*|self::\w+\s*=>.*|\s*\'?\w+\'?\s*=>.*)$')
_src = {}
def src(f, n):
    if f not in _src:
        try: _src[f] = open(f'{PROD}/{f}').read().split('\n')
        except OSError: _src[f] = []
    return _src[f][n - 1] if 0 < n <= len(_src[f]) else ''

FUNC = re.compile(r'function\s+(\w+)\s*\(')
def in_short_accessor(f, n):
    """the line sits in a getX/isX/hasX method of at most 8 lines"""
    lines = _src.get(f) or []
    for i in range(n - 1, max(n - 10, 0), -1):
        m = FUNC.search(lines[i - 1]) if i - 1 < len(lines) else None
        if m:
            end = next((j for j in range(i, min(i + 9, len(lines))) if re.match(r'^    \}\s*$', lines[j])), None)
            return bool(re.match(r'(get|is|has)[A-Z_]', m.group(1))) and end is not None and end - i <= 8
    return False

def role(f, n):
    if '/Transformers/' in f or f.endswith('Transformer.php'): return 'serialization'
    if f.endswith('Voter.php'): return 'access'
    if f.endswith('Repository.php'): return 'data'
    if '/Entity/' in f and (ACCESSOR.match(src(f, n)) or in_short_accessor(f, n)): return 'serialization'
    return 'logic'

def label(names):
    toks = [n.split(' > ')[-1].split(' ') for n in names]
    pre = len(os.path.commonprefix(toks)); suf = len(os.path.commonprefix([x[::-1] for x in toks]))
    return {n: ' '.join(t[pre:len(t) - suf]) or n for n, t in zip(names, toks)}

windows = {}
for l in open(os.path.join(run_dir, 'steps.jsonl')):
    o = json.loads(l)
    if o['k'] == 'test-end': windows[(o['test'], o.get('rep', 0))] = (o['t0'], o['d'])
groups = collections.defaultdict(lambda: collections.defaultdict(list))
for (name, rep), t in tests.items():
    if t.get('qase') is not None and t['status'] == 'passed':
        name = name
        t['key'] = (name, rep); groups[(t['file'], t['qase'])][name].append(t)

SKIP = ('Create', 'Navigate', 'Open', 'Verify')
WHOLE = '--whole' in sys.argv_orig if hasattr(sys, 'argv_orig') else False
def whole_sets(key):
    t0, d = windows[key]
    lo = bisect.bisect_left(tss, t0 - GRACE); hi = bisect.bisect_right(tss, t0 + d + GRACE)
    per = collections.defaultdict(set)
    for r in reqs[lo:hi]:
        if r['m'] == 'GET': continue
        for f, ls in lines_of(r['s']).items(): per[route(r['m'], r['u'])].update((f, x) for x in ls)
    return per

def action_sets(runs):
    """{route: (stable, possible)} over the action steps' write requests of one variant's repeats"""
    per = collections.defaultdict(list)
    for t in runs:
        for ph in t['phase']:
            if ph['title'].startswith(SKIP): continue
            for rt, ls in ph['routes'].items():
                if not rt.startswith('GET '): per[rt].append(ls)
    return {rt: (set.intersection(*v), set.union(*v)) for rt, v in per.items() if len(v) >= len(runs)}

for (file, qase), variants in sorted(groups.items()):
    names = sorted(variants)
    if len(names) < 2: continue
    lab = label(names)
    if '--whole' in sys.argv_orig:
        sets = {}
        for n in names:
            per = collections.defaultdict(list)
            for t in variants[n]:
                for rt, ls in whole_sets(t['key']).items(): per[rt].append(ls)
            sets[n] = {rt: (set.intersection(*v), set.union(*v)) for rt, v in per.items() if len(v) >= len(variants[n])}
    else:
        sets = {n: action_sets(variants[n]) for n in names}
    print(f'\n## {file} QaseID {qase}')
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            c = collections.Counter(); logic = []
            for rt in set(sets[a]) & set(sets[b]):
                sa, pa = sets[a][rt]; sb, pb = sets[b][rt]
                for (f, n) in (sa - pb) | (sb - pa):
                    r = role(f, n); c[r] += 1
                    if r in ('logic', 'data'): logic.append((f, n))
            verdict = 'serialization-only' if not (c['logic'] or c['data']) else 'logic'
            print(f'{lab[a]} <> {lab[b]}: {verdict}  ' + ' '.join(f'{k}={v}' for k, v in sorted(c.items())))
            if show:
                for f, n in sorted(logic)[:12]: print(f'     {f.split("src/")[-1]}:{n}  {src(f, n).strip()[:100]}')
