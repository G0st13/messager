#!/usr/bin/env python3
"""sprint21.py - Night City map as background."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


PIXEL_CITY = r'''import { useEffect, useMemo, useState } from "react";

export type Weather = "auto" | "clear" | "rain" | "snow" | "smog" | "storm";

const W = 900;
const H = 560;

interface District {
  id: string;
  label: string;
  path: string;
  color: string;
  cx: number;
  cy: number;
}

const DISTRICTS: District[] = [
  {
    id: "watson", label: "WATSON", color: "#00f0ff", cx: 240, cy: 130,
    path: "M 100,60 L 320,50 L 360,60 L 380,180 L 340,210 L 180,200 L 130,140 Z",
  },
  {
    id: "westbrook", label: "WESTBROOK", color: "#b967ff", cx: 590, cy: 140,
    path: "M 400,50 L 720,60 L 760,100 L 770,200 L 720,230 L 540,220 L 500,180 L 420,120 Z",
  },
  {
    id: "citycenter", label: "CITY CENTER", color: "#fcee0a", cx: 450, cy: 315,
    path: "M 320,240 L 540,230 L 590,250 L 610,340 L 560,390 L 380,400 L 300,360 L 290,290 Z",
  },
  {
    id: "heywood", label: "HEYWOOD", color: "#ff00a0", cx: 730, cy: 350,
    path: "M 640,250 L 800,260 L 840,320 L 830,430 L 750,470 L 660,450 L 620,380 L 640,310 Z",
  },
  {
    id: "santodomingo", label: "SANTO DOMINGO", color: "#ff6600", cx: 240, cy: 370,
    path: "M 140,240 L 280,250 L 300,360 L 380,400 L 360,480 L 200,510 L 150,470 L 130,380 Z",
  },
  {
    id: "pacifica", label: "PACIFICA", color: "#7cff00", cx: 500, cy: 480,
    path: "M 400,420 L 540,400 L 600,430 L 640,500 L 600,540 L 480,545 L 400,510 L 370,470 Z",
  },
];

const WATER_PATH = "M 0,0 L 100,0 L 130,140 L 120,280 L 90,420 L 140,560 L 0,560 Z";

const FREEWAYS: string[] = [
  "M 250,170 Q 320,220 380,270",
  "M 570,200 Q 520,230 480,260",
  "M 560,300 Q 620,310 660,320",
  "M 360,360 Q 320,360 280,340",
  "M 450,400 Q 470,420 470,440",
  "M 320,440 Q 380,450 420,450",
  "M 700,420 Q 640,440 580,450",
  "M 340,110 Q 400,100 460,110",
];

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

function timeOfDay(): "night" | "dawn" | "day" | "sunset" {
  const h = new Date().getHours();
  if (h >= 21 || h < 5) return "night";
  if (h < 7) return "dawn";
  if (h < 18) return "day";
  return "sunset";
}

interface Palette {
  bg: string;
  water: string;
  grid: string;
  frame: string;
}

const PALETTES: Record<string, Palette> = {
  night:  { bg: "#03060c", water: "#05131f", grid: "rgba(0,240,255,0.05)", frame: "rgba(0,240,255,0.35)" },
  dawn:   { bg: "#0a0611", water: "#0f0818", grid: "rgba(184,103,255,0.05)", frame: "rgba(184,103,255,0.4)" },
  day:    { bg: "#0a1018", water: "#0d1520", grid: "rgba(0,240,255,0.04)", frame: "rgba(0,240,255,0.3)" },
  sunset: { bg: "#100a12", water: "#180810", grid: "rgba(255,102,0,0.05)", frame: "rgba(255,102,0,0.4)" },
};

export default function PixelCity({
  weather = "auto",
  seed = 1,
}: {
  weather?: Weather;
  seed?: number;
}) {
  const [, setTick] = useState(0);

  // обновляем палитру каждый час
  useEffect(() => {
    const int = window.setInterval(() => setTick((v) => v + 1), 60 * 60 * 1000);
    return () => window.clearInterval(int);
  }, []);

  const effective: Weather = weather === "auto"
    ? (["clear", "rain", "rain", "snow", "smog"] as const)[new Date().getDate() % 5]
    : weather;

  const tod = timeOfDay();
  const pal = PALETTES[tod];

  // городские огни, генерируются по seed
  const lights = useMemo(() => {
    const rng = mulberry32(seed);
    const out: { x: number; y: number; c: string; phase: number }[] = [];
    for (let i = 0; i < 110; i++) {
      const d = DISTRICTS[Math.floor(rng() * DISTRICTS.length)];
      const x = d.cx + (rng() - 0.5) * 200;
      const y = d.cy + (rng() - 0.5) * 160;
      out.push({
        x,
        y,
        c: rng() < 0.4 ? d.color : rng() < 0.5 ? "#00f0ff" : "#ffffff",
        phase: rng() * 4,
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
          <radialGradient id="ncWater" cx="0.5" cy="0.5" r="0.85">
            <stop offset="0" stopColor={pal.water} />
            <stop offset="1" stopColor="#000408" />
          </radialGradient>
          <radialGradient id="ncVignette" cx="0.5" cy="0.5" r="0.78">
            <stop offset="0.4" stopColor="rgba(0,0,0,0)" />
            <stop offset="1" stopColor="rgba(0,0,0,0.88)" />
          </radialGradient>
          <pattern id="ncGrid" width="50" height="50" patternUnits="userSpaceOnUse">
            <path d="M 50 0 L 0 0 0 50" fill="none" stroke={pal.grid} strokeWidth="1" />
          </pattern>
        </defs>

        {/* база */}
        <rect width={W} height={H} fill={pal.bg} />

        {/* координатная сетка */}
        <rect width={W} height={H} fill="url(#ncGrid)" />

        {/* вода */}
        <path d={WATER_PATH} fill="url(#ncWater)" />
        <path d={WATER_PATH} fill="none" stroke="rgba(0,240,255,0.25)" strokeWidth={0.8} />

        {/* рамка Badlands */}
        <rect
          x={14}
          y={14}
          width={W - 28}
          height={H - 28}
          fill="none"
          stroke="rgba(240,176,48,0.18)"
          strokeWidth={1}
          strokeDasharray="2 8"
        />

        {/* фривеи */}
        <g>
          {FREEWAYS.map((d, i) => (
            <g key={"fw-" + i}>
              <path d={d} fill="none" stroke="#ff00a0" strokeWidth={3} opacity={0.12} />
              <path d={d} fill="none" stroke="#ff00a0" strokeWidth={1.2} className="nc-freeway" />
            </g>
          ))}
        </g>

        {/* районы */}
        <g>
          {DISTRICTS.map((d) => (
            <g key={d.id} className="nc-district">
              <path
                d={d.path}
                fill={d.color}
                fillOpacity={0.04}
                stroke={d.color}
                strokeWidth={1}
                strokeOpacity={0.8}
              />
              <path
                d={d.path}
                fill="none"
                stroke={d.color}
                strokeWidth={0.4}
                strokeOpacity={0.35}
                transform="translate(3 3)"
              />
            </g>
          ))}
        </g>

        {/* городские огни */}
        <g>
          {lights.map((l, i) => (
            <circle
              key={"l-" + i}
              cx={l.x}
              cy={l.y}
              r={1}
              fill={l.c}
              className="nc-light"
              style={{ animationDelay: l.phase + "s" }}
            />
          ))}
        </g>

        {/* подписи районов */}
        <g>
          {DISTRICTS.map((d) => (
            <g key={"lab-" + d.id}>
              <text
                x={d.cx}
                y={d.cy}
                textAnchor="middle"
                fill={d.color}
                className="nc-label"
                fontSize={11}
                letterSpacing={3}
              >
                {d.label}
              </text>
              <text
                x={d.cx}
                y={d.cy + 14}
                textAnchor="middle"
                fill={d.color}
                opacity={0.55}
                fontSize={6}
                letterSpacing={2}
                className="nc-sublabel"
              >
                SECTOR {String(d.cx).padStart(3, "0")}
              </text>
            </g>
          ))}
        </g>

        {/* сканирующий луч */}
        <line
          x1={0}
          y1={0}
          x2={W}
          y2={0}
          stroke="rgba(0,240,255,0.55)"
          strokeWidth={1}
          className="nc-scan"
        />

        {/* компас */}
        <g transform="translate(840, 66)" className="nc-compass">
          <circle r={22} fill="rgba(5,7,13,0.75)" stroke={pal.frame} strokeWidth={1} />
          <circle r={18} fill="none" stroke={pal.frame} strokeWidth={0.4} opacity={0.6} />
          <path d="M 0,-16 L -3,2 L 0,-2 L 3,2 Z" fill="#00f0ff" />
          <text textAnchor="middle" y={-26} fill="#00f0ff" fontSize={8} letterSpacing={2}>N</text>
          <text textAnchor="middle" y={32} fill={pal.frame} fontSize={7} letterSpacing={1}>
            34°03'
          </text>
        </g>

        {/* легенда */}
        <g transform="translate(20, 488)" className="nc-legend">
          <rect
            width={220}
            height={58}
            fill="rgba(5,7,13,0.8)"
            stroke={pal.frame}
            strokeWidth={1}
          />
          <text x={8} y={16} fill="#00f0ff" fontSize={9} letterSpacing={2}>
            NIGHT CITY // NC-CENTRAL
          </text>
          <text x={8} y={30} fill="#7a90a8" fontSize={7} letterSpacing={1}>
            POP 6,195,000 · ALT 42m · TEMP 18°C
          </text>
          <text x={8} y={42} fill="#7a90a8" fontSize={7} letterSpacing={1}>
            SYS v2077.4 · {tod.toUpperCase()} · {effective.toUpperCase()}
          </text>
          <text x={8} y={52} fill="rgba(0,240,255,0.55)" fontSize={6} letterSpacing={2}>
            ◈ UPLINK STABLE
          </text>
        </g>

        {/* мерцающие детали в углах */}
        <g className="nc-corners">
          <path d="M 30,30 L 30,46 M 30,30 L 46,30" stroke={pal.frame} strokeWidth={1.5} fill="none" />
          <path d={`M ${W - 30},30 L ${W - 30},46 M ${W - 30},30 L ${W - 46},30`} stroke={pal.frame} strokeWidth={1.5} fill="none" />
          <path d={`M 30,${H - 30} L 30,${H - 46} M 30,${H - 30} L 46,${H - 30}`} stroke={pal.frame} strokeWidth={1.5} fill="none" />
          <path d={`M ${W - 30},${H - 30} L ${W - 30},${H - 46} M ${W - 30},${H - 30} L ${W - 46},${H - 30}`} stroke={pal.frame} strokeWidth={1.5} fill="none" />
        </g>

        {/* виньетка */}
        <rect width={W} height={H} fill="url(#ncVignette)" />
      </svg>

      {/* погодные слои поверх */}
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
       NIGHT CITY MAP — фоновый слой
       ============================================================ */
    .night-city-bg {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      overflow: hidden;
      transition: opacity 0.35s, filter 0.35s;
    }

    /* слегка приглушается, когда открыт чат */
    body.chat-open .night-city-bg {
      opacity: 0.35;
      filter: saturate(0.55) brightness(0.65);
    }

    .night-city-svg {
      display: block;
      width: 100%;
      height: 100%;
    }

    /* ---- district outline subtle pulse ---- */
    .nc-district path {
      transition: stroke-opacity 0.6s, fill-opacity 0.6s;
    }
    .nc-district:hover path:first-child {
      fill-opacity: 0.12;
      stroke-opacity: 1;
    }

    /* ---- freeway dash flow ---- */
    .nc-freeway {
      stroke-dasharray: 4 8;
      animation: nc-dash 4s linear infinite;
      filter: drop-shadow(0 0 3px rgba(255, 0, 160, 0.6));
    }
    @keyframes nc-dash {
      to { stroke-dashoffset: -48; }
    }

    /* ---- city lights blink ---- */
    .nc-light {
      animation: nc-light-pulse 3.2s ease-in-out infinite;
    }
    @keyframes nc-light-pulse {
      0%, 100% { opacity: 0.35; }
      50%      { opacity: 1; }
    }

    /* ---- labels ---- */
    .nc-label {
      font-family: "JetBrains Mono", "Fira Code", monospace;
      font-weight: bold;
      paint-order: stroke fill;
      stroke: rgba(0, 0, 0, 0.75);
      stroke-width: 2.5;
      stroke-linejoin: round;
    }
    .nc-sublabel {
      font-family: "JetBrains Mono", "Fira Code", monospace;
      paint-order: stroke fill;
      stroke: rgba(0, 0, 0, 0.7);
      stroke-width: 2;
    }

    /* ---- scan line ---- */
    .nc-scan {
      animation: nc-scan-move 9s linear infinite;
      filter: drop-shadow(0 0 4px rgba(0, 240, 255, 0.8));
    }
    @keyframes nc-scan-move {
      0%   { transform: translateY(0);     opacity: 0; }
      10%  { opacity: 0.7; }
      90%  { opacity: 0.3; }
      100% { transform: translateY(560px); opacity: 0; }
    }

    /* ---- compass slow rotate ring ---- */
    .nc-compass circle:last-of-type {
      animation: nc-compass-spin 24s linear infinite;
      transform-origin: center;
    }
    @keyframes nc-compass-spin {
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

    /* ---- weather layers (поверх SVG) ---- */
    .nc-weather {
      position: absolute;
      inset: 0;
      pointer-events: none;
    }

    /* rain */
    .nc-rain {
      background-image:
        linear-gradient(175deg, rgba(126, 200, 255, 0.55) 1px, transparent 1px),
        linear-gradient(185deg, rgba(126, 200, 255, 0.35) 1px, transparent 1px);
      background-size: 3px 14px, 4px 18px;
      background-position: 0 0, 30px 40px;
      animation: nc-rain-shift 0.6s linear infinite;
      opacity: 0.55;
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

    /* snow */
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

    /* smog */
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

    /* когда скроллим — приглушаем анимации карты, чтобы не лагало */
    body.scrolling .nc-freeway,
    body.scrolling .nc-light,
    body.scrolling .nc-scan,
    body.scrolling .nc-rain,
    body.scrolling .nc-snow,
    body.scrolling .nc-smog,
    body.scrolling .nc-corners {
      animation-play-state: paused !important;
    }
'''


def write_file(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {rel}")


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

    print("\nСпринт 21 — Night City map background\n")

    # перезаписываем PixelCity.tsx новой картой
    write_file(root, "frontend/src/PixelCity.tsx", PIXEL_CITY)

    # CSS
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "NIGHT CITY MAP" not in css_text:
        css_text = css_text.rstrip() + "\n" + NIGHT_CITY_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что нового:")
    print("  • Фон — карта Найт-Сити (6 районов, неоновые контуры)")
    print("  • Фривеи с бегущими пунктирами")
    print("  • Городские огни мерцают")
    print("  • Компас вращается, сканирующий луч ходит по экрану")
    print("  • Погода (rain/snow/smog/storm) поверх карты")
    print("  • Легенда NC-CENTRAL в углу")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())