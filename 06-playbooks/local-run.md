# Локальний прогін: Precoro у Docker, тести з хоста

Як ганяти сьют TAF з Mac проти локального стеку продукту. Запуск через Docker або Jenkins задає середовище неявно, у командах і compose-файлах; тут зібрано те, що для запуску з хоста треба знати явно. Перевірено 2026-09-30 / 10-01.

## Команди

```bash
cd ~/Work/src/precoro-e2e-playwright
rm -rf .auth                      # після кожного prepare-db
npm run test:local-full           # повний прогін як у Jenkins (1 059 запусків на 2026-10-01)
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

## Стек продукту

Гайд: `docs/e2e-local-guide.md` у репо продукту. Розгортання з гілки `feature/brynza/docker-jenkinsfile` (інфра-AQA) плюс локальна `taf/base` з правками, без яких тести з хоста не працювали:

| Коміт (`taf/base`, precoro) | Що |
| --- | --- |
| `eae8a2ffa44` | `TEST_API_ENABLED=1`: без нього кожен API-виклик TAF з `X-AUTO-TESTS` редиректиться на `/login` |
| `e76f056dd07` | `ELASTICA_ENABLE_LISTENERS=true`: інакше нове, що створює тест, не потрапляє в Elasticsearch і списки та пошук його не бачать |
| `2662b53ed51` | Elasticsearch 1 GB (з 400 MB падає на `es-sync` дампа 2026-09-22); `web/uploads/media` на `make up` (без неї падає кожен експорт) |
| `4515eadc139` | `FRANKENPHP_NUM_THREADS=20` для 8 воркерів (типово 8 потоків) |

Імовірно, у розгортанні інфра-AQA частину цього дає Infisical: контейнер застосунку стартує з секретами `development-docker`, якщо на хості є `infisical login`. Без нього контейнер у режимі `DEGRADED`. Не підтверджено.

Розбіжності гайду з кодом на 2026-10-01:

- `make docker-secrets-sync` не існує з 2026-08-20; `make` мовчки нічого не робить. Робочий шлях: `docker compose ... exec -T precoro-app php bin/infisical-sync.php .env.local`.
- Node на хості 22.23+ (`package.json` продукту, `engines`); фронт збирається на хості (`npm run build`), бо в контейнері нема Linux-біндів `node_modules`.
- Мікросервісів `reports` і `imports` у e2e-стеку нема: експорт звітів і імпорт локально не працюють. Ці тести мають `@not_for_isolated_env` або позначені Qase як `@unstable`.

## Стан після стабілізації (2026-10-01)

Контрольний прогін 115 тестів, що впали в першому: з 57 залишкових падінь 51 мали `@not_for_isolated_env`, 4 позначені Qase як `@unstable`, 2 без пояснення. Джерело: `~/Work/Precoro/local-runs/2026-09-30/verify-1.json`, `classify.js`.
