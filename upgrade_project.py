#!/usr/bin/env python3
"""
upgrade_project.py — добавляет в проект мессенджера:
  * модели и роуты для чатов и сообщений
  * WebSocket для realtime-чата
  * TailwindCSS на фронте
  * Alembic для миграций БД

Запуск:
    python upgrade_project.py --path C:\\Users\\karachunn\\Desktop\\jopa
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

PROJECT_DEFAULT = "my-messenger"


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


TEMPLATES: dict[str, str] = {}

# ============================================================== BACKEND
TEMPLATES["backend/pyproject.toml"] = _t("""
    [project]
    name = "messenger-backend"
    version = "0.2.0"
    requires-python = ">=3.12"
    dependencies = [
        "fastapi>=0.115",
        "uvicorn[standard]>=0.30",
        "pydantic>=2.8",
        "pydantic-settings>=2.4",
        "sqlalchemy[asyncio]>=2.0.32",
        "asyncpg>=0.29",
        "alembic>=1.13",
        "python-jose[cryptography]>=3.3",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt==4.0.1",
        "python-multipart>=0.0.9",
        "email-validator>=2.2",
        "websockets>=12.0",
    ]

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"

    [tool.hatch.build.targets.wheel]
    packages = ["app"]
""")

TEMPLATES["backend/Dockerfile"] = _t("""
    FROM python:3.12-slim

    ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

    WORKDIR /app

    COPY pyproject.toml ./
    RUN pip install --upgrade pip && pip install -e .

    COPY . .

    EXPOSE 8000
    CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
""")

TEMPLATES["backend/alembic.ini"] = _t("""
    [alembic]
    script_location = alembic
    prepend_sys_path = .
    sqlalchemy.url =

    [loggers]
    keys = root,sqlalchemy,alembic

    [handlers]
    keys = console

    [formatters]
    keys = generic

    [logger_root]
    level = WARN
    handlers = console

    [logger_sqlalchemy]
    level = WARN
    handlers =
    qualname = sqlalchemy.engine

    [logger_alembic]
    level = INFO
    handlers =
    qualname = alembic

    [handler_console]
    class = StreamHandler
    args = (sys.stderr,)
    level = NOTSET
    formatter = generic

    [formatter_generic]
    format = %(levelname)-5.5s [%(name)s] %(message)s
""")

TEMPLATES["backend/alembic/env.py"] = _t('''
    from __future__ import annotations

    import asyncio
    from logging.config import fileConfig

    from alembic import context
    from sqlalchemy import pool
    from sqlalchemy.engine import Connection
    from sqlalchemy.ext.asyncio import async_engine_from_config

    from app.config import settings
    from app.models import Base

    config = context.config
    config.set_main_option("sqlalchemy.url", settings.database_url)

    if config.config_file_name is not None:
        fileConfig(config.config_file_name)

    target_metadata = Base.metadata


    def run_migrations_offline() -> None:
        context.configure(
            url=settings.database_url,
            target_metadata=target_metadata,
            literal_binds=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


    def do_run_migrations(connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


    async def run_async_migrations() -> None:
        connectable = async_engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()


    if context.is_offline_mode():
        run_migrations_offline()
    else:
        asyncio.run(run_async_migrations())
''')

# Внимание: этот файл содержит ${...} плейсхолдеры Alembic и тройные кавычки,
# поэтому собираем его через конкатенацию строк, а не через _t().
TEMPLATES["backend/alembic/script.py.mako"] = (
    '"""${message}\n'
    "\n"
    "Revision ID: ${up_revision}\n"
    "Revises: ${down_revision | comma,n}\n"
    "Create Date: ${create_date}\n"
    '"""\n'
    "from __future__ import annotations\n"
    "\n"
    "from typing import Sequence, Union\n"
    "\n"
    "from alembic import op\n"
    "import sqlalchemy as sa\n"
    "${imports if imports else \"\"}\n"
    "\n"
    "revision: str = ${repr(up_revision)}\n"
    "down_revision: Union[str, None] = ${repr(down_revision)}\n"
    "branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}\n"
    "depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}\n"
    "\n"
    "\n"
    "def upgrade() -> None:\n"
    '    ${upgrades if upgrades else "pass"}\n'
    "\n"
    "\n"
    "def downgrade() -> None:\n"
    '    ${downgrades if downgrades else "pass"}\n'
)

