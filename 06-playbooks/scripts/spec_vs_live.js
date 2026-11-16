// Compare live GET responses with the 200 schema of the spec. Read-only.
// [SPEC=<spec.json>] node spec_vs_live.js <taf-repo> <out.json>   (SPEC defaults to the TAF snapshot)
const path = require('path');
const fs = require('fs');
const repo = process.argv[2];
require(path.join(repo, 'node_modules/dotenv')).config({ path: path.join(repo, '.env.dev'), quiet: true });
const { createHmac } = require('crypto');
const spec = require(process.env.SPEC || path.join(repo, 'src/api/openapi/precoro-openapi.json'));
const email = 'manual_autotest@qwerty.com';
const headers = {
  'X-AUTH-TOKEN': createHmac('sha256', process.env.MAIN_USER_PASSWORD).update(email).digest('hex'),
  email,
  'X-AUTO-TESTS': '',
  Accept: 'application/json',
};
const api = process.env.API_BASE_URL.replace(/\/$/, '');

const deref = (s) => {
  while (s && s.$ref) s = s.$ref.split('/').slice(1).reduce((o, k) => o[k], spec);
  return s;
};
const kind = (v) => (Array.isArray(v) ? 'array' : v === null ? 'null' : typeof v === 'number' ? 'number' : typeof v);
const specKind = (s) => (s.type === 'integer' ? 'number' : s.type);

function compare(live, schema, at, out, depth = 0) {
  schema = deref(schema);
  if (!schema || depth > 6) return;
  const k = kind(live);
  const alts = schema.anyOf || schema.oneOf;
  if (alts) {
    if (k === 'null') { if (!schema.nullable && !alts.some((a) => deref(a).nullable || deref(a).type === 'null')) out.push({ at, issue: 'null, spec not nullable', spec: 'anyOf' }); return; }
    const branches = alts.map(deref);
    const same = branches.filter((b) => specKind(b) === k);
    const pick = same.sort((a, b) => Object.keys(b.properties || {}).length - Object.keys(a.properties || {}).length)[0];
    if (!pick) { out.push({ at, issue: 'type', spec: branches.map(specKind).join('|'), live: k }); return; }
    return compare(live, pick, at, out, depth);
  }
  const sk = specKind(schema);
  if (k === 'null') {
    if (!schema.nullable && sk) out.push({ at, issue: 'null, spec not nullable', spec: sk });
    return;
  }
  if (sk && sk !== k) {
    out.push({ at, issue: 'type', spec: sk, live: k, liveKeys: k === 'object' ? Object.keys(live).slice(0, 6) : undefined });
    return;
  }
  if (k === 'array' && schema.items) live.slice(0, 50).forEach((el) => compare(el, schema.items, `${at}[*]`, out, depth + 1));
  if (k === 'object') {
    const props = schema.properties || {};
    const declared = Object.keys(props);
    if (!declared.length && !schema.additionalProperties && Object.keys(live).length) {
      out.push({ at, issue: 'object without declared properties', liveKeys: Object.keys(live).slice(0, 8) });
      return;
    }
    const missing = Object.keys(live).filter((x) => !(x in props));
    if (missing.length && declared.length) out.push({ at, issue: 'fields not in spec', fields: missing });
    for (const p of declared) if (p in live) compare(live[p], props[p], `${at}.${p}`, out, depth + 1);
  }
}

async function get(p) {
  const r = await fetch(api + p, { headers });
  return [r.status, await r.json().catch(() => null)];
}

const LISTS = ['/budgets', '/suppliers', '/locations', '/documentcustomfields', '/itemcustomfields', '/invoices', '/purchaseorders', '/requestforproposals', '/items', '/receipts', '/expenses', '/purchaserequisitions'];
const DETAIL = { '/invoices': '/api/invoices/{idn}', '/purchaseorders': '/api/purchaseorders/{idn}', '/requestforproposals': '/api/requestforproposals/{idn}', '/items': '/api/items/{id}', '/receipts': '/api/receipts/{idn}', '/expenses': '/api/expenses/{idn}', '/purchaserequisitions': '/api/purchaserequisitions/{idn}' };

(async () => {
  const report = {};
  const check = async (specPath, url) => {
    const op = spec.paths[specPath]?.get;
    const schema = op?.responses?.['200']?.content?.['application/json']?.schema;
    const [status, body] = await get(url);
    const out = [];
    if (!schema) out.push({ issue: 'no 200 JSON schema in spec' });
    else if (status === 200) compare(body, schema, '$', out);
    const key = `GET ${specPath}`; if (report[key]) { report[key].issues.push(...out); report[key].samples++; } else report[key] = { url, status, issues: out, samples: 1 };
    return body;
  };
  for (const l of LISTS) {
    const body = await check('/api' + l, `${l}?per_page=20`);
    if (DETAIL[l]) for (const first of (body?.data ?? []).slice(0, 5)) {
      const key = DETAIL[l].includes('{id}') ? first.id : first.idn;
      await check(DETAIL[l], `${l}/${key}`);
    }
  }
  const po = report['GET /api/purchaseorders/{idn}']?.url;
  if (po) await check('/api/purchaseorders/{idn}', `${po}?includeGroup[]=relatedPurchaseRequisitions&includeGroup[]=relatedInvoices`);
  await check('/api/reports/config', '/reports/config?include=columnsMetadata');
  for (const v of Object.values(report)) { const m = new Map(); for (const i of v.issues) { const k = i.at + '|' + i.issue + '|' + (i.spec ?? '') + '|' + (i.live ?? ''); const prev = m.get(k); if (prev && i.fields) prev.fields = [...new Set([...prev.fields, ...i.fields])]; else if (!prev) m.set(k, { ...i }); } v.issues = [...m.values()]; }
  fs.writeFileSync(process.argv[3], JSON.stringify(report, null, 1));
  for (const [k, v] of Object.entries(report)) {
    console.log(`${k} [${v.status}] ${v.issues.length} issue(s)`);
    for (const i of v.issues.slice(0, 8)) console.log('   ', JSON.stringify(i).slice(0, 200));
  }
})();
