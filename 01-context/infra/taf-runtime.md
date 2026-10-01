---
_width: wide
---
# TAF: як визначається, де і що запускати

Стан на 2026-10-01, гілка `taf/base` (`origin/develop` + локальний коміт із `scripts/run-local.sh` і `test:local-*`). Усі посилання `файл:рядок` на репозиторій `precoro-e2e-playwright`. Значення секретів тут не наводяться, лише імена змінних.

Коротко: **де** визначає одна змінна `RUN_ENV` (env-файл, хости, тюнінг раннера); **що** визначають проекти-компанії (`grep` на тег компанії), CLI-фільтри (`--grep`, `--grep-invert`, шляхи) і Qase scope, що на етапі збору тестів додає `@smoke` / `@unstable`.

## 1. RUN_ENV: куди йде прогін

`playwright.config.ts:12` викликає `resolveRunEnv(process.env.RUN_ENV)`; `read_configs.ts:11` резолвить ту саму назву, тож конфіг і константи не можуть розійтися.

| `RUN_ENV` | Env-файл | Defaults (`run_env.ts`) | Де біжить |
| --- | --- | --- | --- |
| не задано → `dev` (`run_env.ts:29`, `:74-76`) | `.env.dev` (`run_env.ts:32`) | немає | спільне середовище Precorino (`app.precorino.com`), нічний прогін |
| `docker` | `.env.local-stack` (`run_env.ts:27`, `:34`) | `APP_BASE_URL=https://precoro-app`, `API_BASE_URL=https://precoro-app/api`, `MAILPIT_URL=http://precoro-mailpit:8025`, `DATABASE_URL` на контейнер `precoro-mysql:3306`, `IS_DOCKER=true`, `PW_WORKERS=4`, `PLAYWRIGHT_JUNIT_OUTPUT_NAME`, `QASE_SCOPE_URL` (`run_env.ts:35-47`) | раннер у контейнері, локальний стек |
| `docker_host` | `.env.local-stack` | `https://localhost`, `https://localhost/api`, `http://localhost:8025`, MySQL на `127.0.0.1:3306` (`run_env.ts:50-57`) | раннер на хості / в IDE, той самий локальний стек |
| `branch` | `.env.branch`; шукається в корені і в `/home/jenkins/shared_dotenv` (`playwright.config.ts:26`) | лише `QASE_SCOPE_URL` (`run_env.ts:61-64`); `APP_BASE_URL` і `MAILPIT_URL` Jenkins передає сам, бо вони міняються щобілда (`run_env.ts:59-60`) | гілковий сервер Jenkins |

Правила:

- **Пріоритет: shell > `.env`-файл > defaults.** Спершу dotenv (`playwright.config.ts:42`), потім `applyRunEnvDefaults` ставить значення лише туди, де змінна ще `undefined` (`run_env.ts:86-92`, `playwright.config.ts:46-48`). dotenv теж не перезаписує вже задані змінні shell.
- **Невідоме значення — помилка**, не тихий `dev`: `RUN_ENV=dokcer` кидає `Unknown RUN_ENV` (`run_env.ts:66-83`). Порожнє значення = `dev`.
- **Нема env-файлу — помилка**, фолбеку на голий `.env` нема (`playwright.config.ts:29-38`); нечитабельний файл теж падає одразу (`playwright.config.ts:42-45`).
- **`LOCAL_SERVER_URL` виведено з ужитку.** Якщо він заданий, а `RUN_ENV` не `branch`, прогін кидає помилку (`read_configs.ts:22-33`). Jenkins тепер передає `RUN_ENV=branch` + `APP_BASE_URL`.
- `APP_BASE_URL` без дефолту: якщо порожній, `buildConstants` падає (`read_configs.ts:36-41`, `:108-116`). Так само обов'язковий `MAIN_USER_PASSWORD` (`read_configs.ts:118-124`).
- `_isDocker` у конфігу означає саме `RUN_ENV === 'docker'` (`playwright.config.ts:20`); `docker_host` навмисно не вважається docker (видимий браузер, локальна кількість воркерів, `playwright.config.ts:18-19`).

