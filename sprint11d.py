#!/usr/bin/env python3
"""sprint11d.py - performance: no backdrop-blur, paused canvas, memo, scroll class."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== INDEX.CSS — убираем blur, добавляем contain, gpu hints
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

    /* ============= Antialiasing, лучше текст ============= */
    * {
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      text-rendering: optimizeSpeed;
    }

    /* ============= Grid background — упрощён ============= */
    .cyber-bg {
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      overflow: hidden;
      background: transparent;
      transition: opacity 0.35s;
      /* изолируем от пересчёта при скролле */
      contain: strict;
    }
    .cyber-bg::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(0,240,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,240,255,0.04) 1px, transparent 1px);
      background-size: 40px 40px;
      will-change: transform;
      transform: translate3d(0, 0, 0);
    }

    .cyber-bg::after {
      content: "";
      position: absolute;
      inset: 0;
      background:
        radial-gradient(ellipse at 20% 10%, rgba(255,0,160,0.10), transparent 40%),
        radial-gradient(ellipse at 80% 90%, rgba(0,240,255,0.10), transparent 40%);
      pointer-events: none;
    }

    /* Приглушение города */
    .city-dimmed {
      opacity: 0.55;
      filter: saturate(0.7) brightness(0.75);
      transition: opacity 0.3s, filter 0.3s;
      contain: strict;
    }
    .city-very-dimmed {
      opacity: 0.28;
      filter: saturate(0.45) brightness(0.5);
      transition: opacity 0.3s, filter 0.3s;
      contain: strict;
    }

    /* КОГДА СКРОЛЛ — отключаем все анимации фона */
    body.scrolling .scan-beam,
    body.scrolling .data-stream,
    body.scrolling .wire-dash,
    body.scrolling .flicker,
    body.scrolling .pulse-glow,
    body.scrolling .pulse-glow-mag,
    body.scrolling .cyber-bg::before {
      animation-play-state: paused !important;
    }
    body.scrolling .cyber-bg,
    body.scrolling .scanlines {
      opacity: 0.4;
    }

    /* ============= Chat surface — плотный фон БЕЗ backdrop-blur ============= */
    /* backdrop-filter супер-тяжёлый, заменяем плотным непрозрачным фоном */
    .chat-surface {
      background: rgb(6, 9, 15);
    }

    .panel-solid {
      background: rgb(11, 16, 27);
    }

    .panel-semi {
      background: rgba(8, 12, 21, 0.94);
    }

    .text-readable {
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.7);
    }

    /* Изоляция для панелей чата — не пересчитывает весь layout */
    .isolate-panel {
      contain: layout style paint;
    }

    /* ============= Scanlines (тихие) ============= */
    .scanlines {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0,240,255,0.015) 4px,
        transparent 5px
      );
      opacity: 0.6;
      contain: strict;
    }
    .scan-beam {
      position: absolute;
      left: 0;
      right: 0;
      height: 120px;
      background: linear-gradient(180deg, transparent, rgba(0,240,255,0.05), transparent);
      animation: scan-move 9s linear infinite;
      opacity: 0.5;
      will-change: transform;
      contain: strict;
    }
    @keyframes scan-move {
      0%   { transform: translate3d(0, -120px, 0); }
      100% { transform: translate3d(0, 100vh, 0); }
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
      opacity: 0.6;
    }
    .glitch::before {
      color: var(--neon-magenta);
      animation: glitch-a 4s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
    }
    .glitch::after {
      color: var(--neon-cyan);
      animation: glitch-b 4.5s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
    }
    @keyframes glitch-a {
      0%   { transform: translate3d(0, 0, 0); }
      20%  { transform: translate3d(-1px, 0, 0); }
      40%  { transform: translate3d(-1px, -1px, 0); }
      60%  { transform: translate3d(1px, 0, 0); }
      80%  { transform: translate3d(0, -1px, 0); }
      100% { transform: translate3d(0, 0, 0); }
    }
    @keyframes glitch-b {
      0%   { transform: translate3d(0, 0, 0); }
      25%  { transform: translate3d(1px, -1px, 0); }
      50%  { transform: translate3d(1px, 0, 0); }
      75%  { transform: translate3d(-1px, 1px, 0); }
      100% { transform: translate3d(0, 0, 0); }
    }

    /* ============= Neon glow ============= */
    .neon-text       { color: var(--neon-cyan);    text-shadow: 0 0 6px rgba(0,240,255,0.55), 0 1px 2px rgba(0,0,0,0.8); }
    .neon-text-mag   { color: var(--neon-magenta); text-shadow: 0 0 6px rgba(255,0,160,0.55), 0 1px 2px rgba(0,0,0,0.8); }
    .neon-text-yel   { color: var(--neon-yellow);  text-shadow: 0 0 6px rgba(252,238,10,0.55), 0 1px 2px rgba(0,0,0,0.8); }

    .neon-border {
      border: 1px solid rgba(0,240,255,0.35);
      box-shadow: 0 0 12px rgba(0,240,255,0.15);
    }
    .neon-border-mag {
      border: 1px solid rgba(255,0,160,0.4);
      box-shadow: 0 0 12px rgba(255,0,160,0.2);
    }
    .neon-border-yel {
      border: 1px solid rgba(252,238,10,0.4);
      box-shadow: 0 0 12px rgba(252,238,10,0.2);
    }

    .flicker { animation: flicker 7s infinite; }
    @keyframes flicker {
      0%,92%,100% { opacity: 1; }
      94%         { opacity: 0.85; }
      96%         { opacity: 0.95; }
    }

    .cursor::after {
      content: "▮";
      color: var(--neon-cyan);
      animation: blink 1s step-end infinite;
      margin-left: 2px;
    }
    @keyframes blink { 50% { opacity: 0; } }

    .pulse-glow { animation: pulse-glow 2.6s ease-in-out infinite; }
    @keyframes pulse-glow {
      0%,100% { box-shadow: 0 0 8px rgba(0,240,255,0.35); }
      50%     { box-shadow: 0 0 18px rgba(0,240,255,0.7); }
    }
    .pulse-glow-mag { animation: pulse-glow-mag 1.8s ease-in-out infinite; }
    @keyframes pulse-glow-mag {
      0%,100% { box-shadow: 0 0 8px rgba(255,0,160,0.5); }
      50%     { box-shadow: 0 0 20px rgba(255,0,160,0.85); }
    }

    .data-stream {
      position: absolute;
      font-size: 10px;
      color: rgba(0,240,255,0.12);
      white-space: nowrap;
      pointer-events: none;
      writing-mode: vertical-rl;
      text-orientation: mixed;
      animation: stream-fall 18s linear infinite;
      opacity: 0.6;
      will-change: transform;
      contain: strict;
    }
    @keyframes stream-fall {
      0%   { transform: translate3d(0, -100%, 0); }
      100% { transform: translate3d(0, 100vh, 0); }
    }

    .wire-dash { stroke-dasharray: 6 10; animation: dash-move 40s linear infinite; opacity: 0.6; }
    @keyframes dash-move { to { stroke-dashoffset: -2000; } }
    .wire-glow { filter: drop-shadow(0 0 3px rgba(0,240,255,0.6)); }
    .wire-glow-mag { filter: drop-shadow(0 0 3px rgba(255,0,160,0.6)); }

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
    }
    .corner-frame::before { top: -1px; left: -1px; border-right: none; border-bottom: none; }
    .corner-frame::after { bottom: -1px; right: -1px; border-left: none; border-top: none; }

    /* ============= Скроллбар ============= */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,240,255,0.04); }
    ::-webkit-scrollbar-thumb { background: rgba(0,240,255,0.3); border-radius: 0; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,240,255,0.55); }

    ::selection {
      background: rgba(255,0,160,0.5);
      color: #fff;
    }

    @keyframes materialize {
      from { opacity: 0; transform: translate3d(0, 6px, 0); }
      to   { opacity: 1; transform: translate3d(0, 0, 0); }
    }
    .animate-materialize { animation: materialize 0.2s ease-out; }

    .cyber-input {
      background: rgba(0,240,255,0.05);
      border: 1px solid rgba(0,240,255,0.3);
      color: #e6f4ff;
      transition: border-color 0.15s, box-shadow 0.15s;
      font-family: inherit;
      contain: content;
    }
    .cyber-input:focus {
      outline: none;
      border-color: var(--neon-cyan);
      box-shadow: 0 0 12px rgba(0,240,255,0.4);
      background: rgba(0,240,255,0.08);
    }
    .cyber-input::placeholder { color: rgba(120,150,180,0.6); letter-spacing: 0.08em; }

    .cyber-btn {
      background: rgba(0,240,255,0.1);
      border: 1px solid rgba(0,240,255,0.5);
      color: var(--neon-cyan);
      transition: background 0.15s, box-shadow 0.15s;
      font-family: inherit;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      contain: content;
    }
    .cyber-btn:hover:not(:disabled) {
      background: rgba(0,240,255,0.2);
      box-shadow: 0 0 16px rgba(0,240,255,0.6);
    }
    .cyber-btn:disabled { opacity: 0.35; cursor: not-allowed; }

    .hud-panel {
      background: rgba(10,15,26,0.96);
      border: 1px solid rgba(0,240,255,0.18);
    }

    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }

    /* ============= Контейнер скролла сообщений ============= */
    .msg-scroll {
      contain: layout style paint;
      overflow-anchor: none;
      transform: translate3d(0, 0, 0);
      backface-visibility: hidden;
    }

    /* Внутри — тоже изолируем */
    .msg-scroll > * {
      contain: layout style paint;
    }

    /* Отдельные сообщения — не влияют на layout выше */
    .msg-item {
      contain: layout style;
    }
''')

# ============================================================== scroll detection hook
T["frontend/src/useScrolling.ts"] = _t('''
    import { useEffect, useRef } from "react";

    /**
     * Пока пользователь скроллит — вешаем class="scrolling" на <body>,
     * чтобы CSS отключил тяжёлые анимации (см. index.css).
     */
    export function useScrolling() {
      const timerRef = useRef<number | null>(null);

      useEffect(() => {
        const onScroll = () => {
          if (!document.body.classList.contains("scrolling")) {
            document.body.classList.add("scrolling");
          }
          if (timerRef.current) window.clearTimeout(timerRef.current);
          timerRef.current = window.setTimeout(() => {
            document.body.classList.remove("scrolling");
          }, 150);
        };

        window.addEventListener("scroll", onScroll, { passive: true, capture: true });
        // capture=true ловит скролл любого контейнера, не только window

        return () => {
          window.removeEventListener("scroll", onScroll, { capture: true } as any);
          if (timerRef.current) window.clearTimeout(timerRef.current);
          document.body.classList.remove("scrolling");
        };
      }, []);
    }
''')

# ============================================================== PixelCity — FPS cap 30, пауза при скролле и вкладке
T["frontend/src/PixelCity.tsx"] = _t(r'''import { useEffect, useRef } from "react";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const W = 480;  // ↓ уменьшили для производительности
const H = 270;
const TARGET_FPS = 30;
const FRAME_MS = 1000 / TARGET_FPS;

type Window_ = { x: number; y: number; w: number; h: number; c: number; bright: number };
type Sign = { x: number; y: number; text: string; c: number; blink: boolean };
type Building = {
  x: number; w: number; h: number;
  windows: Window_[];
  signs: Sign[];
  antenna: boolean;
  antennaH: number;
  roofBox: boolean;
  waterTower: boolean;
  pipes: number;
  smokestack: number;
};
type Drop = { x: number; y: number; v: number; l: number };
type Vehicle = { x: number; y: number; vx: number; hue: number; size: number };
type Person = { x: number; vx: number; h: number };
type GroundCar = { x: number; vx: number; hue: number };
type Hologram = { x: number; y: number; w: number; h: number; c: number; glitch: number };
type Cloud = { x: number; y: number; w: number; h: number; v: number; alpha: number };

const NEON = ["#00f0ff", "#ff00a0", "#fcee0a", "#7cff00", "#ff6600", "#b967ff"];
const SIGN_WORDS = ["CYBER", "NEON", "BAR", "RAMEN", "2077", "HOTEL", "NIGHT", "CLUB", "DATA", "SUSHI"];

function rngFrom(seed: number) {
  let s = (seed >>> 0) || 1;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
function pick<T>(r: () => number, arr: T[]): T {
  return arr[Math.floor(r() * arr.length)];
}

function buildLayer(seed: number, minH: number, maxH: number, density: number, maxW: number, signsDensity: number): Building[] {
  const r = rngFrom(seed);
  const out: Building[] = [];
  let x = -20;
  while (x < W + 20) {
    const w = 14 + Math.floor(r() * maxW);
    const h = minH + Math.floor(r() * (maxH - minH));
    const windows: Window_[] = [];
    // реже окна — быстрее рендер
    for (let wy = 4; wy < h - 4; wy += 5) {
      for (let wx = 3; wx < w - 3; wx += 5) {
        if (r() > density * 0.85) continue;
        windows.push({
          x: wx, y: wy, w: 1, h: 1,
          c: Math.floor(r() * NEON.length),
          bright: 0.5 + r() * 0.5,
        });
      }
    }
    const signs: Sign[] = [];
    if (r() < signsDensity && h > 40) {
      signs.push({
        x: 1 + Math.floor(r() * Math.max(1, w - 18)),
        y: 6 + Math.floor(r() * (h - 20)),
        text: pick(r, SIGN_WORDS),
        c: Math.floor(r() * NEON.length),
        blink: r() < 0.5,
      });
    }
    out.push({
      x, w, h, windows, signs,
      antenna: r() < 0.3 && h > 50,
      antennaH: 6 + Math.floor(r() * 12),
      roofBox: r() < 0.35,
      waterTower: r() < 0.12 && h > 60,
      pipes: r() < 0.4 ? 1 : 0,
      smokestack: r() < 0.08 ? 3 + Math.floor(r() * 3) : 0,
    });
    x += w + 1 + Math.floor(r() * 5);
  }
  return out;
}

function phase(): "night" | "dawn" | "day" | "sunset" {
  const h = new Date().getHours();
  if (h >= 21 || h < 5) return "night";
  if (h < 7) return "dawn";
  if (h < 18) return "day";
  return "sunset";
}

const SKY: Record<string, [string, string, string]> = {
  night: ["#02040a", "#08122a", "#0a1d3a"],
  dawn:  ["#0a0316", "#2a0c2e", "#4a1538"],
  day:   ["#101828", "#1e2a44", "#2a3854"],
  sunset:["#1a0410", "#3a0f22", "#5a1a2a"],
};

function windowColor(idx: number, phaseKey: string): string {
  if (phaseKey === "day") return ["#2a3a55", "#3a4a65"][idx % 2];
  return NEON[idx % NEON.length];
}

export default function PixelCity({
  weather = "auto",
  seed = 1,
}: {
  weather?: Weather;
  seed?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: 0, y: 0 });
  const smooth = useRef({ x: 0, y: 0 });
  const paused = useRef(false);
  const scrolling = useRef(false);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;
    canvas.width = W;
    canvas.height = H;
    ctx.imageSmoothingEnabled = false;

    const layers = [
      { data: buildLayer(seed * 11 + 1, 20, 55, 0.05, 20, 0.05), par: 0.03, tint: "#08101e", top: H - 15, dim: 0.35 },
      { data: buildLayer(seed * 11 + 2, 35, 85, 0.08, 26, 0.10), par: 0.07, tint: "#0a1424", top: H - 25, dim: 0.5 },
      { data: buildLayer(seed * 11 + 3, 55, 120, 0.12, 30, 0.20), par: 0.13, tint: "#0b1526", top: H - 40, dim: 0.7 },
      { data: buildLayer(seed * 11 + 4, 80, 170, 0.18, 34, 0.30), par: 0.22, tint: "#0a1220", top: H - 60, dim: 0.85 },
      { data: buildLayer(seed * 11 + 5, 110, 230, 0.25, 40, 0.40), par: 0.38, tint: "#060c18", top: H - 90, dim: 1.0 },
    ];

    const effective: Weather = weather === "auto"
      ? (["clear", "rain", "rain", "snow", "smog"] as const)[new Date().getDate() % 5]
      : weather;

    const drops: Drop[] = [];
    const vehicles: Vehicle[] = [];
    const people: Person[] = [];
    const groundCars: GroundCar[] = [];
    const holograms: Hologram[] = [];
    const clouds: Cloud[] = [];

    let lightningT = 0;
    let flashAlpha = 0;
    let lightningSegs: [number, number, number, number][] = [];

    // меньше частиц
    if (effective === "rain" || effective === "storm") {
      const count = effective === "storm" ? 120 : 70;
      for (let i = 0; i < count; i++) {
        drops.push({ x: Math.random() * W, y: Math.random() * H, v: 5 + Math.random() * 6, l: 3 + Math.random() * 3 });
      }
    } else if (effective === "snow") {
      for (let i = 0; i < 60; i++) {
        drops.push({ x: Math.random() * W, y: Math.random() * H, v: 0.3 + Math.random() * 0.5, l: 1 });
      }
    }

    for (let i = 0; i < 6; i++) {
      vehicles.push({
        x: Math.random() * W,
        y: 15 + Math.random() * 100,
        vx: (Math.random() < 0.5 ? -1 : 1) * (0.4 + Math.random() * 0.8),
        hue: Math.floor(Math.random() * NEON.length),
        size: 1,
      });
    }
    for (let i = 0; i < 5; i++) {
      people.push({ x: Math.random() * W, vx: (Math.random() < 0.5 ? -1 : 1) * 0.2, h: 3 + Math.floor(Math.random() * 2) });
    }
    for (let i = 0; i < 3; i++) {
      groundCars.push({ x: Math.random() * W, vx: (Math.random() < 0.5 ? -1 : 1) * 1.0, hue: Math.floor(Math.random() * NEON.length) });
    }
    for (let i = 0; i < 2; i++) {
      holograms.push({
        x: 40 + Math.random() * (W - 120),
        y: 30 + Math.random() * 100,
        w: 24 + Math.floor(Math.random() * 16),
        h: 32 + Math.floor(Math.random() * 16),
        c: Math.floor(Math.random() * NEON.length),
        glitch: 0,
      });
    }
    for (let i = 0; i < 4; i++) {
      clouds.push({
        x: Math.random() * W,
        y: 20 + Math.random() * 120,
        w: 30 + Math.floor(Math.random() * 40),
        h: 6 + Math.floor(Math.random() * 6),
        v: 0.1 + Math.random() * 0.2,
        alpha: 0.12 + Math.random() * 0.15,
      });
    }

    const onMove = (e: MouseEvent) => {
      mouse.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMove, { passive: true });

    const onVisibility = () => {
      paused.current = document.hidden;
    };
    document.addEventListener("visibilitychange", onVisibility);

    const onScrollStart = () => {
      scrolling.current = true;
      if (scrollTimer) window.clearTimeout(scrollTimer);
      scrollTimer = window.setTimeout(() => { scrolling.current = false; }, 160);
    };
    let scrollTimer: number | null = null;
    window.addEventListener("scroll", onScrollStart, { passive: true, capture: true });

    // Заранее создаём градиенты (тяжёлые) — переиспользуем
    let cachedSky: CanvasGradient | null = null;
    let cachedSkyKey = "";
    let cachedVignette: CanvasGradient | null = null;

    const drawText = (text: string, x: number, y: number, color: string, alpha: number) => {
      ctx.font = "5px monospace";
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      for (let i = 0; i < text.length; i++) {
        ctx.fillText(text[i], Math.floor(x + i * 4), Math.floor(y));
      }
      ctx.globalAlpha = 1;
    };

    const drawBuilding = (b: Building, layer: typeof layers[0], offsetX: number, pKey: string, t: number) => {
      const bx = Math.floor(b.x - offsetX);
      if (bx + b.w < 0 || bx > W) return;
      const top = layer.top - b.h;

      ctx.fillStyle = layer.tint;
      ctx.fillRect(bx, top, b.w, b.h);
      ctx.fillStyle = "rgba(0,240,255,0.08)";
      ctx.fillRect(bx, top, b.w, 1);

      const winPhase = Math.floor(t / 4000);
      for (let i = 0; i < b.windows.length; i++) {
        const w = b.windows[i];
        const blink = ((i * 31 + winPhase) % 23) === 0;
        if (blink && ((i * 7) % 3) !== 0) continue;
        ctx.globalAlpha = layer.dim * w.bright;
        ctx.fillStyle = windowColor(w.c, pKey);
        ctx.fillRect(bx + w.x, top + w.y, 1, 1);
      }
      ctx.globalAlpha = 1;

      for (const s of b.signs) {
        const isOn = !s.blink || ((Math.floor(t / 600) + s.x) % 4 !== 0);
        if (isOn) drawText(s.text, bx + s.x, top + s.y, NEON[s.c], layer.dim * 0.85);
      }

      if (b.antenna) {
        const ax = bx + Math.floor(b.w / 2);
        ctx.fillStyle = layer.tint;
        ctx.fillRect(ax, top - b.antennaH, 1, b.antennaH);
        const bl = (Math.floor(t / 800) % 2) === 0;
        ctx.globalAlpha = layer.dim;
        ctx.fillStyle = bl ? "#ff2d55" : "#ff8888";
        ctx.fillRect(ax - 1, top - b.antennaH - 2, 2, 2);
        ctx.globalAlpha = 1;
      }
      if (b.roofBox) {
        const bw = 5 + Math.floor(b.w * 0.2);
        ctx.fillStyle = "rgba(0,0,0,0.5)";
        ctx.fillRect(bx + 3, top - 4, bw, 4);
      }
      if (b.waterTower) {
        const wx = bx + Math.floor(b.w / 2) + 4;
        const wy = top - 10;
        ctx.fillStyle = layer.tint;
        ctx.fillRect(wx, wy, 6, 6);
        ctx.fillRect(wx + 1, wy + 6, 1, 4);
        ctx.fillRect(wx + 4, wy + 6, 1, 4);
      }
      for (let i = 0; i < b.pipes; i++) {
        const px = bx + 2 + i * 4;
        ctx.fillStyle = "rgba(0,0,0,0.4)";
        ctx.fillRect(px, top + 4, 1, b.h - 4);
      }
      if (b.smokestack > 0) {
        const sx = bx + Math.floor(b.w * 0.7);
        const sy = top - b.smokestack;
        ctx.fillStyle = "rgba(120,140,180,0.3)";
        ctx.fillRect(sx, sy, 1, b.smokestack);
      }
    };

    let raf = 0;
    let last = performance.now();
    let acc = 0;

    const frame = (t: number) => {
      raf = requestAnimationFrame(frame);

      if (paused.current) return;

      const dt = t - last;
      last = t;
      acc += dt;

      // throttle до TARGET_FPS
      if (acc < FRAME_MS) return;
      // При скролле — вообще пропускаем перерисовку (город уже статичен на экране)
      if (scrolling.current) { acc = 0; return; }

      const dtSec = Math.min(0.1, acc / 1000);
      acc = 0;

      smooth.current.x += (mouse.current.x - smooth.current.x) * 0.05;
      smooth.current.y += (mouse.current.y - smooth.current.y) * 0.05;

      const p = phase();
      const [c1, c2, c3] = SKY[p];

      // кэш градиента неба
      const skyKey = `${p}`;
      if (skyKey !== cachedSkyKey || !cachedSky) {
        const grad = ctx.createLinearGradient(0, 0, 0, H);
        grad.addColorStop(0, c1);
        grad.addColorStop(0.6, c2);
        grad.addColorStop(1, c3);
        cachedSky = grad;
        cachedSkyKey = skyKey;
      }
      ctx.fillStyle = cachedSky!;
      ctx.fillRect(0, 0, W, H);

      if (p === "night" || p === "dawn") {
        const r = rngFrom(12345);
        ctx.fillStyle = "#4a5a7a";
        for (let i = 0; i < 60; i++) {
          const x = Math.floor(r() * W);
          const y = Math.floor(r() * (H * 0.55));
          const twinkle = ((Math.floor(t / 900) + i) % 9) === 0;
          ctx.globalAlpha = twinkle ? 0.9 : 0.35;
          ctx.fillRect(x, y, 1, 1);
        }
        ctx.globalAlpha = 1;
      }

      // Луна/солнце
      const isNight = p === "night";
      const sunX = Math.floor(W * 0.82);
      const sunY = isNight ? 42 : p === "dawn" ? Math.floor(H * 0.32) : p === "sunset" ? Math.floor(H * 0.38) : 50;
      if (isNight) {
        ctx.fillStyle = "#e8f0ff";
        ctx.fillRect(sunX, sunY, 10, 10);
        ctx.fillStyle = "rgba(120,140,180,0.5)";
        ctx.fillRect(sunX + 2, sunY + 2, 2, 2);
        ctx.fillRect(sunX + 6, sunY + 5, 2, 2);
      } else {
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = p === "day" ? "#c0c8d8" : "#ff8855";
        ctx.fillRect(sunX, sunY, 8, 8);
        ctx.globalAlpha = 1;
      }

      // Облака
      for (const c of clouds) {
        c.x += c.v * dtSec * 10;
        if (c.x > W + 60) c.x = -60;
        ctx.globalAlpha = c.alpha;
        ctx.fillStyle = p === "sunset" || p === "dawn" ? "#4a2030" : "#1a2438";
        ctx.fillRect(Math.floor(c.x), Math.floor(c.y), c.w, c.h);
        ctx.fillRect(Math.floor(c.x + 6), Math.floor(c.y - 3), Math.floor(c.w * 0.6), 4);
      }
      ctx.globalAlpha = 1;

      for (const L of layers) {
        const offsetX = smooth.current.x * 30 * L.par;
        for (const b of L.data) drawBuilding(b, L, offsetX, p, t);
      }

      // Голограммы
      for (const h of holograms) {
        h.glitch += dtSec;
        const glitching = h.glitch > 8;
        if (glitching) h.glitch = 0;
        const col = NEON[h.c];
        const hx = Math.floor(h.x + smooth.current.x * 15);
        const hy = Math.floor(h.y);
        ctx.globalAlpha = glitching ? 0.15 : 0.3;
        ctx.fillStyle = col;
        ctx.fillRect(hx, hy, h.w, 1);
        ctx.fillRect(hx, hy + h.h, h.w, 1);
        ctx.fillRect(hx, hy, 1, h.h);
        ctx.fillRect(hx + h.w, hy, 1, h.h);
        for (let i = 2; i < h.h; i += 5) {
          const lineW = Math.floor(h.w * (0.5));
          ctx.globalAlpha = 0.2;
          ctx.fillRect(hx + 2, hy + i, lineW, 1);
        }
        ctx.globalAlpha = 0.5;
        ctx.fillRect(Math.floor(hx + h.w / 2 - 3), Math.floor(hy + h.h / 2 - 1), 5, 3);
      }
      ctx.globalAlpha = 1;

      // Летающие машины
      for (const c of vehicles) {
        c.x += c.vx * dtSec * 30;
        if (c.x < -30) c.x = W + 30;
        if (c.x > W + 30) c.x = -30;
        const y = c.y + Math.sin(t / 900 + c.x * 0.01) * 2.5;
        const col = NEON[c.hue];
        ctx.globalAlpha = 0.3;
        ctx.fillStyle = col;
        ctx.fillRect(Math.floor(c.x - c.vx * 8), Math.floor(y), 8, 1);
        ctx.globalAlpha = 1;
        ctx.fillStyle = "#0a0f1a";
        ctx.fillRect(Math.floor(c.x), Math.floor(y - 1), 3, 2);
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = col;
        const front = c.vx > 0 ? Math.floor(c.x) + 2 : Math.floor(c.x) - 1;
        ctx.fillRect(front, Math.floor(y), 1, 1);
      }
      ctx.globalAlpha = 1;

      // Улица
      const streetY = H - 8;
      ctx.fillStyle = "#04070e";
      ctx.fillRect(0, streetY - 4, W, 12);
      ctx.fillStyle = "#0a1020";
      ctx.fillRect(0, streetY - 4, W, 1);

      for (const pn of people) {
        pn.x += pn.vx * dtSec * 30;
        if (pn.x < -5) pn.x = W + 5;
        if (pn.x > W + 5) pn.x = -5;
        ctx.fillStyle = "#050810";
        const px = Math.floor(pn.x);
        ctx.fillRect(px, streetY - pn.h, 2, pn.h);
        ctx.fillRect(px, streetY - pn.h - 2, 2, 2);
      }

      for (const gc of groundCars) {
        gc.x += gc.vx * dtSec * 40;
        if (gc.x < -20) gc.x = W + 20;
        if (gc.x > W + 20) gc.x = -20;
        const col = NEON[gc.hue];
        const gy = streetY - 1;
        ctx.fillStyle = "#0a0f1a";
        ctx.fillRect(Math.floor(gc.x), gy, 8, 2);
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = col;
        const fx = gc.vx > 0 ? Math.floor(gc.x) + 8 : Math.floor(gc.x) - 1;
        ctx.fillRect(fx, gy, 1, 1);
        ctx.globalAlpha = 1;
      }

      // Погода
      if (effective === "rain" || effective === "storm") {
        ctx.strokeStyle = "#7ec8ff";
        ctx.globalAlpha = effective === "storm" ? 0.6 : 0.35;
        ctx.beginPath();
        for (const d of drops) {
          d.y += d.v * dtSec * 60;
          d.x += 0.5;
          if (d.y > H) { d.y = -5; d.x = Math.random() * W; }
          ctx.moveTo(Math.floor(d.x), Math.floor(d.y));
          ctx.lineTo(Math.floor(d.x), Math.floor(d.y + d.l));
        }
        ctx.stroke();
        ctx.globalAlpha = 1;
      } else if (effective === "snow") {
        ctx.fillStyle = "#e8f4ff";
        for (const d of drops) {
          d.y += d.v * dtSec * 60;
          d.x += Math.sin((t + d.x * 10) / 800) * 0.4;
          if (d.y > H) { d.y = -2; d.x = Math.random() * W; }
          ctx.globalAlpha = 0.8;
          ctx.fillRect(Math.floor(d.x), Math.floor(d.y), 1, 1);
        }
        ctx.globalAlpha = 1;
      } else if (effective === "smog") {
        ctx.fillStyle = "rgba(90, 40, 110, 0.12)";
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = "rgba(180, 80, 60, 0.06)";
        ctx.fillRect(0, Math.floor(H * 0.4), W, Math.floor(H * 0.6));
      }

      // Молния
      if (effective === "storm") {
        lightningT += dtSec;
        if (flashAlpha > 0) flashAlpha -= dtSec * 6;
        if (lightningT > 5 + Math.random() * 6) {
          lightningT = 0;
          flashAlpha = 1.0;
          lightningSegs = [];
          let bx = W * 0.25 + Math.random() * W * 0.5;
          let by = 0;
          while (by < H * 0.6) {
            const nx = bx + (Math.random() - 0.5) * 16;
            const ny = by + 4 + Math.random() * 8;
            lightningSegs.push([bx, by, nx, ny]);
            bx = nx; by = ny;
          }
        }
        if (flashAlpha > 0 && lightningSegs.length > 0) {
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1;
          ctx.globalAlpha = Math.min(1, flashAlpha);
          ctx.beginPath();
          for (const [x1, y1, x2, y2] of lightningSegs) {
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
          }
          ctx.stroke();
          ctx.globalAlpha = 1;
        }
        if (flashAlpha > 0) {
          ctx.fillStyle = `rgba(200, 220, 255, ${flashAlpha * 0.35})`;
          ctx.fillRect(0, 0, W, H);
        }
      }

      // Vignette — кэширован
      if (!cachedVignette) {
        const vg = ctx.createRadialGradient(W / 2, H / 2, 60, W / 2, H / 2, W * 0.8);
        vg.addColorStop(0, "rgba(0,0,0,0)");
        vg.addColorStop(1, "rgba(0,0,0,0.65)");
        cachedVignette = vg;
      }
      ctx.fillStyle = cachedVignette;
      ctx.fillRect(0, 0, W, H);
    };

    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("scroll", onScrollStart, { capture: true } as any);
      document.removeEventListener("visibilitychange", onVisibility);
      if (scrollTimer) window.clearTimeout(scrollTimer);
    };
  }, [weather, seed]);

  return (
    <canvas
      ref={ref}
      className="pointer-events-none fixed inset-0 h-full w-full"
      style={{ imageRendering: "pixelated", zIndex: 0 }}
    />
  );
}
''')

# ============================================================== ChatWindow — memo + useCallback + isolate
CHATWINDOW = r'''import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Avatar from "./Avatar";
import MessageBubble from "./MessageBubble";
import EmojiPicker from "./EmojiPicker";
import StickerPicker from "./StickerPicker";
import FileUpload from "./FileUpload";
import VoiceRecorder from "./VoiceRecorder";
import Lightbox from "./Lightbox";
import SearchModal from "./SearchModal";
import { api } from "./api";
import type { Chat, Message, User } from "./types";

export interface QueuedLike {
  client_id: string;
  chat_id: number;
  text: string | null;
  message_type: string;
  attachment_id: number | null;
  reply_to_id: number | null;
  created_at: string;
  attempts: number;
  status: "pending" | "failed";
  author_id: number;
  author_username: string;
  author_display: string | null;
  author_avatar_color: string | null;
}

function dayLabel(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString()) return "▸ TODAY";
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return "▸ YESTERDAY";
  return "▸ " + d.toLocaleDateString([], { day: "numeric", month: "long" }).toUpperCase();
}

function ChatWindowInner({
  chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser, onStartCall,
  queuedMessages, onEnqueue, onRemoveQueued,
}: {
  chat: Chat;
  currentUser: User;
  send: (data: any) => void;
  subscribe: (h: (d: any) => void) => () => void;
  onlineUsers: Set<number>;
  onOpenInfo: () => void;
  onOpenUser: (userId: number) => void;
  onStartCall: (kind: "audio" | "video") => void;
  queuedMessages: QueuedLike[];
  onEnqueue: (chatId: number, text: string | null, messageType: string, attachmentId: number | null, replyToId: number | null) => void;
  onRemoveQueued: (clientId: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [editing, setEditing] = useState<Message | null>(null);
  const [emojiOpen, setEmojiOpen] = useState(false);
  const [stickerOpen, setStickerOpen] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
  const [peerReadUpTo, setPeerReadUpTo] = useState<number>(0);
  const [lightbox, setLightbox] = useState<string | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const [pinned, setPinned] = useState<Message[]>([]);
  const [pinnedIdx, setPinnedIdx] = useState(0);
  const [highlightId, setHighlightId] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const typingTimeout = useRef<number | null>(null);
  const lastTypingSent = useRef<number>(0);
  const draftTimer = useRef<number | null>(null);
  const stickToBottom = useRef(true);

  const myQueue = useMemo(
    () => queuedMessages.filter((m) => m.chat_id === chat.id),
    [queuedMessages, chat.id],
  );

  useEffect(() => {
    api.get<Message[]>(`/chats/${chat.id}/messages`).then((r) => setMessages(r.data));
    api.get<{ draft: string }>(`/chats/${chat.id}/draft`).then((r) => {
      if (r.data.draft) setText(r.data.draft);
      else setText("");
    }).catch(() => setText(""));
    api.get<Message[]>(`/chats/${chat.id}/pinned`).then((r) => setPinned(r.data)).catch(() => {});
    send({ type: "subscribe", chat_id: chat.id });
    api.post(`/chats/${chat.id}/read`).catch(() => {});
    return () => send({ type: "unsubscribe", chat_id: chat.id });
  }, [chat.id]);

  // автоскролл — только если пользователь внизу
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current) return;
    // без smooth: моментально, чтобы не лагало
    el.scrollTop = el.scrollHeight;
  }, [messages.length, myQueue.length]);

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!last) return;
    if (last.author_id !== currentUser.id && last.message_type !== "system") {
      send({ type: "read", chat_id: chat.id, message_id: last.id });
    }
  }, [messages.length]);

  useEffect(() => {
    if (draftTimer.current) window.clearTimeout(draftTimer.current);
    draftTimer.current = window.setTimeout(() => {
      api.patch(`/chats/${chat.id}/draft`, { draft: text || null }).catch(() => {});
    }, 900);
    return () => {
      if (draftTimer.current) window.clearTimeout(draftTimer.current);
    };
  }, [text, chat.id]);

  useEffect(() => {
    const off = subscribe((d) => {
      if (d.type === "message" && d.chat_id === chat.id) {
        if (d.client_id && d.author_id === currentUser.id) {
          onRemoveQueued(d.client_id);
        }
        setMessages((prev) => {
          if (prev.some((m) => m.id === d.id)) return prev;
          return [...prev, {
            id: d.id, chat_id: d.chat_id,
            client_id: d.client_id || null,
            author_id: d.author_id, author_username: d.author_username,
            author_display: d.author_display, author_avatar_color: d.author_avatar_color,
            text: d.text, message_type: d.message_type || "text",
            attachment: d.attachment || null,
            reply_to_id: d.reply_to_id,
            reply_preview: d.reply_preview, reply_author: d.reply_author,
            edited_at: null, is_deleted: false, is_pinned: false,
            reactions: d.reactions || [],
            created_at: d.created_at,
          }];
        });
        if (d.author_id !== currentUser.id && d.message_type !== "system") {
          send({ type: "read", chat_id: chat.id, message_id: d.id });
        }
      } else if (d.type === "message_edited" && d.chat_id === chat.id) {
        setMessages((prev) =>
          prev.map((m) => m.id === d.message_id ? { ...m, text: d.text, edited_at: d.edited_at } : m)
        );
      } else if (d.type === "message_deleted" && d.chat_id === chat.id) {
        setMessages((prev) =>
          prev.map((m) => m.id === d.message_id ? { ...m, is_deleted: true, text: "Сообщение удалено" } : m)
        );
      } else if (d.type === "reactions" && d.chat_id === chat.id) {
        setMessages((prev) =>
          prev.map((m) => m.id === d.message_id ? { ...m, reactions: d.reactions } : m)
        );
      } else if (d.type === "typing" && d.chat_id === chat.id) {
        setTypingUsers((prev) => {
          const next = new Set(prev);
          if (d.is_typing) next.add(d.username);
          else next.delete(d.username);
          return next;
        });
      } else if (d.type === "read" && d.chat_id === chat.id) {
        setPeerReadUpTo((prev) => Math.max(prev, d.message_id));
      }
    });
    return off;
  }, [chat.id, currentUser.id, subscribe, send, onRemoveQueued]);

  const allMessages: Message[] = useMemo(() => {
    const virtual: Message[] = myQueue.map((m) => ({
      id: -1 - Math.random(),
      client_id: m.client_id,
      chat_id: m.chat_id,
      author_id: m.author_id,
      author_username: m.author_username,
      author_display: m.author_display,
      author_avatar_color: m.author_avatar_color,
      text: m.text,
      message_type: m.message_type as any,
      attachment: null,
      reply_to_id: m.reply_to_id,
      reply_preview: null,
      reply_author: null,
      edited_at: null,
      is_deleted: false,
      is_pinned: false,
      reactions: [],
      created_at: m.created_at,
      send_status: m.status === "failed" ? "failed" : "pending",
    }));
    const out = [...messages];
    for (const v of virtual) {
      if (out.some((m) => m.client_id === v.client_id)) continue;
      out.push(v);
    }
    return out.sort((a, b) =>
      new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    );
  }, [messages, myQueue]);

  const grouped = useMemo(() => {
    const out: { day: string; items: Message[] }[] = [];
    for (const m of allMessages) {
      const day = dayLabel(m.created_at);
      const last = out[out.length - 1];
      if (last && last.day === day) last.items.push(m);
      else out.push({ day, items: [m] });
    }
    return out;
  }, [allMessages]);

  const doSend = useCallback(() => {
    const t = text.trim();
    if (!t) return;
    if (editing) {
      send({ type: "edit", message_id: editing.id, text: t });
      setEditing(null);
    } else {
      onEnqueue(chat.id, t, "text", null, replyTo?.id ?? null);
      setReplyTo(null);
    }
    setText("");
    send({ type: "typing", chat_id: chat.id, is_typing: false });
  }, [text, editing, replyTo, chat.id, send, onEnqueue]);

  const sendAttachment = useCallback((attachmentId: number, type: "image" | "file" | "voice") => {
    onEnqueue(chat.id, null, type, attachmentId, replyTo?.id ?? null);
    setReplyTo(null);
  }, [chat.id, replyTo, onEnqueue]);

  const sendSticker = useCallback((sticker: string) => {
    onEnqueue(chat.id, sticker, "sticker", null, replyTo?.id ?? null);
    setStickerOpen(false);
    setReplyTo(null);
  }, [chat.id, replyTo, onEnqueue]);

  const handleReact = useCallback((messageId: number, emoji: string) => {
    if (messageId < 0) return;
    send({ type: "reaction", message_id: messageId, emoji });
  }, [send]);

  const handlePin = useCallback(async (m: Message) => {
    if (m.id < 0) return;
    try {
      if (m.is_pinned) {
        await api.delete(`/chats/messages/${m.id}/pin`);
        setPinned((prev) => prev.filter((x) => x.id !== m.id));
        setMessages((prev) => prev.map((x) => x.id === m.id ? { ...x, is_pinned: false } : x));
      } else {
        await api.post(`/chats/messages/${m.id}/pin`);
        setPinned((prev) => [m, ...prev.filter((x) => x.id !== m.id)]);
        setMessages((prev) => prev.map((x) => x.id === m.id ? { ...x, is_pinned: true } : x));
      }
    } catch {}
  }, []);

  const onReply = useCallback((mm: Message) => { setReplyTo(mm); setEditing(null); }, []);
  const onEdit = useCallback((mm: Message) => { setEditing(mm); setReplyTo(null); setText(mm.text || ""); }, []);
  const onDelete = useCallback((mm: Message) => send({ type: "delete", message_id: mm.id }), [send]);
  const onOpenImage = useCallback((url: string) => setLightbox(url), []);

  const jumpTo = useCallback((messageId: number) => {
    setHighlightId(messageId);
    setTimeout(() => {
      const el = document.getElementById(`msg-${messageId}`);
      el?.scrollIntoView({ behavior: "auto", block: "center" });
    }, 30);
    setTimeout(() => setHighlightId(null), 2000);
  }, []);

  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      doSend();
    }
    if (e.key === "Escape") {
      setReplyTo(null);
      setEditing(null);
    }
  }, [doSend]);

  const onTextChange = useCallback((v: string) => {
    setText(v);
    const now = Date.now();
    if (now - lastTypingSent.current > 2200) {
      send({ type: "typing", chat_id: chat.id, is_typing: true });
      lastTypingSent.current = now;
    }
    if (typingTimeout.current) window.clearTimeout(typingTimeout.current);
    typingTimeout.current = window.setTimeout(() => {
      send({ type: "typing", chat_id: chat.id, is_typing: false });
    }, 3000);
  }, [chat.id, send]);

  // отслеживаем, прилип ли пользователь к низу
  const onScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const dist = el.scrollHeight - el.scrollTop - el.clientHeight;
    stickToBottom.current = dist < 80;
  }, []);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
        e.preventDefault();
        setShowSearch(true);
      }
    };
    document.addEventListener("keydown", h);
    return () => document.removeEventListener("keydown", h);
  }, []);

  const peerOnline = chat.peer ? onlineUsers.has(chat.peer.id) : false;
  const headerTitle = chat.peer
    ? chat.peer.display_name || chat.peer.username
    : chat.title || `NODE #${chat.id}`;
  const headerSub = typingUsers.size > 0
    ? "▸ typing…"
    : chat.peer
    ? (peerOnline ? "◉ online" : "○ offline")
    : `${chat.member_count} nodes`;

  const avatarUser = chat.peer || {
    username: chat.title || "G",
    display_name: chat.title || "GRP",
    avatar_color: chat.avatar_color || "#ff00a0",
  };

  const currentPinned = pinned[pinnedIdx] || null;
  const failedCount = myQueue.filter((m) => m.status === "failed").length;

  return (
    <main className="chat-surface isolate-panel relative z-10 flex flex-1 flex-col">
      <header className="flex items-center gap-2 border-b border-cyber-cyan/25 panel-solid px-4 py-2">
        <button
          onClick={() => chat.peer ? onOpenUser(chat.peer.id) : onOpenInfo()}
          className="flex min-w-0 flex-1 items-center gap-3 transition hover:opacity-90"
        >
          <Avatar user={avatarUser as any} size={40} showOnline={!!chat.peer} online={peerOnline} />
          <div className="min-w-0 flex-1 text-left">
            <div className="truncate font-bold neon-text text-readable">{headerTitle}</div>
            <div className="truncate text-[10px] uppercase tracking-widest text-cyber-dim">{headerSub}</div>
          </div>
        </button>

        <button
          onClick={() => setShowSearch(true)}
          title="Search (Ctrl+F)"
          className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
        >
          ⌕
        </button>

        {chat.peer && (
          <>
            <button
              onClick={() => onStartCall("audio")}
              title="Audio call"
              className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
            >
              ☎
            </button>
            <button
              onClick={() => onStartCall("video")}
              title="Video call"
              className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
            >
              ▶
            </button>
          </>
        )}

        {chat.is_group && (
          <button
            onClick={onOpenInfo}
            title="Group info"
            className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
          >
            ℹ
          </button>
        )}
      </header>

      {failedCount > 0 && (
        <div className="flex items-center gap-2 border-b border-cyber-magenta/30 bg-cyber-magenta/5 px-4 py-1.5 text-xs">
          <span className="neon-text-mag">⚠</span>
          <span className="flex-1 text-cyber-text">
            {failedCount} сообщ. не удалось отправить
          </span>
        </div>
      )}

      {currentPinned && (
        <div className="flex items-center gap-2 border-b border-cyber-yellow/30 bg-cyber-yellow/5 px-4 py-1.5">
          <span className="text-cyber-yellow">📌</span>
          <button
            onClick={() => jumpTo(currentPinned.id)}
            className="min-w-0 flex-1 text-left text-xs text-cyber-text hover:underline"
          >
            <div className="truncate">
              <span className="text-[10px] uppercase tracking-widest neon-text-yel">
                {currentPinned.author_display || currentPinned.author_username}:
              </span>{" "}
              {currentPinned.text || "[attachment]"}
            </div>
          </button>
          {pinned.length > 1 && (
            <div className="flex items-center gap-1 text-[10px] text-cyber-dim">
              <button
                onClick={() => setPinnedIdx((i) => (i - 1 + pinned.length) % pinned.length)}
                className="rounded-sm px-1 hover:text-cyber-cyan"
              >
                ‹
              </button>
              <span>{pinnedIdx + 1}/{pinned.length}</span>
              <button
                onClick={() => setPinnedIdx((i) => (i + 1) % pinned.length)}
                className="rounded-sm px-1 hover:text-cyber-cyan"
              >
                ›
              </button>
            </div>
          )}
          <button
            onClick={() => handlePin(currentPinned)}
            className="text-[10px] uppercase tracking-widest text-cyber-dim hover:neon-text-mag"
          >
            unpin
          </button>
        </div>
      )}

      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="msg-scroll flex-1 overflow-y-auto bg-black/25 px-4 py-4"
      >
        {grouped.map((g) => (
          <div key={g.day} className="mb-4">
            <div className="mb-3 flex items-center gap-2">
              <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent to-cyber-cyan/40" />
              <span className="rounded-sm border border-cyber-cyan/50 bg-cyber-bg/90 px-3 py-1 text-[10px] uppercase tracking-[0.3em] neon-text text-readable">
                {g.day}
              </span>
              <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent to-cyber-cyan/40" />
            </div>
            <div className="space-y-1">
              {g.items.map((m, idx) => {
                const prev = g.items[idx - 1];
                const showAvatar = !prev || prev.author_id !== m.author_id || prev.message_type === "system";
                const isLast = idx === g.items.length - 1 || g.items[idx + 1].author_id !== m.author_id;
                const isHighlighted = highlightId === m.id;
                return (
                  <div
                    key={m.client_id || m.id}
                    className={"msg-item " + (isHighlighted ? "ring-2 ring-cyber-yellow" : "")}
                  >
                    <MessageBubble
                      msg={m}
                      mine={m.author_id === currentUser.id}
                      showAvatar={showAvatar}
                      isLast={isLast}
                      readByPeer={peerReadUpTo >= m.id}
                      onReply={onReply}
                      onEdit={onEdit}
                      onDelete={onDelete}
                      onOpenImage={onOpenImage}
                      onOpenProfile={onOpenUser}
                      onReact={handleReact}
                      onPin={handlePin}
                    />
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {(replyTo || editing) && (
        <div className="flex items-center gap-2 border-t border-cyber-cyan/25 panel-solid px-4 py-2">
          <div className="flex-1 truncate border-l-2 border-cyber-cyan pl-2 text-sm">
            <div className="text-[10px] uppercase tracking-widest neon-text">
              {editing ? "◂ editing" : `↳ reply ${replyTo?.author_display || replyTo?.author_username}`}
            </div>
            <div className="truncate text-xs text-cyber-dim">
              {editing ? editing.text : replyTo?.text}
            </div>
          </div>
          <button
            onClick={() => { setReplyTo(null); setEditing(null); setText(""); }}
            className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15"
          >
            ✕
          </button>
        </div>
      )}

      <div className="relative border-t border-cyber-cyan/25 panel-solid p-3">
        {typingUsers.size > 0 && (
          <div className="absolute -top-5 left-4 flex items-center gap-1 text-[10px] uppercase tracking-widest text-cyber-cyan/80 text-readable">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
            <span className="ml-1">{Array.from(typingUsers).join(", ")}</span>
          </div>
        )}
        <div className="flex items-end gap-1">
          <FileUpload asType="image" accept="image/*" onUploaded={(a, t) => sendAttachment(a.id, t)} />
          <FileUpload asType="file" onUploaded={(a, t) => sendAttachment(a.id, t)} />
          <button
            onClick={() => { setStickerOpen(!stickerOpen); setEmojiOpen(false); }}
            className="rounded-sm p-2 text-lg text-cyber-cyan transition hover:bg-cyber-cyan/10"
          >
            ◈
          </button>
          <button
            onClick={() => { setEmojiOpen(!emojiOpen); setStickerOpen(false); }}
            className="rounded-sm p-2 text-lg text-cyber-cyan transition hover:bg-cyber-cyan/10"
          >
            ☺
          </button>
          <textarea
            value={text}
            onChange={(e) => onTextChange(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="TRANSMIT MESSAGE..."
            className="cyber-input max-h-32 flex-1 resize-none rounded-sm px-3 py-2 text-[13px] leading-relaxed"
          />
          <VoiceRecorder onUploaded={(a) => sendAttachment(a.id, "voice")} />
          <button
            onClick={doSend}
            disabled={!text.trim()}
            className="cyber-btn rounded-sm px-4 py-2 text-xs"
          >
            ▸
          </button>
        </div>

        {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}
        {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}
      </div>

      {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}
      {showSearch && (
        <SearchModal
          chatId={chat.id}
          onClose={() => setShowSearch(false)}
          onJumpTo={jumpTo}
        />
      )}
    </main>
  );
}

export default memo(ChatWindowInner);
'''

T["frontend/src/ChatWindow.tsx"] = CHATWINDOW

# ============================================================== MessageBubble — memo
MESSAGEBUBBLE = r'''import { memo, useState } from "react";
import Avatar from "./Avatar";
import { fileUrl, humanSize } from "./api";
import { renderMarkdown } from "./markdown";
import type { Message, User } from "./types";

const QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🔥"];

function iconFor(mime: string): string {
  if (mime.startsWith("image/")) return "▣";
  if (mime.startsWith("audio/")) return "◍";
  if (mime.startsWith("video/")) return "▶";
  if (mime.includes("pdf")) return "▤";
  if (mime.includes("zip")) return "▥";
  return "▧";
}

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function MessageBubbleInner({
  msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer,
  onOpenImage, onOpenProfile, onReact, onPin
}: {
  msg: Message;
  mine: boolean;
  showAvatar: boolean;
  isLast: boolean;
  onReply: (m: Message) => void;
  onEdit: (m: Message) => void;
  onDelete: (m: Message) => void;
  readByPeer: boolean;
  onOpenImage: (url: string) => void;
  onOpenProfile: (userId: number) => void;
  onReact: (messageId: number, emoji: string) => void;
  onPin: (m: Message) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reactOpen, setReactOpen] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioCurrent, setAudioCurrent] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);

  const sendStatus = msg.send_status;
  const isPending = sendStatus === "pending";
  const isFailed = sendStatus === "failed";
  const isVirtual = msg.id < 0;

  if (msg.message_type === "system") {
    return (
      <div className="my-2 flex justify-center">
        <div className="neon-border-yel rounded-sm bg-cyber-yellow/5 px-3 py-1 text-[10px] uppercase tracking-widest neon-text-yel">
          ⚠ {msg.text}
        </div>
      </div>
    );
  }

  const author: Pick<User, "username" | "display_name" | "avatar_color"> = {
    username: msg.author_username,
    display_name: msg.author_display,
    avatar_color: msg.author_avatar_color,
  };

  const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";
  const bubbleStyle = {
    background: isFailed
      ? "rgba(255,45,85,0.18)"
      : mine
      ? "rgba(0,240,255,0.16)"
      : "rgba(255,0,160,0.14)",
    border: `1px solid ${accent}66`,
    color: "#eaf4ff",
    opacity: isPending ? 0.78 : 1,
  };

  const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
  const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
  const isVideo = msg.message_type === "file" && msg.attachment &&
    msg.attachment.content_type.startsWith("video/") && !msg.is_deleted;
  const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
  const isFile = msg.message_type === "file" && msg.attachment && !isVideo && !msg.is_deleted;

  const hasReactions = msg.reactions && msg.reactions.length > 0;

  if (isSticker) {
    return (
      <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
        {!mine ? (
          <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
            {showAvatar && <Avatar user={author} size={32} />}
          </button>
        ) : null}
        <div className="relative">
          <div className={"text-7xl leading-none " + (isPending ? "opacity-70" : "")}>
            {msg.text}
          </div>
          <div className={"mt-1 flex items-center gap-2 text-[9px] uppercase tracking-wider " + (mine ? "justify-end" : "")}>
            <span className="text-cyber-dim">
              {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            {mine && (
              <span className={isPending ? "text-cyber-dim" : isFailed ? "neon-text-mag" : readByPeer ? "neon-text" : "text-cyber-dim"}>
                {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")} id={`msg-${msg.id}`}>
      {!mine ? (
        <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
          {showAvatar && <Avatar user={author} size={32} />}
        </button>
      ) : null}

      <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
        {!mine && showAvatar && (
          <button
            onClick={() => onOpenProfile(msg.author_id)}
            className="mb-1 ml-2 text-[10px] font-bold uppercase tracking-widest neon-text-mag text-readable"
          >
            ◂ {msg.author_display || msg.author_username}
          </button>
        )}

        <div
          className={"relative overflow-hidden rounded-sm text-sm " + (isImage || isVideo ? "" : " px-3 py-2")}
          style={bubbleStyle}
        >
          {msg.is_pinned && (
            <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">
              📌 pinned
            </div>
          )}

          {msg.reply_to_id && !msg.is_deleted && (
            <div
              className="mx-1 mb-2 mt-1 rounded-sm border-l-2 bg-black/50 px-2 py-1 text-[10px]"
              style={{ borderColor: accent }}
            >
              <div className="font-bold uppercase tracking-wider" style={{ color: accent }}>
                ↳ {msg.reply_author || "?"}
              </div>
              <div className="truncate text-cyber-dim">{msg.reply_preview || "..."}</div>
            </div>
          )}

          {isImage && msg.attachment && (
            <img
              src={fileUrl(msg.attachment.id)}
              alt={msg.attachment.filename}
              onClick={() => !isVirtual && onOpenImage(fileUrl(msg.attachment!.id))}
              className="block max-h-80 w-full cursor-pointer object-cover"
              loading="lazy"
              decoding="async"
            />
          )}

          {isVideo && msg.attachment && (
            <video
              src={fileUrl(msg.attachment.id)}
              controls
              preload="none"
              className="block max-h-80 w-full bg-black"
            />
          )}

          {isVoice && msg.attachment && (
            <div className="flex items-center gap-3 px-2 py-3" style={{ minWidth: 220 }}>
              <button
                onClick={() => {
                  const prev = (window as any).__voiceAudio as HTMLAudioElement;
                  if (prev && prev.dataset.id === String(msg.attachment!.id)) {
                    if (prev.paused) prev.play(); else prev.pause();
                    return;
                  }
                  if (prev) prev.pause();
                  const el = new Audio(fileUrl(msg.attachment!.id));
                  (window as any).__voiceAudio = el;
                  el.dataset.id = String(msg.attachment!.id);
                  el.ontimeupdate = () => setAudioCurrent(el.currentTime);
                  el.onloadedmetadata = () => setAudioDuration(el.duration);
                  el.onplay = () => setAudioPlaying(true);
                  el.onpause = () => setAudioPlaying(false);
                  el.onended = () => { setAudioPlaying(false); setAudioCurrent(0); };
                  el.play();
                }}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm neon-border"
                style={{ color: accent }}
              >
                {audioPlaying ? "❚❚" : "▶"}
              </button>
              <div className="flex-1 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-xl" style={{ color: accent }}>◍</span>
                  <span className="font-mono neon-text">
                    {fmtDuration(audioPlaying ? audioCurrent : (audioDuration || 0))}
                  </span>
                </div>
                <div className="mt-1 flex h-3 items-end gap-[2px]">
                  {Array.from({ length: 24 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-[2px]"
                      style={{
                        height: `${20 + ((i * 7) % 80)}%`,
                        background: accent,
                        opacity: audioPlaying ? 0.8 : 0.35,
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {isFile && msg.attachment && (
            <a
              href={fileUrl(msg.attachment.id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 px-2 py-2 transition hover:bg-cyber-cyan/5"
            >
              <div className="text-2xl" style={{ color: accent }}>
                {iconFor(msg.attachment.content_type)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold text-cyber-text text-readable">
                  {msg.attachment.filename}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-cyber-dim">
                  {humanSize(msg.attachment.size)}
                </div>
              </div>
            </a>
          )}

          {!isImage && !isVideo && !isVoice && !isFile && (
            <div className={"text-readable text-[13px] leading-relaxed " + (msg.is_deleted ? "italic opacity-60" : "break-words")}>
              {msg.is_deleted ? msg.text : renderMarkdown(msg.text || "")}
            </div>
          )}

          {hasReactions && (
            <div className="mt-2 flex flex-wrap gap-1">
              {msg.reactions.map((r) => (
                <button
                  key={r.emoji}
                  onClick={() => onReact(msg.id, r.emoji)}
                  className={
                    "flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs transition " +
                    (r.is_mine
                      ? "border-cyber-cyan bg-cyber-cyan/20 neon-text"
                      : "border-cyber-cyan/25 bg-black/40 text-cyber-text hover:border-cyber-cyan/60")
                  }
                >
                  <span>{r.emoji}</span>
                  <span className="text-[10px] font-bold">{r.count}</span>
                </button>
              ))}
            </div>
          )}

          <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">
            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}
            <span className="text-cyber-dim">
              {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            {mine && !msg.is_deleted && (
              <span className={
                isPending ? "text-cyber-dim" :
                isFailed ? "neon-text-mag" :
                readByPeer ? "neon-text" : "text-cyber-dim"
              }>
                {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
              </span>
            )}
          </div>
        </div>

        {!msg.is_deleted && !isVirtual && (
          <div
            className={
              "absolute top-1 hidden items-center gap-1 group-hover:flex " +
              (mine ? "right-full mr-1" : "left-full ml-1")
            }
          >
            <button
              onClick={() => setReactOpen(!reactOpen)}
              className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"
              title="Reaction"
            >
              ☺
            </button>
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"
              title="Menu"
            >
              ▾
            </button>
          </div>
        )}

        {reactOpen && (
          <div
            className={
              "absolute top-8 z-30 flex gap-1 rounded-sm border border-cyber-cyan/50 panel-solid p-1 " +
              (mine ? "right-0" : "left-0")
            }
            onMouseLeave={() => setReactOpen(false)}
          >
            {QUICK_REACTIONS.map((e) => (
              <button
                key={e}
                onClick={() => { onReact(msg.id, e); setReactOpen(false); }}
                className="rounded-sm p-1 text-lg transition hover:bg-cyber-cyan/20"
              >
                {e}
              </button>
            ))}
          </div>
        )}

        {menuOpen && (
          <div
            className={
              "absolute z-20 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +
              (mine ? "right-0" : "left-0")
            }
          >
            <button
              onClick={() => { onReply(msg); setMenuOpen(false); }}
              className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
            >
              ↳ reply
            </button>
            <button
              onClick={() => { onPin(msg); setMenuOpen(false); }}
              className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-yellow hover:bg-cyber-yellow/15"
            >
              📌 {msg.is_pinned ? "unpin" : "pin"}
            </button>
            {mine && msg.message_type === "text" && (
              <button
                onClick={() => { onEdit(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
              >
                ✎ edit
              </button>
            )}
            {mine && (
              <button
                onClick={() => { onDelete(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"
              >
                ✕ delete
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(MessageBubbleInner);
'''

T["frontend/src/MessageBubble.tsx"] = MESSAGEBUBBLE

# ============================================================== App — useScrolling + bg без blur
APP_REPLACEMENTS = [
    # 1. импорт хука
    (
        'import { useMessageQueue } from "./useMessageQueue";',
        'import { useMessageQueue } from "./useMessageQueue";\n    import { useScrolling } from "./useScrolling";',
    ),
    # 2. вызов хука внутри App
    (
        'const offerRef = useRef<RTCSessionDescriptionInit | null>(null);',
        'const offerRef = useRef<RTCSessionDescriptionInit | null>(null);\n\n      useScrolling();',
    ),
]

# ChatList — убрать backdrop-blur, заменить на плотный фон
CHATLIST_REPLACEMENTS = [
    (
        '<aside className="relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/25 bg-cyber-panel/92 backdrop-blur-md">',
        '<aside className="isolate-panel relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/25 panel-semi">',
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

    print("\nСпринт 11d — оптимизация скролла\n")

    src = root / "frontend" / "src"

    # CSS
    (src / "index.css").write_text(T["frontend/src/index.css"], encoding="utf-8")
    print(f"  ~ {src / 'index.css'}")

    # Новый хук
    (src / "useScrolling.ts").write_text(T["frontend/src/useScrolling.ts"], encoding="utf-8")
    print(f"  + {src / 'useScrolling.ts'}")

    # PixelCity — переписываем целиком
    (src / "PixelCity.tsx").write_text(T["frontend/src/PixelCity.tsx"], encoding="utf-8")
    print(f"  ~ {src / 'PixelCity.tsx'}")

    # ChatWindow + MessageBubble — переписываем целиком (memo + hooks)
    (src / "ChatWindow.tsx").write_text(T["frontend/src/ChatWindow.tsx"], encoding="utf-8")
    print(f"  ~ {src / 'ChatWindow.tsx'}")

    (src / "MessageBubble.tsx").write_text(T["frontend/src/MessageBubble.tsx"], encoding="utf-8")
    print(f"  ~ {src / 'MessageBubble.tsx'}")

    # Патчи
    patch_file(src / "App.tsx", APP_REPLACEMENTS)
    patch_file(src / "ChatList.tsx", CHATLIST_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())