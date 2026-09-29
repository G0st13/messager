#!/usr/bin/env python3
"""fix_jwt.py - заменяет python-jose на PyJWT."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DOCKERFILE = """FROM python:3.12-slim

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
    "email-validator==2.2.0"

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

SECURITY = '''from __future__ import annotations

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
    return pwd_context.verify(p, h)


def _create(sub: str | int, exp: timedelta, tt: TokenType) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(sub),
        "iat": int(now.timestamp()),
        "exp": int((now + exp).timestamp()),
        "type": tt,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(sub: str | int) -> str:
    return _create(sub, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(sub: str | int) -> str:
    return _create(sub, timedelta(days=7), "refresh")


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except InvalidTokenError as exc:
        raise ValueError("invalid token") from exc
'''

ENV_EXTRA = """
REDIS_URL=redis://redis:6379/0
CACHE_TTL_CHATS=15
CACHE_TTL_PROFILE=60
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name / "backend"
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    df = root / "Dockerfile"
    df.write_text(DOCKERFILE, encoding="utf-8")
    print(f"  ~ {df}")

    sec = root / "app" / "security.py"
    sec.write_text(SECURITY, encoding="utf-8")
    print(f"  ~ {sec}")

    env = root / ".env"
    if env.exists():
        text = env.read_text(encoding="utf-8")
        if "REDIS_URL" not in text:
            env.write_text(text.rstrip() + "\n" + ENV_EXTRA.strip() + "\n", encoding="utf-8")
            print(f"  ~ {env}")
        else:
            print(f"  > {env} (уже содержит REDIS_URL)")

    print("\nГотово. Дальше:")
    print(f"  cd {root.parent}")
    print("  docker compose -f infra/docker-compose.yml down")
    print("  docker compose -f infra/docker-compose.yml build --no-cache api")
    print("  docker compose -f infra/docker-compose.yml up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())