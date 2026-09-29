#!/usr/bin/env python3
"""sprint13.py - cyberdeck-style channel selector."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


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
      {/* ============= Header ============= */}
      <div className="cyberdeck-header">
        <div className="cyberdeck-title">◈ NET_CHANNELS</div>
        <div className="cyberdeck-sub">
          <span className="dot">●</span> LINK_UP
          <span className="sep">·</span>{chats.length} CHAN
          <span className="sep">·</span>{onlineCount} ONLINE
        </div>
      </div>

      {/* ============= Operator card ============= */}
      <div className="cyberdeck-operator">
        <button
          onClick={onOpenProfile}
          className="channel-icon shrink-0"
          style={{ width: 40, height: 40, fontSize: 14 }}
          title="Профиль"
        >
          {initials(currentUser.display_name || currentUser.username)}
        </button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[11px] font-bold uppercase tracking-widest neon-text">
            {currentUser.display_name || currentUser.username}
          </div>
          <div className="truncate text-[9px] uppercase tracking-widest text-cyber-dim">
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

      {/* ============= Search ============= */}
      <div className="px-3 pb-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="> SCAN_CHANNELS..."
          className="cyberdeck-search"
        />
      </div>

      {/* ============= Tabs ============= */}
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

      {/* ============= Failed queue alert ============= */}
      {(failedQueue ?? 0) > 0 && (
        <div className="cyberdeck-alert">
          ⚠ {failedQueue} FAILED_UPLINK
        </div>
      )}

      {/* ============= Channel list ============= */}
      <div className="cyberdeck-list">
        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center text-[10px] uppercase tracking-[0.3em] text-cyber-dim">
            // no_channels
          </div>
        ) : (
          filtered.map((c) => {
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
              >
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

      {/* ============= Footer status ============= */}
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


CSS = r'''
    /* ============================================================
       CYBERDECK CHANNEL SELECTOR
       ============================================================ */
    .cyberdeck-panel {
      background:
        linear-gradient(180deg, rgba(10,15,26,0.97), rgba(6,9,15,0.98));
      border-right: 1px solid rgba(0,240,255,0.25);
      position: relative;
      overflow: hidden;
    }
    .cyberdeck-panel::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(0,240,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,240,255,0.03) 1px, transparent 1px);
      background-size: 20px 20px;
      opacity: 0.55;
    }

    /* ---------- Header ---------- */
    .cyberdeck-header {
      padding: 10px 14px;
      border-bottom: 1px solid rgba(0,240,255,0.25);
      background: linear-gradient(90deg, rgba(252,238,10,0.06), transparent 70%);
      position: relative;
    }
    .cyberdeck-header::after {
      content: "";
      position: absolute;
      left: 0;
      bottom: -1px;
      width: 40%;
      height: 1px;
      background: linear-gradient(90deg, #fcee0a, transparent);
      box-shadow: 0 0 8px #fcee0a;
    }
    .cyberdeck-title {
      color: #fcee0a;
      font-size: 11px;
      font-weight: bold;
      letter-spacing: 0.35em;
      text-transform: uppercase;
      text-shadow: 0 0 8px rgba(252,238,10,0.7), 0 1px 2px rgba(0,0,0,0.9);
    }
    .cyberdeck-sub {
      color: #5a7a95;
      font-size: 9px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      margin-top: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .cyberdeck-sub .dot {
      color: #00ff88;
      text-shadow: 0 0 6px #00ff88;
    }
    .cyberdeck-sub .sep { opacity: 0.5; }

    /* ---------- Operator ---------- */
    .cyberdeck-operator {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-bottom: 1px solid rgba(0,240,255,0.12);
      position: relative;
    }
    .cyberdeck-icon-btn {
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #00f0ff;
      background: rgba(0,240,255,0.06);
      border: 1px solid rgba(0,240,255,0.35);
      cursor: pointer;
      font-family: inherit;
      transition: all 0.15s;
      clip-path: polygon(
        0 4px,
        4px 0,
        calc(100% - 4px) 0,
        100% 4px,
        100% calc(100% - 4px),
        calc(100% - 4px) 100%,
        4px 100%,
        0 calc(100% - 4px)
      );
    }
    .cyberdeck-icon-btn:hover {
      background: rgba(0,240,255,0.18);
      filter: drop-shadow(0 0 6px rgba(0,240,255,0.7));
    }

    /* ---------- Search ---------- */
    .cyberdeck-search {
      width: 100%;
      background: rgba(0,240,255,0.04);
      border: 1px solid rgba(0,240,255,0.28);
      color: #eaf4ff;
      padding: 8px 12px;
      font-size: 11px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      font-family: inherit;
      outline: none;
      transition: border-color 0.15s, box-shadow 0.15s;
      clip-path: polygon(
        0 0,
        calc(100% - 8px) 0,
        100% 8px,
        100% 100%,
        8px 100%,
        0 calc(100% - 8px)
      );
    }
    .cyberdeck-search:focus {
      border-color: #fcee0a;
      box-shadow: 0 0 12px rgba(252,238,10,0.35), inset 0 0 8px rgba(252,238,10,0.06);
      background: rgba(252,238,10,0.04);
    }
    .cyberdeck-search::placeholder {
      color: #3a5470;
      letter-spacing: 0.2em;
    }

    /* ---------- Tabs ---------- */
    .cyberdeck-tabs {
      display: flex;
      border-top: 1px solid rgba(0,240,255,0.15);
      border-bottom: 1px solid rgba(0,240,255,0.22);
      background: rgba(0,0,0,0.35);
    }
    .cyberdeck-tab {
      flex: 1;
      padding: 9px 4px;
      font-size: 10px;
      font-weight: bold;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: #5a7a95;
      background: none;
      border: none;
      cursor: pointer;
      transition: all 0.15s;
      font-family: inherit;
      position: relative;
    }
    .cyberdeck-tab:hover {
      color: #00f0ff;
      background: rgba(0,240,255,0.05);
    }
    .cyberdeck-tab.active {
      color: #fcee0a;
      background: rgba(252,238,10,0.06);
    }
    .cyberdeck-tab.active::after {
      content: "";
      position: absolute;
      left: 25%;
      right: 25%;
      bottom: -1px;
      height: 2px;
      background: #fcee0a;
      box-shadow: 0 0 8px #fcee0a;
    }

    /* ---------- Alert ---------- */
    .cyberdeck-alert {
      padding: 6px 14px;
      background: rgba(255,45,85,0.12);
      border-bottom: 1px solid rgba(255,45,85,0.4);
      color: #ff2d55;
      font-size: 10px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      text-shadow: 0 0 6px rgba(255,45,85,0.7);
    }

    /* ---------- List ---------- */
    .cyberdeck-list {
      flex: 1;
      overflow-y: auto;
      padding: 6px 0;
    }

    /* ---------- Channel card ---------- */
    .channel-card {
      position: relative;
      display: flex;
      align-items: center;
      gap: 10px;
      width: calc(100% - 12px);
      margin: 3px 6px;
      padding: 9px 12px;
      text-align: left;
      background: rgba(10,15,26,0.55);
      border: 1px solid rgba(0,240,255,0.16);
      color: inherit;
      font-family: inherit;
      cursor: pointer;
      transition: background 0.12s, border-color 0.12s;
      clip-path: polygon(
        0 0,
        calc(100% - 10px) 0,
        100% 10px,
        100% 100%,
        10px 100%,
        0 calc(100% - 10px)
      );
    }
    .channel-card:hover {
      background: rgba(0,240,255,0.06);
      border-color: rgba(0,240,255,0.55);
    }
    .channel-card:hover .channel-card-name {
      color: #00f0ff;
      text-shadow: 0 0 6px rgba(0,240,255,0.6);
    }
    .channel-card:hover .channel-icon {
      border-color: rgba(0,240,255,0.7);
    }

    .channel-card.active {
      background: linear-gradient(135deg, rgba(252,238,10,0.10), rgba(0,240,255,0.04));
      border-color: #fcee0a;
      filter: drop-shadow(0 0 8px rgba(252,238,10,0.35));
    }
    .channel-card.active .channel-card-name {
      color: #fcee0a;
      text-shadow: 0 0 8px rgba(252,238,10,0.75);
    }
    .channel-card.active::before {
      content: "";
      position: absolute;
      left: 0;
      top: 8px;
      bottom: 8px;
      width: 3px;
      background: #fcee0a;
      box-shadow: 0 0 10px #fcee0a, 0 0 20px rgba(252,238,10,0.6);
    }
    .channel-card.active .channel-icon {
      border-color: #fcee0a;
      background: rgba(252,238,10,0.10);
      box-shadow: 0 0 12px rgba(252,238,10,0.5);
    }
    .channel-card.active .channel-card-tag {
      color: #fcee0a;
      opacity: 0.85;
    }
    .channel-card.active .channel-card-name {
      color: #fcee0a;
    }

    /* ---------- Icon ---------- */
    .channel-icon {
      position: relative;
      flex-shrink: 0;
      width: 38px;
      height: 38px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 13px;
      letter-spacing: 0.05em;
      color: #eaf4ff;
      background: rgba(0,240,255,0.08);
      border: 1px solid rgba(0,240,255,0.4);
      transition: all 0.12s;
      clip-path: polygon(
        0 6px,
        6px 0,
        calc(100% - 6px) 0,
        100% 6px,
        100% calc(100% - 6px),
        calc(100% - 6px) 100%,
        6px 100%,
        0 calc(100% - 6px)
      );
      overflow: hidden;
    }
    .channel-icon::after {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        45deg,
        transparent 0 4px,
        rgba(0,240,255,0.07) 4px 5px
      );
      opacity: 0.6;
    }
    .channel-online-dot {
      position: absolute;
      right: 3px;
      bottom: 3px;
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: #00ff88;
      box-shadow: 0 0 8px #00ff88;
      border: 1px solid #05070d;
      z-index: 1;
    }

    /* ---------- Card body ---------- */
    .channel-card-body {
      min-width: 0;
      flex: 1;
    }
    .channel-card-tag {
      font-size: 8px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: #5a7a95;
      margin-bottom: 2px;
      font-weight: bold;
    }
    .channel-card-tag .dm { color: #00f0ff; text-shadow: 0 0 4px rgba(0,240,255,0.5); }
    .channel-card-tag .grp { color: #ff00a0; text-shadow: 0 0 4px rgba(255,0,160,0.5); }
    .channel-card-tag .pinned { color: #fcee0a; }

    .channel-card-name {
      font-size: 12px;
      font-weight: bold;
      letter-spacing: 0.1em;
      color: #eaf4ff;
      text-transform: uppercase;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      transition: color 0.12s;
    }

    .channel-card-msg {
      font-size: 10px;
      color: #5a7a95;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-top: 2px;
      letter-spacing: 0.03em;
    }

    /* ---------- Right side ---------- */
    .channel-card-right {
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
      flex-shrink: 0;
    }
    .channel-time {
      font-size: 9px;
      color: #5a7a95;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .channel-hex {
      font-size: 8px;
      color: rgba(90,122,149,0.6);
      letter-spacing: 0.1em;
    }
    .channel-badge {
      font-size: 9px;
      font-weight: bold;
      padding: 2px 6px;
      color: #05070d;
      background: #ff00a0;
      letter-spacing: 0.1em;
      box-shadow: 0 0 8px #ff00a0;
      clip-path: polygon(
        0 3px,
        3px 0,
        100% 0,
        100% calc(100% - 3px),
        calc(100% - 3px) 100%,
        0 100%
      );
    }
    .channel-badge.pulse {
      animation: badge-pulse 2s ease-in-out infinite;
    }
    @keyframes badge-pulse {
      0%,100% { box-shadow: 0 0 8px #ff00a0; }
      50%     { box-shadow: 0 0 16px #ff00a0, 0 0 28px rgba(255,0,160,0.5); }
    }

    /* ---------- Footer ---------- */
    .cyberdeck-footer {
      display: flex;
      justify-content: space-between;
      padding: 6px 14px;
      border-top: 1px solid rgba(0,240,255,0.22);
      background: rgba(0,0,0,0.4);
      font-size: 9px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: #5a7a95;
    }
'''


CSS_ANCHOR_OLD = """    .status-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      box-shadow: 0 0 6px currentColor;
    }"""


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

    print("\nСпринт 13 — cyberdeck channel selector\n")

    # ChatList — переписываем полностью
    (src / "ChatList.tsx").write_text(CHATLIST, encoding="utf-8")
    print(f"  ~ {src / 'ChatList.tsx'}")

    # index.css — добавляем стили (в конец)
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if ".cyberdeck-panel" not in css_text:
        css_text = css_text.rstrip() + "\n" + CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path} (стили добавлены)")
    else:
        print(f"  > {css_path} (уже пропатчено)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())