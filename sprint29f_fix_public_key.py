#!/usr/bin/env python3
"""sprint29f_fix_public_key.py - хранит публичный ключ в IndexedDB."""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ==============================================================
# keyStorage.ts — добавляем savePublicB64 / loadPublicB64
# ==============================================================
KEY_STORAGE_PATCH = [
    (
        'export async function clearPrivateJwk(userId: number): Promise<void> {\n'
        '  const db = await openDb();\n'
        '  await new Promise<void>((resolve, reject) => {\n'
        '    const tx = db.transaction(STORE, "readwrite");\n'
        '    tx.objectStore(STORE).delete(`priv:${userId}`);\n'
        '    tx.oncomplete = () => resolve();\n'
        '    tx.onerror = () => reject(tx.error);\n'
        '  });\n'
        '  db.close();\n'
        '}',
        'export async function clearPrivateJwk(userId: number): Promise<void> {\n'
        '  const db = await openDb();\n'
        '  await new Promise<void>((resolve, reject) => {\n'
        '    const tx = db.transaction(STORE, "readwrite");\n'
        '    tx.objectStore(STORE).delete(`priv:${userId}`);\n'
        '    tx.objectStore(STORE).delete(`pub:${userId}`);\n'
        '    tx.oncomplete = () => resolve();\n'
        '    tx.onerror = () => reject(tx.error);\n'
        '  });\n'
        '  db.close();\n'
        '}\n'
        '\n'
        '\n'
        'export async function savePublicB64(userId: number, b64: string): Promise<void> {\n'
        '  const db = await openDb();\n'
        '  await new Promise<void>((resolve, reject) => {\n'
        '    const tx = db.transaction(STORE, "readwrite");\n'
        '    tx.objectStore(STORE).put(b64, `pub:${userId}`);\n'
        '    tx.oncomplete = () => resolve();\n'
        '    tx.onerror = () => reject(tx.error);\n'
        '  });\n'
        '  db.close();\n'
        '}\n'
        '\n'
        '\n'
        'export async function loadPublicB64(userId: number): Promise<string | null> {\n'
        '  const db = await openDb();\n'
        '  const result = await new Promise<string | null>((resolve, reject) => {\n'
        '    const tx = db.transaction(STORE, "readonly");\n'
        '    const req = tx.objectStore(STORE).get(`pub:${userId}`);\n'
        '    req.onsuccess = () => resolve((req.result as string) || null);\n'
        '    req.onerror = () => reject(req.error);\n'
        '  });\n'
        '  db.close();\n'
        '  return result;\n'
        '}',
    ),
]


