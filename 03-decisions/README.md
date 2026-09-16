# Architecture Decision Records

Одне рішення на файл. Статуси: `proposed` → `accepted` → `superseded by ADR-XXX` або `rejected`. Рішення зі статусом accepted не редагується, а замінюється новим.

## Індекс
| ADR | Назва | Статус |
|---|---|---|
| [001](ADR-001-cleanup-order.md) | Порядок модифікації: strangler, дані і залежності диктують черговість | Draft |
| [002](ADR-002-typed-config-instead-of-ini.md) | Типізований конфіг замість INI | Draft |
| [003](ADR-003-reporting-decoupled-from-code.md) | Репортинг знімається з коду: `test.step` замість `allure.*` | Draft |
| [004](ADR-004-page-composition-over-mixins.md) | Композиція компонентів замість mixin-ланцюжка | Draft (proposed) |
| [005](ADR-005-generated-api-client.md) | API-клієнт генерується зі Swagger | Draft (proposed) |
| [006](ADR-006-retries-flaky-policy.md) | Політика ретраїв і flaky | Draft (proposed) |
| [007](ADR-007-test-data-source-of-truth.md) | Джерело правди для автотестових даних: seed з архетипів, не прод | Draft (proposed) |

## Шаблон
```
# ADR-NNN: <назва>
Статус: proposed | Draft | superseded | rejected
Дата: YYYY-MM-DD

## Контекст
Два-три речення і посилання на `01-context`. Цифри не дублюються.

## Рішення
Суть у 3–5 рядків і посилання на файл у `04-target/` за формою.

## Наслідки
Що стає простіше, що складніше, що треба зробити додатково.

## Міграція
Стратегія одним реченням і номери задач із `05-roadmap/plan.md`. Кроки не дублюються.

## Відхилені альтернативи
Що розглядали і чому ні.
```
