# Playbook: вимірюваний результат тижня

Мета: щопонеділка автоматично з'являється звіт, у якому видно, які контрольні лічильники впали і на скільки зменшився machine-time. Дві труби з різними джерелами, один звіт.

## Труба 1. Контрольні лічильники (джерело: код)

### Скрипт
`scripts/debt-counters.ts` → `{ counters: { name: number }, files: { name: { path: count } } }`.

| Лічильник | Спосіб | Область |
|---|---|---|
| `allure.` | regex | `src/ui`, крім `requests.ts` |
| `Constants.` | regex | `src` |
| `doLogin(` / `loginAs` / `new LoginPage(` | regex | спеки |
| `db.` | regex | спеки |
| `expect(await` | regex | спеки |
| `waitForTimeout(` / inline sleep | regex | `src` |
| `force: true` / `clickUsingJavascript(` / `dispatchEvent('click'` | regex | `src` |
| `xpath=` | regex | `*_locators.ts` |
| `this.xxxLocators.` | regex | pages |
| локальні `mergeTests(` | regex | спеки |
| `.catch(() => false)` поза `is*/has*/check*` | ts-morph: ім'я методу, що містить catch | pages, components, base |
| `.catch(() => {})` без коментаря над рядком | ts-morph | `src` |
| `precoro_service` імпорти | regex | `src` |

### Baseline і CI
- `debt-baseline.json` у корені репозиторію.
- На кожному PR: `npm run debt:check`.
  - фактичне > baseline → fail, вивід файлів і рядків, де додано;
  - фактичне < baseline → fail з текстом "run `npm run debt:update` and commit" (baseline на main завжди дорівнює правді);
  - будь-яке число в baseline PR > baseline на `origin/main` → fail ("лічильник може лише зменшуватись").
- На мержі в main: рядок `{date, commit, counters}` → `metrics/debt.jsonl`.
- Атрибуція: `git log -- debt-baseline.json` дає список PR, кожен із яких зменшив конкретні лічильники.

## Труба 2. Machine-time (джерело: прогін)

### Емітер
- `reporter: [['json', { outputFile: 'results.json' }], ...]` у всіх прогонах.
- `scripts/run-metrics.ts results.json` → рядок у `metrics/runs.jsonl`:
  `{date, build, branch, agent, env, language, executed, failed, flaky, skipped, wallClock, machineTime, perProject: {name: {executed, machineTime, flaky}}, perFile, perTag, top50: [{title, file, project, duration}], prepShare}`.
- `prepShare`: частка тривалості кроків, чиї назви матчать `create|prepar|setup|login|precondition`, до загальної. До міграції на `test.step` рахується з allure-results.

### Правила порівняння
- KPI-серія лише з нічних повних прогонів на одному агенті і середовищі. Гілкові прогони в серію не йдуть.
- Медіана останніх 3 нічних, не один прогін.
- Поряд з абсолютним machine-time завжди machine-time на тест, бо сьют росте.
- Ефект конкретної задачі доводиться точково: у PR записано очікування ("no_dcf_company s/test 130 → ≤ 45"), після мержу дашборд підтверджує по `perProject`.

## Тижневий звіт
`scripts/weekly-report.ts` щопонеділка (cron у Jenkins) → `metrics/weekly/YYYY-Www.md`:
1. Таблиця лічильників: значення тиждень тому, зараз, дельта, PR, що дали дельту.
2. Machine-time: медіана минулого тижня vs цього, загалом і на тест; по проектах top-5 прискорень і сповільнень.
3. Top movers серед тестів: 10 найбільших прискорень і сповільнень.
4. Flaky: кількість і список нових.

Зведений графік: індекс боргу (кожен лічильник / стартове значення, усереднено; починається з 1.0) і machine-time на тест.

## Розподіл
- TAF: `debt-counters.ts`, `run-metrics.ts`, `weekly-report.ts`, CI-гейт.
- Інфра-AQA: дашборд читає `metrics/*.jsonl` замість консольного логу; `parse-test-log.js` видаляється.

## Обсяг
Лічильники + CI-гейт: 1–2 дні. Обробка JSON-репорту: 1 день. Тижневий звіт: 1 день. Усе у фазі 0.
