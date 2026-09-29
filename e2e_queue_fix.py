#!/usr/bin/env python3
"""e2e_queue_fix.py - скрывает шифртекст в очереди + добавляет queue info в оверлей."""
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

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cw, backup / "ChatWindow.tsx")
    print(f"📦 Бэкап: {backup}")

    text = cw.read_text(encoding="utf-8")

    # ============================================================
    # 1. Скрыть шифртекст в virtual-сообщениях очереди
    # ============================================================
    hr("1. Скрыть шифртекст в virtual-сообщениях очереди")

    # Ищем строку, где формируется text для virtual
    needles = [
        'text: m.encrypted ? "🔒 ..." : m.text,',
        'text: m.encrypted ? "🔒 ..." : m.text',
        'text: m.text,',
    ]
    new_text = 'text: m.encrypted ? "⏳ (шифруется)" : m.text,'

    patched_text = False
    for old in needles:
        if old in text:
            text = text.replace(old, new_text, 1)
            print(f"  ✓ заменил '{old}' на 'text: m.encrypted ? \"⏳ (шифруется)\" : m.text,'")
            patched_text = True
            break

    if not patched_text:
        print("  ⚠ не нашёл строку с text: m.text в virtual mapping")
        print("  найди в ChatWindow.tsx блок с 'const virtual: Message[]' и покажи его мне")
        # Показать блок
        idx = text.find("const virtual")
        if idx >= 0:
            for j, line in enumerate(text[idx:idx+1500].split("\n")[:30], 1):
                print(f"    {j:3d} | {line}")

    # ============================================================
    # 2. Расширить оверлей — добавить queue
    # ============================================================
    hr("2. Расширить debug-оверлей (queue count + last text)")

    # Ищем текущий оверлей
    marker = "{`msgs=${messages.length} enc=${messages.filter(m => m.encrypted).length} dec=${Object.keys(decrypted).length}"
    if marker in text and "queue=${myQueue.length}" not in text:
        # Добавляем строку с queue и первой буквой текста
        old_line = "msgs=${messages.length} enc=${messages.filter(m => m.encrypted).length} dec=${Object.keys(decrypted).length}\\n"
        new_line = (
            "msgs=${messages.length} enc=${messages.filter(m => m.encrypted).length} dec=${Object.keys(decrypted).length}\\n"
            "queue=${myQueue.length} virtual=${allMessages.length - messages.length}\\n"
        )
        if old_line in text:
            text = text.replace(old_line, new_line, 1)
            print("  ✓ добавил queue=N virtual=N в оверлей")
        else:
            print("  > не нашёл старую строку оверлея, пропущу")
    else:
        print("  > оверлей уже расширен или не найден")

    # ============================================================
    # 3. Добавить в оверлей preview последнего сообщения
    # ============================================================
    hr("3. Добавить preview последнего сообщения в оверлей")

    # Ищем в оверлее блок с last id
    old_last = 'last id=${messages.length ? messages[messages.length-1].id : "-"} '
    if old_last in text and "last text=" not in text:
        # Добавим ещё одну строку с текстом
        # Найдём конец оверлея и вставим перед закрывающей `}`
        idx = text.find('first id=${messages.length ? messages[0].id')
        if idx > 0:
            # Найдём закрытие template literal — `}`
            close_idx = text.find("}`", idx)
            if close_idx > 0:
                add = (
                    "\\n" +
                    "last visible text=${(() => { const last = allMessages[allMessages.length-1]; "
                    "if (!last) return '-'; "
                    "const dec = decrypted[last.id]; "
                    "return (dec !== undefined ? dec : last.text || '').slice(0, 40); })()}"
                )
                text = text[:close_idx] + add + text[close_idx:]
                print("  ✓ добавил 'last visible text=...' в оверлей")
            else:
                print("  > не нашёл закрытие оверлея")
        else:
            print("  > не нашёл 'first id' в оверлее")

    cw.write_text(text, encoding="utf-8")

    # ============================================================
    # 4. Пересборка
    # ============================================================
    hr("4. Пересборка frontend")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        print(out[-2000:])
        return 1
    print("  ✓ Собрано")

    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ up -d")

    hr("ЧТО ДЕЛАТЬ")
    print("""
  1. F12 → Network → Disable cache
  2. Ctrl+Shift+R
  3. Открой чат 2
  4. Посмотри правый нижний угол — теперь там будет БОЛЬШЕ строк:

       msgs=200 enc=200 dec=200
       queue=0 virtual=0        ← ВАЖНО! Если тут не 0 — ciphertext из очереди
       last id=1270 enc=true dec=YES
       first id=1064 enc=true dec=YES
       last visible text=хпукппку

  5. Отправь одно новое сообщение
  6. Смотри нижний угол — что там теперь?

  ПРИШЛИ МНЕ ВСЁ СОДЕРЖИМОЕ ОВЕРЛЕЯ (все 5 строк, скопируй как текст из картинки)
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())