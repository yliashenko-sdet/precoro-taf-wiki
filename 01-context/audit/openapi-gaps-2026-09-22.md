# Запит до розробки: схеми відповідей в OpenAPI

Джерело: `01-context/archive/precoro-openapi-2026-09-22.json`, зіставлено зі шляхами, які будує `src/api/precoro_service.ts`. Потрібно для валідації відповідей у тестах (T1-25, T1-26).

## A. Є в специфікації, але без схеми відповіді: 34 операцій на 17 шляхах

Усі мають лише `default` у `responses`, тобто ні коду, ні тіла. Для DELETE, якщо відповідь порожня, достатньо оголосити `204 No Content`; для решти потрібна схема тіла.

| Метод | Шлях | Область |
|---|---|---|
| DELETE | `/api/approvalsteps/{x}` | Approval Steps |
| DELETE | `/api/approvalsteps/{x}/approvers/{x}` | Approvers |
| DELETE | `/api/budgets/{x}/line` | Budget Lines |
| DELETE | `/api/contract/{x}` | Contracts |
| DELETE | `/api/expenses/{x}/delete` | Expenses |
| DELETE | `/api/invoices/{x}/delete` | Invoices |
| DELETE | `/api/invoices/{x}/items/{x}` | Invoice Items |
| DELETE | `/api/invoices/{x}/service_items/{x}` | Invoice Service Items |
| GET | `/api/itemcustomfields` | Item Custom Fields |
| POST | `/api/itemcustomfields` | Item Custom Fields |
| GET | `/api/itemcustomfields/{x}` | Item Custom Fields |
| PUT | `/api/itemcustomfields/{x}` | Item Custom Fields |
| POST | `/api/itemcustomfields/{x}/options` | Item Custom Field Options |
| PATCH | `/api/itemcustomfields/{x}/options/{x}` | Item Custom Field Options |
| PUT | `/api/itemcustomfields/{x}/options/{x}` | Item Custom Field Options |
| DELETE | `/api/items/{x}` | Items |
| DELETE | `/api/parent/{x}/budget` | Budgets |
| DELETE | `/api/purchaseorders/{x}/delete` | Purchase Orders |
| DELETE | `/api/purchaseorders/{x}/items/{x}` | Purchase Order Items |
| DELETE | `/api/purchaseorders/{x}/service_items/{x}` | Purchase Order Items |
| DELETE | `/api/purchaserequisitions/{x}/delete` | Purchase Requisitions |
| DELETE | `/api/purchaserequisitions/{x}/items/{x}` | Purchase Requisition Items |
| DELETE | `/api/receipts/{x}/delete` | Receipts |
| DELETE | `/api/requestforproposals/{x}/delete` | Requests for Proposals |
| DELETE | `/api/shopping-lists/{x}` | Shopping Lists |
| POST | `/api/shopping-lists/{x}/items` | Shopping Lists |
| POST | `/api/supplierRegistration/{x}/revoke` | Supplier Registration |
| GET | `/api/suppliercustomfields` | Supplier Custom Fields |
| POST | `/api/suppliercustomfields` | Supplier Custom Fields |
| GET | `/api/suppliercustomfields/{x}` | Supplier Custom Fields |
| PUT | `/api/suppliercustomfields/{x}` | Supplier Custom Fields |
| POST | `/api/suppliercustomfields/{x}/options` | Supplier Custom Field Options |
| PUT | `/api/suppliercustomfields/{x}/options/{x}` | Supplier Custom Field Options |
| DELETE | `/api/warehouserequests/{x}/delete` | Warehouse Requests |

## B. Немає в специфікації взагалі: 42 шляхів

Внутрішній API, знятий із фронту. Інфра-AQA каже, що покриття для них теж має з'явитись; це стеля валідації 172 шляхи замість 121.

- `/api/ap/documents`
- `/api/ap/documents/{x}`
- `/api/ap/save_ap_configuration`
- `/api/attachments/{x}/8`
- `/api/categories`
- `/api/companies/current`
- `/api/company_supplier_registration_configuration`
- `/api/company_supplier_registration_configurations`
- `/api/company_user/{x}`
- `/api/credit_notes/{x}/confirm`
- `/api/entity_template`
- `/api/entity_template/{x}/delete`
- `/api/entity_template/{x}/enable`
- `/api/entity_templates`
- `/api/inventories`
- `/api/legalentities`
- `/api/legalentities/{x}`
- `/api/manage/company/{x}/reapproval_setup`
- `/api/manage/company/{x}/reapproval_setup/{x}`
- `/api/paymentterms`
- `/api/paymentterms/{x}`
- `/api/preload/attachments`
- `/api/punch_out/config`
- `/api/punch_out/config/{x}`
- `/api/recurring_document/info`
- `/api/requestforproposals/propositions`
- `/api/stock_takings`
- `/api/stock_takings/{x}`
- `/api/stocktransfers`
- `/api/stocktransfers/{x}`
- `/api/taxes`
- `/api/taxes/{x}`
- `/api/user`
- `/api/user/email/preferences/{x}`
- `/api/user/{x}`
- `/api/users`
- `/api/users/{x}`
- `/api/users/{x}/final_create`
- `/api/users/{x}/vacation_mode`
- `/api/warehouses`
- `/api/warehouses/{x}/items`
- `/api/warehouses/{x}/items/{x}`

## C. Не питати: динамічні шаблони клієнта (9)

Це не окремі ендпоінти, а шляхи, які клієнт будує з типу документа: `/api/${docType}/${idn}/approve` тощо. У специфікації вони існують під конкретними типами.

- `/api/attachments/{x}/{x}`
- `/api/delegator_user_choices/{x}/{x}`
- `/api/is_user_need_delegate_documents/{x}/{x}`
- `/api/{x}/{x}`
- `/api/{x}/{x}/approve`
- `/api/{x}/{x}/approve_matching`
- `/api/{x}/{x}/items`
- `/api/{x}/{x}/reject`
- `/api/{x}/{x}/revision`
