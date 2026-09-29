#!/usr/bin/env python3
"""sprint26_part3.py - final UI integration for channels/tools/comments."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


CHATWINDOW_PATCHES = [
    # 1. messages scroll area → conditional
    (
        '      <div\n'
        '        ref={scrollRef}\n'
        '        onScroll={onScroll}\n'
        '        className="msg-scroll flex-1 overflow-y-auto bg-black/25 px-4 py-4"\n'
        '      >',
        '      {activeTool === "chat" && (\n'
        '      <div\n'
        '        ref={scrollRef}\n'
        '        onScroll={onScroll}\n'
        '        className="msg-scroll flex-1 overflow-y-auto bg-black/25 px-4 py-4"\n'
        '      >',
    ),

    # 2. close messages condition + open nothing (composer stays)
    (
        '        <div ref={bottomRef} />\n'
        '      </div>\n'
        '\n'
        '      {(replyTo || editing) && (',
        '        <div ref={bottomRef} />\n'
        '      </div>\n'
        '      )}\n'
        '\n'
        '      {activeTool === "chat" && (replyTo || editing) && (',
    ),

    # 3. composer → conditional + add tools + comments at the end
    (
        '      <div className="relative border-t border-cyber-cyan/25 panel-solid p-3">',
        '      {activeTool === "chat" && (\n'
        '      <div className="relative border-t border-cyber-cyan/25 panel-solid p-3">',
    ),
    (
        '        {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}\n'
        '        {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}\n'
        '      </div>\n'
        '\n'
        '      {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}',
        '        {emojiOpen && <EmojiPicker onPick={(e) => setText((t) => t + e)} onClose={() => setEmojiOpen(false)} />}\n'
        '        {stickerOpen && <StickerPicker onPick={sendSticker} onClose={() => setStickerOpen(false)} />}\n'
        '      </div>\n'
        '      )}\n'
        '\n'
        '      {activeTool === "doc" && (\n'
        '        <DocTool chatId={chat.id} canEdit={!!(chat.my_permissions?.can_post)} />\n'
        '      )}\n'
        '      {activeTool === "board" && (\n'
        '        <KanbanTool chatId={chat.id} canEdit={!!(chat.my_permissions?.can_post)} userName={currentUser.username} />\n'
        '      )}\n'
        '      {activeTool === "calendar" && (\n'
        '        <CalendarTool chatId={chat.id} canEdit={!!(chat.my_permissions?.can_post)} userName={currentUser.username} />\n'
        '      )}\n'
        '\n'
        '      {commentsFor && (\n'
        '        <CommentsDrawer\n'
        '          parentMessage={commentsFor}\n'
        '          currentUser={currentUser}\n'
        '          send={send}\n'
        '          subscribe={subscribe}\n'
        '          onClose={() => setCommentsFor(null)}\n'
        '        />\n'
        '      )}\n'
        '\n'
        '      {lightbox && <Lightbox src={lightbox} onClose={() => setLightbox(null)} />}',
    ),

    # 4. pass channel props into MessageBubble
    (
        '                      onPin={handlePin}\n'
        '                    />',
        '                      onPin={handlePin}\n'
        '                      chatIsChannel={chat.is_channel}\n'
        '                      onOpenComments={(mm) => setCommentsFor(mm)}\n'
        '                    />',
    ),
]


MESSAGEBUBBLE_PATCHES = [
    # props in signature
    (
        '  onReply, onEdit, onDelete, onRetry, readByPeer,\n'
        '  onOpenImage, onOpenProfile, onReact, onPin, onMenuOpenChange\n'
        '}: {',
        '  onReply, onEdit, onDelete, onRetry, readByPeer,\n'
        '  onOpenImage, onOpenProfile, onReact, onPin, onMenuOpenChange,\n'
        '  chatIsChannel = false,\n'
        '  onOpenComments,\n'
        '}: {',
    ),
    (
        '  onMenuOpenChange?: (open: boolean) => void;\n'
        '}) {',
        '  onMenuOpenChange?: (open: boolean) => void;\n'
        '  chatIsChannel?: boolean;\n'
        '  onOpenComments?: (m: Message) => void;\n'
        '}) {',
    ),
    # render comments button before the time row
    (
        '          <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">\n'
        '            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}',
        '          {chatIsChannel && !msg.reply_to_id && !msg.is_deleted && onOpenComments && (\n'
        '            <button\n'
        '              className="post-comments-btn"\n'
        '              onClick={(e) => { e.stopPropagation(); onOpenComments(msg); }}\n'
        '            >\n'
        '              ◈ открыть комментарии\n'
        '            </button>\n'
        '          )}\n'
        '          <div className="mt-1 flex items-center justify-end gap-2 text-[9px] uppercase tracking-wider">\n'
        '            {msg.edited_at && <span className="text-cyber-yellow/80">[edited]</span>}',
    ),
]


# Additional CSS for tools overlay (in case ChatWindow renders tools before composer ends)
EXTRA_CSS = r'''
    /* ==== Tools render under tabs, above composer ==== */
    .tool-pane {
      flex: 1;
      min-height: 0;
    }
'''


def patch_file(path: Path, pairs: list[tuple[str, str]]) -> int:
    if not path.exists():
        print(f"  ! не найдено: {path}")
        return 0
    text = path.read_text(encoding="utf-8")
    changed = 0
    for old, new in pairs:
        if old in text:
            text = text.replace(old, new, 1)
            changed += 1
        else:
            # silent skip — we'll report count
            pass
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path} ({changed}/{len(pairs)} патчей применено)")
    else:
        print(f"  > {path} (0/{len(pairs)} — ни один не применён)")
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

    src = root / "frontend" / "src"

    print("\nСпринт 26 part 3 — финальная UI-интеграция\n")

    cw = patch_file(src / "ChatWindow.tsx", CHATWINDOW_PATCHES)
    mb = patch_file(src / "MessageBubble.tsx", MESSAGEBUBBLE_PATCHES)

    # CSS
    css_path = src / "index.css"
    css_text = css_path.read_text(encoding="utf-8")
    if "Tools render under tabs" not in css_text:
        css_text = css_text.rstrip() + "\n" + EXTRA_CSS + "\n"
        css_path.write_text(css_text, encoding="utf-8")
        print(f"  ~ {css_path}")

    print()
    print(f"ChatWindow: {cw}/{len(CHATWINDOW_PATCHES)}")
    print(f"MessageBubble: {mb}/{len(MESSAGEBUBBLE_PATCHES)}")

    if cw < 4 or mb < 3:
        print()
        print("⚠ Некоторые патчи не нашли якорь — ChatWindow/MessageBubble отличаются от ожидаемого.")
        print("  Пришли мне текущие файлы, я подгоню патчи точно.")

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())