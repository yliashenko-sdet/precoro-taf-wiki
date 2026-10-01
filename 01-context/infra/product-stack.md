---
_width: wide
---

# Стек продукту для e2e

Довідка: з чого складається Docker-стек продукту, на якому ганяють e2e. Що лежить у `Makefile.e2e` і compose-файлах.

Джерело: репозиторій `precoro`, гілка `taf/base` (= гілка infra-AQA `feature/brynza/docker-jenkinsfile`, коміт `94f8a5399b4`). Усі посилання `файл:рядок` вказують на закомічений стан (`git show HEAD:<файл>`). Локальні правки описані окремо, у розділі 7.

---

## 1. Compose-файли і як вони накладаються

| файл | роль | хто вантажить |
|---|---|---|
| `docker-compose-monolith.yml` | базовий стек моноліту для щоденної розробки | `Makefile` (`DC-MONOLITH`, `Makefile:91`), `Makefile.e2e` |
| `docker-compose-e2e.yml` | e2e-оверлей поверх моноліту: підміняє конфіги на `docker/e2e/*`, додає healthcheck-и і мікросервіси для e2e | `Makefile.e2e:15` |
| `docker/e2e/docker-compose-ci.yml` | CI-оверлей, лише Jenkins | `Makefile.e2e:14` (змінна `CI-OVERLAY`), `Jenkinsfile:1134`, `Jenkinsfile:1181` |
| `docker-compose.yml` | окремий стек мікросервісів для розробки, у e2e не вантажиться | вручну |

Порядок шарів: `docker compose -f docker-compose-monolith.yml -f docker-compose-e2e.yml $(CI-OVERLAY)` (`Makefile.e2e:15`).

Ключові властивості:
- Той самий compose-проєкт і ті самі порти, що в локальному стеку. Тому мережа `precoro_precoro-local-network` зберігає ім'я, і `external: true` в e2e-репо резолвиться (`Makefile.e2e:7-10`, `docker-compose-e2e.yml:1-3`).
- Локальний і e2e-стек одночасно не запускати: спільні порти (`Makefile.e2e:9-10`).
- Друга мережа `microservices-network` має фіксоване ім'я `precoro_microservices-network` (`docker-compose-monolith.yml:239-240`). CI-оверлей робить його per-build через `MICROSERVICES_NETWORK`, щоб паралельні PR-білди не конфліктували (`docker/e2e/docker-compose-ci.yml:3-4`, `:14-16`).
- CI-оверлей ще прокидає `GIT_BRANCH` у `precoro-app` для тегів Sentry (`docker/e2e/docker-compose-ci.yml:6-12`).

### 1.1. Сервіси моноліту + e2e-оверлею

Образи з префіксом "приватний реєстр DigitalOcean" потребують `docker login` у цей реєстр (`docker-compose-e2e.yml:92-93`, `:113`, `:163`).

