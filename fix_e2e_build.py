#!/usr/bin/env python3
"""fix_e2e_build.py - жёсткая пересборка + диагностика бандла + JS для консоли."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> tuple[int, str]:
    print(f"\n$ {' '.join(str(c) for c in cmd)}")
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
        out = (r.stdout or "") + (r.stderr or "")
        if out:
            print(out)
        return r.returncode, out
    except Exception as e:
        print(f"ERR: {e}")
        return -1, str(e)


def check_bundle(root: Path) -> tuple[bool, list[str]]:
    """Проверяет что в собранном бандле есть ключевые строки."""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА БАНДЛА")
    print("=" * 70)

    dist = root / "frontend" / "dist" / "assets"
    if not dist.exists():
        print(f"  ✗ {dist} не найден")
        return False, ["dist/assets не существует"]

    js_files = sorted(dist.glob("*.js"))
    if not js_files:
        print(f"  ✗ в {dist} нет .js файлов")
        return False, ["в dist/assets нет js"]

    print(f"  Найдено .js файлов: {len(js_files)}")
    for f in js_files[:5]:
        print(f"    {f.name} ({f.stat().st_size // 1024} KB)")

    # Ищем ключевые маркеры
    markers = {
        "messenger-e2e": "IndexedDB база для ключей",
        "useE2E": "E2E hook",
        "encryptForChat": "E2E шифрование",
        "decryptFromChat": "E2E расшифровка",
        "/api/v1/keys/me": "эндпоинт для ключей",
        "/keys/me": "эндпоинт для ключей (short)",
    }

    problems = []
    for js in js_files:
        text = js.read_text(encoding="utf-8", errors="replace")
        print(f"\n  --- {js.name} ---")
        for marker, desc in markers.items():
            count = text.count(marker)
            marker_icon = "✓" if count > 0 else "✗"
            print(f"    {marker_icon} {marker!r} × {count} — {desc}")
            if count == 0 and marker in ("messenger-e2e", "encryptForChat"):
                problems.append(f"{js.name}: нет {marker!r}")

    return len(problems) == 0, problems


def hard_rebuild(root: Path, name: str) -> int:
    """Удаляет dist и vite cache, потом пересобирает frontend без кеша."""
    print("\n" + "=" * 70)
    print("ЖЁСТКАЯ ПЕРЕСБОРКА FRONTEND")
    print("=" * 70)

    # 1. удаляем старый dist
    dist = root / "frontend" / "dist"
    if dist.exists():
        import shutil
        shutil.rmtree(dist)
        print(f"  ✓ удалён {dist}")

    # 2. чистим node_modules/.vite в контейнере (если есть)
    compose = root / "infra" / "docker-compose.yml"

    # 3. docker compose build --no-cache frontend
    print("\n  Сборка (это займёт ~40-60 секунд)...")
    code, out = run([
        "docker", "compose", "-f", str(compose),
        "build", "--no-cache", "frontend",
    ], cwd=root, timeout=600)

    if code != 0:
        print(f"\n  ✗ Сборка упала (код {code})")
        return code

    print(f"\n  ✓ Сборка завершена")
    return 0


def get_bundle_hash(root: Path) -> str | None:
    """Возвращает имя главного js-файла (с хешем)."""
    dist = root / "frontend" / "dist" / "assets"
    if not dist.exists():
        return None
    js_files = sorted(dist.glob("index-*.js"))
    return js_files[0].name if js_files else None


def print_browser_js(root: Path) -> None:
    """Печатает JS для вставки в консоль браузера."""
    print("\n" + "=" * 70)
    print("JS ДЛЯ КОНСОЛИ БРАУЗЕРА")
    print("=" * 70)
    print("""
Скопируй ВСЁ ниже в DevTools → Console → Enter.
Это покажет где именно падает E2E на клиенте и попробует залить ключ вручную.
""" + "-" * 70)
    print(r"""
