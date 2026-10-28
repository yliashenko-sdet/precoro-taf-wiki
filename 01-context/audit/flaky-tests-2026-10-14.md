---
_organized: true
_width: wide
---
# Найбільш flaky тести нічного прогону

Знято 2026-10-14 скриптом `06-playbooks/scripts/allure_flaky_by_build.py` з `data/suites.json` Allure-звітів job `Daily autotests - all tests`. Jenkins зберігає 31 останню збірку, з них повних (довше 2,5 год) 21: №251 (21.09) … №281 (14.10).

Вхід: `<JENKINS_URL>/job/Daily%20autotests%20-%20all%20tests/<build>/allure/data/suites.json` кожної збірки, збережений як `<build>.json` (Basic auth змінними `JENKINS_*` з `.env` TAF).

```bash
python3 06-playbooks/scripts/allure_flaky_by_build.py <тека з <build>.json> --top 50 --csv out.csv
```

## Метод

- На кожну ніч у тесту один стан: пройшов з першої спроби, **flaky** (пройшов після ретраю, як рахує flaky-метрика), або фінально впав. Flaky rate = flaky-ночі / ночі, коли тест виконувався.
- Ретраї видно лише в `suites.json` кожної збірки. Історія Allure (`history.json`) зберігає тільки фінальний статус, тому flaky там не видно; крім того, між №271 і №277 вона обірвалась.
- Масові ночі, коли фінально впало понад 10% тестів, виключено як падіння середовища: №260 (28.09, 19,5%), №265–268 (02–05.10, 12–28%), №281 (13.10, 12,4%). Лишилось 15 ночей.
- Тест ідентифікується за (проект, файл, назва, параметри). Тести, перейменовані або перенесені за цей період, мають коротшу серію: наприклад, `documents/budget/test_budgets.spec.ts` має лише 8 ночей.
- Гілкових прогонів тут нема. Branch smoke йде на іншому Jenkins, а доступ є лише до QA Jenkins; локально є один гілковий звіт з одним прогоном.

## Загальна картина

| Що | Значення |
|---|---|
| Тестів з ≥ 8 ночами | 2 114 |
| Flaky хоч раз | 183 (8,7%) |
| Flaky-подій за 15 ночей | 347 |
| Частка подій у топ-50 тестів | 57% |
| Flaky за ніч | 0,6–2,8% виконаних (15–59 тестів) |
| Розподіл flaky rate | ≥ 50%: 7 тестів; 20–50%: 42; 10–20%: 22; до 10%: 112 |

Кластери за файлами (частка всіх flaky-подій): `documents/budget/test_budgets.spec.ts` 14% (20 тестів, імпорт бюджетів), `test_reports.spec.ts` 11% (15), `test_supplier.spec.ts` 8% (12), `test_invoice_documents.spec.ts` 7% (8), `test_po_cancel_remove_module.spec.ts` 6% (9), `test_configurations.spec.ts` 6% (9).

Фінальні падіння в не масових ночах становлять 0,5–6,5% (найменше 29.09–01.10), а 11–12.10 це 6,1% і 8,7%. Тобто нічний прогін червоний не через flaky, а через тести, що падають стабільно; це окремий розбір.

## Топ-40 за flaky rate (мінімум 3 flaky-ночі)

Патерн: `.` пройшов з першої спроби, `f` пройшов після ретраю, `X` фінально впав. Ночі по порядку: 21.09, 22.09, 23.09, 24.09, 25.09, 26.09, 27.09, 28.09, 29.09, 30.09, 01.10, 06.10, 07.10, 11.10, 12.10 (у тестів з коротшою серією це останні з них).

