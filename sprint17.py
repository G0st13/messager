#!/usr/bin/env python3
"""sprint17.py - radically different theme layouts."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================== themes.ts (без изменений структуры)
THEMES_TS = r'''import type { ThemeName } from "./types";

export interface Theme {
  name: ThemeName;
  label: string;
  bodyClass: string;
  vars: Record<string, string>;
}

export const THEMES: Theme[] = [
  { name: "cyber",   label: "◈ CYBER",   bodyClass: "theme-cyber",   vars: {} },
  { name: "matrix",  label: "▶ MATRIX",  bodyClass: "theme-matrix",  vars: {} },
  { name: "sunset",  label: "☀ SUNSET",  bodyClass: "theme-sunset",  vars: {} },
  { name: "amber",   label: "◆ AMBER",   bodyClass: "theme-amber",   vars: {} },
  { name: "deusex",  label: "◈ DEUS EX", bodyClass: "theme-deusex",  vars: {} },
  { name: "gits",    label: "◉ GITS",    bodyClass: "theme-gits",    vars: {} },
  { name: "lain",    label: "◌ LAIN",    bodyClass: "theme-lain",    vars: {} },
];

export function applyTheme(name: ThemeName) {
  const theme = THEMES.find((t) => t.name === name) || THEMES[0];
  for (const t of THEMES) document.body.classList.remove(t.bodyClass);
  document.body.classList.add(theme.bodyClass);
  document.body.setAttribute("data-theme", name);
}
'''


# ============================================================== ChatList — добавляем data-атрибуты
CHATLIST = r'''import { useMemo, useState } from "react";
import type { Chat, User } from "./types";

function fmtTime(iso: string | null | undefined) {
  if (!iso) return "--:--";
  const d = new Date(iso);
  const now = new Date();
  if (d.toDateString() === now.toDateString())
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const y = new Date(now); y.setDate(now.getDate() - 1);
  if (d.toDateString() === y.toDateString()) return "YESTD";
  return d.toLocaleDateString([], { day: "2-digit", month: "2-digit" });
}

function chatTitle(c: Chat) {
  if (c.peer) return c.peer.display_name || c.peer.username;
  return c.title || `NODE-${c.id.toString(16).toUpperCase().padStart(4, "0")}`;
}

function chatSubtitle(c: Chat) {
  const lm = c.last_message;
  if (!lm) return "// no transmission";
  if (lm.message_type === "system") return lm.text || "";
  const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
  let body = lm.text || "";
  if (lm.encrypted) body = "🔒 ENCRYPTED";
  else if (lm.message_type === "image") body = "▣ IMAGE_DATA";
  else if (lm.message_type === "voice") body = "◍ AUDIO_SIGNAL";
  else if (lm.message_type === "file") body = `▤ ${lm.attachment?.filename || "FILE"}`;
  else if (lm.message_type === "sticker") body = lm.text || "◈ SIGIL";
  return "> " + who + body;
}

function initials(name: string): string {
  const s = (name || "?").trim();
  const parts = s.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return s.slice(0, 2).toUpperCase();
}

export default function ChatList({
  chats, activeId, onSelect, onlineUsers, currentUser, onOpenProfile, onOpenSettings,
  onOpenFeed, onOpenMyProfile, mode, failedQueue,
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
  failedQueue?: number;
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
  const onlineCount = onlineUsers.size;
  const hexId = currentUser.id.toString(16).toUpperCase().padStart(4, "0");

  return (
    <aside className="cyberdeck-panel relative z-10 flex w-80 shrink-0 flex-col">
      <div className="cyberdeck-header">
        <div className="cyberdeck-title">◈ NET_CHANNELS</div>
        <div className="cyberdeck-sub">
          <span className="dot">●</span> LINK_UP
          <span className="sep">·</span>{chats.length} CHAN
          <span className="sep">·</span>{onlineCount} ONLINE
        </div>
      </div>

      <div className="cyberdeck-operator">
        <button
          onClick={onOpenProfile}
          className="channel-icon shrink-0 operator-icon"
          title="Профиль"
        >
          {initials(currentUser.display_name || currentUser.username)}
        </button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[11px] font-bold uppercase tracking-widest neon-text operator-name">
            {currentUser.display_name || currentUser.username}
          </div>
          <div className="truncate text-[9px] uppercase tracking-widest text-cyber-dim operator-id">
            ID::0x{hexId} · @{currentUser.username}
          </div>
        </div>
        <button
          onClick={onOpenSettings}
          title="Настройки"
          className="cyberdeck-icon-btn"
        >
          ⚙
        </button>
      </div>

      <div className="px-3 pb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="> SCAN_CHANNELS..."
          className="cyberdeck-search"
        />
      </div>

      <div className="cyberdeck-tabs">
        <button
          onClick={onOpenFeed}
          className={"cyberdeck-tab" + (mode === "feed" ? " active" : "")}
        >
          ◈ FEED
        </button>
        <button
          onClick={onOpenMyProfile}
          className={"cyberdeck-tab" + (mode === "profile" ? " active" : "")}
        >
          ◈ ME
        </button>
      </div>

      {(failedQueue ?? 0) > 0 && (
        <div className="cyberdeck-alert">
          ⚠ {failedQueue} FAILED_UPLINK
        </div>
      )}

      <div className="cyberdeck-list">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-[10px] uppercase tracking-[0.3em] text-cyber-dim">
            // no_channels
          </div>
        ) : (
          filtered.map((c, idx) => {
            const active = c.id === activeId && mode === "chats";
            const peerOnline = c.peer ? onlineUsers.has(c.peer.id) : false;
            const name = chatTitle(c);
            const tag = c.peer
              ? (peerOnline ? "DM·ONLINE" : "DM")
              : `GRP·${c.member_count}`;
            const hasUnread = c.unread_count > 0 && !active;

            return (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={"channel-card" + (active ? " active" : "")}
                data-online={peerOnline ? "true" : "false"}
                data-type={c.peer ? "dm" : "grp"}
                data-unread={hasUnread ? "true" : "false"}
                data-index={String(idx + 1).padStart(2, "0")}
              >
                <div className="channel-card-num">{String(idx + 1).padStart(2, "0")}</div>

                <div
                  className="channel-icon"
                  style={{ color: c.peer?.avatar_color || (c.is_group ? "#ff00a0" : "#00f0ff") }}
                >
                  {initials(name)}
                  {c.peer && peerOnline && <span className="channel-online-dot" />}
                </div>

                <div className="channel-card-body">
                  <div className="channel-card-tag">
                    <span className={c.peer ? "dm" : "grp"}>{tag}</span>
                    {c.last_message?.is_pinned && (
                      <span className="pinned"> · PIN</span>
                    )}
                  </div>
                  <div className="channel-card-name">{name}</div>
                  <div className="channel-card-msg">{chatSubtitle(c)}</div>
                </div>

                <div className="channel-card-right">
                  <div className="channel-time">
                    {fmtTime(c.last_message?.created_at || c.created_at)}
                  </div>
                  {hasUnread ? (
                    <div className="channel-badge pulse">
                      ↑{c.unread_count > 99 ? "99+" : c.unread_count}
                    </div>
                  ) : (
                    <div className="channel-hex">
                      0x{(c.id % 65536).toString(16).toUpperCase().padStart(4, "0")}
                    </div>
                  )}
                </div>
              </button>
            );
          })
        )}
      </div>

      <div className="cyberdeck-footer">
        <span>SYS::NOMINAL</span>
        <span className={unreadTotal > 0 ? "neon-text-mag" : ""}>
          {unreadTotal > 0 ? `PKT_RECV:${unreadTotal}` : "ALL_READ"}
        </span>
      </div>
    </aside>
  );
}
'''


# ============================================================== патч MessageBubble на классы .msg-bubble
MESSAGEBUBBLE_REPLACEMENTS = [
    # убираем inline-style, ставим классы
    (
        '  const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";\n'
        '  const bubbleStyle = {\n'
        '    background: isFailed\n'
        '      ? "rgba(255,45,85,0.18)"\n'
        '      : mine\n'
        '      ? "rgba(0,240,255,0.16)"\n'
        '      : "rgba(255,0,160,0.14)",\n'
        '    border: `1px solid ${accent}66`,\n'
        '    color: "#eaf4ff",\n'
        '    opacity: isPending ? 0.78 : 1,\n'
        '  };',
        '  const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";',
    ),
    # основной bubble div
    (
        '        <div\n'
        '          className={"relative overflow-hidden rounded-sm text-sm " + (isImage || isVideo ? "" : " px-3 py-2")}\n'
        '          style={bubbleStyle}\n'
        '        >',
        '        <div\n'
        '          className={\n'
        '            "msg-bubble relative overflow-hidden text-sm " +\n'
        '            (mine ? "mine " : "other ") +\n'
        '            (isFailed ? "failed " : "") +\n'
        '            (isPending ? "pending " : "") +\n'
        '            (isImage || isVideo ? "media" : "px-3 py-2")\n'
        '          }\n'
        '        >',
    ),
]


# ============================================================== гигантский CSS
THEME_CSS = r'''

    /* ============================================================
       MESSAGE BUBBLES — базовые (cyber) + классовая система
       ============================================================ */
    .msg-bubble {
      border-radius: 0;
      color: var(--text-primary, #eaf4ff);
      transition: opacity 0.15s;
    }
    .msg-bubble.mine {
      background: rgba(0, 240, 255, 0.16);
      border: 1px solid rgba(0, 240, 255, 0.4);
      box-shadow: 0 0 12px rgba(0, 240, 255, 0.13);
    }
    .msg-bubble.other {
      background: rgba(255, 0, 160, 0.14);
      border: 1px solid rgba(255, 0, 160, 0.4);
      box-shadow: 0 0 12px rgba(255, 0, 160, 0.12);
    }
    .msg-bubble.failed {
      background: rgba(255, 45, 85, 0.18) !important;
      border-color: rgba(255, 45, 85, 0.5) !important;
    }
    .msg-bubble.pending {
      opacity: 0.78;
    }

    /* ---------- Общее: номер канала по умолчанию скрыт ---------- */
    .channel-card-num { display: none; }

    /* ============================================================
       MATRIX — текстовый терминал, падающий код, всё капсом
       ============================================================ */
    body.theme-matrix {
      font-family: "JetBrains Mono", "Fira Code", monospace;
    }
    body.theme-matrix * {
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }

    /* Фон — падающие зелёные символы */
    body.theme-matrix::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 2;
      background-image:
        radial-gradient(circle, rgba(0,255,65,0.9) 1.2px, transparent 1.6px),
        radial-gradient(circle, rgba(0,255,65,0.7) 1px, transparent 1.4px),
        radial-gradient(circle, rgba(0,255,65,0.5) 1px, transparent 1.4px);
      background-size: 22px 160px, 34px 240px, 48px 320px;
      background-position: 0 0, 12px 40px, 28px 80px;
      animation: matrix-fall 3.5s linear infinite;
      opacity: 0.35;
      mix-blend-mode: screen;
    }
    @keyframes matrix-fall {
      from { background-position: 0 -320px, 12px -240px, 28px -160px; }
      to   { background-position: 0 0, 12px 0, 28px 0; }
    }

    /* Панель — как терминал */
    body.theme-matrix .cyberdeck-panel {
      background: #000600 !important;
      border-right: 1px dashed rgba(0,255,65,0.35) !important;
    }
    body.theme-matrix .cyberdeck-panel::before { display: none !important; }
    body.theme-matrix .cyberdeck-header {
      background: none !important;
      border-bottom: 1px dashed rgba(0,255,65,0.5) !important;
      padding: 8px 12px !important;
    }
    body.theme-matrix .cyberdeck-header::after { display: none !important; }
    body.theme-matrix .cyberdeck-title {
      color: #00ff41 !important;
      text-shadow: 0 0 8px #00ff41 !important;
      font-size: 12px !important;
    }
    body.theme-matrix .cyberdeck-title::before { content: "> "; }
    body.theme-matrix .cyberdeck-sub { color: #008822 !important; }

    body.theme-matrix .cyberdeck-operator {
      border-bottom: 1px dashed rgba(0,255,65,0.25) !important;
    }
    /* Скрываем операторский аватар */
    body.theme-matrix .operator-icon { display: none !important; }
    body.theme-matrix .operator-name::before { content: "@"; }
    body.theme-matrix .operator-name { color: #00ff41 !important; }
    body.theme-matrix .operator-name::after {
      content: "_";
      animation: matrix-blink 1s step-end infinite;
      color: #00ff41;
    }

    body.theme-matrix .cyberdeck-search {
      background: #000600 !important;
      border: none !important;
      border-bottom: 1px solid #00ff41 !important;
      border-radius: 0 !important;
      color: #00ff41 !important;
      padding: 4px 2px !important;
      clip-path: none !important;
      box-shadow: none !important;
    }
    body.theme-matrix .cyberdeck-search:focus {
      background: rgba(0,255,65,0.05) !important;
    }
    body.theme-matrix .cyberdeck-search::placeholder { color: #005522 !important; }
    body.theme-matrix .cyberdeck-search::before { content: "> "; }

    body.theme-matrix .cyberdeck-tabs {
      border-top: 1px dashed rgba(0,255,65,0.3) !important;
      border-bottom: 1px dashed rgba(0,255,65,0.3) !important;
      background: none !important;
    }
    body.theme-matrix .cyberdeck-tab { color: #008822 !important; }
    body.theme-matrix .cyberdeck-tab.active { color: #ffffff !important; background: rgba(0,255,65,0.08) !important; }
    body.theme-matrix .cyberdeck-tab.active::after { background: #00ff41 !important; box-shadow: 0 0 8px #00ff41 !important; }

    /* Карточки — плоские строки с префиксом */
    body.theme-matrix .cyberdeck-list { counter-reset: mtx; padding: 4px 0 !important; }
    body.theme-matrix .channel-card {
      display: block !important;
      background: none !important;
      border: none !important;
      border-radius: 0 !important;
      clip-path: none !important;
      box-shadow: none !important;
      margin: 0 !important;
      padding: 3px 10px 3px 22px !important;
      width: 100% !important;
      text-align: left !important;
      position: relative;
      counter-increment: mtx;
      font-size: 12px !important;
      color: #00cc33 !important;
    }
    body.theme-matrix .channel-card::before {
      content: "[" counter(mtx, decimal-leading-zero) "]";
      position: absolute;
      left: 4px;
      top: 3px;
      color: #005522;
      font-size: 10px;
    }
    body.theme-matrix .channel-card:hover {
      background: rgba(0,255,65,0.06) !important;
      color: #ffffff !important;
    }
    body.theme-matrix .channel-card.active {
      background: rgba(0,255,65,0.10) !important;
      color: #ffffff !important;
      box-shadow: inset 3px 0 0 #00ff41 !important;
    }
    body.theme-matrix .channel-card.active::after {
      content: " ◄ACTIVE";
      color: #00ff41;
      font-size: 9px;
      text-shadow: 0 0 4px #00ff41;
    }

    body.theme-matrix .channel-icon { display: none !important; }
    body.theme-matrix .channel-card-num { display: none !important; }

    body.theme-matrix .channel-card-tag { display: none !important; }

    body.theme-matrix .channel-card-name {
      color: inherit !important;
      font-size: 12px !important;
      text-shadow: none !important;
    }
    body.theme-matrix .channel-card-name::before { content: "> "; color: #00ff41; }
    body.theme-matrix .channel-card.active .channel-card-name::before { content: "▶ "; color: #ffffff; }

    body.theme-matrix .channel-card-msg {
      font-size: 10px !important;
      color: #008822 !important;
      font-style: italic !important;
      margin-top: 0 !important;
    }

    body.theme-matrix .channel-time { color: #005522 !important; font-size: 9px !important; }
    body.theme-matrix .channel-hex { color: #005522 !important; }

    body.theme-matrix .channel-badge {
      background: #00ff41 !important;
      color: #000600 !important;
      box-shadow: 0 0 8px #00ff41 !important;
      clip-path: none !important;
    }

    body.theme-matrix .cyberdeck-footer {
      background: #000600 !important;
      border-top: 1px dashed rgba(0,255,65,0.4) !important;
      color: #008822 !important;
    }

    /* Сообщения — просто текст без бабблов */
    body.theme-matrix .chat-surface { background: #000600 !important; }
    body.theme-matrix .msg-bubble,
    body.theme-matrix .msg-bubble.mine,
    body.theme-matrix .msg-bubble.other {
      background: none !important;
      border: none !important;
      border-radius: 0 !important;
      box-shadow: none !important;
      padding: 2px 0 !important;
      color: #00ff41 !important;
      text-shadow: 0 0 4px rgba(0,255,65,0.4) !important;
      font-size: 13px !important;
    }
    body.theme-matrix .msg-bubble.mine::before { content: "> "; color: #ffffff; }
    body.theme-matrix .msg-bubble.other::before { content: "< "; color: #00ff41; }

    body.theme-matrix .msg-bubble.failed {
      color: #ff2d55 !important;
      text-shadow: 0 0 6px #ff2d55 !important;
    }
    body.theme-matrix .msg-bubble.failed::before { content: "! "; color: #ff2d55 !important; }

    /* Мигающий курсор в углу */
    body.theme-matrix::after {
      content: "▮";
      position: fixed;
      right: 16px;
      bottom: 14px;
      color: #00ff41;
      font-size: 14px;
      text-shadow: 0 0 10px #00ff41;
      animation: matrix-blink 1s step-end infinite;
      pointer-events: none;
      z-index: 100;
    }
    @keyframes matrix-blink { 50% { opacity: 0; } }

    /* ============================================================
       SUNSET — vaporwave, парящие карточки, круглые аватары
       ============================================================ */
    body.theme-sunset {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }
    body.theme-sunset * { text-transform: none; }

    /* Закатное небо + солнце */
    body.theme-sunset::before {
      content: "";
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background:
        linear-gradient(180deg, transparent 30%, rgba(255,107,53,0.10) 70%, rgba(247,147,30,0.18) 100%),
        radial-gradient(circle at 78% 22%, rgba(255,210,63,0.45) 0%, rgba(255,107,53,0.25) 6%, transparent 22%);
    }
    /* Силуэт пальмы */
    body.theme-sunset::after {
      content: "";
      position: fixed;
      right: 20px;
      bottom: 0;
      width: 180px;
      height: 240px;
      pointer-events: none;
      z-index: 1;
      opacity: 0.35;
      background:
        /* ствол */
        linear-gradient(95deg, transparent 45%, #2a0d1a 46%, #2a0d1a 50%, transparent 51%) no-repeat 60px 40px / 60px 200px,
        /* листья */
        radial-gradient(ellipse 90px 30px at 60px 50px, #2a0d1a 40%, transparent 70%),
        radial-gradient(ellipse 80px 26px at 30px 60px, #2a0d1a 40%, transparent 70%),
        radial-gradient(ellipse 90px 28px at 90px 65px, #2a0d1a 40%, transparent 70%),
        radial-gradient(ellipse 70px 24px at 50px 80px, #2a0d1a 40%, transparent 70%);
    }

    body.theme-sunset .cyberdeck-panel {
      background: linear-gradient(180deg, rgba(38,16,31,0.90), rgba(26,13,26,0.94)) !important;
      border-right: none !important;
      padding: 8px;
    }
    body.theme-sunset .cyberdeck-panel::before { display: none !important; }

    body.theme-sunset .cyberdeck-header {
      background: linear-gradient(135deg, rgba(255,107,53,0.15), rgba(247,147,30,0.05)) !important;
      border: none !important;
      border-radius: 16px !important;
      padding: 12px 14px !important;
      margin-bottom: 8px;
    }
    body.theme-sunset .cyberdeck-header::after { display: none !important; }
    body.theme-sunset .cyberdeck-title { color: #ff6b35 !important; text-shadow: 0 2px 8px rgba(255,107,53,0.5) !important; }
    body.theme-sunset .cyberdeck-sub { color: rgba(255,182,150,0.7) !important; }

    body.theme-sunset .cyberdeck-operator {
      background: linear-gradient(135deg, rgba(255,107,53,0.10), rgba(247,147,30,0.04));
      border-radius: 16px !important;
      border: none !important;
      padding: 10px 12px !important;
      margin-bottom: 8px;
    }
    /* Большой круглый аватар оператора */
    body.theme-sunset .operator-icon {
      width: 44px !important;
      height: 44px !important;
      border-radius: 50% !important;
      clip-path: none !important;
      background: linear-gradient(135deg, #ff6b35, #ffd23f) !important;
      border: 2px solid rgba(255,255,255,0.3) !important;
      box-shadow: 0 4px 16px rgba(255,107,53,0.5) !important;
      font-size: 15px !important;
      color: #2a0d1a !important;
    }
    body.theme-sunset .operator-name { color: #ffd6b8 !important; text-shadow: none !important; font-weight: 700; }

    body.theme-sunset .cyberdeck-search {
      background: rgba(255,107,53,0.08) !important;
      border: 1px solid rgba(255,107,53,0.3) !important;
      border-radius: 999px !important;
      clip-path: none !important;
      padding: 10px 18px !important;
      color: #ffd6b8 !important;
      font-size: 13px !important;
    }
    body.theme-sunset .cyberdeck-search:focus {
      border-color: #ff6b35 !important;
      box-shadow: 0 0 16px rgba(255,107,53,0.4) !important;
    }

    body.theme-sunset .cyberdeck-tabs {
      border: none !important;
      background: none !important;
      gap: 6px;
      padding: 4px 0 !important;
    }
    body.theme-sunset .cyberdeck-tab {
      background: rgba(255,107,53,0.06);
      border-radius: 12px;
      color: #ffb690 !important;
      padding: 8px !important;
    }
    body.theme-sunset .cyberdeck-tab.active {
      background: linear-gradient(135deg, #ff6b35, #f7931e) !important;
      color: #2a0d1a !important;
      font-weight: 700;
    }
    body.theme-sunset .cyberdeck-tab.active::after { display: none !important; }

    body.theme-sunset .cyberdeck-list { padding: 4px !important; }

    /* Парящие карточки */
    body.theme-sunset .channel-card {
      display: flex !important;
      background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,107,53,0.04)) !important;
      border: 1px solid rgba(255,107,53,0.18) !important;
      border-radius: 18px !important;
      clip-path: none !important;
      margin: 6px 4px !important;
      padding: 12px 14px !important;
      box-shadow: 0 4px 16px rgba(0,0,0,0.3) !important;
      transition: transform 0.15s, box-shadow 0.15s;
    }
    body.theme-sunset .channel-card:hover {
      transform: translateY(-2px);
      background: linear-gradient(135deg, rgba(255,255,255,0.10), rgba(255,107,53,0.08)) !important;
      border-color: rgba(255,107,53,0.5) !important;
      box-shadow: 0 8px 24px rgba(255,107,53,0.35) !important;
    }
    body.theme-sunset .channel-card.active {
      background: linear-gradient(135deg, rgba(255,107,53,0.25), rgba(247,147,30,0.12)) !important;
      border-color: #ff6b35 !important;
      box-shadow: 0 8px 28px rgba(255,107,53,0.55) !important;
    }
    body.theme-sunset .channel-card.active::before { display: none !important; }

    /* Крупные круглые аватары 52px */
    body.theme-sunset .channel-icon {
      width: 52px !important;
      height: 52px !important;
      border-radius: 50% !important;
      clip-path: none !important;
      background: linear-gradient(135deg, #ff6b35, #f7931e) !important;
      border: 2px solid rgba(255,255,255,0.25) !important;
      font-size: 18px !important;
      color: #2a0d1a !important;
      box-shadow: 0 3px 12px rgba(255,107,53,0.4) !important;
    }
    body.theme-sunset .channel-icon::after { display: none !important; }

    body.theme-sunset .channel-card-name {
      font-size: 14px !important;
      font-weight: 700;
      color: #ffe8d6 !important;
      text-shadow: none !important;
      letter-spacing: -0.01em;
    }
    body.theme-sunset .channel-card.active .channel-card-name { color: #ffffff !important; }
    body.theme-sunset .channel-card-tag { color: rgba(255,182,150,0.6) !important; font-size: 9px !important; }
    body.theme-sunset .channel-card-msg { color: rgba(255,182,150,0.65) !important; font-size: 11px !important; }
    body.theme-sunset .channel-time { color: rgba(255,182,150,0.6) !important; }
    body.theme-sunset .channel-hex { color: rgba(255,182,150,0.4) !important; }
    body.theme-sunset .channel-badge {
      background: #ff6b35 !important;
      color: #ffffff !important;
      border-radius: 999px !important;
      clip-path: none !important;
      box-shadow: 0 2px 8px rgba(255,107,53,0.6) !important;
      padding: 3px 9px !important;
    }
    body.theme-sunset .cyberdeck-footer {
      background: transparent !important;
      border-top: 1px solid rgba(255,107,53,0.15) !important;
      color: rgba(255,182,150,0.5) !important;
    }

    /* Сообщения — pill */
    body.theme-sunset .msg-bubble {
      border-radius: 22px !important;
      box-shadow: 0 4px 16px rgba(0,0,0,0.25) !important;
    }
    body.theme-sunset .msg-bubble.mine {
      background: linear-gradient(135deg, #ff6b35, #f7931e) !important;
      border: none !important;
      color: #2a0d1a !important;
    }
    body.theme-sunset .msg-bubble.other {
      background: linear-gradient(135deg, rgba(255,255,255,0.12), rgba(255,182,150,0.06)) !important;
      border: none !important;
      color: #ffe8d6 !important;
    }
    body.theme-sunset .chat-surface { background: transparent !important; }
    body.theme-sunset .panel-solid { background: rgba(38,16,31,0.85) !important; }

    /* ============================================================
       AMBER — CRT-терминал: номера каналов, выпуклость, мерцание
       ============================================================ */
    body.theme-amber {
      font-family: "JetBrains Mono", "VT323", monospace;
      letter-spacing: 0.05em;
    }
    body.theme-amber * { text-transform: uppercase; }

    /* Мерцание всего экрана */
    body.theme-amber::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 1000;
      background: rgba(255,176,0,0.02);
      animation: amber-flicker 4s infinite;
    }
    @keyframes amber-flicker {
      0%, 88%, 100% { opacity: 1; }
      89% { opacity: 0.6; }
      90% { opacity: 1; }
      92% { opacity: 0.75; }
      93% { opacity: 1; }
    }

    body.theme-amber .cyberdeck-panel {
      background: #1a1208 !important;
      border-right: 3px double rgba(255,176,0,0.35) !important;
      box-shadow: inset -6px 0 20px rgba(255,176,0,0.08) !important;
    }
    body.theme-amber .cyberdeck-panel::before { display: none !important; }
    body.theme-amber .cyberdeck-header {
      background: none !important;
      border-bottom: 3px double rgba(255,176,0,0.4) !important;
      padding: 12px 14px !important;
      text-align: center;
    }
    body.theme-amber .cyberdeck-header::after { display: none !important; }
    body.theme-amber .cyberdeck-title {
      color: #ffb000 !important;
      font-size: 13px !important;
      letter-spacing: 0.5em !important;
      text-shadow: 0 0 12px rgba(255,176,0,0.7), 0 0 24px rgba(255,176,0,0.4) !important;
    }
    body.theme-amber .cyberdeck-sub { color: #8b5a00 !important; justify-content: center !important; }

    body.theme-amber .cyberdeck-operator {
      border-bottom: 1px solid rgba(255,176,0,0.25) !important;
      padding: 12px 14px !important;
    }
    body.theme-amber .operator-icon {
      border-radius: 50% !important;
      clip-path: none !important;
      background: rgba(255,176,0,0.1) !important;
      border: 2px solid #ffb000 !important;
      color: #ffb000 !important;
      box-shadow: 0 0 12px rgba(255,176,0,0.5), inset 0 0 12px rgba(255,176,0,0.2) !important;
    }

    body.theme-amber .cyberdeck-search {
      background: rgba(255,176,0,0.05) !important;
      border: 1px solid rgba(255,176,0,0.4) !important;
      border-radius: 0 !important;
      clip-path: none !important;
      color: #ffb000 !important;
      letter-spacing: 0.15em !important;
    }

    body.theme-amber .cyberdeck-tabs {
      border-bottom: 3px double rgba(255,176,0,0.3) !important;
      background: rgba(0,0,0,0.3) !important;
    }
    body.theme-amber .cyberdeck-tab { color: #8b5a00 !important; }
    body.theme-amber .cyberdeck-tab.active { color: #ffcc00 !important; background: rgba(255,176,0,0.08) !important; }

    /* Номера каналов */
    body.theme-amber .channel-card-num {
      display: flex !important;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border: 1px solid #ffb000;
      color: #ffb000;
      font-size: 11px;
      font-weight: bold;
      flex-shrink: 0;
      text-shadow: 0 0 6px rgba(255,176,0,0.8);
      box-shadow: inset 0 0 8px rgba(255,176,0,0.15);
    }
    body.theme-amber .channel-card {
      display: flex !important;
      align-items: center !important;
      gap: 12px;
      background: rgba(255,176,0,0.03) !important;
      border: none !important;
      border-bottom: 1px dashed rgba(255,176,0,0.2) !important;
      border-radius: 0 !important;
      clip-path: none !important;
      padding: 12px 14px !important;
      margin: 0 !important;
      box-shadow: none !important;
    }
    body.theme-amber .channel-card:hover {
      background: rgba(255,176,0,0.08) !important;
      box-shadow: inset 3px 0 0 #ffb000 !important;
    }
    body.theme-amber .channel-card.active {
      background: rgba(255,176,0,0.15) !important;
      box-shadow: inset 4px 0 0 #ffb000, 0 0 20px rgba(255,176,0,0.25) !important;
    }
    body.theme-amber .channel-card.active::before { display: none !important; }
    body.theme-amber .channel-icon {
      border-radius: 50% !important;
      clip-path: none !important;
      background: rgba(255,176,0,0.08) !important;
      border: 2px solid rgba(255,176,0,0.6) !important;
      color: #ffb000 !important;
      box-shadow: inset 0 0 12px rgba(255,176,0,0.2), 0 0 10px rgba(255,176,0,0.3) !important;
      text-shadow: 0 0 6px rgba(255,176,0,0.7);
    }
    body.theme-amber .channel-icon::after { display: none !important; }
    body.theme-amber .channel-card-name {
      color: #ffcc00 !important;
      text-shadow: 0 0 8px rgba(255,176,0,0.6) !important;
      letter-spacing: 0.1em !important;
    }
    body.theme-amber .channel-card.active .channel-card-name {
      color: #ffffff !important;
      text-shadow: 0 0 12px #ffb000, 0 0 24px #ffb000 !important;
    }
    body.theme-amber .channel-card-msg { color: #8b5a00 !important; }
    body.theme-amber .channel-card-tag { color: #8b5a00 !important; }
    body.theme-amber .channel-time { color: #8b5a00 !important; }
    body.theme-amber .channel-hex { color: rgba(139,90,0,0.5) !important; }
    body.theme-amber .channel-badge {
      background: #ffb000 !important;
      color: #1a1208 !important;
      box-shadow: 0 0 12px #ffb000 !important;
      clip-path: none !important;
      border-radius: 0 !important;
    }
    body.theme-amber .cyberdeck-footer {
      background: rgba(0,0,0,0.4) !important;
      border-top: 3px double rgba(255,176,0,0.4) !important;
      color: #8b5a00 !important;
    }

    /* Сообщения — коробки с двойной рамкой, светящиеся */
    body.theme-amber .msg-bubble {
      border-radius: 0 !important;
      font-family: "JetBrains Mono", monospace;
      box-shadow: inset 0 0 12px rgba(255,176,0,0.15), 0 0 8px rgba(255,176,0,0.2) !important;
    }
    body.theme-amber .msg-bubble.mine {
      background: rgba(255,176,0,0.10) !important;
      border: 2px solid rgba(255,176,0,0.5) !important;
      color: #ffcc00 !important;
    }
    body.theme-amber .msg-bubble.other {
      background: rgba(255,119,0,0.08) !important;
      border: 2px solid rgba(255,119,0,0.4) !important;
      color: #ffb000 !important;
    }
    body.theme-amber .chat-surface { background: #0d0a05 !important; }
    body.theme-amber .panel-solid { background: #1a1208 !important; }

    /* Угловая метка */
    body.theme-amber .chat-surface::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 2px,
        rgba(255,176,0,0.03) 3px,
        transparent 4px
      );
    }

    /* ============================================================
       DEUS EX — двухколоночный список, гексагоны, тактическая карта
       ============================================================ */
    body.theme-deusex {
      font-family: "Rajdhani", "Eurostile", "JetBrains Mono", sans-serif;
      letter-spacing: 0.08em;
    }
    body.theme-deusex * { text-transform: uppercase; }

    /* Тактическая сетка + координаты */
    body.theme-deusex::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 1;
      background-image:
        linear-gradient(rgba(240,176,48,0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(240,176,48,0.06) 1px, transparent 1px),
        linear-gradient(rgba(240,176,48,0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(240,176,48,0.02) 1px, transparent 1px);
      background-size: 80px 80px, 80px 80px, 20px 20px, 20px 20px;
    }
    /* Координаты в углу */
    body.theme-deusex::after {
      content: "SEC:7F4A / 34.05°N 118.24°W / 2052.09.20";
      position: fixed;
      bottom: 8px;
      right: 14px;
      font-family: "JetBrains Mono", monospace;
      font-size: 9px;
      color: rgba(240,176,48,0.4);
      letter-spacing: 0.25em;
      pointer-events: none;
      z-index: 100;
    }

    body.theme-deusex .cyberdeck-panel {
      background: rgba(8,9,13,0.92) !important;
      border-right: 2px solid rgba(240,176,48,0.4) !important;
      box-shadow: inset -1px 0 0 rgba(240,176,48,0.15), inset -8px 0 0 -7px rgba(240,176,48,0.2);
    }
    body.theme-deusex .cyberdeck-panel::before {
      background-image:
        linear-gradient(rgba(240,176,48,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(240,176,48,0.03) 1px, transparent 1px);
      background-size: 24px 24px;
    }
    body.theme-deusex .cyberdeck-header {
      background: linear-gradient(90deg, rgba(240,176,48,0.10), transparent) !important;
      border-bottom: 1px solid rgba(240,176,48,0.5) !important;
      padding: 10px 14px !important;
      position: relative;
    }
    body.theme-deusex .cyberdeck-header::before {
      content: "[ UNATCO-NET ]";
      position: absolute;
      top: 6px;
      right: 10px;
      font-size: 8px;
      letter-spacing: 0.3em;
      color: rgba(240,176,48,0.55);
    }
    body.theme-deusex .cyberdeck-header::after {
      content: "";
      position: absolute;
      bottom: -1px;
      left: 0;
      width: 60%;
      height: 1px;
      background: linear-gradient(90deg, #f0b030, transparent);
      box-shadow: 0 0 8px #f0b030;
    }
    body.theme-deusex .cyberdeck-title {
      color: #f0b030 !important;
      font-size: 12px !important;
      letter-spacing: 0.4em !important;
      text-shadow: 0 0 8px rgba(240,176,48,0.6) !important;
    }
    body.theme-deusex .cyberdeck-title::before { content: "▸ "; }
    body.theme-deusex .cyberdeck-sub { color: #8a6a30 !important; letter-spacing: 0.3em !important; }

    body.theme-deusex .cyberdeck-operator {
      border-bottom: 1px solid rgba(240,176,48,0.3) !important;
      padding: 12px 14px !important;
    }
    /* Гексагональный аватар оператора */
    body.theme-deusex .operator-icon {
      width: 40px !important;
      height: 44px !important;
      clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%) !important;
      border-radius: 0 !important;
      background: rgba(240,176,48,0.12) !important;
      border: 1px solid rgba(240,176,48,0.6) !important;
      color: #f0b030 !important;
      box-shadow: 0 0 12px rgba(240,176,48,0.4) !important;
      font-size: 13px !important;
    }

    body.theme-deusex .cyberdeck-search {
      background: rgba(240,176,48,0.04) !important;
      border: 1px solid rgba(240,176,48,0.4) !important;
      clip-path: polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px)) !important;
      border-radius: 0 !important;
      color: #f0b030 !important;
    }

    body.theme-deusex .cyberdeck-tabs {
      border: none !important;
      background: rgba(0,0,0,0.3) !important;
      border-bottom: 1px solid rgba(240,176,48,0.3) !important;
    }
    body.theme-deusex .cyberdeck-tab { color: #8a6a30 !important; letter-spacing: 0.3em !important; }
    body.theme-deusex .cyberdeck-tab.active { color: #f0b030 !important; background: rgba(240,176,48,0.1) !important; }
    body.theme-deusex .cyberdeck-tab.active::after { background: #f0b030 !important; box-shadow: 0 0 8px #f0b030 !important; }

    /* Двухколоночный список каналов */
    body.theme-deusex .cyberdeck-list { padding: 0 !important; }
    body.theme-deusex .channel-card {
      display: grid !important;
      grid-template-columns: 30px 40px 1fr auto;
      gap: 8px;
      align-items: center;
      background: rgba(8,9,13,0.7) !important;
      border: none !important;
      border-bottom: 1px solid rgba(240,176,48,0.15) !important;
      border-left: 3px solid transparent !important;
      border-radius: 0 !important;
      clip-path: none !important;
      margin: 0 !important;
      padding: 8px 12px !important;
      box-shadow: none !important;
      position: relative;
    }
    body.theme-deusex .channel-card:hover {
      background: rgba(240,176,48,0.05) !important;
      border-left-color: rgba(240,176,48,0.5) !important;
    }
    body.theme-deusex .channel-card.active {
      background: linear-gradient(90deg, rgba(240,176,48,0.15), rgba(232,90,48,0.05)) !important;
      border-left-color: #f0b030 !important;
      box-shadow: inset 0 0 20px rgba(240,176,48,0.1) !important;
    }
    body.theme-deusex .channel-card.active::before { display: none !important; }
    /* Номер канала — по левому краю */
    body.theme-deusex .channel-card-num {
      display: block !important;
      color: #8a6a30 !important;
      font-size: 10px !important;
      letter-spacing: 0.15em !important;
      font-family: "JetBrains Mono", monospace !important;
      padding-left: 4px;
      border-left: 1px solid rgba(240,176,48,0.3);
      padding-left: 6px;
    }
    body.theme-deusex .channel-card.active .channel-card-num { color: #f0b030 !important; border-color: #f0b030; }
    /* Гексагональные аватары */
    body.theme-deusex .channel-icon {
      width: 34px !important;
      height: 38px !important;
      clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%) !important;
      border-radius: 0 !important;
      background: rgba(240,176,48,0.06) !important;
      border: 1px solid rgba(240,176,48,0.5) !important;
      color: #f0b030 !important;
      font-size: 11px !important;
      box-shadow: 0 0 8px rgba(240,176,48,0.3) !important;
    }
    body.theme-deusex .channel-icon::after { display: none !important; }
    body.theme-deusex .channel-online-dot {
      width: 6px !important;
      height: 6px !important;
      right: 4px !important;
      bottom: 6px !important;
    }
    body.theme-deusex .channel-card-body { min-width: 0; }
    body.theme-deusex .channel-card-tag { color: #8a6a30 !important; font-size: 8px !important; letter-spacing: 0.25em !important; }
    body.theme-deusex .channel-card-name {
      color: #e2d4b0 !important;
      font-size: 12px !important;
      font-weight: 600;
      text-shadow: none !important;
      letter-spacing: 0.15em !important;
    }
    body.theme-deusex .channel-card.active .channel-card-name {
      color: #f7d060 !important;
      text-shadow: 0 0 8px rgba(240,176,48,0.6) !important;
    }
    body.theme-deusex .channel-card-msg { color: #8a6a30 !important; font-size: 10px !important; }
    body.theme-deusex .channel-card-right { flex-direction: column; }
    body.theme-deusex .channel-time { color: #8a6a30 !important; font-size: 9px !important; }
    body.theme-deusex .channel-hex { display: none !important; }
    body.theme-deusex .channel-badge {
      background: #f0b030 !important;
      color: #08090d !important;
      clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px) !important;
      border-radius: 0 !important;
    }
    body.theme-deusex .cyberdeck-footer {
      background: rgba(0,0,0,0.5) !important;
      border-top: 1px solid rgba(240,176,48,0.4) !important;
      color: #8a6a30 !important;
    }

    /* Сообщения — угловые срезы по обеим сторонам */
    body.theme-deusex .msg-bubble {
      font-family: "Rajdhani", "JetBrains Mono", sans-serif;
      letter-spacing: 0.05em;
    }
    body.theme-deusex .msg-bubble.mine {
      background: rgba(240,176,48,0.12) !important;
      border: 1px solid rgba(240,176,48,0.5) !important;
      color: #e2d4b0 !important;
      clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%) !important;
      box-shadow: inset 0 0 12px rgba(240,176,48,0.1), 0 0 8px rgba(240,176,48,0.15) !important;
    }
    body.theme-deusex .msg-bubble.other {
      background: rgba(240,176,48,0.06) !important;
      border: 1px solid rgba(240,176,48,0.35) !important;
      color: #e2d4b0 !important;
      clip-path: polygon(0 0, 100% 0, 100% 100%, 12px 100%, 0 calc(100% - 12px)) !important;
    }
    body.theme-deusex .chat-surface { background: rgba(8,9,13,0.92) !important; }
    body.theme-deusex .panel-solid { background: rgba(15,18,24,0.95) !important; }

    /* ============================================================
       GITS — ультра-минимализм, тонкие линии, много воздуха
       ============================================================ */
    body.theme-gits {
      font-family: "JetBrains Mono", monospace;
      letter-spacing: 0.04em;
      font-weight: 300;
    }

    /* Тонкая голубая сетка очень разреженно */
    body.theme-gits::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 1;
      background-image:
        linear-gradient(rgba(0,217,255,0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,217,255,0.025) 1px, transparent 1px);
      background-size: 120px 120px;
    }
    /* Вертикальная японская метка */
    body.theme-gits::after {
      content: "公安9課 SECTION-9";
      position: fixed;
      left: 8px;
      top: 50%;
      transform: translateY(-50%);
      writing-mode: vertical-rl;
      font-size: 10px;
      letter-spacing: 0.6em;
      color: rgba(0,217,255,0.28);
      pointer-events: none;
      z-index: 100;
      font-weight: 300;
    }

    body.theme-gits .cyberdeck-panel {
      background: rgba(3,10,18,0.6) !important;
      border-right: 1px solid rgba(0,217,255,0.15) !important;
      padding-left: 20px;
    }
    body.theme-gits .cyberdeck-panel::before { display: none !important; }

    body.theme-gits .cyberdeck-header {
      background: none !important;
      border-bottom: 1px solid rgba(0,217,255,0.15) !important;
      padding: 14px 4px !important;
    }
    body.theme-gits .cyberdeck-header::after { display: none !important; }
    body.theme-gits .cyberdeck-title {
      color: #a8d8e8 !important;
      font-size: 10px !important;
      font-weight: 300;
      letter-spacing: 0.5em !important;
      text-shadow: none !important;
      opacity: 0.85;
    }
    body.theme-gits .cyberdeck-sub { color: rgba(168,216,232,0.4) !important; font-weight: 300; letter-spacing: 0.3em !important; }

    body.theme-gits .cyberdeck-operator {
      border-bottom: 1px solid rgba(0,217,255,0.12) !important;
      padding: 14px 4px !important;
    }
    body.theme-gits .operator-icon {
      width: 32px !important;
      height: 32px !important;
      clip-path: none !important;
      border-radius: 0 !important;
      background: none !important;
      border: 1px solid rgba(0,217,255,0.4) !important;
      color: #a8d8e8 !important;
      font-size: 10px !important;
      font-weight: 300;
      box-shadow: none !important;
    }
    body.theme-gits .operator-name {
      color: #e8f4ff !important;
      font-weight: 400 !important;
      letter-spacing: 0.25em !important;
      font-size: 11px !important;
      text-shadow: none !important;
    }
    body.theme-gits .operator-id { font-weight: 300; letter-spacing: 0.2em !important; }

    body.theme-gits .cyberdeck-search {
      background: none !important;
      border: none !important;
      border-bottom: 1px solid rgba(0,217,255,0.25) !important;
      border-radius: 0 !important;
      clip-path: none !important;
      padding: 6px 0 !important;
      color: #e8f4ff !important;
      font-weight: 300;
      letter-spacing: 0.2em !important;
    }
    body.theme-gits .cyberdeck-search::placeholder { color: rgba(168,216,232,0.35) !important; }
    body.theme-gits .cyberdeck-search:focus {
      border-bottom-color: #ff3355 !important;
      box-shadow: none !important;
    }

    body.theme-gits .cyberdeck-tabs {
      background: none !important;
      border-bottom: 1px solid rgba(0,217,255,0.12) !important;
      border-top: none !important;
      padding: 8px 0;
      gap: 24px;
      justify-content: flex-start;
    }
    body.theme-gits .cyberdeck-tab {
      flex: 0 0 auto !important;
      background: none !important;
      color: rgba(168,216,232,0.5) !important;
      font-weight: 300;
      letter-spacing: 0.3em !important;
      font-size: 9px !important;
      padding: 4px 0 !important;
      position: relative;
    }
    body.theme-gits .cyberdeck-tab:hover { color: #a8d8e8 !important; background: none !important; }
    body.theme-gits .cyberdeck-tab.active {
      color: #ff3355 !important;
      background: none !important;
      box-shadow: none !important;
    }
    body.theme-gits .cyberdeck-tab.active::after {
      content: "";
      position: absolute;
      left: 0;
      right: 0;
      bottom: -1px;
      height: 1px;
      background: #ff3355;
      box-shadow: 0 0 4px #ff3355;
    }

    body.theme-gits .cyberdeck-list { padding: 4px 0 !important; }

    /* Очень разреженные строки без карточек */
    body.theme-gits .channel-card {
      display: flex !important;
      align-items: center !important;
      gap: 14px;
      background: none !important;
      border: none !important;
      border-radius: 0 !important;
      clip-path: none !important;
      padding: 14px 4px !important;
      margin: 0 !important;
      box-shadow: none !important;
      position: relative;
    }
    body.theme-gits .channel-card:hover {
      background: rgba(0,217,255,0.02) !important;
    }
    body.theme-gits .channel-card.active {
      background: none !important;
    }
    body.theme-gits .channel-card.active::before {
      content: "";
      position: absolute;
      left: -20px;
      top: 0;
      bottom: 0;
      width: 2px;
      background: #ff3355;
      box-shadow: 0 0 8px #ff3355;
      display: block !important;
    }
    body.theme-gits .channel-card-num { display: none !important; }

    body.theme-gits .channel-icon {
      width: 26px !important;
      height: 26px !important;
      clip-path: none !important;
      border-radius: 0 !important;
      background: none !important;
      border: 1px solid rgba(0,217,255,0.4) !important;
      color: #a8d8e8 !important;
      font-size: 9px !important;
      font-weight: 300;
      box-shadow: none !important;
    }
    body.theme-gits .channel-icon::after { display: none !important; }
    body.theme-gits .channel-online-dot {
      width: 5px !important;
      height: 5px !important;
      right: -1px !important;
      bottom: -1px !important;
      box-shadow: 0 0 4px #00ff88 !important;
    }

    body.theme-gits .channel-card-tag {
      font-size: 8px !important;
      color: rgba(168,216,232,0.4) !important;
      letter-spacing: 0.4em !important;
      font-weight: 300;
    }
    body.theme-gits .channel-card-tag .dm,
    body.theme-gits .channel-card-tag .grp {
      color: rgba(168,216,232,0.4) !important;
      text-shadow: none !important;
    }

    body.theme-gits .channel-card-name {
      color: #e8f4ff !important;
      font-size: 12px !important;
      font-weight: 300;
      letter-spacing: 0.2em !important;
      text-shadow: none !important;
    }
    body.theme-gits .channel-card.active .channel-card-name {
      color: #ffffff !important;
      text-shadow: 0 0 8px rgba(255,51,85,0.5) !important;
    }

    body.theme-gits .channel-card-msg {
      color: rgba(168,216,232,0.35) !important;
      font-size: 10px !important;
      font-weight: 300;
    }

    body.theme-gits .channel-time { color: rgba(168,216,232,0.35) !important; font-size: 9px !important; letter-spacing: 0.2em !important; }
    body.theme-gits .channel-hex { color: rgba(168,216,232,0.2) !important; font-size: 8px !important; }
    body.theme-gits .channel-badge {
      background: #ff3355 !important;
      color: #030a12 !important;
      clip-path: none !important;
      border-radius: 0 !important;
      box-shadow: none !important;
      font-weight: 400;
      padding: 2px 6px !important;
      font-size: 9px !important;
      letter-spacing: 0.15em !important;
    }
    body.theme-gits .cyberdeck-footer {
      background: none !important;
      border-top: 1px solid rgba(0,217,255,0.12) !important;
      color: rgba(168,216,232,0.4) !important;
      font-weight: 300;
      letter-spacing: 0.3em !important;
      padding: 10px 4px !important;
    }

    /* Сообщения — тонкие, минималистичные */
    body.theme-gits .msg-bubble {
      border-radius: 0 !important;
      font-family: "JetBrains Mono", monospace;
      font-weight: 300;
      letter-spacing: 0.02em;
    }
    body.theme-gits .msg-bubble.mine {
      background: rgba(0,217,255,0.05) !important;
      border: 1px solid rgba(0,217,255,0.35) !important;
      color: #e8f4ff !important;
      box-shadow: none !important;
    }
    body.theme-gits .msg-bubble.other {
      background: rgba(255,51,85,0.04) !important;
      border: 1px solid rgba(255,51,85,0.35) !important;
      color: #e8f4ff !important;
      box-shadow: none !important;
    }
    body.theme-gits .chat-surface { background: rgba(3,10,18,0.85) !important; }
    body.theme-gits .panel-solid { background: rgba(6,18,28,0.92) !important; }

    /* ============================================================
       LAIN — VHS-глитч, двойные тени, полупрозрачность, наклон
       ============================================================ */
    body.theme-lain {
      font-family: "JetBrains Mono", monospace;
    }

    /* VHS tracking-bar — полоса, медленно ползущая сверху вниз */
    body.theme-lain::before {
      content: "";
      position: fixed;
      left: 0;
      right: 0;
      height: 60px;
      z-index: 999;
      pointer-events: none;
      background: linear-gradient(180deg,
        transparent,
        rgba(196,48,74,0.06) 40%,
        rgba(216,192,200,0.08) 50%,
        rgba(160,90,138,0.05) 60%,
        transparent);
      animation: lain-track 8s linear infinite;
    }
    @keyframes lain-track {
      0%   { top: -80px; }
      100% { top: 100vh; }
    }

    /* Лёгкое мерцание всего */
    body.theme-lain::after {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      z-index: 998;
      background: rgba(196,48,74,0.015);
      animation: lain-screen 6s infinite;
      mix-blend-mode: screen;
    }
    @keyframes lain-screen {
      0%, 91%, 100% { opacity: 0.3; }
      92% { opacity: 0.9; }
      93% { opacity: 0.3; }
      96% { opacity: 0.6; }
      97% { opacity: 0.3; }
    }

    body.theme-lain .cyberdeck-panel {
      background: rgba(14,7,14,0.94) !important;
      border-right: 1px solid rgba(196,48,74,0.35) !important;
      /* чуть-чуть кривой, как плохая кассета */
      transform: skewX(-0.15deg);
    }
    body.theme-lain .cyberdeck-panel::before {
      background-image:
        repeating-linear-gradient(0deg, transparent 0, transparent 3px, rgba(196,48,74,0.02) 4px, transparent 5px),
        repeating-linear-gradient(90deg, transparent 0, transparent 3px, rgba(160,90,138,0.02) 4px, transparent 5px);
    }

    body.theme-lain .cyberdeck-header {
      background: none !important;
      border-bottom: 1px solid rgba(196,48,74,0.4) !important;
      position: relative;
      padding: 12px 14px !important;
    }
    body.theme-lain .cyberdeck-header::before {
      content: "PRESENT DAY";
      position: absolute;
      right: 12px;
      top: 8px;
      font-size: 8px;
      letter-spacing: 0.4em;
      color: rgba(196,48,74,0.55);
      animation: lain-glitch 5s infinite;
    }
    body.theme-lain .cyberdeck-header::after {
      content: "PRESENT TIME";
      position: absolute;
      right: 12px;
      top: 20px;
      font-size: 8px;
      letter-spacing: 0.4em;
      color: rgba(216,192,200,0.4);
      animation: lain-glitch 5s 0.4s infinite;
    }
    @keyframes lain-glitch {
      0%, 88%, 100% { opacity: 1; transform: translateX(0); }
      90% { opacity: 0.2; transform: translateX(-2px); }
      91% { opacity: 1; transform: translateX(0); }
      94% { opacity: 0.5; transform: translateX(1px); }
      95% { opacity: 1; }
    }
    body.theme-lain .cyberdeck-title {
      color: #c4304a !important;
      font-size: 12px !important;
      letter-spacing: 0.3em !important;
      text-shadow: 1px 0 rgba(160,90,138,0.5), -1px 0 rgba(196,48,74,0.7) !important;
    }
    body.theme-lain .cyberdeck-sub { color: rgba(216,192,200,0.5) !important; }

    body.theme-lain .cyberdeck-operator { border-bottom: 1px solid rgba(196,48,74,0.2) !important; }
    body.theme-lain .operator-icon {
      width: 38px !important;
      height: 38px !important;
      clip-path: none !important;
      border-radius: 6px 0 6px 0 !important;
      background: rgba(24,13,24,0.8) !important;
      border: 1px solid rgba(196,48,74,0.5) !important;
      color: #c4304a !important;
      box-shadow:
        2px 2px 0 rgba(196,48,74,0.15),
        -1px -1px 0 rgba(160,90,138,0.1) !important;
    }
    body.theme-lain .operator-name {
      color: #d8c0c8 !important;
      text-shadow: 1px 0 rgba(196,48,74,0.3), -1px 0 rgba(160,90,138,0.3) !important;
    }

    body.theme-lain .cyberdeck-search {
      background: rgba(24,13,24,0.6) !important;
      border: 1px solid rgba(196,48,74,0.35) !important;
      clip-path: none !important;
      border-radius: 6px 0 6px 0 !important;
      color: #d8c0c8 !important;
      box-shadow: inset 2px 2px 0 rgba(196,48,74,0.05) !important;
      text-shadow: 1px 0 rgba(196,48,74,0.15);
    }

    body.theme-lain .cyberdeck-tabs {
      background: none !important;
      border-top: 1px solid rgba(196,48,74,0.2) !important;
      border-bottom: 1px solid rgba(196,48,74,0.3) !important;
    }
    body.theme-lain .cyberdeck-tab { color: rgba(216,192,200,0.45) !important; }
    body.theme-lain .cyberdeck-tab.active {
      color: #c4304a !important;
      background: rgba(196,48,74,0.08) !important;
      text-shadow: 1px 0 rgba(160,90,138,0.5) !important;
    }
    body.theme-lain .cyberdeck-tab.active::after { background: #c4304a !important; box-shadow: 0 0 8px #c4304a !important; }

    body.theme-lain .cyberdeck-list { padding: 6px 4px !important; }

    /* Карточки с двойными тенями-фантомами + асимметрия */
    body.theme-lain .channel-card {
      display: flex !important;
      align-items: center !important;
      gap: 10px;
      background: rgba(24,13,24,0.7) !important;
      border: 1px solid rgba(196,48,74,0.28) !important;
      border-radius: 10px 0 10px 0 !important;
      clip-path: none !important;
      margin: 4px !important;
      padding: 10px 12px !important;
      position: relative;
      /* тень-двойник */
      box-shadow:
        3px 2px 0 rgba(196,48,74,0.15),
        -2px -2px 0 rgba(160,90,138,0.10) !important;
      transition: transform 0.15s;
    }
    /* Шум-полоска поверх карточки */
    body.theme-lain .channel-card::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 7px,
        rgba(196,48,74,0.04) 8px,
        transparent 9px
      );
      border-radius: inherit;
    }
    body.theme-lain .channel-card:hover {
      background: rgba(40,20,40,0.9) !important;
      transform: translate(-1px, -1px);
      box-shadow:
        5px 3px 0 rgba(196,48,74,0.2),
        -3px -3px 0 rgba(160,90,138,0.15) !important;
    }
    body.theme-lain .channel-card.active {
      background: rgba(50,20,40,0.9) !important;
      border-color: #c4304a !important;
      box-shadow:
        5px 4px 0 rgba(196,48,74,0.25),
        -4px -3px 0 rgba(160,90,138,0.18),
        0 0 16px rgba(196,48,74,0.3) !important;
    }
    body.theme-lain .channel-card.active::before {
      content: "";
      position: absolute;
      left: 0;
      top: 8px;
      bottom: 8px;
      width: 2px;
      background: #c4304a;
      box-shadow: 1px 0 0 rgba(160,90,138,0.8);
      display: block !important;
    }
    body.theme-lain .channel-card-num { display: none !important; }

    body.theme-lain .channel-icon {
      clip-path: none !important;
      border-radius: 8px 0 8px 0 !important;
      background: rgba(24,13,24,0.7) !important;
      border: 1px solid rgba(196,48,74,0.45) !important;
      color: #c4304a !important;
      box-shadow: 2px 2px 0 rgba(196,48,74,0.12), -1px -1px 0 rgba(160,90,138,0.08) !important;
      filter: saturate(0.75) contrast(1.05);
      text-shadow: 1px 0 rgba(160,90,138,0.5);
    }
    body.theme-lain .channel-icon::after { display: none !important; }

    body.theme-lain .channel-card-name {
      color: #d8c0c8 !important;
      text-shadow: 1px 0 rgba(196,48,74,0.25), -1px 0 rgba(160,90,138,0.25) !important;
    }
    body.theme-lain .channel-card.active .channel-card-name {
      color: #c4304a !important;
      text-shadow: 1px 0 rgba(160,90,138,0.7), -1px 0 rgba(196,48,74,0.7), 0 0 8px rgba(196,48,74,0.6) !important;
    }
    body.theme-lain .channel-card-tag { color: rgba(216,192,200,0.4) !important; }
    body.theme-lain .channel-card-msg { color: rgba(216,192,200,0.5) !important; font-style: italic; }
    body.theme-lain .channel-time { color: rgba(216,192,200,0.4) !important; }
    body.theme-lain .channel-hex { color: rgba(160,90,138,0.35) !important; }
    body.theme-lain .channel-badge {
      background: #c4304a !important;
      color: #0e070e !important;
      clip-path: none !important;
      border-radius: 4px 0 4px 0 !important;
      box-shadow: 2px 2px 0 rgba(160,90,138,0.4) !important;
    }
    body.theme-lain .cyberdeck-footer {
      background: rgba(0,0,0,0.4) !important;
      border-top: 1px solid rgba(196,48,74,0.3) !important;
      color: rgba(216,192,200,0.4) !important;
    }

    /* Сообщения — двойные тени-фантомы, асимметрия */
    body.theme-lain .msg-bubble {
      border-radius: 8px 0 8px 0 !important;
      font-family: "JetBrains Mono", monospace;
      position: relative;
      /* VHS-двоение */
      filter: drop-shadow(2px 1px 0 rgba(196,48,74,0.2)) drop-shadow(-1px -1px 0 rgba(160,90,138,0.12));
    }
    body.theme-lain .msg-bubble.mine {
      background: rgba(196,48,74,0.10) !important;
      border: 1px solid rgba(196,48,74,0.45) !important;
      color: #d8c0c8 !important;
      box-shadow: 3px 2px 0 rgba(196,48,74,0.15) !important;
    }
    body.theme-lain .msg-bubble.other {
      background: rgba(40,20,40,0.6) !important;
      border: 1px solid rgba(160,90,138,0.4) !important;
      color: #d8c0c8 !important;
      box-shadow: -3px 2px 0 rgba(160,90,138,0.15) !important;
    }
    body.theme-lain .chat-surface { background: rgba(14,7,14,0.9) !important; }
    body.theme-lain .panel-solid { background: rgba(24,13,24,0.92) !important; }
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

    print("\nСпринт 17 — радикально разные темы\n")

    # 1) themes.ts
    (src / "themes.ts").write_text(THEMES_TS, encoding="utf-8")
    print(f"  ~ {src / 'themes.ts'}")

    # 2) ChatList.tsx — с data-атрибутами и номером
    (src / "ChatList.tsx").write_text(CHATLIST, encoding="utf-8")
    print(f"  ~ {src / 'ChatList.tsx'}")

    # 3) MessageBubble — патчим на классы
    mb_path = src / "MessageBubble.tsx"
    mb_text = mb_path.read_text(encoding="utf-8")
    changed = False
    for old, new in MESSAGEBUBBLE_REPLACEMENTS:
        if old in mb_text:
            mb_text = mb_text.replace(old, new, 1)
            changed = True
    if changed:
        mb_path.write_text(mb_text, encoding="utf-8")
        print(f"  ~ {mb_path}")
    else:
        print(f"  > {mb_path} (патчи не применены, проверь вручную)")

    # 4) index.css — дописываем тему-специфичные стили
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "MESSAGE BUBBLES — базовые (cyber)" not in css_text:
        # удаляем старую секцию theme-extras (из спринта 15/16), чтобы не конфликтовало
        for marker in ["THEME EXTRAS — deus ex / gits / lain",
                       "THEME VISUAL IDENTITY — форма, а не только цвет"]:
            idx = css_text.find(marker)
            if idx != -1:
                # находим конец — до конца файла обычно, но обрежем аккуратно
                # ищем следующий \\n    /* ===== или конец
                end = css_text.find("\n    /*", idx + 20)
                if end == -1:
                    end = len(css_text)
                css_text = css_text[:idx] + css_text[end:]
        css_text = css_text.rstrip() + "\n" + THEME_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path} (радикальные темы добавлены)")
    else:
        print(f"  > {css_path} (уже пропатчено)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Переключение темы: ⚙ → THEME, или Ctrl+K → 'theme'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())