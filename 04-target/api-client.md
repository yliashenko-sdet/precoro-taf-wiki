---
_organized: true
---
# API-клієнт

ADR-005. Задача T1-07 (обгортки до генерації), повна генерація у фазі 3.

## Два клієнти
| Клієнт | Джерело | Стабільність | Приклади |
|---|---|---|---|
| `publicApi` | Swagger, генерується | контракт | документи, items, suppliers, budgets, approval steps, custom fields |
| `internalApi` | ручні обгортки з network | без гарантій | `updateCompanyConfiguration`, `entity_template`, users, roles, warehouses, Control |

## Куди розкладається `precoro_service.ts` (T3-06)
Сьогодні один клас на ~260 методів і чотири ролі. Файл не видаляється одним кроком, а розкладається:

| Роль | Куди |
|---|---|
| Транспорт і типи | генеруються зі специфікації (T1-25) |
| Методи з людськими іменами (`getItemPrice`, `approvePo`) | доменні модулі `api/items`, `api/po`, ...; домени за тегами специфікації |
| Сценарії з кількох кроків (додати товар з каталогу, документ у статусі X) | підготовка даних: фікстури і builders (T1-07, етап 2) |
| БД, тестові дані, хелпери дат | з клієнта геть; БД через T3-08 |

Порядок (2026-09-29): спершу типи (T1-25), потім розкладання. Імпорти змінюються двічі, але codemod ідемпотентний, а типи дають межі доменів.

## Поведінка
- Non-2xx кидає `ApiError` з методом, шляхом, статусом і тілом. Негативний сценарій: `api.po.confirm(idn, { expect: 422 })`.
- Кожен виклик у `test.step` з атачами запиту і відповіді.
- Заголовки: `X-AUTH-TOKEN`, `X-AUTO-TESTS`, `X-Test-Id`.
- Таймаут 30 s, без ретраїв у клієнті; polling лише явний через `expect.poll`.

## Обгортки, яких бракує для "документ у статусі X" (T1-07)
`mass-approve`, `mass-reject`, `approve-review`, `take_over_revise` для всіх документів; `revise` для PR/WR/RFP/Expense; `receipts/receive_all`; `purchaseorders/send`, `manual_complete`, `approve_matching*`; `payments/pay`; `*_documents_import`; `*/revisions`.
