---
_organized: true
_width: wide
---
# Ключі конфігу: що в INI, що в коді, що з цього живе

Задача T0-11, ADR-002. Знято 2026-10-06 на `develop` `01e19ecf` скриптом `06-playbooks/scripts/config_keys.py`:

```bash
python3 06-playbooks/scripts/config_keys.py ~/Work/src/precoro-e2e-playwright
```

Скрипт рахує три множини і їх перетини: ключі INI, ключі, які `buildConstants()` повертає явно, і `Constants.<key>` у коді поза `read_configs.ts`. Доступу через дужки (`Constants['<key>']`) у коді немає взагалі — 0 входжень, тому grep точний і ts-morph не потрібен.

## Показники

| Показник | Значення |
| --- | --- |
| Ключів в INI (`configuration.ini`) | 213 |
| Ключів явно в `buildConstants()` | 376 |
| — дублюють ключ INI | 213 |
| — поза INI (env, дати, шляхи до файлів, літерали) | 163 |
| Різних ключів `Constants.<key>` у коді | 339 |
| Входжень `Constants.<key>` | 2 140 |
| Файлів, що читають `Constants` | 161 |
| Мертвих ключів INI | 21 |
| Мертвих ключів поза INI | 16 |
| Ключів, використаних у коді й ніде не оголошених | 0 |
| `flatMap['<key>']` без такого ключа в INI | 3 |

Секції INI: `user_data` 119 ключів, `management_links` 46, `document_links` 40, `app_info` 8.

## Що з цього випливає

**Сім INI-копій уже одна.** ADR-002 і картка T0-11 писались, коли копій було сім по ~220 ключів. Зараз `configuration.ini` один, 213 ключів, хости в ньому не зберігаються (`read_configs.ts` резолвить шляхи проти `APP_BASE_URL`). Аргумент "дрейф між копіями" відпав; усі інші аргументи ADR-002 лишились.

**Невідомий ключ уже ловить компілятор.** `Constants.totally_made_up_key` дає `TS2339: Property does not exist`. Блок "INI-SOURCED PROPERTIES (explicit for type safety)" у `read_configs.ts` перелічує всі 213 ключів INI поіменно, і саме він закриває цю дірку — ціною 376 рядків, які треба правити руками щоразу, коли в INI з'являється ключ. Твердження ADR-002 "у TS дають `any`" більше не описує стан коду; його треба переписати.

**Справжня дірка протилежна: оголошений ключ без значення.** Три посилання `flatMap['<key>']` не мають ключа в INI:

| Ключ | Стан |
| --- | --- |
| `connection_string` | не дірка: `read_configs.ts:172` присвоює його з `DATABASE_URL` до повернення об'єкта |
| `custom_numbering_main_user` | тип `string`, значення `undefined`; читається в `auth-helpers.ts:40` і `custom_numbering_company.ts:160` |
| `custom_numbering_main_user_for_creating_new_company` | тип `string`, значення `undefined`; у коді не читається |

Перший `custom_numbering_main_user` — відомий випадок: `custom_numbering_company` не має постійного головного юзера, спека реєструє компанію з нуля на кожен прогін, і фікстура `setupCompanyProfile` (`base_fixtures.ts:66-82`) це явно описує і обходить. Але тип каже `string`, а значення `undefined`, і єдине, що тримає прогін, — ця обробка у фікстурі. Це аргумент за типізований конфіг сильніший за "`any`": ключ, оголошений без джерела, компілятор не бачить за побудовою, бо джерело INI він не читає.

**Конфігу в конфігу — 14 ключів із 339.** Решта 325 це юзери (124 ключі, 1 353 входження) і константи коду (201 ключ, 661 входження), які потрапили у файл конфігурації тому, що в Python-сюїті `configparser` був єдиним місцем, куди можна покласти рядок.

## Групи використаних ключів

| Група | Ключів | Входжень | Куди переїжджає |
| --- | --- | --- | --- |
| Константи коду | 201 | 661 | page-об'єкти (шляхи сторінок), код, що їх вживає (файли, схеми, дати) |
| Юзери | 124 | 1 353 | реєстр компаній (`04-target/data-and-companies.md`) |
| Середовище | 14 | 126 | `EnvConfig` |

Усі 14 ключів групи "середовище":

| Ключ | Входжень | Джерело | Що це насправді |
| --- | --- | --- | --- |
| `language` | 48 | `LANGUAGE` | параметр прогону |
| `logout_url` | 28 | INI `[app_info]` | шлях `/logout` проти хоста |
| `main_user_password` | 18 | `MAIN_USER_PASSWORD` | секрет |
| `web_base_url` | 7 | `APP_BASE_URL` + basic auth | хост |
| `control_login_url` | 5 | INI `[app_info]` | хост control + шлях |
| `main_test_company_page_url` | 4 | INI `[app_info]` | шлях з id компанії 6998 |
| `login_url` | 3 | INI `[app_info]` | шлях `/login` проти хоста |
| `api_base_url` | 3 | `API_BASE_URL` | хост |
| `access_substitute_user_password` | 2 | env | секрет |
| `control_account_payments_list` | 2 | INI `[app_info]` | хост control + шлях |
| `mail_pit_quick_emails_url` | 2 | INI `[app_info]`, перекривається env | хост MailPit + шлях, з креденшелами в значенні (F-16) |
| `connection_string` | 2 | `DATABASE_URL` | секрет |
| `second_test_company_page_url` | 1 | INI `[app_info]` | шлях з id компанії 14042 |
| `control_logout_url` | 1 | INI `[app_info]` | шлях control |