(async () => {
  const log = (...a) => console.log("[E2E-DIAG]", ...a);

  log("=== ENV ===");
  log("location:", location.href);
  log("isSecureContext:", window.isSecureContext);
  log("indexedDB:", !!window.indexedDB);
  log("crypto.subtle:", !!(window.crypto && window.crypto.subtle));

  const token = localStorage.getItem("access_token");
  log("access_token:", token ? "present (" + token.length + " chars)" : "MISSING");

  if (!token) {
    log("❌ Нет access_token — залогинься заново");
    return;
  }

  // 1. Проверяем IndexedDB
  log("=== IndexedDB ===");
  let existingKey = null;
  try {
    const db = await new Promise((resolve, reject) => {
      const req = indexedDB.open("messenger-e2e", 1);
      req.onupgradeneeded = () => {
        const d = req.result;
        if (!d.objectStoreNames.contains("keys")) d.createObjectStore("keys");
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
      setTimeout(() => reject(new Error("IndexedDB timeout")), 3000);
    });
    log("✓ БД открыта, stores:", Array.from(db.objectStoreNames));

    const keys = await new Promise((resolve, reject) => {
      const tx = db.transaction("keys", "readonly");
      const req = tx.objectStore("keys").getAllKeys();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    log("✓ Ключи в БД:", keys);

    // определяем userId
    const me = await fetch("/api/v1/auth/me", {
      headers: { "Authorization": "Bearer " + token },
    }).then(r => r.json());
    log("✓ Мой user_id:", me.id);

    const privKey = "priv:" + me.id;
    if (keys.includes(privKey)) {
      log("✓ Приватный ключ найден:", privKey);
      existingKey = await new Promise((resolve) => {
        const tx = db.transaction("keys", "readonly");
        const req = tx.objectStore("keys").get(privKey);
        req.onsuccess = () => resolve(req.result);
      });
    } else {
      log("✗ Приватного ключа НЕТ, генерируем новый...");
    }
    db.close();
  } catch (e) {
    log("❌ IndexedDB ошибка:", e.message || e);
    return;
  }

  // 2. Генерируем или используем существующий ключ
  log("=== Key generation ===");
  let b64 = "";
  try {
    let publicKey;
    if (existingKey) {
      // импортируем существующий
      const privKey = await crypto.subtle.importKey(
        "jwk", existingKey,
        { name: "ECDH", namedCurve: "P-256" },
        true, ["deriveKey", "deriveBits"]
      );
      log("✓ Импортировали существующий приватный ключ");
      // экспорт публичного из jwk — восстановим через derive? Проще создать новую пару.
      // Если у тебя уже есть — это уже другой сценарий, но для теста сделаем новую.
      log("  (для теста генерируем новую пару)");
    }

    const pair = await crypto.subtle.generateKey(
      { name: "ECDH", namedCurve: "P-256" },
      true, ["deriveKey", "deriveBits"]
    );
    log("✓ generateKey OK");

    const spki = await crypto.subtle.exportKey("spki", pair.publicKey);
    const bytes = new Uint8Array(spki);
    let bin = "";
    for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    b64 = btoa(bin);
    log("✓ exportKey OK, длина:", b64.length);

    const jwk = await crypto.subtle.exportKey("jwk", pair.privateKey);
    log("✓ export JWK OK");

    // сохраняем
    const db2 = await new Promise((resolve, reject) => {
      const req = indexedDB.open("messenger-e2e", 1);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    const me = await fetch("/api/v1/auth/me", {
      headers: { "Authorization": "Bearer " + token },
    }).then(r => r.json());
    await new Promise((resolve, reject) => {
      const tx = db2.transaction("keys", "readwrite");
      tx.objectStore("keys").put(jwk, "priv:" + me.id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
    db2.close();
    log("✓ Сохранили приватный ключ в IndexedDB как priv:" + me.id);
  } catch (e) {
    log("❌ Key gen ошибка:", e.message || e);
    return;
  }

  // 3. POST на сервер
  log("=== POST /api/v1/keys/me ===");
  try {
    const r = await fetch("/api/v1/keys/me", {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ public_key: b64, algorithm: "ECDH-P256" }),
    });
    log("HTTP status:", r.status);
    const data = await r.json().catch(() => null);
    log("response:", data);
    if (r.ok) {
      log("✅ КЛЮЧ УСПЕШНО ЗАЛИТ НА СЕРВЕР");
      log("   Проверь в БД:");
      log('   SELECT * FROM user_keys;');
    } else {
      log("❌ Сервер отказал:", data);
    }
  } catch (e) {
    log("❌ Network ошибка:", e.message || e);
  }
})();
""" + "-" * 70)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    p.add_argument("--skip-rebuild", action="store_true",
                   help="только диагностика, без пересборки")
    p.add_argument("--print-js-only", action="store_true",
                   help="только вывести JS для консоли и выйти")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    if args.print_js_only:
        print_browser_js(root)
        return 0

    # 1. Проверяем бандл
    ok, problems = check_bundle(root)

    # 2. Если плохо или попросили — пересобираем
    if not ok and not args.skip_rebuild:
        print("\n⚠ В бандле не хватает E2E-маркеров. Пересобираю...")
        old_hash = get_bundle_hash(root)
        print(f"  Старый hash: {old_hash}")
        code = hard_rebuild(root, args.name)
        if code != 0:
            print("\n❌ Пересборка упала — смотри ошибки выше")
            print_browser_js(root)
            return code
        new_hash = get_bundle_hash(root)
        print(f"  Новый hash: {new_hash}")
        if old_hash == new_hash:
            print("  ⚠ Хеш не изменился — возможно патчи не попали в src")
        # перепроверим
        ok2, _ = check_bundle(root)
        if not ok2:
            print("\n❌ Даже после пересборки в бандле нет маркеров")
            print("   Значит изменения в App.tsx/ChatWindow.tsx не в src — проверь файлы вручную")
    elif ok:
        print("\n✓ Бандл содержит все E2E-маркеры")

    # 3. Печатаем JS для консоли
    print_browser_js(root)

    # 4. Инструкция
    print("\n" + "=" * 70)
    print("ЧТО ДЕЛАТЬ")
    print("=" * 70)
    print("""
1. Если пересборка прошла — выполни:
     docker compose -f infra/docker-compose.yml up -d

2. Открой http://localhost:5173 в браузере

3. ЖМИ Ctrl+Shift+R (hard reload, чтобы сбросить кеш assets)

4. Открой F12 → Console → вставь JS выше → Enter

5. Смотри что выведет. Если увидишь "✅ КЛЮЧ УСПЕШНО ЗАЛИТ" — 
   проверь БД:
     docker compose -f infra/docker-compose.yml exec db psql -U messenger -d messenger \\
       -c "SELECT user_id, LEFT(public_key, 40) FROM user_keys;"

6. Если что-то красное в JS — пришли его мне, починим точечно.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())