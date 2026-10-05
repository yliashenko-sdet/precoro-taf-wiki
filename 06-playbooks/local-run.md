# Локальний прогін: Precoro у Docker, тести з хоста

Як ганяти сьют TAF з Mac проти локального стеку продукту. Запуск через Docker або Jenkins задає середовище неявно, у командах і compose-файлах; тут зібрано те, що для запуску з хоста треба знати явно. Перевірено 2026-09-30 / 10-01.

## Команди

```bash
cd ~/Work/src/precoro-e2e-playwright
rm -rf .auth                      # після кожного prepare-db
npm run test:local-full           # повний прогін як у Jenkins (1 109 запусків на `develop` 2026-10-01; 1 059 на базі від 28.09)
npm run test:local-smoke          # смоук як на гілці (--grep @smoke, 312 запусків)
npm run test:local-full -- --workers=8 --project=po_company   # додаткові аргументи Playwright
```

Скрипт `scripts/run-local.sh` і два записи в `package.json` закомічені 2026-10-02 у PR #203 (`28db4af6`, гілка `feature/liashenko/quality-gate`); після мержу вони будуть у `develop`. Для гілок, де цього коміту ще нема, копія патчем: `~/Work/Precoro/local-runs/run-local-scripts.patch`, `git apply <patch>`.

| Що | Навіщо |
| --- | --- |
| `RUN_ENV=docker_host` | `.env.local-stack` і `https://localhost`. `RUN_ENV=docker` з хоста не працює: імена контейнерів (`precoro-app`, `precoro-mysql`) не резолвляться |
| `CI=1` | headless, 3 ретраї, як у Jenkins |
| `QASE_SCOPE_URL` | Qase додає `@smoke` / `@unstable` за QaseID під час збору тестів; без цього 281 тест, позначений у Qase як `@unstable`, біжить як звичайний |
| `--grep-invert` повного прогону | той самий список, що `e2e-full` у `docker-compose.yml` TAF і повний прогін у `Jenkinsfile` продукту, разом з `@not_for_isolated_env` |
| `NODE_EXTRA_CA_CERTS` | довіра до самопідписаного сертифіката стеку для тестів з власним `browser.newContext()` |
| `git clean -fqX -- src/downloads` | прибирає завантаження попереднього прогону (F-11); тека схована від git локально через `.git/info/exclude` |

`GREP_INVERT` як змінну середовища читає лише `docker-entrypoint.sh` у контейнері; Playwright напряму її не бачить.

## Як стежити за прогоном

Прогін «після» на поточній гілці запускається з термінала одним шаблоном (з 2026-10-02):

```bash
sh ~/Work/Precoro/local-runs/run-after.sh T1-13    # назва йде в теку <дата>-<назва>
```

Шаблон сам створює теку, на старті друкує готову команду `tail -f` для стеження, шлях до `after.meta` і звіту, і відмовляється стартувати, якщо вже йде інший прогін, `prepare-db` або імпорт seed у контейнері (два одночасні `prepare-db` ламають базу, 2026-10-02). Довгі прогони запускає Yevhen з термінала: фонові команди Claude обмежені ~30 хв.

Кожен прогін лежить у своїй теці поза репозиторієм: `~/Work/Precoro/local-runs/<дата>-<гілка>/`. У ній скрипт прогону (`run-before.sh` для бази, `run-after.sh` для гілки), `*.meta` (коміти TAF і продукту, час старту і кінця), живий лог `before-1.log` або `after-1.log`, результат для порівняння `*.json` і HTML-звіт `report-1/`.

