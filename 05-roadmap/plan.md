# План

Єдине місце, де є задачі, їх порядок, критерії готовності та оцінки. Фази описані в `phases.md`, числові цілі в `metrics.md`, рішення в `03-decisions/`. Кожна задача переноситься в трекер як є.

Формат: ID, задача, ADR, критерій готовності, контрольний лічильник або метрика, оцінка в днях для однієї людини, статус (`todo` / `wip` / `done` / `blocked`). Актуальний зріз статусів і наступна задача: `00-status.md`. Оцінки орієнтовні, переглядаються з AQA перед трекером.

## Фаза 0. Гігієна і вимірювання

| ID | Задача | Готово, коли | Метрика | Дні | Статус | ADR |
| --- | --- | --- | --- | --- | --- | --- |
| T0-01 | Зелений `tsc --noEmit` | 0 помилок; крок у Jenkins червоний при помилці | tsc 3 → 0 | 0.5 | todo |  |
| T0-02 | Зелений `eslint` без ослаблення правил | 0 помилок; крок у Jenkins | eslint 109 → 0 | 1–2 | todo |  |
| T0-03 | Секрети з репозиторію | MailPit, ControlClient, прод-токен в env; ротовані; git-історія перевірена | secrets 3 → 0 | 1 + інфра | blocked |  |
| T0-04 | Розширити `metrics-reporter` (є на гілці): top-50 за тривалістю, мова прогону, perFile, perTag | Поля є в `latest.json`; дашборд їх показує |  | 1, інфра-AQA | wip на гілці |  |
| T0-15 | Лічильник запитів на тест: браузер (`context.on('request')`) і API (`withApiStep`) → анотація → `metrics-reporter` | Поля `browserRequests`, `apiRequests` на тест і на проект у `latest.json`; цифра нічного прогону в `metrics.md`. Інтеграція: `06-playbooks/measurement.md`, труба 3 | навантаження на тест | 1 | todo |  |
| T0-16 | Експеримент з нічними зависаннями разом із Дмитром Ясмо: один контрольований прогін із `@heavy` тестами в загальному пулі, зняття lock waits / processlist / slow log / php-fpm / 5xx, накладання на таймлайн тестів | Кожне зависання того прогону має категорію (lock, пам'ять, продукт, тест); підтверджена або відкинута гіпотеза блокувань; рішення, чи лишати розділення `@heavy` | категорія падінь | 1–2 | todo |  |
| T0-05 | Частка preparation зі степів Allure | Скрипт по allure-results; цифра в `metrics.md` |  | 1 | todo |  |
| T0-06 | `--last-failed` у Jenkins-джобі | Параметр "rerun failed only"; `test-results` зберігається між білдами |  | 0.5, інфра-AQA | todo | 006 |
| T0-07 | Явна мова прогону | `LANGUAGE=auto` видалено; матриця в CI; мова в назві білда |  | 0.5 | todo |  |
| T0-08 | Мертві проекти і globalSetup | 3 проекти видалені; логін лише для проектів із тестами |  | 0.5 | todo |  |
| T0-09 | Трейс на першому ретраї | `base_fixtures.ts`; trace є для першого падіння |  | 0.5 | todo | 006 |
| T0-10 | Qase-репортер: підключити або видалити | Рішення з Head of QA; конфіг або package.json |  | 0.5 | done на гілці (`QASE_MODE`) |  |
| T0-11 | `EnvConfig` зі списку використаних ключів | Інтерфейс; звіт мертвих і відсутніх ключів |  | 1 | todo | 002 |
| T0-12 | Маніфест снапшоту + preflight у globalSetup | Маніфест для 5 найбільших компаній; preflight падає з точним повідомленням |  | 2 | todo |  |
| T0-13 | Контрольні лічильники: скрипт, baseline, CI-гейт "тільки вниз" | `debt-baseline.json` дорівнює правді; PR із ростом червоний; `metrics/debt.jsonl` на мержі |  | 1–2 | todo | 001 |
| T0-14 | Тижневий звіт поверх `metrics/history.jsonl` і `debt.jsonl` | `metrics/weekly/*.md` щопонеділка |  | 1 | todo | 001 |

## Фаза 1. Структурна модифікація зі швидкістю

| ID | Задача | ADR | Готово, коли | Метрика | Дні | Статус |
| --- | --- | --- | --- | --- | --- | --- |
| T1-01 | Типізований конфіг + фасад `Constants`, INI видалені | 002 | Усі прогони зелені; INI нема | INI 7 → 0 | 3–4 | todo |
| T1-02 | Codemod `Constants.x` → `config.x`, фасад видалено | 002 |  | `Constants.` 791 → 0 | 5, файлами | todo |
| T1-03 | `asUser` + storageState per user |  | Фікстура; кеш `.auth/<env>/<email>.json`; lint проти `logout_url` |  | 2 | todo |
| T1-04 | Codemod UI-логінів у спеках |  |  | `doLogin`/`LoginPage` 498 → 0 | 3–5, файлами | todo |
| T1-05 | Один merged `test` |  | `fixtures/index.ts` єдина точка; codemod імпортів | локальні `mergeTests` 37 → 0 | 2 | todo |
| T1-06 | Worker-scoped `api` з кешем токенів |  |  | `getUserApiTokenByEmail` у фікстурах 35 → 0 | 1 | todo |
| T1-07 | Lifecycle-обгортки (~55) | 005 | Список із `04-target/api-client.md`; smoke на кожну | Swagger coverage | 3 | todo |
| T1-08 | Фікстури стану з teardown: PO, Invoice, Receipt, PR |  | `confirmedPo`, `approvedInvoice`, `receivedReceipt`, `approvedPr`; delete після use |  | 3 | todo |
| T1-09 | API-preparation: no\_dcf\_company |  |  | s/test 130 → ≤ 45 | 3 | todo |
| T1-10 | API-preparation: common\_company |  |  | s/test 75 → ≤ 40 | 5 | todo |
| T1-11 | Codemod `allure.*` → `test.step`/`attach`; lint | 003 |  | `allure.` 12 000 → 0 | 3 | todo |
| T1-12 | Codemod `expect(await isVisible())` → web-first |  | lint без винятків | 511 → 0 | 2 | todo |
| T1-13 | Codemod sleeps |  | `no-wait-for-timeout` error | 121 → 0 | 2–3 | todo |
| T1-14 | Розбиття minor/common/invoice/items/budgets |  | Жоден проект > 45 хв | найдовший проект | 2 + юзери | todo |
| T1-15 | Tiering-теги і Jenkins-параметр рівня |  | Початковий розподіл `@gate/@module/@nightly` з пріоритетів Qase через `@qase(id)`; `@gate` ≤ 15 хв, збалансований по проектах |  | 3 | todo |
| T1-16 | Retries 1 + flaky-метрика + карантин | 006 | Конфіг; дашборд; політика узгоджена |  | 1 + розмова | todo |
| T1-18 | Декомпозиція spec-файлів: жоден файл понад 1 500 рядків, ціль ≤ 800; один describe-блок або feature-area на файл; module-level `let` і `beforeAll` переносяться у фікстури до розбиття | Правило `max-lines` в eslint як error; теги і Qase-ID збережені; список файлів у прогоні не змінює склад тестів | файлів > 1 500 рядків 27 → 0 | 5, файлами | todo |  |
| T1-19 | Декомпозиція не-spec файлів понад 1 000 рядків, які не покриті іншими задачами: `invoice_strategy.ts` 1 971, `company_profile.ts` 1 726, `po_strategy.ts` 1 063 (стратегії → фікстури стану і builders); `api_fixtures.ts` 1 426 → модулі за доменом у складі T1-05 | Файли зникають або ≤ 800 рядків | не-spec файлів > 1 000 рядків 10 → 0 | 5 | todo |  |
| T1-17 | API-preparation: punchout, spo, po\_receive, budgets |  |  | s/test по проектах | 8 | todo |

## Фаза 2. Стабільність як правило

| ID | Задача | ADR | Готово, коли | Метрика | Дні | Статус |
| --- | --- | --- | --- | --- | --- | --- |
| T2-01 | Розбір кожного `force`/`clickUsingJavascript`/`dispatchEvent` |  | Кожен: продукт, overlay або видалено; лишені з коментарем | ~420 → ≤ 20 | 5–8 | todo |
| T2-02 | `.catch` поза предикатами → 0; порціями з прогонами |  |  | 211 + 131 → 0 | 4 | todo |
| T2-03 | Polling-цикли → `expect.poll`/`toPass` |  |  | while/for-sleep 47 → 0 | 3 | todo |
| T2-04 | Lint-правила Playwright як error; кастомні проти `doLogin`, `db.`, `allure` |  | Усі правила з `06-playbooks/codemods.md` увімкнені |  | 1 | todo |
| T2-05 | `X-Test-Id` у запитах, посилання на Sentry у репорті падіння | 006 |  |  | 2 | todo |
| T2-06 | Візуальні snapshot-тести в окремий проект поза gate |  |  |  | 1 | todo |
| T2-07 | Категорії падінь у репорті; карантин-процес | 006 | Кожне падіння має категорію; `@quarantine` з дедлайном |  | 2 | todo |
| T2-08 | Timeout 120 s за замовчуванням, `test.slow()` явно | 006 |  |  | 1 + прогони | todo |

## Фаза 3. Архітектура для General QA

| ID | Задача | ADR | Готово, коли | Метрика | Дні | Статус |
| --- | --- | --- | --- | --- | --- | --- |
| T3-01 | Компоненти: ItemsTable, StatusBadge, Toast, ConfirmModal, Attachments | 004 | Перші два: PO і Invoice через компоненти |  | 8 | todo |
| T3-02 | `DocumentPage` і `SettingsPage` тонкі базові класи | 004 |  |  | 3 | todo |
| T3-03 | Злиття форкнутих сторінок через компоненти | 004 | 3 пари → 3 класи |  | 5 | todo |
| T3-04 | Codemod локаторів: string → `Locator`, `'{}'` → функції з екрануванням | 004 |  | `this.xxxLocators.` 1 814 → 0 | 5 | todo |
| T3-05 | Видалення mixin-ів, `declare`, Babel-плагіна | 004 |  | mixin-файлів 13 → 0 | 3 | todo |
| T3-06 | Повний згенерований клієнт; `precoro_service.ts` видалено | 005 |  | імпорти → 0 | 8 | todo |
| T3-07 | ajv зі схемами зі Swagger; contract-check у CI | 005 | 63 ручні схеми видалені |  | 3 | todo |
| T3-08 | DB: параметризовані запити; ID через API; `db` у спеках → 0 |  |  | 1 811 → 0 | 5 | todo |
| T3-09 | Playbook "як написати тест", шаблон, CODEOWNERS |  | Новий тест від General QA проходить ревʼю з першого разу |  | 2 | todo |

Деталізація після фази 1, коли будуть цифри API-preparation.

## Фаза 4. Дані і середовища (з інфра-AQA)

| ID | Задача | ADR | Готово, коли | Метрика | Дні | Статус |
| --- | --- | --- | --- | --- | --- | --- |
| T4-01 | Реєстр компаній `data/companies.ts` |  | Тести беруть юзерів і сутності з реєстру | літеральні email 133 → 0 | 5 | todo |
| T4-02 | Архетипи компаній через ControlClient + CompanySetupManager |  | 10–20 профілів у коді, скрипт створення |  | 10 | todo |
| T4-03 | Контракт снапшоту S ↔ тести T |  | Версія в маніфесті; preflight перевіряє |  | 2 | todo |
| T4-07 | Скрипти copy + dump для seed у репозиторій; процедура регенерації в playbook; регенерація з архетипів одним скриптом | Будь-хто з AQA перегенеровує seed за інструкцією; версія інкрементується | `@not_for_isolated_env` 417 → 0 | 3 | todo |  |
| T4-04 | Teardown-політика і sweep за маркером |  | create без delete не мержиться | creates/deletes → 1:1 | 3 | todo |
| T4-05 | Ефемерні середовища зі снапшотом |  | Прогін на ізольованому середовищі |  | інфра-AQA | todo |
| T4-06 | `fullyParallel: true` там, де тести незалежні |  |  |  | після T4-01..04 | todo |

Залежить від відповідей на питання #13, #16, #17.
