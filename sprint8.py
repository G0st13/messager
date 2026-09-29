#!/usr/bin/env python3
"""sprint8.py - UX polish: search, reactions, pins, markdown, code, drafts, cmd palette, notifications, themes, video."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0007_sprint8.py"] = _t('''
    """sprint 8: reactions, pins, drafts

    Revision ID: 0007
    Revises: 0006
    Create Date: 2025-07-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0007"
    down_revision: Union[str, None] = "0006"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "message_reactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "message_id",
                sa.Integer(),
                sa.ForeignKey("messages.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("emoji", sa.String(16), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction"),
        )
        op.create_index("ix_reactions_message", "message_reactions", ["message_id"])

        op.add_column(
            "messages",
            sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        op.add_column(
            "messages",
            sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.add_column(
            "chat_members",
            sa.Column("draft", sa.Text(), nullable=True),
        )


    def downgrade() -> None:
        op.drop_column("chat_members", "draft")
        op.drop_column("messages", "pinned_at")
        op.drop_column("messages", "is_pinned")
        op.drop_index("ix_reactions_message", table_name="message_reactions")
        op.drop_table("message_reactions")
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
        edited_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
        is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
        pinned_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )


    class MessageReaction(Base):
        __tablename__ = "message_reactions"
        __table_args__ = (
            UniqueConstraint("message_id", "user_id", "emoji", name="uq_reaction"),
        )

        id: Mapped[int] = mapped_column(primary_key=True)
        message_id: Mapped[int] = mapped_column(
            ForeignKey("messages.id", ondelete="CASCADE"), index=True
        )
        user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
        emoji: Mapped[str] = mapped_column(String(16))
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

# ============================================================== SCHEMAS (дополнено)
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
        text: str | None = Field(default=None, max_length=4000)
        message_type: str = "text"
        attachment_id: int | None = None
        reply_to_id: int | None = None


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=4000)


    class DraftUpdate(BaseModel):
        draft: str | None = Field(default=None, max_length=5000)


    class ReactionToggle(BaseModel):
        emoji: str = Field(min_length=1, max_length=16)


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

# ============================================================== MESSAGES ROUTER
T["backend/app/routers/messages.py"] = _t('''
    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache
    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import ChatMember, File as FileModel, Message, MessageReaction, User
    from app.schemas import (
        FileRead, MessageCreate, MessageEdit, MessageRead, ReactionRead, ReactionToggle,
    )


    router = APIRouter()


    async def _ensure_member(db: AsyncSession, chat_id: int, user_id: int) -> ChatMember:
        m = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
            )
        )).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        return m


    async def _get_reactions(
        db: AsyncSession, message_id: int, current_id: int
    ) -> list[ReactionRead]:
        rows = (await db.execute(
            select(MessageReaction).where(MessageReaction.message_id == message_id)
        )).scalars().all()
        grouped: dict[str, dict] = {}
        for r in rows:
            g = grouped.setdefault(r.emoji, {"count": 0, "mine": False})
            g["count"] += 1
            if r.user_id == current_id:
                g["mine"] = True
        return [
            ReactionRead(emoji=emoji, count=v["count"], is_mine=v["mine"])
            for emoji, v in sorted(grouped.items(), key=lambda x: -x[1]["count"])
        ]


    async def _to_read(db: AsyncSession, m: Message, current_id: int = 0) -> MessageRead:
        author = (await db.execute(select(User).where(User.id == m.author_id))).scalar_one()

        attachment = None
        if m.attachment_id:
            f = (await db.execute(
                select(FileModel).where(FileModel.id == m.attachment_id)
            )).scalar_one_or_none()
            if f:
                attachment = FileRead.model_validate(f)

        reply_preview = None
        reply_author = None
        if m.reply_to_id:
            r = (await db.execute(
                select(Message).where(Message.id == m.reply_to_id)
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

        reactions = await _get_reactions(db, m.id, current_id)

        return MessageRead(
            id=m.id, chat_id=m.chat_id, author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
            text="Сообщение удалено" if m.is_deleted else m.text,
            message_type=m.message_type or "text",
            attachment=attachment,
            reply_to_id=m.reply_to_id,
            reply_preview=reply_preview, reply_author=reply_author,
            edited_at=m.edited_at,
            is_deleted=m.is_deleted,
            is_pinned=m.is_pinned,
            reactions=reactions,
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
        return [await _to_read(db, m, current.id) for m in msgs]


    @router.get("/{chat_id}/search", response_model=list[MessageRead])
    async def search_messages(
        chat_id: int,
        current: CurrentUser,
        q: str = Query(..., min_length=1, max_length=200),
        limit: int = Query(50, le=100),
        db: AsyncSession = Depends(get_session),
    ):
        await _ensure_member(db, chat_id, current.id)
        pattern = f"%{q}%"
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.is_deleted == False,  # noqa: E712
                Message.text.ilike(pattern),
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        msgs = (await db.execute(stmt)).scalars().all()
        return [await _to_read(db, m, current.id) for m in msgs]


    @router.get("/{chat_id}/pinned", response_model=list[MessageRead])
    async def list_pinned(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        await _ensure_member(db, chat_id, current.id)
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.is_pinned == True,  # noqa: E712
            )
            .order_by(Message.pinned_at.desc())
            .limit(20)
        )
        msgs = (await db.execute(stmt)).scalars().all()
        return [await _to_read(db, m, current.id) for m in msgs]


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
            chat_id=chat_id, author_id=current.id,
            text=payload.text, message_type=payload.message_type,
            attachment_id=payload.attachment_id, reply_to_id=payload.reply_to_id,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        await cache.invalidate_chat_list(db, chat_id)
        return await _to_read(db, msg, current.id)


    @router.patch("/messages/{message_id}", response_model=MessageRead)
    async def edit_message(
        message_id: int,
        payload: MessageEdit,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        if msg.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your message")
        msg.text = payload.text
        msg.edited_at = datetime.now(timezone.utc)
        await db.flush()
        await db.refresh(msg)
        await cache.invalidate_chat_list(db, msg.chat_id)
        return await _to_read(db, msg, current.id)


    @router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_message(
        message_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        if msg.author_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your message")
        msg.is_deleted = True
        msg.text = ""
        await db.flush()
        await cache.invalidate_chat_list(db, msg.chat_id)


    @router.post("/messages/{message_id}/reactions", response_model=list[ReactionRead])
    async def toggle_reaction(
        message_id: int,
        payload: ReactionToggle,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        await _ensure_member(db, msg.chat_id, current.id)

        existing = (await db.execute(
            select(MessageReaction).where(
                MessageReaction.message_id == message_id,
                MessageReaction.user_id == current.id,
                MessageReaction.emoji == payload.emoji,
            )
        )).scalar_one_or_none()

        if existing:
            await db.delete(existing)
        else:
            db.add(MessageReaction(
                message_id=message_id, user_id=current.id, emoji=payload.emoji,
            ))
        await db.flush()
        return await _get_reactions(db, message_id, current.id)


    @router.post("/messages/{message_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
    async def pin_message(
        message_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        await _ensure_member(db, msg.chat_id, current.id)
        msg.is_pinned = True
        msg.pinned_at = datetime.now(timezone.utc)
        await db.flush()


    @router.delete("/messages/{message_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
    async def unpin_message(
        message_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        msg = (await db.execute(
            select(Message).where(Message.id == message_id)
        )).scalar_one_or_none()
        if msg is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "message not found")
        await _ensure_member(db, msg.chat_id, current.id)
        msg.is_pinned = False
        msg.pinned_at = None
        await db.flush()
''')

