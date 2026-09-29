#!/usr/bin/env python3
"""fix_ws.py - WebSocket reconnect after login."""
from __future__ import annotations

import argparse
from pathlib import Path

WS_TS = '''import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE } from "./api";

type Handler = (data: any) => void;

export function useWebSocket(onMessage: Handler, userId: number | null) {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Set<Handler>>(new Set());
  const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);
  const reconnectRef = useRef<number | null>(null);
  const cancelledRef = useRef<boolean>(false);

  const onMessageRef = useRef(onMessage);
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

  const connect = useCallback(() => {
    if (cancelledRef.current) return;
    const token = localStorage.getItem("access_token");
    if (!token) return;
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(`${WS_BASE}?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => setReadyState(WebSocket.OPEN);
    ws.onclose = () => {
      setReadyState(WebSocket.CLOSED);
      if (!cancelledRef.current) {
        reconnectRef.current = window.setTimeout(connect, 2000);
      }
    };
    ws.onerror = () => ws.close();
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        onMessageRef.current(d);
        handlersRef.current.forEach((h) => h(d));
      } catch {}
    };
  }, []);

  // Переподключение при смене пользователя (login / logout)
  useEffect(() => {
    cancelledRef.current = false;
    if (userId == null) {
      // logout — рвём соединение
      if (reconnectRef.current) {
        window.clearTimeout(reconnectRef.current);
        reconnectRef.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
      setReadyState(WebSocket.CLOSED);
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

  return { send, subscribe, connected: readyState === WebSocket.OPEN, readyState };
}
'''

# Патч App.tsx — передать user?.id в хук
APP_PATTERNS = [
    (
        'const { send, subscribe, readyState } = useWebSocket(onWs);',
        'const { send, subscribe, readyState } = useWebSocket(onWs, user?.id ?? null);',
    ),
]

# Патч ChatWindow.tsx — обработать error с client_id
CW_PATTERNS = [
    (
        '          } else if (d.type === "read" && d.chat_id === chat.id) {\n'
        '            setPeerReadUpdTo((prev) => Math.max(prev, d.message_id));\n'
        '          }',
        '          } else if (d.type === "read" && d.chat_id === chat.id) {\n'
        '            setPeerReadUpdTo((prev) => Math.max(prev, d.message_id));\n'
        '          }',
    ),
    # добавим обработку error выше read
    (
        '          } else if (d.type === "typing" && d.chat_id === chat.id) {',
        '          } else if (d.type === "error" && d.client_id) {\n'
        '            onRemoveQueued(d.client_id);\n'
        '          } else if (d.type === "typing" && d.chat_id === chat.id) {',
    ),
]


def patch_file(path: Path, patterns: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in patterns:
        if new in text:
            continue
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
        print(f"ERR: {root} не найдено.")
        return 1

    print(f"\nФикс WS-реконнекта в {root}\n")

    ws = root / "frontend" / "src" / "ws.ts"
    ws.write_text(WS_TS, encoding="utf-8")
    print(f"  ~ {ws}")

    patch_file(root / "frontend" / "src" / "App.tsx", APP_PATTERNS)
    patch_file(root / "frontend" / "src" / "ChatWindow.tsx", CW_PATTERNS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())