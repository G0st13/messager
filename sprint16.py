#!/usr/bin/env python3
"""sprint16.py - full visual identity per theme (shapes, not just colors)."""
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
      "--radius-sm": "0px",
      "--radius-md": "0px",
      "--radius-lg": "0px",
      "--font-family": "JetBrains Mono, Fira Code, Consolas, monospace",
      "--font-tracking": "0.02em",
      "--border-width": "1px",
      "--shadow-glow": "0 0 12px",
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
      "--radius-sm": "0px",
      "--radius-md": "0px",
      "--radius-lg": "0px",
      "--font-family": "JetBrains Mono, Fira Code, Consolas, monospace",
      "--font-tracking": "0.08em",
      "--border-width": "1px",
      "--shadow-glow": "0 0 6px",
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
      "--radius-sm": "8px",
      "--radius-md": "14px",
      "--radius-lg": "20px",
      "--font-family": "system-ui, -apple-system, Segoe UI, sans-serif",
      "--font-tracking": "0em",
      "--border-width": "1px",
      "--shadow-glow": "0 4px 20px",
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
      "--radius-sm": "12px",
      "--radius-md": "18px",
      "--radius-lg": "24px",
      "--font-family": "JetBrains Mono, Consolas, monospace",
      "--font-tracking": "0.05em",
      "--border-width": "2px",
      "--shadow-glow": "0 0 20px",
    },
  },
  {
    name: "deusex",
    label: "◈ DEUS EX",
    bodyClass: "theme-deusex",
    vars: {
      "--neon-cyan": "#f0b030",
      "--neon-magenta": "#e85a30",
      "--neon-yellow": "#f7d060",
      "--bg-deep": "#08090d",
      "--bg-panel": "#0f1218",
      "--bg-elev": "#161a22",
      "--border": "#2a3040",
      "--text-primary": "#e2d4b0",
      "--radius-sm": "2px",
      "--radius-md": "3px",
      "--radius-lg": "4px",
      "--font-family": "Rajdhani, Eurostile, JetBrains Mono, sans-serif",
      "--font-tracking": "0.06em",
      "--border-width": "1px",
      "--shadow-glow": "0 0 14px",
    },
  },
  {
    name: "gits",
    label: "◉ GITS",
    bodyClass: "theme-gits",
    vars: {
      "--neon-cyan": "#00d9ff",
      "--neon-magenta": "#ff3355",
      "--neon-yellow": "#ffaa00",
      "--bg-deep": "#030a12",
      "--bg-panel": "#06121c",
      "--bg-elev": "#0a1a26",
      "--border": "#12303f",
      "--text-primary": "#a8d8e8",
      "--radius-sm": "0px",
      "--radius-md": "2px",
      "--radius-lg": "3px",
      "--font-family": "JetBrains Mono, Consolas, monospace",
      "--font-tracking": "0.04em",
      "--border-width": "1px",
      "--shadow-glow": "0 0 8px",
    },
  },
  {
    name: "lain",
    label: "◌ LAIN",
    bodyClass: "theme-lain",
    vars: {
      "--neon-cyan": "#c4304a",
      "--neon-magenta": "#a05a8a",
      "--neon-yellow": "#d4a850",
      "--bg-deep": "#0e070e",
      "--bg-panel": "#180d18",
      "--bg-elev": "#221024",
      "--border": "#3a1a30",
      "--text-primary": "#d8c0c8",
      "--radius-sm": "6px 0 6px 0",
      "--radius-md": "10px 0 10px 0",
      "--radius-lg": "14px 0 14px 0",
      "--font-family": "JetBrains Mono, Consolas, monospace",
      "--font-tracking": "0.03em",
      "--border-width": "1px",
      "--shadow-glow": "0 0 12px",
    },
  },
];

