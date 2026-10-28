#!/usr/bin/env python3
"""Team statistics for Automation weekly: collect raw data, compute a week, write its report.

    python3 team_stats.py collect [--only nightly,github,debt,jenkins-dev] [--weeks 3]
    python3 team_stats.py week    [--week 2026-W42]     # metrics.json of that week (and of the one before, if missing)
    python3 team_stats.py report  [--week 2026-W42]     # report.md of that week: table, movers, change journal
    python3 team_stats.py journal-sync                   # new merged TAF PRs into journal.json, hypothesis empty
    python3 team_stats.py catalog                        # the metric catalogue as a markdown table
    python3 team_stats.py export                         # data.json of the TAF stats page (~/Work/Precoro/artifacts/taf-stats)

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
JENKINS_DEV_USER_NAME or JENKINS_DEV_USER; all from the environment or the TAF .env. GitHub through `gh`. Nothing secret is printed or stored.
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
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.expanduser(os.environ.get('STATS_DIR', '~/Work/Precoro/stats'))
TAF = os.path.expanduser(os.environ.get('TAF_REPO', '~/Work/src/precoro-e2e-playwright'))
TAF_ENV = os.environ.get('TAF_ENV', os.path.join(TAF, '.env'))
NIGHTLY_JOB = 'Daily%20autotests%20-%20all%20tests'
FULL_NIGHT_H = 2.5      # shorter builds are aborted or broken runs, not a night of the suite
# Nightly counts on develop and on the team's daily fix branches (fix/<date>, fix/<name>/<date>);
# runs on other branches are debug or check runs and are left out (Yevhen, 2026-10-19).
NIGHTLY_BRANCHES = re.compile(os.environ.get('NIGHTLY_BRANCHES', r'^(develop|fix/([^/]+/)?\d{2}-\d{2}-\d{2,4})$'))


def line_of(branch):
    return 'develop' if branch == 'develop' else 'fix' if (branch or '').startswith('fix/') else 'other'
# A branch build runs either the smoke set or the full run. dev Jenkins has no stage API (wfapi), so the kind is
# read from the executed count: smoke runs 200-300 tests, a full run 1100-1300 (20.10.2026), nothing in between.
FULLRUN_MIN = 600
MASS_PCT = 10.0         # a night where more tests finally failed is an environment failure
WINDOW = 7              # nights before / after a change in the journal
TRANSFORMATION_START = '2026-10-01'   # first TAF 2.0 PRs to develop; the journal starts here
BOTS = ('coderabbitai', 'copilot-pull-request-reviewer')

# key: (label, unit, better, source, held). better: 'down' | 'up' | None.
# held: why the number is collected but not brought to the meeting yet.
CATALOG = {
    'nightly.nights': ('Повних нічних прогонів на `develop` і `fix/<дата>`', 'ночей', None, 'QA Jenkins', None),
    'nightly.on_develop': ('з них на `develop`', 'ночей', None, 'QA Jenkins', None),
    'nightly.on_fix': ('з них на `fix/<дата>`', 'ночей', None, 'QA Jenkins', None),
    'nightly.other_branch': ('Нічних на інших гілках (не враховано)', 'ночей', None, 'QA Jenkins', None),
    'nightly.mass_nights': ('Масових ночей (>10% впало, виключено)', 'ночей', 'down', 'QA Jenkins', None),
    'nightly.executed': ('Тестів виконано за ніч, медіана', 'тестів', None, 'QA Jenkins Allure', None),
    'nightly.flaky_pct': ('Flaky rate за ніч, медіана', '%', 'down', 'QA Jenkins Allure', None),
    'nightly.failed': ('Фінально впало за ніч, медіана', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.flaky_tests': ('Різних тестів, flaky хоч раз за тиждень', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.new_failures': ('Нові падіння: падали цього тижня, минулого ні', 'тестів', 'down', 'QA Jenkins Allure', None),
    'nightly.wall_min': ('Wall-clock нічного, медіана', 'хв', 'down', 'QA Jenkins', None),
    'nightly.machine_h': ('Machine-time нічного (сума тестів), медіана', 'год', 'down', 'QA Jenkins Allure', None),
    'nightly.sec_per_test': ('Machine-time на тест, медіана', 'с', 'down', 'QA Jenkins Allure', None),
    # Branch builds run on dev Jenkins: other machines, other worker count, another test selection than the
    # nightly on QA Jenkins. Their numbers are kept apart and never compared with the nightly (Yevhen and
    # Tetiana, 2026-10-20); the same quantities carry the same names, so each is read against its own history.
    'branch.builds': ('Гілкових білдів', 'білдів', None, 'dev Jenkins', None),
    'branch.red_pct': ('Червоних гілкових білдів', '%', 'down', 'dev Jenkins', None),
    'branch.to_green_h': ('Від червоного до зеленого на гілці, медіана', 'год', 'down', 'dev Jenkins', None),
    'branch.multi_branch_tests': ('Тестів, що падали на 2+ гілках (smoke і fullrun)', 'тестів', 'down', 'dev Jenkins Allure', None),
    'branch.smoke_runs': ('Гілкових білдів зі smoke', 'білдів', None, 'dev Jenkins Allure', None),
    'branch.fullruns': ('Гілкових fullrun', 'білдів', None, 'dev Jenkins Allure', None),
    # per-run numbers below: full runs only, the same scope as the nightly
    'branch.executed': ('Тестів виконано за fullrun, медіана', 'тестів', None, 'dev Jenkins Allure', None),
    'branch.flaky_pct': ('Flaky rate за fullrun, медіана', '%', 'down', 'dev Jenkins Allure', None),
    'branch.failed': ('Фінально впало за fullrun, медіана', 'тестів', 'down', 'dev Jenkins Allure', None),
    'branch.flaky_tests': ('Різних тестів, flaky хоч раз за тиждень (fullrun)', 'тестів', 'down', 'dev Jenkins Allure', None),
    'branch.wall_min': ('Тривалість fullrun (увесь пайплайн), медіана', 'хв', 'down', 'dev Jenkins', None),
    'branch.sec_per_test': ('Machine-time на тест (fullrun), медіана', 'с', 'down', 'dev Jenkins Allure', None),
    'slack.bot_posts': ('Постів бота у #jenkins-failed-builds', 'постів', 'down', 'Slack · dev Jenkins', None),
    'slack.test_posts': ('З них тестові падіння', 'постів', 'down', 'Slack · dev Jenkins', None),
    'slack.thread_pct': ('Тестових падінь із розбором у треді', '%', 'up', 'Slack · dev Jenkins',
                         'чекає T0-17: без інформативного повідомлення відповідати нема на що'),
    'slack.product_causes': ('Тестових падінь, де причина продукт (баг знайдено)', 'тредів', None, 'Slack · dev Jenkins', None),
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


# ---------- failure classes

# Symptom of the final failure, from the Allure statusMessage. Not a root cause: a locator timeout can be a
# slow stand, a changed UI or a data problem. Order matters, the first match wins.
FAILURE_CLASSES = (
    ('test_timeout', re.compile(r'(Test|"\w+" hook) timeout of \d+ms exceeded', re.I)),
    ('api_error', re.compile(r'Failed to .*\d{3}|failed: \d{3}|"code":\s*\d{3}|status (code )?[45]\d\d|ECONNREFUSED|ECONNRESET', re.I)),
    ('locator_timeout', re.compile(r'Timeout \d+ms exceeded.*(waiting for locator|locator\.)|locator\.\w+: Timeout', re.I | re.S)),
    ('wait_timeout', re.compile(r'Timeout \d+ms exceeded|waitForEvent|waitForResponse|waitForURL|waiting on the predicate', re.I)),
    ('assertion', re.compile(r'expect\((locator|received|page)|toBe|toHave|toEqual|toContain|toMatch', re.I)),
    ('script_error', re.compile(r'TypeError|ReferenceError|Cannot read propert|is not a function|undefined', re.I)),
)


def failure_class(msg):
    msg = msg or ''
    return next((name for name, rx in FAILURE_CLASSES if rx.search(msg)), 'other' if msg else 'no_message')


def fetch_failures(base, auth, build, suites):
    """Final failures of a nightly build: [key, class, message head]. One request per failed test."""
    out = []
    for path, t in leaves(suites):
        if t['status'] not in ('failed', 'broken'):
            continue
        d = fetch(base, auth, f'/job/{NIGHTLY_JOB}/{build}/allure/data/test-cases/{t["uid"]}.json') or {}
        msg = re.sub(r'\s+', ' ', ((d.get('testStage') or {}).get('statusMessage') or ''))[:300]
        key = ' / '.join([path[0] if path else '?', (path[1] if len(path) > 1 else '?').replace('\\', '/'),
                          t['name']] + list(t.get('parameters') or [])[1:])
        out.append([key, failure_class(msg), msg])
    return out


# ---------- collect

def collect_nightly():
    c = env_creds(['JENKINS_URL', 'JENKINS_USER_NAME', 'JENKINS_PASS'])
    if not c:
        return 'nightly: skipped, JENKINS_URL / JENKINS_USER_NAME / JENKINS_PASS not set'
    base, auth = c[0].rstrip('/'), 'Basic ' + base64.b64encode(f'{c[1]}:{c[2]}'.encode()).decode()
    d = os.path.join(STORE, 'raw', 'nightly')
    index = load(os.path.join(d, 'index.json'), {})
    tree = urllib.parse.quote('builds[number,result,timestamp,duration,building,'
                              'actions[lastBuiltRevision[SHA1,branch[name]]]]')
    new = failures_new = 0
    for b in fetch(base, auth, f'/job/{NIGHTLY_JOB}/api/json?tree={tree}')['builds']:
        if b.get('building'):
            continue
        n = str(b['number'])
        rev = next((a['lastBuiltRevision'] for a in b.get('actions') or [] if a and a.get('lastBuiltRevision')), {})
        branch = next((x['name'] for x in rev.get('branch') or []), None)
        index[n] = {'number': b['number'], 'result': b['result'], 'start': b['timestamp'], 'duration': b['duration'],
                    'branch': re.sub(r'^(refs/remotes/)?origin/', '', branch) if branch else None,
                    'sha': rev.get('SHA1')}
        out = os.path.join(d, f'{n}.json')
        fout = os.path.join(d, f'{n}.failures.json')
        if b['duration'] < FULL_NIGHT_H * 3_600_000 or (os.path.exists(out) and os.path.exists(fout)):
            continue
        suites = fetch(base, auth, f'/job/{NIGHTLY_JOB}/{n}/allure/data/suites.json')
        if suites is None:
            continue
        if not os.path.exists(fout):
            save(fout, fetch_failures(base, auth, n, suites))
            failures_new += 1
        if os.path.exists(out):
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
    return f'nightly: builds in index {len(index)}, full builds fetched +{new}, failure messages +{failures_new}'


def collect_jenkins_dev():
    if not (env_creds(['JENKINS_DEV_URL', 'JENKINS_DEV_USER_NAME', 'JENKINS_DEV_PASS'])
            or env_creds(['JENKINS_DEV_URL', 'JENKINS_DEV_USER', 'JENKINS_DEV_PASS'])):
        return ('jenkins-dev: skipped, JENKINS_DEV_URL / JENKINS_DEV_USER_NAME / JENKINS_DEV_PASS not set; '
                'branch history of merged PRs is lost every day this does not run')
    r = subprocess.run([sys.executable, os.path.join(HERE, 'jenkins_dev_builds.py'), 'collect',
                        '--store', os.path.join(STORE, 'raw', 'jenkins-dev')], capture_output=True, text=True)
    return 'jenkins-dev: ' + (r.stdout.strip() or r.stderr.strip()[-300:])


def collect_github():
    fields = 'number,title,author,createdAt,mergedAt,closedAt,state,baseRefName,isDraft,reviews,additions,deletions,mergeCommit'
    # --limit 1000 is too heavy for the GraphQL endpoint (502/504 every time, 21-26.10.2026); 500 passes and
    # covers all PRs for now (326 on 26.10). A gateway error is transient, so retry before giving up.
    for attempt in range(3):
        r = subprocess.run(['gh', 'pr', 'list', '--state', 'all', '--limit', '500', '--json', fields],
                           cwd=TAF, capture_output=True, text=True)
        if not r.returncode:
            break
        time.sleep(20 * (attempt + 1))
    if r.returncode:
        return 'github: failed, ' + r.stderr.strip()[-300:]
    prs = json.loads(r.stdout)
    for p in prs:   # keep logins only: who reviewed and when
        p['author'] = (p.get('author') or {}).get('login')
        p['mergeCommit'] = (p.get('mergeCommit') or {}).get('oid')
        p['reviews'] = [{'by': (x.get('author') or {}).get('login'), 'at': x.get('submittedAt'), 'state': x.get('state')}
                        for x in p.get('reviews') or []]
    save(os.path.join(STORE, 'raw', 'github', 'prs.json'), {'taken': dt.datetime.now().isoformat(), 'prs': prs})
    return f'github: {len(prs)} PRs'


def develop_at(moment):
    sha = subprocess.run(['git', 'rev-list', '-1', f'--before={moment.isoformat()}', 'origin/develop'],
                         cwd=TAF, capture_output=True, text=True).stdout.strip()
    return sha or None


# One definition of the debt counters for every week, so the series compare: debt.js from this ref is
# run on each week's tree. PR #284 (T1-11) splits `allure.*` into gated steps/attachments; until it is
# merged its branch holds the current definition, and once the branch is gone origin/develop does.
DEBT_DEF_REFS = ['origin/feature/liashenko/T1-11-test-step-attach', 'origin/develop']
ALLURE_META = re.compile(r'\ballure\s*\.\s*(?!step\b|attachment\b)\w+\s*\(')
ALLURE_META_NAME = 'allure metadata: description / suite / subSuite / displayName (T0-26)'


def debt_definition():
    for ref in DEBT_DEF_REFS:
        sha = subprocess.run(['git', 'rev-parse', '--verify', '-q', f'{ref}^{{commit}}'], cwd=TAF,
                             capture_output=True, text=True).stdout.strip()
        if sha:
            return ref, sha
    raise SystemExit('no ref with scripts/debt.js found')


def strip_comments(src):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', src, flags=re.S)


def debt_at(sha):
    ref, def_sha = debt_definition()
    out = os.path.join(STORE, 'raw', 'debt', f'{sha}-def{def_sha[:8]}.json')
    if os.path.exists(out):
        return load(out)
    with tempfile.TemporaryDirectory() as tmp:
        arch = subprocess.run(['git', 'archive', sha], cwd=TAF, capture_output=True)
        subprocess.run(['tar', '-x', '-C', tmp], input=arch.stdout, check=True)
        definition = subprocess.run(['git', 'show', f'{def_sha}:scripts/debt.js'], cwd=TAF, capture_output=True).stdout
        open(os.path.join(tmp, 'scripts', 'debt.js'), 'wb').write(definition)
        subprocess.run(['git', 'init', '-q'], cwd=tmp, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=tmp, check=True)
        r = subprocess.run(['node', 'scripts/debt.js'], cwd=tmp, capture_output=True, text=True,
                           env={**os.environ, 'NODE_PATH': os.path.join(TAF, 'node_modules')})
        meta = 0
        for root, _, files in os.walk(os.path.join(tmp, 'src', 'ui')):
            for f in files:
                if f.endswith('.ts'):
                    meta += len(ALLURE_META.findall(strip_comments(open(os.path.join(root, f), encoding='utf-8').read())))
    if r.returncode:
        return None
    counts = {}
    for line in r.stdout.splitlines()[1:]:
        m = re.match(r'(.+?)\s{2,}(\d+)(\s+yes)?\s*$', line)
        if m:
            counts[m[1].strip()] = {'n': int(m[2]), 'gated': bool(m[3])}
    counts[ALLURE_META_NAME] = {'n': meta, 'gated': False}
    counts['_definition'] = {'ref': ref, 'sha': def_sha[:8]}
    save(out, counts)
    return counts


def collect_debt(weeks):
    subprocess.run(['git', 'fetch', '-q', '--prune', 'origin'], cwd=TAF)
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
        if not (ms(start) <= b['start'] < ms(end)) or not NIGHTLY_BRANCHES.search(b.get('branch') or ''):
            continue
        tests = load(os.path.join(d, f'{n}.json'))
        if tests is None:
            continue
        states = {}
        for key, state, dur in tests:
            states[key] = state
        c = {s: sum(1 for v in states.values() if v == s) for s in ('pass', 'flaky', 'fail')}
        executed = len(states)
        out.append({'number': int(n), 'start': b['start'], 'branch': b.get('branch'), 'line': line_of(b.get('branch')),
                    'sha': b.get('sha'), 'wall_min': round(b['duration'] / 60_000),
                    'machine_h': round(sum(t[2] for t in tests) / 3_600_000, 2), 'executed': executed,
                    'sec_per_test': round(sum(t[2] for t in tests) / 1000 / executed, 1),
                    'flaky': c['flaky'], 'failed': c['fail'], 'flaky_pct': round(c['flaky'] / executed * 100, 2),
                    'mass': c['fail'] / executed * 100 > MASS_PCT, 'states': states})
    return out


def other_branch_nights(start, end):
    index = load(os.path.join(STORE, 'raw', 'nightly', 'index.json'), {})
    return sum(1 for b in index.values() if ms(start) <= b['start'] < ms(end)
               and b['duration'] >= FULL_NIGHT_H * 3_600_000 and not NIGHTLY_BRANCHES.search(b.get('branch') or ''))


def nightly_metrics(start, end):
    nights = nights_in(start, end)
    if not nights:
        return {'nightly.nights': 0, 'nightly.other_branch': other_branch_nights(start, end)}, {}
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
        'nightly.nights': len(nights), 'nightly.other_branch': other_branch_nights(start, end),
        'nightly.on_develop': sum(1 for n in nights if line_of(n['branch']) == 'develop'),
        'nightly.on_fix': sum(1 for n in nights if line_of(n['branch']) == 'fix'),
        'nightly.mass_nights': len(nights) - len(good),
        'nightly.executed': median(n['executed'] for n in good),
        'nightly.flaky_pct': median(n['flaky_pct'] for n in good),
        'nightly.failed': median(n['failed'] for n in good),
        'nightly.flaky_tests': len(flaky_count),
        'nightly.new_failures': len(new_fail) if prev else None,
        'nightly.wall_min': median(n['wall_min'] for n in good),
        'nightly.machine_h': median(n['machine_h'] for n in good),
        'nightly.sec_per_test': median(n['sec_per_test'] for n in good),
    }
    classes = {}
    for n in good:
        for _, _, msg in load(os.path.join(STORE, 'raw', 'nightly', f"{n['number']}.failures.json"), []):
            cls = failure_class(msg)   # from the stored message, so a new rule re-labels old nights too
            classes[cls] = classes.get(cls, 0) + 1
    lists = {
        'failure_classes': sorted(classes.items(), key=lambda kv: -kv[1]),
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
    failed, flaky_count, runs, smoke = {}, {}, [], 0
    for b in week:
        path = os.path.join(store, 'tests', re.sub(r'[^\w.-]+', '_', b['branch']), f"{b['number']}.json")
        d = load(path) or {}
        # The kind of run is known only where the executed count is: files written before it was stored keep
        # failures only. Those builds count for cross-branch failures, not for the full-run numbers.
        full = (d.get('executed') or 0) >= FULLRUN_MIN
        smoke += 0 < (d.get('executed') or 0) < FULLRUN_MIN
        n_fail = n_flaky = 0
        for t in d.get('tests', []):
            key = f"[{t['project']}] {t['name']}"
            if t['status'] in ('failed', 'broken'):
                failed.setdefault(key, set()).add(b['branch'])
                n_fail += 1
            elif t.get('flaky') or t.get('retries'):
                if full:
                    flaky_count[key] = flaky_count.get(key, 0) + 1
                n_flaky += 1
        if full:
            runs.append({'executed': d['executed'], 'failed': n_fail, 'flaky_pct': n_flaky / d['executed'] * 100,
                         'wall_min': b['duration'] / 60_000, 'sec_per_test': d['machine_ms'] / 1000 / d['executed']})
    multi = sorted(((k, len(v)) for k, v in failed.items() if len(v) >= 2), key=lambda kv: -kv[1])
    n_red = sum(1 for b in week if b['result'] in red)
    rnd = lambda v, n=1: None if v is None else round(v, n)
    return ({'branch.builds': len(week), 'branch.red_pct': round(n_red / len(week) * 100, 1) if week else None,
             'branch.to_green_h': median(to_green), 'branch.multi_branch_tests': len(multi),
             'branch.smoke_runs': smoke, 'branch.fullruns': len(runs),
             'branch.executed': median(r['executed'] for r in runs),
             'branch.flaky_pct': rnd(median(r['flaky_pct'] for r in runs), 2),
             'branch.failed': median(r['failed'] for r in runs),
             'branch.flaky_tests': len(flaky_count) if runs else None,
             'branch.wall_min': rnd(median(r['wall_min'] for r in runs), 0),
             'branch.sec_per_test': rnd(median(r['sec_per_test'] for r in runs))},
            {'multi_branch_tests': multi[:15],
             'branch_top_flaky': [[k, c] for k, c in sorted(flaky_count.items(), key=lambda kv: -kv[1])[:15]]})


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
    return ({DEBT_PREFIX + k: v['n'] for k, v in counts.items() if not k.startswith('_')},
            {'debt_commit': sha[:8], 'debt_definition': counts.get('_definition')})


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
        journal.append({'pr': p['number'], 'title': p['title'], 'merged': p['mergedAt'], 'commit': p.get('mergeCommit'),
                        'task': task[0] if task else None,
                        'author': p['author'], 'transformation': None, 'hypothesis': '', 'metrics': [],
                        'recorded': today, 'retro': None})
        added += 1
    save(path, journal)
    todo = [e['pr'] for e in journal if e['transformation'] is None]
    print(f'journal: {len(journal)} entries, +{added}; to classify (transformation true/false, hypothesis, metrics): {todo}')


_ancestry = {}


def contains(night_sha, commit):
    """Whether the TAF commit the night ran on includes the PR's merge commit."""
    if not night_sha or not commit:
        return None
    key = (night_sha, commit)
    if key not in _ancestry:
        r = subprocess.run(['git', 'merge-base', '--is-ancestor', commit, night_sha], cwd=TAF, capture_output=True)
        _ancestry[key] = {0: True, 1: False}.get(r.returncode)
    return _ancestry[key]


