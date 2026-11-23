# Ендпоінти поза спекою: 49 з 51 уже описані, але в інших areas

Перевірив останню версію гілки (`4318995`): усю спеку (613 операцій), код, з якого вона генерується (`src/OpenApi`, Nelmio 5.13.1, DTO, контролери з батьківськими класами), і використання API в усьому TAF. Живі дані: 52 GET-відповіді smoke з precorino. Для кожного пункту нижче вказано, звідки береться розбіжність у коді, бо від цього залежить, як її закрити.


`/api/docs` віддає лише area `default`. Усі areas у `nelmio_api_doc.yaml` мають `with_attribute: true`, тож операція потрапляє тільки в ту area, яку вказує її `#[Areas]`. 49 операцій, які викликає TAF, мають OA-атрибути, але їхні контролери позначено `#[Areas(['company'])]` (27), `['inventory']` (11), `['user']` (8), `['punch_out', 'internal']` (3).

- **Питання:** чи можна TAF брати спеку з `/api/docs/company`, `/inventory`, `/user`, `/punch_out` і зводити в одну? Якщо так, на бекенді тут нічого робити не треба. Інакше потрібно додати цим контролерам `'default'` в `#[Areas]`.
- `GET /api/ap/documents`**,** `GET /api/ap/documents/{id}`**:** у `src` маршруту не знайшов. Звідки вони?

## Запити

### 1. Операції запису без `requestBody`: 194, але причини різні

Nelmio бачить тіло лише з `#[OA\RequestBody]`. Контролери ж читають тіло в коді, і генератор цього не бачить. Що з'ясувалось за кодом дій (з `parent::` і хелперами):

| Як дія читає тіло | Операцій | Що потрібно |
| --- | --- | --- |
| Через DTO або форму, які вже є | 18 | один атрибут `#[OA\RequestBody(attachables: [new Model(type: …)])]` |
| Ключі напряму з `$request` (`comment`, `notSendEmail`, `restart`…) | 97 | описати тіло (inline-схема або DTO) |
| Передає `$request` у сервіс | 38 | подивитись у сервісі, що читається |
| Тіло не читає | 37 | нічого, відсутність `requestBody` тут правильна |
| Маршрут без імені, не зіставив | 4 | перевірити вручну |

⚑ позначено операції, в які автотести надсилають дані (23).

