#!/usr/bin/env python3
"""sprint24.py - Holocall UI in Cyberpunk 2077 style."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================== cyberRingtone.ts
CYBER_RINGTONE = r'''// Web Audio API синтезатор рингтона в стиле Cyberpunk 2077.
// Использует pulsed square + saw, с лёгким глитчем и shimmer.

let ctx: AudioContext | null = null;
let activeNodes: { osc: OscillatorNode; gain: GainNode }[] = [];
let ringTimeout: number | null = null;
let ringing = false;

function getCtx(): AudioContext {
  if (!ctx) {
    const Ctor = (window as any).AudioContext || (window as any).webkitAudioContext;
    ctx = new Ctor();
  }
  if (ctx.state === "suspended") ctx.resume();
  return ctx;
}

// --- single "beep" ---
function beep(freq: number, durMs: number, vol = 0.06, type: OscillatorType = "square") {
  const ac = getCtx();
  const t = ac.currentTime;
  const osc = ac.createOscillator();
  const gain = ac.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(freq, t);

  gain.gain.setValueAtTime(0, t);
  gain.gain.linearRampToValueAtTime(vol, t + 0.01);
  gain.gain.exponentialRampToValueAtTime(0.0001, t + durMs / 1000);

  osc.connect(gain);
  gain.connect(ac.destination);
  osc.start(t);
  osc.stop(t + durMs / 1000 + 0.02);
}

// --- "double-ring" cycle used as incoming tone ---
function ringCycle() {
  if (!ringing) return;
  // два коротких пика + низкий гул
  beep(880, 120, 0.07, "square");
  window.setTimeout(() => beep(1320, 90, 0.05, "square"), 130);
  window.setTimeout(() => beep(660, 140, 0.06, "triangle"), 260);
  window.setTimeout(() => beep(440, 260, 0.04, "sawtooth"), 420);
}

// --- outgoing "dial" tone: softer, low, repeating ---
function dialTone() {
  if (!ringing) return;
  beep(440, 500, 0.04, "sine");
  window.setTimeout(() => beep(554, 500, 0.035, "sine"), 550);
}

export function startIncomingRingtone() {
  if (ringing) return;
  ringing = true;
  // заглушаем возможные старые
  stopRingtone();
  ringing = true;

  // сразу цикл
  ringCycle();
  const loop = () => {
    if (!ringing) return;
    ringCycle();
    ringTimeout = window.setTimeout(loop, 1800);
  };
  ringTimeout = window.setTimeout(loop, 1800);
}

export function startOutgoingRingtone() {
  if (ringing) return;
  ringing = true;
  dialTone();
  const loop = () => {
    if (!ringing) return;
    dialTone();
    ringTimeout = window.setTimeout(loop, 2400);
  };
  ringTimeout = window.setTimeout(loop, 2400);
}

export function stopRingtone() {
  ringing = false;
  if (ringTimeout) {
    window.clearTimeout(ringTimeout);
    ringTimeout = null;
  }
  // гасим активные осцилляторы если остались
  for (const n of activeNodes) {
    try { n.osc.stop(); } catch {}
  }
  activeNodes = [];
}

// --- короткие «системные» бипы для UI ---
export function playConnectBeep() {
  beep(1200, 80, 0.06, "square");
  window.setTimeout(() => beep(1600, 120, 0.05, "square"), 90);
}

export function playDisconnectBeep() {
  beep(600, 120, 0.06, "sawtooth");
  window.setTimeout(() => beep(320, 220, 0.05, "square"), 100);
}

export function playMuteBeep() {
  beep(900, 40, 0.04, "square");
}

export function playDeclineBeep() {
  beep(280, 180, 0.07, "square");
  window.setTimeout(() => beep(200, 260, 0.06, "sawtooth"), 160);
}
'''


# ============================================================== IncomingCallModal.tsx
INCOMING_CALL = r'''import { useEffect } from "react";
import Avatar from "./Avatar";
import { startIncomingRingtone, stopRingtone, playConnectBeep, playDeclineBeep } from "./cyberRingtone";

export default function IncomingCallModal({
  caller, kind, onAccept, onReject,
}: {
  caller: { id: number; username: string; display_name: string | null; avatar_color: string | null };
  kind: "audio" | "video";
  onAccept: () => void;
  onReject: () => void;
}) {
  // Рингтон — играет, пока модалка открыта
  useEffect(() => {
    startIncomingRingtone();
    return () => { stopRingtone(); };
  }, []);

  const accept = () => {
    stopRingtone();
    playConnectBeep();
    onAccept();
  };

  const reject = () => {
    stopRingtone();
    playDeclineBeep();
    onReject();
  };

  // Esc = отклонить, Enter = принять
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") reject();
      if (e.key === "Enter") accept();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  return (
    <div className="holo-overlay holo-overlay--incoming">
      {/* --- Vertical scanlines & noise --- */}
      <div className="holo-scanlines" />
      <div className="holo-noise" />
      <div className="holo-sweep" />

      {/* --- Top status bar --- */}
      <header className="holo-topbar">
        <div className="holo-topbar__left">
          <span className="holo-dot holo-dot--pulse" />
          <span className="holo-topbar__title">INCOMING HOLOCALL</span>
        </div>
        <div className="holo-topbar__right">
          <span className="holo-rec">● REC</span>
          <span className="holo-sep">|</span>
          <span>{new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        </div>
      </header>

      {/* --- Main card --- */}
      <div className="holo-card">
        <div className="holo-card__corner holo-card__corner--tl" />
        <div className="holo-card__corner holo-card__corner--tr" />
        <div className="holo-card__corner holo-card__corner--bl" />
        <div className="holo-card__corner holo-card__corner--br" />

        <div className="holo-card__content">
          {/* Portrait */}
          <div className="holo-portrait">
            <div className="holo-portrait__glitch" data-text="◈" />
            <div className="holo-portrait__frame">
              <Avatar user={caller} size={180} />
            </div>
            <div className="holo-portrait__scan" />
            <div className="holo-portrait__label">SUBJECT</div>
          </div>

          {/* Info */}
          <div className="holo-info">
            <div className="holo-info__kicker">
              ◈ {kind === "video" ? "VIDEO" : "AUDIO"} TRANSMISSION
            </div>
            <h1 className="holo-info__name glitch" data-text={caller.display_name || caller.username}>
              {caller.display_name || caller.username}
            </h1>
            <div className="holo-info__handle">@{caller.username}</div>

            <div className="holo-info__row">
              <span className="holo-info__key">STATUS</span>
              <span className="holo-info__value holo-info__value--cyan">
                CONNECTION SECURED
              </span>
            </div>
            <div className="holo-info__row">
              <span className="holo-info__key">CHANNEL</span>
              <span className="holo-info__value">
                ENCRYPTED · NC-{String(caller.id).padStart(4, "0")}
              </span>
            </div>
            <div className="holo-info__row">
              <span className="holo-info__key">ORIGIN</span>
              <span className="holo-info__value">NIGHT CITY · 2077.4</span>
            </div>

            <div className="holo-info__signal">
              <span>◂ INCOMING TRANSMISSION ▸</span>
              <div className="holo-signal">
                {Array.from({ length: 14 }).map((_, i) => (
                  <div
                    key={i}
                    className="holo-signal__bar"
                    style={{ animationDelay: (i * 0.08) + "s" }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="holo-actions">
          <button className="holo-btn holo-btn--decline" onClick={reject}>
            <span className="holo-btn__icon">✕</span>
            <span className="holo-btn__label">DECLINE</span>
          </button>
          <button className="holo-btn holo-btn--accept" onClick={accept}>
            <span className="holo-btn__icon">◈</span>
            <span className="holo-btn__label">ACCEPT</span>
          </button>
        </div>
      </div>

      {/* --- Footer --- */}
      <footer className="holo-footer">
        <span>◈ NC-CENTRAL · UPLINK STABLE</span>
        <span>PRESS [ENTER] TO ACCEPT · [ESC] TO DECLINE</span>
      </footer>
    </div>
  );
}
'''


# ============================================================== CallWindow.tsx
CALL_WINDOW = r'''import { useEffect, useRef, useState } from "react";
import Avatar from "./Avatar";
import {
  stopRingtone,
  playConnectBeep,
  playDisconnectBeep,
  playMuteBeep,
} from "./cyberRingtone";

function fmt(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

interface TranscriptLine {
  id: number;
  who: "me" | "peer";
  text: string;
}

export default function CallWindow({
  peerName, kind, status, localStream, remoteStream,
  muted, camOff, sharing, durationSec,
  onToggleMute, onToggleCamera, onToggleScreen, onEnd,
}: {
  peerName: string;
  kind: "audio" | "video";
  status: "ringing" | "connecting" | "active" | "ended";
  localStream: MediaStream | null;
  remoteStream: MediaStream | null;
  muted: boolean;
  camOff: boolean;
  sharing: boolean;
  durationSec: number;
  onToggleMute: () => void;
  onToggleCamera: () => void;
  onToggleScreen: () => void;
  onEnd: () => void;
}) {
  const localRef = useRef<HTMLVideoElement>(null);
  const remoteRef = useRef<HTMLVideoElement>(null);
  const [showCaptions, setShowCaptions] = useState(true);
  const [transcript, setTranscript] = useState<TranscriptLine[]>([]);
  const [peerSpeaking, setPeerSpeaking] = useState(false);

  // подключаем video streams
  useEffect(() => {
    if (localRef.current && localStream) localRef.current.srcObject = localStream;
  }, [localStream]);
  useEffect(() => {
    if (remoteRef.current && remoteStream) remoteRef.current.srcObject = remoteStream;
  }, [remoteStream]);

  // при подключении — системный beep, при отключении — тоже
  const prevStatus = useRef(status);
  useEffect(() => {
    if (prevStatus.current !== status) {
      if (status === "active") playConnectBeep();
      if (status === "ended") playDisconnectBeep();
      prevStatus.current = status;
    }
  }, [status]);

  // --- Web Speech API для транскрипции (если доступно) ---
  useEffect(() => {
    if (status !== "active") return;
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "ru-RU";

    let id = 1;
    rec.onresult = (e: any) => {
      const last = e.results[e.results.length - 1];
      const txt = last[0].transcript.trim();
      if (!txt) return;
      if (last.isFinal) {
        setTranscript((t) => [
          ...t.slice(-8),
          { id: id++, who: "me", text: txt },
        ]);
      }
    };
    rec.onerror = () => {};
    try { rec.start(); } catch {}
    return () => {
      try { rec.stop(); } catch {}
    };
  }, [status]);

  // фейковое «собеседник говорит» — мигает когда активен
  useEffect(() => {
    if (status !== "active") return;
    const int = window.setInterval(() => {
      setPeerSpeaking((v) => !v);
      if (Math.random() < 0.35) {
        const samples = [
          "Preem work, choom.",
          "Wake up, samurai.",
          "Connection's solid on my end.",
          "We have a city to burn.",
          "I'm listening.",
          "Uploading the data now.",
          "Meet me at the Afterlife.",
        ];
        const txt = samples[Math.floor(Math.random() * samples.length)];
        setTranscript((t) => [
          ...t.slice(-8),
          { id: Date.now(), who: "peer", text: txt },
        ]);
      }
    }, 2600);
    return () => window.clearInterval(int);
  }, [status]);

  // cleanup ringtone, если оно ещё играло
  useEffect(() => () => stopRingtone(), []);

  const toggleMute = () => { playMuteBeep(); onToggleMute(); };
  const toggleCam = () => { playMuteBeep(); onToggleCamera(); };

  const statusLabel =
    status === "ringing" ? "◂ OUTGOING TRANSMISSION ▸"
    : status === "connecting" ? "◂ ESTABLISHING LINK ▸"
    : status === "active" ? fmt(durationSec)
    : "◂ CONNECTION ENDED ▸";

  return (
    <div className="holo-overlay holo-overlay--call">
      {/* scanlines + noise + sweep */}
      <div className="holo-scanlines" />
      <div className="holo-noise" />
      <div className="holo-sweep holo-sweep--slow" />

      {/* --- Top bar --- */}
      <header className="holo-topbar">
        <div className="holo-topbar__left">
          <span className={"holo-dot " + (status === "active" ? "holo-dot--pulse" : "")} />
          <span className="holo-topbar__title">
            {kind === "video" ? "VIDEO" : "AUDIO"} HOLOCALL
          </span>
          <span className="holo-sep">|</span>
          <span className="holo-topbar__status">{statusLabel}</span>
        </div>
        <div className="holo-topbar__right">
          <span className="holo-rec">● REC</span>
          <span className="holo-sep">|</span>
          <span>{peerName}</span>
        </div>
      </header>

      {/* --- Main --- */}
      <div className="holo-call">
        {/* Portraits */}
        <div className="holo-call__stage">
          {kind === "video" && !sharing ? (
            <video
              ref={remoteRef}
              autoPlay
              playsInline
              className="holo-call__video holo-video-glitch"
            />
          ) : kind === "video" && sharing ? (
            <video
              ref={remoteRef}
              autoPlay
              playsInline
              className="holo-call__video holo-video-glitch"
            />
          ) : (
            /* AUDIO MODE: hologram portrait */
            <div className="holo-call__audio">
              <audio ref={remoteRef as any} autoPlay />
              <div className={"holo-hologram " + (peerSpeaking ? "holo-hologram--speaking" : "")}>
                <div className="holo-hologram__ring holo-hologram__ring--1" />
                <div className="holo-hologram__ring holo-hologram__ring--2" />
                <div className="holo-hologram__ring holo-hologram__ring--3" />
                <div className="holo-hologram__portrait">
                  <Avatar user={{ username: peerName, display_name: peerName, avatar_color: "#00f0ff" }} size={220} />
                </div>
                <div className="holo-hologram__scan" />
              </div>
              <div className="holo-call__name glitch" data-text={peerName}>{peerName}</div>
              <div className="holo-call__sub">
                {peerSpeaking ? "◂ TRANSMITTING ▸" : "◂ LISTENING ▸"}
              </div>
            </div>
          )}

          {/* Local PiP */}
          {kind === "video" && (
            <div className={"holo-pip " + (camOff ? "holo-pip--off" : "")}>
              <video
                ref={localRef}
                autoPlay
                playsInline
                muted
                className="holo-pip__video"
              />
              {camOff && <div className="holo-pip__off">CAM OFF</div>}
              <div className="holo-pip__label">LOCAL UPLINK</div>
            </div>
          )}
        </div>

        {/* Transcript sidebar */}
        {showCaptions && (
          <aside className="holo-transcript">
            <div className="holo-transcript__header">
              <span>◈ TRANSCRIPT.LOG</span>
              <button
                className="holo-transcript__close"
                onClick={() => setShowCaptions(false)}
                title="Скрыть"
              >✕</button>
            </div>
            <div className="holo-transcript__body">
              {transcript.length === 0 && (
                <div className="holo-transcript__empty">
                  // awaiting speech
                </div>
              )}
              {transcript.map((line) => (
                <div key={line.id} className={"holo-line holo-line--" + line.who}>
                  <span className="holo-line__who">
                    {line.who === "me" ? "YOU" : "PEER"}
                  </span>
                  <span className="holo-line__text">{line.text}</span>
                </div>
              ))}
            </div>
          </aside>
        )}

        {!showCaptions && (
          <button
            className="holo-transcript-toggle"
            onClick={() => setShowCaptions(true)}
          >
            ◂ LOG
          </button>
        )}
      </div>

      {/* --- Controls --- */}
      <footer className="holo-controls">
        <button
          className={"holo-ctrl " + (muted ? "holo-ctrl--active" : "")}
          onClick={toggleMute}
          title="Микрофон"
        >
          <span className="holo-ctrl__icon">{muted ? "🔇" : "🎤"}</span>
          <span className="holo-ctrl__label">{muted ? "MUTED" : "MIC"}</span>
        </button>

        {kind === "video" && (
          <>
            <button
              className={"holo-ctrl " + (camOff ? "holo-ctrl--active" : "")}
              onClick={toggleCam}
              title="Камера"
            >
              <span className="holo-ctrl__icon">{camOff ? "📷" : "📹"}</span>
              <span className="holo-ctrl__label">{camOff ? "CAM OFF" : "CAM"}</span>
            </button>
            <button
              className={"holo-ctrl " + (sharing ? "holo-ctrl--live" : "")}
              onClick={onToggleScreen}
              title="Демонстрация экрана"
            >
              <span className="holo-ctrl__icon">🖥</span>
              <span className="holo-ctrl__label">{sharing ? "SHARING" : "SCREEN"}</span>
            </button>
          </>
        )}

        <button
          className="holo-ctrl holo-ctrl--end"
          onClick={onEnd}
          title="Завершить"
        >
          <span className="holo-ctrl__icon">✕</span>
          <span className="holo-ctrl__label">END</span>
        </button>
      </footer>
    </div>
  );
}
'''


# ============================================================== Holocall CSS
HOLO_CSS = r'''
    /* ============================================================
       HOLOCALL — Cyberpunk 2077 style calls
       ============================================================ */

    .holo-overlay {
      position: fixed;
      inset: 0;
      z-index: 400;
      display: flex;
      flex-direction: column;
      background:
        radial-gradient(ellipse at 50% 40%, rgba(0, 40, 70, 0.55), transparent 70%),
        radial-gradient(ellipse at 20% 90%, rgba(120, 20, 80, 0.35), transparent 60%),
        #02060c;
      color: #d6ecff;
      font-family: "JetBrains Mono", "Rajdhani", "Fira Code", monospace;
      overflow: hidden;
    }

    /* --- scanlines --- */
    .holo-scanlines {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(0, 240, 255, 0.045) 3px,
        transparent 4px
      );
      z-index: 1;
      mix-blend-mode: screen;
    }

    /* --- subtle noise --- */
    .holo-noise {
      position: absolute;
      inset: 0;
      pointer-events: none;
      z-index: 2;
      opacity: 0.05;
      background-image:
        radial-gradient(circle at 20% 30%, #00f0ff 0.5px, transparent 0.5px),
        radial-gradient(circle at 70% 60%, #ff00a0 0.5px, transparent 0.5px),
        radial-gradient(circle at 40% 80%, #fcee0a 0.5px, transparent 0.5px);
      background-size: 90px 90px, 120px 120px, 70px 70px;
      animation: holo-noise-shift 0.8s steps(4) infinite;
    }
    @keyframes holo-noise-shift {
      0%   { background-position: 0 0, 0 0, 0 0; }
      25%  { background-position: 20px -10px, -30px 15px, 10px -5px; }
      50%  { background-position: -15px 25px, 10px -20px, -20px 5px; }
      75%  { background-position: 5px -30px, -15px 10px, 30px 15px; }
      100% { background-position: 0 0, 0 0, 0 0; }
    }

    /* --- horizontal sweep --- */
    .holo-sweep {
      position: absolute;
      left: 0;
      right: 0;
      height: 80px;
      z-index: 3;
      pointer-events: none;
      background: linear-gradient(180deg, transparent, rgba(0, 240, 255, 0.12), transparent);
      animation: holo-sweep-move 5s linear infinite;
    }
    .holo-sweep--slow { animation-duration: 8s; }
    @keyframes holo-sweep-move {
      0%   { top: -80px; }
      100% { top: 100vh; }
    }

    /* --- top bar --- */
    .holo-topbar {
      position: relative;
      z-index: 5;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 20px;
      border-bottom: 1px solid rgba(0, 240, 255, 0.35);
      background: linear-gradient(180deg, rgba(0, 240, 255, 0.05), transparent);
      font-size: 11px;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: #9fc4dc;
    }
    .holo-topbar__left { display: flex; align-items: center; gap: 10px; }
    .holo-topbar__right { display: flex; align-items: center; gap: 10px; color: #7a90a8; }
    .holo-topbar__title {
      color: #00f0ff;
      font-weight: bold;
      text-shadow: 0 0 8px rgba(0, 240, 255, 0.8);
    }
    .holo-topbar__status { color: #fcee0a; text-shadow: 0 0 6px rgba(252, 238, 10, 0.6); }
    .holo-dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #ff3355; box-shadow: 0 0 8px #ff3355;
    }
    .holo-dot--pulse {
      background: #00ff88; box-shadow: 0 0 10px #00ff88;
      animation: holo-dot-pulse 1.6s ease-in-out infinite;
    }
    @keyframes holo-dot-pulse {
      0%, 100% { opacity: 1; transform: scale(1); }
      50%      { opacity: 0.4; transform: scale(0.85); }
    }
    .holo-rec {
      color: #ff3355;
      text-shadow: 0 0 6px rgba(255, 51, 85, 0.8);
      animation: holo-rec-blink 1.4s step-end infinite;
    }
    @keyframes holo-rec-blink {
      50% { opacity: 0.35; }
    }
    .holo-sep { color: rgba(0, 240, 255, 0.35); }

    /* --- main card (incoming) --- */
    .holo-card {
      position: relative;
      z-index: 5;
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      margin: 40px auto;
      max-width: 900px;
      width: calc(100% - 60px);
      padding: 40px;
      background: rgba(3, 10, 20, 0.55);
      border: 1px solid rgba(0, 240, 255, 0.35);
      box-shadow:
        0 0 40px rgba(0, 240, 255, 0.15),
        inset 0 0 60px rgba(0, 240, 255, 0.04);
    }

    /* угловые скобки карточки */
    .holo-card__corner {
      position: absolute;
      width: 24px;
      height: 24px;
      border: 2px solid #00f0ff;
      filter: drop-shadow(0 0 6px rgba(0, 240, 255, 0.9));
    }
    .holo-card__corner--tl { top: -2px; left: -2px; border-right: none; border-bottom: none; }
    .holo-card__corner--tr { top: -2px; right: -2px; border-left: none; border-bottom: none; }
    .holo-card__corner--bl { bottom: -2px; left: -2px; border-right: none; border-top: none; border-color: #ff00a0; filter: drop-shadow(0 0 6px rgba(255, 0, 160, 0.9)); }
    .holo-card__corner--br { bottom: -2px; right: -2px; border-left: none; border-top: none; border-color: #ff00a0; filter: drop-shadow(0 0 6px rgba(255, 0, 160, 0.9)); }

    .holo-card__content {
      display: flex;
      gap: 40px;
      align-items: center;
      flex: 1;
    }

    /* --- portrait --- */
    .holo-portrait {
      position: relative;
      width: 240px;
      flex-shrink: 0;
    }
    .holo-portrait__frame {
      position: relative;
      padding: 12px;
      border: 1px solid rgba(0, 240, 255, 0.5);
      background: rgba(0, 240, 255, 0.04);
      box-shadow: inset 0 0 30px rgba(0, 240, 255, 0.15);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    /* scan strip over portrait */
    .holo-portrait__scan {
      position: absolute;
      left: 12px;
      right: 12px;
      top: 12px;
      bottom: 12px;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 4px,
        rgba(0, 240, 255, 0.08) 5px,
        transparent 6px
      );
      mix-blend-mode: screen;
    }
    .holo-portrait__label {
      margin-top: 8px;
      font-size: 10px;
      letter-spacing: 0.35em;
      text-align: center;
      color: #00f0ff;
      text-shadow: 0 0 6px rgba(0, 240, 255, 0.7);
    }
    .holo-portrait__glitch {
      position: absolute;
      inset: -6px;
      pointer-events: none;
      border: 1px dashed rgba(255, 0, 160, 0.4);
      animation: holo-glitch-border 3s steps(2) infinite;
    }
    @keyframes holo-glitch-border {
      0%   { transform: translate(0, 0); border-color: rgba(255, 0, 160, 0.4); }
      20%  { transform: translate(-2px, 1px); border-color: rgba(0, 240, 255, 0.5); }
      40%  { transform: translate(1px, -1px); border-color: rgba(252, 238, 10, 0.5); }
      60%  { transform: translate(-1px, -2px); border-color: rgba(255, 0, 160, 0.6); }
      80%  { transform: translate(2px, 1px); border-color: rgba(0, 240, 255, 0.4); }
      100% { transform: translate(0, 0); border-color: rgba(255, 0, 160, 0.4); }
    }

    /* --- info --- */
    .holo-info { flex: 1; min-width: 0; }
    .holo-info__kicker {
      font-size: 11px;
      letter-spacing: 0.35em;
      color: #ff00a0;
      text-shadow: 0 0 8px rgba(255, 0, 160, 0.7);
      margin-bottom: 10px;
    }
    .holo-info__name {
      font-family: "Rajdhani", "JetBrains Mono", monospace;
      font-size: 42px;
      font-weight: 700;
      line-height: 1.05;
      letter-spacing: 0.02em;
      margin: 0;
    }
    .holo-info__handle {
      margin-top: 6px;
      font-size: 12px;
      letter-spacing: 0.3em;
      color: #7a90a8;
    }
    .holo-info__row {
      margin-top: 14px;
      display: flex;
      gap: 14px;
      align-items: baseline;
      font-size: 11px;
      letter-spacing: 0.25em;
    }
    .holo-info__key { color: #5a7a95; min-width: 80px; }
    .holo-info__value { color: #d6ecff; }
    .holo-info__value--cyan { color: #00f0ff; text-shadow: 0 0 6px rgba(0, 240, 255, 0.6); }

    .holo-info__signal {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid rgba(0, 240, 255, 0.2);
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 11px;
      letter-spacing: 0.3em;
      color: #fcee0a;
      text-shadow: 0 0 6px rgba(252, 238, 10, 0.6);
    }
    .holo-signal {
      display: flex;
      align-items: flex-end;
      gap: 2px;
      height: 20px;
    }
    .holo-signal__bar {
      width: 3px;
      background: #fcee0a;
      box-shadow: 0 0 4px rgba(252, 238, 10, 0.8);
      animation: holo-signal-bounce 1.2s ease-in-out infinite;
    }
    @keyframes holo-signal-bounce {
      0%, 100% { height: 4px; opacity: 0.5; }
      50%      { height: 18px; opacity: 1; }
    }

    /* --- actions (incoming) --- */
    .holo-actions {
      display: flex;
      justify-content: center;
      gap: 24px;
      margin-top: 24px;
      padding-top: 24px;
      border-top: 1px solid rgba(0, 240, 255, 0.2);
    }
    .holo-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 6px;
      padding: 14px 36px;
      background: rgba(0, 240, 255, 0.04);
      border: 2px solid rgba(0, 240, 255, 0.55);
      color: #00f0ff;
      font-family: inherit;
      font-size: 11px;
      letter-spacing: 0.35em;
      font-weight: 700;
      text-transform: uppercase;
      cursor: pointer;
      transition: all 0.15s;
      clip-path: polygon(
        10px 0, calc(100% - 10px) 0, 100% 10px,
        100% calc(100% - 10px), calc(100% - 10px) 100%,
        10px 100%, 0 calc(100% - 10px), 0 10px
      );
    }
    .holo-btn__icon {
      font-size: 22px;
      line-height: 1;
    }
    .holo-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 0 24px rgba(0, 240, 255, 0.6);
    }
    .holo-btn--accept {
      border-color: #00ff88;
      color: #00ff88;
      background: rgba(0, 255, 136, 0.06);
      animation: holo-accept-glow 1.6s ease-in-out infinite;
    }
    .holo-btn--accept:hover { box-shadow: 0 0 28px rgba(0, 255, 136, 0.7); }
    @keyframes holo-accept-glow {
      0%, 100% { box-shadow: 0 0 12px rgba(0, 255, 136, 0.35); }
      50%      { box-shadow: 0 0 28px rgba(0, 255, 136, 0.85); }
    }
    .holo-btn--decline {
      border-color: #ff3355;
      color: #ff3355;
      background: rgba(255, 51, 85, 0.06);
    }
    .holo-btn--decline:hover { box-shadow: 0 0 24px rgba(255, 51, 85, 0.7); }

    /* --- footer --- */
    .holo-footer {
      position: relative;
      z-index: 5;
      display: flex;
      justify-content: space-between;
      padding: 10px 24px;
      border-top: 1px solid rgba(0, 240, 255, 0.25);
      font-size: 10px;
      letter-spacing: 0.3em;
      color: #7a90a8;
    }

    /* ============================================================
       ACTIVE CALL
       ============================================================ */

    .holo-call {
      position: relative;
      z-index: 5;
      flex: 1;
      display: flex;
      gap: 16px;
      padding: 20px;
      min-height: 0;
    }

    .holo-call__stage {
      position: relative;
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(3, 10, 20, 0.5);
      border: 1px solid rgba(0, 240, 255, 0.28);
      box-shadow: inset 0 0 60px rgba(0, 240, 255, 0.06);
      overflow: hidden;
      min-height: 0;
    }

    .holo-call__video {
      width: 100%;
      height: 100%;
      object-fit: contain;
      background: #000;
    }
    /* лёгкий glitch-эффект на видео */
    .holo-video-glitch {
      filter: contrast(1.05) saturate(1.1);
      position: relative;
    }
    .holo-video-glitch::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0, 240, 255, 0.05) 4px,
        transparent 5px
      );
      mix-blend-mode: screen;
    }

    /* --- audio-only hologram --- */
    .holo-call__audio {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 24px;
    }
    .holo-hologram {
      position: relative;
      width: 320px;
      height: 320px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .holo-hologram__portrait {
      position: relative;
      padding: 20px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(0, 240, 255, 0.15), transparent 65%);
      animation: holo-hol-float 3s ease-in-out infinite;
    }
    @keyframes holo-hol-float {
      0%, 100% { transform: translateY(0); }
      50%      { transform: translateY(-6px); }
    }
    .holo-hologram__scan {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0, 240, 255, 0.09) 4px,
        transparent 5px
      );
      border-radius: 50%;
      mix-blend-mode: screen;
    }
    .holo-hologram__ring {
      position: absolute;
      border: 1px solid rgba(0, 240, 255, 0.4);
      border-radius: 50%;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      pointer-events: none;
    }
    .holo-hologram__ring--1 {
      width: 260px; height: 260px;
      animation: holo-hol-ring 4s linear infinite;
    }
    .holo-hologram__ring--2 {
      width: 300px; height: 300px;
      border-style: dashed;
      border-color: rgba(255, 0, 160, 0.4);
      animation: holo-hol-ring-rev 6s linear infinite;
    }
    .holo-hologram__ring--3 {
      width: 340px; height: 340px;
      border-color: rgba(252, 238, 10, 0.3);
      animation: holo-hol-ring 8s linear infinite;
    }
    @keyframes holo-hol-ring {
      from { transform: translate(-50%, -50%) rotate(0deg); }
      to   { transform: translate(-50%, -50%) rotate(360deg); }
    }
    @keyframes holo-hol-ring-rev {
      from { transform: translate(-50%, -50%) rotate(360deg); }
      to   { transform: translate(-50%, -50%) rotate(0deg); }
    }
    .holo-hologram--speaking .holo-hologram__ring--1 {
      box-shadow: 0 0 30px rgba(0, 240, 255, 0.6);
    }
    .holo-hologram--speaking .holo-hologram__portrait {
      filter: drop-shadow(0 0 20px rgba(0, 240, 255, 0.9));
    }

    .holo-call__name {
      font-family: "Rajdhani", "JetBrains Mono", monospace;
      font-size: 36px;
      font-weight: 700;
      color: #eaf4ff;
    }
    .holo-call__sub {
      font-size: 11px;
      letter-spacing: 0.35em;
      color: #00f0ff;
      text-shadow: 0 0 6px rgba(0, 240, 255, 0.6);
    }

    /* --- local PiP (video) --- */
    .holo-pip {
      position: absolute;
      right: 16px;
      bottom: 16px;
      width: 200px;
      height: 130px;
      border: 1px solid rgba(0, 240, 255, 0.5);
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.3);
      background: #000;
      z-index: 3;
    }
    .holo-pip__video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .holo-pip__off {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #ff3355;
      letter-spacing: 0.3em;
      font-size: 11px;
      background: rgba(10, 0, 0, 0.85);
    }
    .holo-pip--off { border-color: #ff3355; }
    .holo-pip__label {
      position: absolute;
      top: -18px;
      left: 0;
      font-size: 9px;
      letter-spacing: 0.3em;
      color: #00f0ff;
      text-shadow: 0 0 6px rgba(0, 240, 255, 0.6);
    }

    /* --- transcript sidebar --- */
    .holo-transcript {
      width: 300px;
      flex-shrink: 0;
      display: flex;
      flex-direction: column;
      background: rgba(3, 10, 20, 0.55);
      border: 1px solid rgba(0, 240, 255, 0.28);
      min-height: 0;
    }
    .holo-transcript__header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 12px;
      border-bottom: 1px solid rgba(0, 240, 255, 0.28);
      font-size: 10px;
      letter-spacing: 0.3em;
      color: #00f0ff;
      text-shadow: 0 0 6px rgba(0, 240, 255, 0.6);
    }
    .holo-transcript__close {
      background: none;
      border: none;
      color: #ff00a0;
      cursor: pointer;
      font-size: 12px;
    }
    .holo-transcript__body {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      min-height: 0;
    }
    .holo-transcript__empty {
      font-size: 10px;
      letter-spacing: 0.3em;
      color: #5a7a95;
      text-align: center;
      margin-top: 40px;
    }
    .holo-line {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 8px 10px;
      border-left: 2px solid;
      background: rgba(0, 0, 0, 0.35);
      font-size: 12px;
      animation: holo-line-in 0.25s ease-out;
    }
    @keyframes holo-line-in {
      from { opacity: 0; transform: translateX(-8px); }
      to   { opacity: 1; transform: translateX(0); }
    }
    .holo-line--me {
      border-color: #00f0ff;
    }
    .holo-line--peer {
      border-color: #ff00a0;
    }
    .holo-line__who {
      font-size: 9px;
      letter-spacing: 0.3em;
      color: #7a90a8;
    }
    .holo-line--me .holo-line__who { color: #00f0ff; }
    .holo-line--peer .holo-line__who { color: #ff00a0; }
    .holo-line__text { color: #d6ecff; line-height: 1.35; }

    .holo-transcript-toggle {
      position: absolute;
      right: 16px;
      top: 16px;
      z-index: 4;
      padding: 6px 12px;
      background: rgba(0, 240, 255, 0.06);
      border: 1px solid rgba(0, 240, 255, 0.5);
      color: #00f0ff;
      font-family: inherit;
      font-size: 10px;
      letter-spacing: 0.3em;
      cursor: pointer;
    }
    .holo-transcript-toggle:hover { background: rgba(0, 240, 255, 0.15); }

    /* --- bottom controls --- */
    .holo-controls {
      position: relative;
      z-index: 5;
      display: flex;
      justify-content: center;
      gap: 16px;
      padding: 16px 24px 22px;
      border-top: 1px solid rgba(0, 240, 255, 0.25);
      background: linear-gradient(0deg, rgba(0, 240, 255, 0.04), transparent);
    }
    .holo-ctrl {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      width: 88px;
      padding: 10px 8px;
      background: rgba(0, 240, 255, 0.04);
      border: 1px solid rgba(0, 240, 255, 0.45);
      color: #00f0ff;
      font-family: inherit;
      font-size: 9px;
      letter-spacing: 0.28em;
      cursor: pointer;
      transition: all 0.15s;
      clip-path: polygon(
        6px 0, calc(100% - 6px) 0, 100% 6px,
        100% calc(100% - 6px), calc(100% - 6px) 100%,
        6px 100%, 0 calc(100% - 6px), 0 6px
      );
    }
    .holo-ctrl__icon { font-size: 20px; line-height: 1; }
    .holo-ctrl__label { font-weight: 700; }
    .holo-ctrl:hover {
      background: rgba(0, 240, 255, 0.15);
      box-shadow: 0 0 16px rgba(0, 240, 255, 0.5);
    }
    .holo-ctrl--active {
      border-color: #ff3355;
      color: #ff3355;
      background: rgba(255, 51, 85, 0.1);
      box-shadow: 0 0 16px rgba(255, 51, 85, 0.4);
    }
    .holo-ctrl--live {
      border-color: #fcee0a;
      color: #fcee0a;
      background: rgba(252, 238, 10, 0.1);
      box-shadow: 0 0 16px rgba(252, 238, 10, 0.5);
    }
    .holo-ctrl--end {
      border-color: #ff3355;
      color: #ff3355;
      background: rgba(255, 51, 85, 0.06);
    }
    .holo-ctrl--end:hover {
      background: rgba(255, 51, 85, 0.2);
      box-shadow: 0 0 22px rgba(255, 51, 85, 0.7);
    }

    /* когда чат открыт — фон города не мешает звонку */
    body.chat-open .holo-overlay {
      background:
        radial-gradient(ellipse at 50% 40%, rgba(0, 40, 70, 0.85), transparent 70%),
        radial-gradient(ellipse at 20% 90%, rgba(120, 20, 80, 0.55), transparent 60%),
        #02060c;
    }

    /* --- glitch text util (используется в .holo-info__name и .holo-call__name) --- */
    .holo-info__name.glitch,
    .holo-call__name.glitch {
      position: relative;
    }
    .holo-info__name.glitch::before,
    .holo-info__name.glitch::after,
    .holo-call__name.glitch::before,
    .holo-call__name.glitch::after {
      content: attr(data-text);
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      overflow: hidden;
      pointer-events: none;
      opacity: 0.7;
    }
    .holo-info__name.glitch::before,
    .holo-call__name.glitch::before {
      color: #ff00a0;
      clip-path: polygon(0 0, 100% 0, 100% 45%, 0 45%);
      animation: holo-glitch-a 3.5s infinite steps(2) alternate-reverse;
    }
    .holo-info__name.glitch::after,
    .holo-call__name.glitch::after {
      color: #00f0ff;
      clip-path: polygon(0 55%, 100% 55%, 100% 100%, 0 100%);
      animation: holo-glitch-b 4s infinite steps(2) alternate-reverse;
    }
    @keyframes holo-glitch-a {
      0%, 100% { transform: translate(0); }
      25% { transform: translate(-1px, 1px); }
      50% { transform: translate(-2px, 0); }
      75% { transform: translate(1px, -1px); }
    }
    @keyframes holo-glitch-b {
      0%, 100% { transform: translate(0); }
      25% { transform: translate(2px, -1px); }
      50% { transform: translate(1px, 1px); }
      75% { transform: translate(-1px, 1px); }
    }
'''


def write_file(path: Path, content: str) -> None:
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {path}")


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

    print("\nСпринт 24 — Holocall (Cyberpunk 2077 style)\n")

    write_file(src / "cyberRingtone.ts", CYBER_RINGTONE)
    write_file(src / "IncomingCallModal.tsx", INCOMING_CALL)
    write_file(src / "CallWindow.tsx", CALL_WINDOW)

    # CSS
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "HOLOCALL — Cyberpunk 2077" not in css_text:
        css_text = css_text.rstrip() + "\n" + HOLO_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")
    else:
        print(f"  > {css_path} (CSS уже пропатчен)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что появилось:")
    print("  📞 IncomingCallModal — полноэкранный голографический оверлей")
    print("     + ringtone из Web Audio (не нужен MP3)")
    print("  📞 CallWindow — с транскрипцией, глитч-эффектами, hologram для аудио")
    print("  🔔 cyberRingtone.ts — синтезатор: double-ring, dial, connect/disconnect beeps")
    print()
    print("Управление звонком:")
    print("  Enter — принять входящий")
    print("  Esc   — отклонить")
    print("  Кнопки внизу — mute / cam / screen / end")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())