# ============================================================== CHATS ROUTER — добавить draft
T["backend/app/routers/chats.py"] = _t('''
    from __future__ import annotations

    import secrets

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache
    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, Message, User
    from app.schemas import (
        AddMemberRequest, ChatCreate, ChatMemberRead, ChatRead, ChatUpdate, DraftUpdate,
        InviteRead, MessageRead, UserRead,
    )
    from app.websocket_manager import manager


    router = APIRouter()

    GROUP_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
        "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#f43f5e",
    ]


    def _msg_to_read(m: Message, author: User) -> MessageRead:
        return MessageRead(
            id=m.id, chat_id=m.chat_id, author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
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
            "edited_at": None, "is_deleted": False,
            "created_at": msg.created_at.isoformat(),
            "author_id": actor.id, "author_username": actor.username,
            "author_display": actor.display_name,
            "author_avatar_color": actor.avatar_color,
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
            peer = UserRead.model_validate(peer_obj) if peer_obj else None

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

        if not payload.is_group and len(member_ids) == 2:
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
            title=payload.title, is_group=payload.is_group,
            avatar_color=color,
            invite_token=secrets.token_urlsafe(16) if payload.is_group else None,
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

# ============================================================== WS ROUTER — add reactions/pin broadcasts
T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

    import json
    from datetime import datetime, timezone

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app import cache
    from app.db import SessionLocal
    from app.models import ChatMember, File as FileModel, Message, MessageReaction, User
    from app.security import decode_token
    from app.websocket_manager import manager


    router = APIRouter()


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
    async def ws_endpoint(ws: WebSocket, token: str) -> None:
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except Exception:
            await ws.close(code=4401)
            return

        async with SessionLocal() as db:
            user = (await db.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()
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
                            message_type=message_type,
                            attachment_id=attachment_id, reply_to_id=reply_to_id,
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
                            "text": text, "message_type": message_type,
                            "attachment": attachment,
                            "reply_to_id": reply_to_id,
                            "reply_preview": reply_preview, "reply_author": reply_author,
                            "edited_at": None, "is_deleted": False, "is_pinned": False,
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
        finally:
            await manager.disconnect(ws)
            async with SessionLocal() as db:
                u = (await db.execute(
                    select(User).where(User.id == user_id)
                )).scalar_one_or_none()
                if u:
                    u.last_seen = datetime.now(timezone.utc)
                    await db.commit()
            await manager.broadcast_all({
                "type": "presence", "user_id": user_id, "online": False,
                "last_seen": datetime.now(timezone.utc).isoformat(),
            })
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
      is_pinned: boolean;
      reactions: Reaction[];
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

    export type ThemeName = "cyber" | "matrix" | "sunset" | "amber";
''')

# ============================================================== THEMES
T["frontend/src/themes.ts"] = _t('''
    import type { ThemeName } from "./types";

    export interface Theme {
      name: ThemeName;
      label: string;
      vars: Record<string, string>;
    }

    export const THEMES: Theme[] = [
      {
        name: "cyber",
        label: "◈ CYBER",
        vars: {
          "--neon-cyan": "#00f0ff",
          "--neon-magenta": "#ff00a0",
          "--neon-yellow": "#fcee0a",
          "--bg-deep": "#05070d",
          "--bg-panel": "#0a0f1a",
          "--bg-elev": "#0f1522",
          "--border": "#1a2537",
          "--text-primary": "#b8d4e8",
        },
      },
      {
        name: "matrix",
        label: "▶ MATRIX",
        vars: {
          "--neon-cyan": "#00ff41",
          "--neon-magenta": "#00cc33",
          "--neon-yellow": "#aaffaa",
          "--bg-deep": "#000600",
          "--bg-panel": "#001100",
          "--bg-elev": "#002200",
          "--border": "#003300",
          "--text-primary": "#88ff88",
        },
      },
      {
        name: "sunset",
        label: "☀ SUNSET",
        vars: {
          "--neon-cyan": "#ff6b35",
          "--neon-magenta": "#f7931e",
          "--neon-yellow": "#ffd23f",
          "--bg-deep": "#1a0d1a",
          "--bg-panel": "#26101f",
          "--bg-elev": "#331522",
          "--border": "#4d2030",
          "--text-primary": "#ffd6b8",
        },
      },
      {
        name: "amber",
        label: "◆ AMBER",
        vars: {
          "--neon-cyan": "#ffb000",
          "--neon-magenta": "#ff7700",
          "--neon-yellow": "#ffcc00",
          "--bg-deep": "#0d0a05",
          "--bg-panel": "#1a1208",
          "--bg-elev": "#261a0c",
          "--border": "#3d2c14",
          "--text-primary": "#e8d4a8",
        },
      },
    ];

    export function applyTheme(name: ThemeName) {
      const theme = THEMES.find((t) => t.name === name) || THEMES[0];
      const root = document.documentElement;
      Object.entries(theme.vars).forEach(([k, v]) => root.style.setProperty(k, v));
      // Обновляем tailwind-переменные цветов
      root.style.setProperty("--tw-cyber-cyan", theme.vars["--neon-cyan"]);
    }
''')

