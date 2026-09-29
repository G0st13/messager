#!/usr/bin/env python3
"""sprint29h_safe_useE2E.py - защита от undefined useE2E."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


FIX_GROUP = [
    # 1. делаем useE2E опциональным в сигнатуре
    (
        'export default function GroupInfoPanel({\n'
        '  chat, currentUser, useE2E, onClose, onChatUpdated, onLeft,\n'
        '}: {\n'
        '  chat: Chat;\n'
        '  currentUser: User;\n'
        '  useE2E: UseE2E;',
        'export default function GroupInfoPanel({\n'
        '  chat, currentUser, useE2E, onClose, onChatUpdated, onLeft,\n'
        '}: {\n'
        '  chat: Chat;\n'
        '  currentUser: User;\n'
        '  useE2E?: UseE2E;',
    ),
    # 2. fallback внутри компонента
    (
        '  const [showE2ESetup, setShowE2ESetup] = useState(false);',
        '  const [showE2ESetup, setShowE2ESetup] = useState(false);\n'
        '  // защита: если useE2E не передан — используем безопасную заглушку\n'
        '  const e2eApi: UseE2E = useE2E ?? ({\n'
        '    ready: false, error: "useE2E not provided",\n'
        '    encryptForChat: async () => null,\n'
        '    decryptFromChat: async () => null,\n'
        '    initGroupEncryption: async () => null,\n'
        '    grantKeyTo: async () => null,\n'
        '    reset: () => {},\n'
        '  });',
    ),
    # 3. используем e2eApi вместо useE2E
    (
        '                <E2EIndicator\n'
        '                  enabled={chat.encryption_enabled}\n'
        '                  hasKey={chat.has_my_key}\n'
        '                  ready={useE2E.ready}\n'
        '                />',
        '                <E2EIndicator\n'
        '                  enabled={chat.encryption_enabled}\n'
        '                  hasKey={chat.has_my_key}\n'
        '                  ready={e2eApi.ready}\n'
        '                />',
    ),
    (
        '                  disabled={!useE2E.ready}\n',
        '                  disabled={!e2eApi.ready}\n',
    ),
    (
        '                  {useE2E.ready ? "[ ВКЛЮЧИТЬ E2E ]" : "[ ИНИЦИАЛИЗАЦИЯ КЛЮЧЕЙ... ]"}',
        '                  {e2eApi.ready ? "[ ВКЛЮЧИТЬ E2E ]" : "[ ИНИЦИАЛИЗАЦИЯ КЛЮЧЕЙ... ]"}',
    ),
    # 4. в модалку передаём e2eApi
    (
        '          <E2ESetupModal\n'
        '            chat={chat}\n'
        '            useE2E={useE2E}\n',
        '          <E2ESetupModal\n'
        '            chat={chat}\n'
        '            useE2E={e2eApi}\n',
    ),
]


def apply(path: Path, pairs: list[tuple[str, str]], label: str) -> int:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0
    text = path.read_text(encoding="utf-8")
    ok = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            ok += 1
    if ok:
        path.write_text(text, encoding="utf-8")
    print(f"  ~ {path.name} [{ok}/{len(pairs)}] {label}")
    return ok


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    src = root / "frontend" / "src" / "GroupInfoPanel.tsx"
    if src.exists():
        dst = b / "GroupInfoPanel.tsx"
        shutil.copy2(src, dst)
    print(f"📦 Бэкап: {b}\n")

    print("Патчи:")
    apply(src, FIX_GROUP, "[safe useE2E fallback]")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up -d")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())