- `POST /api/expensePayments` → `CreateExpensePaymentDto` ⚑
- `POST /api/expensePayments/group` → `GroupExpensePaymentDto`
- `POST /api/expenses/{idn}/taxes` → `DocumentTaxDto`
- `POST /api/receipts/{idn}/confirm` → `ConfirmReceiptDto`
- `POST /api/locations` → `LocationDto` ⚑
- `PUT /api/locations/{id}` → `LocationDto` ⚑
- `PATCH /api/locations/{id}` → `PatchExternalIdDto` ⚑
- `PATCH /api/requestforproposals/{idn}/note` → `DocumentNoteType`
- `PATCH /api/purchaserequisitions/{idn}/note` → `DocumentNoteType`
- `PATCH /api/warehouserequests/{idn}/note` → `DocumentNoteType`
- `PATCH /api/purchaseorders/{idn}/note` → `DocumentNoteType`
- `POST /api/purchaseorders/{idn}/manual_complete` → `PurchaseRequisitionFromDocumentFormHandler`
- `PATCH /api/invoices/{idn}/note` → `DocumentNoteType`
- `PATCH /api/payments/{idn}/note` → `DocumentNoteType`
- `PATCH /api/expenses/{idn}/note` → `DocumentNoteType`
- `PATCH /api/receipts/{idn}/note` → `DocumentNoteType`
- `PATCH /api/suppliers/{id}` → `PatchExternalIntegrationType` ⚑
- `POST /api/supplierRegistration/{supplierRegistrationId}/approve` → `SupplierType`
- `POST /api/requestforproposals/{idn}/bundle/add` (bundle\_id, ordered)
- `POST /api/requestforproposals/{rfp_id}/reject/{slug}` (comment) ⚑
- `PUT /api/requestforproposals/proposition/{id}/items/approve` ⚑
- `PUT /api/requestforproposals/{idn}/propositions/items/approve`
- `POST /api/requestforproposals/{idn}/cancel` (comment)
- `POST /api/requestforproposals/{idn}/confirm_revise` (restart)
- `PATCH /api/purchaserequisitions/{idn}/exchange_rate`
- `POST /api/purchaserequisitions/{idn}/bundle/add` (bundle\_id, ordered)
- `POST /api/purchase_requisition_documents_import`
- `POST /api/purchaserequisitions/{idn}/mass_edit`
- `POST /api/purchaserequisitions/{idn}/approve` (notSendEmail)
- `POST /api/purchaserequisitions/{idn}/reject` (isMassAction, comment) ⚑
- `POST /api/purchaserequisitions/{idn}/revision` (comment)
- `POST /api/purchaserequisitions/mass-approve`
- `POST /api/purchaserequisitions/mass-reject`
- `POST /api/purchaserequisitions/{idn}/cancel` (comment)
- `POST /api/purchaserequisitions/{idn}/confirm_revise` (restart) ⚑
- `POST /api/warehouserequests/{idn}/bundle/add` (bundle\_id, ordered)
- `POST /api/warehouserequests/{idn}/approve` (notSendEmail)
- `POST /api/warehouserequests/{idn}/reject` (isMassAction, comment)
- `POST /api/warehouserequests/{idn}/revision` (comment)
- `POST /api/warehouserequests/mass-approve`
- `POST /api/warehouserequests/mass-reject`
- `POST /api/warehouserequests/{idn}/cancel` (comment)
- `POST /api/warehouserequests/{idn}/confirm_revise` (restart) ⚑
- `POST /api/purchase_order_documents_import`
- `POST /api/purchaseorders/{idn}/mass_edit`
- `POST /api/purchaseorders/{idn}/approve` (notSendEmail)
- `POST /api/purchaseorders/{idn}/reject` (isMassAction, comment) ⚑
- `POST /api/purchaseorders/{idn}/revision` (comment) ⚑
- `POST /api/purchaseorders/mass-approve`
- `POST /api/purchaseorders/mass-reject`
- `POST /api/purchaseorders/{idn}/cancel` (comment)
- `POST /api/purchaseorders/{idn}/confirm_revise` (restart) ⚑
- `PUT /api/purchaseorders/{idn}/items/{id}/budget_parts`
- `PUT /api/purchaseorders/{idn}/service_items/{id}/budget_parts`
- `POST /api/purchaseorders/{idn}/approve_matching` (poIdn) ⚑
- `POST /api/purchaseorders/{idn}/reject_matching` (poIdn, comment)
- `POST /api/purchaseorders/{idn}/reject_matching_receipt` (comment)
- `POST /api/purchaseorders/{idn}/revise_matching` (poIdn, comment)
- `POST /api/purchaseorders/{idn}/revise_matching_receipt` (comment)
- `POST /api/invoices/create_with_ocr/confirm_upload`
- `POST /api/invoices/create_with_ocr`
- `POST /api/invoice_documents_import`
- `POST /api/invoices/{idn}/mass_edit`
- `POST /api/invoices/{idn}/approve` (notSendEmail)
- `POST /api/invoices/{idn}/reject` (isMassAction, comment) ⚑
- `POST /api/invoices/{idn}/revision` (comment)
- `POST /api/invoices/mass-approve`
- `POST /api/invoices/mass-reject`
- `PUT /api/invoices/{idn}/items/{id}/budget_parts`
- `PUT /api/invoices/{idn}/service_items/{id}/budget_parts`
- `POST /api/payments/{idn}/cancel`
- `POST /api/invoices/{idn}/cancel` (comment)
- `POST /api/invoices/{idn}/confirm_revise` (restart) ⚑
- `POST /api/expense_documents_import`
- `POST /api/expenses/{idn}/mass_edit`
- `POST /api/expenses/{idn}/approve` (notSendEmail)
- `POST /api/expenses/{idn}/reject` (isMassAction, comment)
- `POST /api/expenses/{idn}/revision` (comment)
- `POST /api/expenses/mass-approve`
- `POST /api/expenses/mass-reject`
- `POST /api/expenses/{idn}/cancel` (comment)
- `POST /api/expenses/{idn}/confirm_revise` (restart)
- `POST /api/expenses/{idn}/bundle/add` (bundle\_id, ordered)
- `POST /api/receipts/{idn}/approve` (notSendEmail)
- `POST /api/receipts/{idn}/reject` (isMassAction, comment) ⚑
- `POST /api/receipts/{idn}/revision` (comment)
- `POST /api/receipts/mass-approve`
- `POST /api/receipts/mass-reject`
- `POST /api/receipts/{idn}/cancel` (comment)
- `POST /api/receipts/{idn}/confirm_revise` (restart)
- `PATCH /api/approvalsteps/approvers/{id}/dcf_add` (dcf\_options)
- `PATCH /api/approvalsteps/approvers/{id}/dcf_remove` (dcf\_options)
- `PATCH /api/approvalsteps/approvers/{id}/location_add` (locations)
- `PATCH /api/approvalsteps/approvers/{id}/location_remove` (locations)
- `PATCH /api/approvalsteps/approvers/{id}/initiator_add` (initiators)
- `PATCH /api/approvalsteps/approvers/{id}/initiator_remove` (initiators)
- `PATCH /api/approvalsteps/approvers/{id}/threshold_update`
- `PATCH /api/attachments/{attachment_id}`
- `POST /api/attachments/{object_id}/{type}` ⚑
- `POST /api/attachments/{object_id}/{type}/upload_url`
- `POST /api/preload/attachments`
- `POST /api/preload/attachments/delete`
- `POST /api/shopping-lists/{id}/items` (itemId) ⚑
- `POST /api/items/{id}/images`
- `POST /api/items/{id}/images/proxy_s3_upload` (mediaId)
- `POST /api/suppliers` ⚑
- `PUT /api/suppliers/{id}` (restartApproval, isFromTakeOverRevise) ⚑
- `POST /api/suppliers/rfp/{proposition_id}`
- `PATCH /api/suppliers/{id}/customfields` (id, value) ⚑
- `POST /api/suppliers/{id}/approve` (notSendEmail)
- `POST /api/suppliers/{id}/reject` (isMassAction, comment) ⚑
- `POST /api/suppliers/{id}/revision` (comment)
- `POST /api/supplierRegistration/{supplier_registration_id}/resend` (comment)
- `POST /api/supplierRegistration/{supplierRegistrationId}/reject` (comment)
- `POST /api/supplierRegistration/{supplierRegistrationId}/revise` (comment)
- `POST /api/requestforproposals/{idn}/manual_complete`
- `POST /api/requestforproposals/{idn}/propositions/{proposition_id}/resend`
- `POST /api/requestforproposals/{idn}/resend`
- `POST /api/requestforproposals/{idn}/confirm`
- `POST /api/requestforproposals/{idn}/revise`
- `POST /api/requestforproposals/{idn}/take_over_revise`
- `POST /api/purchaserequisitions/{idn}/update/price`
- `POST /api/purchaserequisitions/{idn}/revise`
- `POST /api/purchaserequisitions/{idn}/confirm`
- `POST /api/purchaserequisitions/{idn}/take_over_revise`
- `POST /api/purchaserequisitions/{idn}/approve-review`
- `POST /api/warehouserequests/{idn}/revise`
- `POST /api/warehouserequests/{idn}/confirm`
- `POST /api/warehouserequests/{idn}/take_over_revise`
- `POST /api/warehouserequests/{idn}/approve-review`
- `POST /api/purchaseorders/{idn}/update/price`
- `POST /api/purchase/order/resend_documents`
- `POST /api/purchaseorders/{idn}/revise`
- `POST /api/purchaseorders/{idn}/confirm`
- `POST /api/purchaseorders/{idn}/take_over_revise`
- `POST /api/purchaseorders/{idn}/approve-review`
- `POST /api/purchaseorders/{idn}/approve_matching_receipt`
- `POST /api/invoice/resend_documents`
- `POST /api/invoices/{idn}/revise`
- `POST /api/invoices/{idn}/confirm`
- `POST /api/invoices/{idn}/take_over_revise`
- `POST /api/invoices/{idn}/approve-review`
- `POST /api/expense/resend_documents`
- `POST /api/expenses/{idn}/revise`
- `POST /api/expenses/{idn}/confirm`
- `POST /api/expenses/{idn}/take_over_revise`
- `POST /api/expenses/{idn}/approve-review`
- `POST /api/receipts/{idn}/revise`
- `POST /api/receipts/{idn}/take_over_revise`
- `POST /api/receipts/{idn}/approve-review`
- `POST /api/attachments/{object_id}/{type}/confirm_upload`
- `POST /api/preload/attachments/confirm_upload`
- `POST /api/items/{id}/images/confirm_upload`
- `POST /api/documentcustomfields/{documentcustomfield_id}/options/{option_id}/deletes`
- `POST /api/requestforproposals/{idn}/items/{id}/reject`
- `POST /api/requestforproposals/{rfp_id}/proposition/{slug}/confirm`
- `POST /api/requestforproposals/{rfp_id}/proposition/{slug}/confirm_revise`
- `POST /api/purchaserequisitions/{idn}/complete`
- `PATCH /api/purchaserequisitions/{idn}/supplier/{supplier_id}`
- `PATCH /api/purchaserequisitions/{idn}/items/{id}/approve`
- `POST /api/purchaserequisitions/{idn}/items/{id}/update/price`
- `PATCH /api/warehouserequests/{idn}/items/{id}/approve`
- `POST /api/purchase/order/{idn}/resend_document`
- `POST /api/purchase/order/{idn}/resend_document_ns`
- `POST /api/purchase/order/{idn}/send_xero`
- `PATCH /api/purchaseorders/{idn}/items/{id}/approve`
- `POST /api/purchaseorders/{idn}/items/{id}/update/price`
- `PATCH /api/purchaseorders/{idn}/service_items/{id}/approve`
- `POST /api/prepayments/{prepayment_id}/cancel`
- `POST /api/unblock_invoices`
- `POST /api/invoice/{idn}/resend_document`
- `POST /api/invoice/{idn}/resend_document_ns`
- `POST /api/invoice/{idn}/send_xero`
- `POST /api/invoice/{idn}/resend_document_bill`
- `POST /api/invoice/{idn}/resend_document_microsoft`
- `POST /api/payments/{idn}/pay`
- `POST /api/expense/{idn}/resend_document`
- `POST /api/expensePayments/{expensePayment_idn}/cancel`
- `POST /api/receipt/{idn}/resend_document_ns`
- `POST /api/itemcustomfields/{customfield_id}/options/{option_id}/deletes`
- `POST /api/documents/{documentType}/{idn}/close`
- `POST /api/suppliers/{id}/qbo/map`
- `POST /api/suppliers/{id}/qbo/unmap`
- `POST /api/suppliers/{id}/xero/map`
- `POST /api/suppliers/{id}/xero/unmap`
- `POST /api/suppliers/{id}/netsuite/map`
- `POST /api/suppliers/{id}/netsuite/unmap`
- `POST /api/supplierRegistration/{supplier_registration_id}/revoke`
- `POST /api/contract/{id}/confirm`
- `POST /api/suppliercustomfields/{suppliercustomfield_id}/options/{option_id}/deletes`
- `PATCH /api/documentcustomfields/options/depend_add` (маршрут без імені)
- `PATCH /api/documentcustomfields/options/depend_remove` (маршрут без імені)
- `PATCH /api/itemcustomfields/options/depend_add` (маршрут без імені)
- `PATCH /api/itemcustomfields/options/depend_remove` (маршрут без імені)

