#!/usr/bin/env python3
"""sprint29j_fix_messages_order.py - берём последние N, а не первые N."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


OLD = '''    await _ensure_member(db, chat_id, current.id)
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    msgs = (await db.execute(stmt)).scalars().all()
    return [await _to_read(db, m, current.id) for m in msgs]'''

NEW = '''    await _ensure_member(db, chat_id, current.id)
    # Берём ПОСЛЕДНИЕ `limit` сообщений (свежие), а не первые.
    # Сортируем по убыванию, ограничиваем, потом разворачиваем обратно.
    stmt = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(limit)
    )
    msgs = list((await db.execute(stmt)).scalars().all())
    msgs.reverse()
    return [await _to_read(db, m, current.id) for m in msgs]'''


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    msgs = root / "backend" / "app" / "routers" / "messages.py"
    if not msgs.exists():
        print(f"ERR: {msgs} не найдено", file=sys.stderr)
        return 1

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    shutil.copy2(msgs, b / "messages.py")
    print(f"📦 Бэкап: {b}\n")

    text = msgs.read_text(encoding="utf-8")

    if NEW in text:
        print("  > уже применено")
        return 0

    if OLD not in text:
        print("  ✗ старый блок не найден. Пришли текущий list_messages:")
        print()
        # покажем что есть
        for i, line in enumerate(text.split("\n"), 1):
            if "list_messages" in line:
                for j in range(i - 1, min(i + 30, len(text.split("\n")))):
                    print(f"  {j+1:4d} | {text.split(chr(10))[j]}")
                break
        return 1

    text = text.replace(OLD, NEW, 1)
    msgs.write_text(text, encoding="utf-8")
    print(f"  ~ {msgs.name}: list_messages теперь отдаёт последние N")
    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    print()
    print("После рестарта — Ctrl+Shift+R в браузере.")
    print("E2E-сообщения (id 740-742) должны появиться и расшифроваться.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())