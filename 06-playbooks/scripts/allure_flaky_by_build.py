#!/usr/bin/env python3
"""Flaky rate кожного тесту за серією нічних збірок Jenkins.

Вхід: тека з файлами `<номер_збірки>.json`, кожен це `data/suites.json` Allure-звіту збірки
(`<JENKINS>/job/<job>/<build>/allure/data/suites.json`). Тест ідентифікується за
(проект, файл, назва, параметри).

На кожну ніч у тесту один з трьох станів:
  pass   — пройшов з першої спроби;
  flaky  — пройшов після ретраю (те саме, що рахує flaky-метрика metrics-reporter);
  fail   — фінально впав.
flaky rate = flaky / ночей; нестабільність = (flaky + fail) / ночей.

Масові ночі (фінально впало більше `--mass` відсотків тестів, за замовчуванням 10) виключаються:
це падіння середовища, а не тесту. Їх видно в шапці виводу.

Використання: allure_flaky_by_build.py <тека> [--top 50] [--mass 10] [--min-nights 8] [--csv out.csv]
"""
import json, os, sys, csv, glob, collections

def opt(name, default):
    return type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default

src = sys.argv[1]
top, mass_pct, min_nights, csv_out = opt('--top', 50), opt('--mass', 10.0), opt('--min-nights', 8), opt('--csv', '')

def leaves(node, path):
    for c in node.get('children', []):
        if 'children' in c:
            yield from leaves(c, path + [c['name']])
        else:
            yield path, c

builds = {}  # номер -> {ключ: стан}
for f in sorted(glob.glob(os.path.join(src, '*.json')), key=lambda p: int(os.path.basename(p)[:-5])):
    states = {}
    for path, t in leaves(json.load(open(f)), []):
        if t['status'] == 'skipped':
            continue
        key = (path[0] if path else '?', (path[1] if len(path) > 1 else '?').replace('\\', '/'),
               t['name'], tuple(t.get('parameters', [])))
        if t['status'] in ('failed', 'broken'):
            states[key] = 'fail'
        elif t.get('retriesCount', 0) > 0 or t.get('flaky'):
            states[key] = 'flaky'
        else:
            states[key] = 'pass'
    builds[int(os.path.basename(f)[:-5])] = states

mass = set()
print("build: executed / flaky / failed")
for b, st in builds.items():
    c = collections.Counter(st.values()); n = len(st)
    is_mass = c['fail'] / n * 100 > mass_pct
    if is_mass:
        mass.add(b)
    print(f"  {b}: {n} / {c['flaky']} ({c['flaky']/n*100:.2f}%) / {c['fail']} ({c['fail']/n*100:.1f}%){'  MASS, excluded' if is_mass else ''}")
used = [b for b in builds if b not in mass]
latest = max(builds)

rows = []
for key in builds[latest]:                            # лише тести, що є в найновішій збірці
    seq = [builds[b][key] for b in used if key in builds[b]]
    if len(seq) < min_nights:
        continue
    c = collections.Counter(seq)
    streak = cur = 0
    for s in seq:
        cur = cur + 1 if s == 'fail' else 0; streak = max(streak, cur)
    rows.append({'project': key[0], 'file': key[1], 'name': key[2], 'params': ' '.join(key[3]),
                 'nights': len(seq), 'flaky': c['flaky'], 'fail': c['fail'],
                 'flaky_rate': c['flaky'] / len(seq), 'unstable_rate': (c['flaky'] + c['fail']) / len(seq),
                 'max_fail_streak': streak,
                 'pattern': ''.join({'pass': '.', 'flaky': 'f', 'fail': 'X'}[s] for s in seq)})

n_any = sum(r['flaky'] > 0 for r in rows)
tot_flaky = sum(r['flaky'] for r in rows)
print(f"\nnights used {len(used)} (builds {used[0]}..{used[-1]}), tests with >= {min_nights} nights: {len(rows)}")
print(f"tests flaky at least once: {n_any}; flaky events: {tot_flaky}")
rows.sort(key=lambda r: (-r['flaky_rate'], -r['unstable_rate']))
top_share = sum(r['flaky'] for r in rows[:top]) / tot_flaky * 100 if tot_flaky else 0
print(f"top {top} tests hold {top_share:.0f}% of flaky events")
print(f"\n{'flaky':>6} {'unst':>5} {'f/X/n':>8} {'pattern old→new':24} project / file / test")
for r in rows[:top]:
    print(f"{r['flaky_rate']*100:5.1f}% {r['unstable_rate']*100:4.0f}% {r['flaky']:2d}/{r['fail']:<2d}/{r['nights']:<2d} "
          f"{r['pattern']:24} {r['project']} / {r['file']} / {r['name'][:85]}")
if csv_out:
    with open(csv_out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