| # | Flaky | Фінально впав | Ночей | Патерн (старі → нові) | Проект | Файл | Тест |
|---:|---:|---:|---:|---|---|---|---|
| 1 | 88% (7) | 1 | 8 | `Xfffffff` | import_documents_company | `Import PR Documents tests` | Happy path: basic import with all valid data (HP-1) |
| 2 | 87% (13) | 0 | 15 | `f.fff.fffffffff` | invoice_company | `test_invoice_documents.spec.ts` | Verify Invoice cannot be rejected with active Credit Note |
| 3 | 62% (5) | 0 | 8 | `fff..ff.` | hundred_plus_company | `documents/budget/test_budgets.spec.ts` | Import budget only with icf sub options [ICF] |
| 4 | 60% (9) | 3 | 15 | `fXfXX.ffff.fff.` | control | `test_control.spec.ts` | Create new demo account with template |
| 5 | 53% (8) | 3 | 15 | `fXfXXff.f..fff.` | billing_precorino | `test_billing.spec.ts` | Pay invoice for Plan change |
| 6 | 50% (4) | 0 | 8 | `.f.fff..` | budgets_company | `documents/budget/test_budgets.spec.ts` | Import budget without icf and dcf |
| 7 | 50% (4) | 0 | 8 | `f..fff..` | hundred_plus_company | `documents/budget/test_budgets.spec.ts` | Import budget with 100+ dcf options [DCF] |
| 8 | 47% (7) | 4 | 15 | `XX.Xf.Xf.fffff.` | control | `test_control.spec.ts` | Create new demo account without template |
| 9 | 47% (7) | 1 | 15 | `fX..f..ff.ff.f.` | reports_company | `test_reports.spec.ts` | User runs custom report with each individual filter Invoice - Creation Date, DCF Option from PO (text) |
| 10 | 47% (7) | 1 | 15 | `.fffX..f..ff.f.` | reports_company | `test_reports.spec.ts` | User runs custom report with each individual filter Receipt - Creation Date, DCF Option from PO (text) |
| 11 | 40% (6) | 8 | 15 | `.fffXXXXfffXXXX` | supplier_company | `test_supplier.spec.ts` | Edit registration template |
| 12 | 40% (6) | 2 | 15 | `fffXfff.......X` | supplier_company | `test_supplier.spec.ts` | Supplier show page visual regression |
| 13 | 38% (3) | 0 | 8 | `...ff.f.` | budgets_company | `documents/budget/test_budgets.spec.ts` | Import budget by code |
| 14 | 38% (3) | 0 | 8 | `f.f.f...` | budgets_company | `documents/budget/test_budgets.spec.ts` | Import 2 budgets with same dcf and icf |
| 15 | 38% (3) | 0 | 8 | `.f.ff...` | hundred_plus_company | `documents/budget/test_budgets.spec.ts` | Import budget only with dcf sub options [DCF] |
| 16 | 38% (3) | 0 | 8 | `..f..ff.` | hundred_plus_company | `documents/budget/test_budgets.spec.ts` | Import budget with all and single options in different sub lines [ICF] |
| 17 | 38% (3) | 0 | 8 | `..f.ff..` | hundred_plus_company | `documents/budget/test_budgets.spec.ts` | Import budget with 100+ icf options [ICF] |
| 18 | 27% (4) | 5 | 15 | `.f...ff.Xf.XXXX` | supplier_company | `test_supplier.spec.ts` | Disable registration template |
| 19 | 27% (4) | 2 | 15 | `..ff....f.f..XX` | remove_company | `documents/po/po_cancel_tests/test_po_cancel_remove_module.spec.ts` | Cancel button hidden outside allowed PO statuses (Completed) — FromPrPOStrategy PO |
| 20 | 27% (4) | 2 | 15 | `.X.ff...X.ff...` | reports_company | `test_reports.spec.ts` | User runs custom report with each individual filter Receipt - Creation Date, DCF Option from Receipt (text) |
| 21 | 27% (4) | 2 | 15 | `XffX..f......f.` | no_dcf_company | `test_configurations.spec.ts` | Invoice - Approval Review status |
| 22 | 27% (4) | 1 | 15 | `..f...ff.f...X.` | minor_company | `test_pr_documents.spec.ts` | Approve PR by backup approver |
| 23 | 27% (4) | 1 | 15 | `ff..f.f.......X` | no_dcf_company | `test_configurations.spec.ts` | Receipt - Approval Review status |
| 24 | 27% (4) | 0 | 15 | `.ff......f...f.` | minor_company | `test_reports.spec.ts` | User runs, deletes custom report |
| 25 | 27% (4) | 0 | 15 | `fff.........f..` | minor_company | `test_rfp.spec.ts` | Check RFPs conducted from PR |
| 26 | 27% (4) | 0 | 15 | `...........ffff` | invoice_company | `test_invoice_documents.spec.ts` | Create match invoice / approve it by super user |
| 27 | 27% (4) | 0 | 15 | `.ffff..........` | reports_company | `test_reports.spec.ts` | User runs custom report with each individual filter Stock Transfer - Creation Date, DCF Stock transfer(text) |
| 28 | 27% (4) | 0 | 15 | `.ff.f.......f..` | reports_company | `test_reports.spec.ts` | User runs custom report with each individual filter Payment - Payment Date, Purchase order type |
| 29 | 20% (3) | 5 | 15 | `.XXfXXffX......` | approval_regression | `test_approval.spec.ts` | PO parallel approve - changing approval |
| 30 | 20% (3) | 4 | 15 | `XXX........fXff` | approval_workflow_test | `test_approval_workflow.spec.ts` | When DCF 'Limit access to documents' is enabled and the sole approver lacks user-level access to the docume… |
| 31 | 20% (3) | 3 | 15 | `X.ffX..fX......` | common_company | `test_filters.spec.ts` | Verify item management filters with lambda functions - item_management_page - Name filter |
| 32 | 20% (3) | 3 | 15 | `.Xf...X.f..f..X` | no_dcf_company | `test_configurations.spec.ts` | WR - Approval Review status |
| 33 | 20% (3) | 2 | 15 | `.......f..f.fXX` | remove_company | `documents/po/po_cancel_tests/test_po_cancel_remove_module.spec.ts` | Cancel button hidden outside allowed PO statuses (Completed) — FromPrSPOStrategy SPO |
| 34 | 20% (3) | 2 | 15 | `...f....f.f..XX` | remove_company | `documents/po/po_cancel_tests/test_po_cancel_remove_module.spec.ts` | Cancel button hidden outside allowed PO statuses (Completed) — SPO fromPr=true CF |
| 35 | 20% (3) | 2 | 15 | `fX...f....f...X` | no_dcf_company | `test_configurations.spec.ts` | Expense - Approval Review status |
| 36 | 20% (3) | 1 | 15 | `........fffX...` | main_company | `test_common_functional.spec.ts` | Test document preview functionality — Test document preview fields and table on PR page |
| 37 | 20% (3) | 1 | 15 | `.X..f.....f..f.` | po_company | `documents/bpo/test_bpo.spec.ts` | Create BPO with portal supplier |
| 38 | 20% (3) | 0 | 15 | `.......ff.f....` | remove_company | `documents/po/po_cancel_tests/test_po_cancel_remove_module.spec.ts` | Cancel button hidden outside allowed PO statuses (Completed) — BPOPerItemsStrategy BPO |
| 39 | 20% (3) | 0 | 15 | `.......f....f.f` | items_company | `test_inventory.spec.ts` | Revise receipt with warehouse |
| 40 | 20% (3) | 0 | 15 | `.....f..f.f....` | items_company | `Items tests` | When a supplier is disabled, its items are disabled. |

