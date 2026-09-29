#!/usr/bin/env python3
"""sprint14.py - fix ws 403: accept first, log real error, show banner."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


WS_PY = r'''from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app import cache
from app.db import SessionLocal
from app.logging_config import get_logger
from app.models import ChatMember, File as FileModel, Message, MessageReaction, User
from app.security import decode_token
from app.websocket_manager import manager


router = APIRouter()
log = get_logger("ws")


async def _author_payload(db, user_id: int) -> dict:
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
    return {
        "author_id": u.id, "author_username": u.username,
        "author_display": u.display_name,
        "author_avatar_color": u.avatar_color,
    }


async def _attachment_payload(db, attachment_id: int | None) -> dict | None:
    if not attachment_id:
        return None
    f = (await db.execute(
        select(FileModel).where(FileModel.id == attachment_id)
    )).scalar_one_or_none()
    if not f:
        return None
    return {
        "id": f.id, "filename": f.filename,
        "content_type": f.content_type, "size": f.size,
        "created_at": f.created_at.isoformat(),
    }


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = "") -> None:
    # 1) ВСЕГДА принимаем — чтобы можно было вернуть внятную ошибку.
    #    manager.connect не будет вызывать accept повторно (мы это поправили).
    await ws.accept()

    if not token:
        log.warning("ws_no_token")
        try:
            await ws.send_json({"type": "error", "detail": "missing token"})
        except Exception:
            pass
        await ws.close(code=4401)
        return

    # 2) Декодируем токен с подробным логом
    try:
        payload = decode_token(token)
    except Exception as e:
        log.warning("ws_decode_failed", error=str(e), token_prefix=token[:24])
        try:
            await ws.send_json({"type": "error", "detail": f"decode_failed: {e}"})
        except Exception:
            pass
        await ws.close(code=4401)
        return

    if payload.get("type") != "access":
        log.warning("ws_wrong_token_type", got_type=payload.get("type"))
        try:
            await ws.send_json({"type": "error", "detail": f"wrong_token_type: {payload.get('type')}"})
        except Exception:
            pass
        await ws.close(code=4401)
        return

    try:
        user_id = int(payload["sub"])
    except Exception as e:
        log.warning("ws_bad_subject", error=str(e))
        try:
            await ws.send_json({"type": "error", "detail": f"bad_subject: {e}"})
        except Exception:
            pass
        await ws.close(code=4401)
        return

    # 3) Проверяем пользователя
    async with SessionLocal() as db:
        user = (await db.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()
        if user is None:
            log.warning("ws_user_not_found", user_id=user_id)
            try:
                await ws.send_json({"type": "error", "detail": "user_not_found"})
            except Exception:
                pass
            await ws.close(code=4401)
            return
        if not user.is_active:
            log.warning("ws_user_inactive", user_id=user_id)
            try:
                await ws.send_json({"type": "error", "detail": "user_inactive"})
            except Exception:
                pass
            await ws.close(code=4401)
            return
        username = user.username

    # 4) Регистрируем в менеджере (без повторного accept)
    await manager.register(user_id, ws)
    await ws.send_json({"type": "ready", "user_id": user_id})
    log.info("ws_connected", user_id=user_id, username=username)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            kind = data.get("type")

            if kind == "subscribe":
                manager.subscribe(ws, int(data["chat_id"]))
                await ws.send_json({"type": "subscribed", "chat_id": data["chat_id"]})

            elif kind == "unsubscribe":
                manager.unsubscribe(ws, int(data["chat_id"]))

            elif kind == "typing":
                chat_id = int(data["chat_id"])
                is_typing = bool(data.get("is_typing"))
                manager.set_typing(chat_id, user_id, is_typing)
                await manager.send_to_chat(
                    chat_id,
                    {
                        "type": "typing", "chat_id": chat_id,
                        "user_id": user_id, "username": username,
                        "is_typing": is_typing,
                    },
                    exclude_ws=ws,
                )

            elif kind == "send":
                chat_id = int(data["chat_id"])
                client_id = data.get("client_id")
                text = (data.get("text") or "").strip() or None
                reply_to_id = data.get("reply_to_id")
                attachment_id = data.get("attachment_id")
                message_type = data.get("message_type", "text")
                encrypted = bool(data.get("encrypted", False))

                if not text and not attachment_id:
                    continue

                async with SessionLocal() as db:
                    member = (await db.execute(
                        select(ChatMember).where(
                            ChatMember.chat_id == chat_id,
                            ChatMember.user_id == user_id,
                        )
                    )).scalar_one_or_none()
                    if member is None:
                        await ws.send_json({
                            "type": "error", "client_id": client_id,
                            "detail": "not a member",
                        })
                        continue

                    msg = Message(
                        chat_id=chat_id, author_id=user_id, text=text,
                        message_type=message_type,
                        attachment_id=attachment_id, reply_to_id=reply_to_id,
                        encrypted=encrypted,
                    )
                    db.add(msg)
                    await db.flush()
                    await db.refresh(msg)
                    member.last_read_message_id = msg.id
                    member.draft = None
                    await db.commit()
                    await cache.invalidate_chat_list(db, chat_id)

                    author = await _author_payload(db, user_id)
                    attachment = await _attachment_payload(db, attachment_id)

                    reply_preview = None
                    reply_author = None
                    if reply_to_id:
                        r = (await db.execute(
                            select(Message).where(Message.id == reply_to_id)
                        )).scalar_one_or_none()
                        if r:
                            if r.is_deleted:
                                reply_preview = "Сообщение удалено"
                            elif r.encrypted:
                                reply_preview = "🔒 encrypted"
                            elif r.message_type == "image":
                                reply_preview = "▣ IMAGE"
                            elif r.message_type == "voice":
                                reply_preview = "◍ AUDIO"
                            elif r.message_type == "file":
                                reply_preview = "▤ FILE"
                            elif r.message_type == "sticker":
                                reply_preview = r.text or "◈"
                            else:
                                reply_preview = (r.text or "")[:120]
                            ra = (await db.execute(
                                select(User).where(User.id == r.author_id)
                            )).scalar_one()
                            reply_author = ra.display_name or ra.username

                    payload_out = {
                        "type": "message", "id": msg.id, "chat_id": chat_id,
                        "client_id": client_id,
                        "text": text, "message_type": message_type,
                        "attachment": attachment,
                        "reply_to_id": reply_to_id,
                        "reply_preview": reply_preview, "reply_author": reply_author,
                        "edited_at": None, "is_deleted": False, "is_pinned": False,
                        "encrypted": encrypted,
                        "reactions": [],
                        "created_at": msg.created_at.isoformat(),
                        **author,
                    }
                    await manager.send_to_chat(chat_id, payload_out)

            elif kind == "edit":
                message_id = int(data["message_id"])
                text = str(data.get("text", "")).strip()
                encrypted = bool(data.get("encrypted", False))
                if not text:
                    continue
                async with SessionLocal() as db:
                    m = (await db.execute(
                        select(Message).where(Message.id == message_id)
                    )).scalar_one_or_none()
                    if m is None or m.author_id != user_id:
                        continue
                    m.text = text
                    m.edited_at = datetime.now(timezone.utc)
                    m.encrypted = encrypted
                    await db.commit()
                    await cache.invalidate_chat_list(db, m.chat_id)
                    await manager.send_to_chat(m.chat_id, {
                        "type": "message_edited", "message_id": m.id,
                        "chat_id": m.chat_id, "text": text,
                        "encrypted": encrypted,
                        "edited_at": m.edited_at.isoformat(),
                    })

            elif kind == "delete":
                message_id = int(data["message_id"])
                async with SessionLocal() as db:
                    m = (await db.execute(
                        select(Message).where(Message.id == message_id)
                    )).scalar_one_or_none()
                    if m is None or m.author_id != user_id:
                        continue
                    m.is_deleted = True
                    m.text = ""
                    await db.commit()
                    await cache.invalidate_chat_list(db, m.chat_id)
                    await manager.send_to_chat(m.chat_id, {
                        "type": "message_deleted", "message_id": m.id,
                        "chat_id": m.chat_id,
                    })

            elif kind == "reaction":
                message_id = int(data["message_id"])
                emoji = str(data.get("emoji", "")).strip()
                if not emoji:
                    continue
                async with SessionLocal() as db:
                    m = (await db.execute(
                        select(Message).where(Message.id == message_id)
                    )).scalar_one_or_none()
                    if m is None:
                        continue
                    existing = (await db.execute(
                        select(MessageReaction).where(
                            MessageReaction.message_id == message_id,
                            MessageReaction.user_id == user_id,
                            MessageReaction.emoji == emoji,
                        )
                    )).scalar_one_or_none()
                    if existing:
                        await db.delete(existing)
                    else:
                        db.add(MessageReaction(
                            message_id=message_id, user_id=user_id, emoji=emoji,
                        ))
                    await db.commit()

                    rows = (await db.execute(
                        select(MessageReaction).where(
                            MessageReaction.message_id == message_id
                        )
                    )).scalars().all()
                    grouped: dict[str, dict] = {}
                    for r in rows:
                        g = grouped.setdefault(r.emoji, {"count": 0, "mine": False})
                        g["count"] += 1
                        if r.user_id == user_id:
                            g["mine"] = True
                    reactions = [
                        {"emoji": e, "count": v["count"], "is_mine": v["mine"]}
                        for e, v in sorted(grouped.items(), key=lambda x: -x[1]["count"])
                    ]
                    await manager.send_to_chat(m.chat_id, {
                        "type": "reactions", "message_id": message_id,
                        "chat_id": m.chat_id, "reactions": reactions,
                    })

            elif kind == "read":
                chat_id = int(data["chat_id"])
                message_id = int(data["message_id"])
                async with SessionLocal() as db:
                    member = (await db.execute(
                        select(ChatMember).where(
                            ChatMember.chat_id == chat_id,
                            ChatMember.user_id == user_id,
                        )
                    )).scalar_one_or_none()
                    if member:
                        member.last_read_message_id = message_id
                        await db.commit()
                await cache.invalidate_chat_list_for_user(user_id)
                await manager.send_to_chat(
                    chat_id,
                    {"type": "read", "chat_id": chat_id,
                     "user_id": user_id, "message_id": message_id},
                    exclude_ws=ws,
                )

            elif kind == "ping":
                await ws.send_json({"type": "pong"})

            elif kind in ("webrtc:offer", "webrtc:answer", "webrtc:ice", "webrtc:screen"):
                target_id = data.get("target_id")
                call_id = data.get("call_id")
                if not isinstance(target_id, int):
                    continue
                await manager.send_to_user(target_id, {
                    "type": kind, "call_id": call_id,
                    "from_id": user_id, "payload": data.get("payload"),
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error("ws_error", user_id=user_id, error=str(e), exc_info=True)
    finally:
        await manager.disconnect(ws)
        async with SessionLocal() as db:
            u = (await db.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
            if u:
                u.last_seen = datetime.now(timezone.utc)
                await db.commit()
        log.info("ws_disconnected", user_id=user_id)
'''


WS_MANAGER = r'''from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app import presence


class ConnectionManager:
    """Локальный менеджер + публикация presence в Redis."""

    def __init__(self) -> None:
        self._user_conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._chat_conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._ws_user: dict[WebSocket, int] = {}
        self._typing: dict[tuple[int, int], float] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        """Совместимость: принимает если ещё не принят, потом регистрирует."""
        if ws.client_state == WebSocketState.CONNECTING:
            await ws.accept()
        await self.register(user_id, ws)

    async def register(self, user_id: int, ws: WebSocket) -> None:
        """Только регистрирует уже принятое соединение."""
        self._user_conns[user_id].add(ws)
        self._ws_user[ws] = user_id
        await presence.mark_online(user_id)
        await presence.publish({"kind": "presence", "user_id": user_id, "online": True})

    async def disconnect(self, ws: WebSocket) -> int | None:
        user_id = self._ws_user.pop(ws, None)
        if user_id is None:
            return None
        self._user_conns.get(user_id, set()).discard(ws)
        if not self._user_conns.get(user_id):
            self._user_conns.pop(user_id, None)
            iso = datetime.now(timezone.utc).isoformat()
            await presence.mark_offline(user_id, iso)
            await presence.publish({
                "kind": "presence", "user_id": user_id,
                "online": False, "last_seen": iso,
            })
        for conns in self._chat_conns.values():
            conns.discard(ws)
        return user_id

    def is_online(self, user_id: int) -> bool:
        return bool(self._user_conns.get(user_id))

    def local_user_ids(self) -> list[int]:
        return list(self._user_conns.keys())

    def subscribe(self, ws: WebSocket, chat_id: int) -> None:
        self._chat_conns[chat_id].add(ws)

    def unsubscribe(self, ws: WebSocket, chat_id: int) -> None:
        self._chat_conns.get(chat_id, set()).discard(ws)

    def set_typing(self, chat_id: int, user_id: int, is_typing: bool) -> None:
        if is_typing:
            self._typing[(chat_id, user_id)] = datetime.now(timezone.utc).timestamp()
        else:
            self._typing.pop((chat_id, user_id), None)

    def typing_users(self, chat_id: int, exclude: int) -> list[int]:
        now = datetime.now(timezone.utc).timestamp()
        stale = [k for k, v in self._typing.items() if now - v > 4]
        for k in stale:
            self._typing.pop(k, None)
        return [uid for (cid, uid) in self._typing if cid == chat_id and uid != exclude]

    async def send_to_user(self, user_id: int, message: dict) -> None:
        for ws in list(self._user_conns.get(user_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)

    async def send_to_chat(self, chat_id: int, message: dict, exclude_ws: WebSocket | None = None) -> None:
        for ws in list(self._chat_conns.get(chat_id, ())):
            if ws is exclude_ws:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)

    async def broadcast_local(self, message: dict) -> None:
        for user_id in list(self._user_conns.keys()):
            await self.send_to_user(user_id, message)

    async def broadcast_all(self, message: dict) -> None:
        await presence.publish({"kind": "broadcast", "message": message})
        await self.broadcast_local(message)

    async def close_all(self) -> None:
        for user_conns in list(self._user_conns.values()):
            for ws in list(user_conns):
                try:
                    await ws.close()
                finally:
                    await self.disconnect(ws)


manager = ConnectionManager()
'''


WS_TS = r'''import { useEffect, useRef, useState, useCallback } from "react";
import { WS_BASE } from "./api";

type Handler = (data: any) => void;

export interface WsState {
  readyState: number;
  lastError: string | null;
}

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
      if (e.code !== 1000) {
        console.warn("[ws] closed", e.code, e.reason);
      }
      if (!cancelledRef.current) {
        reconnectRef.current = window.setTimeout(connect, 2000);
      }
    };
    ws.onerror = () => {
      // не закрываем сразу, пусть onclose обработает
    };
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        if (d.type === "error") {
          console.warn("[ws] server error:", d.detail);
          setLastError(d.detail || "unknown error");
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 14 — диагностика и фикс WS 403\n")

    backend = root / "backend" / "app"
    (backend / "routers" / "ws.py").write_text(WS_PY, encoding="utf-8")
    print(f"  ~ {backend / 'routers' / 'ws.py'}")

    (backend / "websocket_manager.py").write_text(WS_MANAGER, encoding="utf-8")
    print(f"  ~ {backend / 'websocket_manager.py'}")

    frontend = root / "frontend" / "src"
    (frontend / "ws.ts").write_text(WS_TS, encoding="utf-8")
    print(f"  ~ {frontend / 'ws.ts'}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache api")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("После перезапуска открой http://localhost:5173 и посмотри:")
    print("  1) в консоли браузера (F12) — что пишет [ws] closed");
    print("  2) в логах api: docker compose logs -f api | grep ws_")
    print()
    print("Скорее всего увидишь ws_decode_failed — тогда проблема в SECRET_KEY.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())