# ============================================================== MARKDOWN
T["frontend/src/markdown.tsx"] = _t('''
    import React from "react";

    function escapeHtml(s: string): string {
      return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
    }

    function renderInline(text: string, key: number): React.ReactNode[] {
      const nodes: React.ReactNode[] = [];
      let rest = text;
      let i = 0;
      const push = (n: React.ReactNode) => nodes.push(n);

      while (rest.length > 0) {
        let m: RegExpMatchArray | null;

        // code `text`
        if ((m = rest.match(/^`([^`]+)`/))) {
          push(
            <code
              key={`c${key}-${i++}`}
              className="rounded-sm border border-cyber-cyan/30 bg-black/40 px-1.5 py-0.5 font-mono text-[0.9em] text-cyber-cyan"
            >
              {m[1]}
            </code>
          );
          rest = rest.slice(m[0].length);
          continue;
        }

        // link [text](url)
        if ((m = rest.match(/^\\[([^\\]]+)\\]\\((https?:\\/\\/[^\\s)]+)\\)/))) {
          push(
            <a
              key={`a${key}-${i++}`}
              href={m[2]}
              target="_blank"
              rel="noreferrer"
              className="neon-text underline decoration-cyber-cyan/50 hover:decoration-cyber-cyan"
            >
              {m[1]}
            </a>
          );
          rest = rest.slice(m[0].length);
          continue;
        }

        // bold **text**
        if ((m = rest.match(/^\\*\\*([^*]+)\\*\\*/))) {
          push(<strong key={`b${key}-${i++}`} className="font-bold text-cyber-cyan">{m[1]}</strong>);
          rest = rest.slice(m[0].length);
          continue;
        }

        // italic *text* (single)
        if ((m = rest.match(/^\\*([^*\\n]+)\\*/))) {
          push(<em key={`i${key}-${i++}`} className="italic text-cyber-cyan/90">{m[1]}</em>);
          rest = rest.slice(m[0].length);
          continue;
        }

        // underline _text_
        if ((m = rest.match(/^_([^_]+)_/))) {
          push(<u key={`u${key}-${i++}`} className="underline decoration-dotted">{m[1]}</u>);
          rest = rest.slice(m[0].length);
          continue;
        }

        // strike ~~text~~
        if ((m = rest.match(/^~~([^~]+)~~/))) {
          push(<s key={`s${key}-${i++}`} className="line-through opacity-70">{m[1]}</s>);
          rest = rest.slice(m[0].length);
          continue;
        }

        // autolink http(s)://...
        if ((m = rest.match(/^(https?:\\/\\/[^\\s]+)/))) {
          push(
            <a
              key={`al${key}-${i++}`}
              href={m[1]}
              target="_blank"
              rel="noreferrer"
              className="neon-text underline decoration-cyber-cyan/50 hover:decoration-cyber-cyan break-all"
            >
              {m[1]}
            </a>
          );
          rest = rest.slice(m[0].length);
          continue;
        }

        // plain text (до следующего маркера)
        const nextMark = rest.search(/[`\\[*_~h]/);
        if (nextMark === -1) {
          push(rest);
          rest = "";
        } else if (nextMark === 0) {
          push(rest[0]);
          rest = rest.slice(1);
        } else {
          push(rest.slice(0, nextMark));
          rest = rest.slice(nextMark);
        }
      }

      return nodes;
    }

    export function renderMarkdown(text: string): React.ReactNode {
      if (!text) return null;

      // Разбиваем на блоки: ``` ... ``` и остальное
      const parts = text.split(/```/);

      return (
        <div className="space-y-1">
          {parts.map((part, idx) => {
            const isCode = idx % 2 === 1;
            if (isCode) {
              // Первая строка — язык (если есть)
              const nl = part.indexOf("\\n");
              const lang = nl > 0 && part.slice(0, nl).length < 20
                ? part.slice(0, nl).trim()
                : "";
              const code = (lang ? part.slice(nl + 1) : part).replace(/\\n$/, "");

              return (
                <div
                  key={`code-${idx}`}
                  className="my-2 overflow-hidden rounded-sm border border-cyber-cyan/40 bg-black/60"
                >
                  {lang && (
                    <div className="border-b border-cyber-cyan/20 bg-cyber-cyan/5 px-3 py-1 text-[9px] uppercase tracking-widest neon-text">
                      // {lang}
                    </div>
                  )}
                  <pre className="overflow-x-auto p-3 text-[12px] leading-relaxed">
                    <code className="font-mono text-cyber-cyan/90">{code}</code>
                  </pre>
                </div>
              );
            }
            // Обычный текст — разбиваем по строкам
            return (
              <React.Fragment key={`txt-${idx}`}>
                {part.split("\\n").map((line, li) => (
                  <React.Fragment key={`l-${idx}-${li}`}>
                    {li > 0 && <br />}
                    {renderInline(line, idx * 1000 + li)}
                  </React.Fragment>
                ))}
              </React.Fragment>
            );
          })}
        </div>
      );
    }
''')

# ============================================================== NOTIFICATIONS
T["frontend/src/notifications.ts"] = _t('''
    let audioCtx: AudioContext | null = null;

    export async function ensureNotificationPermission(): Promise<boolean> {
      if (!("Notification" in window)) return false;
      if (Notification.permission === "granted") return true;
      if (Notification.permission === "denied") return false;
      const result = await Notification.requestPermission();
      return result === "granted";
    }

    export function showNotification(title: string, body: string, tag?: string) {
      try {
        if (!("Notification" in window)) return;
        if (Notification.permission !== "granted") return;
        if (document.visibilityState === "visible") return; // не отвлекаем
        new Notification(title, {
          body,
          tag,
          icon: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='26' font-size='26'>◈</text></svg>",
        });
      } catch {}
    }

    export function playPing() {
      try {
        if (!audioCtx) {
          const Ctor = (window as any).AudioContext || (window as any).webkitAudioContext;
          if (!Ctor) return;
          audioCtx = new Ctor();
        }
        const ctx = audioCtx!;
        const now = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(880, now);
        osc.frequency.exponentialRampToValueAtTime(440, now + 0.15);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.3);
      } catch {}
    }
''')

# ============================================================== COMMAND PALETTE
T["frontend/src/CommandPalette.tsx"] = _t('''
    import { useEffect, useMemo, useRef, useState } from "react";

    export interface Command {
      id: string;
      label: string;
      hint?: string;
      icon: string;
      action: () => void;
    }

    export default function CommandPalette({
      commands, onClose
    }: {
      commands: Command[];
      onClose: () => void;
    }) {
      const [query, setQuery] = useState("");
      const [selected, setSelected] = useState(0);
      const inputRef = useRef<HTMLInputElement>(null);

      useEffect(() => {
        inputRef.current?.focus();
        const h = (e: KeyboardEvent) => {
          if (e.key === "Escape") onClose();
        };
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, [onClose]);

      const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return commands;
        return commands.filter((c) =>
          c.label.toLowerCase().includes(q) ||
          (c.hint || "").toLowerCase().includes(q)
        );
      }, [commands, query]);

      useEffect(() => { setSelected(0); }, [query]);

      const onKey = (e: React.KeyboardEvent) => {
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setSelected((s) => Math.min(s + 1, filtered.length - 1));
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setSelected((s) => Math.max(s - 1, 0));
        } else if (e.key === "Enter") {
          e.preventDefault();
          const cmd = filtered[selected];
          if (cmd) {
            cmd.action();
            onClose();
          }
        }
      };

      return (
        <div
          className="fixed inset-0 z-[300] flex items-start justify-center bg-black/70 p-4 pt-24 backdrop-blur"
          onClick={onClose}
        >
          <div
            className="corner-frame w-full max-w-xl overflow-hidden rounded-sm border border-cyber-cyan/50 bg-cyber-panel shadow-neon-cyan"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-cyber-cyan/20 bg-black/40 p-3">
              <div className="flex items-center gap-2">
                <span className="neon-text text-lg">▸</span>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={onKey}
                  placeholder="COMMAND..."
                  className="w-full bg-transparent text-sm uppercase tracking-widest text-cyber-text outline-none placeholder:text-cyber-dim"
                />
                <span className="text-[9px] uppercase tracking-widest text-cyber-dim">ESC</span>
              </div>
            </div>

            <div className="max-h-80 overflow-y-auto">
              {filtered.length === 0 && (
                <div className="p-6 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                  // no commands found
                </div>
              )}
              {filtered.map((c, i) => (
                <button
                  key={c.id}
                  onClick={() => { c.action(); onClose(); }}
                  onMouseEnter={() => setSelected(i)}
                  className={
                    "flex w-full items-center gap-3 border-b border-cyber-cyan/10 px-4 py-3 text-left transition " +
                    (i === selected
                      ? "bg-cyber-cyan/15 border-l-2 border-l-cyber-cyan"
                      : "border-l-2 border-l-transparent hover:bg-cyber-cyan/5")
                  }
                >
                  <span className="text-lg">{c.icon}</span>
                  <div className="min-w-0 flex-1">
                    <div className={"truncate text-sm font-bold uppercase tracking-wider " + (i === selected ? "neon-text" : "text-cyber-text")}>
                      {c.label}
                    </div>
                    {c.hint && (
                      <div className="truncate text-[10px] uppercase tracking-widest text-cyber-dim">
                        {c.hint}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between border-t border-cyber-cyan/20 bg-black/40 px-4 py-2 text-[9px] uppercase tracking-widest text-cyber-dim">
              <span>↑↓ navigate · ⏎ select · esc close</span>
              <span>{filtered.length} results</span>
            </div>
          </div>
        </div>
      );
    }
''')