Повний список (2 114 тестів з усіма колонками) відтворюється тим самим скриптом з `--csv`.

## Як читати

- Тест, у якого серед `f` є `X`, нестабільний сильніше, ніж показує flaky-метрика: з одним ретраєм він іноді не встигає пройти. Наприклад, `Edit registration template` (6 flaky + 8 впав), `Create new demo account …`, `Pay invoice for Plan change`.
- Серія `XXXX` без `f` означає, що тест зламаний, а не flaky; такі тести в цей список не потрапляють.
- `Supplier show page visual regression` (40%) — візуальний тест з T2-06. Він був flaky 21–27.09, далі пройшов чисто 7 ночей і впав 12.10.

## Чому падали: причини і кроки (топ-40)

Джерело: `test-cases/<uid>.json` кожної збірки для flaky- і fail-ночей топ-40, а для flaky-ночей ще й невдала перша спроба (`extra.retries`). Разом 296 невдалих спроб; 232 з них лягають у 12 причин нижче. Рядки коду вказано за `origin/develop` на 14.10.

| Спроб | Тестів | Причина | Де | Тип |
|---:|---:|---|---|---|
| 35 | 5 | Посилання з листа в MailPit не відкриває нову вкладку за 60 с (`waitForEvent('popup')`) | `MailpitPage.clickGoToPrecoroBtnInEmail` → `BasePage.switchTab`; `control`, `billing_precorino`, реєстрація постачальника | тест або доставка листа; щоночі |
| 34 | 5 | `Cannot read properties of undefined (reading 'fill' / 'click')`: `locator(...).all()` без очікування повертає порожній масив, далі `[0].fill()` | `reports_page.ts:610` `fillInPoTypeField`, `:699` `fillInTextCfByName`; `test_reports.spec.ts`, крок "open custom report" | дефект тесту (`.all()` не чекає) |
| 29 | 2 | Шаблон реєстрації постачальника: нема опції `TestForm_CreatedBeforeTest`, поле `payment_terms` не приєднане, таблиця шаблонів порожня | `test_supplier.spec.ts`, "Edit registration template", "Disable registration template" | залежність від даних іншого тесту (гіпотеза); з 06.10 майже щоночі |
| 29 | 4 | Фікстура Approval Review: нема селекта апрувера `input:manage_approver.user` або чекбокса `delete_approver_confirm_impact` | фікстури `setUp{Invoice,Receipt,WR,Expense}ApprovalReview`, `no_dcf_company` | підготовка через UI; 12.10 впали всі чотири |
| 27 | 8 | Дейтпікер імпорту бюджету не закривається: `Enter` лишає 1–2 видимі `.el-picker__popper`, `toPass` здається через 15 с | `budget_page.ts:719` `closeImportDatePicker` ← `fillEndDateOnImport` | дефект тесту (спосіб закриття); щоночі з 28.09, відколи файл існує |
| 25 | 4 | Підготовка PO через API: `createPoFromPr failed: 400`, далі статус 403 замість 200 на створенні Receipt/Invoice | `po_strategy.ts:1427` `draftDocument`; `test_po_cancel_remove_module.spec.ts` | API або дані `remove_company`; 11–12.10 по 6 |
| 13 | 4 | Не з'явився `toast:success` | імпорт PR, бюджети, реєстрація | таймінг; деталей мало |
| 13 | 1 | Кредит-нота: нема кнопки видалення в `table:previous_payments` | "Verify Invoice cannot be rejected with active Credit Note", крок "Create and confirm Credit Note" | щоночі з першої спроби, після ретраю проходить |
| 10 | 1 | Скриншот відрізняється на ~22 тис. пікселів (2%), стабільно, при порозі 0,5% | "Supplier show page visual regression" | залежить від стану даних на сторінці (гіпотеза: після ретраю дані інші) |
| 9 | 3 | Список мов `documentLocales` не в очікуваному стані | `control`, `billing_precorino` | лише 21–27.09 |
| 6 | 1 | `Failed to create user`: 500 / 400 від API | фікстура `createdApproverUserWithDcfOption` | бекенд; лише 21–23.09 |
| 2 | 1 | `page.getDcfValueOnDocPageByIndex is not a function` | `assertion_helpers.ts:150` | дефект коду 06.10; методу вже нема в `develop` |

