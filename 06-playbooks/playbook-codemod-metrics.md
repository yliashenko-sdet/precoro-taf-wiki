---
_organized: true
---
# Codemod і контрольний показник

## Що таке codemod

Скрипт, що робить одну правку в сотнях файлів через синтаксичне дерево, не через текст. Інструменти для TS: `ts-morph` (простіший API) або `jscodeshift`. Розуміє структуру: "виклик `expect` з аргументом `await x.isVisible()` і далі `.toBe(true)`" переписується цілком, а схожі рядки з іншим змістом не чіпаються.

## Коли codemod, коли руки

| Патерн | Спосіб |
| --- | --- |
| `allure.step` → `test.step`, `attachment` → `attach` | codemod |
| `expect(await x.isVisible()).toBe(true)` → `await expect(x).toBeVisible()` | codemod |
| `waitForTimeout(N)` перед `expect` → видалення | codemod + прогін |
| `Constants.x` → `config.x` | codemod |
| snake\_case → camelCase | codemod (rename через ts-morph, безпечно) |
| `'{}'` + `.replace('{}')` → функція-локатор | codemod |
| `.catch(() => false)` поза предикатами | codemod знаходить, видаляє порціями, прогін підтверджує |
| `force: true`, `clickUsingJavascript` | руки: список від codemod, рішення людини |
| UI-логін → `asUser` | codemod для типового випадку, руки для решти |

## Борг, що залежить від поведінки продукту: спершу докази
Force-кліки, `catch`-ковтання, sleeps не можна замінити наосліп: невідомо, що кожен прикриває. Але й ревʼю по одному не потрібне. Підхід:
1. Хелпер отримує інструментований fallback: спершу штатний виклик із коротким таймаутом, при невдачі стара поведінка плюс запис у лог (тест, локатор, причина від Playwright).
2. Прямі виклики (`force: true`, `dispatchEvent`, `waitForTimeout`) кодмодом заводяться через той самий хелпер.
3. Один нічний прогін дає список: де fallback не спрацював жодного разу (кодмод на штатний виклик без ризику) і де спрацював, згруповано за причиною.
4. Кластери закриваються спільним рішенням: "intercepts pointer events" через обробку накладок (T1-21), "not stable" через очікування, "not visible" через скрол або дефект продукту.
5. Те, що лишилось, отримує коментар-причину і живе легально.

Аргумент: actionability у Playwright це погляд користувача; force це "натисни, навіть якщо користувач не зміг би". Частина таких місць прикриває дефекти продукту, і їх треба розкрити, а не зберегти.

## Правила

1. Один codemod = один PR-серія по файлах, кожен PR мержиться того ж дня. Гілки довші за день не живуть.
2. Codemod лежить у `scripts/codemods/<name>.ts`, повторюваний: можна запустити на будь-якій гілці команди перед мержем.
3. Одразу після codemod вмикається lint-правило як `error`. Без lint показник росте назад.
4. Кожен codemod має "dry-run", що друкує показник до і після. Цифра йде в `05-roadmap/metrics.md`.
5. Перед мержем: прогін зачеплених спеків на Precorino, посилання в PR.

## Контрольні показники: скрипт

```bash
# scripts/debt-counters.sh — друкує показники з metrics.md; CI порівнює з попереднім значенням
c() { printf '%-40s %s\n' "$1" "$(grep -rE "$2" src --include='*.ts' | wc -l | tr -d ' ')"; }
c "allure.*"                'allure\.'
c "expect(await"            'expect\(await'
c "waitForTimeout"          'waitForTimeout\('
c "catch(() => false)"      'catch\(\(\) => false\)'
c "catch(() => {})"         'catch\(\(\) => \{\}\)'
c "force: true"             'force: true'
c "clickUsingJavascript"    'clickUsingJavascript\('
c "doLogin in specs"        'doLogin\('
c "db. in specs"            '\bdb\.'
c "Constants."              'Constants\.'
c "xpath="                  'xpath='
c "this.xxxLocators."       'this\.[a-zA-Z]+Locators\.'
```

У CI: якщо будь-який показник більший за збережений baseline, білд червоний. Baseline оновлюється лише вниз.

## Lint-правила, які вмикаються по мірі codemod-ів

- `playwright/prefer-web-first-assertions` (уже error)
- `playwright/no-wait-for-timeout`
- `playwright/no-force-option`
- `playwright/no-element-handle`
- `playwright/no-networkidle`
- `playwright/no-conditional-in-test`
- `playwright/no-nested-step`
- `no-restricted-imports`: `allure-js-commons` поза `requests.ts`; `LoginPage` у спеках; `dev_precoro_db` у спеках
- `no-restricted-syntax`: `page.goto(*logout*)`
