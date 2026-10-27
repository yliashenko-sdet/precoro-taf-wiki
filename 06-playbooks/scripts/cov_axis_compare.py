import sys, re
sys.argv_orig = list(sys.argv)
run_dir, index_f, sigs_dir, PROD = sys.argv[1:5]
sys.argv = ['x', run_dir, index_f, sigs_dir, '/tmp/axis_unused']
exec(open('cov_analyze.py').read().split('# ---- group variants')[0])
exec(open('cov_classify.py').read().split("groups = collections.defaultdict")[0].split("exec(open(__file__")[0]) if False else None
# reuse role() from cov_classify
src_cls = open('cov_classify.py').read()
start = src_cls.index('ACCESSOR = '); end = src_cls.index('def label(names):')
exec(src_cls[start:end])
SKIPW = ('Create', 'Navigate', 'Open', 'Verify')
def sets_of(name, qase, want):
    per = []
    for (n, rep), t in tests.items():
        if t.get('qase') == qase and n == name and t['status'] == 'passed':
            for ph in t['phase']:
                if ph['title'].startswith('Revise') or ph['title'].startswith('Cancel'):
                    for rt, ls in ph['routes'].items():
                        if rt.startswith(want): per.append(ls)
    return (set.intersection(*per), set.union(*per)) if per else None
def cls(a, b):
    c = collections.Counter()
    for (f, n) in (a[0] - b[1]) | (b[0] - a[1]): c[role(f, n)] += 1
    return dict(c)
byq = collections.defaultdict(dict)
for (n, rep), t in tests.items():
    if t.get('qase'): byq[t['qase']][n.split(' > ')[-1]] = n
import itertools
def typ(title):
    m = re.search(r'(Standard PO|Service PO|BPO per items|BPO per total|PO from PR|PO from RFP|SPO from PR)', title); return m.group(1) if m else None
want = 'POST /api/purchaseorders/{id}/revise'
rows = collections.defaultdict(dict)
for q, d in byq.items():
    for title, full in d.items():
        ty = typ(title)
        if ty and 'revised' in title: rows[ty][q] = sets_of(full, q, want)
labels = {'6319': 'pending/approver', '6320': 'pending/creator', '6321': 'approved/creator', '6323': 'closed/creator'}
for ty, qs in sorted(rows.items()):
    print(ty)
    for a, b in itertools.combinations(sorted(k for k, v in qs.items() if v), 2):
        print(f'   {labels.get(a,a)} <> {labels.get(b,b)}:', cls(qs[a], qs[b]))
