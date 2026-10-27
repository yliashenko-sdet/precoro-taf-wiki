import sys, re
run_dir, index_f, sigs_dir, PROD = sys.argv[1:5]
sys.argv = ['x', run_dir, index_f, sigs_dir, '/tmp/axis_unused']
exec(open('cov_analyze.py').read().split('# ---- group variants')[0])
src_cls = open('cov_classify.py').read()
exec(src_cls[src_cls.index('ACCESSOR = '):src_cls.index('def label(names):')])
TYPES = ['Standard PO', 'Service PO', 'BPO per items', 'BPO per total', 'PO from PR', 'PO from RFP', 'SPO from PR']
CELLS = {'6319': 'pend/appr', '6320': 'pend/crea', '6321': 'appr/crea', '6323': 'clos/crea'}
def typ(t):
    m = re.search('|'.join(TYPES), t); return m.group(0) if m else None
# L[(type, cell)] = {route: (stable, possible)} over action-step write requests
L = {}
for (n, rep), t in tests.items():
    q = t.get('qase'); ty = typ(n.split(' > ')[-1])
    if q in CELLS and ty and t['status'] == 'passed' and 'revised' in n:
        per = L.setdefault((ty, q), collections.defaultdict(list))
        for ph in t['phase']:
            if ph['title'].startswith('Revise'):
                for rt, ls in ph['routes'].items():
                    if not rt.startswith('GET '): per[rt].append(ls)
def lines(ty, q):
    out = set()
    for rt, v in L.get((ty, q), {}).items():
        for (f, n) in set.union(*v): out.add((rt, f, n))
    return out
t0, s0 = 'Standard PO', '6320'
print('anchors: type', t0, 'cell', CELLS[s0])
print('cell (type x state): lines | interaction lines not in [same type @ anchor state] U [anchor type @ same state]: logic/data/access/serial')
for ty in TYPES:
    row = []
    for q in CELLS:
        if (ty, q) == (t0, s0): continue
        cell = lines(ty, q); base = lines(ty, s0) | lines(t0, q)
        inter = cell - base
        c = collections.Counter(role(f, n) for (_, f, n) in inter)
        row.append(f"{CELLS[q]}:{len(cell)}|{sum(c.values())}({c['logic']}/{c['data']}/{c['access']}/{c['serialization']})")
    print(f'{ty:14}', '  '.join(row))
