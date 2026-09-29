#!/usr/bin/env python3
"""find_ready.py - ищет все .ready в frontend/src с контекстом."""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    src = root / "frontend" / "src"
    if not src.exists():
        print(f"ERR: {src} не найден")
        return 1

    print(f"Сканирую {src}\n")
    print("=" * 70)

    total = 0
    for f in sorted(src.rglob("*.ts*")):
        if f.name.endswith(".d.ts"):
            continue
        text = f.read_text(encoding="utf-8")
        lines = text.split("\n")
        hits = []
        for i, line in enumerate(lines, 1):
            # ищем .ready везде кроме чисто типов
            if ".ready" in line and "//" not in line.split(".ready")[0][-5:]:
                hits.append((i, line))
        if not hits:
            continue

        print(f"\n--- {f.relative_to(src)} ({len(hits)} вхождений) ---")
        for i, line in hits:
            print(f"  {i:4d} | {line.rstrip()}")
            total += 1

    print()
    print("=" * 70)
    print(f"Всего: {total} вхождений .ready")
    print()
    print("Ищем те, где перед .ready стоит НЕ e2eApi и НЕ что-то без 'useE2E'")
    print("То есть строки вида 'useE2E.ready' — это подозрительно.")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())