// Finds test()/test.describe() declared inside a loop (for-of / forEach / map) in spec files.
const ts = require(process.cwd() + "/node_modules/typescript");
const fs = require('fs'), path = require('path');
const root = process.argv[2];
const files = [];
(function walk(d){ for (const f of fs.readdirSync(d)) { const p = path.join(d,f); const s = fs.statSync(p);
  if (s.isDirectory()) walk(p); else if (p.endsWith('.spec.ts')) files.push(p); } })(root);

const isTestCall = n => ts.isCallExpression(n) && (() => { const e = n.expression;
  if (ts.isIdentifier(e) && e.text === 'test') return 'test';
  if (ts.isPropertyAccessExpression(e) && ts.isIdentifier(e.expression) && e.expression.text === 'test') {
    const m = e.name.text; if (m === 'describe') return 'describe'; if (['only','fixme','skip'].includes(m) && n.arguments.length >= 2 && (ts.isStringLiteral(n.arguments[0]) || ts.isTemplateExpression(n.arguments[0]) || ts.isNoSubstitutionTemplateLiteral(n.arguments[0]))) return 'test'; }
  if (ts.isPropertyAccessExpression(e) && ts.isPropertyAccessExpression(e.expression) && e.expression.name.text === 'describe') return 'describe';
  return null; })();

const rows = [];
for (const f of files) {
  const src = fs.readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true);
  const consts = {}; // name -> array length (top-level or anywhere)
  (function collect(n){ if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name) && n.initializer) {
      let i = n.initializer; while (ts.isAsExpression(i) || ts.isSatisfiesExpression?.(i)) i = i.expression;
      if (ts.isArrayLiteralExpression(i)) consts[n.name.text] = i.elements.length;
      else if (ts.isObjectLiteralExpression(i)) consts[n.name.text] = 'obj:' + i.properties.length; }
    ts.forEachChild(n, collect); })(sf);
  const lenOf = expr => { let e = expr; while (ts.isAsExpression(e)) e = e.expression;
    if (ts.isArrayLiteralExpression(e)) return e.elements.length;
    if (ts.isIdentifier(e) && e.text in consts) return consts[e.text];
    if (ts.isCallExpression(e) && ts.isPropertyAccessExpression(e.expression) && ['entries','values','keys'].includes(e.expression.name.text) && e.arguments[0]) { const v = lenOf(e.arguments[0]); return typeof v === 'string' ? +v.slice(4) : v; }
    if (ts.isPropertyAccessExpression(e) && ts.isIdentifier(e.expression) && e.expression.text === 'Object') return '?';
    return '?'; };
  const describeTitle = [];
  function visit(n, loops, inTest) {
    let kind = isTestCall(n);
    let loopHere = null;
    if (!inTest) {
      if (ts.isForOfStatement(n)) loopHere = { iter: n.expression.getText(sf).slice(0,80), len: lenOf(n.expression), line: sf.getLineAndCharacterOfPosition(n.getStart()).line+1 };
      if (ts.isCallExpression(n) && ts.isPropertyAccessExpression(n.expression) && ['forEach','map'].includes(n.expression.name.text))
        loopHere = { iter: n.expression.expression.getText(sf).slice(0,80), len: lenOf(n.expression.expression), line: sf.getLineAndCharacterOfPosition(n.getStart()).line+1 };
      if (ts.isForStatement(n)) loopHere = { iter: 'for(;;) ' + (n.condition?.getText(sf)||''), len: '?', line: sf.getLineAndCharacterOfPosition(n.getStart()).line+1 };
    }
    const nl = loopHere ? [...loops, loopHere] : loops;
    if (kind && !inTest && loops.length) {
      const t = n.arguments[0]; const title = t ? t.getText(sf).slice(0,140) : '';
      // count test() inside a looped describe
      let inner = 0; if (kind === 'describe') (function c(m){ if (isTestCall(m) === 'test') inner++; ts.forEachChild(m, c); })(n);
      const body = n.getText(sf);
      const qase = [...body.matchAll(/QaseID['"]?,\s*description:\s*([^}\n]+)/g)].map(m=>m[1].trim()).slice(0,3).join(' | ');
      rows.push({ file: path.relative(root, f), line: sf.getLineAndCharacterOfPosition(n.getStart()).line+1, kind, inner, title,
        loops: loops.map(l => `${l.iter}[${l.len}]@${l.line}`).join(' > '), qase, qparams: /qase\.parameters/.test(body) });
    }
    if (kind === 'test') { ts.forEachChild(n, c => visit(c, nl, true)); return; }
    ts.forEachChild(n, c => visit(c, nl, inTest));
  }
  visit(sf, [], false);
}
// drop tests nested inside an already-reported looped describe
const out = rows.filter(r => !(r.kind === 'test' && rows.some(d => d.kind === 'describe' && d.file === r.file && d.line < r.line && r.loops.startsWith(d.loops) )));
fs.writeFileSync(process.argv[3], JSON.stringify(out, null, 1));
console.log('looped sites:', out.length, 'files:', new Set(out.map(r=>r.file)).size, 'describe:', out.filter(r=>r.kind==='describe').length);
