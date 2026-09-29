#!/usr/bin/env python3
"""check_messages_patch.py - проверяет есть ли encrypted в messages.py."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    msg = root / "backend" / "app" / "routers" / "messages.py"

    if not msg.exists():
        print(f"ERR: {msg} не найден")
        return 1

    text = msg.read_text(encoding="utf-8")
    lines = text.split("\n")

    print("=" * 70)
    print("messages.py — все строки с 'encrypted'")
    print("=" * 70)
    found = 0
    for i, line in enumerate(lines, 1):
        if "encrypted" in line:
            print(f"  {i:4d} | {line.rstrip()}")
            found += 1
    print(f"\nВсего: {found}")

    print()
    print("=" * 70)
    print("Функция _to_read полностью")
    print("=" * 70)
    in_func = False
    for i, line in enumerate(lines, 1):
        if "async def _to_read" in line:
            in_func = True
        if in_func:
            print(f"  {i:4d} | {line.rstrip()}")
            if "return MessageRead(" in line:
                # печатаем до закрывающей скобки
                for j in range(i, min(i + 30, len(lines))):
                    print(f"  {j+1:4d} | {lines[j].rstrip()}")
                    if lines[j].strip() == ")":
                        break
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main())