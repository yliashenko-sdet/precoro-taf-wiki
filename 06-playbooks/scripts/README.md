# Скрипти аналізу

Одноразові скрипти, якими знімались цифри для вікі. Python 3, без залежностей. Запускати з теки TAF-репозиторію або з тек із артефактами, як зазначено.

| Скрипт | Що робить | Використано для |
|---|---|---|
| `allure_run_analysis.py <allure-report/data>` | Тривалості, top-N тестів і файлів, частка підготовки за кроками, категорії падінь, утилізація воркерів | `01-context/audit/nightly-run-2026-09-30.md`, `nightly-run-2026-09-16.md`, T0-05 |
| `slack_failed_builds.py <export.txt>` | Парсер експорту каналу Jenkins Failed Builds: категорії стадій, перезапуски на гілку, гігієна | `01-context/jenkins-failed-builds.md`, T0-18 |
| `swagger_coverage.py <endpoints_list.txt> <taf-repo>` | Які ендпоінти Swagger обгорнуті клієнтом TAF | ADR-005, T1-07, T2-09 |
| `worker_packing_sim.py <latest.json> <playwright.config.ts>` | Симуляція розподілу проектів по воркерах: порядок конфігу vs найбільші першими | T0-22, T1-14 |
| `config_keys.py <taf-repo>` | Ключі конфігу: INI, явні ключі `buildConstants()`, `Constants.<key>` у коді; мертві, відсутні, групи | `01-context/audit/config-keys-2026-10-06.md`, T0-11 |
| `constants_snapshot.js <taf-repo> <збірка> <вихід.json>` | Зліпок усіх значень `Constants` (ключ → хеш) для порівняння до і після перенесення конфігу | T1-01, T1-02 |
| `allure_flaky_by_build.py <тека з <build>.json>` | Flaky rate кожного тесту за серією нічних збірок: пройшов / пройшов після ретраю / впав, масові ночі виключено | `01-context/audit/flaky-tests-2026-10-14.md`, T2-06 |
| `debt_counters.sh <taf-repo>` | Грубий підрахунок показників боргу grep-ом, до появи `scripts/debt-counters.ts` | `05-roadmap/metrics.md`, T0-13 |
| `jenkins_dev_builds.py collect` / `report [--since --until --top]` | Історія гілкових білдів Jenkins dev: `collect` копіює індекс білдів і Allure-дані (failed / broken / flaky) у `~/Work/Precoro/artifacts/jenkins-dev/` і нічого звідти не видаляє (мультибранч втрачає гілку разом з історією при мержі PR), тож запуск щодня зберігає історію; `report` рахує час від червоного білда до наступного зеленого на гілці, червоні поспіль до зеленого і тести, що падають / flaky на кількох гілках. Креденшели `JENKINS_DEV_*` з `.env` TAF | T0-18 (час до вирішення, повторні порушники на гілках), T2-07 |
| `team_stats.py collect` / `week` / `report` / `journal-sync` / `catalog` | Статистика для Automation weekly: сирі зрізи (нічні QA Jenkins, гілкові dev Jenkins, PR GitHub, `npm run debt` на `develop`) у `~/Work/Precoro/stats`, показники тижня, звіт, журнал змін з гіпотезою і виміром до/після; каталог показників у `CATALOG` | `06-playbooks/team-stats.md`, скіл `automation-weekly` |
| `nightly_time.py fetch` / `waits` / `wall` / `concurrency` | Куди йде час нічного: `fetch` бере Allure `test-cases` збірки QA Jenkins у `~/Work/Precoro/artifacts/nightly-allure/<build>/` (креденшели як у `team_stats.py`); `waits` — очікування, що добігли до таймауту, у тестах, що пройшли, `dashboardPage`, падіння з ретраями, топ-локатори по ночах; `wall` — wall-clock з machine-time проєктів (проєкт на одному воркері, 9 воркерів) у порядку конфігу, за часом і без топ-очікувань; `concurrency` — скільки тестів ішло одночасно | T1-33, T1-34, T1-29, порядок проєктів (T0-22, PR #390), `99-log.md` 2026-11-03 |
| `nightly_hooks.py <build>...` | Час Before/After Hooks нічного за фікстурами, час ретраїв окремо; дані ті самі, що в `nightly_time.py fetch` | [Рев'ю PR #390](../../01-context/audit/pr-390-tasks-2026-11-03.md), розділ 5.3 |
