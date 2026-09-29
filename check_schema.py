#!/usr/bin/env python3
"""check_schema.py - проверяет MessageRead.encrypted в schemas.py."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    schemas = root / "backend" / "app" / "schemas.py"

    text = schemas.read_text(encoding="utf-8")
    lines = text.split("\n")

    print("=" * 70)
    print("Класс MessageRead (полностью)")
    print("=" * 70)
    in_class = False
    for i, line in enumerate(lines, 1):
        if line.startswith("class MessageRead("):
            in_class = True
        if in_class:
            print(f"  {i:4d} | {line.rstrip()}")
            # конец класса - следующий "class " или пусто+дефис
            if i > 1 and line.startswith("class ") and "MessageRead" not in line:
                break
            if line.startswith("class ") and i > 100:
                break
        if in_class and i > 200:
            break

    print()
    print("=" * 70)
    print("Проверка 'encrypted' в MessageRead")
    print("=" * 70)
    in_msg_read = False
    found = False
    for line in lines:
        if line.startswith("class MessageRead("):
            in_msg_read = True
            continue
        if in_msg_read:
            if line.startswith("class ") and not line.startswith("class MessageRead"):
                break
            if "encrypted" in line:
                found = True
                print(f"  ✓ найдено: {line.strip()}")
    if not found:
        print("  ✗ поле encrypted НЕ найдено в MessageRead")
        print()
        print("  Нужно добавить после 'is_dead_drop: bool = False':")
        print("     encrypted: bool = False")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())