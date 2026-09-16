# Модулі в Asana і теги в TAF

Джерело: поле модуля в задачах Asana, 112 значень (список нижче, отримано 2026-09-17). Джоба Jenkins запускає smoke + модуль за значенням цього поля або повний прогін на "All modules". Реалізовано лише для PO: теги `@po_purchase_order`, `@so_service_order`, `@bpo_blanket_purchase_order` у 20 файлах із 71.

## Конвенція тега
З наявних прикладів: абревіатура, якщо є, плюс повна назва у snake_case, латиницею. `PO (Purchase Order)` → `@po_purchase_order`. Як саме Jenkins перетворює назву з Asana на grep, невідомо (питання #20).

## Правила, які випливають із масштабу
1. 112 модулів проти 71 файлу: тег ставиться на describe або тест, не на файл. Один тест може мати кілька тегів модулів (інвойс із податками це `@invoice` і `@taxes`).
2. Мапа "назва в Asana → тег" живе в одному файлі TAF (`modules.ts`) і використовується двічі: lint або preflight перевіряє, що кожен тест має тег із мапи, а Jenkins бере grep із неї ж. Перейменування модуля в Asana тоді ламає збірку голосно, а не мовчки запускає порожній набір.
3. Модулі діляться на чотири класи, і для кожного явно записано, що біжить на PR:

| Клас | Приклади | Що біжить на PR |
|---|---|---|
| Продуктовий модуль з E2E-тестами | Invoice, PO, PR, Budget, Approval, Reports, Suppliers, OCR (AI Document Scanning) | smoke + тести з тегом модуля |
| Наскрізний | Sum, Calculations, Front, New Design, Security, Performance, Navigation, Preview, Dependencies, Filters, Mass actions | повний прогін, бо зміна зачіпає всі модулі |
| Без E2E у TAF | Hotglue, Power BI, Sendgrid, Elastica, Translain, Knowledge Base, Mobile Application, Messenger, MS Teams, Slack, Stripe payments, Virtual cards, e-Invoice, AI Agents | smoke, і це записано явно, щоб "зелений" не читався як "покрито" |
| Службові | All modules, Temporary (for module Users), Integration Monitoring (automation) | повний прогін або окреме правило |

4. Кілька записів Asana мапляться на один тег: три "Supplier portal (...)" на `@supplier_portal` з уточненням, "Budget", "Budget Limit", "Budget Parts" на `@budget` з підтегами, "Revision History" і "Audit log" перевіряються разом.

## Груба оцінка покриття за назвами файлів
57 модулів мають файл-кандидат за ключовим словом у назві, 55 не мають. Оцінка неточна, бо багато модулів живуть усередині великих файлів; точна карта з'явиться після розмітки тегами (T1-15). Файли, які не зіставились ні з чим за назвою: `test_common_functional`, `test_price_auto_update`, `test_remove_behavior`, `test_100_plus_options`, `document_setup/test_so_from_pr_document_setup`.

## Повний список з Asana
Dashboard, Expenses, Budget, Budget Limit, Budget Parts, Inventory, Invoice, Credit Note, Matching, PR (Purchase Requisition), WR (Warehouse Request), PO (Purchase Order), SO (Service Order), BPO (Blanket Purchase Order), Receipts, RFP (Request for Proposals), Recurring PO/Invoice, Filters, Catalog, Items, PDF/XLS docs, Payments, Search, Supplier portal (Invoice), Supplier portal (PO), Supplier portal (RFP), Taxes, Currency, Revision History, 3 way match (pending receipt), Attachments, Split Costs, Discounts, Comments/Notes, Sum, Terms of Payment, Inventory Consumption, Stock Transfer, Exchange rates, Favourites, Mass actions, Google login, Configurations, Import/export, SSO, Account Settings, Locations, Custom numbering, Custom Forms, User Management, DCF / ICF, Approval, Multicompanies, Legal Entities, 2FA, Dependencies, Billing, Basic Settings, Control / Admin, Tolerance Limits, Audit log, Multiaccounts, Authentication / Login, Add-ons, Webhook, Units (UOM), Access (document limitation), View Only Self-Created Documents, Integration, Xero, QBO, NetSuite, Slack, Bill.com, SuiteApp, MS Teams, SCF (Supplier Custom Field), Contracts, Emails and notifications, Suppliers, Supplier portal (Registration), Supplier registration form, Sendgrid, Reports, Amazon, PunchOuts, AP, AI Agents, AI Document Scanning, e-Invoice, Stripe payments, Virtual cards, Mobile Application, Front, Hotglue, Power BI, API, Performance, All modules, Security, Translain, Elastica, Preview, Navigation, Calculations, Shipping, Knowledge Base, New Design, Integration Monitoring (automation), Temporary (for module Users), Messenger, Follower.
