#!/usr/bin/env python3
"""show_gip.py - показывает места где читается .ready в GroupInfoPanel."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    gip = root / "frontend" / "src" / "GroupInfoPanel.tsx"

    if not gip.exists():
        print(f"ERR: {gip} не найден")
        return 1

    text = gip.read_text(encoding="utf-8")
    lines = text.split("\n")

    print(f"Файл: {gip}")
    print(f"Строк: {len(lines)}")
    print()

    print("=" * 70)
    print("Все строки где упоминается useE2E / e2eApi / .ready")
    print("=" * 70)
    for i, line in enumerate(lines, 1):
        if "useE2E" in line or "e2eApi" in line or ".ready" in line:
            print(f"  {i:4d} | {line}")

    print()
    print("=" * 70)
    print("Сигнатура props (первые 30 строк где export default)")
    print("=" * 70)
    for i, line in enumerate(lines, 1):
        if i > 50:
            break
        if "export default" in line or "useE2E" in line or "}) {" in line:
            print(f"  {i:4d} | {line}")

    print()
    print("=" * 70)
    print("Блок с E2EIndicator (строки где встречается E2EIndicator)")
    print("=" * 70)
    for i, line in enumerate(lines, 1):
        if "E2EIndicator" in line:
            for j in range(max(0, i - 3), min(len(lines), i + 8)):
                marker = "→" if j == i - 1 else " "
                print(f"  {marker} {j+1:4d} | {lines[j]}")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())