# Page-шар

Рішення: ADR-004 (proposed). Робиться після API-preparation.

## Ціль
```ts
class PoPage extends DocumentPage {
  static url = (idn: number) => `/purchase-orders/${idn}`;
  readonly items = new ItemsTable(this.page.getByTestId('items-table'));
  readonly attachments = new Attachments(this.page);
  readonly status = new StatusBadge(this.page);
  async confirm() { await this.actions.confirm.click(); }
}
```
- Компонент: клас із root `Locator`, полями-локаторами, діями. Без assertion, без `test.step`.
- Assertion у тестах: `await expect(po.status.badge).toHaveText('Approved')`. Спільні перевірки як кастомні матчери `expect(po).toHaveStatus('Approved')`.
- Локатори: `getByTestId` → `getByRole` → i18n-текст → CSS. Параметризовані як функції з екрануванням.
- Один компонент на UI-елемент, а не на документ: `ItemsTable` спільна для PO, Invoice, PR.

## Реальні різні сторінки
Зараз 27 класів наслідують `BaseDocumentPage`, серед них `taxes_page`, `reports_page`, `audit_log_page`, `location_page`, `payment_terms_page`, які документами не є. Кожен отримує всі ~700 методів: PR-сторінка має методи платежів і receipt, сторінка податків уміє додавати позиції з каталогу. Реальних різних сторінок нема.

З композицією сторінка описує лише те, що на ній є:

```ts
class PrPage extends DocumentPage {          // header, status, actions, comments, attachments
  readonly items = new RequestItems(page);
  readonly related = new RelatedDocs(page);
}
class InvoicePage extends DocumentPage {
  readonly items = new BillableItems(page);  // податки, знижки
  readonly payments = new PaymentsTable(page);
  readonly matching = new MatchingPanel(page);
}
class TaxesPage extends SettingsPage {       // не документ
  readonly list = new SettingsList(page);
}
```

- `InvoicePage` має `payments`, `PrPage` ні; компілятор не дасть викликати `pr.payments`.
- Два тонкі базові класи: `DocumentPage` (спільне для всіх документів) і `SettingsPage` (сторінки конфігурації).
- Спільне живе в компонентах, не в базовому класі: одна `ItemsTable`, один `StatusBadge`, один `ConfirmModal`. Дубльовані селектори (142) зникають, бо `button:save` визначений один раз.
- Мертвий код стає видимим: метод належить компоненту, незадіяний компонент не створюється.

Відкрите питання про generic-компоненти (одна `ItemsTable` з параметром колонок чи базовий клас із тонкими підкласами) вирішується на перших двох сторінках. Починати з PO і Invoice: найбільше спільного і найбільше різного одночасно.

## Що зникає
13 mixin-ів, `declare`-поля, `strip-declare-class-fields.js`, `locators!:` повтори, `'{}'` плейсхолдери і `.replace('{}')`, форковані сторінки, `*ByIndex` методи там, де є семантичний локатор, `expect*` методи в page-класах (599).

## Порядок
1. Компоненти для того, що найчастіше в тестах: items table, status, toast, confirm modal, attachments.
2. Нові тести лише через компоненти.
3. Форковані пари зливаються через компоненти.
4. Legacy mixin-и видаляються при нулі call-site.

## Контрольні лічильники
`this.xxxLocators.` (1 814), `xpath=` (1 047), `expect(` у pages (700), `force`/`clickUsingJavascript` (~420), `.first()` (717).
