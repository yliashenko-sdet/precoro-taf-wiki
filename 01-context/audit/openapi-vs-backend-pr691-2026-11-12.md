# Повний перелік розбіжностей спеки з бекендом після PR 691, 2026-11-12

Розробникам, до [precoro/precoro#691](https://github.com/precoro/precoro/pull/691). Загальний опис причин дивись у `openapi-vs-backend-2026-11-08.md`.

## Як перевірено
- Спеку `/api/docs` (area `default`) згенеровано з гілки PR (`9bfea93`), команда `nelmio:apidoc:dump`.
- Звірено з живими відповідями `api.precorino.com`: 20 GET-ендпоінтів, 49 відповідей. Перевірено:
  - 12 списків по 20 записів, кожен елемент;
  - 5 карток кожного з 7 типів документів;
  - картку PO з `relatedPurchaseRequisitions` і `relatedInvoices`;
  - `reports/config`.
- Вкладеність до 6 рівнів; `anyOf` порівнюється з гілкою того ж типу.
- Скрипт `06-playbooks/scripts/spec_vs_live.js` лише читає, нічого не змінює.

## Підсумок
| Причина | До PR | Після PR |
|---|---|---|
| 1. `meta` у списках | 12 | **0** |
| 2. Колекції `{data}` | 61 | **0** |
| 3. Словник описано списком | 25 | 26 |
| 4. Немає `nullable` | 88 | 104 |
| 5. Хибний скалярний тип | 61 | 96 |
| 6. `object` замість типу | 106 | 111 |
| 7. Поля, яких немає в спеці (об'єктів) | 14 | 20 |
| 8. Порожній об'єкт | 26 | 26 |
| **Разом** | **393** | **383** |

Після PR пп. 3–7 зросли не через регресію. Колекції тепер описані правильно, і звірка вперше дійшла всередину `items`, `taxes`, `attachments` та інших колекцій.

Таблиці нижче зведені за полем. Префікс `data[*]` списку прибрано, тож рядок покриває і список, і картку. «(картка)» у колонці ендпоінтів означає `GET /api/<ресурс>/{idn}`.
### 3. Асоціативний масив (словник) описано списком (5 полів)

| Поле | Що не так | Ендпоінти |
|---|---|---|
| `creditBalanceSums` | приходить: {USD…} | suppliers |
| `exchangeRate` | приходить: {AFN:USD, USD:AFN…} | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `precisionData` | приходить: {USD…} | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `propositions.data[*].supplier.creditBalanceSums` | приходить: {USD…} | requestforproposals (картка) |
| `supplier.creditBalanceSums` | приходить: {USD…} | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |

### 4. Приходить null, а nullable у спеці немає (26 полів)

| Поле | Що не так | Ендпоінти |
|---|---|---|
| `attachments.data[*].comment` | спека: string | invoices (картка), receipts (картка) |
| `attachments.data[*].documentId` | спека: number | invoices (картка), receipts (картка) |
| `customName` | спека: string | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `description` | спека: string | documentcustomfields, itemcustomfields |
| `externalId` | спека: number | suppliers, locations, invoices, invoices (картка), purchaseorders, purchaseorders (картка), items, items (картка), receipts, receipts (картка), expenses, expenses (картка) |
| `fullAddress` | спека: string | locations |
| `image` | спека: string | items, items (картка) |
| `items.data[*].description` | спека: string | receipts (картка) |
| `items.data[*].link` | спека: string | receipts (картка) |
| `items.data[*].manufacturerName` | спека: string | requestforproposals (картка), purchaserequisitions (картка) |
| `items.data[*].manufacturerPartNumber` | спека: string | requestforproposals (картка), purchaserequisitions (картка) |
| `items.data[*].supplierPartNumber` | спека: string | requestforproposals (картка), purchaserequisitions (картка) |
| `legalEntity.externalId` | спека: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `location.externalId` | спека: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `location.fullAddress` | спека: string | purchaserequisitions |
| `location.phone` | спека: string | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `location.uniqueCode` | спека: string | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `manufacturerName` | спека: string | items, items (картка) |
| `manufacturerPartNumber` | спека: string | items, items (картка) |
| `paymentTerms.data[*].externalId` | спека: number | suppliers |
| `phone` | спека: string | locations |
| `propositions.data[*].supplier.externalId` | спека: number | requestforproposals (картка) |
| `supplier.externalId` | спека: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |
| `supplier.paymentTerms.data[*].externalId` | спека: number | invoices (картка), purchaseorders (картка) |
| `supplierPartNumber` | спека: string | items, items (картка) |
| `uniqueCode` | спека: string | locations |

### 5. Хибний скалярний тип (35 полів)

| Поле | Що не так | Ендпоінти |
|---|---|---|
| `approvalSteps.data[*].step_number` | спека: string, приходить: number | invoices, receipts, expenses, purchaserequisitions |
| `availableInApprovalWorkflow` | спека: string, приходить: boolean | documentcustomfields |
| `blanketDetails.amountOfDeliveries` | спека: string, приходить: number | purchaseorders, purchaseorders (картка) |
| `blanketDetails.blanketSum` | спека: string, приходить: number | purchaseorders, purchaseorders (картка) |
| `blanketDetails.frequency` | спека: string, приходить: number | purchaseorders, purchaseorders (картка) |
| `currencies` | спека: string, приходить: array | suppliers |
| `dataDocumentCustomFields.data[*].type` | спека: string, приходить: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `exchangeRate` | спека: string, приходить: object | receipts, receipts (картка) |
| `idn` | спека: number, приходить: string | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `isSendToPunchout` | спека: string, приходить: number | purchaseorders, purchaseorders (картка) |
| `items.data[*].expense.idn` | спека: number, приходить: string | expenses (картка) |
| `items.data[*].invoice.idn` | спека: number, приходить: string | invoices (картка) |
| `items.data[*].isSupplierRejected` | спека: string, приходить: boolean | purchaserequisitions (картка) |
| `items.data[*].item` | спека: string, приходить: object | invoices (картка), requestforproposals (картка), expenses (картка), purchaserequisitions (картка) |
| `items.data[*].requestOrdered` | спека: number, приходить: string | purchaserequisitions (картка) |
| `items.data[*].type` | спека: string, приходить: number | invoices (картка) |
| `marketSupplier.minimumSum` | спека: string, приходить: number | suppliers |
| `minimumSum` | спека: string, приходить: number | suppliers |
| `netSum` | спека: string, приходить: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка), expenses, expenses (картка) |
| `position` | спека: string, приходить: number | documentcustomfields, itemcustomfields |
| `propositions.data[*].supplier.currencies` | спека: string, приходить: array | requestforproposals (картка) |
| `propositions.data[*].supplier.minimumSum` | спека: string, приходить: number | requestforproposals (картка) |
| `propositions.data[*].supplier.status` | спека: string, приходить: number | requestforproposals (картка) |
| `punchoutType` | спека: string, приходить: number | invoices, invoices (картка) |
| `purchaseOrder.idn` | спека: number, приходить: string | invoices, invoices (картка), receipts, receipts (картка) |
| `status` | спека: string, приходить: number | suppliers |
| `sumPaid` | спека: number, приходить: string | invoices, invoices (картка) |
| `supplier.currencies` | спека: string, приходить: array | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |
| `supplier.externalId` | спека: number, приходить: string | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |
| `supplier.minimumSum` | спека: string, приходить: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |
| `supplier.status` | спека: string, приходить: number | invoices, invoices (картка), purchaseorders, purchaseorders (картка) |
| `taxes.data[*].isWithholdingTax` | спека: string, приходить: boolean | invoices (картка), purchaseorders (картка), expenses (картка) |
| `taxes.data[*].usedTaxPercent` | спека: string, приходить: number | invoices (картка), purchaseorders (картка), expenses (картка) |
| `taxes.data[*].value` | спека: string, приходить: number | invoices (картка), purchaseorders (картка), expenses (картка) |
| `type` | спека: string, приходить: number | documentcustomfields, itemcustomfields, items, items (картка) |

### 6. Тип не визначено, у спеці стоїть object (41 полів)

| Поле | Що не так | Ендпоінти |
|---|---|---|
| `availableSum` | приходить: number | budgets |
| `budget.availableSum` | приходить: number | expenses |
| `budget.currency` | приходить: string | expenses |
| `budget.fullName` | приходить: string | expenses |
| `budget.parentBudgetId` | приходить: number | expenses |
| `budget.reservedSumInRecurringInvoice` | приходить: number | expenses |
| `budget.reservedSumInRecurringPurchaseOrder` | приходить: number | expenses |
| `comments.data[*].user.hasConfirmationToken` | приходить: boolean | invoices (картка), receipts (картка) |
| `comments.data[*].user.isPower` | приходить: boolean | invoices (картка), receipts (картка) |
| `creator.hasConfirmationToken` | приходить: boolean | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `creator.isPower` | приходить: boolean | invoices, invoices (картка), purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `currency` | приходить: string | budgets |
| `frequencyString` | приходить: string | purchaseorders |
| `fullName` | приходить: string | budgets |
| `isBudgetOverLimit` | приходить: boolean | invoices (картка), purchaseorders (картка), expenses, expenses (картка), purchaserequisitions, purchaserequisitions (картка) |
| `isWithSplits` | приходить: boolean | invoices (картка), purchaseorders (картка) |
| `items.data[*].discounts.data` | приходить: array | expenses (картка) |
| `lastEditor.hasConfirmationToken` | приходить: boolean | invoices, invoices (картка), receipts, receipts (картка), expenses, purchaserequisitions, purchaserequisitions (картка) |
| `lastEditor.isPower` | приходить: boolean | invoices, invoices (картка), receipts, receipts (картка), expenses, purchaserequisitions, purchaserequisitions (картка) |
| `matchingBudgetChangeSum` | приходить: number | purchaseorders (картка) |
| `parentBudgetId` | приходить: number | budgets |
| `relatedCreditNotes` | приходить: array | invoices, invoices (картка) |
| `relatedCreditNotesCount` | приходить: number | invoices |
| `relatedInvoices` | приходить: array | purchaseorders, purchaseorders (картка), receipts, receipts (картка) |
| `relatedInvoicesCount` | приходить: number | purchaseorders, receipts |
| `relatedPurchaseOrders` | приходить: array | invoices, requestforproposals, requestforproposals (картка), purchaserequisitions, purchaserequisitions (картка) |
| `relatedPurchaseOrdersCount` | приходить: number | requestforproposals, purchaserequisitions |
| `relatedPurchaseRequisitions` | приходить: array | purchaseorders, purchaseorders (картка), requestforproposals, requestforproposals (картка), receipts, receipts (картка) |
| `relatedPurchaseRequisitionsCount` | приходить: number | purchaseorders, requestforproposals, receipts |
| `relatedReceipts` | приходить: array | purchaseorders, purchaseorders (картка) |
| `relatedReceiptsCount` | приходить: number | purchaseorders |
| `relatedRequestForProposals` | приходить: array | purchaseorders, purchaseorders (картка), receipts, receipts (картка), purchaserequisitions, purchaserequisitions (картка) |
| `relatedRequestForProposalsCount` | приходить: number | purchaseorders, receipts, purchaserequisitions |
| `relatedServiceOrders` | приходить: array | purchaserequisitions, purchaserequisitions (картка) |
| `relatedServiceOrdersCount` | приходить: number | purchaserequisitions |
| `relatedWarehouseRequests` | приходить: array | purchaserequisitions, purchaserequisitions (картка) |
| `relatedWarehouseRequestsCount` | приходить: number | purchaserequisitions |
| `reservedSumInRecurringInvoice` | приходить: number | budgets |
| `reservedSumInRecurringPurchaseOrder` | приходить: number | budgets |
| `splitMode` | приходить: number | invoices (картка), purchaseorders (картка) |
| `withholdingTaxSumInCompanyCurrency` | приходить: number | invoices |

### 7. Поля, яких немає в спеці (16 об'єктів)

| Ресурс → об'єкт | Поля, яких немає в спеці | Де |
|---|---|---|
| budgets → `(корінь)` | `children` | budgets |
| documentcustomfields → `(корінь)` | `options` | documentcustomfields |
| expenses → `items.data[*]` | `budget` | expenses (картка) |
| invoices → `allocatedInvoice` | `idn`, `creator`, `customName`, `createDate`, `updateDate`, `requiredDate`, `issueDate`, `approvalDate`, `sumPaid`, `sumPaidInCompanyCurrency`, `sum`, `netSum`, `sumInCompanyCurrency`, `netSumInCompanyCurrency`, `sumInLegalEntityCurrency`, `netSumInLegalEntityCurrency`, `withholdingTaxSum`, `currency`, `precisionData`, `note`, `exchangeRate`, `fromSupplier`, `isServiceOrder`, `status`, `logicType`, `invoiceNumber`, `deliveryNote`, `toleranceRateSum`, `toleranceRatePercent`, `purchaseOrder`, `prepaymentPercent`, `postpaymentPercent`, `paymentTermName`, `creditPeriodDays`, `paymentTerm`, `company`, `qboId`, `netSuiteId`, `integrationStatus`, `xeroId`, `billId`, `integratedWithMicrosoft`, `externalId`, `externalIntegrationLog`, `budgetedSum`, `allDocumentCustomFieldOptionsIds`, `isNewSupplierAdded`, `punchoutType`, `location`, `supplier`, `budget`, `budgetLine`, `legalEntity`, `lastEditor` | invoices, invoices (картка) |
| invoices → `items.data[*]` | `supplierPartNumber`, `manufacturerPartNumber`, `manufacturerName`, `price`, `unit`, `logicType`, `allocatedInvoiceItem`, `budget` | invoices (картка) |
| invoices → `purchaseOrder` | `customName`, `createDate`, `updateDate`, `requiredDate`, `approvalDate`, `sum`, `netSum`, `savingsSum`, `isSavingsManuallyUpdated`, `sumInCompanyCurrency`, `netSumInCompanyCurrency`, `sumInLegalEntityCurrency`, `netSumInLegalEntityCurrency`, `currency`, `precisionData`, `note`, `exchangeRate`, `isServiceOrder`, `status`, `statusReceiving`, `statusPayment`, `statusSending`, `isAllItemsReceived`, `blanketDetails`, `paymentTerm`, `company`, `prepaymentPercent`, `postpaymentPercent`, `paymentTermName`, `creditPeriodDays`, `qboId`, `netSuiteId`, `integrationStatus`, `xeroId`, `externalId`, `externalIntegrationLog`, `logicType`, `budgetedSum`, `deliverToName`, `allDocumentCustomFieldOptionsIds`, `sendToSupplier`, `isNewSupplierAdded`, `punchoutType`, `isSendToPunchout`, `autoCreateType`, `punchoutSupplier`, `location`, `supplier`, `budget`, `budgetLine`, `legalEntity`, `lastEditor`, `approvalSteps`, `contracts`, `dataDocumentCustomFields`, `prepayments` | invoices (картка) |
| invoices → `purchaseOrder.creator` | `createDate`, `updateDate`, `email`, `unconfirmedEmail`, `locale`, `phone`, `firstname`, `lastname`, `position`, `dateOfBirth`, `location`, `legalEntity`, `allLocationsAccess`, `allUserDocumentCustomFieldsAccess`, `allItemGroupsAccess`, `roles`, `enable`, `isMarketSupplier`, `isAvailableVacationMode`, `enableVacationMode`, `startVacationMode`, `endVacationMode`, `isPower`, `hasConfirmationToken`, `substitute` | invoices (картка) |
| itemcustomfields → `(корінь)` | `options` | itemcustomfields |
| items → `(корінь)` | `price`, `purchasingUnit`, `dataItemCustomFields`, `bundleItems`, `groupItems`, `shoppingListItems` | items, items (картка) |
| items → `supplier` | `uniqueCode`, `name`, `createDate`, `updateDate`, `approvalDate`, `legalAddress`, `currency`, `currencies`, `autoSendPOSupplier`, `deliveryPeriod`, `minimumSum`, `businessRegistrationNumber`, `accountHolderName`, `bankName`, `accountNumber`, `bankAddress`, `swiftCode`, `permanentAccountNumber`, `internationalBankAccountNumber`, `americanBankersAssociationNumber`, `indianFinancialSystemCode`, `sortCode`, `taxPayer`, `taxPayerType`, `taxPayerLabel`, `taxPayerNumber`, `phone`, `city`, `country`, `countryCode`, `state`, `postalCode`, `note`, `conditions`, `enable`, `qboId`, `netSuiteId`, `xeroId`, `billId`, `integratedWithMicrosoft`, `integrationStatus`, `externalId`, `marketSupplier`, `enableMarketSupplier`, `creditBalanceSums`, `status`, `creator`, `enterInvoiceAsOneLine`, `isPunchoutSupplier`, `isAllAccessLegalEntity`, `paymentTerms` | items, items (картка) |
| purchaserequisitions → `(корінь)` | `sum`, `sumInCompanyCurrency`, `sumInLegalEntityCurrency`, `netSum`, `netSumInCompanyCurrency`, `netSumInLegalEntityCurrency`, `withholdingTaxSum` | purchaserequisitions, purchaserequisitions (картка) |
| purchaserequisitions → `items.data[*]` | `price`, `freeOfCharge`, `grossTotalInCompanyCurrency`, `purchaseOrders`, `budget`, `taxes`, `discounts` | purchaserequisitions (картка) |
| receipts → `items.data[*]` | `received`, `addedToCreditNote` | receipts (картка) |
| receipts → `purchaseOrder` | `customName`, `createDate`, `updateDate`, `requiredDate`, `approvalDate`, `sum`, `netSum`, `savingsSum`, `isSavingsManuallyUpdated`, `sumInCompanyCurrency`, `netSumInCompanyCurrency`, `sumInLegalEntityCurrency`, `netSumInLegalEntityCurrency`, `currency`, `precisionData`, `note`, `exchangeRate`, `isServiceOrder`, `status`, `statusReceiving`, `statusPayment`, `statusSending`, `isAllItemsReceived`, `blanketDetails`, `paymentTerm`, `company`, `prepaymentPercent`, `postpaymentPercent`, `paymentTermName`, `creditPeriodDays`, `qboId`, `netSuiteId`, `integrationStatus`, `xeroId`, `externalId`, `externalIntegrationLog`, `logicType`, `budgetedSum`, `deliverToName`, `allDocumentCustomFieldOptionsIds`, `sendToSupplier`, `isNewSupplierAdded`, `punchoutType`, `isSendToPunchout`, `autoCreateType`, `punchoutSupplier`, `location`, `supplier`, `budget`, `budgetLine`, `legalEntity`, `lastEditor` | receipts (картка) |
| receipts → `purchaseOrder.creator` | `createDate`, `updateDate`, `email`, `unconfirmedEmail`, `locale`, `phone`, `firstname`, `lastname`, `position`, `dateOfBirth`, `location`, `legalEntity`, `allLocationsAccess`, `allUserDocumentCustomFieldsAccess`, `allItemGroupsAccess`, `roles`, `enable`, `isMarketSupplier`, `isAvailableVacationMode`, `enableVacationMode`, `startVacationMode`, `endVacationMode`, `isPower`, `hasConfirmationToken`, `substitute` | receipts (картка) |
| suppliers → `(корінь)` | `dataSupplierCustomFields` | suppliers |

### 8. Об'єкт без жодної властивості в спеці (12 полів)

| Поле | Що не так | Ендпоінти |
|---|---|---|
| `(корінь)` | приходить: channelId, hasValidGoogleSheetsAccessToken, isGoogleSheetsDisconnected, allowedDocumentTypes, isGrantedShowReportAccountUserAccess, columnsMetadata | reports/config |
| `approvalFlow` | приходить: canceledBy, steps | invoices (картка), purchaseorders (картка), requestforproposals (картка), receipts (картка), expenses (картка), purchaserequisitions (картка) |
| `approvalInfo` | приходить: canApproveDocument, canRejectDocument | invoices, receipts, expenses, purchaserequisitions |
| `approvalInfo` | приходить: canAcceptMatchingChanges, canRejectMatchingChanges, documentAC, isMatchingReceipt, canApproveDocument, canRejectDocument | purchaseorders |
| `delegatedFromUser` | приходить: id | invoices (картка), purchaseorders (картка), requestforproposals (картка), receipts (картка), expenses (картка), purchaserequisitions (картка) |
| `items.data[*]` | приходить: id, createDate, updateDate, sku, supplierPartNumber, manufacturerPartNumber, manufacturerName, name | purchaseorders (картка) |
| `items.data[*].purchaseOrderItem` | приходить: id, sku, name, unit, ordered, price, rejected, invoiced | receipts (картка) |
| `ocrAttachment` | приходить: id | invoices |
| `recognizedDocument` | приходить: id | invoices, invoices (картка) |
| `relatedOcrAttachment` | приходить: id | invoices (картка) |
| `relatedRecognizedDocument` | приходить: id | invoices (картка) |
| `supplier` | приходить: id, name, enable, status | receipts |


## Межі перевірки
- POST, PUT і DELETE не звірялись, бо це запис.
- Звірено лише ці 20 GET-ендпоінтів і ті дані, що зараз є на precorino. Поле, яке на цих даних ні разу не прийшло `null` або не трапилось, сюди не потрапить.
