#!/usr/bin/env python3
"""diag_e2e.py - полная диагностика E2E на стороне проекта."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=30, encoding="utf-8", errors="replace",
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except FileNotFoundError:
        return -1, f"команда не найдена: {' '.join(cmd)}"
    except Exception as e:
        return -1, f"ошибка запуска: {e}"


# ============================================================
# ПРОВЕРКА ФАЙЛОВ
# ============================================================

def check_file_contains(path: Path, needle: str, label: str) -> bool:
    if not path.exists():
        print(f"  ✗ {label}: файл {path.name} НЕ НАЙДЕН")
        return False
    text = path.read_text(encoding="utf-8")
    ok = needle in text
    print(f"  {'✓' if ok else '✗'} {label}")
    return ok


def check_app_tsx(root: Path) -> list[str]:
    """Проверяет App.tsx — критичные места."""
    problems = []
    path = root / "frontend" / "src" / "App.tsx"
    if not path.exists():
        problems.append("App.tsx не найден")
        return problems

    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")

    # 1. import useE2E
    if 'from "./useE2E"' not in text:
        problems.append("App.tsx: нет import { useE2E }")
        print("  ✗ import useE2E")
    else:
        print("  ✓ import useE2E")

    # 2. const e2e = useE2E(...)
    if "const e2e = useE2E(" not in text:
        problems.append("App.tsx: нет const e2e = useE2E(...)")
        print("  ✗ const e2e = useE2E(...)")
    else:
        # Найдём строку и проверим что она внутри компонента
        for i, line in enumerate(lines, 1):
            if "const e2e = useE2E(" in line:
                # Найдём ближайший preceding "export default function App"
                prefix = "\n".join(lines[:i])
                if "export default function App" in prefix or "function App(" in prefix:
                    print(f"  ✓ const e2e = useE2E(...) (строка {i})")
                else:
                    problems.append(f"App.tsx: const e2e вне компонента App (строка {i})")
                    print(f"  ✗ const e2e вне компонента App (строка {i})")
                break

    # 3. useE2E={e2e} в GroupInfoPanel
    if "useE2E={e2e}" in text:
        print("  ✓ <GroupInfoPanel useE2E={e2e}>")
    else:
        problems.append("App.tsx: GroupInfoPanel не получает useE2E={e2e}")
        print("  ✗ <GroupInfoPanel useE2E={e2e}>")

    # 4. Порядок аргументов в queue.enqueue
    m = re.search(
        r"queue\.enqueue\(([^)]+)\)",
        text,
        re.S,
    )
    if m:
        args_str = m.group(1)
        # Ищем что идёт после replyToId
        # Если там encrypted до { — порядок неправильный
        # Правильно: ...replyToId, {  ...  }, encrypted)
        # Неправильно: ...replyToId, encrypted, {  ...  })
        after_reply = args_str
        # Уберём первое вхождение replyToId
        idx = after_reply.find("replyToId")
        if idx >= 0:
            tail = after_reply[idx + len("replyToId"):]
            # tail начинается с ", ..."
            if re.match(r"\s*,\s*encrypted\s*,", tail):
                problems.append("App.tsx: queue.enqueue — encrypted передан ДО author (неправильный порядок)")
                print("  ✗ queue.enqueue: порядок аргументов неправильный")
            elif re.match(r"\s*,\s*\{", tail):
                # ожидаем { ... }, encrypted)
                if re.search(r"\}\s*,\s*encrypted\s*\)", args_str):
                    print("  ✓ queue.enqueue: порядок аргументов правильный")
                else:
                    print("  ~ queue.enqueue: порядок вероятно правильный, но не удалось точно проверить")
            else:
                print(f"  ~ queue.enqueue: неизвестный формат после replyToId: {tail[:60]!r}")
    else:
        print("  ~ queue.enqueue не найден")

    return problems


def check_chat_window(root: Path) -> list[str]:
    problems = []
    path = root / "frontend" / "src" / "ChatWindow.tsx"
    if not path.exists():
        problems.append("ChatWindow.tsx не найден")
        return problems

    text = path.read_text(encoding="utf-8")

    checks = [
        ("doSend async с E2E",
         "const doSend = useCallback(async () => {"),
        ("E2E шифрование в doSend",
         "e2e.encryptForChat(chat, t)"),
        ("useEffect расшифровки",
         "E2E: расшифровка входящих"),
        ("decrypted state",
         "const [decrypted, setDecrypted]"),
        ("msg={расшифровка}",
         "m.encrypted && decrypted[m.id]"),
        ("props e2e: UseE2EType",
         "e2e: UseE2E"),
    ]
    for label, needle in checks:
        ok = needle in text
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            problems.append(f"ChatWindow.tsx: {label}")

    return problems


def check_message_queue(root: Path) -> list[str]:
    problems = []
    path = root / "frontend" / "src" / "useMessageQueue.ts"
    if not path.exists():
        problems.append("useMessageQueue.ts не найден")
        return problems

    text = path.read_text(encoding="utf-8")

    checks = [
        ("QueuedMessage.encrypted",
         "encrypted: boolean;"),
        ("enqueue имеет encrypted param",
         "encrypted: boolean = false,"),
        ("wsSend передаёт encrypted",
         "encrypted: (msg as any).encrypted || false"),
    ]
    for label, needle in checks:
        ok = needle in text
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            problems.append(f"useMessageQueue.ts: {label}")

    return problems


def check_group_info_panel(root: Path) -> list[str]:
    problems = []
    path = root / "frontend" / "src" / "GroupInfoPanel.tsx"
    if not path.exists():
        problems.append("GroupInfoPanel.tsx не найден")
        return problems

    text = path.read_text(encoding="utf-8")

    checks = [
        ("import E2ESetupModal",
         'import E2ESetupModal from "./E2ESetupModal"'),
        ("props useE2E",
         "useE2E: UseE2E"),
        ("state showE2ESetup",
         "const [showE2ESetup, setShowE2ESetup]"),
        ("кнопка ВКЛЮЧИТЬ E2E",
         "ВКЛЮЧИТЬ E2E"),
        ("E2ESetupModal в JSX",
         "<E2ESetupModal"),
    ]
    for label, needle in checks:
        ok = needle in text
        print(f"  {'✓' if ok else '✗'} {label}")
        if not ok:
            problems.append(f"GroupInfoPanel.tsx: {label}")

    return problems


def check_crypto_files(root: Path) -> list[str]:
    problems = []
    files = [
        "crypto.ts",
        "keyStorage.ts",
        "useE2E.ts",
        "E2EIndicator.tsx",
        "E2ESetupModal.tsx",
    ]
    fe = root / "frontend" / "src"
    for f in files:
        path = fe / f
        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ {f} ({size} bytes)")
        else:
            print(f"  ✗ {f} НЕ НАЙДЕН")
            problems.append(f"{f} не найден")
    return problems


# ============================================================
# BACKEND
# ============================================================

def check_backend_files(root: Path) -> list[str]:
    problems = []
    files = [
        "backend/app/routers/keys.py",
        "backend/alembic/versions/0014_user_keys.py",
    ]
    for f in files:
        path = root / f
        if path.exists():
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f} НЕ НАЙДЕН")
            problems.append(f"{f} не найден")

    # Проверка main.py — подключён ли keys router
    main_py = root / "backend" / "app" / "main.py"
    if main_py.exists():
        text = main_py.read_text(encoding="utf-8")
        if "keys.router" in text:
            print("  ✓ main.py: keys router подключён")
        else:
            print("  ✗ main.py: keys router НЕ подключён")
            problems.append("main.py: keys router не подключён")

    return problems


# ============================================================
# DOCKER / БД / ЛОГИ
# ============================================================

def check_docker(root: Path) -> list[str]:
    problems = []
    compose = root / "infra" / "docker-compose.yml"
    if not compose.exists():
        problems.append("docker-compose.yml не найден")
        return problems

    # docker compose ps
    code, out = run(
        ["docker", "compose", "-f", str(compose), "ps", "--format", "json"],
        cwd=root,
    )
    if code != 0:
        print(f"  ✗ docker compose ps: {out[:200]}")
        problems.append("docker compose ps не сработал")
        return problems

    print("  Сервисы (docker compose ps):")
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            import json
            obj = json.loads(line)
            name = obj.get("Service") or obj.get("Name", "?")
            state = obj.get("State", "?")
            status = obj.get("Status", "")
            marker = "✓" if state == "running" else "✗"
            print(f"    {marker} {name}: {state} ({status})")
            if state != "running":
                problems.append(f"сервис {name} не running")
        except Exception:
            print(f"    ? {line[:100]}")

    return problems


def check_db(root: Path) -> list[str]:
    problems = []
    compose = root / "infra" / "docker-compose.yml"

    # 1. user_keys
    print("  Таблица user_keys:")
    code, out = run([
        "docker", "compose", "-f", str(compose), "exec", "-T", "db",
        "psql", "-U", "messenger", "-d", "messenger", "-t", "-A",
        "-c", "SELECT COUNT(*) FROM user_keys;",
    ], cwd=root)
    if code != 0:
        print(f"    ✗ запрос не удался: {out[:200]}")
        problems.append("не удалось прочитать user_keys")
    else:
        count = out.strip().split("\n")[0].strip() if out.strip() else "?"
        print(f"    записей: {count}")
        if count == "0":
            problems.append("user_keys пустая — фронт не залил ключ")

    # 2. шифрованные сообщения
    print("  Шифрованные сообщения в БД:")
    code, out = run([
        "docker", "compose", "-f", str(compose), "exec", "-T", "db",
        "psql", "-U", "messenger", "-d", "messenger", "-t", "-A",
        "-c", "SELECT COUNT(*) FROM messages WHERE encrypted = true;",
    ], cwd=root)
    if code != 0:
        print(f"    ✗ запрос не удался")
    else:
        cnt = out.strip().split("\n")[0].strip()
        print(f"    encrypted=true: {cnt}")

    # 3. последние сообщения
    code, out = run([
        "docker", "compose", "-f", str(compose), "exec", "-T", "db",
        "psql", "-U", "messenger", "-d", "messenger", "-t", "-A",
        "-c", "SELECT id, encrypted, LEFT(COALESCE(text,''), 40) FROM messages ORDER BY id DESC LIMIT 3;",
    ], cwd=root)
    if code == 0 and out.strip():
        print("  Последние 3 сообщения (id | encrypted | text-preview):")
        for line in out.strip().split("\n"):
            print(f"    {line}")

    # 4. chats с encryption_enabled
    code, out = run([
        "docker", "compose", "-f", str(compose), "exec", "-T", "db",
        "psql", "-U", "messenger", "-d", "messenger", "-t", "-A",
        "-c", "SELECT id, encryption_enabled FROM chats ORDER BY id;",
    ], cwd=root)
    if code == 0 and out.strip():
        print("  Чаты (id | encryption_enabled):")
        for line in out.strip().split("\n"):
            print(f"    {line}")

    return problems


def check_api_logs(root: Path) -> list[str]:
    problems = []
    compose = root / "infra" / "docker-compose.yml"

    code, out = run([
        "docker", "compose", "-f", str(compose),
        "logs", "api", "--tail", "200", "--no-log-prefix",
    ], cwd=root)
    if code != 0:
        print(f"  ✗ не удалось прочитать логи: {out[:200]}")
        return ["не удалось прочитать логи"]

    # Ищем keys/me запросы
    keys_requests = re.findall(
        r"http_request.*path=/api/v1/keys/me status=(\d+)",
        out,
    )
    if keys_requests:
        print(f"  Запросы /api/v1/keys/me: {len(keys_requests)}")
        for status in keys_requests[-3:]:
            marker = "✓" if status in ("200", "201") else "✗"
            print(f"    {marker} status={status}")
            if status not in ("200", "201"):
                problems.append(f"/keys/me вернул {status}")
    else:
        print("  ✗ запросов /api/v1/keys/me в логах НЕ НАЙДЕНО")
        print("    Значит фронт не пытается залить ключ")
        problems.append("/keys/me никогда не вызывался")

    # Ищем ошибки про user_keys
    if "user_keys" in out and "does not exist" in out:
        problems.append("в логах: user_keys does not exist")
        print("  ✗ в логах: user_keys does not exist")

    # Ищем последние 5 ошибок
    errors = re.findall(r"ERROR.*", out)
    if errors:
        print(f"  Последние ошибки в логах api ({len(errors)}):")
        for e in errors[-5:]:
            print(f"    {e[:150]}")

    return problems


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--skip-docker", action="store_true",
                   help="не проверять docker/бд/логи")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    print(f"\n{'=' * 70}")
    print(f"ДИАГНОСТИКА E2E — {root.name}")
    print(f"{'=' * 70}")

    all_problems: list[str] = []

    # --- Frontend файлы ---
    print(f"\n[1/6] Frontend: E2E-компоненты")
    all_problems += check_crypto_files(root)

    print(f"\n[2/6] App.tsx — useE2E, GroupInfoPanel, enqueue")
    all_problems += check_app_tsx(root)

    print(f"\n[3/6] ChatWindow.tsx — шифрование/расшифровка")
    all_problems += check_chat_window(root)

    print(f"\n[4/6] useMessageQueue.ts — передача encrypted")
    all_problems += check_message_queue(root)

    print(f"\n[5/6] GroupInfoPanel.tsx — UI включения E2E")
    all_problems += check_group_info_panel(root)

    # --- Backend ---
    print(f"\n[6/6] Backend файлы + Docker + БД")
    all_problems += check_backend_files(root)

    if not args.skip_docker:
        print(f"\n  Docker:")
        all_problems += check_docker(root)

        print(f"\n  БД:")
        all_problems += check_db(root)

        print(f"\n  Логи api:")
        all_problems += check_api_logs(root)

    # --- Итог ---
    print(f"\n{'=' * 70}")
    print(f"ИТОГ")
    print(f"{'=' * 70}")

    if not all_problems:
        print("\n  ✓ ВСЁ ОК — E2E настроен корректно")
        print("    Если сообщения всё ещё не шифруются — проблема на клиенте:")
        print("    • Открой F12 → Console → ищи красные ошибки")
        print("    • F12 → Application → IndexedDB → messenger-e2e → keys")
        print("    • В консоли: window.isSecureContext (должно быть true)")
    else:
        print(f"\n  Найдено проблем: {len(all_problems)}")
        for i, prob in enumerate(all_problems, 1):
            print(f"    {i}. {prob}")
        print()
        print("  Что сделать:")
        print("    1. Если frontend-проблемы — запусти sprint29c_e2e_fix.py и sprint29d_fix_e2e_import.py")
        print("    2. Если backend/БД — проверь логи api и миграции")
        print("    3. Пересобери frontend: docker compose -f infra/docker-compose.yml build --no-cache frontend")

    print()
    return 0 if not all_problems else 2


if __name__ == "__main__":
    raise SystemExit(main())