**Критерії прогону «після»** (будь-яка задача, що міняє поведінку тестів):
1. Нових падінь проти бази немає; нові падіння перезапуском відділені від flaky.
2. Зелені тести не повільніші за базу понад шум: `python3 ~/Work/Precoro/local-runs/durations.py <лог бази> <лог гілки>` порівнює сумарний час тестів, що пройшли з першої спроби в обох прогонах. Шум між двома прогонами того самого коду до ±5% (`develop` 2026-10-01: −4,6%); понад +10% це регресія, яку пояснюють і прибирають до мержу. Задача не мусить пришвидшувати, але й не може сповільнювати: T1-13 2026-10-05 дала +61% на зеленому шляху (`Timeouts.probe` 5 s там, де раніше свідомо стояло 0,5–1 s), що виявилось лише цим порівнянням.

Гілку задачі перевіряє **один** повний прогін на хості після свіжого `prepare-db` (рішення Yevhen 2026-10-01; два прогони були потрібні лише для бази, щоб переконатись у стабільності середовища). Нові падіння перезапускаються окремо, щоб відділити flaky.

Приклад на прогоні гілки `feature/liashenko/quality-gate` 2026-10-01:

| Що | Команда |
| --- | --- |
| Живий перебіг: ✓ пройшов, ✘ впав, число це номер тесту в прогоні; `Ctrl+C` зупиняє лише перегляд | `tail -f ~/Work/Precoro/local-runs/2026-10-01-stage-1/after-1.log \| grep --line-buffered -E "✓\|✘"` |
| Скільки пройшло і впало зараз | `grep -c "✓" ~/Work/Precoro/local-runs/2026-10-01-stage-1/after-1.log; grep -c "✘" ~/Work/Precoro/local-runs/2026-10-01-stage-1/after-1.log` |
| Лише падіння | `grep "✘" ~/Work/Precoro/local-runs/2026-10-01-stage-1/after-1.log` |
| Звіт після прогону: фільтри, помилки, скріншоти | `npx playwright show-report ~/Work/Precoro/local-runs/2026-10-01-stage-1/report-1` |

Для іншого прогону замінити теку і назву логу. Сам прогін запускається з репортерами `list` (живий лог), `json` (порівняння) і `html` (звіт); шаблон команди в `run-before.sh` / `run-after.sh` будь-якого прогону.

Test Explorer у VS Code показує лише запуски, зроблені з нього самого; прогін з термінала там не видно. Щоб запускати окремі тести з Explorer проти локального стеку, у `settings.json` робочої теки: `"playwright.env": { "RUN_ENV": "docker_host", "QASE_SCOPE_URL": "https://senana.precorino.com/qase/scope" }`; виключення тегів у фільтрі Explorer: `!@not_for_isolated_env`. Для повного прогону Explorer не підходить: із закриттям VS Code прогін зупиняється.

## Стек продукту

Гайд: `docs/e2e-local-guide.md` у репо продукту. Розгортання з гілки `feature/brynza/docker-jenkinsfile` (інфра-AQA) плюс правки, без яких тести з хоста не працювали. Правки не комітяться (рішення Yevhen, 2026-10-01: пояснення від інфра-AQA, чому цих змінних нема в проєкті, буде пізніше); вони лежать незакоміченими змінами в робочому дереві `~/Work/src/precoro` на `taf/base` і потрібні лише для запуску тестів з хоста, не в Docker:

| Файл (незакомічено) | Що |
| --- | --- |
| `docker/e2e/phpfpm/.env.docker.e2e` | `TEST_API_ENABLED=1`: без нього кожен API-виклик TAF з `X-AUTO-TESTS` редиректиться на `/login` |
| `docker/e2e/phpfpm/.env.docker.e2e` | `ELASTICA_ENABLE_LISTENERS=true`: інакше нове, що створює тест, не потрапляє в Elasticsearch і списки та пошук його не бачать |
| `docker-compose-e2e.yml`, `Makefile.e2e` | Elasticsearch 1 GB (з 400 MB падає на `es-sync` дампа 2026-09-22); `web/uploads/media` на `make up` (без неї падає кожен експорт) |
| `docker/e2e/phpfpm/.env.docker.e2e` | `FRANKENPHP_NUM_THREADS=20` для 8 воркерів (типово 8 потоків) |

