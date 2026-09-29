#!/usr/bin/env python3
"""fix_encrypted2.py - remove `encrypted` lines by content, ignoring indentation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


FIXES = {
    "backend/app/models.py": [
        "encrypted: Mapped[bool] = mapped_column(Boolean, default=False)",
    ],
    "backend/app/schemas.py": [
        "encrypted: bool = False",
    ],
    "backend/app/routers/ws.py": [
        'encrypted = bool(data.get("encrypted", False))',
        "encrypted=encrypted,",
        "elif r.encrypted:",
        'reply_preview = "🔒 encrypted"',
    ],
}


def fix_file(path: Path, remove_lines: list[str]) -> int:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0
    lines = path.read_text(encoding="utf-8").split("\n")
    out = []
    removed = 0
    to_remove = {s.strip() for s in remove_lines}
    for line in lines:
        if line.strip() in to_remove:
            removed += 1
            continue
        out.append(line)
    if removed:
        path.write_text("\n".join(out), encoding="utf-8")
        print(f"  ~ {path} ({removed} строк удалено)")
    else:
        print(f"  > {path} (нечего удалять)")
    return removed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nФикс 2 — удаляем encrypted по содержимому\n")

    total = 0
    for rel, lines in FIXES.items():
        total += fix_file(root / rel, lines)

    print(f"\nУдалено строк: {total}")
    print("\nДальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())