## 2. read_configs → Constants

| Що | Як | Де |
| --- | --- | --- |
| INI | один файл `src/config/ini/configuration.ini`, секції `[app_info]`, `[user_data]`, `[document_links]`, `[management_links]`; зберігає шляхи, не хости | `run_env.ts:9`, `read_configs.ts:81-86` |
| Резолв шляхів | кожне значення, що починається з `/`, стає `${APP_BASE_URL}${value}` у будь-якій секції; абсолютні URL лишаються як є | `read_configs.ts:144-150` |
| Basic auth | `HTTP_AUTH_USER` / `HTTP_AUTH_PASSWORD` вшиваються лише в URL секції `[app_info]`; на `branch` хост застосунку їх не отримує (голий Symfony dev-сервер) | `read_configs.ts:128-137`, `:151-166` |
| `apiBaseUrl` | `API_BASE_URL`, інакше `${APP_BASE_URL}/api`; окремий хост потрібен лише спільним середовищам | `read_configs.ts:43-48` |
| БД | `connection_string` береться лише з `DATABASE_URL`, в INI його нема | `read_configs.ts:170-171` |
| Mailpit | `requireMailPitUrl()` падає, якщо `MAILPIT_URL` не задано, фолбеку нема | `read_configs.ts:50-63` |
| `isSharedEnv` | `RUN_ENV === 'dev'`; гейт для тестів, яким потрібні дані лише спільного середовища (100+ опцій, OCR, історія, білінг) | `read_configs.ts:13-20` |
| Мова | `LANGUAGE` (дефолт `en`); `LANGUAGE=auto` дає ротацію: пн `de`, вт `es`, ср `fr`, решта днів `en`; від мови залежать шляхи xlsx-фікстур | `read_configs.ts:88-96`, `:173`, `:272-308` |

**Гейти `isSharedEnv`** (grep по `src/`, без `read_configs.ts`): 24 виклики `test.skip(!isSharedEnv, ...)`, використання в 19 файлах. Крім skip, `isSharedEnv` міняє таймаути і очікувані дані: `SKELETON_TIMEOUT` (`src/ui/base_page.ts:22`), `SUCCESS_FLASH_TIMEOUT` (`src/ui/web/document_components/common_components.ts:15`), номери рядків в `test_inventory.spec.ts:453-454` тощо. Тобто на `docker`, `docker_host` і `branch` ці 24 тести пропускаються.

## 3. Проекти = компанії

| Параметр | Значення | Де |
| --- | --- | --- |
| Проекти | 41, по одному на тег компанії; кожен має `grep: /@<company>/` | `playwright.config.ts:177-420` |
| `workers` на проект | 1 у кожного: тести однієї компанії ніколи не йдуть паралельно | там само |
| `fullyParallel` | `false`: тести у файлі послідовні | `playwright.config.ts:88` |
| `storageState` | у 37 проектів `.auth/<project>.json`; без нього `spo_company`, `po_from_pr_company`, `matching_company`, `po_receive_company` | `playwright.config.ts:196-215` |
| `.auth` | `AUTH_DIR = <cwd>/.auth`, файл `<project>.json` | `fixtures/auth-dir.ts:11-15` |
| globalSetup | один логін на кожен із 41 проекту послідовно (щоб не ловити 503), окрема сесія на проект навіть при спільному користувачі; fast-login ендпоінт за email, фолбек на UI-форму; існуючий файл перевикористовується, `REFRESH_AUTH=true` форсує перелогін | `global-setup.ts:15-23`, `:45-58`, `:69-83` |
| `forbidOnly` | при `CI` | `playwright.config.ts:91` |

Ретраї і воркери (`playwright.config.ts:94-105`):

