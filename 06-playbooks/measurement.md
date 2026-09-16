# Вимірюваний результат тижня

Мета: щопонеділка автоматично з'являється звіт, у якому видно, які контрольні лічильники впали і на скільки зменшився machine-time. Дві труби з різними джерелами, один звіт.

## Труба 1. Контрольні лічильники (джерело: код)

### Скрипт

`scripts/debt-counters.ts` → `{ counters: { name: number }, files: { name: { path: count } } }`.

| Лічильник | Спосіб | Область |
| --- | --- | --- |
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

На робочій гілці вже є `src/ui/web/tests/reporters/metrics-reporter.ts` (AUTO-8680): пише `metrics/latest.json`, `summary.md`, `history.jsonl` з executed, flaky, machine-time загалом і по проектах. Не дублювати, а розширити. Цільовий рядок у `history.jsonl`: `{date, build, branch, agent, env, language, executed, failed, flaky, skipped, wallClock, machineTime, perProject: {name: {executed, machineTime, flaky}}, perFile, perTag, top50: [{title, file, project, duration}], prepShare}`.
- `prepShare`: частка тривалості кроків, чиї назви матчать `create|prepar|setup|login|precondition`, до загальної. До міграції на `test.step` рахується з allure-results.

### Правила порівняння

- KPI-серія лише з нічних повних прогонів на одному агенті і середовищі. Гілкові прогони в серію не йдуть.
- Медіана останніх 3 нічних, не один прогін.
- Поряд з абсолютним machine-time завжди machine-time на тест, бо сьют росте.
- Ефект конкретної задачі доводиться точково: у PR записано очікування ("no\_dcf\_company s/test 130 → ≤ 45"), після мержу дашборд підтверджує по `perProject`.

## Труба 3. Навантаження на тест (T0-15)

Навіщо: тривалість залежить від того, наскільки завантажений Precorino, тому вона поганий доказ для розмови про потужності і для приймання API-preparation. Кількість запитів не залежить від навантаження середовища і показує, скільки TAF коштує серверу.

### Де чіпляти
Два джерела, обидва обов'язкові. Якщо рахувати лише браузерні запити, переїзд preparation на API покаже фальшивий виграш: навантаження просто переїде в axios.

**1. Браузер.** Слухач на контексті, поруч із наявними `addInitScript` і трейсом у фікстурі `page` (`base_fixtures.ts:169`). Слухач синхронний і на подіях, які Playwright і так отримує, тому overhead нульовий.

```ts
// helpers/track-load.ts
export type LoadCounters = { browser: number; api: number; byType: Record<string, number> };

export function trackContext(context: BrowserContext, c: LoadCounters, appOrigin: string): void {
  context.on('request', (req) => {
    if (!req.url().startsWith(appOrigin)) return;   // відкинути CDN, аналітику, зовнішні
    c.browser++;
    const t = req.resourceType();
    c.byType[t] = (c.byType[t] ?? 0) + 1;
  });
}
```
Викликати скрізь, де створюється контекст: фікстура `page`, майбутній `asUser`, мультиюзерні тести.

**2. API-клієнт.** Один рядок у `withApiStep` (`src/api/requests.ts:71`), там, де вже логуються запит і відповідь: `counters.api++`.

### Як донести до репортера
Воркер і репортер це різні процеси, тому лічильники передаються через `testInfo`. Анотація дешевша за атач (не пише файл):

```ts
// у тій самій фікстурі, після use()
testInfo.annotations.push({ type: 'load', description: JSON.stringify(counters) });
```
У `metrics-reporter.ts` в `onTestEnd` розпарсити анотацію і додати в `ProjectBucket` поля `browserRequests`, `apiRequests`, як уже робиться з `attemptsMs`. Далі в `latest.json`, `summary.md` і `history.jsonl`.

### Чого не робити одразу
Байти. `request.sizes()` це асинхронний виклик по CDP на кожен запит, на тисячах запитів це відчутно. `content-length` із заголовків відповіді безкоштовний, але є не завжди. Кількості запитів достатньо для розмови про потужності; байти додати пізніше і лише якщо знадобляться.

### Як користуватись
- Цифра нічного прогону: "сьют коштує N запитів до Precorino".
- Пілот API-preparation на одному проекті: та сама цифра до і після, це доказ ефекту, не залежний від завантаженості середовища.
- Приймання задач API-preparation: `requests/test` по проекту в критерії готовності поряд із `s/test`.
- Вхід у розмову про капасіті: розрахунок замість відчуття (питання #15).

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
