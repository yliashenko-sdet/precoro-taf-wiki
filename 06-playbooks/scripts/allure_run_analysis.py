#!/usr/bin/env python3
"""Аналіз одного прогону з allure-report/data: тривалості, підготовка за кроками, падіння, воркери."""
import json, glob, re, sys, collections, statistics, os
root = sys.argv[1] if len(sys.argv) > 1 else '.'
tests = []
for f in glob.glob(os.path.join(root, 'test-cases', '*.json')):
    d = json.load(open(f))
    labs = collections.defaultdict(list)
    for l in d.get('labels', []): labs[l['name']].append(l['value'])
    ts = d.get('testStage', {}) or {}
    tests.append({'name': d['name'], 'status': d['status'], 'dur': d['time'].get('duration', 0),
                  'start': d['time'].get('start', 0), 'stop': d['time'].get('stop', 0),
                  'proj': (labs.get('parentSuite') or ['?'])[0], 'file': (labs.get('suite') or ['?'])[0],
                  'thread': (labs.get('thread') or ['?'])[0], 'tags': labs.get('tag', []),
                  'retries': d.get('retriesCount', 0), 'msg': (ts.get('statusMessage') or '')[:300], 'steps': ts.get('steps', [])})
ex = [t for t in tests if t['status'] != 'skipped']
durs = sorted(t['dur'] for t in ex)
print(f"tests {len(tests)} executed {len(ex)} status {collections.Counter(t['status'] for t in tests).most_common()}")
print(f"duration s: median {statistics.median(durs)/1000:.0f} p90 {durs[int(len(durs)*.9)]/1000:.0f} max {durs[-1]/1000:.0f}; machine-time {sum(durs)/3600000:.2f}h")
print("\nTOP 20 longest:")
for t in sorted(ex, key=lambda x: -x['dur'])[:20]: print(f"  {t['dur']/1000:6.0f}s {t['proj'][:22]:22s} {t['file'][:34]:34s} {t['name'][:60]}")
byfile = collections.Counter(); nfile = collections.Counter()
for t in ex: byfile[t['file']] += t['dur']; nfile[t['file']] += 1
print("\nTOP files by machine-time:")
for f, v in byfile.most_common(12): print(f"  {v/3600000:5.2f}h n={nfile[f]:4d} avg={v/nfile[f]/1000:5.0f}s {f}")
prep = re.compile(r'before hooks|creat|prepar|setup|set up|login|log in|precondition|navigate|open |go to|goto|fill|add |select|upload|configur|enable|disable|generate|import', re.I)
ver = re.compile(r'verify|check|expect|assert|validat|should|ensure|compare|confirm that', re.I)
after = re.compile(r'after hooks|cleanup|clean up|delete|remove|restore|teardown', re.I)
agg = collections.Counter()
for t in ex:
    for s in t['steps']:
        n = s.get('name', ''); d = (s.get('time') or {}).get('duration') or 0
        if after.search(n) and not ver.search(n): agg['teardown'] += d
        elif ver.search(n): agg['verify'] += d
        elif prep.search(n): agg['prep'] += d
        else: agg['other'] += d
tot = sum(agg.values()) or 1
print("\nstep time share:", {k: f"{v/tot*100:.0f}%" for k, v in agg.items()})
bh = sum((s.get('time') or {}).get('duration') or 0 for t in ex for s in t['steps'] if s.get('name') == 'Before Hooks')
print(f"Before Hooks: {bh/3600000:.2f}h = {bh/sum(durs)*100:.0f}%")
def cat(m):
    if re.search(r'Timeout \d+ms exceeded|Test timeout of|exceeded while', m): return 'timeout'
    if re.search(r'toBeVisible|toHaveText|toContainText|toHaveCount|toBeHidden|toHaveValue', m): return 'web-first expect'
    if re.search(r'expect\(received\)|toBe\(|toEqual|toContain\(|Expected:', m): return 'value expect'
    if re.search(r'net::|ECONNRESET|ETIMEDOUT|502|503|504', m): return 'network'
    if re.search(r'toMatchSnapshot|screenshot', m, re.I): return 'visual'
    return 'other'
fails = [t for t in tests if t['status'] == 'failed']
print("\nfailures:", len(fails), collections.Counter(cat(t['msg']) for t in fails).most_common())
print("timeouts by value:", sorted(collections.Counter(int(m) for t in fails for m in re.findall(r'Timeout:? (\d+)ms', t['msg'])).items()))
byw = collections.defaultdict(list)
for t in ex:
    if t['start']: byw[t['thread']].append(t)
if byw:
    g0 = min(t['start'] for w in byw.values() for t in w); g1 = max(t['stop'] for w in byw.values() for t in w)
    print(f"\nrun window {(g1-g0)/3600000:.2f}h, workers {len(byw)}")
    busy_total = 0
    for w, ts in sorted(byw.items(), key=lambda kv: -max(t['stop'] for t in kv[1])):
        busy = sum(t['dur'] for t in ts); last = max(t['stop'] for t in ts); busy_total += busy
        print(f"  {w:22s} tests={len(ts):4d} busy={busy/3600000:4.2f}h finished at +{(last-g0)/3600000:4.2f}h")
    print(f"packing {busy_total/(len(byw)*(g1-g0))*100:.0f}%")