| Режим | retries | workers |
| --- | --- | --- |
| `RUN_ENV=docker` | 3 | `PW_WORKERS`, дефолт 4 (також `run_env.ts:41`) |
| `CI`, Linux | 3 | 4 |
| `CI`, Windows | 1 | 9 |
| локально (без `CI`) | 0 | 3 |

`docker` має пріоритет над `CI`. `headless` при docker / `CI` / win32 (`playwright.config.ts:133`).

Таймаути (`src/config/timeouts.ts` у цій гілці нема):

| Таймаут | Значення | Де |
| --- | --- | --- |
| тест | 500 000 мс | `playwright.config.ts:163` |
| action | 60 000 мс | `playwright.config.ts:157` |
| navigation | 60 000 мс | `playwright.config.ts:159` |
| expect | 60 000 мс | `playwright.config.ts:168` |
| globalSetup контекст | navigation 60 с, default 30 с | `global-setup.ts:66-67` |

Репортери (`playwright.config.ts:107-128`): `allure-playwright` (тека `ALLURE_RESULTS_DIR`, дефолт `allure-results`), `html` (не відкривати), `list`, `metrics-reporter` лише при `METRICS` і не на `branch` (`playwright.config.ts:57`), `playwright-qase-reporter` з `mode: 'off'`; вмикається `QASE_MODE=testops` (проект `PTC`, батч 50, без вкладень). Назва Qase-рану `[nightly|fullrun|smoke] <branch> · #<build>` (`playwright.config.ts:59-71`).

Docker-контейнер підміняє репортери на `allure-playwright,html,junit` (`docker-entrypoint.sh:80`), тож там нема `list`, metrics і Qase.

Артефакти:

| Що | Налаштування | Де |
| --- | --- | --- |
| screenshot | `only-on-failure` | `playwright.config.ts:146` |
| video | `retain-on-failure` лише на Windows CI, інакше `off` | `playwright.config.ts:147-150` |
| trace | `off` у конфігу; керується вручну у фікстурі `page`: лише на останній спробі, зберігається при падінні | `playwright.config.ts:151-155` |

## 4. Qase

- **QaseID обов'язковий.** ESLint-правило `local/require-qase-annotation` (рівень `error`) для `src/ui/web/tests/**/*.spec.ts` вимагає `annotation: { type: 'QaseID', ... }` на кожному `test()` / `.skip` / `.fixme` / `.only` / `.fail`, включно з об'єктами з `mergeTests()` / `.extend()`; на `test.describe` анотацію заборонено (`eslint-rules/require-qase-annotation.js:3-7`, `:137-145`; `eslint.config.js:71-85`).
- **Qase scope** (`src/config/qase_scope.ts`):
  - `globalSetup` першим кроком викликає `refreshQaseScope()` (`global-setup.ts:24`): якщо задано `QASE_SCOPE_URL`, тягне JSON `{ "<qaseId>": ["@tag"] }` і пише його в `qase-scope.json` у корені, бо воркери перезавантажують модуль (`qase_scope.ts:5`, `:31-43`).
  - `installQaseScopeTags()` патчить `TestTypeImpl._createTest` / `_describe` і перед збором тестів переписує теги (`qase_scope.ts:65-99`, викликається в `playwright.config.ts:52`).
  - `@smoke` належить Qase: з коду він знімається, ставиться лише зі scope (`QASE_OWNED`, `qase_scope.ts:8`, `:53`). Видати scope може лише `@smoke` і `@unstable` (`QASE_GRANTABLE`, `qase_scope.ts:9`, `:54-56`).
  - `@unstable` прибирає `@smoke` (`qase_scope.ts:58-59`) і робить тест `skip` у будь-якому прогоні, з `--grep` чи без (`qase_scope.ts:90-94`).
  - Нема файлу і нема `QASE_SCOPE_URL` — фіча вимкнена, теги з коду лишаються як є (`qase_scope.ts:23-27`, `:70`). Битий файл або не-2xx відповідь — падіння (`qase_scope.ts:16-21`, `:38`).