# ============================================================== SEARCH MODAL
T["frontend/src/SearchModal.tsx"] = _t('''
    import { useEffect, useRef, useState } from "react";
    import { api } from "./api";
    import type { Message } from "./types";

    export default function SearchModal({
      chatId, onClose, onJumpTo
    }: {
      chatId: number;
      onClose: () => void;
      onJumpTo: (messageId: number) => void;
    }) {
      const [query, setQuery] = useState("");
      const [results, setResults] = useState<Message[]>([]);
      const [busy, setBusy] = useState(false);
      const inputRef = useRef<HTMLInputElement>(null);
      const debounceRef = useRef<number | null>(null);

      useEffect(() => {
        inputRef.current?.focus();
        const h = (e: KeyboardEvent) => e.key === "Escape" && onClose();
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, [onClose]);

      useEffect(() => {
        if (debounceRef.current) window.clearTimeout(debounceRef.current);
        if (!query.trim()) {
          setResults([]);
          return;
        }
        debounceRef.current = window.setTimeout(async () => {
          setBusy(true);
          try {
            const { data } = await api.get<Message[]>(`/chats/${chatId}/search`, {
              params: { q: query.trim() },
            });
            setResults(data);
          } finally {
            setBusy(false);
          }
        }, 300);
        return () => {
          if (debounceRef.current) window.clearTimeout(debounceRef.current);
        };
      }, [query, chatId]);

      const highlight = (text: string | null) => {
        if (!text) return null;
        const q = query.trim();
        if (!q) return text;
        const idx = text.toLowerCase().indexOf(q.toLowerCase());
        if (idx === -1) return text;
        return (
          <>
            {text.slice(0, idx)}
            <mark className="bg-cyber-yellow/40 text-cyber-yellow px-0.5 rounded-sm">
              {text.slice(idx, idx + q.length)}
            </mark>
            {text.slice(idx + q.length)}
          </>
        );
      };

      return (
        <div
          className="fixed inset-0 z-[250] flex items-start justify-center bg-black/70 p-4 pt-24 backdrop-blur"
          onClick={onClose}
        >
          <div
            className="corner-frame w-full max-w-2xl overflow-hidden rounded-sm border border-cyber-cyan/50 bg-cyber-panel shadow-neon-cyan"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="border-b border-cyber-cyan/20 bg-black/40 p-3">
              <div className="flex items-center gap-2">
                <span className="neon-text text-lg">⌕</span>
                <input
                  ref={inputRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="SEARCH MESSAGES..."
                  className="w-full bg-transparent text-sm uppercase tracking-widest text-cyber-text outline-none placeholder:text-cyber-dim"
                />
                {busy && <span className="text-[9px] uppercase tracking-widest neon-text animate-pulse">scanning...</span>}
              </div>
            </div>

            <div className="max-h-[60vh] overflow-y-auto">
              {query.trim() && results.length === 0 && !busy && (
                <div className="p-8 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                  // no matches
                </div>
              )}
              {!query.trim() && (
                <div className="p-8 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                  введите запрос для поиска
                </div>
              )}
              {results.map((m) => (
                <button
                  key={m.id}
                  onClick={() => { onJumpTo(m.id); onClose(); }}
                  className="block w-full border-b border-cyber-cyan/10 border-l-2 border-l-transparent px-4 py-3 text-left transition hover:bg-cyber-cyan/5 hover:border-l-cyber-cyan"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-[10px] font-bold uppercase tracking-widest neon-text-mag">
                      ◂ {m.author_display || m.author_username}
                    </span>
                    <span className="text-[9px] uppercase tracking-widest text-cyber-dim">
                      {new Date(m.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="mt-1 line-clamp-2 text-sm text-cyber-text">
                    {highlight(m.text)}
                  </div>
                </button>
              ))}
            </div>

            <div className="flex items-center justify-between border-t border-cyber-cyan/20 bg-black/40 px-4 py-2 text-[9px] uppercase tracking-widest text-cyber-dim">
              <span>esc close</span>
              <span>{results.length} hits</span>
            </div>
          </div>
        </div>
    );
''')

