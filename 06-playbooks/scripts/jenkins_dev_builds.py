#!/usr/bin/env python3
"""Branch builds of Jenkins dev: keep their history and measure it.

The multibranch job keeps only branches with an open PR; a merged branch disappears together with
its builds. `collect` copies what is there now into a local store and never deletes from it, so
running it daily keeps the history. `report` measures the store.

    python3 jenkins_dev_builds.py collect [--store DIR]
    python3 jenkins_dev_builds.py report  [--store DIR] [--since YYYY-MM-DD] [--until YYYY-MM-DD] [--top N]

Credentials: JENKINS_DEV_URL, JENKINS_DEV_USER_NAME (or JENKINS_DEV_USER), JENKINS_DEV_PASS from the environment or from the
TAF .env (TAF_ENV, default ~/Work/src/precoro-e2e-playwright/.env). Nothing secret is printed or
written to the store.

Store (default ~/Work/Precoro/artifacts/jenkins-dev):
    index.json              every build ever seen: branch, number, result, start, duration, first_seen
    tests/<branch>/<n>.json failed, broken and flaky tests of a finished build (from its Allure data),
                            with the count of executed tests and their summed duration

A red build is FAILURE or UNSTABLE. Time to green: from the end of a red build to the end of the
next SUCCESS build on the same branch. NOT_BUILT and ABORTED are skipped in both roles.
"""
import argparse
import base64
import datetime as dt
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request

JOB = 'test%20webhook%20pr%20creation'
RED = {'FAILURE', 'UNSTABLE'}
DEFAULT_STORE = os.path.expanduser('~/Work/Precoro/artifacts/jenkins-dev')
DEFAULT_ENV = os.path.expanduser('~/Work/src/precoro-e2e-playwright/.env')


def creds():
    env = {}
    path = os.environ.get('TAF_ENV', DEFAULT_ENV)
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            m = re.match(r'\s*(JENKINS_DEV_\w+)\s*=\s*(.*)\s*$', line)
            if m:
                env[m[1]] = m[2].strip().strip('"').strip("'")
    get = lambda k: os.environ.get(k) or env.get(k)
    url, user, pwd = get('JENKINS_DEV_URL'), get('JENKINS_DEV_USER_NAME') or get('JENKINS_DEV_USER'), get('JENKINS_DEV_PASS')
    if not (url and user and pwd):
        sys.exit('JENKINS_DEV_URL, JENKINS_DEV_USER_NAME, JENKINS_DEV_PASS are not set (env or TAF .env)')
    return url.rstrip('/'), 'Basic ' + base64.b64encode(f'{user}:{pwd}'.encode()).decode()


def fetch(base, auth, path):
    req = urllib.request.Request(base + path, headers={'Authorization': auth})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def leaves(node):
    if 'children' in node:
        for c in node['children']:
            yield from leaves(c)
    else:
        yield node


def collect(store):
    base, auth = creds()
    os.makedirs(os.path.join(store, 'tests'), exist_ok=True)
    index_path = os.path.join(store, 'index.json')
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    today = dt.date.today().isoformat()
    tree = urllib.parse.quote('jobs[name,builds[number,result,timestamp,duration,building]]')
    data = fetch(base, auth, f'/job/{JOB}/api/json?tree={tree}')
    new_builds = new_tests = 0
    for job in data['jobs']:
        branch = urllib.parse.unquote(job['name'])
        for b in job.get('builds') or []:
            if b.get('building') or b.get('result') is None:
                continue
            key = f"{branch}#{b['number']}"
            if key not in index:
                new_builds += 1
                index[key] = {'branch': branch, 'number': b['number'], 'result': b['result'],
                              'start': b['timestamp'], 'duration': b['duration'], 'first_seen': today}
            if b['result'] not in RED and b['result'] != 'SUCCESS':
                continue
            safe = re.sub(r'[^\w.-]+', '_', branch)
            out = os.path.join(store, 'tests', safe, f"{b['number']}.json")
            # files written before `executed` was stored are fetched again while the build is still in Jenkins
            if os.path.exists(out) and 'executed' in json.load(open(out)):
                continue
            suites = fetch(base, auth, f"/job/{JOB}/job/{urllib.parse.quote(job['name'], safe='%')}/{b['number']}/allure/data/suites.json")
            tests, executed, machine_ms = [], 0, 0
            for leaf in leaves(suites or {}):
                if leaf.get('status') != 'skipped':
                    executed += 1
                    machine_ms += (leaf.get('time') or {}).get('duration') or 0
                if leaf.get('status') in ('failed', 'broken') or leaf.get('flaky') or leaf.get('retriesCount'):
                    tests.append({'name': leaf.get('name'), 'status': leaf.get('status'),
                                  'flaky': bool(leaf.get('flaky')), 'retries': leaf.get('retriesCount', 0),
                                  'project': (leaf.get('parameters') or [None])[0]})
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump({'allure': suites is not None, 'executed': executed, 'machine_ms': machine_ms, 'tests': tests},
                      open(out, 'w'))
            new_tests += 1
    json.dump(index, open(index_path, 'w'), indent=0)
    print(f'{today}: branches now {len(data["jobs"])}, builds in store {len(index)} (+{new_builds}), '
          f'test files +{new_tests}')


