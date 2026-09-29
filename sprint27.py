#!/usr/bin/env python3
"""sprint27.py - S3-compatible storage for files."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================== config.py
CONFIG = r'''from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=True)

    APP_NAME: str = "Messenger"
    ENV: str = "development"
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

    # ---- S3 ----
    S3_ENABLED: bool = True
    S3_ENDPOINT: str = "https://storage.yandexcloud.net"
    S3_REGION: str = "ru-central1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "messenger"
    S3_PUBLIC_URL: str = ""           # если CDN, иначе пусто
    S3_PRESIGN_EXPIRE: int = 3600

    MAX_IMAGE_MB: int = 15
    MAX_VIDEO_MB: int = 100
    MAX_AUDIO_MB: int = 25
    MAX_DOCUMENT_MB: int = 25
    MAX_ARCHIVE_MB: int = 50
    MAX_OTHER_MB: int = 10
    USER_QUOTA_MB: int = 1024

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
'''


# ============================================================== utils/s3.py
S3_UTIL = r'''"""S3-compatible storage helper."""
from __future__ import annotations

import logging
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings

log = logging.getLogger("s3")

_client = None


def client():
    global _client
    if _client is None:
        if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
            raise RuntimeError("S3_ACCESS_KEY / S3_SECRET_KEY не заданы в .env")
        _client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},  # совместимо с Yandex/VK/MinIO
            ),
        )
    return _client


def ensure_bucket() -> None:
    """Создаёт бакет если его нет."""
    try:
        c = client()
        c.head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchBucket"):
            try:
                c.create_bucket(Bucket=settings.S3_BUCKET)
                log.info("s3_bucket_created", bucket=settings.S3_BUCKET)
            except Exception as e2:
                log.warning("s3_create_bucket_failed", error=str(e2))
        elif code == "403":
            # бакет есть, но нет прав на head — считаем ОК
            pass
        else:
            log.warning("s3_head_bucket_failed", error=str(e))
    except Exception as e:
        log.warning("s3_ensure_bucket_failed", error=str(e))


def put_object(key: str, body: bytes, content_type: str) -> None:
    client().put_object(
        Bucket=settings.S3_BUCKET,
        Key=key,
        Body=body,
        ContentType=content_type,
    )


def delete_object(key: str) -> None:
    try:
        client().delete_object(Bucket=settings.S3_BUCKET, Key=key)
    except Exception as e:
        log.warning("s3_delete_failed", key=key, error=str(e))


def presigned_url(key: str, expires: int | None = None) -> str:
    """Возвращает подписанный URL для скачивания."""
    ttl = expires or settings.S3_PRESIGN_EXPIRE
    return client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=ttl,
    )


def get_object_bytes(key: str) -> bytes:
    """Читает объект в память (для маленьких файлов)."""
    obj = client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    return obj["Body"].read()


def object_exists(key: str) -> bool:
    try:
        client().head_object(Bucket=settings.S3_BUCKET, Key=key)
        return True
    except ClientError:
        return False
    except Exception:
        return False
'''


# ============================================================== routers/files.py
FILES_ROUTER = r'''from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.deps import CurrentUser
from app.logging_config import get_logger
from app.models import File as FileModel, FileUsage
from app.schemas import FileRead, StorageUsage
from app.security import decode_token
from app.upload_guard import quota_bytes, validate_file
from app.utils import s3


router = APIRouter()
log = get_logger("files")


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

    body = await file.read()

    # валидация
    detected_mime, category = validate_file(body, file.filename, file.content_type)

    # квота
    usage = await _get_or_create_usage(db, current.id)
    quota = quota_bytes()
    if usage.used_bytes + len(body) > quota:
        free_mb = (quota - usage.used_bytes) / (1024 * 1024)
        raise HTTPException(
            status.HTTP_507_INSUFFICIENT_STORAGE,
            f"Квота исчерпана. Свободно {free_mb:.1f} МБ из {quota // (1024 * 1024)} МБ.",
        )

    # ключ в S3
    ext = Path(file.filename).suffix[:16]
    key = f"uploads/{current.id}/{uuid.uuid4().hex}{ext}"

    if settings.S3_ENABLED:
        try:
            s3.ensure_bucket()
            s3.put_object(key, body, detected_mime)
            log.info("s3_upload_ok", key=key, size=len(body), mime=detected_mime)
        except Exception as e:
            log.error("s3_upload_failed", key=key, error=str(e))
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                f"Не удалось сохранить файл в S3: {e}",
            )
    else:
        # fallback: локальный диск
        target = settings.upload_path / Path(key).name
        target.write_bytes(body)

    obj = FileModel(
        owner_id=current.id,
        filename=file.filename,
        content_type=detected_mime,
        size=len(body),
        storage_name=key,
    )
    db.add(obj)
    await db.flush()

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

    if settings.S3_ENABLED:
        s3.delete_object(obj.storage_name)
    else:
        path = settings.upload_path / Path(obj.storage_name).name
        path.unlink(missing_ok=True)

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

    # fallback: если файл лежит локально (старые загрузки), отдаём с диска
    local_name = Path(obj.storage_name).name
    local_path = settings.upload_path / local_name
    if local_path.exists():
        inline = obj.content_type.startswith(("image/", "audio/", "video/"))
        return FileResponse(
            local_path,
            media_type=obj.content_type,
            filename=obj.filename,
            content_disposition_type="inline" if inline else "attachment",
        )

    if not settings.S3_ENABLED:
        raise HTTPException(status.HTTP_410_GONE, "file missing on disk")

    # Основной путь: редирект на presigned S3 URL
    try:
        url = s3.presigned_url(obj.storage_name)
    except Exception as e:
        log.error("s3_presign_failed", key=obj.storage_name, error=str(e))
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"Не удалось получить ссылку на файл: {e}",
        )

    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
'''


# ============================================================== Dockerfile
DOCKERFILE = r'''FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN pip install --upgrade pip && pip install \
    "fastapi==0.115.6" \
    "uvicorn[standard]==0.34.0" \
    "pydantic==2.10.4" \
    "pydantic-settings==2.7.0" \
    "sqlalchemy[asyncio]==2.0.36" \
    "asyncpg==0.30.0" \
    "alembic==1.14.0" \
    "redis==5.2.1" \
    "pyjwt==2.10.1" \
    "passlib[bcrypt]==1.7.4" \
    "bcrypt==4.0.1" \
    "python-multipart==0.0.20" \
    "email-validator==2.2.0" \
    "filetype==1.2.0" \
    "structlog==24.4.0" \
    "boto3==1.35.60" \
    "pytest==8.3.4" \
    "pytest-asyncio==0.25.0" \
    "httpx==0.28.1"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "/dev/null"]
'''


# ============================================================== .env.example
ENV_EXAMPLE = r'''# App
APP_NAME=Messenger
ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1

# Security
SECRET_KEY=change-me-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=messenger
POSTGRES_PASSWORD=messenger
POSTGRES_DB=messenger

# Redis
REDIS_URL=redis://redis:6379/0
CACHE_TTL_CHATS=15
CACHE_TTL_PROFILE=60

# ---- S3 ----
S3_ENABLED=true
S3_ENDPOINT=https://storage.yandexcloud.net
S3_REGION=ru-central1
S3_ACCESS_KEY=REPLACE_ME
S3_SECRET_KEY=REPLACE_ME
S3_BUCKET=messenger
S3_PUBLIC_URL=
S3_PRESIGN_EXPIRE=3600

# Uploads
UPLOAD_DIR=/app/uploads
MAX_IMAGE_MB=15
MAX_VIDEO_MB=100
MAX_AUDIO_MB=25
MAX_DOCUMENT_MB=25
MAX_ARCHIVE_MB=50
MAX_OTHER_MB=10
USER_QUOTA_MB=1024

# Rate limit
RATE_LIMIT_AUTH=10
RATE_LIMIT_GLOBAL=300

CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
'''


# ============================================================== docker-compose.yml (без MinIO)
DOCKER_COMPOSE = r'''services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-messenger}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-messenger}
      POSTGRES_DB: ${POSTGRES_DB:-messenger}
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
'''


def write_file(path: Path, content: str) -> None:
    existed = path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {path}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--access-key", default="")
    p.add_argument("--secret-key", default="")
    p.add_argument("--endpoint", default="https://storage.yandexcloud.net")
    p.add_argument("--region", default="ru-central1")
    p.add_argument("--bucket", default="messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    be = root / "backend"

    print("\nСпринт 27 — S3-хранилище\n")

    # config
    write_file(be / "app" / "config.py", CONFIG)

    # s3 utils
    (be / "app" / "utils").mkdir(parents=True, exist_ok=True)
    write_file(be / "app" / "utils" / "s3.py", S3_UTIL)

    # files router
    write_file(be / "app" / "routers" / "files.py", FILES_ROUTER)

    # Dockerfile
    write_file(be / "Dockerfile", DOCKERFILE)

    # .env.example — обновляем
    write_file(be / ".env.example", ENV_EXAMPLE)

    # .env — реальные креды, если переданы
    env_text = ENV_EXAMPLE
    if args.access_key:
        env_text = env_text.replace("S3_ACCESS_KEY=REPLACE_ME", f"S3_ACCESS_KEY={args.access_key}")
    if args.secret_key:
        env_text = env_text.replace("S3_SECRET_KEY=REPLACE_ME", f"S3_SECRET_KEY={args.secret_key}")
    env_text = env_text.replace("S3_ENDPOINT=https://storage.yandexcloud.net", f"S3_ENDPOINT={args.endpoint}")
    env_text = env_text.replace("S3_REGION=ru-central1", f"S3_REGION={args.region}")
    env_text = env_text.replace("S3_BUCKET=messenger", f"S3_BUCKET={args.bucket}")
    # SECRET_KEY приложения — оставляем placeholder, юзер сам вставит или у него уже есть в .env
    write_file(be / ".env", env_text)

    # docker-compose без MinIO
    write_file(root / "infra" / "docker-compose.yml", DOCKER_COMPOSE)

    print()
    print("Готово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml build --no-cache api")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("ВАЖНО:")
    print("  1. Я записал S3-ключи в backend/.env — НО они теперь в истории чата.")
    print("     Сгенерируй новые в панели S3-провайдера и замени их в .env.")
    print("  2. Проверь S3_ENDPOINT — у разных провайдеров свои URL:")
    print("     - Yandex: https://storage.yandexcloud.net")
    print("     - VK Cloud: https://hb.ru-msk.vkcs.cloud")
    print("     - AWS: https://s3.amazonaws.com или оставь пусто")
    print("     - MinIO: http://localhost:9000")
    print("  3. Убедись, что бакет существует (или дай права на create)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())