Решта 64 спроби розкидані по одиночних локаторах (`search_result_link` за 7 с, `validity_period`, опції складу тощо).

Висновки:
- Більшість flaky — це дефекти коду тестів, а не продукту: `.all()` без очікування, закриття дейтпікера через `Enter`, чекання popup на посилання з листа. Ці три місця дають 96 спроб із 296 (третину), і кожне виправляється в одному методі.
- Підготовка даних через UI у фікстурах (Approval Review) і через API (`createPoFromPr`) — друга група. Її скорочує перенос підготовки в API або seed.
- Падіння бекенду (500 на створенні користувача) поодинокі й обмежені кількома днями.

## План виправлень (затверджено 14.10 як частина 2 задачі T0-18)

Причини уточнено по коду `origin/develop` (14.10), кроках Allure, скриншотах і тілах відповідей невдалих спроб. Номери тестів — з таблиці топ-40 вище. Шляхи відносно `src/`.

Правила для всіх кроків (`docs/test-conventions.md`, скіл `playwright-best-practices`, `debugging/flaky-tests.md`): виправляється причина. Без `waitForTimeout`, без більших таймаутів, без `try/catch` з `force`, без ретраїв. Чекаємо на результат дії (відповідь, статус, web-first assertion), а не на час.

Один PR на одну причину (рядок таблиці). Перевірка PR: `--repeat-each=10` на зачеплених тестах на локальному стеку, де проект біжить локально. Умова "тест більше не flaky": 7 поспіль не масових нічних прогонів без `f` і `X` за `allure_flaky_by_build.py`.