# ============================================================== MESSAGE BUBBLE
T["frontend/src/MessageBubble.tsx"] = _t('''
    import { useState } from "react";
    import Avatar from "./Avatar";
    import { fileUrl, humanSize } from "./api";
    import { renderMarkdown } from "./markdown";
    import type { Message, User } from "./types";

    const QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🔥"];

    function iconFor(mime: string): string {
      if (mime.startsWith("image/")) return "▣";
      if (mime.startsWith("audio/")) return "◍";
      if (mime.startsWith("video/")) return "▶";
      if (mime.includes("pdf")) return "▤";
      if (mime.includes("zip")) return "▥";
      return "▧";
    }

    function fmtDuration(sec: number): string {
      const m = Math.floor(sec / 60);
      const s = Math.floor(sec % 60);
      return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    }

    export default function MessageBubble({
      msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer,
      onOpenImage, onOpenProfile, onReact, onPin
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
      onReact: (messageId: number, emoji: string) => void;
      onPin: (m: Message) => void;
    }) {
      const [menuOpen, setMenuOpen] = useState(false);
      const [reactOpen, setReactOpen] = useState(false);
      const [audioPlaying, setAudioPlaying] = useState(false);
      const [audioCurrent, setAudioCurrent] = useState(0);
      const [audioDuration, setAudioDuration] = useState(0);

      if (msg.message_type === "system") {
        return (
          <div className="my-2 flex justify-center">
            <div className="neon-border-yel rounded-sm bg-cyber-yellow/5 px-3 py-1 text-[10px] uppercase tracking-widest neon-text-yel">
              ⚠ {msg.text}
            </div>
          </div>
        );
      }

      const author: Pick<User, "username" | "display_name" | "avatar_color"> = {
        username: msg.author_username,
        display_name: msg.author_display,
        avatar_color: msg.author_avatar_color,
      };

      const accent = mine ? "#00f0ff" : "#ff00a0";
      const bubbleStyle = {
        background: mine
          ? "linear-gradient(135deg, rgba(0,240,255,0.08), rgba(0,240,255,0.02))"
          : "linear-gradient(135deg, rgba(255,0,160,0.06), rgba(255,0,160,0.01))",
        border: `1px solid ${accent}55`,
        boxShadow: `0 0 12px ${accent}22, inset 0 0 12px ${accent}08`,
        color: "#d6ecff",
      };

      const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
      const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
      const isVideo = msg.message_type === "file" && msg.attachment &&
        msg.attachment.content_type.startsWith("video/") && !msg.is_deleted;
      const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
      const isFile = msg.message_type === "file" && msg.attachment && !isVideo && !msg.is_deleted;

      const hasReactions = msg.reactions && msg.reactions.length > 0;

      if (isSticker) {
        return (
          <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")}>
            {!mine ? (
              <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
                {showAvatar && <Avatar user={author} size={32} />}
              </button>
            ) : null}
            <div className="relative">
              <div className="animate-materialize text-7xl leading-none drop-shadow-[0_0_20px_rgba(0,240,255,0.5)]">
                {msg.text}
              </div>
              <div className={"mt-1 flex items-center gap-2 text-[9px] uppercase tracking-wider " + (mine ? "justify-end" : "")}>
                <span className="text-cyber-dim">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && (
                  <span className={readByPeer ? "neon-text" : "text-cyber-dim"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      }

      return (
        <div className={"group flex gap-2 " + (mine ? "flex-row-reverse" : "")} id={`msg-${msg.id}`}>
          {!mine ? (
            <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
              {showAvatar && <Avatar user={author} size={32} />}
            </button>
          ) : null}

          <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
            {!mine && showAvatar && (
              <button
                onClick={() => onOpenProfile(msg.author_id)}
                className="mb-1 ml-2 text-[10px] font-bold uppercase tracking-widest neon-text-mag chroma"
              >
                ◂ {msg.author_display || msg.author_username}
              </button>
            )}

            <div
              className={"animate-materialize relative overflow-hidden rounded-sm text-sm " + (isImage || isVideo ? "" : " px-3 py-2")}
              style={bubbleStyle}
            >
              <div
                className="absolute left-0 right-0 top-0 h-[1px]"
                style={{ background: `linear-gradient(90deg, transparent, ${accent}, transparent)` }}
              />

              {msg.is_pinned && (
                <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">
                  📌 pinned
                </div>
              )}

              {msg.reply_to_id && !msg.is_deleted && (
                <div
                  className="mx-1 mb-2 mt-1 rounded-sm border-l-2 bg-black/40 px-2 py-1 text-[10px]"
                  style={{ borderColor: accent }}
                >
                  <div className="font-bold uppercase tracking-wider" style={{ color: accent }}>
                    ↳ {msg.reply_author || "?"}
                  </div>
                  <div className="truncate text-cyber-dim">{msg.reply_preview || "..."}</div>
                </div>
              )}

              {isImage && msg.attachment && (
                <img
                  src={fileUrl(msg.attachment.id)}
                  alt={msg.attachment.filename}
                  onClick={() => onOpenImage(fileUrl(msg.attachment!.id))}
                  className="block max-h-80 w-full cursor-pointer object-cover"
                  style={{ filter: "contrast(1.05) saturate(1.1)" }}
                />
              )}

              {isVideo && msg.attachment && (
                <video
                  src={fileUrl(msg.attachment.id)}
                  controls
                  className="block max-h-80 w-full bg-black"
                />
              )}

              {isVoice && msg.attachment && (
                <div className="flex items-center gap-3 px-2 py-3" style={{ minWidth: 220 }}>
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
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm neon-border"
                    style={{ color: accent }}
                  >
                    {audioPlaying ? "❚❚" : "▶"}
                  </button>
                  <div className="flex-1 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-xl" style={{ color: accent }}>◍</span>
                      <span className="font-mono neon-text">
                        {fmtDuration(audioPlaying ? audioCurrent : (audioDuration || 0))}
                      </span>
                    </div>
                    <div className="mt-1 flex h-3 items-end gap-[2px]">
                      {Array.from({ length: 24 }).map((_, i) => (
                        <div
                          key={i}
                          className="w-[2px]"
                          style={{
                            height: `${20 + ((i * 7) % 80)}%`,
                            background: accent,
                            opacity: audioPlaying ? 0.8 : 0.35,
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {isFile && msg.attachment && (
                <a
                  href={fileUrl(msg.attachment.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-3 px-2 py-2 transition hover:bg-cyber-cyan/5"
                >
                  <div className="text-2xl" style={{ color: accent }}>
                    {iconFor(msg.attachment.content_type)}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-bold text-cyber-text">
                      {msg.attachment.filename}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-cyber-dim">
                      {humanSize(msg.attachment.size)}
                    </div>
                  </div>
                </a>
              )}

              {!isImage && !isVideo && !isVoice && !isFile && (
                <div className={msg.is_deleted ? "italic opacity-50 text-xs" : "break-words"}>
                  {msg.is_deleted ? msg.text : renderMarkdown(msg.text || "")}
                </div>
              )}

              {/* Reactions */}
              {hasReactions && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {msg.reactions.map((r) => (
                    <button
                      key={r.emoji}
                      onClick={() => onReact(msg.id, r.emoji)}
                      className={
                        "flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs transition " +
                        (r.is_mine
                          ? "border-cyber-cyan bg-cyber-cyan/15 neon-text"
                          : "border-cyber-cyan/25 bg-black/30 text-cyber-text hover:border-cyber-cyan/60")
                      }
                    >
                      <span>{r.emoji}</span>
                      <span className="text-[10px] font-bold">{r.count}</span>
                    </button>
                  ))}
                </div>
              )}

              <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">
                {msg.edited_at && <span className="text-cyber-yellow/70">[edited]</span>}
                <span className="text-cyber-dim">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && !msg.is_deleted && (
                  <span className={readByPeer ? "neon-text" : "text-cyber-dim"}>
                    {readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>

            {/* Hover actions */}
            {!msg.is_deleted && (
              <div
                className={
                  "absolute top-1 hidden items-center gap-1 group-hover:flex " +
                  (mine ? "right-full mr-1" : "left-full ml-1")
                }
              >
                <button
                  onClick={() => setReactOpen(!reactOpen)}
                  className="rounded-sm border border-cyber-cyan/40 bg-cyber-panel/90 px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"
                  title="Reaction"
                >
                  ☺
                </button>
                <button
                  onClick={() => setMenuOpen(!menuOpen)}
                  className="rounded-sm border border-cyber-cyan/40 bg-cyber-panel/90 px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"
                  title="Menu"
                >
                  ▾
                </button>
              </div>
            )}

            {/* Reaction picker */}
            {reactOpen && (
              <div
                className={
                  "animate-materialize absolute top-8 z-30 flex gap-1 rounded-sm border border-cyber-cyan/50 bg-cyber-panel p-1 shadow-neon-cyan " +
                  (mine ? "right-0" : "left-0")
                }
                onMouseLeave={() => setReactOpen(false)}
              >
                {QUICK_REACTIONS.map((e) => (
                  <button
                    key={e}
                    onClick={() => { onReact(msg.id, e); setReactOpen(false); }}
                    className="rounded-sm p-1 text-lg transition hover:bg-cyber-cyan/20"
                  >
                    {e}
                  </button>
                ))}
              </div>
            )}

            {/* Menu */}
            {menuOpen && (
              <div
                className={
                  "animate-materialize absolute z-20 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 bg-cyber-panel text-xs shadow-neon-cyan " +
                  (mine ? "right-0" : "left-0")
                }
              >
                <button
                  onClick={() => { onReply(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
                >
                  ↳ reply
                </button>
                <button
                  onClick={() => { onPin(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-yellow hover:bg-cyber-yellow/15"
                >
                  📌 {msg.is_pinned ? "unpin" : "pin"}
                </button>
                {mine && msg.message_type === "text" && (
                  <button
                    onClick={() => { onEdit(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
                  >
                    ✎ edit
                  </button>
                )}
                {mine && (
                  <button
                    onClick={() => { onDelete(msg); setMenuOpen(false); }}
                    className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"
                  >
                    ✕ delete
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
''')

