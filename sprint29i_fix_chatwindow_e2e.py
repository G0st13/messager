#!/usr/bin/env python3
"""sprint29i_fix_chatwindow_e2e.py - передаёт e2e в ChatWindow + защита."""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    app_tsx = root / "frontend" / "src" / "App.tsx"
    cw_tsx = root / "frontend" / "src" / "ChatWindow.tsx"

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    for f in (app_tsx, cw_tsx):
        if f.exists():
            dst = b / f.name
            shutil.copy2(f, dst)
    print(f"📦 Бэкап: {b}\n")

    # ============================================================
    # 1. Показать что сейчас в <ChatWindow ... />
    # ============================================================
    print("=" * 70)
    print("ЧТО СЕЙЧАС В App.tsx — БЛОК <ChatWindow>")
    print("=" * 70)
    if app_tsx.exists():
        text = app_tsx.read_text(encoding="utf-8")
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            if "<ChatWindow" in line:
                for j in range(i - 1, min(len(lines), i + 25)):
                    print(f"  {j+1:4d} | {lines[j]}")
                break
    print()

    # ============================================================
    # 2. Показать сигнатуру ChatWindow
    # ============================================================
    print("=" * 70)
    print("СИГНАТУРА ChatWindow.tsx")
    print("=" * 70)
    if cw_tsx.exists():
        text = cw_tsx.read_text(encoding="utf-8")
        lines = text.split("\n")
        for i, line in enumerate(lines, 1):
            if "export default function ChatWindow" in line or "export default memo(ChatWindowInner" in line:
                for j in range(i - 1, min(len(lines), i + 30)):
                    print(f"  {j+1:4d} | {lines[j]}")
                break
    print()

    # ============================================================
    # 3. ПАТЧ ChatWindow — делаем e2e опциональным + защита
    # ============================================================
    if not cw_tsx.exists():
        print(f"ERR: {cw_tsx} не найден")
        return 1

    cw = cw_tsx.read_text(encoding="utf-8")
    cw_original = cw

    # 3.1. Сделать prop e2e опциональным в типе
    # Ищем "e2e: UseE2E," или "e2e: UseE2EType," и меняем на опциональный
    cw = re.sub(
        r"(\n\s+e2e:\s*)UseE2E(Type)?,",
        r"\1UseE2E\2 | undefined,",
        cw,
        count=1,
    )

    # 3.2. Добавить fallback в начале компонента
    # Находим строку с const [messages, setMessages] = useState<Message[]>([]);
    anchor = "const [messages, setMessages] = useState<Message[]>([]);"
    if anchor in cw and "e2eApi" not in cw:
        # определяем тип UseE2E (импортирован ли)
        has_type_import = "UseE2E" in cw
        fallback = (
            '  // защита: e2e может быть undefined, если родитель не передал\n'
            '  const e2eApi: UseE2E = e2e ?? ({\n'
            '    ready: false,\n'
            '    error: "e2e not provided",\n'
            '    encryptForChat: async () => null,\n'
            '    decryptFromChat: async () => null,\n'
            '    initGroupEncryption: async () => null,\n'
            '    grantKeyTo: async () => null,\n'
            '    reset: () => {},\n'
            '  });\n\n'
        )
        cw = cw.replace(anchor, fallback + anchor, 1)
        print("  ✓ Добавлен e2eApi fallback в ChatWindow")

    # 3.3. Заменить обращения e2e. на e2eApi. внутри ChatWindow
    # Аккуратно — только там где это относится к нашему хуку
    cw = cw.replace("if (!chat.encryption_enabled || !e2e.ready)", "if (!chat.encryption_enabled || !e2eApi.ready)")
    cw = cw.replace("if (chat.encryption_enabled && e2e.ready)", "if (chat.encryption_enabled && e2eApi.ready)")
    cw = cw.replace("await e2e.encryptForChat(chat, t)", "await e2eApi.encryptForChat(chat, t)")
    cw = cw.replace("await e2e.decryptFromChat(chat, m.text)", "await e2eApi.decryptFromChat(chat, m.text)")
    cw = cw.replace("}, [messages, chat, e2e, decrypted]);", "}, [messages, chat, e2eApi, decrypted]);")
    cw = cw.replace("}, [text, editing, replyTo, chat.id, send, onEnqueue, chat.encryption_enabled, e2e]);",
                    "}, [text, editing, replyTo, chat.id, send, onEnqueue, chat.encryption_enabled, e2eApi]);")

    if cw != cw_original:
        cw_tsx.write_text(cw, encoding="utf-8")
        print(f"  ~ ChatWindow.tsx")
    else:
        print(f"  > ChatWindow.tsx — без изменений")

    # ============================================================
    # 4. ПАТЧ App.tsx — добавить e2e={e2e} в <ChatWindow> если нет
    # ============================================================
    if app_tsx.exists():
        app = app_tsx.read_text(encoding="utf-8")
        app_orig = app

        if "e2e={e2e}" in app:
            print("  > App.tsx: e2e={e2e} уже есть")
        elif "<ChatWindow" in app:
            # Ищем блок <ChatWindow ... /> и добавляем prop перед закрывающим />
            # Находим "currentUser={user}" внутри <ChatWindow>
            m = re.search(
                r"(<ChatWindow\b[^>]*?)(currentUser=\{user\})",
                app,
                re.DOTALL,
            )
            if m:
                app = app[:m.end(2)] + "\n                e2e={e2e}" + app[m.end(2):]
                app_tsx.write_text(app, encoding="utf-8")
                print("  ~ App.tsx: добавлен e2e={e2e} в <ChatWindow>")
            else:
                # fallback: ищем "onStartCall={startCall}" и вставим после
                m2 = re.search(
                    r"(onStartCall=\{startCall\})",
                    app,
                )
                if m2:
                    app = app[:m2.end(1)] + "\n                e2e={e2e}" + app[m2.end(1):]
                    app_tsx.write_text(app, encoding="utf-8")
                    print("  ~ App.tsx: добавлен e2e={e2e} после onStartCall")
                else:
                    print("  ✗ App.tsx: не удалось найти место для вставки e2e={e2e}")
                    print("     найди <ChatWindow ... и добавь e2e={e2e} вручную")

        # Проверка
        if app != app_orig:
            print(f"  ~ App.tsx обновлён")

    # ============================================================
    # Финальная проверка
    # ============================================================
    print()
    print("=" * 70)
    print("ПРОВЕРКА")
    print("=" * 70)

    if cw_tsx.exists():
        cw_new = cw_tsx.read_text(encoding="utf-8")
        print(f"  {'✓' if 'e2eApi' in cw_new else '✗'} ChatWindow: e2eApi fallback")
        print(f"  {'✓' if 'e2eApi.ready' in cw_new else '✗'} ChatWindow: e2eApi.ready")
        # не должно остаться голого e2e.ready
        bad_lines = [l for l in cw_new.split("\n") if re.search(r"\be2e\.ready\b", l)]
        if bad_lines:
            print(f"  ⚠ ChatWindow: остались строки с e2e.ready ({len(bad_lines)}):")
            for l in bad_lines:
                print(f"      {l.strip()}")

    if app_tsx.exists():
        app_new = app_tsx.read_text(encoding="utf-8")
        print(f"  {'✓' if 'e2e={e2e}' in app_new else '✗'} App.tsx: e2e={e2e} в <ChatWindow>")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())