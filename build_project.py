#!/usr/bin/env python3
"""build_project.py - minimal messenger."""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

PROJECT_NAME = "messenger"
OVERWRITE = False


def _t(s: str) -> str:
    return textwrap.dedent(s).strip("\n") + "\n"


TEMPLATES = {}

TEMPLATES["README.md"] = _t("""
    # Messenger

    Minimal FastAPI + PostgreSQL + JWT.

    ## Run

        cp backend/.env.example backend/.env
        docker compose -f infra/docker-compose.yml up --build

    - API:      http://localhost:8000/docs
    - Frontend: http://localhost:5173
""")

TEMPLATES[".gitignore"] = _t("""
    __pycache__/
    *.py[cod]
    .venv/
    venv/
    .env
    .env.*
    !.env.example
    node_modules/
    frontend/dist/
    .idea/
    .vscode/
    .DS_Store
""")

TEMPLATES["backend/pyproject.toml"] = _t("""
    [project]
    name = "messenger-backend"
    version = "0.1.0"
    requires-python = ">=3.12"
    dependencies = [
        "fastapi>=0.115",
        "uvicorn[standard]>=0.30",
        "pydantic>=2.8",
        "pydantic-settings>=2.4",
        "sqlalchemy[asyncio]>=2.0.32",
        "asyncpg>=0.29",
        "python-jose[cryptography]>=3.3",
        "passlib[bcrypt]>=1.7.4",
        "bcrypt==4.0.1",
        "python-multipart>=0.0.9",
        "email-validator>=2.2",
    ]

    [build-system]
    requires = ["hatchling"]
    build-backend = "hatchling.build"
""")

TEMPLATES["backend/Dockerfile"] = _t("""
    FROM python:3.12-slim

    ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

    WORKDIR /app

    RUN apt-get update && apt-get install -y --no-install-recommends \\
            build-essential libpq-dev \\
        && rm -rf /var/lib/apt/lists/*

    COPY pyproject.toml ./
    RUN pip install --upgrade pip && pip install -e .

    COPY . .

    EXPOSE 8000
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
""")