# ============================================================== CHAT WINDOW
T["frontend/src/ChatWindow.tsx"] = _t('''
    import { useEffect, useMemo, useRef, useState } from "react";
    import Avatar from "./Avatar";
    import MessageBubble from "./MessageBubble";
    import EmojiPicker from "./EmojiPicker";
    import StickerPicker from "./StickerPicker";
    import FileUpload from "./FileUpload";
    import VoiceRecorder from "./VoiceRecorder";
    import Lightbox from "./Lightbox";
    import SearchModal from "./SearchModal";
    import { api } from "./api";
    import type { Chat, Message, User } from "./types";

    function dayLabel(iso: string) {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) return "▸ TODAY";
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "▸ YESTERDAY";
      return "▸ " + d.toLocaleDateString([], { day: "numeric", month: "long" }).toUpperCase();
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
      const [showSearch, setShowSearch] = useState(false);
      const [pinned, setPinned] = useState<Message[]>([]);
      const [pinnedIdx, setPinnedIdx] = useState(0);
      const [highlightId, setHighlightId] = useState<number | null>(null);
      const bottomRef = useRef<HTMLDivElement>(null);
      const typingTimeout = useRef<number | null>(null);
      const lastTypingSent = useRef<number>(0);
      const draftTimer = useRef<number | null>(null);

      // load messages + draft
      useEffect(() => {
        api.get<Message[]>(`/chats/${chat.id}/messages`).then((r) => setMessages(r.data));
        api.get<{ draft: string }>(`/chats/${chat.id}/draft`).then((r) => {
          if (r.data.draft) setText(r.data.draft);
          else setText("");
        }).catch(() => setText(""));
        api.get<Message[]>(`/chats/${chat.id}/pinned`).then((r) => setPinned(r.data)).catch(() => {});
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

      // auto-save draft
      useEffect(() => {
        if (draftTimer.current) window.clearTimeout(draftTimer.current);
        draftTimer.current = window.setTimeout(() => {
          api.patch(`/chats/${chat.id}/draft`, { draft: text || null }).catch(() => {});
        }, 800);
        return () => {
          if (draftTimer.current) window.clearTimeout(draftTimer.current);
        };
      }, [text, chat.id]);

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
                edited_at: null, is_deleted: false, is_pinned: d.is_pinned || false,
                reactions: d.reactions || [],
                created_at: d.created_at,
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
          } else if (d.type === "reactions" && d.chat_id === chat.id) {
            setMessages((prev) =>
              prev.map((m) => m.id === d.message_id ? { ...m, reactions: d.reactions } : m)
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

      const handleReact = (messageId: number, emoji: string) => {
        send({ type: "reaction", message_id: messageId, emoji });
      };

      const handlePin = async (m: Message) => {
        try {
          if (m.is_pinned) {
            await api.delete(`/chats/messages/${m.id}/pin`);
            setPinned((prev) => prev.filter((x) => x.id !== m.id));
            setMessages((prev) => prev.map((x) => x.id === m.id ? { ...x, is_pinned: false } : x));
          } else {
            await api.post(`/chats/messages/${m.id}/pin`);
            setPinned((prev) => [m, ...prev.filter((x) => x.id !== m.id)]);
            setMessages((prev) => prev.map((x) => x.id === m.id ? { ...x, is_pinned: true } : x));
          }
        } catch {}
      };

      const jumpTo = (messageId: number) => {
        setHighlightId(messageId);
        setTimeout(() => {
          const el = document.getElementById(`msg-${messageId}`);
          el?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 50);
        setTimeout(() => setHighlightId(null), 2000);
      };

      const onKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          doSend();
        }
        if (e.key === "Escape") {
          setReplyTo(null);
          setEditing(null);
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

      // Ctrl+F — open search
      useEffect(() => {
        const h = (e: KeyboardEvent) => {
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "f") {
            e.preventDefault();
            setShowSearch(true);
          }
        };
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, []);

      const peerOnline = chat.peer ? onlineUsers.has(chat.peer.id) : false;
      const headerTitle = chat.peer
        ? chat.peer.display_name || chat.peer.username
        : chat.title || `NODE #${chat.id}`;
      const headerSub = typingUsers.size > 0
        ? "▸ typing…"
        : chat.peer
        ? (peerOnline ? "◉ online" : "○ offline")
        : `${chat.member_count} nodes`;

      const avatarUser = chat.peer || {
        username: chat.title || "G",
        display_name: chat.title || "GRP",
        avatar_color: chat.avatar_color || "#ff00a0",
      };

      const currentPinned = pinned[pinnedIdx] || null;

      return (
        <main className="relative z-10 flex flex-1 flex-col">
          {/* Header */}
          <header className="flex items-center gap-2 border-b border-cyber-cyan/20 bg-cyber-panel/60 px-4 py-2 backdrop-blur">
            <button
              onClick={() => chat.peer ? onOpenUser(chat.peer.id) : onOpenInfo()}
              className="flex min-w-0 flex-1 items-center gap-3 transition hover:opacity-90"
            >
              <Avatar user={avatarUser as any} size={40} showOnline={!!chat.peer} online={peerOnline} />
              <div className="min-w-0 flex-1 text-left">
                <div className="truncate font-bold neon-text">{headerTitle}</div>
                <div className="truncate text-[10px] uppercase tracking-widest text-cyber-dim">{headerSub}</div>
              </div>
            </button>

            <button
              onClick={() => setShowSearch(true)}
              title="Search (Ctrl+F)"
              className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
            >
              ⌕
            </button>

            {chat.peer && (
              <>
                <button
                  onClick={() => onStartCall("audio")}
                  title="Audio call"
                  className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
                >
                  ☎
                </button>
                <button
                  onClick={() => onStartCall("video")}
                  title="Video call"
                  className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
                >
                  ▶
                </button>
              </>
            )}

            {chat.is_group && (
              <button
                onClick={onOpenInfo}
                title="Group info"
                className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10"
              >
                ℹ
              </button>
            )}
          </header>

          {/* Pinned bar */}
          {currentPinned && (
            <div className="flex items-center gap-2 border-b border-cyber-yellow/30 bg-cyber-yellow/5 px-4 py-1.5">
              <span className="text-cyber-yellow">📌</span>
              <button
                onClick={() => jumpTo(currentPinned.id)}
                className="min-w-0 flex-1 text-left text-xs text-cyber-text hover:underline"
              >
                <div className="truncate">
                  <span className="text-[10px] uppercase tracking-widest neon-text-yel">
                    {currentPinned.author_display || currentPinned.author_username}:
                  </span>{" "}
                  {currentPinned.text || "[attachment]"}
                </div>
              </button>
              {pinned.length > 1 && (
                <div className="flex items-center gap-1 text-[10px] text-cyber-dim">
                  <button
                    onClick={() => setPinnedIdx((i) => (i - 1 + pinned.length) % pinned.length)}
                    className="rounded-sm px-1 hover:text-cyber-cyan"
                  >
                    ‹
                  </button>
                  <span>{pinnedIdx + 1}/{pinned.length}</span>
                  <button
                    onClick={() => setPinnedIdx((i) => (i + 1) % pinned.length)}
                    className="rounded-sm px-1 hover:text-cyber-cyan"
                  >
                    ›
                  </button>
                </div>
              )}
              <button
                onClick={() => handlePin(currentPinned)}
                className="text-[10px] uppercase tracking-widest text-cyber-dim hover:neon-text-mag"
              >
                unpin
              </button>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            {grouped.map((g) => (
              <div key={g.day} className="mb-4">
                <div className="mb-3 flex items-center gap-2">
                  <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent to-cyber-cyan/40" />
                  <span className="rounded-sm border border-cyber-cyan/40 bg-cyber-panel px-3 py-1 text-[9px] uppercase tracking-[0.3em] neon-text">
                    {g.day}
                  </span>
                  <div className="h-[1px] flex-1 bg-gradient-to-l from-transparent to-cyber-cyan/40" />
                </div>
                <div className="space-y-1">
                  {g.items.map((m, idx) => {
                    const prev = g.items[idx - 1];
                    const showAvatar = !prev || prev.author_id !== m.author_id || prev.message_type === "system";
                    const isLast = idx === g.items.length - 1 || g.items[idx + 1].author_id !== m.author_id;
                    const isHighlighted = highlightId === m.id;
                    return (
                      <div
                        key={m.id}
                        className={isHighlighted ? "ring-2 ring-cyber-yellow animate-pulse" : ""}
                      >
                        <MessageBubble
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
                          onReact={handleReact}
                          onPin={handlePin}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Reply/edit bar */}
          {(replyTo || editing) && (
            <div className="flex items-center gap-2 border-t border-cyber-cyan/20 bg-cyber-panel/80 px-4 py-2 backdrop-blur">
              <div className="flex-1 truncate border-l-2 border-cyber-cyan pl-2 text-sm">
                <div className="text-[10px] uppercase tracking-widest neon-text">
                  {editing ? "◂ editing" : `↳ reply ${replyTo?.author_display || replyTo?.author_username}`}
                </div>
                <div className="truncate text-xs text-cyber-dim">
                  {editing ? editing.text : replyTo?.text}
                </div>
              </div>
              <button
                onClick={() => { setReplyTo(null); setEditing(null); setText(""); }}
                className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15"
              >
                ✕
              </button>
            </div>
          )}

          {/* Input */}
          <div className="relative border-t border-cyber-cyan/20 bg-cyber-panel/60 p-3 backdrop-blur">
            {typingUsers.size > 0 && (
              <div className="absolute -top-5 left-4 flex items-center gap-1 text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
                <span className="typing-dot inline-block h-1.5 w-1.5 rounded-full bg-cyber-cyan" />
                <span className="ml-1">{Array.from(typingUsers).join(", ")}</span>
              </div>
            )}
            <div className="flex items-end gap-1">
              <FileUpload asType="image" accept="image/*" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <FileUpload asType="file" onUploaded={(a, t) => sendAttachment(a.id, t)} />
              <button
                onClick={() => { setStickerOpen(!stickerOpen); setEmojiOpen(false); }}
                className="rounded-sm p-2 text-lg text-cyber-cyan transition hover:bg-cyber-cyan/10"
              >
                ◈
              </button>
              <button
                onClick={() => { setEmojiOpen(!emojiOpen); setStickerOpen(false); }}
                className="rounded-sm p-2 text-lg text-cyber-cyan transition hover:bg-cyber-cyan/10"
              >
                ☺
              </button>
              <textarea
                value={text}
                onChange={(e) => onTextChange(e.target.value)}
                onKeyDown={onKeyDown}
                rows={1}
                placeholder="TRANSMIT MESSAGE..."
                className="cyber-input max-h-32 flex-1 resize-none rounded-sm px-3 py-2 text-sm"
              />
              <VoiceRecorder onUploaded={(a) => sendAttachment(a.id, "voice")} />
              <button
                onClick={doSend}
                disabled={!text.trim()}
                className="cyber-btn rounded-sm px-4 py-2 text-xs"
              >
                ▸
              </button>
            </div>

            {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}
            {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}
          </div>

          {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}
          {showSearch && (
            <SearchModal
              chatId={chat.id}
              onClose={() => setShowSearch(false)}
              onJumpTo={jumpTo}
            />
          )}
        </main>
      );
    }
''')