TEMPLATES["backend/alembic/versions/0001_initial.py"] = _t('''
    """initial schema

    Revision ID: 0001
    Revises:
    Create Date: 2025-01-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0001"
    down_revision: Union[str, None] = None
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(50), nullable=False, unique=True),
            sa.Column("email", sa.String(255), nullable=False, unique=True),
            sa.Column("hashed_password", sa.String(255), nullable=False),
            sa.Column("display_name", sa.String(100), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_users_username", "users", ["username"])
        op.create_index("ix_users_email", "users", ["email"])

        op.create_table(
            "chats",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("is_group", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        op.create_table(
            "chat_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "chat_id",
                sa.Integer(),
                sa.ForeignKey("chats.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(20), nullable=False, server_default="member"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.UniqueConstraint("chat_id", "user_id", name="uq_chat_user"),
        )

        op.create_table(
            "messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "chat_id",
                sa.Integer(),
                sa.ForeignKey("chats.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_messages_chat_id", "messages", ["chat_id"])
        op.create_index("ix_messages_created_at", "messages", ["created_at"])


    def downgrade() -> None:
        op.drop_table("messages")
        op.drop_table("chat_members")
        op.drop_table("chats")
        op.drop_table("users")
''')

TEMPLATES["backend/app/__init__.py"] = ""

TEMPLATES["backend/app/config.py"] = _t("""
    from functools import lru_cache
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

        CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:8000"]

        @property
        def database_url(self) -> str:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )


    @lru_cache
    def get_settings() -> Settings:
        return Settings()


    settings = get_settings()
""")

TEMPLATES["backend/app/db.py"] = _t("""
    from collections.abc import AsyncIterator
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.config import settings


    engine = create_async_engine(settings.database_url, echo=False, future=True)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


    async def get_session() -> AsyncIterator[AsyncSession]:
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
""")

TEMPLATES["backend/app/security.py"] = _t("""
    from datetime import datetime, timedelta, timezone
    from typing import Any
    from jose import JWTError, jwt
    from passlib.context import CryptContext
    from app.config import settings


    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


    def hash_password(password: str) -> str:
        return pwd_context.hash(password)


    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)


    def create_access_token(subject: str | int) -> str:
        now = datetime.now(timezone.utc)
        payload: dict[str, Any] = {
            "sub": str(subject),
            "iat": int(now.timestamp()),
            "exp": int(
                (now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()
            ),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def decode_token(token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise ValueError("invalid token") from exc
""")

TEMPLATES["backend/app/models.py"] = _t("""
    from __future__ import annotations

    from datetime import datetime
    from sqlalchemy import (
        Boolean,
        DateTime,
        ForeignKey,
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
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
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
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
        )

        chat: Mapped[Chat] = relationship(back_populates="messages")
        author: Mapped[User] = relationship(back_populates="messages")
""")

TEMPLATES["backend/app/schemas.py"] = _t("""
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
        is_active: bool
        created_at: datetime


    class ChatCreate(BaseModel):
        title: str | None = None
        is_group: bool = False
        member_usernames: list[str] = Field(default_factory=list)


    class ChatRead(BaseModel):
        model_config = ConfigDict(from_attributes=True)
        id: int
        title: str | None
        is_group: bool
        created_at: datetime


    class MessageCreate(BaseModel):
        text: str = Field(min_length=1, max_length=4000)


    class MessageRead(BaseModel):
        id: int
        chat_id: int
        author_id: int
        author_username: str
        text: str
        created_at: datetime
""")

TEMPLATES["backend/app/deps.py"] = _t("""
    from typing import Annotated

    from fastapi import Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import settings
    from app.db import get_session
    from app.models import User
    from app.security import decode_token


    oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
    DbSession = Annotated[AsyncSession, Depends(get_session)]


    async def get_current_user(
        db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
    ) -> User:
        exc = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except (ValueError, KeyError):
            raise exc

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise exc
        return user


    CurrentUser = Annotated[User, Depends(get_current_user)]
""")

