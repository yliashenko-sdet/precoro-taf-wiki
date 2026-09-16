# Конфіг і середовища

Рішення: ADR-002.

## Форма
```ts
// src/config/schema.ts
export interface EnvConfig {
  name: 'precorino' | 'pre_dev' | 'us' | 'docker' | 'docker_host';
  baseUrl: string;            // https://app.precorino.com
  controlUrl: string;
  mailpitUrl: string;
  userDomain: string;         // '@acme.com' | '@test.com'
  db: { url: string };        // з env
  run: { language: 'en'|'de'|'es'|'fr'; today: () => Date };
}
export const secrets = z.object({ MAIN_USER_PASSWORD: z.string(), ... }).parse(process.env);
```
- `environments/base.ts` містить усе спільне; `environments/pre_dev.ts` лише те, що відрізняється.
- Вибір середовища: одна змінна `RUN_ENV`. `LOCAL_SERVER_URL` стає полем `baseUrl` у override, а не селектором.
- Шляхи сторінок: у page-об'єктах як `static path = '/manage/users'`; документи як `PoPage.url(idn)`.
- Юзери: у реєстрі компаній, не в конфігу.
- Мова і дата: явні параметри прогону, пишуться в репорт.

## Що видаляється
`src/config/ini/*`, `read_configs.ts` (609 рядків), `run_env.ts`, пакет `ini`, `verify-.env-configs.js` з README.

## Контрольний лічильник
`grep -c "Constants\." src/**` → 0. Зараз 791.

## Відкрито
- Прод-профіль: чи потрібен, і під якими запобіжниками.