# ============================================================== SETTINGS PANEL — добавить выбор темы
T["frontend/src/SettingsPanel.tsx"] = _t('''
    import { useState } from "react";
    import { api } from "./api";
    import { THEMES } from "./themes";
    import type { Chat, ThemeName, User } from "./types";

    export default function SettingsPanel({
      currentUser, chats, onClose, onChatsChanged, onSelectChat, theme, setTheme
    }: {
      currentUser: User;
      chats: Chat[];
      onClose: () => void;
      onChatsChanged: (c: Chat[]) => void;
      onSelectChat: (id: number) => void;
      theme: ThemeName;
      setTheme: (t: ThemeName) => void;
    }) {
      const [tab, setTab] = useState<"search" | "group" | "theme">("search");
      const [query, setQuery] = useState("");
      const [results, setResults] = useState<User[]>([]);
      const [error, setError] = useState("");

      const [groupTitle, setGroupTitle] = useState("");
      const [groupMembers, setGroupMembers] = useState("");
      const [groupDesc, setGroupDesc] = useState("");

      const searchUsers = async (q: string) => {
        setQuery(q);
        if (!q.trim()) { setResults([]); return; }
        const { data } = await api.get<User[]>("/users", { params: { q, limit: 20 } });
        setResults(data);
      };

      const startDirect = async (u: User) => {
        setError("");
        try {
          const { data } = await api.post<Chat>("/chats", { is_group: false, member_usernames: [u.username] });
          const all = await api.get<Chat[]>("/chats");
          onChatsChanged(all.data);
          onSelectChat(data.id);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const createGroup = async () => {
        setError("");
        if (!groupTitle.trim()) { setError("Нужно название"); return; }
        try {
          const names = groupMembers.split(",").map((s) => s.trim()).filter(Boolean);
          const { data } = await api.post<Chat>("/chats", {
            title: groupTitle,
            description: groupDesc || null,
            is_group: true,
            member_usernames: names,
          });
          const all = await api.get<Chat[]>("/chats");
          onChatsChanged(all.data);
          onSelectChat(data.id);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const input = "cyber-input w-full rounded-sm px-3 py-2 text-sm";

      const tabCls = (active: boolean) =>
        "flex-1 py-3 text-[10px] font-bold uppercase tracking-widest transition " +
        (active
          ? "text-cyber-cyan border-b-2 border-cyber-cyan bg-cyber-cyan/5"
          : "text-cyber-dim hover:text-cyber-cyan hover:bg-cyber-cyan/5");

      return (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4 backdrop-blur" onClick={onClose}>
          <div
            className="corner-frame animate-materialize flex h-[560px] w-[620px] flex-col rounded-sm border border-cyber-cyan/50 bg-cyber-panel shadow-neon-cyan"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-cyber-cyan/20 p-4">
              <h2 className="text-sm font-bold uppercase tracking-widest neon-text">
                ⚙ settings
              </h2>
              <button onClick={onClose} className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15">
                ✕
              </button>
            </div>

            <div className="flex border-b border-cyber-cyan/20">
              <button onClick={() => setTab("search")} className={tabCls(tab === "search")}>◉ search</button>
              <button onClick={() => setTab("group")} className={tabCls(tab === "group")}>◉ group</button>
              <button onClick={() => setTab("theme")} className={tabCls(tab === "theme")}>◉ theme</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tab === "search" && (
                <>
                  <input
                    className={input}
                    placeholder="SEARCH OPERATOR"
                    value={query}
                    onChange={(e) => searchUsers(e.target.value)}
                    autoFocus
                  />
                  {results.length > 0 && (
                    <div className="mt-3 space-y-1">
                      {results.map((u) => (
                        <button
                          key={u.id}
                          onClick={() => startDirect(u)}
                          className="flex w-full items-center gap-3 rounded-sm border border-cyber-cyan/20 p-2 text-left transition hover:border-cyber-cyan hover:bg-cyber-cyan/5"
                        >
                          <div>
                            <div className="text-sm font-bold text-cyber-text">
                              {u.display_name || u.username}
                            </div>
                            <div className="text-[10px] uppercase tracking-widest text-cyber-dim">
                              @{u.username}
                            </div>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </>
              )}

              {tab === "group" && (
                <div className="space-y-3">
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // title
                    </label>
                    <input
                      className={input}
                      placeholder="e.g. NIGHT CITY"
                      value={groupTitle}
                      onChange={(e) => setGroupTitle(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // description
                    </label>
                    <input
                      className={input}
                      placeholder="optional"
                      value={groupDesc}
                      onChange={(e) => setGroupDesc(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // members (comma separated)
                    </label>
                    <input
                      className={input}
                      placeholder="alice, bob, carol"
                      value={groupMembers}
                      onChange={(e) => setGroupMembers(e.target.value)}
                    />
                  </div>
                  <button
                    onClick={createGroup}
                    className="cyber-btn w-full rounded-sm py-2 text-xs"
                  >
                    [ CREATE GROUP ]
                  </button>
                </div>
              )}

              {tab === "theme" && (
                <div className="space-y-3">
                  <div className="text-[10px] uppercase tracking-widest text-cyber-dim mb-2">
                    // choose terminal skin
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {THEMES.map((t) => (
                      <button
                        key={t.name}
                        onClick={() => setTheme(t.name)}
                        className={
                          "rounded-sm border p-3 text-left transition " +
                          (theme === t.name
                            ? "border-cyber-cyan bg-cyber-cyan/15 shadow-neon-cyan"
                            : "border-cyber-cyan/25 hover:border-cyber-cyan/60")
                        }
                      >
                        <div className="text-xs font-bold uppercase tracking-widest" style={{ color: t.vars["--neon-cyan"] }}>
                          {t.label}
                        </div>
                        <div className="mt-2 flex gap-1">
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-cyan"] }} />
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-magenta"] }} />
                          <div className="h-3 w-3 rounded-sm" style={{ background: t.vars["--neon-yellow"] }} />
                          <div className="h-3 w-3 rounded-sm border border-white/20" style={{ background: t.vars["--bg-deep"] }} />
                        </div>
                      </button>
                    ))}
                  </div>
                  <div className="mt-6 border-t border-cyber-cyan/20 pt-3 text-[10px] uppercase tracking-widest text-cyber-dim">
                    <div>channels: {chats.length}</div>
                    <div>operator: @{currentUser.username}</div>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-3 rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}
            </div>
          </div>
        </div>
    );
''')

