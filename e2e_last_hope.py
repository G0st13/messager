#!/usr/bin/env python3
"""e2e_last_hope.py - упрощает рендер + добавляет debug-оверлей в чат."""
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
    # 1. Заменить условие в рендере
    # ============================================================
    hr("1. Патч — упрощаю условие подстановки")

    old_cond = "m.encrypted && decrypted[m.id] !== undefined"
    new_cond = "decrypted[m.id] !== undefined"
    cnt = text.count(old_cond)
    print(f"  Найдено вхождений: {cnt}")

    if cnt > 0:
        text = text.replace(old_cond, new_cond)
        print(f"  ✓ заменил '{old_cond}' на '{new_cond}' во всех местах")
    else:
        print("  > уже заменено или не найдено")

    # ============================================================
    # 2. Добавить debug-оверлей перед </main>
    # ============================================================
    hr("2. Патч — debug-оверлей в чат")

    if "E2E-DEBUG-OVERLAY" in text:
        print("  > оверлей уже добавлен")
    else:
        # ищем закрывающий </main> (последний в файле)
        overlay = '''
      {/* E2E-DEBUG-OVERLAY */}
      <div
        style={{
          position: "absolute", bottom: 8, right: 8, zIndex: 5,
          background: "rgba(0,0,0,0.8)", color: "#0ff",
          fontFamily: "monospace", fontSize: 10, lineHeight: 1.4,
          padding: "6px 8px", border: "1px solid #0ff",
          pointerEvents: "none", whiteSpace: "pre",
        }}
      >
        {`msgs=${messages.length} enc=${messages.filter(m => m.encrypted).length} dec=${Object.keys(decrypted).length}\\n` +
         `last id=${messages.length ? messages[messages.length-1].id : "-"} ` +
         `enc=${messages.length ? String(messages[messages.length-1].encrypted) : "-"} ` +
         `dec=${messages.length && decrypted[messages[messages.length-1].id] !== undefined ? "YES" : "NO"}\\n` +
         `first id=${messages.length ? messages[0].id : "-"} ` +
         `enc=${messages.length ? String(messages[0].encrypted) : "-"} ` +
         `dec=${messages.length && decrypted[messages[0].id] !== undefined ? "YES" : "NO"}`}
      </div>
'''
        # вставляем перед последним </main>
        idx = text.rfind("</main>")
        if idx == -1:
            print("  ✗ не нашёл </main> в файле")
            return 1
        text = text[:idx] + overlay + "\n    " + text[idx:]
        print("  ✓ оверлей добавлен перед </main>")

    cw.write_text(text, encoding="utf-8")

    # ============================================================
    # 3. Пересборка
    # ============================================================
    hr("3. Пересборка frontend")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        print(out[-2000:])
        return 1
    print("  ✓ Собрано")

    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ up -d")

    # Проверим что в контейнере
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "frontend",
                     "ls", "/usr/share/nginx/html/assets/"], cwd=root)
    print("\n  Файлы в контейнере:")
    print("    " + out.strip().replace("\n", "\n    "))

    hr("ЧТО ДЕЛАТЬ")
    print("""
  1. F12 → Network → галочка Disable cache
  2. Ctrl+Shift+R (жёсткое)
  3. Открой чат 2
  4. В ПРАВОМ НИЖНЕМ УГЛУ ЧАТА появится чёрный ящик с цифрами.
     Скопируй мне его содержимое — это 3 строки:

       msgs=200 enc=200 dec=200
       last id=1181 enc=true dec=YES
       first id=980 enc=true dec=YES

     (цифры могут быть другие — мне нужны именно твои)
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())