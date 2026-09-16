# CI, середовища, дані: як працює зараз

Jenkinsfile не в репозиторії; ним володіє інфра-AQA, DevOps у компанії нема. Усе нижче виведено з конфігу, README і коментарів.

## Пайплайни
- **Nightly / dev**: `RUN_ENV=dev`, `configuration.ini` + `.env.dev`, всі тести. Linux-агент: 4 воркери, 3 ретраї. Windows-агент: 9 воркерів, 1 ретрай, відео на падінні.
- **Гілковий smoke**: Jenkins розгортає гілку на IP, експортує лише `LOCAL_SERVER_URL`, запускає `--grep "@smoke|@module"`. `grepInvert` для smoke-only закоментовано 2026-06-17, тому `@module` реально біжить.
- **Повний гілковий**: те саме плюс `ASANA_RUN_ALL_AUTOTESTS=true` з поля задачі в Asana → `configuration_full_branch_run.ini`.
- `.env.*` на Jenkins читаються з `/home/jenkins/shared_dotenv`.
- Результати: консольний лог + Allure JSON; `scripts/parse-test-log.js` парсить лог у HTML; саморобний дашборд показує flaky, wall-clock, machine-time по проектах.

## Docker
`Dockerfile` на базі `mcr.microsoft.com/playwright`, `docker-compose` запускає smoke проти локального стека, 6 воркерів, `shm 2gb`. Allure CLI навмисно не в образі.

## Середовища і дані
- Гілкові середовища: без accounts-мікросервісу, компанії не створюються, використовується снапшот.
- Precorino: рефреш дампу проду раз на 2–4 тижні; автоматизаційні компанії мають пережити рефреш.
- Одна MySQL для тестів, включно з таблицями акаунтів. Пул на воркер, `connectionLimit 3`.
- Швидкий локальний старт: `docker compose run --rm e2e-smoke`.

## Відомі проблеми інфраструктури
- Нестача потужності Jenkins і Docker постійно.
- `LANGUAGE=auto` крутить мову по дню тижня, звіт мову не пише.
- Qase-репортер встановлений, не підключений.
- Три проекти в конфігу не матчать жодного тесту, але логіняться в globalSetup.
