#!/usr/bin/env python3
"""sprint2.py — media, files, voice, stickers."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0003_sprint2.py"] = _t('''
    """sprint 2: files table and message attachments

    Revision ID: 0003
    Revises: 0002
    Create Date: 2025-03-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0003"
    down_revision: Union[str, None] = "0002"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "files",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "owner_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("filename", sa.String(255), nullable=False),
            sa.Column("content_type", sa.String(100), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False),
            sa.Column("storage_name", sa.String(120), nullable=False, unique=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.add_column(
            "messages",
            sa.Column(
                "attachment_id",
                sa.Integer(),
                sa.ForeignKey("files.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.add_column(
            "messages",
            sa.Column(
                "message_type",
                sa.String(20),
                nullable=False,
                server_default="text",
            ),
        )
        op.alter_column("messages", "text", existing_type=sa.Text(), nullable=True)


    def downgrade() -> None:
        op.alter_column("messages", "text", existing_type=sa.Text(), nullable=False)
        op.drop_column("messages", "message_type")
        op.drop_column("messages", "attachment_id")
        op.drop_table("files")
''')

# ============================================================== BACKEND
T["backend/app/config.py"] = _t('''
    from functools import lru_cache
    from pathlib import Path

    from pydantic_settings import BaseSettings, SettingsConfigDict


    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        APP_NAME: str = "Messenger"
        DEBUG: bool = True
        API_V1_PREFIX: str = "/api/v1"
        SECRET_KEY: str = "change-me"
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

        POSTGRES_HOST: str = "localhost"
        POSTGRES_PORT: int = 5432
        POSTGRES_USER: str = "messenger"
        POSTGRES_PASSWORD: str = "messenger"
        POSTGRES_DB: str = "messenger"

        UPLOAD_DIR: str = "/app/uploads"
        MAX_UPLOAD_SIZE_MB: int = 50

        CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]

        @property
        def database_url(self) -> str:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )

        @property
        def upload_path(self) -> Path:
            p = Path(self.UPLOAD_DIR)
            p.mkdir(parents=True, exist_ok=True)
            return p


    @lru_cache
    def get_settings() -> Settings:
        return Settings()


    settings = get_settings()
''')

T["backend/app/models.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from sqlalchemy import (
        Boolean,
        DateTime,
        ForeignKey,
        Integer,
        String,
        Text,
        UniqueConstraint,
        func,
    )
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


    class Base(DeclarativeBase):
        pass


    class User(Base):
        __tablename__ = "users"

        id: Mapped[int] = mapped_column(primary_key=True)
        username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
        email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
        hashed_password: Mapped[str] = mapped_column(String(255))
        display_name: Mapped[str | None] = mapped_column(String(100), default=None)
        bio: Mapped[str | None] = mapped_column(String(500), default=None)
        avatar_color: Mapped[str | None] = mapped_column(String(20), default=None)
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
        last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )

        memberships: Mapped[list[ChatMember]] = relationship(
            back_populates="user", cascade="all, delete-orphan"
        )
        messages: Mapped[list[Message]] = relationship(
            back_populates="author", cascade="all, delete-orphan"
        )


    class File(Base):
        __tablename__ = "files"

        id: Mapped[int] = mapped_column(primary_key=True)
        owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        filename: Mapped[str] = mapped_column(String(255))
        content_type: Mapped[str] = mapped_column(String(100))
        size: Mapped[int] = mapped_column(Integer)
        storage_name: Mapped[str] = mapped_column(String(120), unique=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Chat(Base):
        __tablename__ = "chats"

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str | None] = mapped_column(String(255), default=None)
        is_group: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )

        members: Mapped[list[ChatMember]] = relationship(
            back_populates="chat", cascade="all, delete-orphan"
        )
        messages: Mapped[list[Message]] = relationship(
            back_populates="chat", cascade="all, delete-orphan"
        )


    class ChatMember(Base):
        __tablename__ = "chat_members"
        __table_args__ = (UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        role: Mapped[str] = mapped_column(String(20), default="member")
        last_read_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )

        chat: Mapped[Chat] = relationship(back_populates="members")
        user: Mapped[User] = relationship(back_populates="memberships")


    class Message(Base):
        __tablename__ = "messages"

        id: Mapped[int] = mapped_column(primary_key=True)
        chat_id: Mapped[int] = mapped_column(
            ForeignKey("chats.id", ondelete="CASCADE"), index=True
        )
        author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        message_type: Mapped[str] = mapped_column(String(20), default="text")
        attachment_id: Mapped[int | None] = mapped_column(
            ForeignKey("files.id", ondelete="SET NULL"), nullable=True
        )
        reply_to_id: Mapped[int | None] = mapped_column(
            ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
        )
        edited_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )

        chat: Mapped[Chat] = relationship(back_populates="messages")
        author: Mapped[User] = relationship(back_populates="messages")
''')

