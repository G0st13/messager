#!/usr/bin/env python3
"""sprint18.py - network map + dead drop messages."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0010_sprint18.py"] = _t('''
    """sprint 18: dead drops

    Revision ID: 0010
    Revises: 0009
    Create Date: 2025-09-20
    """
    from __future__ import annotations
    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0010"
    down_revision: Union[str, None] = "0009"
    branch_labels = None
    depends_on = None


    def upgrade() -> None:
        op.create_table(
            "dead_drops",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "author_id", sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column(
                "chat_id", sa.Integer(),
                sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("reply_to_id", sa.Integer(), nullable=True),
            sa.Column("trigger_type", sa.String(20), nullable=False),
            sa.Column("trigger_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("offline_after_hours", sa.Integer(), nullable=True),
            sa.Column("delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True),
                nullable=False, server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_dead_drops_author", "dead_drops", ["author_id"])
        op.create_index("ix_dead_drops_delivered", "dead_drops", ["delivered"])


    def downgrade() -> None:
        op.drop_table("dead_drops")
''')

# ============================================================== MODELS — добавить DeadDrop
T["backend/app/models.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from sqlalchemy import (
        BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text,
        UniqueConstraint, func,
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


    class UserKey(Base):
        __tablename__ = "user_keys"
        user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        )
        public_key: Mapped[str] = mapped_column(Text)
        algorithm: Mapped[str] = mapped_column(String(30), default="ECDH-P256")
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
        )


    class FileUsage(Base):
        __tablename__ = "file_usage"
        user_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
        )
        used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
        files_count: Mapped[int] = mapped_column(Integer, default=0)
        updated_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
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
        draft: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
        pinned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        encrypted: Mapped[bool] = mapped_column(Boolean, default=False)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )


    class MessageReaction(Base):
        __tablename__ = "message_reactions"
        __table_args__ = (UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction"),)
        id: Mapped[int] = mapped_column(primary_key=True)
        message_id: Mapped[int] = mapped_column(
            ForeignKey("messages.id", ondelete="CASCADE"), index=True
        )
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        emoji: Mapped[str] = mapped_column(String(16))
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )


    class DeadDrop(Base):
        __tablename__ = "dead_drops"
        id: Mapped[int] = mapped_column(primary_key=True)
        author_id: Mapped[int] = mapped_column(
            ForeignKey("users.id", ondelete="CASCADE"), index=True
        )
        chat_id: Mapped[int] = mapped_column(
            ForeignKey("chats.id", ondelete="CASCADE")
        )
        text: Mapped[str] = mapped_column(Text)
        reply_to_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
        # trigger_type: "datetime" | "offline"
        trigger_type: Mapped[str] = mapped_column(String(20))
        trigger_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        offline_after_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
        delivered: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
        delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
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

# ============================================================== SCHEMAS — добавить DeadDrop + Network
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


    class TokenPair(BaseModel):
        access_token: str
        refresh_token: str
        token_type: str = "bearer"
        expires_in: int


    class RefreshRequest(BaseModel):
        refresh_token: str


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


    class StorageUsage(BaseModel):
        used_bytes: int
        quota_bytes: int
        files_count: int
        percent: float


    class ReactionRead(BaseModel):
        emoji: str
        count: int
        is_mine: bool


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
        is_pinned: bool = False
        encrypted: bool = False
        reactions: list[ReactionRead] = Field(default_factory=list)
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
        text: str | None = Field(default=None, max_length=8000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None
        client_id: str | None = Field(default=None, max_length=64)
        encrypted: bool = False


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=8000)


    class DraftUpdate(BaseModel):
        draft: str | None = Field(default=None, max_length=5000)


    class ReactionToggle(BaseModel):
        emoji: str = Field(min_length=1, max_length=16)


    class PublicKeyUpload(BaseModel):
        public_key: str = Field(min_length=10, max_length=2000)
        algorithm: str = Field(default="ECDH-P256", max_length=30)


    class PublicKeyRead(BaseModel):
        user_id: int
        public_key: str
        algorithm: str
        updated_at: datetime


    # ---------- DEAD DROP ----------
    class DeadDropCreate(BaseModel):
        chat_id: int
        text: str = Field(min_length=1, max_length=8000)
        reply_to_id: int | None = None
        trigger_type: str = Field(description="'datetime' or 'offline'")
        trigger_at: datetime | None = None
        offline_after_hours: int | None = Field(default=None, ge=1, le=24 * 30)


    class DeadDropRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        author_id: int
        chat_id: int
        text: str
        reply_to_id: int | None
        trigger_type: str
        trigger_at: datetime | None
        offline_after_hours: int | None
        delivered: bool
        delivered_at: datetime | None
        created_at: datetime


    # ---------- NETWORK ----------
    class NetworkNode(BaseModel):
        id: str            # "me" | "user:5" | "chat:3"
        kind: str          # "me" | "user" | "chat"
        label: str
        sub: str | None = None
        color: str | None = None
        size: float = 1.0
        online: bool = False
        unread: int = 0
        chat_id: int | None = None
        user_id: int | None = None
        is_group: bool = False
        member_count: int = 0


    class NetworkEdge(BaseModel):
        source: str
        target: str
        strength: float = 1.0
        kind: str = "channel"  # "channel" | "member"


    class NetworkGraph(BaseModel):
        nodes: list[NetworkNode]
        edges: list[NetworkEdge]


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

# ============================================================== ROUTER — dead drop
T["backend/app/routers/dead_drops.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import ChatMember, DeadDrop
    from app.schemas import DeadDropCreate, DeadDropRead


    router = APIRouter()


    @router.post("", response_model=DeadDropRead, status_code=status.HTTP_201_CREATED)
    async def create_drop(
        payload: DeadDropCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        # проверка членства
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == payload.chat_id,
                ChatMember.user_id == current.id,
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")

        if payload.trigger_type not in ("datetime", "offline"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "bad trigger_type")

        if payload.trigger_type == "datetime":
            if payload.trigger_at is None:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "trigger_at required")
            trig = payload.trigger_at
            if trig.tzinfo is None:
                trig = trig.replace(tzinfo=timezone.utc)
            if trig <= datetime.now(timezone.utc):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "trigger_at must be in future")
        else:  # offline
            if not payload.offline_after_hours or payload.offline_after_hours < 1:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "offline_after_hours required")

        drop = DeadDrop(
            author_id=current.id,
            chat_id=payload.chat_id,
            text=payload.text,
            reply_to_id=payload.reply_to_id,
            trigger_type=payload.trigger_type,
            trigger_at=payload.trigger_at if payload.trigger_type == "datetime" else None,
            offline_after_hours=payload.offline_after_hours if payload.trigger_type == "offline" else None,
        )
        db.add(drop)
        await db.flush()
        await db.refresh(drop)
        return DeadDropRead.model_validate(drop)


    @router.get("", response_model=list[DeadDropRead])
    async def list_my_drops(
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        stmt = (
            select(DeadDrop)
            .where(DeadDrop.author_id == current.id)
            .order_by(DeadDrop.created_at.desc())
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [DeadDropRead.model_validate(r) for r in rows]


    @router.delete("/{drop_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_drop(
        drop_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        d = (await db.execute(
            select(DeadDrop).where(DeadDrop.id == drop_id)
        )).scalar_one_or_none()
        if d is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "drop not found")
        if d.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your drop")
        if d.delivered:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "already delivered")
        await db.delete(d)
        await db.flush()
''')

# ============================================================== ROUTER — network graph
T["backend/app/routers/network.py"] = _t('''
    from __future__ import annotations

    from fastapi import APIRouter, Depends
    from sqlalchemy import func, or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, Message, User
    from app.schemas import NetworkEdge, NetworkGraph, NetworkNode
    from app.websocket_manager import manager


    router = APIRouter()


    @router.get("/graph", response_model=NetworkGraph)
    async def graph(
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        # 1. мои чаты
        stmt = (
            select(Chat, ChatMember)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current.id)
        )
        my_rows = (await db.execute(stmt)).all()

        nodes: list[NetworkNode] = []
        edges: list[NetworkEdge] = []
        chat_ids: list[int] = []

        # центральный узел — я
        nodes.append(NetworkNode(
            id="me",
            kind="me",
            label=current.display_name or current.username,
            sub=f"@{current.username}",
            color=current.avatar_color or "#00f0ff",
            size=2.0,
            online=True,
            user_id=current.id,
        ))

        # 2. собираем чаты и участников
        for chat, membership in my_rows:
            chat_ids.append(chat.id)

        # получаем всех участников всех чатов сразу
        members_stmt = (
            select(ChatMember.chat_id, ChatMember.user_id)
            .where(ChatMember.chat_id.in_(chat_ids or [0]))
        )
        members_rows = (await db.execute(members_stmt)).all()
        chat_members: dict[int, list[int]] = {}
        for cid, uid in members_rows:
            chat_members.setdefault(cid, []).append(uid)

        # все уникальные user_id кроме меня
        all_user_ids = {uid for uids in chat_members.values() for uid in uids if uid != current.id}
        users_by_id: dict[int, User] = {}
        if all_user_ids:
            us = (await db.execute(select(User).where(User.id.in_(all_user_ids)))).scalars().all()
            users_by_id = {u.id: u for u in us}

        # unread counts (грубо: одно значение на чат)
        unread_stmt = (
            select(Message.chat_id, func.count(Message.id))
            .where(
                Message.chat_id.in_(chat_ids or [0]),
                Message.author_id != current.id,
            )
            .group_by(Message.chat_id)
        )
        unread_map = {cid: int(cnt or 0) for cid, cnt in (await db.execute(unread_stmt)).all()}

        # 3. узлы чатов
        for chat, membership in my_rows:
            peer_id: int | None = None
            label: str
            color: str | None = None
            is_online = False

            if chat.is_group:
                label = chat.title or f"GRP-{chat.id}"
                color = chat.avatar_color or "#ff00a0"
            else:
                # личный — берём второго участника
                others = [uid for uid in chat_members.get(chat.id, []) if uid != current.id]
                if others:
                    peer_id = others[0]
                    peer = users_by_id.get(peer_id)
                    if peer:
                        label = peer.display_name or peer.username
                        color = peer.avatar_color or "#00f0ff"
                        is_online = manager.is_online(peer.id)
                    else:
                        label = f"USER-{peer_id}"
                else:
                    label = f"CHAT-{chat.id}"

            unread = unread_map.get(chat.id, 0)
            # размер: базовый 1.0, +0.3 за unread, +0.5 если online (для DM)
            size = 1.0 + min(0.8, unread * 0.15) + (0.4 if is_online else 0)

            node_id = f"chat:{chat.id}"
            nodes.append(NetworkNode(
                id=node_id,
                kind="chat",
                label=label,
                sub=f"#{chat.id}" + ("  ·GROUP" if chat.is_group else ""),
                color=color,
                size=round(size, 2),
                online=is_online,
                unread=unread,
                chat_id=chat.id,
                user_id=peer_id,
                is_group=chat.is_group,
                member_count=len(chat_members.get(chat.id, [])),
            ))

            # ребро от меня к чату
            edges.append(NetworkEdge(
                source="me",
                target=node_id,
                strength=1.0 + min(1.5, unread * 0.2),
                kind="channel",
            ))

        # 4. дополнительные рёбра: если два чата имеют общего участника (кроме меня)
        # — это «сеть связей»
        chat_list = [c for c in my_rows]
        for i in range(len(chat_list)):
            chat_a, _ = chat_list[i]
            members_a = set(chat_members.get(chat_a.id, [])) - {current.id}
            if not members_a:
                continue
            for j in range(i + 1, len(chat_list)):
                chat_b, _ = chat_list[j]
                members_b = set(chat_members.get(chat_b.id, [])) - {current.id}
                if not members_b:
                    continue
                common = members_a & members_b
                if common:
                    edges.append(NetworkEdge(
                        source=f"chat:{chat_a.id}",
                        target=f"chat:{chat_b.id}",
                        strength=min(1.0, len(common) * 0.3),
                        kind="member",
                    ))

        return NetworkGraph(nodes=nodes, edges=edges)
''')

# ============================================================== DEAD DROP WORKER
T["backend/app/dead_drop_worker.py"] = _t('''
    """Фоновый воркер: раз в минуту проверяет dead drops и доставляет готовые."""
    from __future__ import annotations

    import asyncio
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import select

    from app import cache
    from app.db import SessionLocal
    from app.logging_config import get_logger
    from app.models import ChatMember, DeadDrop, Message, User
    from app.websocket_manager import manager


    log = get_logger("dead_drop")
    INTERVAL = 60  # секунд


    async def _deliver(drop: DeadDrop, db) -> bool:
        """Создаёт Message из dead drop и рассылает по WS."""
        author = (await db.execute(select(User).where(User.id == drop.author_id))).scalar_one_or_none()
        if author is None:
            return False

        msg = Message(
            chat_id=drop.chat_id,
            author_id=drop.author_id,
            text=drop.text,
            message_type="text",
            reply_to_id=drop.reply_to_id,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)

        drop.delivered = True
        drop.delivered_at = datetime.now(timezone.utc)
        await db.commit()
        await cache.invalidate_chat_list(db, drop.chat_id)

        payload = {
            "type": "message",
            "id": msg.id,
            "chat_id": drop.chat_id,
            "client_id": None,
            "text": drop.text,
            "message_type": "text",
            "attachment": None,
            "reply_to_id": drop.reply_to_id,
            "reply_preview": None,
            "reply_author": None,
            "edited_at": None,
            "is_deleted": False,
            "is_pinned": False,
            "encrypted": False,
            "reactions": [],
            "is_dead_drop": True,
            "created_at": msg.created_at.isoformat(),
            "author_id": author.id,
            "author_username": author.username,
            "author_display": author.display_name,
            "author_avatar_color": author.avatar_color,
        }
        await manager.send_to_chat(drop.chat_id, payload)
        log.info("dead_drop_delivered", drop_id=drop.id, chat_id=drop.chat_id)
        return True


    async def _check_once() -> int:
        now = datetime.now(timezone.utc)
        delivered = 0

        async with SessionLocal() as db:
            # 1. триггер по времени
            stmt = (
                select(DeadDrop)
                .where(
                    DeadDrop.delivered == False,  # noqa: E712
                    DeadDrop.trigger_type == "datetime",
                    DeadDrop.trigger_at != None,  # noqa: E711
                    DeadDrop.trigger_at <= now,
                )
            )
            for drop in (await db.execute(stmt)).scalars().all():
                if await _deliver(drop, db):
                    delivered += 1

            # 2. триггер по оффлайну
            stmt2 = (
                select(DeadDrop)
                .where(
                    DeadDrop.delivered == False,  # noqa: E712
                    DeadDrop.trigger_type == "offline",
                )
            )
            drops2 = (await db.execute(stmt2)).scalars().all()
            for drop in drops2:
                # если автор онлайн — пропускаем
                if manager.is_online(drop.author_id):
                    continue

                author = (await db.execute(
                    select(User).where(User.id == drop.author_id)
                )).scalar_one_or_none()
                if author is None or author.last_seen is None:
                    continue

                last = author.last_seen
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                threshold = now - timedelta(hours=drop.offline_after_hours or 72)
                if last <= threshold:
                    if await _deliver(drop, db):
                        delivered += 1

        return delivered


    async def run_forever() -> None:
        log.info("dead_drop_worker_started", interval=INTERVAL)
        while True:
            try:
                n = await _check_once()
                if n:
                    log.info("dead_drop_batch", delivered=n)
            except asyncio.CancelledError:
                log.info("dead_drop_worker_stopped")
                return
            except Exception as e:
                log.error("dead_drop_worker_error", error=str(e))
            await asyncio.sleep(INTERVAL)
''')

# ============================================================== MAIN — подключить роутеры и воркер
T["backend/app/main.py"] = _t('''
    from __future__ import annotations

    import asyncio
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from starlette.exceptions import HTTPException as StarletteHTTPException

    from app import cache, presence
    from app.config import settings
    from app.db import engine
    from app.dead_drop_worker import run_forever as dead_drop_loop
    from app.logging_config import get_logger, setup_logging
    from app.routers import (
        auth, calls, chats, dead_drops, files, keys, messages, network, posts, users, ws,
    )
    from app.websocket_manager import manager


    setup_logging()
    log = get_logger("main")


    async def _on_presence_event(event: dict) -> None:
        kind = event.get("kind")
        if kind == "broadcast":
            await manager.broadcast_local(event["message"])
        elif kind == "presence":
            await manager.broadcast_local({
                "type": "presence",
                "user_id": event["user_id"],
                "online": event["online"],
                "last_seen": event.get("last_seen"),
            })


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        log.info("startup", env=settings.ENV)
        settings.upload_path
        await cache.ping()
        pubsub_task = asyncio.create_task(presence.subscribe(_on_presence_event))
        dead_drop_task = asyncio.create_task(dead_drop_loop())
        yield
        log.info("shutdown")
        pubsub_task.cancel()
        dead_drop_task.cancel()
        for t in (pubsub_task, dead_drop_task):
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        await manager.close_all()
        await cache.close()
        await engine.dispose()


    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        import time
        start = time.perf_counter()
        response = await call_next(request)
        dt = (time.perf_counter() - start) * 1000
        if not request.url.path.startswith(("/health", "/readyz")):
            log.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=round(dt, 1),
            )
        return response


    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


    p = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=f"{p}/auth", tags=["auth"])
    app.include_router(users.router, prefix=f"{p}/users", tags=["users"])
    app.include_router(keys.router, prefix=f"{p}/keys", tags=["keys"])
    app.include_router(chats.router, prefix=f"{p}/chats", tags=["chats"])
    app.include_router(messages.router, prefix=f"{p}/chats", tags=["messages"])
    app.include_router(files.router, prefix=f"{p}/files", tags=["files"])
    app.include_router(posts.router, prefix=f"{p}/posts", tags=["posts"])
    app.include_router(calls.router, prefix=f"{p}/calls", tags=["calls"])
    app.include_router(dead_drops.router, prefix=f"{p}/dead-drops", tags=["dead-drops"])
    app.include_router(network.router, prefix=f"{p}/network", tags=["network"])
    app.include_router(ws.router, prefix=p, tags=["ws"])


    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}


    @app.get("/readyz", tags=["health"])
    async def readyz():
        redis_ok = await cache.ping()
        db_ok = True
        try:
            async with engine.connect() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        ready = redis_ok and db_ok
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "ready": ready,
                "redis": "ok" if redis_ok else "down",
                "db": "ok" if db_ok else "down",
                "env": settings.ENV,
            },
        )
''')

# ============================================================== WS — dead_drop флаг
T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

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
        await ws.accept()

        if not token:
            try:
                await ws.send_json({"type": "error", "detail": "missing token"})
            except Exception:
                pass
            await ws.close(code=4401)
            return

        try:
            payload = decode_token(token)
        except Exception as e:
            try:
                await ws.send_json({"type": "error", "detail": f"decode_failed: {e}"})
            except Exception:
                pass
            await ws.close(code=4401)
            return

        if payload.get("type") != "access":
            try:
                await ws.send_json({"type": "error", "detail": "wrong_token_type"})
            except Exception:
                pass
            await ws.close(code=4401)
            return

        try:
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

        await manager.register(user_id, ws)
        await ws.send_json({"type": "ready", "user_id": user_id})

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
                        {"type": "typing", "chat_id": chat_id,
                         "user_id": user_id, "username": username,
                         "is_typing": is_typing},
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
                            await ws.send_json({"type": "error", "client_id": client_id, "detail": "not a member"})
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
                            "is_dead_drop": False,
                            "reactions": [],
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
                        await cache.invalidate_chat_list(db, m.chat_id)
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
                            select(MessageReaction).where(MessageReaction.message_id == message_id)
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
                u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
                if u:
                    u.last_seen = datetime.now(timezone.utc)
                    await db.commit()
''')

# ============================================================== FRONTEND — types
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

    export interface Reaction {
      emoji: string;
      count: number;
      is_mine: boolean;
    }

    export type SendStatus = "pending" | "sent" | "failed";

    export interface Message {
      id: number;
      client_id?: string | null;
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
      is_pinned: boolean;
      encrypted?: boolean;
      is_dead_drop?: boolean;
      reactions: Reaction[];
      created_at: string;
      send_status?: SendStatus;
      upload_progress?: number;
    }

    export interface StorageUsage {
      used_bytes: number;
      quota_bytes: number;
      files_count: number;
      percent: number;
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

    export type ThemeName = "cyber" | "matrix" | "sunset" | "amber" | "deusex" | "gits" | "lain";

    // ---- DEAD DROP ----
    export interface DeadDrop {
      id: number;
      author_id: number;
      chat_id: number;
      text: string;
      reply_to_id: number | null;
      trigger_type: "datetime" | "offline";
      trigger_at: string | null;
      offline_after_hours: number | null;
      delivered: boolean;
      delivered_at: string | null;
      created_at: string;
    }

    // ---- NETWORK ----
    export interface NetworkNode {
      id: string;
      kind: "me" | "user" | "chat";
      label: string;
      sub: string | null;
      color: string | null;
      size: number;
      online: boolean;
      unread: number;
      chat_id: number | null;
      user_id: number | null;
      is_group: boolean;
      member_count: number;
    }

    export interface NetworkEdge {
      source: string;
      target: string;
      strength: number;
      kind: "channel" | "member";
    }

    export interface NetworkGraph {
      nodes: NetworkNode[];
      edges: NetworkEdge[];
    }
''')

# ============================================================== FRONTEND — NetworkMap.tsx
T["frontend/src/NetworkMap.tsx"] = _t(r'''import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import type { NetworkEdge, NetworkGraph, NetworkNode } from "./types";

const W = 900;
const H = 600;
const STORAGE_KEY = "network_positions_v1";

interface Pos { x: number; y: number }
type Positions = Record<string, Pos>;

function loadPositions(): Positions {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  } catch { return {}; }
}
function savePositions(p: Positions) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(p)); } catch {}
}

export default function NetworkMap({
  onClose, onOpenChat, onlineUsers,
}: {
  onClose: () => void;
  onOpenChat: (chatId: number) => void;
  onlineUsers: Set<number>;
}) {
  const [graph, setGraph] = useState<NetworkGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [positions, setPositions] = useState<Positions>(loadPositions);
  const [hovered, setHovered] = useState<string | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const dragOffset = useRef({ x: 0, y: 0 });

  // загрузка графа
  useEffect(() => {
    api.get<NetworkGraph>("/network/graph").then((r) => {
      setGraph(r.data);
      // авто-раскладка по кругу для новых узлов
      const g = r.data;
      const saved = loadPositions();
      const next: Positions = { ...saved };
      const others = g.nodes.filter((n) => n.kind !== "me");
      const cx = W / 2;
      const cy = H / 2;
      // радиус зависит от количества
      const orbit = Math.min(220, 100 + others.length * 6);
      // сортируем: группы дальше, DM ближе
      const dm = others.filter((n) => !n.is_group);
      const grp = others.filter((n) => n.is_group);

      if (!next["me"]) next["me"] = { x: cx, y: cy };

      const place = (arr: NetworkNode[], radius: number, angleOffset: number) => {
        arr.forEach((n, i) => {
          if (next[n.id]) return;
          const a = angleOffset + (i / Math.max(1, arr.length)) * Math.PI * 2;
          next[n.id] = {
            x: cx + Math.cos(a) * radius,
            y: cy + Math.sin(a) * radius,
          };
        });
      };
      place(dm, orbit, -Math.PI / 2);
      place(grp, orbit + 80, -Math.PI / 2 + 0.3);

      setPositions(next);
      savePositions(next);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  // drag обработчики
  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const x = ((e.clientX - rect.left) / rect.width) * W - dragOffset.current.x;
      const y = ((e.clientY - rect.top) / rect.height) * H - dragOffset.current.y;
      setPositions((prev) => ({ ...prev, [dragging]: { x, y } }));
    };
    const onUp = () => {
      setDragging(null);
      // сохранить после окончания
      setPositions((prev) => { savePositions(prev); return prev; });
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, [dragging]);

  const onNodeDown = (e: React.MouseEvent, node: NetworkNode) => {
    e.stopPropagation();
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * W;
    const my = ((e.clientY - rect.top) / rect.height) * H;
    const p = positions[node.id] || { x: W / 2, y: H / 2 };
    dragOffset.current = { x: mx - p.x, y: my - p.y };
    setDragging(node.id);
  };

  const resetLayout = () => {
    setPositions({});
    localStorage.removeItem(STORAGE_KEY);
    // перезагрузка графа — пересчитает новые позиции
    setLoading(true);
    api.get<NetworkGraph>("/network/graph").then((r) => {
      const g = r.data;
      const next: Positions = {};
      const others = g.nodes.filter((n) => n.kind !== "me");
      const cx = W / 2;
      const cy = H / 2;
      const orbit = Math.min(220, 100 + others.length * 6);
      const dm = others.filter((n) => !n.is_group);
      const grp = others.filter((n) => n.is_group);
      next["me"] = { x: cx, y: cy };
      const place = (arr: NetworkNode[], radius: number, angleOffset: number) => {
        arr.forEach((n, i) => {
          const a = angleOffset + (i / Math.max(1, arr.length)) * Math.PI * 2;
          next[n.id] = { x: cx + Math.cos(a) * radius, y: cy + Math.sin(a) * radius };
        });
      };
      place(dm, orbit, -Math.PI / 2);
      place(grp, orbit + 80, -Math.PI / 2 + 0.3);
      setPositions(next);
      savePositions(next);
      setLoading(false);
    });
  };

  const nodesMap = useMemo(() => {
    const m: Record<string, NetworkNode> = {};
    if (graph) for (const n of graph.nodes) m[n.id] = n;
    return m;
  }, [graph]);

  const renderEdges = (edges: NetworkEdge[]) =>
    edges.map((e, i) => {
      const a = positions[e.source];
      const b = positions[e.target];
      if (!a || !b) return null;
      const isChannel = e.kind === "channel";
      const active = hovered === e.source || hovered === e.target;
      return (
        <line
          key={`e-${i}`}
          x1={a.x}
          y1={a.y}
          x2={b.x}
          y2={b.y}
          stroke={isChannel ? "#00f0ff" : "#ff00a0"}
          strokeWidth={active ? 1.8 : 0.8}
          strokeOpacity={active ? 0.9 : isChannel ? 0.35 : 0.15}
          strokeDasharray={isChannel ? "4 4" : "2 6"}
          style={{ filter: active ? `drop-shadow(0 0 4px ${isChannel ? "#00f0ff" : "#ff00a0"})` : "none" }}
        />
      );
    });

  const renderNodes = (nodes: NetworkNode[]) =>
    nodes.map((n) => {
      const p = positions[n.id];
      if (!p) return null;
      const isMe = n.kind === "me";
      const isOnline = isMe || (n.user_id != null && onlineUsers.has(n.user_id)) || n.online;
      const baseR = isMe ? 22 : 10 + n.size * 5;
      const r = hovered === n.id ? baseR + 3 : baseR;
      const fill = n.color || "#00f0ff";
      const opacity = isOnline || isMe ? 1 : 0.35;

      return (
        <g
          key={n.id}
          transform={`translate(${p.x},${p.y})`}
          style={{ cursor: n.chat_id ? "pointer" : dragging === n.id ? "grabbing" : "grab" }}
          onMouseDown={(e) => onNodeDown(e, n)}
          onMouseEnter={() => setHovered(n.id)}
          onMouseLeave={() => setHovered(null)}
          onClick={() => {
            if (dragging) return;
            if (n.chat_id) onOpenChat(n.chat_id);
          }}
        >
          {/* ореол онлайн */}
          {isOnline && !isMe && (
            <circle r={r + 6} fill={fill} opacity={0.12} />
          )}
          {/* пульс у активного */}
          {isMe && (
            <circle r={r + 10} fill="#00f0ff" opacity={0.15}>
              <animate attributeName="r" values={`${r + 8};${r + 20};${r + 8}`} dur="2.4s" repeatCount="indefinite" />
              <animate attributeName="opacity" values="0.2;0.02;0.2" dur="2.4s" repeatCount="indefinite" />
            </circle>
          )}
          {/* основной круг */}
          <circle
            r={r}
            fill={`${fill}22`}
            stroke={fill}
            strokeWidth={isMe ? 2 : 1.2}
            opacity={opacity}
            style={{ filter: `drop-shadow(0 0 6px ${fill}88)` }}
          />
          {/* внутренний маркер для групп */}
          {n.is_group && (
            <rect
              x={-r / 2}
              y={-r / 2}
              width={r}
              height={r}
              fill="none"
              stroke={fill}
              strokeWidth={0.8}
              opacity={opacity * 0.7}
              transform="rotate(45)"
            />
          )}
          {/* инициал */}
          <text
            x={0}
            y={isMe ? 5 : 3.5}
            textAnchor="middle"
            fontSize={isMe ? 11 : 9}
            fill={fill}
            opacity={opacity}
            style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: "bold", pointerEvents: "none" }}
          >
            {n.label.replace(/[^A-Za-z0-9]/g, "").slice(0, 2).toUpperCase()}
          </text>
          {/* label под узлом */}
          <text
            x={0}
            y={r + 14}
            textAnchor="middle"
            fontSize={9}
            fill="#eaf4ff"
            opacity={isOnline || isMe ? 0.9 : 0.4}
            style={{ fontFamily: "JetBrains Mono, monospace", pointerEvents: "none" }}
          >
            {n.label.length > 16 ? n.label.slice(0, 14) + "…" : n.label}
          </text>
          {/* unread badge */}
          {n.unread > 0 && (
            <g transform={`translate(${r - 2},${-r + 2})`}>
              <circle r={7} fill="#ff00a0" />
              <text
                textAnchor="middle"
                y={3}
                fontSize={8}
                fill="#05070d"
                style={{ fontFamily: "JetBrains Mono, monospace", fontWeight: "bold" }}
              >
                {n.unread > 99 ? "99" : n.unread}
              </text>
            </g>
          )}
        </g>
      );
    });

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 p-4">
      <div className="corner-frame relative w-full max-w-[960px] rounded-sm border border-cyber-cyan/50 bg-cyber-panel">
        <header className="flex items-center justify-between border-b border-cyber-cyan/25 px-4 py-3">
          <div>
            <div className="text-sm font-bold uppercase tracking-widest neon-text">
              ◈ NETWORK_MAP
            </div>
            <div className="text-[10px] uppercase tracking-widest text-cyber-dim mt-1">
              {graph ? `${graph.nodes.length} nodes · ${graph.edges.length} links` : "scanning..."}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={resetLayout}
              className="cyber-btn rounded-sm px-3 py-1 text-[10px]"
            >
              ↺ layout
            </button>
            <button
              onClick={onClose}
              className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15"
            >
              ✕
            </button>
          </div>
        </header>

        <div className="relative">
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center text-xs uppercase tracking-widest neon-text">
              scanning network...
            </div>
          )}
          <svg
            ref={svgRef}
            viewBox={`0 0 ${W} ${H}`}
            className="block h-[600px] w-full"
            style={{
              background:
                "radial-gradient(ellipse at center, rgba(0,240,255,0.04), transparent 60%), #05070d",
            }}
          >
            {/* grid */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(0,240,255,0.06)" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width={W} height={H} fill="url(#grid)" />

            {graph && renderEdges(graph.edges)}
            {graph && renderNodes(graph.nodes)}

            {/* метка в углу */}
            <text x={12} y={20} fontSize={9} fill="rgba(0,240,255,0.5)" style={{ fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.2em" }}>
              NET::GRAPH v1
            </text>
            <text x={12} y={H - 10} fontSize={9} fill="rgba(0,240,255,0.35)" style={{ fontFamily: "JetBrains Mono, monospace", letterSpacing: "0.2em" }}>
              DRAG NODE · CLICK TO OPEN
            </text>
          </svg>
        </div>

        <footer className="flex items-center justify-between border-t border-cyber-cyan/25 px-4 py-2 text-[9px] uppercase tracking-widest text-cyber-dim">
          <span>◉ online · ⬡ group · ── channel · ·· members-link</span>
          <span>{graph ? `${graph.nodes.length} NODES` : ""}</span>
        </footer>
      </div>
    </div>
  );
}
''')

# ============================================================== FRONTEND — DeadDropModal.tsx
T["frontend/src/DeadDropModal.tsx"] = _t(r'''import { useEffect, useState } from "react";
import { api } from "./api";
import type { Chat, DeadDrop } from "./types";

function fmtDt(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString([], {
    day: "2-digit", month: "2-digit", year: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function hoursLabel(h: number): string {
  if (h < 24) return `${h} ч`;
  const d = Math.round(h / 24);
  return `${d} дн`;
}

export default function DeadDropModal({
  chats, defaultChatId, onClose,
}: {
  chats: Chat[];
  defaultChatId: number | null;
  onClose: () => void;
}) {
  const [tab, setTab] = useState<"new" | "list">("new");
  const [drops, setDrops] = useState<DeadDrop[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // form
  const [chatId, setChatId] = useState<number | null>(defaultChatId ?? chats[0]?.id ?? null);
  const [text, setText] = useState("");
  const [triggerType, setTriggerType] = useState<"datetime" | "offline">("datetime");
  const [datetime, setDatetime] = useState(() => {
    // дефолт — через 1 час
    const d = new Date(Date.now() + 60 * 60 * 1000);
    const iso = d.toISOString().slice(0, 16);
    return iso;
  });
  const [offlineHours, setOfflineHours] = useState(72);

  const reload = () => {
    api.get<DeadDrop[]>("/dead-drops").then((r) => setDrops(r.data));
  };

  useEffect(() => { reload(); }, []);

  const submit = async () => {
    setError("");
    if (!chatId) { setError("Выбери чат"); return; }
    if (!text.trim()) { setError("Напиши текст"); return; }

    setBusy(true);
    try {
      const payload: any = {
        chat_id: chatId,
        text: text.trim(),
        trigger_type: triggerType,
      };
      if (triggerType === "datetime") {
        // datetime-local отдаёт без TZ, интерпретируем как локальную
        const dt = new Date(datetime);
        if (isNaN(dt.getTime())) { setError("Неверная дата"); setBusy(false); return; }
        payload.trigger_at = dt.toISOString();
      } else {
        payload.offline_after_hours = offlineHours;
      }
      await api.post<DeadDrop>("/dead-drops", payload);
      setText("");
      reload();
      setTab("list");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить dead drop?")) return;
    try {
      await api.delete(`/dead-drops/${id}`);
      reload();
    } catch {}
  };

  const chatName = (id: number) => {
    const c = chats.find((x) => x.id === id);
    if (!c) return `CHAT-${id}`;
    if (c.peer) return c.peer.display_name || c.peer.username;
    return c.title || `GRP-${c.id}`;
  };

  const input = "cyber-input w-full rounded-sm px-3 py-2 text-sm";

  const tabCls = (active: boolean) =>
    "flex-1 py-3 text-[10px] font-bold uppercase tracking-widest transition " +
    (active
      ? "text-cyber-yellow border-b-2 border-cyber-yellow bg-cyber-yellow/5"
      : "text-cyber-dim hover:text-cyber-yellow hover:bg-cyber-yellow/5");

  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
      <div
        className="corner-frame flex h-[560px] w-[640px] flex-col rounded-sm border border-cyber-yellow/50 bg-cyber-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between border-b border-cyber-yellow/25 px-4 py-3">
          <div>
            <div className="text-sm font-bold uppercase tracking-widest neon-text-yel">
              ⏳ DEAD_DROP
            </div>
            <div className="text-[10px] uppercase tracking-widest text-cyber-dim mt-1">
              send a message into the future
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15"
          >
            ✕
          </button>
        </header>

        <div className="flex border-b border-cyber-yellow/20">
          <button onClick={() => setTab("new")} className={tabCls(tab === "new")}>◈ new drop</button>
          <button onClick={() => setTab("list")} className={tabCls(tab === "list")}>◈ my drops ({drops.filter(d => !d.delivered).length})</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {tab === "new" && (
            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-yellow/70">// channel</label>
                <select
                  value={chatId ?? ""}
                  onChange={(e) => setChatId(Number(e.target.value))}
                  className={input}
                >
                  {chats.map((c) => (
                    <option key={c.id} value={c.id} className="bg-cyber-panel">
                      {c.peer ? (c.peer.display_name || c.peer.username) : (c.title || `GRP-${c.id}`)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-yellow/70">// message</label>
                <textarea
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  rows={4}
                  placeholder="Что передать в будущее..."
                  className={input + " resize-none"}
                />
              </div>

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-yellow/70">// trigger</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTriggerType("datetime")}
                    className={
                      "flex-1 rounded-sm border px-3 py-2 text-xs font-bold uppercase tracking-widest transition " +
                      (triggerType === "datetime"
                        ? "border-cyber-yellow bg-cyber-yellow/15 neon-text-yel"
                        : "border-cyber-yellow/25 text-cyber-dim hover:border-cyber-yellow/60")
                    }
                  >
                    ◷ date & time
                  </button>
                  <button
                    onClick={() => setTriggerType("offline")}
                    className={
                      "flex-1 rounded-sm border px-3 py-2 text-xs font-bold uppercase tracking-widest transition " +
                      (triggerType === "offline"
                        ? "border-cyber-yellow bg-cyber-yellow/15 neon-text-yel"
                        : "border-cyber-yellow/25 text-cyber-dim hover:border-cyber-yellow/60")
                    }
                  >
                    ◌ if offline
                  </button>
                </div>
              </div>

              {triggerType === "datetime" && (
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-yellow/70">// at</label>
                  <input
                    type="datetime-local"
                    value={datetime}
                    onChange={(e) => setDatetime(e.target.value)}
                    className={input}
                  />
                  <div className="mt-1 text-[10px] text-cyber-dim">
                    отправится через {Math.max(0, Math.round((new Date(datetime).getTime() - Date.now()) / 60000))} мин
                  </div>
                </div>
              )}

              {triggerType === "offline" && (
                <div>
                  <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-yellow/70">// after offline for</label>
                  <div className="flex items-center gap-3">
                    <input
                      type="range"
                      min={1}
                      max={24 * 14}
                      value={offlineHours}
                      onChange={(e) => setOfflineHours(Number(e.target.value))}
                      className="flex-1"
                    />
                    <span className="w-20 text-center neon-text-yel text-sm">{hoursLabel(offlineHours)}</span>
                  </div>
                  <div className="mt-2 rounded-sm border border-cyber-yellow/20 bg-cyber-yellow/5 px-3 py-2 text-[10px] text-cyber-dim leading-relaxed">
                    Если ты не заходишь {hoursLabel(offlineHours)} — сообщение отправится само.
                    Идеально для «если меня не будет — передай».
                  </div>
                </div>
              )}

              {error && (
                <div className="rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}

              <button
                onClick={submit}
                disabled={busy}
                className="cyber-btn w-full rounded-sm py-2 text-xs"
                style={{ borderColor: "rgba(252,238,10,0.5)", color: "#fcee0a" }}
              >
                {busy ? "[ ARMING... ]" : "[ ARM DEAD DROP ]"}
              </button>
            </div>
          )}

          {tab === "list" && (
            <div className="space-y-2">
              {drops.length === 0 && (
                <div className="p-8 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                  // no drops yet
                </div>
              )}
              {drops.map((d) => (
                <div
                  key={d.id}
                  className={
                    "rounded-sm border p-3 " +
                    (d.delivered
                      ? "border-cyber-cyan/20 bg-black/30 opacity-60"
                      : "border-cyber-yellow/40 bg-cyber-yellow/5")
                  }
                >
                  <div className="mb-1 flex items-baseline justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest neon-text-yel">
                      {d.delivered ? "✓ delivered" : (d.trigger_type === "datetime" ? "◷ scheduled" : "◌ offline-trigger")}
                    </span>
                    <span className="text-[9px] uppercase tracking-widest text-cyber-dim">
                      → {chatName(d.chat_id)}
                    </span>
                  </div>
                  <div className="mb-1 truncate text-xs text-cyber-text">{d.text}</div>
                  <div className="flex items-center justify-between text-[9px] uppercase tracking-widest text-cyber-dim">
                    <span>
                      {d.trigger_type === "datetime"
                        ? `@ ${fmtDt(d.trigger_at)}`
                        : `after ${hoursLabel(d.offline_after_hours || 0)} offline`}
                    </span>
                    {!d.delivered && (
                      <button
                        onClick={() => remove(d.id)}
                        className="neon-text-mag hover:underline"
                      >
                        ✕ cancel
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <footer className="border-t border-cyber-yellow/25 px-4 py-2 text-[9px] uppercase tracking-widest text-cyber-dim">
          drops are private until triggered · can be cancelled anytime
        </footer>
      </div>
    </div>
  );
}
''')

# ============================================================== ChatWindow — кнопка Dead Drop
CHATWINDOW_PATCHES = [
    # добавить props
    (
        '  e2eEncrypt: (peerId: number, text: string) => Promise<string | null>;\n'
        '  e2eDecrypt: (peerId: number, text: string) => Promise<string | null>;\n'
        '  e2eReady: boolean;\n'
        '}) {',
        '  e2eEncrypt: (peerId: number, text: string) => Promise<string | null>;\n'
        '  e2eDecrypt: (peerId: number, text: string) => Promise<string | null>;\n'
        '  e2eReady: boolean;\n'
        '  onOpenDeadDrop: (chatId: number) => void;\n'
        '}) {',
    ),
    (
        '  e2eEnabled, onToggleE2E, e2eEncrypt, e2eDecrypt, e2eReady,\n'
        '}: {',
        '  e2eEnabled, onToggleE2E, e2eEncrypt, e2eDecrypt, e2eReady,\n'
        '  onOpenDeadDrop,\n'
        '}: {',
    ),
    # кнопка в шапке рядом с ☎
    (
        '        {chat.peer && (\n'
        '          <>\n'
        '            <button\n'
        '              onClick={() => onStartCall("audio")}',
        '        <button\n'
        '          onClick={() => onOpenDeadDrop(chat.id)}\n'
        '          title="Dead drop — сообщение с триггером"\n'
        '          className="rounded-sm border border-cyber-yellow/40 px-2 py-1 text-cyber-yellow transition hover:bg-cyber-yellow/15"\n'
        '        >\n'
        '          ⏳\n'
        '        </button>\n'
        '\n'
        '        {chat.peer && (\n'
        '          <>\n'
        '            <button\n'
        '              onClick={() => onStartCall("audio")}',
    ),
    # метка DEAD DROP в bubble — теперь просто проверяем is_dead_drop, ставим пометку в MessageBubble
]


# ============================================================== MessageBubble — метка DEAD DROP
MESSAGEBUBBLE_PATCHES = [
    # добавить метку в шапку баббла
    (
        '          {msg.is_pinned && (\n'
        '            <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">\n'
        '              📌 pinned\n'
        '            </div>\n'
        '          )}',
        '          {msg.is_pinned && (\n'
        '            <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">\n'
        '              📌 pinned\n'
        '            </div>\n'
        '          )}\n'
        '          {msg.is_dead_drop && (\n'
        '            <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">\n'
        '              ⏳ DEAD DROP\n'
        '            </div>\n'
        '          )}',
    ),
    # в стиле активного пусть будет жёлтая обводка для dead drop
    (
        '  const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";',
        '  const accent = msg.is_dead_drop ? "#fcee0a" : (isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0");',
    ),
]


# ============================================================== App patches
APP_PATCHES = [
    # импорты
    (
        'import { useScrolling } from "./useScrolling";',
        'import { useScrolling } from "./useScrolling";\n'
        '    import NetworkMap from "./NetworkMap";\n'
        '    import DeadDropModal from "./DeadDropModal";',
    ),
    # стейты
    (
        '      const [cityWeather, setCityWeather] = useState<Weather>(',
        '      const [showNetworkMap, setShowNetworkMap] = useState(false);\n'
        '      const [deadDropChatId, setDeadDropChatId] = useState<number | null>(null);\n'
        '      const [cityWeather, setCityWeather] = useState<Weather>(',
    ),
    # передача onOpenDeadDrop в ChatWindow
    (
        '                  e2eReady={e2e.ready}\n'
        '                />',
        '                  e2eReady={e2e.ready}\n'
        '                  onOpenDeadDrop={(id) => setDeadDropChatId(id)}\n'
        '                />',
    ),
    # рендер модалок перед закрытием </>
    (
        '            {showCommandPalette && (\n'
        '              <CommandPalette\n'
        '                commands={commands}\n'
        '                onClose={() => setShowCommandPalette(false)}\n'
        '              />\n'
        '            )}',
        '            {showCommandPalette && (\n'
        '              <CommandPalette\n'
        '                commands={commands}\n'
        '                onClose={() => setShowCommandPalette(false)}\n'
        '              />\n'
        '            )}\n'
        '\n'
        '            {showNetworkMap && (\n'
        '              <NetworkMap\n'
        '                onlineUsers={onlineUsers}\n'
        '                onClose={() => setShowNetworkMap(false)}\n'
        '                onOpenChat={(id) => { setShowNetworkMap(false); setActiveChatId(id); setMode("chats"); }}\n'
        '              />\n'
        '            )}\n'
        '\n'
        '            {deadDropChatId != null && (\n'
        '              <DeadDropModal\n'
        '                chats={chats}\n'
        '                defaultChatId={deadDropChatId}\n'
        '                onClose={() => setDeadDropChatId(null)}\n'
        '              />\n'
        '            )}',
    ),
    # добавить в commands палитры
    (
        '          { id: "feed", label: "Open feed", icon: "📰", action: () => setMode("feed") },',
        '          { id: "network", label: "Network map", icon: "🕸", action: () => setShowNetworkMap(true) },\n'
        '          { id: "deaddrop", label: "New dead drop", icon: "⏳", action: () => setDeadDropChatId(activeChatId ?? (chats[0]?.id ?? null)) },\n'
        '          { id: "feed", label: "Open feed", icon: "📰", action: () => setMode("feed") },',
    ),
    # кнопка в ChatList — добавим пропс
    (
        '            <ChatList\n'
        '              chats={chats}\n'
        '              activeId={activeChatId}\n'
        '              onSelect={(id) => { setActiveChatId(id); setMode("chats"); }}\n'
        '              onlineUsers={onlineUsers}\n'
        '              currentUser={user}\n'
        '              onOpenProfile={() => setShowProfile(true)}\n'
        '              onOpenSettings={() => setShowSettings(true)}\n'
        '              onOpenFeed={() => setMode("feed")}\n'
        '              onOpenMyProfile={() => { setProfileUserId(user.id); setMode("profile"); }}\n'
        '              mode={mode}\n'
        '              failedQueue={failedTotal}\n'
        '            />',
        '            <ChatList\n'
        '              chats={chats}\n'
        '              activeId={activeChatId}\n'
        '              onSelect={(id) => { setActiveChatId(id); setMode("chats"); }}\n'
        '              onlineUsers={onlineUsers}\n'
        '              currentUser={user}\n'
        '              onOpenProfile={() => setShowProfile(true)}\n'
        '              onOpenSettings={() => setShowSettings(true)}\n'
        '              onOpenFeed={() => setMode("feed")}\n'
        '              onOpenMyProfile={() => { setProfileUserId(user.id); setMode("profile"); }}\n'
        '              mode={mode}\n'
        '              failedQueue={failedTotal}\n'
        '              onOpenNetworkMap={() => setShowNetworkMap(true)}\n'
        '              onOpenDeadDrop={() => setDeadDropChatId(activeChatId ?? (chats[0]?.id ?? null))}\n'
        '            />',
    ),
]


# ============================================================== ChatList — две кнопки в тулбаре
CHATLIST_PATCHES = [
    # расширить props
    (
        '  mode: "chats" | "feed" | "profile";\n'
        '  failedQueue?: number;\n'
        '}) {',
        '  mode: "chats" | "feed" | "profile";\n'
        '  failedQueue?: number;\n'
        '  onOpenNetworkMap?: () => void;\n'
        '  onOpenDeadDrop?: () => void;\n'
        '}) {',
    ),
    (
        '  onOpenFeed, onOpenMyProfile, mode, failedQueue,\n'
        '}: {',
        '  onOpenFeed, onOpenMyProfile, mode, failedQueue,\n'
        '  onOpenNetworkMap, onOpenDeadDrop,\n'
        '}: {',
    ),
    # добавить кнопки в tabs
    (
        '      <div className="cyberdeck-tabs">\n'
        '        <button\n'
        '          onClick={onOpenFeed}\n'
        '          className={"cyberdeck-tab" + (mode === "feed" ? " active" : "")}\n'
        '        >\n'
        '          ◈ FEED\n'
        '        </button>\n'
        '        <button\n'
        '          onClick={onOpenMyProfile}\n'
        '          className={"cyberdeck-tab" + (mode === "profile" ? " active" : "")}\n'
        '        >\n'
        '          ◈ ME\n'
        '        </button>\n'
        '      </div>',
        '      <div className="cyberdeck-tabs">\n'
        '        <button\n'
        '          onClick={onOpenFeed}\n'
        '          className={"cyberdeck-tab" + (mode === "feed" ? " active" : "")}\n'
        '        >\n'
        '          ◈ FEED\n'
        '        </button>\n'
        '        <button\n'
        '          onClick={onOpenMyProfile}\n'
        '          className={"cyberdeck-tab" + (mode === "profile" ? " active" : "")}\n'
        '        >\n'
        '          ◈ ME\n'
        '        </button>\n'
        '        <button\n'
        '          onClick={onOpenNetworkMap}\n'
        '          title="Network map"\n'
        '          className="cyberdeck-tab"\n'
        '        >\n'
        '          ◉ NET\n'
        '        </button>\n'
        '        <button\n'
        '          onClick={onOpenDeadDrop}\n'
        '          title="Dead drop"\n'
        '          className="cyberdeck-tab"\n'
        '        >\n'
        '          ⏳ DROP\n'
        '        </button>\n'
        '      </div>',
    ),
]


# ============================================================== CSS — тюнинг для новых UI
NET_CSS = r'''
    /* Dead drop + network map */
    .cyberdeck-tabs .cyberdeck-tab {
      font-size: 9px !important;
      letter-spacing: 0.15em !important;
      padding: 8px 2px !important;
    }

    /* Модалки */
    .corner-frame.border-cyber-yellow\/50::before,
    .corner-frame.border-cyber-yellow\/50::after {
      border-color: #fcee0a !important;
      filter: drop-shadow(0 0 3px rgba(252,238,10,0.7));
    }
'''


def write_file(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {rel}")


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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 18 — Network map + Dead drop\n")

    # ===== backend =====
    for rel, content in T.items():
        write_file(root, rel, content)

    # ===== frontend =====
    src = root / "frontend" / "src"

    # новые компоненты
    write_file(root, "frontend/src/NetworkMap.tsx", T["frontend/src/NetworkMap.tsx"])
    write_file(root, "frontend/src/DeadDropModal.tsx", T["frontend/src/DeadDropModal.tsx"])

    # патчи существующих
    patch_file(src / "ChatWindow.tsx", CHATWINDOW_PATCHES)
    patch_file(src / "MessageBubble.tsx", MESSAGEBUBBLE_PATCHES)
    patch_file(src / "App.tsx", APP_PATCHES)
    patch_file(src / "ChatList.tsx", CHATLIST_PATCHES)

    # CSS дописать
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "Dead drop + network map" not in css_text:
        css_text = css_text.rstrip() + "\n" + NET_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Где искать:")
    print("  🕸 Network map — кнопка ◉ NET во вкладках списка чатов,")
    print("     или Ctrl+K → 'Network map'")
    print("  ⏳ Dead drop — кнопка ⏳ в шапке чата,")
    print("     или кнопка ⏳ DROP во вкладках, или Ctrl+K → 'dead drop'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())