Імовірно, у розгортанні інфра-AQA частину цього дає Infisical: контейнер застосунку стартує з секретами `development-docker`, якщо на хості є `infisical login`. Без нього контейнер у режимі `DEGRADED`. Не підтверджено.

Розбіжності гайду з кодом на 2026-10-01:

- `make docker-secrets-sync` не існує з 2026-08-20; `make` мовчки нічого не робить. Робочий шлях: `docker compose ... exec -T precoro-app php bin/infisical-sync.php .env.local`.
- Node на хості 22.23+ (`package.json` продукту, `engines`); фронт збирається на хості (`npm run build`), бо в контейнері нема Linux-біндів `node_modules`.
- Мікросервісів `reports` і `imports` у e2e-стеку нема: експорт звітів і імпорт локально не працюють. Ці тести мають `@not_for_isolated_env` або позначені Qase як `@unstable`.

## Прогони «до»

| Дата | База TAF | Прогін | Пройшли | Впали | Flaky | Skipped | Тривалість |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-01 | `taf/base-2026-09-30` (develop 28.09 + гілка інфра-AQA) | 1 | 986 | 8 | 3 | 62 | 1.2h |
| 2026-10-01 | те саме | 2 | 987 | 5 | 5 | 62 | 1.3h |
| 2026-10-01 | `taf/base` = `develop` `6a5a219f` + незакомічені скрипти (`run-local-scripts.patch`) | 1 | 1 046 | 0 | 1 | 62 | 1.3h |
| 2026-10-01 | те саме | 2 | 1 040 | 0 | 7 | 62 | 1.2h |

1 059 тестів, 8 воркерів, `npm run test:local-full`, свіжий `prepare-db` перед першим прогоном. Стабільно в обох: 5 падінь `approval_regression` (`test_approval.spec.ts`), уночі 30.09 проходять. Причина — середовище, не дані і не тести: користувачі `approval_regression`, `import_documents_company`, `custom_numbering_company` і `close_documents` мають 2FA (так само на Precorino і на Jenkins), а продукт пропускає 2FA лише для IP з `TRUSTED_IPS`. Docker Desktop на Mac передає запити з хоста з `172.64.66.1`, поза діапазонами в e2e-конфігу, тож логін зупиняється на «Authentication code». Локальна незакомічена правка додає цю адресу в `TRUSTED_IPS` (`docker/e2e/phpfpm/.env.docker.e2e`); перевірено: `approval_regression` проходить. Гіпотезу про коміт `dc8d56b1` прогін на `develop` спростував. Решта (8 тестів) не повторюється між прогонами: шум. Усі локальні падіння й flaky уночі проходять (`01-context/audit/nightly-run-2026-09-30.md`). Артефакти: `~/Work/Precoro/local-runs/2026-10-01/` (`before-*.json`, `report-*`).

Далі «до» на `taf/base` = `origin/develop` (`6a5a219f`) + скрипти: 1 109 тестів, `~/Work/Precoro/local-runs/2026-10-01-develop/`. Перша спроба зупинена: нові тести з `develop` (`test_reject`, `test_revise`, `test_send_for_revision`) створюють власний `browser.newContext()` без налаштувань конфігу, і їхні API-запити падають на самопідписаному сертифікаті локального стеку (302 невдалі спроби в `po_from_pr_company`). `scripts/run-local.sh` тепер задає `NODE_EXTRA_CA_CERTS` на сертифікат стеку (`../precoro/docker/local/caddy/dev.crt`, перевизначається `LOCAL_STACK_CA`); на Jenkins і Precorino сертифікати справжні, проблеми нема.