Ще 12 операцій описують тіло inline, без іменованого DTO: `PUT /api/purchaserequisitions/{idn}/items`, `PUT /api/warehouserequests/{idn}/items`, `PUT /api/purchaseorders/{idn}/items`, `PUT /api/purchaseorders/{idn}/service_items`, `PUT /api/invoices/{idn}/items`, `PUT /api/invoices/{idn}/service_items`, `PUT /api/expenses/{idn}/items`, `PUT /api/receipts/{idn}/items`, `PUT /api/receipts/{idn}/service_items`, `PUT /api/recurring_document/info/{id}`, `POST /api/recurring_document/info`, `POST /api/preload/attachments/upload_url`.

### 2. Описані DTO не збігаються з тим, що приймає API

- **Зв'язки: масив порожніх об'єктів у 38 з 66 DTO.** Причина в ручному атрибуті, наприклад `SubmitPurchaseOrderDto::$creator`: `#[OA\Property(type: 'array', items: new OA\Items(type: 'object'))]`. Валідатор того ж поля вимагає `Assert\Collection(fields: ['id' => …])`, тобто об'єкт `{ "id": 5 }`: PHP-масив з ключами стає в JSON об'єктом. Такий атрибут є в 60 файлах `src`. Варто зробити спільну схему `{ id: integer }` і посилатися на неї. Ще `taxes` у PO описано масивом, а надсилається `{ "data": [] }`.