### Етап 0. Уже виправлено в `develop`, лише підтвердити нічними

| Тести | Що було | Чим виправлено |
|---|---|---|
| #4, #5, #8 (частина `documentLocales`) | клік по опції PrimeVue під час анімації | новий `fillInDocumentLocales` з `toPass`; падінь після 28.09 нема |
| #31 Name filter | пошук до появи нового елемента | `eeea1050` (29.09) |
| #25 RFP з PR | загублений клік "Select all" | `694e32d6` (23.09), `toBeChecked` |
| #18 Disable registration template | продукт перейменував `data-test-id` | `3fe0b391` (14.10) |
| #29 PO parallel approve | одноразове читання і цикл перезавантажень | T1-12 і T1-13; з 05.10 проходить |
| #30 (лише 21–23.09) | у тілі створення користувача не було `companyUsers` | `b4254523` (25.09) |

### Етап 1. Дефект коду тесту, причина встановлена (висока впевненість)

| # | Тести | Причина | Виправлення | Де |
|---|---|---|---|---|
| 1.1 | #4, #5, #8, частина #11 і #18 | MailPit дописує `target="_blank"` асинхронно; клік до цього відкриває посилання всередині iframe, тож вкладки нема. Плюс `waitFor().catch(() => false)` дає `undefined`, тому сторінка перезавантажується щоразу | 5 методів `click…InEmail` перевести на наявний `openEmailLinkByLabel` (href з API MailPit + `newPage().goto`); прибрати гілку з перезавантаженням | `mailpit_page.ts:141, 152, 161, 176, 259` |
| 1.2 | #9, #10, #20, #27, #28 | `locator.all()` не чекає, `[i]` на порожньому масиві дає `undefined` | `locator.nth(i).fill()`; `filter({ visible: true }).first().click()` | `reports_page.ts:610, 699` |
| 1.3 | #3, #6, #7, #13–#17 | `closeImportDatePicker` рахує попапи до відкриття і не тисне `Enter`; попап старту лишається відкритим | `fill` → `toHaveCount(1)` → `press('Enter')` → `toHaveCount(0)` без `toPass` і без умовного `Enter`, для обох дат | `budget_page.ts:719-743` |
| 1.4 | #37 BPO | проба `validityPeriod` 6 с, далі 60 с на застарілому id | один локатор `regular.or(legacy)` + `toBeVisible` | `action_buttons_mixin.ts:546-559` |
| 1.5 | #24 custom report | наведення один раз, потім `waitFor` 60 с всередині `toPass`; одна ітерація | дочекатись готовності сторінки, потім `hover` і `expect(tooltip з текстом).toBeVisible()` | `reports_page.ts:741-757` |
| 1.6 | #12 visual Supplier (частина a) | знімок робиться, поки сторінка постачальника ще на спінері: очікування спрацьовують на сторінці списку | `toHaveURL` сторінки постачальника + видимий заголовок перед знімком. Дрейф даних (частина b) лишається в T2-06 | `test_supplier.spec.ts:3138-3167` |

### Етап 2. Дія без очікування результату (середня впевненість, перед PR подивитись трейс T0-09)

