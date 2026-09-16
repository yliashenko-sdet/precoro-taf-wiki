# API-клієнт

ADR-005. Задача T1-07 (обгортки до генерації), повна генерація у фазі 3.

## Два клієнти
| Клієнт | Джерело | Стабільність | Приклади |
|---|---|---|---|
| `publicApi` | Swagger, генерується | контракт | документи, items, suppliers, budgets, approval steps, custom fields |
| `internalApi` | ручні обгортки з network | без гарантій | `updateCompanyConfiguration`, `entity_template`, users, roles, warehouses, Control |

## Поведінка
- Non-2xx кидає `ApiError` з методом, шляхом, статусом і тілом. Негативний сценарій: `api.po.confirm(idn, { expect: 422 })`.
- Кожен виклик у `test.step` з атачами запиту і відповіді.
- Заголовки: `X-AUTH-TOKEN`, `X-AUTO-TESTS`, `X-Test-Id`.
- Таймаут 30 s, без ретраїв у клієнті; polling лише явний через `expect.poll`.

## Обгортки, яких бракує для "документ у статусі X" (T1-07)
`mass-approve`, `mass-reject`, `approve-review`, `take_over_revise` для всіх документів; `revise` для PR/WR/RFP/Expense; `receipts/receive_all`; `purchaseorders/send`, `manual_complete`, `approve_matching*`; `payments/pay`; `*_documents_import`; `*/revisions`.
