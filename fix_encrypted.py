#!/usr/bin/env python3
"""fix_encrypted.py - remove leftover `encrypted` from model/schemas/ws."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPLACEMENTS = {
    "backend/app/models.py": [
        # убрать поле из модели Message
        (
            '        encrypted: Mapped[bool] = mapped_column(Boolean, default=False)\n',
            '',
        ),
    ],
    "backend/app/schemas.py": [
        # убрать из MessageRead
        (
            '        encrypted: bool = False\n',
            '',
        ),
        # убрать из MessageCreate
        (
            '        encrypted: bool = False\n',
            '',
        ),
        # убрать из DeadDropCreate? нет, там нет
    ],
    "backend/app/routers/messages.py": [
        # убрать из _to_read
        (
            '            encrypted=m.encrypted,\n',
            '',
        ),
        # убрать из search (фильтр по encrypted)
        (
            '                Message.encrypted == False,  # noqa: E712  — ищем только по plaintext\n',
            '',
        ),
        # убрать из send_message
        (
            '            encrypted=payload.encrypted,\n',
            '',
        ),
        # убрать из MessageCreate (если было)
        (
            '        encrypted = bool(data.get("encrypted", False))\n',
            '',
        ),
    ],
    "backend/app/routers/ws.py": [
        (
            '                    encrypted = bool(data.get("encrypted", False))\n',
            '',
        ),
        (
            '                            encrypted=encrypted,\n',
            '',
        ),
        (
            '                            "encrypted": encrypted,\n',
            '',
        ),
        (
            '                        m.encrypted = encrypted\n',
            '',
        ),
        (
            '                        "encrypted": encrypted,\n',
            '',
        ),
        (
            '                                elif r.encrypted:\n'
            '                                    reply_preview = "🔒 encrypted"\n',
            '',
        ),
    ],
    "backend/app/routers/chats.py": [
        (
            '            encrypted=m.encrypted,\n',
            '',
        ),
    ],
    "backend/app/dead_drop_worker.py": [
        (
            '            "encrypted": False,\n',
            '',
        ),
    ],
}


def patch(path: Path, pairs: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    before = text
    for old, new in pairs:
        text = text.replace(old, new)
    if text != before:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path}")
        return True
    print(f"  > {path} (без изменений)")
    return False


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nФикс — удаляем `encrypted` из кода\n")

    for rel, pairs in REPLACEMENTS.items():
        patch(root / rel, pairs)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())