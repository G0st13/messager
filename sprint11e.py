#!/usr/bin/env python3
"""sprint11e.py - delete/retry failed queued messages."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


CHATWINDOW_REPLACEMENTS = [
    # onDelete: для virtual (id<0, есть client_id) — удаление из очереди
    (
        '  const onDelete = useCallback((mm: Message) => send({ type: "delete", message_id: mm.id }), [send]);',
        '  const onDelete = useCallback((mm: Message) => {\n'
        '    if (mm.id < 0 && mm.client_id) {\n'
        '      onRemoveQueued(mm.client_id);\n'
        '      return;\n'
        '    }\n'
        '    send({ type: "delete", message_id: mm.id });\n'
        '  }, [send, onRemoveQueued]);\n'
        '\n'
        '  const onRetry = useCallback((mm: Message) => {\n'
        '    if (mm.id < 0 && mm.client_id) {\n'
        '      // убираем из failed — useMessageQueue сам попробует снова\n'
        '      onRetryQueued(mm.client_id);\n'
        '    }\n'
        '  }, [onRetryQueued]);',
    ),
    # prop signature — добавим onRetryQueued
    (
        '  onRemoveQueued: (clientId: string) => void;\n'
        '}) {',
        '  onRemoveQueued: (clientId: string) => void;\n'
        '  onRetryQueued: (clientId: string) => void;\n'
        '}) {',
    ),
    (
        '  queuedMessages, onEnqueue, onRemoveQueued,\n'
        '}: {',
        '  queuedMessages, onEnqueue, onRemoveQueued, onRetryQueued,\n'
        '}: {',
    ),
    # передать onRetry в MessageBubble
    (
        '                      onReply={onReply}\n'
        '                      onEdit={onEdit}\n'
        '                      onDelete={onDelete}\n'
        '                      onOpenImage={onOpenImage}',
        '                      onReply={onReply}\n'
        '                      onEdit={onEdit}\n'
        '                      onDelete={onDelete}\n'
        '                      onRetry={onRetry}\n'
        '                      onOpenImage={onOpenImage}',
    ),
]


MESSAGEBUBBLE_REPLACEMENTS = [
    # prop signature
    (
        '  onDelete: (m: Message) => void;\n'
        '  readByPeer: boolean;',
        '  onDelete: (m: Message) => void;\n'
        '  onRetry: (m: Message) => void;\n'
        '  readByPeer: boolean;',
    ),
    (
        '  onReply, onEdit, onDelete, readByPeer,',
        '  onReply, onEdit, onDelete, onRetry, readByPeer,',
    ),
    (
        '  onReply: (m: Message) => void;\n'
        '  onEdit: (m: Message) => void;\n'
        '  onDelete: (m: Message) => void;\n'
        '  onRetry: (m: Message) => void;',
        '  onReply: (m: Message) => void;\n'
        '  onEdit: (m: Message) => void;\n'
        '  onDelete: (m: Message) => void;\n'
        '  onRetry: (m: Message) => void;',
    ),
    # Показываем hover-actions для failed виртуальных
    (
        '{!msg.is_deleted && !isVirtual && (\n'
        '          <div\n'
        '            className={\n'
        '              "absolute top-1 hidden items-center gap-1 group-hover:flex " +\n'
        '              (mine ? "right-full mr-1" : "left-full ml-1")\n'
        '            }\n'
        '          >\n'
        '            <button\n'
        '              onClick={() => setReactOpen(!reactOpen)}\n'
        '              className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"\n'
        '              title="Reaction"\n'
        '            >\n'
        '              ☺\n'
        '            </button>\n'
        '            <button\n'
        '              onClick={() => setMenuOpen(!menuOpen)}\n'
        '              className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"\n'
        '              title="Menu"\n'
        '            >\n'
        '              ▾\n'
        '            </button>\n'
        '          </div>\n'
        '        )}',
        '{!msg.is_deleted && (!isVirtual || isFailed) && (\n'
        '          <div\n'
        '            className={\n'
        '              "absolute top-1 hidden items-center gap-1 group-hover:flex " +\n'
        '              (mine ? "right-full mr-1" : "left-full ml-1")\n'
        '            }\n'
        '          >\n'
        '            {!isVirtual && (\n'
        '              <button\n'
        '                onClick={() => setReactOpen(!reactOpen)}\n'
        '                className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"\n'
        '                title="Reaction"\n'
        '              >\n'
        '                ☺\n'
        '              </button>\n'
        '            )}\n'
        '            <button\n'
        '              onClick={() => setMenuOpen(!menuOpen)}\n'
        '              className={\n'
        '                "rounded-sm border px-1.5 py-0.5 text-xs panel-solid " +\n'
        '                (isFailed\n'
        '                  ? "border-cyber-magenta/50 text-cyber-magenta hover:bg-cyber-magenta/20"\n'
        '                  : "border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/20")\n'
        '              }\n'
        '              title="Menu"\n'
        '            >\n'
        '              ▾\n'
        '            </button>\n'
        '          </div>\n'
        '        )}',
    ),
    # В меню — для failed virtual показываем retry + delete, остальное скрываем
    (
        '{menuOpen && (\n'
        '          <div\n'
        '            className={\n'
        '              "absolute z-20 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +\n'
        '              (mine ? "right-0" : "left-0")\n'
        '            }\n'
        '          >\n'
        '            <button\n'
        '              onClick={() => { onReply(msg); setMenuOpen(false); }}\n'
        '              className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"\n'
        '            >\n'
        '              ↳ reply\n'
        '            </button>\n'
        '            <button\n'
        '              onClick={() => { onPin(msg); setMenuOpen(false); }}\n'
        '              className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-yellow hover:bg-cyber-yellow/15"\n'
        '            >\n'
        '              📌 {msg.is_pinned ? "unpin" : "pin"}\n'
        '            </button>\n'
        '            {mine && msg.message_type === "text" && (\n'
        '              <button\n'
        '                onClick={() => { onEdit(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"\n'
        '              >\n'
        '                ✎ edit\n'
        '              </button>\n'
        '            )}\n'
        '            {mine && (\n'
        '              <button\n'
        '                onClick={() => { onDelete(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"\n'
        '              >\n'
        '                ✕ delete\n'
        '              </button>\n'
        '            )}\n'
        '          </div>\n'
        '        )}',
        '{menuOpen && (\n'
        '          isVirtual && isFailed ? (\n'
        '            <div\n'
        '              className={\n'
        '                "absolute z-20 mt-1 w-40 overflow-hidden rounded-sm border border-cyber-magenta/60 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }\n'
        '            >\n'
        '              <div className="border-b border-cyber-magenta/30 bg-cyber-magenta/10 px-3 py-1.5 text-[9px] uppercase tracking-widest neon-text-mag">\n'
        '                ⚠ не отправлено\n'
        '              </div>\n'
        '              <button\n'
        '                onClick={() => { onRetry(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"\n'
        '              >\n'
        '                ↻ retry\n'
        '              </button>\n'
        '              <button\n'
        '                onClick={() => { onDelete(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"\n'
        '              >\n'
        '                ✕ удалить\n'
        '              </button>\n'
        '            </div>\n'
        '          ) : (\n'
        '            <div\n'
        '              className={\n'
        '                "absolute z-20 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +\n'
        '                (mine ? "right-0" : "left-0")\n'
        '              }\n'
        '            >\n'
        '              <button\n'
        '                onClick={() => { onReply(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"\n'
        '              >\n'
        '                ↳ reply\n'
        '              </button>\n'
        '              <button\n'
        '                onClick={() => { onPin(msg); setMenuOpen(false); }}\n'
        '                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-yellow hover:bg-cyber-yellow/15"\n'
        '              >\n'
        '                📌 {msg.is_pinned ? "unpin" : "pin"}\n'
        '              </button>\n'
        '              {mine && msg.message_type === "text" && (\n'
        '                <button\n'
        '                  onClick={() => { onEdit(msg); setMenuOpen(false); }}\n'
        '                  className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"\n'
        '                >\n'
        '                  ✎ edit\n'
        '                </button>\n'
        '              )}\n'
        '              {mine && (\n'
        '                <button\n'
        '                  onClick={() => { onDelete(msg); setMenuOpen(false); }}\n'
        '                  className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"\n'
        '                >\n'
        '                  ✕ delete\n'
        '                </button>\n'
        '              )}\n'
        '            </div>\n'
        '          )\n'
        '        )}',
    ),
    # Добавляем inline-подсказку под бабблом failed
    (
        '<div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">\n'
        '            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}',
        '{isVirtual && isFailed && (\n'
        '            <div className="mt-1.5 flex items-center justify-between gap-2 border-t border-cyber-magenta/30 pt-1 text-[9px] uppercase tracking-widest">\n'
        '              <span className="neon-text-mag">⚠ not sent</span>\n'
        '              <span className="text-cyber-dim">наведи → ⋮</span>\n'
        '            </div>\n'
        '          )}\n'
        '          <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">\n'
        '            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}',
    ),
]


# useMessageQueue — добавим функцию retryOne
USEQUEUE_REPLACEMENTS = [
    (
        '  const retryFailed = useCallback(() => {\n'
        '    setQueue((prev) => prev.map((m) =>\n'
        '      m.status === "failed"\n'
        '        ? { ...m, status: "pending", attempts: 0, next_try_at: 0 }\n'
        '        : m\n'
        '    ));\n'
        '  }, []);',
        '  const retryFailed = useCallback(() => {\n'
        '    setQueue((prev) => prev.map((m) =>\n'
        '      m.status === "failed"\n'
        '        ? { ...m, status: "pending", attempts: 0, next_try_at: 0 }\n'
        '        : m\n'
        '    ));\n'
        '  }, []);\n'
        '\n'
        '  const retryOne = useCallback((clientId: string) => {\n'
        '    setQueue((prev) => prev.map((m) =>\n'
        '      m.client_id === clientId\n'
        '        ? { ...m, status: "pending", attempts: 0, next_try_at: 0 }\n'
        '        : m\n'
        '    ));\n'
        '  }, []);',
    ),
    (
        '  return {\n'
        '    queue,\n'
        '    enqueue,\n'
        '    removeByClientId,\n'
        '    retryFailed,\n'
        '    clearFailed,\n'
        '  };',
        '  return {\n'
        '    queue,\n'
        '    enqueue,\n'
        '    removeByClientId,\n'
        '    retryFailed,\n'
        '    retryOne,\n'
        '    clearFailed,\n'
        '  };',
    ),
]


# App — прокинем retryOne в ChatWindow
APP_REPLACEMENTS = [
    (
        '                  queuedMessages={queue.queue}\n'
        '                  onEnqueue={enqueueForChat}\n'
        '                  onRemoveQueued={queue.removeByClientId}\n'
        '                />',
        '                  queuedMessages={queue.queue}\n'
        '                  onEnqueue={enqueueForChat}\n'
        '                  onRemoveQueued={queue.removeByClientId}\n'
        '                  onRetryQueued={queue.retryOne}\n'
        '                />',
    ),
]


def patch_file(path: Path, pairs: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path}")
    else:
        print(f"  > {path} (без изменений)")
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

    print("\nСпринт 11e — удаление и retry неудачных сообщений\n")

    src = root / "frontend" / "src"

    patch_file(src / "ChatWindow.tsx", CHATWINDOW_REPLACEMENTS)
    patch_file(src / "MessageBubble.tsx", MESSAGEBUBBLE_REPLACEMENTS)
    patch_file(src / "useMessageQueue.ts", USEQUEUE_REPLACEMENTS)
    patch_file(src / "App.tsx", APP_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())