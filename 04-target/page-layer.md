---
_organized: true
---
# Page-шар

ADR-004. Фаза 3, після API-preparation.

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

## Редизайни: відповідь фреймворку
UI змінюється часто, і фреймворк має переживати це без переписування тестів. Чотири механізми, кожен окремо недостатній:

1. **`data-test-id` як контракт між фронтендом і тестами.** Вони в продукті вже є масово (256 на одній сторінці), тож контракт це не запит на нове, а формалізація наявного: одна конвенція імен замість двох і правило про зміни. Локатор це не пошук по верстці, а адреса, яку фронтенд обіцяє не змінювати без узгодження. Пріоритет `getByTestId`, XPath і класи в нових локаторах заборонені lint-ом. Інвентар усіх test-id, які використовує TAF, генерується скриптом і перевіряється на боці фронтенду: PR, що видаляє або перейменовує test-id з інвентарю, червоний або вимагає позначки AQA (T2-09). Так редизайн видно до мержу, а не в нічному прогоні.
2. **Один компонент на елемент UI.** Редизайн таблиці позицій це зміна `ItemsTable`, не 300 тестів. Сторінка не знає, як влаштована кнопка підтвердження, вона знає `actions.confirm`. Це ADR-004, і саме редизайни є головним аргументом за компоненти, сильнішим за читабельність.
3. **Перевірки семантичні, не візуальні.** Тест перевіряє статус, суму, наявність документа в списку, а не позицію, колір чи текст кнопки. Візуальна регресія лише в окремому проекті `@visual` поза gate. Текст у локаторах лише через i18n і лише там, де нема test-id.
4. **Процес для змін спільного UI.** PR фронтенду, що змінює спільний компонент або йде під модулем "New Design", позначається; TAF запускає повний прогін на цій гілці до мержу, а не smoke; AQA отримує список зачеплених компонентів з інвентарю test-id (T1-21, `conventions.md`). Редизайн під feature-флагом: тести явно знають, який варіант увімкнений у компанії, і не вгадують.

Показник: кількість тестів, що падають через зміну селекторів на один UI-PR. Ціль: не більше за кількість зачеплених компонентів.

## Що зникає
13 mixin-ів, `declare`-поля, `strip-declare-class-fields.js`, `locators!:` повтори, `'{}'` плейсхолдери і `.replace('{}')`, форковані сторінки, `*ByIndex` методи там, де є семантичний локатор, `expect*` методи в page-класах (599).
