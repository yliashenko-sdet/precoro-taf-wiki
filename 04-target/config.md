# Конфіг і середовища

ADR-002. Задачі T0-11, T1-01, T1-02.

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

- `environments/base.ts` містить усе спільне; override на середовище лише те, що відрізняється, ~15 рядків.
- Вибір середовища однією змінною `RUN_ENV`; `LOCAL_SERVER_URL` стає полем `baseUrl` у override, не селектором.
- Шляхи сторінок у page-об'єктах: `static path = '/manage/users'`, документи `PoPage.url(idn)`.
- Юзери в реєстрі компаній (`data-and-companies.md`), не в конфігу.
- Мова і дата прогону явні параметри, пишуться в репорт.

## Що зникає
`src/config/ini/*`, `read_configs.ts`, `run_env.ts`, пакет `ini`.

## Відкрито
Прод-профіль: чи потрібен, і під якими запобіжниками (питання #8).
