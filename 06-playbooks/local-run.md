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

Скрипт `scripts/run-local.sh` (TAF, коміт `5e2c1994` на `taf/base`) задає те, що запуск через Docker отримує сам:

| Що | Навіщо |
| --- | --- |
| `RUN_ENV=docker_host` | `.env.local-stack` і `https://localhost`. `RUN_ENV=docker` з хоста не працює: імена контейнерів (`precoro-app`, `precoro-mysql`) не резолвляться |
| `CI=1` | headless, 3 ретраї, як у Jenkins |
| `QASE_SCOPE_URL` | Qase додає `@smoke` / `@unstable` за QaseID під час збору тестів; без цього 281 тест, позначений у Qase як `@unstable`, біжить як звичайний |
| `--grep-invert` повного прогону | той самий список, що `e2e-full` у `docker-compose.yml` TAF і повний прогін у `Jenkinsfile` продукту, разом з `@not_for_isolated_env` |

`GREP_INVERT` як змінну середовища читає лише `docker-entrypoint.sh` у контейнері; Playwright напряму її не бачить.

## Як стежити за прогоном

Довгий прогін запускати з репортерами `list` (живий лог), `json` (для порівняння прогонів) і `html` (звіт), лог і звіт складати поза репозиторієм:

```bash
D=~/Work/Precoro/local-runs/<дата>
PLAYWRIGHT_JSON_OUTPUT_NAME=$D/run-1.json PLAYWRIGHT_HTML_OUTPUT_DIR=$D/report-1 PLAYWRIGHT_HTML_OPEN=never \
  npm run -s test:local-full -- --reporter=list,json,html > $D/run-1.log 2>&1
```

| Що | Команда |
| --- | --- |
| Живий перебіг: ✓ пройшов, ✘ впав, число це номер тесту в прогоні | `tail -f $D/run-1.log \| grep --line-buffered -E "✓\|✘"` |
| Звіт після прогону: фільтри, помилки, скріншоти | `npx playwright show-report $D/report-1` |

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

1 059 тестів, 8 воркерів, `npm run test:local-full`, свіжий `prepare-db` перед першим прогоном. Стабільно в обох: 5 падінь `approval_regression` (`test_approval.spec.ts`), уночі 30.09 проходять; вірогідна причина — фікстура `ui_basic_settings_fixtures`, виправлена в `develop` комітом `dc8d56b1`, якого в цій базі нема. Решта (8 тестів) не повторюється між прогонами: шум. Усі локальні падіння й flaky уночі проходять (`01-context/audit/nightly-run-2026-09-30.md`). Артефакти: `~/Work/Precoro/local-runs/2026-10-01/` (`before-*.json`, `report-*`).

Далі «до» на `taf/base` = `origin/develop` (`6a5a219f`) + скрипти (`056c127e`): 1 109 тестів, `~/Work/Precoro/local-runs/2026-10-01-develop/`.

## Стан після стабілізації (2026-10-01)

Контрольний прогін 115 тестів, що впали в першому: з 57 залишкових падінь 51 мали `@not_for_isolated_env`, 4 позначені Qase як `@unstable`, 2 без пояснення. Джерело: `~/Work/Precoro/local-runs/2026-09-30/verify-1.json`, `classify.js`.