Тобто справжніх полів середовища не 14, а п'ять хостів (app, api, control, MailPit, БД), прапорець basic auth і мова. Решта з цих 14 розпадається на хост + шлях, де шлях — константа коду, а два ключі несуть id компаній (6998, 14042), які існують лише на спільному середовищі і належать реєстру компаній, а не конфігу.

Домени пошти юзерів: 7 різних (`@acme.com` 69, `@test.com` 39, `@email.com` 4, `@gmail.com` 4, `@qwerty.com`, `@precoro.com`, `@outlook.com`). Поле `userDomain`, яке малювалось у `04-target/config.md`, одним рядком не описується — домен належить акаунту в реєстрі компаній.

## Мертві ключі

**21 ключ INI не читає ніхто.** `[management_links]` 18: `approval_workflow_config_page_url`, `basic_settings_page_url`, `bill_configuration_page_url`, `billing_page_url`, `custom_forms_page_url`, `custom_numbering_page_url`, `expense_approval_config_page_url`, `export_attachments_config_page_url`, `invoice_approval_config_page_url`, `ns_configuration_page_url`, `po_approval_config_page_url`, `pr_approval_config_page_url`, `qbo_configuration_page_url`, `receipt_approval_config_page_url`, `register_demo_page_url`, `supplier_approval_config_page_url`, `supplier_registration_url`, `wr_approval_config_page_url`. `[document_links]` 1: `show_budget_with_id_url`. `[user_data]` 2: `po_company_dcf_limit_username`, `po_company_remove_dcf_username`.

**16 ключів, оголошених у `read_configs.ts` поза INI, теж не читає ніхто:** `activate_item_by_update_xlsx_file_path`, `beta_test_cases_enabled`, `create_supplier_schema_file_path`, `custom_numbering_main_user_for_creating_new_company`, `date_after_5_years`, `gmail_password`, `import_items_xlsx_file_path`, `main_download_dir`, `main_tests_company_id`, `ocr_invoice_from_po_pdf_file_path`, `precondition_for_item_update_xlsx_file_path`, `precondition_for_update_item_by_name_xlsx_file_path`, `qase_api_token`, `qase_project_code`, `repeat_pr_100_plus_body_file_path`, `update_500_item_icfs_xlsx_file_path`.

Чотири з них дублюють змінну середовища, яку відповідний код читає напряму з `process.env` (`QASE_API_TOKEN`, `BETA_TEST_CASES_ENABLED`, `CLEAR_CACHE`), а `gmail_password` не читає ніхто ніде. Решта — шляхи до файлів тестових даних, які лишились від видалених тестів; чи лежать самі файли в репо, тут не перевірялось.

Разом 37 мертвих ключів із 376 оголошених (усі 213 ключів INI перелічені в `buildConstants()` поіменно, тож 376 — це повний список; 339 використаних + 37 мертвих = 376). Видалення — робота T1-01, не цієї задачі: кожен мертвий шлях сторінки треба звірити з тим, чи не ходить туди page-об'єкт власним рядком.

## Форма `EnvConfig`

`src/config/schema.ts` у репо TAF: самі декларації, нічого не імпортує цей файл і ніхто не імпортує його. `EnvConfig` (хости, basic auth, `isShared`), `Secrets` (значення лише з env), `RunConfig`, `Language`. У коментарі файлу записано, що свідомо **не** потрапило всередину і куди належить замість цього: юзери, шляхи сторінок, шляхи до файлів і схем, id компаній.

Відхилення від `04-target/config.md`: немає `userDomain` (7 доменів, належить реєстру), `baseUrl` названо `appBaseUrl` під стать змінній `APP_BASE_URL`, `today` з `run` прибрано (дати це константи коду, не середовище), секрети винесено в окремий тип, бо вони не поле конфігу і не лежать у файлі.

## Що далі

1. Переписати ADR-002: один INI замість семи, `any` замінити на справжню діру (оголошений ключ без джерела), посилання на цей звіт.
2. T1-01 бере звідси: видалення 37 мертвих ключів, перенесення 86 шляхів сторінок у page-об'єкти, 124 юзерів у реєстр компаній.
3. `custom_numbering_main_user_for_creating_new_company` можна прибрати разом з мертвими; `custom_numbering_main_user` лишається, поки реєстр компаній не опише цю компанію як таку, що створюється на прогін.
