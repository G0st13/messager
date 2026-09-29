#!/usr/bin/env python3
"""sprint22.py - detailed Night City tactical map."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIXEL_CITY = r'''import { useEffect, useMemo, useState } from "react";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const W = 1400;
const H = 800;

// ---------- helpers ----------
function mulberry32(seed: number) {
  let s = (seed >>> 0) || 1;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

interface Sub {
  name: string;
  x: number;
  y: number;
}

interface District {
  id: string;
  label: string;
  color: string;
  path: string;
  cx: number;
  cy: number;
  subs: Sub[];
  density: number; // сколько зданий
  zone: "north" | "central" | "south" | "coast";
}

// ---------- districts ----------
const DISTRICTS: District[] = [
  {
    id: "watson",
    label: "WATSON",
    color: "#00f0ff",
    cx: 260, cy: 200,
    density: 55,
    zone: "north",
    path: "M 90,80 L 200,60 L 320,55 L 420,80 L 460,140 L 440,230 L 380,290 L 260,300 L 150,270 L 100,190 Z",
    subs: [
      { name: "KABUKI", x: 220, y: 160 },
      { name: "LITTLE CHINA", x: 320, y: 180 },
      { name: "NORTHSIDE", x: 180, y: 250 },
      { name: "ARASAKA WF", x: 370, y: 110 },
    ],
  },
  {
    id: "westbrook",
    label: "WESTBROOK",
    color: "#b967ff",
    cx: 800, cy: 200,
    density: 60,
    zone: "north",
    path: "M 480,80 L 700,60 L 900,70 L 1060,110 L 1100,180 L 1080,280 L 1000,330 L 800,340 L 640,320 L 520,260 L 480,180 Z",
    subs: [
      { name: "JAPANTOWN", x: 720, y: 180 },
      { name: "CHARTER HILL", x: 950, y: 160 },
      { name: "NORTH OAK", x: 1000, y: 240 },
    ],
  },
  {
    id: "citycenter",
    label: "CITY CENTER",
    color: "#fcee0a",
    cx: 620, cy: 430,
    density: 70,
    zone: "central",
    path: "M 440,340 L 640,330 L 800,340 L 850,400 L 850,500 L 780,560 L 620,580 L 480,560 L 410,480 L 410,400 Z",
    subs: [
      { name: "DOWNTOWN", x: 620, y: 420 },
      { name: "CORPO PLAZA", x: 730, y: 470 },
    ],
  },
  {
    id: "heywood",
    label: "HEYWOOD",
    color: "#ff00a0",
    cx: 1080, cy: 480,
    density: 65,
    zone: "central",
    path: "M 870,360 L 1090,370 L 1200,430 L 1210,540 L 1150,620 L 1000,660 L 880,600 L 860,490 L 870,410 Z",
    subs: [
      { name: "WELLSPRINGS", x: 1020, y: 420 },
      { name: "VISTA DEL REY", x: 1120, y: 480 },
      { name: "THE GLEN", x: 960, y: 550 },
    ],
  },
  {
    id: "santodomingo",
    label: "SANTO DOMINGO",
    color: "#ff6600",
    cx: 300, cy: 570,
    density: 50,
    zone: "south",
    path: "M 150,330 L 380,320 L 420,400 L 410,560 L 360,660 L 220,700 L 130,640 L 100,480 L 130,380 Z",
    subs: [
      { name: "ARROYO", x: 240, y: 500 },
      { name: "RANCHO CORONADO", x: 180, y: 600 },
    ],
  },
  {
    id: "pacifica",
    label: "PACIFICA",
    color: "#7cff00",
    cx: 720, cy: 640,
    density: 30,
    zone: "south",
    path: "M 460,600 L 620,590 L 780,600 L 860,650 L 840,740 L 680,760 L 520,740 L 440,680 L 440,630 Z",
    subs: [
      { name: "WEST WIND ESTATE", x: 640, y: 660 },
      { name: "COASTVIEW", x: 780, y: 700 },
    ],
  },
];

// ---------- water ----------
const WATER = "M 0,0 L 90,0 L 100,80 L 130,190 L 150,330 L 130,480 L 90,640 L 110,760 L 0,800 Z";

// ---------- bridges ----------
const BRIDGES: { path: string; label: string }[] = [
  { path: "M 100,180 L 155,195 L 155,215 L 100,220", label: "FRANKLIN BR." },
  { path: "M 100,560 L 165,555 L 165,580 L 100,590", label: "NORTHSIDE BR." },
];

// ---------- highways ----------
const HIGHWAYS = [
  "M 60,140 Q 250,130 450,150 Q 700,180 950,150 Q 1150,130 1350,170",     // I-101
  "M 200,320 Q 350,360 500,380 Q 700,410 900,410 Q 1100,420 1300,520",     // I-280
  "M 600,80 Q 620,300 620,500 Q 620,650 640,780",                          // N-S
];

// ---------- ncart lines (metro) ----------
const NCART = [
  "M 120,260 Q 350,280 620,280 Q 900,280 1200,360",
  "M 300,700 Q 420,620 500,480 Q 580,340 700,220",
  "M 1000,700 Q 1000,550 900,450 Q 820,370 800,240",
];

// ---------- landmarks ----------
interface Landmark { x: number; y: number; kind: string; label: string; color: string }

const LANDMARKS: Landmark[] = [
  { x: 250, y: 180, kind: "ncpd", label: "NCPD", color: "#00f0ff" },
  { x: 700, y: 210, kind: "hospital", label: "TRAUMA", color: "#ff3355" },
  { x: 620, y: 430, kind: "bank", label: "ARASAKA", color: "#fcee0a" },
  { x: 1080, y: 480, kind: "delamain", label: "DELAMAIN", color: "#b967ff" },
  { x: 300, y: 570, kind: "power", label: "POWER", color: "#ff6600" },
  { x: 720, y: 640, kind: "avante", label: "AVANTE", color: "#7cff00" },
  { x: 900, y: 400, kind: "metro", label: "NCART", color: "#00f0ff" },
  { x: 420, y: 570, kind: "ripper", label: "RIPPERDOC", color: "#ff00a0" },
  { x: 1050, y: 300, kind: "gun", label: "2ND AMEND.", color: "#ff00a0" },
  { x: 500, y: 200, kind: "food", label: "TOM'S DINER", color: "#fcee0a" },
];

// ---------- time palette ----------
function timeOfDay(): "night" | "dawn" | "day" | "sunset" {
  const h = new Date().getHours();
  if (h >= 21 || h < 5) return "night";
  if (h < 7) return "dawn";
  if (h < 18) return "day";
  return "sunset";
}

const PALETTES: Record<string, { bg: string; water: string; badlands: string; road: string; grid: string; frame: string }> = {
  night:   { bg: "#03060c", water: "#040d18", badlands: "#0a0806", road: "rgba(255,170,60,0.35)", grid: "rgba(0,240,255,0.05)", frame: "rgba(0,240,255,0.45)" },
  dawn:    { bg: "#0a0611", water: "#0c081a", badlands: "#100a08", road: "rgba(255,170,60,0.4)",  grid: "rgba(184,103,255,0.05)", frame: "rgba(184,103,255,0.5)" },
  day:     { bg: "#08111a", water: "#0a1520", badlands: "#16100a", road: "rgba(255,200,80,0.5)",  grid: "rgba(0,240,255,0.04)",   frame: "rgba(0,240,255,0.4)" },
  sunset:  { bg: "#100a12", water: "#140810", badlands: "#1a0f08", road: "rgba(255,120,60,0.5)",  grid: "rgba(255,102,0,0.05)",   frame: "rgba(255,102,0,0.5)" },
};

// ---------- building generation ----------
interface Building { x: number; y: number; w: number; h: number; glow: boolean }

function genBuildings(district: District, seed: number): Building[] {
  const rng = mulberry32(seed + district.id.length * 131 + district.cx);
  const out: Building[] = [];
  // bbox района — упрощённый
  const minX = district.cx - 180;
  const maxX = district.cx + 180;
  const minY = district.cy - 120;
  const maxY = district.cy + 120;
  let attempts = 0;
  while (out.length < district.density && attempts < district.density * 6) {
    attempts++;
    const x = minX + rng() * (maxX - minX);
    const y = minY + rng() * (maxY - minY);
    const w = 3 + Math.floor(rng() * 7);
    const h = 3 + Math.floor(rng() * 7);
    // проверим пересечение с уже существующими (разрешим небольшое)
    let overlap = false;
    for (const b of out) {
      if (Math.abs(b.x - x) < 6 && Math.abs(b.y - y) < 6) {
        overlap = true;
        break;
      }
    }
    if (overlap) continue;
    out.push({ x, y, w, h, glow: rng() < 0.25 });
  }
  return out;
}

// ---------- traffic generators ----------
function genTraffic(seed: number) {
  const rng = mulberry32(seed + 999);
  const out: { path: string; dur: number; delay: number; color: string }[] = [];
  HIGHWAYS.forEach((p, i) => {
    const n = 3 + Math.floor(rng() * 3);
    for (let j = 0; j < n; j++) {
      out.push({
        path: p,
        dur: 18 + rng() * 14,
        delay: rng() * 12,
        color: i === 0 ? "#ffaa3c" : i === 1 ? "#fcee0a" : "#00f0ff",
      });
    }
  });
  return out;
}

// ---------- landmark icons ----------
function landmarkIcon(kind: string, color: string) {
  switch (kind) {
    case "ncpd":
      return (
        <g>
          <path d="M 0,-7 L 6,-3 L 6,4 L 0,8 L -6,4 L -6,-3 Z" fill="none" stroke={color} strokeWidth={1.2} />
          <text y={2} textAnchor="middle" fontSize={5} fill={color} fontWeight="bold">P</text>
        </g>
      );
    case "hospital":
      return (
        <g>
          <rect x={-6} y={-6} width={12} height={12} fill="none" stroke={color} strokeWidth={1.2} />
          <path d="M -3,-1 H -1 V -3 H 1 V -1 H 3 V 1 H 1 V 3 H -1 V 1 H -3 Z" fill={color} />
        </g>
      );
    case "bank":
      return (
        <g>
          <path d="M -7,4 L 0,-6 L 7,4 Z" fill="none" stroke={color} strokeWidth={1.2} />
          <rect x={-4} y={4} width={8} height={3} fill={color} />
        </g>
      );
    case "delamain":
      return (
        <g>
          <circle r={6} fill="none" stroke={color} strokeWidth={1.2} />
          <path d="M -3,-1 H 3 M -3,1 H 3" stroke={color} strokeWidth={1.5} />
        </g>
      );
    case "power":
      return (
        <g>
          <path d="M -1,-7 L -3,1 L 0,0 L -1,7 L 3,-1 L 0,0 Z" fill={color} />
        </g>
      );
    case "avante":
      return (
        <g>
          <path d="M 0,-6 L 5,5 L -5,5 Z" fill="none" stroke={color} strokeWidth={1.2} />
          <circle r={1.5} fill={color} />
        </g>
      );
    case "metro":
      return (
        <g>
          <circle r={6} fill="none" stroke={color} strokeWidth={1.2} />
          <text y={2} textAnchor="middle" fontSize={6} fill={color} fontWeight="bold">M</text>
        </g>
      );
    case "ripper":
      return (
        <g>
          <path d="M 0,-6 L 4,0 L 0,6 L -4,0 Z" fill="none" stroke={color} strokeWidth={1.2} />
          <path d="M -2,0 H 2" stroke={color} strokeWidth={1.5} />
        </g>
      );
    case "gun":
      return (
        <g>
          <rect x={-6} y={-3} width={12} height={6} fill="none" stroke={color} strokeWidth={1.2} />
          <circle r={1.5} fill={color} />
        </g>
      );
    case "food":
      return (
        <g>
          <rect x={-5} y={-5} width={10} height={10} fill="none" stroke={color} strokeWidth={1.2} />
          <path d="M -2,-3 V 3 M 0,-3 V 3 M 2,-3 V 3" stroke={color} strokeWidth={1} />
        </g>
      );
    default:
      return <circle r={4} fill={color} />;
  }
}

// ---------- component ----------
export default function PixelCity({
  weather = "auto",
  seed = 1,
}: {
  weather?: Weather;
  seed?: number;
}) {
  const [, setTick] = useState(0);

  useEffect(() => {
    const int = window.setInterval(() => setTick((v) => v + 1), 60 * 60 * 1000);
    return () => window.clearInterval(int);
  }, []);

  const effective: Weather = weather === "auto"
    ? (["clear", "rain", "rain", "snow", "smog"] as const)[new Date().getDate() % 5]
    : weather;

  const tod = timeOfDay();
  const pal = PALETTES[tod];

  // генерируем здания для каждого района
  const buildings = useMemo(() => {
    const map: Record<string, Building[]> = {};
    for (const d of DISTRICTS) {
      map[d.id] = genBuildings(d, seed);
    }
    return map;
  }, [seed]);

  // трафик
  const traffic = useMemo(() => genTraffic(seed), [seed]);

  // маленькие случайные точки-огни
  const dots = useMemo(() => {
    const rng = mulberry32(seed + 333);
    const out: { x: number; y: number; c: string; delay: number }[] = [];
    for (let i = 0; i < 220; i++) {
      out.push({
        x: rng() * W,
        y: rng() * H,
        c: rng() < 0.5 ? "#00f0ff" : rng() < 0.5 ? "#ff00a0" : "#fcee0a",
        delay: rng() * 3,
      });
    }
    return out;
  }, [seed]);

  return (
    <div className="night-city-bg">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid slice"
        className="night-city-svg"
      >
        <defs>
          <radialGradient id="ncWater" cx="0.15" cy="0.5" r="0.9">
            <stop offset="0" stopColor={pal.water} />
            <stop offset="0.7" stopColor="#000408" />
            <stop offset="1" stopColor="#000000" />
          </radialGradient>
          <radialGradient id="ncVignette" cx="0.5" cy="0.5" r="0.85">
            <stop offset="0.4" stopColor="rgba(0,0,0,0)" />
            <stop offset="1" stopColor="rgba(0,0,0,0.92)" />
          </radialGradient>
          <pattern id="ncGrid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke={pal.grid} strokeWidth="1" />
          </pattern>
          <pattern id="ncGridBig" width="200" height="200" patternUnits="userSpaceOnUse">
            <path d="M 200 0 L 0 0 0 200" fill="none" stroke="rgba(0,240,255,0.1)" strokeWidth="1.5" />
          </pattern>
          <filter id="ncGlow">
            <feGaussianBlur stdDeviation="1.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* база */}
        <rect width={W} height={H} fill={pal.bg} />

        {/* Badlands — внешний слой */}
        <path
          d={`M 0,0 H ${W} V ${H} H 0 Z M 100,20 L ${W - 20},20 L ${W - 20},${H - 20} L 100,${H - 20} L 100,20 Z`}
          fill={pal.badlands}
          fillRule="evenodd"
        />
        <path
          d={`M 100,20 L ${W - 20},20 L ${W - 20},${H - 20} L 100,${H - 20} L 100,20 Z`}
          fill="none"
          stroke="rgba(240,176,48,0.25)"
          strokeWidth={1}
          strokeDasharray="3 8"
        />

        {/* сетка */}
        <rect width={W} height={H} fill="url(#ncGrid)" />
        <rect width={W} height={H} fill="url(#ncGridBig)" />

        {/* вода */}
        <path d={WATER} fill="url(#ncWater)" />
        <path d={WATER} fill="none" stroke="rgba(0,240,255,0.3)" strokeWidth={1.2} />
        {/* прибой */}
        <path d={WATER} fill="none" stroke="rgba(0,240,255,0.1)" strokeWidth={4} />

        {/* мосты */}
        <g>
          {BRIDGES.map((b, i) => (
            <g key={"br-" + i}>
              <path d={b.path} fill="rgba(0,240,255,0.08)" stroke="rgba(0,240,255,0.55)" strokeWidth={1} />
              <text
                x={b.path.match(/M (\d+)/) ? 105 : 105}
                y={i === 0 ? 200 : 575}
                fontSize={6}
                fill="rgba(0,240,255,0.6)"
                letterSpacing={1}
                fontFamily="JetBrains Mono, monospace"
              >
                {b.label}
              </text>
            </g>
          ))}
        </g>

        {/* highways */}
        <g>
          {HIGHWAYS.map((d, i) => (
            <g key={"hw-" + i}>
              <path d={d} fill="none" stroke="rgba(255,170,60,0.15)" strokeWidth={6} />
              <path
                d={d}
                fill="none"
                stroke={pal.road}
                strokeWidth={1.8}
                strokeDasharray={i === 2 ? "none" : "8 4"}
              />
              <text
                x={i === 0 ? 200 : i === 1 ? 500 : 630}
                y={i === 0 ? 128 : i === 1 ? 375 : 200}
                fontSize={7}
                fill={pal.road}
                letterSpacing={2}
                fontFamily="JetBrains Mono, monospace"
                opacity={0.8}
              >
                {i === 0 ? "I-101" : i === 1 ? "I-280" : "NC-1"}
              </text>
            </g>
          ))}
        </g>

        {/* NCART metro lines */}
        <g>
          {NCART.map((d, i) => (
            <path
              key={"ncart-" + i}
              d={d}
              fill="none"
              stroke="rgba(0,240,255,0.55)"
              strokeWidth={0.8}
              strokeDasharray="2 5"
              className="nc-ncart"
            />
          ))}
        </g>

        {/* districts */}
        <g>
          {DISTRICTS.map((d) => (
            <g key={d.id} className="nc-district">
              {/* заливка района */}
              <path
                d={d.path}
                fill={d.color}
                fillOpacity={0.05}
                stroke={d.color}
                strokeWidth={1}
                strokeOpacity={0.9}
              />
              {/* вложенная обводка (смещённая) */}
              <path
                d={d.path}
                fill="none"
                stroke={d.color}
                strokeWidth={0.4}
                strokeOpacity={0.35}
                transform="translate(3 3)"
              />
              {/* buildings */}
              <g>
                {buildings[d.id].map((b, i) => (
                  <rect
                    key={d.id + "-b-" + i}
                    x={b.x}
                    y={b.y}
                    width={b.w}
                    height={b.h}
                    fill={b.glow ? d.color : "rgba(20,30,45,0.85)"}
                    stroke={b.glow ? "none" : d.color + "55"}
                    strokeWidth={0.4}
                    opacity={b.glow ? 0.85 : 0.7}
                    className={b.glow ? "nc-building-glow" : ""}
                    style={b.glow ? { animationDelay: (i % 7) * 0.4 + "s" } : undefined}
                  />
                ))}
              </g>
            </g>
          ))}
        </g>

        {/* city dots */}
        <g>
          {dots.map((l, i) => (
            <circle
              key={"dot-" + i}
              cx={l.x}
              cy={l.y}
              r={0.8}
              fill={l.c}
              className="nc-light"
              style={{ animationDelay: l.delay + "s" }}
            />
          ))}
        </g>

        {/* district labels + sublabels */}
        <g>
          {DISTRICTS.map((d) => (
            <g key={"lab-" + d.id}>
              {/* главный label */}
              <text
                x={d.cx}
                y={d.cy - 30}
                textAnchor="middle"
                fill={d.color}
                fontSize={14}
                fontWeight="bold"
                letterSpacing={5}
                className="nc-label"
              >
                {d.label}
              </text>
              {/* линия под label */}
              <path
                d={`M ${d.cx - 40},${d.cy - 24} L ${d.cx + 40},${d.cy - 24}`}
                stroke={d.color}
                strokeWidth={0.5}
                opacity={0.5}
              />
              {/* sublabels */}
              {d.subs.map((s, i) => (
                <g key={d.id + "-sub-" + i}>
                  <circle cx={s.x - 62} cy={s.y - 3} r={1.2} fill={d.color} opacity={0.7} />
                  <text
                    x={s.x - 56}
                    y={s.y}
                    fill={d.color}
                    fontSize={7}
                    letterSpacing={2}
                    opacity={0.75}
                    className="nc-sublabel"
                  >
                    {s.name}
                  </text>
                </g>
              ))}
            </g>
          ))}
        </g>

        {/* landmarks */}
        <g>
          {LANDMARKS.map((lm, i) => (
            <g key={"lm-" + i} transform={`translate(${lm.x},${lm.y})`} className="nc-landmark">
              <circle r={10} fill="rgba(0,0,0,0.6)" stroke={lm.color} strokeWidth={0.6} opacity={0.85} />
              {landmarkIcon(lm.kind, lm.color)}
              <text
                y={19}
                textAnchor="middle"
                fill={lm.color}
                fontSize={6}
                letterSpacing={1}
                fontFamily="JetBrains Mono, monospace"
                opacity={0.9}
              >
                {lm.label}
              </text>
            </g>
          ))}
        </g>

        {/* traffic dots — двигаются по highways */}
        <g filter="url(#ncGlow)">
          {traffic.map((t, i) => (
            <circle key={"traf-" + i} r={2} fill={t.color}>
              <animateMotion
                dur={t.dur + "s"}
                repeatCount="indefinite"
                begin={t.delay + "s"}
                path={t.path}
              />
            </circle>
          ))}
        </g>

        {/* scan line */}
        <line
          x1={0}
          y1={0}
          x2={W}
          y2={0}
          stroke="rgba(0,240,255,0.6)"
          strokeWidth={1.5}
          className="nc-scan"
        />

        {/* scan sweep — узкий прямоугольник */}
        <rect
          x={0}
          y={0}
          width={W}
          height={40}
          fill="url(#ncGrid)"
          className="nc-scan-sweep"
        />

        {/* compass */}
        <g transform="translate(1280, 100)" className="nc-compass">
          <circle r={34} fill="rgba(3,6,12,0.85)" stroke={pal.frame} strokeWidth={1} />
          <circle r={28} fill="none" stroke={pal.frame} strokeWidth={0.5} opacity={0.6} />
          <circle r={20} fill="none" stroke="rgba(0,240,255,0.4)" strokeWidth={0.4} className="nc-compass-spin" />
          <path d="M 0,-26 L -5,0 L 0,-4 L 5,0 Z" fill="#00f0ff" />
          <path d="M 0,26 L -3,8 L 0,12 L 3,8 Z" fill="#ff00a0" opacity={0.6} />
          <text textAnchor="middle" y={-38} fill="#00f0ff" fontSize={9} letterSpacing={2}>N</text>
          <text textAnchor="middle" y={44} fill={pal.frame} fontSize={7} letterSpacing={1}>
            34°03'N 118°14'W
          </text>
        </g>

        {/* title block (top-left) */}
        <g transform="translate(24, 24)" className="nc-title">
          <rect width={330} height={58} fill="rgba(3,6,12,0.85)" stroke={pal.frame} strokeWidth={1} />
          {/* уголки */}
          <path d="M 0,0 L 12,0 M 0,0 L 0,12" stroke="#00f0ff" strokeWidth={2} fill="none" />
          <path d="M 330,0 L 318,0 M 330,0 L 330,12" stroke="#00f0ff" strokeWidth={2} fill="none" />
          <path d="M 0,58 L 12,58 M 0,58 L 0,46" stroke="#ff00a0" strokeWidth={2} fill="none" />
          <path d="M 330,58 L 318,58 M 330,58 L 330,46" stroke="#ff00a0" strokeWidth={2} fill="none" />

          <text x={12} y={20} fill="#00f0ff" fontSize={12} fontWeight="bold" letterSpacing={3} fontFamily="JetBrains Mono, monospace">
            NIGHT CITY
          </text>
          <text x={12} y={33} fill="#7a90a8" fontSize={7} letterSpacing={2} fontFamily="JetBrains Mono, monospace">
            SECTOR MAP · v2077.4
          </text>
          <text x={12} y={45} fill="#7a90a8" fontSize={7} letterSpacing={2} fontFamily="JetBrains Mono, monospace">
            POP 6,195,000 · ALT 42m · TEMP 18°C
          </text>
          <text x={12} y={54} fill="rgba(0,240,255,0.6)" fontSize={6} letterSpacing={2} fontFamily="JetBrains Mono, monospace">
            ◈ {tod.toUpperCase()} · {effective.toUpperCase()} · UPLINK OK
          </text>
        </g>

        {/* legend (bottom-left) */}
        <g transform="translate(24, 660)" className="nc-legend">
          <rect width={260} height={110} fill="rgba(3,6,12,0.85)" stroke={pal.frame} strokeWidth={1} />
          <text x={10} y={18} fill="#00f0ff" fontSize={9} letterSpacing={2} fontFamily="JetBrains Mono, monospace">
            LEGEND
          </text>
          <line x1={10} y1={24} x2={250} y2={24} stroke="rgba(0,240,255,0.3)" strokeWidth={0.5} />

          <g transform="translate(10, 36)" fontFamily="JetBrains Mono, monospace">
            <path d="M 0,0 L 20,0" stroke={pal.road} strokeWidth={1.8} strokeDasharray="4 2" />
            <text x={26} y={3} fill="#7a90a8" fontSize={7} letterSpacing={1}>HIGHWAY</text>
          </g>
          <g transform="translate(10, 52)" fontFamily="JetBrains Mono, monospace">
            <path d="M 0,0 L 20,0" stroke="rgba(0,240,255,0.6)" strokeWidth={0.8} strokeDasharray="2 4" />
            <text x={26} y={3} fill="#7a90a8" fontSize={7} letterSpacing={1}>NCART METRO</text>
          </g>
          <g transform="translate(10, 68)" fontFamily="JetBrains Mono, monospace">
            <circle r={3} cx={3} fill="#00f0ff" />
            <text x={26} y={3} fill="#7a90a8" fontSize={7} letterSpacing={1}>NCPD / LANDMARK</text>
          </g>
          <g transform="translate(10, 84)" fontFamily="JetBrains Mono, monospace">
            <rect x={0} y={-3} width={6} height={6} fill="#00f0ff" opacity={0.9} />
            <text x={26} y={3} fill="#7a90a8" fontSize={7} letterSpacing={1}>DISTRICT HUB</text>
          </g>
          <g transform="translate(10, 98)" fontFamily="JetBrains Mono, monospace">
            <circle r={2} fill="#ff00a0" />
            <circle r={2} cx={8} fill="#fcee0a" />
            <circle r={2} cx={16} fill="#00f0ff" />
            <text x={26} y={3} fill="#7a90a8" fontSize={7} letterSpacing={1}>TRAFFIC</text>
          </g>
        </g>

        {/* corner brackets */}
        <g className="nc-corners">
          <path d="M 40,40 L 40,60 M 40,40 L 60,40" stroke={pal.frame} strokeWidth={2} fill="none" />
          <path d={`M ${W - 40},40 L ${W - 40},60 M ${W - 40},40 L ${W - 60},40`} stroke={pal.frame} strokeWidth={2} fill="none" />
          <path d={`M 40,${H - 40} L 40,${H - 60} M 40,${H - 40} L 60,${H - 40}`} stroke={pal.frame} strokeWidth={2} fill="none" />
          <path d={`M ${W - 40},${H - 40} L ${W - 40},${H - 60} M ${W - 40},${H - 40} L ${W - 60},${H - 40}`} stroke={pal.frame} strokeWidth={2} fill="none" />
        </g>

        {/* координатные метки по краям */}
        <g fontFamily="JetBrains Mono, monospace" fontSize={6} fill="rgba(0,240,255,0.4)">
          {[100, 300, 500, 700, 900, 1100, 1300].map((x) => (
            <text key={"x-" + x} x={x} y={H - 6} textAnchor="middle">E {x.toString().padStart(4, "0")}</text>
          ))}
          {[100, 200, 300, 400, 500, 600, 700].map((y) => (
            <text key={"y-" + y} x={W - 6} y={y + 3} textAnchor="end">N {y.toString().padStart(3, "0")}</text>
          ))}
        </g>

        {/* vignette */}
        <rect width={W} height={H} fill="url(#ncVignette)" />
      </svg>

      {/* weather overlays */}
      {(effective === "rain" || effective === "storm") && (
        <div className={"nc-weather nc-rain" + (effective === "storm" ? " nc-storm" : "")} />
      )}
      {effective === "snow" && <div className="nc-weather nc-snow" />}
      {effective === "smog" && <div className="nc-weather nc-smog" />}
    </div>
  );
}
'''


NIGHT_CITY_CSS = r'''
    /* ============================================================
       NIGHT CITY MAP — детальная тактическая карта
       ============================================================ */
    .night-city-bg {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      overflow: hidden;
      transition: opacity 0.35s, filter 0.35s;
    }
    body.chat-open .night-city-bg {
      opacity: 0.32;
      filter: saturate(0.55) brightness(0.65);
    }

    .night-city-svg {
      display: block;
      width: 100%;
      height: 100%;
    }

    /* ---- district subtle hover ---- */
    .nc-district path:first-child {
      transition: fill-opacity 0.5s, stroke-opacity 0.5s;
    }

    /* ---- buildings glow ---- */
    .nc-building-glow {
      animation: nc-bld-pulse 4s ease-in-out infinite;
    }
    @keyframes nc-bld-pulse {
      0%, 100% { opacity: 0.55; }
      50%      { opacity: 0.95; }
    }

    /* ---- city dots ---- */
    .nc-light {
      animation: nc-light-pulse 3.2s ease-in-out infinite;
    }
    @keyframes nc-light-pulse {
      0%, 100% { opacity: 0.25; }
      50%      { opacity: 1; }
    }

    /* ---- labels ---- */
    .nc-label {
      font-family: "JetBrains Mono", "Fira Code", monospace;
      paint-order: stroke fill;
      stroke: rgba(0, 0, 0, 0.85);
      stroke-width: 3;
      stroke-linejoin: round;
      filter: drop-shadow(0 0 6px currentColor);
    }
    .nc-sublabel {
      font-family: "JetBrains Mono", monospace;
      paint-order: stroke fill;
      stroke: rgba(0, 0, 0, 0.8);
      stroke-width: 2;
    }

    /* ---- ncart animated dash ---- */
    .nc-ncart {
      animation: nc-ncart-dash 3s linear infinite;
    }
    @keyframes nc-ncart-dash {
      to { stroke-dashoffset: -28; }
    }

    /* ---- landmark hover scale ---- */
    .nc-landmark {
      animation: nc-lm-pulse 5s ease-in-out infinite;
    }
    @keyframes nc-lm-pulse {
      0%, 100% { opacity: 0.9; }
      50%      { opacity: 1; }
    }

    /* ---- scan ---- */
    .nc-scan {
      animation: nc-scan-move 11s linear infinite;
      filter: drop-shadow(0 0 5px rgba(0, 240, 255, 0.9));
    }
    @keyframes nc-scan-move {
      0%   { transform: translateY(0);     opacity: 0; }
      8%   { opacity: 0.85; }
      92%  { opacity: 0.3; }
      100% { transform: translateY(800px); opacity: 0; }
    }
    .nc-scan-sweep {
      animation: nc-sweep-move 11s linear infinite;
      opacity: 0.15;
      fill: rgba(0, 240, 255, 0.5);
    }
    @keyframes nc-sweep-move {
      0%   { transform: translateY(-40px); }
      100% { transform: translateY(840px); }
    }

    /* ---- compass rotating inner ring ---- */
    .nc-compass-spin {
      animation: nc-spin 30s linear infinite;
      transform-origin: center;
    }
    @keyframes nc-spin {
      to { transform: rotate(360deg); }
    }

    /* ---- corners flicker ---- */
    .nc-corners {
      animation: nc-corners-flicker 4s ease-in-out infinite;
    }
    @keyframes nc-corners-flicker {
      0%, 90%, 100% { opacity: 1; }
      92% { opacity: 0.3; }
      94% { opacity: 1; }
      96% { opacity: 0.6; }
    }

    /* ---- title & legend appear with slight fade ---- */
    .nc-title, .nc-legend {
      animation: nc-fade-in 1.2s ease-out;
    }
    @keyframes nc-fade-in {
      from { opacity: 0; transform: translateY(-6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    /* ---- weather layers ---- */
    .nc-weather {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }
    .nc-rain {
      background-image:
        linear-gradient(175deg, rgba(126, 200, 255, 0.55) 1px, transparent 1px),
        linear-gradient(185deg, rgba(126, 200, 255, 0.35) 1px, transparent 1px);
      background-size: 3px 14px, 4px 18px;
      background-position: 0 0, 30px 40px;
      animation: nc-rain-shift 0.6s linear infinite;
      opacity: 0.5;
      mix-blend-mode: screen;
    }
    @keyframes nc-rain-shift {
      to { background-position: -6px 120px, 24px 160px; }
    }
    .nc-rain.nc-storm {
      opacity: 0.85;
      animation-duration: 0.35s;
    }
    .nc-storm::after {
      content: "";
      position: absolute;
      inset: 0;
      background: rgba(200, 220, 255, 0.08);
      animation: nc-lightning 4s infinite;
    }
    @keyframes nc-lightning {
      0%, 92%, 100% { opacity: 0; }
      93% { opacity: 0.6; }
      94% { opacity: 0.05; }
      95% { opacity: 0.4; }
      96% { opacity: 0; }
    }
    .nc-snow {
      background-image:
        radial-gradient(circle 1px at 10px 10px, rgba(232, 244, 255, 0.9), transparent 2px),
        radial-gradient(circle 1px at 40px 30px, rgba(232, 244, 255, 0.7), transparent 2px),
        radial-gradient(circle 1px at 70px 60px, rgba(232, 244, 255, 0.8), transparent 2px);
      background-size: 90px 90px, 120px 120px, 150px 150px;
      animation: nc-snow-shift 12s linear infinite;
      opacity: 0.7;
    }
    @keyframes nc-snow-shift {
      to { background-position: -40px 90px, 30px 120px, 70px 150px; }
    }
    .nc-smog {
      background:
        radial-gradient(ellipse at 30% 40%, rgba(140, 90, 140, 0.18), transparent 60%),
        radial-gradient(ellipse at 70% 60%, rgba(180, 90, 60, 0.12), transparent 55%);
      mix-blend-mode: multiply;
      animation: nc-smog-drift 30s ease-in-out infinite alternate;
    }
    @keyframes nc-smog-drift {
      from { transform: translate(0, 0); }
      to   { transform: translate(40px, -20px); }
    }

    /* при скролле — пауза */
    body.scrolling .nc-ncart,
    body.scrolling .nc-light,
    body.scrolling .nc-building-glow,
    body.scrolling .nc-scan,
    body.scrolling .nc-scan-sweep,
    body.scrolling .nc-rain,
    body.scrolling .nc-snow,
    body.scrolling .nc-smog,
    body.scrolling .nc-corners,
    body.scrolling .nc-compass-spin,
    body.scrolling .nc-landmark {
      animation-play-state: paused !important;
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

    print("\nСпринт 22 — детальная карта Найт-Сити\n")

    (src / "PixelCity.tsx").write_text(PIXEL_CITY, encoding="utf-8")
    print(f"  ~ {src / 'PixelCity.tsx'}")

    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    # удаляем старую секцию NIGHT CITY MAP если была
    if "NIGHT CITY MAP" in css_text:
        # найдём начало и до конца файла — обрежем
        idx = css_text.find("/* ============================================================\n       NIGHT CITY MAP")
        if idx > 0:
            css_text = css_text[:idx].rstrip()
    css_text = css_text.rstrip() + "\n" + NIGHT_CITY_CSS + "\n"
    css_path.write_text(css_text, encoding="utf-8")
    print(f"  ~ {css_path}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что нового:")
    print("  • 6 районов × 250+ зданий (генерация по seed)")
    print("  • 18 подрайонов (KABUKI, JAPANTOWN, DOWNTOWN...)")
    print("  • Мосты FRANKLIN / NORTHSIDE через залив")
    print("  • I-101 / I-280 / NC-1 highways с трафиком")
    print("  • NCART линии метро (dashed cyan)")
    print("  • 10 иконок-достопримечательностей (NCPD, Trauma, Delamain, Arasaka...)")
    print("  • Компас, легенда, координаты, corner brackets")
    print("  • Трафик — светящиеся точки по дорогам")
    print("  • Scan line + sweep + погода")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())