#!/usr/bin/env python3
"""show_fragments.py - показывает фрагменты файлов вокруг ключевых мест."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


QUERIES = {
    "frontend/src/App.tsx": [
        (r"showGroupInfo && activeChat", 30),
        (r"const enqueueForChat", 20),
    ],
    "frontend/src/ChatWindow.tsx": [
        (r"const doSend", 25),
        (r"onEnqueue\(", 6),
        (r"<MessageBubble", 20),
    ],
    "frontend/src/useMessageQueue.ts": [
        (r"trySend", 25),
        (r"wsSend\(", 15),
    ],
}


def show(path: Path, pattern: str, lines: int) -> None:
    if not path.exists():
        print(f"  ! ФАЙЛ НЕ НАЙДЕН: {path}")
        return
    text = path.read_text(encoding="utf-8")
    m = re.search(pattern, text)
    if not m:
        print(f"  ✗ паттерн {pattern!r} не найден")
        return

    # Номер строки
    line_no = text[:m.start()].count("\n") + 1
    lines_list = text.split("\n")
    start = max(0, line_no - 2)
    end = min(len(lines_list), line_no + lines)

    print(f"\n  --- {path.name} : строки {start+1}..{end} ---")
    for i in range(start, end):
        marker = "→" if i == line_no - 1 else " "
        print(f"  {marker} {i+1:4d} | {lines_list[i]}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name

    for rel, queries in QUERIES.items():
        path = root / rel
        print(f"\n{'=' * 70}")
        print(f"{rel}")
        print("=" * 70)
        for pattern, lines in queries:
            show(path, pattern, lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())