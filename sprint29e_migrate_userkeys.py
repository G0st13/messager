#!/usr/bin/env python3
"""sprint29e_migrate_userkeys.py - создаёт миграцию 0014 для user_keys."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


MIGRATION = '''"""create user_keys table

Revision ID: 0014
Revises: 0013
Create Date: 2025-09-21
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_keys",
        sa.Column(
            "user_id", sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("algorithm", sa.String(30), nullable=False, server_default="ECDH-P256"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_keys")
'''


def find_head(versions_dir: Path) -> str:
    """Находит текущую голову (rev, на которую никто не ссылается)."""
    rev_re = re.compile(r'^revision(?::\s*str)?\s*[:=]\s*["\']([^"\']+)["\']', re.M)
    down_re = re.compile(
        r'^down_revision(?::\s*[^=]*)?\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
        re.M,
    )

    all_revs: set[str] = set()
    all_downs: set[str] = set()
    for f in versions_dir.glob("*.py"):
        if f.name.startswith("__"):
            continue
        text = f.read_text(encoding="utf-8")
        m1 = rev_re.search(text)
        m2 = down_re.search(text)
        if m1:
            all_revs.add(m1.group(1))
        if m2:
            d = m2.group(1).strip()
            if d not in ("None", ""):
                all_downs.add(d)

    heads = sorted(all_revs - all_downs)
    return heads[-1] if heads else "0013"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    versions = root / "backend" / "alembic" / "versions"
    if not versions.exists():
        print(f"ERR: {versions} не найдено", file=sys.stderr)
        return 1

    # определяем текущую голову
    head = find_head(versions)
    print(f"\nТекущая голова: {head}\n")

    # Проверяем, есть ли уже миграция для user_keys
    for f in versions.glob("*.py"):
        text = f.read_text(encoding="utf-8")
        if "user_keys" in text and "create_table" in text:
            print(f"  ✓ миграция для user_keys уже есть: {f.name}")
            return 0

    # Создаём миграцию
    new_rev = "0014"
    target = versions / f"{new_rev}_user_keys.py"

    if target.exists():
        print(f"  ! {target.name} уже существует")
        return 1

    content = MIGRATION.replace('Revises: 0013', f'Revises: {head}')
    content = content.replace('down_revision: Union[str, None] = "0013"',
                              f'down_revision: Union[str, None] = "{head}"')

    # бэкап не нужен — файл новый
    target.write_text(content, encoding="utf-8")
    print(f"  + {target.name}")
    print(f"     revision: {new_rev}")
    print(f"     down_revision: {head}")

    # Проверим, что голова одна
    new_head = find_head(versions)
    print(f"\nНовая голова: {new_head}")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    print()
    print("Проверка после старта:")
    print(f"  docker compose -f infra/docker-compose.yml logs api --tail=20 | grep alembic")
    print(f"  Должно быть: Running upgrade {head} -> {new_rev}, create user_keys table")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())