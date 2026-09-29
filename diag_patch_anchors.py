#!/usr/bin/env python3
"""diag_patch_anchors.py - показывает, какие якоря не найдены."""
from __future__ import annotations

import argparse
from pathlib import Path


ANCHORS = {
    "frontend/src/App.tsx": [
        ("GroupInfoPanel e2e",
         'useE2E={e2e}'),
        ("GroupInfoPanel блок",
         '{showGroupInfo && activeChat && ('),
        ("enqueueForChat signature",
         'const enqueueForChat = useCallback(('),
        ("enqueueForChat queue call",
         'queue.enqueue(chatId, text, messageType, attachmentId, replyToId, {'),
    ],
    "frontend/src/ChatWindow.tsx": [
        ("doSend signature",
         'const doSend = useCallback(() => {'),
        ("doSend async check",
         'const doSend = useCallback(async () => {'),
        ("virtual messages комментарий",
         '// Все "виртуальные" сообщения = серверные + очередь'),
        ("MessageBubble в рендере",
         '<MessageBubble'),
        ("msg={m}",
         'msg={m}'),
        ("msg={ расшифровка",
         'msg={\n                        m.encrypted && decrypted[m.id]'),
    ],
    "frontend/src/useMessageQueue.ts": [
        ("interface encrypted",
         'encrypted: boolean;'),
        ("enqueue signature",
         'encrypted: boolean = false,'),
        ("wsSend encrypted",
         'encrypted: msg.encrypted,'),
    ],
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name

    for rel, anchors in ANCHORS.items():
        path = root / rel
        print(f"\n{'=' * 60}\n{rel}\n{'=' * 60}")
        if not path.exists():
            print("  ! ФАЙЛ НЕ НАЙДЕН")
            continue
        text = path.read_text(encoding="utf-8")
        for label, anchor in anchors:
            found = anchor in text
            marker = "✓" if found else "✗"
            print(f"  {marker} {label}")
            if not found:
                # покажем ближайший похожий фрагмент
                # ищем по первому слову
                key = anchor.split()[0] if anchor.split() else ""
                idx = text.find(key)
                if idx >= 0:
                    snippet = text[idx:idx + 200]
                    print(f"      есть похожее: {snippet[:150]!r}")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())