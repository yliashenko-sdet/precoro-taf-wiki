// For each looped test site: builds where some variants finally failed and others did not (mass builds excluded).
// Input: history/<source>~<build>.json from normalize_history.py. A branch record has no file: matched by title
// alone, and only when exactly one site matches. Usage: node divergence.js <sites.json> <history dir> <out.json> [massPct=10] [minBuilds=2]
const fs = require('fs'), path = require('path');
const [sitesF, dir, outF, massArg, minArg] = process.argv.slice(2);
const mass = +(massArg || 10), minBuilds = +(minArg || 2);
const sites = require(path.resolve(sitesF));
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
for (const s of sites) {
  const t = s.title.trim(); let re;
  if (t.startsWith('`')) re = t.slice(1, -1).split(/\$\{[^}]*\}/).map(esc).join('.*');
  else re = t.split(/\s*\+\s*/).map(p => /^['"]/.test(p) ? esc(p.slice(1, -1)) : '.*').join('');
  s.re = new RegExp('^' + re + '$', 's'); s.base = path.basename(s.file); s.builds = []; s.seen = 0;
}
const find = (file, title) => {
  const c = sites.filter(s => (!file || s.base === file) && s.re.test(title));
  return c.length === 1 ? c[0] : null;
};
const mass_ = {}, used = {};
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.json'))) {
  const [src, build] = f.slice(0, -5).split('~');
  const recs = JSON.parse(fs.readFileSync(path.join(dir, f)));
  if (recs.filter(r => r[3] === 'fail').length / recs.length * 100 > mass) { mass_[src] = (mass_[src] || 0) + 1; continue; }
  used[src] = (used[src] || 0) + 1;
  const bySite = new Map();
  for (const [, file, title, st] of recs) {
    const s = find(file, title); if (!s) continue;
    if (!bySite.has(s)) bySite.set(s, []); bySite.get(s).push([title, st]);
  }
  for (const [s, v] of bySite) {
    if (v.length > 1) s.seen++;
    const fl = v.filter(x => x[1] === 'fail');
    if (fl.length && fl.length < v.length) s.builds.push({ src, build, failed: fl.map(x => x[0]), of: v.length });
  }
}
const res = sites.map(s => {
  const cnt = {}; for (const b of s.builds) for (const t of b.failed) cnt[t] = (cnt[t] || 0) + 1;
  const top = Object.entries(cnt).sort((a, b) => b[1] - a[1]);
  return { file: s.file, line: s.line, cls: s.cls, tests: s.listed, buildsSeen: s.seen, divergent: s.builds.length,
    sameVariantMax: top.length ? top[0][1] : 0, verdict: !s.seen ? 'no-history' : s.builds.length >= minBuilds ? 'do-not-touch' : s.builds.length ? 'weak' : 'clean',
    failedVariants: top, builds: s.builds };
});
fs.writeFileSync(outF, JSON.stringify({ used, massExcluded: mass_, minBuilds, sites: res }, null, 1));
const v = {}; for (const r of res) { const k = r.cls[0] + ' ' + r.verdict; v[k] = (v[k] || 0) + r.tests; }
console.log('builds used', used, 'mass excluded', mass_); console.log(Object.entries(v).sort().map(([k, n]) => `${k}: ${n}`).join('\n'));
