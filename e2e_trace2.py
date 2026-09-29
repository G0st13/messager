#!/usr/bin/env python3
"""e2e_trace2.py - показывает содержимое decrypted + проверяет патчи."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
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
    if not root.exists():
        print(f"ERR: {root} не найдено")
        return 1

    src = root / "frontend" / "src"
    cw = src / "ChatWindow.tsx"
    ue = src / "useE2E.ts"
    compose = root / "infra" / "docker-compose.yml"

    hr("1. ПРОВЕРКА ПАТЧЕЙ ИЗ e2e_trace.py")

    for f in (cw, ue):
        if not f.exists():
            print(f"  ✗ {f.name} не найден")
            continue
        text = f.read_text(encoding="utf-8")
        marks = {
            "decryptFromChat called": "[E2E-TRACE] decryptFromChat called",
            "render msg": "[E2E-TRACE] render msg",
            "WS message": "[E2E-TRACE] WS message",
            "decrypt useEffect fired": "[E2E-TRACE] decrypt useEffect fired",
        }
        print(f"\n  {f.name}:")
        for label, needle in marks.items():
            print(f"    {'✓' if needle in text else '✗'} {label}")

    # Показать реальный decryptFromChat в useE2E.ts
    hr("2. РЕАЛЬНЫЙ decryptFromChat В useE2E.ts")
    if ue.exists():
        text = ue.read_text(encoding="utf-8")
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "decryptFromChat" in line and ("useCallback" in line or "const" in line):
                for j in range(i, min(len(lines), i + 18)):
                    print(f"  {j+1:4d} | {lines[j]}")
                break
        else:
            # ищем любой блок с decryptFromChat
            for i, line in enumerate(lines, 1):
                if "decryptFromChat" in line:
                    print(f"  {i:4d} | {line}")

    # Показать реальный рендер в ChatWindow.tsx
    hr("3. РЕАЛЬНЫЙ БЛОК РЕНДЕРА MessageBubble В ChatWindow.tsx")
    if cw.exists():
        text = cw.read_text(encoding="utf-8")
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "<MessageBubble" in line:
                for j in range(i, min(len(lines), i + 25)):
                    print(f"  {j+1:4d} | {lines[j]}")
                break

    # Показать useEffect расшифровки
    hr("4. useEffect РАСШИФРОВКИ В ChatWindow.tsx")
    if cw.exists():
        text = cw.read_text(encoding="utf-8")
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if "[E2E-TRACE] decrypt useEffect fired" in line:
                start = max(0, i - 3)
                for j in range(start, min(len(lines), i + 40)):
                    print(f"  {j+1:4d} | {lines[j]}")
                break

    # ДОБАВИТЬ ЛОГ СОДЕРЖИМОГО decrypted
    hr("5. ПАТЧ — ЛОГ СОДЕРЖИМОГО decrypted")

    if not cw.exists():
        print("  ✗ ChatWindow.tsx не найден")
        return 1

    text = cw.read_text(encoding="utf-8")

    if "[E2E-TRACE] decrypted content" in text:
        print("  > уже пропатчено")
    else:
        # Ищем блок setDecrypted
        anchor_candidates = [
            'if (!cancelled && Object.keys(updates).length > 0) {\n      setDecrypted((prev) => ({ ...prev, ...updates }));',
            'setDecrypted((prev) => ({ ...prev, ...updates }));',
        ]
        patched = False
        for old in anchor_candidates:
            if old in text:
                if "setDecrypted" in old and "decrypted content" not in text:
                    new = old + '\n        console.log("[E2E-TRACE] decrypted content sample:",\n          Object.entries(updates).slice(0, 3).map(([k, v]) =>\n            `id=${k} → ${String(v).slice(0, 40)}`));'
                    text = text.replace(old, new, 1)
                    patched = True
                    break

        if not patched:
            # запасной якорь — просто после setDecrypted добавить лог
            m = re.search(r"(setDecrypted\(\(prev\) => \(\{ \.\.\.prev, \.\.\.updates \}\)\);)", text)
            if m:
                add = m.group(1) + '\n        console.log("[E2E-TRACE] decrypted content sample:",\n          Object.entries(updates).slice(0, 3).map(([k, v]) =>\n            `id=${k} → ${String(v).slice(0, 40)}`));'
                text = text.replace(m.group(1), add, 1)
                patched = True

        if patched:
            cw.write_text(text, encoding="utf-8")
            print("  ✓ ChatWindow.tsx — добавлен лог содержимого decrypted")
        else:
            print("  ✗ не нашёл setDecrypted((prev) => ...)")
            print("  Открой ChatWindow.tsx, найди 'setDecrypted' — покажи мне строку")

    hr("6. ПЕРЕСБОРКА")
    print("  → build --no-cache frontend ...")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        print(out[-2000:])
        return 1
    print("  ✓ Собрано")

    print("  → up -d ...")
    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ Готово")

    hr("ЧТО ДЕЛАТЬ")
    print("""
  1. Браузер → F12 → Console → очисти (ПКМ → Clear console)
  2. F5 (не Ctrl+Shift+R — обычное, чтобы console.log не потерялись)
  3. Открой чат 2
  4. Подожди 2-3 секунды
  5. Скопируй ВСЕ строки с [E2E-TRACE] — особенно новые:
       • decrypted content sample: id=XXX → <текст>
  6. Отправь новый сообщение, снова скопируй новые [E2E-TRACE]
  7. Пришли мне всё

  Особенно важно:
    • Что в "decrypted content sample" — там будут первые 3 расшифрованных значения.
      Если там "id=760 → 🔒 ..." или "id=760 → null" — значит decryptFromChat падает.
      Если там "id=760 → привет" — значит всё расшифровывается, проблема только в рендере.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())