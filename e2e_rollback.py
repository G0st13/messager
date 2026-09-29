#!/usr/bin/env python3
"""e2e_rollback.py - убирает дубль encrypted= в MessageRead, перезапускает api."""
from __future__ import annotations

import argparse
import re
import subprocess
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

    # Показать все строки с encrypted= перед проверкой
    print("=" * 72)
    print("СТРОКИ С 'encrypted=' СЕЙЧАС")
    print("=" * 72)
    for i, line in enumerate(text.split("\n"), 1):
        if "encrypted=" in line:
            print(f"  {i:4d} | {line}")

    # Удалить ВСЕ дубли новой строки
    bad_line = "encrypted=m.encrypted,"
    count = text.count(bad_line)
    print(f"\nНайдено дублей '{bad_line}': {count}")

    if count == 0:
        print("  > дублей нет, откат не нужен")
    else:
        # Удалить строку + её перевод строки (и лишние пробелы перед)
        # Простая замена: убираем строку целиком
        text = re.sub(r"[ \t]*encrypted=m\.encrypted,\s*\n", "", text)
        mpy.write_text(text, encoding="utf-8")
        print(f"  ✓ удалено дублей: {count}")

    # Проверка синтаксиса
    print()
    print("=" * 72)
    print("ПРОВЕРКА СИНТАКСИСА PYTHON")
    print("=" * 72)
    import ast
    try:
        ast.parse(text)
        print("  ✓ синтаксис OK")
    except SyntaxError as e:
        print(f"  ✗ SyntaxError: {e}")
        print(f"    строка {e.lineno}: {e.text}")
        return 1

    # Финальная проверка содержимого _to_read
    print()
    print("=" * 72)
    print("БЛОК return MessageRead(...) ПОСЛЕ ОТКАТА")
    print("=" * 72)
    idx = text.find("return MessageRead(")
    if idx >= 0:
        depth = 0
        i = idx + len("return MessageRead")
        while i < len(text):
            if text[i] == "(":
                depth += 1
            elif text[i] == ")":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        block = text[idx:i]
        for j, line in enumerate(block.split("\n"), 1):
            print(f"  {j:3d} | {line}")

    # Перезапуск
    print()
    print("=" * 72)
    print("ПЕРЕЗАПУСК API")
    print("=" * 72)
    code, out = run(["docker", "compose", "-f", str(compose), "restart", "api"], cwd=root)
    print("  " + ("✓ Готово" if code == 0 else "✗ Ошибка"))

    # Ждём и проверяем здоровье
    print()
    print("=" * 72)
    print("ПРОВЕРКА ЗДОРОВЬЯ API (ждать 5 сек)")
    print("=" * 72)
    import time
    time.sleep(5)
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "api",
                     "python", "-c", "from app.routers.messages import router; print('IMPORT OK')"],
                    cwd=root)
    print("  " + (out.strip() if out.strip() else "(пусто)"))

    print()
    print("=" * 72)
    print("ЧТО ДЕЛАТЬ")
    print("=" * 72)
    print("""
  Если выше "IMPORT OK" — API снова живой.
  Если SyntaxError или другая ошибка — пришли вывод.

  Дальше в браузере:
    1. F12 → Console → очисти
    2. F5
    3. Открой чат 2
    4. В Console вставь:
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

  Если получишь "encrypted=true: 200" — расшифровка в UI должна заработать после F5.
  Если UI всё ещё e2e:1:... — значит есть второй баг, копаем дальше.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())