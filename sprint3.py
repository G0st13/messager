#!/usr/bin/env python3
"""sprint3.py - groups, roles, invites."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0004_sprint3.py"] = _t('''
    """sprint 3: group fields and invite tokens

    Revision ID: 0004
    Revises: 0003
    Create Date: 2025-04-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0004"
    down_revision: Union[str, None] = "0003"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.add_column("chats", sa.Column("avatar_color", sa.String(20), nullable=True))
        op.add_column("chats", sa.Column("description", sa.String(500), nullable=True))
        op.add_column("chats", sa.Column("invite_token", sa.String(64), nullable=True))
        op.create_unique_constraint("uq_chats_invite_token", "chats", ["invite_token"])


    def downgrade() -> None:
        op.drop_constraint("uq_chats_invite_token", "chats", type_="unique")
        op.drop_column("chats", "invite_token")
        op.drop_column("chats", "description")
        op.drop_column("chats", "avatar_color")
''')

# ============================================================== BACKEND
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
        description: Mapped[str | None] = mapped_column(String(500), default=None)
        avatar_color: Mapped[str | None] = mapped_column(String(20), default=None)
        invite_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
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
''')

# ---------- chats router (fully rewritten with groups)
T["backend/app/routers/chats.py"] = _t('''
    from __future__ import annotations

    import secrets

    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, Message, User
    from app.schemas import (
        AddMemberRequest,
        ChatCreate,
        ChatMemberRead,
        ChatRead,
        ChatUpdate,
        InviteRead,
        MessageRead,
        UserRead,
    )
    from app.websocket_manager import manager


    router = APIRouter()

    GROUP_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
        "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#f43f5e",
    ]


    def _msg_to_read(m: Message, author: User) -> MessageRead:
        return MessageRead(
            id=m.id,
            chat_id=m.chat_id,
            author_id=m.author_id,
            author_username=author.username,
            author_display=author.display_name,
            author_avatar_color=author.avatar_color,
            text="Сообщение удалено" if m.is_deleted else m.text,
            message_type=m.message_type or "text",
            reply_to_id=m.reply_to_id,
            edited_at=m.edited_at,
            is_deleted=m.is_deleted,
            created_at=m.created_at,
        )


    async def _system_message(db: AsyncSession, chat_id: int, actor_id: int, text: str) -> None:
        """Создаёт системное сообщение и рассылает его всем в чате."""
        msg = Message(
            chat_id=chat_id,
            author_id=actor_id,
            text=text,
            message_type="system",
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        actor = (await db.execute(select(User).where(User.id == actor_id))).scalar_one()
        payload = {
            "type": "message",
            "id": msg.id,
            "chat_id": chat_id,
            "text": text,
            "message_type": "system",
            "attachment": None,
            "reply_to_id": None,
            "reply_preview": None,
            "reply_author": None,
            "edited_at": None,
            "is_deleted": False,
            "created_at": msg.created_at.isoformat(),
            "author_id": actor.id,
            "author_username": actor.username,
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
            id=chat.id,
            title=chat.title,
            description=chat.description,
            avatar_color=chat.avatar_color,
            is_group=chat.is_group,
            created_at=chat.created_at,
            last_message=last_msg,
            unread_count=unread,
            peer=peer,
            member_count=member_count,
            my_role=membership.role,
        )


    async def _require_role(
        db: AsyncSession, chat_id: int, user_id: int, roles: tuple[str, ...] = ("owner", "admin")
    ) -> ChatMember:
        m = (
            await db.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if m is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")
        if m.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not enough rights")
        return m


    @router.get("", response_model=list[ChatRead])
    async def my_chats(current: CurrentUser, db: AsyncSession = Depends(get_session)):
        stmt = (
            select(Chat, ChatMember)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current.id)
        )
        rows = (await db.execute(stmt)).all()
        out = [await _build_chat_read(db, chat, current.id, m) for chat, m in rows]

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
            title=payload.title,
            is_group=payload.is_group,
            avatar_color=color,
            invite_token=secrets.token_urlsafe(16) if payload.is_group else None,
        )
        db.add(chat)
        await db.flush()

        for uid in member_ids:
            db.add(ChatMember(
                chat_id=chat.id,
                user_id=uid,
                role="owner" if uid == current.id else "member",
            ))
        await db.flush()
        await db.refresh(chat)

        membership = (await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat.id, ChatMember.user_id == current.id
            )
        )).scalar_one()
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
                user_id=u.id,
                username=u.username,
                display_name=u.display_name,
                avatar_color=u.avatar_color,
                role=m.role,
                joined_at=m.created_at,
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

        return ChatMemberRead(
            user_id=user.id,
            username=user.username,
            display_name=user.display_name,
            avatar_color=user.avatar_color,
            role="member",
            joined_at=m.created_at,
        )


    @router.delete("/{chat_id}/members/{user_id}", status_code=204)
    async def remove_member(
        chat_id: int,
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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


    @router.post("/{chat_id}/leave", status_code=204)
    async def leave_chat(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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


    @router.post("/{chat_id}/invite", response_model=InviteRead)
    async def create_invite(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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
        token: str,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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
        else:
            membership = existing

        return await _build_chat_read(db, chat, current.id, membership)


    @router.post("/{chat_id}/read", status_code=204)
    async def mark_read(
        chat_id: int,
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
        last = (await db.execute(
            select(Message.id)
            .where(Message.chat_id == chat_id)
            .order_by(Message.id.desc())
            .limit(1)
        )).scalar()
        if last is not None:
            m.last_read_message_id = last
            await db.flush()
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
''')

