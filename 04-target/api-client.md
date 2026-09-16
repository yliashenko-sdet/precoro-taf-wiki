# API-клієнт

Рішення: ADR-005 (proposed).

## Два клієнти
| Клієнт | Джерело | Стабільність | Приклади |
|---|---|---|---|
| `publicApi` | Swagger, генерується | контракт | документи, items, suppliers, budgets, approval steps, custom fields |
| `internalApi` | ручні обгортки, з network | без гарантій | `updateCompanyConfiguration`, `entity_template`, users, roles, warehouses, Control |

## Поведінка
- Non-2xx кидає `ApiError` з методом, шляхом, статусом і тілом. Негативні сценарії: `api.po.confirm(idn, { expect: 422 })`.
- Кожен виклик у `test.step` з атачами запиту і відповіді (перенос із `requests.ts`).
- Заголовки: `X-AUTH-TOKEN`, `X-AUTO-TESTS`, `X-Test-Id` (для Sentry).
- Таймаут 30 s, без ретраїв на рівні клієнта; polling лише явний через `expect.poll`.

## Швидкі перемоги ще до генерації
Дописати ~55 lifecycle-обгорток, яких бракує: `mass-approve`, `mass-reject`, `approve-review`, `take_over_revise` для всіх документів; `revise` для PR/WR/RFP/Expense; `receipts/receive_all`; `purchaseorders/send`, `manual_complete`, `approve_matching*`; `payments/pay`; `*_documents_import`; `*/revisions`. Це відкриває "документ у статусі X" без UI для дорогих проектів.

## Храповик
Імпорти `precoro_service` → 0. Покриття Swagger у клієнті: зараз ~177/507.
