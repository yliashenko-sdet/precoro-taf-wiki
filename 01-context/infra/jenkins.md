---
_width: wide
---
# Jenkins: як ганяються тести

Довідка для автоматизації: що саме робить Jenkinsfile продукту, коли запускаються тести, що валить білд, а що лише попереджає. Стан на 2026-10-01.

**Позначення джерел** (усі посилання у форматі `файл:рядок`):

| Скорочення | Що це |
| --- | --- |
| `JF` | `precoro` `origin/Develop:Jenkinsfile`, поточний гілковий пайплайн (останній коміт у файлі 2026-09-23) |
| `JFd` | `precoro` `feature/brynza/docker-jenkinsfile:Jenkinsfile`, новий Docker/K8s пайплайн інфра-AQA (останній коміт 2026-09-30) |
| `MK`, `CI.yml` | `Makefile.e2e` і `docker/e2e/docker-compose-ci.yml` з тієї ж Docker-гілки |
| `pw.config`, `run_env`, `compose`, `entrypoint` | TAF `origin/develop`: `playwright.config.ts`, `src/config/run_env.ts`, `docker-compose.yml`, `docker-entrypoint.sh` |

## 1. Два Jenkins

| Інстанс | Що ганяє | Хто власник | Джерело |
| --- | --- | --- | --- |
| **qa** | Нічні прогони на Precorino, усі тести, `RUN_ENV=dev` | QA, змінюється без узгодження з розробкою | `ci-and-envs.md:10`, `:31` |
| **dev** | Гілкові прогони на PR (smoke + модуль, full run) і робота AQA; на ньому живе `Jenkinsfile` нижче | Спільний із розробкою; зміни в Jenkinsfile з апрувом девів | `ci-and-envs.md:11` |

Жоден із них не тригериться змінами в репозиторії TAF (`ci-and-envs.md:12`). Тести з TAF пайплайн клонує сам, гілку обирає за гілкою продукту (див. §2).

## 2. Пайплайн на `Develop` (`JF`)

Multibranch-джоба, `agent any` (`JF:10`), тобто Jenkins-нода з локальними Redis, PHP, Node і `symfony` CLI. Опції `parallelsAlwaysFailFast`, `disableConcurrentBuilds` (`JF:18-19`).

**Тригери.** Оновлення PR у Bitbucket (`bitBucketTrigger`, `JF:32`) і подія `comment_resolved` через Generic Webhook Trigger (`JF:48`). На approve не тригериться. Ручний параметр `ONLY_START_SERVER` піднімає сервер гілки для ручного дебагу (`JF:23`).

**Прапорці, що керують `when`:** `mustBeSkipped` (гейт вирішив не ганяти), `onlyStartServer`, `runFullRunAnyway` (ганяти лише full run), `ONLY_HC_CHANGED` (змінено лише `src/Command/HealthCheck/`), `FULL_RUN_ENABLED`.

### Стейджі по порядку

