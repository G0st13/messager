#!/usr/bin/env python3
"""sprint11b.py - detailed pixel-art city v2."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIXEL_CITY = r'''import { useEffect, useRef } from "react";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const W = 640;
const H = 360;

type Window = { x: number; y: number; w: number; h: number; c: number; bright: number };
type Sign = { x: number; y: number; text: string; c: number; blink: boolean };
type Building = {
  x: number; w: number; h: number;
  windows: Window[];
  signs: Sign[];
  antenna: boolean;
  antennaH: number;
  roofBox: boolean;
  waterTower: boolean;
  pipes: number;
  smokestack: number; // 0 = нет
};
type Drop = { x: number; y: number; v: number; l: number };
type Vehicle = { x: number; y: number; vx: number; hue: number; size: number };
type Person = { x: number; vx: number; h: number };
type GroundCar = { x: number; vx: number; hue: number };
type Hologram = { x: number; y: number; w: number; h: number; c: number; glitch: number };
type Cloud = { x: number; y: number; w: number; h: number; v: number; alpha: number };
type Smoke = { x: number; y: number; v: number; life: number };

const NEON = ["#00f0ff", "#ff00a0", "#fcee0a", "#7cff00", "#ff6600", "#b967ff"];
const SIGN_WORDS = ["CYBER", "NEON", "BAR", "RAMEN", "2077", "HOTEL", "NIGHT", "KIROSHI", "DATA", "CLUB", "NOODLE", "SUSHI"];
const SIGN_CHARS = "01XZ▲◆●λΣ";

function rngFrom(seed: number) {
  let s = (seed >>> 0) || 1;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}

function pick<T>(r: () => number, arr: T[]): T {
  return arr[Math.floor(r() * arr.length)];
}

function buildLayer(
  seed: number, minH: number, maxH: number, density: number, maxW: number, signsDensity: number,
): Building[] {
  const r = rngFrom(seed);
  const out: Building[] = [];
  let x = -20;
  while (x < W + 20) {
    const w = 14 + Math.floor(r() * maxW);
    const h = minH + Math.floor(r() * (maxH - minH));
    const windows: Window[] = [];

    // Окна разного размера: 1x1, 2x1, 1x2
    for (let wy = 4; wy < h - 4; wy += 4) {
      for (let wx = 3; wx < w - 3; wx += 4) {
        if (r() > density) continue;
        const tw = r() < 0.15 ? 2 : 1;
        const th = r() < 0.15 ? 2 : 1;
        const c = r() < 0.6
          ? (r() < 0.5 ? 3 : 2) // cyan-ish (indices into NEON for tint)
          : (r() < 0.5 ? 2 : 4);
        const bright = 0.5 + r() * 0.5;
        windows.push({ x: wx, y: wy, w: tw, h: th, c, bright });
      }
    }

    // Неоновые вывески
    const signs: Sign[] = [];
    if (r() < signsDensity && h > 40) {
      const count = 1 + Math.floor(r() * 2);
      for (let i = 0; i < count; i++) {
        signs.push({
          x: 1 + Math.floor(r() * Math.max(1, w - 18)),
          y: 6 + Math.floor(r() * (h - 20)),
          text: pick(r, SIGN_WORDS),
          c: Math.floor(r() * NEON.length),
          blink: r() < 0.5,
        });
      }
    }

    const antenna = r() < 0.35 && h > 50;
    const antennaH = 6 + Math.floor(r() * 14);
    const roofBox = r() < 0.4;
    const waterTower = r() < 0.15 && h > 60;
    const pipes = r() < 0.5 ? 1 + Math.floor(r() * 2) : 0;
    const smokestack = r() < 0.1 ? 3 + Math.floor(r() * 4) : 0;

    out.push({ x, w, h, windows, signs, antenna, antennaH, roofBox, waterTower, pipes, smokestack });
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

// Цвет окна в зависимости от индекса
function windowColor(idx: number, phaseKey: string): string {
  if (phaseKey === "day") {
    return ["#2a3a55", "#3a4a65"][idx % 2];
  }
  // night/dawn/sunset
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

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = W;
    canvas.height = H;
    ctx.imageSmoothingEnabled = false;

    // Пять слоёв зданий
    const layers = [
      { data: buildLayer(seed * 11 + 1, 20, 55, 0.06, 20, 0.05), par: 0.03, tint: "#08101e", top: H - 15, dim: 0.35 },
      { data: buildLayer(seed * 11 + 2, 35, 85, 0.10, 26, 0.10), par: 0.07, tint: "#0a1424", top: H - 25, dim: 0.5 },
      { data: buildLayer(seed * 11 + 3, 55, 120, 0.16, 30, 0.20), par: 0.13, tint: "#0b1526", top: H - 40, dim: 0.7 },
      { data: buildLayer(seed * 11 + 4, 80, 170, 0.24, 34, 0.30), par: 0.22, tint: "#0a1220", top: H - 60, dim: 0.85 },
      { data: buildLayer(seed * 11 + 5, 110, 230, 0.35, 40, 0.40), par: 0.38, tint: "#060c18", top: H - 90, dim: 1.0 },
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
    const smokes: Smoke[] = [];

    let lightningT = 0;
    let flashAlpha = 0;
    let lightningSegs: [number, number, number, number][] = [];

    if (effective === "rain" || effective === "storm") {
      const count = effective === "storm" ? 260 : 150;
      for (let i = 0; i < count; i++) {
        drops.push({
          x: Math.random() * W, y: Math.random() * H,
          v: 5 + Math.random() * 6, l: 3 + Math.random() * 4,
        });
      }
    } else if (effective === "snow") {
      for (let i = 0; i < 130; i++) {
        drops.push({
          x: Math.random() * W, y: Math.random() * H,
          v: 0.3 + Math.random() * 0.6, l: 1,
        });
      }
    }

    for (let i = 0; i < 10; i++) {
      vehicles.push({
        x: Math.random() * W,
        y: 15 + Math.random() * 100,
        vx: (Math.random() < 0.5 ? -1 : 1) * (0.4 + Math.random() * 0.9),
        hue: Math.floor(Math.random() * NEON.length),
        size: Math.random() < 0.3 ? 2 : 1,
      });
    }

    for (let i = 0; i < 8; i++) {
      people.push({
        x: Math.random() * W,
        vx: (Math.random() < 0.5 ? -1 : 1) * (0.15 + Math.random() * 0.3),
        h: 3 + Math.floor(Math.random() * 3),
      });
    }

    for (let i = 0; i < 4; i++) {
      groundCars.push({
        x: Math.random() * W,
        vx: (Math.random() < 0.5 ? -1 : 1) * (0.8 + Math.random() * 1.2),
        hue: Math.floor(Math.random() * NEON.length),
      });
    }

    for (let i = 0; i < 3; i++) {
      holograms.push({
        x: 40 + Math.random() * (W - 120),
        y: 30 + Math.random() * 100,
        w: 24 + Math.floor(Math.random() * 20),
        h: 32 + Math.floor(Math.random() * 20),
        c: Math.floor(Math.random() * NEON.length),
        glitch: 0,
      });
    }

    for (let i = 0; i < 6; i++) {
      clouds.push({
        x: Math.random() * W,
        y: 20 + Math.random() * 120,
        w: 30 + Math.floor(Math.random() * 50),
        h: 6 + Math.floor(Math.random() * 8),
        v: 0.1 + Math.random() * 0.3,
        alpha: 0.15 + Math.random() * 0.2,
      });
    }

    const onMove = (e: MouseEvent) => {
      mouse.current.x = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.current.y = (e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener("mousemove", onMove);

    const drawText = (text: string, x: number, y: number, color: string, alpha: number) => {
      ctx.font = "5px monospace";
      ctx.globalAlpha = alpha;
      ctx.fillStyle = color;
      // рисуем посимвольно, чтобы не размывалось
      for (let i = 0; i < text.length; i++) {
        ctx.fillText(text[i], Math.floor(x + i * 4), Math.floor(y));
      }
      ctx.globalAlpha = 1;
    };

    const drawBuilding = (b: Building, layer: typeof layers[0], offsetX: number, pKey: string, t: number) => {
      const bx = Math.floor(b.x - offsetX);
      if (bx + b.w < 0 || bx > W) return;

      const top = layer.top - b.h;

      // Основной силуэт
      ctx.fillStyle = layer.tint;
      ctx.fillRect(bx, top, b.w, b.h);

      // Лёгкая подсветка левого края (объём)
      ctx.fillStyle = "rgba(255,255,255,0.03)";
      ctx.fillRect(bx, top, 1, b.h);

      // Тёмный край справа
      ctx.fillStyle = "rgba(0,0,0,0.3)";
      ctx.fillRect(bx + b.w - 1, top, 1, b.h);

      // Крыша с обводкой
      ctx.fillStyle = "rgba(0,240,255,0.08)";
      ctx.fillRect(bx, top, b.w, 1);

      // Окна
      const winPhase = Math.floor(t / 3500);
      for (let i = 0; i < b.windows.length; i++) {
        const w = b.windows[i];
        const blink = ((i * 31 + winPhase) % 17) === 0;
        if (blink && ((i * 7) % 3) !== 0) continue;

        const col = windowColor(w.c, pKey);
        ctx.globalAlpha = layer.dim * w.bright;

        // окно с «ореолом» (более яркий центр)
        ctx.fillStyle = col;
        ctx.fillRect(bx + w.x, top + w.y, w.w, w.h);

        // если большое окно — добавляем яркий пиксель
        if (w.w >= 2 || w.h >= 2) {
          ctx.globalAlpha = layer.dim * w.bright * 0.4;
          ctx.fillStyle = "#ffffff";
          ctx.fillRect(bx + w.x, top + w.y, 1, 1);
        }
      }
      ctx.globalAlpha = 1;

      // Вывески
      for (const s of b.signs) {
        const col = NEON[s.c];
        const isOn = !s.blink || ((Math.floor(t / 500) + s.x) % 4 !== 0);
        if (isOn) {
          drawText(s.text, bx + s.x, top + s.y, col, layer.dim * 0.9);
        }
      }

      // Антенна
      if (b.antenna) {
        const ax = bx + Math.floor(b.w / 2);
        ctx.fillStyle = layer.tint;
        ctx.fillRect(ax, top - b.antennaH, 1, b.antennaH);
        // мигающий огонёк на кончике
        const bl = (Math.floor(t / 700) % 2) === 0;
        ctx.fillStyle = bl ? "#ff2d55" : "#ff8888";
        ctx.globalAlpha = layer.dim;
        ctx.fillRect(ax - 1, top - b.antennaH - 2, 2, 2);
        ctx.globalAlpha = 1;
      }

      // Крышная коробка
      if (b.roofBox) {
        const bw = 5 + Math.floor(b.w * 0.2);
        ctx.fillStyle = "rgba(0,0,0,0.5)";
        ctx.fillRect(bx + 3, top - 4, bw, 4);
        ctx.fillStyle = layer.tint;
        ctx.fillRect(bx + 3, top - 4, bw, 1);
      }

      // Водонапорная башня
      if (b.waterTower) {
        const wx = bx + Math.floor(b.w / 2) + 4;
        const wy = top - 10;
        ctx.fillStyle = layer.tint;
        ctx.fillRect(wx, wy, 6, 6);
        ctx.fillRect(wx + 1, wy + 6, 1, 4);
        ctx.fillRect(wx + 4, wy + 6, 1, 4);
        ctx.fillStyle = "rgba(0,240,255,0.15)";
        ctx.fillRect(wx, wy, 6, 1);
      }

      // Трубы (вертикальные полосы)
      for (let i = 0; i < b.pipes; i++) {
        const px = bx + 2 + i * 4;
        ctx.fillStyle = "rgba(0,0,0,0.4)";
        ctx.fillRect(px, top + 4, 1, b.h - 4);
        ctx.fillStyle = "rgba(0,240,255,0.05)";
        ctx.fillRect(px, top + 4, 1, b.h - 4);
      }

      // Дым из трубы (частица добавляется в update)
      if (b.smokestack > 0) {
        const sx = bx + Math.floor(b.w * 0.7);
        const sy = top - b.smokestack;
        ctx.fillStyle = "rgba(120,140,180,0.4)";
        ctx.fillRect(sx, sy, 1, b.smokestack);
      }
    };

    let raf = 0;
    let last = performance.now();
    let smokeTimer = 0;

    const frame = (t: number) => {
      const dt = Math.min(50, t - last) / 1000;
      last = t;
      smokeTimer += dt;

      smooth.current.x += (mouse.current.x - smooth.current.x) * 0.05;
      smooth.current.y += (mouse.current.y - smooth.current.y) * 0.05;

      const p = phase();
      const [c1, c2, c3] = SKY[p];
      const grad = ctx.createLinearGradient(0, 0, 0, H);
      grad.addColorStop(0, c1);
      grad.addColorStop(0.6, c2);
      grad.addColorStop(1, c3);
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, W, H);

      // Звёзды ночью
      if (p === "night" || p === "dawn") {
        const r = rngFrom(12345);
        ctx.fillStyle = "#4a5a7a";
        for (let i = 0; i < 90; i++) {
          const x = Math.floor(r() * W);
          const y = Math.floor(r() * (H * 0.55));
          const twinkle = ((Math.floor(t / 800) + i) % 7) === 0;
          ctx.globalAlpha = twinkle ? 0.9 : 0.3 + r() * 0.4;
          ctx.fillRect(x, y, 1, 1);
        }
        ctx.globalAlpha = 1;
      }

      // Луна/солнце
      const isNight = p === "night";
      const sunX = Math.floor(W * 0.82);
      const sunY = isNight ? 42 : p === "dawn" ? Math.floor(H * 0.32) : p === "sunset" ? Math.floor(H * 0.38) : 50;
      if (isNight) {
        // Луна с кратерами
        ctx.fillStyle = "#e8f0ff";
        ctx.fillRect(sunX, sunY, 10, 10);
        ctx.fillStyle = "rgba(120,140,180,0.5)";
        ctx.fillRect(sunX + 2, sunY + 2, 2, 2);
        ctx.fillRect(sunX + 6, sunY + 5, 2, 2);
        ctx.fillRect(sunX + 4, sunY + 7, 1, 1);
        // ореол
        ctx.globalAlpha = 0.15;
        ctx.fillStyle = "#88aaff";
        ctx.fillRect(sunX - 3, sunY - 3, 16, 16);
        ctx.globalAlpha = 1;
      } else {
        ctx.globalAlpha = 0.85;
        ctx.fillStyle = p === "day" ? "#c0c8d8" : "#ff8855";
        ctx.fillRect(sunX, sunY, 8, 8);
        ctx.globalAlpha = 0.2;
        ctx.fillRect(sunX - 4, sunY - 4, 16, 16);
        ctx.globalAlpha = 1;
      }

      // Облака
      for (const c of clouds) {
        c.x += c.v * dt * 10;
        if (c.x > W + 60) c.x = -60;
        ctx.globalAlpha = c.alpha;
        ctx.fillStyle = p === "sunset" || p === "dawn" ? "#4a2030" : "#1a2438";
        // облако из нескольких прямоугольников
        ctx.fillRect(Math.floor(c.x), Math.floor(c.y), c.w, c.h);
        ctx.fillRect(Math.floor(c.x + 6), Math.floor(c.y - 3), Math.floor(c.w * 0.6), 4);
        ctx.fillRect(Math.floor(c.x + 12), Math.floor(c.y - 5), Math.floor(c.w * 0.35), 3);
      }
      ctx.globalAlpha = 1;

      // Здания back-to-front
      for (const L of layers) {
        const offsetX = smooth.current.x * 30 * L.par;
        for (const b of L.data) drawBuilding(b, L, offsetX, p, t);
      }

      // Голограммы (поверх дальних зданий)
      for (const h of holograms) {
        h.glitch += dt;
        const glitching = h.glitch > 8;
        if (glitching) h.glitch = 0;

        const col = NEON[h.c];
        const hx = Math.floor(h.x + smooth.current.x * 15);
        const hy = Math.floor(h.y);

        ctx.globalAlpha = glitching ? 0.15 : 0.35;
        ctx.fillStyle = col;
        // рамка
        ctx.fillRect(hx, hy, h.w, 1);
        ctx.fillRect(hx, hy + h.h, h.w, 1);
        ctx.fillRect(hx, hy, 1, h.h);
        ctx.fillRect(hx + h.w, hy, 1, h.h);

        // «строки» внутри
        for (let i = 2; i < h.h; i += 4) {
          const lineW = Math.floor(h.w * (0.4 + Math.random() * 0.5));
          ctx.globalAlpha = glitching ? 0.1 : 0.25;
          ctx.fillRect(hx + 2, hy + i, lineW, 1);
        }

        // «◈» в центре
        ctx.globalAlpha = glitching ? 0.3 : 0.6;
        ctx.fillStyle = col;
        ctx.fillRect(Math.floor(hx + h.w / 2 - 3), Math.floor(hy + h.h / 2 - 1), 5, 3);
        ctx.fillRect(Math.floor(hx + h.w / 2 - 1), Math.floor(hy + h.h / 2 - 3), 3, 7);
      }
      ctx.globalAlpha = 1;

      // Дым из труб — частицы
      if (smokeTimer > 0.15) {
        smokeTimer = 0;
        // найдём пару дымоходов в видимом слое
        const front = layers[4];
        const off = smooth.current.x * 30 * front.par;
        for (const b of front.data) {
          if (b.smokestack > 0 && Math.random() < 0.15) {
            smokes.push({
              x: b.x - off + Math.floor(b.w * 0.7),
              y: front.top - b.h - b.smokestack,
              v: 0.3 + Math.random() * 0.3,
              life: 1.0,
            });
          }
        }
      }

      // Рисуем дым
      for (let i = smokes.length - 1; i >= 0; i--) {
        const s = smokes[i];
        s.y -= s.v * dt * 30;
        s.x += 0.05;
        s.life -= dt * 0.4;
        if (s.life <= 0 || s.y < 0) {
          smokes.splice(i, 1);
          continue;
        }
        ctx.globalAlpha = s.life * 0.4;
        ctx.fillStyle = "#9aa8c8";
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), 2, 2);
      }
      ctx.globalAlpha = 1;

      // Летающие машины
      for (const c of vehicles) {
        c.x += c.vx * dt * 30;
        if (c.x < -30) c.x = W + 30;
        if (c.x > W + 30) c.x = -30;
        const y = c.y + Math.sin(t / 900 + c.x * 0.01) * 2.5;
        const col = NEON[c.hue];
        // световой след (trail)
        ctx.globalAlpha = 0.35;
        ctx.fillStyle = col;
        const trailLen = 5 * (c.size + 1);
        ctx.fillRect(Math.floor(c.x - c.vx * trailLen), Math.floor(y), trailLen, c.size);
        // корпус
        ctx.globalAlpha = 1;
        ctx.fillStyle = "#0a0f1a";
        ctx.fillRect(Math.floor(c.x), Math.floor(y - 1), 3 + c.size, 2 + c.size);
        // «фары» - вперёд
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = col;
        const front = c.vx > 0 ? Math.floor(c.x) + 2 + c.size : Math.floor(c.x) - 1;
        ctx.fillRect(front, Math.floor(y), 1, 1);
      }
      ctx.globalAlpha = 1;

      // Улица — силуэты людей
      const streetY = H - 8;
      // асфальт
      ctx.fillStyle = "#04070e";
      ctx.fillRect(0, streetY - 4, W, 12);
      // тротуар
      ctx.fillStyle = "#0a1020";
      ctx.fillRect(0, streetY - 4, W, 1);

      // силуэты
      for (const pn of people) {
        pn.x += pn.vx * dt * 30;
        if (pn.x < -5) pn.x = W + 5;
        if (pn.x > W + 5) pn.x = -5;
        ctx.fillStyle = "#050810";
        const px = Math.floor(pn.x);
        ctx.fillRect(px, streetY - pn.h, 2, pn.h);
        // голова
        ctx.fillRect(px, streetY - pn.h - 2, 2, 2);
      }

      // машины по улице
      for (const gc of groundCars) {
        gc.x += gc.vx * dt * 40;
        if (gc.x < -20) gc.x = W + 20;
        if (gc.x > W + 20) gc.x = -20;
        const col = NEON[gc.hue];
        const gy = streetY - 1;
        // корпус
        ctx.fillStyle = "#0a0f1a";
        ctx.fillRect(Math.floor(gc.x), gy, 8, 2);
        // фары
        ctx.globalAlpha = 0.9;
        ctx.fillStyle = col;
        const fx = gc.vx > 0 ? Math.floor(gc.x) + 8 : Math.floor(gc.x) - 1;
        ctx.fillRect(fx, gy, 1, 1);
        // подсветка днища
        ctx.globalAlpha = 0.4;
        ctx.fillRect(Math.floor(gc.x) + 1, gy + 2, 6, 1);
        ctx.globalAlpha = 1;
      }

      // Отражающие лужи (при дожде/после дождя)
      if (effective === "rain" || effective === "storm") {
        ctx.globalAlpha = 0.25;
        // «отражаем» окна — просто размытые пятна внизу
        const puddlePhase = Math.floor(t / 3000);
        const r = rngFrom(seed + puddlePhase);
        for (let i = 0; i < 8; i++) {
          const px = Math.floor(r() * W);
          const py = streetY - 2 + Math.floor(r() * 3);
          const pw = 6 + Math.floor(r() * 12);
          const col = NEON[Math.floor(r() * NEON.length)];
          ctx.fillStyle = col;
          ctx.fillRect(px, py, pw, 1);
        }
        ctx.globalAlpha = 1;
      }

      // Погода
      if (effective === "rain" || effective === "storm") {
        ctx.strokeStyle = "#7ec8ff";
        ctx.globalAlpha = effective === "storm" ? 0.7 : 0.4;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (const d of drops) {
          d.y += d.v * dt * 60;
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
          d.y += d.v * dt * 60;
          d.x += Math.sin((t + d.x * 10) / 800) * 0.4;
          if (d.y > H) { d.y = -2; d.x = Math.random() * W; }
          ctx.globalAlpha = 0.85;
          ctx.fillRect(Math.floor(d.x), Math.floor(d.y), 1, 1);
        }
        ctx.globalAlpha = 1;
      } else if (effective === "smog") {
        // оранжево-фиолетовая дымка
        ctx.fillStyle = "rgba(90, 40, 110, 0.15)";
        ctx.fillRect(0, 0, W, H);
        ctx.fillStyle = "rgba(180, 80, 60, 0.08)";
        ctx.fillRect(0, Math.floor(H * 0.4), W, Math.floor(H * 0.6));
      }

      // Молния
      if (effective === "storm") {
        lightningT += dt;
        if (flashAlpha > 0) flashAlpha -= dt * 6;
        if (lightningT > 4 + Math.random() * 5) {
          lightningT = 0;
          flashAlpha = 1.0;
          // строим молнию с ветвлением
          lightningSegs = [];
          let bx = W * 0.25 + Math.random() * W * 0.5;
          let by = 0;
          while (by < H * 0.6) {
            const nx = bx + (Math.random() - 0.5) * 16;
            const ny = by + 4 + Math.random() * 8;
            lightningSegs.push([bx, by, nx, ny]);
            // ветвление
            if (Math.random() < 0.2) {
              let vx = nx, vy = ny;
              const branchLen = 3 + Math.random() * 4;
              for (let i = 0; i < branchLen; i++) {
                const bx2 = vx + (Math.random() - 0.5) * 10;
                const by2 = vy + 3 + Math.random() * 5;
                lightningSegs.push([vx, vy, bx2, by2]);
                vx = bx2; vy = by2;
              }
            }
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
          ctx.fillStyle = `rgba(200, 220, 255, ${flashAlpha * 0.4})`;
          ctx.fillRect(0, 0, W, H);
        }
      }

      // Vignette
      const vg = ctx.createRadialGradient(W / 2, H / 2, 60, W / 2, H / 2, W * 0.8);
      vg.addColorStop(0, "rgba(0,0,0,0)");
      vg.addColorStop(1, "rgba(0,0,0,0.7)");
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

    target = root / "frontend" / "src" / "PixelCity.tsx"
    target.write_text(PIXEL_CITY, encoding="utf-8")
    print(f"\nОбновлено: {target}")
    print("\nДальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())