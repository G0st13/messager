#!/usr/bin/env python3
"""e2e_nuclear.py - смотрит бандл внутри контейнера + патчит рендер + пересобирает."""
from __future__ import annotations

import argparse
import hashlib
import subprocess
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
    # 1. Хеш исходника
    # ============================================================
    hr("1. ЧТО В ИСХОДНИКЕ ChatWindow.tsx")

    text = cw.read_text(encoding="utf-8")
    h = hashlib.md5(text.encode()).hexdigest()
    print(f"  md5: {h}")
    print(f"  размер: {len(text)} байт")
    print(f"  'decrypted[m.id]' встречается: {text.count('decrypted[m.id]')}")
    print(f"  'render msg' встречается: {text.count('render msg')}")
    print(f"  'WS message' встречается: {text.count('WS message')}")

    # ============================================================
    # 2. Что в контейнере frontend прямо сейчас
    # ============================================================
    hr("2. ЧТО В КОНТЕЙНЕРЕ FRONTEND (assets/*.js)")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "frontend",
                     "ls", "-la", "/usr/share/nginx/html/assets/"], cwd=root)
    if code != 0:
        print("  (не могу зайти в контейнер frontend)")
        print(out[:500])
    else:
        print(out)

    # Хеши бандлов (grep по маркеру)
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "frontend",
                     "sh", "-c",
                     "for f in /usr/share/nginx/html/assets/index-*.js; do "
                     "echo '---' $f; "
                     "grep -o 'render msg\\|WS message\\|decrypted\\[m.id\\]' $f | sort | uniq -c; "
                     "done"], cwd=root)
    print("  Маркеры в бандлах:")
    print(out)

    # ============================================================
    # 3. Патчим блок рендера (заменяем точный текст)
    # ============================================================
    hr("3. ПАТЧ — заменяю блок <MessageBubble msg=...>")

    old_render = '''                    <MessageBubble
                      msg={
                        m.encrypted && decrypted[m.id] !== undefined
                          ? { ...m, text: decrypted[m.id], encrypted: false }
                          : m
                      }
                      mine={m.author_id === currentUser.id}'''

    new_render = '''                    {(() => {
                      const hasDec = m.encrypted && decrypted[m.id] !== undefined;
                      if (m.encrypted) {
                        console.log("[E2E-TRACE] RENDER id=" + m.id +
                          " hasDec=" + hasDec +
                          " text=" + String(m.text).slice(0, 20));
                      }
                      return null;
                    })()}
                    <MessageBubble
                      msg={
                        m.encrypted && decrypted[m.id] !== undefined
                          ? { ...m, text: decrypted[m.id], encrypted: false }
                          : m
                      }
                      mine={m.author_id === currentUser.id}'''

    if "RENDER id=" in text:
        print("  > патч рендера уже применён")
    elif old_render in text:
        text = text.replace(old_render, new_render, 1)
        cw.write_text(text, encoding="utf-8")
        print("  ✓ блок рендера пропатчен (добавлен лог RENDER id=...)")
    else:
        print("  ✗ не нашёл блок рендера — пришли мне строки 568-580 из ChatWindow.tsx")
        return 1

    # ============================================================
    # 4. Пересборка
    # ============================================================
    hr("4. ПЕРЕСБОРКА FRONTEND")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        print(out[-2000:])
        return 1
    print("  ✓ Собрано")

    run(["docker", "compose", "-f", str(compose), "up", "-d"], cwd=root, timeout=120)
    print("  ✓ up -d")

    # ============================================================
    # 5. Снова смотрим что теперь в контейнере
    # ============================================================
    hr("5. ЧТО В КОНТЕЙНЕРЕ ПОСЛЕ ПЕРЕСБОРКИ")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "frontend",
                     "ls", "-la", "/usr/share/nginx/html/assets/"], cwd=root)
    print(out)

    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "frontend",
                     "sh", "-c",
                     "for f in /usr/share/nginx/html/assets/index-*.js; do "
                     "echo '---' $f; "
                     "grep -o 'render msg\\|WS message\\|RENDER id=\\|decrypted\\[m.id\\]' $f | sort | uniq -c; "
                     "done"], cwd=root)
    print("  Маркеры в бандлах:")
    print(out)

    # ============================================================
    # 6. Что делать
    # ============================================================
    hr("ЧТО ДЕЛАТЬ В БРАУЗЕРЕ")
    print("""
  1. F12 → Network → включи Disable cache (галочка сверху)
  2. Ctrl+Shift+R (жёсткое)
  3. Открой чат 2
  4. Смотри Console — теперь должны появляться строки:
       [E2E-TRACE] RENDER id=XXX hasDec=TRUE/FALSE text=...
  5. Пришли мне ВСЕ строки [E2E-TRACE] RENDER

  Если RENDER id=XXX hasDec=FALSE — значит расшифровка для этого id ещё не готова.
  Если RENDER id=XXX hasDec=TRUE — значит расшифровано, но по какой-то причине в UI всё равно шифртекст.
  Если RENDER вообще нет — значит бандл опять не подхватился.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())