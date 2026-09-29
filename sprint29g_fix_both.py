#!/usr/bin/env python3
"""sprint29g_fix_both.py - фикс importPrivateJwk + PublicKeyRead.from_attributes."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ==============================================================
# FIX 1: useE2E.ts — importPrivateJwk → importPrivateKeyJwk
# ==============================================================
USE_E2E_FIXES = [
    # в импорте
    (
        '  importPrivateJwk,\n',
        '  importPrivateKeyJwk,\n',
    ),
    # в использовании (в старом и новом useEffect)
    (
        'const priv = await importPrivateJwk(jwk);',
        'const priv = await importPrivateKeyJwk(jwk);',
    ),
    (
        'const priv = await importPrivateJwk(privJwk);',
        'const priv = await importPrivateKeyJwk(privJwk);',
    ),
]


# ==============================================================
# FIX 2: schemas.py — from_attributes для PublicKeyRead
# ==============================================================
SCHEMAS_FIXES = [
    (
        'class PublicKeyRead(BaseModel):\n'
        '    user_id: int\n'
        '    public_key: str\n'
        '    algorithm: str\n'
        '    updated_at: datetime',
        'class PublicKeyRead(BaseModel):\n'
        '    model_config = ConfigDict(from_attributes=True)\n'
        '    user_id: int\n'
        '    public_key: str\n'
        '    algorithm: str\n'
        '    updated_at: datetime',
    ),
    # На случай если уже добавили — не сломать
    (
        'class PublicKeyRead(BaseModel):\n'
        '    model_config = ConfigDict(from_attributes=True)\n'
        '    model_config = ConfigDict(from_attributes=True)\n',
        'class PublicKeyRead(BaseModel):\n'
        '    model_config = ConfigDict(from_attributes=True)\n',
    ),
]


def apply(path: Path, pairs: list[tuple[str, str]], label: str) -> int:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0
    text = path.read_text(encoding="utf-8")
    ok = 0
    for old, new in pairs:
        if new in text:
            print(f"     (уже применено: {label})")
            ok += 1
            continue
        if old in text:
            text = text.replace(old, new)
            ok += 1
    if ok:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path.name} [{ok}/{len(pairs)}] {label}")
    else:
        print(f"  > {path.name} — ничего не изменилось ({label})")
    return ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    for rel in ["frontend/src/useE2E.ts", "backend/app/schemas.py"]:
        src = root / rel
        if src.exists():
            dst = b / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"📦 Бэкап: {b}\n")

    print("Frontend:")
    apply(
        root / "frontend" / "src" / "useE2E.ts",
        USE_E2E_FIXES,
        "[importPrivateJwk → importPrivateKeyJwk]",
    )

    print("\nBackend:")
    apply(
        root / "backend" / "app" / "schemas.py",
        SCHEMAS_FIXES,
        "[PublicKeyRead.from_attributes]",
    )

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml restart api")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up -d")
    print()
    print("Потом в браузере:")
    print("  F12 → Console:")
    print("     indexedDB.deleteDatabase('messenger-e2e')")
    print("  F5 на странице")
    print("  Подожди 3 секунды")
    print()
    print("Проверка БД:")
    print(f'  docker compose -f infra/docker-compose.yml exec db psql -U messenger -d messenger -c "SELECT user_id, LEFT(public_key,30) FROM user_keys;"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())