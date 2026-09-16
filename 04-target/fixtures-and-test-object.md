# Фікстури і один `test`

Статус: draft. Рішення ще не оформлене в ADR; цей файл є основою для нього.

## Проблема
22 окремі `test`-об'єкти; 37 спеків збирають `mergeTests` самі; `apiClient` test-scoped і читає токен з БД щотесту; 498 UI-логінів у спеках попри storageState; document-фікстури без teardown.

## Ціль
- `fixtures/index.ts` експортує один `test` і `expect`. Спеки імпортують лише звідти.
- Worker-scoped: `config`, `company` (об'єкт із реєстру, з юзерами і токенами), `api` (клієнт головного юзера з кешем токенів).
- Test-scoped: `asUser(email)` повертає `Page` у новому контексті з кешованим storageState для цього юзера; `page` за замовчуванням це головний юзер компанії.
- Фікстури стану іменуються за результатом, не за процесом: `draftPo`, `confirmedPo`, `approvedInvoice`, `receivedReceipt`. Кожна після `use()` видаляє, що створила, через `DELETE /{doc}/{idn}/delete`.
- Фікстури налаштувань: `withSetting({ key: value })` застосовує і повертає назад у teardown.

## Логін
- storageState per user, не per project. Кеш у `.auth/<env>/<email>.json`, генерується лениво при першому запиті.
- `logout_url` у тестах заборонено, бо PHPSESSID серверний і logout вбиває сесію всього проекту. Тести на logout ізолюються в окремий контекст.

## Міграція
1. `asUser` і кеш storageState per user. Codemod `new LoginPage(page).doLogin(email, pw)` → `const page = await asUser(email)`. Контрольний лічильник: `doLogin(` у спеках, зараз 301.
2. Один merged `test`, codemod імпортів. Контрольний лічильник: локальні `mergeTests(` у спеках, зараз 37.
3. Worker-scoped `api` з кешем токенів; `getUserApiTokenByEmail` у фікстурах зникає (35 місць).
4. Teardown у document-фікстурах.