def evaluate(entry):
    """Nightly metrics: medians over up to WINDOW full non-mass nights whose TAF commit lacks the change
    (before the merge) against up to WINDOW nights whose commit has it. The nightly job runs whatever
    branch it is pointed at (develop, a daily fix branch, a feature branch), so the merge date alone
    does not say which nights carried the change."""
    merged = dt.datetime.fromisoformat(entry['merged'].replace('Z', '+00:00')).astimezone().replace(tzinfo=None)
    nights = [n for n in nights_in(merged - dt.timedelta(days=28), merged + dt.timedelta(days=28)) if not n['mass']]
    before = [n for n in nights if n['start'] < ms(merged) and contains(n['sha'], entry.get('commit')) is False][-WINDOW:]
    after = [n for n in nights if contains(n['sha'], entry.get('commit'))][:WINDOW]
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
    lines += ['Нічні (QA Jenkins) і гілкові (dev Jenkins) — різні середовища: інші машини, кількість воркерів і набір '
              'тестів. Їхні числа між собою не порівнюються, лише кожне зі своїм минулим тижнем.', '']
    groups = [('Нічний прогін (QA Jenkins)', 'nightly.'), ('Гілкові прогони (dev Jenkins)', 'branch.'),
              ('Slack #jenkins-failed-builds (падіння гілкових білдів, dev Jenkins)', 'slack.'), ('PR у TAF (GitHub)', 'github.')]
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
        lines += ['### Ночі тижня', '', '| Збірка | Старт | Гілка TAF | Виконано | Flaky | Впало | Wall, хв | Machine, год | |',
                  '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for n in L['nights']:
            lines.append(f"| {n['number']} | {dt.datetime.fromtimestamp(n['start'] / 1000):%a %d.%m} | `{n.get('branch') or '?'}` | {n['executed']} | "
                         f"{n['flaky']} ({n['flaky_pct']}%) | {n['failed']} | {n['wall_min']} | {n['machine_h']} | "
                         f"{'масова, виключено' if n['mass'] else ''} |")
        lines.append('')
    for key, title in (('top_flaky', 'Нічні: найчастіше flaky за тиждень (ночей flaky / ночей)'),
                       ('new_failures', 'Нічні: нові падіння (ночей впав / ночей; минулого тижня не падав)'),
                       ('branch_top_flaky', 'Гілкові: найчастіше flaky за тиждень (білдів)'),
                       ('multi_branch_tests', 'Гілкові: падали на кількох гілках (гілок)')):
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
                  f'Нічні показники: медіана до {WINDOW} повних немасових ночей, чий коміт TAF ще не містить зміни, '
                  f'проти до {WINDOW}, що містять (нічний ганяє різні гілки, дата мержу цього не визначає).', '',
                  '| PR | Задача | Змерджено | Гіпотеза | Показник: до → після (ночей) |', '| --- | --- | --- | --- | --- |']
        for e in sorted(tr, key=lambda e: e['merged'], reverse=True):
            ev = evaluate(e)
            res = '; '.join(f'{CATALOG.get(k, (k,))[0]}: {fmt(b)} → {fmt(a)} ({nb}/{na})' for k, (b, a, nb, na) in ev.items())
            if ev and min(min(v[2], v[3]) for v in ev.values()) < 3:
                res += ' — мало ночей, не висновок'
            if not res and e['metrics']:
                res = 'ще збирається' if any(k.startswith('nightly.') for k in e['metrics']) else 'не нічний показник'
            lines.append(f"| #{e['pr']} | {e.get('task') or ''} | {e['merged'][:10]} | "
                         f"{e['hypothesis']}{' *(ретроспективно)*' if e.get('retro') else ''} | {res} |")
    out = os.path.join(STORE, 'weeks', week, 'report.md')
    open(out, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(out)


# Phase targets from 05-roadmap/metrics.md (phase 1), in the catalogue's units.
TARGETS = {'nightly.flaky_pct': 1.0, 'nightly.wall_min': 60, 'nightly.machine_h': 17.0}
PAGE_DIR = os.path.expanduser('~/Work/Precoro/artifacts/taf-stats')


def export(weeks_back):
    """data.json for the TAF stats page: every computed week, the nights, the journal, the topics."""
    weeks = sorted(w for w in os.listdir(os.path.join(STORE, 'weeks'))
                   if os.path.exists(os.path.join(STORE, 'weeks', w, 'metrics.json'))
                   and week_bounds(w)[1] <= dt.datetime.now())[-weeks_back:]   # the running week is not a column
    data = {'generated': dt.datetime.now().isoformat(timespec='minutes'), 'weeks': [], 'metrics': {}, 'debt': {},
            'catalog': {k: {'label': v[0], 'unit': v[1], 'better': v[2], 'source': v[3], 'held': v[4],
                            'group': k.split('.')[0], 'target': TARGETS.get(k)} for k, v in CATALOG.items()},
            'nights': [], 'journal': [], 'topics': {}, 'lists': {}}
    for w in weeks:
        m = load(os.path.join(STORE, 'weeks', w, 'metrics.json'))
        data['weeks'].append({'id': w, 'from': m['from'], 'to': m['to']})
        data['metrics'][w] = {k: v for k, v in m['metrics'].items() if not k.startswith(DEBT_PREFIX)}
        data['debt'][w] = {k[len(DEBT_PREFIX):]: v for k, v in m['metrics'].items() if k.startswith(DEBT_PREFIX)}
        data['lists'][w] = {k: m['lists'].get(k) for k in ('top_flaky', 'new_failures', 'multi_branch_tests', 'branch_top_flaky', 'merged',
                                                          'debt_commit', 'debt_definition')}
        t = load(os.path.join(STORE, 'weeks', w, 'topics.json'))
        if t:
            data['topics'][w] = t
    start = week_bounds(weeks[0])[0]
    for n in nights_in(start, week_bounds(weeks[-1])[1]):
        data['nights'].append({k: n[k] for k in ('number', 'branch', 'line', 'mass', 'executed', 'flaky', 'failed',
                                                 'flaky_pct', 'wall_min', 'machine_h', 'sec_per_test')}
                              | {'date': dt.datetime.fromtimestamp(n['start'] / 1000).strftime('%Y-%m-%d')})
    for e in sorted(load(os.path.join(STORE, 'journal.json'), []), key=lambda e: e['merged'], reverse=True):
        if e.get('transformation'):
            data['journal'].append({k: e.get(k) for k in ('pr', 'title', 'task', 'merged', 'hypothesis', 'retro', 'metrics')}
                                   | {'eval': {k: list(v) for k, v in evaluate(e).items()}})
    # Last scheduled collection, from its log (stats/bin/daily-collect.sh): when, and which sources answered.
    logs = sorted(f for f in os.listdir(os.path.join(STORE, 'logs')) if re.match(r'\d{4}-\d{2}-\d{2}\.log$', f)) \
        if os.path.isdir(os.path.join(STORE, 'logs')) else []
    if logs:
        lines = open(os.path.join(STORE, 'logs', logs[-1]), encoding='utf-8').read().splitlines()
        runs = [i for i, l in enumerate(lines) if re.match(r'^\w{3} \w{3} +\d+ [\d:]+ ', l)]
        run = lines[runs[-1]:] if runs else lines
        data['collect'] = {'date': logs[-1][:10], 'time': (re.search(r'\d{2}:\d{2}', run[0]) or [''])[0] if run else '',
                           'sources': [l.split(':')[0] for l in run if re.match(r'^(nightly|jenkins-dev|github|debt):', l)],
                           'failed': [l.split(':')[0] for l in run if re.match(r'^(nightly|jenkins-dev|github|debt):', l)
                                      and re.search(r'failed|skipped|error|Traceback', l)]}
    out = os.path.join(PAGE_DIR, 'data.json')
    save(out, data)
    print(out)


def catalog():
    print('| Ключ | Показник | Одиниця | Краще | Джерело | Чекає |\n| --- | --- | --- | --- | --- | --- |')
    for k, (label, unit, better, source, held) in CATALOG.items():
        print(f'| `{k}` | {label} | {unit} | {"↓" if better == "down" else "↑" if better == "up" else ""} | {source} | {held or ""} |')
    print(f'| `{DEBT_PREFIX}<патерн>` | кожен патерн `npm run debt` | входжень | ↓ | `scripts/debt.js` на `develop` | |')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['collect', 'week', 'report', 'journal-sync', 'catalog', 'export'])
    ap.add_argument('--week')
    ap.add_argument('--only', default='nightly,github,debt,jenkins-dev')
    ap.add_argument('--weeks', type=int, default=3, help='collect debt for this many last weeks')
    ap.add_argument('--weeks-back', type=int, default=12, help='export: this many last computed weeks')
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
    elif a.cmd == 'export':
        export(a.weeks_back)
    elif a.cmd == 'journal-sync':
        journal_sync()
    else:
        catalog()


if __name__ == '__main__':
    main()
