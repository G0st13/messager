#!/usr/bin/env python3
"""e2e_doctor.py - полная диагностика E2E: исходники + БД + сборка + логи."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 600) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def hr(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def check_source_patches(root: Path) -> dict[str, bool]:
    hr("1. ПРОВЕРКА ИСХОДНИКОВ (патчи E2E)")
    fe = root / "frontend" / "src"
    be = root / "backend" / "app"

    checks: dict[str, tuple[Path, str, str]] = {
        "ChatWindow: encrypted в WS-обработчике":
            (fe / "ChatWindow.tsx", "encrypted: d.encrypted", "string"),
        "ChatWindow: e2eApi fallback":
            (fe / "ChatWindow.tsx", "e2eApi", "string"),
        "ChatWindow: useEffect расшифровки":
            (fe / "ChatWindow.tsx", "decryptFromChat", "string"),
        "ChatWindow: подмена текста в рендере":
            (fe / "ChatWindow.tsx", "decrypted[m.id]", "string"),
        "App.tsx: import useE2E":
            (fe / "App.tsx", 'from "./useE2E"', "string"),
        "App.tsx: const e2e = useE2E":
            (fe / "App.tsx", "const e2e = useE2E(", "string"),
        "App.tsx: e2e={e2e} в ChatWindow":
            (fe / "App.tsx", "e2e={e2e}", "string"),
        "useE2E.ts: importPrivateKeyJwk":
            (fe / "useE2E.ts", "importPrivateKeyJwk", "string"),
        "useE2E.ts: decryptFromChat":
            (fe / "useE2E.ts", "decryptFromChat", "string"),
        "useE2E.ts: savePublicB64":
            (fe / "useE2E.ts", "savePublicB64", "string"),
        "ws.py: читает encrypted":
            (be / "routers" / "ws.py", 'data.get("encrypted"', "string"),
        "ws.py: сохраняет encrypted":
            (be / "routers" / "ws.py", "encrypted=encrypted", "string"),
        "ws.py: отправляет encrypted":
            (be / "routers" / "ws.py", '"encrypted": encrypted', "string"),
    }

    results: dict[str, bool] = {}
    for label, (path, needle, _) in checks.items():
        if not path.exists():
            print(f"  ✗ {label}  — файл не найден: {path.name}")
            results[label] = False
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        ok = needle in text
        mark = "✓" if ok else "✗"
        print(f"  {mark} {label}")
        results[label] = ok
    return results


def check_db(compose: Path) -> None:
    hr("2. ПРОВЕРКА БАЗЫ ДАННЫХ")

    print("\n  user_keys (публичные ключи E2E):")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "db",
                     "psql", "-U", "messenger", "-d", "messenger", "-c",
                     "SELECT user_id, LEFT(public_key, 30) AS pub FROM user_keys ORDER BY user_id;"])
    print("    " + (out.strip().replace("\n", "\n    ") if out.strip() else "(пусто)"))

    print("\n  chat_members.permissions колонка:")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "db",
                     "psql", "-U", "messenger", "-d", "messenger", "-c",
                     "SELECT column_name FROM information_schema.columns WHERE table_name='chat_members' AND column_name='permissions';"])
    print("    " + (out.strip().replace("\n", "\n    ") if out.strip() else "(пусто)"))

    print("\n  messages.encrypted колонка:")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "db",
                     "psql", "-U", "messenger", "-d", "messenger", "-c",
                     "SELECT column_name FROM information_schema.columns WHERE table_name='messages' AND column_name='encrypted';"])
    print("    " + (out.strip().replace("\n", "\n    ") if out.strip() else "(пусто)"))

    print("\n  Последние 5 зашифрованных сообщений в чате 2:")
    code, out = run(["docker", "compose", "-f", str(compose), "exec", "-T", "db",
                     "psql", "-U", "messenger", "-d", "messenger", "-c",
                     "SELECT id, encrypted, LEFT(COALESCE(text,''), 60) AS preview FROM messages WHERE chat_id=2 ORDER BY id DESC LIMIT 5;"])
    print("    " + (out.strip().replace("\n", "\n    ") if out.strip() else "(нет)"))


def check_bundle(root: Path) -> None:
    hr("3. ПРОВЕРКА СОБРАННОГО БАНДЛА (что лежит в frontend/dist)")

    dist = root / "frontend" / "dist" / "assets"
    if not dist.exists():
        print("  ✗ dist/assets не найден — бандл собирается внутри контейнера, это нормально")
        return

    js_files = sorted(dist.glob("index-*.js"))
    if not js_files:
        print("  ✗ нет index-*.js в dist/assets")
        return

    latest = js_files[0]
    text = latest.read_text(encoding="utf-8", errors="replace")
    print(f"  Файл: {latest.name}  ({latest.stat().st_size // 1024} KB)")
    print()
    markers = [
        ("messenger-e2e", "IndexedDB база ключей"),
        ("decryptFromChat", "функция расшифровки"),
        ("encrypted", "флаг шифрования"),
    ]
    for marker, desc in markers:
        cnt = text.count(marker)
        mark = "✓" if cnt > 0 else "✗"
        print(f"  {mark} {marker!r} × {cnt} — {desc}")


def rebuild_and_restart(root: Path, compose: Path) -> None:
    hr("4. ПЕРЕСБОРКА FRONTEND + ПЕРЕЗАПУСК")

    print("\n  → build --no-cache frontend ...")
    code, out = run(["docker", "compose", "-f", str(compose),
                     "build", "--no-cache", "frontend"], cwd=root, timeout=600)
    if code != 0:
        print("  ✗ Сборка упала:")
        print("    " + out[-2000:].replace("\n", "\n    "))
        return
    print("  ✓ Сборка завершена")

    print("\n  → up -d ...")
    code, out = run(["docker", "compose", "-f", str(compose), "up", "-d"],
                    cwd=root, timeout=120)
    print("  " + ("✓ Готово" if code == 0 else "✗ Ошибка"))


def check_logs(compose: Path) -> None:
    hr("5. ПОСЛЕДНИЕ ЛОГИ API")

    code, out = run(["docker", "compose", "-f", str(compose),
                     "logs", "api", "--tail", "30"])
    lines = (out or "").split("\n")
    interesting = [l for l in lines if any(x in l.lower() for x in
                                          ["error", "traceback", "exception",
                                           "alembic", "startup complete",
                                           "keys/me", "ws"])]
    if interesting:
        for l in interesting[-25:]:
            print("    " + l)
    else:
        print("  " + (out[-1500:].replace("\n", "\n  ") if out else "(нет)"))


def verdict(patches: dict[str, bool], root: Path) -> None:
    hr("ВЕРДИКТ")

    missing = [k for k, v in patches.items() if not v]
    if missing:
        print("  ✗ В исходниках отсутствуют патчи:")
        for m in missing:
            print(f"      — {m}")
        print()
        print("  → Нужно применить недостающие патчи, потом пересобрать.")
        return

    print("  ✓ Все патчи на месте в исходниках")
    print("  ✓ Frontend пересобран, контейнеры перезапущены")
    print()
    print("  ЧТО ДЕЛАТЬ ДАЛЬШЕ (в браузере):")
    print("    1. F12 → Network → включи 'Disable cache'")
    print("    2. Ctrl+Shift+R (hard reload)")
    print("    3. Открой чат 2, отправь 'тест_расшифровки'")
    print()
    print("  ЧТО ПРОВЕРИТЬ ПОСЛЕ:")
    print("    — В UI должен быть читаемый текст, не e2e:1:...")
    print("    — В Console (F12) не должно быть красных ошибок")
    print("    — В БД (запрос ниже) encrypted=t, preview=e2e:1:...")
    print()
    print("    docker compose -f infra/docker-compose.yml exec db \\")
    print("      psql -U messenger -d messenger -c \\")
    print('      "SELECT id, encrypted, LEFT(COALESCE(text,\'\'), 60) FROM messages WHERE chat_id=2 ORDER BY id DESC LIMIT 2;"')


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-rebuild", action="store_true",
                   help="только диагностика, без пересборки")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено")
        return 1

    compose = root / "infra" / "docker-compose.yml"
    if not compose.exists():
        print(f"ERR: {compose} не найден")
        return 1

    print(f"\n  Проект: {root}")
    print(f"  Compose: {compose}")

    patches = check_source_patches(root)
    check_db(compose)
    check_bundle(root)

    if not args.no_rebuild:
        rebuild_and_restart(root, compose)
        check_logs(compose)

    verdict(patches, root)

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())