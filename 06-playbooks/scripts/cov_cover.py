#!/usr/bin/env python3
"""T1-32: which cells of a parametrized grid are redundant by coverage subsumption.

Cells = variants of the looped tests of one spec file (all its sites). A cell's lines = the product lines its
action and verify steps executed (all requests after the preparation steps, both repeats united when given).
Greedy set cover: keep the cell that adds most uncovered lines until every line is covered, and at least one
cell per site (a Qase case needs a test). The rest are removable: everything they execute is executed by a kept cell
with the same test body shape.
Modes: strict = all lines;  relaxed = serialization and access lines ignored (only logic and data count).
Usage: cover.py <run dir> <index.jsonl> <sigs dir> <product repo> [--show]
"""
import sys
run_dir, index_f, sigs_dir, PROD = sys.argv[1:5]
SHOW = '--show' in sys.argv
sys.argv = ['x', run_dir, index_f, sigs_dir, '/tmp/cover_unused']
exec(open(__file__.rsplit('/', 1)[0] + '/cov_analyze.py').read().split('# ---- group variants')[0])
src_cls = open(__file__.rsplit('/', 1)[0] + '/cov_classify.py').read()
exec(src_cls[src_cls.index('ACCESSOR = '):src_cls.index('def label(names):')])
PREP = ('Create', 'Navigate', 'Open', 'Document setup', 'Add ', 'Confirm')

cells = collections.defaultdict(dict)   # file -> {(qase, name): lines}
for (n, rep), t in tests.items():
    if t.get('qase') is None or t['status'] != 'passed': continue
    cur = cells[t['file']].setdefault((t['qase'], n.split(' > ')[-1]), [])
    ls = set()
    for ph in t['phase']:
        if ph['title'].startswith(PREP): continue
        for rt, lines in ph['routes'].items(): ls |= {(f, x) for f, x in lines}
    cur.append(ls)
for file, cs in sorted(cells.items()):
    # variants seen in repeats: lines in the cell = union of repeats (the noise floor was 0 in the pilot)
    cell = {k: set.union(*v) for k, v in cs.items()}
    if len(cell) < 3: continue
    for mode in ('strict', 'relaxed'):
        def keep(l): return mode == 'strict' or role(*l) in ('logic', 'data')
        cl = {k: {l for l in v if keep(l)} for k, v in cell.items()}
        universe = set.union(*cl.values())
        kept, covered = [], set()
        while covered != universe:
            k = max(cl, key=lambda c: len(cl[c] - covered))
            kept.append(k); covered |= cl[k]
        for q in {k[0] for k in cell}:
            if not any(k[0] == q for k in kept):
                kept.append(max((k for k in cell if k[0] == q), key=lambda c: len(cl[c])))
        print(f'{file} [{mode}]: {len(cell)} cells -> keep {len(kept)}, removable {len(cell) - len(kept)}')
        if SHOW and mode == 'relaxed':
            for q in sorted({k[0] for k in cell}):
                print('   ', q, 'keep:', [k[1][-40:] for k in kept if k[0] == q])
