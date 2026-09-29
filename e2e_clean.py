#!/usr/bin/env python3
"""e2e_clean.py - восстановление из бэкапа + чистый фикс."""
from __future__ import annotations

import argparse
import shutil
import subprocess
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
    cw = root / "frontend" / "src" / "ChatWindow.tsx"
    compose = root / "infra" / "docker-compose.yml"

    if not cw.exists():
        print(f"ERR: {cw} не найден")
        return 1

    # ============================================================
    # 1. Найти бэкап (самый свежий до поломки)
    # ============================================================
    hr("1. Ищу бэкап ChatWindow.tsx")

    backups = sorted(root.glob("_backup_*/ChatWindow.tsx"),
                     key=lambda p: p.stat().st_mtime, reverse=True)

    if not backups:
        print("  ✗ бэкапов нет — восстанавливать не из чего")
        return 1

    print(f"  Найдено бэкапов: {len(backups)}")
    for b in backups[:5]:
        # проверим синтаксис простой эвристикой — есть ли "⏳ (шифруется)"
        content = b.read_text(encoding="utf-8", errors="replace")
        marker = "⏳ (шифруется)" in content
        print(f"    {b.parent.name}: {b.stat().st_size} байт, '⏳ (шифруется)' = {marker}")

    # Берём первый (свежий) бэкап, где НЕТ маркера "⏳ (шифруется)" и есть "E2E-DEBUG-OVERLAY"
    chosen = None
    for b in backups:
        content = b.read_text(encoding="utf-8", errors="replace")
        if "E2E-DEBUG-OVERLAY" in content and "⏳ (шифруется)" not in content:
            chosen = b
            break

    if chosen is None:
        # Fallback: любой бэкап с E2E-DEBUG-OVERLAY
        for b in backups:
            if "E2E-DEBUG-OVERLAY" in b.read_text(encoding="utf-8", errors="replace"):
                chosen = b
                break

    if chosen is None:
        # Fallback 2: самый свежий
        chosen = backups[0]

    print(f"\n  → восстановлю из: {chosen.parent.name}")

    # Сохраним текущий сломанный для истории
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    broken_backup = root / f"_backup_{ts}"
    broken_backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cw, broken_backup / "ChatWindow_broken.tsx")
    print(f"  📦 Сломанный сохранён: {broken_backup}/ChatWindow_broken.tsx")

    # Восстанавливаем
    shutil.copy2(chosen, cw)
    print(f"  ✓ ChatWindow.tsx восстановлен")

    # ============================================================
    # 2. Простой патч — только скрыть ciphertext в очереди
    # ============================================================
    hr("2. Простой патч — скрыть ciphertext в очереди")

    text = cw.read_text(encoding="utf-8")

    old_virtual = "text: m.text,\n"
    new_virtual = 'text: m.encrypted ? "⏳ (шифруется)" : m.text,\n'

    if '⏳ (шифруется)' in text:
        print("  > уже применено")
    elif old_virtual in text:
        text = text.replace(old_virtual, new_virtual, 1)
        cw.write_text(text, encoding="utf-8")
        print("  ✓ применено: pending-сообщения теперь показывают '⏳ (шифруется)'")
    else:
        print("  ⚠ не нашёл 'text: m.text,' — пропущу")
        idx = text.find("const virtual")
        if idx >= 0:
            for j, line in enumerate(text[idx:idx+1200].split("\n")[:25], 1):
                print(f"    {j:3d} | {line}")

    # ============================================================
    # 3. Проверка синтаксиса через простую эвристику
    # ============================================================
    hr("3. Проверка блока <main>...</main>")

    main_open = text.count("<main")
    main_close = text.count("</main>")
    print(f"  <main>  = {main_open}")
    print(f"  </main> = {main_close}")

    overlay_count = text.count("E2E-DEBUG-OVERLAY")
    print(f"  E2E-DEBUG-OVERLAY = {overlay_count}")

    # Простой heuristic: проверка баланса фигурных скобок в конце файла
    # (не идеально, но поймает грубые ошибки)
    tail = text[-3000:]
    opens = tail.count("{")
    closes = tail.count("}")
    print(f"  Баланс {{}} в последних 3000 симв: {opens} open, {closes} close")

    if main_open != main_close:
        print("  ✗ <main> и </main> не сходятся — файл битый")
        return 1

    # ============================================================
    # 4. Пересборка
    # ============================================================
    hr("4. Пересборка frontend")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        # показать только осмысленные строки
        for line in out.split("\n"):
            if any(x in line for x in ["error", "Error", "ERROR", "expected",
                                       "Unexpected", "ChatWindow.tsx"]):
                print("    " + line)
        return 1
    print("  ✓ Собрано")

    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ up -d")

    hr("ЧТО ДЕЛАТЬ")
    print("""
  1. F12 → Network → Disable cache
  2. Ctrl+Shift+R
  3. Открой чат 2
  4. Смотри правый нижний угол — там будет оверлей:

       msgs=200 enc=200 dec=200
       last id=1270 enc=true dec=YES
       first id=1064 enc=true dec=YES

  5. И что теперь в самом чате — читаемый текст или всё ещё e2e:1:...?

  Пришли:
    • Все строки из оверлея
    • Что видишь в сообщениях
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())