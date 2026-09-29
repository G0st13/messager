#!/usr/bin/env python3
"""sprint19.py - factions, chrome slots, rank, firewall, dark room."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0011_sprint19.py"] = _t('''
    """sprint 19: factions, chrome, xp, firewall, dark room

    Revision ID: 0011
    Revises: 0010
    Create Date: 2025-09-22
    """
    from __future__ import annotations
    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0011"
    down_revision: Union[str, None] = "0010"
    branch_labels = None
    depends_on = None


    def upgrade() -> None:
        # user fields
        op.add_column("users", sa.Column("faction", sa.String(20), nullable=True))
        op.add_column("users", sa.Column("xp", sa.Integer(), nullable=False, server_default="0"))
        op.add_column("users", sa.Column("chrome_neuro_link", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.add_column("users", sa.Column("chrome_deep_scan", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.add_column("users", sa.Column("chrome_pulse_sync", sa.Boolean(), nullable=False, server_default=sa.false()))

        # chat fields
        op.add_column("chats", sa.Column("firewall_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.add_column("chats", sa.Column("firewall_seconds", sa.Integer(), nullable=False, server_default="60"))
        op.add_column("chats", sa.Column("auto_delete_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column("chats", sa.Column("is_dark_room", sa.Boolean(), nullable=False, server_default=sa.false()))

        op.create_index("ix_chats_auto_delete", "chats", ["auto_delete_at"])


    def downgrade() -> None:
        op.drop_index("ix_chats_auto_delete", table_name="chats")
        op.drop_column("chats", "is_dark_room")
        op.drop_column("chats", "auto_delete_at")
        op.drop_column("chats", "firewall_seconds")
        op.drop_column("chats", "firewall_enabled")
        op.drop_column("users", "chrome_pulse_sync")
        op.drop_column("users", "chrome_deep_scan")
        op.drop_column("users", "chrome_neuro_link")
        op.drop_column("users", "xp")
        op.drop_column("users", "faction")
''')

# ============================================================== MODELS (полностью)
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

        # sprint 19
        faction: Mapped[str | None] = mapped_column(String(20), default=None)
        xp: Mapped[int] = mapped_column(Integer, default=0)
        chrome_neuro_link: Mapped[bool] = mapped_column(Boolean, default=False)
        chrome_deep_scan: Mapped[bool] = mapped_column(Boolean, default=False)
        chrome_pulse_sync: Mapped[bool] = mapped_column(Boolean, default=False)

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

        # sprint 19
        firewall_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
        firewall_seconds: Mapped[int] = mapped_column(Integer, default=60)
        auto_delete_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True, index=True
        )
        is_dark_room: Mapped[bool] = mapped_column(Boolean, default=False)

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
        chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
        text: Mapped[str] = mapped_column(Text)
        reply_to_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

# ============================================================== SCHEMAS — патчим UserRead + ChatRead
T["backend/app/schemas.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from typing import Literal
    from pydantic import BaseModel, ConfigDict, EmailStr, Field


    FactionName = Literal["netrunners", "corpo", "nomads", "rebels"]


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
        # sprint 19
        faction: FactionName | None = None
        xp: int = 0
        rank: str = "novice"
        chrome_neuro_link: bool = False
        chrome_deep_scan: bool = False
        chrome_pulse_sync: bool = False


    class FactionUpdate(BaseModel):
        faction: FactionName


    class ChromeUpdate(BaseModel):
        chrome_neuro_link: bool | None = None
        chrome_deep_scan: bool | None = None
        chrome_pulse_sync: bool | None = None


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
        faction: FactionName | None = None
        xp: int = 0
        rank: str = "novice"


    class UserUpdate(BaseModel):
        display_name: str | None = Field(default=None, max_length=100)
        bio: str | None = Field(default=None, max_length=500)


    class ChatCreate(BaseModel):
        title: str | None = None
        is_group: bool = False
        member_usernames: list[str] = Field(default_factory=list)
        is_dark_room: bool = False
        dark_room_hours: int | None = Field(default=None, ge=1, le=168)


    class ChatUpdate(BaseModel):
        title: str | None = Field(default=None, max_length=255)
        description: str | None = Field(default=None, max_length=500)
        avatar_color: str | None = Field(default=None, max_length=20)


    class FirewallUpdate(BaseModel):
        enabled: bool
        seconds: int = Field(default=60, ge=10, le=3600)


    class ChatMemberRead(BaseModel):
        user_id: int
        username: str
        display_name: str | None
        avatar_color: str | None
        role: str
        joined_at: datetime
        faction: FactionName | None = None
        rank: str = "novice"


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
        author_faction: FactionName | None = None
        text: str | None = None
        message_type: str = "text"
        attachment: FileRead | None = None
        reply_to_id: int | None = None
        reply_preview: str | None = None
        reply_author: str | None = None
        edited_at: datetime | None = None
        is_deleted: bool = False
        is_pinned: bool = False
        is_dead_drop: bool = False
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
        # sprint 19
        firewall_enabled: bool = False
        firewall_seconds: int = 60
        is_dark_room: bool = False
        auto_delete_at: datetime | None = None


    class MessageCreate(BaseModel):
        text: str | None = Field(default=None, max_length=8000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None
        client_id: str | None = Field(default=None, max_length=64)


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


    class DeadDropCreate(BaseModel):
        chat_id: int
        text: str = Field(min_length=1, max_length=8000)
        reply_to_id: int | None = None
        trigger_type: str
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


    class NetworkNode(BaseModel):
        id: str
        kind: str
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
        kind: str = "channel"


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
        faction: FactionName | None = None


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

# ============================================================== FRACTIONS/RANKS module
T["backend/app/factions.py"] = _t('''
    """Фракции и ранги."""
    from __future__ import annotations

    from app.models import User


    FACTIONS = {
        "netrunners": {"label": "NETRUNNERS", "color": "#00f0ff", "icon": "◈"},
        "corpo":      {"label": "CORPO",      "color": "#f0b030", "icon": "◆"},
        "nomads":     {"label": "NOMADS",     "color": "#ff6600", "icon": "⬢"},
        "rebels":     {"label": "REBELS",     "color": "#ff00a0", "icon": "▲"},
    }


    RANKS = [
        (0,    "novice",    "NOVICE"),
        (100,  "runner",    "RUNNER"),
        (500,  "netrunner", "NETRUNNER"),
        (2000, "legend",    "LEGEND"),
    ]


    def rank_from_xp(xp: int) -> tuple[str, str, int]:
        """
        Возвращает (rank_key, rank_label, xp_to_next).
        xp_to_next = 0 если максимальный.
        """
        current = RANKS[0]
        for i, (threshold, key, label) in enumerate(RANKS):
            if xp >= threshold:
                current = (threshold, key, label)
            else:
                return current[1], current[2], threshold - xp
        return current[1], current[2], 0


    def faction_info(faction: str | None) -> dict | None:
        if not faction:
            return None
        return FACTIONS.get(faction)


    async def add_xp(db, user_id: int, amount: int = 1) -> None:
        u = (await db.get(User, user_id))
        if u is None:
            return
        u.xp = (u.xp or 0) + amount
        await db.flush()
''')

# ============================================================== ROUTER USERS — faction/chrome/rank
T["backend/app/routers/users.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache, presence
    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.factions import FACTIONS, rank_from_xp
    from app.models import Follow, Post, User
    from app.schemas import ChromeUpdate, FactionUpdate, UserProfile, UserRead, UserUpdate


    router = APIRouter()


    def _to_read(u: User) -> UserRead:
        _, rank_label, _ = rank_from_xp(u.xp or 0)
        return UserRead(
            id=u.id,
            username=u.username,
            email=u.email,
            display_name=u.display_name,
            bio=u.bio,
            avatar_color=u.avatar_color,
            is_active=u.is_active,
            last_seen=u.last_seen,
            created_at=u.created_at,
            faction=u.faction,  # type: ignore
            xp=u.xp or 0,
            rank=rank_label,
            chrome_neuro_link=u.chrome_neuro_link,
            chrome_deep_scan=u.chrome_deep_scan,
            chrome_pulse_sync=u.chrome_pulse_sync,
        )


    @router.get("", response_model=list[UserRead])
    async def list_users(
        current: CurrentUser,
        q: str | None = None,
        limit: int = 50,
        db: AsyncSession = Depends(get_session),
    ):
        stmt = select(User).where(User.id != current.id)
        if q:
            p = f"%{q}%"
            stmt = stmt.where(or_(User.username.ilike(p), User.display_name.ilike(p)))
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return [_to_read(u) for u in result.scalars().all()]


    @router.patch("/me", response_model=UserRead)
    async def update_me(
        payload: UserUpdate, current: CurrentUser, db: AsyncSession = Depends(get_session)
    ):
        if payload.display_name is not None:
            current.display_name = payload.display_name or None
        if payload.bio is not None:
            current.bio = payload.bio or None
        await db.flush()
        await db.refresh(current)
        await cache.invalidate_profile(current.id)
        return _to_read(current)


    @router.patch("/me/faction", response_model=UserRead)
    async def update_faction(
        payload: FactionUpdate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        if payload.faction not in FACTIONS:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid faction")
        current.faction = payload.faction
        await db.flush()
        await db.refresh(current)
        await cache.invalidate_profile(current.id)
        return _to_read(current)


    @router.patch("/me/chrome", response_model=UserRead)
    async def update_chrome(
        payload: ChromeUpdate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        if payload.chrome_neuro_link is not None:
            current.chrome_neuro_link = payload.chrome_neuro_link
        if payload.chrome_deep_scan is not None:
            current.chrome_deep_scan = payload.chrome_deep_scan
        if payload.chrome_pulse_sync is not None:
            current.chrome_pulse_sync = payload.chrome_pulse_sync
        await db.flush()
        await db.refresh(current)
        return _to_read(current)


    @router.get("/{user_id}/profile", response_model=UserProfile)
    async def user_profile(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        key = f"profile:{user_id}:viewer:{current.id}"
        cached = await cache.get(key)
        if cached is not None:
            return UserProfile.model_validate(cached)

        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

        posts_count = int((await db.execute(
            select(func.count(Post.id)).where(
                Post.author_id == user_id, Post.is_deleted == False  # noqa: E712
            )
        )).scalar() or 0)

        followers_count = int((await db.execute(
            select(func.count(Follow.id)).where(Follow.following_id == user_id)
        )).scalar() or 0)

        following_count = int((await db.execute(
            select(func.count(Follow.id)).where(Follow.follower_id == user_id)
        )).scalar() or 0)

        is_following = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none() is not None

        _, rank_label, _ = rank_from_xp(u.xp or 0)

        profile = UserProfile(
            id=u.id, username=u.username, display_name=u.display_name,
            bio=u.bio, avatar_color=u.avatar_color, created_at=u.created_at,
            posts_count=posts_count,
            followers_count=followers_count,
            following_count=following_count,
            is_following=is_following,
            is_me=u.id == current.id,
            faction=u.faction,  # type: ignore
            xp=u.xp or 0,
            rank=rank_label,
        )
        await cache.set(key, profile.model_dump(mode="json"), ttl=settings.CACHE_TTL_PROFILE)
        return profile


    @router.get("/{user_id}/presence")
    async def user_presence(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        online = await presence.is_online(user_id)
        last_seen = await presence.get_last_seen(user_id)
        # deep_scan — показывает last_seen только тем, у кого включён
        show_last_seen = current.chrome_deep_scan or (last_seen is None and not online)
        return {
            "user_id": user_id,
            "online": online,
            "last_seen": last_seen if show_last_seen else None,
        }


    @router.get("/presence/online")
    async def online_users(current: CurrentUser):
        ids = await presence.get_online_ids()
        return {"online": ids}


    @router.post("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
    async def follow_user(
        user_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        if user_id == current.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "cannot follow self")
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
        existing = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none()
        if existing is None:
            db.add(Follow(follower_id=current.id, following_id=user_id))
            await db.flush()
        await cache.invalidate_profile(user_id)
        await cache.invalidate_profile(current.id)


    @router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
    async def unfollow_user(
        user_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        f = (await db.execute(
            select(Follow).where(
                Follow.follower_id == current.id, Follow.following_id == user_id
            )
        )).scalar_one_or_none()
        if f:
            await db.delete(f)
            await db.flush()
        await cache.invalidate_profile(user_id)
        await cache.invalidate_profile(current.id)
''')

# ============================================================== ROUTER CHATS — firewall + dark room
T["backend/app/routers/chats.py"] = _t('''
    from __future__ import annotations

    import secrets
    from datetime import datetime, timedelta, timezone

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache
    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.factions import rank_from_xp
    from app.models import Chat, ChatMember, Message, User
    from app.schemas import (
        AddMemberRequest, ChatCreate, ChatMemberRead, ChatRead, ChatUpdate,
        DraftUpdate, FirewallUpdate, InviteRead, MessageRead, UserRead,
    )
    from app.websocket_manager import manager


    router = APIRouter()

    GROUP_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
        "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#f43f5e",
    ]


    def _user_to_read(u: User) -> UserRead:
        _, rank_label, _ = rank_from_xp(u.xp or 0)
        return UserRead(
            id=u.id, username=u.username, email=u.email,
            display_name=u.display_name, bio=u.bio,
            avatar_color=u.avatar_color, is_active=u.is_active,
            last_seen=u.last_seen, created_at=u.created_at,
            faction=u.faction,  # type: ignore
            xp=u.xp or 0, rank=rank_label,
            chrome_neuro_link=u.chrome_neuro_link,
            chrome_deep_scan=u.chrome_deep_scan,
            chrome_pulse_sync=u.chrome_pulse_sync,
        )


    def _msg_to_read(m: Message, author: User) -> MessageRead:
        return MessageRead(
            id=m.id, chat_id=m.chat_id, author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
            author_faction=author.faction,  # type: ignore
            text="Сообщение удалено" if m.is_deleted else m.text,
            message_type=m.message_type or "text",
            reply_to_id=m.reply_to_id,
            edited_at=m.edited_at,
            is_deleted=m.is_deleted,
            is_pinned=m.is_pinned,
            created_at=m.created_at,
        )


    async def _system_message(db: AsyncSession, chat_id: int, actor_id: int, text: str) -> None:
        msg = Message(
            chat_id=chat_id, author_id=actor_id, text=text, message_type="system",
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        actor = (await db.execute(select(User).where(User.id == actor_id))).scalar_one()
        payload = {
            "type": "message", "id": msg.id, "chat_id": chat_id, "text": text,
            "message_type": "system", "attachment": None,
            "reply_to_id": None, "reply_preview": None, "reply_author": None,
            "edited_at": None, "is_deleted": False, "is_pinned": False,
            "is_dead_drop": False,
            "created_at": msg.created_at.isoformat(),
            "author_id": actor.id, "author_username": actor.username,
            "author_display": actor.display_name,
            "author_avatar_color": actor.avatar_color,
            "author_faction": actor.faction,
        }
        await manager.send_to_chat(chat_id, payload)


    async def _build_chat_read(
        db: AsyncSession, chat: Chat, current_id: int, membership: ChatMember
    ) -> ChatRead:
        last_stmt = (
            select(Message, User)
            .join(User, User.id == Message.author_id)
            .where(Message.chat_id == chat.id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        last = (await db.execute(last_stmt)).first()
        last_msg = _msg_to_read(last[0], last[1]) if last else None

        if membership.last_read_message_id is None:
            cnt = await db.execute(
                select(func.count(Message.id)).where(
                    Message.chat_id == chat.id, Message.author_id != current_id
                )
            )
        else:
            cnt = await db.execute(
                select(func.count(Message.id)).where(
                    Message.chat_id == chat.id,
                    Message.author_id != current_id,
                    Message.id > membership.last_read_message_id,
                )
            )
        unread = int(cnt.scalar() or 0)

        peer: UserRead | None = None
        if not chat.is_group:
            peer_stmt = (
                select(User)
                .join(ChatMember, ChatMember.user_id == User.id)
                .where(ChatMember.chat_id == chat.id, User.id != current_id)
                .limit(1)
            )
            peer_obj = (await db.execute(peer_stmt)).scalar_one_or_none()
            peer = _user_to_read(peer_obj) if peer_obj else None

        total = await db.execute(
            select(func.count(ChatMember.id)).where(ChatMember.chat_id == chat.id)
        )
        member_count = int(total.scalar() or 0)

        return ChatRead(
            id=chat.id, title=chat.title, description=chat.description,
            avatar_color=chat.avatar_color, is_group=chat.is_group,
            created_at=chat.created_at,
            last_message=last_msg, unread_count=unread, peer=peer,
            member_count=member_count, my_role=membership.role,
            firewall_enabled=chat.firewall_enabled,
            firewall_seconds=chat.firewall_seconds,
            is_dark_room=chat.is_dark_room,
            auto_delete_at=chat.auto_delete_at,
        )


    async def _require_role(
        db: AsyncSession, chat_id: int, user_id: int,
        roles: tuple[str, ...] = ("owner", "admin"),
    ) -> ChatMember:
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        if m.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not enough rights")
        return m


    @router.get("", response_model=list[ChatRead])
    async def my_chats(current: CurrentUser, db: AsyncSession = Depends(get_session)):
        key = f"chats:{current.id}"
        cached = await cache.get(key)
        if cached is not None:
            return [ChatRead.model_validate(c) for c in cached]

        stmt = (
            select(Chat, ChatMember)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current.id)
        )
        rows = (await db.execute(stmt)).all()
        out = [await _build_chat_read(db, chat, current.id, m) for chat, m in rows]

        def key_fn(c: ChatRead):
            return c.last_message.created_at if c.last_message else c.created_at

        out.sort(key=key_fn, reverse=True)

        await cache.set(
            key, [c.model_dump(mode="json") for c in out],
            ttl=settings.CACHE_TTL_CHATS,
        )
        return out


    @router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
    async def create_chat(
        payload: ChatCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        member_ids = {current.id}
        if payload.member_usernames:
            res = await db.execute(
                select(User).where(User.username.in_(payload.member_usernames))
            )
            for u in res.scalars().all():
                member_ids.add(u.id)

        # dark room — только группа, авто-удаление
        auto_delete = None
        if payload.is_dark_room:
            hours = payload.dark_room_hours or 24
            auto_delete = datetime.now(timezone.utc) + timedelta(hours=hours)

        if not payload.is_group and len(member_ids) == 2 and not payload.is_dark_room:
            other = next(iter(member_ids - {current.id}))
            existing = await db.execute(
                select(Chat)
                .join(ChatMember, ChatMember.chat_id == Chat.id)
                .where(Chat.is_group == False)  # noqa: E712
                .group_by(Chat.id)
                .having(func.count(ChatMember.user_id) == 2)
                .having(Chat.id.in_(
                    select(ChatMember.chat_id).where(ChatMember.user_id == other)
                ))
                .having(Chat.id.in_(
                    select(ChatMember.chat_id).where(ChatMember.user_id == current.id)
                ))
            )
            existing_chat = existing.scalars().first()
            if existing_chat:
                membership = (await db.execute(
                    select(ChatMember).where(
                        ChatMember.chat_id == existing_chat.id,
                        ChatMember.user_id == current.id,
                    )
                )).scalar_one()
                return await _build_chat_read(db, existing_chat, current.id, membership)

        color = None
        if payload.is_group:
            color = GROUP_COLORS[hash(payload.title or "g") % len(GROUP_COLORS)]

        chat = Chat(
            title=payload.title,
            is_group=payload.is_group or payload.is_dark_room,
            avatar_color=color,
            invite_token=secrets.token_urlsafe(16) if payload.is_group else None,
            is_dark_room=payload.is_dark_room,
            auto_delete_at=auto_delete,
        )
        db.add(chat)
        await db.flush()

        for uid in member_ids:
            db.add(ChatMember(
                chat_id=chat.id, user_id=uid,
                role="owner" if uid == current.id else "member",
            ))
        await db.flush()
        await db.refresh(chat)

        membership = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat.id, ChatMember.user_id == current.id
            )
        )).scalar_one()

        for uid in member_ids:
            await cache.invalidate_chat_list_for_user(uid)

        return await _build_chat_read(db, chat, current.id, membership)


    @router.get("/{chat_id}", response_model=ChatRead)
    async def get_chat(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        row = (await db.execute(
            select(Chat, ChatMember)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(Chat.id == chat_id, ChatMember.user_id == current.id)
        )).first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
        chat, membership = row
        return await _build_chat_read(db, chat, current.id, membership)


    @router.patch("/{chat_id}", response_model=ChatRead)
    async def update_chat(
        chat_id: int,
        payload: ChatUpdate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id)
        chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
        if chat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
        if payload.title is not None:
            chat.title = payload.title or None
        if payload.description is not None:
            chat.description = payload.description or None
        if payload.avatar_color is not None:
            chat.avatar_color = payload.avatar_color or None
        await db.flush()
        await db.refresh(chat)
        await cache.invalidate_chat_list(db, chat_id)

        membership = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one()
        return await _build_chat_read(db, chat, current.id, membership)


    @router.patch("/{chat_id}/firewall", response_model=ChatRead)
    async def update_firewall(
        chat_id: int,
        payload: FirewallUpdate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id)
        chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
        if chat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
        chat.firewall_enabled = payload.enabled
        chat.firewall_seconds = payload.seconds
        await db.flush()
        await cache.invalidate_chat_list(db, chat_id)

        membership = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one()
        return await _build_chat_read(db, chat, current.id, membership)


    @router.get("/{chat_id}/members", response_model=list[ChatMemberRead])
    async def list_members(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id, ("owner", "admin", "member"))
        stmt = (
            select(ChatMember, User)
            .join(User, User.id == ChatMember.user_id)
            .where(ChatMember.chat_id == chat_id)
            .order_by(ChatMember.role.desc(), User.username)
        )
        rows = (await db.execute(stmt)).all()
        return [
            ChatMemberRead(
                user_id=u.id, username=u.username,
                display_name=u.display_name, avatar_color=u.avatar_color,
                role=m.role, joined_at=m.created_at,
                faction=u.faction,  # type: ignore
                rank=rank_from_xp(u.xp or 0)[1],
            )
            for m, u in rows
        ]


    @router.post("/{chat_id}/members", response_model=ChatMemberRead, status_code=201)
    async def add_member(
        chat_id: int,
        payload: AddMemberRequest,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id)
        chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
        if chat is None or not chat.is_group:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a group")

        user = (await db.execute(
            select(User).where(User.username == payload.username)
        )).scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")

        existing = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user.id
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(status.HTTP_409_CONFLICT, "already a member")

        m = ChatMember(chat_id=chat_id, user_id=user.id, role="member")
        db.add(m)
        await db.flush()
        await _system_message(db, chat_id, current.id, f"{current.username} добавил {user.username}")
        await db.commit()
        await cache.invalidate_chat_list(db, chat_id)

        return ChatMemberRead(
            user_id=user.id, username=user.username,
            display_name=user.display_name, avatar_color=user.avatar_color,
            role="member", joined_at=m.created_at,
            faction=user.faction,  # type: ignore
            rank=rank_from_xp(user.xp or 0)[1],
        )


    @router.delete("/{chat_id}/members/{user_id}", status_code=204)
    async def remove_member(
        chat_id: int, user_id: int,
        current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id)
        if user_id == current.id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "use leave endpoint")
        target = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
            )
        )).scalar_one_or_none()
        if target is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not a member")
        if target.role == "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "cannot remove owner")
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one()
        await db.delete(target)
        await db.flush()
        await _system_message(db, chat_id, current.id, f"{current.username} удалил {user.username}")
        await db.commit()
        await cache.invalidate_chat_list(db, chat_id)
        await cache.invalidate_chat_list_for_user(user_id)


    @router.post("/{chat_id}/leave", status_code=204)
    async def leave_chat(
        chat_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "not a member")
        if m.role == "owner":
            others = (await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat_id, ChatMember.user_id != current.id
                )
            )).scalars().all()
            if others:
                new_owner = next((x for x in others if x.role == "admin"), others[0])
                new_owner.role = "owner"
        await _system_message(db, chat_id, current.id, f"{current.username} вышел из группы")
        await db.delete(m)
        await db.commit()
        await cache.invalidate_chat_list(db, chat_id)
        await cache.invalidate_chat_list_for_user(current.id)


    @router.post("/{chat_id}/invite", response_model=InviteRead)
    async def create_invite(
        chat_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        await _require_role(db, chat_id, current.id)
        chat = (await db.execute(select(Chat).where(Chat.id == chat_id))).scalar_one_or_none()
        if chat is None or not chat.is_group:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "not a group")
        if not chat.invite_token:
            chat.invite_token = secrets.token_urlsafe(16)
            await db.flush()
        return InviteRead(
            token=chat.invite_token,
            url=f"http://localhost:5173/?invite={chat.invite_token}",
        )


    @router.post("/join/{token}", response_model=ChatRead)
    async def join_by_invite(
        token: str, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        chat = (await db.execute(
            select(Chat).where(Chat.invite_token == token)
        )).scalar_one_or_none()
        if chat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "invalid invite")

        existing = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat.id, ChatMember.user_id == current.id
            )
        )).scalar_one_or_none()
        if existing is None:
            db.add(ChatMember(chat_id=chat.id, user_id=current.id, role="member"))
            await db.flush()
            await _system_message(db, chat.id, current.id, f"{current.username} присоединился")
            await db.commit()
            membership = (await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat.id, ChatMember.user_id == current.id
                )
            )).scalar_one()
            await cache.invalidate_chat_list(db, chat.id)
            await cache.invalidate_chat_list_for_user(current.id)
        else:
            membership = existing

        return await _build_chat_read(db, chat, current.id, membership)


    @router.post("/{chat_id}/read", status_code=204)
    async def mark_read(
        chat_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        last = (await db.execute(
            select(Message.id)
            .where(Message.chat_id == chat_id)
            .order_by(Message.id.desc()).limit(1)
        )).scalar()
        if last is not None:
            m.last_read_message_id = last
            await db.flush()
        await cache.invalidate_chat_list_for_user(current.id)


    @router.patch("/{chat_id}/draft", status_code=204)
    async def save_draft(
        chat_id: int,
        payload: DraftUpdate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        m.draft = payload.draft or None
        await db.flush()


    @router.get("/{chat_id}/draft")
    async def get_draft(
        chat_id: int, current: CurrentUser, db: AsyncSession = Depends(get_session),
    ):
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        return {"draft": m.draft or ""}
''')

# ============================================================== WS — firewall check + XP
T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

    import json
    from datetime import datetime, timedelta, timezone

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app import cache
    from app.db import SessionLocal
    from app.factions import rank_from_xp
    from app.logging_config import get_logger
    from app.models import Chat, ChatMember, File as FileModel, Message, MessageReaction, User
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
            "author_faction": u.faction,
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


    async def _add_xp(db, user_id: int, amount: int) -> None:
        u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if u is None:
            return
        u.xp = (u.xp or 0) + amount


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

                        chat = (await db.execute(
                            select(Chat).where(Chat.id == chat_id)
                        )).scalar_one_or_none()
                        if chat is None:
                            continue

                        # firewall check
                        if chat.firewall_enabled:
                            threshold = datetime.now(timezone.utc) - timedelta(seconds=chat.firewall_seconds)
                            last_msg = (await db.execute(
                                select(Message.created_at)
                                .where(
                                    Message.chat_id == chat_id,
                                    Message.author_id == user_id,
                                )
                                .order_by(Message.id.desc())
                                .limit(1)
                            )).scalar()
                            if last_msg is not None:
                                lmt = last_msg
                                if lmt.tzinfo is None:
                                    lmt = lmt.replace(tzinfo=timezone.utc)
                                if lmt > threshold:
                                    wait_sec = int((lmt - threshold).total_seconds()) + 1
                                    await ws.send_json({
                                        "type": "error",
                                        "client_id": client_id,
                                        "detail": f"firewall: подожди {wait_sec} сек",
                                    })
                                    continue

                        msg = Message(
                            chat_id=chat_id, author_id=user_id, text=text,
                            message_type=message_type,
                            attachment_id=attachment_id, reply_to_id=reply_to_id,
                        )
                        db.add(msg)
                        await db.flush()
                        await db.refresh(msg)
                        member.last_read_message_id = msg.id
                        member.draft = None

                        # XP: +1 за сообщение, +1 бонус если neuro_link
                        author = (await db.execute(
                            select(User).where(User.id == user_id)
                        )).scalar_one()
                        xp_gain = 1 + (1 if author.chrome_neuro_link else 0)
                        author.xp = (author.xp or 0) + xp_gain

                        await db.commit()
                        await cache.invalidate_chat_list(db, chat_id)

                        author_dict = {
                            "author_id": author.id,
                            "author_username": author.username,
                            "author_display": author.display_name,
                            "author_avatar_color": author.avatar_color,
                            "author_faction": author.faction,
                        }
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
                            "is_dead_drop": False,
                            "reactions": [],
                            "created_at": msg.created_at.isoformat(),
                            **author_dict,
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
                            # XP за реакцию
                            u = (await db.execute(
                                select(User).where(User.id == user_id)
                            )).scalar_one()
                            u.xp = (u.xp or 0) + 1
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

# ============================================================== WORKER — dark room cleanup
T["backend/app/dark_room_worker.py"] = _t('''
    """Удаляет просроченные Dark Rooms."""
    from __future__ import annotations

    import asyncio
    from datetime import datetime, timezone

    from sqlalchemy import delete, select

    from app import cache
    from app.db import SessionLocal
    from app.logging_config import get_logger
    from app.models import Chat, ChatMember
    from app.websocket_manager import manager


    log = get_logger("dark_room")
    INTERVAL = 60


    async def _cleanup_once() -> int:
        now = datetime.now(timezone.utc)
        removed = 0
        async with SessionLocal() as db:
            stmt = select(Chat).where(
                Chat.is_dark_room == True,  # noqa: E712
                Chat.auto_delete_at != None,  # noqa: E711
                Chat.auto_delete_at <= now,
            )
            for chat in (await db.execute(stmt)).scalars().all():
                # уведомить участников
                await manager.send_to_chat(chat.id, {
                    "type": "chat_expired",
                    "chat_id": chat.id,
                })
                # удалить связанные через CASCADE
                await db.delete(chat)
                removed += 1
            if removed:
                await db.commit()
                # почистить кеш чатов у всех
                try:
                    client = cache.client()
                    keys = await client.keys("chats:*")
                    if keys:
                        await client.delete(*keys)
                except Exception:
                    pass
                log.info("dark_rooms_removed", count=removed)
        return removed


    async def run_forever() -> None:
        log.info("dark_room_worker_started", interval=INTERVAL)
        while True:
            try:
                await _cleanup_once()
            except asyncio.CancelledError:
                return
            except Exception as e:
                log.error("dark_room_worker_error", error=str(e))
            await asyncio.sleep(INTERVAL)
''')

# ============================================================== MAIN — патчим lifespan + добавить воркер
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
    from app.dark_room_worker import run_forever as dark_room_loop
    from app.db import engine
    from app.dead_drop_worker import run_forever as dead_drop_loop
    from app.logging_config import get_logger, setup_logging
    from app.routers import (
        auth, calls, chats, dead_drops, files, messages, network, posts, users, ws,
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
        dark_room_task = asyncio.create_task(dark_room_loop())
        yield
        log.info("shutdown")
        for t in (pubsub_task, dead_drop_task, dark_room_task):
            t.cancel()
        for t in (pubsub_task, dead_drop_task, dark_room_task):
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

# ============================================================== FRONTEND — types
T["frontend/src/types.ts"] = _t('''
    export type FactionName = "netrunners" | "corpo" | "nomads" | "rebels";

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
      faction: FactionName | null;
      xp: number;
      rank: string;
      chrome_neuro_link: boolean;
      chrome_deep_scan: boolean;
      chrome_pulse_sync: boolean;
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
      faction: FactionName | null;
      xp: number;
      rank: string;
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
      firewall_enabled: boolean;
      firewall_seconds: number;
      is_dark_room: boolean;
      auto_delete_at: string | null;
    }

    export interface ChatMember {
      user_id: number;
      username: string;
      display_name: string | null;
      avatar_color: string | null;
      role: "owner" | "admin" | "member";
      joined_at: string;
      faction: FactionName | null;
      rank: string;
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
      author_faction?: FactionName | null;
      text: string | null;
      message_type: MessageType;
      attachment: Attachment | null;
      reply_to_id: number | null;
      reply_preview: string | null;
      reply_author: string | null;
      edited_at: string | null;
      is_deleted: boolean;
      is_pinned: boolean;
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
      faction?: FactionName | null;
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

# ============================================================== FRONTEND — factions.ts
T["frontend/src/factions.ts"] = _t('''
    import type { FactionName } from "./types";

    export interface FactionMeta {
      name: FactionName;
      label: string;
      color: string;
      icon: string;
      motto: string;
    }

    export const FACTIONS: FactionMeta[] = [
      {
        name: "netrunners",
        label: "NETRUNNERS",
        color: "#00f0ff",
        icon: "◈",
        motto: "Мы — ток в проводах. Мы — код в сети.",
      },
      {
        name: "corpo",
        label: "CORPO",
        color: "#f0b030",
        icon: "◆",
        motto: "Порядок. Эффективность. Прибыль.",
      },
      {
        name: "nomads",
        label: "NOMADS",
        color: "#ff6600",
        icon: "⬢",
        motto: "Дом там, где наши колёса.",
      },
      {
        name: "rebels",
        label: "REBELS",
        color: "#ff00a0",
        icon: "▲",
        motto: "Свобода или смерть системе.",
      },
    ];

    export const RANKS = [
      { key: "novice", label: "NOVICE", threshold: 0 },
      { key: "runner", label: "RUNNER", threshold: 100 },
      { key: "netrunner", label: "NETRUNNER", threshold: 500 },
      { key: "legend", label: "LEGEND", threshold: 2000 },
    ];

    export function factionMeta(name: FactionName | null | undefined): FactionMeta | null {
      if (!name) return null;
      return FACTIONS.find((f) => f.name === name) || null;
    }

    export function rankProgress(xp: number): { label: string; next: number; percent: number } {
      const current = RANKS[RANKS.length - 1];
      for (const r of RANKS) {
        if (xp >= r.threshold) current = r;
      }
      const idx = RANKS.indexOf(current);
      const nextThreshold = RANKS[idx + 1]?.threshold ?? current.threshold;
      const prevThreshold = current.threshold;
      const span = nextThreshold - prevThreshold;
      const percent = span > 0 ? Math.min(100, ((xp - prevThreshold) / span) * 100) : 100;
      return {
        label: current.label,
        next: nextThreshold,
        percent: idx === RANKS.length - 1 ? 100 : percent,
      };
    }
''')

# ============================================================== FRONTEND — FactionBadge.tsx
T["frontend/src/FactionBadge.tsx"] = _t('''
    import { factionMeta } from "./factions";
    import type { FactionName } from "./types";

    export default function FactionBadge({
      faction, size = "sm", showLabel = false,
    }: {
      faction: FactionName | null | undefined;
      size?: "sm" | "md";
      showLabel?: boolean;
    }) {
      const meta = factionMeta(faction);
      if (!meta) return null;
      const cls = size === "sm"
        ? "text-[10px] px-1 py-0.5"
        : "text-xs px-2 py-1";

      return (
        <span
          className={"inline-flex items-center gap-1 rounded-sm border font-bold uppercase tracking-widest " + cls}
          style={{
            color: meta.color,
            borderColor: meta.color + "66",
            background: meta.color + "11",
            textShadow: `0 0 6px ${meta.color}80`,
          }}
          title={meta.label}
        >
          <span>{meta.icon}</span>
          {showLabel && <span>{meta.label}</span>}
        </span>
      );
    }
''')

# ============================================================== FRONTEND — FactionPicker.tsx
T["frontend/src/FactionPicker.tsx"] = _t('''
    import { useState } from "react";
    import { api } from "./api";
    import { FACTIONS } from "./factions";
    import type { FactionName, User } from "./types";

    export default function FactionPicker({
      user, onChosen, canClose = false, onClose,
    }: {
      user: User;
      onChosen: (u: User) => void;
      canClose?: boolean;
      onClose?: () => void;
    }) {
      const [selected, setSelected] = useState<FactionName | null>(null);
      const [busy, setBusy] = useState(false);
      const [error, setError] = useState("");

      const submit = async () => {
        if (!selected) return;
        setBusy(true);
        setError("");
        try {
          const { data } = await api.patch<User>("/users/me/faction", { faction: selected });
          onChosen(data);
          if (onClose) onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        } finally {
          setBusy(false);
        }
      };

      return (
        <div className="fixed inset-0 z-[300] flex items-center justify-center bg-black/85 p-4 backdrop-blur-sm">
          <div className="corner-frame w-full max-w-2xl rounded-sm border border-cyber-cyan/50 bg-cyber-panel p-6 shadow-neon-cyan">
            <div className="mb-6 text-center">
              <div className="mb-3 text-5xl flicker neon-text">◈</div>
              <h2 className="glitch text-2xl font-bold tracking-widest" data-text="CHOOSE FACTION">
                CHOOSE FACTION
              </h2>
              <div className="mt-2 text-[10px] uppercase tracking-[0.4em] text-cyber-dim">
                оператор @{user.username} · выбери свою сторону
              </div>
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {FACTIONS.map((f) => {
                const isSel = selected === f.name;
                return (
                  <button
                    key={f.name}
                    onClick={() => setSelected(f.name)}
                    className={
                      "relative rounded-sm border p-4 text-left transition " +
                      (isSel
                        ? "bg-" + f.name + "-bg scale-[1.02]"
                        : "border-cyber-cyan/20 hover:border-cyber-cyan/60")
                    }
                    style={
                      isSel
                        ? {
                            borderColor: f.color,
                            background: f.color + "18",
                            boxShadow: `0 0 20px ${f.color}66`,
                          }
                        : undefined
                    }
                  >
                    <div className="mb-2 flex items-center gap-2">
                      <span className="text-2xl" style={{ color: f.color, textShadow: `0 0 8px ${f.color}` }}>
                        {f.icon}
                      </span>
                      <span className="text-sm font-bold uppercase tracking-widest" style={{ color: f.color }}>
                        {f.label}
                      </span>
                    </div>
                    <div className="text-[11px] italic text-cyber-dim">
                      «{f.motto}»
                    </div>
                    {isSel && (
                      <div className="absolute right-2 top-2 text-xs" style={{ color: f.color }}>
                        ✓
                      </div>
                    )}
                  </button>
                );
              })}
            </div>

            {error && (
              <div className="mt-4 rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
                ⚠ {error}
              </div>
            )}

            <div className="mt-6 flex justify-center gap-3">
              {canClose && onClose && (
                <button
                  onClick={onClose}
                  className="cyber-btn rounded-sm px-4 py-2 text-xs"
                >
                  [ ОТМЕНА ]
                </button>
              )}
              <button
                onClick={submit}
                disabled={!selected || busy}
                className="cyber-btn rounded-sm px-6 py-2 text-xs"
                style={
                  selected
                    ? {
                        borderColor: FACTIONS.find((f) => f.name === selected)!.color,
                        color: FACTIONS.find((f) => f.name === selected)!.color,
                      }
                    : undefined
                }
              >
                {busy ? "[ РЕГИСТРАЦИЯ... ]" : "[ ПРИНЯТЬ ]"}
              </button>
            </div>

            <div className="mt-4 text-center text-[9px] uppercase tracking-widest text-cyber-dim">
              фракция изменит цвет ника, значок и звуки
            </div>
          </div>
        </div>
    );
}
''')

# ============================================================== FRONTEND — ChromePanel.tsx
T["frontend/src/ChromePanel.tsx"] = _t('''
    import { useState } from "react";
    import { api } from "./api";
    import type { User } from "./types";

    const SLOTS = [
      {
        key: "chrome_neuro_link" as const,
        label: "NEURO-LINK",
        icon: "◈",
        desc: "+1 XP за каждое сообщение",
      },
      {
        key: "chrome_deep_scan" as const,
        label: "DEEP-SCAN",
        icon: "◉",
        desc: "видишь last seen собеседников",
      },
      {
        key: "chrome_pulse_sync" as const,
        label: "PULSE-SYNC",
        icon: "◌",
        desc: "усиленные уведомления",
      },
    ];

    export default function ChromePanel({
      user, onUpdate,
    }: {
      user: User;
      onUpdate: (u: User) => void;
    }) {
      const [busy, setBusy] = useState<string | null>(null);

      const toggle = async (key: typeof SLOTS[number]["key"]) => {
        setBusy(key);
        try {
          const { data } = await api.patch<User>("/users/me/chrome", {
            [key]: !user[key],
          });
          onUpdate(data);
        } catch {}
        finally { setBusy(null); }
      };

      return (
        <div className="space-y-3">
          <div className="text-[10px] uppercase tracking-widest text-cyber-dim">
            // chrome slots · активируй импланты
          </div>
          {SLOTS.map((s) => {
            const active = user[s.key];
            return (
              <button
                key={s.key}
                onClick={() => toggle(s.key)}
                disabled={busy === s.key}
                className={
                  "flex w-full items-center gap-3 rounded-sm border p-3 text-left transition " +
                  (active
                    ? "border-cyber-cyan bg-cyber-cyan/10 shadow-neon-cyan"
                    : "border-cyber-cyan/25 hover:border-cyber-cyan/60")
                }
              >
                <div
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-sm text-xl"
                  style={{
                    color: active ? "#00f0ff" : "#5a7a95",
                    textShadow: active ? "0 0 8px #00f0ff" : "none",
                  }}
                >
                  {s.icon}
                </div>
                <div className="min-w-0 flex-1">
                  <div className={"text-xs font-bold uppercase tracking-widest " + (active ? "neon-text" : "text-cyber-dim")}>
                    {s.label}
                  </div>
                  <div className="text-[10px] text-cyber-dim">{s.desc}</div>
                </div>
                <div className={
                  "shrink-0 rounded-sm border px-2 py-0.5 text-[9px] uppercase tracking-widest " +
                  (active
                    ? "border-cyber-cyan text-cyber-cyan"
                    : "border-cyber-dim/40 text-cyber-dim")
                }>
                  {active ? "on" : "off"}
                </div>
              </button>
            );
          })}
        </div>
    );
}
''')

# ============================================================== FRONTEND — UserNameBadge.tsx
T["frontend/src/UserNameBadge.tsx"] = _t('''
    import FactionBadge from "./FactionBadge";
    import { factionMeta } from "./factions";
    import type { FactionName } from "./types";

    export default function UserNameBadge({
      name, faction, rank, align = "left", size = "md",
    }: {
      name: string;
      faction: FactionName | null | undefined;
      rank?: string;
      align?: "left" | "right";
      size?: "sm" | "md" | "lg";
    }) {
      const meta = factionMeta(faction);
      const color = meta?.color;
      const cls = size === "lg"
        ? "text-base"
        : size === "md"
        ? "text-sm"
        : "text-xs";

      return (
        <span
          className={
            "inline-flex items-center gap-2 " +
            (align === "right" ? "flex-row-reverse" : "")
          }
        >
          <span
            className={"truncate font-bold " + cls}
            style={
              color
                ? { color, textShadow: `0 0 6px ${color}88` }
                : undefined
            }
          >
            {name}
          </span>
          {faction && <FactionBadge faction={faction} />}
          {rank && rank !== "novice" && (
            <span
              className="rounded-sm border border-cyber-yellow/40 bg-cyber-yellow/10 px-1 py-0.5 text-[9px] font-bold uppercase tracking-widest neon-text-yel"
              title={`Rank: ${rank}`}
            >
              {rank}
            </span>
          )}
        </span>
    );
}
''')

# ============================================================== FRONTEND — DarkRoomModal
T["frontend/src/DarkRoomModal.tsx"] = _t('''
    import { useState } from "react";
    import { api } from "./api";
    import type { Chat, User } from "./types";

    export default function DarkRoomModal({
      currentUser, onClose, onCreated,
    }: {
      currentUser: User;
      onClose: () => void;
      onCreated: (chat: Chat) => void;
    }) {
      const [title, setTitle] = useState("");
      const [members, setMembers] = useState("");
      const [hours, setHours] = useState(24);
      const [busy, setBusy] = useState(false);
      const [error, setError] = useState("");

      const submit = async () => {
        setError("");
        if (!title.trim()) { setError("Нужно название"); return; }
        setBusy(true);
        try {
          const names = members.split(",").map((s) => s.trim()).filter(Boolean);
          const { data } = await api.post<Chat>("/chats", {
            title: title.trim(),
            is_group: true,
            is_dark_room: true,
            dark_room_hours: hours,
            member_usernames: names,
          });
          onCreated(data);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        } finally {
          setBusy(false);
        }
      };

      const input = "cyber-input w-full rounded-sm px-3 py-2 text-sm";

      return (
        <div className="fixed inset-0 z-[250] flex items-center justify-center bg-black/80 p-4" onClick={onClose}>
          <div
            className="corner-frame w-[560px] rounded-sm border border-cyber-magenta/60 bg-cyber-panel p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4">
              <div className="text-sm font-bold uppercase tracking-widest neon-text-mag">
                ⬢ DARK ROOM
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-widest text-cyber-dim">
                комната существует ограниченное время. все сообщения исчезнут.
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-magenta/70">
                  // название
                </label>
                <input className={input} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="BLACKSITE 07" />
              </div>

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-magenta/70">
                  // участники (username через запятую)
                </label>
                <input className={input} value={members} onChange={(e) => setMembers(e.target.value)} placeholder="bob, carol" />
              </div>

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-magenta/70">
                  // время жизни
                </label>
                <div className="flex gap-2">
                  {[1, 6, 24, 72].map((h) => (
                    <button
                      key={h}
                      onClick={() => setHours(h)}
                      className={
                        "flex-1 rounded-sm border px-2 py-2 text-xs font-bold uppercase tracking-widest transition " +
                        (hours === h
                          ? "border-cyber-magenta bg-cyber-magenta/15 neon-text-mag"
                          : "border-cyber-magenta/25 text-cyber-dim hover:border-cyber-magenta/60")
                      }
                    >
                      {h}ч
                    </button>
                  ))}
                </div>
              </div>

              {error && (
                <div className="rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}

              <button
                onClick={submit}
                disabled={busy}
                className="cyber-btn w-full rounded-sm py-2 text-xs"
                style={{ borderColor: "rgba(255,0,160,0.5)", color: "#ff00a0" }}
              >
                {busy ? "[ СОЗДАЮ... ]" : "[ ОТКРЫТЬ КОМНАТУ ]"}
              </button>

              <div className="text-center text-[9px] uppercase tracking-widest text-cyber-dim">
                предупреждение: после закрытия восстановить нельзя
              </div>
            </div>
          </div>
        </div>
    );
}
''')

# ============================================================== CSS — фракции + dark room
DARK_CSS = r'''
    /* ========== FACTION COLORS ========== */
    [data-faction="netrunners"] { --faction-color: #00f0ff; }
    [data-faction="corpo"]      { --faction-color: #f0b030; }
    [data-faction="nomads"]     { --faction-color: #ff6600; }
    [data-faction="rebels"]     { --faction-color: #ff00a0; }

    /* ========== DARK ROOM ========== */
    .dark-room-indicator {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 2px 8px;
      border: 1px solid rgba(255, 0, 160, 0.5);
      background: rgba(255, 0, 160, 0.08);
      color: #ff00a0;
      font-size: 10px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      text-shadow: 0 0 6px rgba(255, 0, 160, 0.7);
    }

    .dark-room-timer {
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
      color: #ff00a0;
      text-shadow: 0 0 6px rgba(255, 0, 160, 0.6);
      animation: dark-room-pulse 2s ease-in-out infinite;
    }
    @keyframes dark-room-pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.6; }
    }

    /* ========== FIREWALL INDICATOR ========== */
    .firewall-indicator {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 2px 6px;
      border: 1px solid rgba(252, 238, 10, 0.5);
      background: rgba(252, 238, 10, 0.08);
      color: #fcee0a;
      font-size: 10px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      text-shadow: 0 0 6px rgba(252, 238, 10, 0.7);
    }

    /* ========== RANK BADGE ========== */
    .rank-badge {
      display: inline-block;
      padding: 1px 6px;
      font-size: 9px;
      font-weight: bold;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      border: 1px solid currentColor;
    }
    .rank-novice    { color: #5a7a95; }
    .rank-runner    { color: #00f0ff; }
    .rank-netrunner { color: #ff00a0; text-shadow: 0 0 6px currentColor; }
    .rank-legend    { color: #fcee0a; text-shadow: 0 0 8px currentColor; }
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


# ============================================================== APP patches
APP_PATCHES = [
    (
        'import { useScrolling } from "./useScrolling";',
        'import { useScrolling } from "./useScrolling";\n'
        '    import FactionPicker from "./FactionPicker";\n'
        '    import DarkRoomModal from "./DarkRoomModal";',
    ),
    (
        '      const [showNetworkMap, setShowNetworkMap] = useState(false);',
        '      const [showNetworkMap, setShowNetworkMap] = useState(false);\n'
        '      const [showDarkRoom, setShowDarkRoom] = useState(false);',
    ),
    # рендер FactionPicker поверх всего, если faction не выбран
    (
        '        {deadDropChatId != null && (\n'
        '          <DeadDropModal\n'
        '            chats={chats}\n'
        '            defaultChatId={deadDropChatId}\n'
        '            onClose={() => setDeadDropChatId(null)}\n'
        '          />\n'
        '        )}',
        '        {deadDropChatId != null && (\n'
        '          <DeadDropModal\n'
        '            chats={chats}\n'
        '            defaultChatId={deadDropChatId}\n'
        '            onClose={() => setDeadDropChatId(null)}\n'
        '          />\n'
        '        )}\n'
        '\n'
        '        {showDarkRoom && (\n'
        '          <DarkRoomModal\n'
        '            currentUser={user}\n'
        '            onClose={() => setShowDarkRoom(false)}\n'
        '            onCreated={(chat) => {\n'
        '              refreshChats().then(() => { setActiveChatId(chat.id); setMode("chats"); });\n'
        '            }}\n'
        '          />\n'
        '        )}\n'
        '\n'
        '        {!user.faction && (\n'
        '          <FactionPicker user={user} onChosen={(u) => setUser(u)} />\n'
        '        )}',
    ),
    # добавить в commands
    (
        '          { id: "network", label: "Network map", icon: "🕸", action: () => setShowNetworkMap(true) },',
        '          { id: "network", label: "Network map", icon: "🕸", action: () => setShowNetworkMap(true) },\n'
        '          { id: "darkroom", label: "Open dark room", icon: "⬢", action: () => setShowDarkRoom(true) },',
    ),
]


# ============================================================== ChatList patches — Dark Room + firewall indicators
CHATLIST_PATCHES = [
    (
        '          onOpenNetworkMap?: () => void;\n'
        '          onOpenDeadDrop?: () => void;\n'
        '        }) {',
        '          onOpenNetworkMap?: () => void;\n'
        '          onOpenDeadDrop?: () => void;\n'
        '          onOpenDarkRoom?: () => void;\n'
        '        }) {',
    ),
    (
        '          onOpenNetworkMap, onOpenDeadDrop,\n'
        '        }: {',
        '          onOpenNetworkMap, onOpenDeadDrop, onOpenDarkRoom,\n'
        '        }: {',
    ),
    # добавим вкладку «⬢ DARK» рядом с DROP
    (
        '        <button\n'
        '          onClick={onOpenDeadDrop}\n'
        '          title="Dead drop"\n'
        '          className="cyberdeck-tab"\n'
        '        >\n'
        '          ⏳ DROP\n'
        '        </button>',
        '        <button\n'
        '          onClick={onOpenDeadDrop}\n'
        '          title="Dead drop"\n'
        '          className="cyberdeck-tab"\n'
        '        >\n'
        '          ⏳ DROP\n'
        '        </button>\n'
        '        <button\n'
        '          onClick={onOpenDarkRoom}\n'
        '          title="Dark room"\n'
        '          className="cyberdeck-tab"\n'
        '        >\n'
        '          ⬢ DARK\n'
        '        </button>',
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

    print("\nСпринт 19 — Фракции / Rank / Chrome / Firewall / Dark Room\n")

    for rel, content in T.items():
        write_file(root, rel, content)

    src = root / "frontend" / "src"
    # новые компоненты
    write_file(root, "frontend/src/factions.ts", T["frontend/src/factions.ts"])
    write_file(root, "frontend/src/FactionBadge.tsx", T["frontend/src/FactionBadge.tsx"])
    write_file(root, "frontend/src/FactionPicker.tsx", T["frontend/src/FactionPicker.tsx"])
    write_file(root, "frontend/src/ChromePanel.tsx", T["frontend/src/ChromePanel.tsx"])
    write_file(root, "frontend/src/UserNameBadge.tsx", T["frontend/src/UserNameBadge.tsx"])
    write_file(root, "frontend/src/DarkRoomModal.tsx", T["frontend/src/DarkRoomModal.tsx"])

    patch_file(src / "App.tsx", APP_PATCHES)
    patch_file(src / "ChatList.tsx", CHATLIST_PATCHES)

    # прокидываем onOpenDarkRoom в ChatList
    app_path = src / "App.tsx"
    app_text = app_path.read_text(encoding="utf-8")
    if "onOpenDarkRoom=" not in app_text:
        app_text = app_text.replace(
            '          onOpenDeadDrop={() => setDeadDropChatId(activeChatId ?? (chats[0]?.id ?? null))}\n'
            '        />',
            '          onOpenDeadDrop={() => setDeadDropChatId(activeChatId ?? (chats[0]?.id ?? null))}\n'
            '          onOpenDarkRoom={() => setShowDarkRoom(true)}\n'
            '        />',
            1,
        )
        app_path.write_text(app_text, encoding="utf-8")
        print(f"  ~ {app_path} (добавил onOpenDarkRoom)")

    # CSS
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "FACTION COLORS" not in css_text:
        css_text = css_text.rstrip() + "\n" + DARK_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что появится:")
    print("  🎭 FactionPicker — при первом входе (если не выбрана фракция)")
    print("  🕸 Три новых вкладки слева: ⬢ DARK")
    print("  ⚙ SettingsPanel — там будет вкладка Chrome (в след. спринте)")
    print("  📊 XP и ранг — в профиле")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())