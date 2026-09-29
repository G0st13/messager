#!/usr/bin/env python3
"""sprint7.py - cyberpunk redesign."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== TAILWIND
T["frontend/tailwind.config.js"] = _t("""
    /** @type {import('tailwindcss').Config} */
    export default {
      content: ["./index.html", "./src/**/*.{ts,tsx}"],
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            cyber: {
              cyan: "#00f0ff",
              magenta: "#ff00a0",
              yellow: "#fcee0a",
              red: "#ff2d55",
              bg: "#05070d",
              panel: "#0a0f1a",
              elevated: "#0f1522",
              border: "#1a2537",
              text: "#b8d4e8",
              dim: "#5a7a95",
            },
            tg: {
              bg: "#05070d",
              panel: "#0a0f1a",
              side: "#080c15",
              bubble: "#0f1522",
              accent: "#00f0ff",
            },
            brand: {
              50: "#e6feff",
              500: "#00f0ff",
              600: "#00c4d4",
              700: "#0097a3",
            },
          },
          fontFamily: {
            mono: ["JetBrains Mono", "Fira Code", "Consolas", "monospace"],
          },
          boxShadow: {
            "neon-cyan": "0 0 12px rgba(0,240,255,0.5), inset 0 0 12px rgba(0,240,255,0.1)",
            "neon-magenta": "0 0 12px rgba(255,0,160,0.5), inset 0 0 12px rgba(255,0,160,0.1)",
            "neon-yellow": "0 0 12px rgba(252,238,10,0.5), inset 0 0 12px rgba(252,238,10,0.1)",
          },
        },
      },
      plugins: [],
    };
""")

# ============================================================== INDEX.CSS
T["frontend/src/index.css"] = _t("""
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
    }

    html, body, #root { height: 100%; margin: 0; }

    body {
      font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
      background: var(--bg-deep);
      color: #b8d4e8;
      overflow: hidden;
      letter-spacing: 0.02em;
    }

    /* ============= Grid background ============= */
    .cyber-bg {
      position: fixed;
      inset: 0;
      z-index: 0;
      pointer-events: none;
      overflow: hidden;
    }
    .cyber-bg::before {
      content: "";
      position: absolute;
      inset: 0;
      background-image:
        linear-gradient(rgba(0,240,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,240,255,0.035) 1px, transparent 1px);
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
        radial-gradient(ellipse at 20% 10%, rgba(255,0,160,0.08), transparent 40%),
        radial-gradient(ellipse at 80% 90%, rgba(0,240,255,0.08), transparent 40%),
        radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.75) 100%);
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

    /* ============= Blinking cursor ============= */
    .cursor::after {
      content: "▮";
      color: var(--neon-cyan);
      animation: blink 1s step-end infinite;
      margin-left: 2px;
      text-shadow: 0 0 6px var(--neon-cyan);
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* ============= Pulse ============= */
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

    /* ============= Data stream ============= */
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

    /* ============= Wire dash ============= */
    .wire-dash {
      stroke-dasharray: 6 10;
      animation: dash-move 30s linear infinite;
    }
    @keyframes dash-move {
      to { stroke-dashoffset: -2000; }
    }
    .wire-glow { filter: drop-shadow(0 0 3px rgba(0,240,255,0.8)); }
    .wire-glow-mag { filter: drop-shadow(0 0 3px rgba(255,0,160,0.8)); }

    /* ============= Chroma hover ============= */
    .chroma:hover { animation: chroma 0.35s; }
    @keyframes chroma {
      0%   { text-shadow: 0 0 6px rgba(0,240,255,0.6); }
      25%  { text-shadow: 2px 0 var(--neon-magenta), -2px 0 var(--neon-cyan); }
      50%  { text-shadow: -2px 0 var(--neon-magenta), 2px 0 var(--neon-cyan); }
      100% { text-shadow: 0 0 6px rgba(0,240,255,0.6); }
    }

    /* ============= Corner brackets ============= */
    .corner-frame { position: relative; }
    .corner-frame::before,
    .corner-frame::after {
      content: "";
      position: absolute;
      width: 14px;
      height: 14px;
      border: 2px solid var(--neon-cyan);
      pointer-events: none;
      filter: drop-shadow(0 0 3px rgba(0,240,255,0.7));
    }
    .corner-frame::before {
      top: -1px; left: -1px;
      border-right: none; border-bottom: none;
    }
    .corner-frame::after {
      bottom: -1px; right: -1px;
      border-left: none; border-top: none;
    }
    .corner-frame-mag::before,
    .corner-frame-mag::after {
      border-color: var(--neon-magenta);
      filter: drop-shadow(0 0 3px rgba(255,0,160,0.7));
    }

    /* ============= Scrollbar ============= */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(0,240,255,0.04); }
    ::-webkit-scrollbar-thumb {
      background: rgba(0,240,255,0.3);
      border-radius: 0;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,240,255,0.55); }

    ::selection {
      background: rgba(255,0,160,0.5);
      color: #fff;
      text-shadow: 0 0 6px var(--neon-magenta);
    }

    /* ============= Entry animation ============= */
    @keyframes materialize {
      from { opacity: 0; transform: translateY(6px) scale(0.98); filter: blur(2px); }
      to   { opacity: 1; transform: translateY(0) scale(1); filter: blur(0); }
    }
    .animate-materialize { animation: materialize 0.25s ease-out; }

    /* ============= Terminal input ============= */
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

    /* ============= Button ============= */
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

    /* ============= HUD panel ============= */
    .hud-panel {
      background:
        linear-gradient(180deg, rgba(0,240,255,0.03), transparent 30%),
        rgba(10,15,26,0.85);
      border: 1px solid rgba(0,240,255,0.18);
      backdrop-filter: blur(4px);
    }

    /* ============= Status dot ============= */
    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }
""")

# ============================================================== CYBER BG
T["frontend/src/CyberBackground.tsx"] = _t("""
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
            <path
              className="wire-dash wire-glow"
              d="M-10 40 Q 60 40 90 20 T 210 -10"
              stroke="#00f0ff"
              strokeWidth="1.2"
            />
            <path
              className="wire-dash"
              d="M-10 70 Q 40 70 60 50 T 210 30"
              stroke="#ff00a0"
              strokeWidth="0.8"
            />
            <path
              className="wire-dash"
              d="M-10 100 Q 30 100 50 80 T 210 60"
              stroke="#00f0ff"
              strokeWidth="0.6"
              opacity="0.6"
            />
          </svg>

          <svg
            className="pointer-events-none absolute bottom-0 right-0 h-72 w-72 opacity-40"
            viewBox="0 0 220 220"
            fill="none"
          >
            <path
              className="wire-dash wire-glow-mag"
              d="M230 180 Q 160 180 130 200 T -10 230"
              stroke="#ff00a0"
              strokeWidth="1.2"
            />
            <path
              className="wire-dash"
              d="M230 150 Q 180 150 160 170 T -10 200"
              stroke="#00f0ff"
              strokeWidth="0.8"
            />
            <path
              className="wire-dash"
              d="M230 120 Q 190 120 175 140 T -10 170"
              stroke="#fcee0a"
              strokeWidth="0.6"
              opacity="0.6"
            />
          </svg>

          {/* Стримы данных */}
          {streams.map((s, i) => (
            <div
              key={i}
              className="data-stream"
              style={{
                left: s.left,
                animationDelay: s.delay,
                animationDuration: s.dur,
              }}
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
    }
""")

# ============================================================== AVATAR
T["frontend/src/Avatar.tsx"] = _t("""
    import type { User } from "./types";

    export default function Avatar({
      user, size = 40, showOnline = false, online = false
    }: {
      user: Pick<User, "username" | "display_name" | "avatar_color">;
      size?: number;
      showOnline?: boolean;
      online?: boolean;
    }) {
      const name = user.display_name || user.username || "?";
      const initials = name
        .split(/\\s+/)
        .map((w) => w[0])
        .filter(Boolean)
        .slice(0, 2)
        .join("")
        .toUpperCase();
      const color = user.avatar_color || "#00f0ff";

      return (
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <div
            className="relative flex h-full w-full items-center justify-center overflow-hidden rounded-full font-bold"
            style={{
              background: `radial-gradient(circle at 30% 30%, ${color}22, #0a0f1a 80%)`,
              border: `1px solid ${color}`,
              boxShadow: `0 0 12px ${color}66, inset 0 0 12px ${color}22`,
              color: color,
              fontSize: size * 0.38,
              letterSpacing: "0.05em",
              textShadow: `0 0 8px ${color}`,
            }}
          >
            {initials}
            {/* scanlines overlay */}
            <div
              className="pointer-events-none absolute inset-0 opacity-30"
              style={{
                background:
                  "repeating-linear-gradient(0deg, transparent 0, transparent 2px, rgba(0,240,255,0.15) 3px, transparent 4px)",
              }}
            />
          </div>

          {showOnline && (
            <span
              className={
                "absolute bottom-0 right-0 block rounded-full " +
                (online ? "pulse-glow" : "")
              }
              style={{
                width: size * 0.26,
                height: size * 0.26,
                background: online ? "#00ff88" : "#5a7a95",
                boxShadow: online
                  ? "0 0 10px #00ff88"
                  : "0 0 4px rgba(90,122,149,0.5)",
                border: "2px solid #05070d",
              }}
            />
          )}
        </div>
      );
    }
""")

# ============================================================== LOGIN
T["frontend/src/Login.tsx"] = _t("""
    import { useEffect, useState } from "react";
    import { api } from "./api";

    const BOOT_LINES = [
      "> INITIALIZING NEURAL LINK...",
      "> CONNECTING TO NODE 0x7F4A...",
      "> ENCRYPTION: AES-256 ACTIVE",
      "> HANDSHAKE COMPLETE",
      "> AWAITING IDENTIFICATION",
    ];

    export default function Login({ onLogin }: { onLogin: () => void }) {
      const [mode, setMode] = useState<"login" | "register">("login");
      const [username, setUsername] = useState("");
      const [password, setPassword] = useState("");
      const [email, setEmail] = useState("");
      const [displayName, setDisplayName] = useState("");
      const [error, setError] = useState("");
      const [busy, setBusy] = useState(false);
      const [visibleBoot, setVisibleBoot] = useState(0);

      useEffect(() => {
        if (visibleBoot >= BOOT_LINES.length) return;
        const t = setTimeout(() => setVisibleBoot((v) => v + 1), 320);
        return () => clearTimeout(t);
      }, [visibleBoot]);

      const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setBusy(true);
        try {
          if (mode === "register") {
            await api.post("/auth/register", {
              username, email, password,
              display_name: displayName || null,
            });
          }
          const { data } = await api.post("/auth/login", { username, password });
          localStorage.setItem("access_token", data.access_token);
          onLogin();
        } catch (err: any) {
          setError(err.response?.data?.detail || "ACCESS DENIED");
        } finally {
          setBusy(false);
        }
      };

      const inputCls = "cyber-input w-full rounded-sm px-4 py-3 text-sm";

      return (
        <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
          <div className="corner-frame w-full max-w-md hud-panel rounded-sm p-8">
            {/* Header */}
            <div className="mb-6 text-center">
              <div className="flicker mb-4 inline-block">
                <div className="text-6xl">◈</div>
              </div>
              <h1
                className="glitch text-3xl font-bold tracking-widest"
                data-text="MESSENGER"
              >
                MESSENGER
              </h1>
              <div className="mt-2 text-[10px] uppercase tracking-[0.4em] text-cyber-dim">
                {mode === "login" ? "secure access terminal" : "register new operator"}
              </div>
            </div>

            {/* Boot sequence */}
            <div className="mb-6 h-20 overflow-hidden border-l-2 border-cyber-cyan/40 bg-black/40 p-3 text-[10px] leading-relaxed text-cyber-cyan/80">
              {BOOT_LINES.slice(0, visibleBoot).map((l, i) => (
                <div key={i} className="animate-materialize">
                  {l}
                </div>
              ))}
              {visibleBoot >= BOOT_LINES.length && (
                <div className="cursor neon-text" />
              )}
            </div>

            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                  // OPERATOR ID
                </label>
                <input
                  className={inputCls}
                  placeholder="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>

              {mode === "register" && (
                <>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // COMM CHANNEL
                    </label>
                    <input
                      className={inputCls}
                      type="email"
                      placeholder="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // CALLSIGN (optional)
                    </label>
                    <input
                      className={inputCls}
                      placeholder="display name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                    />
                  </div>
                </>
              )}

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                  // ACCESS KEY
                </label>
                <input
                  className={inputCls}
                  type="password"
                  placeholder="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="neon-border-mag animate-materialize rounded-sm bg-cyber-magenta/10 px-3 py-2 text-center text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="cyber-btn w-full rounded-sm py-3 text-sm font-bold"
              >
                {busy ? "[ AUTHENTICATING... ]" : mode === "login" ? "[ ENTER SYSTEM ]" : "[ CREATE OPERATOR ]"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
                className="w-full text-center text-[11px] uppercase tracking-widest text-cyber-dim transition hover:text-cyber-cyan chroma"
              >
                {mode === "login"
                  ? "> no account? register"
                  : "> already have access? sign in"}
              </button>
            </form>

            {/* Footer */}
            <div className="mt-6 flex items-center justify-between border-t border-cyber-cyan/20 pt-3 text-[9px] uppercase tracking-widest text-cyber-dim">
              <span className="flex items-center gap-2">
                <span className="status-dot" style={{ color: "#00ff88" }} />
                node: online
              </span>
              <span>v7.0.cyber</span>
            </div>
          </div>
        </div>
    );
""")

# ============================================================== CHAT LIST
T["frontend/src/ChatList.tsx"] = _t("""
    import { useMemo, useState } from "react";
    import Avatar from "./Avatar";
    import type { Chat, User } from "./types";

    function fmtTime(iso: string | null | undefined) {
      if (!iso) return "--:--";
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString())
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "YESTERDAY";
      return d.toLocaleDateString([], { day: "2-digit", month: "2-digit" });
    }

    function chatTitle(c: Chat) {
      if (c.peer) return c.peer.display_name || c.peer.username;
      return c.title || `NODE #${c.id}`;
    }

    function chatSubtitle(c: Chat) {
      const lm = c.last_message;
      if (!lm) return "// no transmission";
      if (lm.message_type === "system") return lm.text || "";
      const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
      let body = lm.text || "";
      if (lm.message_type === "image") body = "▣ IMAGE DATA";
      else if (lm.message_type === "voice") body = "◍ AUDIO SIGNAL";
      else if (lm.message_type === "file") body = `▤ ${lm.attachment?.filename || "FILE"}`;
      else if (lm.message_type === "sticker") body = lm.text || "◈ SIGIL";
      return "> " + who + body;
    }

    export default function ChatList({
      chats, activeId, onSelect, onlineUsers, currentUser, onOpenProfile, onOpenSettings,
      onOpenFeed, onOpenMyProfile, mode
    }: {
      chats: Chat[];
      activeId: number | null;
      onSelect: (id: number) => void;
      onlineUsers: Set<number>;
      currentUser: User;
      onOpenProfile: () => void;
      onOpenSettings: () => void;
      onOpenFeed: () => void;
      onOpenMyProfile: () => void;
      mode: "chats" | "feed" | "profile";
    }) {
      const [query, setQuery] = useState("");

      const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return chats;
        return chats.filter((c) =>
          chatTitle(c).toLowerCase().includes(q) ||
          chatSubtitle(c).toLowerCase().includes(q)
        );
      }, [chats, query]);

      const unreadTotal = chats.reduce((s, c) => s + c.unread_count, 0);

      return (
        <aside className="relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/20 bg-cyber-panel/60 backdrop-blur-sm">
          {/* Header */}
          <div className="border-b border-cyber-cyan/20 p-3">
            <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-widest text-cyber-dim">
              <span>// operator</span>
              <span className="flex items-center gap-1">
                <span className="status-dot" style={{ color: "#00ff88" }} />
                online
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={onOpenProfile} className="transition hover:opacity-80">
                <Avatar user={currentUser} size={44} />
              </button>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold neon-text">
                  {currentUser.display_name || currentUser.username}
                </div>
                <div className="truncate text-[10px] text-cyber-dim">
                  @{currentUser.username}
                </div>
              </div>
              <button
                onClick={onOpenSettings}
                title="Settings"
                className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10 hover:shadow-neon-cyan"
              >
                ⚙
              </button>
            </div>
          </div>

          {/* Search */}
          <div className="border-b border-cyber-cyan/10 p-3">
            <div className="relative">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-cyber-cyan/60 text-xs">
                ▸
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="SEARCH CHANNELS"
                className="cyber-input w-full rounded-sm py-2 pl-6 pr-3 text-xs uppercase tracking-wider"
              />
            </div>
          </div>

          {/* Mode buttons */}
          <div className="flex border-b border-cyber-cyan/20">
            <button
              onClick={onOpenFeed}
              className={
                "flex-1 py-2 text-[10px] font-bold uppercase tracking-widest transition " +
                (mode === "feed"
                  ? "bg-cyber-cyan/15 neon-text border-b-2 border-cyber-cyan"
                  : "text-cyber-dim hover:bg-cyber-cyan/5 hover:text-cyber-cyan")
              }
            >
              ◉ feed
            </button>
            <button
              onClick={onOpenMyProfile}
              className={
                "flex-1 py-2 text-[10px] font-bold uppercase tracking-widest transition " +
                (mode === "profile"
                  ? "bg-cyber-cyan/15 neon-text border-b-2 border-cyber-cyan"
                  : "text-cyber-dim hover:bg-cyber-cyan/5 hover:text-cyber-cyan")
              }
            >
              ◉ profile
            </button>
          </div>

          {/* Channel list */}
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-6 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                // no channels found
              </div>
            ) : (
              filtered.map((c) => {
                const active = c.id === activeId && mode === "chats";
                const peerOnline = c.peer ? onlineUsers.has(c.peer.id) : false;
                const avatarUser = c.peer || {
                  username: c.title || "G",
                  display_name: c.title || "GRP",
                  avatar_color: c.avatar_color || "#ff00a0",
                };
                const hasUnread = c.unread_count > 0 && !active;

                return (
                  <button
                    key={c.id}
                    onClick={() => onSelect(c.id)}
                    className={
                      "group relative flex w-full items-center gap-3 border-b border-cyber-cyan/10 px-3 py-3 text-left transition " +
                      (active
                        ? "bg-cyber-cyan/10 border-l-2 border-l-cyber-cyan"
                        : "hover:bg-cyber-cyan/5 border-l-2 border-l-transparent")
                    }
                  >
                    <Avatar
                      user={avatarUser as any}
                      size={44}
                      showOnline={!!c.peer}
                      online={peerOnline}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span
                          className={
                            "truncate text-sm font-bold " +
                            (active ? "neon-text" : "text-cyber-text group-hover:neon-text")
                          }
                        >
                          {chatTitle(c)}
                        </span>
                        <span className="shrink-0 text-[9px] uppercase tracking-wider text-cyber-dim">
                          {fmtTime(c.last_message?.created_at || c.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={
                            "truncate text-[11px] " +
                            (active ? "text-cyber-cyan/80" : "text-cyber-dim")
                          }
                        >
                          {chatSubtitle(c)}
                        </span>
                        {hasUnread && (
                          <span className="neon-border-mag shrink-0 rounded-sm px-1.5 py-0.5 text-[9px] font-bold neon-text-mag pulse-glow-mag">
                            {c.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer status */}
          <div className="border-t border-cyber-cyan/20 p-2 text-[9px] uppercase tracking-widest text-cyber-dim">
            <div className="flex items-center justify-between">
              <span>channels: {chats.length}</span>
              {unreadTotal > 0 && (
                <span className="neon-text-mag">unread: {unreadTotal}</span>
              )}
            </div>
          </div>
        </aside>
      );
    }
""")

# ============================================================== MESSAGE BUBBLE
T["frontend/src/MessageBubble.tsx"] = _t('''
    import { useState } from "react";
    import Avatar from "./Avatar";
    import { fileUrl, humanSize } from "./api";
    import type { Message, User } from "./types";

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

    export default function MessageBubble({
      msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer, onOpenImage, onOpenProfile
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
    }) {
      const [menuOpen, setMenuOpen] = useState(false);
      const [audioPlaying, setAudioPlaying] = useState(false);
      const [audioCurrent, setAudioCurrent] = useState(0);
      const [audioDuration, setAudioDuration] = useState(0);

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

      const accent = mine ? "#00f0ff" : "#ff00a0";
      const bubbleStyle = {
        background: mine
          ? "linear-gradient(135deg, rgba(0,240,255,0.08), rgba(0,240,255,0.02))"
          : "linear-gradient(135deg, rgba(255,0,160,0.06), rgba(255,0,160,0.01))",
        border: `1px solid ${accent}55`,
        boxShadow: `0 0 12px ${accent}22, inset 0 0 12px ${accent}08`,
        color: "#d6ecff",
      };

      const radius = isLast ? "rounded-sm" : "rounded-sm";

      const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
      const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
      const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
      const isFile = msg.message_type === "file" && msg.attachment && !msg.is_deleted;

      if (isSticker) {
        return (
          <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
            {!mine ? (
              <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
                {showAvatar && <Avatar user={author} size={32} />}
              </button>
            ) : null}
            <div className="relative">
              <div className="animate-materialize text-7xl leading-none drop-shadow-[0_0_20px_rgba(0,240,255,0.5)]">
                {msg.text}
              </div>
              <div className={"mt-1 flex items-center gap-2 text-[9px] uppercase tracking-wider " + (mine ? "justify-end" : "")}>
                <span className="text-cyber-dim">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && (
                  <span className={readByPeer ? "neon-text" : "text-cyber-dim"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
          {!mine ? (
            <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
              {showAvatar && <Avatar user={author} size={32} />}
            </button>
          ) : null}

          <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
            {!mine && showAvatar && (
              <button
                onClick={() => onOpenProfile(msg.author_id)}
                className="mb-1 ml-2 text-[10px] font-bold uppercase tracking-widest neon-text-mag chroma"
              >
                ◂ {msg.author_display || msg.author_username}
              </button>
            )}

            <div
              className={
                "animate-materialize relative overflow-hidden text-sm " +
                radius + (isImage ? "" : " px-3 py-2")
              }
              style={bubbleStyle}
            >
              {/* Top accent line */}
              <div
                className="absolute left-0 right-0 top-0 h-[1px]"
                style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }}
              />

              {msg.reply_to_id && !msg.is_deleted && (
                <div
                  className="mx-1 mb-2 mt-1 rounded-sm border-l-2 bg-black/40 px-2 py-1 text-[10px]"
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
                  onClick={() => onOpenImage(fileUrl(msg.attachment!.id))}
                  className="block max-h-80 w-full cursor-pointer object-cover"
                  style={{ filter: "contrast(1.05) saturate(1.1)" }}
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
                    {/* fake waveform */}
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
                    <div className="truncate text-sm font-bold text-cyber-text">
                      {msg.attachment.filename}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-cyber-dim">
                      {humanSize(msg.attachment.size)}
                    </div>
                  </div>
                </a>
              )}

              {!isImage && !isVoice && !isFile && (
                <div className={msg.is_deleted ? "italic opacity-50 text-xs" : "whitespace-pre-wrap break-words"}>
                  {msg.text}
                </div>
              )}

              <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">
                {msg.edited_at && <span className="text-cyber-yellow/70">[edited]</span>}
                <span className="text-cyber-dim">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && !msg.is_deleted && (
                  <span className={readByPeer ? "neon-text" : "text-cyber-dim"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>

            {!msg.is_deleted && (
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className={
                  "absolute top-1 hidden rounded-sm border border-cyber-cyan/40 bg-cyber-panel/90 px-1.5 py-0.5 text-xs text-cyber-cyan group-hover:block hover:bg-cyber-cyan/20 " +
                  (mine ? "-left-7" : "-right-7")
                }
              >
                ▾
              </button>
            )}

            {menuOpen && (
              <div
                className={
                  "animate-materialize absolute z-20 mt-1 w-32 overflow-hidden rounded-sm border border-cyber-cyan/40 bg-cyber-panel text-xs shadow-neon-cyan " +
                  (mine ? "right-0" : "left-0")
                }
              >
                <button
                  onClick={() => { onReply(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
                >
                  ↳ reply
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
''')

# ============================================================== APP
T["frontend/src/App.tsx"] = _t('''
    import { useCallback, useEffect, useRef, useState } from "react";
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
    import { api } from "./api";
    import { useWebSocket } from "./ws";
    import { useWebRTC } from "./useWebRTC";
    import type { CallInfo, Chat, User } from "./types";

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
      const [theme, setTheme] = useState<"light" | "dark">(
        (localStorage.getItem("theme") as "light" | "dark") || "dark"
      );
      const [mode, setMode] = useState<Mode>("chats");
      const [profileUserId, setProfileUserId] = useState<number | null>(null);
      const [incomingCall, setIncomingCall] = useState<CallInfo | null>(null);
      const [callDuration, setCallDuration] = useState(0);
      const offerRef = useRef<RTCSessionDescriptionInit | null>(null);

      useEffect(() => {
        document.documentElement.classList.toggle("dark", theme === "dark");
        localStorage.setItem("theme", theme);
      }, [theme]);

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
        }
      }, [activeChatId, user?.id, user?.username, user?.display_name, user?.avatar_color]);

      const { send, subscribe } = useWebSocket(onWs);
      const rtc = useWebRTC(send, subscribe);

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

      const logout = () => {
        localStorage.removeItem("access_token");
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
          try { await api.post(`/calls/${s.id ?? s.callId}/end`); } catch {}
        }
      };

      if (loading) {
        return (
          <>
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
            <CyberBackground />
            <Login onLogin={loadMe} />
          </>
        );
      }

      const activeChat = chats.find((c) => c.id === activeChatId) || null;
      const inCall = rtc.session !== null && (rtc.status === "connecting" || rtc.status === "active" || rtc.status === "ringing");

      return (
        <>
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

    print("\nСпринт 7: cyberpunk redesign")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())