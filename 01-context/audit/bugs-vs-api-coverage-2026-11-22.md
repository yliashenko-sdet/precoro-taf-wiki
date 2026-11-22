# Баги критичних модулів проти API-покриття, 2026-11-22

Чи спіймали б API-тести реальні баги критичних модулів, якби ці модулі були покриті повніше. Розмітка кожного бага нижче. Висновки для плану — в обговоренні задач етапу 2 (T1-27, T1-18), тут лише дані.

## Як зібрано
- **Баги:** Asana, проєкт Bugs (`71082169842278`), Task Type = Bug, без сабтасків, створені 20.11.2025–20.11.2026, модуль з поля Module*. Запити через `search_tasks`, вікна дробились, поки кожне не давало < 100. Усього по 47 модулях 2 455 багів.
- **Ручні баги:** з них прибрано алерти моніторингу за назвою: префікси `[COM]`, `[US]`, `[HC]`, `[Duplicate]`, `[NetSuite]`, `[billing]`, `[mobile]`, `[ai]`, `[xero]`, `[QBO]`, `[ocr]`, `[MS]` і тексти винятків (`Exception`, `Error:`, `AxiosError`, `SQLSTATE`, `TypeError`, `Cron failure`, `CompanyId: N`). Евристика за назвою, тож поділ приблизний.
- **Модулі:** 12 критичних за кількістю ручних багів і блокувань клієнта. Один баг потрапив лише в один модуль.
- **Client blocked:** поле `Client blocked? = Yes`.
- **Розмітка:** за назвою бага, без відкриття задачі (Claude, 22.11). Існування потрібних ендпоінтів звірено з `src/api/openapi/precoro-openapi.json` (T1-25). 148 із 497 позначок невпевнені (колонка «?»).

## Кошики
| кошик | що означає |
|---|---|
| A | CRUD одного ресурсу: create/read/update/delete чи один перехід статусу документа з перевіркою збереженого стану, статусу, коду відповіді або ролі |
| B | API-сценарій через кілька документів: PR→PO→Invoice→matching, cancel PO з PR, CN на оплаченому інвойсі, prepayment, вимкнення модуля чи налаштування при відкритих документах |
| C | Лише UI: відображення, кнопки, стан фронту, фільтри й пагінація списків, мобільний застосунок |
| D | Поза API-тестами: якість OCR, інтеграції, вміст імпорту й експорту, листи, PDF, health-check, фікси даних, інфраструктура |

Межі: перевірка бюджету на одній дії документа (create, confirm, approve, cancel) — A; з матчингом, PO↔PR, PO↔Invoice або перемиканням налаштування — B. Поля самого Credit Note — A, його вплив на Invoice — B.

## Підсумок
| модуль | ручних | A | B | C | D | ? | client blocked | з них A+B |
|---|---|---|---|---|---|---|---|---|
| AP | 84 | 10 | 6 | 19 | 49 | 30 | 6 | 4 |
| PO | 68 | 17 | 32 | 8 | 11 | 12 | 5 | 5 |
| Budget | 63 | 15 | 18 | 19 | 11 | 19 | 8 | 6 |
| Split Costs | 52 | 28 | 15 | 7 | 2 | 20 | 6 | 6 |
| Invoice | 44 | 8 | 20 | 15 | 1 | 13 | 4 | 2 |
| Import/export | 44 | 0 | 0 | 2 | 42 | 3 | 3 | 0 |
| Approval | 42 | 15 | 18 | 3 | 6 | 17 | 6 | 5 |
| PR | 33 | 4 | 12 | 13 | 4 | 10 | 3 | 0 |
| Budget Parts | 23 | 12 | 10 | 1 | 0 | 10 | 3 | 3 |
| Credit Note | 16 | 6 | 8 | 2 | 0 | 6 | 4 | 4 |
| RFP | 16 | 8 | 2 | 3 | 3 | 6 | 4 | 2 |
| Budget Limit | 12 | 3 | 9 | 0 | 0 | 2 | 3 | 3 |
| **разом** | **497** | **126** | **150** | **92** | **129** | **148** | **55** | **40** |

A+B: 276 із 497 (56%), серед багів, що блокували клієнта, 40 із 55.

## Що ловить A і що ловить B
- **A:** після кожного create/update/переходу перечитати документ і звірити всі поля, зокрема внутрішні (`status_*`, `is_all_items_*`, `logic_type`, `can_be_received`, savings, суми бюджету). Негативні випадки: неактивний LE, вимкнене налаштування чи DCF, роль без права → очікується 4xx, не 500. По одному тесту на перехід (approve, revise, repeat, cancel, reject позиції, mass edit) під різними ролями.
- **B:** ланцюжки з перевіркою пов'язаних документів після кожного кроку: PR→PO→Receipt/Invoice→approve матчингу, потім `status_payment`, waiting і completed з обох боків; `used_sum` бюджету і переліміт після approve матчингу, cancel, CN, prepayment; стан відкритих документів після вимкнення модуля (Invoices, Receipts, Payments, Budget Breakdown, Splits).
- **Не API:** C і D разом 45%. AP переважно D (OCR, вебхуки, пошта), Import/export майже весь D.

## Покриття цих модулів зараз (22.11)
| модуль | операцій спеки, що викликає smoke `test_api` | кейсів у Qase з Run scope = Smoke |
|---|---|---|
| PO | 10 із 72 | 9 |
| Invoice | 4 із 54 | 10 |
| PR | 7 із 54 | 6 |
| RFP | 7 із 39 | 7 |
| Budget | 1 із 10 (`/api/budgets`) | 2 |
| Budget Parts | 0 (`budget_parts` у PO й Invoice) | 5 |
| Budget Limit | 0 | 2 |
| Split Costs | 0 (`split` у PO й Invoice) | 0 |
| Approval | 0 (`approvalsteps` smoke не викликає) | 5 |
| Credit Note | 0 (`credit_note` smoke не викликає) | 1 |
| AP | 2 із 29 | 0 |
| Import/export | 0 | 0 |

Джерела: операції — кроки API у smoke 20.11 (`~/local-runs/2026-11-20-0009-t1-25-typed-areas/results.json`) проти знімка спеки T1-25; Smoke — поле Module і Run scope кейсів PTC (Qase API, 22.11). Прапорець IsBug у Qase стоїть на 1 кейсі (2326), defects 41 унікальний, 33 з 2025 року, тож баги рахуються з Asana.