def pct(values, p):
    if not values:
        return None
    s = sorted(values)
    return s[min(len(s) - 1, int(round(p * (len(s) - 1))))]


def hours(ms):
    return None if ms is None else round(ms / 3_600_000, 1)


def report(store, since, until, top):
    index = json.load(open(os.path.join(store, 'index.json')))
    day = lambda ms: dt.datetime.fromtimestamp(ms / 1000).date().isoformat()
    builds = [b for b in index.values()
              if (not since or day(b['start']) >= since) and (not until or day(b['start']) <= until)]
    by_branch = {}
    for b in builds:
        by_branch.setdefault(b['branch'], []).append(b)
    to_green, reds_before_green, open_red = [], [], 0
    for bs in by_branch.values():
        bs.sort(key=lambda b: b['number'])
        streak = 0
        for i, b in enumerate(bs):
            if b['result'] in RED:
                streak += 1
                nxt = next((x for x in bs[i + 1:] if x['result'] == 'SUCCESS'), None)
                if nxt is None:
                    open_red += 1
                else:
                    to_green.append(nxt['start'] + nxt['duration'] - (b['start'] + b['duration']))
            elif b['result'] == 'SUCCESS':
                if streak:
                    reds_before_green.append(streak)
                streak = 0
    results = {}
    for b in builds:
        results[b['result']] = results.get(b['result'], 0) + 1
    print(f'Builds {len(builds)} on {len(by_branch)} branches; by result {results}')
    print(f'Red builds with a later green on the branch: {len(to_green)}; still red or branch gone: {open_red}')
    print(f'Time to green, hours: median {hours(pct(to_green, .5))}, p75 {hours(pct(to_green, .75))}, '
          f'p90 {hours(pct(to_green, .9))}')
    print(f'Red builds in a row before green: median {pct(reds_before_green, .5)}, '
          f'p75 {pct(reds_before_green, .75)}, max {max(reds_before_green) if reds_before_green else None}')

    failed, flaky = {}, {}
    no_allure = 0
    for b in builds:
        if b['result'] not in RED and b['result'] != 'SUCCESS':
            continue
        path = os.path.join(store, 'tests', re.sub(r'[^\w.-]+', '_', b['branch']), f"{b['number']}.json")
        if not os.path.exists(path):
            continue
        d = json.load(open(path))
        if not d['allure']:
            no_allure += 1
        for t in d['tests']:
            key = f"[{t['project']}] {t['name']}"
            target = failed if t['status'] in ('failed', 'broken') else flaky
            e = target.setdefault(key, {'branches': set(), 'builds': 0})
            e['branches'].add(b['branch'])
            e['builds'] += 1
    print(f'Builds without Allure data: {no_allure}')
    for title, table in (('Failed (final) on most branches', failed), ('Flaky (passed on retry) on most branches', flaky)):
        rows = sorted(table.items(), key=lambda kv: (-len(kv[1]['branches']), -kv[1]['builds']))
        print(f'\n{title}: {len(rows)} tests, {sum(1 for _, e in rows if len(e["branches"]) >= 2)} on 2+ branches')
        for name, e in rows[:top]:
            print(f'  {len(e["branches"]):3} branches {e["builds"]:3} builds  {name}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['collect', 'report'])
    ap.add_argument('--store', default=DEFAULT_STORE)
    ap.add_argument('--since')
    ap.add_argument('--until')
    ap.add_argument('--top', type=int, default=25)
    a = ap.parse_args()
    if a.cmd == 'collect':
        collect(a.store)
    else:
        report(a.store, a.since, a.until, a.top)


if __name__ == '__main__':
    main()
