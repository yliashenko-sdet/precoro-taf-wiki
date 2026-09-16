# TAF as-is: коротко

Повні цифри і докази: `audit-2026-09-15.md`. Тут лише те, що треба тримати в голові.

## Профіль
- 2 775 тестів у 50 spec-файлах, ~179K рядків TS. Page-шар ~26K рядків, 48 сторінок, 13 mixin-ів. API-клієнт 241 метод. DB-шар 171 метод.
- Міграція з Python+Selenium: 14 комітів за 36 годин 30–31 березня 2026, AI-assisted. 64% із 1 046 комітів після цього це стабілізаційні фікси.
- 36 Playwright-проектів, по одному на компанію з дампу, кожен `workers: 1`. Ізоляція тримається на цьому, а не на незалежності тестів.

## Прогін (build #240, 9 воркерів, 1 ретрай)
- 2 142 виконано, 21 flaky (1%), 12 failed. Wall-clock 3h19m, machine-time 26h43m, ~45 s на тест.
- Пакування 90%: на 9 воркерах прогін обмежений сумарною роботою. Найдовша лінія minor_company 2h20m стане стелею після ~11 воркерів.
- Найдорожчі тести: no_dcf 130 s, punchout 118 s, spo 89 s, po_receive 88 s, common 75 s, budgets 69 s. main_company 15 s.
- Smoke: 317 тестів, 86% у main_company.

## Що добре і зберігається
- storageState per project через globalSetup; трейс лише на останньому ретраї; `page`-override не піднімає браузер для API-тестів.
- API-фікстури документів (builder → API → use) написані правильно.
- `CompanySetupManager` + `ControlClient` вміють створювати і конфігурувати компанію програмно.
- Managers з `ensureX` ідемпотентні; builders консистентні.
- ESLint уже має `prefer-web-first-assertions` і `no-floating-promises` як error.
- CodeRabbit-гайдлайн забороняє те, що є в коді: команда знає правильні патерни.
- Обгортка HTTP у `requests.ts` з атачами тіла і відповіді.

## Головні борги (кількості)
| Борг | Кількість |
|---|---|
| Value-assertions замість web-first | 5 035 vs 569 |
| Обходи actionability (`force`, `clickUsingJavascript`, `dispatchEvent`) | ~420 |
| `.catch(() => false)` поза предикатами | ~211 |
| `.catch(() => {})` | 131 |
| XPath у локаторах | 1 047, `getByTestId` 0 |
| Hard sleeps | 121 |
| UI-логін у спеках попри storageState | 498 |
| `allure.step` замість `test.step` | 10 243 |
| Прямі DB-виклики у спеках | 1 811; SQL конкатенацією 196/197 |
| API-створень / видалень | 348 / 45, teardown документів 0 |
| Мутації company-wide налаштувань у спеках | 231 у 22 файлах |
| Окремих `test`-об'єктів | 22; 37 спеків збирають `mergeTests` самі |
| INI-конфіги | 7 копій по 220 ключів, `Constants` ~430 ключів, 791 call-site |
| Swagger-ендпоінтів обгорнуто | ~177 із 507 |
| Глибина прототипів page-шару | 15, тримається Babel-хаком `strip-declare-class-fields` |
| Секрети в репозиторії | MailPit basic-auth у всіх INI, прод-токен у `configuration_app.ini`, креденшели ControlClient |
| `tsc` / `eslint` на release | 3 помилки / 109 помилок |
