#!/usr/bin/env python3
"""sprint11.py - pixel-art cyberpunk city with weather."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== PIXEL CITY
T["frontend/src/PixelCity.tsx"] = _t('''
    import { useEffect, useRef } from "react";

    export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

    const W = 480;
    const H = 270;

    type Building = { x: number; w: number; h: number; windows: [number, number, number][] };
    type Drop = { x: number; y: number; v: number; l: number };
    type Vehicle = { x: number; y: number; vx: number; hue: number };
    type Layer = { data: Building[]; par: number; tint: string; top: number; dim: number };

    function rngFrom(seed: number) {
      let s = (seed >>> 0) || 1;
      return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
    }

    function buildLayer(seed: number, minH: number, maxH: number, density: number): Building[] {
      const r = rngFrom(seed);
      const out: Building[] = [];
      let x = -15;
      while (x < W + 15) {
        const w = 10 + Math.floor(r() * 18);
        const h = minH + Math.floor(r() * (maxH - minH));
        const windows: [number, number, number][] = [];
        for (let wy = 4; wy < h - 3; wy += 3) {
          for (let wx = 2; wx < w - 2; wx += 3) {
            if (r() < density) {
              windows.push([wx, wy, Math.floor(r() * 3)]);
            }
          }
        }
        out.push({ x, w, h, windows });
        x += w + 1 + Math.floor(r() * 4);
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

    const SKY: Record<string, [string, string]> = {
      night: ["#03060c", "#0a1428"],
      dawn: ["#0d0514", "#2a0f33"],
      day: ["#12182a", "#242c44"],
      sunset: ["#1a0a14", "#40162a"],
    };

    const NEON = ["#00f0ff", "#ff00a0", "#fcee0a"];

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

      useEffect(() => {
        const canvas = ref.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        canvas.width = W;
        canvas.height = H;
        ctx.imageSmoothingEnabled = false;

        const layers: Layer[] = [
          { data: buildLayer(seed * 7 + 1, 15, 45, 0.10), par: 0.04, tint: "#0a0f1c", top: H - 10, dim: 0.5 },
          { data: buildLayer(seed * 7 + 2, 30, 75, 0.20), par: 0.10, tint: "#0d1524", top: H - 20, dim: 0.7 },
          { data: buildLayer(seed * 7 + 3, 50, 120, 0.35), par: 0.22, tint: "#0a1220", top: H - 40, dim: 0.85 },
          { data: buildLayer(seed * 7 + 4, 80, 190, 0.50), par: 0.40, tint: "#070d18", top: H - 60, dim: 1.0 },
        ];

        const effective: Weather = weather === "auto"
          ? (["clear", "rain", "rain", "snow", "smog"] as const)[new Date().getDate() % 5]
          : weather;

        const drops: Drop[] = [];
        const cars: Vehicle[] = [];
        let lightningT = 0;
        let flashAlpha = 0;

        if (effective === "rain" || effective === "storm") {
          const count = effective === "storm" ? 180 : 100;
          for (let i = 0; i < count; i++) {
            drops.push({
              x: Math.random() * W, y: Math.random() * H,
              v: 4 + Math.random() * 4, l: 3 + Math.random() * 3,
            });
          }
        } else if (effective === "snow") {
          for (let i = 0; i < 80; i++) {
            drops.push({
              x: Math.random() * W, y: Math.random() * H,
              v: 0.3 + Math.random() * 0.5, l: 1,
            });
          }
        }

        for (let i = 0; i < 6; i++) {
          cars.push({
            x: Math.random() * W,
            y: 20 + Math.random() * 60,
            vx: (Math.random() < 0.5 ? -1 : 1) * (0.3 + Math.random() * 0.6),
            hue: Math.floor(Math.random() * 3),
          });
        }

        const onMove = (e: MouseEvent) => {
          mouse.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
          mouse.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
        };
        window.addEventListener("mousemove", onMove);

        let raf = 0;
        let last = performance.now();

        const drawBuilding = (b: Building, layer: Layer, offsetX: number) => {
          const bx = Math.floor(b.x - offsetX);
          if (bx + b.w < 0 || bx > W) return;
          ctx.fillStyle = layer.tint;
          ctx.fillRect(bx, layer.top - b.h, b.w, b.h);

          const winPhase = Math.floor(Date.now() / 4000);
          for (let i = 0; i < b.windows.length; i++) {
            const [wx, wy, c] = b.windows[i];
            const blink = ((i * 31 + winPhase) % 12) === 0;
            if (blink && ((i * 7) % 3) !== 0) continue;
            const alpha = layer.dim * (0.5 + ((i * 13) % 5) * 0.1);
            ctx.fillStyle = NEON[c];
            ctx.globalAlpha = alpha;
            ctx.fillRect(bx + wx, layer.top - b.h + wy, 1, 1);
          }
          ctx.globalAlpha = 1;
        };

        const frame = (t: number) => {
          const dt = Math.min(50, t - last) / 1000;
          last = t;

          smooth.current.x += (mouse.current.x - smooth.current.x) * 0.05;
          smooth.current.y += (mouse.current.y - smooth.current.y) * 0.05;

          const p = phase();
          const [c1, c2] = SKY[p];
          const grad = ctx.createLinearGradient(0, 0, 0, H);
          grad.addColorStop(0, c1);
          grad.addColorStop(1, c2);
          ctx.fillStyle = grad;
          ctx.fillRect(0, 0, W, H);

          // Stars at night
          if (p === "night") {
            const r = rngFrom(12345);
            ctx.fillStyle = "#3a4a66";
            for (let i = 0; i < 40; i++) {
              const x = Math.floor(r() * W);
              const y = Math.floor(r() * (H * 0.5));
              ctx.globalAlpha = 0.4 + r() * 0.4;
              ctx.fillRect(x, y, 1, 1);
            }
            ctx.globalAlpha = 1;
          }

          // Moon / sun
          const sunX = Math.floor(W * 0.82);
          const sunY = p === "night" ? 40 : p === "dawn" ? Math.floor(H * 0.35) : p === "sunset" ? Math.floor(H * 0.4) : 50;
          ctx.fillStyle = p === "night" ? "#ddeeff" : p === "day" ? "#aab0c0" : "#ff8855";
          ctx.globalAlpha = 0.9;
          ctx.fillRect(sunX, sunY, 8, 8);
          ctx.globalAlpha = 1;

          // Buildings back-to-front
          for (const L of layers) {
            const offsetX = smooth.current.x * 20 * L.par;
            for (const b of L.data) drawBuilding(b, L, offsetX);
          }

          // Flying cars
          for (const c of cars) {
            c.x += c.vx * dt * 30;
            if (c.x < -20) c.x = W + 20;
            if (c.x > W + 20) c.x = -20;
            const y = c.y + Math.sin(t / 1000 + c.x * 0.01) * 2;
            ctx.fillStyle = NEON[c.hue];
            ctx.globalAlpha = 0.3;
            ctx.fillRect(Math.floor(c.x - c.vx * 6), Math.floor(y), 3, 1);
            ctx.globalAlpha = 0.9;
            ctx.fillRect(Math.floor(c.x), Math.floor(y), 1, 1);
          }
          ctx.globalAlpha = 1;

          // Weather
          if (effective === "rain" || effective === "storm") {
            ctx.strokeStyle = "#7ec8ff";
            ctx.globalAlpha = effective === "storm" ? 0.7 : 0.45;
            ctx.lineWidth = 1;
            ctx.beginPath();
            for (const d of drops) {
              d.y += d.v * dt * 60;
              d.x += 0.4;
              if (d.y > H) { d.y = -5; d.x = Math.random() * W; }
              ctx.moveTo(Math.floor(d.x), Math.floor(d.y));
              ctx.lineTo(Math.floor(d.x), Math.floor(d.y + d.l));
            }
            ctx.stroke();
            ctx.globalAlpha = 1;
          } else if (effective === "snow") {
            ctx.fillStyle = "#e8f4ff";
            for (const d of drops) {
              d.y += d.v * dt * 60;
              d.x += Math.sin((t + d.x * 10) / 800) * 0.3;
              if (d.y > H) { d.y = -2; d.x = Math.random() * W; }
              ctx.globalAlpha = 0.85;
              ctx.fillRect(Math.floor(d.x), Math.floor(d.y), 1, 1);
            }
            ctx.globalAlpha = 1;
          } else if (effective === "smog") {
            ctx.fillStyle = "rgba(80, 40, 100, 0.18)";
            ctx.fillRect(0, 0, W, H);
            ctx.fillStyle = "rgba(160, 80, 60, 0.10)";
            ctx.fillRect(0, Math.floor(H * 0.5), W, Math.floor(H * 0.5));
          }

          // Lightning
          if (effective === "storm") {
            lightningT += dt;
            if (flashAlpha > 0) flashAlpha -= dt * 8;
            if (lightningT > 4 + Math.random() * 5) {
              lightningT = 0;
              flashAlpha = 0.85;
              ctx.strokeStyle = "#ffffff";
              ctx.lineWidth = 1;
              ctx.globalAlpha = 0.9;
              ctx.beginPath();
              let bx = W * 0.3 + Math.random() * W * 0.4;
              let by = 0;
              ctx.moveTo(bx, by);
              while (by < H * 0.5) {
                bx += (Math.random() - 0.5) * 14;
                by += 4 + Math.random() * 8;
                ctx.lineTo(bx, by);
              }
              ctx.stroke();
              ctx.globalAlpha = 1;
            }
            if (flashAlpha > 0) {
              ctx.fillStyle = `rgba(200, 220, 255, ${flashAlpha * 0.5})`;
              ctx.fillRect(0, 0, W, H);
            }
          }

          // Vignette
          const vg = ctx.createRadialGradient(W / 2, H / 2, 40, W / 2, H / 2, W * 0.75);
          vg.addColorStop(0, "rgba(0,0,0,0)");
          vg.addColorStop(1, "rgba(0,0,0,0.65)");
          ctx.fillStyle = vg;
          ctx.fillRect(0, 0, W, H);

          raf = requestAnimationFrame(frame);
        };

        raf = requestAnimationFrame(frame);

        return () => {
          cancelAnimationFrame(raf);
          window.removeEventListener("mousemove", onMove);
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

# ============================================================== CYBER BACKGROUND — добавить weather param, оставить grid
T["frontend/src/CyberBackground.tsx"] = _t('''
    export default function CyberBackground() {
      const streams = [
        { left: "3%",  delay: "0s",   dur: "14s", text: "01101 ДАННЫЕ ПОТОК 1101" },
        { left: "18%", delay: "-4s",  dur: "18s", text: "СИГНАЛ 0x00A4F2 ЗАХВАЧЕН" },
        { left: "37%", delay: "-9s",  dur: "16s", text: "01 СЕАНС АКТИВЕН 110100101" },
        { left: "62%", delay: "-2s",  dur: "20s", text: "ПРОТОКОЛ СВЯЗИ ОК 0xCC" },
        { left: "78%", delay: "-6s",  dur: "15s", text: "01001 ШИФР 1010 КЛЮЧ" },
        { left: "94%", delay: "-11s", dur: "17s", text: "ПАКЕТЫ 1101 ДОСТАВЛЕНЫ" },
      ];

      return (
        <div className="cyber-bg">
          <div className="scanlines" />
          <div className="scan-beam" />

          {/* Провода по углам */}
          <svg
            className="pointer-events-none absolute left-0 top-0 h-64 w-64 opacity-40"
            viewBox="0 0 200 200"
            fill="none"
          >
            <path className="wire-dash wire-glow" d="M-10 40 Q 60 40 90 20 T 210 -10" stroke="#00f0ff" strokeWidth="1.2" />
            <path className="wire-dash" d="M-10 70 Q 40 70 60 50 T 210 30" stroke="#ff00a0" strokeWidth="0.8" />
            <path className="wire-dash" d="M-10 100 Q 30 100 50 80 T 210 60" stroke="#00f0ff" strokeWidth="0.6" opacity="0.6" />
          </svg>

          <svg
            className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 opacity-40"
            viewBox="0 0 220 220"
            fill="none"
          >
            <path className="wire-dash wire-glow-mag" d="M230 180 Q 160 180 130 200 T -10 230" stroke="#ff00a0" strokeWidth="1.2" />
            <path className="wire-dash" d="M230 150 Q 180 150 160 170 T -10 200" stroke="#00f0ff" strokeWidth="0.8" />
            <path className="wire-dash" d="M230 120 Q 190 120 175 140 T -10 170" stroke="#fcee0a" strokeWidth="0.6" opacity="0.6" />
          </svg>

          {streams.map((s, i) => (
            <div
              key={i}
              className="data-stream"
              style={{ left: s.left, animationDelay: s.delay, animationDuration: s.dur }}
            >
              {s.text}
            </div>
          ))}

          {/* Уголки в углах экрана */}
          <div className="absolute left-3 top-3 h-4 w-4 border-l-2 border-t-2 border-cyber-cyan/50" />
          <div className="absolute right-3 top-3 h-4 w-4 border-r-2 border-t-2 border-cyber-cyan/50" />
          <div className="absolute left-3 bottom-3 h-4 w-4 border-l-2 border-b-2 border-cyber-magenta/50" />
          <div className="absolute right-3 bottom-3 h-4 w-4 border-r-2 border-b-2 border-cyber-magenta/50" />
        </div>
    );
''')

# ============================================================== INDEX.CSS — градиент фона полупрозрачный, чтобы город было видно
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
      --text-primary: #b8d4e8;
    }

    html, body, #root { height: 100%; margin: 0; }

    body {
      font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
      background: var(--bg-deep);
      color: #b8d4e8;
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

    /* ============= Scanlines ============= */
    .scanlines {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(0,240,255,0.025) 3px,
        transparent 4px
      );
      mix-blend-mode: screen;
    }
    .scan-beam {
      position: absolute;
      left: 0;
      right: 0;
      height: 120px;
      background: linear-gradient(180deg, transparent, rgba(0,240,255,0.08), transparent);
      animation: scan-move 7s linear infinite;
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
    }
    .glitch::before {
      color: var(--neon-magenta);
      animation: glitch-a 2.8s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
      text-shadow: 0 0 6px var(--neon-magenta);
    }
    .glitch::after {
      color: var(--neon-cyan);
      animation: glitch-b 3.6s infinite steps(2) alternate-reverse;
      clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
      text-shadow: 0 0 6px var(--neon-cyan);
    }
    @keyframes glitch-a {
      0%   { transform: translate(0); }
      20%  { transform: translate(-2px, 1px); }
      40%  { transform: translate(-1px, -1px); }
      60%  { transform: translate(2px, 1px); }
      80%  { transform: translate(1px, -1px); }
      100% { transform: translate(0); }
    }
    @keyframes glitch-b {
      0%   { transform: translate(0); }
      25%  { transform: translate(2px, -1px); }
      50%  { transform: translate(1px, 1px); }
      75%  { transform: translate(-2px, 1px); }
      100% { transform: translate(0); }
    }

    /* ============= Neon glow ============= */
    .neon-text       { color: var(--neon-cyan);    text-shadow: 0 0 6px rgba(0,240,255,0.7); }
    .neon-text-mag   { color: var(--neon-magenta); text-shadow: 0 0 6px rgba(255,0,160,0.7); }
    .neon-text-yel   { color: var(--neon-yellow);  text-shadow: 0 0 6px rgba(252,238,10,0.7); }

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
    .flicker { animation: flicker 5s infinite; }
    @keyframes flicker {
      0%,89%,100% { opacity: 1; }
      90%         { opacity: 0.4; }
      91%         { opacity: 1; }
      93%         { opacity: 0.6; }
      94%         { opacity: 1; }
      96%         { opacity: 0.85; }
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
      color: rgba(0,240,255,0.18);
      white-space: nowrap;
      pointer-events: none;
      writing-mode: vertical-rl;
      text-orientation: mixed;
      animation: stream-fall 15s linear infinite;
    }
    @keyframes stream-fall {
      from { transform: translateY(-100%); }
      to   { transform: translateY(100vh); }
    }

    .wire-dash { stroke-dasharray: 6 10; animation: dash-move 30s linear infinite; }
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
      background: rgba(0,240,255,0.03);
      border: 1px solid rgba(0,240,255,0.25);
      color: #d6ecff;
      transition: all 0.15s;
      font-family: inherit;
    }
    .cyber-input:focus {
      outline: none;
      border-color: var(--neon-cyan);
      box-shadow: 0 0 12px rgba(0,240,255,0.4), inset 0 0 8px rgba(0,240,255,0.08);
      background: rgba(0,240,255,0.06);
    }
    .cyber-input::placeholder { color: rgba(90,122,149,0.7); letter-spacing: 0.1em; }

    .cyber-btn {
      background: rgba(0,240,255,0.08);
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
      background: rgba(255,0,160,0.08);
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
        rgba(10,15,26,0.85);
      border: 1px solid rgba(0,240,255,0.18);
      backdrop-filter: blur(4px);
    }

    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }
''')

# ============================================================== SETTINGS — добавить вкладку City
T["frontend/src/SettingsPanel.tsx"] = _t('''
    import { useState } from "react";
    import { api } from "./api";
    import { THEMES } from "./themes";
    import type { Chat, ThemeName, User } from "./types";
    import type { Weather } from "./PixelCity";

    const WEATHERS: { value: Weather; label: string }[] = [
      { value: "auto",   label: "◇ auto" },
      { value: "clear",  label: "☀ clear" },
      { value: "rain",   label: "☂ rain" },
      { value: "snow",   label: "❄ snow" },
      { value: "smog",   label: "░ smog" },
      { value: "storm",  label: "⚡ storm" },
    ];

    export default function SettingsPanel({
      currentUser, chats, onClose, onChatsChanged, onSelectChat,
      theme, setTheme, cityWeather, setCityWeather,
    }: {
      currentUser: User;
      chats: Chat[];
      onClose: () => void;
      onChatsChanged: (c: Chat[]) => void;
      onSelectChat: (id: number) => void;
      theme: ThemeName;
      setTheme: (t: ThemeName) => void;
      cityWeather: Weather;
      setCityWeather: (w: Weather) => void;
    }) {
      const [tab, setTab] = useState<"search" | "group" | "theme" | "city">("search");
      const [query, setQuery] = useState("");
      const [results, setResults] = useState<User[]>([]);
      const [error, setError] = useState("");

      const [groupTitle, setGroupTitle] = useState("");
      const [groupMembers, setGroupMembers] = useState("");
      const [groupDesc, setGroupDesc] = useState("");

      const searchUsers = async (q: string) => {
        setQuery(q);
        if (!q.trim()) { setResults([]); return; }
        const { data } = await api.get<User[]>("/users", { params: { q, limit: 20 } });
        setResults(data);
      };

      const startDirect = async (u: User) => {
        setError("");
        try {
          const { data } = await api.post<Chat>("/chats", { is_group: false, member_usernames: [u.username] });
          const all = await api.get<Chat[]>("/chats");
          onChatsChanged(all.data);
          onSelectChat(data.id);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const createGroup = async () => {
        setError("");
        if (!groupTitle.trim()) { setError("Нужно название"); return; }
        try {
          const names = groupMembers.split(",").map((s) => s.trim()).filter(Boolean);
          const { data } = await api.post<Chat>("/chats", {
            title: groupTitle,
            description: groupDesc || null,
            is_group: true,
            member_usernames: names,
          });
          const all = await api.get<Chat[]>("/chats");
          onChatsChanged(all.data);
          onSelectChat(data.id);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const input = "cyber-input w-full rounded-sm px-3 py-2 text-sm";

      const tabCls = (active: boolean) =>
        "flex-1 py-3 text-[10px] font-bold uppercase tracking-widest transition " +
        (active
          ? "text-cyber-cyan border-b-2 border-cyber-cyan bg-cyber-cyan/5"
          : "text-cyber-dim hover:text-cyber-cyan hover:bg-cyber-cyan/5");

      return (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4 backdrop-blur" onClick={onClose}>
          <div
            className="corner-frame animate-materialize flex h-[600px] w-[680px] flex-col rounded-sm border border-cyber-cyan/50 bg-cyber-panel shadow-neon-cyan"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-cyber-cyan/20 p-4">
              <h2 className="text-sm font-bold uppercase tracking-widest neon-text">⚙ settings</h2>
              <button onClick={onClose} className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15">✕</button>
            </div>

            <div className="flex border-b border-cyber-cyan/20">
              <button onClick={() => setTab("search")} className={tabCls(tab === "search")}>◉ search</button>
              <button onClick={() => setTab("group")} className={tabCls(tab === "group")}>◉ group</button>
              <button onClick={() => setTab("theme")} className={tabCls(tab === "theme")}>◉ theme</button>
              <button onClick={() => setTab("city")} className={tabCls(tab === "city")}>◉ city</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tab === "search" && (
                <>
                  <input
                    className={input}
                    placeholder="SEARCH OPERATOR"
                    value={query}
                    onChange={(e) => searchUsers(e.target.value)}
                    autoFocus
                  />
                  {results.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {results.map((u) => (
                        <button
                          key={u.id}
                          onClick={() => startDirect(u)}
                          className="flex w-full items-center gap-3 rounded-sm border border-cyber-cyan/20 p-2 text-left transition hover:border-cyber-cyan hover:bg-cyber-cyan/5"
                        >
                          <div>
                            <div className="text-sm font-bold text-cyber-text">
                              {u.display_name || u.username}
                            </div>
                            <div className="text-[10px] uppercase tracking-widest text-cyber-dim">
                              @{u.username}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}

              {tab === "group" && (
                <div className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // title
                    </label>
                    <input className={input} placeholder="e.g. NIGHT CITY" value={groupTitle} onChange={(e) => setGroupTitle(e.target.value)} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // description
                    </label>
                    <input className={input} placeholder="optional" value={groupDesc} onChange={(e) => setGroupDesc(e.target.value)} />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // members (comma separated)
                    </label>
                    <input className={input} placeholder="alice, bob, carol" value={groupMembers} onChange={(e) => setGroupMembers(e.target.value)} />
                  </div>
                  <button onClick={createGroup} className="cyber-btn w-full rounded-sm py-2 text-xs">
                    [ CREATE GROUP ]
                  </button>
                </div>
              )}

              {tab === "theme" && (
                <div className="space-y-3">
                  <div className="text-[10px] uppercase tracking-widest text-cyber-dim mb-2">
                    // choose terminal skin
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {THEMES.map((t) => (
                      <button
                        key={t.name}
                        onClick={() => setTheme(t.name)}
                        className={
                          "rounded-sm border p-3 text-left transition " +
                          (theme === t.name
                            ? "border-cyber-cyan bg-cyber-cyan/15 shadow-neon-cyan"
                            : "border-cyber-cyan/25 hover:border-cyber-cyan/60")
                        }
                      >
                        <div className="text-xs font-bold uppercase tracking-widest" style={{ color: t.vars["--neon-cyan"] }}>
                          {t.label}
                        </div>
                        <div className="mt-2 flex gap-1">
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-cyan"] }} />
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-magenta"] }} />
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-yellow"] }} />
                          <div className="h-3 w-3 rounded-sm border border-white/20" style={{ background: t.vars["--bg-deep"] }} />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {tab === "city" && (
                <div className="space-y-3">
                  <div className="text-[10px] uppercase tracking-widest text-cyber-dim">
                    // weather over the city
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    {WEATHERS.map((w) => (
                      <button
                        key={w.value}
                        onClick={() => setCityWeather(w.value)}
                        className={
                          "rounded-sm border px-3 py-2 text-xs font-bold uppercase tracking-widest transition " +
                          (cityWeather === w.value
                            ? "border-cyber-cyan bg-cyber-cyan/15 neon-text"
                            : "border-cyber-cyan/25 text-cyber-dim hover:border-cyber-cyan/60 hover:text-cyber-cyan")
                        }
                      >
                        {w.label}
                      </button>
                    ))}
                  </div>
                  <div className="mt-4 rounded-sm border border-cyber-cyan/20 bg-black/30 p-3 text-[10px] leading-relaxed text-cyber-dim">
                    <div className="mb-1 neon-text">// about pixel-city</div>
                    Живой мегаполис за интерфейсом: 3 слоя зданий с parallax,
                    мигающие окна, летающие машины. Меняется по времени суток
                    (рассвет / день / закат / ночь). Погода влияет на атмосферу.
                  </div>
                  <div className="mt-3 text-[10px] uppercase tracking-widest text-cyber-dim">
                    <div>channels: {chats.length}</div>
                    <div>operator: @{currentUser.username}</div>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-3 rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}
            </div>
          </div>
        </div>
    );
''')

# ============================================================== APP — подключить PixelCity
T["frontend/src/App.tsx"] = _t('''
    import { useCallback, useEffect, useMemo, useRef, useState } from "react";
    import Login from "./Login";
    import ChatList from "./ChatList";
    import ChatWindow from "./ChatWindow";
    import ProfileModal from "./ProfileModal";
    import SettingsPanel from "./SettingsPanel";
    import GroupInfoPanel from "./GroupInfoPanel";
    import Feed from "./Feed";
    import ProfilePage from "./ProfilePage";
    import IncomingCallModal from "./IncomingCallModal";
    import CallWindow from "./CallWindow";
    import CyberBackground from "./CyberBackground";
    import PixelCity, { type Weather } from "./PixelCity";
    import CommandPalette, { type Command } from "./CommandPalette";
    import { api } from "./api";
    import { useWebSocket } from "./ws";
    import { useWebRTC } from "./useWebRTC";
    import { useMessageQueue } from "./useMessageQueue";
    import { applyTheme } from "./themes";
    import { ensureNotificationPermission, showNotification, playPing } from "./notifications";
    import type { CallInfo, Chat, ThemeName, User } from "./types";

    type Mode = "chats" | "feed" | "profile";

    export default function App() {
      const [user, setUser] = useState<User | null>(null);
      const [chats, setChats] = useState<Chat[]>([]);
      const [activeChatId, setActiveChatId] = useState<number | null>(null);
      const [loading, setLoading] = useState(true);
      const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());
      const [showProfile, setShowProfile] = useState(false);
      const [showSettings, setShowSettings] = useState(false);
      const [showGroupInfo, setShowGroupInfo] = useState(false);
      const [showCommandPalette, setShowCommandPalette] = useState(false);
      const [theme, setTheme] = useState<ThemeName>(
        (localStorage.getItem("theme") as ThemeName) || "cyber"
      );
      const [cityWeather, setCityWeather] = useState<Weather>(
        (localStorage.getItem("city_weather") as Weather) || "auto"
      );
      const [mode, setMode] = useState<Mode>("chats");
      const [profileUserId, setProfileUserId] = useState<number | null>(null);
      const [incomingCall, setIncomingCall] = useState<CallInfo | null>(null);
      const [callDuration, setCallDuration] = useState(0);
      const offerRef = useRef<RTCSessionDescriptionInit | null>(null);

      useEffect(() => {
        applyTheme(theme);
        localStorage.setItem("theme", theme);
      }, [theme]);

      useEffect(() => {
        localStorage.setItem("city_weather", cityWeather);
      }, [cityWeather]);

      useEffect(() => {
        if (user) ensureNotificationPermission();
      }, [user]);

      useEffect(() => {
        const h = (e: KeyboardEvent) => {
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            setShowCommandPalette((v) => !v);
          }
          if (e.key === "Escape") setShowCommandPalette(false);
        };
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, []);

      const onWs = useCallback((d: any) => {
        if (d.type === "presence") {
          setOnlineUsers((prev) => {
            const next = new Set(prev);
            if (d.online) next.add(d.user_id);
            else next.delete(d.user_id);
            return next;
          });
        } else if (d.type === "message") {
          setChats((prev) => prev.map((c) =>
            c.id === d.chat_id
              ? {
                  ...c,
                  last_message: { ...c.last_message, ...d } as any,
                  unread_count: c.id === activeChatId || d.author_id === user?.id || d.message_type === "system"
                    ? c.unread_count
                    : c.unread_count + 1,
                }
              : c
          ));
          if (user && d.author_id !== user.id && d.message_type !== "system") {
            playPing();
            showNotification(
              d.author_display || d.author_username,
              d.message_type === "text" ? (d.text || "").slice(0, 120) :
              d.message_type === "image" ? "▣ Image" :
              d.message_type === "voice" ? "◍ Voice" :
              d.message_type === "file" ? "▤ File" : "◈ Sticker",
              `chat-${d.chat_id}`
            );
          }
        } else if (d.type === "call:incoming") {
          setIncomingCall({
            id: d.call_id,
            caller_id: d.caller.id,
            callee_id: user?.id ?? 0,
            kind: d.kind,
            status: "ringing",
            started_at: null, ended_at: null, duration_sec: null,
            created_at: new Date().toISOString(),
            caller: d.caller,
            callee: { id: user?.id ?? 0, username: user?.username ?? "", display_name: user?.display_name ?? null, avatar_color: user?.avatar_color ?? null },
          });
          if (user) {
            playPing();
            showNotification(
              "◈ INCOMING CALL",
              `${d.caller.display_name || d.caller.username} · ${d.kind === "video" ? "VIDEO" : "AUDIO"}`,
              "call"
            );
          }
        }
      }, [activeChatId, user?.id, user?.username, user?.display_name, user?.avatar_color]);

      const { send, subscribe, readyState } = useWebSocket(onWs, user?.id ?? null);
      const rtc = useWebRTC(send, subscribe);

      const isWsOpen = useCallback(() => readyState === WebSocket.OPEN, [readyState]);
      const queue = useMessageQueue(user?.id ?? null, send, isWsOpen);

      const enqueueForChat = useCallback((
        chatId: number, text: string | null, messageType: string,
        attachmentId: number | null, replyToId: number | null,
      ) => {
        if (!user) return;
        queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {
          id: user.id, username: user.username,
          display_name: user.display_name,
          avatar_color: user.avatar_color,
        });
      }, [queue, user]);

      useEffect(() => {
        if (rtc.status !== "active") { setCallDuration(0); return; }
        const start = Date.now();
        const int = window.setInterval(() => setCallDuration(Math.floor((Date.now() - start) / 1000)), 1000);
        return () => window.clearInterval(int);
      }, [rtc.status]);

      const refreshChats = useCallback(async () => {
        const { data } = await api.get<Chat[]>("/chats");
        setChats(data);
      }, []);

      const loadMe = useCallback(async () => {
        try {
          const me = await api.get<User>("/auth/me");
          setUser(me.data);
          await refreshChats();
        } catch {
          setUser(null);
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
        } finally {
          setLoading(false);
        }
      }, [refreshChats]);

      useEffect(() => {
        loadMe();
        const logout = () => setUser(null);
        window.addEventListener("auth:logout", logout);
        return () => window.removeEventListener("auth:logout", logout);
      }, [loadMe]);

      useEffect(() => {
        if (!user) return;
        const params = new URLSearchParams(window.location.search);
        const invite = params.get("invite");
        if (!invite) return;
        api.post<Chat>(`/chats/join/${invite}`).then((r) => {
          refreshChats().then(() => { setActiveChatId(r.data.id); setMode("chats"); });
          window.history.replaceState({}, "", "/");
        }).catch(() => { window.history.replaceState({}, "", "/"); });
      }, [user, refreshChats]);

      useEffect(() => {
        if (activeChatId !== null && mode === "chats") {
          api.post(`/chats/${activeChatId}/read`).then(() => refreshChats()).catch(() => {});
        }
      }, [activeChatId, refreshChats, mode]);

      const logout = async () => {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try { await api.post("/auth/logout", { refresh_token: refresh }); } catch {}
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        setUser(null); setChats([]); setActiveChatId(null);
        setMode("chats"); setProfileUserId(null);
      };

      const openProfile = (userId: number) => { setProfileUserId(userId); setMode("profile"); };

      const chatWithUser = async (userId: number) => {
        try {
          const { data: p } = await api.get<{ username: string }>(`/users/${userId}/profile`);
          const { data } = await api.post<Chat>("/chats", { is_group: false, member_usernames: [p.username] });
          const all = await api.get<Chat[]>("/chats");
          setChats(all.data); setActiveChatId(data.id); setMode("chats");
        } catch {}
      };

      const startCall = async (kind: "audio" | "video") => {
        const chat = chats.find((c) => c.id === activeChatId);
        if (!chat || !chat.peer) return;
        try {
          const { data } = await api.post<CallInfo>("/calls", { callee_id: chat.peer.id, kind });
          await rtc.startCall(data.id, chat.peer.id, chat.peer.display_name || chat.peer.username, kind);
        } catch (e: any) {
          alert(e.response?.data?.detail || "Не удалось начать звонок");
        }
      };

      const acceptIncoming = async () => {
        const c = incomingCall;
        if (!c) return;
        try {
          await api.post(`/calls/${c.id}/accept`);
          offerRef.current = null;
          setIncomingCall(null);

          const off = subscribe(async (d) => {
            if (d.type === "webrtc:offer" && d.call_id === c.id) {
              off();
              await rtc.acceptCall(
                c.id, c.caller.id,
                c.caller.display_name || c.caller.username,
                c.kind, d.payload as RTCSessionDescriptionInit,
              );
            }
          });
        } catch (e: any) {
          alert(e.response?.data?.detail || "Не удалось принять");
          setIncomingCall(null);
        }
      };

      const rejectIncoming = async () => {
        const c = incomingCall;
        if (!c) return;
        setIncomingCall(null);
        try { await api.post(`/calls/${c.id}/reject`); } catch {}
      };

      const endCurrentCall = async () => {
        const s = rtc.session;
        rtc.endCall(true);
        if (s) {
          try { await api.post(`/calls/${s.callId}/end`); } catch {}
        }
      };

      const commands: Command[] = useMemo(() => {
        const list: Command[] = [
          { id: "feed", label: "Open feed", icon: "📰", action: () => setMode("feed") },
          { id: "profile", label: "Open my profile", icon: "👤", action: () => { setProfileUserId(user?.id ?? null); setMode("profile"); } },
          { id: "settings", label: "Open settings", icon: "⚙", action: () => setShowSettings(true) },
          { id: "theme-cyber", label: "Theme: Cyber", icon: "◈", action: () => setTheme("cyber") },
          { id: "theme-matrix", label: "Theme: Matrix", icon: "▶", action: () => setTheme("matrix") },
          { id: "theme-sunset", label: "Theme: Sunset", icon: "☀", action: () => setTheme("sunset") },
          { id: "theme-amber", label: "Theme: Amber", icon: "◆", action: () => setTheme("amber") },
          { id: "city-clear", label: "Weather: Clear", icon: "☀", action: () => setCityWeather("clear") },
          { id: "city-rain", label: "Weather: Rain", icon: "☂", action: () => setCityWeather("rain") },
          { id: "city-snow", label: "Weather: Snow", icon: "❄", action: () => setCityWeather("snow") },
          { id: "city-smog", label: "Weather: Smog", icon: "░", action: () => setCityWeather("smog") },
          { id: "city-storm", label: "Weather: Storm", icon: "⚡", action: () => setCityWeather("storm") },
          { id: "retry-failed", label: "Retry failed messages", icon: "🔁", action: () => queue.retryFailed() },
          { id: "logout", label: "Logout", icon: "✕", action: logout },
        ];
        chats.slice(0, 20).forEach((c) => {
          list.unshift({
            id: `chat-${c.id}`,
            label: c.peer ? (c.peer.display_name || c.peer.username) : (c.title || `Chat ${c.id}`),
            hint: `> open channel #${c.id}`,
            icon: "💬",
            action: () => { setActiveChatId(c.id); setMode("chats"); },
          });
        });
        return list;
      }, [chats, user?.id, queue]);

      if (loading) {
        return (
          <>
            <PixelCity weather={cityWeather} seed={user?.id ?? 1} />
            <CyberBackground />
            <div className="relative z-10 flex h-screen items-center justify-center">
              <div className="text-center">
                <div className="mb-4 text-5xl flicker neon-text">◈</div>
                <div className="text-xs uppercase tracking-[0.4em] neon-text cursor">
                  establishing link
                </div>
              </div>
            </div>
          </>
        );
      }

      if (!user) {
        return (
          <>
            <PixelCity weather={cityWeather} seed={1} />
            <CyberBackground />
            <Login onLogin={loadMe} />
          </>
        );
      }

      const activeChat = chats.find((c) => c.id === activeChatId) || null;
      const inCall = rtc.session !== null && (rtc.status === "connecting" || rtc.status === "active" || rtc.status === "ringing");
      const failedTotal = queue.queue.filter((m) => m.status === "failed").length;

      return (
        <>
          <PixelCity weather={cityWeather} seed={user?.id ?? 1} />
          <CyberBackground />
          <div className="relative z-10 flex h-screen">
            <ChatList
              chats={chats}
              activeId={activeChatId}
              onSelect={(id) => { setActiveChatId(id); setMode("chats"); }}
              onlineUsers={onlineUsers}
              currentUser={user}
              onOpenProfile={() => setShowProfile(true)}
              onOpenSettings={() => setShowSettings(true)}
              onOpenFeed={() => setMode("feed")}
              onOpenMyProfile={() => { setProfileUserId(user.id); setMode("profile"); }}
              mode={mode}
              failedQueue={failedTotal}
            />

            {mode === "chats" && (
              activeChat ? (
                <ChatWindow
                  key={activeChat.id}
                  chat={activeChat}
                  currentUser={user}
                  send={send}
                  subscribe={subscribe}
                  onlineUsers={onlineUsers}
                  onOpenInfo={() => setShowGroupInfo(true)}
                  onOpenUser={openProfile}
                  onStartCall={startCall}
                  queuedMessages={queue.queue}
                  onEnqueue={enqueueForChat}
                  onRemoveQueued={queue.removeByClientId}
                />
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center">
                  <div className="text-7xl flicker neon-text mb-6">◈</div>
                  <div className="text-sm uppercase tracking-[0.4em] neon-text">
                    select channel
                  </div>
                  <div className="mt-2 text-[10px] uppercase tracking-widest text-cyber-dim">
                    // no active link
                  </div>
                  <button
                    onClick={() => setShowSettings(true)}
                    className="cyber-btn mt-6 rounded-sm px-6 py-2 text-xs"
                  >
                    [ start transmission ]
                  </button>
                  <div className="mt-4 text-[10px] uppercase tracking-widest text-cyber-dim">
                    press <span className="neon-text">ctrl+k</span> for commands
                  </div>
                </div>
              )
            )}

            {mode === "feed" && (
              <div className="flex-1 overflow-y-auto">
                <Feed currentUser={user} onOpenProfile={openProfile} />
              </div>
            )}

            {mode === "profile" && profileUserId !== null && (
              <ProfilePage
                userId={profileUserId}
                currentUser={user}
                onBack={() => { setMode("chats"); setProfileUserId(null); }}
                onOpenProfile={openProfile}
                onChatWith={chatWithUser}
              />
            )}

            {showProfile && (
              <ProfileModal
                user={user}
                onClose={() => setShowProfile(false)}
                onUpdate={(u) => { setUser(u); refreshChats(); }}
                onLogout={() => { setShowProfile(false); logout(); }}
              />
            )}

            {showSettings && (
              <SettingsPanel
                currentUser={user}
                chats={chats}
                theme={theme}
                setTheme={setTheme}
                cityWeather={cityWeather}
                setCityWeather={setCityWeather}
                onClose={() => setShowSettings(false)}
                onChatsChanged={setChats}
                onSelectChat={(id) => { setActiveChatId(id); setMode("chats"); }}
              />
            )}

            {showGroupInfo && activeChat && (
              <GroupInfoPanel
                chat={activeChat}
                currentUser={user}
                onClose={() => setShowGroupInfo(false)}
                onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}
                onLeft={() => { setActiveChatId(null); refreshChats(); }}
              />
            )}

            {incomingCall && !rtc.session && (
              <IncomingCallModal
                caller={incomingCall.caller}
                kind={incomingCall.kind}
                onAccept={acceptIncoming}
                onReject={rejectIncoming}
              />
            )}

            {inCall && rtc.session && (
              <CallWindow
                peerName={rtc.session.peerName}
                kind={rtc.session.kind}
                status={rtc.status}
                localStream={rtc.localStream}
                remoteStream={rtc.remoteStream}
                muted={rtc.muted}
                camOff={rtc.camOff}
                sharing={rtc.sharing}
                durationSec={callDuration}
                onToggleMute={rtc.toggleMute}
                onToggleCamera={rtc.toggleCamera}
                onToggleScreen={rtc.toggleScreenShare}
                onEnd={endCurrentCall}
              />
            )}

            {showCommandPalette && (
              <CommandPalette
                commands={commands}
                onClose={() => setShowCommandPalette(false)}
              />
            )}
          </div>
        </>
      );
    }
''')


def write_all(root: Path) -> tuple[int, int]:
    created = updated = 0
    for rel, content in T.items():
        target = root / rel
        existed = target.exists()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print(f"  {'~' if existed else '+'} {rel}")
            if existed: updated += 1
            else: created += 1
        except OSError as e:
            print(f"ERR {rel}: {e}", file=sys.stderr)
    return created, updated


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 11: pixel-art cyberpunk city + weather")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())