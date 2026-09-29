#!/usr/bin/env python3
"""add_favicon.py - создаёт favicon.svg + robots.txt + патчит index.html."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


FAVICON_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="#05070d"/>
  <rect x="4" y="4" width="56" height="56" fill="none" stroke="#00f0ff" stroke-width="2"/>
  <text x="32" y="46" text-anchor="middle"
        font-family="JetBrains Mono, monospace"
        font-size="40"
        font-weight="700"
        fill="#00f0ff">&#9672;</text>
</svg>
'''

ROBOTS_TXT = """User-agent: *
Disallow: /
"""

MANIFEST_JSON = '''{
  "name": "Messenger",
  "short_name": "MSG",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#05070d",
  "theme_color": "#00f0ff",
  "icons": [
    { "src": "/favicon.svg", "sizes": "any", "type": "image/svg+xml" }
  ]
}
'''


def create_backup(root: Path) -> Path | None:
    index = root / "frontend" / "index.html"
    if not index.exists():
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    dst = b / "frontend" / "index.html"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(index, dst)
    print(f"\n📦 Бэкап: {b}")
    return b


def patch_index_html(path: Path) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False

    text = path.read_text(encoding="utf-8")

    # если уже есть favicon-link — не дублируем
    if 'rel="icon"' in text and 'favicon.svg' in text:
        print(f"  > {path.name} (favicon уже подключён)")
        return False

    # вставляем блок прямо перед </head>
    inject = (
        '    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />\n'
        '    <link rel="alternate icon" href="/favicon.svg" />\n'
        '    <link rel="manifest" href="/manifest.json" />\n'
        '    <meta name="theme-color" content="#05070d" />\n'
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />\n'
    )

    # убираем старый viewport если он есть (мы вставляем свой)
    for old_vp in [
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    ]:
        if old_vp in text:
            text = text.replace(old_vp, "", 1)
            break

    if "</head>" in text:
        text = text.replace("</head>", inject + "  </head>", 1)
    else:
        # вставляем после <head>
        text = text.replace("<head>", "<head>\n" + inject, 1)

    path.write_text(text, encoding="utf-8")
    print(f"  ~ {path.name} (добавлены favicon + manifest + theme-color)")
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-backup", action="store_true")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    fe = root / "frontend"
    if not fe.exists():
        print(f"ERR: {fe} не найдено", file=sys.stderr)
        return 1

    if not args.no_backup:
        create_backup(root)

    print("\nСоздаю файлы:")
    public = fe / "public"
    public.mkdir(parents=True, exist_ok=True)

    files = {
        public / "favicon.svg": FAVICON_SVG,
        public / "robots.txt": ROBOTS_TXT,
        public / "manifest.json": MANIFEST_JSON,
    }
    for path, content in files.items():
        existed = path.exists()
        path.write_text(content, encoding="utf-8")
        print(f"  {'~' if existed else '+'} frontend/public/{path.name}")

    print("\nПатчу index.html:")
    patch_index_html(fe / "index.html")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("Проверка:")
    print("  • favicon появится во вкладке браузера")
    print("  • F12 → Network → больше нет 404 на /favicon.ico")
    print("  • F12 → Application → Manifest покажет 'Messenger'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())