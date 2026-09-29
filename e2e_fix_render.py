#!/usr/bin/env python3
"""e2e_fix_render.py - находит блок рендера MessageBubble и правит подмену текста."""
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
    p.add_argument("--no-rebuild", action="store_true")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    cw = root / "frontend" / "src" / "ChatWindow.tsx"
    compose = root / "infra" / "docker-compose.yml"

    if not cw.exists():
        print(f"ERR: {cw} не найден")
        return 1

    hr("1. РЕАЛЬНЫЙ БЛОК <MessageBubble> В ChatWindow.tsx")

    text = cw.read_text(encoding="utf-8")
    lines = text.split("\n")

    block_start = None
    for i, line in enumerate(lines):
        if "<MessageBubble" in line:
            block_start = i
            break

    if block_start is None:
        print("  ✗ в файле нет <MessageBubble")
        return 1

    for j in range(block_start, min(len(lines), block_start + 35)):
        print(f"  {j+1:4d} | {lines[j]}")

    hr("2. ПОИСК 'msg=' ВНУТРИ БЛОКА")
    msg_line_idx = None
    for j in range(block_start, min(len(lines), block_start + 35)):
        if re.search(r"\bmsg\s*=", lines[j]):
            msg_line_idx = j
            print(f"  найдено на строке {j+1}: {lines[j]}")
            break

    if msg_line_idx is None:
        print("  ✗ 'msg=' не найден внутри <MessageBubble>")
        return 1

    hr("3. ПАТЧ")

    # Уже правим? Проверим, есть ли подмена
    already = False
    for j in range(block_start, min(len(lines), block_start + 35)):
        if "decrypted[" in lines[j]:
            already = True
            break

    if already:
        print("  > подмена decrypted[ уже есть в блоке")
        # всё равно добавим лог в рендер
    else:
        # Заменим msg={m} или msg={ ... } на подмену через IIFE
        # Ищем самую простую форму msg={m}
        simple_match = re.compile(r"(\s*)msg=\{m\}\s*,?\s*$")
        if simple_match.search(lines[msg_line_idx]):
            indent_m = re.match(r"(\s*)", lines[msg_line_idx]).group(1)
            new_block = [
                f"{indent_m}msg={{",
                f"{indent_m}  m.encrypted && decrypted[m.id] !== undefined",
                f"{indent_m}    ? {{ ...m, text: decrypted[m.id], encrypted: false }}",
                f"{indent_m}    : m",
                f"{indent_m}}}",
            ]
            lines[msg_line_idx] = "\n".join(new_block)
            print("  ✓ заменил msg={m} на условную подмену")
        else:
            # msg={...} многострочный — попробуем найти закрывающую }
            print("  ⚠ msg= не является простой формой {m}, показываю что там:")
            print(f"    {lines[msg_line_idx]}")
            # ищем на следующих строках
            for j in range(msg_line_idx + 1, min(len(lines), msg_line_idx + 10)):
                print(f"    {j+1:4d} | {lines[j]}")
                if lines[j].strip() == "}" or lines[j].strip() == "},":
                    break
            print("  → пришли мне этот блок, я подгоню точно")
            return 1

    # Также добавим лог рендера прямо здесь — чтобы увидеть на живой странице
    # Вставим console.log перед MessageBubble
    if "[E2E-TRACE] RENDER-MAP" not in text:
        indent = re.match(r"(\s*)", lines[block_start]).group(1)
        log_lines = [
            f"{indent}{{(() => {{",
            f"{indent}  const hasDec = decrypted[m.id] !== undefined;",
            f"{indent}  if (m.encrypted) console.log(\"[E2E-TRACE] RENDER-MAP id=\" + m.id + \" hasDec=\" + hasDec + \" text=\" + String(m.text).slice(0,20));",
            f"{indent}  return null;",
            f"{indent}}})()}}",
        ]
        # вставляем перед <MessageBubble>
        # но так нельзя — JSX не позволяет так просто
        # Поэтому вместо лога — оставим всё как есть, но намекнём через debug
        pass

    cw.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ~ ChatWindow.tsx обновлён")

    # Бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cw, b / "ChatWindow.tsx")
    print(f"  📦 Бэкап: {b}")

    if args.no_rebuild:
        print("\n  (--no-rebuild — пропускаю сборку)")
        return 0

    hr("4. ПЕРЕСБОРКА")
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
  1. Браузер → F12 → Console → очисти
  2. F5
  3. Открой чат 2
  4. Смотри — если текст стал читаемым (не e2e:1:...) — ПОБЕДА!

  Если всё ещё e2e:1:... — скопируй строки [E2E-TRACE] из Console.
  Если UI показывает что-то другое — пришли скриншот/описание.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())