**База «до» для гілок задач: `taf/base` на `develop` `6a5a219f`**, 1 109 тестів, 0 падінь у двох прогонах, шум 1–7 flaky. Перед прогонами додано довіру до сертифіката стеку і адресу хоста Docker Desktop у `TRUSTED_IPS` (2FA). Flaky прогону 2: три поспіль о 18:09–18:10 збіглися з відключенням Mac від мережі (`net::ERR_NETWORK_CHANGED`); `Revise receipt with warehouse` (`items_company`) flaky в обох прогонах і на старій базі — кандидат у справжній flaky. Усі flaky уночі 30.09 проходять. Артефакти: `~/Work/Precoro/local-runs/2026-10-01-develop/` (`before-*.json`, `report-*`); зупинені спроби в `attempt-1/`, `attempt-2/`.

## Прогони «після»

Порівнюються з базою «до» на `taf/base` (`develop` `6a5a219f`): 0 падінь у двох прогонах, 1–7 flaky.

| Дата | Гілка | Пройшли | Впали | Flaky | Skipped | Тривалість | Висновок |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-01 22:52 – 00:04 | `feature/liashenko/quality-gate` (`de9243b0`: T0-01, T0-02, T0-13 + мерж `develop` `6a5a219f`) | 1 031 | 14 | 2 | 62 | 1.2h | нових падінь від гілки нема: усі 14 це `budget_limit_company`, тести валют бюджету, що почали падати о 00:00 за Києвом (F-12); ті самі 14 окремо о 00:05 падають однаково на `develop` і на гілці. Flaky: `Revise receipt with warehouse` (як «до»), `Create/edit item, verify is manual update [Expense]` (новий, пройшов на ретраї) |
| 2026-10-02 15:37 – 16:51 | `feature/liashenko/T1-12-value-assertions` (`d20b60c7`: T1-12 + мерж `feature/liashenko/quality-gate` `02a3561e`) | 1 027 | 0 | 6 | 62 | 1.2h | база «до» — прогін гейта 2026-10-01 (рішення Yevhen 2026-10-02). Нових падінь 0; 14 падінь бази (F-12, північ) тут проходять. 6 flaky: `Revise receipt with warehouse` (як завжди) і 5 нових, жоден не на перевірці, яку змінила T1-12 (BPO `fillInValidityPeriod`, `expectStatusApproved`, скелетон після Create, API-ціна в `test_items`, пошук інвойсу в БД). 14 тестів менше, ніж у базі: Qase між прогонами дав їм `@unstable` (QaseID 3043, 4589, 1971, 1168, 3108, 6090; `qase-scope.json` 2026-10-02). 11 змінених T1-12 спек локально не збираються (OCR, імпорт, експорт, інтеграції, `control`, кастомна нумерація, email-налаштування, `icf_dcf`) |
| 2026-10-05 11:33 – 12:51 UTC (`TZ=UTC`) | `feature/liashenko/T1-13-sleeps-timeouts` (`7b2907d0` + варіант А, закомічено як `0c2fde40`; база `develop` `24b0244e`) | 1 073 | 0 | 9 | 62 | 1.3h | нових падінь 0; зелені тести +1.3% проти T1-12 02.10 (708 спільних, медіана 1.00, шум ±5%). 9 flaky: 2 відмови API в підготовці (403, 400), 7 таймаутів у рядках, яких T1-13 не змінювала; `Revise receipt with warehouse` як завжди. Попередній прогін T1-13 (до варіанта А, 05.10 00:38–02:58) дав 92 падіння: 78 від часового поясу (F-12), 12 від T1-13, і +61% на зеленому шляху; розбір у картці T1-13 |

Прогін, що перетинає північ за Києвом, ламає тести з валютою і бюджетом (F-12): стартувати так, щоб закінчився до 00:00. Артефакти: `~/Work/Precoro/local-runs/2026-10-01-stage-1/` (`after-1.json`, `report-1`, `check-base.json`, `check-branch.json`).

## Стан після стабілізації (2026-10-01)

Контрольний прогін 115 тестів, що впали в першому: з 57 залишкових падінь 51 мали `@not_for_isolated_env`, 4 позначені Qase як `@unstable`, 2 без пояснення. Джерело: `~/Work/Precoro/local-runs/2026-09-30/verify-1.json`, `classify.js`.
