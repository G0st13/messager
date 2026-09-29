#!/usr/bin/env python3
"""sprint26_part4.py - role editor + channel toggle + locked composer."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


# ============================================================== GroupInfoPanel (полностью переписываем)
GROUP_INFO = r'''import { useCallback, useEffect, useState } from "react";
import Avatar from "./Avatar";
import { api } from "./api";
import type { Chat, ChatMember, User } from "./types";

const ROLES = ["owner", "admin", "moderator", "member", "guest"] as const;
type Role = typeof ROLES[number];

const PERMS: { key: string; label: string }[] = [
  { key: "can_post",         label: "писать" },
  { key: "can_comment",      label: "комментировать" },
  { key: "can_pin",          label: "закреплять" },
  { key: "can_delete_any",   label: "удалять чужие" },
  { key: "can_invite",       label: "приглашать" },
  { key: "can_kick",         label: "выгонять" },
  { key: "can_change_info",  label: "менять инфо" },
];

function roleLabel(r: string): string {
  return r === "owner" ? "владелец"
       : r === "admin" ? "админ"
       : r === "moderator" ? "модератор"
       : r === "guest" ? "гость"
       : "участник";
}

export default function GroupInfoPanel({
  chat, currentUser, onClose, onChatUpdated, onLeft,
}: {
  chat: Chat;
  currentUser: User;
  onClose: () => void;
  onChatUpdated: (c: Chat) => void;
  onLeft: () => void;
}) {
  const [members, setMembers] = useState<ChatMember[]>([]);
  const [title, setTitle] = useState(chat.title || "");
  const [description, setDescription] = useState(chat.description || "");
  const [adding, setAdding] = useState("");
  const [error, setError] = useState("");
  const [invite, setInvite] = useState<string | null>(null);
  const [expandedPerms, setExpandedPerms] = useState<number | null>(null);

  const isGroup = chat.is_group;
  const isChannel = chat.is_channel;
  const isOwner = chat.my_role === "owner";
  const isAdmin = chat.my_role === "owner" || chat.my_role === "admin";

  const reload = useCallback(async () => {
    if (!isGroup) return;
    try {
      const { data } = await api.get<ChatMember[]>(`/chats/${chat.id}/members`);
      setMembers(data);
    } catch {}
  }, [chat.id, isGroup]);

  useEffect(() => { reload(); }, [reload]);

  const save = async () => {
    setError("");
    try {
      const { data } = await api.patch<Chat>(`/chats/${chat.id}`, {
        title: isGroup ? title : undefined,
        description: isGroup ? description : undefined,
      });
      onChatUpdated(data);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Ошибка");
    }
  };

  const addMember = async () => {
    if (!adding.trim()) return;
    setError("");
    try {
      await api.post(`/chats/${chat.id}/members`, { username: adding.trim() });
      setAdding("");
      await reload();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Не удалось добавить");
    }
  };

  const removeMember = async (userId: number) => {
    if (!confirm("Удалить участника?")) return;
    try {
      await api.delete(`/chats/${chat.id}/members/${userId}`);
      await reload();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Не удалось удалить");
    }
  };

  const changeRole = async (userId: number, role: Role) => {
    try {
      await api.patch(`/chats/${chat.id}/members/${userId}/role`, { role });
      await reload();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Не удалось изменить роль");
    }
  };

  const togglePerm = async (userId: number, permKey: string, current: boolean) => {
    try {
      await api.patch(`/chats/${chat.id}/members/${userId}/permissions`, {
        [permKey]: !current,
      });
      await reload();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Не удалось изменить права");
    }
  };

  const leave = async () => {
    if (!confirm("Выйти из группы?")) return;
    try {
      await api.post(`/chats/${chat.id}/leave`);
      onLeft();
      onClose();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Ошибка");
    }
  };

  const generateInvite = async () => {
    try {
      const { data } = await api.post<{ token: string; url: string }>(`/chats/${chat.id}/invite`);
      setInvite(data.url);
      await navigator.clipboard.writeText(data.url).catch(() => {});
    } catch (e: any) {
      setError(e.response?.data?.detail || "Ошибка");
    }
  };

  const input = "cyber-input w-full rounded-sm px-3 py-2 text-sm";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="animate-materialize flex h-[640px] w-[560px] flex-col rounded-sm border border-cyber-cyan/50 bg-cyber-panel shadow-neon-cyan"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-cyber-cyan/20 p-4">
          <h2 className="text-sm font-bold uppercase tracking-widest neon-text">
            {isChannel ? "▸ КАНАЛ" : isGroup ? "▸ ГРУППА" : "▸ ИНФО"}
          </h2>
          <button onClick={onClose} className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-xs neon-text-mag hover:bg-cyber-magenta/15">✕</button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          <div className="mb-4 flex flex-col items-center">
            <Avatar
              user={chat.peer || { username: chat.title || "G", display_name: chat.title || "Group", avatar_color: chat.avatar_color }}
              size={96}
            />
            {isGroup && isAdmin ? (
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Название"
                className="mt-3 w-full rounded-sm border border-cyber-cyan/30 bg-black/40 px-3 py-2 text-center text-lg font-semibold text-cyber-cyan outline-none focus:border-cyber-cyan"
              />
            ) : (
              <div className="mt-3 text-lg font-semibold neon-text">
                {chat.peer ? (chat.peer.display_name || chat.peer.username) : (chat.title || `Чат #${chat.id}`)}
              </div>
            )}
            {isGroup && (
              <div className="mt-1 text-xs text-cyber-dim">
                {chat.member_count} участников
                {isChannel && <span className="channel-header-badge ml-2">КАНАЛ</span>}
              </div>
            )}
          </div>

          {isGroup && (
            <div className="mb-4">
              <label className="mb-1 block text-[10px] uppercase tracking-widest text-cyber-cyan/70">// описание</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={!isAdmin}
                rows={2}
                className={input + " resize-none disabled:opacity-60"}
              />
            </div>
          )}

          {isGroup && isAdmin && (
            <button onClick={save} className="cyber-btn mb-4 w-full rounded-sm py-2 text-xs">
              [ СОХРАНИТЬ ]
            </button>
          )}

          {isGroup && (
            <>
              <div className="mb-2 text-[10px] uppercase tracking-widest text-cyber-cyan/70">
                // участники ({members.length})
              </div>

              {isAdmin && (
                <div className="mb-3 flex gap-2">
                  <input
                    value={adding}
                    onChange={(e) => setAdding(e.target.value)}
                    placeholder="username"
                    className={input}
                    onKeyDown={(e) => e.key === "Enter" && addMember()}
                  />
                  <button onClick={addMember} className="cyber-btn rounded-sm px-4 text-xs">+</button>
                </div>
              )}

              <div className="space-y-1">
                {members.map((m) => {
                  const isSelf = m.user_id === currentUser.id;
                  const canEditThis = isAdmin && m.role !== "owner" && !isSelf;
                  const isExpanded = expandedPerms === m.user_id;

                  return (
                    <div
                      key={m.user_id}
                      className="rounded-sm border border-cyber-cyan/15 bg-black/20 p-2"
                    >
                      <div className="flex items-center gap-2">
                        <Avatar
                          user={{ username: m.username, display_name: m.display_name, avatar_color: m.avatar_color }}
                          size={32}
                        />
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-bold text-cyber-text">
                            {m.display_name || m.username}
                            {isSelf && <span className="ml-1 text-[9px] text-cyber-dim">(вы)</span>}
                          </div>
                          <div className="text-[10px] text-cyber-dim">
                            @{m.username} · {roleLabel(m.role)}
                          </div>
                        </div>

                        {canEditThis && (
                          <>
                            <select
                              value={m.role}
                              onChange={(e) => changeRole(m.user_id, e.target.value as Role)}
                              className="role-select"
                            >
                              {ROLES.filter((r) => r !== "owner").map((r) => (
                                <option key={r} value={r}>{roleLabel(r)}</option>
                              ))}
                            </select>

                            {isOwner && (
                              <button
                                onClick={() => setExpandedPerms(isExpanded ? null : m.user_id)}
                                className="rounded-sm border border-cyber-cyan/30 px-2 py-1 text-[10px] text-cyber-cyan hover:bg-cyber-cyan/10"
                                title="Права"
                              >
                                ⚙
                              </button>
                            )}

                            <button
                              onClick={() => removeMember(m.user_id)}
                              className="rounded-sm border border-cyber-magenta/40 px-2 py-1 text-[10px] text-cyber-magenta hover:bg-cyber-magenta/15"
                              title="Удалить"
                            >
                              ✕
                            </button>
                          </>
                        )}
                      </div>

                      {isExpanded && (
                        <div className="mt-2 grid grid-cols-2 gap-1 border-t border-cyber-cyan/15 pt-2">
                          {PERMS.map((p) => {
                            const enabled = !!m.permissions?.[p.key];
                            return (
                              <button
                                key={p.key}
                                onClick={() => togglePerm(m.user_id, p.key, enabled)}
                                className={
                                  "flex items-center justify-between gap-2 rounded-sm border px-2 py-1 text-[10px] uppercase tracking-wider transition " +
                                  (enabled
                                    ? "border-cyber-cyan/60 bg-cyber-cyan/10 text-cyber-cyan"
                                    : "border-cyber-dim/30 text-cyber-dim hover:border-cyber-cyan/40")
                                }
                              >
                                <span>{p.label}</span>
                                <span className={enabled ? "neon-text" : "opacity-40"}>{enabled ? "●" : "○"}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {isAdmin && (
                <button
                  onClick={generateInvite}
                  className="cyber-btn mt-4 w-full rounded-sm py-2 text-xs"
                >
                  {invite ? "◈ ссылка скопирована" : "🔗 создать пригласительную ссылку"}
                </button>
              )}
              {invite && (
                <div className="mt-2 truncate rounded-sm border border-cyber-cyan/20 bg-black/40 px-3 py-2 text-[10px] text-cyber-cyan">
                  {invite}
                </div>
              )}
            </>
          )}

          {error && (
            <div className="mt-3 rounded-sm border border-cyber-magenta/40 bg-cyber-magenta/10 px-3 py-2 text-xs neon-text-mag">
              ⚠ {error}
            </div>
          )}
        </div>

        {isGroup && (
          <div className="border-t border-cyber-cyan/20 p-4">
            <button
              onClick={leave}
              className="w-full rounded-sm border border-cyber-magenta/40 py-2 text-xs font-bold uppercase tracking-widest neon-text-mag hover:bg-cyber-magenta/15"
            >
              выйти
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
'''


# ============================================================== SettingsPanel patches
SETTINGS_PATCHES = [
    # state — добавить isChannel
    (
        '  const [groupTitle, setGroupTitle] = useState("");\n'
        '      const [groupMembers, setGroupMembers] = useState("");\n'
        '      const [groupDesc, setGroupDesc] = useState("");',
        '  const [groupTitle, setGroupTitle] = useState("");\n'
        '      const [groupMembers, setGroupMembers] = useState("");\n'
        '      const [groupDesc, setGroupDesc] = useState("");\n'
        '      const [groupIsChannel, setGroupIsChannel] = useState(false);',
    ),
    # createGroup — передать is_channel
    (
        '          const { data } = await api.post<Chat>("/chats", {\n'
        '            title: groupTitle,\n'
        '            description: groupDesc || null,\n'
        '            is_group: true,\n'
        '            member_usernames: names,\n'
        '          });',
        '          const { data } = await api.post<Chat>("/chats", {\n'
        '            title: groupTitle,\n'
        '            description: groupDesc || null,\n'
        '            is_group: true,\n'
        '            is_channel: groupIsChannel,\n'
        '            member_usernames: names,\n'
        '          });',
    ),
    # UI — добавить тумблер канала после поля участников
    (
        '                  <button\n'
        '                    onClick={createGroup}\n'
        '                    className="cyber-btn w-full rounded-sm py-2 text-xs"\n'
        '                  >\n'
        '                    [ CREATE GROUP ]\n'
        '                  </button>',
        '                  <button\n'
        '                    type="button"\n'
        '                    onClick={() => setGroupIsChannel(!groupIsChannel)}\n'
        '                    className={\n'
        '                      "flex w-full items-center gap-3 rounded-sm border p-3 text-left transition " +\n'
        '                      (groupIsChannel\n'
        '                        ? "border-cyber-yellow bg-cyber-yellow/10"\n'
        '                        : "border-cyber-cyan/25 hover:border-cyber-cyan/60")\n'
        '                    }\n'
        '                  >\n'
        '                    <span className="text-2xl" style={{ color: groupIsChannel ? "#fcee0a" : "#5a7a95" }}>📢</span>\n'
        '                    <div className="flex-1">\n'
        '                      <div className={"text-xs font-bold uppercase tracking-widest " + (groupIsChannel ? "neon-text-yel" : "text-cyber-dim")}>\n'
        '                        Канал\n'
        '                      </div>\n'
        '                      <div className="text-[10px] text-cyber-dim">\n'
        '                        писать могут только админы, остальные читают и комментируют\n'
        '                      </div>\n'
        '                    </div>\n'
        '                    <div className={"rounded-sm border px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest " + (groupIsChannel ? "border-cyber-yellow text-cyber-yellow" : "border-cyber-dim/40 text-cyber-dim")}>\n'
        '                      {groupIsChannel ? "on" : "off"}\n'
        '                    </div>\n'
        '                  </button>\n'
        '\n'
        '                  <button\n'
        '                    onClick={createGroup}\n'
        '                    className="cyber-btn w-full rounded-sm py-2 text-xs"\n'
        '                  >\n'
        '                    [ {groupIsChannel ? "CREATE CHANNEL" : "CREATE GROUP"} ]\n'
        '                  </button>',
    ),
]


# ============================================================== ChatWindow patches — locked composer
CHATWINDOW_PATCHES = [
    # заменить composer на lock, если нельзя писать
    (
        '      {activeTool === "chat" && (\n'
        '      <div className="relative border-t border-cyber-cyan/25 panel-solid p-3">',
        '      {activeTool === "chat" && chat.is_channel && !chat.my_permissions?.can_post && (\n'
        '        <div className="channel-lock">\n'
        '          🔒 В этом канале писать могут только <strong>администраторы</strong>\n'
        '        </div>\n'
        '      )}\n'
        '\n'
        '      {activeTool === "chat" && (!chat.is_channel || chat.my_permissions?.can_post) && (\n'
        '      <div className="relative border-t border-cyber-cyan/25 panel-solid p-3">',
    ),
]


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
    if changed:
        path.write_text(text, encoding="utf-8")
        print(f"  ~ {path} ({changed}/{len(pairs)})")
    else:
        print(f"  > {path} (0/{len(pairs)})")
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

    print("\nСпринт 26 part 4 — роли, каналы, locked composer\n")

    # GroupInfoPanel — переписываем полностью
    (src / "GroupInfoPanel.tsx").write_text(GROUP_INFO, encoding="utf-8")
    print(f"  ~ {src / 'GroupInfoPanel.tsx'}")

    # SettingsPanel — патчи
    patch_file(src / "SettingsPanel.tsx", SETTINGS_PATCHES)

    # ChatWindow — locked composer
    patch_file(src / "ChatWindow.tsx", CHATWINDOW_PATCHES)

    print()
    print("Дальше:")
    print(f"  cd {root}")
    print("  docker compose -f infra/docker-compose.yml up --build")
    print()
    print("Что появилось:")
    print("  • GroupInfoPanel — dropdown ролей для каждого участника")
    print("  • Кнопка ⚙ (только owner) — раскрывает матрицу прав (7 переключателей)")
    print("  • SettingsPanel — тумблер «Канал» при создании группы")
    print("  • Для гостей в канале — плашка «🔒 только админы могут постить»")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())