#!/usr/bin/env python3
"""check_ws.py - есть ли encrypted в WS-ответах сервера."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    ws = root / "backend" / "app" / "routers" / "ws.py"

    if not ws.exists():
        print(f"ERR: {ws} не найден")
        return 1

    text = ws.read_text(encoding="utf-8")
    lines = text.split("\n")

    print(f"Файл: {ws}")
    print()
    print("Все строки с 'encrypted':")
    found = 0
    for i, line in enumerate(lines, 1):
        if "encrypted" in line:
            print(f"  {i:4d} | {line.rstrip()}")
            found += 1
    print(f"\nВсего: {found}")

    print()
    print("Проверка ключевых мест:")
    checks = {
        "Чтение encrypted из WS": "data.get(\"encrypted\"",
        "Сохранение в Message": "encrypted=encrypted,",
        "Отправка в payload_out": '"encrypted": encrypted,',
    }
    for label, needle in checks.items():
        ok = needle in text
        print(f"  {'✓' if ok else '✗'} {label}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())