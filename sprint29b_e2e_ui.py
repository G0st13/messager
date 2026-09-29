#!/usr/bin/env python3
"""sprint29b_e2e_ui.py - кнопка E2E в GroupInfoPanel."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
import shutil


# ==============================================================
# Патчи GroupInfoPanel.tsx
# ==============================================================
PATCHES = [
    # import
    (
        'import Avatar from "./Avatar";\n'
        'import { api } from "./api";\n'
        'import type { Chat, ChatMember, User } from "./types";',
        'import Avatar from "./Avatar";\n'
        'import { api } from "./api";\n'
        'import E2EIndicator from "./E2EIndicator";\n'
        'import E2ESetupModal from "./E2ESetupModal";\n'
        'import type { Chat, ChatMember, User, UseE2E } from "./types";',
    ),
    # props signature
    (
        'export default function GroupInfoPanel({\n'
        '  chat, currentUser, onClose, onChatUpdated, onLeft,\n'
        '}: {\n'
        '  chat: Chat;\n'
        '  currentUser: User;\n'
        '  onClose: () => void;\n'
        '  onChatUpdated: (c: Chat) => void;\n'
        '  onLeft: () => void;\n'
        '}) {',
        'export default function GroupInfoPanel({\n'
        '  chat, currentUser, useE2E, onClose, onChatUpdated, onLeft,\n'
        '}: {\n'
        '  chat: Chat;\n'
        '  currentUser: User;\n'
        '  useE2E: UseE2E;\n'
        '  onClose: () => void;\n'
        '  onChatUpdated: (c: Chat) => void;\n'
        '  onLeft: () => void;\n'
        '}) {',
    ),
    # state — модалка E2E + локальное "включено"
    (
        '  const [expandedPerms, setExpandedPerms] = useState<number | null>(null);',
        '  const [expandedPerms, setExpandedPerms] = useState<number | null>(null);\n'
        '  const [showE2ESetup, setShowE2ESetup] = useState(false);',
    ),
    # вычислить isOwner если нет (уже есть isOwner, но проверим)
    # добавляем блок E2E в JSX перед секцией // участники
    (
        '          {isGroup && (\n'
        '            <>\n'
        '              <div className="mb-2 text-[10px] uppercase tracking-widest text-cyber-cyan/70">\n'
        '                // участники ({members.length})\n'
        '              </div>',
        '          {isGroup && (\n'
        '            <div className="mb-4 rounded-sm border border-cyber-cyan/25 bg-cyber-cyan/5 p-3">\n'
        '              <div className="mb-2 flex items-center justify-between">\n'
        '                <div className="text-[10px] font-bold uppercase tracking-widest neon-text">\n'
        '                  🔒 E2E ENCRYPTION\n'
        '                </div>\n'
        '                <E2EIndicator\n'
        '                  enabled={chat.encryption_enabled}\n'
        '                  hasKey={chat.has_my_key}\n'
        '                  ready={useE2E.ready}\n'
        '                />\n'
        '              </div>\n'
        '\n'
        '              {chat.encryption_enabled ? (\n'
        '                <div className="text-[10px] text-cyber-dim leading-relaxed">\n'
        '                  Все новые сообщения шифруются сквозным шифрованием.\n'
        '                  Сервер видит только шифртекст.\n'
        '                  {!chat.has_my_key && (\n'
        '                    <span className="ml-1 text-cyber-magenta">\n'
        '                      У тебя нет ключа — попроси владельца выдать его.\n'
        '                    </span>\n'
        '                  )}\n'
        '                </div>\n'
        '              ) : isOwner ? (\n'
        '                <button\n'
        '                  onClick={() => setShowE2ESetup(true)}\n'
        '                  disabled={!useE2E.ready}\n'
        '                  className="cyber-btn w-full rounded-sm py-2 text-xs"\n'
        '                >\n'
        '                  {useE2E.ready ? "[ ВКЛЮЧИТЬ E2E ]" : "[ ИНИЦИАЛИЗАЦИЯ КЛЮЧЕЙ... ]"}\n'
        '                </button>\n'
        '              ) : (\n'
        '                <div className="text-[10px] text-cyber-dim">\n'
        '                  Владелец чата ещё не включил E2E.\n'
        '                </div>\n'
        '              )}\n'
        '            </div>\n'
        '          )}\n'
        '\n'
        '          {isGroup && (\n'
        '            <>\n'
        '              <div className="mb-2 text-[10px] uppercase tracking-widest text-cyber-cyan/70">\n'
        '                // участники ({members.length})\n'
        '              </div>',
    ),
    # рендер модалки в конце — перед закрывающим </div> root
    (
        '        {isGroup && (\n'
        '          <div className="border-t border-cyber-cyan/20 p-4">\n'
        '            <button\n'
        '              onClick={leave}\n'
        '              className="w-full rounded-sm border border-cyber-magenta/40 py-2 text-xs font-bold uppercase tracking-widest neon-text-mag hover:bg-cyber-magenta/15"\n'
        '            >\n'
        '              выйти\n'
        '            </button>\n'
        '          </div>\n'
        '        )}',
        '        {isGroup && (\n'
        '          <div className="border-t border-cyber-cyan/20 p-4">\n'
        '            <button\n'
        '              onClick={leave}\n'
        '              className="w-full rounded-sm border border-cyber-magenta/40 py-2 text-xs font-bold uppercase tracking-widest neon-text-mag hover:bg-cyber-magenta/15"\n'
        '            >\n'
        '              выйти\n'
        '            </button>\n'
        '          </div>\n'
        '        )}\n'
        '\n'
        '        {showE2ESetup && (\n'
        '          <E2ESetupModal\n'
        '            chat={chat}\n'
        '            useE2E={useE2E}\n'
        '            onClose={() => setShowE2ESetup(false)}\n'
        '            onEnabled={() => {\n'
        '              // перезагрузим chat с сервера\n'
        '              api.get<Chat>(`/chats/${chat.id}`).then((r) => onChatUpdated(r.data));\n'
        '            }}\n'
        '          />\n'
        '        )}',
    ),
]


# ==============================================================
# Патч App.tsx — пробросить e2e в GroupInfoPanel
# ==============================================================
APP_PATCHES = [
    (
        '            {showGroupInfo && activeChat && (\n'
        '              <GroupInfoPanel\n'
        '                chat={activeChat}\n'
        '                currentUser={user}\n'
        '                onClose={() => setShowGroupInfo(false)}\n'
        '                onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}\n'
        '                onLeft={() => { setActiveChatId(null); refreshChats(); }}\n'
        '              />\n'
        '            )}',
        '            {showGroupInfo && activeChat && (\n'
        '              <GroupInfoPanel\n'
        '                chat={activeChat}\n'
        '                currentUser={user}\n'
        '                useE2E={e2e}\n'
        '                onClose={() => setShowGroupInfo(false)}\n'
        '                onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}\n'
        '                onLeft={() => { setActiveChatId(null); refreshChats(); }}\n'
        '              />\n'
        '            )}',
    ),
]


# ==============================================================
# ChatWindow — использовать e2e для шифрования/расшифровки
# ==============================================================
# Это самая большая часть. Встраиваем реальное шифрование в doSend и расшифровку в useEffect.

CHATWINDOW_PATCHES = [
    # doSend: шифруем перед отправкой
    (
        '  const doSend = useCallback(() => {\n'
        '    const t = text.trim();\n'
        '    if (!t) return;\n'
        '    if (editing) {\n'
        '      send({ type: "edit", message_id: editing.id, text: t });\n'
        '      setEditing(null);\n'
        '    } else {\n'
        '      onEnqueue(chat.id, t, "text", null, replyTo?.id ?? null);\n'
        '      setReplyTo(null);\n'
        '    }\n'
        '    setText("");\n'
        '    send({ type: "typing", chat_id: chat.id, is_typing: false });\n'
        '  }, [text, editing, replyTo, chat.id, send, onEnqueue]);',
        '  const doSend = useCallback(async () => {\n'
        '    const t = text.trim();\n'
        '    if (!t) return;\n'
        '\n'
        '    // если E2E включён — шифруем на клиенте\n'
        '    let payloadText: string | null = t;\n'
        '    let encrypted = false;\n'
        '    if (chat.encryption_enabled && e2e.ready) {\n'
        '      const enc = await e2e.encryptForChat(chat, t);\n'
        '      if (!enc) {\n'
        '        alert("Не удалось зашифровать — нет ключа. Попроси владельца выдать ключ.");\n'
        '        return;\n'
        '      }\n'
        '      payloadText = enc;\n'
        '      encrypted = true;\n'
        '    }\n'
        '\n'
        '    if (editing) {\n'
        '      send({ type: "edit", message_id: editing.id, text: payloadText, encrypted });\n'
        '      setEditing(null);\n'
        '    } else {\n'
        '      onEnqueue(chat.id, payloadText, "text", null, replyTo?.id ?? null, encrypted);\n'
        '      setReplyTo(null);\n'
        '    }\n'
        '    setText("");\n'
        '    send({ type: "typing", chat_id: chat.id, is_typing: false });\n'
        '  }, [text, editing, replyTo, chat.id, send, onEnqueue, chat.encryption_enabled, e2e]);',
    ),
    # useEffect — расшифровываем входящие
    (
        '  // Все "виртуальные" сообщения = серверные + очередь',
        '  // Расшифровываем сообщения, у которых есть encrypted=true и ещё нет расшифровки\n'
        '  useEffect(() => {\n'
        '    if (!chat.encryption_enabled || !e2e.ready) return;\n'
        '    let cancelled = false;\n'
        '    (async () => {\n'
        '      const updates: Record<number, string> = {};\n'
        '      for (const m of messages) {\n'
        '        if (!m.encrypted || !m.text) continue;\n'
        '        if (decrypted[m.id] !== undefined) continue;\n'
        '        const pt = await e2e.decryptFromChat(chat, m.text);\n'
        '        if (cancelled) return;\n'
        '        if (pt !== null) updates[m.id] = pt;\n'
        '      }\n'
        '      if (Object.keys(updates).length) {\n'
        '        setDecrypted((prev) => ({ ...prev, ...updates }));\n'
        '      }\n'
        '    })();\n'
        '    return () => { cancelled = true; };\n'
        '  }, [messages, chat, e2e, decrypted]);\n'
        '\n'
        '  // Все "виртуальные" сообщения = серверные + очередь',
    ),
    # Подменяем text у MessageBubble на расшифрованный
    (
        '                    <MessageBubble\n'
        '                      msg={m}\n'
        '                      mine={m.author_id === currentUser.id}',
        '                    <MessageBubble\n'
        '                      msg={\n'
        '                        m.encrypted && decrypted[m.id] !== undefined\n'
        '                          ? { ...m, text: decrypted[m.id], encrypted: false }\n'
        '                          : m\n'
        '                      }\n'
        '                      mine={m.author_id === currentUser.id}',
    ),
]


# ==============================================================
# useMessageQueue — пробрасываем encrypted
# ==============================================================
QUEUE_PATCHES = [
    (
        '  attachment_id: number | null;\n'
        '  reply_to_id: number | null;\n'
        '  created_at: string;',
        '  attachment_id: number | null;\n'
        '  reply_to_id: number | null;\n'
        '  encrypted: boolean;\n'
        '  created_at: string;',
    ),
    (
        '  const enqueue = useCallback((\n'
        '    chatId: number,\n'
        '    text: string | null,\n'
        '    messageType: string,\n'
        '    attachmentId: number | null,\n'
        '    replyToId: number | null,\n'
        '    author: { id: number; username: string; display_name: string | null; avatar_color: string | null },\n'
        '  ): QueuedMessage => {\n'
        '    const msg: QueuedMessage = {\n'
        '      client_id: uuid(),\n'
        '      chat_id: chatId,\n'
        '      text,\n'
        '      message_type: messageType,\n'
        '      attachment_id: attachmentId,\n'
        '      reply_to_id: replyToId,\n'
        '      created_at: new Date().toISOString(),',
        '  const enqueue = useCallback((\n'
        '    chatId: number,\n'
        '    text: string | null,\n'
        '    messageType: string,\n'
        '    attachmentId: number | null,\n'
        '    replyToId: number | null,\n'
        '    author: { id: number; username: string; display_name: string | null; avatar_color: string | null },\n'
        '    encrypted: boolean = false,\n'
        '  ): QueuedMessage => {\n'
        '    const msg: QueuedMessage = {\n'
        '      client_id: uuid(),\n'
        '      chat_id: chatId,\n'
        '      text,\n'
        '      message_type: messageType,\n'
        '      attachment_id: attachmentId,\n'
        '      reply_to_id: replyToId,\n'
        '      encrypted,\n'
        '      created_at: new Date().toISOString(),',
    ),
    (
        '          wsSend({\n'
        '            type: "send",\n'
        '            client_id: msg.client_id,\n'
        '            chat_id: msg.chat_id,\n'
        '            text: msg.text,\n'
        '            message_type: msg.message_type,\n'
        '            attachment_id: msg.attachment_id,\n'
        '            reply_to_id: msg.reply_to_id,\n'
        '          });',
        '          wsSend({\n'
        '            type: "send",\n'
        '            client_id: msg.client_id,\n'
        '            chat_id: msg.chat_id,\n'
        '            text: msg.text,\n'
        '            message_type: msg.message_type,\n'
        '            attachment_id: msg.attachment_id,\n'
        '            reply_to_id: msg.reply_to_id,\n'
        '            encrypted: msg.encrypted,\n'
        '          });',
    ),
]


# ==============================================================
# ChatWindow — прокинуть encrypted в onEnqueue
# ==============================================================
CHATWINDOW_ENQUEUE_PATCH = [
    (
        '  onEnqueue: (chatId: number, text: string | null, messageType: string, attachmentId: number | null, replyToId: number | null) => void;',
        '  onEnqueue: (chatId: number, text: string | null, messageType: string, attachmentId: number | null, replyToId: number | null, encrypted?: boolean) => void;',
    ),
]


# ==============================================================
# App.tsx — обновляем enqueueForChat
# ==============================================================
APP_ENQUEUE_PATCH = [
    (
        '      const enqueueForChat = useCallback((\n'
        '        chatId: number, text: string | null, messageType: string,\n'
        '        attachmentId: number | null, replyToId: number | null,\n'
        '      ) => {\n'
        '        if (!user) return;\n'
        '        queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {\n'
        '          id: user.id, username: user.username,\n'
        '          display_name: user.display_name,\n'
        '          avatar_color: user.avatar_color,\n'
        '        });\n'
        '      }, [queue, user]);',
        '      const enqueueForChat = useCallback((\n'
        '        chatId: number, text: string | null, messageType: string,\n'
        '        attachmentId: number | null, replyToId: number | null,\n'
        '        encrypted: boolean = false,\n'
        '      ) => {\n'
        '        if (!user) return;\n'
        '        queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {\n'
        '          id: user.id, username: user.username,\n'
        '          display_name: user.display_name,\n'
        '          avatar_color: user.avatar_color,\n'
        '        }, encrypted);\n'
        '      }, [queue, user]);',
    ),
]


FILES_TO_BACKUP = [
    "frontend/src/GroupInfoPanel.tsx",
    "frontend/src/App.tsx",
    "frontend/src/ChatWindow.tsx",
    "frontend/src/useMessageQueue.ts",
]


def create_backup(root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    for rel in FILES_TO_BACKUP:
        src = root / rel
        if src.exists():
            dst = backup / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (backup / "MANIFEST.txt").write_text(
        f"Backup {ts}\n" + "\n".join(FILES_TO_BACKUP) + "\n",
        encoding="utf-8",
    )
    return backup


def apply_patch(path: Path, pairs: list[tuple[str, str]]) -> tuple[int, int]:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0, len(pairs)
    text = path.read_text(encoding="utf-8")
    ok = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            ok += 1
    if ok:
        path.write_text(text, encoding="utf-8")
    status = "OK" if ok == len(pairs) else "ЧАСТИЧНО"
    print(f"  ~ {path.name} [{status} {ok}/{len(pairs)}]")
    return ok, len(pairs)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-backup", action="store_true")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    fe = root / "frontend" / "src"

    if not args.no_backup:
        backup = create_backup(root)
        print(f"\n📦 Бэкап: {backup}\n")

    print("Патчи:")
    apply_patch(fe / "GroupInfoPanel.tsx", PATCHES)
    apply_patch(fe / "App.tsx", APP_PATCHES)
    apply_patch(fe / "App.tsx", APP_ENQUEUE_PATCH)
    apply_patch(fe / "ChatWindow.tsx", CHATWINDOW_PATCHES)
    apply_patch(fe / "ChatWindow.tsx", CHATWINDOW_ENQUEUE_PATCH)
    apply_patch(fe / "useMessageQueue.ts", QUEUE_PATCHES)

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    print()
    print("Проверка E2E:")
    print("  1. Открой группу → ⚙ → должна появиться секция 🔒 E2E ENCRYPTION")
    print("  2. Если ты owner — кнопка [ ВКЛЮЧИТЬ E2E ]")
    print("  3. Нажми → сообщения начнут шифроваться")
    print("  4. Отправь текст → в БД увидишь e2e:1:... вместо plaintext")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())