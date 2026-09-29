#!/usr/bin/env python3
"""fix_exclude_ws.py - заменяет exclude_ws=ws на exclude_user_id=user_id в ws.py."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    ws_path = root / "backend" / "app" / "routers" / "ws.py"
    if not ws_path.exists():
        print(f"ERR: {ws_path} не найдено", file=sys.stderr)
        return 1

    text = ws_path.read_text(encoding="utf-8")
    original = text

    # Все варианты "exclude_ws=ws" в разных местах
    text = text.replace("exclude_ws=ws,", "exclude_user_id=user_id,")
    text = text.replace("exclude_ws=ws)", "exclude_user_id=user_id)")

    if text == original:
        print(f"  > {ws_path} (ничего не заменено)")
        return 0

    # Посчитаем сколько строк изменилось
    old_count = original.count("exclude_ws=ws")
    new_count = original.count("exclude_ws=ws") - text.count("exclude_ws=ws")

    ws_path.write_text(text, encoding="utf-8")
    print(f"  ~ {ws_path} (заменено {new_count} вхождений)")

    # Показать где именно
    for i, line in enumerate(text.split("\n"), 1):
        if "exclude_user_id" in line:
            print(f"     строка {i}: {line.strip()}")

    print()
    print("Готово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())