TEMPLATES["backend/app/websocket_manager.py"] = _t("""
    from __future__ import annotations

    from collections import defaultdict

    from fastapi import WebSocket


    class ConnectionManager:
        \"\"\"Хранит соединения: пользователь -> сокеты и чат -> сокеты.\"\"\"

        def __init__(self) -> None:
            self._user_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._chat_conns: dict[int, set[WebSocket]] = defaultdict(set)
            self._ws_user: dict[WebSocket, int] = {}

        async def connect(self, user_id: int, ws: WebSocket) -> None:
            await ws.accept()
            self._user_conns[user_id].add(ws)
            self._ws_user[ws] = user_id

        async def disconnect(self, ws: WebSocket) -> None:
            user_id = self._ws_user.pop(ws, None)
            if user_id is not None:
                self._user_conns.get(user_id, set()).discard(ws)
                if not self._user_conns.get(user_id):
                    self._user_conns.pop(user_id, None)
            for conns in self._chat_conns.values():
                conns.discard(ws)

        def subscribe(self, ws: WebSocket, chat_id: int) -> None:
            self._chat_conns[chat_id].add(ws)

        def unsubscribe(self, ws: WebSocket, chat_id: int) -> None:
            self._chat_conns.get(chat_id, set()).discard(ws)

        async def broadcast_to_chat(self, chat_id: int, message: dict) -> None:
            for ws in list(self._chat_conns.get(chat_id, ())):
                try:
                    await ws.send_json(message)
                except Exception:
                    await self.disconnect(ws)

        async def close_all(self) -> None:
            for user_conns in list(self._user_conns.values()):
                for ws in list(user_conns):
                    try:
                        await ws.close()
                    finally:
                        await self.disconnect(ws)


    manager = ConnectionManager()
""")

# ---------------- Роутеры
TEMPLATES["backend/app/routers/__init__.py"] = ""

TEMPLATES["backend/app/routers/auth.py"] = _t("""
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import User
    from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
    from app.security import create_access_token, hash_password, verify_password


    router = APIRouter()


    @router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
    async def register(
        payload: RegisterRequest, db: AsyncSession = Depends(get_session)
    ) -> UserRead:
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
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return UserRead.model_validate(user)


    @router.post("/login", response_model=TokenResponse)
    async def login(
        payload: LoginRequest, db: AsyncSession = Depends(get_session)
    ) -> TokenResponse:
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
        return TokenResponse(access_token=create_access_token(user.id))


    @router.get("/me", response_model=UserRead)
    async def me(current: CurrentUser) -> UserRead:
        return UserRead.model_validate(current)
""")

TEMPLATES["backend/app/routers/users.py"] = _t("""
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import or_, select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import User
    from app.schemas import UserRead


    router = APIRouter()


    @router.get("", response_model=list[UserRead])
    async def list_users(
        current: CurrentUser,
        q: str | None = None,
        limit: int = 50,
        db: AsyncSession = Depends(get_session),
    ) -> list[UserRead]:
        stmt = select(User).where(User.id != current.id)
        if q:
            p = f"%{q}%"
            stmt = stmt.where(or_(User.username.ilike(p), User.display_name.ilike(p)))
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return [UserRead.model_validate(u) for u in result.scalars().all()]


    @router.get("/{user_id}", response_model=UserRead)
    async def get_user(user_id: int, db: AsyncSession = Depends(get_session)) -> UserRead:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
        return UserRead.model_validate(user)
""")

TEMPLATES["backend/app/routers/chats.py"] = _t("""
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, User
    from app.schemas import ChatCreate, ChatRead


    router = APIRouter()


    @router.get("", response_model=list[ChatRead])
    async def my_chats(
        current: CurrentUser, db: AsyncSession = Depends(get_session)
    ) -> list[ChatRead]:
        stmt = (
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(ChatMember.user_id == current.id)
            .order_by(Chat.created_at.desc())
        )
        result = await db.execute(stmt)
        return [ChatRead.model_validate(c) for c in result.scalars().all()]


    @router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
    async def create_chat(
        payload: ChatCreate,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ) -> ChatRead:
        chat = Chat(title=payload.title, is_group=payload.is_group)
        db.add(chat)
        await db.flush()

        member_ids = {current.id}
        if payload.member_usernames:
            result = await db.execute(
                select(User).where(User.username.in_(payload.member_usernames))
            )
            for u in result.scalars().all():
                member_ids.add(u.id)

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
        return ChatRead.model_validate(chat)


    @router.get("/{chat_id}", response_model=ChatRead)
    async def get_chat(
        chat_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ) -> ChatRead:
        stmt = (
            select(Chat)
            .join(ChatMember, ChatMember.chat_id == Chat.id)
            .where(Chat.id == chat_id, ChatMember.user_id == current.id)
            .options(selectinload(Chat.members))
        )
        result = await db.execute(stmt)
        chat = result.scalar_one_or_none()
        if chat is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "chat not found")
        return ChatRead.model_validate(chat)
""")

