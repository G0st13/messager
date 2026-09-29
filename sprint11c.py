#!/usr/bin/env python3
"""sprint11c.py - readability: dim city, opaque chat panels, brighter text."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== INDEX.CSS
T["frontend/src/index.css"] = _t('''
    @tailwind base;
    @tailwind components;
    @tailwind utilities;

    :root {
      --neon-cyan: #00f0ff;
      --neon-magenta: #ff00a0;
      --neon-yellow: #fcee0a;
      --bg-deep: #05070d;
      --bg-panel: #0a0f1a;
      --bg-elev: #0f1522;
      --border: #1a2537;
      --text-primary: #eaf4ff;
      --text-muted: #9db4cc;
    }

    html, body, #root { height: 100%; margin: 0; }

    body {
      font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
      background: var(--bg-deep);
      color: var(--text-primary);
      overflow: hidden;
      letter-spacing: 0.02em;
    }

    /* ============= Grid background (поверх города) ============= */
    .cyber-bg {
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      overflow: hidden;
      background: transparent;
      transition: opacity 0.35s;
    }
    .cyber-bg::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(0,240,255,0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,240,255,0.05) 1px, transparent 1px);
      background-size: 40px 40px;
      animation: grid-drift 60s linear infinite;
    }
    @keyframes grid-drift {
      from { background-position: 0 0; }
      to   { background-position: 40px 40px; }
    }

    .cyber-bg::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse at 20% 10%, rgba(255,0,160,0.12), transparent 40%),
        radial-gradient(ellipse at 80% 90%, rgba(0,240,255,0.12), transparent 40%);
      pointer-events: none;
    }

    /* Приглушение города, когда чат открыт */
    .city-dimmed {
      opacity: 0.5;
      filter: saturate(0.6) brightness(0.7);
    }
    .city-very-dimmed {
      opacity: 0.25;
      filter: saturate(0.4) brightness(0.4);
    }

    /* ============= Chat surface — плотные панели чата ============= */
    .chat-surface {
      background:
        linear-gradient(180deg, rgba(5,7,13,0.94), rgba(5,7,13,0.97));
      backdrop-filter: blur(14px) saturate(0.9);
      -webkit-backdrop-filter: blur(14px) saturate(0.9);
    }

    .panel-solid {
      background: rgba(10, 15, 26, 0.94);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
    }

    .panel-semi {
      background: rgba(8, 12, 21, 0.86);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
    }

    /* Мягкая тень текста — читается поверх любых цветов */
    .text-readable {
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.7), 0 0 6px rgba(0, 0, 0, 0.4);
    }

    /* ============= Scanlines (тише) ============= */
    .scanlines {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0,240,255,0.018) 4px,
        transparent 5px
      );
      mix-blend-mode: screen;
      opacity: 0.7;
    }
    .scan-beam {
      position: absolute;
      left: 0;
      right: 0;
      height: 120px;
      background: linear-gradient(180deg, transparent, rgba(0,240,255,0.06), transparent);
      animation: scan-move 8s linear infinite;
      opacity: 0.6;
    }
    @keyframes scan-move {
      0%   { top: -120px; }
      100% { top: 100vh; }
    }

    /* ============= Glitch text ============= */
    .glitch {
      position: relative;
      color: #e8f6ff;
      text-shadow: 0 0 8px rgba(0,240,255,0.5);
      display: inline-block;
    }
    .glitch::before,
    .glitch::after {
      content: attr(data-text);
      position: absolute;
      top: 0; left: 0;
      width: 100%;
      overflow: hidden;
      pointer-events: none;
      opacity: 0.7;
    }
    .glitch::before {
      color: var(--neon-magenta);
      animation: glitch-a 3.5s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
      text-shadow: 0 0 6px var(--neon-magenta);
    }
    .glitch::after {
      color: var(--neon-cyan);
      animation: glitch-b 4.2s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
      text-shadow: 0 0 6px var(--neon-cyan);
    }
    @keyframes glitch-a {
      0%   { transform: translate(0); }
      20%  { transform: translate(-1px, 0); }
      40%  { transform: translate(-1px, -1px); }
      60%  { transform: translate(1px, 0); }
      80%  { transform: translate(0, -1px); }
      100% { transform: translate(0); }
    }
    @keyframes glitch-b {
      0%   { transform: translate(0); }
      25%  { transform: translate(1px, -1px); }
      50%  { transform: translate(1px, 0); }
      75%  { transform: translate(-1px, 1px); }
      100% { transform: translate(0); }
    }

    /* ============= Neon glow ============= */
    .neon-text       { color: var(--neon-cyan);    text-shadow: 0 0 6px rgba(0,240,255,0.7), 0 1px 2px rgba(0,0,0,0.8); }
    .neon-text-mag   { color: var(--neon-magenta); text-shadow: 0 0 6px rgba(255,0,160,0.7), 0 1px 2px rgba(0,0,0,0.8); }
    .neon-text-yel   { color: var(--neon-yellow);  text-shadow: 0 0 6px rgba(252,238,10,0.7), 0 1px 2px rgba(0,0,0,0.8); }

    .neon-border {
      border: 1px solid rgba(0,240,255,0.35);
      box-shadow: 0 0 12px rgba(0,240,255,0.15), inset 0 0 12px rgba(0,240,255,0.04);
    }
    .neon-border-mag {
      border: 1px solid rgba(255,0,160,0.4);
      box-shadow: 0 0 12px rgba(255,0,160,0.2), inset 0 0 12px rgba(255,0,160,0.05);
    }
    .neon-border-yel {
      border: 1px solid rgba(252,238,10,0.4);
      box-shadow: 0 0 12px rgba(252,238,10,0.2);
    }

    /* ============= Flicker ============= */
    .flicker { animation: flicker 6s infinite; }
    @keyframes flicker {
      0%,92%,100% { opacity: 1; }
      93%         { opacity: 0.7; }
      95%         { opacity: 0.9; }
      96%         { opacity: 0.6; }
      97%         { opacity: 1; }
    }

    .cursor::after {
      content: "▮";
      color: var(--neon-cyan);
      animation: blink 1s step-end infinite;
      margin-left: 2px;
      text-shadow: 0 0 6px var(--neon-cyan);
    }
    @keyframes blink { 50% { opacity: 0; } }

    .pulse-glow { animation: pulse-glow 2.4s ease-in-out infinite; }
    @keyframes pulse-glow {
      0%,100% { box-shadow: 0 0 8px rgba(0,240,255,0.35); }
      50%     { box-shadow: 0 0 22px rgba(0,240,255,0.85), inset 0 0 12px rgba(0,240,255,0.15); }
    }
    .pulse-glow-mag { animation: pulse-glow-mag 1.6s ease-in-out infinite; }
    @keyframes pulse-glow-mag {
      0%,100% { box-shadow: 0 0 10px rgba(255,0,160,0.5); }
      50%     { box-shadow: 0 0 28px rgba(255,0,160,0.95); }
    }

    .data-stream {
      position: absolute;
      font-size: 10px;
      color: rgba(0,240,255,0.14);
      white-space: nowrap;
      pointer-events: none;
      writing-mode: vertical-rl;
      text-orientation: mixed;
      animation: stream-fall 15s linear infinite;
      opacity: 0.7;
    }
    @keyframes stream-fall {
      from { transform: translateY(-100%); }
      to   { transform: translateY(100vh); }
    }

    .wire-dash { stroke-dasharray: 6 10; animation: dash-move 30s linear infinite; opacity: 0.7; }
    @keyframes dash-move { to { stroke-dashoffset: -2000; } }
    .wire-glow { filter: drop-shadow(0 0 3px rgba(0,240,255,0.8)); }
    .wire-glow-mag { filter: drop-shadow(0 0 3px rgba(255,0,160,0.8)); }

    .chroma:hover { animation: chroma 0.35s; }
    @keyframes chroma {
      0%   { text-shadow: 0 0 6px rgba(0,240,255,0.6); }
      25%  { text-shadow: 2px 0 var(--neon-magenta), -2px 0 var(--neon-cyan); }
      50%  { text-shadow: -2px 0 var(--neon-magenta), 2px 0 var(--neon-cyan); }
      100% { text-shadow: 0 0 6px rgba(0,240,255,0.6); }
    }

    .corner-frame { position: relative; }
    .corner-frame::before,
    .corner-frame::after {
      content: "";
      position: absolute;
      width: 14px; height: 14px;
      border: 2px solid var(--neon-cyan);
      pointer-events: none;
      filter: drop-shadow(0 0 3px rgba(0,240,255,0.7));
    }
    .corner-frame::before { top: -1px; left: -1px; border-right: none; border-bottom: none; }
    .corner-frame::after { bottom: -1px; right: -1px; border-left: none; border-top: none; }
    .corner-frame-mag::before, .corner-frame-mag::after {
      border-color: var(--neon-magenta);
      filter: drop-shadow(0 0 3px rgba(255,0,160,0.7));
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,240,255,0.04); }
    ::-webkit-scrollbar-thumb { background: rgba(0,240,255,0.3); border-radius: 0; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,240,255,0.55); }

    ::selection {
      background: rgba(255,0,160,0.5);
      color: #fff;
      text-shadow: 0 0 6px var(--neon-magenta);
    }

    @keyframes materialize {
      from { opacity: 0; transform: translateY(6px) scale(0.98); filter: blur(2px); }
      to   { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }
    .animate-materialize { animation: materialize 0.25s ease-out; }

    .cyber-input {
      background: rgba(0,240,255,0.05);
      border: 1px solid rgba(0,240,255,0.3);
      color: #e6f4ff;
      transition: all 0.15s;
      font-family: inherit;
    }
    .cyber-input:focus {
      outline: none;
      border-color: var(--neon-cyan);
      box-shadow: 0 0 12px rgba(0,240,255,0.4), inset 0 0 8px rgba(0,240,255,0.08);
      background: rgba(0,240,255,0.08);
    }
    .cyber-input::placeholder { color: rgba(120,150,180,0.6); letter-spacing: 0.08em; }

    .cyber-btn {
      background: rgba(0,240,255,0.1);
      border: 1px solid rgba(0,240,255,0.5);
      color: var(--neon-cyan);
      transition: all 0.15s;
      font-family: inherit;
      text-transform: uppercase;
      letter-spacing: 0.1em;
    }
    .cyber-btn:hover:not(:disabled) {
      background: rgba(0,240,255,0.2);
      box-shadow: 0 0 16px rgba(0,240,255,0.6);
      transform: translateY(-1px);
    }
    .cyber-btn:active:not(:disabled) { transform: translateY(0); }
    .cyber-btn:disabled { opacity: 0.35; cursor: not-allowed; }

    .cyber-btn-mag {
      background: rgba(255,0,160,0.1);
      border-color: rgba(255,0,160,0.5);
      color: var(--neon-magenta);
    }
    .cyber-btn-mag:hover:not(:disabled) {
      background: rgba(255,0,160,0.2);
      box-shadow: 0 0 16px rgba(255,0,160,0.6);
    }

    .hud-panel {
      background:
        linear-gradient(180deg, rgba(0,240,255,0.03), transparent 30%),
        rgba(10,15,26,0.94);
      border: 1px solid rgba(0,240,255,0.18);
      backdrop-filter: blur(8px);
    }

    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }
''')

# ============================================================== CHATWINDOW patch (string replaces)
# Мы перепишем только те строки, которые влияют на фон и читаемость.
CHATWINDOW_REPLACEMENTS = [
    # Root — добавляем класс chat-surface
    (
        '<main className="relative z-10 flex flex-1 flex-col">',
        '<main className="chat-surface relative z-10 flex flex-1 flex-col">',
    ),
    # Header — плотнее
    (
        '<header className="flex items-center gap-2 border-b border-cyber-cyan/20 bg-cyber-panel/60 px-4 py-2 backdrop-blur">',
        '<header className="flex items-center gap-2 border-b border-cyber-cyan/25 bg-cyber-panel/95 px-4 py-2 backdrop-blur-md">',
    ),
    # Input bar
    (
        '<div className="relative border-t border-cyber-cyan/20 bg-cyber-panel/60 p-3 backdrop-blur">',
        '<div className="relative border-t border-cyber-cyan/25 bg-cyber-panel/95 p-3 backdrop-blur-md">',
    ),
    # Reply/edit bar
    (
        '<div className="flex items-center gap-2 border-t border-cyber-cyan/20 bg-cyber-panel/80 px-4 py-2 backdrop-blur">',
        '<div className="flex items-center gap-2 border-t border-cyber-cyan/25 bg-cyber-panel/95 px-4 py-2 backdrop-blur-md">',
    ),
    # textarea placeholder — крупнее
    (
        'className="cyber-input max-h-32 flex-1 resize-none rounded-sm px-3 py-2 text-sm"',
        'className="cyber-input max-h-32 flex-1 resize-none rounded-sm px-3 py-2 text-[13px] leading-relaxed"',
    ),
    # Дни — крупнее и читаемее
    (
        '<span className="rounded-sm border border-cyber-cyan/40 bg-cyber-panel px-3 py-1 text-[9px] uppercase tracking-[0.3em] neon-text">',
        '<span className="rounded-sm border border-cyber-cyan/50 bg-cyber-bg/90 px-3 py-1 text-[10px] uppercase tracking-[0.3em] neon-text text-readable">',
    ),
    # Область сообщений — слегка затемнена
    (
        '<div className="flex-1 overflow-y-auto px-4 py-4">',
        '<div className="flex-1 overflow-y-auto bg-black/15 px-4 py-4">',
    ),
]

# ============================================================== CHATLIST patch
CHATLIST_REPLACEMENTS = [
    (
        '<aside className="relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/20 bg-cyber-panel/60 backdrop-blur-sm">',
        '<aside className="relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/25 bg-cyber-panel/92 backdrop-blur-md">',
    ),
    # Заголовки в списке — читаемее
    (
        '"truncate text-sm font-bold " +\n                        (active ? "neon-text" : "text-cyber-text group-hover:neon-text")',
        '"truncate text-[13px] font-bold text-readable " +\n                        (active ? "neon-text" : "text-cyber-text group-hover:neon-text")',
    ),
    (
        '"truncate text-[11px] " +\n                            (active ? "text-cyber-cyan/80" : "text-cyber-dim")',
        '"truncate text-[11px] " +\n                            (active ? "text-cyber-cyan/90" : "text-cyber-dim")',
    ),
]

# ============================================================== MESSAGEBUBBLE patch
# bubble background — плотнее + text-readable
MESSAGEBUBBLE_REPLACEMENTS = [
    (
        'background: mine\n          ? "linear-gradient(135deg, rgba(0,240,255,0.08), rgba(0,240,255,0.02))"\n          : "linear-gradient(135deg, rgba(255,0,160,0.06), rgba(255,0,160,0.01))",',
        'background: mine\n          ? "linear-gradient(135deg, rgba(0,240,255,0.18), rgba(0,240,255,0.06))"\n          : "linear-gradient(135deg, rgba(255,0,160,0.14), rgba(255,0,160,0.03))",',
    ),
    (
        'color: "#d6ecff",',
        'color: "#eaf4ff",',
    ),
    # Текст внутри баббла — крупнее и с тенью
    (
        '<div className={msg.is_deleted ? "italic opacity-50 text-xs" : "break-words"}>',
        '<div className={"text-readable text-[13px] leading-relaxed " + (msg.is_deleted ? "italic opacity-50 text-xs" : "break-words")}>',
    ),
]

# ============================================================== APP patch — диммим город, когда чат открыт
APP_REPLACEMENTS = [
    # Пропускаем dimming через props к PixelCity — но проще глобальным классом на <body>
    # Оборачиваем: при activeChat добавляем класс city-dimmed к <PixelCity> контейнеру.
    # Пиксель-город рендерится как <PixelCity weather={cityWeather} seed={user?.id ?? 1} />
    # Внутри App я добавлю div-обертку с классом и передам режим через CSS
    (
        '          <PixelCity weather={cityWeather} seed={user?.id ?? 1} />\n          <CyberBackground />\n          <div className="relative z-10 flex h-screen">',
        '          <div className={activeChatId ? "city-very-dimmed" : "city-dimmed"} style={{ position: "fixed", inset: 0, zIndex: 0, transition: "opacity 0.35s, filter 0.35s" }}>\n            <PixelCity weather={cityWeather} seed={user?.id ?? 1} />\n          </div>\n          <CyberBackground />\n          <div className="relative z-10 flex h-screen">',
    ),
    (
        '          <PixelCity weather={cityWeather} seed={1} />\n          <CyberBackground />\n          <Login onLogin={loadMe} />',
        '          <div className="city-dimmed" style={{ position: "fixed", inset: 0, zIndex: 0 }}>\n            <PixelCity weather={cityWeather} seed={1} />\n          </div>\n          <CyberBackground />\n          <Login onLogin={loadMe} />',
    ),
    (
        '            <PixelCity weather={cityWeather} seed={user?.id ?? 1} />\n            <CyberBackground />\n            <div className="relative z-10 flex h-screen items-center justify-center">',
        '            <div className="city-dimmed" style={{ position: "fixed", inset: 0, zIndex: 0 }}>\n              <PixelCity weather={cityWeather} seed={user?.id ?? 1} />\n            </div>\n            <CyberBackground />\n            <div className="relative z-10 flex h-screen items-center justify-center">',
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

    print(f"\nСпринт 11c — читаемость + приглушение фона\n")

    # CSS
    css = root / "frontend" / "src" / "index.css"
    css.write_text(T["frontend/src/index.css"], encoding="utf-8")
    print(f"  ~ {css}")

    # Патчи
    src = root / "frontend" / "src"
    patch_file(src / "ChatWindow.tsx", CHATWINDOW_REPLACEMENTS)
    patch_file(src / "ChatList.tsx", CHATLIST_REPLACEMENTS)
    patch_file(src / "MessageBubble.tsx", MESSAGEBUBBLE_REPLACEMENTS)
    patch_file(src / "App.tsx", APP_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())