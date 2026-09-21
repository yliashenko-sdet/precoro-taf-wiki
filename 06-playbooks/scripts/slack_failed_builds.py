#!/usr/bin/env python3
"""Парсер текстового експорту каналу Jenkins Failed Builds (без тредів)."""
import re, sys, collections, statistics
s = open(sys.argv[1], encoding='utf-8').read().replace(' ', ' ')
hdr = re.compile(r'(PrecoroCI|[A-Z][a-z]+ [A-Z][a-z]+)  \[(\d{1,2}:\d{2} [AP]M)\]')
heads = [(m.start(), m.end(), m.group(1)) for m in hdr.finditer(s)]
msgs = [(who, s[en:(heads[i+1][0] if i+1 < len(heads) else len(s))]) for i, (st, en, who) in enumerate(heads)]
bot = [t for who, t in msgs if who == 'PrecoroCI']
def stage_of(t):
    m = re.search(r'Failed at stage: ([^\n]+?)(?=$|\n)', t); return m.group(1).strip() if m else '?'
def cat(st):
    if st.startswith(('Test End-to-End', 'Full Run Tests: playwright')): return 'tests'
    if 'Sentry' in st: return 'sentry'
    if st.startswith('Auto Update'): return 'merge'
    if 'Unit Tests' in st: return 'unit'
    return 'pipeline'
br = collections.Counter(); maxb = {}
for t in bot:
    b = re.search(r'for branch: (\S+?)Build (\d+)', t)
    if b: br[b.group(1)] += 1; maxb[b.group(1)] = max(maxb.get(b.group(1), 0), int(b.group(2)))
cc = collections.Counter(cat(stage_of(t)) for t in bot); tot = sum(cc.values())
print("bot posts", len(bot), "branches", len(br), "humans", sum(1 for who, _ in msgs if who != 'PrecoroCI'))
print("categories", [(k, v, f"{round(v/tot*100)}%") for k, v in cc.most_common()])
print("stages", collections.Counter(stage_of(t) for t in bot).most_common(12))
v = sorted(maxb.values()); print("max build per branch: median", statistics.median(v), "p90", v[int(len(v)*.9)], ">=5:", sum(1 for x in v if x >= 5), ">=20:", sum(1 for x in v if x >= 20))
print("smoke passed but full failed", sum(1 for t in bot if 'Smoke passed' in t), "| no task link", len(re.findall(r'No task link', s)), "| missing Jenkinsfile", len(re.findall(r'missing Jenkinsfile', s)))
