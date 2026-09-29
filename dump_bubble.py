#!/usr/bin/env python3
"""dump_bubble.py - показывает блок MessageBubble из ChatWindow.tsx."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    cw = root / "frontend" / "src" / "ChatWindow.tsx"

    if not cw.exists():
        print(f"ERR: {cw} не найден")
        return 1

    text = cw.read_text(encoding="utf-8")
    lines = text.split("\n")

    print("=" * 72)
    print("БЛОК <MessageBubble> В ChatWindow.tsx")
    print("=" * 72)

    found = 0
    for i, line in enumerate(lines):
        if "<MessageBubble" in line:
            found += 1
            print(f"\n--- Найдено на строке {i+1} ---")
            for j in range(i, min(len(lines), i + 40)):
                print(f"{j+1:4d} | {lines[j]}")
                if "/>" in lines[j] and j > i:
                    break

    if not found:
        print("✗ <MessageBubble> не найдено в файле")
        return 1

    print()
    print("=" * 72)
    print("ВСЕ МЕСТА С 'decrypted[' В ФАЙЛЕ")
    print("=" * 72)
    for i, line in enumerate(lines, 1):
        if "decrypted[" in line:
            print(f"{i:4d} | {line}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())