#!/usr/bin/env python3
"""e2e_trace.py - добавляет console.log в E2E-цепочку, пересобирает, показывает как смотреть."""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd, cwd=None, timeout=600):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)


def hr(t):
    print()
    print("=" * 72)
    print(f"  {t}")
    print("=" * 72)


# ============================================================
# ПАТЧ 1: useE2E.ts — логируем в decryptFromChat
# ============================================================
USE_E2E_OLD = """  const decryptFromChat = useCallback(async (chat, text) => {
    const key = await getChatKey(chat);
    if (!key) return null;
    try {
      return await decryptText(key, text);
    } catch {
      return null;
    }
  }, [getChatKey]);"""

USE_E2E_NEW = """  const decryptFromChat = useCallback(async (chat, text) => {
    console.log("[E2E-TRACE] decryptFromChat called for chat", chat?.id, "text prefix:", (text || "").slice(0, 30));
    const key = await getChatKey(chat);
    console.log("[E2E-TRACE] chatKey:", key ? "OK len=" + (key.keySize || "?") : "NULL");
    if (!key) return null;
    try {
      const pt = await decryptText(key, text);
      console.log("[E2E-TRACE] decrypt OK, plaintext prefix:", (pt || "").slice(0, 30));
      return pt;
    } catch (e) {
      console.error("[E2E-TRACE] decrypt FAILED:", e);
      return null;
    }
  }, [getChatKey]);"""


# ============================================================
# ПАТЧ 2: ChatWindow.tsx — логируем useEffect расшифровки
# ============================================================
CW_EFFECT_OLD = """  useEffect(() => {
    if (!chat.encryption_enabled || !e2eApi.ready) return;"""

CW_EFFECT_NEW = """  useEffect(() => {
    console.log("[E2E-TRACE] decrypt useEffect fired: enc_enabled=",
      chat.encryption_enabled, "ready=", e2eApi.ready,
      "messages=", messages.length,
      "already_decrypted=", Object.keys(decrypted).length);
    if (!chat.encryption_enabled || !e2eApi.ready) return;"""


# ============================================================
# ПАТЧ 3: ChatWindow.tsx — логируем когда сообщение приходит по WS
# ============================================================
CW_WS_OLD = """          if (d.type === "message" && d.chat_id === chat.id) {
            if (d.client_id && d.author_id === currentUser.id) {
              onRemoveQueued(d.client_id);
            }"""

CW_WS_NEW = """          if (d.type === "message" && d.chat_id === chat.id) {
            console.log("[E2E-TRACE] WS message: id=", d.id,
              "encrypted=", d.encrypted,
              "text prefix=", (d.text || "").slice(0, 30));
            if (d.client_id && d.author_id === currentUser.id) {
              onRemoveQueued(d.client_id);
            }"""


# ============================================================
# ПАТЧ 4: ChatWindow.tsx — логируем рендер бабла
# ============================================================
CW_RENDER_OLD = """              msg={
                m.encrypted && decrypted[m.id] !== undefined
                  ? { ...m, text: decrypted[m.id], encrypted: false }
                  : m
              }"""

CW_RENDER_NEW = """              msg={
                (() => {
                  const hasDec = decrypted[m.id] !== undefined;
                  if (m.encrypted) {
                    console.log("[E2E-TRACE] render msg id=", m.id,
                      "encrypted=true hasDecrypted=", hasDec,
                      "->", hasDec ? "DECRYPTED" : "SHOWING-CIPHERTEXT");
                  }
                  return m.encrypted && hasDec
                    ? { ...m, text: decrypted[m.id], encrypted: false }
                    : m;
                })()
              }"""


PATCHES = [
    ("useE2E.ts", USE_E2E_OLD, USE_E2E_NEW, "decryptFromChat логирование"),
    ("ChatWindow.tsx", CW_EFFECT_OLD, CW_EFFECT_NEW, "useEffect расшифровки логирование"),
    ("ChatWindow.tsx", CW_WS_OLD, CW_WS_NEW, "WS message логирование"),
    ("ChatWindow.tsx", CW_RENDER_OLD, CW_RENDER_NEW, "render msg логирование"),
]


def apply_patch(path: Path, old: str, new: str, label: str) -> bool:
    if not path.exists():
        print(f"  ✗ {path.name} не найден")
        return False
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"  > {path.name}: уже пропатчено ({label})")
        return True
    if old not in text:
        print(f"  ✗ {path.name}: якорь не найден для '{label}'")
        # показать первые 60 символов якоря для сверки
        first = old.split("\n")[0][:60]
        print(f"     искал: {first!r}")
        return False
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")
    print(f"  ✓ {path.name}: {label}")
    return True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--no-rebuild", action="store_true")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено")
        return 1

    src = root / "frontend" / "src"
    compose = root / "infra" / "docker-compose.yml"

    hr("ПАТЧИ — добавляю console.log в E2E-цепочку")

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = root / f"_backup_{ts}"
    backup.mkdir(parents=True, exist_ok=True)
    for fname in ("useE2E.ts", "ChatWindow.tsx"):
        f = src / fname
        if f.exists():
            shutil.copy2(f, backup / fname)
    print(f"  📦 Бэкап: {backup}")

    print()
    ok = 0
    for fname, old, new, label in PATCHES:
        if apply_patch(src / fname, old, new, label):
            ok += 1

    print(f"\n  Итог: {ok}/{len(PATCHES)} патчей применено")

    if not args.no_rebuild:
        hr("ПЕРЕСБОРКА FRONTEND")
        print("  → build --no-cache frontend ... (до 60 сек)")
        code, out = run(["docker", "compose", "-f", str(compose),
                         "build", "--no-cache", "frontend"], cwd=root, timeout=600)
        if code != 0:
            print("  ✗ Сборка упала:")
            print("    " + out[-2000:].replace("\n", "\n    "))
            return 1
        print("  ✓ Сборка завершена")

        print("  → up -d ...")
        code, out = run(["docker", "compose", "-f", str(compose), "up", "-d"],
                        cwd=root, timeout=120)
        print("  " + ("✓ Готово" if code == 0 else "✗ Ошибка"))

    hr("ЧТО ДЕЛАТЬ ДАЛЬШЕ")
    print("""
  1. Открой http://localhost:5173 в браузере
  2. F12 → Network → включи 'Disable cache'
  3. Ctrl+Shift+R (hard reload)
  4. F12 → Console → ПКМ по пустому месту → Clear console
  5. Открой чат 2 (там E2E)
  6. Отправь сообщение: тест_расшифровки

  В Console появятся строки [E2E-TRACE]. Скопируй их сюда ВСЕ.

  Что искать:
    • [E2E-TRACE] WS message: id=... encrypted=true/false  — приходит ли флаг
    • [E2E-TRACE] decrypt useEffect fired: enc_enabled=... ready=...  — срабатывает ли useEffect
    • [E2E-TRACE] decryptFromChat called for chat ...  — вызывается ли расшифровка
    • [E2E-TRACE] chatKey: OK/NULL  — есть ли ключ
    • [E2E-TRACE] decrypt OK/FAILED  — успешна ли расшифровка
    • [E2E-TRACE] render msg id=... encrypted=true hasDecrypted=... — попадает ли plaintext в рендер
""")

    hr("ЧТО ПРИСЛАТЬ")
    print("""
  Скопируй ВСЕ строки из Console, которые начинаются с [E2E-TRACE].
  Обычно их 5-15 штук. По ним точно увижу где рвётся цепочка.

  Если [E2E-TRACE] вообще нет — значит фронт не пересобрался,
  или console.log вырезан минификатором.
""")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())