T["frontend/src/Avatar.tsx"] = _t('''
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
''')

T["frontend/src/ChatList.tsx"] = _t('''
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
      if (lm.message_type === "system") return lm.text || "";
      const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
      let body = lm.text || "";
      if (lm.message_type === "image") body = "📷 Фото";
      else if (lm.message_type === "voice") body = "🎤 Голосовое";
      else if (lm.message_type === "file") body = `📎 ${lm.attachment?.filename || "Файл"}`;
      else if (lm.message_type === "sticker") body = lm.text || "Стикер";
      return who + body;
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
            <button onClick={onOpenProfile} className="transition hover:opacity-80" title="Профиль">
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
                avatar_color: c.avatar_color || "#64748b",
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
                  <Avatar user={avatarUser as any} size={48} showOnline={!!c.peer} online={peerOnline} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate font-medium text-slate-800 dark:text-slate-100">
                        {chatTitle(c)}
                      </span>
                      <span className={
                        "shrink-0 text-[11px] " +
                        (active ? "text-white/80" : "text-slate-400 dark:text-slate-500")
                      }>
                        {fmtTime(c.last_message?.created_at || c.created_at)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between gap-2">
                      <span className={
                        "truncate text-sm " +
                        (active ? "text-white/90" : "text-slate-500 dark:text-slate-400")
                      }>
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
              <div className="w-8 shrink-0">
                {showAvatar && <Avatar user={author} size={32} />}
              </div>
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

T["frontend/src/GroupInfoPanel.tsx"] = _t('''
    import { useEffect, useState } from "react";
    import Avatar from "./Avatar";
    import { api } from "./api";
    import type { Chat, ChatMember, User } from "./types";

    export default function GroupInfoPanel({
      chat, currentUser, onClose, onChatUpdated, onLeft
    }: {
      chat: Chat;
      currentUser: User;
      onClose: () => void;
      onChatUpdated: (c: Chat) => void;
      onLeft: () => void;
    }) {
      const [members, setMembers] = useState<ChatMember[]>([]);
      const [title, setTitle] = useState(chat.title || "");
      const [description, setDescription] = useState(chat.description || "");
      const [adding, setAdding] = useState("");
      const [error, setError] = useState("");
      const [invite, setInvite] = useState<string | null>(null);

      const isGroup = chat.is_group;
      const isAdmin = chat.my_role === "owner" || chat.my_role === "admin";

      const reload = async () => {
        if (!isGroup) return;
        const { data } = await api.get<ChatMember[]>(`/chats/${chat.id}/members`);
        setMembers(data);
      };

      useEffect(() => { reload(); }, [chat.id]);

      const save = async () => {
        setError("");
        try {
          const { data } = await api.patch<Chat>(`/chats/${chat.id}`, {
            title: isGroup ? title : undefined,
            description: isGroup ? description : undefined,
          });
          onChatUpdated(data);
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const addMember = async () => {
        if (!adding.trim()) return;
        setError("");
        try {
          await api.post(`/chats/${chat.id}/members`, { username: adding.trim() });
          setAdding("");
          await reload();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Не удалось добавить");
        }
      };

      const removeMember = async (userId: number) => {
        if (!confirm("Удалить участника?")) return;
        try {
          await api.delete(`/chats/${chat.id}/members/${userId}`);
          await reload();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Не удалось удалить");
        }
      };

      const makeAdmin = async (userId: number, role: string) => {
        try {
          await api.patch(`/chats/${chat.id}/members/${userId}/role`, { role });
          await reload();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const leave = async () => {
        if (!confirm("Выйти из группы?")) return;
        try {
          await api.post(`/chats/${chat.id}/leave`);
          onLeft();
          onClose();
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const generateInvite = async () => {
        try {
          const { data } = await api.post<{ token: string; url: string }>(`/chats/${chat.id}/invite`);
          setInvite(data.url);
          await navigator.clipboard.writeText(data.url);
        } catch (e: any) {
          setError(e.response?.data?.detail || "Ошибка");
        }
      };

      const input = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-tg-bubble dark:text-slate-100";

      return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
          <div
            className="animate-pop flex h-[600px] w-[480px] flex-col rounded-2xl bg-white shadow-2xl dark:bg-tg-side"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-white">
                {isGroup ? "Информация о группе" : "Информация"}
              </h2>
              <button onClick={onClose} className="rounded-full p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700">✕</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="mb-4 flex flex-col items-center">
                <Avatar
                  user={chat.peer || { username: chat.title || "G", display_name: chat.title || "Group", avatar_color: chat.avatar_color }}
                  size={96}
                />
                {isGroup && isAdmin ? (
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Название группы"
                    className="mt-3 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-center text-lg font-semibold outline-none focus:border-brand-500 dark:border-slate-600 dark:bg-tg-bubble dark:text-white"
                  />
                ) : (
                  <div className="mt-3 text-lg font-semibold text-slate-800 dark:text-white">
                    {chat.peer ? (chat.peer.display_name || chat.peer.username) : (chat.title || `Чат #${chat.id}`)}
                  </div>
                )}
                {isGroup && (
                  <div className="mt-1 text-sm text-slate-500">
                    {chat.member_count} участников
                  </div>
                )}
              </div>

              {isGroup && (
                <div className="mb-4">
                  <label className="mb-1 block text-xs text-slate-500">Описание</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    disabled={!isAdmin}
                    rows={2}
                    placeholder="О чём группа?"
                    className={input + " resize-none disabled:opacity-60"}
                  />
                </div>
              )}

              {isGroup && isAdmin && (
                <button
                  onClick={save}
                  className="mb-4 w-full rounded-xl bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700"
                >
                  Сохранить
                </button>
              )}

              {isGroup && (
                <>
                  <div className="mb-2 flex items-center justify-between">
                    <div className="text-sm font-medium text-slate-700 dark:text-slate-200">
                      Участники
                    </div>
                  </div>

                  {isAdmin && (
                    <div className="mb-3 flex gap-2">
                      <input
                        value={adding}
                        onChange={(e) => setAdding(e.target.value)}
                        placeholder="username"
                        className={input}
                        onKeyDown={(e) => e.key === "Enter" && addMember()}
                      />
                      <button
                        onClick={addMember}
                        className="rounded-xl bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700"
                      >
                        Добавить
                      </button>
                    </div>
                  )}

                  <div className="space-y-1">
                    {members.map((m) => (
                      <div
                        key={m.user_id}
                        className="flex items-center gap-3 rounded-xl p-2 hover:bg-slate-50 dark:hover:bg-slate-800"
                      >
                        <Avatar
                          user={{ username: m.username, display_name: m.display_name, avatar_color: m.avatar_color }}
                          size={36}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
                            {m.display_name || m.username}
                            {m.user_id === currentUser.id && <span className="ml-1 text-xs text-slate-400">(вы)</span>}
                          </div>
                          <div className="text-xs text-slate-500">
                            @{m.username} · {m.role === "owner" ? "владелец" : m.role === "admin" ? "админ" : "участник"}
                          </div>
                        </div>
                        {isAdmin && m.user_id !== currentUser.id && m.role !== "owner" && (
                          <div className="flex gap-1">
                            {m.role === "member" && (
                              <button
                                onClick={() => makeAdmin(m.user_id, "admin")}
                                title="Сделать админом"
                                className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"
                              >
                                ↑
                              </button>
                            )}
                            {m.role === "admin" && (
                              <button
                                onClick={() => makeAdmin(m.user_id, "member")}
                                title="Снять админа"
                                className="rounded-lg px-2 py-1 text-xs text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700"
                              >
                                ↓
                              </button>
                            )}
                            <button
                              onClick={() => removeMember(m.user_id)}
                              title="Удалить"
                              className="rounded-lg px-2 py-1 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30"
                            >
                              ✕
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {isAdmin && (
                    <button
                      onClick={generateInvite}
                      className="mt-4 w-full rounded-xl border border-brand-500 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-600/10"
                    >
                      {invite ? "Ссылка скопирована" : "🔗 Создать пригласительную ссылку"}
                    </button>
                  )}
                  {invite && (
                    <div className="mt-2 truncate rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600 dark:bg-tg-bubble dark:text-slate-300">
                      {invite}
                    </div>
                  )}
                </>
              )}

              {error && (
                <div className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-300">
                  {error}
                </div>
              )}
            </div>

            {isGroup && (
              <div className="border-t border-slate-200 p-4 dark:border-slate-800">
                <button
                  onClick={leave}
                  className="w-full rounded-xl border border-red-300 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-800 dark:hover:bg-red-900/30"
                >
                  Выйти из группы
                </button>
              </div>
            )}
          </div>
        </div>
      );
    }
''')

T["frontend/src/SettingsPanel.tsx"] = _t('''
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
      const [tab, setTab] = useState<"new" | "search" | "group">("search");
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

      const input = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 dark:border-slate-600 dark:bg-tg-bubble dark:text-slate-100";

      const tabCls = (active: boolean) =>
        "flex-1 py-3 text-sm font-medium transition " +
        (active
          ? "border-b-2 border-brand-500 text-brand-600"
          : "text-slate-500 hover:text-slate-700 dark:text-slate-400");

      return (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
          <div
            className="animate-pop flex h-[540px] w-[600px] flex-col rounded-2xl bg-white shadow-2xl dark:bg-tg-side"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-200 p-4 dark:border-slate-800">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Настройки</h2>
              <button onClick={onClose} className="rounded-full p-1 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700">✕</button>
            </div>

            <div className="flex border-b border-slate-200 dark:border-slate-800">
              <button onClick={() => setTab("search")} className={tabCls(tab === "search")}>Поиск</button>
              <button onClick={() => setTab("group")} className={tabCls(tab === "group")}>Новая группа</button>
              <button onClick={() => setTab("new")} className={tabCls(tab === "new")}>Оформление</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tab === "search" && (
                <>
                  <input
                    className={input}
                    placeholder="Имя пользователя"
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
                          className="flex w-full items-center gap-3 rounded-xl p-2 text-left transition hover:bg-slate-100 dark:hover:bg-slate-800"
                        >
                          <div>
                            <div className="text-sm font-medium text-slate-800 dark:text-slate-100">
                              {u.display_name || u.username}
                            </div>
                            <div className="text-xs text-slate-500">@{u.username}</div>
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
                    <label className="mb-1 block text-xs text-slate-500">Название</label>
                    <input
                      className={input}
                      placeholder="Например: Друзья"
                      value={groupTitle}
                      onChange={(e) => setGroupTitle(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">Описание</label>
                    <input
                      className={input}
                      placeholder="Необязательно"
                      value={groupDesc}
                      onChange={(e) => setGroupDesc(e.target.value)}
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-xs text-slate-500">
                      Участники (через запятую)
                    </label>
                    <input
                      className={input}
                      placeholder="alice, bob, carol"
                      value={groupMembers}
                      onChange={(e) => setGroupMembers(e.target.value)}
                    />
                    <div className="mt-1 text-xs text-slate-400">
                      Введите usernames существующих пользователей
                    </div>
                  </div>
                  <button
                    onClick={createGroup}
                    className="w-full rounded-xl bg-brand-600 py-2 font-medium text-white hover:bg-brand-700"
                  >
                    Создать группу
                  </button>
                </div>
              )}

              {tab === "new" && (
                <div>
                  <div className="text-sm font-medium text-slate-700 dark:text-slate-200">Тема</div>
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
                  <div className="mt-6 text-xs text-slate-400">
                    Всего чатов: {chats.length}. Логин: @{currentUser.username}
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-900/30 dark:text-red-300">
                  {error}
                </div>
              )}
            </div>
          </div>
        </div>
    );
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
      chat, currentUser, send, subscribe, onlineUsers, onOpenInfo
    }: {
      chat: Chat;
      currentUser: User;
      send: (data: any) => void;
      subscribe: (h: (d: any) => void) => () => void;
      onlineUsers: Set<number>;
      onOpenInfo: () => void;
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
          <header
            className="flex cursor-pointer items-center gap-3 border-b border-slate-200 bg-white px-4 py-2 transition hover:bg-slate-50 dark:border-slate-800 dark:bg-tg-side dark:hover:bg-slate-800/50"
            onClick={onOpenInfo}
          >
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

T["frontend/src/App.tsx"] = _t('''
    import { useCallback, useEffect, useState } from "react";
    import Login from "./Login";
    import ChatList from "./ChatList";
    import ChatWindow from "./ChatWindow";
    import ProfileModal from "./ProfileModal";
    import SettingsPanel from "./SettingsPanel";
    import GroupInfoPanel from "./GroupInfoPanel";
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
      const [showGroupInfo, setShowGroupInfo] = useState(false);
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
              ? {
                  ...c,
                  last_message: { ...c.last_message, ...d } as any,
                  unread_count: c.id === activeChatId || d.author_id === user?.id || d.message_type === "system"
                    ? c.unread_count
                    : c.unread_count + 1,
                }
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

      // handle invite link ?invite=TOKEN
      useEffect(() => {
        if (!user) return;
        const params = new URLSearchParams(window.location.search);
        const invite = params.get("invite");
        if (!invite) return;
        api.post<Chat>(`/chats/join/${invite}`).then((r) => {
          refreshChats().then(() => setActiveChatId(r.data.id));
          window.history.replaceState({}, "", "/");
        }).catch(() => {
          window.history.replaceState({}, "", "/");
        });
      }, [user, refreshChats]);

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
              onOpenInfo={() => setShowGroupInfo(true)}
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

          {showGroupInfo && activeChat && (
            <GroupInfoPanel
              chat={activeChat}
              currentUser={user}
              onClose={() => setShowGroupInfo(false)}
              onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}
              onLeft={() => { setActiveChatId(null); refreshChats(); }}
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

    print("\nСпринт 3: группы, роли, приглашения")
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