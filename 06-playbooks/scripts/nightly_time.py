#!/usr/bin/env python3
"""Куди йде час нічного прогону, з Allure-даних збірок QA Jenkins.

  fetch <build>...                     test-cases/*.json збірки в ~/Work/Precoro/artifacts/nightly-allure/<build>/
                                       (креденшели JENKINS_URL / JENKINS_USER_NAME / JENKINS_PASS, як у team_stats.py)
  waits <build>...                     по ночах: очікування, що добігли до таймауту, у тестах, що пройшли;
                                       dashboardPage; падіння разом із ретраями; топ-локатори за середнім часом
  wall <playwright.config.ts> <build>...
                                       wall-clock з machine-time проєктів: проєкт іде на одному воркері, проєкти
                                       роздаються вільним воркерам у порядку конфігу; порівняння з сортуванням
                                       за часом і з прибиранням топ-очікувань
  concurrency <build>                  скільки тестів ішло одночасно, частка часу прогону
  long <build | local-run dir>...      T1-29: кроки тестів, що пройшли, які завершились успішно довше за 15 с
                                       (навігація за 30 с) — їх зламає зниження таймаутів; проби, що добігли до
                                       60 с за замовчуванням (виграш); падіння з ретраями. Локальний прогін
                                       читається з HTML-звіту (report/index.html): там є файл:рядок кроку

Очікування «до таймауту» — листовий крок Allure, що тривав T..T+350 мс для T з 1, 2, 3, 5, 10, 15, 20, 30, 60 с.
Для 1–2 с віднімається контрольне вікно T+500..T+850 мс (випадкові збіги); «≥ 3 с» у таблиці по ночах
рахується без поправки, контрольне вікно там майже порожнє.
Топ-локатори і віднімання топ-очікувань у wall рахуються з поправкою в кожній корзині, окремо для кожного
локатора (проєкту): у лоадера корзина 1–2 с дорівнює контрольному вікну, тобто це звичайне зникнення, не таймаут.
"""
import base64, collections, glob, json, os, re, statistics, sys
from concurrent.futures import ThreadPoolExecutor

STORE = os.path.expanduser(os.environ.get('NIGHTLY_ALLURE_DIR', '~/Work/Precoro/artifacts/nightly-allure'))
T = [1000, 2000, 3000, 5000, 10000, 15000, 20000, 30000, 60000]
W = 350
H = 3.6e6
WORKERS = int(os.environ.get('W', 9))  # нічний іде на Windows CI: 9 воркерів (playwright.config.ts)
# Топ-11 очікувань за 297, 298, 299, 301 з поправкою на контрольне вікно (картка T1-33); клік у legal entity
# потрапляє через той самий підрядок. Skeleton (0,08 год) замінено на button:delete 2026-11-04.
TOP = ['data-test-id="loader"', 'input:item_ordered', 'input:legal_entity" or', 'input:comment', 'toast:error',
       'pc-select__menu-container', '.available.today', 'button:delete"]\').first()', 'button:add_product',
       'contains(text(), "DCC")']


def tests(build):
    for f in glob.glob(os.path.join(STORE, str(build), 'test-cases', '*.json')):
        d = json.load(open(f))
        if d.get('status') == 'skipped':
            continue
        d['_labels'] = {l['name']: l['value'] for l in d.get('labels', [])}
        d['_retries'] = sum(((x.get('time') or {}).get('duration') or 0) for x in (d.get('extra') or {}).get('retries') or [])
        yield d


def at_timeout(d):
    return next((t for t in T if t <= d <= t + W), None), next((t for t in T if t + 500 <= d <= t + 500 + W), None)


def net(hits, ctls):
    """Час до таймауту за вирахуванням контрольного вікна, по кожній корзині окремо."""
    return sum(max(0, hits[t] - ctls[t]) for t in T)


def leaves(steps):
    for s in steps:
        if s.get('steps'):
            yield from leaves(s['steps'])
        else:
            yield s


def fetch(builds):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import team_stats as ts
    c = ts.env_creds(['JENKINS_URL', 'JENKINS_USER_NAME', 'JENKINS_PASS'])
    if not c:
        sys.exit('JENKINS_URL / JENKINS_USER_NAME / JENKINS_PASS not set')
    base, auth = c[0].rstrip('/'), 'Basic ' + base64.b64encode(f'{c[1]}:{c[2]}'.encode()).decode()
    for n in builds:
        suites = ts.fetch(base, auth, f'/job/{ts.NIGHTLY_JOB}/{n}/allure/data/suites.json')
        if suites is None:
            print(f'{n}: no Allure data in Jenkins')
            continue
        out = os.path.join(STORE, str(n), 'test-cases')
        os.makedirs(out, exist_ok=True)

        def get(uid):
            p = os.path.join(out, uid + '.json')
            if os.path.exists(p):
                return 1
            d = ts.fetch(base, auth, f'/job/{ts.NIGHTLY_JOB}/{n}/allure/data/test-cases/{uid}.json')
            if d is None:
                return 0
            json.dump(d, open(p, 'w'))
            return 1
        uids = [t['uid'] for _, t in ts.leaves(suites)]
        with ThreadPoolExecutor(8) as ex:
            ok = sum(ex.map(get, uids))
        print(f'{n}: {ok}/{len(uids)} test-cases')