`DocumentCustomFieldDto` (limitAccessToDocuments);`CreateRfpDto` (location, legalEntity, exchangeRate, dataDocumentCustomFields);`PatchRfpDto` (location, legalEntity, exchangeRate, dataDocumentCustomFields);`CreateRfpFromRequisitionsDto` (location, legalEntity, exchangeRate, dataDocumentCustomFields, selectedItems);`RequestForProposalItemDto` (item, dataItemCustomFields);`RfpPropositionDto` (requestForProposal, supplier);`SubmitPurchaseRequisitionDto` (creator, location, legalEntity, budget, supplier, entityTemplate, dataDocumentCustomFields, documentShippingAddress, exchangeRate, items, attachments, selectedItems, taxes, discounts);`PurchaseRequisitionItemDto` (supplier, dataItemCustomFields, budget, item, taxes, discounts);`WarehouseRequestDto` (location, legalEntity, warehouse, dataDocumentCustomFields);`PatchWarehouseRequestDto` (location, creator, legalEntity, warehouse, dataDocumentCustomFields);`WarehouseRequestItemDto` (supplier, dataItemCustomFields, item);`SubmitPurchaseOrderDto` (creator, location, legalEntity, budget, budgetLine, budgetParts, documentSplits, supplier, contracts, paymentTerm, termsAndConditions, blanketDetails, documentShippingAddress, taxes, discounts, entityTemplate, dataDocumentCustomFields, exchangeRate, items, selectedItemsPR);`SubmitPurchaseOrderFromInventoryDto` (selectedItems, creator, location, legalEntity, budget, budgetLine, budgetParts, documentSplits, supplier, contracts, paymentTerm, termsAndConditions, blanketDetails, documentShippingAddress, taxes, discounts, entityTemplate, dataDocumentCustomFields, exchangeRate, items, selectedItemsPR);`PurchaseOrderSplitDto` (location, budget, budgetLine, budgetParts, dataDocumentCustomFields);`SendPurchaseOrderDto` (recipients);`PurchaseOrderItemDto` (dataItemCustomFields, budget, item, supplier, taxes, discounts, itemSplits);`PurchaseOrderServiceItemDto` (dataItemCustomFields, budget, item, supplier, taxes, discounts, itemSplits);`CreatePrepaymentDto` (purchaseOrder);`SubmitParentBudgetDto` (budgetLines);`SubmitInvoiceDto` (purchaseOrder, location, legalEntity, supplier, paymentTerm, contracts, exchangeRate, budget, budgetLine, budgetParts, discounts, taxes, documentSplits, dataDocumentCustomFields, creator, entityTemplate, checkedItems, items);`SubmitInvoiceSplitDto` (location, purchaseOrder, budget, budgetLine, budgetParts, dataDocumentCustomFields);`InvoiceItemDto` (dataItemCustomFields, budget, item, purchaseOrderItem, purchaseOrder, allocatedInvoiceItem, taxes, discounts, itemSplits);`InvoiceServiceItemDto` (dataItemCustomFields, budget, item, purchaseOrderItem, purchaseOrder, originalInvoiceItem, allocatedInvoiceItem, taxes, discounts, itemSplits);`SubmitPaymentDto` (invoice, purchaseOrder);`SubmitDraftPaymentDto` (invoice, fundingAccount);`PatchDraftPaymentDto` (fundingAccount);`SubmitExpenseDto` (location, taxes, entityTemplate, items, dataDocumentCustomFields, creator, budget, legalEntity);`PatchExpenseDto` (dataDocumentCustomFields, location, creator, budget, legalEntity);`PatchExpenseMobileDto` (items, dataDocumentCustomFields, location, creator, budget, legalEntity);`ExpenseItemDto` (dataItemCustomFields, budget, taxes);`SubmitReceiptDto` (warehouse, dataDocumentCustomFields, selectedItems);`PatchReceiptDto` (warehouse, dataDocumentCustomFields, creator);`MassReceiveAllDto` (dataDocumentCustomFields);`UpdateReceiptItemDto` (purchaseOrderItem, dataItemCustomFields);`UpdateReceiptServiceItemDto` (purchaseOrderItem, dataItemCustomFields);`BundleDto` (bundleItems);`ItemModel` (bundleItems, groupItems, dataItemCustomFields);`LinkCardTransactionsDto` (pairs)

