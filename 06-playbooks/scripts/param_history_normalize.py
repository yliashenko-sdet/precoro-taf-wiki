"""Brings every run source to one format: history/<source>-<build>.json = [[project, file, title, status], ...]
status: pass | flaky | fail. Sources: stats/raw/nightly (QA Jenkins nightly), archived Allure reports
(history.json of jenkins-run-*/allure-report: per test up to 20 earlier builds), stats/raw/jenkins-dev (branch builds, no file).
Usage: normalize_history.py <precoro dir> <out dir>"""
import json, glob, os, sys, urllib.parse, collections
root, out = sys.argv[1], sys.argv[2]
builds = collections.defaultdict(dict)  # (source, build) -> {(project, file, title): status}
for f in glob.glob(f'{root}/stats/raw/nightly/[0-9]*.json'):
    for key, st, *_ in json.load(open(f)):
        p, fl, *t = key.split(' / ')
        if st in ('pass', 'flaky', 'fail'):
            builds[('nightly', os.path.basename(f)[:-5])][(p, os.path.basename(fl), ' / '.join(t))] = st
for rep in glob.glob(f'{root}/jenkins-run-*/allure-report'):
    names = {}
    for f in glob.glob(f'{rep}/data/test-cases/*.json'):
        d = json.load(open(f))
        proj = next((x['value'] for x in d.get('parameters', []) if x['name'] == 'Project'), '?')
        names[d['historyId']] = (proj, d['fullName'].split(':')[0].split('/')[-1], d['name'])
    for hid, v in json.load(open(f'{rep}/history/history.json')).items():
        if hid not in names: continue
        for i in v['items']:
            u = urllib.parse.unquote(i.get('reportUrl', '')).split('/job/')
            if len(u) < 2: continue
            job, n = u[1].split('/')[:2]
            src = 'nightly' if job.startswith('Daily') else 'qa-run'
            st = {'passed': 'pass', 'failed': 'fail', 'broken': 'fail'}.get(i['status'])
            if st and not (src == 'nightly' and os.path.exists(f'{root}/stats/raw/nightly/{n}.json')):
                builds[(src, n)].setdefault(names[hid], st)
for f in glob.glob(f'{root}/stats/raw/jenkins-dev/tests/*/*.json'):
    tests = json.load(open(f)).get('tests') or []
    br = f.split('/')[-2]
    for t in tests:
        title = t['name'].split(' @qase(')[0]
        st = 'fail' if t['status'] in ('failed', 'broken') else ('flaky' if t.get('flaky') else ('pass' if t['status'] == 'passed' else None))
        if st: builds[('branch', f"{br}#{os.path.basename(f)[:-5]}")][(t.get('project', '?'), '', title)] = st
os.makedirs(out, exist_ok=True)
for f in glob.glob(f'{out}/*.json'): os.remove(f)
c = collections.Counter()
for (src, n), tests in builds.items():
    json.dump([[*k, s] for k, s in tests.items()], open(f'{out}/{src}~{n.replace("/", "_")}.json', 'w'))
    c[src] += 1
print(dict(c), 'builds')
