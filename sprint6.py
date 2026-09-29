#!/usr/bin/env python3
"""sprint6.py - Redis caching layer."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

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

      redis:
        image: redis:7-alpine
        restart: unless-stopped
        ports:
          - "6379:6379"
        command: redis-server --save "" --appendonly no

      api:
        build:
          context: ../backend
        env_file:
          - ../backend/.env
        depends_on:
          db:
            condition: service_healthy
          redis:
            condition: service_started
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

T["backend/Dockerfile"] = _t("""
    FROM python:3.12-slim

    ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

    WORKDIR /app

    RUN pip install --upgrade pip && pip install \\
        "fastapi>=0.115" \\
        "uvicorn[standard]>=0.30" \\
        "pydantic>=2.8" \\
        "pydantic-settings>=2.4" \\
        "sqlalchemy[asyncio]>=2.0.32" \\
        "asyncpg>=0.29" \\
        "alembic>=1.13" \\
        "redis>=5.0" \\
        "python-jose[cryptography]>=3.3" \\
        "passlib[bcrypt]>=1.7.4" \\
        "bcrypt==4.0.1" \\
        "python-multipart>=0.0.9" \\
        "email-validator>=2.2"

    COPY . .

    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
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

    REDIS_URL=redis://redis:6379/0
    CACHE_TTL_CHATS=15
    CACHE_TTL_PROFILE=60

    UPLOAD_DIR=/app/uploads
    MAX_UPLOAD_SIZE_MB=50

    CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
""")

# ============================================================== CONFIG
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

        REDIS_URL: str = "redis://localhost:6379/0"
        CACHE_TTL_CHATS: int = 15
        CACHE_TTL_PROFILE: int = 60

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

# ============================================================== CACHE MODULE
T["backend/app/cache.py"] = _t('''
    from __future__ import annotations

    import json
    from typing import Any

    import redis.asyncio as aioredis
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import settings
    from app.models import ChatMember

    _client: aioredis.Redis | None = None


    def client() -> aioredis.Redis:
        global _client
        if _client is None:
            _client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
        return _client


    async def ping() -> bool:
        try:
            await client().ping()
            return True
        except Exception:
            return False


    async def close() -> None:
        global _client
        if _client is not None:
            try:
                await _client.aclose()
            except Exception:
                pass
            _client = None


    async def get(key: str) -> Any | None:
        try:
            raw = await client().get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None


    async def set(key: str, value: Any, ttl: int = 30) -> None:
        try:
            await client().setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception:
            pass


    async def delete(*keys: str) -> None:
        try:
            if keys:
                await client().delete(*keys)
        except Exception:
            pass


    async def invalidate_chat_list(db: AsyncSession, chat_id: int) -> None:
        """Сбрасывает кэш списка чатов у всех участников чата."""
        try:
            stmt = select(ChatMember.user_id).where(ChatMember.chat_id == chat_id)
            ids = (await db.execute(stmt)).scalars().all()
            keys = [f"chats:{uid}" for uid in ids]
            if keys:
                await client().delete(*keys)
        except Exception:
            pass


    async def invalidate_chat_list_for_user(user_id: int) -> None:
        await delete(f"chats:{user_id}")


    async def invalidate_profile(user_id: int) -> None:
        await delete(f"profile:{user_id}")
''')

# ============================================================== CHATS ROUTER (cached)
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
        msg = Message(
            chat_id=chat_id, author_id=actor_id, text=text, message_type="system",
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
            key,
            [c.model_dump(mode="json") for c in out],
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
            title=payload.title,
            is_group=payload.is_group,
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

        # invalidate всех участников
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
        await cache.invalidate_chat_list(db, chat_id)
        await cache.invalidate_chat_list_for_user(user_id)


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
        await cache.invalidate_chat_list(db, chat_id)
        await cache.invalidate_chat_list_for_user(current.id)


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
            await cache.invalidate_chat_list(db, chat.id)
            await cache.invalidate_chat_list_for_user(current.id)
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
        await cache.invalidate_chat_list_for_user(current.id)
''')

# ============================================================== USERS ROUTER (cached profile)
T["backend/app/routers/users.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache
    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Follow, Post, User
    from app.schemas import UserProfile, UserRead, UserUpdate


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
        await cache.invalidate_profile(current.id)
        return UserRead.model_validate(current)


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

        profile = UserProfile(
            id=u.id, username=u.username, display_name=u.display_name,
            bio=u.bio, avatar_color=u.avatar_color, created_at=u.created_at,
            posts_count=posts_count,
            followers_count=followers_count,
            following_count=following_count,
            is_following=is_following,
            is_me=u.id == current.id,
        )
        await cache.set(key, profile.model_dump(mode="json"), ttl=settings.CACHE_TTL_PROFILE)
        return profile


    @router.post("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
    async def follow_user(
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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
        user_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
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

# ============================================================== MESSAGES ROUTER (invalidate on change)
T["backend/app/routers/messages.py"] = _t('''
    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache
    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import ChatMember, File as FileModel, Message, User
    from app.schemas import FileRead, MessageCreate, MessageEdit, MessageRead


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


    async def _to_read(db: AsyncSession, m: Message) -> MessageRead:
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
            chat_id=chat_id, author_id=current.id,
            text=payload.text, message_type=payload.message_type,
            attachment_id=payload.attachment_id, reply_to_id=payload.reply_to_id,
        )
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        await cache.invalidate_chat_list(db, chat_id)
        return await _to_read(db, msg)


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
        return await _to_read(db, msg)


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
''')

# ============================================================== WS ROUTER (invalidate on change)
T["backend/app/routers/ws.py"] = _t('''
    from __future__ import annotations

    import json
    from datetime import datetime, timezone

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app import cache
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

# ============================================================== MAIN (ping redis on start)
T["backend/app/main.py"] = _t('''
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app import cache
    from app.config import settings
    from app.db import engine
    from app.routers import auth, calls, chats, files, messages, posts, users, ws
    from app.websocket_manager import manager


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.upload_path
        await cache.ping()
        yield
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
        redis_ok = await cache.ping()
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "redis": "ok" if redis_ok else "down",
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

    print("\nСпринт 6: Redis + кеширование")
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