TEMPLATES["backend/app/routers/messages.py"] = _t("""
    from fastapi import APIRouter, Depends, HTTPException, Query, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import Chat, ChatMember, Message
    from app.schemas import MessageCreate, MessageRead


    router = APIRouter()


    async def _ensure_member(db: AsyncSession, chat_id: int, user_id: int) -> None:
        result = await db.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id, ChatMember.user_id == user_id
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not a member")


    @router.get("/{chat_id}/messages", response_model=list[MessageRead])
    async def list_messages(
        chat_id: int,
        current: CurrentUser,
        limit: int = Query(100, le=500),
        db: AsyncSession = Depends(get_session),
    ) -> list[MessageRead]:
        await _ensure_member(db, chat_id, current.id)
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(selectinload(Message.author))
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        return [
            MessageRead(
                id=m.id,
                chat_id=m.chat_id,
                author_id=m.author_id,
                author_username=m.author.username,
                text=m.text,
                created_at=m.created_at,
            )
            for m in result.scalars().all()
        ]


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
    ) -> MessageRead:
        await _ensure_member(db, chat_id, current.id)
        msg = Message(chat_id=chat_id, author_id=current.id, text=payload.text)
        db.add(msg)
        await db.flush()
        await db.refresh(msg)
        return MessageRead(
            id=msg.id,
            chat_id=msg.chat_id,
            author_id=msg.author_id,
            author_username=current.username,
            text=msg.text,
            created_at=msg.created_at,
        )
""")

TEMPLATES["backend/app/routers/ws.py"] = _t("""
    from __future__ import annotations

    import json

    from fastapi import APIRouter, WebSocket, WebSocketDisconnect
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import ChatMember, Message, User
    from app.security import decode_token
    from app.websocket_manager import manager


    router = APIRouter()


    @router.websocket("/ws")
    async def ws_endpoint(ws: WebSocket, token: str) -> None:
        # 1. Авторизация
        try:
            payload = decode_token(token)
            user_id = int(payload["sub"])
        except Exception:
            await ws.close(code=4401)
            return

        async with SessionLocal() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user is None or not user.is_active:
                await ws.close(code=4401)
                return
            username = user.username

        await manager.connect(user_id, ws)

        try:
            while True:
                raw = await ws.receive_text()
                data = json.loads(raw)
                kind = data.get("type")

                if kind == "subscribe":
                    chat_id = int(data["chat_id"])
                    manager.subscribe(ws, chat_id)
                    await ws.send_json({"type": "subscribed", "chat_id": chat_id})

                elif kind == "unsubscribe":
                    chat_id = int(data["chat_id"])
                    manager.unsubscribe(ws, chat_id)

                elif kind == "send":
                    chat_id = int(data["chat_id"])
                    text = str(data.get("text", "")).strip()
                    if not text:
                        continue

                    async with SessionLocal() as db:
                        member = await db.execute(
                            select(ChatMember).where(
                                ChatMember.chat_id == chat_id,
                                ChatMember.user_id == user_id,
                            )
                        )
                        if member.scalar_one_or_none() is None:
                            await ws.send_json({"type": "error", "detail": "not a member"})
                            continue

                        msg = Message(chat_id=chat_id, author_id=user_id, text=text)
                        db.add(msg)
                        await db.commit()
                        await db.refresh(msg)

                        await manager.broadcast_to_chat(
                            chat_id,
                            {
                                "type": "message",
                                "chat_id": chat_id,
                                "id": msg.id,
                                "author_id": user_id,
                                "author_username": username,
                                "text": text,
                                "created_at": msg.created_at.isoformat(),
                            },
                        )
        except WebSocketDisconnect:
            pass
        finally:
            await manager.disconnect(ws)
""")

TEMPLATES["backend/app/main.py"] = _t("""
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

    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=f"{prefix}/auth", tags=["auth"])
    app.include_router(users.router, prefix=f"{prefix}/users", tags=["users"])
    app.include_router(chats.router, prefix=f"{prefix}/chats", tags=["chats"])
    app.include_router(messages.router, prefix=f"{prefix}/chats", tags=["messages"])
    app.include_router(ws.router, prefix=prefix, tags=["ws"])


    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}
""")

