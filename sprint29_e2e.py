#!/usr/bin/env python3
"""sprint29_e2e.py - end-to-end encryption (DM + groups).

Архитектура:
  * DM: ECDH(P-256) между двумя участниками → AES-256-GCM
  * Группы: owner генерирует случайный chatKey,
    шифрует его публичным ключом каждого участника (через ECDH),
    сервер хранит только шифртексты. Расшифровать может только участник.

Backend:
  * Message.encrypted, Chat.encryption_enabled, ChatMember.encrypted_chat_key
  * Миграция 0012
  * Router /keys (upload/get public key)
  * Router /chats/{id}/encryption/* (enable, distribute keys, get my key)
  * WS: пробрасывает encrypted флаг, reply preview = "🔒"

Frontend:
  * WebCrypto: ECDH + AES-GCM
  * IndexedDB: хранение приватного ключа
  * useE2E hook
  * Интеграция в ChatWindow + индикаторы
  * E2ESetupModal — owner включает шифрование

Usage:
    python sprint29_e2e.py --path . --name my-messenger
    python sprint29_e2e.py --path . --name my-messenger --restore _backup_YYYYMMDD_HHMMSS
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


FILES_TO_BACKUP = [
    "backend/app/models.py",
    "backend/app/schemas.py",
    "backend/app/main.py",
    "backend/app/routers/chats.py",
    "backend/app/routers/messages.py",
    "backend/app/routers/ws.py",
    "frontend/src/types.ts",
    "frontend/src/ChatWindow.tsx",
    "frontend/src/App.tsx",
    "frontend/src/api.ts",
]


# ==============================================================
# BACKEND: миграция
# ==============================================================
ALEMBIC_0012 = '''"""sprint 29: e2e encryption

