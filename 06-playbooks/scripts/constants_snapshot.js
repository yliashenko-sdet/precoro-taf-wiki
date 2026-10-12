/**
 * Зліпок усіх значень `Constants`: ключ → sha256(значення). Значення не друкуються і не
 * зберігаються: серед них паролі і рядок підключення до БД.
 *
 * Навіщо: довести, що перенесення конфігу (T1-01, T1-02) не змінило жодного значення, без
 * повного прогону. Знімається до зміни і після, порівнюються ключі і хеші.
 *
 * Використання (з теки репо TAF):
 *   npx tsc src/config/read_configs.ts --outDir /tmp/cfg-before --module commonjs \
 *       --target es2020 --esModuleInterop --skipLibCheck
 *   cp -r src/config/ini /tmp/cfg-before/ini      # поки INI ще існує
 *   RUN_ENV=dev ENV_FILE=.env.dev NODE_PATH="$PWD/node_modules" \
 *       node constants_snapshot.js "$PWD" /tmp/cfg-before /tmp/before.json
 *   # ...зміни...  те саме в /tmp/cfg-after, далі порівняти два json
 *
 * Знято так T1-01 на чотирьох середовищах: dev, branch, docker, docker_host.
 */
const path = require('path'), fs = require('fs'), crypto = require('crypto');
const root = process.argv[2], out = process.argv[3], file = process.argv[4];
require(path.join(root, 'node_modules/dotenv')).config({ path: path.join(root, process.env.ENV_FILE || '.env.dev') });
// playwright.config.ts робить це після dotenv; для docker/docker_host хости беруться звідси.
const runEnv = require(path.join(out, 'run_env.js'));
runEnv.applyRunEnvDefaults(runEnv.RUN_ENV_TARGETS[runEnv.resolveRunEnv(process.env.RUN_ENV)]);
const { Constants } = require(path.join(out, 'read_configs.js'));
const dump = {};
for (const k of Object.keys(Constants).sort()) {
  // __dirname відрізняється між теками збірки, тож шлях самої збірки нормалізуємо.
  const v = String(Constants[k]).split(out).join('<OUT>');
  dump[k] = crypto.createHash('sha256').update(v).digest('hex').slice(0, 16);
}
fs.writeFileSync(file, JSON.stringify(dump, null, 1));
console.error('ключів знято: ' + Object.keys(dump).length);
