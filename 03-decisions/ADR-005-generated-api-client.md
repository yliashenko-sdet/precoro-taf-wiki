# ADR-005: API-клієнт генерується зі Swagger
Статус: proposed
Дата: 2026-09-16

## Контекст
`precoro_service.ts`: 241 ручний метод, Axios із `validateStatus: () => true` (non-2xx не кидає), 5 перевірок статусу на весь сервіс і 219 `expect(statusCode)` у фікстурах, 7 типів на весь API, `Record<string, unknown>` ~700 разів. Swagger з'явився нещодавно, 507 ендпоінтів; клієнт покриває ~177. Не покриті саме lifecycle-переходи (mass-approve, approve-review, take_over_revise, receive_all, send, pay, imports, revisions), через що "документ у статусі X" будується через UI.

Swagger покриває публічний API до Locations включно. Users, roles, warehouses, company settings, custom forms, OCR ідуть через внутрішні ендпоінти, зняті з network.

## Рішення (пропозиція)
- `openapi-typescript` генерує типи, `openapi-fetch` або Playwright `request` дає клієнт. Генерація в `npm run api:generate`, результат комітиться.
- Non-2xx кидає помилку за замовчуванням; `expect(statusCode)` у фікстурах зникають. Явний `allowStatus` там, де негативний сценарій.
- Два клієнти з явними назвами: `publicApi` (зі Swagger) і `internalApi` (ручні обгортки для того, чого нема в Swagger), щоб різна стабільність була видимою.
- Обгортка з атачами запиту/відповіді зберігається як middleware.
- Схеми для 117 API-тестів через ajv із OpenAPI, 63 ручні JSON-схеми видаляються.
- Contract-check у CI: якщо Swagger змінив ендпоінт, який TAF використовує, збірка червона до оновлення.

## Міграція
Новий клієнт поруч зі старим; фікстури переїжджають першими (вони найбільш централізовані); `precoro_service.ts` видаляється при нулі call-site. Храповик: кількість імпортів `precoro_service`.

## Відкрито
- Чи повний Swagger, чи є секції після Locations.
- Чи можна отримати OpenAPI-файл у CI автоматично з Precorino.