Revision ID: 0012
Revises: 0011
Create Date: 2025-09-21
"""
from __future__ import annotations
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "chats",
        sa.Column("encryption_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "chat_members",
        sa.Column("encrypted_chat_key", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_members", "encrypted_chat_key")
    op.drop_column("chats", "encryption_enabled")
    op.drop_column("messages", "encrypted")
'''


# ==============================================================
# BACKEND: patches
# ==============================================================
PATCHES: dict[str, list[tuple[str, str]]] = {}

# -------- models.py --------
PATCHES["backend/app/models.py"] = [
    # ChatMember: + encrypted_chat_key
    (
        '    role: Mapped[str] = mapped_column(String(20), default="member")\n'
        '    last_read_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)\n'
        '    draft: Mapped[str | None] = mapped_column(Text, nullable=True)\n'
        '    permissions: Mapped[str | None] = mapped_column(Text, nullable=True)',
        '    role: Mapped[str] = mapped_column(String(20), default="member")\n'
        '    last_read_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)\n'
        '    draft: Mapped[str | None] = mapped_column(Text, nullable=True)\n'
        '    permissions: Mapped[str | None] = mapped_column(Text, nullable=True)\n'
        '    encrypted_chat_key: Mapped[str | None] = mapped_column(Text, nullable=True)',
    ),
    # Chat: + encryption_enabled
    (
        '    is_dark_room: Mapped[bool] = mapped_column(Boolean, default=False)\n'
        '    is_channel: Mapped[bool] = mapped_column(Boolean, default=False)\n',
        '    is_dark_room: Mapped[bool] = mapped_column(Boolean, default=False)\n'
        '    is_channel: Mapped[bool] = mapped_column(Boolean, default=False)\n'
        '    encryption_enabled: Mapped[bool] = mapped_column(Boolean, default=False)\n',
    ),
    # Message: + encrypted
    (
        '    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n'
        '    created_at: Mapped[datetime] = mapped_column(',
        '    pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)\n'
        '    encrypted: Mapped[bool] = mapped_column(Boolean, default=False)\n'
        '    created_at: Mapped[datetime] = mapped_column(',
    ),
]


# -------- schemas.py --------
PATCHES["backend/app/schemas.py"] = [
    # MessageRead.encrypted
    (
        '    is_deleted: bool = False\n'
        '    is_pinned: bool = False\n'
        '    is_dead_drop: bool = False\n'
        '    reactions: list[ReactionRead] = Field(default_factory=list)\n'
        '    created_at: datetime',
        '    is_deleted: bool = False\n'
        '    is_pinned: bool = False\n'
        '    is_dead_drop: bool = False\n'
        '    encrypted: bool = False\n'
        '    reactions: list[ReactionRead] = Field(default_factory=list)\n'
        '    created_at: datetime',
    ),
    # ChatRead.encryption_enabled
    (
        '    firewall_enabled: bool = False\n'
        '    firewall_seconds: int = 60\n'
        '    is_dark_room: bool = False\n'
        '    auto_delete_at: datetime | None = None',
        '    firewall_enabled: bool = False\n'
        '    firewall_seconds: int = 60\n'
        '    is_dark_room: bool = False\n'
        '    auto_delete_at: datetime | None = None\n'
        '    encryption_enabled: bool = False\n'
        '    has_my_key: bool = False',
    ),
    # MessageCreate.encrypted + MessageEdit.encrypted
    (
        'class MessageCreate(BaseModel):\n'
        '    text: str | None = Field(default=None, max_length=8000)\n'
        '    message_type: str = "text"\n'
        '    attachment_id: int | None = None\n'
        '    reply_to_id: int | None = None\n'
        '    client_id: str | None = Field(default=None, max_length=64)',
        'class MessageCreate(BaseModel):\n'
        '    text: str | None = Field(default=None, max_length=8000)\n'
        '    message_type: str = "text"\n'
        '    attachment_id: int | None = None\n'
        '    reply_to_id: int | None = None\n'
        '    client_id: str | None = Field(default=None, max_length=64)\n'
        '    encrypted: bool = False',
    ),
    (
        'class MessageEdit(BaseModel):\n'
        '    text: str = Field(min_length=1, max_length=8000)',
        'class MessageEdit(BaseModel):\n'
        '    text: str = Field(min_length=1, max_length=8000)\n'
        '    encrypted: bool = False',
    ),
    # Новые схемы для ключей
    (
        'class PublicKeyUpload(BaseModel):\n'
        '    public_key: str = Field(min_length=10, max_length=2000)\n'
        '    algorithm: str = Field(default="ECDH-P256", max_length=30)',
        'class PublicKeyUpload(BaseModel):\n'
        '    public_key: str = Field(min_length=10, max_length=4000)\n'
        '    algorithm: str = Field(default="ECDH-P256", max_length=30)',
    ),
    (
        'class DeadDropCreate(BaseModel):',
        'class ChatKeyEntry(BaseModel):\n'
        '    user_id: int\n'
        '    encrypted_key: str = Field(min_length=10, max_length=8000)\n'
        '\n'
        '\n'
        'class ChatKeysBulk(BaseModel):\n'
        '    keys: list[ChatKeyEntry]\n'
        '\n'
        '\n'
        'class MyChatKeyRead(BaseModel):\n'
        '    encrypted_key: str | None = None\n'
        '    owner_id: int\n'
        '\n'
        '\n'
        'class EnableEncryptionRequest(BaseModel):\n'
        '    enabled: bool = True\n'
        '\n'
        '\n'
        'class DeadDropCreate(BaseModel):',
    ),
]


# -------- chats.py --------
CHATS_PATCHES = [
    # imports
    (
        'from app.schemas import (\n'
        '    AddMemberRequest, ChatCreate, ChatMemberRead, ChatRead, ChatUpdate,\n'
        '    DraftUpdate, FirewallUpdate, InviteRead, MessageRead, RoleUpdate, UserRead,\n'
        ')',
        'from app.schemas import (\n'
        '    AddMemberRequest, ChatCreate, ChatMemberRead, ChatRead, ChatUpdate,\n'
        '    ChatKeyEntry, ChatKeysBulk, DraftUpdate, EnableEncryptionRequest,\n'
        '    FirewallUpdate, InviteRead, MessageRead, MyChatKeyRead, RoleUpdate, UserRead,\n'
        ')',
    ),
    # _build_chat_read: добавить encryption_enabled + has_my_key
    (
        '    perms = get_permissions(membership.role, membership.permissions)\n'
        '\n'
        '    return ChatRead(',
        '    perms = get_permissions(membership.role, membership.permissions)\n'
        '    has_my_key = bool(membership.encrypted_chat_key)\n'
        '\n'
        '    return ChatRead(',
    ),
    (
        '        is_dark_room=chat.is_dark_room,\n'
        '        auto_delete_at=chat.auto_delete_at,\n'
        '    )',
        '        is_dark_room=chat.is_dark_room,\n'
        '        auto_delete_at=chat.auto_delete_at,\n'
        '        encryption_enabled=chat.encryption_enabled,\n'
        '        has_my_key=has_my_key,\n'
        '    )',
    ),
]

# Добавим новые эндпоинты в конец chats.py — как отдельный append
CHATS_APPEND = '''

# ============================================================
# E2E ENCRYPTION ENDPOINTS
# ============================================================

@router.post("/{chat_id}/encryption/enable", response_model=ChatRead)
async def enable_encryption(
    chat_id: int,
    payload: EnableEncryptionRequest,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    """Owner включает/выключает E2E для чата."""
    m = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
        )
    )).scalar_one_or_none()
    if m is None or m.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only owner can toggle encryption")
    chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")

    chat.encryption_enabled = payload.enabled

    if not payload.enabled:
        # при выключении — стираем разданные ключи у всех
        await db.execute(
            __import__("sqlalchemy").update(ChatMember)
            .where(ChatMember.chat_id == chat_id)
            .values(encrypted_chat_key=None)
        )

    await db.flush()
    await cache.invalidate_chat_list(db, chat_id)
    await db.refresh(m)
    return await _build_chat_read(db, chat, current.id, m)


@router.post("/{chat_id}/encryption/keys", status_code=204)
async def distribute_keys(
    chat_id: int,
    payload: ChatKeysBulk,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    """Owner/инициатор раздаёт зашифрованные chat_key каждому участнику.

    Сервер не может расшифровать их — только пересылает.
    """
    m = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
        )
    )).scalar_one_or_none()
    if m is None or m.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not enough rights")

    chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")

    # проверяем, что все user_id — реальные участники чата
    members_rows = (await db.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id)
    )).scalars().all()
    valid_ids = {x.user_id for x in members_rows}

    for entry in payload.keys:
        if entry.user_id not in valid_ids:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"user {entry.user_id} not a member",
            )

    # применяем
    for entry in payload.keys:
        target = next(x for x in members_rows if x.user_id == entry.user_id)
        target.encrypted_chat_key = entry.encrypted_key

    chat.encryption_enabled = True
    await db.flush()
    await cache.invalidate_chat_list(db, chat_id)


@router.post("/{chat_id}/encryption/grant/{user_id}", status_code=204)
async def grant_key_to_member(
    chat_id: int,
    user_id: int,
    payload: ChatKeyEntry,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    """Доступ к chat_key для нового/отставшего участника."""
    if payload.user_id != user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "user_id mismatch")
    m = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
        )
    )).scalar_one_or_none()
    if m is None or m.role not in ("owner", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not enough rights")

    target = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
        )
    )).scalar_one_or_none()
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not a member")

    target.encrypted_chat_key = payload.encrypted_key
    await db.flush()
    await cache.invalidate_chat_list_for_user(user_id)


@router.get("/{chat_id}/encryption/my-key", response_model=MyChatKeyRead)
async def get_my_chat_key(
    chat_id: int,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    """Возвращает мой зашифрованный chat_key + id владельца (нужен для ECDH)."""
    m = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
        )
    )).scalar_one_or_none()
    if m is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")

    owner_row = (await db.execute(
        select(ChatMember).where(
            ChatMember.chat_id == chat_id, ChatMember.role == "owner"
        )
    )).scalar_one_or_none()
    owner_id = owner_row.user_id if owner_row else current.id

    return MyChatKeyRead(encrypted_key=m.encrypted_chat_key, owner_id=owner_id)
'''


# -------- messages.py --------
MESSAGES_PATCHES = [
    # _msg_to_read: encrypted
    (
        '        is_deleted=m.is_deleted,\n'
        '        is_pinned=m.is_pinned,\n'
        '        reactions=reactions,\n'
        '        created_at=m.created_at,',
        '        is_deleted=m.is_deleted,\n'
        '        is_pinned=m.is_pinned,\n'
        '        encrypted=getattr(m, "encrypted", False),\n'
        '        reactions=reactions,\n'
        '        created_at=m.created_at,',
    ),
    # send_message: сохранять encrypted, permission can_post уже есть из sprint28
    (
        '    msg = Message(\n'
        '        chat_id=chat_id, author_id=current.id,\n'
        '        text=payload.text, message_type=payload.message_type,\n'
        '        attachment_id=payload.attachment_id, reply_to_id=payload.reply_to_id,\n'
        '    )',
        '    msg = Message(\n'
        '        chat_id=chat_id, author_id=current.id,\n'
        '        text=payload.text, message_type=payload.message_type,\n'
        '        attachment_id=payload.attachment_id, reply_to_id=payload.reply_to_id,\n'
        '        encrypted=bool(payload.encrypted),\n'
        '    )',
    ),
    # edit_message: encrypted
    (
        '    msg.text = payload.text\n'
        '    msg.edited_at = datetime.now(timezone.utc)',
        '    msg.text = payload.text\n'
        '    msg.edited_at = datetime.now(timezone.utc)\n'
        '    msg.encrypted = bool(payload.encrypted)',
    ),
    # search — блокируем для E2E
    (
        '    await _ensure_member(db, chat_id, current.id)\n'
        '    pattern = f"%{q}%"',
        '    await _ensure_member(db, chat_id, current.id)\n'
        '    _chat = (await db.execute(\n'
        '        select(Chat).where(Chat.id == chat_id)\n'
        '    )).scalar_one_or_none()\n'
        '    if _chat is not None and _chat.encryption_enabled:\n'
        '        raise HTTPException(\n'
        '            status.HTTP_400_BAD_REQUEST,\n'
        '            "search is not available for encrypted chats",\n'
        '        )\n'
        '    pattern = f"%{q}%"',
    ),
]

# нужен импорт Chat
MESSAGES_IMPORT_PATCH = (
    'from app.models import ChatMember, File as FileModel, Message, MessageReaction, User',
    'from app.models import Chat, ChatMember, File as FileModel, Message, MessageReaction, User',
)


# -------- ws.py --------
WS_PATCHES = [
    # send: encrypted
    (
        '                attachment_id = data.get("attachment_id")\n'
        '                message_type = data.get("message_type", "text")\n'
        '\n'
        '                if not text and not attachment_id:',
        '                attachment_id = data.get("attachment_id")\n'
        '                message_type = data.get("message_type", "text")\n'
        '                encrypted = bool(data.get("encrypted", False))\n'
        '\n'
        '                if not text and not attachment_id:',
    ),
    (
        '                    msg = Message(\n'
        '                        chat_id=chat_id, author_id=user_id, text=text,\n'
        '                        message_type=message_type,\n'
        '                        attachment_id=attachment_id, reply_to_id=reply_to_id,\n'
        '                    )',
        '                    msg = Message(\n'
        '                        chat_id=chat_id, author_id=user_id, text=text,\n'
        '                        message_type=message_type,\n'
        '                        attachment_id=attachment_id, reply_to_id=reply_to_id,\n'
        '                        encrypted=encrypted,\n'
        '                    )',
    ),
    # reply_preview для зашифрованных
    (
        '                        if r:\n'
        '                            if r.is_deleted:\n'
        '                                reply_preview = "Сообщение удалено"\n'
        '                            elif r.message_type == "image":',
        '                        if r:\n'
        '                            if r.is_deleted:\n'
        '                                reply_preview = "Сообщение удалено"\n'
        '                            elif getattr(r, "encrypted", False):\n'
        '                                reply_preview = "🔒 зашифровано"\n'
        '                            elif r.message_type == "image":',
    ),
    # payload_out: encrypted
    (
        '                        "edited_at": None, "is_deleted": False, "is_pinned": False,\n'
        '                        "is_dead_drop": False,\n'
        '                        "reactions": [],',
        '                        "edited_at": None, "is_deleted": False, "is_pinned": False,\n'
        '                        "is_dead_drop": False,\n'
        '                        "encrypted": encrypted,\n'
        '                        "reactions": [],',
    ),
    # edit: encrypted
    (
        '            elif kind == "edit":\n'
        '                message_id = int(data["message_id"])\n'
        '                text = str(data.get("text", "")).strip()\n'
        '                if not text:\n'
        '                    continue\n'
        '                async with SessionLocal() as db:\n'
        '                    m = (await db.execute(\n'
        '                        select(Message).where(Message.id == message_id)\n'
        '                    )).scalar_one_or_none()\n'
        '                    if m is None or m.author_id != user_id:\n'
        '                        continue\n'
        '                    m.text = text\n'
        '                    m.edited_at = datetime.now(timezone.utc)\n'
        '                    await db.commit()',
        '            elif kind == "edit":\n'
        '                message_id = int(data["message_id"])\n'
        '                text = str(data.get("text", "")).strip()\n'
        '                encrypted_edit = bool(data.get("encrypted", False))\n'
        '                if not text:\n'
        '                    continue\n'
        '                async with SessionLocal() as db:\n'
        '                    m = (await db.execute(\n'
        '                        select(Message).where(Message.id == message_id)\n'
        '                    )).scalar_one_or_none()\n'
        '                    if m is None or m.author_id != user_id:\n'
        '                        continue\n'
        '                    m.text = text\n'
        '                    m.edited_at = datetime.now(timezone.utc)\n'
        '                    m.encrypted = encrypted_edit\n'
        '                    await db.commit()',
    ),
    # message_edited event — добавить encrypted
    (
        '                    await manager.send_to_chat(m.chat_id, {\n'
        '                        "type": "message_edited", "message_id": m.id,\n'
        '                        "chat_id": m.chat_id, "text": text,\n'
        '                        "edited_at": m.edited_at.isoformat(),\n'
        '                    })',
        '                    await manager.send_to_chat(m.chat_id, {\n'
        '                        "type": "message_edited", "message_id": m.id,\n'
        '                        "chat_id": m.chat_id, "text": text,\n'
        '                        "encrypted": encrypted_edit,\n'
        '                        "edited_at": m.edited_at.isoformat(),\n'
        '                    })',
    ),
]


# ==============================================================
# BACKEND: новый роутер keys.py
# ==============================================================
KEYS_ROUTER = '''from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import CurrentUser
from app.models import User, UserKey
from app.schemas import PublicKeyRead, PublicKeyUpload


router = APIRouter()


@router.post("/me", response_model=PublicKeyRead, status_code=status.HTTP_201_CREATED)
async def upload_my_key(
    payload: PublicKeyUpload,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    existing = (await db.execute(
        select(UserKey).where(UserKey.user_id == current.id)
    )).scalar_one_or_none()

    if existing is None:
        existing = UserKey(
            user_id=current.id,
            public_key=payload.public_key,
            algorithm=payload.algorithm,
        )
        db.add(existing)
    else:
        existing.public_key = payload.public_key
        existing.algorithm = payload.algorithm

    await db.flush()
    await db.refresh(existing)
    return PublicKeyRead.model_validate(existing)


@router.get("/me", response_model=PublicKeyRead)
async def get_my_key(
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    k = (await db.execute(
        select(UserKey).where(UserKey.user_id == current.id)
    )).scalar_one_or_none()
    if k is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no key uploaded")
    return PublicKeyRead.model_validate(k)


@router.get("/{user_id}", response_model=PublicKeyRead)
async def get_user_key(
    user_id: int,
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    k = (await db.execute(
        select(UserKey).where(UserKey.user_id == user_id)
    )).scalar_one_or_none()
    if k is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user has no key")
    return PublicKeyRead.model_validate(k)


@router.post("/bulk", response_model=list[PublicKeyRead])
async def get_bulk_keys(
    user_ids: list[int],
    current: CurrentUser,
    db: AsyncSession = Depends(get_session),
):
    if not user_ids:
        return []
    rows = (await db.execute(
        select(UserKey).where(UserKey.user_id.in_(user_ids))
    )).scalars().all()
    return [PublicKeyRead.model_validate(r) for r in rows]
'''


# ==============================================================
# FRONTEND: crypto.ts
# ==============================================================
CRYPTO_TS = r'''// WebCrypto helpers: ECDH P-256 + AES-GCM.
// Формат зашифрованного payload: "e2e:1:<base64(iv||ct)>"

const VERSION = 1;
const IV_LEN = 12;

function b64encode(buf: ArrayBuffer | Uint8Array): string {
  const bytes = buf instanceof Uint8Array ? buf : new Uint8Array(buf);
  let s = "";
  for (let i = 0; i < bytes.byteLength; i++) s += String.fromCharCode(bytes[i]);
  return btoa(s);
}

function b64decode(s: string): Uint8Array {
  const bin = atob(s);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// ---------- key generation ----------

export async function generateKeyPair(): Promise<CryptoKeyPair> {
  return crypto.subtle.generateKey(
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveKey", "deriveBits"],
  );
}

export async function exportPublicKeyB64(pair: CryptoKeyPair): Promise<string> {
  const spki = await crypto.subtle.exportKey("spki", pair.publicKey);
  return b64encode(spki);
}

export async function exportPrivateKeyJwk(pair: CryptoKeyPair): Promise<JsonWebKey> {
  return crypto.subtle.exportKey("jwk", pair.privateKey);
}

export async function importPrivateKeyJwk(jwk: JsonWebKey): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "ECDH", namedCurve: "P-256" },
    true,
    ["deriveKey", "deriveBits"],
  );
}

export async function importPublicKeyB64(b64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "spki",
    b64decode(b64),
    { name: "ECDH", namedCurve: "P-256" },
    true,
    [],
  );
}

// ---------- ECDH shared secret → AES key ----------

export async function deriveSharedAesKey(
  myPrivate: CryptoKey,
  peerPublic: CryptoKey,
): Promise<CryptoKey> {
  return crypto.subtle.deriveKey(
    { name: "ECDH", public: peerPublic },
    myPrivate,
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
}

// ---------- AES-GCM ----------

export async function encryptWithKey(key: CryptoKey, plaintext: string): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LEN));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, tagLength: 128 },
    key,
    new TextEncoder().encode(plaintext),
  );
  const buf = new Uint8Array(IV_LEN + ct.byteLength);
  buf.set(iv, 0);
  buf.set(new Uint8Array(ct), IV_LEN);
  return `e2e:${VERSION}:${b64encode(buf)}`;
}

export async function decryptWithKey(key: CryptoKey, payload: string): Promise<string> {
  if (!payload.startsWith("e2e:")) throw new Error("not encrypted");
  const parts = payload.split(":");
  if (parts.length < 3 || parts[0] !== "e2e") throw new Error("bad payload");
  const raw = b64decode(parts.slice(2).join(":"));
  if (raw.byteLength < IV_LEN + 16) throw new Error("payload too short");
  const iv = raw.slice(0, IV_LEN);
  const ct = raw.slice(IV_LEN);
  const pt = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv, tagLength: 128 },
    key,
    ct,
  );
  return new TextDecoder().decode(pt);
}

export function looksEncrypted(text: string | null | undefined): boolean {
  return !!text && text.startsWith("e2e:");
}

// ---------- random AES key (для группы) ----------

export async function generateRandomAesKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
}

export async function exportAesKeyB64(key: CryptoKey): Promise<string> {
  const raw = await crypto.subtle.exportKey("raw", key);
  return b64encode(raw);
}

export async function importAesKeyB64(b64: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    b64decode(b64),
    { name: "AES-GCM", length: 256 },
    true,
    ["encrypt", "decrypt"],
  );
}

// ---------- base64 helpers для отдельных полей ----------

export async function encryptBytesForPeer(
  sharedKey: CryptoKey,
  raw: Uint8Array,
): Promise<string> {
  const iv = crypto.getRandomValues(new Uint8Array(IV_LEN));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv, tagLength: 128 },
    sharedKey,
    raw,
  );
  const buf = new Uint8Array(IV_LEN + ct.byteLength);
  buf.set(iv, 0);
  buf.set(new Uint8Array(ct), IV_LEN);
  return b64encode(buf);
}

export async function decryptBytesFromPeer(
  sharedKey: CryptoKey,
  b64: string,
): Promise<Uint8Array> {
  const raw = b64decode(b64);
  const iv = raw.slice(0, IV_LEN);
  const ct = raw.slice(IV_LEN);
  const pt = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv, tagLength: 128 },
    sharedKey,
    ct,
  );
  return new Uint8Array(pt);
}

export { b64encode, b64decode };
'''


# ==============================================================
# FRONTEND: keyStorage.ts (IndexedDB)
# ==============================================================
KEY_STORAGE_TS = r'''// IndexedDB wrapper для хранения приватного ECDH-ключа.
// Используем нативный API без зависимостей.

const DB_NAME = "messenger-e2e";
const DB_VERSION = 1;
const STORE = "keys";

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function savePrivateJwk(userId: number, jwk: JsonWebKey): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(jwk, `priv:${userId}`);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function loadPrivateJwk(userId: number): Promise<JsonWebKey | null> {
  const db = await openDb();
  const result = await new Promise<JsonWebKey | null>((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).get(`priv:${userId}`);
    req.onsuccess = () => resolve((req.result as JsonWebKey) || null);
    req.onerror = () => reject(req.error);
  });
  db.close();
  return result;
}

export async function clearPrivateJwk(userId: number): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete(`priv:${userId}`);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}
'''


# ==============================================================
# FRONTEND: useE2E.ts
# ==============================================================
USE_E2E_TS = r'''import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import {
  decryptWithKey,
  deriveSharedAesKey,
  encryptWithKey,
  exportPublicKeyB64,
  exportPrivateKeyJwk,
  generateKeyPair,
  generateRandomAesKey,
  exportAesKeyB64,
  importAesKeyB64,
  importPrivateKeyJwk,
  importPublicKeyB64,
  looksEncrypted,
} from "./crypto";
import { loadPrivateJwk, savePrivateJwk } from "./keyStorage";
import type { Chat } from "./types";

interface PeerPubKeyCache {
  [userId: number]: CryptoKey;
}

interface ChatKeyCache {
  [chatId: number]: CryptoKey;
}

export interface UseE2EReturn {
  ready: boolean;
  error: string | null;

  /** Зашифровать текст для отправки в чат. */
  encryptForChat: (chat: Chat, plaintext: string) => Promise<string | null>;

  /** Расшифровать payload из сообщения. */
  decryptFromChat: (chat: Chat, payload: string) => Promise<string | null>;

  /** Инициализировать групповой ключ (owner). Возвращает массив для рассылки. */
  initGroupEncryption: (
    chatId: number,
    memberIds: number[],
  ) => Promise<{ user_id: number; encrypted_key: string }[] | null>;

  /** Выдать ключ новому участнику (owner). */
  grantKeyTo: (
    chatId: number,
    userId: number,
  ) => Promise<{ user_id: number; encrypted_key: string } | null>;

  /** Сбросить кеш ключей (при logout). */
  reset: () => void;
}

export function useE2E(userId: number | null): UseE2EReturn {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const myPrivateRef = useRef<CryptoKey | null>(null);
  const myPublicB64Ref = useRef<string | null>(null);
  const peerCacheRef = useRef<PeerPubKeyCache>({});
  const chatKeyCacheRef = useRef<ChatKeyCache>({});

  // ---------- ensure keypair on mount ----------
  useEffect(() => {
    if (userId == null) {
      myPrivateRef.current = null;
      myPublicB64Ref.current = null;
      peerCacheRef.current = {};
      chatKeyCacheRef.current = {};
      setReady(false);
      return;
    }
    let cancelled = false;

    (async () => {
      try {
        const jwk = await loadPrivateJwk(userId);
        if (jwk) {
          const priv = await importPrivateJwk(jwk);
          if (cancelled) return;
          myPrivateRef.current = priv;
        } else {
          const pair = await generateKeyPair();
          const privJwk = await exportPrivateKeyJwk(pair);
          await savePrivateJwk(userId, privJwk);
          if (cancelled) return;
          myPrivateRef.current = pair.privateKey;
          // экспортируем публичный и заливаем
          const pubB64 = await exportPublicKeyB64(pair);
          myPublicB64Ref.current = pubB64;
          await api.post("/keys/me", {
            public_key: pubB64,
            algorithm: "ECDH-P256",
          });
          setReady(true);
          return;
        }
        // если загрузили старый — надо перезалить публичный (мог потеряться)
        // но у нас нет ключа публичного в jwk? он есть в "x","y".
        // Проще: сгенерировать заново, если сервер не отдаёт наш ключ.
        try {
          const { data } = await api.get<{ public_key: string }>("/keys/me");
          if (cancelled) return;
          myPublicB64Ref.current = data.public_key;
          setReady(true);
        } catch {
          // сервер не знает наш ключ — регенерируем и перезаливаем
          const pair = await generateKeyPair();
          const privJwk2 = await exportPrivateKeyJwk(pair);
          await savePrivateJwk(userId, privJwk2);
          if (cancelled) return;
          myPrivateRef.current = pair.privateKey;
          const pubB64 = await exportPublicKeyB64(pair);
          myPublicB64Ref.current = pubB64;
          await api.post("/keys/me", {
            public_key: pubB64,
            algorithm: "ECDH-P256",
          });
          setReady(true);
        }
      } catch (e: any) {
        setError(e.message || "failed to init e2e");
        setReady(false);
      }
    })();

    return () => { cancelled = true; };
  }, [userId]);

  const fetchPeerPub = useCallback(async (peerId: number): Promise<CryptoKey | null> => {
    if (peerCacheRef.current[peerId]) return peerCacheRef.current[peerId];
    try {
      const { data } = await api.get<{ public_key: string }>(`/keys/${peerId}`);
      const key = await importPublicKeyB64(data.public_key);
      peerCacheRef.current[peerId] = key;
      return key;
    } catch {
      return null;
    }
  }, []);

  // ---------- DM key ----------
  const getDmKey = useCallback(async (peerId: number): Promise<CryptoKey | null> => {
    if (!myPrivateRef.current) return null;
    const peerPub = await fetchPeerPub(peerId);
    if (!peerPub) return null;
    return deriveSharedAesKey(myPrivateRef.current, peerPub);
  }, [fetchPeerPub]);

  // ---------- group key ----------
  const getGroupKey = useCallback(async (chat: Chat): Promise<CryptoKey | null> => {
    if (chatKeyCacheRef.current[chat.id]) return chatKeyCacheRef.current[chat.id];
    if (!myPrivateRef.current) return null;
    try {
      const { data } = await api.get<{ encrypted_key: string | null; owner_id: number }>(
        `/chats/${chat.id}/encryption/my-key`,
      );
      if (!data.encrypted_key) return null;
      const ownerPub = await fetchPeerPub(data.owner_id);
      if (!ownerPub) return null;
      const shared = await deriveSharedAesKey(myPrivateRef.current, ownerPub);
      // encrypted_key = base64(iv||ct) с AES-ключом чата внутри
      const { decryptBytesFromPeer } = await import("./crypto");
      const rawKey = await decryptBytesFromPeer(shared, data.encrypted_key);
      const keyB64 = btoa(String.fromCharCode(...rawKey));
      const aes = await importAesKeyB64(keyB64);
      chatKeyCacheRef.current[chat.id] = aes;
      return aes;
    } catch {
      return null;
    }
  }, [fetchPeerPub]);

  // ---------- public API ----------

  const encryptForChat = useCallback(async (chat: Chat, plaintext: string): Promise<string | null> => {
    if (!chat.encryption_enabled) return plaintext;
    const key = chat.is_group
      ? await getGroupKey(chat)
      : (chat.peer ? await getDmKey(chat.peer.id) : null);
    if (!key) {
      setError("no encryption key for this chat");
      return null;
    }
    try {
      return await encryptWithKey(key, plaintext);
    } catch (e: any) {
      setError(e.message || "encrypt failed");
      return null;
    }
  }, [getDmKey, getGroupKey]);

  const decryptFromChat = useCallback(async (chat: Chat, payload: string): Promise<string | null> => {
    if (!looksEncrypted(payload)) return payload;
    const key = chat.is_group
      ? await getGroupKey(chat)
      : (chat.peer ? await getDmKey(chat.peer.id) : null);
    if (!key) return null;
    try {
      return await decryptWithKey(key, payload);
    } catch {
      return null;
    }
  }, [getDmKey, getGroupKey]);

  const initGroupEncryption = useCallback(async (
    chatId: number,
    memberIds: number[],
  ) => {
    if (!myPrivateRef.current) return null;
    // 1. генерируем случайный chatKey
    const chatKey = await generateRandomAesKey();
    const chatKeyB64 = await exportAesKeyB64(chatKey);

    const out: { user_id: number; encrypted_key: string }[] = [];
    const { encryptBytesForPeer } = await import("./crypto");
    const raw = Uint8Array.from(atob(chatKeyB64), (c) => c.charCodeAt(0));

    for (const uid of memberIds) {
      // с собой — просто сохраняем raw как "себе"
      const peerPub = await fetchPeerPub(uid);
      if (!peerPub) return null;
      const shared = await deriveSharedAesKey(myPrivateRef.current, peerPub);
      const enc = await encryptBytesForPeer(shared, raw);
      out.push({ user_id: uid, encrypted_key: enc });
    }
    // запоминаем в кеше чата
    chatKeyCacheRef.current[chatId] = chatKey;
    return out;
  }, [fetchPeerPub]);

  const grantKeyTo = useCallback(async (chatId: number, userIdToGrant: number) => {
    if (!myPrivateRef.current) return null;
    // берём ключ из кеша, или тянем свой расшифрованный
    let key = chatKeyCacheRef.current[chatId];
    if (!key) {
      // попробуем вытянуть через my-key эндпоинт (мы owner, наш encrypted_key есть)
      try {
        const { data } = await api.get<{ encrypted_key: string | null; owner_id: number }>(
          `/chats/${chatId}/encryption/my-key`,
        );
        if (!data.encrypted_key) return null;
        const ownerPub = await fetchPeerPub(data.owner_id);
        if (!ownerPub) return null;
        const shared = await deriveSharedAesKey(myPrivateRef.current, ownerPub);
        const { decryptBytesFromPeer } = await import("./crypto");
        const raw = await decryptBytesFromPeer(shared, data.encrypted_key);
        const b64 = btoa(String.fromCharCode(...raw));
        key = await importAesKeyB64(b64);
        chatKeyCacheRef.current[chatId] = key;
      } catch {
        return null;
      }
    }
    const raw = await crypto.subtle.exportKey("raw", key);
    const peerPub = await fetchPeerPub(userIdToGrant);
    if (!peerPub) return null;
    const shared = await deriveSharedAesKey(myPrivateRef.current, peerPub);
    const { encryptBytesForPeer } = await import("./crypto");
    const enc = await encryptBytesForPeer(shared, new Uint8Array(raw));
    return { user_id: userIdToGrant, encrypted_key: enc };
  }, [fetchPeerPub]);

  const reset = useCallback(() => {
    myPrivateRef.current = null;
    myPublicB64Ref.current = null;
    peerCacheRef.current = {};
    chatKeyCacheRef.current = {};
    setReady(false);
    setError(null);
  }, []);

  return { ready, error, encryptForChat, decryptFromChat, initGroupEncryption, grantKeyTo, reset };
}
'''


# ==============================================================
# FRONTEND: E2EIndicator.tsx
# ==============================================================
E2E_INDICATOR = r'''export default function E2EIndicator({
  enabled, hasKey, ready,
}: {
  enabled: boolean;
  hasKey: boolean;
  ready: boolean;
}) {
  if (!enabled) return null;

  let label = "🔒 E2E";
  let title = "Сквозное шифрование включено";
  let cls = "border-cyber-cyan/40 text-cyber-cyan";

  if (!ready) {
    label = "🔒 …";
    title = "Инициализация ключей";
    cls = "border-cyber-yellow/40 text-cyber-yellow";
  } else if (!hasKey) {
    label = "🔒 нет ключа";
    title = "Нет ключа для этого чата — попроси владельца раздать его";
    cls = "border-cyber-magenta/50 text-cyber-magenta";
  }

  return (
    <span
      title={title}
      className={
        "inline-flex items-center gap-1 rounded-sm border px-1.5 py-0.5 text-[9px] uppercase tracking-widest " +
        cls
      }
    >
      {label}
    </span>
  );
}
'''


# ==============================================================
# FRONTEND: E2ESetupModal.tsx
# ==============================================================
E2E_SETUP = r'''import { useState } from "react";
import { api } from "./api";
import type { Chat, ChatMember, UseE2E } from "./types";

export default function E2ESetupModal({
  chat, useE2E, onClose, onEnabled,
}: {
  chat: Chat;
  useE2E: {
    initGroupEncryption: (
      chatId: number, memberIds: number[],
    ) => Promise<{ user_id: number; encrypted_key: string }[] | null>;
  };
  onClose: () => void;
  onEnabled: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const enable = async () => {
    setBusy(true);
    setError("");
    try {
      // 1. получаем список участников
      const { data: members } = await api.get<ChatMember[]>(`/chats/${chat.id}/members`);
      const ids = members.map((m) => m.user_id);

      // 2. генерируем chatKey и шифруем его каждому
      const keys = await useE2E.initGroupEncryption(chat.id, ids);
      if (!keys) {
        throw new Error("не удалось сгенерировать ключ — проверь, что у всех есть публичные ключи E2E");
      }

      // 3. отправляем на сервер
      await api.post(`/chats/${chat.id}/encryption/keys`, { keys });

      onEnabled();
      onClose();
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "ошибка");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/85 p-4" onClick={onClose}>
      <div
        className="corner-frame w-[520px] rounded-sm border border-cyber-cyan/50 bg-cyber-panel p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4">
          <div className="text-sm font-bold uppercase tracking-widest neon-text">
            🔒 ENABLE E2E ENCRYPTION
          </div>
          <div className="mt-2 text-[11px] leading-relaxed text-cyber-dim">
            Все новые сообщения будут шифроваться на твоём устройстве.
            <br />
            Сервер будет хранить только шифртекст — прочитать его не сможет.
            <br /><br />
            <span className="neon-text-yel">
              ⚠ Старые сообщения останутся незашифрованными.
            </span>
            <br />
            <span className="neon-text-yel">
              ⚠ Вложения (файлы, фото, голосовые) сейчас не шифруются.
            </span>
            <br />
            <span className="neon-text-yel">
              ⚠ Поиск по сообщениям в этом чате будет отключён.
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-3 rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
            ⚠ {error}
          </div>
        )}

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="cyber-btn rounded-sm px-4 py-2 text-xs">
            [ ОТМЕНА ]
          </button>
          <button
            onClick={enable}
            disabled={busy}
            className="cyber-btn rounded-sm px-5 py-2 text-xs"
            style={{ borderColor: "rgba(0,240,255,0.7)", color: "#00e0ff" }}
          >
            {busy ? "[ ШИФРУЮ... ]" : "[ ВКЛЮЧИТЬ ]"}
          </button>
        </div>
      </div>
    </div>
  );
}
'''


# ==============================================================
# FRONTEND: patches
# ==============================================================

TYPES_PATCHES = [
    (
        'export interface Message {\n'
        '  id: number;\n'
        '  client_id?: string | null;',
        'export interface Message {\n'
        '  id: number;\n'
        '  client_id?: string | null;\n'
        '  encrypted?: boolean;',
    ),
    (
        '  firewall_enabled: boolean;\n'
        '  firewall_seconds: number;\n'
        '  is_dark_room: boolean;\n'
        '  auto_delete_at: string | null;\n'
        '}',
        '  firewall_enabled: boolean;\n'
        '  firewall_seconds: number;\n'
        '  is_dark_room: boolean;\n'
        '  auto_delete_at: string | null;\n'
        '  encryption_enabled: boolean;\n'
        '  has_my_key: boolean;\n'
        '}',
    ),
    # UseE2E type для передачи в модалку
    (
        'export type ThemeName = "cyber" | "matrix" | "sunset" | "amber" | "deusex" | "gits" | "lain";',
        'export type ThemeName = "cyber" | "matrix" | "sunset" | "amber" | "deusex" | "gits" | "lain";\n'
        '\n'
        'export interface UseE2E {\n'
        '  ready: boolean;\n'
        '  error: string | null;\n'
        '  encryptForChat: (chat: Chat, plaintext: string) => Promise<string | null>;\n'
        '  decryptFromChat: (chat: Chat, payload: string) => Promise<string | null>;\n'
        '  initGroupEncryption: (\n'
        '    chatId: number, memberIds: number[],\n'
        '  ) => Promise<{ user_id: number; encrypted_key: string }[] | null>;\n'
        '  grantKeyTo: (\n'
        '    chatId: number, userId: number,\n'
        '  ) => Promise<{ user_id: number; encrypted_key: string } | null>;\n'
        '  reset: () => void;\n'
        '}',
    ),
]


# ChatWindow: интеграция
CHATWINDOW_PATCHES = [
    # imports
    (
        'import CommentsDrawer from "./CommentsDrawer";',
        'import CommentsDrawer from "./CommentsDrawer";\n'
        'import E2EIndicator from "./E2EIndicator";\n'
        'import E2ESetupModal from "./E2ESetupModal";\n'
        'import { looksEncrypted } from "./crypto";\n'
        'import type { UseE2E as UseE2EType } from "./types";',
    ),
    # props signature
    (
        '  queuedMessages: QueuedLike[];',
        '  e2e: UseE2EType;\n'
        '  queuedMessages: QueuedLike[];',
    ),
    (
        '  chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser, onStartCall,\n'
        '  queuedMessages, onEnqueue, onRemoveQueued, onRetryQueued,\n'
        '}: {',
        '  chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser, onStartCall,\n'
        '  e2e, queuedMessages, onEnqueue, onRemoveQueued, onRetryQueued,\n'
        '}: {',
    ),
    # state — расшифрованные тексты + модалка setup
    (
        '  const [commentsFor, setCommentsFor] = useState<Message | null>(null);',
        '  const [commentsFor, setCommentsFor] = useState<Message | null>(null);\n'
        '  const [decrypted, setDecrypted] = useState<Record<number, string>>({});\n'
        '  const [showE2ESetup, setShowE2ESetup] = useState(false);',
    ),
]


# App.tsx: подключить useE2E и передать в ChatWindow
APP_PATCHES = [
    (
        'import { useScrolling } from "./useScrolling";',
        'import { useScrolling } from "./useScrolling";\n'
        '    import { useE2E } from "./useE2E";',
    ),
    (
        '      const queue = useMessageQueue(user?.id ?? null, send, isWsOpen);',
        '      const queue = useMessageQueue(user?.id ?? null, send, isWsOpen);\n'
        '      const e2e = useE2E(user?.id ?? null);',
    ),
    # пробрасываем в ChatWindow
    (
        '                  queuedMessages={queue.queue}\n'
        '                  onEnqueue={enqueueForChat}\n'
        '                  onRemoveQueued={queue.removeByClientId}\n'
        '                  onRetryQueued={queue.retryOne}\n'
        '                />',
        '                  queuedMessages={queue.queue}\n'
        '                  onEnqueue={enqueueForChat}\n'
        '                  onRemoveQueued={queue.removeByClientId}\n'
        '                  onRetryQueued={queue.retryOne}\n'
        '                  e2e={e2e}\n'
        '                />',
    ),
    # сброс e2e при logout — найдём функцию logout
    (
        '      const logout = async () => {\n'
        '        const refresh = localStorage.getItem("refresh_token");\n'
        '        if (refresh) {\n'
        '          try { await api.post("/auth/logout", { refresh_token: refresh }); } catch {}\n'
        '        }\n'
        '        localStorage.removeItem("access_token");\n'
        '        localStorage.removeItem("refresh_token");\n'
        '        setUser(null); setChats([]); setActiveChatId(null);\n'
        '        setMode("chats"); setProfileUserId(null);\n'
        '      };',
        '      const logout = async () => {\n'
        '        const refresh = localStorage.getItem("refresh_token");\n'
        '        if (refresh) {\n'
        '          try { await api.post("/auth/logout", { refresh_token: refresh }); } catch {}\n'
        '        }\n'
        '        localStorage.removeItem("access_token");\n'
        '        localStorage.removeItem("refresh_token");\n'
        '        try { e2e.reset(); } catch {}\n'
        '        setUser(null); setChats([]); setActiveChatId(null);\n'
        '        setMode("chats"); setProfileUserId(null);\n'
        '      };',
    ),
]


# ==============================================================
# Filesystem helpers
# ==============================================================

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


def write_new(path: Path, content: str) -> None:
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {path}")


def append_to(path: Path, content: str, marker: str) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    if marker in text:
        print(f"  > {path} (уже содержит {marker})")
        return False
    text = text.rstrip() + "\n" + content
    path.write_text(text, encoding="utf-8")
    print(f"  ~ {path} (добавлено {len(content)} символов)")
    return True


# ==============================================================
# MAIN
# ==============================================================

def main() -> int:
    p = argparse.ArgumentParser(description="sprint29 e2e encryption")
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-backup", action="store_true")
    p.add_argument("--restore", default=None)
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    be = root / "backend"
    fe = root / "frontend" / "src"

    # --------- RESTORE ---------
    if args.restore:
        backup = (root / args.restore).resolve()
        if not backup.exists():
            backup = Path(args.restore).resolve()
        print(f"\nОткат из {backup}\n")
        n = restore_backup(root, backup)
        print(f"\nВосстановлено: {n}\n")
        return 0

    # --------- BACKUP ---------
    backup_dir: Path | None = None
    if not args.no_backup:
        backup_dir = create_backup(root)
        print(f"\n📦 Бэкап: {backup_dir}")
        print(f"   откат: python sprint29_e2e.py --path . --name {args.name} --restore {backup_dir.name}\n")

    # --------- BACKEND ---------

    # Миграция
    print("Миграции:")
    write_new(be / "alembic" / "versions" / "0012_e2e.py", ALEMBIC_0012)

    # Новый роутер keys.py
    print("\nНовые файлы backend:")
    write_new(be / "app" / "routers" / "keys.py", KEYS_ROUTER)

    # Патчи models/schemas
    print("\nПатчи backend:")
    apply_patch(be / "app" / "models.py", PATCHES["backend/app/models.py"])
    apply_patch(be / "app" / "schemas.py", PATCHES["backend/app/schemas.py"])

    # chats.py — патчи + append
    apply_patch(be / "app" / "routers" / "chats.py", CHATS_PATCHES)
    append_to(be / "app" / "routers" / "chats.py", CHATS_APPEND, "/encryption/enable")

    # messages.py — патчи (импорт + encrypted поля + блокировка search)
    msg_path = be / "app" / "routers" / "messages.py"
    if msg_path.exists():
        text = msg_path.read_text(encoding="utf-8")
        if MESSAGES_IMPORT_PATCH[0] in text:
            text = text.replace(MESSAGES_IMPORT_PATCH[0], MESSAGES_IMPORT_PATCH[1], 1)
            msg_path.write_text(text, encoding="utf-8")
            print(f"  ~ {msg_path} [import]")
    apply_patch(msg_path, MESSAGES_PATCHES)

    # ws.py
    apply_patch(be / "app" / "routers" / "ws.py", WS_PATCHES)

    # main.py — подключить роутер keys
    main_path = be / "app" / "main.py"
    if main_path.exists():
        text = main_path.read_text(encoding="utf-8")
        changed = False
        if "from app.routers import (" in text and " keys," not in text:
            # найдём точку — после "auth," добавим " keys,"
            if "auth, calls, chats, dead_drops, files," in text:
                text = text.replace(
                    "auth, calls, chats, dead_drops, files,",
                    "auth, calls, chats, dead_drops, files, keys,",
                    1,
                )
                changed = True
            elif "auth, calls, chats," in text:
                text = text.replace(
                    "auth, calls, chats,",
                    "auth, calls, chats, keys,",
                    1,
                )
                changed = True
        # include_router
        if "app.include_router(users.router" in text and "keys.router" not in text:
            text = text.replace(
                'app.include_router(users.router, prefix=f"{p}/users", tags=["users"])',
                'app.include_router(users.router, prefix=f"{p}/users", tags=["users"])\n'
                'app.include_router(keys.router, prefix=f"{p}/keys", tags=["keys"])',
                1,
            )
            changed = True
        if changed:
            main_path.write_text(text, encoding="utf-8")
            print(f"  ~ {main_path} [подключён keys router]")
        else:
            print(f"  > {main_path} (без изменений — keys может быть уже подключён)")

    # --------- FRONTEND ---------
    print("\nНовые файлы frontend:")
    write_new(fe / "crypto.ts", CRYPTO_TS)
    write_new(fe / "keyStorage.ts", KEY_STORAGE_TS)
    write_new(fe / "useE2E.ts", USE_E2E_TS)
    write_new(fe / "E2EIndicator.tsx", E2E_INDICATOR)
    write_new(fe / "E2ESetupModal.tsx", E2E_SETUP)

    print("\nПатчи frontend:")
    apply_patch(fe / "types.ts", TYPES_PATCHES)
    apply_patch(fe / "ChatWindow.tsx", CHATWINDOW_PATCHES)
    apply_patch(fe / "App.tsx", APP_PATCHES)

    # --------- REPORT ---------
    print()
    print("=" * 60)
    print("ГОТОВО")
    print("=" * 60)
    if backup_dir:
        print(f"📦 Бэкап: {backup_dir}")
    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml build --no-cache api frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("После рестарта:")
    print("  1. Зайди в любой чат — ключи сгенерируются автоматически")
    print("  2. Открой группу → ⚙ → включи E2E (только owner)")
    print("  3. Отправь сообщение — увидишь 🔒 индикатор в шапке")
    print()
    print("Если что-то сломалось — откат:")
    print(f"  python sprint29_e2e.py --path . --name {args.name} "
          f"--restore {backup_dir.name if backup_dir else '_backup_XXX'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())