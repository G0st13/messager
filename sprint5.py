#!/usr/bin/env python3
"""sprint5.py - WebRTC audio/video calls + screen sharing."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0006_sprint5.py"] = _t('''
    """sprint 5: calls

    Revision ID: 0006
    Revises: 0005
    Create Date: 2025-06-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0006"
    down_revision: Union[str, None] = "0005"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "calls",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "caller_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "callee_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("kind", sa.String(10), nullable=False, server_default="audio"),
            sa.Column("status", sa.String(20), nullable=False, server_default="ringing"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_sec", sa.Integer(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_calls_caller", "calls", ["caller_id"])
        op.create_index("ix_calls_callee", "calls", ["callee_id"])
        op.create_index("ix_calls_created", "calls", ["created_at"])


    def downgrade() -> None:
        op.drop_table("calls")
''')

# ============================================================== MODELS
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
    from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
        description: Mapped[str | None] = mapped_column(String(500), default=None)
        avatar_color: Mapped[str | None] = mapped_column(String(20), default=None)
        invite_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
        is_group: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
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


    class Post(Base):
        __tablename__ = "posts"

        id: Mapped[int] = mapped_column(primary_key=True)
        author_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        text: Mapped[str | None] = mapped_column(Text, nullable=True)
        attachment_id: Mapped[int | None] = mapped_column(
            ForeignKey("files.id", ondelete="SET NULL"), nullable=True
        )
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )


    class PostLike(Base):
        __tablename__ = "post_likes"
        __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_like"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"))
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class PostComment(Base):
        __tablename__ = "post_comments"

        id: Mapped[int] = mapped_column(primary_key=True)
        post_id: Mapped[int] = mapped_column(
            ForeignKey("posts.id", ondelete="CASCADE"), index=True
        )
        author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        text: Mapped[str] = mapped_column(Text)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Follow(Base):
        __tablename__ = "follows"
        __table_args__ = (UniqueConstraint("follower_id", "following_id", name="uq_follow"),)

        id: Mapped[int] = mapped_column(primary_key=True)
        follower_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        following_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class Call(Base):
        __tablename__ = "calls"

        id: Mapped[int] = mapped_column(primary_key=True)
        caller_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        callee_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        kind: Mapped[str] = mapped_column(String(10), default="audio")
        status: Mapped[str] = mapped_column(String(20), default="ringing")
        started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )
''')

# ============================================================== SCHEMAS
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


    class UserProfile(BaseModel):
        id: int
        username: str
        display_name: str | None
        bio: str | None
        avatar_color: str | None
        created_at: datetime
        posts_count: int
        followers_count: int
        following_count: int
        is_following: bool
        is_me: bool


    class UserUpdate(BaseModel):
        display_name: str | None = Field(default=None, max_length=100)
        bio: str | None = Field(default=None, max_length=500)


    class ChatCreate(BaseModel):
        title: str | None = None
        is_group: bool = False
        member_usernames: list[str] = Field(default_factory=list)


    class ChatUpdate(BaseModel):
        title: str | None = Field(default=None, max_length=255)
        description: str | None = Field(default=None, max_length=500)
        avatar_color: str | None = Field(default=None, max_length=20)


    class ChatMemberRead(BaseModel):
        user_id: int
        username: str
        display_name: str | None
        avatar_color: str | None
        role: str
        joined_at: datetime


    class AddMemberRequest(BaseModel):
        username: str


    class InviteRead(BaseModel):
        token: str
        url: str


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
        description: str | None = None
        avatar_color: str | None = None
        is_group: bool
        created_at: datetime
        last_message: MessageRead | None = None
        unread_count: int = 0
        peer: UserRead | None = None
        member_count: int = 0
        my_role: str | None = None


    class MessageCreate(BaseModel):
        text: str | None = Field(default=None, max_length=4000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=4000)


    class PostCreate(BaseModel):
        text: str | None = Field(default=None, max_length=5000)
        attachment_id: int | None = None


    class PostAuthor(BaseModel):
        id: int
        username: str
        display_name: str | None
        avatar_color: str | None


    class PostCommentRead(BaseModel):
        id: int
        post_id: int
        author: PostAuthor
        text: str
        created_at: datetime


    class PostRead(BaseModel):
        id: int
        author: PostAuthor
        text: str | None
        attachment: FileRead | None
        is_deleted: bool
        created_at: datetime
        likes_count: int
        comments_count: int
        is_liked: bool
        is_mine: bool


    class PostCommentCreate(BaseModel):
        text: str = Field(min_length=1, max_length=2000)


    class CallInitiate(BaseModel):
        callee_id: int
        kind: str = "audio"


    class CallRead(BaseModel):
        id: int
        caller_id: int
        callee_id: int
        kind: str
        status: str
        started_at: datetime | None
        ended_at: datetime | None
        duration_sec: int | None
        created_at: datetime


    class CallPeer(BaseModel):
        id: int
        username: str
        display_name: str | None
        avatar_color: str | None


    class CallDetailed(CallRead):
        caller: CallPeer
        callee: CallPeer