| # | Тести | Причина | Виправлення | Де |
|---|---|---|---|---|
| 2.1 | #2 Credit Note | після Confirm одразу перехід на інвойс; платіж ще не створено | `expectStatusConfirmed()` кредит-ноти перед переходом | `test_invoice_documents.spec.ts:3249-3260` |
| 2.2 | #26 match invoice | Confirm через 0,1 с після Save ціни; збереження ще не завершене | `waitForResponse` збереження позиції в `acceptItemEditing`, перед кліком | `item_mixin.ts:239-247` |
| 2.3 | #1 Import PR HP-1 | шаблон качається в `beforeAll`, до фікстур, що міняють колонки; файл застарілий, тост помилки | шаблон у тесті або в фікстурі після налаштувань; чекати `toast:success.or(toast:error)` | `test_import_pr.spec.ts:81-85, 270-279` |
| 2.4 | #39 warehouse | опція клікається в закритому селекті; підрядкове `data-test-id*=` + `.first()` знаходить приховану | дочекатись готовності форми, відкрити, `expect(видима опція).toBeVisible()`, точна назва | `receipt_page.ts:95-101` |
| 2.5 | #21, #23, #32, #35 Approval Review | клік "Add approver" до того, як сторінка кроків готова | чекати відповідь кроків перед кліком, `expect(modal input).toBeVisible()` після; надалі сетап через API (`ApproverBuilder`) | `approval_workflow_page.ts:103-123` |
| 2.6 | #36 preview | поля і нотатка читаються одноразово через 0,1 с; документ береться "перший Approved" зі спільних даних | `toContainText` / `toHaveText` замість читання; власний документ через API | `base_document.ts:1363-1392`, `test_common_functional.spec.ts:150-170` |

### Етап 3. Передумова в даних (висока або середня впевненість, зміни у фікстурах)

| # | Тести | Причина | Виправлення | Де |
|---|---|---|---|---|
| 3.1 | #19, #33 PO cancel FromPr | після заміни даних 05–06.10 у PR є крок погодження → PR Pending → `Not found checked items for PO` (400); варіант Approval Review вмикає `blockAutoApproval` до створення PR | `FromPr*Strategy.draftDocument` гарантує Approved PR (погодити й перевірити статус 2); PR створювати до `blockAutoApproval` | `po_strategy.ts:1397-1427`, `api_fixtures.ts:1377` |
| 3.2 | #34, #38 (і 403 у #19) | крок Receipt відновлюється лише в teardown; наступний тест стартує без кроку, receipt одразу Approved, approve дає 403 | забезпечити крок і апрувера до `use()`; перевіряти Pending після створення і 200 на approve (зараз 403 ігнорується мовчки) | `approval_workflow_fixtures.ts:567-610`, spec `:204, 425, 489` |
| 3.3 | #11 Edit registration template | у компанії нема логотипа (чекбокс вимкнений); один спільний шаблон з перемиканням "прочитав → клікнув" | логотип у сетапі компанії (або прибрати перевірку логотипа з кейсу); шаблон на тест через API з видаленням; `setChecked()` замість перемикання з `force` | `supplier_registration_form_page.ts:308-354`, `api_fixtures.ts:168-206` |
| 3.4 | #40 disabled supplier → items | деактивація позицій асинхронна на бекенді | `expect.poll` статусу позиції через API, потім перевірка UI | `test_items.spec.ts:1219-1229` |
| 3.5 | #22 backup approver | відпустка вмикається після підтвердження PR; перепризначення асинхронне | відпустку і заступника через API до створення PR | `test_pr_documents.spec.ts:858-905` |

### Етап 4. Причина не встановлена: спершу трейс

#30 (падіння 06–12.10, інша причина, ніж API користувача), #10b (вкладка відпустки 11.10), розкидані `toast:success`, B3 (`status:approval_review`). Трейс першої невдалої спроби з нічного прогону (T0-09) → причина → рядок у таблицю вище.

### Поза планом: патерни, а не тести

Ті самі дефекти є далеко за межами топ-40. Кожен лягає в кодмод або правило гейта, а не в точкові PR: `.all()` + `[i]` (~111 місць у 29 файлах), проба з коротким таймаутом і гілкою (~205 `.then(() => true)`), підрядковий `dropdown_option_by_name` + `.first()` (73), перемикання "прочитав → клікнув" для чекбоксів (16), `clickAddUserForStep` (67 викликів), `_clickActionButton` без очікування результату. Записати в `findings.md`.