def waits(builds):
    rows, sites = [], collections.defaultdict(list)
    for n in builds:
        r = collections.Counter()
        site_hit, site_ctl = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
        for d in tests(n):
            dur = d['time'].get('duration', 0)
            r['all'] += dur + d['_retries']
            steps = (d.get('testStage') or {}).get('steps') or []
            for s in steps:
                if s.get('name') == 'Before Hooks':
                    r['dash'] += sum((k.get('time') or {}).get('duration') or 0 for k in s.get('steps') or []
                                     if k.get('name') == 'Fixture "dashboardPage"')
            if d['status'] != 'passed':
                r['failing'] += dur + d['_retries']
                r['nfail'] += 1
                continue
            r['npassed'] += 1
            for s in leaves(steps):
                sd = (s.get('time') or {}).get('duration') or 0
                hit, ctl = at_timeout(sd)
                if hit:
                    r[('hit', hit)] += sd
                    site_hit[s.get('name', '')[:110]][hit] += sd
                    r['n60'] += hit == 60000
                elif ctl:
                    r[('ctl', ctl)] += sd
                    site_ctl[s.get('name', '')[:110]][ctl] += sd
        strict = sum(r[('hit', t)] for t in T if t >= 3000)
        loose = sum(max(0, r[('hit', t)] - r[('ctl', t)]) for t in T)
        rows.append((n, r, strict, loose))
        for k in site_hit:
            v = net(site_hit[k], site_ctl[k])
            if v:
                sites[k].append(v)
    print('| Ніч | Пройшло | Machine-time, год | До таймауту ≥ 3 с | З 1–2 с | По 60 с | dashboardPage | Падіння з ретраями |')
    print('| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |')
    pct = lambda v, a: f'{v / H:.2f} ({v / a * 100:.1f}%)'
    for n, r, s, l in rows:
        a = r['all']
        print(f"| {n} | {r['npassed']} | {a / H:.1f} | {pct(s, a)} | {pct(l, a)} | {r['n60']} | {pct(r['dash'], a)} | {pct(r['failing'], a)} [{r['nfail']}] |")
    m = lambda f: statistics.mean(f(x) for x in rows)
    print(f"| середнє | | {m(lambda x: x[1]['all']) / H:.1f} | {m(lambda x: x[2]) / H:.2f} ({m(lambda x: x[2] / x[1]['all']) * 100:.1f}%) | "
          f"{m(lambda x: x[3]) / H:.2f} ({m(lambda x: x[3] / x[1]['all']) * 100:.1f}%) | | "
          f"{m(lambda x: x[1]['dash']) / H:.2f} | {m(lambda x: x[1]['failing']) / H:.2f} |")
    print(f'\nТоп-20 очікувань до таймауту в тестах, що пройшли, за вирахуванням контрольного вікна, '
          f'год за ніч, середнє за {len(rows)} (мін..макс):')
    cum = 0
    for k, v in sorted(sites.items(), key=lambda kv: -sum(kv[1]))[:20]:
        v = v + [0] * (len(rows) - len(v))
        mean = sum(v) / len(rows) / H
        cum += mean
        print(f'  {mean:5.2f} ({min(v) / H:.2f}..{max(v) / H:.2f}) Σ {cum:5.2f}  {k}')


def pack(mt, order):
    load, seen = [0.0] * WORKERS, set()
    for p in list(order) + sorted(mt):
        if p in mt and p not in seen:
            seen.add(p)
            i = load.index(min(load))
            load[i] += mt[p]
    return max(load)


def wall(config, builds):
    order = re.findall(r"name: '([a-z_0-9]+)'", open(config, encoding='utf-8').read())
    print(f'{WORKERS} воркерів; хв тестів від першого старту до останнього кінця (без підняття стеку)')
    for n in builds:
        mt = collections.Counter()
        top_hit, top_ctl = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
        for d in tests(n):
            p = d['_labels'].get('parentSuite', '?')
            mt[p] += (d['time'].get('duration', 0) + d['_retries']) / 60000
            if d['status'] == 'passed':
                for s in leaves((d.get('testStage') or {}).get('steps') or []):
                    k = next((k for k in TOP if k in s.get('name', '')), None)
                    if not k:
                        continue
                    sd = (s.get('time') or {}).get('duration') or 0
                    hit, ctl = at_timeout(sd)
                    if hit:
                        top_hit[(p, k)][hit] += sd / 60000
                    elif ctl:
                        top_ctl[(p, k)][ctl] += sd / 60000
        top = collections.Counter()
        for (p, k), hits in top_hit.items():
            top[p] += net(hits, top_ctl[(p, k)])
        less = {p: mt[p] - top[p] for p in mt}
        by_time = lambda x: sorted(x, key=lambda p: -x[p])
        longest = max(mt, key=mt.get)
        print(f'{n}: порядок конфігу {pack(mt, order):.0f} | за часом {pack(mt, by_time(mt)):.0f} | '
              f'за часом без топ-очікувань {pack(less, by_time(less)):.0f} | найдовший проєкт {longest} '
              f'{mt[longest]:.0f} -> {less[longest]:.0f}')


