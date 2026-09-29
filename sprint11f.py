#!/usr/bin/env python3
"""sprint11f.py - fix context menu layering."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


CSS_REPLACEMENTS = [
    # Убираем contain: paint из .msg-scroll — он обрезает выпадающие меню
    (
        '    .msg-scroll {\n'
        '      contain: layout style paint;\n'
        '      overflow-anchor: none;\n'
        '      transform: translate3d(0, 0, 0);\n'
        '      backface-visibility: hidden;\n'
        '    }\n'
        '\n'
        '    /* Внутри — тоже изолируем */\n'
        '    .msg-scroll > * {\n'
        '      contain: layout style paint;\n'
        '    }\n'
        '\n'
        '    /* Отдельные сообщения — не влияют на layout выше */\n'
        '    .msg-item {\n'
        '      contain: layout style;\n'
        '    }',
        '    .msg-scroll {\n'
        '      /* contain: paint ОБРЕЗАЕТ выпадающие меню — убираем */\n'
        '      contain: layout style;\n'
        '      overflow-anchor: none;\n'
        '      transform: translate3d(0, 0, 0);\n'
        '      backface-visibility: hidden;\n'
        '      overflow-x: visible;\n'
        '      overflow-y: auto;\n'
        '    }\n'
        '\n'
        '    /* Обёртки сообщений — без paint-clipping */\n'
        '    .msg-scroll > * {\n'
        '      contain: layout;\n'
        '    }\n'
        '\n'
        '    .msg-item {\n'
        '      contain: layout;\n'
        '      position: relative;\n'
        '    }\n'
        '\n'
        '    /* Когда у сообщения открыто меню — поднимаем весь его контейнер выше соседей */\n'
        '    .msg-item.menu-open {\n'
        '      z-index: 40;\n'
        '    }\n'
        '\n'
        '    /* Слой для вложенных absolute-меню */\n'
        '    .msg-layer-high {\n'
        '      z-index: 50 !important;\n'
        '    }',
    ),
]


CHATWINDOW_REPLACEMENTS = [
    # пробрасываем state открытости меню наверх через callback
    (
        '                    <MessageBubble\n'
        '                      msg={m}\n'
        '                      mine={m.author_id === currentUser.id}\n'
        '                      showAvatar={showAvatar}\n'
        '                      isLast={isLast}\n'
        '                      readByPeer={peerReadUpTo >= m.id}\n'
        '                      onReply={onReply}\n'
        '                      onEdit={onEdit}\n'
        '                      onDelete={onDelete}\n'
        '                      onRetry={onRetry}\n'
        '                      onOpenImage={onOpenImage}\n'
        '                      onOpenProfile={onOpenUser}\n'
        '                      onReact={handleReact}\n'
        '                      onPin={handlePin}\n'
        '                    />',
        '                    <MessageBubble\n'
        '                      msg={m}\n'
        '                      mine={m.author_id === currentUser.id}\n'
        '                      showAvatar={showAvatar}\n'
        '                      isLast={isLast}\n'
        '                      readByPeer={peerReadUpTo >= m.id}\n'
        '                      onReply={onReply}\n'
        '                      onEdit={onEdit}\n'
        '                      onDelete={onDelete}\n'
        '                      onRetry={onRetry}\n'
        '                      onOpenImage={onOpenImage}\n'
        '                      onOpenProfile={onOpenUser}\n'
        '                      onReact={handleReact}\n'
        '                      onPin={handlePin}\n'
        '                      onMenuOpenChange={(open) => {\n'
        '                        const el = document.getElementById(`item-${m.client_id || m.id}`);\n'
        '                        if (el) el.classList.toggle("menu-open", open);\n'
        '                      }}\n'
        '                    />',
    ),
    # даём обёртке id
    (
        '                  <div\n'
        '                    key={m.client_id || m.id}\n'
        '                    className={"msg-item " + (isHighlighted ? "ring-2 ring-cyber-yellow" : "")}\n'
        '                  >',
        '                  <div\n'
        '                    key={m.client_id || m.id}\n'
        '                    id={`item-${m.client_id || m.id}`}\n'
        '                    className={"msg-item " + (isHighlighted ? "ring-2 ring-cyber-yellow" : "")}\n'
        '                  >',
    ),
]


MESSAGEBUBBLE_REPLACEMENTS = [
    # prop в сигнатуру
    (
        '  onReact: (messageId: number, emoji: string) => void;\n'
        '  onPin: (m: Message) => void;\n'
        '}) {',
        '  onReact: (messageId: number, emoji: string) => void;\n'
        '  onPin: (m: Message) => void;\n'
        '  onMenuOpenChange?: (open: boolean) => void;\n'
        '}) {',
    ),
    (
        '  onReply, onEdit, onDelete, onRetry, readByPeer,\n'
        '  onOpenImage, onOpenProfile, onReact, onPin\n'
        '}: {',
        '  onReply, onEdit, onDelete, onRetry, readByPeer,\n'
        '  onOpenImage, onOpenProfile, onReact, onPin, onMenuOpenChange\n'
        '}: {',
    ),
    # Сообщаем родителю, когда меню открыто (menuOpen ИЛИ reactOpen)
    (
        '  const sendStatus = msg.send_status;\n'
        '  const isPending = sendStatus === "pending";',
        '  // сообщаем родителю для поднятия z-index обёртки\n'
        '  useEffect(() => {\n'
        '    onMenuOpenChange?.(menuOpen || reactOpen);\n'
        '  }, [menuOpen, reactOpen, onMenuOpenChange]);\n'
        '\n'
        '  const sendStatus = msg.send_status;\n'
        '  const isPending = sendStatus === "pending";',
    ),
    # Импорт useEffect
    (
        'import { memo, useState } from "react";',
        'import { memo, useEffect, useState } from "react";',
    ),
    # Меню реакции: z-30 → z-50
    (
        '            className={\n'
        '              "absolute top-8 z-30 flex gap-1 rounded-sm border border-cyber-cyan/50 panel-solid p-1 " +\n'
        '              (mine ? "right-0" : "left-0")\n'
        '            }',
        '            className={\n'
        '              "msg-layer-high absolute top-8 flex gap-1 rounded-sm border border-cyber-cyan/50 panel-solid p-1 " +\n'
        '              (mine ? "right-0" : "left-0")\n'
        '            }',
    ),
    # Основное меню: z-20 → z-50 (обе ветки — failed и обычная)
    (
        '              className={\n'
        '                "absolute z-20 mt-1 w-40 overflow-hidden rounded-sm border border-cyber-magenta/60 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }',
        '              className={\n'
        '                "msg-layer-high absolute mt-1 w-40 overflow-hidden rounded-sm border border-cyber-magenta/60 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }',
    ),
    (
        '              className={\n'
        '                "absolute z-20 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }',
        '              className={\n'
        '                "msg-layer-high absolute mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }',
    ),
    # Кнопки-триггеры тоже поднимаем и делаем более заметные
    (
        '          <div\n'
        '            className={\n'
        '              "absolute top-1 hidden items-center gap-1 group-hover:flex " +\n'
        '              (mine ? "right-full mr-1" : "left-full ml-1")\n'
        '            }\n'
        '          >',
        '          <div\n'
        '            className={\n'
        '              "absolute top-1 z-30 hidden items-center gap-1 group-hover:flex " +\n'
        '              (mine ? "right-full mr-1" : "left-full ml-1")\n'
        '            }\n'
        '          >',
    ),
]


def patch_file(path: Path, pairs: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if new.strip() and new.strip() in text:
            continue  # уже применено
        if old in text:
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path}")
    else:
        print(f"  > {path} (без изменений — возможно, уже пропатчено)")
    return changed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 11f — fix: контекстное меню поверх сообщений\n")

    src = root / "frontend" / "src"

    patch_file(src / "index.css", CSS_REPLACEMENTS)
    patch_file(src / "ChatWindow.tsx", CHATWINDOW_REPLACEMENTS)
    patch_file(src / "MessageBubble.tsx", MESSAGEBUBBLE_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())