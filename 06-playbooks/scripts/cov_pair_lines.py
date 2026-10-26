import sys
args = sys.argv[1:]  # qase labelA labelB step_prefix route
qase, A, B, stepp, want = args
sys.argv = ['x', '/Users/yevhenlyashenko/local-runs/2026-10-27-0018-t132-pilot', 'data/index.jsonl', 'data/sigs', 'out2']
exec(open('cov_analyze.py').read().split('# ---- group variants')[0])
def get(label):
    sets = []
    for (name, rep), t in tests.items():
        if t.get('qase') == qase and (' '+label+' can be revised') in name.split(' > ')[-1]:
            for ph in t['phase']:
                if ph['title'].startswith(stepp):
                    for rt, ls in ph['routes'].items():
                        if rt.startswith(want): sets.append(ls)
    return set.intersection(*sets), set.union(*sets)
sa, pa = get(A); sb, pb = get(B)
PROD = '/Users/yevhenlyashenko/Work/src/precoro'
def show(only, tag):
    print(f'--- only in {tag}: {len(only)}')
    for f, n in sorted(only):
        try: txt = open(f'{PROD}/{f}').read().split('\n')[n-1].strip()[:110]
        except Exception as e: txt = '?'
        print(f'{f}:{n}  {txt}')
show(sa - pb, A); show(sb - pa, B)
