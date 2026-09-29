#!/usr/bin/env python3
"""sprint11h.py - fix onMenuOpenChange ReferenceError + правильное поднятие меню."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# Полностью переписываем MessageBubble без onMenuOpenChange
MESSAGEBUBBLE = r'''import { memo, useEffect, useState } from "react";
import Avatar from "./Avatar";
import { fileUrl, humanSize } from "./api";
import { renderMarkdown } from "./markdown";
import type { Message, User } from "./types";

const QUICK_REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🔥"];

function iconFor(mime: string): string {
  if (mime.startsWith("image/")) return "▣";
  if (mime.startsWith("audio/")) return "◍";
  if (mime.startsWith("video/")) return "▶";
  if (mime.includes("pdf")) return "▤";
  if (mime.includes("zip")) return "▥";
  return "▧";
}

function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function MessageBubbleInner({
  msg, mine, showAvatar, isLast, onReply, onEdit, onDelete, onRetry, readByPeer,
  onOpenImage, onOpenProfile, onReact, onPin
}: {
  msg: Message;
  mine: boolean;
  showAvatar: boolean;
  isLast: boolean;
  onReply: (m: Message) => void;
  onEdit: (m: Message) => void;
  onDelete: (m: Message) => void;
  onRetry: (m: Message) => void;
  readByPeer: boolean;
  onOpenImage: (url: string) => void;
  onOpenProfile: (userId: number) => void;
  onReact: (messageId: number, emoji: string) => void;
  onPin: (m: Message) => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [reactOpen, setReactOpen] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [audioCurrent, setAudioCurrent] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);

  // клик вне меню — закрываем
  useEffect(() => {
    if (!menuOpen && !reactOpen) return;
    const h = (e: MouseEvent) => {
      const t = e.target as HTMLElement;
      if (!t.closest(".msg-menu-container")) {
        setMenuOpen(false);
        setReactOpen(false);
      }
    };
    setTimeout(() => document.addEventListener("mousedown", h), 0);
    return () => document.removeEventListener("mousedown", h);
  }, [menuOpen, reactOpen]);

  const sendStatus = msg.send_status;
  const isPending = sendStatus === "pending";
  const isFailed = sendStatus === "failed";
  const isVirtual = msg.id < 0;

  // поднимаем корневой div, если открыто меню
  const elevated = menuOpen || reactOpen;

  if (msg.message_type === "system") {
    return (
      <div className="my-2 flex justify-center">
        <div className="neon-border-yel rounded-sm bg-cyber-yellow/5 px-3 py-1 text-[10px] uppercase tracking-widest neon-text-yel">
          ⚠ {msg.text}
        </div>
      </div>
    );
  }

  const author: Pick<User, "username" | "display_name" | "avatar_color"> = {
    username: msg.author_username,
    display_name: msg.author_display,
    avatar_color: msg.author_avatar_color,
  };

  const accent = isFailed ? "#ff2d55" : mine ? "#00f0ff" : "#ff00a0";
  const bubbleStyle = {
    background: isFailed
      ? "rgba(255,45,85,0.18)"
      : mine
      ? "rgba(0,240,255,0.16)"
      : "rgba(255,0,160,0.14)",
    border: `1px solid ${accent}66`,
    color: "#eaf4ff",
    opacity: isPending ? 0.78 : 1,
  };

  const isSticker = msg.message_type === "sticker" && !msg.is_deleted;
  const isImage = msg.message_type === "image" && msg.attachment && !msg.is_deleted;
  const isVideo = msg.message_type === "file" && msg.attachment &&
    msg.attachment.content_type.startsWith("video/") && !msg.is_deleted;
  const isVoice = msg.message_type === "voice" && msg.attachment && !msg.is_deleted;
  const isFile = msg.message_type === "file" && msg.attachment && !isVideo && !msg.is_deleted;

  const hasReactions = msg.reactions && msg.reactions.length > 0;

  // Класс поднятия
  const rootClass =
    "group flex gap-2 msg-menu-container " +
    (mine ? "flex-row-reverse " : "") +
    (elevated ? "msg-elevated" : "");

  if (isSticker) {
    return (
      <div className={rootClass}>
        {!mine ? (
          <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
            {showAvatar && <Avatar user={author} size={32} />}
          </button>
        ) : null}
        <div className="relative">
          <div className={"text-7xl leading-none " + (isPending ? "opacity-70" : "")}>
            {msg.text}
          </div>
          <div className={"mt-1 flex items-center gap-2 text-[9px] uppercase tracking-wider " + (mine ? "justify-end" : "")}>
            <span className="text-cyber-dim">
              {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            {mine && (
              <span className={isPending ? "text-cyber-dim" : isFailed ? "neon-text-mag" : readByPeer ? "neon-text" : "text-cyber-dim"}>
                {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
              </span>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={rootClass} id={`msg-${msg.id}`}>
      {!mine ? (
        <button className="w-8 shrink-0" onClick={() => onOpenProfile(msg.author_id)}>
          {showAvatar && <Avatar user={author} size={32} />}
        </button>
      ) : null}

      <div className={"relative max-w-[70%] " + (mine ? "items-end" : "items-start")}>
        {!mine && showAvatar && (
          <button
            onClick={() => onOpenProfile(msg.author_id)}
            className="mb-1 ml-2 text-[10px] font-bold uppercase tracking-widest neon-text-mag text-readable"
          >
            ◂ {msg.author_display || msg.author_username}
          </button>
        )}

        <div
          className={"relative overflow-hidden rounded-sm text-sm " + (isImage || isVideo ? "" : " px-3 py-2")}
          style={bubbleStyle}
        >
          {msg.is_pinned && (
            <div className="mb-1 flex items-center gap-1 text-[9px] uppercase tracking-widest neon-text-yel">
              📌 pinned
            </div>
          )}

          {msg.reply_to_id && !msg.is_deleted && (
            <div
              className="mx-1 mb-2 mt-1 rounded-sm border-l-2 bg-black/50 px-2 py-1 text-[10px]"
              style={{ borderColor: accent }}
            >
              <div className="font-bold uppercase tracking-wider" style={{ color: accent }}>
                ↳ {msg.reply_author || "?"}
              </div>
              <div className="truncate text-cyber-dim">{msg.reply_preview || "..."}</div>
            </div>
          )}

          {isImage && msg.attachment && (
            <img
              src={fileUrl(msg.attachment.id)}
              alt={msg.attachment.filename}
              onClick={() => !isVirtual && onOpenImage(fileUrl(msg.attachment!.id))}
              className="block max-h-80 w-full cursor-pointer object-cover"
              loading="lazy"
              decoding="async"
            />
          )}

          {isVideo && msg.attachment && (
            <video
              src={fileUrl(msg.attachment.id)}
              controls
              preload="none"
              className="block max-h-80 w-full bg-black"
            />
          )}

          {isVoice && msg.attachment && (
            <div className="flex items-center gap-3 px-2 py-3" style={{ minWidth: 220 }}>
              <button
                onClick={() => {
                  const prev = (window as any).__voiceAudio as HTMLAudioElement;
                  if (prev && prev.dataset.id === String(msg.attachment!.id)) {
                    if (prev.paused) prev.play(); else prev.pause();
                    return;
                  }
                  if (prev) prev.pause();
                  const el = new Audio(fileUrl(msg.attachment!.id));
                  (window as any).__voiceAudio = el;
                  el.dataset.id = String(msg.attachment!.id);
                  el.ontimeupdate = () => setAudioCurrent(el.currentTime);
                  el.onloadedmetadata = () => setAudioDuration(el.duration);
                  el.onplay = () => setAudioPlaying(true);
                  el.onpause = () => setAudioPlaying(false);
                  el.onended = () => { setAudioPlaying(false); setAudioCurrent(0); };
                  el.play();
                }}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-sm neon-border"
                style={{ color: accent }}
              >
                {audioPlaying ? "❚❚" : "▶"}
              </button>
              <div className="flex-1 text-xs">
                <div className="flex items-center gap-2">
                  <span className="text-xl" style={{ color: accent }}>◍</span>
                  <span className="font-mono neon-text">
                    {fmtDuration(audioPlaying ? audioCurrent : (audioDuration || 0))}
                  </span>
                </div>
                <div className="mt-1 flex h-3 items-end gap-[2px]">
                  {Array.from({ length: 24 }).map((_, i) => (
                    <div
                      key={i}
                      className="w-[2px]"
                      style={{
                        height: `${20 + ((i * 7) % 80)}%`,
                        background: accent,
                        opacity: audioPlaying ? 0.8 : 0.35,
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}

          {isFile && msg.attachment && (
            <a
              href={fileUrl(msg.attachment.id)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-3 px-2 py-2 transition hover:bg-cyber-cyan/5"
            >
              <div className="text-2xl" style={{ color: accent }}>
                {iconFor(msg.attachment.content_type)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-bold text-cyber-text text-readable">
                  {msg.attachment.filename}
                </div>
                <div className="text-[10px] uppercase tracking-wider text-cyber-dim">
                  {humanSize(msg.attachment.size)}
                </div>
              </div>
            </a>
          )}

          {!isImage && !isVideo && !isVoice && !isFile && (
            <div className={"text-readable text-[13px] leading-relaxed " + (msg.is_deleted ? "italic opacity-60" : "break-words")}>
              {msg.is_deleted ? msg.text : renderMarkdown(msg.text || "")}
            </div>
          )}

          {hasReactions && (
            <div className="mt-2 flex flex-wrap gap-1">
              {msg.reactions.map((r) => (
                <button
                  key={r.emoji}
                  onClick={() => onReact(msg.id, r.emoji)}
                  className={
                    "flex items-center gap-1 rounded-sm border px-2 py-0.5 text-xs transition " +
                    (r.is_mine
                      ? "border-cyber-cyan bg-cyber-cyan/20 neon-text"
                      : "border-cyber-cyan/25 bg-black/40 text-cyber-text hover:border-cyber-cyan/60")
                  }
                >
                  <span>{r.emoji}</span>
                  <span className="text-[10px] font-bold">{r.count}</span>
                </button>
              ))}
            </div>
          )}

          {isVirtual && isFailed && (
            <div className="mt-1.5 flex items-center justify-between gap-2 border-t border-cyber-magenta/30 pt-1 text-[9px] uppercase tracking-widest">
              <span className="neon-text-mag">⚠ not sent</span>
              <span className="text-cyber-dim">наведи → ⋮</span>
            </div>
          )}

          <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">
            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}
            <span className="text-cyber-dim">
              {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </span>
            {mine && !msg.is_deleted && (
              <span className={
                isPending ? "text-cyber-dim" :
                isFailed ? "neon-text-mag" :
                readByPeer ? "neon-text" : "text-cyber-dim"
              }>
                {isPending ? "⏳" : isFailed ? "⚠" : readByPeer ? "✓✓" : "✓"}
              </span>
            )}
          </div>
        </div>

        {!msg.is_deleted && (!isVirtual || isFailed) && (
          <div
            className={
              "absolute top-1 hidden items-center gap-1 group-hover:flex " +
              (mine ? "right-full mr-1" : "left-full ml-1")
            }
          >
            {!isVirtual && (
              <button
                onClick={() => setReactOpen(!reactOpen)}
                className="rounded-sm border border-cyber-cyan/40 panel-solid px-1.5 py-0.5 text-xs text-cyber-cyan hover:bg-cyber-cyan/20"
                title="Reaction"
              >
                ☺
              </button>
            )}
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              className={
                "rounded-sm border px-1.5 py-0.5 text-xs panel-solid " +
                (isFailed
                  ? "border-cyber-magenta/50 text-cyber-magenta hover:bg-cyber-magenta/20"
                  : "border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/20")
              }
              title="Menu"
            >
              ▾
            </button>
          </div>
        )}

        {reactOpen && (
          <div
            className={
              "absolute top-8 z-50 flex gap-1 rounded-sm border border-cyber-cyan/50 panel-solid p-1 " +
              (mine ? "right-0" : "left-0")
            }
            onMouseLeave={() => setReactOpen(false)}
          >
            {QUICK_REACTIONS.map((e) => (
              <button
                key={e}
                onClick={() => { onReact(msg.id, e); setReactOpen(false); }}
                className="rounded-sm p-1 text-lg transition hover:bg-cyber-cyan/20"
              >
                {e}
              </button>
            ))}
          </div>
        )}

        {menuOpen && (
          isVirtual && isFailed ? (
            <div
              className={
                "absolute z-50 mt-1 w-40 overflow-hidden rounded-sm border border-cyber-magenta/60 panel-solid text-xs " +
                (mine ? "right-0" : "left-0")
              }
            >
              <div className="border-b border-cyber-magenta/30 bg-cyber-magenta/10 px-3 py-1.5 text-[9px] uppercase tracking-widest neon-text-mag">
                ⚠ не отправлено
              </div>
              <button
                onClick={() => { onRetry(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
              >
                ↻ retry
              </button>
              <button
                onClick={() => { onDelete(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"
              >
                ✕ удалить
              </button>
            </div>
          ) : (
            <div
              className={
                "absolute z-50 mt-1 w-36 overflow-hidden rounded-sm border border-cyber-cyan/40 panel-solid text-xs " +
                (mine ? "right-0" : "left-0")
              }
            >
              <button
                onClick={() => { onReply(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
              >
                ↳ reply
              </button>
              <button
                onClick={() => { onPin(msg); setMenuOpen(false); }}
                className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-yellow hover:bg-cyber-yellow/15"
              >
                📌 {msg.is_pinned ? "unpin" : "pin"}
              </button>
              {mine && msg.message_type === "text" && (
                <button
                  onClick={() => { onEdit(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-2 text-left uppercase tracking-wider text-cyber-cyan hover:bg-cyber-cyan/15"
                >
                  ✎ edit
                </button>
              )}
              {mine && (
                <button
                  onClick={() => { onDelete(msg); setMenuOpen(false); }}
                  className="block w-full px-3 py-2 text-left uppercase tracking-wider neon-text-mag hover:bg-cyber-magenta/15"
                >
                  ✕ delete
                </button>
              )}
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default memo(MessageBubbleInner);
'''


# Убираем onMenuOpenChange из ChatWindow
CHATWINDOW_REPLACEMENTS = [
    (
        '                      onMenuOpenChange={(open) => {\n'
        '                        const el = document.getElementById(`item-${m.client_id || m.id}`);\n'
        '                        if (el) el.classList.toggle("menu-open", open);\n'
        '                      }}\n',
        '',
    ),
]


# CSS — поднятие сообщения с открытым меню
CSS_REPLACEMENTS = [
    (
        '    /* Когда у сообщения открыто меню — поднимаем весь его контейнер выше соседей */\n'
        '    .msg-item.menu-open {\n'
        '      z-index: 40;\n'
        '    }\n'
        '\n'
        '    /* Слой для вложенных absolute-меню */\n'
        '    .msg-layer-high {\n'
        '      z-index: 50 !important;\n'
        '    }',
        '    /* Когда у сообщения открыто меню — поднимаем его выше соседей */\n'
        '    .msg-menu-container.msg-elevated {\n'
        '      position: relative;\n'
        '      z-index: 60;\n'
        '    }\n'
        '\n'
        '    /* Внутри — меню абсолютно позиционируются и уже z-50+ */',
    ),
]


def patch_file(path: Path, pairs: list[tuple[str, str]]) -> bool:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    changed = False
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            changed = True
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path}")
    else:
        print(f"  > {path} (без изменений)")
    return changed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--path", default=".")
    p.add_argument("--name", default="my-messenger")
    args = p.parse_args()

    root = Path(args.path).expanduser().resolve() / args.name
    if not root.exists():
        print(f"ERR: {root} не найдено.", file=sys.stderr)
        return 1

    print("\nСпринт 11h — фикс onMenuOpenChange + правильные слои меню\n")

    src = root / "frontend" / "src"

    # Переписываем MessageBubble полностью — надёжнее чем патч
    (src / "MessageBubble.tsx").write_text(MESSAGEBUBBLE, encoding="utf-8")
    print(f"  ~ {src / 'MessageBubble.tsx'}")

    patch_file(src / "ChatWindow.tsx", CHATWINDOW_REPLACEMENTS)
    patch_file(src / "index.css", CSS_REPLACEMENTS)

    print("\nГотово. Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())