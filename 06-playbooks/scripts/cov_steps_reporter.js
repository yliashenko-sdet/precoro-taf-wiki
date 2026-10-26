// Writes test and step wall-clock intervals (epoch seconds) to steps.jsonl next to the run's results.json,
// one JSON object per line. Used by the T1-32 coverage pilot.
const fs = require('fs');
const path = require('path');

const out =
  process.env.COV_STEPS_FILE ||
  path.join(path.dirname(process.env.PLAYWRIGHT_JSON_OUTPUT_NAME || '/tmp/x'), 'steps.jsonl');
const write = (o) => fs.appendFileSync(out, JSON.stringify(o) + '\n');
const name = (test) => test.titlePath().slice(1).join(' > ');
const qase = (test) => (test.annotations.find((a) => a.type === 'QaseID') || {}).description;
let seq = 0;
const ids = new WeakMap();

class StepsReporter {
  onTestBegin(test, result) {
    write({ k: 'test-begin', test: name(test), qase: qase(test), file: test.location.file, project: test.parent.project()?.name, retry: result.retry, rep: test.repeatEachIndex, t: result.startTime.getTime() / 1000 });
  }
  onStepBegin(test, result, step) {
    ids.set(step, ++seq);
  }
  onStepEnd(test, result, step) {
    if (!['test.step', 'hook', 'fixture'].includes(step.category)) return;
    write({
      k: 'step', test: name(test), retry: result.retry, rep: test.repeatEachIndex, id: ids.get(step),
      parent: step.parent ? (ids.get(step.parent) ?? null) : null,
      cat: step.category, title: step.title, t0: step.startTime.getTime() / 1000, d: step.duration / 1000, err: !!step.error,
    });
  }
  onTestEnd(test, result) {
    write({ k: 'test-end', test: name(test), retry: result.retry, rep: test.repeatEachIndex, status: result.status, t0: result.startTime.getTime() / 1000, d: result.duration / 1000 });
  }
}
module.exports = StepsReporter;
