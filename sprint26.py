#!/usr/bin/env python3
"""sprint26_part2.py - UI integration for channels, roles, tools."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================== CommentsDrawer.tsx
COMMENTS_DRAWER = r'''import { useEffect, useState } from "react";
import Avatar from "./Avatar";
import { api } from "./api";
import type { Message } from "./types";

export default function CommentsDrawer({
  parentMessage, currentUser, send, subscribe, onClose,
}: {
  parentMessage: Message;
  currentUser: { id: number; username: string; display_name: string | null; avatar_color: string | null };
  send: (data: any) => void;
  subscribe: (h: (d: any) => void) => () => void;
  onClose: () => void;
}) {
  const [comments, setComments] = useState<Message[]>([]);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(true);

  // Load existing comments
  useEffect(() => {
    let cancelled = false;
    api.get<Message[]>(`/chats/${parentMessage.chat_id}/messages`)
      .then((r) => {
        if (cancelled) return;
        // filter by reply_to_id === parentMessage.id
        const filtered = r.data.filter((m) => m.reply_to_id === parentMessage.id);
        setComments(filtered);
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [parentMessage.id, parentMessage.chat_id]);

  // Subscribe to new comments
  useEffect(() => {
    const off = subscribe((d) => {
      if (d.type === "message"
          && d.chat_id === parentMessage.chat_id
          && d.reply_to_id === parentMessage.id) {
        setComments((prev) => {
          if (prev.some((c) => c.id === d.id)) return prev;
          return [...prev, {
            id: d.id,
            chat_id: d.chat_id,
            author_id: d.author_id,
            author_username: d.author_username,
            author_display: d.author_display,
            author_avatar_color: d.author_avatar_color,
            author_faction: d.author_faction,
            text: d.text,
            message_type: d.message_type || "text",
            attachment: d.attachment || null,
            reply_to_id: d.reply_to_id,
            reply_preview: null,
            reply_author: null,
            edited_at: null,
            is_deleted: false,
            is_pinned: false,
            reactions: [],
            created_at: d.created_at,
          }];
        });
      }
    });
    return off;
  }, [parentMessage.id, parentMessage.chat_id, subscribe]);

  const submit = () => {
    const t = text.trim();
    if (!t) return;
    send({
      type: "send",
      chat_id: parentMessage.chat_id,
      text: t,
      reply_to_id: parentMessage.id,
      message_type: "text",
    });
    setText("");
  };

  return (
    <aside className="comments-drawer">
      <header className="comments-drawer__head">
        <span>◈ COMMENTS · {comments.length}</span>
        <button className="comments-drawer__close" onClick={onClose} title="Закрыть">✕</button>
      </header>

      {/* Parent post preview */}
      <div className="comments-parent">
        <div className="comments-parent__label">POST</div>
        <div className="comments-parent__text">
          {parentMessage.text || "[attachment]"}
        </div>
      </div>

      <div className="comments-drawer__body">
        {loading && (
          <div className="comments-empty">// loading...</div>
        )}
        {!loading && comments.length === 0 && (
          <div className="comments-empty">// пока нет комментариев</div>
        )}
        {comments.map((c) => (
          <div key={c.id} className="comment-item">
            <Avatar
              user={{
                username: c.author_username,
                display_name: c.author_display,
                avatar_color: c.author_avatar_color,
              }}
              size={28}
            />
            <div className="comment-item__body">
              <div className="comment-item__head">
                <span className="comment-item__author">
                  {c.author_display || c.author_username}
                </span>
                <span className="comment-item__time">
                  {new Date(c.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
              <div className="comment-item__text">{c.text}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="comments-drawer__input">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), submit())}
          placeholder="Написать комментарий..."
        />
        <button onClick={submit} disabled={!text.trim()}>▶</button>
      </div>
    </aside>
  );
}
'''


# ============================================================== ws.ts — add tool_updated handler
WS_TS = r'''import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE } from "./api";

type Handler = (data: any) => void;

export function useWebSocket(onMessage: Handler, userId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Set<Handler>>(new Set());
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);
  const [lastError, setLastError] = useState<string | null>(null);
  const reconnectRef = useRef<number | null>(null);
  const cancelledRef = useRef<boolean>(false);

  const onMessageRef = useRef(onMessage);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

  const connect = useCallback(() => {
    if (cancelledRef.current) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const url = `${WS_BASE}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setReadyState(WebSocket.OPEN);
      setLastError(null);
    };
    ws.onclose = (e) => {
      setReadyState(WebSocket.CLOSED);
      if (e.code !== 1000) console.warn("[ws] closed", e.code, e.reason);
      if (!cancelledRef.current) {
        reconnectRef.current = window.setTimeout(connect, 2000);
      }
    };
    ws.onerror = () => {};
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "error") {
          console.warn("[ws] server error:", d.detail);
          setLastError(d.detail || "unknown error");
        }
        // broadcast tool_updated via CustomEvent so any component can listen
        if (d.type === "tool_updated") {
          window.dispatchEvent(new CustomEvent("tool_updated", { detail: d }));
        }
        onMessageRef.current(d);
        handlersRef.current.forEach((h) => h(d));
      } catch {}
    };
  }, []);

  useEffect(() => {
    cancelledRef.current = false;
    if (userId == null) {
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
      setReadyState(WebSocket.CLOSED);
      setLastError(null);
      return;
    }
    connect();
    return () => {
      cancelledRef.current = true;
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [userId, connect]);

  const send = useCallback((data: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
      return true;
    }
    return false;
  }, []);

  const subscribe = useCallback((h: Handler) => {
    handlersRef.current.add(h);
    return () => handlersRef.current.delete(h);
  }, []);

  return {
    send,
    subscribe,
    connected: readyState === WebSocket.OPEN,
    readyState,
    lastError,
  };
}
'''


# ============================================================== Comments CSS
COMMENTS_CSS = r'''
    /* ============ COMMENTS DRAWER ============ */
    .comments-parent {
      padding: 10px 14px;
      background: rgba(0,240,255,0.04);
      border-bottom: 1px solid rgba(0,240,255,0.15);
    }
    .comments-parent__label {
      font-size: 9px;
      letter-spacing: 0.3em;
      color: #5a7a95;
      text-transform: uppercase;
      margin-bottom: 4px;
    }
    .comments-parent__text {
      font-size: 12px;
      color: #a8c8e0;
      opacity: 0.8;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 80px;
      overflow-y: auto;
    }
    .comments-empty {
      padding: 30px 10px;
      text-align: center;
      font-size: 10px;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: #5a7a95;
    }
    .comment-item {
      display: flex;
      gap: 8px;
      padding: 6px 0;
      border-bottom: 1px solid rgba(0,240,255,0.08);
    }
    .comment-item:last-child { border-bottom: none; }
    .comment-item__body {
      flex: 1;
      min-width: 0;
    }
    .comment-item__head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 6px;
      margin-bottom: 2px;
    }
    .comment-item__author {
      font-size: 11px;
      font-weight: bold;
      color: #00f0ff;
      text-shadow: 0 0 4px rgba(0,240,255,0.5);
      text-transform: uppercase;
      letter-spacing: 0.1em;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .comment-item__time {
      font-size: 9px;
      color: #5a7a95;
      white-space: nowrap;
    }
    .comment-item__text {
      font-size: 12px;
      color: #d6ecff;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.4;
    }
'''


# ============================================================== Channel badge CSS
CHANNEL_BADGE_CSS = r'''
    /* ============ CHANNEL INDICATORS ============ */
    .channel-header-badge {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 8px;
      background: rgba(252,238,10,0.08);
      border: 1px solid rgba(252,238,10,0.5);
      color: #fcee0a;
      font-size: 9px;
      font-weight: bold;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      text-shadow: 0 0 6px rgba(252,238,10,0.7);
      clip-path: polygon(4px 0, 100% 0, 100% calc(100% - 4px), calc(100% - 4px) 100%, 0 100%, 0 4px);
    }
    .channel-header-badge--guest {
      background: rgba(90,122,149,0.08);
      border-color: rgba(90,122,149,0.5);
      color: #8ba0b8;
      text-shadow: none;
    }

    /* Locked composer for channels (guests) */
    .channel-lock {
      padding: 14px;
      text-align: center;
      font-size: 10px;
      letter-spacing: 0.3em;
      text-transform: uppercase;
      color: #5a7a95;
      border-top: 1px solid rgba(0,240,255,0.2);
      background: rgba(3,10,20,0.65);
    }
    .channel-lock strong {
      color: #fcee0a;
      text-shadow: 0 0 6px rgba(252,238,10,0.6);
    }
'''


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


# ============================================================== ChatWindow patches
CHATWINDOW_PATCHES = [
    # imports
    (
        'import SearchModal from "./SearchModal";',
        'import SearchModal from "./SearchModal";\n'
        'import DocTool from "./DocTool";\n'
        'import KanbanTool from "./KanbanTool";\n'
        'import CalendarTool from "./CalendarTool";\n'
        'import CommentsDrawer from "./CommentsDrawer";',
    ),
    # state — tools tabs + comments
    (
        'const [showSearch, setShowSearch] = useState(false);',
        'const [showSearch, setShowSearch] = useState(false);\n'
        '  const [activeTool, setActiveTool] = useState<"chat" | "doc" | "board" | "calendar">("chat");\n'
        '  const [commentsFor, setCommentsFor] = useState<Message | null>(null);',
    ),
    # Header — add tabs row below header (inject after </header>)
    (
        '        )}\n'
        '      </header>\n'
        '\n'
        '      {failedCount > 0 && (',
        '        )}\n'
        '      </header>\n'
        '\n'
        '      {/* Tools tabs */}\n'
        '      <div className="tool-tabs">\n'
        '        <button\n'
        '          onClick={() => setActiveTool("chat")}\n'
        '          className={"tool-tab" + (activeTool === "chat" ? " active" : "")}\n'
        '        >◈ CHAT</button>\n'
        '        <button\n'
        '          onClick={() => setActiveTool("doc")}\n'
        '          className={"tool-tab" + (activeTool === "doc" ? " active" : "")}\n'
        '        >▤ DOC</button>\n'
        '        <button\n'
        '          onClick={() => setActiveTool("board")}\n'
        '          className={"tool-tab" + (activeTool === "board" ? " active" : "")}\n'
        '        >▦ BOARD</button>\n'
        '        <button\n'
        '          onClick={() => setActiveTool("calendar")}\n'
        '          className={"tool-tab" + (activeTool === "calendar" ? " active" : "")}\n'
        '        >▦ CAL</button>\n'
        '      </div>\n'
        '\n'
        '      {failedCount > 0 && (',
    ),
]


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

    print("\nСпринт 26 part 2 — UI интеграция\n")

    # 1. Создаём CommentsDrawer.tsx
    (src / "CommentsDrawer.tsx").write_text(COMMENTS_DRAWER, encoding="utf-8")
    print(f"  + {src / 'CommentsDrawer.tsx'}")

    # 2. Перезаписываем ws.ts с tool_updated event
    (src / "ws.ts").write_text(WS_TS, encoding="utf-8")
    print(f"  ~ {src / 'ws.ts'}")

    # 3. CSS — добавляем в конец index.css
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "COMMENTS DRAWER" not in css_text:
        css_text = css_text.rstrip() + "\n" + COMMENTS_CSS + "\n" + CHANNEL_BADGE_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    # 4. Патчи в ChatWindow
    patch_file(src / "ChatWindow.tsx", CHATWINDOW_PATCHES)

    print("\nЧто добавилось в CSS и файлах:")
    print("  • CommentsDrawer.tsx — компонент панели комментариев")
    print("  • ws.ts — теперь dispatch'ит CustomEvent 'tool_updated'")
    print("  • CSS для comments-drawer, channel-header-badge, channel-lock")
    print("  • В ChatWindow.tsx добавлены импорты и state (activeTool, commentsFor)")
    print("  • В шапку чата — вкладки CHAT/DOC/BOARD/CAL")
    print()
    print("ВАЖНО: это только часть. Осталось вставить в ChatWindow JSX:")
    print("  1. Условный рендер: если activeTool === 'doc' → <DocTool .../>")
    print("  2. Тот же паттерн для board и calendar")
    print("  3. Кнопка 'comments' под постами канала")
    print("  4. Интеграцию в GroupInfoPanel (редактор ролей)")
    print("  5. Переключатель канала в SettingsPanel")
    print()
    print("Это будет sprint26_part3.py — скажи 'продолжай', и пришлю.")
    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())