export function applyTheme(name: ThemeName) {
  const theme = THEMES.find((t) => t.name === name) || THEMES[0];
  const root = document.documentElement;
  Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v));
  root.style.setProperty("--tw-cyber-cyan", theme.vars["--neon-cyan"]);

  for (const t of THEMES) document.body.classList.remove(t.bodyClass);
  document.body.classList.add(theme.bodyClass);
}
'''


THEME_VISUAL_CSS = r'''
    /* ============================================================
       THEME VISUAL IDENTITY — форма, а не только цвет
       ============================================================ */

    /* Применяем переменные к базовым элементам */
    body {
      font-family: var(--font-family, "JetBrains Mono", monospace);
      letter-spacing: var(--font-tracking, 0.02em);
    }
    .cyber-btn,
    .cyber-input,
    .channel-card,
    .channel-icon,
    .cyberdeck-search,
    .cyberdeck-icon-btn,
    .cyberdeck-tab {
      font-family: var(--font-family, "JetBrains Mono", monospace);
      letter-spacing: var(--font-tracking, 0.02em);
    }

    /* Базовые закругления — берём из переменных */
    .cyber-btn {
      border-radius: var(--radius-sm, 0);
    }
    .cyber-input {
      border-radius: var(--radius-sm, 0);
    }
    .cyberdeck-search {
      border-radius: var(--radius-sm, 0);
    }
    .cyberdeck-icon-btn {
      border-radius: var(--radius-sm, 0);
    }
    .channel-icon {
      border-radius: var(--radius-sm, 0);
    }
    .channel-card {
      border-radius: var(--radius-md, 0);
    }

    /* ============================================================
       MATRIX — монолитный CRT-терминал
       ============================================================ */
    body.theme-matrix .channel-card,
    body.theme-matrix .channel-icon,
    body.theme-matrix .cyber-btn,
    body.theme-matrix .cyber-input,
    body.theme-matrix .cyberdeck-search {
      clip-path: none !important;
      border-radius: 0 !important;
      border-width: 1px !important;
    }
    body.theme-matrix .channel-card {
      border-left-width: 3px !important;
      background: rgba(0,17,0,0.7) !important;
    }
    body.theme-matrix .channel-card:hover {
      background: rgba(0,50,0,0.5) !important;
      border-color: #00ff41 !important;
    }
    body.theme-matrix .channel-card.active {
      background: rgba(0,80,0,0.35) !important;
      border-color: #00ff41 !important;
      box-shadow: inset 0 0 0 1px #00ff41, 0 0 20px rgba(0,255,65,0.4) !important;
    }
    body.theme-matrix .channel-card.active::before {
      display: none !important;
    }
    /* CRT мерцание на границах */
    body.theme-matrix .channel-icon {
      background: rgba(0,50,0,0.6) !important;
      border-color: #00ff41 !important;
      color: #88ff88 !important;
    }
    /* мигающие точки по краям сообщений */
    body.theme-matrix .msg-scroll::-webkit-scrollbar-thumb {
      background: #00ff41;
    }
    /* Значок «терминал» в углу */
    body.theme-matrix::after {
      content: "> _";
      position: fixed;
      right: 14px;
      bottom: 12px;
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
      color: #00ff41;
      text-shadow: 0 0 6px #00ff41;
      pointer-events: none;
      z-index: 6;
      animation: matrix-blink 1.2s step-end infinite;
    }
    @keyframes matrix-blink { 50% { opacity: 0; } }

    /* ============================================================
       SUNSET — мягкий плавающий vaporwave
       ============================================================ */
    body.theme-sunset .channel-card,
    body.theme-sunset .channel-icon,
    body.theme-sunset .cyber-btn,
    body.theme-sunset .cyber-input,
    body.theme-sunset .cyberdeck-search,
    body.theme-sunset .cyberdeck-icon-btn {
      clip-path: none !important;
      border-radius: var(--radius-lg) !important;
    }
    body.theme-sunset .channel-icon {
      border-radius: 50% !important;
      background: linear-gradient(135deg, rgba(255,107,53,0.18), rgba(247,147,30,0.10)) !important;
      border-color: rgba(255,107,53,0.55) !important;
      box-shadow: 0 4px 16px rgba(255,107,53,0.3) !important;
    }
    body.theme-sunset .channel-card {
      background: linear-gradient(135deg, rgba(255,107,53,0.06), rgba(247,147,30,0.03)) !important;
      border-color: rgba(255,107,53,0.25) !important;
      box-shadow: 0 2px 12px rgba(0,0,0,0.3) !important;
      margin: 5px 8px !important;
    }
    body.theme-sunset .channel-card:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 20px rgba(255,107,53,0.35) !important;
      border-color: rgba(255,107,53,0.6) !important;
    }
    body.theme-sunset .channel-card.active {
      background: linear-gradient(135deg, rgba(255,107,53,0.18), rgba(247,147,30,0.10)) !important;
      border-color: #ff6b35 !important;
      box-shadow: 0 6px 24px rgba(255,107,53,0.5) !important;
    }
    body.theme-sunset .channel-card.active::before {
      display: none;
    }
    body.theme-sunset .cyber-btn {
      border-radius: 999px !important;
      padding: 8px 20px !important;
    }
    body.theme-sunset .cyber-input,
    body.theme-sunset .cyberdeck-search {
      border-radius: 999px !important;
      padding-left: 16px;
      padding-right: 16px;
    }
    body.theme-sunset .cyberdeck-icon-btn {
      border-radius: 50% !important;
    }
    /* Солнечный ореол в углу экрана */
    body.theme-sunset::after {
      content: "";
      position: fixed;
      right: -100px;
      top: -100px;
      width: 400px;
      height: 400px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(255,107,53,0.15), transparent 70%);
      pointer-events: none;
      z-index: 1;
    }

    /* ============================================================
       AMBER — выпуклая ЭЛТ-панель
       ============================================================ */
    body.theme-amber .channel-card,
    body.theme-amber .channel-icon,
    body.theme-amber .cyber-btn,
    body.theme-amber .cyber-input {
      clip-path: none !important;
    }
    /* Главная фишка: панель выглядит как изогнутый экран */
    body.theme-amber .cyberdeck-panel {
      border-radius: 20px 20px 0 0 !important;
      box-shadow:
        inset 0 20px 40px rgba(255,176,0,0.06),
        inset 0 -20px 40px rgba(0,0,0,0.6),
        0 0 40px rgba(255,176,0,0.15) !important;
    }
    body.theme-amber .channel-card {
      border-radius: 14px !important;
      background: linear-gradient(180deg, rgba(255,176,0,0.05), rgba(255,119,0,0.02)) !important;
      border-width: 2px !important;
      border-color: rgba(255,176,0,0.3) !important;
    }
    body.theme-amber .channel-card.active {
      border-color: #ffb000 !important;
      background: linear-gradient(180deg, rgba(255,176,0,0.18), rgba(255,119,0,0.06)) !important;
      box-shadow: 0 0 24px rgba(255,176,0,0.5), inset 0 0 20px rgba(255,176,0,0.15) !important;
    }
    body.theme-amber .channel-card.active::before {
      display: none;
    }
    body.theme-amber .channel-icon {
      border-radius: 50% !important;
      border-width: 2px !important;
      box-shadow: 0 0 16px rgba(255,176,0,0.4), inset 0 0 12px rgba(255,176,0,0.2) !important;
    }
    body.theme-amber .cyber-btn,
    body.theme-amber .cyber-input {
      border-radius: 12px !important;
      border-width: 2px !important;
    }
    /* CRT полосы поверх всей панели */
    body.theme-amber .cyberdeck-panel::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(255,176,0,0.04) 3px,
        transparent 4px
      );
      border-radius: 20px 20px 0 0;
    }
    /* Тёплое свечение вокруг всего */
    body.theme-amber::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background: radial-gradient(ellipse at center, rgba(255,176,0,0.04), transparent 60%);
      z-index: 1;
    }

    /* ============================================================
       DEUS EX — военный угловатый HUD
       ============================================================ */
    /* Иконки — ромбы (сжатые по горизонтали) */
    body.theme-deusex .channel-icon {
      clip-path: polygon(
        8px 0,
        calc(100% - 8px) 0,
        100% 50%,
        calc(100% - 8px) 100%,
        8px 100%,
        0 50%
      ) !important;
      border-radius: 0 !important;
      background: rgba(240,176,48,0.08) !important;
      border: 1px solid rgba(240,176,48,0.55) !important;
      padding: 0 6px;
    }
    /* Карточки — углы срезаны по-военному */
    body.theme-deusex .channel-card {
      clip-path: polygon(
        0 0,
        calc(100% - 12px) 0,
        100% 12px,
        100% 100%,
        12px 100%,
        0 calc(100% - 12px)
      ) !important;
      border-radius: 0 !important;
      border-color: rgba(240,176,48,0.35) !important;
      background: linear-gradient(180deg, rgba(240,176,48,0.04), rgba(0,0,0,0.3)) !important;
    }
    body.theme-deusex .channel-card:hover {
      border-color: #f0b030 !important;
      background: linear-gradient(180deg, rgba(240,176,48,0.10), rgba(0,0,0,0.3)) !important;
    }
    body.theme-deusex .channel-card.active {
      border-color: #f0b030 !important;
      background: linear-gradient(180deg, rgba(240,176,48,0.16), rgba(232,90,48,0.05)) !important;
      box-shadow: 0 0 20px rgba(240,176,48,0.4) !important;
    }
    body.theme-deusex .channel-card.active::before {
      background: #f0b030;
      box-shadow: 0 0 10px #f0b030, 0 0 20px rgba(240,176,48,0.6);
    }
    /* Кнопки — угловые срезы со всех 4 сторон */
    body.theme-deusex .cyber-btn {
      clip-path: polygon(
        6px 0,
        calc(100% - 6px) 0,
        100% 6px,
        100% calc(100% - 6px),
        calc(100% - 6px) 100%,
        6px 100%,
        0 calc(100% - 6px),
        0 6px
      ) !important;
      border-radius: 0 !important;
      letter-spacing: 0.15em !important;
      text-transform: uppercase;
    }
    body.theme-deusex .cyber-input,
    body.theme-deusex .cyberdeck-search {
      clip-path: polygon(
        0 0,
        calc(100% - 10px) 0,
        100% 10px,
        100% 100%,
        10px 100%,
        0 calc(100% - 10px)
      ) !important;
      border-radius: 0 !important;
    }
    /* Двойные линии по краям панели — «военный терминал» */
    body.theme-deusex .cyberdeck-panel {
      border-right: 1px solid rgba(240,176,48,0.35) !important;
      box-shadow: inset -8px 0 0 -7px rgba(240,176,48,0.15);
    }
    /* Уголки-скобки по всем 4 углам панели */
    body.theme-deusex .cyberdeck-panel::before {
      background-image:
        linear-gradient(rgba(240,176,48,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(240,176,48,0.03) 1px, transparent 1px);
    }

    /* ============================================================
       GITS — чистота, минимализм, двойные рамки
       ============================================================ */
    body.theme-gits .channel-icon {
      clip-path: none !important;
      border-radius: 0 !important;
      border: 1px solid rgba(0,217,255,0.6) !important;
      box-shadow: inset 0 0 0 3px rgba(0,217,255,0.08) !important;
      background: rgba(3,10,18,0.9) !important;
    }
    body.theme-gits .channel-card {
      clip-path: none !important;
      border-radius: 0 !important;
      border: 1px solid rgba(0,217,255,0.18) !important;
      box-shadow: inset 0 0 0 3px rgba(0,217,255,0.03) !important;
      background: rgba(3,10,18,0.7) !important;
      padding: 12px 14px !important;
    }
    body.theme-gits .channel-card:hover {
      border-color: rgba(0,217,255,0.55) !important;
      background: rgba(6,18,28,0.9) !important;
    }
    body.theme-gits .channel-card.active {
      border-color: #ff3355 !important;
      box-shadow:
        inset 0 0 0 3px rgba(255,51,85,0.08),
        0 0 16px rgba(255,51,85,0.3) !important;
      background: rgba(10,4,10,0.9) !important;
    }
    body.theme-gits .channel-card.active::before {
      background: #ff3355;
      box-shadow: 0 0 10px #ff3355;
      top: 0;
      bottom: 0;
      width: 2px;
    }
    body.theme-gits .channel-card.active .channel-card-name {
      color: #ff3355 !important;
      text-shadow: 0 0 8px rgba(255,51,85,0.8) !important;
    }
    /* Кнопки — прямые с тонкой внутренней линией */
    body.theme-gits .cyber-btn {
      clip-path: none !important;
      border-radius: 0 !important;
      border: 1px solid rgba(0,217,255,0.6) !important;
      box-shadow: inset 0 0 0 2px rgba(0,217,255,0.08) !important;
      padding: 8px 18px !important;
      letter-spacing: 0.2em !important;
      text-transform: uppercase;
    }
    body.theme-gits .cyber-input,
    body.theme-gits .cyberdeck-search {
      clip-path: none !important;
      border-radius: 0 !important;
      border: 1px solid rgba(0,217,255,0.35) !important;
      box-shadow: inset 0 0 0 2px rgba(0,217,255,0.05) !important;
    }
    body.theme-gits .cyber-input:focus,
    body.theme-gits .cyberdeck-search:focus {
      border-color: #ff3355 !important;
      box-shadow: inset 0 0 0 2px rgba(255,51,85,0.08), 0 0 12px rgba(255,51,85,0.3) !important;
    }
    /* Внешние вертикальные метки — уже добавлены в предыдущем спринте */
    body.theme-gits .cyberdeck-panel {
      border-right: 1px solid rgba(255,51,85,0.3) !important;
      box-shadow: inset -6px 0 0 -5px rgba(0,217,255,0.2);
    }

    /* ============================================================
       LAIN — VHS искажения, асимметрия, размытые границы
       ============================================================ */
    body.theme-lain .channel-icon {
      clip-path: none !important;
      border-radius: 8px 0 8px 0 !important;
      border: 1px solid rgba(196,48,74,0.5) !important;
      background: rgba(24,13,24,0.8) !important;
      filter: saturate(0.75) contrast(1.1);
      box-shadow:
        2px 2px 0 rgba(196,48,74,0.15),
        -1px -1px 0 rgba(160,90,138,0.1) !important;
    }
    body.theme-lain .channel-card {
      clip-path: none !important;
      border-radius: 10px 0 10px 0 !important;
      border: 1px solid rgba(196,48,74,0.28) !important;
      background: rgba(24,13,24,0.65) !important;
      /* двойная тень — как двоящееся изображение на плохой кассете */
      box-shadow:
        2px 2px 0 rgba(196,48,74,0.08),
        -2px -2px 0 rgba(160,90,138,0.05) !important;
      position: relative;
    }
    body.theme-lain .channel-card::after {
      /* VHS noise полоска */
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 6px,
        rgba(196,48,74,0.03) 7px,
        transparent 8px
      );
      border-radius: inherit;
    }
    body.theme-lain .channel-card:hover {
      background: rgba(40,20,40,0.9) !important;
      border-color: rgba(196,48,74,0.6) !important;
      box-shadow:
        3px 2px 0 rgba(196,48,74,0.15),
        -3px -2px 0 rgba(160,90,138,0.10) !important;
    }
    body.theme-lain .channel-card.active {
      background: rgba(50,20,40,0.9) !important;
      border-color: #c4304a !important;
      box-shadow:
        4px 3px 0 rgba(196,48,74,0.2),
        -4px -3px 0 rgba(160,90,138,0.15),
        0 0 20px rgba(196,48,74,0.3) !important;
    }
    body.theme-lain .channel-card.active::before {
      background: #c4304a;
      box-shadow: 0 0 10px #c4304a, 0 0 20px rgba(196,48,74,0.5);
    }
    /* Кнопки — с асимметричными углами */
    body.theme-lain .cyber-btn {
      clip-path: none !important;
      border-radius: 8px 0 8px 0 !important;
      border: 1px solid rgba(196,48,74,0.55) !important;
      box-shadow: 2px 2px 0 rgba(196,48,74,0.15) !important;
    }
    body.theme-lain .cyber-btn:hover:not(:disabled) {
      transform: translate(-1px, -1px);
      box-shadow:
        3px 3px 0 rgba(196,48,74,0.2),
        -1px -1px 0 rgba(160,90,138,0.15) !important;
    }
    body.theme-lain .cyber-input,
    body.theme-lain .cyberdeck-search {
      clip-path: none !important;
      border-radius: 8px 0 8px 0 !important;
      border: 1px solid rgba(196,48,74,0.4) !important;
      box-shadow: inset 2px 2px 0 rgba(196,48,74,0.05) !important;
    }
    /* Лёгкое мерцание всей панели — как плохая плёнка */
    body.theme-lain .cyberdeck-panel {
      animation: lain-flicker-panel 7s infinite;
      border-right: 1px solid rgba(196,48,74,0.35) !important;
    }
    @keyframes lain-flicker-panel {
      0%, 92%, 100% { opacity: 1; }
      93% { opacity: 0.94; }
      94% { opacity: 1; }
      96% { opacity: 0.96; }
      97% { opacity: 1; }
    }
    /* Двойная подпись present day/time уже есть — добавим третью метку */
    body.theme-lain .cyberdeck-header::before {
      content: "LAYER::04";
      position: absolute;
      right: 14px;
      top: 10px;
      font-size: 8px;
      letter-spacing: 0.3em;
      color: rgba(160,90,138,0.6);
      pointer-events: none;
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

    print("\nСпринт 16 — визуальная айдентика тем\n")

    # 1) themes.ts — с расширенными переменными
    (src / "themes.ts").write_text(THEMES_TS, encoding="utf-8")
    print(f"  ~ {src / 'themes.ts'}")

    # 2) index.css — добавляем блок THEME VISUAL IDENTITY
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "THEME VISUAL IDENTITY" not in css_text:
        css_text = css_text.rstrip() + "\n" + THEME_VISUAL_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path} (визуальные темы добавлены)")
    else:
        print(f"  > {css_path} (уже пропатчено)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Переключение: ⚙ → THEME или Ctrl+K → 'theme'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())