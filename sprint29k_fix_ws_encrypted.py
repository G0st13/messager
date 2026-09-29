#!/usr/bin/env python3
"""sprint29k_fix_ws_encrypted.py - прокидывает encrypted из WS в state."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# Ищем блок в обработчике WS, где добавляется новое сообщение
OLD_1 = '''              return [...prev, {
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
              }];'''

NEW_1 = '''              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                client_id: d.client_id || null,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, is_pinned: false,
                encrypted: d.encrypted || false,
                reactions: d.reactions || [],
                created_at: d.created_at,
              }];'''

# Альтернативный якорь — без client_id
OLD_2 = '''              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, is_pinned: false,
                reactions: d.reactions || [],
                created_at: d.created_at,
              }];'''

NEW_2 = '''              return [...prev, {
                id: d.id, chat_id: d.chat_id,
                author_id: d.author_id, author_username: d.author_username,
                author_display: d.author_display, author_avatar_color: d.author_avatar_color,
                text: d.text, message_type: d.message_type || "text",
                attachment: d.attachment || null,
                reply_to_id: d.reply_to_id,
                reply_preview: d.reply_preview, reply_author: d.reply_author,
                edited_at: null, is_deleted: false, is_pinned: false,
                encrypted: d.encrypted || false,
                reactions: d.reactions || [],
                created_at: d.created_at,
              }];'''


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    cw = root / "frontend" / "src" / "ChatWindow.tsx"
    if not cw.exists():
        print(f"ERR: {cw} не найдено", file=sys.stderr)
        return 1

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cw, b / "ChatWindow.tsx")
    print(f"📦 Бэкап: {b}\n")

    text = cw.read_text(encoding="utf-8")

    if 'encrypted: d.encrypted' in text:
        print("  > уже применено")
        return 0

    applied = False
    for old, new in [(OLD_1, NEW_1), (OLD_2, NEW_2)]:
        if old in text:
            text = text.replace(old, new, 1)
            print(f"  ~ ChatWindow.tsx: добавлено encrypted в WS-обработчик")
            applied = True
            break

    if not applied:
        # Запасной вариант — regex: ищем return [...prev, {...}] внутри обработчика WS
        import re
        # Ищем блок с "is_pinned: false," в контексте добавления нового сообщения
        pattern = re.compile(
            r"(return\s+\[\.\.\.prev,\s*\{\s*\n\s+id:\s*d\.id,\s*chat_id:\s*d\.chat_id,\s*\n"
            r"(?:.*\n)*?"
            r"(\s+)edited_at:\s*null,\s*is_deleted:\s*false,\s*is_pinned:\s*false,\s*\n)"
            r"(\s+)reactions:",
            re.MULTILINE,
        )
        m = pattern.search(text)
        if m:
            indent1 = m.group(2)
            insert = f"{indent1}encrypted: d.encrypted || false,\n"
            pos = m.end(2)  # после "is_pinned: false,\n" (до reactions)
            # Вставим перед строкой "reactions:"
            text = text[:m.start(2)] + insert + text[m.start(2):]
            cw.write_text(text, encoding="utf-8")
            print(f"  ~ ChatWindow.tsx: применено через regex-fallback")
            applied = True
        else:
            print(f"  ✗ не нашёл блок. Пришли текущий фрагмент из ChatWindow.tsx")
            print(f"     Ищи 'is_pinned: false,' внутри 'return [...prev,'")
            # Покажем что есть
            for i, line in enumerate(text.split("\n"), 1):
                if "is_pinned: false" in line:
                    for j in range(max(0, i-15), min(len(text.split("\n")), i+5)):
                        print(f"     {j+1:4d} | {text.split(chr(10))[j]}")
                    break
            return 1

    cw.write_text(text, encoding="utf-8")
    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up -d")
    print()
    print("После сборки Ctrl+Shift+R. Отправь новое сообщение — должно расшифроваться.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())