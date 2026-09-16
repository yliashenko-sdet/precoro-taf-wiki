# Цільова архітектура: огляд

```
tests/            специфікації: describe + test.step + expect; жодного preparation через UI
  └─ fixtures/    один merged `test`; фікстури стану: asUser, company, confirmedPo, approvedInvoice ...
       ├─ api/        publicApi (зі Swagger) + internalApi (ручні, позначені)
       ├─ data/       реєстр компаній і архетипів, builders, teardown
       └─ config/     EnvConfig + override на середовище + zod для env
pages/            сторінки з компонентами (Locator-поля), без assertion, без кроків
components/       ItemsTable, Attachments, Comments, StatusBadge, ConfirmModal, Toast ...
```

Потік тесту: фікстура створює стан через API → тест відкриває сторінку одразу в потрібному місці → дія через компонент → `expect(locator)`.

## Файли цього розділу
| Файл | Шар | Статус |
|---|---|---|
| `config.md` | Конфіг і середовища | Draft, ADR-002 |
| `fixtures-and-test-object.md` | Фікстури, один `test`, логін, apiClient | draft |
| `api-client.md` | Клієнт зі Swagger, internal API | proposed, ADR-005 |
| `data-and-companies.md` | Реєстр компаній, архетипи, teardown, ізоляція | draft |
| `page-layer.md` | Компоненти замість mixin-ів | proposed, ADR-004 |
| `ci-tiering-and-projects.md` | Проекти, воркери, tiering, репортери | draft |

## Межа "не чіпаємо" у фазах 0–1
- Mixin-ланцюжок і Babel-плагін: живуть до фази 3.
- Рядкові локатори: живуть до фази 3, крім нових компонентів.
- `precoro_service.ts`: живе, поки новий клієнт не покриє фікстури.