T["backend/app/schemas.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from pydantic import BaseModel, ConfigDict, EmailStr, Field


    class RegisterRequest(BaseModel):
        username: str = Field(min_length=3, max_length=50)
        email: EmailStr
        password: str = Field(min_length=8, max_length=128)
        display_name: str | None = None


    class LoginRequest(BaseModel):
        username: str
        password: str


    class TokenResponse(BaseModel):
        access_token: str
        token_type: str = "bearer"


    class UserRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        username: str
        email: EmailStr
        display_name: str | None
        bio: str | None = None
        avatar_color: str | None = None
        is_active: bool
        last_seen: datetime | None = None
        created_at: datetime


    class UserUpdate(BaseModel):
        display_name: str | None = Field(default=None, max_length=100)
        bio: str | None = Field(default=None, max_length=500)


    class ChatCreate(BaseModel):
        title: str | None = None
        is_group: bool = False
        member_usernames: list[str] = Field(default_factory=list)


    class FileRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        filename: str
        content_type: str
        size: int
        created_at: datetime


    class MessageRead(BaseModel):
        id: int
        chat_id: int
        author_id: int
        author_username: str
        author_display: str | None = None
        author_avatar_color: str | None = None
        text: str | None = None
        message_type: str = "text"
        attachment: FileRead | None = None
        reply_to_id: int | None = None
        reply_preview: str | None = None
        reply_author: str | None = None
        edited_at: datetime | None = None
        is_deleted: bool = False
        created_at: datetime


    class ChatRead(BaseModel):
        id: int
        title: str | None
        is_group: bool
        created_at: datetime
        last_message: MessageRead | None = None
        unread_count: int = 0
        peer: UserRead | None = None


    class MessageCreate(BaseModel):
        text: str | None = Field(default=None, max_length=4000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=4000)
''')

# ---------- Files router (new)
T["backend/app/routers/files.py"] = _t('''
    from __future__ import annotations

    import uuid
    from pathlib import Path

    from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
    from fastapi.responses import FileResponse
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import File as FileModel
    from app.schemas import FileRead
    from app.security import decode_token


    router = APIRouter()


    @router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
    async def upload(
        current: CurrentUser,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_session),
    ) -> FileRead:
        if not file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "no filename")

        ext = Path(file.filename).suffix[:16]
        storage_name = f"{uuid.uuid4().hex}{ext}"
        target = settings.upload_path / storage_name

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        written = 0
        with target.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        f"file too large (>{settings.MAX_UPLOAD_SIZE_MB}MB)",
                    )
                f.write(chunk)

        obj = FileModel(
            owner_id=current.id,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            size=written,
            storage_name=storage_name,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return FileRead.model_validate(obj)


    @router.get("/{file_id}")
    async def download(
        file_id: int,
        token: str = Query(...),
        db: AsyncSession = Depends(get_session),
    ):
        # авторизация через query-параметр, т.к. <img> не может ставить заголовки
        try:
            decode_token(token)
        except ValueError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

        obj = (
            await db.execute(select(FileModel).where(FileModel.id == file_id))
        ).scalar_one_or_none()
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")

        path = settings.upload_path / obj.storage_name
        if not path.exists():
            raise HTTPException(status.HTTP_410_GONE, "file missing on disk")

        # inline-рендеринг для картинок/аудио, download для остального
        inline = obj.content_type.startswith(("image/", "audio/", "video/"))
        return FileResponse(
            path,
            media_type=obj.content_type,
            filename=obj.filename,
            content_disposition_type="inline" if inline else "attachment",
        )
''')

# ---------- messages router (updated)
T["backend/app/routers/messages.py"] = _t('''
    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import ChatMember, File as FileModel, Message, User
    from app.schemas import FileRead, MessageCreate, MessageEdit, MessageRead


    router = APIRouter()


    async def _ensure_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember:
        m = (
            await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        return m


    async def _to_read(db: AsyncSession, m: Message) -> MessageRead:
        author = (await db.execute(select(User).where(User.id == m.author_id))).scalar_one()

        attachment = None
        if m.attachment_id:
            f = (
                await db.execute(select(FileModel).where(FileModel.id == m.attachment_id))
            ).scalar_one_or_none()
            if f:
                attachment = FileRead.model_validate(f)

        reply_preview = None
        reply_author = None
        if m.reply_to_id:
            r = (
                await db.execute(select(Message).where(Message.id == m.reply_to_id))
            ).scalar_one_or_none()
            if r:
                if r.is_deleted:
                    reply_preview = "Сообщение удалено"
                elif r.message_type == "image":
                    reply_preview = "📷 Фото"
                elif r.message_type == "voice":
                    reply_preview = "🎤 Голосовое"
                elif r.message_type == "file":
                    reply_preview = "📎 Файл"
                elif r.message_type == "sticker":
                    reply_preview = r.text or "Стикер"
                else:
                    reply_preview = (r.text or "")[:120]
                ra = (
                    await db.execute(select(User).where(User.id == r.author_id))
                ).scalar_one()
                reply_author = ra.display_name or ra.username

        return MessageRead(
            id=m.id,
            chat_id=m.chat_id,
            author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
            text="Сообщение удалено" if m.is_deleted else m.text,
            message_type=m.message_type or "text",
            attachment=attachment,
            reply_to_id=m.reply_to_id,
            reply_preview=reply_preview,
            reply_author=reply_author,
            edited_at=m.edited_at,
            is_deleted=m.is_deleted,
            created_at=m.created_at,
        )


    @router.get("/{chat_id}/messages", response_model=list[MessageRead])
    async def list_messages(
        chat_id: int,
        current: CurrentUser,
        limit: int = Query(200, le=500),
        db: AsyncSession = Depends(get_session),
    ):
        await _ensure_member(db, chat_id, current.id)
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        msgs = (await db.execute(stmt)).scalars().all()
        return [await _to_read(db, m) for m in msgs]


    @router.post(
        "/{chat_id}/messages",
        response_model=MessageRead,
        status_code=status.HTTP_201_CREATED,
    )
    async def send_message(
        chat_id: int,
        payload: MessageCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _ensure_member(db, chat_id, current.id)
        if not (payload.text or payload.attachment_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "empty message")
        msg = Message(
            chat_id=chat_id,
            author_id=current.id,
            text=payload.text,
            message_type=payload.message_type,
            attachment_id=payload.attachment_id,
            reply_to_id=payload.reply_to_id,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        return await _to_read(db, msg)


    @router.patch("/messages/{message_id}", response_model=MessageRead)
    async def edit_message(
        message_id: int,
        payload: MessageEdit,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        if msg.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your message")
        msg.text = payload.text
        msg.edited_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(msg)
        return await _to_read(db, msg)


    @router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_message(
        message_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (
            await db.execute(select(Message).where(Message.id == message_id))
        ).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        if msg.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your message")
        msg.is_deleted = True
        msg.text = ""
        await db.flush()
''')

# ---------- ws router (updated to carry attachments)
T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

    import json
    from datetime import datetime, timezone

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import ChatMember, File as FileModel, Message, User
    from app.security import decode_token
    from app.websocket_manager import manager


    router = APIRouter()


    async def _author_payload(db, user_id: int) -> dict:
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        return {
            "author_id": u.id,
            "author_username": u.username,
            "author_display": u.display_name,
            "author_avatar_color": u.avatar_color,
        }


    async def _attachment_payload(db, attachment_id: int | None) -> dict | None:
        if not attachment_id:
            return None
        f = (
            await db.execute(select(FileModel).where(FileModel.id == attachment_id))
        ).scalar_one_or_none()
        if not f:
            return None
        return {
            "id": f.id,
            "filename": f.filename,
            "content_type": f.content_type,
            "size": f.size,
            "created_at": f.created_at.isoformat(),
        }


    @router.websocket("/ws")
    async def ws_endpoint(ws: WebSocket, token: str) -> None:
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except Exception:
            await ws.close(code=4401)
            return

        async with SessionLocal() as db:
            user = (
                await db.execute(select(User).where(User.id == user_id))
            ).scalar_one_or_none()
            if user is None or not user.is_active:
                await ws.close(code=4401)
                return
            username = user.username

        await manager.connect(user_id, ws)
        await manager.broadcast_all(
            {"type": "presence", "user_id": user_id, "online": True}
        )

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
                            "type": "typing",
                            "chat_id": chat_id,
                            "user_id": user_id,
                            "username": username,
                            "is_typing": is_typing,
                        },
                        exclude_ws=ws,
                    )

                elif kind == "send":
                    chat_id = int(data["chat_id"])
                    text = (data.get("text") or "").strip() or None
                    reply_to_id = data.get("reply_to_id")
                    attachment_id = data.get("attachment_id")
                    message_type = data.get("message_type", "text")

                    if not text and not attachment_id:
                        continue

                    async with SessionLocal() as db:
                        member = (
                            await db.execute(
                                select(ChatMember).where(
                                    ChatMember.chat_id == chat_id,
                                    ChatMember.user_id == user_id,
                                )
                            )
                        ).scalar_one_or_none()
                        if member is None:
                            await ws.send_json({"type": "error", "detail": "not a member"})
                            continue

                        msg = Message(
                            chat_id=chat_id,
                            author_id=user_id,
                            text=text,
                            message_type=message_type,
                            attachment_id=attachment_id,
                            reply_to_id=reply_to_id,
                        )
                        db.add(msg)
                        await db.flush()
                        await db.refresh(msg)

                        member.last_read_message_id = msg.id
                        await db.commit()

                        author = await _author_payload(db, user_id)
                        attachment = await _attachment_payload(db, attachment_id)

                        reply_preview = None
                        reply_author = None
                        if reply_to_id:
                            r = (
                                await db.execute(
                                    select(Message).where(Message.id == reply_to_id)
                                )
                            ).scalar_one_or_none()
                            if r:
                                if r.is_deleted:
                                    reply_preview = "Сообщение удалено"
                                elif r.message_type == "image":
                                    reply_preview = "📷 Фото"
                                elif r.message_type == "voice":
                                    reply_preview = "🎤 Голосовое"
                                elif r.message_type == "file":
                                    reply_preview = "📎 Файл"
                                elif r.message_type == "sticker":
                                    reply_preview = r.text or "Стикер"
                                else:
                                    reply_preview = (r.text or "")[:120]
                                ra = (
                                    await db.execute(
                                        select(User).where(User.id == r.author_id)
                                    )
                                ).scalar_one()
                                reply_author = ra.display_name or ra.username

                        payload_out = {
                            "type": "message",
                            "id": msg.id,
                            "chat_id": chat_id,
                            "text": text,
                            "message_type": message_type,
                            "attachment": attachment,
                            "reply_to_id": reply_to_id,
                            "reply_preview": reply_preview,
                            "reply_author": reply_author,
                            "edited_at": None,
                            "is_deleted": False,
                            "created_at": msg.created_at.isoformat(),
                            **author,
                        }
                        await manager.send_to_chat(chat_id, payload_out)

                elif kind == "edit":
                    message_id = int(data["message_id"])
                    text = str(data.get("text", "")).strip()
                    if not text:
                        continue
                    async with SessionLocal() as db:
                        m = (
                            await db.execute(
                                select(Message).where(Message.id == message_id)
                            )
                        ).scalar_one_or_none()
                        if m is None or m.author_id != user_id:
                            continue
                        m.text = text
                        m.edited_at = datetime.now(timezone.utc)
                        await db.commit()
                        await manager.send_to_chat(
                            m.chat_id,
                            {
                                "type": "message_edited",
                                "message_id": m.id,
                                "chat_id": m.chat_id,
                                "text": text,
                                "edited_at": m.edited_at.isoformat(),
                            },
                        )

                elif kind == "delete":
                    message_id = int(data["message_id"])
                    async with SessionLocal() as db:
                        m = (
                            await db.execute(
                                select(Message).where(Message.id == message_id)
                            )
                        ).scalar_one_or_none()
                        if m is None or m.author_id != user_id:
                            continue
                        m.is_deleted = True
                        m.text = ""
                        await db.commit()
                        await manager.send_to_chat(
                            m.chat_id,
                            {
                                "type": "message_deleted",
                                "message_id": m.id,
                                "chat_id": m.chat_id,
                            },
                        )

                elif kind == "read":
                    chat_id = int(data["chat_id"])
                    message_id = int(data["message_id"])
                    async with SessionLocal() as db:
                        member = (
                            await db.execute(
                                select(ChatMember).where(
                                    ChatMember.chat_id == chat_id,
                                    ChatMember.user_id == user_id,
                                )
                            )
                        ).scalar_one_or_none()
                        if member:
                            member.last_read_message_id = message_id
                            await db.commit()
                    await manager.send_to_chat(
                        chat_id,
                        {
                            "type": "read",
                            "chat_id": chat_id,
                            "user_id": user_id,
                            "message_id": message_id,
                        },
                        exclude_ws=ws,
                    )

                elif kind == "ping":
                    await ws.send_json({"type": "pong"})

        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(ws)
            async with SessionLocal() as db:
                u = (
                    await db.execute(select(User).where(User.id == user_id))
                ).scalar_one_or_none()
                if u:
                    u.last_seen = datetime.now(timezone.utc)
                    await db.commit()
            await manager.broadcast_all(
                {
                    "type": "presence",
                    "user_id": user_id,
                    "online": False,
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                }
            )
''')

T["backend/app/main.py"] = _t('''
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.db import engine
    from app.routers import auth, chats, files, messages, users, ws
    from app.websocket_manager import manager


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.upload_path  # ensure dir exists
        yield
        await manager.close_all()
        await engine.dispose()


    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    p = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=f"{p}/auth", tags=["auth"])
    app.include_router(users.router, prefix=f"{p}/users", tags=["users"])
    app.include_router(chats.router, prefix=f"{p}/chats", tags=["chats"])
    app.include_router(messages.router, prefix=f"{p}/chats", tags=["messages"])
    app.include_router(files.router, prefix=f"{p}/files", tags=["files"])
    app.include_router(ws.router, prefix=p, tags=["ws"])


    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}
''')

# ============================================================== FRONTEND
T["frontend/src/types.ts"] = _t('''
    export interface User {
      id: number;
      username: string;
      email: string;
      display_name: string | null;
      bio: string | null;
      avatar_color: string | null;
      is_active: boolean;
      last_seen: string | null;
      created_at: string;
    }

    export interface Chat {
      id: number;
      title: string | null;
      is_group: boolean;
      created_at: string;
      last_message: Message | null;
      unread_count: number;
      peer: User | null;
    }

    export interface Attachment {
      id: number;
      filename: string;
      content_type: string;
      size: number;
      created_at: string;
    }

    export type MessageType = "text" | "image" | "file" | "voice" | "sticker";

    export interface Message {
      id: number;
      chat_id: number;
      author_id: number;
      author_username: string;
      author_display: string | null;
      author_avatar_color: string | null;
      text: string | null;
      message_type: MessageType;
      attachment: Attachment | null;
      reply_to_id: number | null;
      reply_preview: string | null;
      reply_author: string | null;
      edited_at: string | null;
      is_deleted: boolean;
      created_at: string;
    }
''')

T["frontend/src/api.ts"] = _t('''
    import axios from "axios";

    export const API_BASE = "http://localhost:8000/api/v1";
    export const WS_BASE = "ws://localhost:8000/api/v1/ws";

    export const api = axios.create({ baseURL: API_BASE });

    api.interceptors.request.use((config) => {
      const t = localStorage.getItem("access_token");
      if (t) config.headers.Authorization = `Bearer ${t}`;
      return config;
    });

    api.interceptors.response.use(
      (r) => r,
      (e) => {
        if (e.response?.status === 401) {
          localStorage.removeItem("access_token");
          window.dispatchEvent(new Event("auth:logout"));
        }
        return Promise.reject(e);
      }
    );

    export function fileUrl(id: number): string {
      const t = localStorage.getItem("access_token") || "";
      return `${API_BASE}/files/${id}?token=${encodeURIComponent(t)}`;
    }

    export function humanSize(bytes: number): string {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    }
''')

T["frontend/src/FileUpload.tsx"] = _t('''
    import { useRef, useState } from "react";
    import { api } from "./api";
    import type { Attachment } from "./types";

    export default function FileUpload({
      onUploaded, accept, asType
    }: {
      onUploaded: (a: Attachment, type: "image" | "file" | "voice") => void;
      accept?: string;
      asType: "image" | "file";
    }) {
      const ref = useRef<HTMLInputElement>(null);
      const [busy, setBusy] = useState(false);

      const pick = () => ref.current?.click();

      const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (!f) return;
        setBusy(true);
        try {
          const form = new FormData();
          form.append("file", f);
          const { data } = await api.post<Attachment>("/files/upload", form, {
            headers: { "Content-Type": "multipart/form-data" }
          });
          // если это картинка — тип image, иначе file
          const type = asType === "image" && data.content_type.startsWith("image/")
            ? "image"
            : "file";
          onUploaded(data, type);
        } catch (err: any) {
          alert(err.response?.data?.detail || "Не удалось загрузить файл");
        } finally {
          setBusy(false);
          if (ref.current) ref.current.value = "";
        }
      };

      return (
        <>
          <input
            ref={ref}
            type="file"
            accept={accept}
            onChange={onChange}
            className="hidden"
          />
          <button
            onClick={pick}
            disabled={busy}
            title={asType === "image" ? "Прикрепить фото" : "Прикрепить файл"}
            className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 disabled:opacity-50 dark:hover:bg-slate-700"
          >
            {busy ? "⏳" : asType === "image" ? "🖼" : "📎"}
          </button>
        </>
      );
    }
''')

T["frontend/src/VoiceRecorder.tsx"] = _t('''
    import { useEffect, useRef, useState } from "react";
    import { api } from "./api";
    import type { Attachment } from "./types";

    export default function VoiceRecorder({
      onUploaded
    }: {
      onUploaded: (a: Attachment) => void;
    }) {
      const [recording, setRecording] = useState(false);
      const [elapsed, setElapsed] = useState(0);
      const recorderRef = useRef<MediaRecorder | null>(null);
      const chunksRef = useRef<BlobPart[]>([]);
      const timerRef = useRef<number | null>(null);

      useEffect(() => {
        return () => {
          if (timerRef.current) window.clearInterval(timerRef.current);
          recorderRef.current?.stream.getTracks().forEach((t) => t.stop());
        };
      }, []);

      const start = async () => {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
          const rec = new MediaRecorder(stream, { mimeType: "audio/webm" });
          chunksRef.current = [];
          rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
          rec.onstop = async () => {
            stream.getTracks().forEach((t) => t.stop());
            const blob = new Blob(chunksRef.current, { type: "audio/webm" });
            const form = new FormData();
            form.append("file", blob, `voice-${Date.now()}.webm`);
            try {
              const { data } = await api.post<Attachment>("/files/upload", form, {
                headers: { "Content-Type": "multipart/form-data" }
              });
              onUploaded(data);
            } catch (err: any) {
              alert(err.response?.data?.detail || "Не удалось отправить голосовое");
            }
          };
          rec.start();
          recorderRef.current = rec;
          setRecording(true);
          setElapsed(0);
          timerRef.current = window.setInterval(() => setElapsed((x) => x + 1), 1000);
        } catch {
          alert("Нет доступа к микрофону");
        }
      };

      const stop = (cancel = false) => {
        if (timerRef.current) window.clearInterval(timerRef.current);
        setRecording(false);
        const rec = recorderRef.current;
        if (!rec) return;
        if (cancel) {
          rec.onstop = () => rec.stream.getTracks().forEach((t) => t.stop());
        }
        rec.stop();
        recorderRef.current = null;
      };

      if (recording) {
        return (
          <div className="flex items-center gap-2 rounded-full bg-red-500/10 px-3 py-1 text-sm">
            <span className="h-2 w-2 animate-pulse rounded-full bg-red-500" />
            <span className="font-mono text-red-600 dark:text-red-400">
              {String(Math.floor(elapsed / 60)).padStart(2, "0")}:
              {String(elapsed % 60).padStart(2, "0")}
            </span>
            <button
              onClick={() => stop(true)}
              className="rounded-full px-2 py-1 text-xs text-slate-600 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              Отмена
            </button>
            <button
              onClick={() => stop(false)}
              className="rounded-full bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700"
            >
              Отправить
            </button>
          </div>
        );
      }

      return (
        <button
          onClick={start}
          title="Голосовое сообщение"
          className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
        >
          🎤
        </button>
      );
    }
''')

T["frontend/src/StickerPicker.tsx"] = _t('''
    import { useEffect, useRef } from "react";

    const STICKERS = [
      "🐱", "🐶", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯",
      "🦁", "🐮", "🐷", "🐸", "🐵", "🐔", "🐧", "🐦", "🦆", "🦉",
      "🦄", "🐝", "🦋", "🐌", "🐞", "🐢", "🐍", "🦖", "🐙", "🦑",
      "🍎", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍒", "🍑",
      "🥑", "🍆", "🥕", "🌽", "🍕", "🍔", "🍟", "🌮", "🍣", "🍜",
      "⚽", "🏀", "🏈", "🎾", "🎱", "🏓", "🎯", "🎮", "🎲", "🎰",
      "🚗", "🚕", "🚙", "🚌", "🚎", "🏎", "🚓", "🚑", "🚒", "🚐",
      "✈️", "🚀", "🛸", "🚁", "⛵", "🚤", "🛥", "🚢", "🚂", "🚆",
    ];

    export default function StickerPicker({
      onPick, onClose
    }: { onPick: (e: string) => void; onClose: () => void }) {
      const ref = useRef<HTMLDivElement>(null);

      useEffect(() => {
        const h = (e: MouseEvent) => {
          if (ref.current && !ref.current.contains(e.target as Node)) onClose();
        };
        setTimeout(() => document.addEventListener("mousedown", h), 0);
        return () => document.removeEventListener("mousedown", h);
      }, [onClose]);

      return (
        <div
          ref={ref}
          className="animate-pop absolute bottom-16 right-2 z-30 grid max-h-72 w-96 grid-cols-6 gap-2 overflow-y-auto rounded-xl border border-slate-200 bg-white p-3 shadow-2xl dark:border-slate-700 dark:bg-tg-panel"
        >
          {STICKERS.map((e, i) => (
            <button
              key={i}
              onClick={() => onPick(e)}
              className="rounded-xl p-2 text-4xl transition hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              {e}
            </button>
          ))}
        </div>
      );
    }
''')

T["frontend/src/MessageBubble.tsx"] = _t('''
    import { useState } from "react";
    import Avatar from "./Avatar";
    import { fileUrl, humanSize } from "./api";
    import type { Message, User } from "./types";

    function iconFor(mime: string): string {
      if (mime.startsWith("image/")) return "🖼";
      if (mime.startsWith("audio/")) return "🎵";
      if (mime.startsWith("video/")) return "🎬";
      if (mime.includes("pdf")) return "📕";
      if (mime.includes("zip") || mime.includes("tar")) return "🗜";
      if (mime.includes("word") || mime.includes("document")) return "📘";
      if (mime.includes("sheet") || mime.includes("excel")) return "📗";
      return "📎";
    }

    function fmtDuration(sec: number): string {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    export default function MessageBubble({
      msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer, onOpenImage
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
    }) {
      const [menuOpen, setMenuOpen] = useState(false);
      const [audioPlaying, setAudioPlaying] = useState(false);
      const [audioCurrent, setAudioCurrent] = useState(0);
      const [audioDuration, setAudioDuration] = useState(0);
      const audioRef = useState<HTMLAudioElement | null>(null)[0];

      const author: Pick<User, "username" | "display_name" | "avatar_color"> = {
        username: msg.author_username,
        display_name: msg.author_display,
        avatar_color: msg.author_avatar_color,
      };

      const bubbleColor = mine
        ? "bg-brand-600 text-white"
        : "bg-white text-slate-800 dark:bg-tg-bubble dark:text-slate-100";

      const radius = isLast
        ? mine
          ? "rounded-2xl rounded-br-sm"
          : "rounded-2xl rounded-bl-sm"
        : "rounded-2xl";

      const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
      const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
      const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
      const isFile = msg.message_type === "file" && msg.attachment && !msg.is_deleted;

      if (isSticker) {
        return (
          <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
            {!mine ? (
              <div className="w-8 shrink-0">
                {showAvatar && <Avatar user={author} size={32} />}
              </div>
            ) : null}
            <div className="relative">
              <div className="animate-pop text-7xl leading-none">{msg.text}</div>
              <div className={"mt-0.5 flex items-center gap-1 text-[10px] " + (mine ? "justify-end" : "")}>
                <span className="text-slate-400">
                  {new Date(msg.created_at).toLocaleTimeString([], {
                    hour: "2-digit", minute: "2-digit"
                  })}
                </span>
                {mine && <span className={readByPeer ? "text-sky-500" : "text-slate-400"}>
                  {readByPeer ? "✓✓" : "✓"}
                </span>}
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
          {!mine ? (
            <div className="w-8 shrink-0">
              {showAvatar && <Avatar user={author} size={32} />}
            </div>
          ) : null}

          <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
            {!mine && showAvatar && (
              <div className="mb-0.5 ml-2 text-xs font-medium text-brand-600 dark:text-brand-500">
                {msg.author_display || msg.author_username}
              </div>
            )}

            <div
              className={
                "animate-pop relative overflow-hidden text-sm shadow-sm " +
                bubbleColor + " " + radius +
                (isImage ? "" : " px-3 py-2")
              }
            >
              {msg.reply_to_id && !msg.is_deleted && (
                <div
                  className={
                    "mx-2 mb-1 mt-2 rounded border-l-2 px-2 py-1 text-xs " +
                    (mine
                      ? "border-white/60 bg-white/10"
                      : "border-brand-500 bg-slate-50 dark:bg-slate-800")
                  }
                >
                  <div className="font-medium opacity-90">{msg.reply_author || "?"}</div>
                  <div className="truncate opacity-75">{msg.reply_preview || "..."}</div>
                </div>
              )}

              {isImage && msg.attachment && (
                <img
                  src={fileUrl(msg.attachment.id)}
                  alt={msg.attachment.filename}
                  onClick={() => onOpenImage(fileUrl(msg.attachment!.id))}
                  className="block max-h-80 w-full cursor-pointer object-cover"
                />
              )}

              {isVoice && msg.attachment && (
                <div className="flex items-center gap-2 px-2 py-3" style={{ minWidth: 220 }}>
                  <button
                    onClick={() => {
                      const a = (window as any).__voiceAudio as HTMLAudioElement;
                      if (a && a.dataset.id === String(msg.attachment!.id)) {
                        a.paused ? a.play() : a.pause();
                        return;
                      }
                      if (a) a.pause();
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
                    className={
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-full " +
                      (mine ? "bg-white/20" : "bg-brand-600 text-white")
                    }
                  >
                    {audioPlaying ? "❚❚" : "▶"}
                  </button>
                  <div className={"flex-1 text-xs " + (mine ? "text-white/90" : "text-slate-500")}>
                    <div className="flex items-center gap-1">
                      <span className="text-2xl">🎤</span>
                      <span className="font-mono">
                        {fmtDuration(audioPlaying ? audioCurrent : (audioDuration || 0))}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {isFile && msg.attachment && (
                <a
                  href={fileUrl(msg.attachment.id)}
                  target="_blank"
                  rel="noreferrer"
                  className={
                    "flex items-center gap-3 px-2 py-3 transition " +
                    (mine ? "hover:bg-white/10" : "hover:bg-slate-50 dark:hover:bg-slate-800")
                  }
                >
                  <div className="text-3xl">{iconFor(msg.attachment.content_type)}</div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">{msg.attachment.filename}</div>
                    <div className={"text-xs " + (mine ? "text-white/70" : "text-slate-500")}>
                      {humanSize(msg.attachment.size)}
                    </div>
                  </div>
                </a>
              )}

              {!isImage && !isVoice && !isFile && (
                <div className={msg.is_deleted ? "italic opacity-60" : "whitespace-pre-wrap break-words"}>
                  {msg.text}
                </div>
              )}

              <div className="mt-0.5 flex items-center justify-end gap-1 px-1 text-[10px]">
                {msg.edited_at && <span className="opacity-70">изм.</span>}
                <span className={mine ? "text-white/70" : "text-slate-400"}>
                  {new Date(msg.created_at).toLocaleTimeString([], {
                    hour: "2-digit", minute: "2-digit"
                  })}
                </span>
                {mine && !msg.is_deleted && (
                  <span className={readByPeer ? "text-sky-200" : "text-white/60"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>

            {!msg.is_deleted && (
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className={
                  "absolute top-1 hidden rounded-full bg-white/90 px-1.5 py-0.5 text-xs text-slate-600 shadow group-hover:block dark:bg-slate-700 dark:text-slate-200 " +
                  (mine ? "-left-6" : "-right-6")
                }
              >
                ⋮
              </button>
            )}

            {menuOpen && (
              <div
                className={
                  "absolute z-20 mt-1 w-32 overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-xl dark:border-slate-700 dark:bg-tg-panel " +
                  (mine ? "right-0" : "left-0")
                }
              >
                <button
                  onClick={() => { onReply(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  Ответить
                </button>
                {mine && msg.message_type === "text" && (
                  <button
                    onClick={() => { onEdit(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700"
                  >
                    Изменить
                  </button>
                )}
                {mine && (
                  <button
                    onClick={() => { onDelete(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-1.5 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                  >
                    Удалить
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
''')

T["frontend/src/Lightbox.tsx"] = _t('''
    import { useEffect } from "react";

    export default function Lightbox({
      src, onClose
    }: { src: string; onClose: () => void }) {
      useEffect(() => {
        const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, [onClose]);

      return (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 p-4"
          onClick={onClose}
        >
          <img src={src} alt="" className="max-h-full max-w-full object-contain" />
          <button
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full bg-white/10 p-3 text-2xl text-white hover:bg-white/20"
          >
            ✕
          </button>
        </div>
      );
    }
''')

T["frontend/src/ChatWindow.tsx"] = _t('''
    import { useEffect, useMemo, useRef, useState } from "react";
    import Avatar from "./Avatar";
    import MessageBubble from "./MessageBubble";
    import EmojiPicker from "./EmojiPicker";
    import StickerPicker from "./StickerPicker";
    import FileUpload from "./FileUpload";
    import VoiceRecorder from "./VoiceRecorder";
    import Lightbox from "./Lightbox";
    import { api } from "./api";
    import type { Chat, Message, User } from "./types";

    function dayLabel(iso: string) {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) return "Сегодня";
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "Вчера";
      return d.toLocaleDateString([], { day: "numeric", month: "long" });
    }

    export default function ChatWindow({
      chat, currentUser, send, subscribe, onlineUsers
    }: {
      chat: Chat;
      currentUser: User;
      send: (data: any) => void;
      subscribe: (h: (d: any) => void) => () => void;
      onlineUsers: Set<number>;
    }) {
      const [messages, setMessages] = useState<Message[]>([]);
      const [text, setText] = useState("");
      const [replyTo, setReplyTo] = useState<Message | null>(null);
      const [editing, setEditing] = useState<Message | null>(null);
      const [emojiOpen, setEmojiOpen] = useState(false);
      const [stickerOpen, setStickerOpen] = useState(false);
      const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
      const [peerReadUpTo, setPeerReadUpTo] = useState<number>(0);
      const [lightbox, setLightbox] = useState<string | null>(null);
      const bottomRef = useRef<HTMLDivElement>(null);
      const typingTimeout = useRef<number | null>(null);
      const lastTypingSent = useRef<number>(0);

      useEffect(() => {
        api.get<Message[]>(`/chats/${chat.id}/messages`).then((r) => setMessages(r.data));
        send({ type: "subscribe", chat_id: chat.id });
        api.post(`/chats/${chat.id}/read`).catch(() => {});
        return () => send({ type: "unsubscribe", chat_id: chat.id });
      }, [chat.id]);

      useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "auto" });
      }, [messages.length]);

      useEffect(() => {
        const last = messages[messages.length - 1];
        if (!last) return;
        if (last.author_id !== currentUser.id) {
          send({ type: "read", chat_id: chat.id, message_id: last.id });
        }
      }, [messages.length]);

      useEffect(() => {
        const off = subscribe((d) => {
          if (d.type === "message" && d.chat_id === chat.id) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === d.id)) return prev;
              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, created_at: d.created_at,
              }];
            });
            if (d.author_id !== currentUser.id) {
              send({ type: "read", chat_id: chat.id, message_id: d.id });
            }
          } else if (d.type === "message_edited" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, text: d.text, edited_at: d.edited_at } : m)
            );
          } else if (d.type === "message_deleted" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id
                ? { ...m, is_deleted: true, text: "Сообщение удалено" }
                : m)
            );
          } else if (d.type === "typing" && d.chat_id === chat.id) {
            setTypingUsers((prev) => {
              const next = new Set(prev);
              if (d.is_typing) next.add(d.username);
              else next.delete(d.username);
              return next;
            });
          } else if (d.type === "read" && d.chat_id === chat.id) {
            setPeerReadUpTo((prev) => Math.max(prev, d.message_id));
          }
        });
        return off;
      }, [chat.id, currentUser.id, subscribe, send]);

      const grouped = useMemo(() => {
        const out: { day: string; items: Message[] }[] = [];
        for (const m of messages) {
          const day = dayLabel(m.created_at);
          const last = out[out.length - 1];
          if (last && last.day === day) last.items.push(m);
          else out.push({ day, items: [m] });
        }
        return out;
      }, [messages]);

      const doSend = () => {
        const t = text.trim();
        if (!t) return;
        if (editing) {
          send({ type: "edit", message_id: editing.id, text: t });
          setEditing(null);
        } else {
          send({ type: "send", chat_id: chat.id, text: t, reply_to_id: replyTo?.id ?? null, message_type: "text" });
          setReplyTo(null);
        }
        setText("");
        send({ type: "typing", chat_id: chat.id, is_typing: false });
      };

      const sendAttachment = (attachmentId: number, type: "image" | "file" | "voice") => {
        send({
          type: "send",
          chat_id: chat.id,
          text: null,
          message_type: type,
          attachment_id: attachmentId,
          reply_to_id: replyTo?.id ?? null,
        });
        setReplyTo(null);
      };

      const sendSticker = (sticker: string) => {
        send({
          type: "send",
          chat_id: chat.id,
          text: sticker,
          message_type: "sticker",
          reply_to_id: replyTo?.id ?? null,
        });
        setStickerOpen(false);
        setReplyTo(null);
      };

      const onKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          doSend();
        }
      };

      const onTextChange = (v: string) => {
        setText(v);
        const now = Date.now();
        if (now - lastTypingSent.current > 2000) {
          send({ type: "typing", chat_id: chat.id, is_typing: true });
          lastTypingSent.current = now;
        }
        if (typingTimeout.current) window.clearTimeout(typingTimeout.current);
        typingTimeout.current = window.setTimeout(() => {
          send({ type: "typing", chat_id: chat.id, is_typing: false });
        }, 3000);
      };

      const peerOnline = chat.peer ? onlineUsers.has(chat.peer.id) : false;
      const headerTitle = chat.peer
        ? chat.peer.display_name || chat.peer.username
        : chat.title || `Чат #${chat.id}`;
      const headerSub = typingUsers.size > 0
        ? "печатает…"
        : chat.peer
        ? (peerOnline ? "в сети" : "не в сети")
        : `${chat.is_group ? "группа" : ""}`;

      const avatarUser = chat.peer || {
        username: chat.title || "G",
        display_name: chat.title || "Group",
        avatar_color: "#64748b",
      };

      return (
        <main className="flex flex-1 flex-col bg-slate-100 dark:bg-tg-bg">
          <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-tg-side">
            <Avatar user={avatarUser as any} size={40} showOnline={!!chat.peer} online={peerOnline} />
            <div className="min-w-0 flex-1">
              <div className="truncate font-medium text-slate-800 dark:text-slate-100">
                {headerTitle}
              </div>
              <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                {headerSub}
              </div>
            </div>
          </header>

          <div className="flex-1 overflow-y-auto px-4 py-4">
            {grouped.map((g) => (
              <div key={g.day} className="mb-4">
                <div className="mb-3 text-center">
                  <span className="rounded-full bg-slate-200/80 px-3 py-1 text-xs text-slate-600 dark:bg-tg-panel dark:text-slate-400">
                    {g.day}
                  </span>
                </div>
                <div className="space-y-1">
                  {g.items.map((m, idx) => {
                    const prev = g.items[idx - 1];
                    const showAvatar = !prev || prev.author_id !== m.author_id;
                    const isLast = idx === g.items.length - 1 || g.items[idx + 1].author_id !== m.author_id;
                    return (
                      <MessageBubble
                        key={m.id}
                        msg={m}
                        mine={m.author_id === currentUser.id}
                        showAvatar={showAvatar}
                        isLast={isLast}
                        readByPeer={peerReadUpTo >= m.id}
                        onReply={(mm) => { setReplyTo(mm); setEditing(null); }}
                        onEdit={(mm) => { setEditing(mm); setReplyTo(null); setText(mm.text || ""); }}
                        onDelete={(mm) => send({ type: "delete", message_id: mm.id })}
                        onOpenImage={(url) => setLightbox(url)}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {(replyTo || editing) && (
            <div className="flex items-center gap-2 border-t border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-tg-side">
              <div className="flex-1 truncate border-l-2 border-brand-500 pl-2 text-sm">
                <div className="text-xs font-medium text-brand-600">
                  {editing ? "Редактирование" : `Ответ ${replyTo?.author_display || replyTo?.author_username}`}
                </div>
                <div className="truncate text-slate-500 dark:text-slate-400">
                  {editing ? editing.text : replyTo?.text}
                </div>
              </div>
              <button
                onClick={() => { setReplyTo(null); setEditing(null); setText(""); }}
                className="rounded-full p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                ✕
              </button>
            </div>
          )}

          <div className="relative border-t border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-tg-side">
            {typingUsers.size > 0 && (
              <div className="absolute -top-5 left-4 flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-slate-500" />
                <span className="ml-1">{Array.from(typingUsers).join(", ")}</span>
              </div>
            )}
            <div className="flex items-end gap-1">
              <FileUpload asType="image" accept="image/*" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <FileUpload asType="file" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <button
                onClick={() => { setStickerOpen(!stickerOpen); setEmojiOpen(false); }}
                className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                🐱
              </button>
              <button
                onClick={() => { setEmojiOpen(!emojiOpen); setStickerOpen(false); }}
                className="rounded-full p-2 text-xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                😊
              </button>
              <textarea
                value={text}
                onChange={(e) => onTextChange(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder="Написать сообщение..."
                className="max-h-32 flex-1 resize-none rounded-2xl bg-slate-100 px-4 py-2 text-sm outline-none transition focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
              />
              <VoiceRecorder onUploaded={(a) => sendAttachment(a.id, "voice")} />
              <button
                onClick={doSend}
                disabled={!text.trim()}
                className="rounded-full bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:opacity-40"
              >
                ➤
              </button>
            </div>

            {emojiOpen && (
              <EmojiPicker
                onPick={(e) => { setText((t) => t + e); }}
                onClose={() => setEmojiOpen(false)}
              />
            )}
            {stickerOpen && (
              <StickerPicker
                onPick={sendSticker}
                onClose={() => setStickerOpen(false)}
              />
            )}
          </div>

          {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}
        </main>
    );
''')

# ============================================================== INFRA
T["infra/docker-compose.yml"] = _t("""
    services:
      db:
        image: postgres:16-alpine
        restart: unless-stopped
        environment:
          POSTGRES_USER: messenger
          POSTGRES_PASSWORD: messenger
          POSTGRES_DB: messenger
        volumes:
          - pgdata:/var/lib/postgresql/data
        ports:
          - "5432:5432"
        healthcheck:
          test: ["CMD-SHELL", "pg_isready -U messenger"]
          interval: 5s
          timeout: 5s
          retries: 10

      api:
        build:
          context: ../backend
        env_file:
          - ../backend/.env
        depends_on:
          db:
            condition: service_healthy
        ports:
          - "8000:8000"
        volumes:
          - ../backend:/app
        command: >
          sh -c "alembic upgrade head &&
                 uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

      frontend:
        build:
          context: ../frontend
        ports:
          - "5173:80"
        depends_on:
          - api

    volumes:
      pgdata:
""")

T["backend/.env.example"] = _t("""
    APP_NAME=Messenger
    DEBUG=true
    API_V1_PREFIX=/api/v1
    SECRET_KEY=change-me-in-production
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    POSTGRES_USER=messenger
    POSTGRES_PASSWORD=messenger
    POSTGRES_DB=messenger
    UPLOAD_DIR=/app/uploads
    MAX_UPLOAD_SIZE_MB=50
    CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
""")


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

    print(f"\nСпринт 2: медиа, файлы, голос, стикеры")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("ВАЖНО: 'down' без -v — данные и файлы сохранятся,")
    print("       миграция 0003 добавит новые таблицы/колонки.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())