# ==============================================================
# useE2E.ts — полностью заменяем useEffect инициализации
# ==============================================================
USE_E2E_PATCH = [
    # import
    (
        'import { loadPrivateJwk, savePrivateJwk } from "./keyStorage";',
        'import { loadPrivateJwk, savePrivateJwk, savePublicB64, loadPublicB64 } from "./keyStorage";',
    ),
    # заменяем весь useEffect инициализации
    (
        '  // ---------- ensure keypair on mount ----------\n'
        '  useEffect(() => {\n'
        '    if (userId == null) {\n'
        '      myPrivateRef.current = null;\n'
        '      myPublicB64Ref.current = null;\n'
        '      peerCacheRef.current = {};\n'
        '      chatKeyCacheRef.current = {};\n'
        '      setReady(false);\n'
        '      return;\n'
        '    }\n'
        '    let cancelled = false;\n'
        '\n'
        '    (async () => {\n'
        '      try {\n'
        '        const jwk = await loadPrivateJwk(userId);\n'
        '        if (jwk) {\n'
        '          const priv = await importPrivateJwk(jwk);\n'
        '          if (cancelled) return;\n'
        '          myPrivateRef.current = priv;\n'
        '        } else {\n'
        '          const pair = await generateKeyPair();\n'
        '          const privJwk = await exportPrivateKeyJwk(pair);\n'
        '          await savePrivateJwk(userId, privJwk);\n'
        '          if (cancelled) return;\n'
        '          myPrivateRef.current = pair.privateKey;\n'
        '          // экспортируем публичный и заливаем\n'
        '          const pubB64 = await exportPublicKeyB64(pair);\n'
        '          myPublicB64Ref.current = pubB64;\n'
        '          await api.post("/keys/me", {\n'
        '            public_key: pubB64,\n'
        '            algorithm: "ECDH-P256",\n'
        '          });\n'
        '          setReady(true);\n'
        '          return;\n'
        '        }\n'
        '        // если загрузили старый — надо перезалить публичный (мог потеряться)\n'
        '        // но у нас нет ключа публичного в jwk? он есть в "x","y".\n'
        '        // Проще: сгенерировать заново, если сервер не отдаёт наш ключ.\n'
        '        try {\n'
        '          const { data } = await api.get<{ public_key: string }>("/keys/me");\n'
        '          if (cancelled) return;\n'
        '          myPublicB64Ref.current = data.public_key;\n'
        '          setReady(true);\n'
        '        } catch {\n'
        '          // сервер не знает наш ключ — регенерируем и перезаливаем\n'
        '          const pair = await generateKeyPair();\n'
        '          const privJwk2 = await exportPrivateKeyJwk(pair);\n'
        '          await savePrivateJwk(userId, privJwk2);\n'
        '          if (cancelled) return;\n'
        '          myPrivateRef.current = pair.privateKey;\n'
        '          const pubB64 = await exportPublicKeyB64(pair);\n'
        '          myPublicB64Ref.current = pubB64;\n'
        '          await api.post("/keys/me", {\n'
        '            public_key: pubB64,\n'
        '            algorithm: "ECDH-P256",\n'
        '          });\n'
        '          setReady(true);\n'
        '        }\n'
        '      } catch (e: any) {\n'
        '        setError(e.message || "failed to init e2e");\n'
        '        setReady(false);\n'
        '      }\n'
        '    })();\n'
        '\n'
        '    return () => { cancelled = true; };\n'
        '  }, [userId]);',
        '  // ---------- ensure keypair on mount ----------\n'
        '  useEffect(() => {\n'
        '    if (userId == null) {\n'
        '      myPrivateRef.current = null;\n'
        '      myPublicB64Ref.current = null;\n'
        '      peerCacheRef.current = {};\n'
        '      chatKeyCacheRef.current = {};\n'
        '      setReady(false);\n'
        '      return;\n'
        '    }\n'
        '    let cancelled = false;\n'
        '\n'
        '    const syncPublicToServer = async (pubB64: string) => {\n'
        '      try {\n'
        '        await api.post("/keys/me", {\n'
        '          public_key: pubB64,\n'
        '          algorithm: "ECDH-P256",\n'
        '        });\n'
        '      } catch (e) {\n'
        '        // если упало — не критично, попробуем в следующий раз\n'
        '        console.warn("[useE2E] POST /keys/me failed:", e);\n'
        '      }\n'
        '    };\n'
        '\n'
        '    (async () => {\n'
        '      try {\n'
        '        const privJwk = await loadPrivateJwk(userId);\n'
        '        const pubB64 = await loadPublicB64(userId);\n'
        '\n'
        '        if (privJwk && pubB64) {\n'
        '          // Оба есть локально — используем их\n'
        '          const priv = await importPrivateJwk(privJwk);\n'
        '          if (cancelled) return;\n'
        '          myPrivateRef.current = priv;\n'
        '          myPublicB64Ref.current = pubB64;\n'
        '          setReady(true);\n'
        '          // тихо синхронизируем на сервер (на случай если там ещё нет)\n'
        '          syncPublicToServer(pubB64);\n'
        '          return;\n'
        '        }\n'
        '\n'
        '        // Генерируем новую пару — старые данные могли быть частичными\n'
        '        const pair = await generateKeyPair();\n'
        '        const newPrivJwk = await exportPrivateKeyJwk(pair);\n'
        '        const newPubB64 = await exportPublicKeyB64(pair);\n'
        '        await savePrivateJwk(userId, newPrivJwk);\n'
        '        await savePublicB64(userId, newPubB64);\n'
        '        if (cancelled) return;\n'
        '        myPrivateRef.current = pair.privateKey;\n'
        '        myPublicB64Ref.current = newPubB64;\n'
        '        setReady(true);\n'
        '        await syncPublicToServer(newPubB64);\n'
        '      } catch (e: any) {\n'
        '        console.error("[useE2E] init failed:", e);\n'
        '        setError(e.message || "failed to init e2e");\n'
        '        setReady(false);\n'
        '      }\n'
        '    })();\n'
        '\n'
        '    return () => { cancelled = true; };\n'
        '  }, [userId]);',
    ),
]


def apply(path: Path, pairs: list[tuple[str, str]], label: str) -> tuple[int, int]:
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
    print(f"  ~ {path.name} [{status} {ok}/{len(pairs)}] {label}")
    return ok, len(pairs)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено", file=sys.stderr)
        return 1

    fe = root / "frontend" / "src"

    # бэкап
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = root / f"_backup_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    for rel in ["frontend/src/keyStorage.ts", "frontend/src/useE2E.ts"]:
        src = root / rel
        if src.exists():
            dst = b / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"📦 Бэкап: {b}\n")

    print("Патчи:")
    apply(fe / "keyStorage.ts", KEY_STORAGE_PATCH, "[save/load public key]")
    apply(fe / "useE2E.ts", USE_E2E_PATCH, "[правильная init-логика]")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml build --no-cache frontend")
    print("  docker compose -f infra/docker-compose.yml up -d")
    print()
    print("Затем в браузере:")
    print("  F12 → Application → IndexedDB → messenger-e2e → удалить базу")
    print("  F5 на странице → useE2E создаст НОВУЮ пару и зальёт оба ключа")
    print()
    print("Проверка:")
    print(f'  docker compose -f infra/docker-compose.yml exec db psql -U messenger -d messenger -c "SELECT user_id, LEFT(public_key,40) FROM user_keys;"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())