- **Хто ставить `QASE_SCOPE_URL`:** defaults `docker` (`run_env.ts:47`) і `branch` (`run_env.ts:63`); `scripts/run-local.sh:29` для `docker_host`. У `dev` (нічний Precorino) його нема, тож уночі scope не застосовується і `@unstable` з Qase не виключає тести.

## 5. Як тести говорять із застосунком

| Канал | Механізм | Де |
| --- | --- | --- |
| UI | Chromium із `storageState` проекту (сесія з globalSetup), `ignoreHTTPSErrors` | `playwright.config.ts:130-145`, `global-setup.ts:83` |
| API | `BaseClient`: заголовки `X-AUTH-TOKEN`, `email`, `X-AUTO-TESTS`; базовий хост `apiBaseUrl` | `src/api/base_service.ts:17-23` |
| API-токен | `BaseClient.create()` бере токен із БД за email: `fos_user_user` → `api_token` (`enable=1`), з очікуванням до 10 с; кеш промісів на email, невдалий запит викидається з кешу | `base_service.ts:42-45`, `:52-65`; `src/data_base/dev_precoro_db.ts:40-49` |
| MySQL напряму | `DataBase` будує пул із `DATABASE_URL` (через `Constants.connection_string`), один пул на рядок підключення на воркер, `connectionLimit: 3` | `src/data_base/db_connection.ts:20-41` |
| Пошта | Mailpit за `MAILPIT_URL` (`requireMailPitUrl`), швидкий список листів `MAILPIT_QUICK_EMAILS_URL` | `read_configs.ts:55-63`, `:421` |

## 6. Рецепти вибору тестів

CLI `--grep` не замінює `grep` проекту, а накладається поверх нього (`docker-entrypoint.sh:35-37`): кожен проект лишається звуженим до своєї компанії.

| Прогін | Команда / змінні | Джерело |
| --- | --- | --- |
| Jenkins гілковий smoke | `RUN_ENV=branch` + `APP_BASE_URL`, `--grep "@smoke\|@<модуль>"` (модуль з Asana-задачі гілки); `--grep-invert` нема | `Jenkinsfile` продукту, не в репо TAF; `01-context/ci-and-envs.md`; `playwright.config.ts:170-172` |
| Jenkins full run | `CI=true npx playwright test --grep-invert "<список нижче>"` | `docker-compose.yml:79-80`, `:107-109` |
| Precorino nightly | усі тести, `RUN_ENV=dev`, без `QASE_SCOPE_URL` | `run_env.ts:32`; `01-context/ci-and-envs.md` |
| `npm run test:local-full` | `scripts/run-local.sh full`: `CI=1`, `RUN_ENV=docker_host`, `QASE_SCOPE_URL` (якщо не задано), `--grep-invert` списку full run | `package.json:10`, `scripts/run-local.sh:25-32` |
| `npm run test:local-smoke` | те саме, але `--grep '@smoke'` без invert | `package.json:11`, `scripts/run-local.sh:33` |
| `docker compose run --rm e2e-smoke` | `RUN_ENV=docker`, `IS_DOCKER=true`, grep за замовчуванням `@smoke` | `docker-compose.yml:7-20`, `docker-entrypoint.sh:38` |
| `docker compose run --rm e2e-full` | `PW_GREP=".*"`, `PW_GREP_INVERT=<список>`, `PW_PATHS=src/ui/web/tests`, `PW_WORKERS` (дефолт 4) | `docker-compose.yml:99-114` |
| `docker compose run --rm e2e-documents` | `PW_GREP=".*"`, `PW_PATHS=src/ui/web/tests/documents` (7 компаній документів) | `docker-compose.yml:49-62` |