NAV = ('Navigate to', 'Reload', 'Go back', 'Wait for navigation', 'Wait for load state', 'Wait for URL')


def runs(src):
    """(статус, тривалість, кроки) кожної спроби; крок — (назва, тривалість, успішний, місце, діти)."""
    if src.isdigit():
        conv = lambda ss: [(s.get('name', ''), (s.get('time') or {}).get('duration') or 0, s.get('status') == 'passed',
                            '', conv(s.get('steps') or [])) for s in ss]
        for d in tests(src):
            steps = conv((d.get('testStage') or {}).get('steps') or [])
            yield d['status'], d['time'].get('duration', 0), steps
            if d['_retries']:
                yield 'failed', d['_retries'], []
        return
    import io, zipfile
    html = open(os.path.join(src, 'report', 'index.html'), encoding='utf-8').read()
    z = zipfile.ZipFile(io.BytesIO(base64.b64decode(re.search(r'playwrightReportBase64">data:application/zip;base64,([^<"]+)', html).group(1))))
    loc = lambda s: f"{s['location']['file'].split('/')[-1]}:{s['location']['line']}" if s.get('location') else ''
    conv = lambda ss: [(s['title'], s['duration'], not s.get('error'), loc(s), conv(s.get('steps') or [])) for s in ss]
    for f in z.namelist():
        if f != 'report.json':
            for t in json.loads(z.read(f))['tests']:
                for r in t['results']:
                    yield r['status'], r['duration'], conv(r['steps'])


def long(sources):
    for src in sources:
        r, slow, probes = collections.Counter(), collections.Counter(), collections.Counter()

        def walk(ss, failed):
            for name, dur, ok, where, kids in ss:
                # toPass і poll — не листові кроки, але їх обмежує той самий таймаут expect
                if kids and not name.startswith('Expect'):
                    walk(kids, failed)
                    continue
                if failed:
                    r['fail60'] += at_timeout(dur)[0] == 60000 and dur
                elif ok and dur > (30000 if name.startswith(NAV) else 15000):
                    slow[(name[:90], where)] += 1
                elif not ok and at_timeout(dur)[0] == 60000:
                    probes[(name[:90], where)] += 1
                    r['probe60'] += dur
        for status, dur, steps in runs(src):
            r['all'] += dur
            if status not in ('passed', 'skipped'):
                r['failing'] += dur
            walk(steps, status != 'passed')
        print(f"{src}: machine-time {r['all'] / H:.2f} год; падіння з ретраями {r['failing'] / H:.2f} год, з них "
              f"очікування по 60 с {r['fail60'] / H:.2f}; проби до 60 с у тестах, що пройшли, "
              f"{sum(probes.values())} за {r['probe60'] / H:.2f} год (з 15 с: {r['probe60'] / 4 / H:.2f})")
        print(f'  успішні кроки довші за 15 с (навігація 30 с): {sum(slow.values())}')
        for (name, where), c in slow.most_common():
            print(f'    {c:3d}  {name}  {where}')
        for (name, where), c in probes.most_common():
            print(f'    проба 60 с ×{c}  {name}  {where}')


def concurrency(build):
    ev = []
    for d in tests(build):
        t = d.get('time') or {}
        if t.get('start'):
            ev += [(t['start'], 1), (t['stop'], -1)]
    ev.sort()
    cur, hist, prev = 0, collections.Counter(), ev[0][0]
    for ts_, k in ev:
        hist[cur] += ts_ - prev
        prev, cur = ts_, cur + k
    span = ev[-1][0] - ev[0][0]
    print(f'{build}: від першого старту до останнього кінця {span / 60000:.0f} хв')
    for c in sorted(hist):
        print(f'  {c:2d} одночасно: {hist[c] / span * 100:5.1f}%')


if __name__ == '__main__':
    cmd, args = sys.argv[1], sys.argv[2:]
    {'fetch': lambda: fetch(args), 'waits': lambda: waits(args), 'wall': lambda: wall(args[0], args[1:]),
     'concurrency': lambda: concurrency(args[0]), 'long': lambda: long(args)}[cmd]()
