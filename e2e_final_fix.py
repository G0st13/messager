#!/usr/bin/env python3
"""e2e_final_fix.py - финальный фикс: модель Message.encrypted + откат дубля."""
from __future__ import annotations

import argparse
import ast
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


def run(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def hr(t):
    print()
    print("=" * 72)
    print(f"  {t}")
    print("=" * 72)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    models = root / "backend" / "app" / "models.py"
    mpy = root / "backend" / "app" / "routers" / "messages.py"
    compose = root / "infra" / "docker-compose.yml"

    for f in (models, mpy):
        if not f.exists():
            print(f"ERR: {f} не найден")
            return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1. models.py — добавить encrypted в класс Message
    # ============================================================
    hr("1. models.py — поле encrypted в классе Message")

    mtext = models.read_text(encoding="utf-8")

    # Проверим есть ли уже
    m = re.search(r"class Message\(Base[^)]*\):(.*?)(?=\nclass |\Z)", mtext, re.DOTALL)
    if not m:
        print("  ✗ класс Message не найден в models.py")
        return 1
    msg_body = m.group(1)

    if "encrypted: Mapped" in msg_body:
        print("  > поле encrypted уже есть в классе Message")
    else:
        print("  поле encrypted НЕ найдено — добавляю")

        shutil.copy2(models, backup / "models.py")

        # Найдём строку в блоке Message с "is_pinned: Mapped[bool]" и после неё добавим
        anchor_pattern = re.compile(
            r"(\n\s+)(is_pinned: Mapped\[bool\] = mapped_column\(Boolean, default=False\)\n)",
            re.MULTILINE,
        )
        anchor_in_body = anchor_pattern.search(msg_body)
        if not anchor_in_body:
            # fallback — ищем просто is_pinned: Mapped[bool]
            anchor_pattern = re.compile(
                r"(\n\s+)(is_pinned:\s*Mapped\[bool\][^\n]*\n)",
                re.MULTILINE,
            )
            anchor_in_body = anchor_pattern.search(msg_body)

        if not anchor_in_body:
            print("  ✗ не нашёл якорь is_pinned в классе Message")
            print("  Пришли мне строки класса Message (фрагмент с полями)")
            return 1

        # Найдём абсолютную позицию в файле
        rel_start = anchor_in_body.start(2)
        abs_start = m.start(1) + rel_start
        abs_end = abs_start + len(anchor_in_body.group(2))
        indent = anchor_in_body.group(1).strip() or "        "

        insert = f"{indent}encrypted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=\"false\")\n"
        mtext = mtext[:abs_end] + insert + mtext[abs_end:]

        models.write_text(mtext, encoding="utf-8")
        print("  ✓ добавлено поле encrypted в класс Message")

    # Проверим синтаксис models.py
    try:
        ast.parse(mtext)
        print("  ✓ models.py — синтаксис OK")
    except SyntaxError as e:
        print(f"  ✗ models.py — SyntaxError: {e}")
        return 1

    # ============================================================
    # 2. messages.py — убрать дубль encrypted=
    # ============================================================
    hr("2. messages.py — убрать возможный дубль encrypted=m.encrypted,")

    m2 = mpy.read_text(encoding="utf-8")
    dup_count = m2.count("encrypted=m.encrypted,")
    print(f"  Найдено дублей 'encrypted=m.encrypted,': {dup_count}")

    if dup_count > 0:
        shutil.copy2(mpy, backup / "messages.py")
        m2 = re.sub(r"[ \t]*encrypted=m\.encrypted,\s*\n", "", m2)
        mpy.write_text(m2, encoding="utf-8")
        print(f"  ✓ удалено: {dup_count}")

    try:
        ast.parse(m2)
        print("  ✓ messages.py — синтаксис OK")
    except SyntaxError as e:
        print(f"  ✗ messages.py — SyntaxError: {e}")
        return 1

    # ============================================================
    # 3. Перезапуск api
    # ============================================================
    hr("3. Перезапуск API")
    code, out = run(["docker", "compose", "-f", str(compose), "restart", "api"], cwd=root)
    print("  " + ("✓ restarted" if code == 0 else "✗ " + out[-300:]))

    print("  Ждём 6 сек...")
    time.sleep(6)

    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "api",
                     "python", "-c",
                     "from app.models import Message; "
                     "from app.routers.messages import router; "
                     "print('import OK; Message.encrypted =', hasattr(Message, 'encrypted'))"],
                    cwd=root)
    print("  " + out.strip())

    if "True" not in out:
        print("  ✗ модель всё ещё без encrypted — пришли вывод")
        return 1

    # ============================================================
    # 4. Пересборка frontend
    # ============================================================
    hr("4. Пересборка frontend (~40 сек)")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала: " + out[-1500:])
        return 1
    print("  ✓ Собрано")

    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ up -d")

    # ============================================================
    # Финальная проверка API — что отдаёт /messages
    # ============================================================
    hr("5. Проверка API — что отдаёт /chats/2/messages")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "api",
                     "python", "-c",
                     "import asyncio; "
                     "from app.db import SessionLocal; "
                     "from app.models import Message; "
                     "from sqlalchemy import select; "
                     "async def main():\n"
                     "    async with SessionLocal() as db:\n"
                     "        rows = (await db.execute(select(Message).where(Message.chat_id==2).order_by(Message.id.desc()).limit(3))).scalars().all()\n"
                     "        for r in rows: print(r.id, r.encrypted, (r.text or '')[:30])\n"
                     "asyncio.run(main())"],
                    cwd=root)
    print(out)

    hr("ЧТО ДЕЛАТЬ В БРАУЗЕРЕ")
    print("""
  1. F12 → Console → очисти
  2. Ctrl+Shift+R (hard reload)
  3. Открой чат 2
  4. Смотри: если видишь читаемый текст вместо e2e:1:... — ПОБЕДА

  Если всё ещё e2e:1:... — в Console выполни:
""")
    print(r"""
     (async () => {
       const token = localStorage.getItem("access_token");
       const r = await fetch("http://localhost:8000/api/v1/chats/2/messages", {
         headers: { Authorization: "Bearer " + token },
       });
       const msgs = await r.json();
       const enc = msgs.filter(m => m.encrypted);
       console.log("Всего:", msgs.length, "| encrypted=true:", enc.length);
       enc.slice(-3).forEach(m => console.log("  id=" + m.id, "encrypted=" + m.encrypted));
     })();
""")
    print("""
  5. Пришли мне вывод JS.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())