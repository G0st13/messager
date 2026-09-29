#!/usr/bin/env python3
"""sprint15.py - add deus ex / gits / lain themes."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


THEMES_TS = r'''import type { ThemeName } from "./types";

export interface Theme {
  name: ThemeName;
  label: string;
  bodyClass: string;
  vars: Record<string, string>;
}

export const THEMES: Theme[] = [
  {
    name: "cyber",
    label: "◈ CYBER",
    bodyClass: "theme-cyber",
    vars: {
      "--neon-cyan": "#00f0ff",
      "--neon-magenta": "#ff00a0",
      "--neon-yellow": "#fcee0a",
      "--bg-deep": "#05070d",
      "--bg-panel": "#0a0f1a",
      "--bg-elev": "#0f1522",
      "--border": "#1a2537",
      "--text-primary": "#eaf4ff",
    },
  },
  {
    name: "matrix",
    label: "▶ MATRIX",
    bodyClass: "theme-matrix",
    vars: {
      "--neon-cyan": "#00ff41",
      "--neon-magenta": "#00cc33",
      "--neon-yellow": "#aaffaa",
      "--bg-deep": "#000600",
      "--bg-panel": "#001100",
      "--bg-elev": "#002200",
      "--border": "#003300",
      "--text-primary": "#88ff88",
    },
  },
  {
    name: "sunset",
    label: "☀ SUNSET",
    bodyClass: "theme-sunset",
    vars: {
      "--neon-cyan": "#ff6b35",
      "--neon-magenta": "#f7931e",
      "--neon-yellow": "#ffd23f",
      "--bg-deep": "#1a0d1a",
      "--bg-panel": "#26101f",
      "--bg-elev": "#331522",
      "--border": "#4d2030",
      "--text-primary": "#ffd6b8",
    },
  },
  {
    name: "amber",
    label: "◆ AMBER",
    bodyClass: "theme-amber",
    vars: {
      "--neon-cyan": "#ffb000",
      "--neon-magenta": "#ff7700",
      "--neon-yellow": "#ffcc00",
      "--bg-deep": "#0d0a05",
      "--bg-panel": "#1a1208",
      "--bg-elev": "#261a0c",
      "--border": "#3d2c14",
      "--text-primary": "#e8d4a8",
    },
  },
  {
    name: "deusex",
    label: "◈ DEUS EX",
    bodyClass: "theme-deusex",
    vars: {
      "--neon-cyan": "#f0b030",     // gold — main accent
      "--neon-magenta": "#e85a30",  // burnt orange
      "--neon-yellow": "#f7d060",   // bright amber
      "--bg-deep": "#08090d",       // near-black
      "--bg-panel": "#0f1218",
      "--bg-elev": "#161a22",
      "--border": "#2a3040",
      "--text-primary": "#e2d4b0",  // warm cream
    },
  },
  {
    name: "gits",
    label: "◉ GITS",
    bodyClass: "theme-gits",
    vars: {
      "--neon-cyan": "#00d9ff",     // bright cyan — Motoko's eyes
      "--neon-magenta": "#ff3355",  // clean red
      "--neon-yellow": "#ffaa00",   // warm signal
      "--bg-deep": "#030a12",
      "--bg-panel": "#06121c",
      "--bg-elev": "#0a1a26",
      "--border": "#12303f",
      "--text-primary": "#a8d8e8",
    },
  },
  {
    name: "lain",
    label: "◌ LAIN",
    bodyClass: "theme-lain",
    vars: {
      "--neon-cyan": "#c4304a",     // desaturated red
      "--neon-magenta": "#a05a8a",  // dusty pink-purple
      "--neon-yellow": "#d4a850",   // dim gold
      "--bg-deep": "#0e070e",       // dark purple-black
      "--bg-panel": "#180d18",
      "--bg-elev": "#221024",
      "--border": "#3a1a30",
      "--text-primary": "#d8c0c8",  // pinkish grey
    },
  },
];

export function applyTheme(name: ThemeName) {
  const theme = THEMES.find((t) => t.name === name) || THEMES[0];
  const root = document.documentElement;
  Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v));
  root.style.setProperty("--tw-cyber-cyan", theme.vars["--neon-cyan"]);

  // set body class for per-theme extras
  for (const t of THEMES) document.body.classList.remove(t.bodyClass);
  document.body.classList.add(theme.bodyClass);
}
'''


THEME_CSS = r'''
    /* ============================================================
       THEME EXTRAS — deus ex / gits / lain
       ============================================================ */

    /* ---------- DEUS EX ---------- */
    /* Золото + чёрный, индустриальный HUD */
    body.theme-deusex .cyber-bg::before {
      background-image:
        linear-gradient(rgba(240,176,48,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(240,176,48,0.04) 1px, transparent 1px);
      background-size: 48px 48px;
    }
    body.theme-deusex .cyber-bg::after {
      background:
        radial-gradient(ellipse at 20% 10%, rgba(240,176,48,0.10), transparent 45%),
        radial-gradient(ellipse at 80% 90%, rgba(232,90,48,0.08), transparent 45%);
    }
    body.theme-deusex .scanlines {
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(240,176,48,0.03) 3px,
        transparent 4px
      );
    }
    body.theme-deusex .chat-surface,
    body.theme-deusex .panel-solid,
    body.theme-deusex .cyberdeck-panel {
      background: #08090d;
    }
    body.theme-deusex .channel-icon {
      clip-path: polygon(
        0 5px, 5px 0,
        calc(100% - 5px) 0, 100% 5px,
        100% calc(100% - 5px), calc(100% - 5px) 100%,
        5px 100%, 0 calc(100% - 5px)
      );
      background: rgba(240,176,48,0.08);
      border-color: rgba(240,176,48,0.5);
    }
    body.theme-deusex .channel-card.active::before {
      background: #f0b030;
      box-shadow: 0 0 10px #f0b030, 0 0 20px rgba(240,176,48,0.6);
    }
    body.theme-deusex .neon-text {
      text-shadow: 0 0 6px rgba(240,176,48,0.7), 0 1px 2px rgba(0,0,0,0.9);
    }
    /* угловая метка DEUS EX в правом-нижнем углу */
    body.theme-deusex::after {
      content: "UNATCO // 2052";
      position: fixed;
      right: 12px;
      bottom: 10px;
      font-size: 9px;
      letter-spacing: 0.35em;
      color: rgba(240,176,48,0.45);
      pointer-events: none;
      z-index: 5;
      text-shadow: 0 0 4px rgba(240,176,48,0.4);
    }

    /* ---------- GHOST IN THE SHELL ---------- */
    /* Чистота + плотность, японские иероглифы */
    body.theme-gits .cyber-bg::before {
      background-image:
        linear-gradient(rgba(0,217,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,217,255,0.04) 1px, transparent 1px);
      background-size: 32px 32px;
      animation: grid-drift 50s linear infinite;
    }
    body.theme-gits .cyber-bg::after {
      background:
        radial-gradient(ellipse at 75% 20%, rgba(0,217,255,0.10), transparent 40%),
        radial-gradient(ellipse at 25% 85%, rgba(255,51,85,0.06), transparent 45%);
    }
    body.theme-gits .chat-surface,
    body.theme-gits .panel-solid,
    body.theme-gits .cyberdeck-panel {
      background: #030a12;
    }
    body.theme-gits .channel-icon {
      background: rgba(0,217,255,0.08);
      border-color: rgba(0,217,255,0.55);
      clip-path: polygon(
        0 0,
        calc(100% - 8px) 0, 100% 8px,
        100% 100%,
        8px 100%, 0 calc(100% - 8px)
      );
    }
    body.theme-gits .channel-card {
      background: rgba(3,10,18,0.75);
      border-color: rgba(0,217,255,0.18);
    }
    body.theme-gits .channel-card.active {
      background: linear-gradient(135deg, rgba(255,51,85,0.08), rgba(0,217,255,0.06));
      border-color: #ff3355;
    }
    body.theme-gits .channel-card.active::before {
      background: #ff3355;
      box-shadow: 0 0 10px #ff3355;
    }
    body.theme-gits .channel-card.active .channel-card-name {
      color: #ff3355;
      text-shadow: 0 0 8px rgba(255,51,85,0.75);
    }
    /* вертиклаьная японская метка */
    body.theme-gits::after {
      content: "公安9課";
      position: fixed;
      left: 6px;
      top: 50%;
      transform: translateY(-50%);
      writing-mode: vertical-rl;
      font-size: 14px;
      letter-spacing: 0.4em;
      color: rgba(0,217,255,0.35);
      pointer-events: none;
      z-index: 5;
      text-shadow: 0 0 6px rgba(0,217,255,0.5);
    }
    /* вторая метка справа */
    body.theme-gits::before {
      content: "SECTION 9";
      position: fixed;
      right: 8px;
      top: 50%;
      transform: translateY(-50%) rotate(90deg);
      font-size: 9px;
      letter-spacing: 0.5em;
      color: rgba(255,51,85,0.35);
      pointer-events: none;
      z-index: 5;
    }
    /* тонкие оранжевые засечки по краям экрана (HUD-рамка) */
    body.theme-gits .chat-surface {
      box-shadow:
        inset 2px 0 0 rgba(255,51,85,0.15),
        inset -2px 0 0 rgba(0,217,255,0.15);
    }

    /* ---------- LAIN ---------- */
    /* VHS-полосы, десатурация, «present day, present time» */
    body.theme-lain .cyber-bg::before {
      background-image:
        linear-gradient(rgba(196,48,74,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(196,48,74,0.04) 1px, transparent 1px);
      background-size: 56px 56px;
      opacity: 0.7;
      animation: grid-drift 90s linear infinite;
    }
    body.theme-lain .cyber-bg::after {
      background:
        radial-gradient(ellipse at 50% 50%, rgba(160,90,138,0.06), transparent 55%),
        radial-gradient(ellipse at 10% 90%, rgba(196,48,74,0.10), transparent 45%),
        radial-gradient(ellipse at 90% 10%, rgba(100,60,120,0.08), transparent 45%);
    }
    body.theme-lain .scanlines {
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(196,48,74,0.02) 3px,
        transparent 5px
      );
      opacity: 0.85;
    }
    body.theme-lain .chat-surface,
    body.theme-lain .panel-solid,
    body.theme-lain .cyberdeck-panel {
      background: #0e070e;
    }
    /* VHS-разрыв — одна тонкая полоса, медленно ползёт вниз */
    body.theme-lain .cyber-bg::after {
      animation: vhs-tracking 12s linear infinite;
    }
    @keyframes vhs-tracking {
      0%   { transform: translateY(-15%); }
      100% { transform: translateY(115%); }
    }
    /* дополнительная шумовая полоса */
    body.theme-lain .scan-beam {
      background: linear-gradient(180deg, transparent, rgba(196,48,74,0.10), transparent);
      opacity: 0.9;
      animation-duration: 5s;
    }
    body.theme-lain .channel-icon {
      background: rgba(196,48,74,0.08);
      border-color: rgba(196,48,74,0.5);
      filter: saturate(0.7);
    }
    body.theme-lain .channel-card {
      filter: saturate(0.85);
    }
    body.theme-lain .channel-card.active {
      background: linear-gradient(135deg, rgba(196,48,74,0.14), rgba(160,90,138,0.06));
      border-color: #c4304a;
    }
    body.theme-lain .channel-card.active::before {
      background: #c4304a;
      box-shadow: 0 0 12px #c4304a, 0 0 24px rgba(196,48,74,0.5);
    }
    body.theme-lain .channel-card.active .channel-card-name {
      color: #c4304a;
      text-shadow: 0 0 10px rgba(196,48,74,0.8);
    }
    body.theme-lain .neon-text {
      color: #c4304a;
      text-shadow: 0 0 8px rgba(196,48,74,0.7), 0 1px 2px rgba(0,0,0,0.9);
    }
    /* «present day, present time» — в правом-верхнем углу, мелко */
    body.theme-lain::after {
      content: "present day";
      position: fixed;
      right: 12px;
      top: 12px;
      font-size: 9px;
      letter-spacing: 0.5em;
      color: rgba(216,192,200,0.5);
      pointer-events: none;
      z-index: 5;
      animation: lain-flicker 4s infinite;
    }
    body.theme-lain::before {
      content: "present time";
      position: fixed;
      right: 12px;
      top: 26px;
      font-size: 9px;
      letter-spacing: 0.5em;
      color: rgba(216,192,200,0.4);
      pointer-events: none;
      z-index: 5;
      animation: lain-flicker 4s 0.5s infinite;
    }
    @keyframes lain-flicker {
      0%,90%,100% { opacity: 0.6; }
      92% { opacity: 0.1; }
      94% { opacity: 0.6; }
      96% { opacity: 0.2; }
      98% { opacity: 0.6; }
    }
'''


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    src = root / "frontend" / "src"

    print("\nСпринт 15 — темы deus ex / gits / lain\n")

    # 1) themes.ts — перезаписываем
    (src / "themes.ts").write_text(THEMES_TS, encoding="utf-8")
    print(f"  ~ {src / 'themes.ts'}")

    # 2) types.ts — расширяем ThemeName
    types_path = src / "types.ts"
    types_text = types_path.read_text(encoding="utf-8")
    old = 'export type ThemeName = "cyber" | "matrix" | "sunset" | "amber";'
    new = 'export type ThemeName = "cyber" | "matrix" | "sunset" | "amber" | "deusex" | "gits" | "lain";'
    if old in types_text:
        types_text = types_text.replace(old, new, 1)
        types_path.write_text(types_text, encoding="utf-8")
        print(f"  ~ {types_path}")
    else:
        print(f"  > {types_path} (уже пропатчено или не найдено)")

    # 3) index.css — добавляем theme-extras
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "THEME EXTRAS" not in css_text:
        css_text = css_text.rstrip() + "\n" + THEME_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path} (тема-экстры добавлены)")
    else:
        print(f"  > {css_path} (уже пропатчено)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Переключение темы: ⚙ → вкладка THEME или Ctrl+K → 'theme'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())