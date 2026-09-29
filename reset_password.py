#!/usr/bin/env python3
"""reset_password.py - сбрасывает пароль пользователя через bcrypt."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    compose = root / "infra" / "docker-compose.yml"

    # 1. Список юзеров
    print("Пользователи в БД:")
    r = subprocess.run(
        ["docker", "compose", "-f", str(compose), "exec", "-T", "db",
         "psql", "-U", "messenger", "-d", "messenger", "-c",
         "SELECT id, username FROM users ORDER BY id;"],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
    )
    print(r.stdout or r.stderr)

    # 2. Генерируем bcrypt-хеш
    print(f"Генерирую bcrypt-хеш для {args.password!r}...")
    gen = subprocess.run(
        ["docker", "compose", "-f", str(compose), "exec", "-T", "api",
         "python", "-c",
         "from passlib.context import CryptContext; "
         "print(CryptContext(schemes=['bcrypt'], deprecated='auto').hash("
         + repr(args.password) + "))"],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
    )
    if gen.returncode != 0:
        print(f"ERR generate: {gen.stderr}")
        return 1
    hashval = gen.stdout.strip().split("\n")[-1].strip()
    if not hashval.startswith("$2"):
        print(f"ERR: не bcrypt: {hashval[:40]}")
        return 1
    print(f"✓ хеш: {hashval[:30]}...")

    # 3. UPDATE
    sql = f"UPDATE users SET hashed_password = '{hashval}' WHERE username = '{args.username}';"
    upd = subprocess.run(
        ["docker", "compose", "-f", str(compose), "exec", "-T", "db",
         "psql", "-U", "messenger", "-d", "messenger", "-c", sql],
        capture_output=True, text=True, timeout=30, encoding="utf-8",
    )
    print(upd.stdout or upd.stderr)

    if "UPDATE 1" in (upd.stdout or ""):
        print(f"\n✅ Пароль для {args.username} = {args.password}")
        print("   Логинься с ним в браузере.")
    else:
        print(f"\n⚠ UPDATE не сработал. Юзер {args.username} есть?")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())