# ============================================================== FRONTEND
TEMPLATES["frontend/package.json"] = _t("""
    {
      "name": "messenger-frontend",
      "private": true,
      "version": "0.2.0",
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

TEMPLATES["frontend/tailwind.config.js"] = _t("""
    /** @type {import('tailwindcss').Config} */
    export default {
      content: ["./index.html", "./src/**/*.{ts,tsx}"],
      theme: {
        extend: {
          colors: {
            brand: { 500: "#6366f1", 600: "#4f46e5", 700: "#4338ca" }
          }
        }
      },
      plugins: []
    };
""")

TEMPLATES["frontend/postcss.config.js"] = _t("""
    export default {
      plugins: {
        tailwindcss: {},
        autoprefixer: {}
      }
    };
""")

TEMPLATES["frontend/src/index.css"] = _t("""
    @tailwind base;
    @tailwind components;
    @tailwind utilities;

    html, body, #root { height: 100%; margin: 0; }
    body { font-family: system-ui, -apple-system, sans-serif; }
""")

TEMPLATES["frontend/src/main.tsx"] = _t("""
    import React from "react";
    import ReactDOM from "react-dom/client";
    import App from "./App";
    import "./index.css";

    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
""")

TEMPLATES["frontend/src/api.ts"] = _t("""
    import axios from "axios";

    export const api = axios.create({ baseURL: "http://localhost:8000/api/v1" });

    api.interceptors.request.use((config) => {
      const t = localStorage.getItem("access_token");
      if (t) config.headers.Authorization = `Bearer ${t}`;
      return config;
    });

    export const WS_BASE = "ws://localhost:8000/api/v1/ws";
""")

TEMPLATES["frontend/src/types.ts"] = _t("""
    export interface User {
      id: number;
      username: string;
      email: string;
      display_name: string | null;
      is_active: boolean;
      created_at: string;
    }

    export interface Chat {
      id: number;
      title: string | null;
      is_group: boolean;
      created_at: string;
    }

    export interface Message {
      id: number;
      chat_id: number;
      author_id: number;
      author_username: string;
      text: string;
      created_at: string;
    }
""")

TEMPLATES["frontend/src/Login.tsx"] = _t("""
    import { useState } from "react";
    import { api } from "./api";

    export default function Login({ onLogin }: { onLogin: () => void }) {
      const [mode, setMode] = useState<"login" | "register">("login");
      const [username, setUsername] = useState("");
      const [password, setPassword] = useState("");
      const [email, setEmail] = useState("");
      const [error, setError] = useState("");

      const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        try {
          if (mode === "register") {
            await api.post("/auth/register", { username, email, password });
          }
          const { data } = await api.post("/auth/login", { username, password });
          localStorage.setItem("access_token", data.access_token);
          onLogin();
        } catch (err: any) {
          setError(err.response?.data?.detail || "Something went wrong");
        }
      };

      const inputCls =
        "w-full rounded-lg border border-slate-300 px-3 py-2 text-slate-900 " +
        "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30";
      const btnCls =
        "w-full rounded-lg bg-brand-600 px-4 py-2 font-medium text-white " +
        "hover:bg-brand-700 transition disabled:opacity-50";

      return (
        <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
          <form
            onSubmit={submit}
            className="w-96 space-y-4 rounded-2xl bg-white p-8 shadow-xl"
          >
            <div className="text-center">
              <h1 className="text-2xl font-bold text-slate-800">
                {mode === "login" ? "Welcome back" : "Create account"}
              </h1>
              <p className="text-sm text-slate-500">
                {mode === "login" ? "Sign in to continue" : "Register a new account"}
              </p>
            </div>

            <input
              className={inputCls}
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            {mode === "register" && (
              <input
                className={inputCls}
                type="email"
                placeholder="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            )}

            <input
              className={inputCls}
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </div>
            )}

            <button className={btnCls} type="submit">
              {mode === "login" ? "Sign in" : "Create account"}
            </button>

            <button
              type="button"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
              className="w-full text-sm text-brand-600 hover:underline"
            >
              {mode === "login"
                ? "Don't have an account? Register"
                : "Already have an account? Sign in"}
            </button>
          </form>
        </div>
      );
    }
