#!/usr/bin/env python3
"""sprint1.py — Telegram-style UI + core messaging features."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== BACKEND
T["backend/alembic/versions/0002_sprint1.py"] = _t('''
    """sprint 1: avatar_color, bio, last_seen, message edit/reply, read tracking

    Revision ID: 0002
    Revises: 0001
    Create Date: 2025-02-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0002"
    down_revision: Union[str, None] = "0001"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.add_column("users", sa.Column("avatar_color", sa.String(20), nullable=True))
        op.add_column("users", sa.Column("bio", sa.String(500), nullable=True))
        op.add_column(
            "users", sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True)
        )

        op.add_column(
            "messages", sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True)
        )
        op.add_column(
            "messages",
            sa.Column(
                "reply_to_id",
                sa.Integer(),
                sa.ForeignKey("messages.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.add_column(
            "messages",
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

        op.add_column(
            "chat_members",
            sa.Column("last_read_message_id", sa.Integer(), nullable=True),
        )


    def downgrade() -> None:
        op.drop_column("chat_members", "last_read_message_id")
        op.drop_column("messages", "is_deleted")
        op.drop_column("messages", "reply_to_id")
        op.drop_column("messages", "edited_at")
        op.drop_column("users", "last_seen")
        op.drop_column("users", "bio")
        op.drop_column("users", "avatar_color")
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
        text: Mapped[str] = mapped_column(Text)
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


    class ChatRead(BaseModel):
        id: int
        title: str | None
        is_group: bool
        created_at: datetime
        last_message: "MessageRead | None" = None
        unread_count: int = 0
        peer: UserRead | None = None


    class MessageCreate(BaseModel):
        text: str = Field(min_length=1, max_length=4000)
        reply_to_id: int | None = None


    class MessageEdit(BaseModel):
        text: str = Field(min_length=1, max_length=4000)


    class MessageRead(BaseModel):
        id: int
        chat_id: int
        author_id: int
        author_username: str
        author_display: str | None = None
        author_avatar_color: str | None = None
        text: str
        reply_to_id: int | None = None
        reply_preview: str | None = None
        reply_author: str | None = None
        edited_at: datetime | None = None
        is_deleted: bool = False
        created_at: datetime


    ChatRead.model_rebuild()
''')

T["backend/app/websocket_manager.py"] = _t('''
    from __future__ import annotations

    from collections import defaultdict
    from datetime import datetime, timezone

    from fastapi import WebSocket


    class ConnectionManager:
        """Отслеживает соединения, подписки на чаты, typing и presence."""

        def __init__(self) -> None:
            self._user_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._chat_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._ws_user: dict[WebSocket, int] = {}
            self._typing: dict[tuple[int, int], float] = {}
            self._last_seen: dict[int, datetime] = {}

        async def connect(self, user_id: int, ws: WebSocket) -> None:
            await ws.accept()
            self._user_conns[user_id].add(ws)
            self._ws_user[ws] = user_id

        async def disconnect(self, ws: WebSocket) -> int | None:
            user_id = self._ws_user.pop(ws, None)
            if user_id is None:
                return None
            self._user_conns.get(user_id, set()).discard(ws)
            if not self._user_conns.get(user_id):
                self._user_conns.pop(user_id, None)
                self._last_seen[user_id] = datetime.now(timezone.utc)
            for conns in self._chat_conns.values():
                conns.discard(ws)
            return user_id

        def is_online(self, user_id: int) -> bool:
            return bool(self._user_conns.get(user_id))

        def get_last_seen(self, user_id: int) -> datetime | None:
            return self._last_seen.get(user_id)

        def online_user_ids(self) -> list[int]:
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

        async def broadcast_all(self, message: dict) -> None:
            for user_id in list(self._user_conns.keys()):
                await self.send_to_user(user_id, message)

        async def close_all(self) -> None:
            for user_conns in list(self._user_conns.values()):
                for ws in list(user_conns):
                    try:
                        await ws.close()
                    finally:
                        await self.disconnect(ws)


    manager = ConnectionManager()
''')

T["backend/app/routers/__init__.py"] = ""

T["backend/app/routers/auth.py"] = _t('''
    import random

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import User
    from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
    from app.security import create_access_token, hash_password, verify_password


    router = APIRouter()

    AVATAR_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
        "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#f43f5e",
    ]


    @router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
    async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_session)):
        existing = await db.execute(select(User).where(User.username == payload.username))
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "username taken")
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")

        user = User(
            username=payload.username,
            email=payload.email,
            display_name=payload.display_name,
            hashed_password=hash_password(payload.password),
            avatar_color=random.choice(AVATAR_COLORS),
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return UserRead.model_validate(user)


    @router.post("/login", response_model=TokenResponse)
    async def login(payload: LoginRequest, db: AsyncSession = Depends(get_session)):
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
        return TokenResponse(access_token=create_access_token(user.id))


    @router.get("/me", response_model=UserRead)
    async def me(current: CurrentUser):
        return UserRead.model_validate(current)
''')

T["backend/app/routers/users.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import User
    from app.schemas import UserRead, UserUpdate
    from app.websocket_manager import manager


    router = APIRouter()


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
        return [UserRead.model_validate(u) for u in result.scalars().all()]


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
        return UserRead.model_validate(current)


    @router.get("/{user_id}", response_model=UserRead)
    async def get_user(user_id: int, db: AsyncSession = Depends(get_session)):
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
        return UserRead.model_validate(user)


    @router.get("/{user_id}/presence")
    async def user_presence(user_id: int):
        return {
            "user_id": user_id,
            "online": manager.is_online(user_id),
            "last_seen": manager.get_last_seen(user_id).isoformat()
            if manager.get_last_seen(user_id)
            else None,
        }
''')

