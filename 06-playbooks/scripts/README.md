# Скрипти аналізу

Одноразові скрипти, якими знімались цифри для вікі. Python 3, без залежностей. Запускати з теки TAF-репозиторію або з тек із артефактами, як зазначено.

| Скрипт | Що робить | Використано для |
|---|---|---|
| `allure_run_analysis.py <allure-report/data>` | Тривалості, top-N тестів і файлів, частка підготовки за кроками, категорії падінь, утилізація воркерів | `01-context/nightly-run-2026-09-16.md`, T0-05 |
| `slack_failed_builds.py <export.txt>` | Парсер експорту каналу Jenkins Failed Builds: категорії стадій, перезапуски на гілку, гігієна | `01-context/jenkins-failed-builds.md`, T0-18 |
| `swagger_coverage.py <endpoints_list.txt> <taf-repo>` | Які ендпоінти Swagger обгорнуті клієнтом TAF | ADR-005, T1-07, T2-09 |
| `worker_packing_sim.py <latest.json> <playwright.config.ts>` | Симуляція розподілу проектів по воркерах: порядок конфігу vs найбільші першими | T0-22, T1-14 |
| `debt_counters.sh <taf-repo>` | Грубий підрахунок показників боргу grep-ом, до появи `scripts/debt-counters.ts` | `05-roadmap/metrics.md`, T0-13 |
