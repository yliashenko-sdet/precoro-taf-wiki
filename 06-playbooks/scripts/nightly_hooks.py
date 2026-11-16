#!/usr/bin/env python3
"""Час хуків нічного прогону за фікстурами, з тих самих Allure-даних, що й nightly_time.py.

  nightly_hooks.py <build>...   machine-time, ретраї, Before/After Hooks і топ фікстур по кожній ночі

Рахується остання спроба тесту; час ретраїв окремим числом, тож setup, запущений ретраєм, у рядки фікстур не входить.
"""
import glob,json,os,collections,sys,re
S=os.path.expanduser('~/Work/Precoro/artifacts/nightly-allure')
H=3.6e6
dur=lambda s:(s.get('time') or {}).get('duration') or 0
for b in sys.argv[1:]:
    tot=n=retries=0; top=collections.Counter(); fx=collections.Counter(); fc=collections.Counter(); ex=collections.Counter(); proj=collections.Counter(); projs=collections.Counter()
    def walk(steps,depth=0):
        for s in steps or []:
            nm=re.sub(r'\d+','N',s.get('name','?'))[:70]
            if 'xchange' in nm or 'setupAll' in nm or 'ompanyProfile' in nm or 'ompany setup' in nm.lower(): ex[nm]+=dur(s)
            walk(s.get('steps'),depth+1)
    for f in glob.glob(f'{S}/{b}/test-cases/*.json'):
        d=json.load(open(f))
        if d.get('status')=='skipped':continue
        n+=1; tot+=dur(d)
        retries+=sum(dur(x) for x in (d.get('extra') or {}).get('retries') or [])
        L={l['name']:l['value'] for l in d.get('labels',[])}
        st=(d.get('testStage') or {}).get('steps') or []
        for s in st:
            nm=s.get('name','?')
            if nm in('Before Hooks','After Hooks'):
                top[nm]+=dur(s)
                for c in s.get('steps') or []:
                    k=re.sub(r'\d+','N',c.get('name','?'))[:60]; fx[(nm[0],k)]+=dur(c); fc[(nm[0],k)]+=1
        walk(st)
    print(f'== {b}: tests {n}, machine {tot/H:.2f}h, retries {retries/H:.2f}h, '+', '.join(f'{k} {v/H:.2f}h' for k,v in top.items()))
    for k,v in fx.most_common(16): print(f'  {v/H:6.2f}h x{fc[k]:<5} {k[0]} {k[1]}')
    print('  -- named'); 
    for k,v in ex.most_common(8): print(f'  {v/H:6.2f}h {k}')