TEMPLATES["backend/.env.example"] = _t("""
    APP_NAME=Messenger
    DEBUG=true
    API_V1_PREFIX=/api/v1
    SECRET_KEY=change-me-in-production
    ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    POSTGRES_HOST=db
    POSTGRES_PORT=5432
    POSTGRES_USER=messenger
    POSTGRES_PASSWORD=messenger
    POSTGRES_DB=messenger
    CORS_ORIGINS=["http://localhost:5173","http://localhost:8000"]
""")

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
        ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

        POSTGRES_HOST: str = "localhost"
        POSTGRES_PORT: int = 5432
        POSTGRES_USER: str = "messenger"
        POSTGRES_PASSWORD: str = "messenger"
        POSTGRES_DB: str = "messenger"

        CORS_ORIGINS: list[str] = ["http://localhost:5173"]

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
            "exp": int((now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


    def decode_token(token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError as exc:
            raise ValueError("invalid token") from exc
""")

TEMPLATES["backend/app/models.py"] = _t("""
    from datetime import datetime
    from sqlalchemy import Boolean, DateTime, String, func
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
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
""")

TEMPLATES["backend/app/schemas.py"] = _t("""
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
""")

TEMPLATES["backend/app/deps.py"] = _t("""
    from typing import Annotated
    from fastapi import Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.config import settings
    from app.db import get_session
    from app.security import decode_token
    from app.models import User


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

TEMPLATES["backend/app/router.py"] = _t("""
    from fastapi import APIRouter, Depends, HTTPException, status
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.db import get_session
    from app.deps import CurrentUser
    from app.models import User
    from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
    from app.security import create_access_token, hash_password, verify_password


    router = APIRouter()


    @router.post("/auth/register", response_model=UserRead, status_code=201)
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
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return UserRead.model_validate(user)


    @router.post("/auth/login", response_model=TokenResponse)
    async def login(payload: LoginRequest, db: AsyncSession = Depends(get_session)):
        result = await db.execute(select(User).where(User.username == payload.username))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
        return TokenResponse(access_token=create_access_token(user.id))


    @router.get("/auth/me", response_model=UserRead)
    async def me(current: CurrentUser):
        return UserRead.model_validate(current)


    @router.get("/users", response_model=list[UserRead])
    async def list_users(db: AsyncSession = Depends(get_session), limit: int = 50):
        result = await db.execute(select(User).limit(limit))
        return [UserRead.model_validate(u) for u in result.scalars().all()]
""")

TEMPLATES["backend/app/main.py"] = _t("""
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from app.config import settings
    from app.db import engine
    from app.models import Base
    from app.router import router


    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()


    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix=settings.API_V1_PREFIX)


    @app.get("/health")
    async def health():
        return {"status": "ok", "app": settings.APP_NAME}
""")

TEMPLATES["frontend/package.json"] = _t("""
    {
      "name": "messenger-frontend",
      "private": true,
      "version": "0.1.0",
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
        "typescript": "^5.5.4",
        "vite": "^5.4.0"
      }
    }
""")

TEMPLATES["frontend/vite.config.ts"] = _t("""
    import { defineConfig } from "vite";
    import react from "@vitejs/plugin-react";

    export default defineConfig({
      plugins: [react()],
      server: { port: 5173, host: "0.0.0.0" }
    });
""")

TEMPLATES["frontend/tsconfig.json"] = _t("""
    {
      "compilerOptions": {
        "target": "ES2022",
        "lib": ["ES2022", "DOM", "DOM.Iterable"],
        "module": "ESNext",
        "moduleResolution": "Bundler",
        "jsx": "react-jsx",
        "strict": false,
        "skipLibCheck": true,
        "esModuleInterop": true,
        "isolatedModules": true
      },
      "include": ["src"]
    }
""")

TEMPLATES["frontend/index.html"] = _t("""
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Messenger</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module" src="/src/main.tsx"></script>
      </body>
    </html>
""")

TEMPLATES["frontend/Dockerfile"] = _t("""
    FROM node:20-alpine AS build
    WORKDIR /app
    COPY package.json ./
    RUN npm install
    COPY . .
    RUN npm run build

    FROM nginx:1.27-alpine
    COPY --from=build /app/dist /usr/share/nginx/html
    EXPOSE 80
    CMD ["nginx", "-g", "daemon off;"]
""")

TEMPLATES["frontend/src/main.tsx"] = _t("""
    import React from "react";
    import ReactDOM from "react-dom/client";
    import App from "./App";

    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <App />
      </React.StrictMode>
    );
""")

TEMPLATES["frontend/src/api.ts"] = _t("""
    import axios from "axios";

    export const api = axios.create({ baseURL: "/api/v1" });

    api.interceptors.request.use((config) => {
      const t = localStorage.getItem("access_token");
      if (t) config.headers.Authorization = `Bearer ${t}`;
      return config;
    });
""")

TEMPLATES["frontend/src/Login.tsx"] = _t("""
    import { useState } from "react";
    import { api } from "./api";

    export default function Login({ onLogin }: { onLogin: () => void }) {
      const [username, setUsername] = useState("");
      const [password, setPassword] = useState("");
      const [error, setError] = useState("");

      const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
          const { data } = await api.post("/auth/login", { username, password });
          localStorage.setItem("access_token", data.access_token);
          onLogin();
        } catch (err: any) {
          setError(err.response?.data?.detail || "Login failed");
        }
      };

      return (
        <form onSubmit={submit} style={{ maxWidth: 320, margin: "80px auto", display: "flex", flexDirection: "column", gap: 12 }}>
          <h1>Sign in</h1>
          <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" style={{ padding: 8 }} />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" style={{ padding: 8 }} />
          <button type="submit" style={{ padding: 10 }}>Login</button>
          {error && <p style={{ color: "red" }}>{error}</p>}
        </form>
      );
    }
""")

TEMPLATES["frontend/src/App.tsx"] = _t("""
    import { useEffect, useState } from "react";
    import Login from "./Login";
    import { api } from "./api";

    export default function App() {
      const [user, setUser] = useState<any>(null);

      const loadMe = async () => {
        try {
          const { data } = await api.get("/auth/me");
          setUser(data);
        } catch {
          setUser(null);
        }
      };

      useEffect(() => { loadMe(); }, []);

      if (!user) return <Login onLogin={loadMe} />;

      return (
        <div style={{ padding: 24 }}>
          <h1>Hello, {user.username}!</h1>
          <p>Email: {user.email}</p>
          <button onClick={() => { localStorage.removeItem("access_token"); setUser(null); }}>
            Logout
          </button>
        </div>
      );
    }
""")

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
        command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

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


def write_all(root: Path, overwrite: bool) -> tuple[int, int, int]:
    created = skipped = errors = 0
    for rel, content in TEMPLATES.items():
        target = root / rel
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"ERR mkdir {target.parent}: {e}", file=sys.stderr)
            errors += 1
            continue
        if target.exists() and not overwrite:
            print(f"  skip {rel}")
            skipped += 1
            continue
        try:
            target.write_text(content, encoding="utf-8")
            print(f"  + {rel}")
            created += 1
        except OSError as e:
            print(f"ERR {rel}: {e}", file=sys.stderr)
            errors += 1
    return created, skipped, errors


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--name", default=PROJECT_NAME)
    p.add_argument("--path", default=".")
    p.add_argument("--overwrite", action="store_true", default=OVERWRITE)
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    print(f"\nProject: {args.name}")
    print(f"Path:    {root}\n")

    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERR: {e}", file=sys.stderr)
        return 1

    created, skipped, errors = write_all(root, args.overwrite)
    print(f"\nDone: {created} created, {skipped} skipped, {errors} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())