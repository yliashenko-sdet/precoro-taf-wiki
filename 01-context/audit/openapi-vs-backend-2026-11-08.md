# OpenAPI-спека проти реальних відповідей бекенду, 2026-11-08

Для розробки. Спека з `/api/docs` (NelmioApiDoc) описує відповіді інакше, ніж їх реально повертає бекенд. Це не окремі помилки в анотаціях: майже всі розбіжності мають кілька спільних причин у генераторі схем `src/OpenApi/` і `src/Service/TransformerParser/`.

## Як перевірено
- 20 GET-ендпоінтів на `api.precorino.com`, 08.11.2026: 12 списків і 8 карток документів.
- Жива відповідь 200 порівнювалась зі схемою 200 у спеці. Для списків брався перший елемент, вкладені об'єкти до глибини 4.
- Скрипт `06-playbooks/scripts/spec_vs_live.js` лише читає, нічого не змінює.
- **Разом 385 розбіжностей.**

POST, PUT і DELETE не перевірялись, бо це запис. Список ендпоінтів неповний, тож реальна кількість більша.

## Розбіжності за причинами

### 1. Пагінація `meta` не оголошена (12 з 12 списків)
- **Спека:** `{ data: [...] }`. **Бекенд:** `{ data: [...], meta: { pagination } }`.
- **Причина (перевірено):** `OA\Response` пишеться вручну в кожному контролері й оголошує тільки `data`. Приклад: `src/Controller/Budget/Rest/BudgetRestController.php:78`. Таких оголошень `data: array` 130, і жодне не оголошує `meta`.
- **Як виправити:** спільний хелпер або атрибут «пагінована відповідь моделі X», щоб `meta` додавався в одному місці. Заміна 130 оголошень механічна.

### 2. Колекційні includes Fractal описані масивом, а приходять як `{ data: [...] }` (61)
- **Приклади:** `items`, `taxes`, `discounts`, `comments`, `payments`, `attachments`, `approvalSteps`, `dataDocumentCustomFields` в інвойсах, PO, RFP, чеках і expense; `paymentTerms` у постачальника.
- **Причина (перевірено):** `TransformerSchemaFactory::includeToProperty`, гілка `collection` ставить `type: array`. Fractal же серіалізує колекцію як об'єкт з ключем `data`.
- **Як виправити:** одна правка в цій гілці, `type: object` з властивістю `data: array`. Закриває всі 61 випадок.

### 3. Асоціативні масиви описані списком (25)
- **Приклади:** `exchangeRate` (`{"AFN:USD": …}`), `precisionData` (`{"USD": …}`), `creditBalanceSums` (`{"USD": …}`).
- **Причина (перевірено):** `TransformerSchemaFactory::mapType` і `TransformerParser::mapPhpTypeToSchema` перетворюють PHP `array` на OpenAPI `array`. PHP не розрізняє список і словник.
- **Як виправити:** для таких полів `type: object` з `additionalProperties`. Потрібна підказка в трансформері (phpdoc на кшталт `array<string, …>`) або перелік полів.

### 4. Не позначено `nullable` (87)
- **Приклади:** `externalId` (38 разів), `uniqueCode`, `phone`, `customName`, `description`, `image`, `supplierPartNumber` та інші.
- **Причина (гіпотеза):** `TransformerParser` виводить нульованість з типу геттера сутності. Ці поля, мабуть, читаються інакше (через `?->`, сервіс чи масив), і парсер її не бачить.

### 5. Хибний скалярний тип (62)
| Поле | Спека | Бекенд |
|---|---|---|
| `idn` в інвойсах, PO, RFP, PR, expense | number | string (`"781"`) |
| `netSum`, `minimumSum`, `blanketSum`, `prepaymentPercent`, `postpaymentPercent`, `creditPeriodDays` | string | number |
| `status`, `type`, `position`, `punchoutType` | string | number |
| `sumPaid` в інвойсі | number | string |
| `currencies` у постачальника | string | array |

- **Причина (частково перевірено):** невивідний тип (`mixed`) у `TransformerSchemaFactory::mapType` за замовчуванням стає `string`.
- **Гіпотеза:** `idn` береться з геттера сутності (int), а трансформер віддає його рядком.

### 6. Невизначений тип описано як `object` (97)
- **Приклади:** булеві `isPower`, `hasConfirmationToken`, `isBudgetOverLimit`; масиви `relatedPurchaseRequisitions`, `relatedRequestForProposals`, `relatedPurchaseOrders`, `relatedInvoices`; числа `parentBudgetId`, `availableSum`, `reservedSum*`; рядки `fullName`, `currency`.
- **Причина (гіпотеза):** `TransformerParser` дає `object` для виразів, тип яких зводиться до класу чи не виводиться (див. `mapPhpTypeToSchema`, гілка `class_exists`).

### 7. Поля, яких у спеці немає (15 місць)
- `children` у бюджету (списки й `expense.budget`), `options` у DCF/ICF, `dataSupplierCustomFields`.
- `price`, `purchasingUnit`, `dataItemCustomFields`, `bundleItems`, `groupItems` в айтема.
- Суми `sum*`, `netSum*`, `withholdingTaxSum` у PR.
- Вкладені `purchaseOrder` і `purchaseOrder.creator` в інвойсі й чеку: бекенд віддає повний об'єкт, спека описує кілька полів.
- **Причина (гіпотеза):** поля з `defaultIncludes`, умовні чи злиті через `array_merge`, які парсер не бачить. Вкладений item-include, мабуть, описано за іншим (скороченим) трансформером.

### 8. Об'єкт без жодної властивості (26)
- **Приклади:** `approvalInfo`, `approvalFlow`, `delegatedFromUser`, `allocatedInvoice`, `recognizedDocument`, `ocrAttachment`.
- `GET /api/reports/config` (разом із `columnsMetadata`) описано порожнім об'єктом, а бекенд віддає повний конфіг.
- **Причина (гіпотеза):** форму не виведено, і схема лишилась `{type: object}`. Для `reports/config` це ручний `OA\Response` без схеми.

## На що вже спираються тести TAF
Ці розбіжності TAF зачепив першими, коли типізував клієнт згенерованими з спеки типами:
- `meta` у списках бюджетів, постачальників, локацій, DCF і ICF: пагінація в менеджерах даних (п. 1).
- `items` у картках інвойсу, PO й RFP (п. 2).
- `relatedPurchaseRequisitions` у PO (п. 6).
- `children` у бюджету, `price` в айтема, `columnsMetadata` у конфігу звітів (пп. 7–8).
- `idn` документів рядком (п. 5).
- `id` у відповіді `POST /api/expenses`: спека оголошує тільки `idn`. Наживо не перевірялось, бо це запис; тести TAF на це поле покладаються.

## Пропозиція
1. Пп. 1 і 2 закриваються центральними правками й прибирають 73 розбіжності. Це найбільший виграш за найменшу роботу.
2. Пп. 3–8 потребують доробки `TransformerParser` або явних підказок у трансформерах. Це більша робота для власника генератора: усі коміти в `src/OpenApi/` і `src/Service/TransformerParser/` від Maksym Shchehel.
3. Щоб спека знову не розходилась із бекендом, додати перевірку «жива відповідь ↔ схема» в CI бекенду. Скрипт TAF можна взяти за основу.
