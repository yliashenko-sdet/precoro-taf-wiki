# Фікстури і один `test`

ADR ще нема; цей файл є його основою. Задачі T1-03, T1-04, T1-05, T1-06, T1-08.

## Форма
- `fixtures/index.ts` експортує один `test` і `expect`. Спеки імпортують лише звідти.
- Worker-scoped: `config`, `company` (об'єкт із реєстру з юзерами і токенами), `api` (клієнт головного юзера з кешем токенів).
- Test-scoped: `page` головного юзера компанії; `asUser(email)` повертає `Page` у новому контексті з кешованим storageState цього юзера.
- Фікстури стану іменуються за результатом: `draftPo`, `confirmedPo`, `approvedInvoice`, `receivedReceipt`. Після `use()` видаляють створене через `DELETE /{doc}/{idn}/delete`.
- Фікстури налаштувань: `withSetting({ key: value })` застосовує і повертає в teardown.

```ts
test('approver sees PO in pending list', async ({ confirmedPo, asUser, company }) => {
  const page = await asUser(company.users.approver);
  await page.goto(PoPage.url(confirmedPo.idn));
  await expect(new PoPage(page).status.badge).toHaveText('Pending');
});
```

## Логін
- storageState per user, кеш `.auth/<env>/<email>.json`, генерується лениво.
- `logout_url` у тестах заборонено: PHPSESSID серверний, logout вбиває сесію проекту. Тести на logout в окремому контексті.