Список `--grep-invert` full run (дослівно, `docker-compose.yml:109`, той самий у `scripts/run-local.sh:25`):

```
@unstable|@ocr|@dd_ocr|@google_ocr|@email_preferences|@not_for_isolated_env|@billing_precorino|@control|@ns_company|@qbo_company|@bill_company|@suite_app
```

Змінні `docker-entrypoint.sh`:

| Змінна | Дія | Де |
| --- | --- | --- |
| `PW_GREP` | `--grep`, дефолт `@smoke`; `.*` скасовує smoke-фільтр | `docker-entrypoint.sh:32-38` |
| `PW_GREP_INVERT` | `--grep-invert`, додається лише непорожнім (порожній regex виключив би все) | `docker-entrypoint.sh:40-48` |
| `PW_PATHS` | шляхи через пробіл, передаються через env, щоб `--project=X` не затирав їх | `docker-entrypoint.sh:50-53`, `:63-72` |
| `PW_EXCLUDE` | regex-альтернація імен spec-файлів, вшивається в шлях негативним lookahead; без `PW_PATHS` ігнорується | `docker-entrypoint.sh:55-75` |
| аргументи `docker compose run` | ідуть після фільтрів (`--project=X`, `--last-failed`, явний `--grep` перекриває дефолтний) | `docker-entrypoint.sh:77-80` |

Перед прогоном entrypoint очищає вміст `allure-results` і відмовляється стартувати, якщо не зміг (`docker-entrypoint.sh:15-30`); при `--list` не чіпає. Сесії в контейнері живуть у `./.auth-docker`, не в `./.auth` (`docker-compose.yml:29-31`). Мережа `precoro_stack` = `PRECORO_NETWORK` або `precoro_precoro-local-network` (`docker-compose.yml:145-148`).

## 7. Змінні середовища

Лише імена. Значення в `.env.<середовище>`, шаблон `.env.example`.

| Змінна | Призначення | Обов'язкова? |
| --- | --- | --- |
| `RUN_ENV` | вибір середовища (`dev` / `docker` / `docker_host` / `branch`) | ні, дефолт `dev` |
| `APP_BASE_URL` | хост застосунку, база для шляхів INI | так (на `docker*` з defaults) |
| `API_BASE_URL` | хост API, якщо не `APP_BASE_URL/api` | лише на спільних середовищах |
| `MAILPIT_URL` | інбокс Mailpit | так для тестів із поштою (на `docker*` з defaults) |
| `MAILPIT_QUICK_EMAILS_URL` | перевизначення швидкого списку листів | ні |
| `DATABASE_URL` | рядок підключення MySQL | так для API (токени) і DB-хелперів |
| `MAIN_USER_PASSWORD` | пароль усіх тестових акаунтів | так, без нього падає старт |
| `ACCESS_SUBSTITUTE_USER_PASSWORD` | пароль окремого акаунта substitute | для відповідних тестів |
| `HTTP_AUTH_USER`, `HTTP_AUTH_PASSWORD` | basic auth спільних `*.precorino.com` | на спільних середовищах |
| `GMAIL_USERNAME`, `GMAIL_PASSWORD`, `GMAIL_APP_PASSWORD` | поштові тести через Gmail | для відповідних тестів |
| `AMAZON_FROM_IDENTITY`, `AMAZON_SHARED_SECRET`, `FISHERSCI_SHARED_SECRET` | punchout-інтеграції | для punchout-тестів |
| `QASE_MODE` | `testops` вмикає Qase-репортер (читає сам репортер) | ні, дефолт `off` |
| `QASE_TESTOPS_API_TOKEN` / `QASE_API_TOKEN` (стара назва) | токен Qase TestOps | лише при `QASE_MODE=testops` |
| `QASE_SCOPE_URL` | джерело Qase scope (`@smoke` / `@unstable`) | ні (на `docker` / `branch` з defaults) |
| `LOCAL_SERVER_URL` | виведено з ужитку; з `RUN_ENV != branch` дає помилку | не задавати |
| `CI` | headless, ретраї / воркери CI, `forbidOnly` | ні |
| `IS_DOCKER` | headless у globalSetup | ні (на `docker` з defaults) |
| `PW_WORKERS` | воркери в `docker` | ні, дефолт 4 |
| `REFRESH_AUTH` | `true` форсує перелогін усіх проектів | ні |
| `LANGUAGE` | мова прогону, `auto` = ротація за днем тижня | ні, дефолт `en` |
| `CLEAR_CACHE`, `BETA_TEST_CASES_ENABLED` | прапорці поведінки тестів | ні |
| `METRICS`, `METRICS_DIR`, `GIT_COMMIT`, `GIT_BRANCH` | metrics-репортер (не на `branch`) | ні |
| `ALLURE_RESULTS_DIR` | тека Allure | ні |
| `PLAYWRIGHT_JUNIT_OUTPUT_NAME` | файл junit у контейнері | ні (з defaults `docker`) |
| `PLAYWRIGHT_WORKER_INDEX` | індекс воркера для тек завантажень | ставить Playwright |
| `BUILD_NUMBER`, `BUILD_URL`, `BRANCH_NAME`, `CURRENT_STAGE` | Jenkins: назва і опис Qase-рану, ознака full run | ставить Jenkins |
| `PW_GREP`, `PW_GREP_INVERT`, `PW_PATHS`, `PW_EXCLUDE` | фільтри `docker-entrypoint.sh` | ні |
| `PRECORO_NETWORK` | docker-мережа стека | ні |
| `JENKINS_URL`, `JENKINS_USER_NAME`, `JENKINS_PASS` (або `JENKINS_USER` + `JENKINS_API_TOKEN`) | скрипти тріажу трейсів, не прогін | ні |