| # | Стейдж | Що робить | Коли пропускається | Падіння |
| --- | --- | --- | --- | --- |
| 1 | `🚦 Trigger gate (draft check)` `JF:64` | Тягне стан PR з Bitbucket. Рішення: немає open PR → skip (`:111`); 429 від API → fail-open, білдимо (`:109`); перший білд або READY → **clean-gate** `checkPrCleanForTests` (`:144`, `:194`, тіло `:1747`): CodeRabbit (або Arbiter для авторів, яких CodeRabbit не рев'ює) зелений на HEAD і всі треди вирішені; DRAFT → skip (`:152`); коміт уже зелений → SUCCESS без тестів (`:159`), але якщо в назві PR є `-full-run` і full run ще не проходив, ганяє лише full run (`:168`). Гасить чергу дублів гілки | `ONLY_START_SERVER` обходить гейт | Skip дає `NOT_BUILT` або зберігає `SUCCESS`, якщо коміт уже був зелений (`skipBuildResult`, `:1824`) |
| 2 | `Auto update from source branch` `JF:220` | `git merge --no-commit --no-ff` з source-гілки: `feature/` ← `Develop`, `bugfix/` ← `release`, `hotfix/` ← `master` (`:1166-1171`) | skip, server mode (для нього окремий стейдж `🔄 … (Server mode)` `:257`) | **Валить** при конфлікті (`:237`), `MERGE_CONFLICT=true` |
| 3 | `Check Jenkinsfile Consistency` `JF:290` | Чи нема в source-гілці комітів у `Jenkinsfile`, яких нема в гілці | skip, server mode | Лише **попередження**: `JENKINSFILE_OUTDATED=true` (`:1273`), рядок у Slack |
| 4 | `Detect Changed Files` `JF:307` | Diff від merge-base: `ONLY_HC_CHANGED` (`:332`), `ASSETS_JS_CHANGED` (`:336`) | skip, server mode | Лише при помилці git |
| 5 | `🧹 Clean Sentry Issues` `JF:345` | Резолвить усі unresolved issues гілки до будь-якої збірки (див. §4) | skip, server mode | **Попередження**, помилка ковтається (`:358`) |
| 6 | `Prepare project` `JF:363` | Чистить кеші, копіює `.env.local`, `.env.test.local`, `phpunit.xml` зі спільного каталогу ноди (`:384-386`), `composer install --no-scripts` через `infisical-run.php` (`:407`), JWT keypair, `translain:pull:all`, `cache:clear` (`:416-420`) | `mustBeSkipped && !runFullRunAnyway` | **Валить** |
| 7 | `🔐 Validate Env Variables` `JF:430` | Порівнює ключі `.env` з тим, що дають Infisical + `.env.local`; відсутні ставить з дефолтів `.env` | як 6 | Лише **попередження** (`:468`) |
| 8 | `Prepare JavaScript` `JF:475` | `prepareJavaScript` (`:2328`): `npm ci`, `translain:pull:js`, `npm run build-ci` | як 6 | **Валить** |
| 9 | `🔗 Detect Asana task & module from PR` `JF:491` | Шукає ID задачі Asana в назві й описі PR (`:1279`), читає кастомне поле `Module*` (`:1355`), перетворює в snake_case → `ASANA_MODULE`. Окремо: `-full-run` у назві PR → `FULL_RUN_ENABLED=true` (`:519`) | skip, server mode, `ONLY_HC_CHANGED` | Лише **попередження** (API Asana з ретраями, помилки ковтаються) |
| 10 | `Prepare Database` `JF:528` | БД на гілку: `db_<branch>` (`:544`) на спільному MySQL з `SHARED_DATABASE_URL`; дописує `DATABASE_URL` тощо в кінець `.env.local`; drop → create (`:573-576`) → імпорт seed `autotests_seed_2026-09-22.sql.gz` через `precoro:ImportSeedCommand` (`:582-584`) → міграції → швидкий ES-sync контейнером sync-service (`:591`, тіло `:2096`, починається з `fos:elastica:reset`) | skip без full-run, server mode; при `runFullRunAnyway` seed і ES-sync тут не робляться (їх робить full run) | **Валить** |
| 11 | `Unit Tests` `JF:596` | Лише якщо змінено `assets/js/`: `npm run check:ci` (JS unit + type check) (`:608`). PHP unit-тести закоментовані | skip, server mode | **Валить** |
| 12 | `Select Redis DB` `JF:639` | Бере вільний Redis DB 1–15 локом у db0 на 2 год, `FLUSHDB`, пише `REDIS_DSN` в `.env.local` | як 6 | **Валить**, якщо вільних нема (`:679`) |
| 13 | `Symfony server` `JF:693` | **Лише для `ONLY_START_SERVER`**: міграції, `fos:elastica:populate`, `symfony server:start`, `input` чекає ручного завершення (`:740`), потім ставить SUCCESS-статуси в Bitbucket | у звичайних білдах завжди | — |
| 14 | `Test End-to-End` `JF:758` | Стартує `symfony server:start -d --no-tls`, URL з виводу → `LOCAL_SERVER_URL` (`:776`), далі `runE2ETests` (`:1467`). `feature/`, `bugfix/` → Playwright: клон TAF (`develop`; `bugfix/` → `release`; `hotfix/` → `main`), `withEnv RUN_ENV=branch`, `APP_BASE_URL=${LOCAL_SERVER_URL}` (`:1585-1586`), `npm ci`, `playwright install chromium`, `CI=true npx playwright test --grep "@smoke\|@<module>\b"` (`:1600`, `:1607`); без модуля лише `@smoke`. `hotfix/` → старий Python-репо, `pytest -m "smoke or <module>"` (`:1573`) | skip, server mode, `ONLY_HC_CHANGED` | **Валить**; при `-full-run` ставить Bitbucket-статус `smoke-run` FAILED |
| 15 | `🚨 Check Sentry Issues After Tests` `JF:789` | `checkSentryIssues(branch, 'after_tests')` | як 14 | **Валить**, якщо є unresolved issues (`:802`) |
| 16 | `🔍 Health Check after tests` `JF:807` | `bash src/Command/jenkins_health_check_command.sh` (`:2191`), читає `health_check_results.log` і `critical_summary.log`; `CRITICAL` або `[HC]` → `HEALTH_CHECK_FAILURE=true` | skip, server mode, Sentry вже знайшов issues. **Не** пропускається при `ONLY_HC_CHANGED` | Сам **не валить** (`returnStatus: true`) |
| 17 | `🚨 Check Sentry Issues After Health Check` `JF:821` | `checkSentryAfterHealthCheck` (`:2223`). Після успіху ставить Bitbucket `smoke-run` SUCCESSFUL або затирає застарілий `full-run` як `Full Run Tests (skipped)` (`:838`) | як 16 | **Валить** при issues після HC або при впалому HC без issues (`HC_FAILED_NO_SENTRY`, `:2258`) |
| 18 | `🔄 Full Run Tests` `JF:844` | Лише якщо `FULL_RUN_ENABLED` (тобто `-full-run` у назві PR) і попередні гейти чисті. `runFullTests` (`:1940`): пропуск, якщо `full-run` для коміту вже SUCCESSFUL; Bitbucket INPROGRESS; `FLUSHDB`; drop/create БД, seed, міграції, ES-sync; сервер, якщо smoke не ганявся; `CI=true npx playwright test --grep-invert "<список нижче>"` (`:2018`) | `!FULL_RUN_ENABLED`, `ONLY_HC_CHANGED`, будь-який Sentry/HC фейл раніше | **Не валить білд**: білд лишається зеленим, Bitbucket `full-run` FAILED, повідомлення в канал, PR → Draft (`:2025-2049`) |
| 19 | `🚨 Check Sentry Issues After Full Run` `JF:862` | `checkSentryIssues(branch, 'after_tests')` | як 18, плюс `FULL_RUN_FAILED` | **Валить** при issues (`:880`) |
| 20 | `Cleanup` `JF:885` | `runCleanup` (`:2264`): `rm var/log` (3 спроби), drop гілкової БД, DELETE ES-індексів `*_<suffix>` | лише при повному skip | Помилки ES і `var/log` ковтаються; drop БД може впасти |
| post | `always` / `failure` / `success` `JF:898-952` | `always`: публікує Allure, звільняє Redis DB. `failure`: PR → Draft (`:925`), повідомлення в канал (`:927`), DM актору і автору PR. `success`: DM, крім білдів «коміт уже зелений» (`:940`) | — | — |

**Список `--grep-invert` full run** (`JF:2018`, той самий у `compose:109`):
`@unstable|@ocr|@dd_ocr|@google_ocr|@email_preferences|@not_for_isolated_env|@billing_precorino|@control|@ns_company|@qbo_company|@bill_company|@suite_app`

**Умова full run.** У коді full run вмикає лише `-full-run` у назві PR (`JF:165`, `:519`) і повторний білд зеленого коміту з тим самим прапорцем (`runFullRunAnyway`, `:168`). Поля Asana `ASANA_RUN_ALL_AUTOTESTS` і `configuration_full_branch_run.ini`, описаних у `ci-and-envs.md:33`, у жодному з двох Jenkinsfile нема (grep: 0 збігів). Asana дає лише модуль для smoke.

**Що валить білд, а що лише попереджає**

| Валить (червоний білд, PR → Draft) | Лише попередження або ковтається |
| --- | --- |
| Конфлікт авто-мержу; будь-який `sh` у Prepare project / JS / Database; `npm run check:ci`; немає вільного Redis DB; падіння smoke; Sentry issues після smoke, HC або full run; впалий HC без Sentry | Застарілий Jenkinsfile; відсутні env-змінні; помилка Sentry clean; Asana API або відсутній модуль; **падіння full run** (лише статус Bitbucket `full-run` FAILED + Slack + Draft); ES- і log-cleanup |

## 3. Docker/K8s пайплайн інфра-AQA (`JFd`): відмінності

Ідея: кожен білд піднімає власний Docker-стек (моноліт + e2e + CI-оверлей) у pod-і Kubernetes, тому паралельні білди гілок не ділять БД, Redis і ES. Інші гілки працюють за старим файлом, бо multibranch бере Jenkinsfile з самої гілки (`JFd:12-13`).

| Стейдж `JF` | У `JFd` | Різниця |
| --- | --- | --- |
| `agent any` | `agent { kubernetes { inheritFrom 'docker-dind' } }` `JFd:14-21` | Pod на DOKS з docker-in-docker; контейнер за замовчуванням `docker` |
| — | **новий** `Pod bootstrap: CLI tools` `JFd:71` | `apk add` bash, make, git, curl, compose, aws-cli, JRE (для Allure); SSH-ключ із credential `jenkins id_ed25519` (`:82`) |
| `ONLY_START_SERVER`, `🔄 … (Server mode)`, `Symfony server` | **прибрано** `JFd:2-4` | Режиму ручного сервера нема; `onlyStartServer` лишився константою `false` |
| Trigger gate … Clean Sentry, Detect Asana | ті самі `JFd:95-349`, `:365` | Логіка гейта, авто-мержу, Sentry і Asana без змін |
| `Prepare project` | `JFd:350` | Лише `mkdir`; збірка переїхала в контейнер |
| `🔐 Validate Env Variables`, `Prepare JavaScript`, `Select Redis DB` | **прибрано** | JS збирається в `ci-build`; Redis свій у стеку |
| `Prepare Database` | `Prepare Docker stack & DB` `JFd:402` → `prepareDockerStack` `:1178` | Логін у приватний DO registry (`do-registry`); TLS-сертифікати (`generate-certs-ci.sh`); seed з приватного S3-бакета (credential `s3`) замість файлу на ноді (`:1204`); `compose up` з профілями `minio`, `mailpit`, `elasticsearch` (`:1217`) і власне очікування health до 60×5 с (`:1228`); `.env.local` з Infisical **усередині** `precoro-app` під окремою identity `infisical-e2e-env`, середовище `e2e-tests` (`:1254-1260`); `make -f Makefile.e2e ci-build` (`:1266`, `MK:110`: composer, npm ci, JWT, assets, translations, `npm run build`, `cache:clear`); `make prepare-db` (`:1276`, `MK:174`: drop, create, seed, міграції, `es-sync`, `cache-clear`) |
| — | ізоляція білда `JFd:1140-1154` | `COMPOSE_PROJECT_NAME=e2e_<branch>_<build>`, власні мережі, усі хост-порти `=0` (випадкові); `GIT_BRANCH` прокидається в контейнер для Sentry-тегу (`:1148`, `CI.yml`) |
| `Unit Tests` | `JFd:413` | `npm run check:ci` через `compose exec precoro-app` |
| `Test End-to-End` | `JFd:435` → `runPlaywrightDocker('smoke')` `:1282` | Сервер не стартує (бекенд доступний за ім'ям сервісу). Клон TAF **запінено** на `feature/brynza/docker-updates` (`:1293`, TODO повернути мапінг). `.env.local-stack` із secret file `e2e-env-local-stack` (`:1316`). Запуск: `docker compose run --rm -e CI=true -e REFRESH_AUTH=true e2e-smoke [--grep "@smoke\|@<module>\b"]` (`:1323`); у контейнері `RUN_ENV=docker` (`compose:13`). Архівує `playwright-report/**`, `test-results/**` (`:1332`) |
| `🔍 Health Check` | `JFd:479` | Той самий скрипт через `compose exec -T precoro-app` (`:1351`) |
| `🔄 Full Run Tests` | `JFd:516` → `runFullTestsDocker` `:1382` | Перезаливає БД `make prepare-db` (`:1398`), потім сервіс `e2e-full` (`:1300`), у якого `PW_GREP=".*"` і `PW_GREP_INVERT` з тим самим списком (`compose:99-109`). Поведінка при падінні та сама: білд зелений, статус + Slack + Draft |
| `Cleanup` | `JFd:557` + `post.always` `:577` | `teardownE2EDocker` (`:1430`): збирає логи стеку й `var/log` в артефакти, `compose down -v` (`:1444`). Drop БД на спільному MySQL і чистка ES-індексів більше не потрібні |
| `post` | `JFd:570-612` | Те саме, плюс страховочний teardown |

Ретраї й воркери в Docker: `retries: 3`, `workers = PW_WORKERS ?? 4` (`pw.config:94`, `:99-100`; дефолт `PW_WORKERS=4` у `run_env:41`, для `e2e-full` теж 4, `compose:105`). Коментарі в `pw.config:15`, `:96-98` (про 2 ретраї і 6 воркерів) застаріли. Нативний Linux CI: 3 ретраї, 4 воркери; Windows CI: 1 ретрай, 9 воркерів (`pw.config:94`, `:101-105`).

## 4. Sentry-гейт

Організація Sentry `precoro-u9`, два проєкти: бекенд і фронтенд (`getSentryProjectIds`, `JF:2492`). Токен із Jenkins credential `sentry-auth-token` (`JF:2439`, `:2504`). У `JFd` функції ідентичні (`JFd:1779`, `:1869-1984`).

Запит в усіх функціях: `query=git_branch:<branch> is:unresolved` (`JF:2450`, `:2512`). Тег `git_branch` ставить сам застосунок (SentryService) з env `GIT_BRANCH`; у Docker його прокидає `CI.yml`.

| Функція | Де викликається | Що робить | Валить? |
| --- | --- | --- | --- |
| `cleanSentryIssuesForBranch` `JF:2436` | `🧹 Clean Sentry Issues` | GET issues гілки → PUT `status: resolved` по ID, в обох проєктах. Мета: старі issues гілки не валять новий білд | Ні, помилка ковтається |
| `checkSentryIssues(branch, stage)` `JF:2533` (через `fetchSentryIssueLines` `:2502`) | `🚨 … After Tests` (`:799`), `🚨 … After Full Run` (`:877`) | Збирає `• title: permalink`; ставить `SENTRY_ISSUES_FOUND_AFTER_TESTS` або `_AFTER_HC` і посилання для Slack | Так, стейдж робить `error` при непорожньому списку |
| `checkSentryAfterHealthCheck` `JF:2223` | `🚨 … After Health Check` | Якщо HC упав: чекає 10 с і до 3 спроб з паузою 5 с (`:2233`); інакше одна перевірка | Так: issues → `error`; HC упав, а issues нема → `HC_FAILED_NO_SENTRY`, `error` |

Крім гейта, при будь-якому фейлі `sendFailureNotification` best-effort дописує в повідомлення Sentry issues, пійманих за прогін (`JF:1444-1453`).

## 5. Qase у CI

| Факт | Джерело |
| --- | --- |
| `QASE_MODE` / `testops` не задається в жодному Jenkinsfile (`JF`, `JFd`, `JenkinsfileCheckTests`, `JenkinsfilePHPStan`, `JenkinsfileReview`, `JenkinsfileScheduledDeploy`), у `MK` і `CI.yml` теж: grep `qase\|QASE_MODE\|testops` дає 0 збігів | grep |
| Репортер у конфігу з `mode: 'off'`; CI мав би вмикати його через `QASE_MODE=testops`. Значить, на гілкових білдах Qase працює лише якщо `QASE_MODE` прийде з `.env.branch` у спільному каталозі ноди (у репо не видно) | `pw.config:115-127` |
| У Docker-шляху entrypoint явно задає `--reporter=allure-playwright,html,junit`, тож qase-репортер там не працює навіть із `QASE_MODE` | `entrypoint:80` |
| Назва рану: `[<scope>] <BRANCH_NAME> · #<BUILD_NUMBER>`, де scope = `nightly`, якщо `RUN_ENV` не `branch`; `fullrun`, якщо `CURRENT_STAGE` містить «full run» або в аргументах є `--grep-invert`; інакше `smoke`. Опис рану: посилання на білд і Allure. Без `BUILD_NUMBER` назва не задається | `pw.config:59-71` |
| Окремо від репортера: `QASE_SCOPE_URL` (за замовчуванням для `branch` і `docker`) дає `installQaseScopeTags`, який за QaseID проставляє `@smoke`/`@unstable` | `run_env:47`, `:61-64`; `pw.config:52` |

Узгоджується з `ci-and-envs.md:72`: «Qase-репортер встановлений, не підключений».

## 6. Slack

| Подія | Куди | Джерело |
| --- | --- | --- |
| Білд упав (`post.failure`) | **Канал** через incoming webhook (`sendFailureNotification`). Канал у коді не названо, лише вебхук; за форматом постів це `#jenkins-failed-builds` | `JF:927`, `:1396-1465` |
| Full run упав (білд зелений) | **Канал**, той самий вебхук, заголовок `🔄 Full Run Failed` | `JF:2034` |
| Будь-який фейл | DM актору і автору PR (мапа Bitbucket-ім'я → Slack ID у файлі) | `JF:928-933`, `:1000` |
| Успіх | DM актору і автору, крім білдів «коміт уже зелений» | `JF:940-950` |
| Full run пройшов або впав | Додатково DM інфра-AQA | `JF:2024`, `:2042` |

Заголовок посту в канал залежить від причини (`JF:1417-1437`): `[SENTRY ISSUES AFTER TESTS]`, `[HC]` (Sentry після HC), `[HC FAILED]`, авто-мерж (`:warning:`), `Full Run Failed`, інакше `Build Failed for branch`. Тіло: номер білда, PR, Asana-посилання або `⚠️ No task link in PR description` (`:1408`), рядок `🛑 Failed at stage: <CURRENT_STAGE>`, примітка про застарілий Jenkinsfile (`:1402`), Sentry issues прогону.

## 7. Стейджі з `#jenkins-failed-builds` → пайплайн

У каналі видно значення `env.CURRENT_STAGE`, а не назву стейджу Jenkins. Кількості з `jenkins-failed-builds.md` (686 постів).

| Категорія в аудиті | Постів | `Failed at stage` (CURRENT_STAGE) | Стейдж пайплайну | Джерело |
| --- | --- | --- | --- | --- |
| Smoke + модуль | 237 | `Test End-to-End`, `…: run tests`, `…: start Symfony server` | `Test End-to-End` | `JF:773-778`, `:1468` |
| Повний прогін | 218 | `Full Run Tests: playwright` | `🔄 Full Run Tests` (білд зелений, пост із `runFullTests`) | `JF:2001` |
| Пайплайн до тестів, разом | 136 | розбивка нижче | | `jenkins-failed-builds.md:16` |
| · elastica reset | 35 | `Fast ES sync (sync-service): elastica reset` | `Prepare Database` або `Full Run Tests` | `JF:2121` |
| · composer install | 16 | `Prepare project: composer install` | `Prepare project` | `JF:397` |
| · pull translations | 18 | `Prepare project: pull translations` / `Prepare JavaScript: pull JS translations` | `Prepare project` / `Prepare JavaScript` | `JF:417`, `:2367` |
| · npm build | 10 | `Prepare JavaScript: npm run build-ci` | `Prepare JavaScript` | `JF:2377` |
| · міграції | 6 | `Prepare Database: run migrations` / `Full Run Tests: run migrations` | `Prepare Database` / `Full Run Tests` | `JF:587`, `:1969` |
| · фікстури | 6 | історичний крок doctrine fixtures, тепер замінений seed | `Prepare Database` (старі версії) | `JF:579-581` |
| · docker up | 4 | у `JF` такого кроку нема; найімовірніше гілки інфра-AQA (`Prepare Docker stack: up`) | `Prepare Docker stack & DB` (`JFd`) | `JFd:1212` |
| · JWT | 3 | `Prepare project: generate JWT keypair` | `Prepare project` | `JF:415` |
| · seed | 2 | `Prepare Database: import seed` / `Full Run Tests: import seed` | `Prepare Database` / `Full Run Tests` | `JF:582`, `:1966` |
| Sentry після тестів або HC | 54 | `Sentry Check After Tests`, `Sentry Check After HC`, `Sentry Check After Full Run` | `🚨 Check Sentry Issues …` | `JF:799`, `:2224`, `:877` |
| Конфлікт авто-мержу | 30 | `Auto Update From Source` | `Auto update from source branch` | `JF:229` |
| Unit-тести | 8 | `Unit Tests` | `Unit Tests` | `JF:605` |
| Сигнал «No task link in PR description» | 106 | рядок Asana в тілі посту | `🔗 Detect Asana task` не знайшов посилання | `JF:1408` |
| Сигнал «branch is missing Jenkinsfile commits» | 95 | примітка в посту | `Check Jenkinsfile Consistency` | `JF:1402` |

Без окремого рядка в аудиті, але можливі: `Health Check` (без Sentry → `[HC FAILED]`), `Select Redis DB`, `Prepare Database: drop/create DB`, `Full Run Tests: flush Redis`.

## 8. Інші Jenkinsfile продукту

| Файл | Агент | Коли | Що робить |
| --- | --- | --- | --- |
| `JenkinsfileCheckTests` | `any` | За коментарем щоденний cron на `Develop` + вручну на будь-якій гілці (`:12`; блоку `triggers` у файлі нема) | Повний PHP-сьют + smoke консольних команд через `check_tests_command.sh -skip-hc`; параметри `BACKEND_BRANCH`, `FAST_MODE`, `RUN_PHPSTAN` (`:35-38`); свої БД і Redis, мікросервіси в Docker; JUnit і Slack-зведення |
| `JenkinsfilePHPStan` | `internal` | На PR | `composer`/`npm install`, PHPStan і JS-перевірки (composition API, ключі перекладів, JS unit, type check), Slack |
| `JenkinsfileReview` | `Review` | Bitbucket PR updated, лише перехід Draft → Ready (`:277`) | Тригерить Bitbucket Pipeline AI-рев'ю (`precoro-ai-code-reviewer`, selector `review-pr`), це статус Arbiter для clean-gate |
| `JenkinsfileScheduledDeploy` | `internal` | За розкладом джоби (у файлі не задано) | `composer install`, Deployer `dep deploy` на Precorino, Slack на старт/успіх/скасування/фейл, `deploy:unlock` при фейлі |
| `deploy.php` + `hosts.yml` | — | Викликається деплой-джобами | Deployer: три цілі `Develop` → stage `develop` (Precorino), `release` → `prod` (COM), `master` → `prod` (US) (`hosts.yml:5-64`); `deploy_path` вигляду `/var/www/<домен>/html`; перед деплоєм перевірка гілки й мержів (`deploy.php:40-59`), міграції перед symlink (`:94`), зупинка messenger-воркерів і очистка opcache після symlink (`:160-164`) |

## Відкриті питання

- Чи задано `QASE_MODE=testops` у `.env.branch` на dev-ноді: з репо не видно.
- `JFd` пінить TAF на `feature/brynza/docker-updates`; поки це так, Docker-білди тестують не `develop` TAF.
- `ci-and-envs.md:33` (повний гілковий прогін через поле Asana) розходиться з кодом: оновити сторінку.