''')

# ============================================================== CALLS ROUTER
T["backend/app/routers/calls.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Call, User
    from app.schemas import CallDetailed, CallInitiate, CallPeer, CallRead
    from app.websocket_manager import manager


    router = APIRouter()


    async def _to_detailed(db: AsyncSession, c: Call) -> CallDetailed:
        caller = (await db.execute(select(User).where(User.id == c.caller_id))).scalar_one()
        callee = (await db.execute(select(User).where(User.id == c.callee_id))).scalar_one()

        def peer(u: User) -> CallPeer:
            return CallPeer(
                id=u.id, username=u.username,
                display_name=u.display_name, avatar_color=u.avatar_color,
            )

        return CallDetailed(
            id=c.id, caller_id=c.caller_id, callee_id=c.callee_id,
            kind=c.kind, status=c.status,
            started_at=c.started_at, ended_at=c.ended_at,
            duration_sec=c.duration_sec, created_at=c.created_at,
            caller=peer(caller), callee=peer(callee),
        )


    @router.post("", response_model=CallDetailed, status_code=status.HTTP_201_CREATED)
    async def initiate_call(
        payload: CallInitiate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        if payload.callee_id == current.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot call yourself")
        callee = (await db.execute(
            select(User).where(User.id == payload.callee_id)
        )).scalar_one_or_none()
        if callee is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

        c = Call(
            caller_id=current.id,
            callee_id=payload.callee_id,
            kind=payload.kind if payload.kind in ("audio", "video") else "audio",
            status="ringing",
        )
        db.add(c)
        await db.flush()
        await db.refresh(c)

        # сообщим вызываемому через WS
        await manager.send_to_user(payload.callee_id, {
            "type": "call:incoming",
            "call_id": c.id,
            "kind": c.kind,
            "caller": {
                "id": current.id,
                "username": current.username,
                "display_name": current.display_name,
                "avatar_color": current.avatar_color,
            },
        })

        return await _to_detailed(db, c)


    @router.post("/{call_id}/accept", response_model=CallDetailed)
    async def accept_call(
        call_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        c = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "call not found")
        if c.callee_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your call")
        if c.status != "ringing":
            raise HTTPException(status.HTTP_409_CONFLICT, "call already handled")

        c.status = "active"
        c.started_at = datetime.now(timezone.utc)
        await db.flush()

        await manager.send_to_user(c.caller_id, {
            "type": "call:accepted",
            "call_id": c.id,
        })

        return await _to_detailed(db, c)


    @router.post("/{call_id}/reject", response_model=CallDetailed)
    async def reject_call(
        call_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        c = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "call not found")
        if c.callee_id != current.id and c.caller_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your call")
        if c.status not in ("ringing",):
            raise HTTPException(status.HTTP_409_CONFLICT, "call already handled")

        c.status = "rejected"
        c.ended_at = datetime.now(timezone.utc)
        await db.flush()

        peer_id = c.caller_id if current.id == c.callee_id else c.callee_id
        await manager.send_to_user(peer_id, {
            "type": "call:rejected",
            "call_id": c.id,
        })

        return await _to_detailed(db, c)


    @router.post("/{call_id}/end", response_model=CallDetailed)
    async def end_call(
        call_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        c = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "call not found")
        if c.caller_id != current.id and c.callee_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your call")

        now = datetime.now(timezone.utc)
        c.ended_at = now
        if c.started_at:
            c.duration_sec = int((now - c.started_at).total_seconds())
        c.status = "ended" if c.status == "active" else "cancelled"
        await db.flush()

        peer_id = c.caller_id if current.id == c.callee_id else c.callee_id
        await manager.send_to_user(peer_id, {
            "type": "call:ended",
            "call_id": c.id,
            "duration_sec": c.duration_sec,
        })

        return await _to_detailed(db, c)


    @router.get("/history", response_model=list[CallDetailed])
    async def call_history(
        current: CurrentUser,
        limit: int = 50,
        db: AsyncSession = Depends(get_session),
    ):
        stmt = (
            select(Call)
            .where(or_(Call.caller_id == current.id, Call.callee_id == current.id))
            .order_by(Call.created_at.desc())
            .limit(limit)
        )
        calls = (await db.execute(stmt)).scalars().all()
        return [await _to_detailed(db, c) for c in calls]


    @router.get("/{call_id}", response_model=CallDetailed)
    async def get_call(
        call_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        c = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "call not found")
        if c.caller_id != current.id and c.callee_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your call")
        return await _to_detailed(db, c)
''')

