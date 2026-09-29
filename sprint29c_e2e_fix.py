#!/usr/bin/env python3
"""sprint29c_e2e_fix.py - точечные фиксы sprint29b."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


def apply_patch(path: Path, pairs: list[tuple[str, str]], label: str = "") -> tuple[int, int]:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0, len(pairs)
    text = path.read_text(encoding="utf-8")
    ok = 0
    for old, new in pairs:
        if new.strip() and new.strip() in text:
            # уже применено
            ok += 1
            continue
        if old in text:
            text = text.replace(old, new, 1)
            ok += 1
    if ok:
        path.write_text(text, encoding="utf-8")
    status = "OK" if ok == len(pairs) else "ЧАСТИЧНО"
    print(f"  ~ {path.name} [{status} {ok}/{len(pairs)}] {label}")
    return ok, len(pairs)


# ==============================================================
# FIX 1: App.tsx — порядок аргументов + передать e2e в GroupInfoPanel
# ==============================================================
APP_FIXES = [
    # 1a. queue.enqueue — переставить author и encrypted
    (
        '    queue.enqueue(chatId, text, messageType, attachmentId, replyToId, encrypted, {\n'
        '      id: user.id, username: user.username,\n'
        '      display_name: user.display_name,\n'
        '      avatar_color: user.avatar_color,\n'
        '    });',
        '    queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {\n'
        '      id: user.id, username: user.username,\n'
        '      display_name: user.display_name,\n'
        '      avatar_color: user.avatar_color,\n'
        '    }, encrypted);',
    ),
    # 1b. GroupInfoPanel — добавить useE2E
    (
        '          <GroupInfoPanel\n'
        '            chat={activeChat}\n'
        '            currentUser={user}\n'
        '            onClose={() => setShowGroupInfo(false)}\n'
        '            onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}\n'
        '            onLeft={() => { setActiveChatId(null); refreshChats(); }}\n'
        '          />',
        '          <GroupInfoPanel\n'
        '            chat={activeChat}\n'
        '            currentUser={user}\n'
        '            useE2E={e2e}\n'
        '            onClose={() => setShowGroupInfo(false)}\n'
        '            onChatUpdated={(c) => { setChats((prev) => prev.map((x) => x.id === c.id ? c : x)); }}\n'
        '            onLeft={() => { setActiveChatId(null); refreshChats(); }}\n'
        '          />',
    ),
]


# ==============================================================
# FIX 2: useMessageQueue.ts — передать encrypted в wsSend
# ==============================================================
QUEUE_FIXES = [
    (
        '      wsSend({\n'
        '        type: "send",\n'
        '        client_id: msg.client_id,\n'
        '        chat_id: msg.chat_id,\n'
        '        text: msg.text,\n'
        '        message_type: msg.message_type,\n'
        '        attachment_id: msg.attachment_id,\n'
        '        reply_to_id: msg.reply_to_id,\n'
        '      });',
        '      wsSend({\n'
        '        type: "send",\n'
        '        client_id: msg.client_id,\n'
        '        chat_id: msg.chat_id,\n'
        '        text: msg.text,\n'
        '        message_type: msg.message_type,\n'
        '        attachment_id: msg.attachment_id,\n'
        '        reply_to_id: msg.reply_to_id,\n'
        '        encrypted: (msg as any).encrypted || false,\n'
        '      });',
    ),
]


# ==============================================================
# FIX 3: ChatWindow.tsx — добавить useEffect расшифровки если нет
# ==============================================================
CHATWINDOW_FIXES = [
    # вставляем useEffect расшифровки перед "const allMessages"
    (
        '  const allMessages: Message[] = useMemo(() => {',
        '  // ---- E2E: расшифровка входящих зашифрованных сообщений ----\n'
        '  useEffect(() => {\n'
        '    if (!chat.encryption_enabled || !e2e.ready) return;\n'
        '    let cancelled = false;\n'
        '    (async () => {\n'
        '      const updates: Record<number, string> = {};\n'
        '      for (const m of messages) {\n'
        '        if (!m.encrypted || !m.text) continue;\n'
        '        if (decrypted[m.id] !== undefined) continue;\n'
        '        try {\n'
        '          const pt = await e2e.decryptFromChat(chat, m.text);\n'
        '          if (cancelled) return;\n'
        '          if (pt !== null) updates[m.id] = pt;\n'
        '        } catch {}\n'
        '      }\n'
        '      if (!cancelled && Object.keys(updates).length > 0) {\n'
        '        setDecrypted((prev) => ({ ...prev, ...updates }));\n'
        '      }\n'
        '    })();\n'
        '    return () => { cancelled = true; };\n'
        '  }, [messages, chat, e2e, decrypted]);\n'
        '\n'
        '  const allMessages: Message[] = useMemo(() => {',
    ),
]


def backup(root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    for rel in ["frontend/src/App.tsx", "frontend/src/ChatWindow.tsx", "frontend/src/useMessageQueue.ts"]:
        src = root / rel
        if src.exists():
            dst = b / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"\n📦 Бэкап: {b}\n")
    return b


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
        backup(root)

    print("Патчи:")
    apply_patch(fe / "App.tsx", APP_FIXES, "[arg order + e2e prop]")
    apply_patch(fe / "useMessageQueue.ts", QUEUE_FIXES, "[encrypted in wsSend]")

    # ChatWindow — аккуратно, только если ещё нет
    cw_path = fe / "ChatWindow.tsx"
    if cw_path.exists():
        cw_text = cw_path.read_text(encoding="utf-8")
        if "E2E: расшифровка входящих" in cw_text:
            print(f"  > ChatWindow.tsx (useEffect расшифровки уже есть)")
        else:
            apply_patch(cw_path, CHATWINDOW_FIXES, "[decrypt useEffect]")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())