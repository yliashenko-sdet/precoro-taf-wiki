import json,os,sys,re,collections
root=sys.argv[1]
tot=collections.Counter(); names=collections.Counter()
for n in sorted(os.listdir(root)):
    d=os.path.join(root,n,'test-cases')
    if not os.path.isdir(d): continue
    att=0; final=0; tests=set()
    for f in os.listdir(d):
        j=json.load(open(os.path.join(d,f)))
        if j.get('status') not in ('failed','broken'): continue
        msg=(j.get('testStage') or {}).get('statusMessage') or ''
        trace=(j.get('testStage') or {}).get('statusTrace') or ''
        if 'toast:success' not in msg+trace: continue
        att+=1; tests.add(j['fullName'])
        if not j.get('hidden'): final+=1
        names[j['name'][:70]]+=1
    print(f"{n}: failed attempts on success toast {att}, final failures {final}, distinct tests {len(tests)}")
print('--- top tests'); 
for k,v in names.most_common(15): print(v,k)