- `required` **на всіх полях у 48 з 66 DTO.** Це правило Nelmio (`ObjectModelDescriber::markRequiredProperties`): поле обов'язкове, якщо воно не `nullable` і не має `default`. Властивості DTO нетипізовані (`public $creator;`), тому обов'язковими стають усі, крім тих, що мають значення за замовчуванням (`$logicType = 0`, `?int $splitMode = null`). Перевірено на PO: обов'язкових 31 з 36, а автотест створює PO без 13 із них і отримує 201. Що справді обов'язкове, вже записано у валідаторі: `Assert\NotNull(groups: ['post'])` / `NotBlank`. Варто взяти `required` звідти, через `#[OA\Schema(required: [...])]` або `= null` на необов'язкових полях.

### 3. Query-параметри

- **Пагінація, 42 списки.** `PaginationParams::fromRequest` читає `page`, `per_page`, `sort`, `order`. `PaginatedResponseDescriber` уже знаходить такі дії (`serializeCollectionPaginated`), але описує лише `meta.pagination` у відповіді. Додати ці 4 параметри там само, з `enum` для `per_page` (`Company::AVAILABLE_PER_PAGE`: 5, 10, 20, 50, 100, 200; інше значення мовчки стає 100).
- **Параметри, які дія читає напряму з** `$request->query`**.** `QueryFilterDescriber` описує лише поля filter-форми з `#[QueryFilter]`:
  - `includeGroup[]`: `GET /api/purchaseorders/{idn}` (`PurchaseOrderRestController.php:346`; так само в PR, WR, Receipt, Expense);
  - `invoiceNumber`: `GET /api/invoices` (не поле `InvoiceFilterType`, а шлях пошуку `DocumentSearchParamsMapper.php:21`);
  - `searchQuery`, `isUsedInDocuments`: `GET /api/items` (`ItemRestController.php:135, 164`);
  - `includeEmptySteps`: `GET /api/approvalsteps/{stepType}` (`ApprovalStepRestController.php:77`);
  - `transactionIds[]`: `GET /api/card-transactions/link-statuses` (`CardTransactionRestController.php:89`).