T["backend/app/routers/chats.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, Message, User
    from app.schemas import ChatCreate, ChatRead, MessageRead, UserRead


    router = APIRouter()


    def _msg_to_read(m: Message, author: User) -> MessageRead:
        return MessageRead(
            id=m.id,
            chat_id=m.chat_id,
            author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
            text="Сообщение удалено" if m.is_deleted else m.text,
            reply_to_id=m.reply_to_id,
            edited_at=m.edited_at,
            is_deleted=m.is_deleted,
            created_at=m.created_at,
        )


    async def build_chat_read(
        db: AsyncSession, chat: Chat, current_id: int, membership: ChatMember
    ) -> ChatRead:
        # last message
        last_stmt = (
            select(Message, User)
            .join(User, User.id == Message.author_id)
            .where(Message.chat_id == chat.id)
            .order_by(Message.id.desc())
            .limit(1)
        )
        last = (await db.execute(last_stmt)).first()
        last_msg = _msg_to_read(last[0], last[1]) if last else None

        # unread count
        unread = 0
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

        # peer for direct chats
        peer: UserRead | None = None
        if not chat.is_group:
            peer_stmt = (
                select(User)
                .join(ChatMember, ChatMember.user_id == User.id)
                .where(ChatMember.chat_id == chat.id, User.id != current_id)
                .limit(1)
            )
            peer = (await db.execute(peer_stmt)).scalar_one_or_none()
            peer = UserRead.model_validate(peer) if peer else None

        return ChatRead(
            id=chat.id,
            title=chat.title,
            is_group=chat.is_group,
            created_at=chat.created_at,
            last_message=last_msg,
            unread_count=unread,
            peer=peer,
        )


    @router.get("", response_model=list[ChatRead])
    async def my_chats(
        current: CurrentUser, db: AsyncSession = Depends(get_session)
    ) -> list[ChatRead]:
        stmt = (
            select(Chat, ChatMember)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current.id)
            .order_by(Chat.created_at.desc())
        )
        rows = (await db.execute(stmt)).all()
        out: list[ChatRead] = []
        for chat, membership in rows:
            out.append(await build_chat_read(db, chat, current.id, membership))

        # sort by last message time (or chat creation if none)
        def key(c: ChatRead):
            ts = c.last_message.created_at if c.last_message else c.created_at
            return ts

        out.sort(key=key, reverse=True)
        return out


    @router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
    async def create_chat(
        payload: ChatCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ) -> ChatRead:
        member_ids = {current.id}
        if payload.member_usernames:
            result = await db.execute(
                select(User).where(User.username.in_(payload.member_usernames))
            )
            for u in result.scalars().all():
                member_ids.add(u.id)

        # if direct chat already exists — return it
        if not payload.is_group and len(member_ids) == 2:
            other = next(iter(member_ids - {current.id}))
            existing = await db.execute(
                select(Chat)
                .join(ChatMember, ChatMember.chat_id == Chat.id)
                .where(Chat.is_group == False)  # noqa: E712
                .group_by(Chat.id)
                .having(func.count(ChatMember.user_id) == 2)
                .having(
                    Chat.id.in_(
                        select(ChatMember.chat_id).where(ChatMember.user_id == other)
                    )
                )
                .having(
                    Chat.id.in_(
                        select(ChatMember.chat_id).where(ChatMember.user_id == current.id)
                    )
                )
            )
            existing_chat = existing.scalars().first()
            if existing_chat:
                membership = (
                    await db.execute(
                        select(ChatMember).where(
                            ChatMember.chat_id == existing_chat.id,
                            ChatMember.user_id == current.id,
                        )
                    )
                ).scalar_one()
                return await build_chat_read(db, existing_chat, current.id, membership)

        chat = Chat(title=payload.title, is_group=payload.is_group)
        db.add(chat)
        await db.flush()

        for uid in member_ids:
            db.add(
                ChatMember(
                    chat_id=chat.id,
                    user_id=uid,
                    role="owner" if uid == current.id else "member",
                )
            )
        await db.flush()
        await db.refresh(chat)

        membership = (
            await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat.id, ChatMember.user_id == current.id
                )
            )
        ).scalar_one()
        return await build_chat_read(db, chat, current.id, membership)


    @router.get("/{chat_id}", response_model=ChatRead)
    async def get_chat(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ) -> ChatRead:
        row = (
            await db.execute(
                select(Chat, ChatMember)
                .join(ChatMember, ChatMember.chat_id == Chat.id)
                .where(Chat.id == chat_id, ChatMember.user_id == current.id)
            )
        ).first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
        chat, membership = row
        return await build_chat_read(db, chat, current.id, membership)


    @router.post("/{chat_id}/read", status_code=status.HTTP_204_NO_CONTENT)
    async def mark_read(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        membership = (
            await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat_id, ChatMember.user_id == current.id
                )
            )
        ).scalar_one_or_none()
        if membership is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        last = (
            await db.execute(
                select(Message.id)
                .where(Message.chat_id == chat_id)
                .order_by(Message.id.desc())
                .limit(1)
            )
        ).scalar()
        if last is not None:
            membership.last_read_message_id = last
            await db.flush()
