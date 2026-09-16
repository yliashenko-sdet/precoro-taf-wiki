# Беклог

Задачі, готові для переносу в трекер. Формат: ID, назва, фаза, ADR, DoD, храповик, оцінка. Оцінки в днях для однієї людини.

## Фаза 0

| ID | Задача | DoD | Храповик | Оцінка |
|---|---|---|---|---|
| T0-01 | Зелений `tsc --noEmit` на робочій гілці | 0 помилок; крок у Jenkins червоний при помилці | tsc errors 3 → 0 | 0.5 |
| T0-02 | Зелений `eslint` без ослаблення правил | 0 помилок; крок у Jenkins | eslint errors 109 → 0 | 1–2 |
| T0-03 | Секрети з репозиторію | MailPit-пароль, ControlClient, прод-токен в env; секрети ротовані; git-історія перевірена | secrets 3 → 0 | 1 + ротація на боці інфри |
| T0-04 | JSON-репортер і дашборд: machine-time, top-50, мова | `json` у reporter; дашборд читає його; поля є | | 1–2, з інфра-AQA |
| T0-05 | Частка preparation зі степів Allure | Скрипт по allure-results: сума кроків create/prepare/login vs verify по проектах; цифра в `metrics.md` | | 1 |
| T0-06 | `--last-failed` у Jenkins-джобі | Параметр "rerun failed only"; `test-results` зберігається між білдами | | 0.5 + Jenkins |
| T0-07 | Явна мова прогону | `LANGUAGE=auto` видалено; матриця в CI; мова в назві білда і в репорті | | 0.5 |
| T0-08 | Мертві проекти і globalSetup | 3 проекти видалені; globalSetup логінить лише проекти з тестами | | 0.5 |
| T0-09 | Трейс на першому ретраї | `base_fixtures.ts` змінено; trace є для першого падіння | | 0.5 |
| T0-10 | Qase-репортер: підключити або видалити | Рішення з Head of QA; конфіг або package.json | | 0.5 |
| T0-11 | `EnvConfig` зі списку використаних ключів | Інтерфейс; скрипт-звіт мертвих і відсутніх ключів | | 1 |

## Фаза 1, перший зріз

| ID | Задача | ADR | DoD | Храповик | Оцінка |
|---|---|---|---|---|---|
| T1-01 | Типізований конфіг + фасад `Constants`, INI видалені | 002 | Усі прогони зелені на новому конфігу; INI нема | INI 7 → 0 | 3–4 |
| T1-02 | Codemod `Constants.x` → `config.x` | 002 | Фасад видалено | `Constants.` 791 → 0 | 5, файлами |
| T1-03 | `asUser` + storageState per user | draft fixtures | Фікстура; кеш `.auth/<env>/<email>.json`; `logout_url` заборонено lint-правилом | | 2 |
| T1-04 | Codemod UI-логінів у спеках | | `doLogin`/`LoginPage` у спеках 0 | 498 → 0 | 3–5, файлами |
| T1-05 | Один merged `test` | | `fixtures/index.ts` єдина точка; codemod імпортів | локальні `mergeTests` 37 → 0 | 2 |
| T1-06 | Worker-scoped `api` з кешем токенів | | `getUserApiTokenByEmail` у фікстурах 0 | 35 → 0 | 1 |
| T1-07 | Lifecycle-обгортки (~55) | 005 | Список із `api-client.md` покритий; smoke-тести на кожну | Swagger coverage | 3 |
| T1-08 | Фікстури стану з teardown: PO, Invoice, Receipt, PR | | `confirmedPo`, `approvedInvoice`, `receivedReceipt`, `approvedPr`; delete після use | | 3 |
| T1-09 | API-preparation: no_dcf_company | | s/test 130 → ≤ 45 | machine-time проекту | 3 |
| T1-10 | API-preparation: common_company | | s/test 75 → ≤ 40 | | 5 |
| T1-11 | Codemod `allure.*` → `test.step`/`attach` | 003 | Lint проти `allure-js-commons` | `allure.` 12 000 → 0 | 3 |
| T1-12 | Codemod `expect(await isVisible())` → web-first | | lint `prefer-web-first-assertions` без винятків | 511 → 0 | 2 |
| T1-13 | Codemod sleeps | | `no-wait-for-timeout` error | 121 → 0 | 2–3, з прогонами |
| T1-14 | Розбиття minor/common/invoice/items/budgets | | Жоден проект > 45 хв | найдовший проект | 2 + окремі юзери |
| T1-15 | Tiering-теги і Jenkins-параметр рівня | | `@gate` ≤ 15 хв збалансований по проектах | | 3 |
| T1-16 | Retries 1 + flaky-метрика + карантин | 006 | Конфіг; дашборд; політика узгоджена | | 1 + розмова |

## Далі
Фази 2–4 деталізуються, коли фаза 1 дасть цифри. Кандидати вже названі в `phases.md` і у файлах `04-target/`.

## Додано 2026-09-16
| ID | Задача | Фаза | DoD | Оцінка |
|---|---|---|---|---|
| T0-12 | Маніфест снапшоту + preflight у globalSetup | 0 | Маніфест для 5 найбільших компаній; preflight падає з точним повідомленням при відсутній сутності | 2 |
