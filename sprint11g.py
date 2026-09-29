#!/usr/bin/env python3
"""sprint11g.py - fix dark purple screen in chat."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


CSS_REPLACEMENTS = [
    # 1. chat-surface — 100% непрозрачный, без всяких фильтров
    (
        '    .chat-surface {\n'
        '      background: rgb(6, 9, 15);\n'
        '    }',
        '    .chat-surface {\n'
        '      background: #0a0f1a;\n'
        '      background-image: none;\n'
        '    }',
    ),
    # 2. city-very-dimmed — только opacity, без filter (фильтр даёт фиолетовый из-за smog)
    (
        '    .city-very-dimmed {\n'
        '      opacity: 0.28;\n'
        '      filter: saturate(0.45) brightness(0.5);\n'
        '      transition: opacity 0.3s, filter 0.3s;\n'
        '      contain: strict;\n'
        '    }',
        '    .city-very-dimmed {\n'
        '      opacity: 0.22;\n'
        '      transition: opacity 0.3s;\n'
        '      contain: strict;\n'
        '    }',
    ),
    # 3. city-dimmed — тоже без filter
    (
        '    .city-dimmed {\n'
        '      opacity: 0.55;\n'
        '      filter: saturate(0.7) brightness(0.75);\n'
        '      transition: opacity 0.3s, filter 0.3s;\n'
        '      contain: strict;\n'
        '    }',
        '    .city-dimmed {\n'
        '      opacity: 0.6;\n'
        '      transition: opacity 0.3s;\n'
        '      contain: strict;\n'
        '    }',
    ),
    # 4. scanlines — убираем mix-blend-mode screen (он подмешивает цвета фона)
    (
        '    .scanlines {\n'
        '      position: absolute;\n'
        '      inset: 0;\n'
        '      pointer-events: none;\n'
        '      background: repeating-linear-gradient(\n'
        '        0deg,\n'
        '        transparent 0,\n'
        '        transparent 3px,\n'
        '        rgba(0,240,255,0.015) 4px,\n'
        '        transparent 5px\n'
        '      );\n'
        '      opacity: 0.6;\n'
        '      contain: strict;\n'
        '    }',
        '    .scanlines {\n'
        '      position: absolute;\n'
        '      inset: 0;\n'
        '      pointer-events: none;\n'
        '      background: repeating-linear-gradient(\n'
        '        0deg,\n'
        '        transparent 0,\n'
        '        transparent 3px,\n'
        '        rgba(0,240,255,0.012) 4px,\n'
        '        transparent 5px\n'
        '      );\n'
        '      opacity: 0.5;\n'
        '      contain: strict;\n'
        '    }',
    ),
    # 5. cyber-bg ::after — мягче градиенты, чтобы не складывались в фиолетовый
    (
        '    .cyber-bg::after {\n'
        '      content: "";\n'
        '      position: absolute;\n'
        '      inset: 0;\n'
        '      background:\n'
        '        radial-gradient(ellipse at 20% 10%, rgba(255,0,160,0.10), transparent 40%),\n'
        '        radial-gradient(ellipse at 80% 90%, rgba(0,240,255,0.10), transparent 40%);\n'
        '      pointer-events: none;\n'
        '    }',
        '    .cyber-bg::after {\n'
        '      content: "";\n'
        '      position: absolute;\n'
        '      inset: 0;\n'
        '      background:\n'
        '        radial-gradient(ellipse at 20% 10%, rgba(255,0,160,0.06), transparent 45%),\n'
        '        radial-gradient(ellipse at 80% 90%, rgba(0,240,255,0.06), transparent 45%);\n'
        '      pointer-events: none;\n'
        '      opacity: 0.8;\n'
        '    }',
    ),
    # 6. При открытом чате — cyber-bg становится еле заметным
    (
        '    body.scrolling .cyber-bg,\n'
        '    body.scrolling .scanlines {\n'
        '      opacity: 0.4;\n'
        '    }',
        '    body.scrolling .cyber-bg,\n'
        '    body.scrolling .scanlines {\n'
        '      opacity: 0.4;\n'
        '    }\n'
        '\n'
        '    /* При открытом чате фон-грид сильно приглушается, чтобы не мешать */\n'
        '    body.chat-open .cyber-bg::before {\n'
        '      opacity: 0.25;\n'
        '    }\n'
        '    body.chat-open .cyber-bg::after {\n'
        '      opacity: 0.35;\n'
        '    }',
    ),
]


# PixelCity — смягчаем smog, он был слишком фиолетовым
PIXELCITY_REPLACEMENTS = [
    (
        '      } else if (effective === "smog") {\n'
        '        ctx.fillStyle = "rgba(90, 40, 110, 0.12)";\n'
        '        ctx.fillRect(0, 0, W, H);\n'
        '        ctx.fillStyle = "rgba(180, 80, 60, 0.06)";\n'
        '        ctx.fillRect(0, Math.floor(H * 0.4), W, Math.floor(H * 0.6));\n'
        '      }',
        '      } else if (effective === "smog") {\n'
        '        // мягкая оранжево-серая дымка, без выраженного фиолетового\n'
        '        ctx.fillStyle = "rgba(70, 60, 80, 0.10)";\n'
        '        ctx.fillRect(0, 0, W, H);\n'
        '        ctx.fillStyle = "rgba(140, 90, 70, 0.05)";\n'
        '        ctx.fillRect(0, Math.floor(H * 0.4), W, Math.floor(H * 0.6));\n'
        '      }',
    ),
]


# App — ставим/снимаем body.chat-open
APP_REPLACEMENTS = [
    (
        '      useScrolling();',
        '      useScrolling();\n'
        '\n'
        '      // помечаем body, когда открыт чат — чтобы приглушить фон\n'
        '      useEffect(() => {\n'
        '        if (activeChatId !== null) document.body.classList.add("chat-open");\n'
        '        else document.body.classList.remove("chat-open");\n'
        '        return () => document.body.classList.remove("chat-open");\n'
        '      }, [activeChatId]);',
    ),
]


def patch_file(path: Path, pairs: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path}")
    else:
        print(f"  > {path} (без изменений)")
    return changed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 11g — фикс тёмнофиолетового экрана\n")

    src = root / "frontend" / "src"

    patch_file(src / "index.css", CSS_REPLACEMENTS)
    patch_file(src / "PixelCity.tsx", PIXELCITY_REPLACEMENTS)
    patch_file(src / "App.tsx", APP_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())