''')

T["backend/app/routers/messages.py"] = _t('''
    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import ChatMember, Message, User
    from app.schemas import MessageCreate, MessageEdit, MessageRead


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
        author = (
            await db.execute(select(User).where(User.id == m.author_id))
        ).scalar_one()
        reply_preview = None
        reply_author = None
        if m.reply_to_id:
            r = (
                await db.execute(select(Message).where(Message.id == m.reply_to_id))
            ).scalar_one_or_none()
            if r:
                reply_preview = "Сообщение удалено" if r.is_deleted else r.text[:120]
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
        msg = Message(
            chat_id=chat_id,
            author_id=current.id,
            text=payload.text,
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

T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

    import json
    from datetime import datetime, timezone

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import ChatMember, Message, User
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

        # tell everyone this user is online
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
                    text = str(data.get("text", "")).strip()
                    reply_to_id = data.get("reply_to_id")
                    if not text:
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
                            reply_to_id=reply_to_id,
                        )
                        db.add(msg)
                        await db.flush()
                        await db.refresh(msg)

                        # mark as read for sender
                        member.last_read_message_id = msg.id
                        await db.commit()

                        author = await _author_payload(db, user_id)
                        reply_preview = None
                        reply_author = None
                        if reply_to_id:
                            r = (
                                await db.execute(
                                    select(Message).where(Message.id == reply_to_id)
                                )
                            ).scalar_one_or_none()
                            if r:
                                reply_preview = (
                                    "Сообщение удалено" if r.is_deleted else r.text[:120]
                                )
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
    from app.routers import auth, chats, messages, users, ws
    from app.websocket_manager import manager


    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
    app.include_router(ws.router, prefix=p, tags=["ws"])


    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}
