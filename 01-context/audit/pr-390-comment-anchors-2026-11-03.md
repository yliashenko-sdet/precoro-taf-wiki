# PR #390: review

Пункти плану закриття з [рев'ю PR #390](pr-390-review-2026-11-03.md), розділ 0. Рядки вказано на голові PR `fb01324e` (станом на 2026-11-03). Після рев'ю в PR лише мерджі `develop` і два коміти про DCF і tolerance limit, тож усі пункти ще відкриті.

«У диффі» — на рядку можна лишити inline-коментар. Шляхи — від `src/ui/web/`, якщо не вказано інше.

| # | Що виправити | Код |
| --- | --- | --- |
| 1 | 1490: backup approver має доходити до інвойсу через свій список (`clickApproveInfocard` з фільтром за idn), а не за URL | `tests/documents/invoice/test_invoice_approval.spec.ts:237` |
| 2 | 3003: унікальне значення ICF на кожен прогін і точна перевірка `=== 600` замість `> 500` | `tests/items/import/test_item_import_update.spec.ts:203` (+ `:156`) |
| 3 | Прибрати проєкти `invoice_company` / `items_company`, які лишились без тестів: конфіг, `PROFILES`, логіни в global setup | `playwright.config.ts:290` або коментар до файлу |
| 4 | Прибрати пароль з `testInfo.annotations` | `tests/documents/invoice/test_invoice_approval.spec.ts:206` |
| 5 | Негативні async-перевірки `price_auto_update`: контрольний item з увімкненим auto-update, дочекатися зміни його ціни, потім перевіряти решту | `tests/price_auto_update/test_auto_update_not_triggered.spec.ts:134` (+ 7 місць) |
| 6 | Нові спеки `price_auto_update` перевести з копій `StandardPOStrategy` / `BPOPerItemsStrategy` в `invoice_strategy` на класи з `po_strategy` | 6 спеків `tests/price_auto_update/` (рядок імпорту) |

## Деталі

**1. Тест 1490: backup approver відкриває інвойс за URL**
- `tests/documents/invoice/test_invoice_approval.spec.ts:237`, у диффі: `.gotoShowInvoiceByIdnUrl(invoiceIdn)`. Сюди коментар про те, що треба повернути `clickApproveInfocard` зі своїм списком.

**2. Тест 3003: фальшиво-зелена перевірка ICF**
- `tests/items/import/test_item_import_update.spec.ts:203`, у диффі: `expect(items.length).toBeGreaterThan(500)`. Сюди основний коментар.
- Той самий файл, `:156`, у диффі: `const textIcf = 'ez 500 update'`. Значення однакове на кожному прогоні, тому треба зробити його унікальним. Другим коментарем або згадати в першому.

**3. Проєкти `invoice_company` / `items_company`.** Самі визначення проєктів у PR не змінювались, тому inline-коментар на них не поставити. Варіанти:
- `playwright.config.ts:290`, у диффі: перший рядок нового блоку проєктів PR. Тут можна написати, що `invoice_company` (`:376`) і `items_company` (`:394`) лишились без тестів.
- Або коментар до всього файлу `playwright.config.ts`: GitHub дозволяє коментувати файл, а не рядок.
- Що ще прибрати, перелічити в тому самому коментарі:
  - `utilities/companies_data/index.ts:130` і `:138` (записи в `PROFILES`; логіни в global setup, ймовірно, йдуть звідси);
  - `src/config/test_users.ts:41-45` і `:202-205`.

  Найближчі рядки диффа — `index.ts:168` і `test_users.ts:90`.
- ⚠️ **Для автора:** користувачів `items_company` з `test_users.ts` прибирати не можна. `tests/fixtures/api_fixtures.ts:761`, `:785`, `:1094`, `:1137` досі логіняться під ними, і без них код не скомпілюється. Ці рядки старі, не з цього PR.

**4. Пароль в анотаціях**
- `tests/documents/invoice/test_invoice_approval.spec.ts:206`, у диффі: `JSON.stringify({ username: APPROVER, password: Constants.main_user_password })`.

**5. Перевірки «not triggered» нічого не доводять.** Усі рядки в диффі, бо файли нові:
- головний коментар — `tests/price_auto_update/test_auto_update_not_triggered.spec.ts:134`, тобто `expect.poll` у `expectCatalogPricesUnchanged`. Цю функцію викликають 8 тестів сюїти;
- ті самі перевірки в інших спеках `tests/price_auto_update/`:
  - `test_auto_update_on_approval.spec.ts:163`, `:202`, `:254`, `:310`;
  - `test_auto_update_on_revise.spec.ts:108`, `:176`;
  - `test_auto_update_prices.spec.ts:334`.

  На них досить коротких коментарів «те саме, див. :134» або одного списку в головному.

**6. Імпорт копій PO-стратегій з `invoice_strategy`.** Рядок `import {` блоку, що імпортує з `invoice_strategy`, у `tests/price_auto_update/`:
- `test_auto_update_not_triggered.spec.ts:25`;
- `test_auto_update_on_approval.spec.ts:18`;
- `test_auto_update_on_matching_and_paid.spec.ts:22`;
- `test_auto_update_on_revise.spec.ts:17`;
- `test_auto_update_prices.spec.ts:11`;
- `test_update_prices_by_catalog.spec.ts:11`.

Усі шість у диффі. Сьомий файл, `tests/test_items.spec.ts:10`, **не в диффі**: цей імпорт був і до PR. Його можна згадати в коментарі до будь-якого з шести.

## Окремо, не для цього PR

Фікстура `enableTwoDropdownScfForTest` налаштовує SCF через користувача `items_company` (`api_fixtures.ts:1094`). Але використовує її `test_supplier.spec.ts`, який працює в `@supplier_company`. Схоже, SCF створюється не в тій компанії. Так було й до PR, тож це кандидат у `findings.md`; ще не перевірено.
