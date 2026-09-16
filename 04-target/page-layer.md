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

## Що зникає
13 mixin-ів, `declare`-поля, `strip-declare-class-fields.js`, `locators!:` повтори, `'{}'` плейсхолдери і `.replace('{}')`, форковані сторінки, `*ByIndex` методи там, де є семантичний локатор, `expect*` методи в page-класах (599).

## Порядок
1. Компоненти для того, що найчастіше в тестах: items table, status, toast, confirm modal, attachments.
2. Нові тести лише через компоненти.
3. Форковані пари зливаються через компоненти.
4. Legacy mixin-и видаляються при нулі call-site.

## Храповики
`this.xxxLocators.` (1 814), `xpath=` (1 047), `expect(` у pages (700), `force`/`clickUsingJavascript` (~420), `.first()` (717).
