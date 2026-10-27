// For every looped test()/describe() site: where do the loop variables end up inside the test body?
//   assert  an identifier of the loop variable sits in expect(...) / assert*(...) arguments or a matcher call on them
//   branch  ... in an if / ternary / switch / &&, || condition
//   label   ... in the title, annotations or qase.parameters only
//   data    everything else (passed to builders, strategies, helpers)
// Run from the TAF repo root: node param_usage.js src/ui/web/tests <out.json>
const ts = require(process.cwd() + '/node_modules/typescript');
const fs = require('fs'), path = require('path');
const root = process.argv[2];
const files = [];
(function walk(d){ for (const f of fs.readdirSync(d)) { const p = path.join(d, f); const s = fs.statSync(p);
  if (s.isDirectory()) walk(p); else if (p.endsWith('.spec.ts')) files.push(p); } })(root);

const names = bn => { const r = [];
  (function w(b){ if (ts.isIdentifier(b)) r.push(b.text);
    else if (ts.isObjectBindingPattern(b) || ts.isArrayBindingPattern(b)) b.elements.forEach(e => { if (!ts.isOmittedExpression(e)) w(e.name); }); })(bn);
  return r; };

const testKind = n => {
  if (!ts.isCallExpression(n)) return null;
  const e = n.expression;
  if (ts.isIdentifier(e) && e.text === 'test') return 'test';
  if (ts.isPropertyAccessExpression(e) && ts.isIdentifier(e.expression) && e.expression.text === 'test') {
    if (e.name.text === 'describe') return 'describe';
    if (['only', 'fixme', 'skip'].includes(e.name.text) && n.arguments.length >= 2) return 'test'; }
  if (ts.isPropertyAccessExpression(e) && ts.isPropertyAccessExpression(e.expression) && e.expression.name.text === 'describe') return 'describe';
  return null; };

const isAssertCall = n => ts.isCallExpression(n) && (() => { let e = n.expression;
  while (ts.isPropertyAccessExpression(e) || ts.isCallExpression(e)) e = ts.isPropertyAccessExpression(e) ? e.expression : e.expression;
  return ts.isIdentifier(e) && (e.text === 'expect' || /^assert/.test(e.text)); })();

const out = [];
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true);
  const line = n => sf.getLineAndCharacterOfPosition(n.getStart()).line + 1;
  function visit(n, vars, inTest) {
    let nv = vars;
    if (!inTest) {
      if (ts.isForOfStatement(n) && ts.isVariableDeclarationList(n.initializer)) nv = [...vars, ...names(n.initializer.declarations[0].name)];
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && ['forEach', 'map'].includes(n.expression.name.text)) {
        const cb = n.arguments[0];
        if (cb && (ts.isArrowFunction(cb) || ts.isFunctionExpression(cb))) nv = [...vars, ...cb.parameters.flatMap(p => names(p.name))]; }
    }
    const kind = testKind(n);
    if (kind && !inTest && vars.length) {
      const body = n.arguments[n.arguments.length - 1];
      const title = n.arguments[0];
      const c = { assert: 0, branch: 0, label: 0, data: 0 };
      const set = new Set(vars);
      (function walk(m) {
        if (ts.isIdentifier(m) && set.has(m.text) && !(ts.isPropertyAccessExpression(m.parent) && m.parent.name === m)
            && !(ts.isPropertyAssignment(m.parent) && m.parent.name === m)) {
          let p = m, cls = 'data';
          for (; p && p !== n; p = p.parent) {
            if (p === title) { cls = 'label'; break; }
            if (ts.isCallExpression(p) && /qase\.parameters|annotation/.test(p.expression.getText(sf))) { cls = 'label'; break; }
            if (ts.isPropertyAssignment(p) && ['annotation', 'tag'].includes(p.name.getText(sf))) { cls = 'label'; break; }
            if (isAssertCall(p)) { cls = 'assert'; break; }
            if (ts.isIfStatement(p.parent || p) && (p.parent).expression === p) { cls = 'branch'; break; }
            if (ts.isConditionalExpression(p.parent || p) && p.parent.condition === p) { cls = 'branch'; break; }
            if (ts.isSwitchStatement(p.parent || p) && p.parent.expression === p) { cls = 'branch'; break; }
            if (ts.isBinaryExpression(p.parent || p) && ['&&', '||', '??'].includes(p.parent.operatorToken.getText(sf)) && p.parent.left === p) { cls = 'branch'; break; }
          }
          c[cls]++;
        }
        ts.forEachChild(m, walk);
      })(n);
      out.push({ file: path.relative(root, f), line: line(n), kind, vars: vars.join(','), ...c });
    }
    if (kind === 'test') { ts.forEachChild(n, ch => visit(ch, nv, true)); return; }
    ts.forEachChild(n, ch => visit(ch, nv, inTest));
  }
  visit(sf, [], false);
}
// a test inside an already reported describe is covered by it
const res = out.filter(r => !(r.kind === 'test' && out.some(d => d.kind === 'describe' && d.file === r.file && d.line < r.line)));
fs.writeFileSync(process.argv[3], JSON.stringify(res, null, 1));
const k = res.map(r => r.assert ? 'assert' : r.branch ? 'branch' : r.data ? 'data-only' : 'label-only');
console.log('sites', res.length, JSON.stringify(k.reduce((a, x) => (a[x] = (a[x] || 0) + 1, a), {})));