Джерела: `.env.example`, grep `process.env` по `src/`, `scripts/`, `playwright.config.ts`, `docker-compose.yml`, `docker-entrypoint.sh`.

## Розбіжності, знайдені під час збору

| Де | Що каже | Як насправді |
| --- | --- | --- |
| `CLAUDE.md` репо:141 | невідомий `RUN_ENV` резолвиться в `dev` | кидає помилку (`run_env.ts:72-80`) |
| `docker-compose.yml:90-92` | наявність `LOCAL_SERVER_URL` дає `branch` | без `RUN_ENV=branch` це помилка (`read_configs.ts:28-33`) |
| `docker-compose.yml:103`, `playwright.config.ts:96-98` | docker-дефолт 6 воркерів | 4 (`playwright.config.ts:100`, `run_env.ts:41`) |
| `playwright.config.ts:93` | "Equivalent to pytest --reruns 1" | 0 / 1 / 3 залежно від режиму |
| `01-context/ci-and-envs.md` | гілковий Jenkins експортує лише `LOCAL_SERVER_URL`; повний гілковий читає `configuration_full_branch_run.ini` | тепер `RUN_ENV=branch` + `APP_BASE_URL`; INI один (`run_env.ts:9`) |

## Локальний стек: сертифікат і 2FA

- `https://localhost` локального стеку має самопідписаний сертифікат. `ignoreHTTPSErrors` з конфігу діє лише на контексти, створені з нього; тест, що сам робить `browser.newContext()`, отримує `self-signed certificate` на API-запитах. `scripts/run-local.sh` задає `NODE_EXTRA_CA_CERTS` на `../precoro/docker/local/caddy/dev.crt` (змінна `LOCAL_STACK_CA`).
- Швидкий логін у `globalSetup` відповідає `409 user_has_2fa` для користувачів з 2FA і переходить на UI-форму; TAF 2FA не підтримує, тож такі проєкти локально падають на сторінці «Authentication code». У seed 2026-09-22 це `approval_regression` і `import_documents_company`.