''')

# ============================================================== FRONTEND
T["frontend/package.json"] = _t("""
    {
      "name": "messenger-frontend",
      "private": true,
      "version": "0.3.0",
      "type": "module",
      "scripts": {
        "dev": "vite",
        "build": "vite build",
        "preview": "vite preview"
      },
      "dependencies": {
        "axios": "^1.7.0",
        "react": "^18.3.1",
        "react-dom": "^18.3.1"
      },
      "devDependencies": {
        "@types/react": "^18.3.3",
        "@types/react-dom": "^18.3.0",
        "@vitejs/plugin-react": "^4.3.1",
        "autoprefixer": "^10.4.19",
        "postcss": "^8.4.40",
        "tailwindcss": "^3.4.7",
        "typescript": "^5.5.4",
        "vite": "^5.4.0"
      }
    }
""")

T["frontend/tailwind.config.js"] = _t("""
    /** @type {import('tailwindcss').Config} */
    export default {
      content: ["./index.html", "./src/**/*.{ts,tsx}"],
      darkMode: "class",
      theme: {
        extend: {
          colors: {
            brand: { 50: "#eef2ff", 500: "#6366f1", 600: "#4f46e5", 700: "#4338ca" },
            tg: {
              bg: "#17212b",
              panel: "#0e1621",
              side: "#17212b",
              bubble: "#182533",
              accent: "#5288c1",
            }
          }
        }
      },
      plugins: []
    };
""")

T["frontend/src/index.css"] = _t("""
    @tailwind base;
    @tailwind components;
    @tailwind utilities;

    html, body, #root { height: 100%; margin: 0; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(140, 140, 140, 0.4); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(140, 140, 140, 0.6); }

    @keyframes pop-in {
      from { opacity: 0; transform: translateY(6px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .animate-pop { animation: pop-in 0.15s ease-out; }

    @keyframes typing-dot {
      0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
      30% { transform: translateY(-3px); opacity: 1; }
    }
    .typing-dot { animation: typing-dot 1.2s infinite; }
    .typing-dot:nth-child(2) { animation-delay: 0.15s; }
    .typing-dot:nth-child(3) { animation-delay: 0.3s; }
""")

T["frontend/src/types.ts"] = _t("""
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

    export interface Message {
      id: number;
      chat_id: number;
      author_id: number;
      author_username: string;
      author_display: string | null;
      author_avatar_color: string | null;
      text: string;
      reply_to_id: number | null;
      reply_preview: string | null;
      reply_author: string | null;
      edited_at: string | null;
      is_deleted: boolean;
      created_at: string;
    }
""")

T["frontend/src/api.ts"] = _t("""
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
""")

T["frontend/src/ws.ts"] = _t("""
    import { useEffect, useRef, useState, useCallback } from "react";
    import { WS_BASE } from "./api";

    type Handler = (data: any) => void;

    export function useWebSocket(onMessage: Handler) {
      const wsRef = useRef<WebSocket | null>(null);
      const handlersRef = useRef<Set<Handler>>(new Set());
      const [connected, setConnected] = useState(false);
      const reconnectRef = useRef<number | null>(null);

      const onMessageRef = useRef(onMessage);
      useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

      const connect = useCallback(() => {
        const token = localStorage.getItem("access_token");
        if (!token) return;
        const ws = new WebSocket(`${WS_BASE}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          reconnectRef.current = window.setTimeout(connect, 2000);
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

      useEffect(() => {
        connect();
        return () => {
          if (reconnectRef.current) window.clearTimeout(reconnectRef.current);
          wsRef.current?.close();
        };
      }, [connect]);

      const send = useCallback((data: any) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify(data));
        }
      }, []);

      const subscribe = useCallback((h: Handler) => {
        handlersRef.current.add(h);
        return () => handlersRef.current.delete(h);
      }, []);

      return { send, subscribe, connected };
    }
""")

T["frontend/src/Avatar.tsx"] = _t("""
    import type { User } from "./types";

    export default function Avatar({
      user, size = 40, showOnline = false, online = false
    }: {
      user: Pick<User, "username" | "display_name" | "avatar_color">;
      size?: number;
      showOnline?: boolean;
      online?: boolean;
    }) {
      const name = user.display_name || user.username || "?";
      const initials = name
        .split(/\\s+/)
        .map((w) => w[0])
        .filter(Boolean)
        .slice(0, 2)
        .join("")
        .toUpperCase();
      const bg = user.avatar_color || "#4f46e5";

      return (
        <div className="relative shrink-0" style={{ width: size, height: size }}>
          <div
            className="flex h-full w-full items-center justify-center rounded-full font-semibold text-white"
            style={{ background: bg, fontSize: size * 0.4 }}
          >
            {initials}
          </div>
          {showOnline && (
            <span
              className={
                "absolute bottom-0 right-0 block rounded-full border-2 border-white dark:border-tg-side " +
                (online ? "bg-green-500" : "bg-slate-400")
              }
              style={{ width: size * 0.28, height: size * 0.28 }}
            />
          )}
        </div>
      );
    }
""")

T["frontend/src/EmojiPicker.tsx"] = _t("""
    import { useEffect, useRef } from "react";

    const EMOJI = [
      "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
      "🙂", "🙃", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚",
      "😋", "😛", "😝", "😜", "🤪", "🤨", "🧐", "🤓", "😎", "🥳",
      "😏", "😒", "😞", "😔", "😟", "😕", "🙁", "☹️", "😣", "😖",
      "😫", "😩", "🥺", "😢", "😭", "😤", "😠", "😡", "🤬", "🤯",
      "😳", "🥵", "🥶", "😱", "😨", "😰", "😥", "😓", "🤗", "🤔",
      "👍", "👎", "👌", "✌️", "🤞", "🤝", "🙏", "💪", "👋", "🤚",
      "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "💔", "❣️",
      "🔥", "⭐", "✨", "💫", "💥", "🎉", "🎊", "🎁", "🏆", "🥇",
    ];

    export default function EmojiPicker({
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
          className="animate-pop absolute bottom-16 right-2 z-30 grid max-h-64 w-80 grid-cols-8 gap-1 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-2xl dark:border-slate-700 dark:bg-tg-panel"
        >
          {EMOJI.map((e, i) => (
            <button
              key={i}
              onClick={() => onPick(e)}
              className="rounded p-1 text-2xl transition hover:bg-slate-100 dark:hover:bg-slate-700"
            >
              {e}
            </button>
          ))}
        </div>
      );
    }
""")

T["frontend/src/Login.tsx"] = _t("""
    import { useState } from "react";
    import { api } from "./api";

    export default function Login({ onLogin }: { onLogin: () => void }) {
      const [mode, setMode] = useState<"login" | "register">("login");
      const [username, setUsername] = useState("");
      const [password, setPassword] = useState("");
      const [email, setEmail] = useState("");
      const [displayName, setDisplayName] = useState("");
      const [error, setError] = useState("");
      const [busy, setBusy] = useState(false);

      const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setBusy(true);
        try {
          if (mode === "register") {
            await api.post("/auth/register", {
              username,
              email,
              password,
              display_name: displayName || null
            });
          }
          const { data } = await api.post("/auth/login", { username, password });
          localStorage.setItem("access_token", data.access_token);
          onLogin();
        } catch (err: any) {
          setError(err.response?.data?.detail || "Ошибка");
        } finally {
          setBusy(false);
        }
      };

      const input =
        "w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-900 " +
        "outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 " +
        "dark:border-slate-600 dark:bg-tg-bubble dark:text-slate-100";

      return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 dark:from-tg-bg dark:to-tg-panel">
          <form onSubmit={submit} className="w-96 space-y-3 rounded-2xl bg-white p-8 shadow-2xl dark:bg-tg-side">
            <div className="mb-4 text-center">
              <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-brand-600 text-3xl">
                💬
              </div>
              <h1 className="text-2xl font-bold text-slate-800 dark:text-white">
                {mode === "login" ? "Добро пожаловать" : "Регистрация"}
              </h1>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {mode === "login" ? "Войдите, чтобы продолжить" : "Создайте новый аккаунт"}
              </p>
            </div>

            <input
              className={input} placeholder="Логин" value={username}
              onChange={(e) => setUsername(e.target.value)} required
            />

            {mode === "register" && (
              <>
                <input
                  className={input} type="email" placeholder="Email"
                  value={email} onChange={(e) => setEmail(e.target.value)} required
                />
                <input
                  className={input} placeholder="Имя (необязательно)"
                  value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                />
              </>
            )}

            <input
              className={input} type="password" placeholder="Пароль"
              value={password} onChange={(e) => setPassword(e.target.value)} required
            />

            {error && (
              <div className="rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-300">
                {error}
              </div>
            )}

            <button
              type="submit" disabled={busy}
              className="w-full rounded-xl bg-brand-600 py-3 font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
            >
              {busy ? "..." : mode === "login" ? "Войти" : "Создать аккаунт"}
            </button>

            <button
              type="button"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
              className="w-full text-sm text-brand-600 hover:underline dark:text-brand-500"
            >
              {mode === "login" ? "Нет аккаунта? Зарегистрироваться" : "Уже есть аккаунт? Войти"}
            </button>
          </form>
        </div>
      );
    }
""")

T["frontend/src/ChatList.tsx"] = _t("""
    import { useMemo, useState } from "react";
    import Avatar from "./Avatar";
    import type { Chat, User } from "./types";

    function fmtTime(iso: string | null | undefined) {
      if (!iso) return "";
      const d = new Date(iso);
      const now = new Date();
      const sameDay = d.toDateString() === now.toDateString();
      if (sameDay) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const yest = new Date(now); yest.setDate(now.getDate() - 1);
      if (d.toDateString() === yest.toDateString()) return "Вчера";
      return d.toLocaleDateString([], { day: "2-digit", month: "2-digit" });
    }

    function chatTitle(c: Chat) {
      if (c.peer) return c.peer.display_name || c.peer.username;
      return c.title || `Чат #${c.id}`;
    }

    function chatSubtitle(c: Chat) {
      const lm = c.last_message;
      if (!lm) return "Нет сообщений";
      const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
      return who + (lm.text || "");
    }

    export default function ChatList({
      chats, activeId, onSelect, onlineUsers, currentUser, onOpenProfile, onOpenSettings
    }: {
      chats: Chat[];
      activeId: number | null;
      onSelect: (id: number) => void;
      onlineUsers: Set<number>;
      currentUser: User;
      onOpenProfile: () => void;
      onOpenSettings: () => void;
    }) {
      const [query, setQuery] = useState("");

      const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return chats;
        return chats.filter((c) => {
          const t = chatTitle(c).toLowerCase();
          const s = chatSubtitle(c).toLowerCase();
          return t.includes(q) || s.includes(q);
        });
      }, [chats, query]);

      return (
        <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-tg-side">
          <div className="flex items-center gap-2 p-3">
            <button
              onClick={onOpenProfile}
              className="transition hover:opacity-80"
              title="Профиль"
            >
              <Avatar user={currentUser} size={40} />
            </button>
            <div className="relative flex-1">
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Поиск"
                className="w-full rounded-full bg-slate-100 px-4 py-2 text-sm outline-none transition focus:ring-2 focus:ring-brand-500/30 dark:bg-tg-bubble dark:text-slate-100"
              />
            </div>
            <button
              onClick={onOpenSettings}
              title="Настройки"
              className="rounded-full p-2 text-slate-500 transition hover:bg-slate-100 dark:hover:bg-slate-700 dark:text-slate-300"
            >
              ⚙
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 && (
              <div className="p-6 text-center text-sm text-slate-400">
                {query ? "Ничего не найдено" : "Пока нет чатов"}
              </div>
            )}
            {filtered.map((c) => {
              const active = c.id === activeId;
              const peerOnline = c.peer ? onlineUsers.has(c.peer.id) : false;
              const avatarUser = c.peer || {
                username: c.title || "G",
                display_name: c.title || "Group",
                avatar_color: "#64748b",
              };
              return (
                <button
                  key={c.id}
                  onClick={() => onSelect(c.id)}
                  className={
                    "flex w-full items-center gap-3 border-b border-slate-100 px-3 py-2 text-left transition dark:border-slate-800 " +
                    (active
                      ? "bg-brand-500 text-white dark:bg-tg-accent/30"
                      : "hover:bg-slate-50 dark:hover:bg-slate-800/50")
                  }
                >
                  <Avatar
                    user={avatarUser as any}
                    size={48}
                    showOnline={!!c.peer}
                    online={peerOnline}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate font-medium text-slate-800 dark:text-slate-100">
                        {chatTitle(c)}
                      </span>
                      <span
                        className={
                          "shrink-0 text-[11px] " +
                          (active ? "text-white/80" : "text-slate-400 dark:text-slate-500")
                        }
                      >
                        {fmtTime(c.last_message?.created_at || c.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span
                        className={
                          "truncate text-sm " +
                          (active
                            ? "text-white/90"
                            : "text-slate-500 dark:text-slate-400")
                        }
                      >
                        {chatSubtitle(c)}
                      </span>
                      {c.unread_count > 0 && !active && (
                        <span className="shrink-0 rounded-full bg-brand-600 px-2 py-0.5 text-[11px] font-medium text-white">
                          {c.unread_count}
                        </span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>
      );
    }
""")

T["frontend/src/MessageBubble.tsx"] = _t("""
    import { useState } from "react";
    import Avatar from "./Avatar";
    import type { Message, User } from "./types";

    export default function MessageBubble({
      msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, readByPeer
    }: {
      msg: Message;
      mine: boolean;
      showAvatar: boolean;
      isLast: boolean;
      onReply: (m: Message) => void;
      onEdit: (m: Message) => void;
      onDelete: (m: Message) => void;
      readByPeer: boolean;
    }) {
      const [menuOpen, setMenuOpen] = useState(false);
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
                "animate-pop relative px-3 py-2 text-sm shadow-sm " +
                bubbleColor + " " + radius
              }
            >
              {msg.reply_to_id && !msg.is_deleted && (
                <div
                  className={
                    "mb-1 rounded border-l-2 px-2 py-1 text-xs " +
                    (mine
                      ? "border-white/60 bg-white/10"
                      : "border-brand-500 bg-slate-50 dark:bg-slate-800")
                  }
                >
                  <div className="font-medium opacity-90">
                    {msg.reply_author || "?"}
                  </div>
                  <div className="truncate opacity-75">
                    {msg.reply_preview || "..."}
                  </div>
                </div>
              )}

              <div className={msg.is_deleted ? "italic opacity-60" : "whitespace-pre-wrap break-words"}>
                {msg.text}
              </div>

              <div className="mt-0.5 flex items-center justify-end gap-1 text-[10px]">
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
                {mine && (
                  <>
                    <button
                      onClick={() => { onEdit(msg); setMenuOpen(false); }}
                      className="block w-full px-3 py-1.5 text-left hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                      Изменить
                    </button>
                    <button
                      onClick={() => { onDelete(msg); setMenuOpen(false); }}
                      className="block w-full px-3 py-1.5 text-left text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
                    >
                      Удалить
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }
""")

T["frontend/src/ChatWindow.tsx"] = _t("""
    import { useEffect, useMemo, useRef, useState } from "react";
    import Avatar from "./Avatar";
    import MessageBubble from "./MessageBubble";
    import EmojiPicker from "./EmojiPicker";
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
      const [typingUsers, setTypingUsers] = useState<Set<string>>(new Set());
      const [peerReadUpTo, setPeerReadUpTo] = useState<number>(0);
      const bottomRef = useRef<HTMLDivElement>(null);
      const typingTimeout = useRef<number | null>(null);
      const lastTypingSent = useRef<number>(0);

      // load messages + subscribe
      useEffect(() => {
        api.get<Message[]>(`/chats/${chat.id}/messages`).then((r) => setMessages(r.data));
        send({ type: "subscribe", chat_id: chat.id });
        api.post(`/chats/${chat.id}/read`).catch(() => {});
        return () => send({ type: "unsubscribe", chat_id: chat.id });
      }, [chat.id]);

      // auto scroll
      useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "auto" });
      }, [messages.length]);

      // mark read on new messages
      useEffect(() => {
        const last = messages[messages.length - 1];
        if (!last) return;
        if (last.author_id !== currentUser.id) {
          send({ type: "read", chat_id: chat.id, message_id: last.id });
        }
      }, [messages.length]);

      // ws handlers
      useEffect(() => {
        const off = subscribe((d) => {
          if (d.type === "message" && d.chat_id === chat.id) {
            setMessages((prev) => {
              if (prev.some((m) => m.id === d.id)) return prev;
              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, reply_to_id: d.reply_to_id,
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
          send({ type: "send", chat_id: chat.id, text: t, reply_to_id: replyTo?.id ?? null });
          setReplyTo(null);
        }
        setText("");
        send({ type: "typing", chat_id: chat.id, is_typing: false });
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
            <Avatar
              user={avatarUser as any}
              size={40}
              showOnline={!!chat.peer}
              online={peerOnline}
            />
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
                        onEdit={(mm) => { setEditing(mm); setReplyTo(null); setText(mm.text); }}
                        onDelete={(mm) => send({ type: "delete", message_id: mm.id })}
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
            <div className="flex items-end gap-2">
              <button
                onClick={() => setEmojiOpen(!emojiOpen)}
                className="rounded-full p-2 text-2xl leading-none transition hover:bg-slate-100 dark:hover:bg-slate-700"
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
                onPick={(e) => { setText((t) => t + e); setEmojiOpen(false); }}
                onClose={() => setEmojiOpen(false)}
              />
            )}
          </div>
        </main>
      );
    }
""")

T["frontend/src/ProfileModal.tsx"] = _t("""
    import { useState } from "react";
    import Avatar from "./Avatar";
    import { api } from "./api";
    import type { User } from "./types";

    export default function ProfileModal({
      user, onClose, onUpdate, onLogout
    }: {
      user: User;
      onClose: () => void;
      onUpdate: (u: User) => void;
      onLogout: () => void;
    }) {
      const [displayName, setDisplayName] = useState(user.display_name || "");
      const [bio, setBio] = useState(user.bio || "");
      const [saving, setSaving] = useState(false);

      const save = async () => {
        setSaving(true);
        try {
          const { data } = await api.patch<User>("/users/me", {
            display_name: displayName,
            bio,
          });
          onUpdate(data);
          onClose();
        } finally {
          setSaving(false);
        }
      };

      const input =
        "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none " +
        "focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-tg-bubble dark:text-slate-100";

      return (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={onClose}
        >
          <div
            className="animate-pop w-96 rounded-2xl bg-white p-6 shadow-2xl dark:bg-tg-side"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex justify-center">
              <Avatar user={user} size={96} />
            </div>
            <div className="mb-4 text-center">
              <div className="text-lg font-semibold text-slate-800 dark:text-white">
                {user.display_name || user.username}
              </div>
              <div className="text-sm text-slate-500">@{user.username}</div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="mb-1 block text-xs text-slate-500">Имя</label>
                <input
                  className={input}
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Ваше имя"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">О себе</label>
                <textarea
                  className={input + " resize-none"}
                  rows={3}
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  placeholder="Например: Люблю котиков"
                />
              </div>
            </div>

            <div className="mt-5 flex gap-2">
              <button
                onClick={save}
                disabled={saving}
                className="flex-1 rounded-xl bg-brand-600 py-2 font-medium text-white transition hover:bg-brand-700 disabled:opacity-50"
              >
                {saving ? "..." : "Сохранить"}
              </button>
              <button
                onClick={onLogout}
                className="rounded-xl border border-red-300 px-4 py-2 text-sm text-red-600 transition hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-900/30"
              >
                Выйти
              </button>
            </div>
          </div>
        </div>
      );
    }
""")

T["frontend/src/SettingsPanel.tsx"] = _t("""
    import { useState } from "react";
    import { api } from "./api";
    import type { Chat, User } from "./types";

    export default function SettingsPanel({
      currentUser, chats, onClose, onChatsChanged, onSelectChat, theme, setTheme
    }: {
      currentUser: User;
      chats: Chat[];
      onClose: () => void;
      onChatsChanged: (c: Chat[]) => void;
      onSelectChat: (id: number) => void;
      theme: "light" | "dark";
      setTheme: (t: "light" | "dark") => void;
    }) {
      const [tab, setTab] = useState<"new" | "search">("new");
      const [query, setQuery] = useState("");
      const [results, setResults] = useState<User[]>([]);
      const [error, setError] = useState("");

      const searchUsers = async (q: string) => {
        setQuery(q);
        if (!q.trim()) { setResults([]); return; }
        const { data } = await api.get<User[]>("/users", { params: { q, limit: 20 } });
        setResults(data);
      };

      const startDirect = async (u: User) => {
        setError("");
        try {
          const { data } = await api.post<Chat>("/chats", {
            is_group: false,
            member_usernames: [u.username],
          });
          const all = await api.get<Chat[]>("/chats");
          onChatsChanged(all.data);
          onSelectChat(data.id);
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const input =
        "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none " +
        "focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-tg-bubble dark:text-slate-100";

      return (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4"
          onClick={onClose}
        >
          <div
            className="animate-pop flex h-[500px] w-[600px] flex-col rounded-2xl bg-white shadow-2xl dark:bg-tg-side"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-white">
                Настройки
              </h2>
              <button
                onClick={onClose}
                className="rounded-full p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
              >
                ✕
              </button>
            </div>

            <div className="flex border-b border-slate-200 dark:border-slate-800">
              <button
                onClick={() => setTab("new")}
                className={
                  "flex-1 py-3 text-sm font-medium transition " +
                  (tab === "new"
                    ? "border-b-2 border-brand-500 text-brand-600"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400")
                }
              >
                Новый чат
              </button>
              <button
                onClick={() => setTab("search")}
                className={
                  "flex-1 py-3 text-sm font-medium transition " +
                  (tab === "search"
                    ? "border-b-2 border-brand-500 text-brand-600"
                    : "text-slate-500 hover:text-slate-700 dark:text-slate-400")
                }
              >
                Поиск пользователей
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tab === "search" && (
                <input
                  className={input}
                  placeholder="Введите имя пользователя"
                  value={query}
                  onChange={(e) => searchUsers(e.target.value)}
                  autoFocus
                />
              )}

              {tab === "new" && (
                <div className="space-y-3">
                  <p className="text-sm text-slate-500">
                    Все ваши чаты уже в списке слева.
                    Воспользуйтесь вкладкой «Поиск пользователей», чтобы найти человека и начать переписку.
                  </p>
                  <div className="rounded-xl border border-slate-200 p-3 dark:border-slate-700">
                    <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                      Оформление
                    </div>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => setTheme("light")}
                        className={
                          "rounded-lg border px-3 py-1.5 text-sm " +
                          (theme === "light"
                            ? "border-brand-500 bg-brand-50 text-brand-700"
                            : "border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-300")
                        }
                      >
                        ☀ Светлая
                      </button>
                      <button
                        onClick={() => setTheme("dark")}
                        className={
                          "rounded-lg border px-3 py-1.5 text-sm " +
                          (theme === "dark"
                            ? "border-brand-500 bg-brand-50 text-brand-700"
                            : "border-slate-300 text-slate-600 dark:border-slate-600 dark:text-slate-300")
                        }
                      >
                        🌙 Тёмная
                      </button>
                    </div>
                  </div>
                  <div className="text-xs text-slate-400">
                    Всего чатов: {chats.length}. Логин: @{currentUser.username}
                  </div>
                </div>
              )}

              {tab === "search" && results.length > 0 && (
                <div className="mt-3 space-y-1">
                  {results.map((u) => (
                    <button
                      key={u.id}
                      onClick={() => startDirect(u)}
                      className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                      <div className="text-sm font-medium text-slate-800 dark:text-slate-100">
                        {u.display_name || u.username}
                      </div>
                      <div className="text-xs text-slate-500">@{u.username}</div>
                    </button>
                  ))}
                </div>
              )}

              {error && (
                <div className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
      );
    }
""")

T["frontend/src/App.tsx"] = _t("""
    import { useCallback, useEffect, useState } from "react";
    import Login from "./Login";
    import ChatList from "./ChatList";
    import ChatWindow from "./ChatWindow";
    import ProfileModal from "./ProfileModal";
    import SettingsPanel from "./SettingsPanel";
    import { api } from "./api";
    import { useWebSocket } from "./ws";
    import type { Chat, User } from "./types";

    export default function App() {
      const [user, setUser] = useState<User | null>(null);
      const [chats, setChats] = useState<Chat[]>([]);
      const [activeChatId, setActiveChatId] = useState<number | null>(null);
      const [loading, setLoading] = useState(true);
      const [onlineUsers, setOnlineUsers] = useState<Set<number>>(new Set());
      const [showProfile, setShowProfile] = useState(false);
      const [showSettings, setShowSettings] = useState(false);
      const [theme, setTheme] = useState<"light" | "dark">(
        (localStorage.getItem("theme") as "light" | "dark") || "light"
      );

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
              ? { ...c, last_message: { ...c.last_message, ...d } as any,
                  unread_count: c.id === activeChatId || d.author_id === user?.id
                    ? c.unread_count
                    : c.unread_count + 1 }
              : c
          ));
        }
      }, [activeChatId, user?.id]);

      const { send, subscribe } = useWebSocket(onWs);

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
        if (activeChatId !== null) {
          api.post(`/chats/${activeChatId}/read`).then(() => refreshChats()).catch(() => {});
        }
      }, [activeChatId, refreshChats]);

      const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
        setChats([]);
        setActiveChatId(null);
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

      return (
        <div className="flex h-screen bg-slate-100 dark:bg-tg-bg">
          <ChatList
            chats={chats}
            activeId={activeChatId}
            onSelect={setActiveChatId}
            onlineUsers={onlineUsers}
            currentUser={user}
            onOpenProfile={() => setShowProfile(true)}
            onOpenSettings={() => setShowSettings(true)}
          />

          {activeChat ? (
            <ChatWindow
              key={activeChat.id}
              chat={activeChat}
              currentUser={user}
              send={send}
              subscribe={subscribe}
              onlineUsers={onlineUsers}
            />
          ) : (
            <div className="flex flex-1 flex-col items-center justify-center text-slate-400 dark:text-slate-500">
              <div className="mb-3 text-5xl">💬</div>
              <div className="text-lg">Выберите чат</div>
              <button
                onClick={() => setShowSettings(true)}
                className="mt-4 rounded-xl bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
              >
                Найти собеседника
              </button>
            </div>
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
              onSelectChat={setActiveChatId}
            />
          )}
        </div>
      );
    }
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

    print(f"\nОбновляю: {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down -v")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())