""")

TEMPLATES["frontend/src/ChatSidebar.tsx"] = _t("""
    import { useState } from "react";
    import { api } from "./api";
    import type { Chat, User } from "./types";

    export default function ChatSidebar({
      user, chats, activeChat, onSelect, onChatsChanged, onLogout
    }: {
      user: User;
      chats: Chat[];
      activeChat: number | null;
      onSelect: (id: number) => void;
      onChatsChanged: (chats: Chat[]) => void;
      onLogout: () => void;
    }) {
      const [showNew, setShowNew] = useState(false);
      const [newTitle, setNewTitle] = useState("");
      const [members, setMembers] = useState("");
      const [error, setError] = useState("");

      const createChat = async () => {
        setError("");
        try {
          const usernames = members
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean);
          const { data } = await api.post<Chat>("/chats", {
            title: newTitle || null,
            is_group: usernames.length > 1,
            member_usernames: usernames
          });
          const res = await api.get<Chat[]>("/chats");
          onChatsChanged(res.data);
          onSelect(data.id);
          setShowNew(false);
          setNewTitle("");
          setMembers("");
        } catch (err: any) {
          setError(err.response?.data?.detail || "Failed to create chat");
        }
      };

      return (
        <aside className="flex w-72 flex-col border-r border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 p-4">
            <div>
              <div className="font-semibold text-slate-800">{user.display_name || user.username}</div>
              <div className="text-xs text-slate-500">@{user.username}</div>
            </div>
            <button
              onClick={onLogout}
              className="rounded-lg border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
            >
              Logout
            </button>
          </div>

          <div className="p-3">
            <button
              onClick={() => setShowNew(!showNew)}
              className="w-full rounded-lg bg-brand-600 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              + New chat
            </button>
          </div>

          {showNew && (
            <div className="space-y-2 border-b border-slate-200 p-3">
              <input
                placeholder="Chat title (optional)"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              <input
                placeholder="Members: bob, carol"
                value={members}
                onChange={(e) => setMembers(e.target.value)}
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
              />
              {error && <div className="text-xs text-red-600">{error}</div>}
              <button
                onClick={createChat}
                className="w-full rounded-lg bg-brand-600 py-2 text-sm text-white hover:bg-brand-700"
              >
                Create
              </button>
            </div>
          )}

          <div className="flex-1 overflow-y-auto">
            {chats.length === 0 && (
              <div className="p-4 text-sm text-slate-400">No chats yet</div>
            )}
            {chats.map((c) => (
              <button
                key={c.id}
                onClick={() => onSelect(c.id)}
                className={
                  "block w-full border-b border-slate-100 px-4 py-3 text-left transition " +
                  (activeChat === c.id ? "bg-brand-50" : "hover:bg-slate-50")
                }
              >
                <div className="font-medium text-slate-800">
                  {c.title || `Chat #${c.id}`}
                </div>
                <div className="text-xs text-slate-500">
                  {c.is_group ? "Group" : "Direct"}
                </div>
              </button>
            ))}
          </div>
        </aside>
      );
    }
