#!/usr/bin/env python3
"""fix_alembic_dup.py - чинит дубликат revision 0012."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REV_RE = re.compile(
    r'^revision(?::\s*str)?\s*[:=]\s*["\']([^"\']+)["\']',
    re.M,
)
DOWN_RE = re.compile(
    r'^down_revision(?::\s*[^=]*)?\s*[:=]\s*["\']?([^"\'\n,]+)["\']?',
    re.M,
)


def parse_rev(path: Path) -> tuple[str | None, str | None]:
    text = path.read_text(encoding="utf-8")
    m1 = REV_RE.search(text)
    m2 = DOWN_RE.search(text)
    rev = m1.group(1) if m1 else None
    down = m2.group(1).strip() if m2 else None
    if down in ("None", ""):
        down = None
    return rev, down


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    versions = root / "backend" / "alembic" / "versions"
    if not versions.exists():
        print(f"ERR: {versions} не найдено", file=sys.stderr)
        return 1

    print(f"\nСканирую {versions}\n")

    # --- инвентаризация ---
    parsed: dict[Path, tuple[str | None, str | None]] = {}
    by_rev: dict[str, list[Path]] = {}

    for f in sorted(versions.glob("*.py")):
        if f.name.startswith("__"):
            continue
        rev, down = parse_rev(f)
        parsed[f] = (rev, down)
        if rev:
            by_rev.setdefault(rev, []).append(f)
        print(f"  {f.name:30s} rev={str(rev):8s} down={str(down)}")

    print()
    duplicates = {rev: files for rev, files in by_rev.items() if len(files) > 1}

    if not duplicates:
        print("✓ Дубликатов нет. Alembic должен работать.")
        return 0

    print(f"⚠ Дубликаты: {list(duplicates.keys())}\n")

    # --- ищем наш e2e и их sprint26 ---
    our_file: Path | None = None
    their_file: Path | None = None

    for rev, files in duplicates.items():
        for f in files:
            if "e2e" in f.name.lower():
                our_file = f
            elif "sprint26" in f.name.lower():
                their_file = f
            else:
                # любой другой не-e2e
                if their_file is None:
                    their_file = f

    if our_file is None:
        print("ERR: не нашёл нашу e2e-миграцию")
        return 1

    print(f"Наша: {our_file.name}")
    if their_file:
        print(f"Чужая: {their_file.name} (оставляем как 0012)")
    print()

    # --- выясняем down_revision чужой — это должна быть наша база ---
    if their_file:
        their_rev, their_down = parsed[their_file]
        new_down = their_rev  # наша цепляется за неё
    else:
        new_down = "0011"

    # --- находим следующий свободный номер ---
    all_nums: set[int] = set()
    for rev in by_rev.keys():
        if rev.isdigit():
            all_nums.add(int(rev))
    next_num = max(all_nums) + 1 if all_nums else 13
    new_rev = f"{next_num:04d}"

    print(f"План:")
    print(f"  • {our_file.name}")
    print(f"      revision: {parsed[our_file][0]} → {new_rev}")
    print(f"      down_revision: {parsed[our_file][1]} → {new_down}")
    print(f"      имя: → {new_rev}_e2e.py")
    print()

    # --- применяем ---
    text = our_file.read_text(encoding="utf-8")

    # revision
    text, n1 = re.subn(
        r'(revision(?::\s*str)?\s*[:=]\s*)["\']0012["\']',
        rf'\g<1>"{new_rev}"',
        text,
    )
    # down_revision (может быть "0011" или что-то ещё)
    text, n2 = re.subn(
        r'(down_revision(?::\s*[^=]*)?\s*[:=]\s*)["\']?0011["\']?',
        rf'\g<1>"{new_down}"',
        text,
    )
    # docstring
    text = text.replace("Revision ID: 0012", f"Revision ID: {new_rev}")
    text = text.replace("Revises: 0011", f"Revises: {new_down}")

    if n1 == 0 or n2 == 0:
        print(f"⚠ Внимание: заменено revision={n1}, down_revision={n2}")
        print("  Проверь файл вручную перед запуском!")

    new_path = our_file.parent / f"{new_rev}_e2e.py"
    new_path.write_text(text, encoding="utf-8")
    our_file.unlink()
    print(f"  ✓ {our_file.name} → {new_path.name}")

    # --- проверка ---
    print("\nФинальный список:")
    by_rev2: dict[str, list[Path]] = {}
    parsed2: dict[str, str | None] = {}

    for f in sorted(versions.glob("*.py")):
        if f.name.startswith("__"):
            continue
        rev, down = parse_rev(f)
        if rev:
            by_rev2.setdefault(rev, []).append(f)
            parsed2[rev] = down
        print(f"  {f.name:30s} rev={str(rev):8s} down={str(down)}")

    dups2 = {r: fs for r, fs in by_rev2.items() if len(fs) > 1}
    if dups2:
        print(f"\n✗ Всё ещё дубликаты: {list(dups2.keys())}")
        return 1

    # --- ищем головы (rev, на которые никто не ссылается) ---
    all_downs = {v for v in parsed2.values() if v}
    heads = sorted(set(by_rev2.keys()) - all_downs)

    print(f"\nГолова(ы): {heads}")
    if len(heads) > 1:
        print("⚠ Несколько голов — надо свести вручную")
        return 1

    print("\n✓ Одна голова. Можно запускать.")
    print(f"\n  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())