## Розмітка
| # | модуль | кошик | ? | client blocked | баг |
|---|---|---|---|---|---|
| 1 | AP | A | ? |  | [500 при створенні CN з Інвойса з OCR, якщо ІКФ опшен на айтемі задізеблений](https://app.asana.com/0/0/1213750407811821) |
| 2 | AP | A |  |  | [AP Inbox: автостворення інвойсу на неактивних Legal Entity і Location (API)](https://app.asana.com/0/0/1220423198070027) |
| 3 | AP | A | ? | так | [Unable to create the invoice from the AP Inbox due to a tax error](https://app.asana.com/0/0/1218259698408556) |
| 4 | AP | A | ? | так | [Tax Error While Creating an Invoice fromAP Inbox](https://app.asana.com/0/0/1217266686787492) |
| 5 | AP | A | ? |  | [Discount Error While Invoice Processing through AP Inbox](https://app.asana.com/0/0/1218280562551405) |
| 6 | AP | A | ? | так | [The ‘Selected choice is invalid’ error message appears during OCR invoice creation](https://app.asana.com/0/0/1214414482517253) |
| 7 | AP | A | ? |  | [Inforcard on OCR page doesn't work [this value should be of type numeric error]](https://app.asana.com/0/0/1214104856411991) |
| 8 | AP | A | ? |  | [В Credit Note створеному з OCR можна редагувати Tax на товарі](https://app.asana.com/0/0/1213198395204138) |
| 9 | AP | A | ? |  | [OCR: Enter Invoice as one line проставляє розпізнаний total в price для Free of Сharge товару](https://app.asana.com/0/0/1216203903791654) |
| 10 | AP | A | ? | так | [Спрацьовує валідація на ICF опшен бюджета при створенні AP Inbox Інвойса](https://app.asana.com/0/0/1216064713635857) |
| 11 | AP | B | ? |  | [[CN from OCR] [HC][invoice]invoice_item where price >= 0 and chartSum < 0: Count 1, 4757748](https://app.asana.com/0/0/1212268565093129) |
| 12 | AP | B | ? |  | [Створення Invoice from PO (Custom Form) з OCR без жодної PO ролі неможливе - повертає 403](https://app.asana.com/0/0/1213312064227618) |
| 13 | AP | B | ? |  | [Location not auto-populated from PO](https://app.asana.com/0/0/1213804676488813) |
| 14 | AP | B |  |  | [В CN (створеному з OCR) сума товару більша ніж в Invoice](https://app.asana.com/0/0/1212977783267491) |
| 15 | AP | B | ? |  | [OCR: при метчингу до сервіс айтема сума айтема стає відʼємною із відʼємним таксом](https://app.asana.com/0/0/1212885027300762) |
| 16 | AP | B |  |  | [Створили CN from Invoice через OCR, в якому сума таксу на 0.01 більша, ніж в інвойсі](https://app.asana.com/0/0/1216188415290438) |
| 17 | AP | C |  |  | [не можу зберегти фільтр Assignee кнопкою "save filter"](https://app.asana.com/0/0/1214121199700282) |
| 18 | AP | C | ? |  | [Поправити нульові айтеми, щоб вони відображались](https://app.asana.com/0/0/1213819324582177) |
| 19 | AP | C |  |  | [Totals are displayed as NaN in the AP Inbox](https://app.asana.com/0/0/1213609322437311) |
| 20 | AP | C | ? |  | [Wrong totals in the AP Inbox attachments list](https://app.asana.com/0/0/1213682771977181) |
| 21 | AP | C |  |  | [вибір єдиної опції -має бути одразу, а не через зайві кліки](https://app.asana.com/0/0/1220574375075861) |
| 22 | AP | C |  |  | [[Add with AI] Тултип закривається при наведенні, на посилання неможливо натиснути](https://app.asana.com/0/0/1220555723443439) |
| 23 | AP | C |  |  | [змінились стилі в Ап Інбокс](https://app.asana.com/0/0/1220426268268650) |
| 24 | AP | C |  |  | [не працює галочка масових дій](https://app.asana.com/0/0/1220430463679115) |
| 25 | AP | C | ? |  | [Gross Total in AP Inbox is Incorrect](https://app.asana.com/0/0/1217258228218546) |
| 26 | AP | C |  | так | [Tax is blocked for selection in the AP Inbox CN creation window](https://app.asana.com/0/0/1217314421642108) |
| 27 | AP | C |  |  | [Не округляється тотал у таблиці ОСР атачментів](https://app.asana.com/0/0/1213431859436430) |
| 28 | AP | C | ? | так | [Unable to Preview Files in AP Inbox with % symbol](https://app.asana.com/0/0/1214133019051187) |
| 29 | AP | C | ? |  | [Не працють кастомні форми на Invoice from PO with OCR](https://app.asana.com/0/0/1213975674351560) |
| 30 | AP | C |  |  | [Не відображаються вибрані DCF опшени та empty в збережених фільтрах Ap Inbox](https://app.asana.com/0/0/1214415397222766) |
| 31 | AP | C |  |  | [Не фільтрується список ЛЕ відносно саплаєра на створенні інвойсу з ОСР, коли саплаєр підтягнувся на форму з dentified Supplier](https://app.asana.com/0/0/1213035730048827) |
| 32 | AP | C |  |  | [Не видно постачальника у селекті AP inbox](https://app.asana.com/0/0/1212803754104259) |
| 33 | AP | C |  |  | [Не блокувати кнопку -Щоразу йдуть запити до api/account/billingvalues на сторінці інвойсів](https://app.asana.com/0/0/1213198403052027) |
| 34 | AP | C | ? |  | [Department/Project defaults not auto-filling in AP inbox](https://app.asana.com/0/0/1217246162308251) |
| 35 | AP | C |  |  | [не працює фільтр по тегах](https://app.asana.com/0/0/1216556815470080) |
| 36 | AP | D |  |  | [Transport error sending document to Microservice. Data: {"document_type":0,"provider_type":1,"company_data":{"precoro_id":16164,"precoro_name":"Four Hands LLC"},"account_data":{"precoro_id":15359,"precoro_name":"Four Hands"}} Code: 0 Detail: Idle timeou...](https://app.asana.com/0/0/1212503447975020) |
| 37 | AP | D | ? |  | [OcrWebhookMessageHandler виконав створення Invoice from PO через OCR (Auto-Create with AI) коли модуль Invoices був вимкнений](https://app.asana.com/0/0/1213035593528817) |
| 38 | AP | D |  |  | [Failed to parse XML. Document is likely corrupted.](https://app.asana.com/0/0/1212266969783152) |
| 39 | AP | D |  |  | [PHP-FPM: Worker Pool Exhausted (max_children reached)](https://app.asana.com/0/0/1212908731371672) |
| 40 | AP | D |  |  | [Transport error sending document to Microservice. Data: {"document_type":0,"provider_type":1,"company_data":{"precoro_id":20240,"precoro_name":"Virtual Pipeline Ventures"},"account_data":{"precoro_id":19105,"precoro_name":"VP Ventures"}} Code: 0 Detail:...](https://app.asana.com/0/0/1212294169919147) |
| 41 | AP | D |  |  | [PHP-FPM: Worker Pool Exhausted (max_children reached)](https://app.asana.com/0/0/1212669289505876) |
| 42 | AP | D |  |  | [Attention! The ResendGmailUnreadMessagesCommand has found 12 bad cases.](https://app.asana.com/0/0/1212442657972218) |
| 43 | AP | D |  |  | [Transport error sending document to Microservice. Data: {"document_type":0,"provider_type":1,"company_data":{"precoro_id":9414,"precoro_name":"Zasbi"},"account_data":{"precoro_id":9083,"precoro_name":"Zasbi Management"}} Code: 0 Detail: Idle timeout rea...](https://app.asana.com/0/0/1212301132926845) |
| 44 | AP | D |  |  | [Vertex AI Error by document processing: {](https://app.asana.com/0/0/1213869787119483) |
| 45 | AP | D | ? |  | [OCR \| неправильно проставляється rounding в інвойсах](https://app.asana.com/0/0/1213689869789821) |
| 46 | AP | D | ? |  | [Documents processed \| Sentinel Contracting](https://app.asana.com/0/0/1213719826007696) |
| 47 | AP | D |  |  | [OCR неправильно розпізнає саплаєр нейм, коли є декілька схожих](https://app.asana.com/0/0/1213987769528793) |
| 48 | AP | D |  |  | [Vertex AI Error by document processing: {](https://app.asana.com/0/0/1213872957273626) |
| 49 | AP | D |  |  | [Vertex AI Error by document processing. Document ID: 268957 Detail: {](https://app.asana.com/0/0/1214002654409873) |
| 50 | AP | D | ? |  | [Потрібний курс валют не записується в Інвойс автостворений з OCR](https://app.asana.com/0/0/1213872949408104) |
| 51 | AP | D | ? |  | [issue with auto-created invoice in AP inbox](https://app.asana.com/0/0/1219773460771648) |
| 52 | AP | D |  |  | [Skipping PDF conversion: previous attempt crashed the worker](https://app.asana.com/0/0/1219113627206103) |
| 53 | AP | D |  |  | [Gmail push pipeline missed 1 unread email(s), recovered by reprocessor](https://app.asana.com/0/0/1218411809566133) |
| 54 | AP | D |  |  | [Precoro webhook returned error. ID: 36253 Status: 400 Body: "Attachment wasn\u0027t created. Check request data"](https://app.asana.com/0/0/1217980069718177) |
| 55 | AP | D |  |  | [Attention! The ResendGmailUnreadMessagesCommand has found 7 bad cases.](https://app.asana.com/0/0/1218082339107595) |
| 56 | AP | D |  |  | [Some "invoices" in AP inbox appear to be Amazon confirmation emails and should not be created](https://app.asana.com/0/0/1217795534707141) |
| 57 | AP | D | ? |  | [поправити мепінг такс лайнів ( автостворення інвойсу до ПО)](https://app.asana.com/0/0/1217896577585606) |
| 58 | AP | D |  |  | [Precoro webhook returned error. ID: 36253 Status: 400 Body: "Attachment wasn\u0027t created. Check request data"](https://app.asana.com/0/0/1217881551291941) |
| 59 | AP | D | ? |  | [Duplicated invoices in OCR inbox](https://app.asana.com/0/0/1217786189725196) |
| 60 | AP | D |  |  | [OCR wrongly added tax to invoice](https://app.asana.com/0/0/1217538084415979) |
| 61 | AP | D |  |  | [Precoro webhook returned error. ID: 33726 Status: 400 Body: "Attachment wasn\u0027t created. Check request data"](https://app.asana.com/0/0/1217750248705117) |
| 62 | AP | D |  |  | [Matching being triggered - amount being recognized as quantity instead of price](https://app.asana.com/0/0/1216018815603432) |
| 63 | AP | D |  |  | [Precoro webhook returned error. ID: 29250 Status: 400 Body: "Attachment wasn\u0027t created. Check request data"](https://app.asana.com/0/0/1217618584383771) |
| 64 | AP | D | ? |  | [VAT in Credit Notes](https://app.asana.com/0/0/1217565970037803) |
| 65 | AP | D |  |  | [Unable to download file from S3](https://app.asana.com/0/0/1215824675971018) |
| 66 | AP | D | ? |  | [Глянути чому вийшло на 0.01 більше](https://app.asana.com/0/0/1216199682194039) |
| 67 | AP | D |  |  | [Edenred SFTP: filesystem error](https://app.asana.com/0/0/1216255273385323) |
| 68 | AP | D |  |  | [Precoro webhook returned error. ID: 4129 Status: 502 Body: <!DOCTYPE html>](https://app.asana.com/0/0/1215327345973893) |
| 69 | AP | D |  |  | [Unknown XML format. Could not identify CFDI, UBL, or CII. Root: Invoice Namespace: rrn:org.xcbl:schemas/xcbl/v4_0/financial/v1_0/financial.xsd Document ID: 224299 Host: app.precorino.com](https://app.asana.com/0/0/1213452394679321) |
| 70 | AP | D |  |  | [Vertex AI Error by document processing: {](https://app.asana.com/0/0/1213764361388766) |
| 71 | AP | D |  |  | [OCR Invoice-PO matching AI suggests PO in matching status for auto-creation](https://app.asana.com/0/0/1213796688509340) |
| 72 | AP | D |  |  | [Автостворює простий інвойс, хоч є розпізнано orderNumber](https://app.asana.com/0/0/1214690377243147) |
| 73 | AP | D | ? |  | [[OCR.precorino] не створюється інвойс на РО](https://app.asana.com/0/0/1212817718463085) |
| 74 | AP | D |  |  | [League\Flysystem\UnableToListContents: Unable to list contents for '/PayTech/AP_Invoice_PayTech-GIS', shallow listing](https://app.asana.com/0/0/1216425564424907) |
| 75 | AP | D |  |  | [League\Flysystem\UnableToListContents: Unable to list contents for '/PayTech/AP_Invoice_PayTech-GIS', shallow listing](https://app.asana.com/0/0/1216354677337126) |
| 76 | AP | D |  |  | [League\Flysystem\UnableToReadFile: Unable to read file from location: b8aea7cbd42f8beecaa541bf822822640684d8a2.pdf.](https://app.asana.com/0/0/1215707045151451) |
| 77 | AP | D |  |  | [SFTP error. Code: 0 Detail: Unable to list contents for '/PayTech/AP_Invoice_PayTech-GIS', shallow listing](https://app.asana.com/0/0/1215509162811671) |
| 78 | AP | D |  |  | [League\Flysystem\UnableToReadFile: Unable to read file from location: de531e05d5076536818ab50e9f54402f53f2dd74.pdf.](https://app.asana.com/0/0/1215322410174041) |
| 79 | AP | D |  |  | [Unable to download file from S3](https://app.asana.com/0/0/1215324608126097) |
| 80 | AP | D | ? |  | [не мепиться такс](https://app.asana.com/0/0/1215963052508240) |
| 81 | AP | D |  |  | [[Back Up Task]Precoro webhook returned error. ID: 29250 Status: 400 Body: "Attachment wasn\u0027t created. Check request data"](https://app.asana.com/0/0/1217500114962693) |
| 82 | AP | D |  |  | [[Back Up Task][HC]Attachments that have been sending to a Google provider and have been in the processing status for more than 4 hours: Count 3, 58174, 58175, 58217](https://app.asana.com/0/0/1217354538637428) |
| 83 | AP | D |  |  | [[Xero+Netsuite] Не передається атачмент з РО створеного через AI Scan](https://app.asana.com/0/0/1216947248940353) |
| 84 | AP | D |  |  | [Cannot send notification to Precoro: file not uploaded to S3. ID: 16840](https://app.asana.com/0/0/1216824456848385) |
| 85 | PO | A |  |  | [is_all_items_received має значення 1 при створенні ПО/СПО, поки не додати перший айтем](https://app.asana.com/0/0/1212300997735254) |
| 86 | PO | A |  |  | [Якщо передати в запиті POST purchaseorders ключ documentDiscount з значенням {"id": null} падає 500](https://app.asana.com/0/0/1214346664101802) |
| 87 | PO | A | ? |  | [Можна конфірмнути і апрувнути документ, коли постачальник на статусі Pending Form](https://app.asana.com/0/0/1213231042749321) |
| 88 | PO | A |  | так | [Не працює оверфлоу кастомної нумерації з форматом дати з днями](https://app.asana.com/0/0/1213315461371041) |
| 89 | PO | A | ? |  | [Розібратись з дублюванням діскаунтів 0.00% на айтемі в PO](https://app.asana.com/0/0/1212768277311044) |
| 90 | PO | A | ? | так | [Unable to confirm PO item line edits](https://app.asana.com/0/0/1214378738982493) |
| 91 | PO | A |  |  | [Після мапінгу з tax item каталожного айтему non-inventory не змінюється logic_type на 0](https://app.asana.com/0/0/1218807233563081) |
| 92 | PO | A | ? |  | [Terms&Conditions are not updated in PO](https://app.asana.com/0/0/1218762251709341) |
| 93 | PO | A |  |  | [Не рахувати savings по айтемам, де baseline price = 0 або 1](https://app.asana.com/0/0/1218705798385890) |
| 94 | PO | A |  |  | [Після апруву ПО savings на рівні документу не перераховується](https://app.asana.com/0/0/1219095457019490) |
| 95 | PO | A | ? | так | [Baseline Price issue on the PO](https://app.asana.com/0/0/1217732193804566) |
| 96 | PO | A |  |  | [Виникає Diff sum in PurchaseOrder savingsSum 2650689 - backend sum: -100.00, frontend sum: 14900.00 після реджекту amount-based item з каталогу](https://app.asana.com/0/0/1217942714119849) |
| 97 | PO | A | ? |  | [unable to confirm PO due to an issue with COA](https://app.asana.com/0/0/1217865879014925) |
| 98 | PO | A |  | так | [Неможливо заріджектити амаунт таксу в ПО](https://app.asana.com/0/0/1216779205186192) |
| 99 | PO | A | ? |  | [Розбіжність суми (DiffSumError) у Purchase Requisition при оновленні айтема backend sum: 1097.80, frontend sum: 49.90.](https://app.asana.com/0/0/1215869932180065) |
| 100 | PO | A |  |  | [Шипінг айтем має CanBeReceived = 1, якщо додається в ПО через емпті роу і мепиться з каталожним шипінг айтемом](https://app.asana.com/0/0/1215678060343117) |
| 101 | PO | A |  |  | [Free of charge Tax Items cannot be rejected / removed from PO](https://app.asana.com/0/0/1215688207370888) |
| 102 | PO | B |  |  | [PO зі статусом Paid має is_all_items_invoiced = false (Free of charge товар)](https://app.asana.com/0/0/1212501979116750) |
| 103 | PO | B |  |  | [Cannot reject PR item with disabled ICF Option on the Purchase Orders → From Requisition menu \| You don't have access to the 786039 option from the NetSuite Departments ICF](https://app.asana.com/0/0/1213495279847001) |
| 104 | PO | B |  |  | [Не оновлюється status_payment не першого в списку РО після видалення Draft мульти-інвойса через вимкнення модулю Invoices](https://app.asana.com/0/0/1214146798162283) |
| 105 | PO | B |  | так | [падає 500 при створенні кастомного ПО з ПР](https://app.asana.com/0/0/1213607645111773) |
| 106 | PO | B |  |  | [Неправильно значеня budgeted sum на PO із Invoice та Credit Note](https://app.asana.com/0/0/1213724079225178) |
| 107 | PO | B |  |  | [Automatically created PO from PR in incorrect status](https://app.asana.com/0/0/1213739895261815) |
| 108 | PO | B |  |  | [Не можна PO - Mark as Completed, якщо частковий Invoice містить WHT Item](https://app.asana.com/0/0/1214285189790270) |
| 109 | PO | B |  |  | [Падає помилка при спробі відредагувати айтем PO на метчінгу](https://app.asana.com/0/0/1212760668398166) |
| 110 | PO | B |  |  | [При створенні ПО з ПР, айтеми в ПО додаються не в тому порядку що  в ПР](https://app.asana.com/0/0/1212743820171912) |
| 111 | PO | B |  |  | [При створені ПО з ПР, в якого айтеми в другорядній валюті, при створені підтягується базова](https://app.asana.com/0/0/1213816323190689) |
| 112 | PO | B |  |  | [ПО-айтеми з типом tax, shipping створюються з can_be_received = 1 при австостворенні з ПР](https://app.asana.com/0/0/1214625402269158) |
| 113 | PO | B |  |  | [Автоматично створене ПО з ПР створюється з ЛЕ, яка не підходить по депендах](https://app.asana.com/0/0/1212584014133577) |
| 114 | PO | B |  |  | [Можна видалити заінвойшений amount based айтем в ПО, якщо айтем в інвойсі free of charge](https://app.asana.com/0/0/1220232665636850) |
| 115 | PO | B |  |  | [SO отримує статус Paid при наявності незаінвойсованих від'ємних айтемів](https://app.asana.com/0/0/1220240786151749) |
| 116 | PO | B |  |  | [invoiced не оновлюється в ПО-айтемах, якщо Інвойс був Pending Receipt і став Approved після апруву КН](https://app.asana.com/0/0/1216387444120155) |
| 117 | PO | B |  |  | [Неправильний status_payment в ПО, якщо є два Інвойси (Draft i Paid) і вимикається модуль Інвойсів](https://app.asana.com/0/0/1216190552421723) |
| 118 | PO | B |  |  | [Створення Invoice from PO при статусі Draft в PO через API](https://app.asana.com/0/0/1218728303030495) |
| 119 | PO | B |  |  | [Ціна айтему залишаєтсья 0 при зміні статусу на approved при видаленні апрувал флоу](https://app.asana.com/0/0/1218454311004225) |
| 120 | PO | B |  |  | [Такс айтем створюється з type 4, але logic_type 0 при автостворенні ПО з ПР (в ПР-айтема logic_type теж 0)](https://app.asana.com/0/0/1216926348284334) |
| 121 | PO | B |  |  | [Помилка після апруву matching з receipt при зміні кількості, якщо був вказаний baseline price: Diff sum in PurchaseOrder savingsSum 2247668 - backend sum: 470.70, frontend sum: 627.60](https://app.asana.com/0/0/1218276643634734) |
| 122 | PO | B | ? |  | [При автостворенні invoice з OCR проставляється  logic_type = 0 для tax item](https://app.asana.com/0/0/1216613999664952) |
| 123 | PO | B |  |  | [Після вимкнення модуля Інвойсів status_payment не скидається на одному з PO при метчингу з інвойсом](https://app.asana.com/0/0/1215962658707787) |
| 124 | PO | B |  |  | [Айтем додається з Інвойса в ПО з can_be_received = 1, якщо модуль ресіптів вимкнено](https://app.asana.com/0/0/1216187600465276) |
| 125 | PO | B |  |  | [Падає помилка при реджекті айтемів на Create PO from PR page](https://app.asana.com/0/0/1215955206210897) |
| 126 | PO | B | ? |  | [Сума в PO на такс айтем не змінюється на залишок](https://app.asana.com/0/0/1215231298358444) |
| 127 | PO | B |  |  | [500 при створенні СПО з ПР з айтемом типу такс](https://app.asana.com/0/0/1215227599064401) |
| 128 | PO | B |  |  | [При вимкненні payment залишаєтсья prepayment в PO з невикористаним балансом, якщо скасувати  в інвойсі](https://app.asana.com/0/0/1216420112497270) |
| 129 | PO | B |  |  | [Can't complete the PO, although all invoices are paid and Received / Paid amounts match](https://app.asana.com/0/0/1216594904871315) |
| 130 | PO | B |  |  | [По кліку на кнопку Update price by catalog ціна такс айтема у РО може бути меншою за Invoice](https://app.asana.com/0/0/1216368333265416) |
| 131 | PO | B |  |  | [Can be received з true стає false після вимкнення модулю Receipt і редагування айтему в РО на якого є Receipt](https://app.asana.com/0/0/1216647106882743) |
| 132 | PO | B |  |  | [Нересівнутий айтем реджектиться в частково отриманому БПО після вимкнення Інвойсів, якщо тотал БПО не повністю інвойснутий](https://app.asana.com/0/0/1216234928447094) |
| 133 | PO | B |  |  | [В PO№1 проставляється статус not paid після апруву метчингу PO№2](https://app.asana.com/0/0/1216348608264338) |
| 134 | PO | C |  |  | [User search in 'Purchaser' field displays all users](https://app.asana.com/0/0/1213612691635949) |
| 135 | PO | C |  |  | [Імейли в DCF конвертуються в лінку (селектор написаний як Plain Text) на документах](https://app.asana.com/0/0/1213802992886283) |
| 136 | PO | C | ? |  | [Немає кнопки Revise на ПО та Інвойсі/Ресіпті, коли вони на метчингу і кріейтор ПО вже апрувнув метчинг](https://app.asana.com/0/0/1213733657843709) |
| 137 | PO | C |  |  | [Перекривати лоудером пагінацію поки не відпрацює запит](https://app.asana.com/0/0/1213038422160016) |
| 138 | PO | C |  |  | [Поле саплаєра пусте, хоч саплаєр обраний](https://app.asana.com/0/0/1217186012858367) |
| 139 | PO | C |  |  | [Fix Purchase Orders “+” Button to Open Service Order Creation Form](https://app.asana.com/0/0/1217759211259254) |
| 140 | PO | C |  |  | [В полі Contracts відображається порожня заглушка, якщо змінити постачальника в СПО/БПО](https://app.asana.com/0/0/1217543722286224) |
| 141 | PO | C | ? |  | [Confusing billing amounts in PO](https://app.asana.com/0/0/1215959215753735) |
| 142 | PO | D |  |  | [getFailedPurchaseOrdersCount повільно відпрацьовує (15+ с)](https://app.asana.com/0/0/1213761324756809) |
| 143 | PO | D |  |  | [Не видаляється звʼязок якщо зробити Reject PO from PR через Slack](https://app.asana.com/0/0/1220503375033949) |
| 144 | PO | D |  |  | [Команда на виправлення savings для sum-based PO айтемів та айтемів з негативним baseline price](https://app.asana.com/0/0/1219086344807150) |
| 145 | PO | D |  |  | [SO Імпортуєтсья без проставленого net total - айтеми free of charge](https://app.asana.com/0/0/1219916977327522) |
| 146 | PO | D |  |  | [При імпорті item не змінюється status_receiving з Non-receivable на Not received](https://app.asana.com/0/0/1219721303193810) |
| 147 | PO | D | ? |  | [Стоврився tax item з item level tax при створенні через ai scanning](https://app.asana.com/0/0/1218395044669539) |
| 148 | PO | D |  |  | [[banner]CSM email not found for company 17380 (csm name: "Yevheniia Karnaukh")](https://app.asana.com/0/0/1218299256842577) |
| 149 | PO | D |  |  | [[elasticsearch]ES indexing failed: No enabled connection](https://app.asana.com/0/0/1217206592410599) |
| 150 | PO | D |  |  | [[elasticsearch]ES indexing failed: Operation timed out](https://app.asana.com/0/0/1215958663210448) |
| 151 | PO | D |  |  | [Масовий апдейт айтемів на сторінці purchase/order/create/from_requests викликає 524](https://app.asana.com/0/0/1216190490013156) |
| 152 | PO | D |  |  | [[elasticsearch]ES indexing failed: Operation timed out](https://app.asana.com/0/0/1216413237818724) |
| 153 | Budget | A | ? |  | [[budget]Budget overlimit false positive on BudgetOnCustomFieldService::setBudgetInItem](https://app.asana.com/0/0/1220727968285776) |
| 154 | Budget | A |  | так | [Budget line edit throws false validation error when reallocating unspent amounts](https://app.asana.com/0/0/1220290143350091) |
| 155 | Budget | A |  |  | [Перераховувати used суми бюджета щоразу, коли змінюється бюджетна сума айтема/документа](https://app.asana.com/0/0/1219854757840189) |
| 156 | Budget | A |  |  | [можу редагувати бюджет, хоча не маю достатньо ролей](https://app.asana.com/0/0/1219155113994437) |
| 157 | Budget | A | ? |  | [4 бюджети завжди повертаються після запиту до доступних бюджетів при створенні документу: [HC][budget]Found in invoices with bad budget Access parameters (dcf options) : Count 2, 2387974, 2391705](https://app.asana.com/0/0/1217777482767564) |
| 158 | Budget | A |  |  | [Не обнуляється used_sum в баджет лайні при кенселі документа, який використовує ICF бюджет](https://app.asana.com/0/0/1216895792951188) |
| 159 | Budget | A |  | так | [Updatating Budget Amount Doesn't Work](https://app.asana.com/0/0/1216606926278667) |
| 160 | Budget | A |  |  | [не видаляє budgetParts при реджекті items](https://app.asana.com/0/0/1212933883383384) |
| 161 | Budget | A | ? |  | [Створені порожні бюджети не відображаються, якщо в юзера доступи не до всіх локацій](https://app.asana.com/0/0/1212149391602800) |
| 162 | Budget | A |  |  | [Можна створити бюджет, якщо в момент створення деактивувати ІКФ/ДКФ](https://app.asana.com/0/0/1213123854475412) |
| 163 | Budget | A | ? |  | [Дати в періоді зміщуються на один день при апдейті бюджета](https://app.asana.com/0/0/1213983820708730) |
| 164 | Budget | A |  | так | [На сторінці редагування бюджету можна додати однакові періоди бюджету](https://app.asana.com/0/0/1212625598621123) |
| 165 | Budget | A | ? |  | [неможливо зберегти назву бюджету після її редагування](https://app.asana.com/0/0/1212021405994131) |
| 166 | Budget | A | ? |  | [Галка required budgets змінюється на 1 після рестару апрувалу для ПР](https://app.asana.com/0/0/1213750538978196) |
| 167 | Budget | A | ? |  | [Юзер може вписати невалідну дату в Starting From при створенні бюджету](https://app.asana.com/0/0/1214625061811138) |
| 168 | Budget | B |  |  | [Переліміт бюджету якщо змінити отриману кількість в ресіпті через ревайз і зміна в межах TL](https://app.asana.com/0/0/1220006565126944) |
| 169 | Budget | B |  |  | [Не оновився parent_budget.all_location_ids після авто-видалення баджет лайну через видалення ICF Option, який був на цьому баджет лайні](https://app.asana.com/0/0/1218142773711106) |
| 170 | Budget | B |  |  | [500 при видаленні бюджета, що використовується в документі на драфті](https://app.asana.com/0/0/1218730324384958) |
| 171 | Budget | B |  |  | [Авто-видалення сплітованого драфту після деактивації юзера, мінусувало бюджетну суму](https://app.asana.com/0/0/1218214253617157) |
| 172 | Budget | B |  | так | [PO is blocked by overbudget limit while the budget only used by related PR](https://app.asana.com/0/0/1217815773324192) |
| 173 | Budget | B |  |  | [Сума доданого в Інвойсі айтема враховується в бюджеті і з ПО і з Інвойса після метчингу, якщо в ПО був препеймент](https://app.asana.com/0/0/1216332167137920) |
| 174 | Budget | B |  |  | [В used_sum_in_purchase_order не записується сума товару додана без матчингу, коли інвойс на матчингу з іншим РО](https://app.asana.com/0/0/1215860156352212) |
| 175 | Budget | B |  |  | [На rejected товар в PO from PR записується budget_id при зміні постачальника](https://app.asana.com/0/0/1216236145946162) |
| 176 | Budget | B |  |  | [Бюджетна і чартова суми ПР-айтема обнуляються після реджекту ПО-айтема](https://app.asana.com/0/0/1215350841367259) |
| 177 | Budget | B |  | так | [Overbudget error while approving matching when there is no overlimit](https://app.asana.com/0/0/1215092367444378) |
| 178 | Budget | B |  |  | [Айтем що додається з Інвойса в ПО після метчингу враховується в бюджеті двічі, якщо в ПО був препеймент](https://app.asana.com/0/0/1214929518997393) |
| 179 | Budget | B |  | так | [Can't add negative item to PO from PR](https://app.asana.com/0/0/1213817956022240) |
| 180 | Budget | B |  |  | [Переліміт при конфірмі часткового Інвойса з ПО через округлення](https://app.asana.com/0/0/1213883286536140) |
| 181 | Budget | B |  |  | [Мінусовий айтем спліт-документів не враховується в used сумі ІКФ бюджета](https://app.asana.com/0/0/1214126474138915) |
| 182 | Budget | B |  |  | [Галка is_required_budget стає 1 для інвойса на Pending Receipt після вимкнення модулю Ресіптів](https://app.asana.com/0/0/1213384052192706) |
| 183 | Budget | B |  |  | [Не видаляється budget_sub_line, якщо він використаний тільки в спліт документах на драфті](https://app.asana.com/0/0/1213966551753585) |
| 184 | Budget | B |  |  | [500 при видаленні бюджету, в якого є зарезервована сума і лайн містить більше 20 саблайнів](https://app.asana.com/0/0/1213464748590002) |
| 185 | Budget | B |  |  | [Можна змінити Deducted Sum бюждету, якщо той використаний тільки в документах з баджет партами](https://app.asana.com/0/0/1213326782884286) |
| 186 | Budget | C | ? |  | [1 item over budget. Click to review  - не зрозуміла логіка](https://app.asana.com/0/0/1220291474377611) |
| 187 | Budget | C |  |  | [Помилка в текстовці на прев'ю для документів без бюджету](https://app.asana.com/0/0/1219274395344851) |
| 188 | Budget | C | ? |  | [При створенні бюджета через новий дизайн з фронта передається allItemCustomFieldOptionsIds: ""](https://app.asana.com/0/0/1219098462422224) |
| 189 | Budget | C |  | так | [Safari: unable to edit budget amounts in Budgets module](https://app.asana.com/0/0/1218696630539135) |
| 190 | Budget | C | ? |  | [Бюджети не фільтруються по LE під час пошуку в полі Budgets звичайного документа (без сплітів / баджет партів), якщо шуканий бюджет не в першій сотні](https://app.asana.com/0/0/1217450649455485) |
| 191 | Budget | C |  |  | [NaN замість порядкових номерів бюджетів при переході на останню сторінку пагінації](https://app.asana.com/0/0/1217450649455513) |
| 192 | Budget | C |  |  | [Не відображається валюта бюджету в документі](https://app.asana.com/0/0/1215962741186766) |
| 193 | Budget | C |  |  | [Filter by ICF on show budget is not working correctly](https://app.asana.com/0/0/1214435939904661) |
| 194 | Budget | C |  |  | [Відсутня фільтрація при фільтрації по двом параметрам з ДКФ (мультиселект)](https://app.asana.com/0/0/1214505155079659) |
| 195 | Budget | C |  |  | [Wise Productions \| Filter by ICF in budgets is not working](https://app.asana.com/0/0/1214185725411679) |
| 196 | Budget | C |  |  | [фільтри в бюджеті не працюють коректно](https://app.asana.com/0/0/1214347940022826) |
| 197 | Budget | C |  |  | [Заголовки періодів зміщуються ліворуч і накладаються на «Description», «Location» та «Limit» у таблиці бюджетних ліній](https://app.asana.com/0/0/1213895067953518) |
| 198 | Budget | C |  |  | [Budget filters are disappearing](https://app.asana.com/0/0/1214730287872179) |
| 199 | Budget | C |  |  | [Падають консольні помилки при видаленні одного лайну в різних вкладках](https://app.asana.com/0/0/1212374830957816) |
| 200 | Budget | C | ? |  | [Баджет лайн створюється без саблайнів, якщо в момент створення бюджету переключитися на іншу вкладку (чи поставити курсор поза межами таблиці)](https://app.asana.com/0/0/1212532056179686) |
| 201 | Budget | C | ? |  | [Budget page unresponsive, no pagination on show budget page](https://app.asana.com/0/0/1214103611862236) |
| 202 | Budget | C |  |  | [Відображається пагінація при створенні Бюджета](https://app.asana.com/0/0/1214217504003179) |
| 203 | Budget | C |  |  | [Консольна помилка при додаванні нового кастомного періоду з порожніми датами](https://app.asana.com/0/0/1213735449946221) |
| 204 | Budget | C |  |  | [Таймзона девайсу впливає на відображення дат кастомного періоду бюджету на едіті](https://app.asana.com/0/0/1213609377930290) |
| 205 | Budget | D | ? |  | [[budget]Budget limit is exceeded, budget id: 1954831, used sum: 103328.310000, sum: 102991](https://app.asana.com/0/0/1219673749091738) |
| 206 | Budget | D |  | так | [Issues with Amazon Orders [US]](https://app.asana.com/0/0/1218389683913324) |
| 207 | Budget | D | ? |  | [[budget]Budget limit is exceeded, budget id: 2204308, used sum: 149368.740000, sum: 113840.16](https://app.asana.com/0/0/1219362851117567) |
| 208 | Budget | D | ? |  | [При створені акаунта з темплейту в бюджет проставився all_locations_access = 1, в all_location_ids частково записались локації](https://app.asana.com/0/0/1215962070258283) |
| 209 | Budget | D | ? |  | [Неправильно рахується сума бюджету після автотрансферу сум](https://app.asana.com/0/0/1212235616633030) |
| 210 | Budget | D | ? |  | [Не має приходити чекер на required budget, якщо документ створений з AI коли бюджети були увімкнені, а конфірмнутий коли бюджети вимкнені](https://app.asana.com/0/0/1213505346588325) |
| 211 | Budget | D |  |  | [Падає помилка $budgetSubLine->getItemCustomFieldOptions()->isEmpty() при імпорті бюджету, якщо в момент імпорту деактивувати ІКФ опшен](https://app.asana.com/0/0/1212479937471919) |
| 212 | Budget | D | ? |  | [логіка item budget part має працювати однаково](https://app.asana.com/0/0/1214381010269788) |
| 213 | Budget | D |  |  | [Не враховувати в чекері is_required_budget інвойси з порталу постачальника](https://app.asana.com/0/0/1213405138155556) |
| 214 | Budget | D | ? |  | [Неправильна сума переноситься в період бюджета при автотрансфері суми](https://app.asana.com/0/0/1213062105118308) |
| 215 | Budget | D |  |  | [[фікс чекера][HC][budget]Purchase Requisitions with Purchase Orders with bad budgeted_sum: Count 3, 795721, 795839, 827221](https://app.asana.com/0/0/1213753492683875) |
| 216 | Split Costs | A | ? |  | [Некріейтор не може редагувати поля на рівні документу і на рівні спліта, якщо не має доступу до одного зі сплітів](https://app.asana.com/0/0/1212295083668483) |
| 217 | Split Costs | A | ? |  | [[Не блокує реліз]Не можна включити баджет брейкдаун, якщо включити і виключити спліти](https://app.asana.com/0/0/1212149356323342) |
| 218 | Split Costs | A |  |  | [500 при додаванні айтема з каталогу в документ зі сплітами, якщо перший спліт реджектнутий](https://app.asana.com/0/0/1214765274549977) |
| 219 | Split Costs | A |  |  | [На парент інвойс-сервіс-айтемі з'являється бюджет після зменшення нет тоталу](https://app.asana.com/0/0/1213619902867444) |
| 220 | Split Costs | A |  |  | [Якщо в драфт ПО без сплітів is_all_items_received = 1, то після додавання сплітів в них is_all_items_received буде 0](https://app.asana.com/0/0/1214723525326874) |
| 221 | Split Costs | A | ? |  | [При ручному компліті сплітованого РО, спліти залишаються в статусі Approved, якщо Payments вимкнено для Invoices](https://app.asana.com/0/0/1213962044499234) |
| 222 | Split Costs | A | ? | так | [Парент сплітованого ПО не комплітиться після конфірму ревайзу](https://app.asana.com/0/0/1214892330703034) |
| 223 | Split Costs | A |  |  | [Виправити створення сплітів без запису айді ЛЕ в базі](https://app.asana.com/0/0/1214378175927437) |
| 224 | Split Costs | A | ? | так | [Budget error when confirming document with ICF splits](https://app.asana.com/0/0/1213745760781209) |
| 225 | Split Costs | A |  |  | [Неправильні відсотки в сплітах після репіту спліт-документу по ІКФ з реджектнутим сплітом](https://app.asana.com/0/0/1214790374063864) |
| 226 | Split Costs | A | ? |  | [Парент лишився на Pending, коли спліти перейшли в In revision](https://app.asana.com/0/0/1213300397649249) |
| 227 | Split Costs | A | ? |  | [У базового PO значення send_to_supplier = false, а у сплітів true: [HC][purchaseOrder]Critical Purchase Order Split send_to_supplier differs from parent value: Count 6, 2262080, 2262081, 2262090, 2262091, 2262102, 2262103](https://app.asana.com/0/0/1212319660440707) |
| 228 | Split Costs | A |  |  | [Документ зі сплітами можна Confirm / Approve без обов'язкових бюджетів](https://app.asana.com/0/0/1213115253462854) |
| 229 | Split Costs | A |  |  | [[16.04]Можна конфірмнути документ з одним сплітом](https://app.asana.com/0/0/1213742210550013) |
| 230 | Split Costs | A |  |  | [Не можна змінити Due date/Delivery date на спліт документі, якщо спочатку були бюджети, що тепер не підходять по даті](https://app.asana.com/0/0/1220245498601964) |
| 231 | Split Costs | A |  |  | [403 помилка при додаванні нового спліта в інвойсі на ревайзі](https://app.asana.com/0/0/1220196647247774) |
| 232 | Split Costs | A |  |  | [Send for approval на спліт PO падає з помилкою "Please, add items"](https://app.asana.com/0/0/1219924875179491) |
| 233 | Split Costs | A | ? | так | [Error while splitting cost by amount](https://app.asana.com/0/0/1218178658801216) |
| 234 | Split Costs | A | ? | так | [error while using Split Cost](https://app.asana.com/0/0/1217345434243472) |
| 235 | Split Costs | A | ? |  | [Split by item functionality issue](https://app.asana.com/0/0/1218235253965683) |
| 236 | Split Costs | A |  |  | [Не можна підтвердити документ зі сплітами по ICF бюджету та WHT айтемом](https://app.asana.com/0/0/1217946109080023) |
| 237 | Split Costs | A |  |  | [В спліта відрізняється status_sending від парента після додавання на ревайзі](https://app.asana.com/0/0/1217489084377968) |
| 238 | Split Costs | A | ? | так | [Required budget error after enabling Split Costs and changing the 1st split budget](https://app.asana.com/0/0/1217148693825574) |
| 239 | Split Costs | A |  |  | [Можу зробити сплітований інвойс рекарінгом](https://app.asana.com/0/0/1215827949499485) |
| 240 | Split Costs | A |  |  | [budget_id в спліт-парента лишається після увімкнення сплітів](https://app.asana.com/0/0/1215655654019954) |
| 241 | Split Costs | A | ? |  | [status_receiving в сплітах лишається 3 після кенселу](https://app.asana.com/0/0/1216450419536524) |
| 242 | Split Costs | A |  |  | [Неправильні нет суми сплітів з такс айтемом](https://app.asana.com/0/0/1216387648718462) |
| 243 | Split Costs | A | ? |  | [Спліт залишається в статусі Pending, якщо його кріейтор є апрувером на першому кроці і цей спліт не підходить під подальші кроки](https://app.asana.com/0/0/1216450199086290) |
| 244 | Split Costs | B | ? |  | [Error While Creating PO from PR](https://app.asana.com/0/0/1212555088589161) |
| 245 | Split Costs | B |  | так | [[CRITICAL] PO зі сплітами блочиться на статусі Pending після фінального апруву матчингу + падають 500 та ексепшени при апруві Overbudget Approval степів на одному зі сплітів](https://app.asana.com/0/0/1212070649757308) |
| 246 | Split Costs | B |  |  | [Cancel PO зі сплітами переводить пов'язаний PR в статус Rejected](https://app.asana.com/0/0/1212395161118058) |
| 247 | Split Costs | B |  |  | [На ПО-айтемі неправильний бюджет, якщо при створенні спліт ПО з ПР змінити бюджет](https://app.asana.com/0/0/1212671809312398) |
| 248 | Split Costs | B | ? |  | [[Після релізу 5.03] Спліти інвойса оновлюють is_required_budgets при переході з Pending Receipt на інший статус](https://app.asana.com/0/0/1213439690640622) |
| 249 | Split Costs | B |  |  | [Cпліти в ПО стають Completed після вимкнення пейментів, якщо ПО не ресівнуті, і є апрувнуті Інвойси](https://app.asana.com/0/0/1213802950518131) |
| 250 | Split Costs | B |  |  | [Інвойс прив'язується до другого ПО-спліта, якщо кріейтор не має доступу до першого спліта](https://app.asana.com/0/0/1213896593981646) |
| 251 | Split Costs | B |  |  | [Mass Payment Split Invoice не оновлює status_payment для Split PO та статус базового Invoice](https://app.asana.com/0/0/1212081403374533) |
| 252 | Split Costs | B |  |  | [В Інвойсі зі спліт ПО не можна редагувати ДКФи, які увімкнені для апрувал флоу](https://app.asana.com/0/0/1212294149492202) |
| 253 | Split Costs | B |  |  | [Бюджетна сума спліта обнуляється після зміни deducted суми бюджету](https://app.asana.com/0/0/1219372168169454) |
| 254 | Split Costs | B |  |  | [Не спрацьовує валідація на переліміт при конфірмі часткового спліт-Інвойса з ПО](https://app.asana.com/0/0/1217484668409081) |
| 255 | Split Costs | B |  |  | [Supplier Portal: обнуляються бюджетні суми сплітів, якщо Invoice from PO відправити з Matching на Revise і конфірмнути з такою сумою, як в РО](https://app.asana.com/0/0/1217402495112345) |
| 256 | Split Costs | B | ? |  | [При зміні DCF Option на сплітах в Invoice from PO, очищуються бюджети на сплітах](https://app.asana.com/0/0/1217453158805832) |
| 257 | Split Costs | B |  |  | [Спліти РО не змінили валюту на валюту інвойсу після матчингу](https://app.asana.com/0/0/1216503059180537) |
| 258 | Split Costs | B |  |  | [Після кенселу інвойса значення isNeedMatchWithPurchaseOrder в сплітах лишається 1](https://app.asana.com/0/0/1216673520696108) |
| 259 | Split Costs | C | ? |  | [На едіті айтема відсотки в сплітах завжди розподілені рівномірно](https://app.asana.com/0/0/1212007023030102) |
| 260 | Split Costs | C |  |  | [Відсотки відображаються на сплітах в модалках, якщо спліти по ІКФ бюджету](https://app.asana.com/0/0/1213719744878537) |
| 261 | Split Costs | C |  |  | [Відсотки відображаються на сплітах, якщо спліти по ІКФ бюджету](https://app.asana.com/0/0/1213688570961930) |
| 262 | Split Costs | C |  |  | [Split total displayed instead of PO total in the POs list when use 'Approve' infocard](https://app.asana.com/0/0/1213802915373073) |
| 263 | Split Costs | C | ? |  | [Department Discrepancy Display](https://app.asana.com/0/0/1219195376518958) |
| 264 | Split Costs | C | ? |  | [Глянути з точки зору FE - Помилка переліміту при реджекті сплітованого РО](https://app.asana.com/0/0/1218506910378197) |
| 265 | Split Costs | C |  |  | [Айтем, ІКФ-опшен якого не в обраному бюджеті, ніяк не підсвічується в спліт документах](https://app.asana.com/0/0/1217580901629830) |
| 266 | Split Costs | D |  |  | [пофіксити чекер - [HC][invoice]Invoices with status Matching and wrong PO status: Count 1, invoice id: 1952452, PO status: status.approved PO status payment: status.pending](https://app.asana.com/0/0/1212302519151731) |
| 267 | Split Costs | D | ? |  | [Дедлоки при реджекті кількох (але не всіх) сплітів за раз](https://app.asana.com/0/0/1220203813089000) |
| 268 | Invoice | A |  |  | [не видаляється такс з документу після видалення на айтемі](https://app.asana.com/0/0/1212548842932730) |
| 269 | Invoice | A | ? |  | [Some fields contain newline characters or has untrimmed whitespace. : Count 5, invoice.invoice_number: Count (5), ids: 2190457,2190666,2190678,2190783,2191189](https://app.asana.com/0/0/1214441410279702) |
| 270 | Invoice | A |  |  | [API: Валідувати тип Payment для Invoice [HC][invoice]Invoice Payments with wrong logic type : Count 1, 1401079](https://app.asana.com/0/0/1213985863160781) |
| 271 | Invoice | A |  |  | [При очищенні необов'язкового ДКФ під час репіту запис не видаляється з document_customfield__invoice](https://app.asana.com/0/0/1214505196341313) |
| 272 | Invoice | A |  |  | [403 при мас едіті Інвойс айтемів, коли Інвойс на Пендінгу](https://app.asana.com/0/0/1213812328678131) |
| 273 | Invoice | A | ? | так | [Service Invoice new line confirmation doesn't work](https://app.asana.com/0/0/1217145810749532) |
| 274 | Invoice | A | ? |  | [[не робили]В Paid Інвойса немає пейменту, якщо його сума to pay = 0 за рахунок wht таксу](https://app.asana.com/0/0/1215327161721136) |
| 275 | Invoice | A | ? |  | [В оплаченому інвойсі можна зменшити суму, якщо пейменти вимкнені](https://app.asana.com/0/0/1216655035656104) |
| 276 | Invoice | B |  |  | [[Зміна запиту HC] Prepayment перенісся в Invoice зі статусом Pending після апруву матчингу](https://app.asana.com/0/0/1212018905285159) |
| 277 | Invoice | B | ? |  | [Пофіксити HC Invoice attachment has type != po attachment](https://app.asana.com/0/0/1213734607577447) |
| 278 | Invoice | B |  |  | [Не проставляється айді ЛЕ в інвойсі створеному з декількох ПО](https://app.asana.com/0/0/1214482647348711) |
| 279 | Invoice | B |  |  | [Товар з інвойсу (на декілька РО) не додається в РО, якщо цей товар проходить по TL, але інший товар тригерить матчинг з іншим РО](https://app.asana.com/0/0/1214830195965765) |
| 280 | Invoice | B |  |  | [[16.04]Інвойс стає Аппрувд після ревайзу ПО, якщо вимкнені пейменти і Інвойс з ПО були Closed](https://app.asana.com/0/0/1213796743268679) |
| 281 | Invoice | B | ? |  | [Баг вже пофікшено - [HC][invoice]Invoice attachment has type != po attachment: Count 2, 4809375, 4809377](https://app.asana.com/0/0/1214076819469406) |
| 282 | Invoice | B |  |  | [Не дозволяти створювати другий інвойс на айтем в іншій валюті, відмінній від валюти першого інвойса на цей айтем](https://app.asana.com/0/0/1213840124764491) |
| 283 | Invoice | B | ? |  | [Invoice shows 0 value for both Received/ Waiting](https://app.asana.com/0/0/1213840187200892) |
| 284 | Invoice | B |  |  | [Якщо більше одного Invoice на матчингу з РО, то при вимкненні модулю Invoices, один інвойс не реджектиться, а залишається на матчингу](https://app.asana.com/0/0/1213880585079252) |
| 285 | Invoice | B |  |  | [Invoices created from PO incorrectly default the Location field instead of carrying it over from the PO](https://app.asana.com/0/0/1220108423519238) |
| 286 | Invoice | B |  |  | [Можна створити інвойс на по з іншим постачальником через API](https://app.asana.com/0/0/1219022217496224) |
| 287 | Invoice | B | ? |  | [Invoice-айтем при створенні з OCR отримує type каталожного айтему замість type PO-айтема, коли вони відрізняються](https://app.asana.com/0/0/1218200939021639) |
| 288 | Invoice | B |  |  | [type i logic_type ПО та Інвойс-айтемів мають синхронізовуватися після конфірму Інвойса](https://app.asana.com/0/0/1216674682155988) |
| 289 | Invoice | B |  |  | [При закритті Інвойса на метчингу реджектити Інвойс](https://app.asana.com/0/0/1215988463820087) |
| 290 | Invoice | B |  |  | [Можна вносити зміни в інвойс, в якому є CN](https://app.asana.com/0/0/1217447082159489) |
| 291 | Invoice | B |  | так | [DCF Option з інвойсу валідується до LE з PO (а не з інвойса)](https://app.asana.com/0/0/1215914102152302) |
| 292 | Invoice | B |  |  | [[Edge Case] Invoice for Multiple POs: інвойс матчиться тільки з одним з РО, коли додають нові товари, які проходять по TL (але вимкнена опція Add New Items Without Matching)](https://app.asana.com/0/0/1215000868631776) |
| 293 | Invoice | B |  |  | [Incorrect “To Pay” Amount After Applying Credit Note](https://app.asana.com/0/0/1215857344807457) |
| 294 | Invoice | B |  |  | [[не баг, чекає на мерж чекера][HC][invoice]Invoice item tax IDs where withholding flag differs from PO item tax: Count 1, 3168937](https://app.asana.com/0/0/1215469998891183) |
| 295 | Invoice | B |  |  | [500 при видаленні айтема з Інвойса, якщо є контракт, діскаунт і закенселений CN](https://app.asana.com/0/0/1216468619681531) |
| 296 | Invoice | C | ? |  | [Кнопки Revise та Cancel доступні Super User (з View Only ролями) на Invoice з кенсельнутим Payment](https://app.asana.com/0/0/1213338390344536) |
| 297 | Invoice | C |  |  | [Заборонити сортування по Gross Total на сторінці Add Invoice from PO](https://app.asana.com/0/0/1213719850265212) |
| 298 | Invoice | C |  |  | [Кнопка Mass Edit Items перекривається при відкритому Attachment Preview (Новий дизайн)](https://app.asana.com/0/0/1213743711044902) |
| 299 | Invoice | C | ? |  | [Для апрувера, який вже не підходить під апрувал флоу конкретного інвойсу, з'являється кнопка [Revise] після кенселу пейменту](https://app.asana.com/0/0/1213991491535657) |
| 300 | Invoice | C |  | так | ["Add Invoice from PO" page freezes](https://app.asana.com/0/0/1213609322437362) |
| 301 | Invoice | C |  |  | [[UI / minor] Після видалення Prepayment з Invoice на статусі Pending Receipt, плашка статусу міняється на Approved](https://app.asana.com/0/0/1212992541097731) |
| 302 | Invoice | C |  |  | [В загальному списку інвойсів при відкритті OCR аттачменту йде редірект на сторінку інвойсу](https://app.asana.com/0/0/1214396672521305) |
| 303 | Invoice | C | ? |  | [знову не обирається 1 єдиний айтем при створенні документу з документу](https://app.asana.com/0/0/1213619663669955) |
| 304 | Invoice | C |  |  | [Неправильне відображення кнопки Add в меню Invoices та PO, якщо увімкнена лише Custom Form](https://app.asana.com/0/0/1213731822260185) |
| 305 | Invoice | C |  |  | [не змінюється посилання в браузері при зміні пагінації  на сторінці Add Invoice from PO](https://app.asana.com/0/0/1213719850265230) |
| 306 | Invoice | C |  | так | [Падають консольні помилки при відкритті модалки едіту Інвойса, якщо контракт обов'язковий, але прихований за залежністю кастомної форми](https://app.asana.com/0/0/1213564833092857) |
| 307 | Invoice | C | ? |  | [Incorrect invoice payment date in PO Invoices and Credit Notes section](https://app.asana.com/0/0/1217531622695371) |
| 308 | Invoice | C |  |  | [Кнопка вимкненої кастомної форми Інвойсів відображається на сторінці списку Інвойсів](https://app.asana.com/0/0/1216777069977983) |
| 309 | Invoice | C |  |  | [Правильний статус інвойсу відображається лише після релоаду якщо скасувати CN пеймент](https://app.asana.com/0/0/1217184190223754) |
| 310 | Invoice | C | ? |  | [Поле Supplier не заблоковане на формі створення Invoice from BPO per Total](https://app.asana.com/0/0/1215001184996615) |
| 311 | Invoice | D |  |  | [Повністю оплачений Інвойс стає Partly Paid після імпорту пеймента з NetSuite](https://app.asana.com/0/0/1216821264546249) |
| 312 | Import/export | C |  |  | [revision history погано показує зміну валюти постачальника](https://app.asana.com/0/0/1220565208747685) |
| 313 | Import/export | C |  |  | [[Item Management/Import] ПО кліку на іконку ʼвидалитиʼ завжди видаляється останній айтем з списку на сторінці превʼю](https://app.asana.com/0/0/1217239124065631) |
| 314 | Import/export | D |  |  | [Заборонити редагування імпортом кількості, суми айтему в PR якщо PO approved](https://app.asana.com/0/0/1212562998550443) |
| 315 | Import/export | D | ? |  | [AssertionError](https://app.asana.com/0/0/1213965992142958) |
| 316 | Import/export | D |  |  | [При імпорті/апдейті постачальників Netsuite і Xero дозволяти мультивалютність](https://app.asana.com/0/0/1213898755464511) |
| 317 | Import/export | D |  |  | [Неправильне округлення budget_line.sum при імпорті бюджету (новий імпорт)](https://app.asana.com/0/0/1213796730051040) |
| 318 | Import/export | D |  |  | [Можна зробити невалідну дату періоду бюджету апдейтом](https://app.asana.com/0/0/1214755824971814) |
| 319 | Import/export | D |  |  | [Не працює новий імпорт бюджетів: Something went wrong](https://app.asana.com/0/0/1213798939949376) |
| 320 | Import/export | D |  |  | [Зменшується сума Parent Budget при апдейті бюджету з видаленням періодної колонки](https://app.asana.com/0/0/1213809527145145) |
| 321 | Import/export | D |  |  | [Додані імпортом періоди і баджет лайни завжди мають значення 100 в usedTaxPercentInBudget](https://app.asana.com/0/0/1213884375887543) |
| 322 | Import/export | D |  |  | [Створювати записи в таблицю user_license_info при імпорті юзера](https://app.asana.com/0/0/1213539053766390) |
| 323 | Import/export | D |  | так | [Price Column Error While Importing New Items](https://app.asana.com/0/0/1212001926906874) |
| 324 | Import/export | D |  |  | [Зламались валідації даних в файлі при імпорті інвойсів](https://app.asana.com/0/0/1212455730303370) |
| 325 | Import/export | D |  |  | [Довгий запит на завантаження темплейту Update Items (40с+)](https://app.asana.com/0/0/1213487446409386) |
| 326 | Import/export | D |  |  | [Можу вимкнути локацію через апдейт файлом, якщо вона використана в користувача як Main](https://app.asana.com/0/0/1211994850814384) |
| 327 | Import/export | D |  |  | [Не дозволяє Import / Update товарів з мінусовою ціною в PO / SPO](https://app.asana.com/0/0/1212374815601594) |
| 328 | Import/export | D |  |  | [Старий імпорт РО: Падає помилка при імпорті 2+ РО з Taxes](https://app.asana.com/0/0/1214597312096098) |
| 329 | Import/export | D |  |  | [Не видаляється депенд на локацію в кастомних формах, після вимкнення локації через імпорт](https://app.asana.com/0/0/1220565169113607) |
| 330 | Import/export | D |  |  | [Не парситься ціна при оновленні айтемів у каталозі якщо значення у форматі тексту](https://app.asana.com/0/0/1220289565305196) |
| 331 | Import/export | D | ? |  | [Minimum Stock Level and Reorder To Not Updating for Items with Zero Stock](https://app.asana.com/0/0/1220364834447165) |
| 332 | Import/export | D |  |  | [Не проставляється Approval date після імпорту файлу з вказанням статусу Pending](https://app.asana.com/0/0/1219214419338708) |
| 333 | Import/export | D |  |  | [Шаблон імпорту айтемів у PR містить колонку SKU, коли в Basic Settings вимкнено PR → SKUs](https://app.asana.com/0/0/1220102753810067) |
| 334 | Import/export | D |  |  | [PO не створюється через імпорт на US](https://app.asana.com/0/0/1219023260483135) |
| 335 | Import/export | D |  |  | [Імпорт нових товарів затирає budget_sub_line на існуючих товарах і підсвічує валідні ICF Options як невалідні](https://app.asana.com/0/0/1216263638517970) |
| 336 | Import/export | D |  |  | [Статус Approved після імпорту PO item з 0 ціною](https://app.asana.com/0/0/1219257249960286) |
| 337 | Import/export | D |  |  | [імпорт і апдейт бюджетів пропускає файл і завантажує бюджет який потім не можна використати в документах](https://app.asana.com/0/0/1218441493500889) |
| 338 | Import/export | D |  |  | [Failed to export metrics batch code: None, reason: HTTPConnectionPool(host='alloy-logs.monitoring.svc.cluster.local', port=4318): Read timed out. (read timeout=9.999213695526123)](https://app.asana.com/0/0/1219372169424311) |
| 339 | Import/export | D |  |  | [503 python_repo rt (17 шт, COM)](https://app.asana.com/0/0/1217539947937903) |
| 340 | Import/export | D |  |  | [[Import] Виправити текст валідаційних помилок](https://app.asana.com/0/0/1217767012859706) |
| 341 | Import/export | D |  |  | [[Import] Відсутня валідація на присутні рядки підказок](https://app.asana.com/0/0/1217239124065614) |
| 342 | Import/export | D |  |  | [[Tax/WHT/Shipping] Сan be received = true, logic_type=0 якщо доданий через імпорт і змаплений з каталожним айтемом](https://app.asana.com/0/0/1216656483440077) |
| 343 | Import/export | D |  | так | [Bulk PR import error, якщо в колонці Ціна значення з комою](https://app.asana.com/0/0/1217531622695357) |
| 344 | Import/export | D |  |  | [еджкейс "Something went wrong" через " лапки в назві постачальника](https://app.asana.com/0/0/1216390043506910) |
| 345 | Import/export | D |  |  | [MS Import PR: значення Creation Date та Delivery Date ігноруються (проставляється поточна дата)](https://app.asana.com/0/0/1215092516443546) |
| 346 | Import/export | D |  |  | [MS Budget Import: бюджети імпортуються по дефолту з Deducted Sum = Gross, ігноруючи налаштування Total Shown in Document Lists](https://app.asana.com/0/0/1216202132956962) |
| 347 | Import/export | D | ? |  | [Не можу апдейтнути доступну Legal Entity для бюджету](https://app.asana.com/0/0/1216347999154478) |
| 348 | Import/export | D |  |  | [Invoice import not working](https://app.asana.com/0/0/1216032375651406) |
| 349 | Import/export | D |  |  | [UnsupportedMediaType: 415 Unsupported Media Type: Did not attempt to load JSON data because the request Content-Type was not 'application/json'.](https://app.asana.com/0/0/1216159074954199) |
| 350 | Import/export | D |  |  | [RequestEntityTooLarge: 413 Request Entity Too Large: The data value transmitted exceeds the capacity limit.](https://app.asana.com/0/0/1215613245302362) |
| 351 | Import/export | D |  |  | [Імпортований айтем в РО на іншого постачальника мапиться з rejected айтемом у PR](https://app.asana.com/0/0/1216072396209259) |
| 352 | Import/export | D |  |  | [MS Invoice Import: Internal Server Error when trying to import historical invoices with fixed Exchange Rate Type](https://app.asana.com/0/0/1215355962655110) |
| 353 | Import/export | D |  |  | [Замість юзера з темплейту імпортувався сетап юзер як інвойс ішшюер](https://app.asana.com/0/0/1215420259783004) |
| 354 | Import/export | D |  | так | [PO PHP Import: POs with ICF Budgets Fail to Import When Containing ICFs Not Included in the Budget - Historical PO Import fails with false budget validation errors](https://app.asana.com/0/0/1215189582513620) |
| 355 | Import/export | D |  |  | [Помилка Internal Server Error в статусі 400 при імпорті великої кількості айтемів на склад через Add stock balance](https://app.asana.com/0/0/1216348977318029) |
| 356 | Approval | A | ? |  | [Апруверу записуються доступи до ДКФ опшенів, коли в апрувера access to all і немає кастомного трешхолда](https://app.asana.com/0/0/1220161565421030) |
| 357 | Approval | A |  |  | [Падає 403 при запиті на отримання логів по спліту до якого юзер немає доступу](https://app.asana.com/0/0/1217524464963755) |
| 358 | Approval | A | ? | так | [PO approval is skipped](https://app.asana.com/0/0/1216363548656426) |
| 359 | Approval | A | ? |  | [Не видаляється запис з eligible_approvers__ після делегації документа іншому юзеру](https://app.asana.com/0/0/1215859601470370) |
| 360 | Approval | A | ? | так | [Overbudget approval being triggered for not overbudget POs](https://app.asana.com/0/0/1212622176124953) |
| 361 | Approval | A |  |  | [Відображається something went wrong при спробі апрувнути PO з бюджетом та не заповненими ICF](https://app.asana.com/0/0/1212508738337644) |
| 362 | Approval | A | ? |  | [Invoice was sent to wrong approval step](https://app.asana.com/0/0/1212565719582920) |
| 363 | Approval | A | ? |  | [Апруверу записується в таблицю доступ до опшенів, коли в нього аксес ту ол](https://app.asana.com/0/0/1213688424388308) |
| 364 | Approval | A |  |  | [не можу апрувнути документ, якщо не маю доступа до одного з обраних опшенів](https://app.asana.com/0/0/1212305326685823) |
| 365 | Approval | A |  |  | [Не можна створити апрувал крок перед паралельними кроками, якщо між цими паралельними кроками є видалені кроки](https://app.asana.com/0/0/1212490240811363) |
| 366 | Approval | A |  |  | [трігернувся ре-апрувал після ревайзу ПО без змін](https://app.asana.com/0/0/1214899509088718) |
| 367 | Approval | A | ? | так | [Кастомний трешхолд any не аплаїться на апруверів, в яких access to all](https://app.asana.com/0/0/1214530544221109) |
| 368 | Approval | A | ? |  | [Забирати доступ в апрувера до вимкнених сабопшенів, коли забирають доступ до перента](https://app.asana.com/0/0/1214293845939967) |
| 369 | Approval | A | ? |  | [OutOfMemory Error /api/approvalsteps/2?location[]=114397&per_page=10&includeEmptySteps=1](https://app.asana.com/0/0/1213892918571436) |
| 370 | Approval | A | ? |  | [Можу апрувнути документ без бюджету при рекваред баджет з списку документів](https://app.asana.com/0/0/1213883243472061) |
| 371 | Approval | B | ? |  | [В апрувера залишається доступ до документ реквесторів, після апдейту на access to all меседжом](https://app.asana.com/0/0/1220232576327402) |
| 372 | Approval | B |  |  | [Не перераховуються апрувери на ресітах після зміни ДКФ опшена на ревайзі](https://app.asana.com/0/0/1218915373753298) |
| 373 | Approval | B | ? |  | [Backup Approver (Vacation Mode) cannot approve pending Supplier - approval action not available](https://app.asana.com/0/0/1219646230706148) |
| 374 | Approval | B |  |  | [Запис в eligible_approvers створюється з ід вимкненого юзера при делегації апруверів на вимкненні юзера](https://app.asana.com/0/0/1219088647515677) |
| 375 | Approval | B |  | так | [Інвойс пішов на Approval Review при включені функції Auto-Approve Invoices from Orders](https://app.asana.com/0/0/1216629082679386) |
| 376 | Approval | B |  |  | [Не трігериться рестар апруву, коли на кроці не залишилося підходящих апруверів і вимкнули ДКФ, не заповнений в документі](https://app.asana.com/0/0/1216086632692535) |
| 377 | Approval | B |  |  | [Не змінюється апрувер на спліті після ревайзу](https://app.asana.com/0/0/1217353476226952) |
| 378 | Approval | B |  |  | [В сплітах інвойса автоапрувиться перший крок, коли кріейтор є апрувером першого кроку, але інвйос на статусі Pending Receipt](https://app.asana.com/0/0/1214962187056011) |
| 379 | Approval | B |  |  | [Не видаляється апрувер з eligible_approvers__ після того як в нього забрали доступ до кріейтора документа](https://app.asana.com/0/0/1217232377142260) |
| 380 | Approval | B |  |  | [Wrong approval flow after matching](https://app.asana.com/0/0/1212006870225644) |
| 381 | Approval | B |  |  | [Після того як в юзера забрати доступ до ЛЕ, документ з таким ЛЕ все ще залишається на апруві в цього юзера](https://app.asana.com/0/0/1213203841563983) |
| 382 | Approval | B | ? | так | [Бекап апрувер не може апрувити PO, коли в нього  access to all DCF, але в його юзера немає записів в таблиці з доступами](https://app.asana.com/0/0/1212856985132569) |
| 383 | Approval | B |  |  | [падають 500 та ексепшени при апруві Overbudget Approval степів на одному зі сплітів](https://app.asana.com/0/0/1212148592177400) |
| 384 | Approval | B |  |  | [Апрувал крок залишається в таблиці кроків документа після того як єдиного апрувера цього кроку вимкнули](https://app.asana.com/0/0/1214145131352999) |
| 385 | Approval | B |  |  | [Не апрувиться Credit Note from Invoice from SPO](https://app.asana.com/0/0/1213797886212350) |
| 386 | Approval | B |  |  | [Документ не переходить на степ, який зробили паралельним і після цього дали необхідні доступи апруверу з цього степа](https://app.asana.com/0/0/1213555060964337) |
| 387 | Approval | B | ? |  | [Після вимкнення і активації СКФ/ДКФ, який єдиний доступний в апрувалі, апрувер залишається без доступу до СКФ/ДКФ опшенів](https://app.asana.com/0/0/1213892694910972) |
| 388 | Approval | B |  |  | [ПО з ПР зі сплітами переходить на пендінг, коли на ПО не налаштований апрувал](https://app.asana.com/0/0/1212470249084561) |
| 389 | Approval | C | ? |  | [Апруверу записується доступ до ДКФ опшена, до якого його юзер не має доступу (кейс з двома вкладками)](https://app.asana.com/0/0/1212687348566493) |
| 390 | Approval | C | ? |  | [Approval Workflow - фільтр для локацій відображає тільки перші 100 локацій](https://app.asana.com/0/0/1214411878573073) |
| 391 | Approval | C | ? | так | [Не можливо зберегти зміни в апрувера, в якого в доступах локація з другої сотні](https://app.asana.com/0/0/1214378082504454) |
| 392 | Approval | D |  |  | [Відправляється лист апруверу на спліті, на якому не змінився апрувал крок](https://app.asana.com/0/0/1220378823054843) |
| 393 | Approval | D |  |  | [Не створюються записи в eligible_approvers__ після імпорту апрувера на крок, на якому зараз знаходиться документ](https://app.asana.com/0/0/1215717858436594) |
| 394 | Approval | D |  |  | [При копіюванні компанії копіюється апрувер з кастомним трешхолдом з ід з попередньої компанії](https://app.asana.com/0/0/1215624069564336) |
| 395 | Approval | D |  |  | [При створенні акаунта з темплейта Tech & SaaS Ltd. в ПР записаний апрувал крок без апрувера](https://app.asana.com/0/0/1216023071792693) |
| 396 | Approval | D |  |  | [При створенні акаунта з шаблона не створюються записи в таблицях eligible_approvers__ для пендінг документів](https://app.asana.com/0/0/1215593965612698) |
| 397 | Approval | D |  |  | [Додати розсилку сповіщень по апрувал SLA для лєгасі акаунтів](https://app.asana.com/0/0/1214055434471092) |
| 398 | PR | A | ? |  | [[PR]Не оновлюються поля для каталожних айтемів при mass edit](https://app.asana.com/0/0/1212455793336152) |
| 399 | PR | A |  |  | [Атачмент додається без прив'язки до документа при створенні ПР](https://app.asana.com/0/0/1219143203710532) |
| 400 | PR | A |  |  | [Catalog item price resets to default (Free of Charge) after initial PR confirmation](https://app.asana.com/0/0/1219247879747062) |
| 401 | PR | A | ? |  | [[Custom form - PR] Помилка при додаванні  айтему іншої валюти з призначеним постачальником на рівні документу](https://app.asana.com/0/0/1217187439252109) |
| 402 | PR | B |  |  | [Text / Date DCF value is not transferred from PR to PO (auto-create) if user has no Access to All DCFs](https://app.asana.com/0/0/1213239274396387) |
| 403 | PR | B | ? |  | ['Not set' Available in Budget на ПР айтемі, якщо спочатку айтем був доданий з ІКФ-опшеном поза межами бюджету](https://app.asana.com/0/0/1213732744981359) |
| 404 | PR | B |  |  | [ПР комплітиться, коли ПО оплачений, але не отриманий](https://app.asana.com/0/0/1213309735156110) |
| 405 | PR | B |  |  | [FOC айтем з logic_type = 1 дублюється в окремому РО при подвійному створенні](https://app.asana.com/0/0/1219428446546647) |
| 406 | PR | B | ? |  | [Реквестор, який не бачить ціни в PR, бачить ціни в PO через preview](https://app.asana.com/0/0/1217306789382577) |
| 407 | PR | B |  |  | [[PR status Rejected] RFP-> Mark as Completed «повертає» позиції PR status 0 і знімає лінк на request_for_proposal_item_id](https://app.asana.com/0/0/1216972699280885) |
| 408 | PR | B |  |  | [is_all_items_ordered лишається 1 в ПР після видалення free of charge такс айтему з ПО](https://app.asana.com/0/0/1216116285720047) |
| 409 | PR | B |  |  | [Після деактивації модулю Ресіпт PR не комплітиться](https://app.asana.com/0/0/1215419373785685) |
| 410 | PR | B | ? |  | [Incorrect 'Waiting' amount](https://app.asana.com/0/0/1215116388144401) |
| 411 | PR | B |  |  | [[PO з PR ]Після збільшення ціни tax itemа і реджекту в PO, значення waiting в PR йде в мінусове значення](https://app.asana.com/0/0/1216069810299495) |
| 412 | PR | B |  |  | [ПР не комплітиться, якщо ціна айтем таксу менше 1](https://app.asana.com/0/0/1216224769629431) |
| 413 | PR | B |  |  | [[нічого не робили]403 на receive all з PR](https://app.asana.com/0/0/1216213025998767) |
| 414 | PR | C | ? | так | [(старий дизайн) Неможливо виконати заміну айтема в  PR](https://app.asana.com/0/0/1212602694426010) |
| 415 | PR | C |  |  | [wrong text on the PR page](https://app.asana.com/0/0/1213730888219713) |
| 416 | PR | C |  |  | [пропав стовпчик з саплаєром в таблиці вибору айтемів на сторінці створення PR з WR](https://app.asana.com/0/0/1212263159425580) |
| 417 | PR | C | ? |  | [Не можна створити PO зі сторінки PR, якщо PR містить товари без постачальника (новий дизайн)](https://app.asana.com/0/0/1212375856433534) |
| 418 | PR | C |  |  | [Не відображати кнопку Replace якщо у користувача немає доступу до каталогу](https://app.asana.com/0/0/1212516088734153) |
| 419 | PR | C |  |  | [На формі створення PR не фільтруються Taxes по LE](https://app.asana.com/0/0/1220651015825001) |
| 420 | PR | C |  |  | [Не відображається назва бюджету на формі створення PR, якщо бюджет з другої сотні знайдений через пошук](https://app.asana.com/0/0/1220650311846687) |
| 421 | PR | C |  |  | [На формі PR відсутні поля Taxes та Discounts, коли вимкнена функція Display Prices](https://app.asana.com/0/0/1220513205467410) |
| 422 | PR | C |  |  | [Unable to type a supplier name while converting PO from PR](https://app.asana.com/0/0/1218861391663225) |
| 423 | PR | C |  | так | [The FOC toggle is available for FOC items when PR - Restrict Catalog Items Editing (price) is ON](https://app.asana.com/0/0/1218358096871062) |
| 424 | PR | C |  |  | [Confusing UI in closed PR](https://app.asana.com/0/0/1215479551245783) |
| 425 | PR | C |  |  | [Не натискається повторно кнопка Create PO from PR після скасування](https://app.asana.com/0/0/1215417682737885) |
| 426 | PR | C | ? |  | [[PR] Редагування колонки Supplier дублює поведінку для рядків з однаковим значення](https://app.asana.com/0/0/1217106742413580) |
| 427 | PR | D |  |  | [довго відпрацьовує запит purchaseorder/choose_data](https://app.asana.com/0/0/1213014498010692) |
| 428 | PR | D |  |  | [Вимкнули всіх користувачів через акару - [HC][purchaseRequisition]PR items errors rejected in PR and has not rejected count in PO: Count 16, 1580204, 1785036, 1812829, 1812832, 1812835, 1812837, 2126914, 2126915, 2126916, 2126917, 2126936, 2503975, 3029843, 3029853, 3029867, 3029868](https://app.asana.com/0/0/1212151316344743) |
| 429 | PR | D | ? | так | [Unable to confirm PunchOut PR for a specific LE](https://app.asana.com/0/0/1217466997785502) |
| 430 | PR | D | ? |  | [Некоректне значення addedToPurchaseOrder у PR айтемах під час копіювання компанії](https://app.asana.com/0/0/1216558205329255) |
| 431 | Budget Parts | A | ? |  | [[19.03]Каталожний айтем з баджет партами додається без budget_sub_line, якщо він перевищує ліміт бюджета (документ на драфті)](https://app.asana.com/0/0/1213505996072273) |
| 432 | Budget Parts | A |  |  | [Неправильна сума вираховується з бюджету при зміні ІКФ опшену в документі з баджет партами](https://app.asana.com/0/0/1214527340463063) |
| 433 | Budget Parts | A |  |  | [Бюждетна сума не записується на рівні документу при додаванні айтема з каталогу, якщо є баджет парти](https://app.asana.com/0/0/1213100866683169) |
| 434 | Budget Parts | A | ? | так | [Multi-year SO 1622 сannot be confirmed because "total exceeds the amount available in the budget"](https://app.asana.com/0/0/1220381275825901) |
| 435 | Budget Parts | A |  |  | [Суми баджет партів != бюджетній сумі айтемів, якщо документ має нульову суму за рахунок мінусового айтема](https://app.asana.com/0/0/1219450497497585) |
| 436 | Budget Parts | A |  |  | [item_budget_part не видаляються, якщо айтем реджектиться після ручного компліту ПО](https://app.asana.com/0/0/1219287822141472) |
| 437 | Budget Parts | A | ? |  | [Розподіл округлення по партам може перелімітити бюджет - [budget]Budget limit is exceeded, budget id: 2140026, used sum: 137841.040000, sum: 137841](https://app.asana.com/0/0/1218813204230807) |
| 438 | Budget Parts | A | ? | так | [budget error while PO total reduction](https://app.asana.com/0/0/1216383062089187) |
| 439 | Budget Parts | A |  |  | [В SPO з Budget Breakdown на 1 період проставляється 2 парти](https://app.asana.com/0/0/1216423887658544) |
| 440 | Budget Parts | A | ? |  | [Від'ємний баджет парт: залишок округлення пишеться в останній період без перевірки available](https://app.asana.com/0/0/1217353479209696) |
| 441 | Budget Parts | A |  |  | [500 при репіті СПО з баджет брейкдауном](https://app.asana.com/0/0/1215277418276883) |
| 442 | Budget Parts | A | ? |  | [Помилка переліміту при зменшенні ціни в репітнутому SPO з Budget Breakdown, якщо включено нульовий парт](https://app.asana.com/0/0/1216812535696150) |
| 443 | Budget Parts | B |  | так | [Unable to Add Invoice to PO, if PO is created from PR and has Budget Breakdown](https://app.asana.com/0/0/1213097351306775) |
| 444 | Budget Parts | B |  |  | [Айтем-парти в Інвойсі видаляються після додавання нового баджет парту в СПО з ПРу](https://app.asana.com/0/0/1214080598467091) |
| 445 | Budget Parts | B |  |  | [Суми баджет партів не перераховуються, якщо при створенні Інвойса з СПО був змінений курс валюти](https://app.asana.com/0/0/1213611480434476) |
| 446 | Budget Parts | B |  |  | [Після деактивації користувача, ресіпт залишився в статусі PENDING](https://app.asana.com/0/0/1212704605364029) |
| 447 | Budget Parts | B | ? |  | [Дивне розподілення баджет партів при створенні Інвойса з ПО з AP inbox](https://app.asana.com/0/0/1217665150056242) |
| 448 | Budget Parts | B |  |  | [Неправильний розрахунок бюджету при створенні Credit Note from Invoice з Budget Breakdown та Discount Item / Negative Item](https://app.asana.com/0/0/1218225918522172) |
| 449 | Budget Parts | B |  |  | [Budget Breakdown: Після кенселу Invoice from PO на один з періодів, сума заінвойшеного періоду повертається саме в нього без перерахунку партів РО](https://app.asana.com/0/0/1217409158055265) |
| 450 | Budget Parts | B | ? |  | [Айтем баджет парти не створюються при створенні Інвойса з СПО через OCR](https://app.asana.com/0/0/1215235471732068) |
| 451 | Budget Parts | B |  |  | [Суми Інвойс баджет партів не обнуляються, якщо реджектиться метчинг після вимкнення модулю Інвойсів](https://app.asana.com/0/0/1216840226055810) |
| 452 | Budget Parts | B | ? |  | [Баджет парти не видаляються з документа і його товарів після вимкнення Budget Breakdown](https://app.asana.com/0/0/1216752566299335) |
| 453 | Budget Parts | C | ? |  | [Budget Breakdown: пошук бюджетів обрізаний до 100 перших баджет лайнів, які приходять по дефолту](https://app.asana.com/0/0/1217450649455495) |
| 454 | Credit Note | A | ? |  | [Нульовий Exchange Rate при створенні Credit Note на Invoice з товаром у неосновній валюті](https://app.asana.com/0/0/1212515904333687) |
| 455 | Credit Note | A |  |  | [При репіті Credit Note створюється Invoice](https://app.asana.com/0/0/1214570460500527) |
| 456 | Credit Note | A |  |  | [Помилка при редагуванні айтема в кредіт ноуті](https://app.asana.com/0/0/1214069476705471) |
| 457 | Credit Note | A | ? | так | [Issue Creating the Credit Note](https://app.asana.com/0/0/1218691864855115) |
| 458 | Credit Note | A | ? |  | [Неможливо додати залишок Tax line в CN](https://app.asana.com/0/0/1216814857194570) |
| 459 | Credit Note | A |  | так | [Не можна відредагувати Supplier credit note # на статусі Paid](https://app.asana.com/0/0/1215557791072730) |
| 460 | Credit Note | B |  |  | [Чартова сума інвойс айтемів не обнуляється якщо на Інвойс є CN на пендінгу](https://app.asana.com/0/0/1213682920208559) |
| 461 | Credit Note | B |  | так | [500 при конфірмі КН, якщо в Інвойс з ПО додати айтем типу 'Tax'](https://app.asana.com/0/0/1213204983926892) |
| 462 | Credit Note | B |  |  | [Округлення в Credit Note робить chart_sum товару в Invoice від'ємним](https://app.asana.com/0/0/1213022688619126) |
| 463 | Credit Note | B |  |  | [Не можна approve / reject Credit Note from Invoice зі сплітами](https://app.asana.com/0/0/1213374842033117) |
| 464 | Credit Note | B |  | так | ["This entity is currently locked" error when confirming Credit Note for received items that were posted to warehouse](https://app.asana.com/0/0/1214932095229526) |
| 465 | Credit Note | B |  |  | [WHT item враховується в CN, тому paid Invoice стає Partly Paid при кенселі СN](https://app.asana.com/0/0/1219448532220587) |
| 466 | Credit Note | B | ? |  | [Не можна створити CN якщо DCF з інвойсу вимкнули](https://app.asana.com/0/0/1216226881619966) |
| 467 | Credit Note | B |  |  | [В Invoice можна зменшувати ціну / кіл-сть товару, якщо Credit Note на статусі Pending](https://app.asana.com/0/0/1216387167160793) |
| 468 | Credit Note | C | ? |  | [quantity column showing 1, but no credit note is registered](https://app.asana.com/0/0/1220671976448875) |
| 469 | Credit Note | C | ? |  | [Відображається ключ помилки при додаванні мінусового айтема з каталогу в Standalone CN](https://app.asana.com/0/0/1216815974354013) |
| 470 | RFP | A |  |  | [500 на створенні пропозішен-айтема, якщо одночасно редагувати та створювати айтеми](https://app.asana.com/0/0/1219107451088056) |
| 471 | RFP | A |  |  | [Після ревізії rfp_proposition.status confirmed замість sent](https://app.asana.com/0/0/1219673364857865) |
| 472 | RFP | A |  |  | [[RFP] Статус Need to create a supplier не проставляється після  In Revision](https://app.asana.com/0/0/1217817034445242) |
| 473 | RFP | A | ? |  | [Коли FoC Discount отримує ціну через PRF Proposal, значення free_of_charge не змінюється](https://app.asana.com/0/0/1217444994354073) |
| 474 | RFP | A |  |  | [При додаванні Tax з каталогу в RFP можливо встановити кількість > 1](https://app.asana.com/0/0/1217184724432686) |
| 475 | RFP | A | ? |  | [не можливо змінити поля в RFP на in Revise - якщо документ створений не сьогодні (дати в минулому)](https://app.asana.com/0/0/1215923077850437) |
| 476 | RFP | A |  | так | [Заборонити зміну rfp_proposition.status з 2 на 1](https://app.asana.com/0/0/1212582448752880) |
| 477 | RFP | A |  |  | [Постачальник відправив Proposal з нульовою сумою товару: [HC][requestForProposal] RFP Proposition Item errors. Problem proposition items ids: Count 1, 394364](https://app.asana.com/0/0/1212368954904798) |
| 478 | RFP | B |  | так | [RFP з PR недоступний для створення після реджекту айтема з постачальником в PR](https://app.asana.com/0/0/1216986283211134) |
| 479 | RFP | B |  |  | [Unable to create RFP from PR](https://app.asana.com/0/0/1217369509135146) |
| 480 | RFP | C |  |  | [На сторінці RFP зі сторони постачальника не відображається лого Precoro](https://app.asana.com/0/0/1219777941455928) |
| 481 | RFP | C |  |  | [Two arrow icons are overlapping each other on the expand/collapse action on the RFP page](https://app.asana.com/0/0/1215994927375831) |
| 482 | RFP | C | ? |  | [Додати попап якщо постачальник вже видалений, прибрати помилку- RFP документ](https://app.asana.com/0/0/1212739104219937) |
| 483 | RFP | D | ? | так | [An error when working with RFP](https://app.asana.com/0/0/1220667276986133) |
| 484 | RFP | D | ? | так | [Email Error while Adding a Supplier to RFP](https://app.asana.com/0/0/1216901205804646) |
| 485 | RFP | D | ? |  | [403 помилки посипались, бо під час заповнення RFP Proposition, Company User був залогіненим](https://app.asana.com/0/0/1212213020666285) |
| 486 | Budget Limit | A |  |  | [Mass Edit товарів не валідується на переліміт при зміні ICF Option для саблайну, в якому недостатньо суми](https://app.asana.com/0/0/1220156977679123) |
| 487 | Budget Limit | A |  |  | [Відсутня помилка про перевищення ліміту бюджету по кліку на Update price by catalog](https://app.asana.com/0/0/1217246210346986) |
| 488 | Budget Limit | A | ? | так | [Budget overlimit error appears when there are enough funds in a budget](https://app.asana.com/0/0/1217314587718493) |
| 489 | Budget Limit | B |  |  | [Budget overlimit false positive при зміні бюджету на РО, який має пов'язаний Draft Invoice (який не влазить в новий бюджет)](https://app.asana.com/0/0/1220511784813925) |
| 490 | Budget Limit | B |  |  | [Бюджетна сума Invoice from BPO per Items ніде не резервується коли той в статусі Matching / взятий на Revise з Matching і не тригерить валідацію на переліміт при Confirm Revise](https://app.asana.com/0/0/1219206136454866) |
| 491 | Budget Limit | B |  |  | [Немає валідації на переліміт при апруві метчингу в ПО з баджет партами, якщо сума бюджету була зменшена](https://app.asana.com/0/0/1219088706582185) |
| 492 | Budget Limit | B | ? | так | [budget error while creating an Invoice](https://app.asana.com/0/0/1217141165989805) |
| 493 | Budget Limit | B |  |  | [[не фіксили] Supplier Portal: переліміт бюджету, якщо взяти Invoice from PO на Revise і збільшити ціну товару після того, як матчинг був апрувнутий](https://app.asana.com/0/0/1217398035848198) |
| 494 | Budget Limit | B |  | так | [Budget Error While Adding an Invoice from a Split PO](https://app.asana.com/0/0/1216189530036967) |
| 495 | Budget Limit | B |  |  | [Переліміт при апруві метчингу в ПО, якщо два Інвойси на метчингу](https://app.asana.com/0/0/1215652897216168) |
| 496 | Budget Limit | B |  |  | [Немає валідації на переліміт при кенселі ПО з ПР, якщо в ПО інший бюджет чи інший саблайн](https://app.asana.com/0/0/1212212546453444) |
| 497 | Budget Limit | B |  |  | [[Плановий дозапуск]Не спрацьовує валідація на переліміт при кенселі ПО з ПР, якщо ціни в ПР більші за ціни в ПО](https://app.asana.com/0/0/1212150328892883) |