# ============================================================== WS ROUTER (дополнен сигналингом)
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
        f = (await db.execute(select(FileModel).where(FileModel.id == attachment_id))).scalar_one_or_none()
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
            user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if user is None or not user.is_active:
                await ws.close(code=4401)
                return
            username = user.username

        await manager.connect(user_id, ws)
        await manager.broadcast_all({"type": "presence", "user_id": user_id, "online": True})

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
                    text = (data.get("text") or "").strip() or None
                    reply_to_id = data.get("reply_to_id")
                    attachment_id = data.get("attachment_id")
                    message_type = data.get("message_type", "text")

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
                            await ws.send_json({"type": "error", "detail": "not a member"})
                            continue

                        msg = Message(
                            chat_id=chat_id, author_id=user_id, text=text,
                            message_type=message_type, attachment_id=attachment_id,
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
                            r = (await db.execute(
                                select(Message).where(Message.id == reply_to_id)
                            )).scalar_one_or_none()
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
                                ra = (await db.execute(
                                    select(User).where(User.id == r.author_id)
                                )).scalar_one()
                                reply_author = ra.display_name or ra.username

                        payload_out = {
                            "type": "message", "id": msg.id, "chat_id": chat_id,
                            "text": text, "message_type": message_type,
                            "attachment": attachment,
                            "reply_to_id": reply_to_id,
                            "reply_preview": reply_preview, "reply_author": reply_author,
                            "edited_at": None, "is_deleted": False,
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
                        m = (await db.execute(
                            select(Message).where(Message.id == message_id)
                        )).scalar_one_or_none()
                        if m is None or m.author_id != user_id:
                            continue
                        m.text = text
                        m.edited_at = datetime.now(timezone.utc)
                        await db.commit()
                        await manager.send_to_chat(m.chat_id, {
                            "type": "message_edited", "message_id": m.id,
                            "chat_id": m.chat_id, "text": text,
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
                        await manager.send_to_chat(m.chat_id, {
                            "type": "message_deleted", "message_id": m.id,
                            "chat_id": m.chat_id,
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
                    await manager.send_to_chat(
                        chat_id,
                        {"type": "read", "chat_id": chat_id, "user_id": user_id, "message_id": message_id},
                        exclude_ws=ws,
                    )

                elif kind == "ping":
                    await ws.send_json({"type": "pong"})

                # ---------- WebRTC signaling ----------
                elif kind in ("webrtc:offer", "webrtc:answer", "webrtc:ice", "webrtc:screen"):
                    target_id = data.get("target_id")
                    call_id = data.get("call_id")
                    if not isinstance(target_id, int):
                        continue
                    # пробрасываем как есть, добавляя from
                    await manager.send_to_user(target_id, {
                        "type": kind,
                        "call_id": call_id,
                        "from_id": user_id,
                        "payload": data.get("payload"),
                    })

        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(ws)
            async with SessionLocal() as db:
                u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                if u:
                    u.last_seen = datetime.now(timezone.utc)
                    await db.commit()
            await manager.broadcast_all({
                "type": "presence", "user_id": user_id, "online": False,
                "last_seen": datetime.now(timezone.utc).isoformat(),
            })
''')

# ============================================================== MAIN
T["backend/app/main.py"] = _t('''
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.db import engine
    from app.routers import auth, calls, chats, files, messages, posts, users, ws
    from app.websocket_manager import manager


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.upload_path
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
    app.include_router(posts.router, prefix=f"{p}/posts", tags=["posts"])
    app.include_router(calls.router, prefix=f"{p}/calls", tags=["calls"])
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

    export interface UserProfile {
      id: number;
      username: string;
      display_name: string | null;
      bio: string | null;
      avatar_color: string | null;
      created_at: string;
      posts_count: number;
      followers_count: number;
      following_count: number;
      is_following: boolean;
      is_me: boolean;
    }

    export interface Chat {
      id: number;
      title: string | null;
      description: string | null;
      avatar_color: string | null;
      is_group: boolean;
      created_at: string;
      last_message: Message | null;
      unread_count: number;
      peer: User | null;
      member_count: number;
      my_role: string | null;
    }

    export interface ChatMember {
      user_id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
      role: "owner" | "admin" | "member";
      joined_at: string;
    }

    export interface Attachment {
      id: number;
      filename: string;
      content_type: string;
      size: number;
      created_at: string;
    }

    export type MessageType = "text" | "image" | "file" | "voice" | "sticker" | "system";

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

    export interface PostAuthor {
      id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
    }

    export interface Post {
      id: number;
      author: PostAuthor;
      text: string | null;
      attachment: Attachment | null;
      is_deleted: boolean;
      created_at: string;
      likes_count: number;
      comments_count: number;
      is_liked: boolean;
      is_mine: boolean;
    }

    export interface PostComment {
      id: number;
      post_id: number;
      author: PostAuthor;
      text: string;
      created_at: string;
    }

    export type CallKind = "audio" | "video";
    export type CallStatus = "ringing" | "active" | "ended" | "rejected" | "cancelled";

    export interface CallPeer {
      id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
    }

    export interface CallInfo {
      id: number;
      caller_id: number;
      callee_id: number;
      kind: CallKind;
      status: CallStatus;
      started_at: string | null;
      ended_at: string | null;
      duration_sec: number | null;
      created_at: string;
      caller: CallPeer;
      callee: CallPeer;
    }
''')

# ---------- WebRTC hook
T["frontend/src/useWebRTC.ts"] = _t('''
    import { useCallback, useEffect, useRef, useState } from "react";

    const ICE_SERVERS: RTCIceServer[] = [
      { urls: "stun:stun.l.google.com:19302" },
      { urls: "stun:stun1.l.google.com:19302" },
    ];

    export interface CallSession {
      callId: number;
      peerId: number;
      peerName: string;
      kind: "audio" | "video";
      isCaller: boolean;
    }

    export function useWebRTC(send: (data: any) => void, subscribe: (h: (d: any) => void) => () => void) {
      const [session, setSession] = useState<CallSession | null>(null);
      const [localStream, setLocalStream] = useState<MediaStream | null>(null);
      const [remoteStream, setRemoteStream] = useState<MediaStream | null>(null);
      const [muted, setMuted] = useState(false);
      const [camOff, setCamOff] = useState(false);
      const [sharing, setSharing] = useState(false);
      const [status, setStatus] = useState<"idle" | "ringing" | "connecting" | "active" | "ended">("idle");

      const pcRef = useRef<RTCPeerConnection | null>(null);
      const localStreamRef = useRef<MediaStream | null>(null);
      const remoteStreamRef = useRef<MediaStream | null>(null);
      const pendingCandidatesRef = useRef<RTCIceCandidateInit[]>([]);
      const sessionRef = useRef<CallSession | null>(null);

      useEffect(() => { sessionRef.current = session; }, [session]);

      const cleanup = useCallback(() => {
        pcRef.current?.close();
        pcRef.current = null;
        localStreamRef.current?.getTracks().forEach((t) => t.stop());
        localStreamRef.current = null;
        remoteStreamRef.current = null;
        pendingCandidatesRef.current = [];
        setLocalStream(null);
        setRemoteStream(null);
        setSession(null);
        setStatus("idle");
        setMuted(false);
        setCamOff(false);
        setSharing(false);
      }, []);

      const ensurePeer = useCallback((callId: number, peerId: number): RTCPeerConnection => {
        if (pcRef.current) return pcRef.current;
        const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
        pcRef.current = pc;

        const remote = new MediaStream();
        remoteStreamRef.current = remote;
        setRemoteStream(remote);

        pc.ontrack = (e) => {
          e.streams[0].getTracks().forEach((t) => remote.addTrack(t));
          setRemoteStream(remote);
        };

        pc.onicecandidate = (e) => {
          if (e.candidate) {
            send({
              type: "webrtc:ice",
              call_id: callId,
              target_id: peerId,
              payload: e.candidate.toJSON(),
            });
          }
        };

        pc.onconnectionstatechange = () => {
          if (pc.connectionState === "connected") setStatus("active");
          if (pc.connectionState === "disconnected" || pc.connectionState === "failed") {
            cleanup();
          }
        };

        return pc;
      }, [send, cleanup]);

      const getMedia = useCallback(async (kind: "audio" | "video"): Promise<MediaStream> => {
        const constraints: MediaStreamConstraints = {
          audio: true,
          video: kind === "video" ? { width: 1280, height: 720 } : false,
        };
        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        localStreamRef.current = stream;
        setLocalStream(stream);
        return stream;
      }, []);

      const attachLocal = useCallback((pc: RTCPeerConnection, stream: MediaStream) => {
        stream.getTracks().forEach((track) => pc.addTrack(track, stream));
      }, []);

      // ---- public API ----
      const startCall = useCallback(async (
        callId: number, peerId: number, peerName: string, kind: "audio" | "video"
      ) => {
        setSession({ callId, peerId, peerName, kind, isCaller: true });
        setStatus("connecting");
        const stream = await getMedia(kind);
        const pc = ensurePeer(callId, peerId);
        attachLocal(pc, stream);
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        send({
          type: "webrtc:offer",
          call_id: callId,
          target_id: peerId,
          payload: offer,
        });
      }, [getMedia, ensurePeer, attachLocal, send]);

      const acceptCall = useCallback(async (
        callId: number, peerId: number, peerName: string, kind: "audio" | "video", offer: RTCSessionDescriptionInit
      ) => {
        setSession({ callId, peerId, peerName, kind, isCaller: false });
        setStatus("connecting");
        const stream = await getMedia(kind);
        const pc = ensurePeer(callId, peerId);
        attachLocal(pc, stream);
        await pc.setRemoteDescription(new RTCSessionDescription(offer));
        // applying pending candidates
        for (const c of pendingCandidatesRef.current) {
          try { await pc.addIceCandidate(c); } catch {}
        }
        pendingCandidatesRef.current = [];
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        send({
          type: "webrtc:answer",
          call_id: callId,
          target_id: peerId,
          payload: answer,
        });
      }, [getMedia, ensurePeer, attachLocal, send]);

      const toggleMute = useCallback(() => {
        const stream = localStreamRef.current;
        if (!stream) return;
        const next = !muted;
        stream.getAudioTracks().forEach((t) => { t.enabled = !next; });
        setMuted(next);
      }, [muted]);

      const toggleCamera = useCallback(() => {
        const stream = localStreamRef.current;
        if (!stream) return;
        const next = !camOff;
        stream.getVideoTracks().forEach((t) => { t.enabled = !next; });
        setCamOff(next);
      }, [camOff]);

      const toggleScreenShare = useCallback(async () => {
        const pc = pcRef.current;
        if (!pc) return;
        if (sharing) {
          // вернуть камеру
          const camTrack = localStreamRef.current?.getVideoTracks()[0];
          const sender = pc.getSenders().find((s) => s.track?.kind === "video");
          if (sender && camTrack) {
            await sender.replaceTrack(camTrack);
          }
          setSharing(false);
          return;
        }
        try {
          const display = await navigator.mediaDevices.getDisplayMedia({ video: true });
          const screenTrack = display.getVideoTracks()[0];
          const sender = pc.getSenders().find((s) => s.track?.kind === "video");
          if (sender) {
            await sender.replaceTrack(screenTrack);
          } else {
            pc.addTrack(screenTrack, display);
          }
          screenTrack.onended = () => {
            const camTrack = localStreamRef.current?.getVideoTracks()[0];
            if (sender && camTrack) sender.replaceTrack(camTrack);
            setSharing(false);
          };
          setSharing(true);
        } catch {}
      }, [sharing]);

      const endCall = useCallback((notify: boolean = true) => {
        const s = sessionRef.current;
        if (s && notify) {
          send({ type: "webrtc:end", call_id: s.callId, target_id: s.peerId });
        }
        cleanup();
      }, [send, cleanup]);

      // ---- incoming signaling handlers ----
      useEffect(() => {
        const off = subscribe(async (d) => {
          // offer — входящий звонок принят
          if (d.type === "webrtc:offer") {
            const s = sessionRef.current;
            if (!s) {
              // значит offer пришёл раньше (редко) — сохраним в pending
              return;
            }
            const pc = pcRef.current;
            if (!pc) return;
            try {
              await pc.setRemoteDescription(new RTCSessionDescription(d.payload));
              for (const c of pendingCandidatesRef.current) {
                try { await pc.addIceCandidate(c); } catch {}
              }
              pendingCandidatesRef.current = [];
            } catch {}
          } else if (d.type === "webrtc:answer") {
            const pc = pcRef.current;
            if (!pc) return;
            try {
              await pc.setRemoteDescription(new RTCSessionDescription(d.payload));
              for (const c of pendingCandidatesRef.current) {
                try { await pc.addIceCandidate(c); } catch {}
              }
              pendingCandidatesRef.current = [];
            } catch {}
          } else if (d.type === "webrtc:ice") {
            const pc = pcRef.current;
            const candidate = d.payload as RTCIceCandidateInit;
            if (!pc || !pc.remoteDescription) {
              pendingCandidatesRef.current.push(candidate);
              return;
            }
            try { await pc.addIceCandidate(candidate); } catch {}
          } else if (d.type === "call:ended" || d.type === "call:rejected") {
            cleanup();
          }
        });
        return off;
      }, [subscribe, cleanup]);

      return {
        session, localStream, remoteStream, muted, camOff, sharing, status,
        startCall, acceptCall, toggleMute, toggleCamera, toggleScreenShare, endCall,
      };
    }
''')

# ---------- Incoming Call modal
T["frontend/src/IncomingCallModal.tsx"] = _t('''
    import Avatar from "./Avatar";

    export default function IncomingCallModal({
      caller, kind, onAccept, onReject
    }: {
      caller: { id: number; username: string; display_name: string | null; avatar_color: string | null };
      kind: "audio" | "video";
      onAccept: () => void;
      onReject: () => void;
    }) {
      return (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-sm">
          <div className="w-80 rounded-3xl bg-white p-6 text-center shadow-2xl dark:bg-tg-side">
            <div className="mx-auto mb-4 animate-pulse">
              <Avatar user={caller} size={96} />
            </div>
            <div className="text-lg font-semibold text-slate-800 dark:text-white">
              {caller.display_name || caller.username}
            </div>
            <div className="mb-6 text-sm text-slate-500">
              {kind === "video" ? "📹 Входящий видеозвонок" : "📞 Входящий звонок"}
            </div>
            <div className="flex justify-center gap-6">
              <button
                onClick={onReject}
                className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500 text-2xl text-white shadow-lg transition hover:bg-red-600"
                title="Отклонить"
              >
                ✕
              </button>
              <button
                onClick={onAccept}
                className="flex h-14 w-14 animate-bounce items-center justify-center rounded-full bg-green-500 text-2xl text-white shadow-lg transition hover:bg-green-600"
                title="Принять"
              >
                ✓
              </button>
            </div>
          </div>
        </div>
      );
    }
''')

# ---------- Call window
T["frontend/src/CallWindow.tsx"] = _t('''
    import { useEffect, useRef } from "react";

    function fmtDuration(sec: number): string {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    export default function CallWindow({
      peerName, kind, status, localStream, remoteStream, muted, camOff, sharing,
      durationSec, onToggleMute, onToggleCamera, onToggleScreen, onEnd
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

      useEffect(() => {
        if (localRef.current && localStream) localRef.current.srcObject = localStream;
      }, [localStream]);

      useEffect(() => {
        if (remoteRef.current && remoteStream) remoteRef.current.srcObject = remoteStream;
      }, [remoteStream]);

      const statusLabel =
        status === "ringing" ? "Звонок…"
        : status === "connecting" ? "Соединение…"
        : status === "active" ? fmtDuration(durationSec)
        : "Завершён";

      const btn = "flex h-14 w-14 items-center justify-center rounded-full text-2xl shadow-lg transition";

      return (
        <div className="fixed inset-0 z-[200] flex flex-col bg-slate-900">
          <header className="flex items-center justify-between bg-slate-800/80 px-6 py-3 text-white backdrop-blur">
            <div>
              <div className="text-lg font-semibold">{peerName}</div>
              <div className="text-xs text-slate-300">{statusLabel}</div>
            </div>
            <div className="rounded-full bg-white/10 px-3 py-1 text-xs text-white">
              {kind === "video" ? "📹 Видео" : "📞 Аудио"}
            </div>
          </header>

          <div className="relative flex-1 overflow-hidden">
            {kind === "video" && !sharing && (
              <video
                ref={remoteRef}
                autoPlay
                playsInline
                className="absolute inset-0 h-full w-full bg-black object-contain"
              />
            )}

            {kind === "video" && sharing && (
              <video
                ref={remoteRef}
                autoPlay
                playsInline
                className="absolute inset-0 h-full w-full bg-black object-contain"
              />
            )}

            {kind === "audio" && (
              <div className="flex h-full flex-col items-center justify-center text-white">
                <audio ref={remoteRef as any} autoPlay />
                <div className="mb-4 text-8xl">📞</div>
                <div className="text-3xl font-bold">{statusLabel}</div>
                <div className="mt-2 text-sm text-slate-400">{peerName}</div>
              </div>
            )}

            {kind === "video" && (
              <video
                ref={localRef}
                autoPlay
                playsInline
                muted
                className={
                  "absolute bottom-4 right-4 z-10 rounded-xl border-2 border-white/30 bg-black shadow-2xl " +
                  (camOff ? "hidden" : "")
                }
                style={{ width: 220, height: 140, objectFit: "cover" }}
              />
            )}

            {kind === "video" && camOff && (
              <div
                className="absolute bottom-4 right-4 z-10 flex items-center justify-center rounded-xl border-2 border-white/30 bg-slate-800 text-xs text-white"
                style={{ width: 220, height: 140 }}
              >
                Камера выключена
              </div>
            )}
          </div>

          <footer className="flex items-center justify-center gap-3 bg-slate-800/80 py-4 backdrop-blur">
            <button
              onClick={onToggleMute}
              className={btn + (muted ? " bg-red-500 text-white" : " bg-slate-700 text-white hover:bg-slate-600")}
              title={muted ? "Включить микрофон" : "Выключить микрофон"}
            >
              {muted ? "🔇" : "🎤"}
            </button>

            {kind === "video" && (
              <button
                onClick={onToggleCamera}
                className={btn + (camOff ? " bg-red-500 text-white" : " bg-slate-700 text-white hover:bg-slate-600")}
                title={camOff ? "Включить камеру" : "Выключить камеру"}
              >
                {camOff ? "📷" : "📹"}
              </button>
            )}

            {kind === "video" && (
              <button
                onClick={onToggleScreen}
                className={btn + (sharing ? " bg-brand-600 text-white" : " bg-slate-700 text-white hover:bg-slate-600")}
                title="Демонстрация экрана"
              >
                🖥
              </button>
            )}

            <button
              onClick={onEnd}
              className={btn + " bg-red-600 text-white hover:bg-red-700"}
              title="Завершить"
            >
              ✕
            </button>
          </footer>
        </div>
      );
    }
''')

# ---------- MessageBubble — добавим поддержку call-сообщений
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
            <span className="rounded-full bg-slate-200/70 px-3 py-1 text-xs text-slate-600 dark:bg-tg-panel dark:text-slate-400">
              {msg.text}
            </span>
          </div>
        );
      }

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
              <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
                {showAvatar && <Avatar user={author} size={32} />}
              </button>
            ) : null}
            <div className="relative">
              <div className="animate-pop text-7xl leading-none">{msg.text}</div>
              <div className={"mt-0.5 flex items-center gap-1 text-[10px] " + (mine ? "justify-end" : "")}>
                <span className="text-slate-400">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && (
                  <span className={readByPeer ? "text-sky-500" : "text-slate-400"}>
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
                className="mb-0.5 ml-2 text-xs font-medium text-brand-600 hover:underline dark:text-brand-500"
              >
                {msg.author_display || msg.author_username}
              </button>
            )}

            <div className={
              "animate-pop relative overflow-hidden text-sm shadow-sm " +
              bubbleColor + " " + radius + (isImage ? "" : " px-3 py-2")
            }>
              {msg.reply_to_id && !msg.is_deleted && (
                <div className={
                  "mx-2 mb-1 mt-2 rounded border-l-2 px-2 py-1 text-xs " +
                  (mine ? "border-white/60 bg-white/10" : "border-brand-500 bg-slate-50 dark:bg-slate-800")
                }>
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
                    className={
                      "flex h-9 w-9 shrink-0 items-center justify-center rounded-full " +
                      (mine ? "bg-white/20" : "bg-brand-600 text-white")
                    }
                  >
                    {audioPlaying ? "❚❚" : "▶"}
                  </button>
                  <div className="flex-1 text-xs">
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
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
              <div className={
                "absolute z-20 mt-1 w-32 overflow-hidden rounded-lg border border-slate-200 bg-white text-sm shadow-xl dark:border-slate-700 dark:bg-tg-panel " +
                (mine ? "right-0" : "left-0")
              }>
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

# ---------- ChatWindow — добавим кнопки звонка и обработку call:end → системное сообщение
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
      chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser, onStartCall
    }: {
      chat: Chat;
      currentUser: User;
      send: (data: any) => void;
      subscribe: (h: (d: any) => void) => () => void;
      onlineUsers: Set<number>;
      onOpenInfo: () => void;
      onOpenUser: (userId: number) => void;
      onStartCall: (kind: "audio" | "video") => void;
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
        if (last.author_id !== currentUser.id && last.message_type !== "system") {
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
            if (d.author_id !== currentUser.id && d.message_type !== "system") {
              send({ type: "read", chat_id: chat.id, message_id: d.id });
            }
          } else if (d.type === "message_edited" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, text: d.text, edited_at: d.edited_at } : m)
            );
          } else if (d.type === "message_deleted" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, is_deleted: true, text: "Сообщение удалено" } : m)
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
          type: "send", chat_id: chat.id, text: null,
          message_type: type, attachment_id: attachmentId,
          reply_to_id: replyTo?.id ?? null,
        });
        setReplyTo(null);
      };

      const sendSticker = (sticker: string) => {
        send({
          type: "send", chat_id: chat.id, text: sticker,
          message_type: "sticker", reply_to_id: replyTo?.id ?? null,
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
        : `${chat.member_count} участников`;

      const avatarUser = chat.peer || {
        username: chat.title || "G",
        display_name: chat.title || "Group",
        avatar_color: chat.avatar_color || "#64748b",
      };

      return (
        <main className="flex flex-1 flex-col bg-slate-100 dark:bg-tg-bg">
          <header className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2 dark:border-slate-800 dark:bg-tg-side">
            <button
              onClick={() => chat.peer ? onOpenUser(chat.peer.id) : onOpenInfo()}
              className="flex min-w-0 flex-1 items-center gap-3 transition hover:opacity-90"
            >
              <Avatar user={avatarUser as any} size={40} showOnline={!!chat.peer} online={peerOnline} />
              <div className="min-w-0 flex-1 text-left">
                <div className="truncate font-medium text-slate-800 dark:text-slate-100">
                  {headerTitle}
                </div>
                <div className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {headerSub}
                </div>
              </div>
            </button>

            {chat.peer && (
              <>
                <button
                  onClick={() => onStartCall("audio")}
                  title="Аудиозвонок"
                  className="rounded-full p-2 text-xl transition hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  📞
                </button>
                <button
                  onClick={() => onStartCall("video")}
                  title="Видеозвонок"
                  className="rounded-full p-2 text-xl transition hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  📹
                </button>
              </>
            )}

            {chat.is_group && (
              <button
                onClick={onOpenInfo}
                className="rounded-full p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                title="Информация о группе"
              >
                ℹ
              </button>
            )}
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
                    const showAvatar = !prev || prev.author_id !== m.author_id || prev.message_type === "system";
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
                        onOpenProfile={onOpenUser}
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

            {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}
            {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}
          </div>

          {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}
        </main>
      );
    }
''')

# ---------- App.tsx
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
        (localStorage.getItem("theme") as "light" | "dark") || "light"
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

      // таймер длительности звонка
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
          // ждём webrtc:offer от caller'а (там уже будет RTCSessionDescription)
          // сохраним offer во временное поле (обработчик в useWebRTC придет через subscribe)
          offerRef.current = null;
          // инициализируем сессию немедленно
          // (сам acceptCall вызовется, когда придёт offer — см. ниже)
          setIncomingCall(null);

          // подписываемся на конкретный offer
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
          try { await api.post(`/calls/${s.callId}/end`); } catch {}
        }
      };

      if (loading) {
        return (
          <div className="flex h-screen items-center justify-center bg-slate-100 text-slate-500 dark:bg-tg-bg dark:text-slate-400">
            Загрузка...
          </div>
        );
      }

      if (!user) return <Login onLogin={loadMe} />;

      const activeChat = chats.find((c) => c.id === activeChatId) || null;
      const inCall = rtc.session !== null && (rtc.status === "connecting" || rtc.status === "active" || rtc.status === "ringing");

      return (
        <div className="flex h-screen bg-slate-100 dark:bg-tg-bg">
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
              <div className="flex flex-1 flex-col items-center justify-center text-slate-400 dark:text-slate-500">
                <div className="mb-3 text-5xl">💬</div>
                <div className="text-lg">Выберите чат</div>
                <button
                  onClick={() => setShowSettings(true)}
                  className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  Начать переписку
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

    print("\nСпринт 5: WebRTC-звонки")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())