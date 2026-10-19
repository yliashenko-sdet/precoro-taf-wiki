#!/usr/bin/env python3
"""Team statistics for Automation weekly: collect raw data, compute a week, write its report.

    python3 team_stats.py collect [--only nightly,github,debt,jenkins-dev] [--weeks 3]
    python3 team_stats.py week    [--week 2026-W42]     # metrics.json of that week (and of the one before, if missing)
    python3 team_stats.py report  [--week 2026-W42]     # report.md of that week: table, movers, change journal
    python3 team_stats.py journal-sync                   # new merged TAF PRs into journal.json, hypothesis empty
    python3 team_stats.py catalog                        # the metric catalogue as a markdown table

A week is an ISO week, Monday 00:00 to Sunday 24:00 local time; without --week, the last finished one.
Store: ~/Work/Precoro/stats (STATS_DIR). Layout:

    raw/nightly/index.json        every nightly build seen: number, result, start, duration
    raw/nightly/<n>.json          tests of a full nightly build, reduced from its Allure suites.json
    raw/jenkins-dev/              store of jenkins_dev_builds.py (branch builds)
    raw/github/prs.json           TAF pull requests, last snapshot (gh)
    raw/debt/<sha>.json           npm run debt on that commit of origin/develop
    raw/slack/<week>.json         #jenkins-failed-builds posts of the week, written by the skill
    weeks/<week>/metrics.json     computed metrics of the week
    weeks/<week>/report.md        the week's report
    journal.json                  TAF changes and the metric each one is expected to move

Credentials: QA Jenkins JENKINS_URL, JENKINS_USER_NAME, JENKINS_PASS; dev Jenkins JENKINS_DEV_*;
both from the environment or the TAF .env. GitHub through `gh`. Nothing secret is printed or stored.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.expanduser(os.environ.get('STATS_DIR', '~/Work/Precoro/stats'))
TAF = os.path.expanduser(os.environ.get('TAF_REPO', '~/Work/src/precoro-e2e-playwright'))
TAF_ENV = os.environ.get('TAF_ENV', os.path.join(TAF, '.env'))
NIGHTLY_JOB = 'Daily%20autotests%20-%20all%20tests'
FULL_NIGHT_H = 2.5      # shorter builds are aborted or broken runs, not a night of the suite
MASS_PCT = 10.0         # a night where more tests finally failed is an environment failure
WINDOW = 7              # nights before / after a change in the journal
TRANSFORMATION_START = '2026-10-01'   # first TAF 2.0 PRs to develop; the journal starts here
BOTS = ('coderabbitai', 'copilot-pull-request-reviewer')

# key: (label, unit, better, source, held). better: 'down' | 'up' | None.
# held: why the number is collected but not brought to the meeting yet.
CATALOG = {
    'nightly.nights': ('Повних нічних прогонів', 'ночей', None, 'QA Jenkins', None),
    'nightly.mass_nights': ('Масових ночей (>10% впало, виключено)', 'ночей', 'down', 'QA Jenkins', None),
    'nightly.executed': ('Тестів виконано за ніч, медіана', 'тестів', None, 'QA Jenkins Allure', None),
    'nightly.flaky_pct': ('Flaky rate за ніч, медіана', '%', 'down', 'QA Jenkins Allure', None),
    'nightly.failed': ('Фінально впало за ніч, медіана', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.flaky_tests': ('Різних тестів, flaky хоч раз за тиждень', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.new_failures': ('Нові падіння: падали цього тижня, минулого ні', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.wall_h': ('Wall-clock нічного, медіана', 'год', 'down', 'QA Jenkins', None),
    'nightly.machine_h': ('Machine-time нічного (сума тестів), медіана', 'год', 'down', 'QA Jenkins Allure', None),
    'nightly.sec_per_test': ('Machine-time на тест, медіана', 'с', 'down', 'QA Jenkins Allure', None),
    'branch.builds': ('Гілкових білдів', 'білдів', None, 'dev Jenkins', None),
    'branch.red_pct': ('Червоних гілкових білдів', '%', 'down', 'dev Jenkins', None),
    'branch.to_green_h': ('Від червоного до зеленого на гілці, медіана', 'год', 'down', 'dev Jenkins', None),
    'branch.multi_branch_tests': ('Тестів, що падали на 2+ гілках', 'тестів', 'down', 'dev Jenkins Allure', None),
    'slack.bot_posts': ('Постів бота у #jenkins-failed-builds', 'постів', 'down', 'Slack', None),
    'slack.test_posts': ('З них тестові падіння', 'постів', 'down', 'Slack', None),
    'slack.thread_pct': ('Тестових падінь із розбором у треді', '%', 'up', 'Slack',
                         'чекає T0-24 / T0-17: без інформативного повідомлення відповідати нема на що'),
    'slack.product_causes': ('Тестових падінь, де причина продукт (баг знайдено)', 'тредів', None, 'Slack', None),
    'github.opened': ('PR у TAF відкрито', 'PR', None, 'GitHub', None),
    'github.merged': ('PR у TAF змерджено в develop', 'PR', 'up', 'GitHub', None),
    'github.open_end': ('Відкритих PR на кінець тижня', 'PR', 'down', 'GitHub', None),
    'github.open_age_d': ('Вік відкритого PR, медіана', 'днів', 'down', 'GitHub', None),
    'github.to_merge_h': ('Від відкриття до мержу, медіана', 'год', 'down', 'GitHub', None),
    'github.to_review_h': ('До першого рев\'ю людини, медіана', 'год', 'down', 'GitHub', None),
    'github.authors': ('Авторів PR', 'людей', None, 'GitHub', None),
}
DEBT_PREFIX = 'debt.'   # one metric per pattern of scripts/debt.js, labels taken from its table


# ---------- helpers

def week_bounds(week):
    year, w = map(int, week.split('-W'))
    start = dt.datetime.combine(dt.date.fromisocalendar(year, w, 1), dt.time())
    return start, start + dt.timedelta(days=7)


def last_week():
    y, w, _ = (dt.date.today() - dt.timedelta(days=7)).isocalendar()
    return f'{y}-W{w:02d}'


def prev_week(week):
    y, w, _ = (week_bounds(week)[0] - dt.timedelta(days=7)).isocalendar()
    return f'{y}-W{w:02d}'


def ms(d):
    return d.timestamp() * 1000


def median(xs):
    xs = [x for x in xs if x is not None]
    return round(statistics.median(xs), 2) if xs else None


def load(path, default=None):
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else default


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def env_creds(prefix_keys):
    env = {}
    if os.path.exists(TAF_ENV):
        for line in open(TAF_ENV, encoding='utf-8'):
            m = re.match(r'\s*(JENKINS_\w+)\s*=\s*(.*)\s*$', line)
            if m:
                env[m[1]] = m[2].strip().strip('"').strip("'")
    vals = [os.environ.get(k) or env.get(k) for k in prefix_keys]
    return vals if all(vals) else None


def fetch(base, auth, path):
    req = urllib.request.Request(base + path, headers={'Authorization': auth})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def leaves(node, path=()):
    for c in node.get('children', []):
        if 'children' in c:
            yield from leaves(c, path + (c['name'],))
        else:
            yield path, c


# ---------- collect

def collect_nightly():
    c = env_creds(['JENKINS_URL', 'JENKINS_USER_NAME', 'JENKINS_PASS'])
    if not c:
        return 'nightly: skipped, JENKINS_URL / JENKINS_USER_NAME / JENKINS_PASS not set'
    base, auth = c[0].rstrip('/'), 'Basic ' + base64.b64encode(f'{c[1]}:{c[2]}'.encode()).decode()
    d = os.path.join(STORE, 'raw', 'nightly')
    index = load(os.path.join(d, 'index.json'), {})
    tree = urllib.parse.quote('builds[number,result,timestamp,duration,building]')
    new = 0
    for b in fetch(base, auth, f'/job/{NIGHTLY_JOB}/api/json?tree={tree}')['builds']:
        if b.get('building'):
            continue
        n = str(b['number'])
        index[n] = {'number': b['number'], 'result': b['result'], 'start': b['timestamp'], 'duration': b['duration']}
        out = os.path.join(d, f'{n}.json')
        if b['duration'] < FULL_NIGHT_H * 3_600_000 or os.path.exists(out):
            continue
        suites = fetch(base, auth, f'/job/{NIGHTLY_JOB}/{n}/allure/data/suites.json')
        if suites is None:
            continue
        tests = []
        for path, t in leaves(suites):
            if t['status'] == 'skipped':
                continue
            state = ('fail' if t['status'] in ('failed', 'broken')
                     else 'flaky' if t.get('retriesCount', 0) > 0 or t.get('flaky') else 'pass')
            key = ' / '.join([path[0] if path else '?', (path[1] if len(path) > 1 else '?').replace('\\', '/'),
                              t['name']] + list(t.get('parameters') or [])[1:])
            tests.append([key, state, (t.get('time') or {}).get('duration') or 0])
        save(out, tests)
        new += 1
    save(os.path.join(d, 'index.json'), index)
    return f'nightly: builds in index {len(index)}, full builds fetched +{new}'


def collect_jenkins_dev():
    if not env_creds(['JENKINS_DEV_URL', 'JENKINS_DEV_USER', 'JENKINS_DEV_PASS']):
        return ('jenkins-dev: skipped, JENKINS_DEV_URL / JENKINS_DEV_USER / JENKINS_DEV_PASS not set; '
                'branch history of merged PRs is lost every day this does not run')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'jenkins_dev_builds.py'), 'collect',
                        '--store', os.path.join(STORE, 'raw', 'jenkins-dev')], capture_output=True, text=True)
    return 'jenkins-dev: ' + (r.stdout.strip() or r.stderr.strip()[-300:])


def collect_github():
    fields = 'number,title,author,createdAt,mergedAt,closedAt,state,baseRefName,isDraft,reviews,additions,deletions'
    r = subprocess.run(['gh', 'pr', 'list', '--state', 'all', '--limit', '1000', '--json', fields],
                       cwd=TAF, capture_output=True, text=True)
    if r.returncode:
        return 'github: failed, ' + r.stderr.strip()[-300:]
    prs = json.loads(r.stdout)
    for p in prs:   # keep logins only: who reviewed and when
        p['author'] = (p.get('author') or {}).get('login')
        p['reviews'] = [{'by': (x.get('author') or {}).get('login'), 'at': x.get('submittedAt'), 'state': x.get('state')}
                        for x in p.get('reviews') or []]
    save(os.path.join(STORE, 'raw', 'github', 'prs.json'), {'taken': dt.datetime.now().isoformat(), 'prs': prs})
    return f'github: {len(prs)} PRs'


def develop_at(moment):
    sha = subprocess.run(['git', 'rev-list', '-1', f'--before={moment.isoformat()}', 'origin/develop'],
                         cwd=TAF, capture_output=True, text=True).stdout.strip()
    return sha or None


def debt_at(sha):
    out = os.path.join(STORE, 'raw', 'debt', f'{sha}.json')
    if os.path.exists(out):
        return load(out)
    with tempfile.TemporaryDirectory() as tmp:
        arch = subprocess.run(['git', 'archive', sha], cwd=TAF, capture_output=True)
        subprocess.run(['tar', '-x', '-C', tmp], input=arch.stdout, check=True)
        subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=tmp, check=True)
        r = subprocess.run(['node', 'scripts/debt.js'], cwd=tmp, capture_output=True, text=True,
                           env={**os.environ, 'NODE_PATH': os.path.join(TAF, 'node_modules')})
    if r.returncode:
        return None
    counts = {}
    for line in r.stdout.splitlines()[1:]:
        m = re.match(r'(.+?)\s{2,}(\d+)(\s+yes)?\s*$', line)
        if m:
            counts[m[1].strip()] = {'n': int(m[2]), 'gated': bool(m[3])}
    save(out, counts)
    return counts


def collect_debt(weeks):
    subprocess.run(['git', 'fetch', '-q', 'origin', 'develop'], cwd=TAF)
    done = []
    w = last_week()
    for _ in range(weeks):
        sha = develop_at(week_bounds(w)[1])
        if sha and debt_at(sha) is not None:
            done.append(f'{w} {sha[:8]}')
        w = prev_week(w)
    return 'debt: ' + ', '.join(done)


# ---------- week

def nights_in(start, end):
    d = os.path.join(STORE, 'raw', 'nightly')
    index = load(os.path.join(d, 'index.json'), {})
    out = []
    for n, b in sorted(index.items(), key=lambda kv: int(kv[0])):
        if not (ms(start) <= b['start'] < ms(end)):
            continue
        tests = load(os.path.join(d, f'{n}.json'))
        if tests is None:
            continue
        states = {}
        for key, state, dur in tests:
            states[key] = state
        c = {s: sum(1 for v in states.values() if v == s) for s in ('pass', 'flaky', 'fail')}
        executed = len(states)
        out.append({'number': int(n), 'start': b['start'], 'wall_h': round(b['duration'] / 3_600_000, 2),
                    'machine_h': round(sum(t[2] for t in tests) / 3_600_000, 2), 'executed': executed,
                    'sec_per_test': round(sum(t[2] for t in tests) / 1000 / executed, 1),
                    'flaky': c['flaky'], 'failed': c['fail'], 'flaky_pct': round(c['flaky'] / executed * 100, 2),
                    'mass': c['fail'] / executed * 100 > MASS_PCT, 'states': states})
    return out


def nightly_metrics(start, end):
    nights = nights_in(start, end)
    if not nights:
        return {}, {}
    good = [n for n in nights if not n['mass']]
    prev = [n for n in nights_in(start - dt.timedelta(days=7), start) if not n['mass']]
    flaky_count, fail_count = {}, {}
    for n in good:
        for k, s in n['states'].items():
            if s == 'flaky':
                flaky_count[k] = flaky_count.get(k, 0) + 1
            elif s == 'fail':
                fail_count[k] = fail_count.get(k, 0) + 1
    prev_failed = {k for n in prev for k, s in n['states'].items() if s == 'fail'}
    prev_seen = {k for n in prev for k in n['states']}
    new_fail = sorted((k for k, c in fail_count.items() if (c >= 2 or len(good) < 2) and k in prev_seen
                       and k not in prev_failed), key=lambda k: -fail_count[k])
    m = {
        'nightly.nights': len(nights), 'nightly.mass_nights': len(nights) - len(good),
        'nightly.executed': median(n['executed'] for n in good),
        'nightly.flaky_pct': median(n['flaky_pct'] for n in good),
        'nightly.failed': median(n['failed'] for n in good),
        'nightly.flaky_tests': len(flaky_count),
        'nightly.new_failures': len(new_fail) if prev else None,
        'nightly.wall_h': median(n['wall_h'] for n in good),
        'nightly.machine_h': median(n['machine_h'] for n in good),
        'nightly.sec_per_test': median(n['sec_per_test'] for n in good),
    }
    lists = {
        'nights': [{k: v for k, v in n.items() if k != 'states'} for n in nights],
        'top_flaky': [[k, c, len(good)] for k, c in sorted(flaky_count.items(), key=lambda kv: -kv[1])[:15]],
        'new_failures': [[k, fail_count[k], len(good)] for k in new_fail[:15]],
    }
    return m, lists


def branch_metrics(start, end):
    store = os.path.join(STORE, 'raw', 'jenkins-dev')
    index = load(os.path.join(store, 'index.json'))
    if not index:
        return {}, {}
    red = {'FAILURE', 'UNSTABLE'}
    week = [b for b in index.values() if ms(start) <= b['start'] < ms(end) and b['result'] in red | {'SUCCESS'}]
    by_branch = {}
    for b in index.values():
        by_branch.setdefault(b['branch'], []).append(b)
    to_green = []
    for b in week:
        if b['result'] in red:
            nxt = next((x for x in sorted(by_branch[b['branch']], key=lambda x: x['number'])
                        if x['number'] > b['number'] and x['result'] == 'SUCCESS'), None)
            if nxt:
                to_green.append((nxt['start'] + nxt['duration'] - b['start'] - b['duration']) / 3_600_000)
    failed = {}
    for b in week:
        path = os.path.join(store, 'tests', re.sub(r'[^\w.-]+', '_', b['branch']), f"{b['number']}.json")
        for t in (load(path) or {}).get('tests', []):
            if t['status'] in ('failed', 'broken'):
                failed.setdefault(f"[{t['project']}] {t['name']}", set()).add(b['branch'])
    multi = sorted(((k, len(v)) for k, v in failed.items() if len(v) >= 2), key=lambda kv: -kv[1])
    n_red = sum(1 for b in week if b['result'] in red)
    return ({'branch.builds': len(week), 'branch.red_pct': round(n_red / len(week) * 100, 1) if week else None,
             'branch.to_green_h': median(to_green), 'branch.multi_branch_tests': len(multi)},
            {'multi_branch_tests': multi[:15]})


def slack_metrics(week):
    d = load(os.path.join(STORE, 'raw', 'slack', f'{week}.json'))
    if not d:
        return {}, {}
    posts = d['posts']
    tests = [p for p in posts if p.get('category') == 'tests']
    return ({'slack.bot_posts': len(posts), 'slack.test_posts': len(tests),
             'slack.thread_pct': round(sum(1 for p in tests if p.get('human_replies')) / len(tests) * 100, 1) if tests else None,
             'slack.product_causes': sum(1 for p in tests if p.get('cause') == 'product')},
            {'causes': {c: sum(1 for p in tests if p.get('cause') == c) for c in sorted({p.get('cause') or '-' for p in tests})}})


def github_metrics(start, end):
    d = load(os.path.join(STORE, 'raw', 'github', 'prs.json'))
    if not d:
        return {}, {}
    t = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone().replace(tzinfo=None) if s else None
    prs = [p for p in d['prs'] if p['baseRefName'] == 'develop']
    opened = [p for p in prs if start <= t(p['createdAt']) < end]
    merged = [p for p in prs if p['mergedAt'] and start <= t(p['mergedAt']) < end]
    open_end = [p for p in prs if t(p['createdAt']) < end and not (p['closedAt'] and t(p['closedAt']) < end)]
    first_review = []
    for p in opened + [p for p in merged if p not in opened]:
        rs = [t(r['at']) for r in p['reviews'] if r['by'] != p['author'] and r['by'] not in BOTS and r['at']]
        if rs:
            first_review.append((min(rs) - t(p['createdAt'])).total_seconds() / 3600)
    return ({'github.opened': len(opened), 'github.merged': len(merged), 'github.open_end': len(open_end),
             'github.open_age_d': median((end - t(p['createdAt'])).total_seconds() / 86400 for p in open_end),
             'github.to_merge_h': median((t(p['mergedAt']) - t(p['createdAt'])).total_seconds() / 3600 for p in merged),
             'github.to_review_h': median(first_review),
             'github.authors': len({p['author'] for p in opened + merged})},
            {'merged': [[p['number'], p['title'], p['mergedAt'][:10]] for p in merged]})


def debt_metrics(end):
    sha = develop_at(end)
    counts = debt_at(sha) if sha else None
    if not counts:
        return {}, {}
    return {DEBT_PREFIX + k: v['n'] for k, v in counts.items()}, {'debt_commit': sha[:8]}


def compute_week(week):
    start, end = week_bounds(week)
    metrics, lists = {}, {}
    for m, l in (nightly_metrics(start, end), branch_metrics(start, end), slack_metrics(week),
                 github_metrics(start, end), debt_metrics(end)):
        metrics.update(m)
        lists.update(l)
    data = {'week': week, 'from': start.date().isoformat(), 'to': (end - dt.timedelta(days=1)).date().isoformat(),
            'computed': dt.datetime.now().isoformat(timespec='minutes'), 'metrics': metrics, 'lists': lists}
    save(os.path.join(STORE, 'weeks', week, 'metrics.json'), data)
    return data


# ---------- journal

def journal_sync():
    path = os.path.join(STORE, 'journal.json')
    journal = load(path, [])
    known = {e['pr'] for e in journal}
    d = load(os.path.join(STORE, 'raw', 'github', 'prs.json'))
    today = dt.date.today().isoformat()
    added = 0
    for p in sorted(d['prs'], key=lambda p: p['mergedAt'] or ''):
        if (p['baseRefName'] != 'develop' or not p['mergedAt'] or p['number'] in known
                or p['mergedAt'] < TRANSFORMATION_START):
            continue
        task = re.search(r'\bT\d-\d{2}\b', p['title'])
        journal.append({'pr': p['number'], 'title': p['title'], 'merged': p['mergedAt'], 'task': task[0] if task else None,
                        'author': p['author'], 'transformation': None, 'hypothesis': '', 'metrics': [],
                        'recorded': today, 'retro': None})
        added += 1
    save(path, journal)
    todo = [e['pr'] for e in journal if e['transformation'] is None]
    print(f'journal: {len(journal)} entries, +{added}; to classify (transformation true/false, hypothesis, metrics): {todo}')


def evaluate(entry):
    """Nightly metrics: medians over up to WINDOW full non-mass nights before and after the merge."""
    merged = dt.datetime.fromisoformat(entry['merged'].replace('Z', '+00:00')).astimezone().replace(tzinfo=None)
    before = [n for n in nights_in(merged - dt.timedelta(days=21), merged) if not n['mass']][-WINDOW:]
    after = [n for n in nights_in(merged, merged + dt.timedelta(days=21)) if not n['mass']][:WINDOW]
    res = {}
    for key in entry['metrics']:
        f = key.split('.', 1)[1]
        if key.startswith('nightly.') and before and after and f in before[0]:
            res[key] = (median(n[f] for n in before), median(n[f] for n in after), len(before), len(after))
    return res


# ---------- report

def fmt(v):
    return '—' if v is None else (f'{v:,}'.replace(',', ' ') if isinstance(v, int) else f'{v:g}')


def delta(cur, prev, better):
    if cur is None or prev is None:
        return '', None
    d = round(cur - prev, 2)
    rel = (d / prev * 100) if prev else (100.0 if d else 0.0)
    mark = ''
    if better and d:
        mark = ' ✓' if (d < 0) == (better == 'down') else ' ✗'
    return f'{"+" if d > 0 else ""}{fmt(d)}{mark}', rel


def report(week):
    cur = load(os.path.join(STORE, 'weeks', week, 'metrics.json')) or compute_week(week)
    pw = prev_week(week)
    prev = load(os.path.join(STORE, 'weeks', pw, 'metrics.json')) or compute_week(pw)
    cm, pm = cur['metrics'], prev['metrics']
    lines = [f'# Automation weekly {week} ({cur["from"]} … {cur["to"]})', '',
             f'Пораховано {cur["computed"]} скриптом `06-playbooks/scripts/team_stats.py`. Попередній тиждень {pw}. '
             '✓ / ✗ — зміна в кращий / гірший бік.', '']
    movers = []
    groups = [('Нічний прогін (QA Jenkins)', 'nightly.'), ('Гілкові прогони (dev Jenkins)', 'branch.'),
              ('Slack #jenkins-failed-builds', 'slack.'), ('PR у TAF (GitHub)', 'github.')]
    for title, prefix in groups:
        keys = [k for k in CATALOG if k.startswith(prefix)]
        if not any(k in cm or k in pm for k in keys):
            lines += [f'## {title}', '', 'Даних за тиждень нема.', '']
            continue
        lines += [f'## {title}', '', '| Показник | Цей тиждень | Минулий | Δ |', '| --- | ---: | ---: | ---: |']
        for k in keys:
            label, unit, better, _, held = CATALOG[k]
            d, rel = delta(cm.get(k), pm.get(k), better)
            lines.append(f'| {label}, {unit}{" *(чекає)*" if held else ""} | {fmt(cm.get(k))} | {fmt(pm.get(k))} | {d} |')
            if rel is not None and abs(rel) >= 10 and better and not held:
                movers.append((abs(rel), label, cm.get(k), pm.get(k), d))
        lines.append('')
    debt = sorted(k for k in cm if k.startswith(DEBT_PREFIX))
    if debt:
        lines += [f'## Показники боргу (`npm run debt` на `develop` {cur["lists"].get("debt_commit")} '
                  f'проти {prev["lists"].get("debt_commit")})', '',
                  '| Патерн | Цей тиждень | Минулий | Δ |', '| --- | ---: | ---: | ---: |']
        for k in debt:
            d, rel = delta(cm.get(k), pm.get(k), 'down')
            lines.append(f'| {k[len(DEBT_PREFIX):]} | {fmt(cm.get(k))} | {fmt(pm.get(k))} | {d} |')
            if rel is not None and abs(rel) >= 10 and (pm.get(k) or 0) >= 20:
                movers.append((abs(rel), f'debt: {k[len(DEBT_PREFIX):]}', cm.get(k), pm.get(k), d))
        lines.append('')
    L = cur['lists']
    if L.get('nights'):
        lines += ['### Ночі тижня', '', '| Збірка | Старт | Виконано | Flaky | Впало | Wall, год | Machine, год | |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for n in L['nights']:
            lines.append(f"| {n['number']} | {dt.datetime.fromtimestamp(n['start'] / 1000):%a %d.%m} | {n['executed']} | "
                         f"{n['flaky']} ({n['flaky_pct']}%) | {n['failed']} | {n['wall_h']} | {n['machine_h']} | "
                         f"{'масова, виключено' if n['mass'] else ''} |")
        lines.append('')
    for key, title in (('top_flaky', 'Найчастіше flaky за тиждень (ночей flaky / ночей)'),
                       ('new_failures', 'Нові падіння (ночей впав / ночей; минулого тижня не падав)'),
                       ('multi_branch_tests', 'Падали на кількох гілках (гілок)')):
        if L.get(key):
            lines += [f'### {title}', ''] + [f'- {r[0]} — ' + '/'.join(map(str, r[1:])) for r in L[key]] + ['']
    lines += ['## Що зрушило найбільше (кандидати на обговорення)', '']
    movers.sort(reverse=True)
    lines += [f'- {label}: {fmt(p)} → {fmt(c)} ({d})' for _, label, c, p, d in movers[:8]] or ['- Нічого не зрушило на 10% і більше.']
    held = [f'- {CATALOG[k][0]}: {CATALOG[k][4]}' for k in CATALOG if CATALOG[k][4] and k in cm]
    if held:
        lines += ['', 'Збираємо, але поки не обговорюємо:'] + held
    journal = load(os.path.join(STORE, 'journal.json'), [])
    tr = [e for e in journal if e.get('transformation')]
    if tr:
        lines += ['', '## Журнал змін TAF: очікуваний і виміряний ефект', '',
                  f'Нічні показники: медіана до {WINDOW} повних не-масових ночей до мержу і після.', '',
                  '| PR | Задача | Змерджено | Гіпотеза | Показник: до → після (ночей) |', '| --- | --- | --- | --- | --- |']
        for e in sorted(tr, key=lambda e: e['merged'], reverse=True):
            ev = evaluate(e)
            res = '; '.join(f'{CATALOG.get(k, (k,))[0]}: {fmt(b)} → {fmt(a)} ({nb}/{na})' for k, (b, a, nb, na) in ev.items())
            if not res and e['metrics']:
                res = 'ще збирається' if any(k.startswith('nightly.') for k in e['metrics']) else 'не нічний показник'
            lines.append(f"| #{e['pr']} | {e.get('task') or ''} | {e['merged'][:10]} | "
                         f"{e['hypothesis']}{' *(ретроспективно)*' if e.get('retro') else ''} | {res} |")
    out = os.path.join(STORE, 'weeks', week, 'report.md')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(out)


def catalog():
    print('| Ключ | Показник | Одиниця | Краще | Джерело | Чекає |\n| --- | --- | --- | --- | --- | --- |')
    for k, (label, unit, better, source, held) in CATALOG.items():
        print(f'| `{k}` | {label} | {unit} | {"↓" if better == "down" else "↑" if better == "up" else ""} | {source} | {held or ""} |')
    print(f'| `{DEBT_PREFIX}<патерн>` | кожен патерн `npm run debt` | входжень | ↓ | `scripts/debt.js` на `develop` | |')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['collect', 'week', 'report', 'journal-sync', 'catalog'])
    ap.add_argument('--week')
    ap.add_argument('--only', default='nightly,github,debt,jenkins-dev')
    ap.add_argument('--weeks', type=int, default=3, help='collect debt for this many last weeks')
    a = ap.parse_args()
    week = a.week or last_week()
    if a.cmd == 'collect':
        only = a.only.split(',')
        for name, fn in (('nightly', collect_nightly), ('jenkins-dev', collect_jenkins_dev),
                         ('github', collect_github), ('debt', lambda: collect_debt(a.weeks))):
            if name in only:
                print(fn(), flush=True)
    elif a.cmd == 'week':
        d = compute_week(week)
        if not os.path.exists(os.path.join(STORE, 'weeks', prev_week(week), 'metrics.json')):
            compute_week(prev_week(week))
        print(json.dumps(d['metrics'], ensure_ascii=False, indent=1))
    elif a.cmd == 'report':
        report(week)
    elif a.cmd == 'journal-sync':
        journal_sync()
    else:
        catalog()


if __name__ == '__main__':
    main()
