# Architecture Decision Records

Одне рішення на файл. Статуси: `proposed` → `accepted` → `superseded by ADR-XXX` або `rejected`. Прийняте рішення не редагується, а замінюється новим.

## Індекс
| ADR | Назва | Статус |
|---|---|---|
| [001](ADR-001-cleanup-order.md) | Порядок причісування: strangler, дані і залежності диктують черговість | accepted |
| [002](ADR-002-typed-config-instead-of-ini.md) | Типізований конфіг замість INI | accepted |
| [003](ADR-003-reporting-decoupled-from-code.md) | Репортинг знімається з коду: `test.step` замість `allure.*` | accepted |
| [004](ADR-004-page-composition-over-mixins.md) | Композиція компонентів замість mixin-ланцюжка | proposed |
| [005](ADR-005-generated-api-client.md) | API-клієнт генерується зі Swagger | proposed |
| [006](ADR-006-retries-flaky-policy.md) | Політика ретраїв і flaky | proposed |

## Шаблон
```
# ADR-NNN: <назва>
Статус: proposed | accepted | superseded | rejected
Дата: YYYY-MM-DD

## Контекст
Що є зараз і чому це проблема. Цифри з аудиту.

## Рішення
Що робимо. Цільова форма.

## Наслідки
Що стає простіше, що складніше, що треба зробити додатково.

## Міграція
Кроки, порядок, як не зупинити команду. Метрика-храповик.

## Відхилені альтернативи
Що розглядали і чому ні.
```
