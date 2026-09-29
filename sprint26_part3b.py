#!/usr/bin/env python3
"""sprint26_part3b.py - точные патчи MessageBubble.tsx."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PATCHES = [
    # 1. деструктуризация props — добавляем chatIsChannel и onOpenComments
    (
        "  msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, onRetry, readByPeer,\n"
        "  onOpenImage, onOpenProfile, onReact, onPin\n"
        "}: {",
        "  msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, onRetry, readByPeer,\n"
        "  onOpenImage, onOpenProfile, onReact, onPin,\n"
        "  chatIsChannel = false, onOpenComments\n"
        "}: {",
    ),

    # 2. тип props — добавляем те же поля
    (
        "  onReact: (messageId: number, emoji: string) => void;\n"
        "  onPin: (m: Message) => void;\n"
        "}) {",
        "  onReact: (messageId: number, emoji: string) => void;\n"
        "  onPin: (m: Message) => void;\n"
        "  chatIsChannel?: boolean;\n"
        "  onOpenComments?: (m: Message) => void;\n"
        "}) {",
    ),

    # 3. кнопка комментариев — вставляем ПЕРЕД блоком с меткой времени
    # Якорь: блок с цифрой времени, отсчёт от "<div className=\"mt-0.5"
    # В реальном файле он выглядит иначе, найдём по уникальной строке "new Date(msg.created_at).toLocaleTimeString"
    (
        "              <div className=\"mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider\">\n"
        "                {msg.edited_at && <span className=\"text-cyber-yellow/70\">[edited]</span>}",
        "              {chatIsChannel && !msg.reply_to_id && !msg.is_deleted && onOpenComments && (\n"
        "                <button\n"
        "                  className=\"post-comments-btn\"\n"
        "                  onClick={(e) => { e.stopPropagation(); onOpenComments(msg); }}\n"
        "                >\n"
        "                  ◈ открыть комментарии\n"
        "                </button>\n"
        "              )}\n"
        "              <div className=\"mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider\">\n"
        "                {msg.edited_at && <span className=\"text-cyber-yellow/70\">[edited]</span>}",
    ),
]


# Альтернативный якорь для #3 — если у пользователя строка mt-0.5 вместо mt-1
PATCHES_ALT_3 = [
    (
        "<div className=\"mt-0.5 flex items-center justify-end gap-2 text-[10px] uppercase tracking-wider\">",
        "PLACEHOLDER_MT05",
    ),
]


def try_patches(text: str, pairs: list[tuple[str, str]]) -> tuple[str, int, int]:
    applied = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            applied += 1
    return text, applied, len(pairs)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    target = root / "frontend" / "src" / "MessageBubble.tsx"
    if not target.exists():
        print(f"ERR: {target} не найдено.", file=sys.stderr)
        return 1

    text = target.read_text(encoding="utf-8")
    original = text

    text, ok, total = try_patches(text, PATCHES)
    print(f"  Основные патчи: {ok}/{total}")

    if ok < 3:
        # попробуем альтернативный якорь для #3
        # вставим кнопку через позицию — находим `mt-0.5 flex items-center justify-end`
        for marker in [
            '<div className="mt-0.5 flex items-center justify-end gap-2 text-[10px] uppercase tracking-wider">',
            '<div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">',
            '<div className="mt-0.5 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">',
        ]:
            if marker in text and "post-comments-btn" not in text:
                comment_btn = (
                    '              {chatIsChannel && !msg.reply_to_id && !msg.is_deleted && onOpenComments && (\n'
                    '                <button\n'
                    '                  className="post-comments-btn"\n'
                    '                  onClick={(e) => { e.stopPropagation(); onOpenComments(msg); }}\n'
                    '                >\n'
                    '                  ◈ открыть комментарии\n'
                    '                </button>\n'
                    '              )}\n'
                )
                text = text.replace(marker, comment_btn + marker, 1)
                ok += 1
                print(f"  → использован альтернативный якорь для кнопки: OK")
                break

    if text != original:
        target.write_text(text, encoding="utf-8")
        print(f"  ~ {target}")
    else:
        print(f"  > {target} — без изменений")

    print()
    # Проверка
    check = target.read_text(encoding="utf-8")
    print("Проверка:")
    print(f"  chatIsChannel в props:  {'OK' if 'chatIsChannel?: boolean' in check else 'НЕТ'}")
    print(f"  onOpenComments в props: {'OK' if 'onOpenComments?:' in check else 'НЕТ'}")
    print(f"  деструктуризация:       {'OK' if 'chatIsChannel = false' in check else 'НЕТ'}")
    print(f"  кнопка comments:        {'OK' if 'post-comments-btn' in check else 'НЕТ'}")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())