# ============================================================== APP — интеграция
T["frontend/src/App.tsx"] = _t('''
    import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
    import CyberBackground from "./CyberBackground";
    import CommandPalette, { type Command } from "./CommandPalette";
    import { api } from "./api";
    import { useWebSocket } from "./ws";
    import { useWebRTC } from "./useWebRTC";
    import { applyTheme } from "./themes";
    import { ensureNotificationPermission, showNotification, playPing } from "./notifications";
    import type { CallInfo, Chat, ThemeName, User } from "./types";

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
      const [showCommandPalette, setShowCommandPalette] = useState(false);
      const [theme, setTheme] = useState<ThemeName>(
        (localStorage.getItem("theme") as ThemeName) || "cyber"
      );
      const [mode, setMode] = useState<Mode>("chats");
      const [profileUserId, setProfileUserId] = useState<number | null>(null);
      const [incomingCall, setIncomingCall] = useState<CallInfo | null>(null);
      const [callDuration, setCallDuration] = useState(0);
      const offerRef = useRef<RTCSessionDescriptionInit | null>(null);

      // apply theme on change
      useEffect(() => {
        applyTheme(theme);
        localStorage.setItem("theme", theme);
      }, [theme]);

      // request notifications permission on login
      useEffect(() => {
        if (user) ensureNotificationPermission();
      }, [user]);

      // Ctrl+K палитра
      useEffect(() => {
        const h = (e: KeyboardEvent) => {
          if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
            e.preventDefault();
            setShowCommandPalette((v) => !v);
          }
          if (e.key === "Escape") setShowCommandPalette(false);
        };
        document.addEventListener("keydown", h);
        return () => document.removeEventListener("keydown", h);
      }, []);

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
          // notification
          if (user && d.author_id !== user.id && d.message_type !== "system") {
            playPing();
            showNotification(
              d.author_display || d.author_username,
              d.message_type === "text" ? (d.text || "").slice(0, 120) :
              d.message_type === "image" ? "▣ Image" :
              d.message_type === "voice" ? "◍ Voice" :
              d.message_type === "file" ? "▤ File" : "◈ Sticker",
              `chat-${d.chat_id}`
            );
          }
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
          if (user) {
            playPing();
            showNotification(
              "◈ INCOMING CALL",
              `${d.caller.display_name || d.caller.username} · ${d.kind === "video" ? "VIDEO" : "AUDIO"}`,
              "call"
            );
          }
        }
      }, [activeChatId, user?.id, user?.username, user?.display_name, user?.avatar_color]);

      const { send, subscribe } = useWebSocket(onWs);
      const rtc = useWebRTC(send, subscribe);

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
          offerRef.current = null;
          setIncomingCall(null);

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

      // Command palette commands
      const commands: Command[] = useMemo(() => {
        const list: Command[] = [
          { id: "feed", label: "Open feed", icon: "📰", action: () => setMode("feed") },
          { id: "profile", label: "Open my profile", icon: "👤", action: () => { setProfileUserId(user?.id ?? null); setMode("profile"); } },
          { id: "settings", label: "Open settings", icon: "⚙", action: () => setShowSettings(true) },
          { id: "theme-cyber", label: "Theme: Cyber", icon: "◈", action: () => setTheme("cyber") },
          { id: "theme-matrix", label: "Theme: Matrix", icon: "▶", action: () => setTheme("matrix") },
          { id: "theme-sunset", label: "Theme: Sunset", icon: "☀", action: () => setTheme("sunset") },
          { id: "theme-amber", label: "Theme: Amber", icon: "◆", action: () => setTheme("amber") },
          { id: "logout", label: "Logout", icon: "✕", action: logout },
        ];
        chats.slice(0, 20).forEach((c) => {
          list.unshift({
            id: `chat-${c.id}`,
            label: c.peer ? (c.peer.display_name || c.peer.username) : (c.title || `Chat ${c.id}`),
            hint: `> open channel #${c.id}`,
            icon: "💬",
            action: () => { setActiveChatId(c.id); setMode("chats"); },
          });
        });
        return list;
      }, [chats, user?.id]);

      if (loading) {
        return (
          <>
            <CyberBackground />
            <div className="relative z-10 flex h-screen items-center justify-center">
              <div className="text-center">
                <div className="mb-4 text-5xl flicker neon-text">◈</div>
                <div className="text-xs uppercase tracking-[0.4em] neon-text cursor">
                  establishing link
                </div>
              </div>
            </div>
          </>
        );
      }

      if (!user) {
        return (
          <>
            <CyberBackground />
            <Login onLogin={loadMe} />
          </>
        );
      }

      const activeChat = chats.find((c) => c.id === activeChatId) || null;
      const inCall = rtc.session !== null && (rtc.status === "connecting" || rtc.status === "active" || rtc.status === "ringing");

      return (
        <>
          <CyberBackground />
          <div className="relative z-10 flex h-screen">
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
                <div className="flex flex-1 flex-col items-center justify-center">
                  <div className="text-7xl flicker neon-text mb-6">◈</div>
                  <div className="text-sm uppercase tracking-[0.4em] neon-text">
                    select channel
                  </div>
                  <div className="mt-2 text-[10px] uppercase tracking-widest text-cyber-dim">
                    // no active link
                  </div>
                  <button
                    onClick={() => setShowSettings(true)}
                    className="cyber-btn mt-6 rounded-sm px-6 py-2 text-xs"
                  >
                    [ start transmission ]
                  </button>
                  <div className="mt-4 text-[10px] uppercase tracking-widest text-cyber-dim">
                    press <span className="neon-text">ctrl+k</span> for commands
                  </div>
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

            {showCommandPalette && (
              <CommandPalette
                commands={commands}
                onClose={() => setShowCommandPalette(false)}
              />
            )}
          </div>
        </>
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

    print("\nСпринт 8: UX-полировка")
    print(f"Проект:   {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())