| сервіс | профіль | звідки образ | що робить e2e-оверлей | джерело |
|---|---|---|---|---|
| `precoro-app` | — | **локальна збірка** `docker/local/phpfpm` (FrankenPHP, PHP 8.2, Node 22 всередині) | `env_file` = `docker/e2e/phpfpm/.env.docker.e2e`; healthcheck на статичний `/web/`; `var/cache` на іменованому томі `appcache`; чекає healthy MySQL і Redis | monolith `:2-41`; e2e `:12-38`; `docker/local/phpfpm/Dockerfile:1,46-47` |
| `precoro-mysql` | — | `mysql:8.0` | швидкість замість durability (`flush-log-at-trx-commit=2`, `skip-log-bin`, buffer pool 512M); healthcheck через `SELECT 1` | monolith `:43-65`; e2e `:42-62` |
| `precoro-redis` | — | `redis:latest` | healthcheck `redis-cli ping` | monolith `:67-72`; e2e `:64-69` |
| `precoro-mailpit` | `mailpit` | `axllent/mailpit` | — | monolith `:74-81` |
| `precoro-minio` | `minio` | `rustfs/rustfs` (S3) | `RUSTFS_SERVER_DOMAINS=precoro-minio`, без цього аплоади 500 | monolith `:83-111`; e2e `:71-75` |
| `precoro-minio-init` | `minio` | `rclone/rclone`, одноразовий | створює бакет `precoro-local` | monolith `:113-131` |
| `precoro-elasticsearch` | `elasticsearch` | **локальна збірка**: ES 7.17.4 + плагін `analysis-icu` | своя збірка й env: `xpack.security` вимкнено, single-node | monolith `:175-203`; e2e `:77-82`; `docker/e2e/elasticsearch/Dockerfile:1-2`; `docker/e2e/elasticsearch/.env.docker.e2e:1-3` |
| `mail-templates` | — | приватний реєстр DigitalOcean, тег `latest-staging`, `pull_policy: missing` | оголошений тут, щоб жити в одному lifecycle зі стеком | e2e `:84-110` |
| `exports` | — | приватний реєстр DigitalOcean, `latest-staging`, `pull_policy: always` | рендер PDF; ходить у MySQL стеку | e2e `:112-135` |
| `ai-mock` | — | `nginx:alpine` + `docker/e2e/ai-mock/nginx.conf` | статичний catch-all замість AI-мікросервісу | e2e `:137-150` |
| `sync-service` | `sync` | приватний реєстр DigitalOcean, `opensearch-sync:${SYNC_SERVICE_TAG}`, `linux/amd64` | одноразовий індексатор ES (`/loader -index-all`), не стартує на `up` | e2e `:155-195` |
| `precoro-loki`, `precoro-alloy`, `precoro-grafana` | `logs` | публічні образи Grafana | у e2e не вмикається (лише `reset` згадує профіль) | monolith `:133-173`; `Makefile.e2e:234` |
| `mercure` | `mercure` | `dunglas/mercure` | у e2e не вмикається, `MERCURE_URL=none` | monolith `:205-234`; `.env.docker.e2e:158-159` |

Профілі, які вмикає `Makefile.e2e`: `minio`, `mailpit`, `elasticsearch` (`Makefile.e2e:16`). `sync` вмикається лише в `es-sync` (`Makefile.e2e:219`).

Креденшели MySQL у `Makefile.e2e` і `sync-service`: дефолтні локальні креденшели з compose-файлу (`Makefile.e2e:18`, `docker-compose-e2e.yml:186-190`). Пароль root для контейнера MySQL береться зі змінної `MYSQL_ROOT_PASSWORD` (`docker-compose-monolith.yml:59`).

Мережевий вхід: FrankenPHP сам термінує `:80` і `:443` з dev-сертифікатом, окремого nginx немає (`docker/local/caddy/Caddyfile:1-3`, `:70-77`). Кількість PHP-потоків: `{$FRANKENPHP_NUM_THREADS:8}` (`Caddyfile:12-14`).

### 1.2. Стек мікросервісів `docker-compose.yml`

Окремий файл, без профілів. Ділить з монолітом мережу `precoro_microservices-network` (`docker-compose.yml:384-386`). Майже всі образи тягнуться з приватного реєстру DigitalOcean, тег `latest-staging`.

| група | сервіси | джерело |
|---|---|---|
| інфраструктура | `elasticsearch` (локальна збірка), `clickhouse`, `redis`, `postgres`, `minio` (rustfs), `createbuckets` | `docker-compose.yml:6,26,46,51,69,91` |
| мікросервіси | `dashboards`, `mail-templates`, `exports`, `inventory`, `reports` + `reports-celery`, `imports`, `ai` + `ai-celery`, `integrations` + `-grpc` + `-celery`, `payments` + `-celery` + `-celery-beat` + `-grpc`, `auth` | `docker-compose.yml:111,127,138,148,172,194,208,219,239,251,269,286,298,320,332,344,361` |

`payments-grpc` тягнеться з іншого dev-реєстру з тегом `develop` (`docker-compose.yml:346`). Мікросервіси ходять у БД моноліту через `host.docker.internal`, дефолт задано в `x-microservice-defaults` (`docker-compose.yml:1-3`).

---

## 2. Цілі `Makefile.e2e`

