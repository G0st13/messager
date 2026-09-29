#!/usr/bin/env python3
"""sprint29d_fix_e2e_import.py - добавляет useE2E в App.tsx."""
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
    app_path = root / "frontend" / "src" / "App.tsx"
    if not app_path.exists():
        print(f"ERR: {app_path} не найдено", file=sys.stderr)
        return 1

    text = app_path.read_text(encoding="utf-8")
    original = text

    # --- бэкап ---
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    (b / "App.tsx").write_text(text, encoding="utf-8")
    print(f"📦 Бэкап: {b}\n")

    # ===== FIX 1: импорт useE2E =====
    if "useE2E" not in text.split("\n\n")[0] and "from \"./useE2E\"" not in text:
        # ищем строку импорта useScrolling
        if 'import { useScrolling } from "./useScrolling";' in text:
            text = text.replace(
                'import { useScrolling } from "./useScrolling";',
                'import { useScrolling } from "./useScrolling";\n'
                'import { useE2E } from "./useE2E";',
                1,
            )
            print("  ~ добавлен import useE2E")
        else:
            print("  ! не нашёл точку для import useE2E")
    else:
        print("  > import useE2E уже есть")

    # ===== FIX 2: const e2e = useE2E(...) =====
    if "const e2e = useE2E(" in text:
        print("  > const e2e = useE2E(...) уже есть")
    else:
        # ищем любую из возможных строк-якорей
        anchors = [
            'const queue = useMessageQueue(user?.id ?? null, send, isWsOpen);',
            'const queue = useMessageQueue(user?.id ?? null, send, () => readyState === WebSocket.OPEN);',
            'useMessageQueue(user?.id ?? null',
        ]
        inserted = False
        for anchor in anchors:
            if anchor in text:
                # найдём конец строки с useMessageQueue
                idx = text.find(anchor)
                # конец строки
                end_of_line = text.find("\n", idx)
                if end_of_line == -1:
                    continue
                # вставим после всей строки, добавив отступ как в оригинале
                line_start = text.rfind("\n", 0, idx) + 1
                indent = text[line_start:idx]
                new_line = f"\n{indent}const e2e = useE2E(user?.id ?? null);"
                text = text[:end_of_line] + new_line + text[end_of_line:]
                print(f"  ~ добавлен const e2e = useE2E(user?.id ?? null) после useMessageQueue")
                inserted = True
                break

        if not inserted:
            # резервный вариант — ищем useMessageQueue определение через regex
            m = re.search(
                r"^(\s*)const\s+queue\s*=\s*useMessageQueue\([^;]*\);",
                text,
                re.M,
            )
            if m:
                text = text[:m.end()] + f"\n{m.group(1)}const e2e = useE2E(user?.id ?? null);" + text[m.end():]
                print("  ~ добавлен const e2e (regex)")
                inserted = True

        if not inserted:
            print("  ✗ НЕ НАЙДЕН якорь для const e2e")
            print("     покажи вручную эти строки из App.tsx:")
            for line in text.split("\n"):
                if "useMessageQueue" in line:
                    print(f"     → {line}")

    # ===== Запись =====
    if text != original:
        app_path.write_text(text, encoding="utf-8")
        print(f"\n  ✓ {app_path}")
    else:
        print(f"\n  > {app_path} без изменений")

    # ===== Проверка =====
    final = app_path.read_text(encoding="utf-8")
    print("\nПроверка:")
    print(f"  {'✓' if 'from \"./useE2E\"' in final else '✗'} import useE2E")
    print(f"  {'✓' if 'const e2e = useE2E(' in final else '✗'} const e2e")
    print(f"  {'✓' if 'useE2E={e2e}' in final else '✗'} <GroupInfoPanel useE2E={e2e}>")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())