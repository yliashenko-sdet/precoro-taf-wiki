#!/usr/bin/env python3
"""Симуляція розподілу проектів по воркерах: порядок як у конфігу vs найбільші першими."""
import json, re, sys
latest, cfg = sys.argv[1], sys.argv[2]
order = re.findall(r"name: '([a-z_0-9]+)'", open(cfg, encoding='utf-8').read())
mt = {k: v['sumTestDurationMs']/60000 for k, v in json.load(open(latest))['perProject'].items()}
def sim(seq, w):
    load = [0]*w
    for p in seq: i = load.index(min(load)); load[i] += mt.get(p, 0)
    return max(load), sum(load)/w
seq_cfg = [p for p in order if p in mt]; seq_lpt = sorted(mt, key=lambda p: -mt[p])
for w in (9, 12, 16):
    print(f"{w} workers: config {sim(seq_cfg, w)[0]:.0f} | largest-first {sim(seq_lpt, w)[0]:.0f} | ideal {sim(seq_lpt, w)[1]:.0f} min | longest project {max(mt.values()):.0f}")
