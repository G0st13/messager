#!/usr/bin/env python3
"""sprint20.py - profile page + pixel Johnny Silverhand."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PIXEL_JOHNNY = r'''import { useEffect, useRef } from "react";

// Johnny Silverhand — pixel art, курит в углу
// Холст 60x80, апскейл x3 с pixelated rendering

const W = 60;
const H = 80;

type SmokeParticle = { x: number; y: number; vx: number; vy: number; life: number; max: number };

export default function PixelJohnny() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = W;
    canvas.height = H;
    ctx.imageSmoothingEnabled = false;

    const smoke: SmokeParticle[] = [];
    let t0 = performance.now();
    let raf = 0;
    let lastSmoke = 0;

    // Палитра
    const P = {
      bg: null as string | null,
      hair: "#1a1a1f",
      hairHi: "#3a3a44",
      skin: "#c89878",
      skinShade: "#a07050",
      shade: "#2a1a10",
      glass: "#0a0a0e",
      glassGlow: "#fcee0a",
      jacket: "#3a2a1a",
      jacketHi: "#5a4530",
      shirt: "#a0a0a8",
      mech: "#a0a8b0",
      mechHi: "#d0d8e0",
      mechRed: "#c4302a",
      mechGlow: "#ff5540",
      cig: "#f0f0e0",
      cigTip: "#ffaa20",
      cigGlow: "#ffdd66",
      outline: "#000000",
      smoke: "#9aa0b0",
    };

    const px = (x: number, y: number, c: string, a = 1) => {
      ctx.globalAlpha = a;
      ctx.fillStyle = c;
      ctx.fillRect(x, y, 1, 1);
      ctx.globalAlpha = 1;
    };

    const rect = (x: number, y: number, w: number, h: number, c: string) => {
      ctx.fillStyle = c;
      ctx.fillRect(x, y, w, h);
    };

    const drawCharacter = (t: number) => {
      // лёгкое покачивание
      const sway = Math.sin(t / 1400) * 0.5;
      const ox = 0;
      const oy = Math.floor(sway);

      ctx.save();
      ctx.translate(ox, oy);

      // ===== Волосы (верх головы + хвост) =====
      rect(20, 6, 16, 4, P.hair);        // затылок
      rect(18, 8, 20, 6, P.hair);        // макушка
      rect(16, 10, 4, 10, P.hair);       // левый висок
      rect(40, 10, 4, 10, P.hair);       // правый висок
      rect(44, 12, 3, 14, P.hair);       // хвост вниз справа
      rect(46, 14, 3, 10, P.hair);       // кончик хвоста
      // блики
      rect(22, 8, 6, 1, P.hairHi);
      rect(20, 9, 3, 1, P.hairHi);

      // ===== Лицо =====
      rect(20, 14, 20, 12, P.skin);      // основа
      rect(20, 14, 20, 2, P.skinShade);  // тень сверху (под волосами)
      // подбородок
      rect(22, 24, 16, 2, P.skinShade);

      // ===== Очки (авиаторы, чёрные с жёлтым отливом) =====
      rect(18, 15, 24, 5, P.glass);      // перекладина
      rect(18, 15, 10, 5, P.glass);      // левая линза
      rect(32, 15, 10, 5, P.glass);      // правая линза
      // оправа
      rect(18, 15, 24, 1, "#3a3a44");
      rect(18, 19, 24, 1, "#3a3a44");
      // блики на линзах — мерцают
      const blink = Math.sin(t / 900) > 0.7;
      if (blink) {
        rect(20, 16, 3, 2, P.glassGlow);
        rect(34, 16, 3, 2, P.glassGlow);
      }
      // дужки
      rect(16, 15, 2, 4, P.glass);
      rect(42, 15, 2, 4, P.glass);

      // ===== Борода =====
      rect(22, 22, 16, 4, P.shade);
      rect(20, 20, 2, 4, P.shade);
      rect(38, 20, 2, 4, P.shade);
      // усы
      rect(24, 21, 12, 1, "#1a1010");

      // ===== Рот (с сигаретой) =====
      rect(24, 24, 12, 1, "#2a1010");

      // ===== Сигарета =====
      rect(30, 24, 1, 3, P.cig);         // тело сигареты (вниз)
      rect(30, 27, 1, 1, P.cigTip);      // кончик (тлеющий)
      // свечение кончика — пульсирует
      const pulse = 0.6 + Math.sin(t / 300) * 0.4;
      ctx.globalAlpha = pulse;
      px(30, 28, P.cigGlow);
      px(29, 28, P.cigGlow, pulse * 0.5);
      px(31, 28, P.cigGlow, pulse * 0.5);
      ctx.globalAlpha = 1;

      // ===== Шея =====
      rect(26, 26, 8, 3, P.skinShade);

      // ===== Куртка (ворот) =====
      rect(14, 28, 32, 3, P.jacket);     // воротник
      rect(14, 28, 4, 3, P.jacketHi);
      rect(42, 28, 4, 3, P.jacketHi);

      // ===== Тело / куртка =====
      rect(12, 31, 36, 30, P.jacket);    // корпус куртки
      // молния / центральная полоса (футболка)
      rect(28, 31, 4, 22, P.shirt);
      rect(28, 31, 1, 22, "#707078");
      // заклёпки на куртке
      rect(16, 34, 1, 1, P.jacketHi);
      rect(16, 38, 1, 1, P.jacketHi);
      rect(16, 42, 1, 1, P.jacketHi);
      rect(43, 34, 1, 1, P.jacketHi);
      rect(43, 38, 1, 1, P.jacketHi);
      rect(43, 42, 1, 1, P.jacketHi);
      // тени на куртке
      rect(12, 31, 3, 30, "#2a1a10");
      rect(45, 31, 3, 30, "#2a1a10");
      // плечи
      rect(10, 30, 40, 2, "#2a1a10");

      // ===== Механическая рука (левая, у нас справа — Johnny левша) =====
      // предплечье + кисть, серебряная с красной полосой
      rect(46, 32, 6, 4, P.mech);        // плечо-протез
      rect(46, 32, 6, 1, P.mechHi);      // блик сверху
      rect(48, 33, 4, 1, P.mechRed);     // красная полоса
      rect(48, 36, 8, 12, P.mech);       // предплечье
      rect(48, 36, 1, 12, P.mechHi);     // блик слева
      rect(55, 36, 1, 12, "#707880");    // тень справа
      // сегменты
      rect(48, 40, 8, 1, "#707880");
      rect(48, 44, 8, 1, "#707880");
      // кулак
      rect(48, 48, 8, 6, P.mech);
      rect(48, 48, 8, 1, P.mechHi);
      rect(48, 53, 8, 1, "#707880");
      // пальцы-сегменты
      rect(48, 54, 2, 2, P.mech);
      rect(51, 54, 2, 2, P.mech);
      rect(54, 54, 2, 2, P.mech);
      // огонёк на предплечье
      const ledPulse = Math.sin(t / 500) > 0.3;
      if (ledPulse) {
        px(54, 38, P.mechGlow);
        ctx.globalAlpha = 0.5;
        px(53, 38, P.mechGlow, 0.5);
        px(55, 38, P.mechGlow, 0.5);
        ctx.globalAlpha = 1;
      }

      // ===== Правая рука (обычная) =====
      rect(6, 33, 6, 20, P.jacket);
      rect(6, 33, 1, 20, P.jacketHi);
      rect(10, 33, 2, 20, "#2a1a10");
      // кисть
      rect(6, 53, 6, 5, P.skin);
      rect(6, 53, 6, 1, P.skinShade);

      // ===== Ремень =====
      rect(14, 58, 32, 3, "#1a0f0a");
      rect(28, 58, 4, 3, "#a08040");     // пряжка

      // ===== Обводка (тёмные края) =====
      // обводка головы
      rect(18, 6, 20, 1, P.outline);
      rect(16, 10, 2, 14, P.outline);
      rect(42, 10, 2, 12, P.outline);
      // плечи
      rect(10, 30, 40, 1, P.outline);

      ctx.restore();
    };

    const drawSmoke = (dt: number) => {
      // добавляем новые частицы раз в ~180мс
      lastSmoke += dt;
      if (lastSmoke > 180) {
        lastSmoke = 0;
        smoke.push({
          x: 30 + (Math.random() - 0.5) * 2,
          y: 28,
          vx: (Math.random() - 0.5) * 4,
          vy: -10 - Math.random() * 8,
          life: 0,
          max: 2200 + Math.random() * 800,
        });
      }
      // апдейт
      for (let i = smoke.length - 1; i >= 0; i--) {
        const s = smoke[i];
        s.life += dt;
        if (s.life > s.max) { smoke.splice(i, 1); continue; }
        s.x += s.vx * (dt / 1000);
        s.y += s.vy * (dt / 1000);
        s.vx += (Math.random() - 0.5) * 0.5;
      }
      // рисуем
      for (const s of smoke) {
        const p = s.life / s.max;
        const alpha = (1 - p) * 0.55;
        const size = p < 0.3 ? 1 : p < 0.7 ? 2 : 2;
        ctx.globalAlpha = alpha;
        ctx.fillStyle = "#c8d0dc";
        ctx.fillRect(Math.floor(s.x), Math.floor(s.y), size, size);
      }
      ctx.globalAlpha = 1;
    };

    const frame = (t: number) => {
      const dt = Math.min(50, t - t0);
      t0 = t;

      ctx.clearRect(0, 0, W, H);
      drawCharacter(t);
      drawSmoke(dt);

      raf = requestAnimationFrame(frame);
    };

    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div className="johnny-corner" aria-hidden="true">
      <canvas
        ref={ref}
        className="block"
        style={{
          width: W * 3,
          height: H * 3,
          imageRendering: "pixelated",
          filter: "drop-shadow(0 0 8px rgba(0,240,255,0.35))",
        }}
      />
      <div className="johnny-label">J.SILVERHAND</div>
    </div>
  );
}
'''


PROFILE_PAGE = r'''import { useCallback, useEffect, useState } from "react";
import Avatar from "./Avatar";
import PostCard from "./PostCard";
import FactionBadge from "./FactionBadge";
import FactionPicker from "./FactionPicker";
import ChromePanel from "./ChromePanel";
import PixelJohnny from "./PixelJohnny";
import { api } from "./api";
import { rankProgress } from "./factions";
import type { Post, User, UserProfile } from "./types";

export default function ProfilePage({
  userId, currentUser, onBack, onOpenProfile, onChatWith, onUserUpdate,
}: {
  userId: number;
  currentUser: User;
  onBack: () => void;
  onOpenProfile: (id: number) => void;
  onChatWith: (userId: number) => void;
  onUserUpdate?: (u: User) => void;
}) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [showFactionPicker, setShowFactionPicker] = useState(false);
  const [showChrome, setShowChrome] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const [p, ps] = await Promise.all([
      api.get<UserProfile>(`/users/${userId}/profile`),
      api.get<Post[]>(`/posts/user/${userId}`),
    ]);
    setProfile(p.data);
    setPosts(ps.data);
    setLoading(false);
  }, [userId]);

  useEffect(() => { load(); }, [load]);

  const toggleFollow = async () => {
    if (!profile) return;
    if (profile.is_following) {
      await api.delete(`/users/${userId}/follow`);
      setProfile({ ...profile, is_following: false, followers_count: profile.followers_count - 1 });
    } else {
      await api.post(`/users/${userId}/follow`);
      setProfile({ ...profile, is_following: true, followers_count: profile.followers_count + 1 });
    }
  };

  const handleUpdate = (p: Post) =>
    setPosts((prev) => prev.map((x) => (x.id === p.id ? p : x)));

  const handleDelete = async (id: number) => {
    if (!confirm("Удалить пост?")) return;
    await api.delete(`/posts/${id}`);
    setPosts((prev) => prev.filter((x) => x.id !== id));
    if (profile) setProfile({ ...profile, posts_count: profile.posts_count - 1 });
  };

  if (loading || !profile) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-xs uppercase tracking-[0.4em] neon-text cursor">
          scanning operator
        </div>
      </div>
    );
  }

  const avatarUser = {
    username: profile.username,
    display_name: profile.display_name,
    avatar_color: profile.avatar_color,
  };

  const rank = rankProgress(profile.xp || 0);
  const hexId = profile.id.toString(16).toUpperCase().padStart(4, "0");

  return (
    <div className="relative flex-1 overflow-y-auto bg-cyber-bg/60">
      <div className="mx-auto w-full max-w-3xl px-6 py-8">

        {/* ===== Header / card ===== */}
        <div className="corner-frame relative mb-6 rounded-sm border border-cyber-cyan/40 bg-cyber-panel/90 p-6">

          {/* верхняя линия + бэкграунд сканлайнов */}
          <div className="profile-scanlines" />

          {/* Кнопка назад */}
          <button
            onClick={onBack}
            className="cyber-btn mb-4 rounded-sm px-3 py-1 text-[10px]"
          >
            ← BACK
          </button>

          {/* Метка в углу */}
          <div className="absolute right-4 top-3 text-[9px] uppercase tracking-[0.3em] text-cyber-dim">
            NET_ID::0x{hexId}
          </div>

          <div className="flex flex-col items-center gap-5 md:flex-row md:items-start">
            {/* Avatar с большим размером */}
            <div className="relative">
              <Avatar user={avatarUser} size={120} />
              <div className="avatar-glow" />
            </div>

            {/* Info */}
            <div className="min-w-0 flex-1 text-center md:text-left">
              <div className="flex flex-wrap items-center justify-center gap-2 md:justify-start">
                <h1 className="truncate text-2xl font-bold uppercase tracking-widest neon-text text-readable">
                  {profile.display_name || profile.username}
                </h1>
                <FactionBadge faction={profile.faction} size="md" showLabel />
              </div>

              <div className="mt-1 text-xs uppercase tracking-[0.3em] text-cyber-dim">
                @{profile.username}
              </div>

              {/* Rank */}
              <div className="mt-3 flex items-center justify-center gap-3 md:justify-start">
                <span className={"rank-badge rank-" + (profile.rank || "novice")}>
                  {profile.rank || "novice"}
                </span>
                <div className="flex items-center gap-2">
                  <div className="h-1 w-32 overflow-hidden rounded-sm bg-cyber-cyan/15">
                    <div
                      className="h-full bg-cyber-cyan transition-all"
                      style={{ width: rank.percent + "%", boxShadow: "0 0 6px #00f0ff" }}
                    />
                  </div>
                  <span className="text-[9px] uppercase tracking-widest text-cyber-dim">
                    XP {profile.xp} {rank.next > 0 && `→ ${rank.next}`}
                  </span>
                </div>
              </div>

              {profile.bio && (
                <p className="mt-4 whitespace-pre-wrap text-sm text-cyber-text/80 leading-relaxed">
                  {profile.bio}
                </p>
              )}
            </div>
          </div>

          {/* Stats — три блока */}
          <div className="mt-6 grid grid-cols-3 gap-3">
            <div className="stat-cell">
              <div className="stat-value neon-text">{profile.posts_count}</div>
              <div className="stat-label">transmissions</div>
            </div>
            <div className="stat-cell">
              <div className="stat-value neon-text-mag">{profile.followers_count}</div>
              <div className="stat-label">followers</div>
            </div>
            <div className="stat-cell">
              <div className="stat-value neon-text-yel">{profile.following_count}</div>
              <div className="stat-label">following</div>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-5 flex flex-wrap justify-center gap-2 md:justify-start">
            {!profile.is_me && (
              <>
                <button
                  onClick={toggleFollow}
                  className={
                    "rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-widest transition " +
                    (profile.is_following
                      ? "border border-cyber-dim/40 text-cyber-dim hover:border-cyber-magenta/60 hover:text-cyber-magenta"
                      : "cyber-btn")
                  }
                >
                  {profile.is_following ? "◌ UNFOLLOW" : "◈ FOLLOW"}
                </button>
                <button
                  onClick={() => onChatWith(profile.id)}
                  className="cyber-btn rounded-sm px-4 py-2 text-xs"
                >
                  ▸ TRANSMIT
                </button>
              </>
            )}
            {profile.is_me && (
              <>
                <button
                  onClick={() => setShowFactionPicker(true)}
                  className="cyber-btn rounded-sm px-4 py-2 text-xs"
                >
                  ◈ {profile.faction ? "CHANGE FACTION" : "CHOOSE FACTION"}
                </button>
                <button
                  onClick={() => setShowChrome(true)}
                  className="cyber-btn rounded-sm px-4 py-2 text-xs"
                >
                  ◆ CHROME
                </button>
              </>
            )}
          </div>
        </div>

        {/* ===== Posts / Transmissions ===== */}
        <div className="mb-3 flex items-center justify-between border-b border-cyber-cyan/20 pb-2">
          <div className="text-[10px] font-bold uppercase tracking-[0.3em] neon-text">
            ▸ TRANSMISSION_LOG
          </div>
          <div className="text-[9px] uppercase tracking-widest text-cyber-dim">
            {posts.length} records
          </div>
        </div>

        {posts.length === 0 && (
          <div className="corner-frame rounded-sm border border-cyber-cyan/20 bg-cyber-panel/70 p-8 text-center">
            <div className="mb-3 text-4xl flicker">◈</div>
            <div className="text-xs uppercase tracking-widest text-cyber-dim">
              // no transmissions
            </div>
          </div>
        )}

        <div className="space-y-3">
          {posts.map((p) => (
            <PostCard
              key={p.id}
              post={p}
              currentUserId={currentUser.id}
              onOpenProfile={onOpenProfile}
              onDelete={handleDelete}
              onUpdate={handleUpdate}
            />
          ))}
        </div>
      </div>

      {/* ===== Johnny Silverhand в углу ===== */}
      <PixelJohnny />

      {/* ===== Modals ===== */}
      {showFactionPicker && (
        <FactionPicker
          user={currentUser}
          canClose
          onClose={() => setShowFactionPicker(false)}
          onChosen={(u) => {
            if (onUserUpdate) onUserUpdate(u);
            setProfile((prev) => prev ? { ...prev, faction: u.faction } : prev);
          }}
        />
      )}

      {showChrome && (
        <div
          className="fixed inset-0 z-[250] flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm"
          onClick={() => setShowChrome(false)}
        >
          <div
            className="corner-frame w-[520px] rounded-sm border border-cyber-cyan/50 bg-cyber-panel p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <div className="text-sm font-bold uppercase tracking-widest neon-text">
                ◆ CHROME_SLOTS
              </div>
              <button
                onClick={() => setShowChrome(false)}
                className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15"
              >
                ✕
              </button>
            </div>
            <ChromePanel
              user={currentUser}
              onUpdate={(u) => {
                if (onUserUpdate) onUserUpdate(u);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
'''


PROFILE_CSS = r'''
    /* ============ PROFILE PAGE ============ */
    .profile-scanlines {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: repeating-linear-gradient(
        0deg,
        transparent 0,
        transparent 3px,
        rgba(0,240,255,0.02) 4px,
        transparent 5px
      );
      border-radius: inherit;
      overflow: hidden;
    }

    .avatar-glow {
      position: absolute;
      inset: -8px;
      border-radius: 50%;
      pointer-events: none;
      background: radial-gradient(circle, rgba(0,240,255,0.25), transparent 70%);
      animation: avatar-glow-pulse 3s ease-in-out infinite;
    }
    @keyframes avatar-glow-pulse {
      0%, 100% { opacity: 0.5; transform: scale(1); }
      50%      { opacity: 0.9; transform: scale(1.05); }
    }

    .stat-cell {
      position: relative;
      border: 1px solid rgba(0,240,255,0.25);
      background: rgba(0,240,255,0.04);
      padding: 10px 12px;
      text-align: center;
      transition: border-color 0.15s, background 0.15s;
    }
    .stat-cell:hover {
      border-color: rgba(0,240,255,0.6);
      background: rgba(0,240,255,0.08);
    }
    .stat-cell::before,
    .stat-cell::after {
      content: "";
      position: absolute;
      width: 6px;
      height: 6px;
      border: 1px solid rgba(0,240,255,0.5);
      pointer-events: none;
    }
    .stat-cell::before {
      top: -1px; left: -1px;
      border-right: none; border-bottom: none;
    }
    .stat-cell::after {
      bottom: -1px; right: -1px;
      border-left: none; border-top: none;
    }
    .stat-value {
      font-size: 20px;
      font-weight: bold;
      line-height: 1.1;
      text-shadow: 0 0 8px currentColor;
    }
    .stat-label {
      margin-top: 4px;
      font-size: 9px;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      color: #5a7a95;
    }

    /* ============ PIXEL JOHNNY ============ */
    .johnny-corner {
      position: fixed;
      right: 18px;
      bottom: 14px;
      z-index: 30;
      pointer-events: none;
      user-select: none;
    }
    .johnny-corner canvas {
      animation: johnny-float 4s ease-in-out infinite;
    }
    @keyframes johnny-float {
      0%, 100% { transform: translateY(0); }
      50%      { transform: translateY(-3px); }
    }
    .johnny-label {
      margin-top: 6px;
      text-align: center;
      font-size: 8px;
      letter-spacing: 0.4em;
      text-transform: uppercase;
      color: rgba(0,240,255,0.5);
      text-shadow: 0 0 6px rgba(0,240,255,0.6);
    }

    /* Johnny скрывается на маленьких экранах */
    @media (max-width: 900px) {
      .johnny-corner { display: none; }
    }
'''


def write_file(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.write_text(content, encoding="utf-8")
    print(f"  {'~' if existed else '+'} {rel}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    src = root / "frontend" / "src"

    print("\nСпринт 20 — Profile page + Johnny Silverhand\n")

    write_file(root, "frontend/src/PixelJohnny.tsx", PIXEL_JOHNNY)
    write_file(root, "frontend/src/ProfilePage.tsx", PROFILE_PAGE)

    # CSS
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "PROFILE PAGE" not in css_text:
        css_text = css_text.rstrip() + "\n" + PROFILE_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    # Прокидываем onUserUpdate в ProfilePage из App
    app_path = src / "App.tsx"
    app_text = app_path.read_text(encoding="utf-8")
    if "onUserUpdate={(u) => setUser(u)}" not in app_text:
        # ищем монтирование ProfilePage
        old_block = """        {mode === "profile" && profileUserId !== null && (
          <ProfilePage
            userId={profileUserId}
            currentUser={user}
            onBack={() => { setMode("chats"); setProfileUserId(null); }}
            onOpenProfile={openProfile}
            onChatWith={chatWithUser}
          />
        )}"""
        new_block = """        {mode === "profile" && profileUserId !== null && (
          <ProfilePage
            userId={profileUserId}
            currentUser={user}
            onBack={() => { setMode("chats"); setProfileUserId(null); }}
            onOpenProfile={openProfile}
            onChatWith={chatWithUser}
            onUserUpdate={(u) => setUser(u)}
          />
        )}"""
        if old_block in app_text:
            app_text = app_text.replace(old_block, new_block, 1)
            app_path.write_text(app_text, encoding="utf-8")
            print(f"  ~ {app_path} (передал onUserUpdate)")
        else:
            print(f"  > {app_path} (ProfilePage-блок не найден — вставь onUserUpdate вручную)")

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что нового:")
    print("  • Вкладка ◈ ME — полностью в стиле кибердеки (NET_ID, ranking, stat-cells)")
    print("  • В правом-нижнем углу — пиксельный Johnny Silverhand, курит, дым идёт")
    print("  • Johnny мерцает сигаретой, светодиодом на руке и моргает очками")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())