- **Форма параметра в спеці не збігається з формою:**
  - `supplier` у purchaserequisitions і requestforproposals: у спеці рядок, а форма чекає масив;
  - `documentCustomFieldPRs`: у спеці список рядків, а форма чекає мапу `{dcfId: optionId}` (`NumericKeyValue`);
  - `textCustomFieldProducts`, `dateCustomFieldProducts` в items: у спеці рядок, а форма чекає мапу за id ICF.

## Відповіді

### 4. `required` на верхньому рівні: 67 з 69 схем

Причина в `TransformerSchemaFactory::buildSchema()`: поля з `transform()` додаються як properties без `required`. Для вкладених масивів `applyType()` уже ставить `required` за прапорцем `optional` від `TransformerParser`, тобто «ключ є на кожному шляху». Для верхнього рівня цей самий прапорець просто не використовується. Include-поля позначати не треба.

### 5. Статус

`POST /api/contract`**:** спека описує 201, а `postContractAction` повертає `new JsonResponse(...)`, тобто 200. Так само в develop. З 801 дії з описаним 2xx це єдина розбіжність, яку видно статично.

### 6. Тіло помилок

`ErrorResponsesDescriber` додає до кодів з `#[ErrorResponses]` лише `description`, без `content`. Тож жодна 4xx не описує тіло: 400 (344), 401 (493), 403 (478), 404 (396), 409 (90), 415 (9), 422 (4), 423 (14), 429 (9). Єдиного формату помилки в коді теж немає:

- `ExceptionListener` віддає `{ code, message }`;
- контролери самі будують `{ message }` (щонайменше 54 місця з 4xx-статусом), `{ errors }` (9) і `{ error }` (3).

Описати ці форми як 2–3 спільні схеми й додати `content` в `ErrorResponsesDescriber`. Чи зводити їх в одну, вирішувати вам.

### 7. Типи

- `string | integer` **/** `string | number`**:** 95 полів, з них `idn` 55. Як домовлялись, окремою задачею.
- **Поля без типу: 103.** Це свідомо: `applyType()` не ставить тип, коли `TransformerParser` не вивів його, щоб «спека не суперечила значенню». Переважно це опції custom fields, `approvalFlow.canceledBy`, `showApprovalReviewers`, адреса компанії. Тип з'явиться, коли парсер зможе його вивести, наприклад з return type чи PHPDoc у джерелі.

`DocumentCustomFieldTransformer.options.data[].name`, `DocumentCustomFieldTransformer.options.data[].code`, `DocumentCustomFieldTransformer.options.data[].label`, `DocumentCustomFieldTransformer.options.data[].externalId`, `DocumentCustomFieldTransformer.options.data[].billId`, `DocumentCustomFieldTransformer.options.data[].documentCustomFieldOptionDependOnDCFOptions.data`, `DocumentCustomFieldTransformer.options.data[].documentCustomFieldOptionDependOnLegalEntities.data`, `DocumentCustomFieldTransformer2.options.data[].name`, `DocumentCustomFieldTransformer2.options.data[].code`, `DocumentCustomFieldTransformer2.options.data[].label`, `DocumentCustomFieldTransformer2.options.data[].externalId`, `DocumentCustomFieldTransformer2.options.data[].billId`, `DocumentCustomFieldTransformer2.options.data[].documentCustomFieldOptionDependOnDCFOptions.data`, `DocumentCustomFieldTransformer2.options.data[].documentCustomFieldOptionDependOnLegalEntities.data`, `ItemCustomFieldTransformer.options.data[].name`, `ItemCustomFieldTransformer.options.data[].code`, `ItemCustomFieldTransformer.options.data[].label`, `ItemCustomFieldTransformer.options.data[].netSuiteId`, `ItemCustomFieldTransformer.options.data[].billId`, `ItemCustomFieldTransformer.options.data[].externalId`, `ItemCustomFieldTransformer.options.data[].itemCustomFieldOptionDependOnDCFOptions.data`, `ItemCustomFieldTransformer.options.data[].itemCustomFieldOptionDependOnLegalEntities.data`, `SupplierTransformer.marketContacts.data[].email`, `SupplierTransformer.marketContacts.data[].phone`, `SupplierTransformer.approvalFlow.canceledBy.fullName`, `SupplierTransformer.invoicesToCancel[].idn`, `PurchaseRequisitionTransformer.approvalFlow.canceledBy.fullName`, `PurchaseRequisitionTransformer.showApprovalReviewers[].email`, `PurchaseRequisitionTransformer.showApprovalReviewers[].fullName`, `BudgetLineTransformer.locations`, `CompanyTransformer.mailDomain`, `CompanyTransformer.accountFields.daysActive`, `CompanyTransformer.accountingPeriodSettings.id`, `CompanyTransformer.accountingPeriodSettings.periodType`, `CompanyTransformer.accountingPeriodSettings.closingMethod`, `CompanyTransformer.accountingPeriodSettings.closingPeriodDay`, `CompanyTransformer.accountingPeriodSettings.closingPeriodDate`, `CompanyTransformer.companyBillingAddress.id`, `CompanyTransformer.companyBillingAddress.country`, `CompanyTransformer.companyBillingAddress.state`, `CompanyTransformer.companyBillingAddress.city`, `CompanyTransformer.companyBillingAddress.postalCode`, `CompanyTransformer.companyBillingAddress.taxPayerNumber`, `CompanyTransformer.companyBillingAddress.isVatPayer`, `CompanyTransformer.companyBillingAddress.vatIdentificationNumber`, `InvoiceTransformer.autoApproveReason`, `InvoiceTransformer.withholdingTaxSumInCompanyCurrency`, `InvoiceTransformer.approvalFlow.canceledBy.fullName`, `InvoiceTransformer.showApprovalReviewers[].email`, `InvoiceTransformer.showApprovalReviewers[].fullName`, `PurchaseOrderTransformer.matchingInfo.matchingInvoiceIdn`, `PurchaseOrderTransformer.matchingInfo.matchingReceiptIdn`, `PurchaseOrderTransformer.approvalFlow.canceledBy.fullName`, `PurchaseOrderTransformer.showApprovalReviewers[].email`, `PurchaseOrderTransformer.showApprovalReviewers[].fullName`, `PaymentTransformer.integrationLog[].date`, `PaymentTransformer.integrationLog[].errorMessage`, `PaymentTransformer.integrationLog[].userId`, `WarehouseItemTaxTransformer.name`, `WarehouseItemTaxTransformer.value`, `WarehouseItemTaxTransformer.usedTaxPercent`, `WarehouseItemTaxTransformer.isWithholdingTax`, `ReceiptTransformer.relatedPurchaseRequisitionsCount`, `ReceiptTransformer.approvalFlow.canceledBy.fullName`, `ReceiptTransformer.showApprovalReviewers[].email`, `ReceiptTransformer.showApprovalReviewers[].fullName`, `MatchingDataTransformer.document.relatedPurchaseRequisitionsCount`, `MatchingDataTransformer.document.approvalFlow.canceledBy.fullName`, `MatchingDataTransformer.document.showApprovalReviewers[].email`, `MatchingDataTransformer.document.showApprovalReviewers[].fullName`, `MatchingDataTransformer.document.autoApproveReason`, `MatchingDataTransformer.document.withholdingTaxSumInCompanyCurrency`, `PurchaseOrderForInvoiceTransformer.matchingInfo.matchingInvoiceIdn`, `PurchaseOrderForInvoiceTransformer.matchingInfo.matchingReceiptIdn`, `PurchaseOrderForInvoiceTransformer.approvalFlow.canceledBy.fullName`, `PurchaseOrderForInvoiceTransformer.showApprovalReviewers[].email`, `PurchaseOrderForInvoiceTransformer.showApprovalReviewers[].fullName`, `RequestForProposalTransformer.approvalFlow.canceledBy.fullName`, `RequestForProposalTransformer.showApprovalReviewers[].email`, `RequestForProposalTransformer.showApprovalReviewers[].fullName`, `PropositionTransformer.requestForProposal.approvalFlow.canceledBy.fullName`, `PropositionTransformer.requestForProposal.showApprovalReviewers[].email`, `PropositionTransformer.requestForProposal.showApprovalReviewers[].fullName`, `RelatedPurchaseOrderPreviewTransformer.location.name`, `RelatedPurchaseOrderPreviewTransformer.creator.firstname`, `RelatedPurchaseOrderPreviewTransformer.creator.lastname`, `RelatedPurchaseOrderPreviewTransformer.showApprovalReviewers[].email`, `RelatedPurchaseOrderPreviewTransformer.showApprovalReviewers[].fullName`, `WarehouseRequestItemTransformer.item.name`, `WarehouseRequestItemTransformer.item.sku`, `WarehouseRequestItemTransformer.item.unit`, `WarehouseRequestItemTransformer.item.price`, `WarehouseRequestItemTransformer.item.currency`, `WarehouseRequestItemTransformer.item.purchasingUnit.unit`, `WarehouseRequestTransformer.approvalFlow.canceledBy.fullName`, `WarehouseRequestTransformer.showApprovalReviewers[].email`, `WarehouseRequestTransformer.showApprovalReviewers[].fullName`, `ParentBudgetTransformer.usedSum`, `ParentBudgetTransformer.reservedSum`, `BudgetLineTransformer2.locations`, `ExpenseTransformer.approvalFlow.canceledBy.fullName`, `ExpenseTransformer.showApprovalReviewers[].email`, `ExpenseTransformer.showApprovalReviewers[].fullName`

---

Помилки в самих автотестах, знайдені під час перевірки, виправимо в TAF: `order` без `sort` (бекенд його ігнорує), `per_page` поза `enum`, `withBudgetSubLine`, `include` для `generate_user_api_token`.
