#!/usr/bin/env python3
"""sprint28_fixes.py - critical fixes with automatic backup.

Fixes:
  1. Permission checks (can_post/can_comment/can_pin) в messages.py, ws.py, tools.py
  2. Multi-worker: send_to_chat через Redis pub/sub
  3. files.py: проверка доступа при download + async S3 (не блокирует event loop)
  4. s3.py: addressing_style=path (Yandex не работает с virtual)
  5. users.py: presence — исправлена логика show_last_seen
  6. chats.py: стабильный avatar_color (md5 вместо рандомного hash)
  7. auth.py: race condition в refresh (сначала store, потом revoke)
  8. network.py: unread считает непрочитанные, а не все
  9. dead_drops.py: проверка can_post при создании

Backup: создаёт _backup_YYYYMMDD_HHMMSS/ со всеми изменяемыми файлами.
Restore: --restore <путь_к_бэкапу>

Usage:
    python sprint28_fixes.py --path . --name my-messenger
    python sprint28_fixes.py --path . --name my-messenger --restore _backup_20250101_120000
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ============================================================
# FILES TO BACKUP
# ============================================================
FILES_TO_BACKUP = [
    "backend/app/main.py",
    "backend/app/websocket_manager.py",
    "backend/app/routers/ws.py",
    "backend/app/routers/messages.py",
    "backend/app/routers/tools.py",
    "backend/app/routers/files.py",
    "backend/app/routers/users.py",
    "backend/app/routers/chats.py",
    "backend/app/routers/auth.py",
    "backend/app/routers/network.py",
    "backend/app/routers/dead_drops.py",
    "backend/app/utils/s3.py",
    "backend/app/router.py",
]


# ============================================================
# WEBSOCKET MANAGER — full rewrite (Redis pub/sub для чатов)
# ============================================================
WS_MANAGER = r'''from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app import presence


class ConnectionManager:
    """Локальный менеджер + Redis pub/sub для межворкерной доставки."""

    def __init__(self) -> None:
        self._user_conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._chat_conns: dict[int, set[WebSocket]] = defaultdict(set)
        self._ws_user: dict[WebSocket, int] = {}
        self._typing: dict[tuple[int, int], float] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        if ws.client_state == WebSocketState.CONNECTING:
            await ws.accept()
        await self.register(user_id, ws)

    async def register(self, user_id: int, ws: WebSocket) -> None:
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

    # --- локальная доставка (не публикует) ---

    async def send_to_user_local(self, user_id: int, message: dict) -> None:
        for ws in list(self._user_conns.get(user_id, ())):
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)

    async def send_to_chat_local(
        self,
        chat_id: int,
        message: dict,
        exclude_user_id: int | None = None,
    ) -> None:
        for ws in list(self._chat_conns.get(chat_id, ())):
            uid = self._ws_user.get(ws)
            if uid == exclude_user_id:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                await self.disconnect(ws)

    async def broadcast_local(self, message: dict) -> None:
        for user_id in list(self._user_conns.keys()):
            await self.send_to_user_local(user_id, message)

    # --- публикация через Redis (для других воркеров) ---

    async def send_to_chat(
        self,
        chat_id: int,
        message: dict,
        exclude_user_id: int | None = None,
    ) -> None:
        """Публикует в Redis. Все воркеры, включая свой, доставят через подписчика."""
        await presence.publish({
            "kind": "chat_message",
            "chat_id": chat_id,
            "exclude_user_id": exclude_user_id,
            "message": message,
        })

    async def send_to_user(self, user_id: int, message: dict) -> None:
        """Публикует в Redis для конкретного пользователя."""
        await presence.publish({
            "kind": "user_message",
            "user_id": user_id,
            "message": message,
        })

    async def broadcast_all(self, message: dict) -> None:
        await presence.publish({"kind": "broadcast", "message": message})

    async def close_all(self) -> None:
        for user_conns in list(self._user_conns.values()):
            for ws in list(user_conns):
                try:
                    await ws.close()
                finally:
                    await self.disconnect(ws)


manager = ConnectionManager()
'''


# ============================================================
# S3 UTIL — path style + кеш ensure_bucket
# ============================================================
S3_UTIL = r'''"""S3-compatible storage helper."""
from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings

log = logging.getLogger("s3")

_client: Any = None
_bucket_checked = False


def client():
    global _client
    if _client is None:
        if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
            raise RuntimeError("S3_ACCESS_KEY / S3_SECRET_KEY не заданы в .env")
        _client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                # path-style обязателен для Yandex Object Storage,
                # VK Cloud и MinIO. AWS тоже поддерживает.
                s3={"addressing_style": "path"},
            ),
        )
    return _client


def ensure_bucket() -> None:
    """Создаёт бакет если его нет. Выполняется один раз за жизнь процесса."""
    global _bucket_checked
    if _bucket_checked:
        return
    try:
        c = client()
        c.head_bucket(Bucket=settings.S3_BUCKET)
        _bucket_checked = True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            try:
                c.create_bucket(Bucket=settings.S3_BUCKET)
                log.info("s3_bucket_created bucket=%s", settings.S3_BUCKET)
                _bucket_checked = True
            except Exception as e2:
                log.warning("s3_create_bucket_failed error=%s", e2)
        elif code == "403":
            # Бакет есть, но нет прав на head. Помечаем как "проверено" —
            # дальше put/delete сами покажут реальную ошибку.
            _bucket_checked = True
        else:
            log.warning("s3_head_bucket_failed error=%s", e)
    except Exception as e:
        log.warning("s3_ensure_bucket_failed error=%s", e)


def put_object(key: str, body: bytes, content_type: str) -> None:
    client().put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def delete_object(key: str) -> None:
    try:
        client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except Exception as e:
        log.warning("s3_delete_failed key=%s error=%s", key, e)


def presigned_url(key: str, expires: int | None = None) -> str:
    ttl = expires or settings.S3_PRESIGN_EXPIRE
    return client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=ttl,
    )


def get_object_bytes(key: str) -> bytes:
    obj = client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    return obj["Body"].read()


def object_exists(key: str) -> bool:
    try:
        client().head_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False
    except Exception:
        return False
'''


# ============================================================
# PATCHES — (old, new) для str.replace
# ============================================================

PATCHES: dict[str, list[tuple[str, str]]] = {}


# ---------- main.py: обработчик chat_message / user_message ----------
PATCHES["backend/app/main.py"] = [
    (
        '        elif kind == "presence":\n'
        '            await manager.broadcast_local({',
        '        elif kind == "chat_message":\n'
        '            await manager.send_to_chat_local(\n'
        '                event["chat_id"],\n'
        '                event["message"],\n'
        '                exclude_user_id=event.get("exclude_user_id"),\n'
        '            )\n'
        '        elif kind == "user_message":\n'
        '            await manager.send_to_user_local(\n'
        '                event["user_id"],\n'
        '                event["message"],\n'
        '            )\n'
        '        elif kind == "presence":\n'
        '            await manager.broadcast_local({',
    ),
]


# ---------- ws.py: permissions + exclude_user_id ----------
PATCHES["backend/app/routers/ws.py"] = [
    # imports
    (
        'from app.models import Chat, ChatMember, File as FileModel, Message, MessageReaction, User\n'
        'from app.security import decode_token\n',
        'from app.models import Chat, ChatMember, File as FileModel, Message, MessageReaction, User\n'
        'from app.permissions import get_permissions\n'
        'from app.security import decode_token\n',
    ),
    # exclude_ws → exclude_user_id (typing)
    (
        '                    await manager.send_to_chat(\n'
        '                        chat_id,\n'
        '                        {"type": "typing", "chat_id": chat_id,\n'
        '                         "user_id": user_id, "username": username,\n'
        '                         "is_typing": is_typing},\n'
        '                        exclude_ws=ws,\n'
        '                    )',
        '                    await manager.send_to_chat(\n'
        '                        chat_id,\n'
        '                        {"type": "typing", "chat_id": chat_id,\n'
        '                         "user_id": user_id, "username": username,\n'
        '                         "is_typing": is_typing},\n'
        '                        exclude_user_id=user_id,\n'
        '                    )',
    ),
    # exclude_ws → exclude_user_id (read)
    (
        '                await manager.send_to_chat(\n'
        '                    chat_id,\n'
        '                    {"type": "read", "chat_id": chat_id,\n'
        '                     "user_id": user_id, "message_id": message_id},\n'
        '                    exclude_ws=ws,\n'
        '                )',
        '                await manager.send_to_chat(\n'
        '                    chat_id,\n'
        '                    {"type": "read", "chat_id": chat_id,\n'
        '                     "user_id": user_id, "message_id": message_id},\n'
        '                    exclude_user_id=user_id,\n'
        '                )',
    ),
    # permission check в send
    (
        '                    if member is None:\n'
        '                        await ws.send_json({"type": "error", "client_id": client_id, "detail": "not a member"})\n'
        '                        continue\n'
        '\n'
        '                    chat = (await db.execute(',
        '                    if member is None:\n'
        '                        await ws.send_json({"type": "error", "client_id": client_id, "detail": "not a member"})\n'
        '                        continue\n'
        '\n'
        '                    _perms = get_permissions(member.role, member.permissions)\n'
        '                    if not _perms.get("can_post"):\n'
        '                        await ws.send_json({\n'
        '                            "type": "error", "client_id": client_id,\n'
        '                            "detail": "no permission: can_post",\n'
        '                        })\n'
        '                        continue\n'
        '\n'
        '                    chat = (await db.execute(',
    ),
    # permission check в reaction
    (
        '                    m = (await db.execute(\n'
        '                        select(Message).where(Message.id == message_id)\n'
        '                    )).scalar_one_or_none()\n'
        '                    if m is None:\n'
        '                        continue\n'
        '                    existing = (await db.execute(\n'
        '                        select(MessageReaction).where(',
        '                    m = (await db.execute(\n'
        '                        select(Message).where(Message.id == message_id)\n'
        '                    )).scalar_one_or_none()\n'
        '                    if m is None:\n'
        '                        continue\n'
        '                    _rmem = (await db.execute(\n'
        '                        select(ChatMember).where(\n'
        '                            ChatMember.chat_id == m.chat_id,\n'
        '                            ChatMember.user_id == user_id,\n'
        '                        )\n'
        '                    )).scalar_one_or_none()\n'
        '                    if _rmem is None:\n'
        '                        continue\n'
        '                    _rperms = get_permissions(_rmem.role, _rmem.permissions)\n'
        '                    if not _rperms.get("can_comment"):\n'
        '                        continue\n'
        '                    existing = (await db.execute(\n'
        '                        select(MessageReaction).where(',
    ),
]


# ---------- messages.py: permission checks ----------
PATCHES["backend/app/routers/messages.py"] = [
    # import
    (
        'from app.models import ChatMember, File as FileModel, Message, MessageReaction, User\n',
        'from app.models import ChatMember, File as FileModel, Message, MessageReaction, User\n'
        'from app.permissions import get_permissions\n',
    ),
    # helper
    (
        'async def _ensure_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember:\n'
        '    m = (await db.execute(\n'
        '        select(ChatMember).where(\n'
        '            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id\n'
        '        )\n'
        '    )).scalar_one_or_none()\n'
        '    if m is None:\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")\n'
        '    return m\n',
        'async def _ensure_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember:\n'
        '    m = (await db.execute(\n'
        '        select(ChatMember).where(\n'
        '            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id\n'
        '        )\n'
        '    )).scalar_one_or_none()\n'
        '    if m is None:\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")\n'
        '    return m\n'
        '\n'
        '\n'
        'async def _ensure_permission(\n'
        '    db: AsyncSession, chat_id: int, user_id: int, perm: str\n'
        ') -> ChatMember:\n'
        '    m = await _ensure_member(db, chat_id, user_id)\n'
        '    perms = get_permissions(m.role, m.permissions)\n'
        '    if not perms.get(perm):\n'
        '        raise HTTPException(\n'
        '            status.HTTP_403_FORBIDDEN, f"missing permission: {perm}"\n'
        '        )\n'
        '    return m\n',
    ),
    # send_message
    (
        '    await _ensure_member(db, chat_id, current.id)\n'
        '    if not (payload.text or payload.attachment_id):\n'
        '        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty message")',
        '    await _ensure_permission(db, chat_id, current.id, "can_post")\n'
        '    if not (payload.text or payload.attachment_id):\n'
        '        raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty message")',
    ),
    # toggle_reaction
    (
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_member(db, msg.chat_id, current.id)\n'
        '\n'
        '    existing = (await db.execute(\n'
        '        select(MessageReaction).where(',
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_permission(db, msg.chat_id, current.id, "can_comment")\n'
        '\n'
        '    existing = (await db.execute(\n'
        '        select(MessageReaction).where(',
    ),
    # pin_message
    (
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_member(db, msg.chat_id, current.id)\n'
        '    msg.is_pinned = True',
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_permission(db, msg.chat_id, current.id, "can_pin")\n'
        '    msg.is_pinned = True',
    ),
    # unpin_message
    (
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_member(db, msg.chat_id, current.id)\n'
        '    msg.is_pinned = False',
        '    if msg is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")\n'
        '    await _ensure_permission(db, msg.chat_id, current.id, "can_pin")\n'
        '    msg.is_pinned = False',
    ),
]


# ---------- tools.py: can_comment вместо can_post ----------
PATCHES["backend/app/routers/tools.py"] = [
    (
        '    # perm check: can_post required to edit\n'
        '    perms = get_permissions(m.role, m.permissions)\n'
        '    if not perms.get("can_post"):\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "no permission to edit tools")',
        '    # perm check: can_comment — гость канала тоже может править вики\n'
        '    perms = get_permissions(m.role, m.permissions)\n'
        '    if not perms.get("can_comment"):\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "no permission to edit tools")',
    ),
]


# ---------- files.py: async S3 + проверка доступа ----------
PATCHES["backend/app/routers/files.py"] = [
    # imports
    (
        'from __future__ import annotations\n'
        '\n'
        'import uuid\n'
        'from pathlib import Path\n',
        'from __future__ import annotations\n'
        '\n'
        'import asyncio\n'
        'import uuid\n'
        'from pathlib import Path\n',
    ),
    (
        'from app.models import File as FileModel, FileUsage\n',
        'from app.models import ChatMember, File as FileModel, FileUsage, Message, Post\n',
    ),
    # upload: блокирующий S3 в потоке
    (
        '    if settings.S3_ENABLED:\n'
        '        try:\n'
        '            s3.ensure_bucket()\n'
        '            s3.put_object(key, body, detected_mime)\n'
        '            log.info("s3_upload_ok", key=key, size=len(body), mime=detected_mime)\n'
        '        except Exception as e:\n'
        '            log.error("s3_upload_failed", key=key, error=str(e))\n'
        '            raise HTTPException(\n'
        '                status.HTTP_502_BAD_GATEWAY,\n'
        '                f"Не удалось сохранить файл в S3: {e}",\n'
        '            )',
        '    if settings.S3_ENABLED:\n'
        '        try:\n'
        '            await asyncio.to_thread(s3.ensure_bucket)\n'
        '            await asyncio.to_thread(s3.put_object, key, body, detected_mime)\n'
        '            log.info("s3_upload_ok", key=key, size=len(body), mime=detected_mime)\n'
        '        except Exception as e:\n'
        '            log.error("s3_upload_failed", key=key, error=str(e))\n'
        '            raise HTTPException(\n'
        '                status.HTTP_502_BAD_GATEWAY,\n'
        '                f"Не удалось сохранить файл в S3: {e}",\n'
        '            )',
    ),
    # delete: async S3
    (
        '    if settings.S3_ENABLED:\n'
        '        s3.delete_object(obj.storage_name)\n'
        '    else:\n'
        '        path = settings.upload_path / Path(obj.storage_name).name\n'
        '        path.unlink(missing_ok=True)',
        '    if settings.S3_ENABLED:\n'
        '        await asyncio.to_thread(s3.delete_object, obj.storage_name)\n'
        '    else:\n'
        '        path = settings.upload_path / Path(obj.storage_name).name\n'
        '        path.unlink(missing_ok=True)',
    ),
    # download: проверка доступа + async presign
    (
        '    try:\n'
        '        decode_token(token)\n'
        '    except ValueError:\n'
        '        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")\n'
        '\n'
        '    obj = (await db.execute(\n'
        '        select(FileModel).where(FileModel.id == file_id)\n'
        '    )).scalar_one_or_none()\n'
        '    if obj is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")\n'
        '\n'
        '    # fallback: если файл лежит локально (старые загрузки), отдаём с диска\n'
        '    local_name = Path(obj.storage_name).name\n'
        '    local_path = settings.upload_path / local_name\n'
        '    if local_path.exists():\n'
        '        inline = obj.content_type.startswith(("image/", "audio/", "video/"))\n'
        '        return FileResponse(\n'
        '            local_path,\n'
        '            media_type=obj.content_type,\n'
        '            filename=obj.filename,\n'
        '            content_disposition_type="inline" if inline else "attachment",\n'
        '        )\n'
        '\n'
        '    if not settings.S3_ENABLED:\n'
        '        raise HTTPException(status.HTTP_410_GONE, "file missing on disk")\n'
        '\n'
        '    # Основной путь: редирект на presigned S3 URL\n'
        '    try:\n'
        '        url = s3.presigned_url(obj.storage_name)\n'
        '    except Exception as e:\n'
        '        log.error("s3_presign_failed", key=obj.storage_name, error=str(e))\n'
        '        raise HTTPException(\n'
        '            status.HTTP_502_BAD_GATEWAY,\n'
        '            f"Не удалось получить ссылку на файл: {e}",\n'
        '        )\n'
        '\n'
        '    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)',
        '    try:\n'
        '        payload = decode_token(token)\n'
        '        user_id = int(payload["sub"])\n'
        '    except (ValueError, KeyError):\n'
        '        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")\n'
        '\n'
        '    obj = (await db.execute(\n'
        '        select(FileModel).where(FileModel.id == file_id)\n'
        '    )).scalar_one_or_none()\n'
        '    if obj is None:\n'
        '        raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")\n'
        '\n'
        '    # --- Проверка доступа ---\n'
        '    # 1. Владелец — всегда.\n'
        '    # 2. Иначе — файл должен быть вложен в сообщение, к чату которого есть доступ.\n'
        '    # 3. Иначе — файл должен быть в посту (публичный доступ).\n'
        '    allowed = obj.owner_id == user_id\n'
        '    if not allowed:\n'
        '        msg_row = (await db.execute(\n'
        '            select(Message).where(Message.attachment_id == file_id).limit(1)\n'
        '        )).scalar_one_or_none()\n'
        '        if msg_row is not None:\n'
        '            member = (await db.execute(\n'
        '                select(ChatMember).where(\n'
        '                    ChatMember.chat_id == msg_row.chat_id,\n'
        '                    ChatMember.user_id == user_id,\n'
        '                )\n'
        '            )).scalar_one_or_none()\n'
        '            allowed = member is not None\n'
        '        if not allowed:\n'
        '            post_row = (await db.execute(\n'
        '                select(Post).where(Post.attachment_id == file_id).limit(1)\n'
        '            )).scalar_one_or_none()\n'
        '            if post_row is not None:\n'
        '                allowed = True\n'
        '    if not allowed:\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "no access to file")\n'
        '\n'
        '    # fallback: если файл лежит локально (старые загрузки), отдаём с диска\n'
        '    local_name = Path(obj.storage_name).name\n'
        '    local_path = settings.upload_path / local_name\n'
        '    if local_path.exists():\n'
        '        inline = obj.content_type.startswith(("image/", "audio/", "video/"))\n'
        '        return FileResponse(\n'
        '            local_path,\n'
        '            media_type=obj.content_type,\n'
        '            filename=obj.filename,\n'
        '            content_disposition_type="inline" if inline else "attachment",\n'
        '        )\n'
        '\n'
        '    if not settings.S3_ENABLED:\n'
        '        raise HTTPException(status.HTTP_410_GONE, "file missing on disk")\n'
        '\n'
        '    # Основной путь: редирект на presigned S3 URL\n'
        '    try:\n'
        '        url = await asyncio.to_thread(s3.presigned_url, obj.storage_name)\n'
        '    except Exception as e:\n'
        '        log.error("s3_presign_failed", key=obj.storage_name, error=str(e))\n'
        '        raise HTTPException(\n'
        '            status.HTTP_502_BAD_GATEWAY,\n'
        '            f"Не удалось получить ссылку на файл: {e}",\n'
        '        )\n'
        '\n'
        '    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)',
    ),
]


# ---------- users.py: presence fix ----------
PATCHES["backend/app/routers/users.py"] = [
    (
        '    online = await presence.is_online(user_id)\n'
        '    last_seen = await presence.get_last_seen(user_id)\n'
        '    # deep_scan — показывает last_seen только тем, у кого включён\n'
        '    show_last_seen = current.chrome_deep_scan or (last_seen is None and not online)\n'
        '    return {\n'
        '        "user_id": user_id,\n'
        '        "online": online,\n'
        '        "last_seen": last_seen if show_last_seen else None,\n'
        '    }',
        '    online = await presence.is_online(user_id)\n'
        '    last_seen = await presence.get_last_seen(user_id)\n'
        '    # deep_scan — владелец видит свой last_seen и last_seen тех, кому разрешено\n'
        '    show_last_seen = bool(current.chrome_deep_scan) or user_id == current.id\n'
        '    return {\n'
        '        "user_id": user_id,\n'
        '        "online": online,\n'
        '        "last_seen": last_seen if show_last_seen else None,\n'
        '    }',
    ),
]


# ---------- chats.py: стабильный avatar_color ----------
PATCHES["backend/app/routers/chats.py"] = [
    (
        'from __future__ import annotations\n'
        '\n'
        'import json\n'
        'import secrets\n',
        'from __future__ import annotations\n'
        '\n'
        'import hashlib\n'
        'import secrets\n',
    ),
    (
        '    color = None\n'
        '    if payload.is_group or payload.is_channel:\n'
        '        color = GROUP_COLORS[hash(payload.title or "g") % len(GROUP_COLORS)]',
        '    color = None\n'
        '    if payload.is_group or payload.is_channel:\n'
        '        # Стабильный цвет (hash() в Python рандомизирован между запусками)\n'
        '        h = hashlib.md5((payload.title or "g").encode("utf-8")).hexdigest()\n'
        '        color = GROUP_COLORS[int(h, 16) % len(GROUP_COLORS)]',
    ),
]


# ---------- auth.py: race condition в refresh ----------
PATCHES["backend/app/routers/auth.py"] = [
    (
        '    # ротация: старый отзываем, выдаём новый\n'
        '    await _revoke_refresh(jti)\n'
        '    access = create_access_token(user.id)\n'
        '    new_refresh, new_jti = create_refresh_token(user.id)\n'
        '    await _store_refresh(new_jti, user.id)',
        '    # Ротация: сначала сохраняем новый, потом отзываем старый.\n'
        '    # Если процесс упадёт в середине — пользователь остаётся с одним\n'
        '    # живым токеном, а не с нулём.\n'
        '    access = create_access_token(user.id)\n'
        '    new_refresh, new_jti = create_refresh_token(user.id)\n'
        '    await _store_refresh(new_jti, user.id)\n'
        '    await _revoke_refresh(jti)',
    ),
]


# ---------- network.py: правильный unread ----------
PATCHES["backend/app/routers/network.py"] = [
    # import: or_ нужен, сейчас есть
    (
        '    # unread counts (грубо: одно значение на чат)\n'
        '    unread_stmt = (\n'
        '        select(Message.chat_id, func.count(Message.id))\n'
        '        .where(\n'
        '            Message.chat_id.in_(chat_ids or [0]),\n'
        '            Message.author_id != current.id,\n'
        '        )\n'
        '        .group_by(Message.chat_id)\n'
        '    )\n'
        '    unread_map = {cid: int(cnt or 0) for cid, cnt in (await db.execute(unread_stmt)).all()}',
        '    # Unread counts — только сообщения после last_read_message_id\n'
        '    unread_stmt = (\n'
        '        select(Message.chat_id, func.count(Message.id))\n'
        '        .join(\n'
        '            ChatMember,\n'
        '            (ChatMember.chat_id == Message.chat_id)\n'
        '            & (ChatMember.user_id == current.id),\n'
        '        )\n'
        '        .where(\n'
        '            Message.chat_id.in_(chat_ids or [0]),\n'
        '            Message.author_id != current.id,\n'
        '            or_(\n'
        '                ChatMember.last_read_message_id.is_(None),\n'
        '                Message.id > ChatMember.last_read_message_id,\n'
        '            ),\n'
        '        )\n'
        '        .group_by(Message.chat_id)\n'
        '    )\n'
        '    unread_map = {cid: int(cnt or 0) for cid, cnt in (await db.execute(unread_stmt)).all()}',
    ),
]


# ---------- dead_drops.py: permission check ----------
PATCHES["backend/app/routers/dead_drops.py"] = [
    (
        'from app.models import ChatMember, DeadDrop\n'
        'from app.schemas import DeadDropCreate, DeadDropRead\n',
        'from app.models import ChatMember, DeadDrop\n'
        'from app.permissions import get_permissions\n'
        'from app.schemas import DeadDropCreate, DeadDropRead\n',
    ),
    (
        '    if m is None:\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")\n'
        '\n'
        '    if payload.trigger_type not in ("datetime", "offline"):',
        '    if m is None:\n'
        '        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")\n'
        '    perms = get_permissions(m.role, m.permissions)\n'
        '    if not perms.get("can_post"):\n'
        '        raise HTTPException(\n'
        '            status.HTTP_403_FORBIDDEN, "no permission: can_post"\n'
        '        )\n'
        '\n'
        '    if payload.trigger_type not in ("datetime", "offline"):',
    ),
]


# ============================================================
# BACKUP / RESTORE
# ============================================================

def create_backup(root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for rel in FILES_TO_BACKUP:
        src = root / rel
        if not src.exists():
            continue
        dst = backup / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(rel)
    (backup / "MANIFEST.txt").write_text(
        f"Backup created: {ts}\nFiles: {len(copied)}\n\n" + "\n".join(copied) + "\n",
        encoding="utf-8",
    )
    return backup


def restore_backup(root: Path, backup: Path) -> int:
    if not backup.exists():
        print(f"ERR: {backup} не найдено", file=sys.stderr)
        return 0
    count = 0
    for src in backup.rglob("*"):
        if not src.is_file() or src.name == "MANIFEST.txt":
            continue
        rel = src.relative_to(backup)
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"  ← {rel}")
        count += 1
    return count


# ============================================================
# APPLY
# ============================================================

def apply_patch(path: Path, pairs: list[tuple[str, str]]) -> tuple[int, int]:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0, len(pairs)
    text = path.read_text(encoding="utf-8")
    ok = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            ok += 1
    if ok:
        path.write_text(text, encoding="utf-8")
    status = "OK" if ok == len(pairs) else "ЧАСТИЧНО"
    print(f"  ~ {path} [{status} {ok}/{len(pairs)}]")
    return ok, len(pairs)


def main() -> int:
    p = argparse.ArgumentParser(description="sprint28 fixes + backup")
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-backup", action="store_true",
                   help="пропустить создание бэкапа (не рекомендуется)")
    p.add_argument("--restore", default=None,
                   help="путь к бэкап-папке для отката (относительно корня проекта)")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    # --- RESTORE MODE ---
    if args.restore:
        backup = (root / args.restore).resolve()
        if not backup.exists():
            backup = Path(args.restore).resolve()
        print(f"\nОткат из {backup}\n")
        n = restore_backup(root, backup)
        print(f"\nВосстановлено файлов: {n}\n")
        return 0

    # --- BACKUP ---
    backup_dir: Path | None = None
    if not args.no_backup:
        backup_dir = create_backup(root)
        print(f"\n📦 Бэкап: {backup_dir}")
        print(f"   (откат: python sprint28_fixes.py --path . --name {args.name} "
              f"--restore {backup_dir.name})\n")

    # --- FULL REWRITES ---
    print("Полные перезаписи:")
    rewrites = {
        "backend/app/websocket_manager.py": WS_MANAGER,
        "backend/app/utils/s3.py": S3_UTIL,
    }
    for rel, content in rewrites.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content, encoding="utf-8")
        print(f"  {'~' if existed else '+'} {target}")

    # --- PATCHES ---
    print("\nПатчи:")
    summary: list[tuple[str, int, int]] = []
    for rel, pairs in PATCHES.items():
        ok, total = apply_patch(root / rel, pairs)
        summary.append((rel, ok, total))

    # --- DELETE OBSOLETE ---
    print("\nУдаление:")
    obsolete = root / "backend" / "app" / "router.py"
    if obsolete.exists():
        obsolete.unlink()
        print(f"  ✕ {obsolete}")
    else:
        print(f"  · router.py уже удалён")

    # --- REPORT ---
    print("\n" + "=" * 60)
    print("ОТЧЁТ")
    print("=" * 60)
    total_ok = 0
    total_need = 0
    for rel, ok, total in summary:
        marker = "✓" if ok == total else ("◐" if ok > 0 else "✕")
        print(f"  {marker} {rel}: {ok}/{total}")
        total_ok += ok
        total_need += total
    print(f"\nИтого патчей: {total_ok}/{total_need}")

    if backup_dir:
        print(f"\n📦 Бэкап сохранён: {backup_dir}")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml build --no-cache api")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("Если что-то сломалось — откат:")
    print(f"  python sprint28_fixes.py --path . --name {args.name} "
          f"--restore {backup_dir.name if backup_dir else '_backup_XXX'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())