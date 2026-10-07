#!/usr/bin/env python3
"""Ключі конфігу TAF: що в INI, що в `read_configs.ts`, що реально використано в коді.

Аргумент: тека TAF-репозиторію (за замовчуванням поточна).

Рахує три множини і їх перетини:
  INI      — ключі з `src/config/ini/configuration.ini`;
  BUILT    — ключі, які `buildConstants()` повертає явно (літерал, геттери, env);
  USED     — `Constants.<key>` у коді поза `read_configs.ts`.

Звідси: мертві ключі (INI \\ USED), відсутні (USED \\ (INI ∪ BUILT)) і групи
ключів для `EnvConfig` (`04-target/config.md`): середовище / юзери / константи коду.

Доступу `Constants['<key>']` у коді немає (перевірено 2026-10-06), тож grep точний.
Вивід: markdown у stdout. Задача T0-11, ADR-002.
"""

import os
import re
import sys
from collections import Counter, defaultdict

INI_PATH = "src/config/ini/configuration.ini"
READ_CONFIGS = "src/config/read_configs.ts"
SCAN_DIRS = ("src", "scripts")
SCAN_FILES = ("playwright.config.ts",)

USE_RE = re.compile(r"Constants\.([A-Za-z_][A-Za-z_0-9]*)")
BRACKET_RE = re.compile(r"Constants\[")
INI_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*)$")
INI_SECTION_RE = re.compile(r"^\[([^\]]+)\]")
# Ключ верхнього рівня в літералі, який повертає buildConstants(): рівно 4 пробіли.
# `,` в кінці класу покриває скорочений запис (`language,`), `(` — геттери.
BUILT_KEY_RE = re.compile(r"^ {4}(?:get\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*[:(,]")

# Групи для EnvConfig. Порядок важливий: перший збіг виграє.
USER_SECTIONS = {"user_data", "user_info"}
ENV_SECTIONS = {"app_info"}
USER_SUFFIXES = ("_username", "_user_name", "_user", "_email", "_main_user")
ENV_KEYS = {
    "api_base_url",
    "web_base_url",
    "connection_string",
    "mail_pit_quick_emails_url",
    "language",
    "main_user_password",
    "access_substitute_user_password",
}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_ini(root):
    """{key: section}, у порядку файлу. Значення не читаємо: у них бувають секрети."""
    keys = {}
    section = ""
    for line in read(os.path.join(root, INI_PATH)).splitlines():
        line = line.strip()
        if not line or line.startswith((";", "#")):
            continue
        sec = INI_SECTION_RE.match(line)
        if sec:
            section = sec.group(1)
            continue
        key = INI_KEY_RE.match(line)
        if key:
            keys[key.group(1)] = section
    return keys


def parse_built(root):
    """Ключі, які літерал `return {...}` у buildConstants() називає явно."""
    text = read(os.path.join(root, READ_CONFIGS))
    # Лише тіло літерала `return {...}`, інакше в ключі потрапляють `if` і `for`
    # з коду функції вище.
    start = text.index("\n  return {", text.index("function buildConstants"))
    body = text[start:]
    keys = []
    for line in body.splitlines():
        match = BUILT_KEY_RE.match(line)
        if match:
            keys.append(match.group(1))
    return keys


def collect_usages(root):
    """{key: Counter(файл -> входження)} по всьому репозиторію, крім read_configs.ts."""
    usages = defaultdict(Counter)
    bracket_hits = []
    targets = []
    for directory in SCAN_DIRS:
        for dirpath, _, filenames in os.walk(os.path.join(root, directory)):
            if "node_modules" in dirpath:
                continue
            for name in filenames:
                if name.endswith(".ts"):
                    targets.append(os.path.join(dirpath, name))
    targets += [os.path.join(root, name) for name in SCAN_FILES]

    for path in targets:
        rel = os.path.relpath(path, root)
        if rel == READ_CONFIGS or not os.path.exists(path):
            continue
        text = read(path)
        for key in USE_RE.findall(text):
            usages[key][rel] += 1
        if BRACKET_RE.search(text):
            bracket_hits.append(rel)
    return usages, bracket_hits


def group_of(key, section):
    if key in ENV_KEYS or section in ENV_SECTIONS:
        return "середовище"
    if section in USER_SECTIONS or key.endswith(USER_SUFFIXES):
        return "юзери"
    return "константи коду"


def table(rows, header):
    out = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    out += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(out)


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    ini = parse_ini(root)
    built_list = parse_built(root)
    built = set(built_list)
    usages, bracket_hits = collect_usages(root)

    used = set(usages)
    total_occurrences = sum(sum(files.values()) for files in usages.values())
    files_touched = {f for files in usages.values() for f in files}

    known = set(ini) | built
    dead = sorted(k for k in ini if k not in used)
    missing = sorted(k for k in used if k not in known)
    built_only = sorted(k for k in built if k not in ini)
    duplicated = sorted(k for k in built if k in ini)
    dead_built = sorted(k for k in built_only if k not in used)

    print("# Ключі конфігу: INI, read_configs.ts, код\n")
    print(f"Репозиторій: `{root}`\n")
    print(
        table(
            [
                ["ключів в INI", len(ini)],
                ["ключів явно в `buildConstants()`", len(built)],
                ["— з них дублюють ключ INI", len(duplicated)],
                ["— з них поза INI (env, дати, шляхи, літерали)", len(built_only)],
                ["різних ключів `Constants.<key>` у коді", len(used)],
                ["входжень `Constants.<key>`", total_occurrences],
                ["файлів, що читають `Constants`", len(files_touched)],
                ["мертвих ключів INI (не використані)", len(dead)],
                ["мертвих ключів поза INI", len(dead_built)],
                ["відсутніх ключів (у коді, але ніде не оголошені)", len(missing)],
                ["доступів `Constants['<key>']`", len(bracket_hits)],
            ],
            ["показник", "значення"],
        )
    )

    groups = Counter()
    group_occurrences = Counter()
    for key in used:
        group = group_of(key, ini.get(key, ""))
        groups[group] += 1
        group_occurrences[group] += sum(usages[key].values())
    print("\n## Групи використаних ключів\n")
    print(
        table(
            [[g, groups[g], group_occurrences[g]] for g in sorted(groups, key=lambda g: -groups[g])],
            ["група", "ключів", "входжень"],
        )
    )

    print("\n## Мертві ключі INI\n")
    print("\n".join(f"- `{k}` (`[{ini[k]}]`)" for k in dead) if dead else "Немає.")

    print("\n## Мертві ключі, оголошені в read_configs.ts поза INI\n")
    print("\n".join(f"- `{k}`" for k in dead_built) if dead_built else "Немає.")

    print("\n## Відсутні ключі (у коді є, ніде не оголошені)\n")
    if missing:
        for key in missing:
            where = ", ".join(f"`{f}` ×{n}" for f, n in usages[key].most_common())
            print(f"- `{key}` — {where}")
    else:
        print("Немає.")

    print("\n## Топ-20 ключів за входженнями\n")
    top = sorted(used, key=lambda k: -sum(usages[k].values()))[:20]
    print(
        table(
            [
                [f"`{k}`", sum(usages[k].values()), len(usages[k]), group_of(k, ini.get(k, ""))]
                for k in top
            ],
            ["ключ", "входжень", "файлів", "група"],
        )
    )


if __name__ == "__main__":
    main()
