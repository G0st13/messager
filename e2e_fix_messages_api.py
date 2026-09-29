#!/usr/bin/env python3
"""e2e_fix_messages_api.py - гарантирует что API отдаёт encrypted в /messages."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def run(cmd, cwd=None, timeout=120):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    mpy = root / "backend" / "app" / "routers" / "messages.py"
    compose = root / "infra" / "docker-compose.yml"

    if not mpy.exists():
        print(f"ERR: {mpy} не найден")
        return 1

    text = mpy.read_text(encoding="utf-8")
    lines = text.split("\n")

    print("=" * 72)
    print("1. ВСЕ СТРОКИ С 'encrypted' В messages.py")
    print("=" * 72)
    cnt = 0
    for i, line in enumerate(lines, 1):
        if "encrypted" in line.lower():
            print(f"  {i:4d} | {line}")
            cnt += 1
    if cnt == 0:
        print("  (нет ни одной строки — вот в чём проблема)")

    print()
    print("=" * 72)
    print("2. БЛОК return MessageRead(...) В _to_read")
    print("=" * 72)
    idx = text.find("async def _to_read")
    if idx < 0:
        idx = text.find("def _to_read")
    if idx < 0:
        print("  ✗ функция _to_read не найдена")
        return 1

    sub = text[idx:idx + 2500]
    mstart = sub.find("return MessageRead(")
    if mstart < 0:
        print("  ✗ 'return MessageRead(' не найден")
        return 1

    depth = 0
    i = mstart + len("return MessageRead")
    while i < len(sub):
        if sub[i] == "(":
            depth += 1
        elif sub[i] == ")":
            depth -= 1
            if depth == 0:
                i += 1
                break
        i += 1
    block = sub[mstart:i]
    for j, line in enumerate(block.split("\n"), 1):
        print(f"  {j:3d} | {line}")

    print()
    print("=" * 72)
    print("3. ПРОВЕРКА / ПАТЧ")
    print("=" * 72)

    if "encrypted=m.encrypted" in block:
        print("  ✓ encrypted=m.encrypted уже есть в _to_read")
        print("  → API отдаёт encrypted, проблема в другом месте")
        print("  → пришли мне вывод JS-проверки и Console [E2E-TRACE]")
        return 0

    # Патчим
    anchor = "created_at=m.created_at,"
    a_idx = text.find(anchor, idx)
    if a_idx < 0:
        anchor = "created_at=m.created_at"
        a_idx = text.find(anchor, idx)
    if a_idx < 0:
        print("  ✗ не нашёл 'created_at=m.created_at,' внутри _to_read")
        return 1

    line_start = text.rfind("\n", 0, a_idx) + 1
    line_indent = text[line_start:a_idx]
    insert = f"{line_indent}encrypted=m.encrypted,\n"
    text = text[:a_idx] + insert + text[a_idx:]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    shutil.copy2(mpy, b / "messages.py")
    print(f"  📦 Бэкап: {b}")

    mpy.write_text(text, encoding="utf-8")
    print("  ✓ Добавлено: encrypted=m.encrypted, перед created_at=m.created_at,")

    print()
    print("=" * 72)
    print("4. ПЕРЕЗАПУСК API")
    print("=" * 72)
    code, out = run(["docker", "compose", "-f", str(compose), "restart", "api"], cwd=root)
    print("  " + ("✓ Готово" if code == 0 else "✗ Ошибка: " + out[-500:]))

    print()
    print("=" * 72)
    print("ЧТО ДЕЛАТЬ ДАЛЬШЕ")
    print("=" * 72)
    print("""
  1. Браузер → F12 → Console → очисти (ПКМ → Clear console)
  2. F5
  3. Открой чат 2
  4. В Console выполни проверку:
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
  5. Скопируй вывод — там будет 2 строки.
     • "encrypted=true: 200" (или >0) → перезагрузи F5 ещё раз, открой чат 2,
       текст должен стать читаемым.
     • "encrypted=true: 0" → пришли, копаем дальше.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())