""")

TEMPLATES["frontend/src/ChatWindow.tsx"] = _t("""
    import { useEffect, useRef, useState } from "react";
    import { api, WS_BASE } from "./api";
    import type { Message, User } from "./types";

    export default function ChatWindow({
      chatId, currentUser
    }: {
      chatId: number;
      currentUser: User;
    }) {
      const [messages, setMessages] = useState<Message[]>([]);
      const [text, setText] = useState("");
      const wsRef = useRef<WebSocket | null>(null);
      const bottomRef = useRef<HTMLDivElement>(null);

      useEffect(() => {
        let cancelled = false;
        api.get<Message[]>(`/chats/${chatId}/messages`).then((res) => {
          if (!cancelled) setMessages(res.data);
        });

        const token = localStorage.getItem("access_token");
        if (!token) return;

        const ws = new WebSocket(`${WS_BASE}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({ type: "subscribe", chat_id: chatId }));
        };

        ws.onmessage = (e) => {
          try {
            const d = JSON.parse(e.data);
            if (d.type === "message" && d.chat_id === chatId) {
              setMessages((prev) => [
                ...prev,
                {
                  id: d.id,
                  chat_id: d.chat_id,
                  author_id: d.author_id,
                  author_username: d.author_username,
                  text: d.text,
                  created_at: d.created_at
                }
              ]);
            }
          } catch {}
        };

        return () => {
          cancelled = true;
          ws.close();
        };
      }, [chatId]);

      useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
      }, [messages]);

      const send = () => {
        const t = text.trim();
        if (!t || !wsRef.current) return;
        wsRef.current.send(
          JSON.stringify({ type: "send", chat_id: chatId, text: t })
        );
        setText("");
      };

      return (
        <div className="flex flex-1 flex-col bg-slate-50">
          <div className="border-b border-slate-200 bg-white px-6 py-4">
            <div className="font-semibold text-slate-800">Chat #{chatId}</div>
          </div>

          <div className="flex-1 space-y-2 overflow-y-auto px-6 py-4">
            {messages.map((m) => {
              const mine = m.author_id === currentUser.id;
              return (
                <div
                  key={m.id}
                  className={"flex " + (mine ? "justify-end" : "justify-start")}
                >
                  <div
                    className={
                      "max-w-md rounded-2xl px-4 py-2 shadow-sm " +
                      (mine
                        ? "bg-brand-600 text-white"
                        : "bg-white text-slate-800")
                    }
                  >
                    {!mine && (
                      <div className="mb-0.5 text-xs font-medium text-brand-600">
                        {m.author_username}
                      </div>
                    )}
                    <div className="whitespace-pre-wrap break-words">{m.text}</div>
                    <div className={"mt-1 text-[10px] " + (mine ? "text-white/70" : "text-slate-400")}>
                      {new Date(m.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              );
            })}
            <div ref={bottomRef} />
          </div>

          <div className="border-t border-slate-200 bg-white p-4">
            <div className="flex gap-2">
              <input
                className="flex-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/30"
                placeholder="Type a message..."
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
              />
              <button
                onClick={send}
                disabled={!text.trim()}
                className="rounded-lg bg-brand-600 px-5 py-2 font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                Send
              </button>
            </div>
          </div>
        </div>
      );
    }
""")

TEMPLATES["frontend/src/App.tsx"] = _t("""
    import { useEffect, useState } from "react";
    import Login from "./Login";
    import ChatSidebar from "./ChatSidebar";
    import ChatWindow from "./ChatWindow";
    import { api } from "./api";
    import type { Chat, User } from "./types";

    export default function App() {
      const [user, setUser] = useState<User | null>(null);
      const [chats, setChats] = useState<Chat[]>([]);
      const [activeChat, setActiveChat] = useState<number | null>(null);
      const [loading, setLoading] = useState(true);

      const loadMe = async () => {
        try {
          const me = await api.get<User>("/auth/me");
          setUser(me.data);
          const cs = await api.get<Chat[]>("/chats");
          setChats(cs.data);
        } catch {
          setUser(null);
          localStorage.removeItem("access_token");
        } finally {
          setLoading(false);
        }
      };

      useEffect(() => { loadMe(); }, []);

      const logout = () => {
        localStorage.removeItem("access_token");
        setUser(null);
        setChats([]);
        setActiveChat(null);
      };

      if (loading) {
        return (
          <div className="flex h-screen items-center justify-center bg-slate-100 text-slate-500">
            Loading...
          </div>
        );
      }

      if (!user) return <Login onLogin={loadMe} />;

      return (
        <div className="flex h-screen bg-slate-100">
          <ChatSidebar
            user={user}
            chats={chats}
            activeChat={activeChat}
            onSelect={setActiveChat}
            onChatsChanged={setChats}
            onLogout={logout}
          />
          {activeChat ? (
            <ChatWindow chatId={activeChat} currentUser={user} />
          ) : (
            <div className="flex flex-1 items-center justify-center text-slate-400">
              Select a chat or create a new one
            </div>
          )}
        </div>
      );
    }
""")

# ============================================================== INFRA
TEMPLATES["infra/docker-compose.yml"] = _t("""
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


def write_all(root: Path) -> tuple[int, int]:
    created = updated = 0
    for rel, content in TEMPLATES.items():
        target = root / rel
        existed = target.exists()
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if existed:
                print(f"  ~ {rel}")
                updated += 1
            else:
                print(f"  + {rel}")
                created += 1
        except OSError as e:
            print(f"ERR {rel}: {e}", file=sys.stderr)
    return created, updated


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".",
                   help="Папка, в которой лежит my-messenger")
    p.add_argument("--name", default=PROJECT_DEFAULT)
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено. Проверь --path и --name.", file=sys.stderr)
        return 1

    print(f"\nОбновляю проект: {root}\n")
    created, updated = write_all(root)
    print(f"\nГотово: {created} создано, {updated} обновлено\n")
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down -v")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())