#!/usr/bin/env python3
"""sprint10.py - tech debt: logging, refresh tokens, rate limit, redis presence, tests."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== DOCKERFILE
T["backend/Dockerfile"] = _t("""
    FROM python:3.12-slim

    ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

    WORKDIR /app

    RUN pip install --upgrade pip && pip install \\
        "fastapi==0.115.6" \\
        "uvicorn[standard]==0.34.0" \\
        "pydantic==2.10.4" \\
        "pydantic-settings==2.7.0" \\
        "sqlalchemy[asyncio]==2.0.36" \\
        "asyncpg==0.30.0" \\
        "alembic==1.14.0" \\
        "redis==5.2.1" \\
        "pyjwt==2.10.1" \\
        "passlib[bcrypt]==1.7.4" \\
        "bcrypt==4.0.1" \\
        "python-multipart==0.0.20" \\
        "email-validator==2.2.0" \\
        "filetype==1.2.0" \\
        "structlog==24.4.0" \\
        "pytest==8.3.4" \\
        "pytest-asyncio==0.25.0" \\
        "httpx==0.28.1"

    COPY . .

    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "/dev/null"]
""")

# ============================================================== CONFIG
T["backend/app/config.py"] = _t('''
    from functools import lru_cache
    from pathlib import Path

    from pydantic_settings import BaseSettings, SettingsConfigDict


    class Settings(BaseSettings):
        model_config = SettingsConfigDict(env_file=".env", extra="ignore")

        APP_NAME: str = "Messenger"
        ENV: str = "development"  # development | production
        DEBUG: bool = True
        API_V1_PREFIX: str = "/api/v1"

        SECRET_KEY: str = "change-me"
        ALGORITHM: str = "HS256"
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
        REFRESH_TOKEN_EXPIRE_DAYS: int = 30

        POSTGRES_HOST: str = "localhost"
        POSTGRES_PORT: int = 5432
        POSTGRES_USER: str = "messenger"
        POSTGRES_PASSWORD: str = "messenger"
        POSTGRES_DB: str = "messenger"

        REDIS_URL: str = "redis://localhost:6379/0"
        CACHE_TTL_CHATS: int = 15
        CACHE_TTL_PROFILE: int = 60

        UPLOAD_DIR: str = "/app/uploads"

        MAX_IMAGE_MB: int = 15
        MAX_VIDEO_MB: int = 100
        MAX_AUDIO_MB: int = 25
        MAX_DOCUMENT_MB: int = 25
        MAX_ARCHIVE_MB: int = 50
        MAX_OTHER_MB: int = 10
        USER_QUOTA_MB: int = 1024

        # Rate limit (запросов в минуту)
        RATE_LIMIT_AUTH: int = 10
        RATE_LIMIT_GLOBAL: int = 300

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

        @property
        def is_production(self) -> bool:
            return self.ENV == "production"


    @lru_cache
    def get_settings() -> Settings:
        return Settings()


    settings = get_settings()
''')

# ============================================================== LOGGING
T["backend/app/logging_config.py"] = _t('''
    """Structlog: JSON в prod, цветной вывод в dev."""
    from __future__ import annotations

    import logging
    import sys

    import structlog

    from app.config import settings


    def setup_logging() -> None:
        # базовый уровень
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=logging.DEBUG if settings.DEBUG else logging.INFO,
        )

        # приглушим шумные логгеры
        for noisy in ("uvicorn.access", "watchfiles", "sqlalchemy.engine"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

        shared_processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]

        if settings.is_production:
            # JSON — для Loki/ELK/CloudWatch
            renderer = structlog.processors.JSONRenderer()
        else:
            # цветной вывод для человека
            renderer = structlog.dev.ConsoleRenderer(colors=True)

        structlog.configure(
            processors=[*shared_processors, renderer],
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.DEBUG if settings.DEBUG else logging.INFO,
            ),
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )


    def get_logger(name: str = "app"):
        return structlog.get_logger(name)
''')

# ============================================================== SECURITY (refresh)
T["backend/app/security.py"] = _t('''
    from __future__ import annotations

    import hashlib
    import secrets
    from datetime import datetime, timedelta, timezone
    from typing import Any, Literal

    import jwt
    from jwt import InvalidTokenError
    from passlib.context import CryptContext

    from app.config import settings

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    TokenType = Literal["access", "refresh"]


    def hash_password(p: str) -> str:
        return pwd_context.hash(p)


    def verify_password(p: str, h: str) -> bool:
        try:
            return pwd_context.verify(p, h)
        except Exception:
            return False


    def _create(sub: str | int, exp: timedelta, tt: TokenType, jti: str | None = None) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": str(sub),
            "iat": int(now.timestamp()),
            "exp": int((now + exp).timestamp()),
            "type": tt,
        }
        if jti:
            payload["jti"] = jti
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def create_access_token(sub: str | int) -> str:
        return _create(sub, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


    def create_refresh_token(sub: str | int) -> tuple[str, str]:
        """Возвращает (token, jti). jti нужен для отзыва."""
        jti = secrets.token_urlsafe(24)
        token = _create(sub, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), "refresh", jti)
        return token, jti


    def decode_token(token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except InvalidTokenError as exc:
            raise ValueError("invalid token") from exc


    def hash_jti(jti: str) -> str:
        return hashlib.sha256(jti.encode("utf-8")).hexdigest()
''')

# ============================================================== RATE LIMIT
T["backend/app/rate_limit.py"] = _t('''
    """Простой rate limiter на Redis: INCR + EXPIRE."""
    from __future__ import annotations

    from fastapi import HTTPException, Request, status

    from app import cache
    from app.config import settings


    async def _hit(key: str, limit: int, window_sec: int) -> tuple[int, int]:
        """Инкрементирует счётчик и возвращает (count, ttl)."""
        client = cache.client()
        try:
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, window_sec)
            ttl = await client.ttl(key)
            return int(count), max(1, int(ttl))
        except Exception:
            # если Redis лёг — пропускаем, не блокируем приложение
            return 0, 0


    def client_ip(request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"


    async def limit_auth(request: Request) -> None:
        """Жёсткий лимит на /auth/* — против брутфорса."""
        ip = client_ip(request)
        key = f"rl:auth:{ip}"
        count, ttl = await _hit(key, settings.RATE_LIMIT_AUTH, 60)
        if count > settings.RATE_LIMIT_AUTH:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Слишком много попыток. Повторите через {ttl} сек.",
                headers={"Retry-After": str(ttl)},
            )


    async def limit_global(request: Request) -> None:
        """Мягкий лимит на всё остальное."""
        ip = client_ip(request)
        key = f"rl:global:{ip}"
        count, ttl = await _hit(key, settings.RATE_LIMIT_GLOBAL, 60)
        if count > settings.RATE_LIMIT_GLOBAL:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Превышен лимит запросов. Повторите через {ttl} сек.",
                headers={"Retry-After": str(ttl)},
            )
''')

# ============================================================== PRESENCE через Redis
T["backend/app/presence.py"] = _t('''
    """Presence и typing через Redis pub/sub — для нескольких воркеров."""
    from __future__ import annotations

    import asyncio
    import json
    from typing import Any

    from app import cache


    PRESENCE_KEY = "presence:online"           # set of user_id
    PRESENCE_LAST_SEEN = "presence:last_seen"  # hash user_id -> iso
    PUBSUB_CHANNEL = "presence:events"         # broadcast presence/typing
    TYPING_KEY = "presence:typing:{chat_id}"   # hash user_id -> iso ts


    async def mark_online(user_id: int) -> None:
        try:
            client = cache.client()
            await client.sadd(PRESENCE_KEY, str(user_id))
        except Exception:
            pass


    async def mark_offline(user_id: int, last_seen_iso: str) -> None:
        try:
            client = cache.client()
            await client.srem(PRESENCE_KEY, str(user_id))
            await client.hset(PRESENCE_LAST_SEEN, str(user_id), last_seen_iso)
        except Exception:
            pass


    async def is_online(user_id: int) -> bool:
        try:
            client = cache.client()
            return bool(await client.sismember(PRESENCE_KEY, str(user_id)))
        except Exception:
            return False


    async def get_online_ids() -> list[int]:
        try:
            client = cache.client()
            members = await client.smembers(PRESENCE_KEY)
            return [int(m) for m in members]
        except Exception:
            return []


    async def set_last_seen(user_id: int, iso: str) -> None:
        try:
            client = cache.client()
            await client.hset(PRESENCE_LAST_SEEN, str(user_id), iso)
        except Exception:
            pass


    async def get_last_seen(user_id: int) -> str | None:
        try:
            client = cache.client()
            val = await client.hget(PRESENCE_LAST_SEEN, str(user_id))
            return val
        except Exception:
            return None


    # -------- Pub/sub --------

    async def publish(event: dict[str, Any]) -> None:
        try:
            client = cache.client()
            await client.publish(PUBSUB_CHANNEL, json.dumps(event))
        except Exception:
            pass


    async def subscribe(callback) -> None:
        """Бесконечный цикл чтения pub/sub. Запускается как background task."""
        while True:
            try:
                client = cache.client()
                pubsub = client.pubsub()
                await pubsub.subscribe(PUBSUB_CHANNEL)
                async for msg in pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    try:
                        data = json.loads(msg["data"])
                        await callback(data)
                    except Exception:
                        continue
            except asyncio.CancelledError:
                return
            except Exception:
                await asyncio.sleep(2)
''')

# ============================================================== WEBSOCKET MANAGER (Redis-aware)
T["backend/app/websocket_manager.py"] = _t('''
    from __future__ import annotations

    from collections import defaultdict
    from datetime import datetime, timezone

    from fastapi import WebSocket

    from app import presence


    class ConnectionManager:
        """Локальный менеджер + публикация presence в Redis."""

        def __init__(self) -> None:
            self._user_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._chat_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._ws_user: dict[WebSocket, int] = {}
            self._typing: dict[tuple[int, int], float] = {}

        async def connect(self, user_id: int, ws: WebSocket) -> None:
            await ws.accept()
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

        async def broadcast_local(self, message: dict) -> None:
            """Отправить всем локальным соединениям."""
            for user_id in list(self._user_conns.keys()):
                await self.send_to_user(user_id, message)

        async def broadcast_all(self, message: dict) -> None:
            """Опубликовать всем инстансам (включая этот) через Redis."""
            await presence.publish({"kind": "broadcast", "message": message})
            await self.broadcast_local(message)

        async def close_all(self) -> None:
            for user_conns in list(self._user_conns.values()):
                for ws in list(user_conns):
                    try:
                        await ws.close()
                    finally:
                        await self.disconnect(ws)


    manager = ConnectionManager()
''')

# ============================================================== SCHEMAS (refresh)
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
        expires_in: int = Field(description="Секунд до истечения access_token")


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
        client_id: str | None = Field(default=None, max_length=64)


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

# ============================================================== AUTH ROUTER (refresh + rate limit)
T["backend/app/routers/auth.py"] = _t('''
    from __future__ import annotations

    import random
    from datetime import datetime, timezone

    from fastapi import APIRouter, Depends, HTTPException, Request, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache, presence
    from app.config import settings
    from app.db import get_session
    from app.deps import CurrentUser
    from app.logging_config import get_logger
    from app.models import User
    from app.rate_limit import limit_auth
    from app.schemas import (
        LoginRequest, RefreshRequest, RegisterRequest, TokenPair, UserRead,
    )
    from app.security import (
        create_access_token, create_refresh_token, decode_token,
        hash_jti, hash_password, verify_password,
    )


    router = APIRouter()
    log = get_logger("auth")

    AVATAR_COLORS = [
        "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
        "#3b82f6", "#6366f1", "#a855f7", "#ec4899", "#f43f5e",
    ]

    REFRESH_KEY = "auth:refresh:{jti}"


    async def _store_refresh(jti: str, user_id: int) -> None:
        try:
            client = cache.client()
            await client.setex(
                REFRESH_KEY.format(jti=hash_jti(jti)),
                settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
                str(user_id),
            )
        except Exception:
            pass


    async def _revoke_refresh(jti: str) -> None:
        try:
            client = cache.client()
            await client.delete(REFRESH_KEY.format(jti=hash_jti(jti)))
        except Exception:
            pass


    async def _is_refresh_active(jti: str) -> bool:
        try:
            client = cache.client()
            return bool(await client.exists(REFRESH_KEY.format(jti=hash_jti(jti))))
        except Exception:
            return True  # если Redis лёг — не блокируем


    @router.post(
        "/register",
        response_model=UserRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(limit_auth)],
    )
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
        log.info("user_registered", user_id=user.id, username=user.username)
        return UserRead.model_validate(user)


    @router.post(
        "/login",
        response_model=TokenPair,
        dependencies=[Depends(limit_auth)],
    )
    async def login(
        payload: LoginRequest,
        request: Request,
        db: AsyncSession = Depends(get_session),
    ):
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()

        # Защита от timing-атак: всегда выполняем bcrypt
        ok = user is not None and verify_password(payload.password, user.hashed_password)
        if not ok:
            log.warning("login_failed", username=payload.username)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")

        access = create_access_token(user.id)
        refresh, jti = create_refresh_token(user.id)
        await _store_refresh(jti, user.id)

        user.last_seen = datetime.now(timezone.utc)
        await db.flush()

        log.info("login_ok", user_id=user.id)
        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


    @router.post("/refresh", response_model=TokenPair)
    async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_session)):
        try:
            data = decode_token(payload.refresh_token)
        except ValueError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")

        if data.get("type") != "refresh":
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "wrong token type")

        jti = data.get("jti")
        if not jti or not await _is_refresh_active(jti):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "refresh token revoked")

        user_id = int(data["sub"])
        user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")

        # ротация: старый отзываем, выдаём новый
        await _revoke_refresh(jti)
        access = create_access_token(user.id)
        new_refresh, new_jti = create_refresh_token(user.id)
        await _store_refresh(new_jti, user.id)

        return TokenPair(
            access_token=access,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(payload: RefreshRequest):
        try:
            data = decode_token(payload.refresh_token)
        except ValueError:
            return
        jti = data.get("jti")
        if jti:
            await _revoke_refresh(jti)


    @router.get("/me", response_model=UserRead)
    async def me(current: CurrentUser):
        return UserRead.model_validate(current)
''')

# ============================================================== WS (presence через pubsub)
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
    async def ws_endpoint(ws: WebSocket, token: str) -> None:
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                raise ValueError("wrong token type")
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
        log.info("ws_connected", user_id=user_id, username=username)

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
                            await ws.send_json({
                                "type": "error", "client_id": client_id,
                                "detail": "not a member",
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
                            "client_id": client_id,
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
                            select(MessageReaction).where(
                                MessageReaction.message_id == message_id
                            )
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
            log.error("ws_error", user_id=user_id, error=str(e))
        finally:
            await manager.disconnect(ws)
            async with SessionLocal() as db:
                u = (await db.execute(
                    select(User).where(User.id == user_id)
                )).scalar_one_or_none()
                if u:
                    u.last_seen = datetime.now(timezone.utc)
                    await db.commit()
            log.info("ws_disconnected", user_id=user_id)
''')

# ============================================================== USERS ROUTER — presence через Redis
T["backend/app/routers/users.py"] = _t('''
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import func, or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app import cache, presence
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


    @router.get("/{user_id}/presence")
    async def user_presence(user_id: int):
        online = await presence.is_online(user_id)
        last_seen = await presence.get_last_seen(user_id)
        return {"user_id": user_id, "online": online, "last_seen": last_seen}


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

# ============================================================== MAIN
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
    from app.logging_config import get_logger, setup_logging
    from app.routers import auth, calls, chats, files, messages, posts, users, ws
    from app.websocket_manager import manager


    setup_logging()
    log = get_logger("main")


    async def _on_presence_event(event: dict) -> None:
        """Слушаем Redis pub/sub — ретранслируем другим инстансам."""
        kind = event.get("kind")
        if kind == "broadcast":
            await manager.broadcast_local(event["message"])
        elif kind == "presence":
            # обновим локальные сокеты
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

        # подписываемся на pub/sub
        pubsub_task = asyncio.create_task(presence.subscribe(_on_presence_event))

        yield

        log.info("shutdown")
        pubsub_task.cancel()
        try:
            await pubsub_task
        except (asyncio.CancelledError, Exception):
            pass
        await manager.close_all()
        await cache.close()
        await engine.dispose()


    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

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
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )


    @app.exception_handler(Exception)
    async def unhandled_exc_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", path=request.url.path, error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
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


    @app.get("/health", tags=["health"])
    async def health():
        """Liveness probe — процесс жив."""
        return {"status": "ok", "app": settings.APP_NAME}


    @app.get("/readyz", tags=["health"])
    async def readyz():
        """Readiness probe — все зависимости готовы."""
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

# ============================================================== TESTS
T["backend/tests/__init__.py"] = ""

T["backend/tests/conftest.py"] = _t('''
    from __future__ import annotations

    import asyncio
    from typing import AsyncIterator

    import pytest
    import pytest_asyncio
    from httpx import ASGITransport, AsyncClient

    from app.main import app


    @pytest.fixture(scope="session")
    def event_loop():
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()


    @pytest_asyncio.fixture
    async def client() -> AsyncIterator[AsyncClient]:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


    @pytest_asyncio.fixture
    async def auth_client(client: AsyncClient) -> AsyncIterator[AsyncClient]:
        """Клиент с уже залогиненным пользователем. Пропускает, если БД недоступна."""
        import random
        import string
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        username = f"test_{suffix}"
        password = "supersecret123"

        try:
            r = await client.post("/api/v1/auth/register", json={
                "username": username,
                "email": f"{username}@test.local",
                "password": password,
            })
            if r.status_code not in (201, 409):
                pytest.skip(f"register failed: {r.status_code}")
        except Exception as e:
            pytest.skip(f"DB not available: {e}")

        r = await client.post("/api/v1/auth/login", json={
            "username": username, "password": password,
        })
        if r.status_code != 200:
            pytest.skip(f"login failed: {r.status_code}")

        data = r.json()
        client.headers["Authorization"] = f"Bearer {data['access_token']}"
        yield client
''')

T["backend/tests/test_health.py"] = _t('''
    from __future__ import annotations

    import pytest


    @pytest.mark.asyncio
    async def test_health(client):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "app" in data


    @pytest.mark.asyncio
    async def test_readyz(client):
        r = await client.get("/readyz")
        # 200 если всё ок, 503 если что-то отвалилось — оба варианта валидны
        assert r.status_code in (200, 503)
        data = r.json()
        assert "ready" in data
        assert "redis" in data
        assert "db" in data
''')

T["backend/tests/test_auth.py"] = _t('''
    from __future__ import annotations

    import random
    import string

    import pytest


    def _rand(prefix: str = "u") -> str:
        s = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{prefix}_{s}"


    @pytest.mark.asyncio
    async def test_register_and_login(client):
        username = _rand()
        password = "supersecret123"

        r = await client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.local",
            "password": password,
        })
        if r.status_code == 500:
            pytest.skip("DB not available")
        assert r.status_code == 201
        data = r.json()
        assert data["username"] == username
        assert "hashed_password" not in data

        r = await client.post("/api/v1/auth/login", json={
            "username": username, "password": password,
        })
        assert r.status_code == 200
        tokens = r.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0


    @pytest.mark.asyncio
    async def test_login_wrong_password(client):
        username = _rand()
        r = await client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.local",
            "password": "supersecret123",
        })
        if r.status_code == 500:
            pytest.skip("DB not available")

        r = await client.post("/api/v1/auth/login", json={
            "username": username, "password": "wrong_password",
        })
        assert r.status_code == 401


    @pytest.mark.asyncio
    async def test_refresh_rotates_token(client):
        username = _rand()
        password = "supersecret123"
        r = await client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@test.local",
            "password": password,
        })
        if r.status_code == 500:
            pytest.skip("DB not available")

        r = await client.post("/api/v1/auth/login", json={
            "username": username, "password": password,
        })
        assert r.status_code == 200
        old_refresh = r.json()["refresh_token"]

        r = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": old_refresh,
        })
        assert r.status_code == 200
        new_refresh = r.json()["refresh_token"]
        assert new_refresh != old_refresh

        # старый токен отозван
        r = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": old_refresh,
        })
        assert r.status_code == 401


    @pytest.mark.asyncio
    async def test_me_requires_auth(client):
        r = await client.get("/api/v1/auth/me")
        assert r.status_code == 401


    @pytest.mark.asyncio
    async def test_me_with_token(auth_client):
        r = await auth_client.get("/api/v1/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["username"].startswith("test_")
''')

T["backend/tests/test_users.py"] = _t('''
    from __future__ import annotations

    import pytest


    @pytest.mark.asyncio
    async def test_update_me(auth_client):
        r = await auth_client.patch("/api/v1/users/me", json={
            "display_name": "Test User",
            "bio": "Hello world",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["display_name"] == "Test User"
        assert data["bio"] == "Hello world"


    @pytest.mark.asyncio
    async def test_list_users(auth_client):
        r = await auth_client.get("/api/v1/users", params={"limit": 10})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


    @pytest.mark.asyncio
    async def test_presence_endpoint(auth_client):
        me = (await auth_client.get("/api/v1/auth/me")).json()
        r = await auth_client.get(f"/api/v1/users/{me['id']}/presence")
        assert r.status_code == 200
        data = r.json()
        assert "online" in data
        assert "user_id" in data
''')

T["backend/pytest.ini"] = _t("""
    [pytest]
    asyncio_mode = auto
    testpaths = tests
    addopts = -q --tb=short
""")

# ============================================================== ENV EXAMPLE
T["backend/.env.example"] = _t("""
    APP_NAME=Messenger
    ENV=development
    DEBUG=true
    API_V1_PREFIX=/api/v1
    SECRET_KEY=change-me-in-production
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    REFRESH_TOKEN_EXPIRE_DAYS=30

    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    POSTGRES_USER=messenger
    POSTGRES_PASSWORD=messenger
    POSTGRES_DB=messenger

    REDIS_URL=redis://redis:6379/0
    CACHE_TTL_CHATS=15
    CACHE_TTL_PROFILE=60

    UPLOAD_DIR=/app/uploads
    MAX_IMAGE_MB=15
    MAX_VIDEO_MB=100
    MAX_AUDIO_MB=25
    MAX_DOCUMENT_MB=25
    MAX_ARCHIVE_MB=50
    MAX_OTHER_MB=10
    USER_QUOTA_MB=1024

    RATE_LIMIT_AUTH=10
    RATE_LIMIT_GLOBAL=300

    CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
""")

# ============================================================== FRONTEND — refresh
T["frontend/src/api.ts"] = _t('''
    import axios, { AxiosError, AxiosRequestConfig } from "axios";

    export const API_BASE = "http://localhost:8000/api/v1";
    export const WS_BASE = "ws://localhost:8000/api/v1/ws";

    export const api = axios.create({ baseURL: API_BASE });

    let refreshingPromise: Promise<string | null> | null = null;

    async function doRefresh(): Promise<string | null> {
      const refresh = localStorage.getItem("refresh_token");
      if (!refresh) return null;
      try {
        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refresh,
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        return data.access_token as string;
      } catch {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        window.dispatchEvent(new Event("auth:logout"));
        return null;
      }
    }

    api.interceptors.request.use((config) => {
      const t = localStorage.getItem("access_token");
      if (t) config.headers.Authorization = `Bearer ${t}`;
      return config;
    });

    api.interceptors.response.use(
      (r) => r,
      async (error: AxiosError) => {
        const original = error.config as AxiosRequestConfig & { _retry?: boolean };
        if (
          error.response?.status === 401 &&
          original &&
          !original._retry &&
          !original.url?.includes("/auth/refresh") &&
          !original.url?.includes("/auth/login")
        ) {
          original._retry = true;
          if (!refreshingPromise) {
            refreshingPromise = doRefresh().finally(() => {
              refreshingPromise = null;
            });
          }
          const newToken = await refreshingPromise;
          if (newToken) {
            original.headers = { ...(original.headers || {}), Authorization: `Bearer ${newToken}` };
            return api(original);
          }
        }
        return Promise.reject(error);
      },
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

    export interface UploadOptions {
      onProgress?: (percent: number) => void;
      signal?: AbortSignal;
    }

    export async function uploadFile(
      file: File,
      options: UploadOptions = {},
    ): Promise<{ id: number; filename: string; content_type: string; size: number; created_at: string }> {
      const form = new FormData();
      form.append("file", file);

      const { data } = await api.post("/files/upload", form, {
        headers: { "Content-Type": "multipart/form-data" },
        signal: options.signal,
        onUploadProgress: (e) => {
          if (options.onProgress && e.total) {
            options.onProgress(Math.round((e.loaded / e.total) * 100));
          }
        },
      });
      return data;
    }
''')

# ============================================================== LOGIN — сохранить refresh_token
T["frontend/src/Login.tsx"] = _t('''
    import { useEffect, useState } from "react";
    import { api } from "./api";

    const BOOT_LINES = [
      "> INITIALIZING NEURAL LINK...",
      "> CONNECTING TO NODE 0x7F4A...",
      "> ENCRYPTION: AES-256 ACTIVE",
      "> HANDSHAKE COMPLETE",
      "> AWAITING IDENTIFICATION",
    ];

    export default function Login({ onLogin }: { onLogin: () => void }) {
      const [mode, setMode] = useState<"login" | "register">("login");
      const [username, setUsername] = useState("");
      const [password, setPassword] = useState("");
      const [email, setEmail] = useState("");
      const [displayName, setDisplayName] = useState("");
      const [error, setError] = useState("");
      const [busy, setBusy] = useState(false);
      const [visibleBoot, setVisibleBoot] = useState(0);

      useEffect(() => {
        if (visibleBoot >= BOOT_LINES.length) return;
        const t = setTimeout(() => setVisibleBoot((v) => v + 1), 320);
        return () => clearTimeout(t);
      }, [visibleBoot]);

      const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setBusy(true);
        try {
          if (mode === "register") {
            await api.post("/auth/register", {
              username, email, password,
              display_name: displayName || null,
            });
          }
          const { data } = await api.post("/auth/login", { username, password });
          localStorage.setItem("access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("refresh_token", data.refresh_token);
          }
          onLogin();
        } catch (err: any) {
          const msg = err.response?.data?.detail;
          setError(typeof msg === "string" ? msg : "ACCESS DENIED");
        } finally {
          setBusy(false);
        }
      };

      const inputCls = "cyber-input w-full rounded-sm px-4 py-3 text-sm";

      return (
        <div className="relative z-10 flex min-h-screen items-center justify-center p-4">
          <div className="corner-frame w-full max-w-md hud-panel rounded-sm p-8">
            <div className="mb-6 text-center">
              <div className="flicker mb-4 inline-block">
                <div className="text-6xl">◈</div>
              </div>
              <h1
                className="glitch text-3xl font-bold tracking-widest"
                data-text="MESSENGER"
              >
                MESSENGER
              </h1>
              <div className="mt-2 text-[10px] uppercase tracking-[0.4em] text-cyber-dim">
                {mode === "login" ? "secure access terminal" : "register new operator"}
              </div>
            </div>

            <div className="mb-6 h-20 overflow-hidden border-l-2 border-cyber-cyan/40 bg-black/40 p-3 text-[10px] leading-relaxed text-cyber-cyan/80">
              {BOOT_LINES.slice(0, visibleBoot).map((l, i) => (
                <div key={i} className="animate-materialize">{l}</div>
              ))}
              {visibleBoot >= BOOT_LINES.length && (
                <div className="cursor neon-text" />
              )}
            </div>

            <form onSubmit={submit} className="space-y-3">
              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                  // OPERATOR ID
                </label>
                <input
                  className={inputCls}
                  placeholder="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>

              {mode === "register" && (
                <>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // COMM CHANNEL
                    </label>
                    <input
                      className={inputCls}
                      type="email"
                      placeholder="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>
                  <div>
                    <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                      // CALLSIGN (optional)
                    </label>
                    <input
                      className={inputCls}
                      placeholder="display name"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                    />
                  </div>
                </>
              )}

              <div>
                <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                  // ACCESS KEY
                </label>
                <input
                  className={inputCls}
                  type="password"
                  placeholder="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>

              {error && (
                <div className="neon-border-mag animate-materialize rounded-sm bg-cyber-magenta/10 px-3 py-2 text-center text-xs neon-text-mag">
                  ⚠ {error}
                </div>
              )}

              <button
                type="submit"
                disabled={busy}
                className="cyber-btn w-full rounded-sm py-3 text-sm font-bold"
              >
                {busy ? "[ AUTHENTICATING... ]" : mode === "login" ? "[ ENTER SYSTEM ]" : "[ CREATE OPERATOR ]"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setMode(mode === "login" ? "register" : "login");
                  setError("");
                }}
                className="w-full text-center text-[11px] uppercase tracking-widest text-cyber-dim transition hover:text-cyber-cyan chroma"
              >
                {mode === "login"
                  ? "> no account? register"
                  : "> already have access? sign in"}
              </button>
            </form>

            <div className="mt-6 flex items-center justify-between border-t border-cyber-cyan/20 pt-3 text-[9px] uppercase tracking-widest text-cyber-dim">
              <span className="flex items-center gap-2">
                <span className="status-dot" style={{ color: "#00ff88" }} />
                node: online
              </span>
              <span>v10.0.tech</span>
            </div>
          </div>
        </div>
    );
''')

# ============================================================== APP — logout чистит refresh
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
    import { useMessageQueue } from "./useMessageQueue";
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

      useEffect(() => {
        applyTheme(theme);
        localStorage.setItem("theme", theme);
      }, [theme]);

      useEffect(() => {
        if (user) ensureNotificationPermission();
      }, [user]);

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

      const { send, subscribe, readyState } = useWebSocket(onWs, user?.id ?? null);
      const rtc = useWebRTC(send, subscribe);

      const isWsOpen = useCallback(() => readyState === WebSocket.OPEN, [readyState]);

      const queue = useMessageQueue(user?.id ?? null, send, isWsOpen);

      const enqueueForChat = useCallback((
        chatId: number, text: string | null, messageType: string,
        attachmentId: number | null, replyToId: number | null,
      ) => {
        if (!user) return;
        queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {
          id: user.id, username: user.username,
          display_name: user.display_name,
          avatar_color: user.avatar_color,
        });
      }, [queue, user]);

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
          localStorage.removeItem("refresh_token");
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

      const logout = async () => {
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try { await api.post("/auth/logout", { refresh_token: refresh }); } catch {}
        }
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
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

      const commands: Command[] = useMemo(() => {
        const list: Command[] = [
          { id: "feed", label: "Open feed", icon: "📰", action: () => setMode("feed") },
          { id: "profile", label: "Open my profile", icon: "👤", action: () => { setProfileUserId(user?.id ?? null); setMode("profile"); } },
          { id: "settings", label: "Open settings", icon: "⚙", action: () => setShowSettings(true) },
          { id: "theme-cyber", label: "Theme: Cyber", icon: "◈", action: () => setTheme("cyber") },
          { id: "theme-matrix", label: "Theme: Matrix", icon: "▶", action: () => setTheme("matrix") },
          { id: "theme-sunset", label: "Theme: Sunset", icon: "☀", action: () => setTheme("sunset") },
          { id: "theme-amber", label: "Theme: Amber", icon: "◆", action: () => setTheme("amber") },
          { id: "retry-failed", label: "Retry failed messages", icon: "🔁", action: () => queue.retryFailed() },
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
      }, [chats, user?.id, queue]);

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
      const failedTotal = queue.queue.filter((m) => m.status === "failed").length;

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
              failedQueue={failedTotal}
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
                  queuedMessages={queue.queue}
                  onEnqueue={enqueueForChat}
                  onRemoveQueued={queue.removeByClientId}
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

    print("\nСпринт 10: техдолг")
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