Запуск: `make -f Makefile.e2e <ціль>`. Ціль за замовчуванням `help` (`Makefile.e2e:55`). `.NOTPARALLEL`, щоб `start` ішов строго по черзі (`Makefile.e2e:57-60`).

| ціль | що робить | джерело |
|---|---|---|
| `start` | `up` → `deps` → `assets`. Ціль "після git pull" | `:79` |
| `up` | `compose up -d --build --remove-orphans` з профілями | `:81-82` |
| `deps` | `composer install --no-scripts` у контейнері. Без скриптів, бо `post-install-cmd` накочує міграції | `:84-92` |
| `assets` | якщо немає `assets/js_translations/js_translations_en.json`, тягне JS-переклади через `node scripts/frontend/pull-translations.mjs`; далі `npm run build` у контейнері | `:94-106` |
| `ci-build` | лише CI: `composer install --no-scripts`, `npm ci`, генерація JWT-ключів, `assets:install`, `translain:pull:all`, `translain:pull:js`, `npm run build`, `cache:clear` | `:108-118`; `Jenkinsfile:1266` |
| `stop` | `down`, томи лишаються | `:120-121` |
| `restart` | `restart` контейнерів | `:123-124` |
| `translations` | `translain:pull:all` + `translain:pull:js` + `cache:clear`. Без перекладів Twig рендерить сирі ключі, і селектори за текстом падають | `:126-145` |
| `prepare-db` | **руйнівна**. Кроки: перевірка, що є `SEED-FILE` → `doctrine:database:drop` → `doctrine:database:create` → `precoro:ImportSeedCommand` (дамп містить схему, дані і `migration_versions`) → `doctrine:migrations:migrate` → `es-sync` → `cache-clear`. Консоль іде з `--env=test` і з `TEST_DATABASE_*`, перевизначеними на БД `precoro` | `:147-186`; `EXEC-TESTDB` `:30-34` |
| `es-sync` | `fos:elastica:reset` (обов'язково першим, інакше конфлікти мапінгу) → резолв тегу `sync-service` через `doctl` (якщо `SYNC-SERVICE-TAG` не задано) → `compose --profile sync run --rm sync-service`. Лоадер наповнює 16 з 17 індексів, `supplier_unspsc_map_v1` лишається порожнім, як і в CI | `:188-219` |
| `cache-clear` | `rm -rf var/cache/{prod,dev,test}` → `redis-cli FLUSHALL` → `cache:clear`. `cache:pool:clear --all` свідомо не використовується, бо завжди виходить з кодом 1 | `:221-229` |
| `reset` | **руйнівна**. `down -v --remove-orphans` разом з профілем `logs`. Зносить томи MySQL, ES, MinIO, кеш | `:231-234` |

Порядок для першого запуску: `start` → `translations` → `prepare-db` (див. `docs/e2e-local-guide.md:97-198`).

### Змінні

| змінна | дефолт | роль | джерело |
|---|---|---|---|
| `CI-OVERLAY` | порожньо | додаткові `-f` для всіх compose-викликів. Jenkins передає `-f ./docker/e2e/docker-compose-ci.yml` | `:12-15`; `Jenkinsfile:1181` |
| `SEED-FILE` | `autotests_seed_2026-09-22.sql.gz` | дамп для `prepare-db`, лежить у корені репо (у gitignore). Корінь змонтовано в `/var/www`, тому копіювати не треба | `:36-40`; `.gitignore:124` |
| `SYNC-SERVICE-TAG` | порожньо | тег образу `opensearch-sync`. У реєстрі немає плаваючого тегу, лише хеші комітів. Порожньо → береться найновіший через `doctl` | `:48-52`, `:206-217` |
| `TRANSLAIN-ENV` | `staging-com` | **середовище** Translain, не git-гілка. Те саме, що тягне Jenkins | `:42-46` |

---

## 3. Перемикачі середовища `docker/e2e/phpfpm/.env.docker.e2e`

Файл підключається як `env_file` для `precoro-app` (`docker-compose-e2e.yml:15-16`). Це повна копія `docker/local/phpfpm/.env.docker.local` плюс перевизначення, а не дельта (`.env.docker.e2e:1-10`).

Чому саме цей шар: `env_file` дає справжні змінні процесу. Symfony Dotenv їх не перезаписує, тож вони перемагають `.env.local` і значення з Infisical (`.env.docker.e2e:99-100`, `:146-152`, `:199-201`).

Значення наведено лише для нетаємних перемикачів та імен контейнерів. Решта змінних названа тільки на ім'я.

| змінна / група | значення | роль | рядок |
|---|---|---|---|
| `APP_ENV` | `prod` | апка працює як прод і читає засіяну БД `precoro` | `:12-18` |
| `PROJECT_HOST` | `precoro-app` | не прод-хост, щоб fast-login ендпоінт автотестів не віддавав 404; хост роутера і cookie збігається з браузером | `:20-24` |
| `DATABASE_URL`, `DATABASE_RO_URL`, `DATABASE_INFOCARDS_URL`, `MYSQL_ROOT_PASSWORD`, `TEST_DATABASE_URL`, `TEST_DATABASE_RO_URL` | хост `precoro-mysql` | БД стеку | `:26-29`, `:44-45` |
| `MAILER_DSN` | хост `precoro-mailpit` | пошта йде в Mailpit | `:31` |
| `REDIS_DSN` | `redis://precoro-redis:6379` | Redis стеку | `:33` |
| `DO_SPACES_S3_ENDPOINT`, `DO_SPACES_S3_BUCKET`, `DO_SPACES_REGION`, `DO_SPACES_S3_CDN_ENDPOINT`, `DO_SPACES_S3_KEY`, `DO_SPACES_S3_SECRET` | ендпоінт `precoro-minio:9100`, бакет `precoro-local` | S3-сховище (rustfs) | `:35-40` |
| `ELASTICSEARCH_URL` | `http://precoro-elasticsearch:9200/` | ES стеку | `:47` |
| `ELASTICSEARCH_USERNAME`, `ELASTICSEARCH_PASSWORD` | порожні | ES без авторизації | `:163-166` |
| `PRECORO_MS_MAIL_TEMPLATES_URL` | `http://mail-templates:3001` | рендер листів | `:53-58` |
| `PRECORO_MS_AI_URL` | `http://ai-mock:80` | AI-мок | `:60-65` |
| `PRECORO_MS_EXPORTS_URL` | `http://exports:8000` | рендер PDF при confirm PO | `:220-227` |
| `PRECORO_MS_{REPORTS,IMPORTS,DASHBOARDS,INTEGRATIONS,PAYMENTS,AUTH,MESSENGER_LOGGER}_URL` | порожні | навмисно. Порожній URL падає миттєво. Адреса `127.0.0.1` дає 7 с ретраїв на кожен виклик | `:67-86` |
| `CONTROL_MS_URL` | порожньо | Control MS у стеку немає | `:160-162` |
| `MESSENGER_*_TRANSPORT_DSN`, `REDIS_CONTROL_EVENTS_*_TRANSPORT_DSN` | `sync://` | обробка в межах запиту, воркерів немає | `:91-108`, `:131-135` |
| `MESSENGER_ASYNC_NOTIFICATIONS_TRANSPORT_DSN` | `sync://` | п'ять класів листів. `in-memory://` мовчки їх губив, тому повернули `sync://` | `:110-130` |
| `MESSENGER_INVENTORY_MS_EVENTS_TRANSPORT_DSN` | `redis://precoro-redis:6379/...` | немає PHP-обробника. `sync://` дає `NoHandlerForMessageException` на створенні item | `:137-144` |
| `MESSENGER_DISABLE_MODULE_CLEANUP_DSN` | `sync://` | не тягне хостовий redis з CI `.env.local` | `:154-156` |
| `MERCURE_URL`, `MERCURE_PUBLIC_URL` | `none` | Mercure у стеку немає | `:157-159` |
| `CDN_HMAC_SECRET` | — | підпис CDN-URL | `:88-89` |
| `SAML_ENTITY_ID_URL`, `SAML_ACS_URL`, `SAML_SINGLE_LOGOUT_RESPONSE_URL` | синтаксично валідні локальні URL | без них кожна сторінка 500 через OneLogin strict | `:168-176` |
| `TRUSTED_IPS` | приватні діапазони docker-мереж | 2FA пропускається, як колись на нативному `127.0.0.1` | `:178-184` |
| `INTERCOM_SECRET_KEY`, `MERCURE_JWT_SECRET`, `PRECORO_SIGNING_SECRET`, `PRECORO_MS_*_SIGNING_SECRET` (AI, AUTH, DASHBOARDS, DOCUMENT_PROCESSING, IMPORTS, INTEGRATIONS, INVENTORY, MAIL_TEMPLATES, PAYMENTS) | фейкові, довжина ≥ 32 байти | `firebase/php-jwt` вимагає мінімальну довжину ключа HS256, інакше 500 | `:186-218` |
| `PRECORO_MS_EXPORTS_SIGNING_SECRET` | dev-дефолт | має збігатися з тим, що чекає staging-образ `exports` | `:224-228` |
| `PHP_IDE_CONFIG`, `XDEBUG_MODE` (закоментовано) | — | налагодження | `:42`, `:49-51` |

Окремо, поза цим файлом:
- `TEST_API_ENABLED` вмикає firewall `test_api` (`config/packages/security.yaml:137-141`, matcher `TestApiRequestMatcher`). Параметр `test_api_enabled` за замовчуванням `false` (`config/services.yaml:246-247`, `:1027-1029`). У закоміченому `.env.docker.e2e` цієї змінної **немає**.
- `ELASTICA_ENABLE_LISTENERS` керує параметром `enable_listeners` у `src/Kernel.php:18` (також `config/services.yaml:183`). У базовому `.env` стоїть `false` (`.env:157`). У закоміченому `.env.docker.e2e` перевизначення **немає**, тож зміни з тестів не потрапляють в ES до наступного `es-sync`.

---

## 4. Мікросервіси

Імена змінних з базового `.env:173-219`. Стан у e2e — з `.env.docker.e2e`.

| мікросервіс | призначення | є в e2e-стеку? | змінна | що буде без нього |
|---|---|---|---|---|
| mail-templates | рендер HTML-листів | так, контейнер `mail-templates` | `PRECORO_MS_MAIL_TEMPLATES_URL` | URL, що не резолвиться → 500 на confirm/approve. Порожній URL → листи з порожнім тілом (`docker-compose-e2e.yml:84-94`, `.env.docker.e2e:53-58`) |
| exports | PDF-вкладення, експорт документів | так, контейнер `exports` | `PRECORO_MS_EXPORTS_URL` | confirm PO → 500 "scheme is missing" (`.env.docker.e2e:220-227`, `docker-compose-e2e.yml:112-113`) |
| ai | AI-асистент, OCR, контракти | **мок** `ai-mock` | `PRECORO_MS_AI_URL` | без мока кожен виклик пише помилку в Sentry. Мок віддає `["ok"]` і не віддає PDF для `GetFileFromAttachmentEndpoint` (`docker-compose-e2e.yml:137-143`) |
| reports | звіти | ні, URL порожній | `PRECORO_MS_REPORTS_URL` | звіти не працюють, виклики повертають `ErrorResponse` (`.env.docker.e2e:67-80`) |
| imports | імпорт файлів | ні, URL порожній | `PRECORO_MS_IMPORTS_URL` | імпорти не працюють (`.env.docker.e2e:81`) |
| dashboards | дашборди | ні | `PRECORO_MS_DASHBOARDS_URL` | `ErrorResponse` (`:82`) |
| integrations | інтеграції | ні | `PRECORO_MS_INTEGRATIONS_URL` | `ErrorResponse` (`:83`) |
| payments | платежі | ні | `PRECORO_MS_PAYMENTS_URL` | `ErrorResponse` (`:84`) |
| auth | авторизація | ні | `PRECORO_MS_AUTH_URL` | `ErrorResponse`. У `--env=test` виклики обходяться (`Makefile.e2e:158-159`) |
| messenger-logger | лог повідомлень шини | ні | `PRECORO_MS_MESSENGER_LOGGER_URL` | `ErrorResponse` (`:86`) |
| inventory | склад | ні | `PRECORO_MS_INVENTORY_URL` | у `.env.docker.e2e` не перевизначено, лишається дефолт з `.env`. Події йдуть у Redis-стрім без споживача (`:137-144`) |
| document-processing | обробка документів | ні | `PRECORO_MS_DOCUMENT_PROCESSING_URL` | не перевизначено, дефолт з `.env` |
| notifications | нотифікації | ні | `PRECORO_MS_NOTIFICATIONS_URL` | не перевизначено, дефолт з `.env` |

Загальний механізм: порожній URL → `InvalidArgumentException` одразу (0 с). Адреса на `127.0.0.1` → `RetryableHttpClient` робить 1+2+4 = 7 с ретраїв, і ця затримка потрапляє у web-запит (`.env.docker.e2e:67-79`).

---

## 5. Секрети: Infisical

Тільки механізм, без значень.

1. **Контейнер `precoro-app`.** Entrypoint `docker/local/phpfpm/entrypoint.sh` (`Dockerfile:52,58`) запускає FrankenPHP під `infisical run --watch --env=development-docker` (`entrypoint.sh:24`, `:106-113`).
   - **ONLINE.** Infisical доступний (перевірка на рівні auth, `:96-99`). Секрети живі, кеш оновлюється в `/run/infisical/secrets.env` (tmpfs) (`:84-94`, `docker-compose-monolith.yml:29-30`).
   - **DEGRADED.** Infisical недоступний. FrankenPHP стартує з кешу або зовсім без секретів, якщо кешу немає. Раз на 15 с перевіряє, чи Infisical повернувся, і тоді перезапускається (`entrypoint.sh:115-136`).
   - Сесія береться з хоста: `~/.infisical` (ro) і `~/infisical-keyring` змонтовані в контейнер (`docker-compose-monolith.yml:17-20`). Тому на хості потрібен `infisical login`; підказка в логах: `infisical vault set file && infisical login` (`entrypoint.sh:21`, `:122`).
2. **`docker exec`** — окремий процес без секретів. Цілі основного `Makefile` обгортають його в `infisical run --env=development-docker --` (`Makefile:106-111`). `Makefile.e2e` цього **не** робить: `prepare-db` і `deps` свідомо йдуть без Infisical (`Makefile.e2e:89-90`, `:164-169`).
3. **`bin/infisical-sync.php`** дописує в `.env.local` ключі з Infisical, яких там немає або які стоять як плейсхолдер. Наявні значення не перезаписує (`bin/infisical-sync.php:4-13`, `:56-65`). Авторизація: `INFISICAL_UNIVERSAL_AUTH_CLIENT_ID` / `INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET`. Спершу береться з env процесу, потім з `.env.local`, потім з `.env` (`:21-44`).
4. **Пріоритет:** `env_file` (`.env.docker.e2e`) > Infisical / `.env.local` для всіх перевизначених ендпоінтів. Infisical несе хостові адреси (`127.0.0.1`, `localhost`), які всередині контейнера вказують на сам контейнер (`.env.docker.e2e:91-100`, `Makefile.e2e:164-169`).
5. **Реєстр і `doctl`.** Для `mail-templates`, `exports` і `sync-service` потрібен `docker login` у приватний реєстр DigitalOcean. Для автотегу `es-sync` потрібен `doctl auth init` (`docs/e2e-local-guide.md:72-88`).

---

## 6. Розбіжності між гайдом і кодом

| що | гайд / коментар | реальність | джерело |
|---|---|---|---|
| `make docker-secrets-sync` | крок 5 гайду і "лікування" курсів валют | цілі в `Makefile` немає. Прибрана комітом `89eaa9a298f` (2026-08-20, "moved functional & minor improvements"), додана в `1c4ecdfb7b5` (2026-07-21). Обхід: виконати `php bin/infisical-sync.php .env.local` у контейнері (саме це робила ціль) | `docs/e2e-local-guide.md:170-177`, `:389`; `Makefile.e2e:168`; `git log -S"docker-secrets-sync:" -- Makefile` |
| `make docker-start-e2e` | коментар у `docker-compose-e2e.yml:6` | такої цілі в `Makefile` немає | `git grep docker-start-e2e` |
| Node на хості | гайд: `npm install` на хості (`:131-137`) | `package.json:162-164` вимагає `node ^22.23.2 \|\| >=24.15.0`. Контейнер має Node з образу `node:22-slim` (`docker/local/phpfpm/Dockerfile:46-47`) | |
| збірка фронта | `assets` / `start` роблять `npm run build` у контейнері (`Makefile.e2e:103-106`) | `node_modules` ставиться на хості (macOS-нативні бінди) і лежить на бінд-маунті. Linux-контейнер не може зібрати з ними фронт, тому фронт практично доводиться збирати на хості | `docs/e2e-local-guide.md:120-122`, `:133-137` Перевірено 2026-09-30: у контейнері `Cannot find native binding` (rolldown), на хості з Node 22.23 збірка проходить. |
| листи | "`MESSENGER_ASYNC_NOTIFICATIONS_TRANSPORT_DSN=in-memory://` гасить п'ять класів листів" | у файлі вже `sync://` | `docs/e2e-local-guide.md:334`; `.env.docker.e2e:130` |
| кількість контейнерів | "Підніметься 8 контейнерів" | з профілями `minio`/`mailpit`/`elasticsearch` їх 10: 9 сервісів плюс одноразовий `precoro-minio-init` | `docs/e2e-local-guide.md:124`; розділ 1.1 |
| `docker/e2e/phpfpm/{Dockerfile,entrypoint.sh,php.ini,...}` | `Makefile.e2e:162` посилається на ліміт у `docker/e2e/phpfpm/php.ini` | e2e-оверлей не має `build:` для `precoro-app` і бере образ `docker/local/phpfpm`. Ці файли не використовуються | `docker-compose-e2e.yml:13-14` |
| heap ES | `docker/e2e/elasticsearch/.env.docker.e2e:9` задає 512m | `environment.ES_JAVA_OPTS` з моноліту (дефолт 400m) має пріоритет над `env_file`, тож у закоміченому стеку діє 400m | `docker-compose-monolith.yml:184-189` |
| `TEST_API_ENABLED`, `ELASTICA_ENABLE_LISTENERS` | TAF викликає `/api/*` через test-api і чекає, що зміни видно в ES-списках | у закоміченому `.env.docker.e2e` їх немає | розділ 3 |

---

## 7. Локальні незакомічені правки для запуску з хоста, не в репо

Робоче дерево `precoro` має 3 змінені файли (`git diff --stat`).

| файл | що додано | навіщо |
|---|---|---|
| `Makefile.e2e`, ціль `up` | перед `up`: `mkdir -p ./web/uploads/media/default/0001`. Після `up`: `chmod -R 777 var web/uploads` від root у `precoro-app` | без каталогу кожен експорт/звіт закінчується "Something went wrong". Jenkins створює той самий каталог (`Jenkinsfile:361` за коментарем) |
| `docker-compose-e2e.yml`, `precoro-elasticsearch` | `environment.ES_JAVA_OPTS` з дефолтом heap 1g | з 400m ES падає на `es-sync` дампа 2026-09-22 ("Data too large") |
| `docker/e2e/phpfpm/.env.docker.e2e` | `TEST_API_ENABLED=1` | відкриває firewall `test_api` для викликів TAF з `X-AUTO-TESTS` + `X-AUTH-TOKEN`. Без нього API-сетап редиректиться на `/login` |
| те саме | `ELASTICA_ENABLE_LISTENERS=true` | зміни з тестів одразу індексуються в ES |
| те саме | `FRANKENPHP_NUM_THREADS=20` | 8 потоків за замовчуванням ставлять запити в чергу при кількох воркерах Playwright |

Ці правки варто запропонувати в репо продукту: без них стек з закоміченого стану під TAF не працює.
