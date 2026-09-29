#!/usr/bin/env python3
"""sprint9.py - message queue + file limits."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


T: dict[str, str] = {}

# ============================================================== ALEMBIC
T["backend/alembic/versions/0008_sprint9.py"] = _t('''
    """sprint 9: file usage quotas

    Revision ID: 0008
    Revises: 0007
    Create Date: 2025-08-01
    """
    from __future__ import annotations

    from typing import Sequence, Union

    from alembic import op
    import sqlalchemy as sa

    revision: str = "0008"
    down_revision: Union[str, None] = "0007"
    branch_labels: Union[str, Sequence[str], None] = None
    depends_on: Union[str, Sequence[str], None] = None


    def upgrade() -> None:
        op.create_table(
            "file_usage",
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("used_bytes", sa.BigInteger(), nullable=False, server_default="0"),
            sa.Column("files_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )


    def downgrade() -> None:
        op.drop_table("file_usage")
''')

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

        # Лимиты по категориям (в мегабайтах)
        MAX_IMAGE_MB: int = 15
        MAX_VIDEO_MB: int = 100
        MAX_AUDIO_MB: int = 25
        MAX_DOCUMENT_MB: int = 25
        MAX_ARCHIVE_MB: int = 50
        MAX_OTHER_MB: int = 10

        # Квота на пользователя
        USER_QUOTA_MB: int = 1024  # 1 GB

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
        "filetype==1.2.0"

    COPY . .

    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

# ============================================================== MODELS
T["backend/app/models.py"] = _t('''
    from __future__ import annotations

    from datetime import datetime
    from sqlalchemy import (
        BigInteger,
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

# ============================================================== FILE VALIDATION
T["backend/app/upload_guard.py"] = _t('''
    """Валидация загружаемых файлов: MIME по magic bytes, лимиты, квоты."""
    from __future__ import annotations

    import filetype as ftype
    from fastapi import HTTPException, status

    from app.config import settings

    # Категории по MIME
    IMAGE_PREFIXES = ("image/",)
    VIDEO_PREFIXES = ("video/",)
    AUDIO_PREFIXES = ("audio/",)
    DOCUMENT_PREFIXES = (
        "text/",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/rtf",
        "application/json",
        "application/xml",
    )
    ARCHIVE_PREFIXES = (
        "application/zip",
        "application/x-tar",
        "application/gzip",
        "application/x-7z-compressed",
        "application/x-rar",
        "application/x-bzip2",
        "application/x-xz",
    )

    # Запрещённые расширения (исполняемые, скрипты)
    FORBIDDEN_EXTS = {
        ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".com",
        ".scr", ".msi", ".sh", ".ps1", ".vbs", ".jar", ".app",
        ".deb", ".rpm", ".apk", ".dmg", ".bin",
    }


    def _categorize(mime: str) -> str:
        if any(mime.startswith(p) for p in IMAGE_PREFIXES):
            return "image"
        if any(mime.startswith(p) for p in VIDEO_PREFIXES):
            return "video"
        if any(mime.startswith(p) for p in AUDIO_PREFIXES):
            return "audio"
        if any(mime.startswith(p) for p in ARCHIVE_PREFIXES):
            return "archive"
        if any(mime.startswith(p) for p in DOCUMENT_PREFIXES):
            return "document"
        return "other"


    def _limit_bytes(category: str) -> int:
        mapping = {
            "image": settings.MAX_IMAGE_MB,
            "video": settings.MAX_VIDEO_MB,
            "audio": settings.MAX_AUDIO_MB,
            "document": settings.MAX_DOCUMENT_MB,
            "archive": settings.MAX_ARCHIVE_MB,
            "other": settings.MAX_OTHER_MB,
        }
        return mapping.get(category, settings.MAX_OTHER_MB) * 1024 * 1024


    def _ext_of(filename: str) -> str:
        if "." not in filename:
            return ""
        return "." + filename.rsplit(".", 1)[-1].lower()


    def validate_file(content: bytes, filename: str, declared_mime: str | None) -> tuple[str, str]:
        """
        Проверяет содержимое и возвращает (mime, category).

        Бросает HTTPException при нарушении.
        """
        ext = _ext_of(filename)
        if ext in FORBIDDEN_EXTS:
            raise HTTPException(
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                f"Запрещённый тип файла: {ext}",
            )

        # Определяем MIME по содержимому (первые 512 байт достаточно)
        kind = ftype.guess(content[:8192])
        if kind is not None:
            mime = kind.mime
        else:
            # откатываемся к объявленному клиентом (для текстов и прочего)
            mime = (declared_mime or "application/octet-stream").split(";")[0].strip()

        category = _categorize(mime)
        limit = _limit_bytes(category)
        size = len(content)

        if size > limit:
            limit_mb = limit // (1024 * 1024)
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"Файл слишком большой для категории «{category}». "
                f"Максимум {limit_mb} МБ, получено {size / (1024 * 1024):.2f} МБ.",
            )

        return mime, category


    def quota_bytes() -> int:
        return settings.USER_QUOTA_MB * 1024 * 1024
''')

# ============================================================== FILES ROUTER
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
    from app.models import File as FileModel, FileUsage
    from app.schemas import FileRead, StorageUsage
    from app.security import decode_token
    from app.upload_guard import quota_bytes, validate_file


    router = APIRouter()


    async def _get_or_create_usage(db: AsyncSession, user_id: int) -> FileUsage:
        usage = (await db.execute(
            select(FileUsage).where(FileUsage.user_id == user_id)
        )).scalar_one_or_none()
        if usage is None:
            usage = FileUsage(user_id=user_id, used_bytes=0, files_count=0)
            db.add(usage)
            await db.flush()
        return usage


    @router.get("/usage", response_model=StorageUsage)
    async def get_usage(current: CurrentUser, db: AsyncSession = Depends(get_session)):
        usage = await _get_or_create_usage(db, current.id)
        quota = quota_bytes()
        return StorageUsage(
            used_bytes=usage.used_bytes,
            quota_bytes=quota,
            files_count=usage.files_count,
            percent=round(min(100.0, usage.used_bytes / quota * 100), 1) if quota else 0,
        )


    @router.post("/upload", response_model=FileRead, status_code=status.HTTP_201_CREATED)
    async def upload(
        current: CurrentUser,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_session),
    ) -> FileRead:
        if not file.filename:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "no filename")

        # Читаем содержимое целиком (лимиты уже жёсткие, максимум 100 МБ)
        body = await file.read()

        # Валидация: magic bytes, категория, размер
        detected_mime, category = validate_file(
            body, file.filename, file.content_type,
        )

        # Проверка квоты пользователя
        usage = await _get_or_create_usage(db, current.id)
        quota = quota_bytes()
        if usage.used_bytes + len(body) > quota:
            free_mb = (quota - usage.used_bytes) / (1024 * 1024)
            raise HTTPException(
                status.HTTP_507_INSUFFICIENT_STORAGE,
                f"Квота исчерпана. Свободно {free_mb:.1f} МБ из "
                f"{quota // (1024 * 1024)} МБ.",
            )

        # Сохраняем на диск
        ext = Path(file.filename).suffix[:16]
        storage_name = f"{uuid.uuid4().hex}{ext}"
        target = settings.upload_path / storage_name
        target.write_bytes(body)

        obj = FileModel(
            owner_id=current.id,
            filename=file.filename,
            content_type=detected_mime,
            size=len(body),
            storage_name=storage_name,
        )
        db.add(obj)
        await db.flush()

        # Обновляем квоту
        usage.used_bytes += len(body)
        usage.files_count += 1
        await db.flush()
        await db.refresh(obj)

        return FileRead.model_validate(obj)


    @router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_file(
        file_id: int,
        current: CurrentUser,
        db: AsyncSession = Depends(get_session),
    ):
        obj = (await db.execute(
            select(FileModel).where(FileModel.id == file_id)
        )).scalar_one_or_none()
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")
        if obj.owner_id != current.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "not your file")

        # Удаляем с диска
        path = settings.upload_path / obj.storage_name
        if path.exists():
            path.unlink(missing_ok=True)

        # Уменьшаем квоту
        usage = await _get_or_create_usage(db, current.id)
        usage.used_bytes = max(0, usage.used_bytes - obj.size)
        usage.files_count = max(0, usage.files_count - 1)

        await db.delete(obj)
        await db.flush()


    @router.get("/{file_id}")
    async def download(
        file_id: int,
        token: str = Query(...),
        db: AsyncSession = Depends(get_session),
    ):
        try:
            decode_token(token)
        except ValueError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

        obj = (await db.execute(
            select(FileModel).where(FileModel.id == file_id)
        )).scalar_one_or_none()
        if obj is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "file not found")

        path = settings.upload_path / obj.storage_name
        if not path.exists():
            raise HTTPException(status.HTTP_410_GONE, "file missing on disk")

        inline = obj.content_type.startswith(("image/", "audio/", "video/"))
        return FileResponse(
            path,
            media_type=obj.content_type,
            filename=obj.filename,
            content_disposition_type="inline" if inline else "attachment",
        )
''')

# ============================================================== SCHEMAS — добавить StorageUsage
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

# ============================================================== WS — вернуть client_id
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
                    client_id = data.get("client_id")  # <- для сопоставления с очередью
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
                                "type": "error",
                                "client_id": client_id,
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
                            "client_id": client_id,  # <- возвращаем
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

# ============================================================== MAIN — подключить files
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

    export type ThemeName = "cyber" | "matrix" | "sunset" | "amber";
''')

# ============================================================== MESSAGE QUEUE HOOK
T["frontend/src/useMessageQueue.ts"] = _t('''
    import { useCallback, useEffect, useRef, useState } from "react";

    const STORAGE_KEY = "msg_queue_v1";
    const MAX_ATTEMPTS = 5;

    export interface QueuedMessage {
      client_id: string;
      chat_id: number;
      text: string | null;
      message_type: string;
      attachment_id: number | null;
      reply_to_id: number | null;
      created_at: string;
      attempts: number;
      next_try_at: number;
      status: "pending" | "failed";
      author_id: number;
      author_username: string;
      author_display: string | null;
      author_avatar_color: string | null;
    }

    function loadQueue(userId: number): QueuedMessage[] {
      try {
        const raw = localStorage.getItem(`${STORAGE_KEY}:${userId}`);
        return raw ? (JSON.parse(raw) as QueuedMessage[]) : [];
      } catch {
        return [];
      }
    }

    function saveQueue(userId: number, queue: QueuedMessage[]) {
      try {
        localStorage.setItem(`${STORAGE_KEY}:${userId}`, JSON.stringify(queue));
      } catch {}
    }

    function uuid(): string {
      if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
        return crypto.randomUUID();
      }
      return Math.random().toString(36).slice(2) + Date.now().toString(36);
    }

    export function useMessageQueue(
      userId: number | null,
      wsSend: (data: any) => void,
      isWsOpen: () => boolean,
    ) {
      const [queue, setQueue] = useState<QueuedMessage[]>([]);
      const queueRef = useRef<QueuedMessage[]>([]);
      const timerRef = useRef<number | null>(null);

      // load on login
      useEffect(() => {
        if (userId == null) {
          setQueue([]);
          queueRef.current = [];
          return;
        }
        const loaded = loadQueue(userId);
        setQueue(loaded);
        queueRef.current = loaded;
      }, [userId]);

      // persist on change
      useEffect(() => {
        if (userId == null) return;
        saveQueue(userId, queue);
        queueRef.current = queue;
      }, [queue, userId]);

      const trySend = useCallback((msg: QueuedMessage) => {
        if (!isWsOpen()) return false;
        try {
          wsSend({
            type: "send",
            client_id: msg.client_id,
            chat_id: msg.chat_id,
            text: msg.text,
            message_type: msg.message_type,
            attachment_id: msg.attachment_id,
            reply_to_id: msg.reply_to_id,
          });
          return true;
        } catch {
          return false;
        }
      }, [wsSend, isWsOpen]);

      // flush: try all pending messages whose next_try_at <= now
      const flush = useCallback(() => {
        const now = Date.now();
        setQueue((prev) => {
          const remaining: QueuedMessage[] = [];
          for (const m of prev) {
            if (m.status === "failed" && m.attempts >= MAX_ATTEMPTS) {
              remaining.push(m);
              continue;
            }
            if (m.next_try_at > now) {
              remaining.push(m);
              continue;
            }
            const ok = trySend(m);
            if (ok) {
              // отправили, пометим — но НЕ удаляем пока не придёт подтверждение
              // Просто обнулим next_try_at, чтобы не отправлять повторно часто
              remaining.push({ ...m, next_try_at: now + 30_000, attempts: m.attempts + 1 });
            } else {
              const attempts = m.attempts + 1;
              const backoff = Math.min(30_000, 1000 * Math.pow(2, attempts));
              remaining.push({
                ...m,
                attempts,
                next_try_at: now + backoff,
                status: attempts >= MAX_ATTEMPTS ? "failed" : "pending",
              });
            }
          }
          return remaining;
        });
      }, [trySend]);

      // tick every 2 seconds
      useEffect(() => {
        if (userId == null) return;
        const t = window.setInterval(() => {
          if (queueRef.current.length > 0) flush();
        }, 2000);
        return () => window.clearInterval(t);
      }, [userId, flush]);

      const enqueue = useCallback((
        chatId: number,
        text: string | null,
        messageType: string,
        attachmentId: number | null,
        replyToId: number | null,
        author: { id: number; username: string; display_name: string | null; avatar_color: string | null },
      ): QueuedMessage => {
        const msg: QueuedMessage = {
          client_id: uuid(),
          chat_id: chatId,
          text,
          message_type: messageType,
          attachment_id: attachmentId,
          reply_to_id: replyToId,
          created_at: new Date().toISOString(),
          attempts: 0,
          next_try_at: 0,
          status: "pending",
          author_id: author.id,
          author_username: author.username,
          author_display: author.display_name,
          author_avatar_color: author.avatar_color,
        };
        setQueue((prev) => [...prev, msg]);
        // сразу попытаемся отправить
        setTimeout(() => trySend(msg), 0);
        return msg;
      }, [trySend]);

      const removeByClientId = useCallback((clientId: string) => {
        setQueue((prev) => prev.filter((m) => m.client_id !== clientId));
      }, []);

      const retryFailed = useCallback(() => {
        setQueue((prev) => prev.map((m) =>
          m.status === "failed"
            ? { ...m, status: "pending", attempts: 0, next_try_at: 0 }
            : m
        ));
      }, []);

      const clearFailed = useCallback(() => {
        setQueue((prev) => prev.filter((m) => m.status !== "failed"));
      }, []);

      return {
        queue,
        enqueue,
        removeByClientId,
        retryFailed,
        clearFailed,
      };
    }
''')

# ============================================================== FILE LIMITS (client-side)
T["frontend/src/fileLimits.ts"] = _t('''
    // Клиентские лимиты (должны совпадать с серверными)
    const LIMITS_MB: Record<string, number> = {
      image: 15,
      video: 100,
      audio: 25,
      document: 25,
      archive: 50,
      other: 10,
    };

    const FORBIDDEN_EXTS = new Set([
      ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".com",
      ".scr", ".msi", ".sh", ".ps1", ".vbs", ".jar", ".app",
      ".deb", ".rpm", ".apk", ".dmg", ".bin",
    ]);

    export function extOf(name: string): string {
      const i = name.lastIndexOf(".");
      return i < 0 ? "" : name.slice(i).toLowerCase();
    }

    export function categoryOf(file: File): string {
      const t = file.type || "";
      if (t.startsWith("image/")) return "image";
      if (t.startsWith("video/")) return "video";
      if (t.startsWith("audio/")) return "audio";
      const ext = extOf(file.name);
      if ([".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz"].includes(ext)) return "archive";
      if ([".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md", ".csv"].includes(ext)) return "document";
      return "other";
    }

    export function limitBytes(file: File): number {
      const cat = categoryOf(file);
      return (LIMITS_MB[cat] ?? LIMITS_MB.other) * 1024 * 1024;
    }

    export function checkFile(file: File): string | null {
      const ext = extOf(file.name);
      if (FORBIDDEN_EXTS.has(ext)) {
        return `Файлы типа ${ext} загружать нельзя`;
      }
      const limit = limitBytes(file);
      if (file.size > limit) {
        const mb = (limit / (1024 * 1024)).toFixed(0);
        const size = (file.size / (1024 * 1024)).toFixed(2);
        return `Файл слишком большой (${size} МБ). Максимум ${mb} МБ`;
      }
      return null;
    }

    // Сжатие изображений через canvas
    export async function compressImage(
      file: File,
      maxDim = 1920,
      quality = 0.85,
    ): Promise<File> {
      if (!file.type.startsWith("image/")) return file;
      // GIF/SVG не трогаем
      if (file.type === "image/gif" || file.type === "image/svg+xml") return file;

      try {
        const bitmap = await createImageBitmap(file);
        let { width, height } = bitmap;
        const scale = Math.min(1, maxDim / Math.max(width, height));
        width = Math.round(width * scale);
        height = Math.round(height * scale);

        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext("2d");
        if (!ctx) return file;
        ctx.drawImage(bitmap, 0, 0, width, height);

        const blob: Blob | null = await new Promise((res) =>
          canvas.toBlob(res, "image/webp", quality)
        );
        if (!blob) return file;

        const name = file.name.replace(/\.[^.]+$/, "") + ".webp";
        const compressed = new File([blob], name, { type: "image/webp" });
        // Если сжатие не помогло — оставляем оригинал
        return compressed.size < file.size ? compressed : file;
      } catch {
        return file;
      }
    }
''')

# ============================================================== API — upload progress
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

# ============================================================== FILE UPLOAD WIDGET
T["frontend/src/FileUpload.tsx"] = _t('''
    import { useRef, useState } from "react";
    import { humanSize, uploadFile } from "./api";
    import { checkFile, compressImage } from "./fileLimits";
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
      const [progress, setProgress] = useState(0);
      const [error, setError] = useState("");
      const abortRef = useRef<AbortController | null>(null);

      const pick = () => {
        setError("");
        ref.current?.click();
      };

      const onChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const raw = e.target.files?.[0];
        if (!raw) return;

        setBusy(true);
        setProgress(0);
        setError("");

        try {
          // сжимаем картинки
          let file = raw;
          if (asType === "image" && raw.type.startsWith("image/")) {
            file = await compressImage(raw);
          }

          // проверка лимитов
          const err = checkFile(file);
          if (err) {
            setError(err);
            setBusy(false);
            if (ref.current) ref.current.value = "";
            return;
          }

          const ctrl = new AbortController();
          abortRef.current = ctrl;

          const data = await uploadFile(file, {
            onProgress: setProgress,
            signal: ctrl.signal,
          });

          const type = asType === "image" && data.content_type.startsWith("image/")
            ? "image"
            : "file";
          onUploaded(data, type);
        } catch (err: any) {
          if (err.name === "CanceledError" || err.code === "ERR_CANCELED") {
            // отмена — ничего не делаем
          } else {
            setError(err.response?.data?.detail || "Не удалось загрузить файл");
          }
        } finally {
          setBusy(false);
          abortRef.current = null;
          if (ref.current) ref.current.value = "";
        }
      };

      const cancel = () => {
        abortRef.current?.abort();
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
          {busy ? (
            <div className="relative flex items-center gap-2 rounded-sm border border-cyber-cyan/40 bg-cyber-cyan/10 px-2 py-1 text-xs">
              <div className="relative h-1 w-16 overflow-hidden rounded-full bg-cyber-cyan/20">
                <div
                  className="absolute left-0 top-0 h-full bg-cyber-cyan transition-all"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-[9px] font-bold neon-text">{progress}%</span>
              <button
                onClick={cancel}
                className="text-[9px] uppercase tracking-widest neon-text-mag hover:underline"
                title="Отменить"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              onClick={pick}
              title={asType === "image" ? "Прикрепить фото" : "Прикрепить файл"}
              className="rounded-sm p-2 text-lg text-cyber-cyan transition hover:bg-cyber-cyan/10"
            >
              {asType === "image" ? "▣" : "▤"}
            </button>
          )}
          {error && (
            <div className="absolute bottom-full mb-1 left-0 whitespace-nowrap rounded-sm border border-cyber-magenta/50 bg-cyber-panel px-2 py-1 text-[10px] neon-text-mag">
              ⚠ {error}
            </div>
          )}
        </>
      );
    }
''')

# ============================================================== CHAT WINDOW — интеграция очереди
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

    export interface QueuedLike {
      client_id: string;
      chat_id: number;
      text: string | null;
      message_type: string;
      attachment_id: number | null;
      reply_to_id: number | null;
      created_at: string;
      attempts: number;
      status: "pending" | "failed";
      author_id: number;
      author_username: string;
      author_display: string | null;
      author_avatar_color: string | null;
    }

    function dayLabel(iso: string) {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) return "▸ TODAY";
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "▸ YESTERDAY";
      return "▸ " + d.toLocaleDateString([], { day: "numeric", month: "long" }).toUpperCase();
    }

    export default function ChatWindow({
      chat, currentUser, send, subscribe, onlineUsers, onOpenInfo, onOpenUser, onStartCall,
      queuedMessages, onEnqueue, onRemoveQueued,
    }: {
      chat: Chat;
      currentUser: User;
      send: (data: any) => void;
      subscribe: (h: (d: any) => void) => () => void;
      onlineUsers: Set<number>;
      onOpenInfo: () => void;
      onOpenUser: (userId: number) => void;
      onStartCall: (kind: "audio" | "video") => void;
      queuedMessages: QueuedLike[];
      onEnqueue: (
        chatId: number, text: string | null, messageType: string,
        attachmentId: number | null, replyToId: number | null,
      ) => void;
      onRemoveQueued: (clientId: string) => void;
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

      // моя очередь для этого чата
      const myQueue = useMemo(
        () => queuedMessages.filter((m) => m.chat_id === chat.id),
        [queuedMessages, chat.id],
      );

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
      }, [messages.length, myQueue.length]);

      useEffect(() => {
        const last = messages[messages.length - 1];
        if (!last) return;
        if (last.author_id !== currentUser.id && last.message_type !== "system") {
          send({ type: "read", chat_id: chat.id, message_id: last.id });
        }
      }, [messages.length]);

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
            // пришло подтверждение для сообщения из очереди — уберём из очереди
            if (d.client_id && d.author_id === currentUser.id) {
              onRemoveQueued(d.client_id);
            }
            setMessages((prev) => {
              // не дублируем: если уже есть с этим id
              if (prev.some((m) => m.id === d.id)) return prev;
              // если это наш ответ — заменим pending-сообщение
              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                client_id: d.client_id || null,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, is_pinned: false,
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
      }, [chat.id, currentUser.id, subscribe, send, onRemoveQueued]);

      // Все "виртуальные" сообщения = серверные + очередь
      const allMessages: Message[] = useMemo(() => {
        const virtual: Message[] = myQueue.map((m) => ({
          id: -1 - Math.random(),
          client_id: m.client_id,
          chat_id: m.chat_id,
          author_id: m.author_id,
          author_username: m.author_username,
          author_display: m.author_display,
          author_avatar_color: m.author_avatar_color,
          text: m.text,
          message_type: m.message_type as any,
          attachment: null,
          reply_to_id: m.reply_to_id,
          reply_preview: null,
          reply_author: null,
          edited_at: null,
          is_deleted: false,
          is_pinned: false,
          reactions: [],
          created_at: m.created_at,
          send_status: m.status === "failed" ? "failed" : "pending",
        }));
        const out = [...messages];
        for (const v of virtual) {
          // пропустить, если сервер уже прислал с тем же client_id
          if (out.some((m) => m.client_id === v.client_id)) continue;
          out.push(v);
        }
        return out.sort((a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        );
      }, [messages, myQueue]);

      const grouped = useMemo(() => {
        const out: { day: string; items: Message[] }[] = [];
        for (const m of allMessages) {
          const day = dayLabel(m.created_at);
          const last = out[out.length - 1];
          if (last && last.day === day) last.items.push(m);
          else out.push({ day, items: [m] });
        }
        return out;
      }, [allMessages]);

      const doSend = () => {
        const t = text.trim();
        if (!t) return;
        if (editing) {
          send({ type: "edit", message_id: editing.id, text: t });
          setEditing(null);
        } else {
          onEnqueue(chat.id, t, "text", null, replyTo?.id ?? null);
          setReplyTo(null);
        }
        setText("");
        send({ type: "typing", chat_id: chat.id, is_typing: false });
      };

      const sendAttachment = (attachmentId: number, type: "image" | "file" | "voice") => {
        onEnqueue(chat.id, null, type, attachmentId, replyTo?.id ?? null);
        setReplyTo(null);
      };

      const sendSticker = (sticker: string) => {
        onEnqueue(chat.id, sticker, "sticker", null, replyTo?.id ?? null);
        setStickerOpen(false);
        setReplyTo(null);
      };

      const handleReact = (messageId: number, emoji: string) => {
        if (messageId < 0) return; // нельзя реагировать на pending
        send({ type: "reaction", message_id: messageId, emoji });
      };

      const handlePin = async (m: Message) => {
        if (m.id < 0) return;
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
      const failedCount = myQueue.filter((m) => m.status === "failed").length;

      return (
        <main className="relative z-10 flex flex-1 flex-col">
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

          {failedCount > 0 && (
            <div className="flex items-center gap-2 border-b border-cyber-magenta/30 bg-cyber-magenta/5 px-4 py-1.5 text-xs">
              <span className="neon-text-mag">⚠</span>
              <span className="flex-1 text-cyber-text">
                {failedCount} сообщ. не удалось отправить
              </span>
            </div>
          )}

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
                        key={m.client_id || m.id}
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

# ============================================================== MESSAGE BUBBLE — статус отправки
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

      const sendStatus = msg.send_status;
      const isPending = sendStatus === "pending";
      const isFailed = sendStatus === "failed";
      const isVirtual = msg.id < 0;

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

      const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";
      const bubbleStyle = {
        background: isFailed
          ? "linear-gradient(135deg, rgba(255,45,85,0.08), rgba(255,45,85,0.02))"
          : mine
          ? "linear-gradient(135deg, rgba(0,240,255,0.08), rgba(0,240,255,0.02))"
          : "linear-gradient(135deg, rgba(255,0,160,0.06), rgba(255,0,160,0.01))",
        border: `1px solid ${accent}55`,
        boxShadow: `0 0 12px ${accent}22, inset 0 0 12px ${accent}08`,
        color: "#d6ecff",
        opacity: isPending ? 0.75 : 1,
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
              <div className={"animate-materialize text-7xl leading-none " + (isPending ? "opacity-70" : "drop-shadow-[0_0_20px_rgba(0,240,255,0.5)]")}>
                {msg.text}
              </div>
              <div className={"mt-1 flex items-center gap-2 text-[9px] uppercase tracking-wider " + (mine ? "justify-end" : "")}>
                <span className="text-cyber-dim">
                  {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {mine && (
                  <span className={isPending ? "text-cyber-dim" : isFailed ? "neon-text-mag" : readByPeer ? "neon-text" : "text-cyber-dim"}>
                    {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
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
                  onClick={() => !isVirtual && onOpenImage(fileUrl(msg.attachment!.id))}
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
                  <span className={
                    isPending ? "text-cyber-dim" :
                    isFailed ? "neon-text-mag animate-pulse" :
                    readByPeer ? "neon-text" : "text-cyber-dim"
                  }>
                    {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
                  </span>
                )}
              </div>
            </div>

            {!msg.is_deleted && !isVirtual && (
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

# ============================================================== APP — подключить очередь
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

      const { send, subscribe, readyState } = useWebSocket(onWs);
      const rtc = useWebRTC(send, subscribe);

      const isWsOpen = useCallback(() => readyState === WebSocket.OPEN, [readyState]);

      // очередь сообщений
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

# ============================================================== WS HOOK — expose readyState
T["frontend/src/ws.ts"] = _t('''
    import { useEffect, useRef, useState, useCallback } from "react";
    import { WS_BASE } from "./api";

    type Handler = (data: any) => void;

    export function useWebSocket(onMessage: Handler) {
      const wsRef = useRef<WebSocket | null>(null);
      const handlersRef = useRef<Set<Handler>>(new Set());
      const [readyState, setReadyState] = useState<number>(WebSocket.CLOSED);
      const reconnectRef = useRef<number | null>(null);

      const onMessageRef = useRef(onMessage);
      useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);

      const connect = useCallback(() => {
        const token = localStorage.getItem("access_token");
        if (!token) return;
        const ws = new WebSocket(`${WS_BASE}?token=${token}`);
        wsRef.current = ws;

        ws.onopen = () => setReadyState(WebSocket.OPEN);
        ws.onclose = () => {
          setReadyState(WebSocket.CLOSED);
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
          return true;
        }
        return false;
      }, []);

      const subscribe = useCallback((h: Handler) => {
        handlersRef.current.add(h);
        return () => handlersRef.current.delete(h);
      }, []);

      return { send, subscribe, connected: readyState === WebSocket.OPEN, readyState };
    }
''')

# ============================================================== CHAT LIST — бейдж с ошибками очереди
T["frontend/src/ChatList.tsx"] = _t('''
    import { useMemo, useState } from "react";
    import Avatar from "./Avatar";
    import type { Chat, User } from "./types";

    function fmtTime(iso: string | null | undefined) {
      if (!iso) return "--:--";
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString())
        return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const y = new Date(now); y.setDate(now.getDate() - 1);
      if (d.toDateString() === y.toDateString()) return "YESTERDAY";
      return d.toLocaleDateString([], { day: "2-digit", month: "2-digit" });
    }

    function chatTitle(c: Chat) {
      if (c.peer) return c.peer.display_name || c.peer.username;
      return c.title || `NODE #${c.id}`;
    }

    function chatSubtitle(c: Chat) {
      const lm = c.last_message;
      if (!lm) return "// no transmission";
      if (lm.message_type === "system") return lm.text || "";
      const who = c.is_group ? `${lm.author_display || lm.author_username}: ` : "";
      let body = lm.text || "";
      if (lm.message_type === "image") body = "▣ IMAGE DATA";
      else if (lm.message_type === "voice") body = "◍ AUDIO SIGNAL";
      else if (lm.message_type === "file") body = `▤ ${lm.attachment?.filename || "FILE"}`;
      else if (lm.message_type === "sticker") body = lm.text || "◈ SIGIL";
      return "> " + who + body;
    }

    export default function ChatList({
      chats, activeId, onSelect, onlineUsers, currentUser, onOpenProfile, onOpenSettings,
      onOpenFeed, onOpenMyProfile, mode, failedQueue,
    }: {
      chats: Chat[];
      activeId: number | null;
      onSelect: (id: number) => void;
      onlineUsers: Set<number>;
      currentUser: User;
      onOpenProfile: () => void;
      onOpenSettings: () => void;
      onOpenFeed: () => void;
      onOpenMyProfile: () => void;
      mode: "chats" | "feed" | "profile";
      failedQueue?: number;
    }) {
      const [query, setQuery] = useState("");

      const filtered = useMemo(() => {
        const q = query.trim().toLowerCase();
        if (!q) return chats;
        return chats.filter((c) =>
          chatTitle(c).toLowerCase().includes(q) ||
          chatSubtitle(c).toLowerCase().includes(q)
        );
      }, [chats, query]);

      const unreadTotal = chats.reduce((s, c) => s + c.unread_count, 0);

      return (
        <aside className="relative z-10 flex w-80 shrink-0 flex-col border-r border-cyber-cyan/20 bg-cyber-panel/60 backdrop-blur-sm">
          <div className="border-b border-cyber-cyan/20 p-3">
            <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-widest text-cyber-dim">
              <span>// operator</span>
              <span className="flex items-center gap-1">
                <span className="status-dot" style={{ color: "#00ff88" }} />
                online
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={onOpenProfile} className="transition hover:opacity-80">
                <Avatar user={currentUser} size={44} />
              </button>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold neon-text">
                  {currentUser.display_name || currentUser.username}
                </div>
                <div className="truncate text-[10px] text-cyber-dim">
                  @{currentUser.username}
                </div>
              </div>
              <button
                onClick={onOpenSettings}
                title="Settings"
                className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-cyber-cyan transition hover:bg-cyber-cyan/10 hover:shadow-neon-cyan"
              >
                ⚙
              </button>
            </div>
          </div>

          <div className="border-b border-cyber-cyan/10 p-3">
            <div className="relative">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-cyber-cyan/60 text-xs">
                ▸
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="SEARCH CHANNELS"
                className="cyber-input w-full rounded-sm py-2 pl-6 pr-3 text-xs uppercase tracking-wider"
              />
            </div>
          </div>

          {(failedQueue ?? 0) > 0 && (
            <div className="border-b border-cyber-magenta/30 bg-cyber-magenta/10 px-3 py-2 text-[10px] uppercase tracking-widest neon-text-mag">
              ⚠ {failedQueue} failed in queue
            </div>
          )}

          <div className="flex border-b border-cyber-cyan/20">
            <button
              onClick={onOpenFeed}
              className={
                "flex-1 py-2 text-[10px] font-bold uppercase tracking-widest transition " +
                (mode === "feed"
                  ? "bg-cyber-cyan/15 neon-text border-b-2 border-cyber-cyan"
                  : "text-cyber-dim hover:bg-cyber-cyan/5 hover:text-cyber-cyan")
              }
            >
              ◉ feed
            </button>
            <button
              onClick={onOpenMyProfile}
              className={
                "flex-1 py-2 text-[10px] font-bold uppercase tracking-widest transition " +
                (mode === "profile"
                  ? "bg-cyber-cyan/15 neon-text border-b-2 border-cyber-cyan"
                  : "text-cyber-dim hover:bg-cyber-cyan/5 hover:text-cyber-cyan")
              }
            >
              ◉ profile
            </button>
          </div>

          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-6 text-center text-[10px] uppercase tracking-widest text-cyber-dim">
                // no channels found
              </div>
            ) : (
              filtered.map((c) => {
                const active = c.id === activeId && mode === "chats";
                const peerOnline = c.peer ? onlineUsers.has(c.peer.id) : false;
                const avatarUser = c.peer || {
                  username: c.title || "G",
                  display_name: c.title || "GRP",
                  avatar_color: c.avatar_color || "#ff00a0",
                };
                const hasUnread = c.unread_count > 0 && !active;

                return (
                  <button
                    key={c.id}
                    onClick={() => onSelect(c.id)}
                    className={
                      "group relative flex w-full items-center gap-3 border-b border-cyber-cyan/10 px-3 py-3 text-left transition " +
                      (active
                        ? "bg-cyber-cyan/10 border-l-2 border-l-cyber-cyan"
                        : "hover:bg-cyber-cyan/5 border-l-2 border-l-transparent")
                    }
                  >
                    <Avatar
                      user={avatarUser as any}
                      size={44}
                      showOnline={!!c.peer}
                      online={peerOnline}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline justify-between gap-2">
                        <span
                          className={
                            "truncate text-sm font-bold " +
                            (active ? "neon-text" : "text-cyber-text group-hover:neon-text")
                          }
                        >
                          {chatTitle(c)}
                        </span>
                        <span className="shrink-0 text-[9px] uppercase tracking-wider text-cyber-dim">
                          {fmtTime(c.last_message?.created_at || c.created_at)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={
                            "truncate text-[11px] " +
                            (active ? "text-cyber-cyan/80" : "text-cyber-dim")
                          }
                        >
                          {chatSubtitle(c)}
                        </span>
                        {hasUnread && (
                          <span className="neon-border-mag shrink-0 rounded-sm px-1.5 py-0.5 text-[9px] font-bold neon-text-mag pulse-glow-mag">
                            {c.unread_count}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>

          <div className="border-t border-cyber-cyan/20 p-2 text-[9px] uppercase tracking-widest text-cyber-dim">
            <div className="flex items-center justify-between">
              <span>channels: {chats.length}</span>
              {unreadTotal > 0 && (
                <span className="neon-text-mag">unread: {unreadTotal}</span>
              )}
            </div>
          </div>
        </aside>
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

    print("\nСпринт 9: очередь сообщений + лимиты файлов")
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