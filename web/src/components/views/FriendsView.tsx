import React, { useEffect, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { studio } from '../../api/studio';
import { apiGetBlob } from '../../api/client';
import { t } from '../../i18n';
import { fmtChatTime } from '../../utils/serverTime';
import { Send } from 'lucide-react';

const tr = (key: string, vars?: Record<string, string | number>) => {
  let s = t(key, key);
  if (!vars) return s;
  return s.replace(/\{(\w+)(:[^}]*)?\}/g, (m, name) =>
    name in vars ? String(vars[name]) : m);
};

// Parity ChatDialog.REACTIONS
const REACTIONS = ['👍', '❤️', '😂', '🎉', '😮', '😢'];

/** Parity FriendsPage: add teman, pending requests, couple requests, daftar
 * teman (status couple + presence + aksi couple/pvp/chat/profil/hapus), PvP. */
export const FriendsView: React.FC = () => {
  const {
    user, friends, friendRequests, pvpChallenges,
    sendFriendRequest, acceptFriendRequest, rejectFriendRequest,
    sendPvpChallenge, respondPvpChallenge, claimPvPReward,
    refreshSocial, showToast, applyLive, clockNow,
  } = useGame();

  const [friendName, setFriendName] = useState('');
  const [coupleRequests, setCoupleRequests] = useState<{ id: string; name: string; direction: string }[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [chatWith, setChatWith] = useState<any | null>(null);
  const [chatMsgs, setChatMsgs] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLimit, setChatLimit] = useState(50);
  const [chatCloudMode, setChatCloudMode] = useState(false);
  const [friendTyping, setFriendTyping] = useState(false);
  const [pendingAttachments, setPendingAttachments] = useState<any[]>([]);
  const [selectedMsg, setSelectedMsg] = useState<any | null>(null);
  const [replyTarget, setReplyTarget] = useState<any | null>(null);
  const [editingMsg, setEditingMsg] = useState<any | null>(null);
  const [editText, setEditText] = useState('');
  const [tick, setTick] = useState(0);
  const chatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const typingDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const typingClear = useRef<ReturnType<typeof setTimeout> | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);
  const chatListRef = useRef<HTMLDivElement | null>(null);

  const reload = () => { refreshSocial(); setTick((x) => x + 1); };
  useEffect(() => {
    refreshSocial();
    studio.friends().then((d) => {
      if (Array.isArray(d?.coupleRequests)) setCoupleRequests(d.coupleRequests);
    }).catch(() => undefined);
  }, [tick, refreshSocial]);

  // ── Admin block (parity load awal) ──
  if ((user as any).isAdmin) {
    return (
      <div className="px-4 md:px-8 pb-24 pt-4 max-w-3xl mx-auto animate-fade-in-up">
        <p className="text-center text-slate-500 py-16">{tr('friends_admin_block')}</p>
      </div>
    );
  }

  const post = (p: Promise<any>) =>
    p.then((r) => { applyLive(r); const m = r?.result || r; if (m?.msg) showToast(m?.ok === false ? 'info' : 'success', m.msg, ''); reload(); })
     .catch((e) => showToast('info', String(e?.message || e), ''));

  const myName = (user as any).displayName || (user as any).username || '';

  // ── ChatDialog parity: fetch (limit), reply/edit/delete/react, clear, poll 3s ──
  const fetchChat = (f: any, limit?: number) => {
    studio.friendChat(f.id, limit)
      .then((d) => {
        setChatMsgs(Array.isArray(d?.messages) ? d.messages : []);
        setChatCloudMode(!!d?.cloudMode);
        setFriendTyping(!!d?.friendTyping);
        reload();
      })
      .catch(() => setChatMsgs([]));
  };
  const discardPending = () => {
    if (pendingAttachments.length) {
      studio.discardFriendAttachments(pendingAttachments.map((a) => a.id)).catch(() => undefined);
    }
    setPendingAttachments([]);
  };
  const openChat = (f: any) => {
    setChatWith(f);
    setChatLimit(50);
    setSelectedMsg(null);
    setReplyTarget(null);
    setEditingMsg(null);
    setPendingAttachments([]);
    setFriendTyping(false);
    fetchChat(f);
    // PyQt: QTimer 3 detik refresh pesan saat dialog aktif.
    if (chatTimer.current) clearInterval(chatTimer.current);
    chatTimer.current = setInterval(() => fetchChat(f), 3000);
  };
  const closeChat = () => {
    if (chatTimer.current) { clearInterval(chatTimer.current); chatTimer.current = null; }
    if (typingDebounce.current) { clearTimeout(typingDebounce.current); typingDebounce.current = null; }
    if (typingClear.current) { clearTimeout(typingClear.current); typingClear.current = null; }
    discardPending();
    setChatWith(null);
  };
  useEffect(() => () => {
    if (chatTimer.current) clearInterval(chatTimer.current);
    if (typingDebounce.current) clearTimeout(typingDebounce.current);
    if (typingClear.current) clearTimeout(typingClear.current);
  }, []);

  // Auto-scroll ke bawah saat pesan baru (parity scrollToBottom ChatDialog).
  useEffect(() => {
    const el = chatListRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [chatMsgs]);

  const sendChat = () => {
    const text = chatInput.trim();
    const attIds = pendingAttachments.map((a) => a.id);
    if ((!text && !attIds.length) || !chatWith) return;
    const replyId = replyTarget?.id || null;
    setChatInput('');
    const tmpAtts = pendingAttachments;
    setChatMsgs((prev) => [...prev, {
      id: `tmp-${Date.now()}`, text, isSelf: true, senderId: String(user.id ?? ''),
      createdAt: (clockNow() ?? new Date()).toISOString(), replyToId: replyId,
      reactions: {}, attachments: tmpAtts, syncStatus: 'pending',
    }]);
    setReplyTarget(null);
    setPendingAttachments([]);
    setFriendTyping(false);
    studio.sendFriendChat(chatWith.id, text, replyId, attIds)
      .then(() => fetchChat(chatWith))
      .catch((e) => showToast('info', String(e?.message || e), ''));
  };

  const doClearChat = () => {
    if (!chatWith) return;
    if (!window.confirm(tr('chat_clear_confirm_self'))) return;
    studio.clearFriendChat(chatWith.id)
      .then((r) => {
        const m = r?.result || r;
        if (m?.ok === false && m?.msg) showToast('info', tr(m.msg), '');
        fetchChat(chatWith);
      })
      .catch(() => undefined);
  };

  const doDeleteMsg = () => {
    if (!selectedMsg?.id || String(selectedMsg.id).startsWith('tmp-')) return;
    if (selectedMsg.syncStatus === 'pending') {
      showToast('info', tr('chat_pending_action_blocked'), '');
      return;
    }
    if (!window.confirm(tr('chat_delete_confirm'))) return;
    studio.deleteFriendMessage(selectedMsg.id, chatCloudMode)
      .then(() => { setSelectedMsg(null); fetchChat(chatWith); })
      .catch(() => undefined);
  };

  const doReact = (emoji: string | null) => {
    if (!selectedMsg?.id || String(selectedMsg.id).startsWith('tmp-')) return;
    if (selectedMsg.syncStatus === 'pending') {
      showToast('info', tr('chat_pending_action_blocked'), '');
      return;
    }
    studio.reactFriendMessage(selectedMsg.id, emoji, chatCloudMode)
      .then(() => { setSelectedMsg(null); fetchChat(chatWith); })
      .catch(() => undefined);
  };

  const doSaveEdit = () => {
    if (!editingMsg || !editText.trim()) return;
    if (editingMsg.syncStatus === 'pending') {
      showToast('info', tr('chat_pending_action_blocked'), '');
      return;
    }
    studio.editFriendMessage(editingMsg.id, editText.trim(), chatCloudMode)
      .then(() => { setEditingMsg(null); fetchChat(chatWith); })
      .catch((e) => showToast('info', String(e?.message || e), ''));
  };

  const doDownloadAttachment = (att: any) => {
    if (!att?.id) return;
    apiGetBlob(`/api/friends/attachments/${att.id}/download`, att.originalFilename || 'attachment')
      .then(({ blob, name }) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 1500);
        showToast('success', tr('chat_attachment_saved'), '');
      })
      .catch(() => showToast('info', tr('chat_attachment_not_cached'), ''));
  };

  const onPickFiles = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    e.target.value = '';
    if (!files.length) return;
    const remaining = 5 - pendingAttachments.length;
    if (remaining <= 0) { showToast('info', tr('chat_attachment_max'), ''); return; }
    for (const file of files.slice(0, remaining)) {
      try {
        const r = await studio.friendChatAttachment(file);
        const att = r?.result?.attachment || r?.attachment;
        if (att) setPendingAttachments((prev) => [...prev, att]);
      } catch (err) {
        showToast('info', String((err as any)?.message || err), '');
      }
    }
  };

  const onChatInputChange = (v: string) => {
    setChatInput(v);
    if (!chatCloudMode || !chatWith) return;
    if (typingDebounce.current) clearTimeout(typingDebounce.current);
    if (typingClear.current) clearTimeout(typingClear.current);
    typingDebounce.current = setTimeout(() => {
      studio.friendTyping(chatWith.id, !!v.trim()).catch(() => undefined);
    }, 500);
    typingClear.current = setTimeout(() => {
      studio.friendTyping(chatWith.id, false).catch(() => undefined);
    }, 4500);
  };

  const reactionText = (reactions: Record<string, string> | undefined) => {
    const counts: Record<string, number> = {};
    for (const r of Object.values(reactions || {})) counts[r] = (counts[r] || 0) + 1;
    return Object.entries(counts).map(([e, c]) => `${e} ${c}`).join('  ');
  };

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-4xl mx-auto space-y-4 animate-fade-in-up">
      <header>
        <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">{tr('page_friends_subtitle')}</p>
        <h2 className="text-2xl font-black text-slate-100">{tr('page_friends_title')}</h2>
      </header>

      {/* Form tambah teman (parity add_form) */}
      <div className="flex gap-2">
        <input value={friendName} onChange={(e) => setFriendName(e.target.value)}
          placeholder={tr('friends_add_placeholder')}
          className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
        <button type="button"
          onClick={() => {
            const uname = friendName.trim();
            if (!uname) { showToast('info', tr('msg_error'), tr('msg_enter_username')); return; }
            sendFriendRequest(uname);
            setFriendName('');
            setTick((x) => x + 1);
          }}
          className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
          {tr('friends_add_btn')}
        </button>
      </div>

      {/* Daftar permintaan masuk (parity pending_group) */}
      {(friendRequests || []).length > 0 && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
          <h3 className="text-sm font-black text-slate-100">{tr('friends_pending')}</h3>
          {friendRequests.map((req: any) => (
            <div key={req.id} className="flex items-center gap-2 text-xs">
              <span className="text-2xl">⚔️</span>
              <span className="flex-1">
                <b className="text-slate-100">{req.name || req.displayName}</b>
                <span className="text-slate-500 block">@{req.username}</span>
              </span>
              <button type="button" onClick={() => acceptFriendRequest(req.id)}
                className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold">{tr('guild_accept')}</button>
              <button type="button" onClick={() => rejectFriendRequest(req.id)}
                className="px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-200 font-bold">{tr('guild_reject')}</button>
            </div>
          ))}
        </section>
      )}

      {/* Couple requests (parity couple_requests_group) */}
      {coupleRequests.length > 0 && (
        <section className="rounded-2xl border border-pink-800/40 bg-slate-900/70 p-4 space-y-2">
          <h3 className="text-sm font-black text-pink-300">{tr('couple_requests_title')}</h3>
          {coupleRequests.map((req) => (
            <div key={req.id} className="flex items-center justify-between text-xs">
              <span className="text-slate-200"><b>{req.name}</b></span>
              {req.direction === 'incoming' ? (
                <span className="flex gap-1.5">
                  <button type="button" onClick={() => void post(studio.coupleRespond(req.id, true))}
                    className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold">{tr('couple_accept')}</button>
                  <button type="button" onClick={() => void post(studio.coupleRespond(req.id, false))}
                    className="px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-200 font-bold">{tr('couple_reject')}</button>
                </span>
              ) : (
                <button type="button" onClick={() => void post(studio.coupleCancel(req.id))}
                  className="px-3 py-1.5 rounded-lg bg-slate-700 text-slate-200 font-bold">{tr('couple_cancel')}</button>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Daftar teman (parity friends_group) */}
      {(friends || []).length > 0 && (
        <section className="space-y-2">
          <h3 className="text-sm font-black text-slate-100">{tr('friends_list')}</h3>
          {friends.map((f: any) => {
            const status = f.coupleStatus || 'friend';
            const statusText = status === 'accepted' ? tr('couple_status_couple')
              : status === 'pending' ? tr('couple_status_pending') : tr('couple_status_friend');
            const presenceText = f.presence === 'online' ? tr('presence_online') : tr('presence_offline');
            return (
              <div key={f.id} className="flex items-center gap-2.5 rounded-2xl border border-slate-800 bg-slate-900/70 px-3 py-2.5">
                <span className="text-3xl">{f.avatarEmoji || '⚔️'}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-slate-100 truncate">{f.displayName || f.name}</div>
                  <div className="text-[10px] text-slate-500">
                    {tr('level_abbr', { level: f.level || 1 })} · {statusText} · {presenceText}
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-1.5">
                  {status === 'friend' && (
                    <button type="button" onClick={() => void post(studio.coupleRequest(f.id))}
                      className="px-2 py-1 rounded-lg bg-pink-700/50 hover:bg-pink-700/80 text-pink-100 text-[11px] font-bold">{tr('couple_connect')}</button>
                  )}
                  {status === 'accepted' && (
                    <button type="button" onClick={() => { if (window.confirm(tr('couple_end_confirm'))) void post(studio.endCouple()); }}
                      className="px-2 py-1 rounded-lg bg-rose-900/60 text-rose-200 text-[11px] font-bold">{tr('couple_end')}</button>
                  )}
                  <button type="button" title={tr('pvp_btn')} onClick={() => sendPvpChallenge(f.id)}
                    className="px-2 py-1 rounded-lg bg-amber-600/40 hover:bg-amber-600/70 text-amber-200 text-[11px] font-bold">⚔️</button>
                  <button type="button" onClick={() => openChat(f)}
                    className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold">
                    {f.unreadCount ? tr('friends_chat_unread', { count: f.unreadCount }) : tr('friends_chat_btn')}
                  </button>
                  <button type="button" onClick={() => studio.friendProfile(f.id).then((d) => setProfile(d?.profile || null)).catch(() => undefined)}
                    className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-bold">{tr('friends_profile_short')}</button>
                  <button type="button" onClick={() => { if (window.confirm(tr('friends_remove_btn'))) void post(studio.removeFriend(f.id)); }}
                    className="px-2 py-1 rounded-lg bg-rose-900/40 hover:bg-rose-900/70 text-rose-300 text-[11px] font-bold">{tr('friends_remove_btn')}</button>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* ⚔️ PvP section (parity pvp_group, lokal) */}
      <section className="space-y-2">
        <h3 className="text-sm font-black text-slate-100">{tr('pvp_section')}</h3>
        {(() => {
          const items = (pvpChallenges || []).filter((c: any) => (c.rawStatus || c.status) !== 'declined').slice(0, 6);
          if (!items.length) return <p className="text-xs text-slate-500">{tr('pvp_none')}</p>;
          return items.map((it: any) => {
            const raw = it.rawStatus || it.status;
            return (
              <div key={it.id} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-3 text-xs space-y-1.5">
                {raw === 'pending' && !it.isChallenger ? (
                  <>
                    <div className="font-bold text-slate-100">⚔️ {it.opponentName}</div>
                    <div className="flex gap-1.5">
                      <button type="button" onClick={() => respondPvpChallenge(it.id, true)}
                        className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold">{tr('pvp_accept')}</button>
                      <button type="button" onClick={() => respondPvpChallenge(it.id, false)}
                        className="px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-200 font-bold">{tr('pvp_decline')}</button>
                    </div>
                  </>
                ) : raw === 'pending' ? (
                  <div className="text-slate-400">{tr('pvp_pending_out', { name: it.opponentName })}</div>
                ) : raw === 'active' ? (
                  <div className="text-slate-300">
                    {tr('pvp_score_line', {
                      me: myName, opp: it.opponentName,
                      ms: it.playerScore, os: it.opponentScore, days: it.daysLeft ?? 0,
                    })}
                  </div>
                ) : raw === 'finished' || raw === 'completed' ? (
                  <>
                    <div className="text-slate-300">
                      {tr(
                        it.winnerId == null ? 'pvp_finished_tie'
                          : String(it.winnerId) === String(user.id ?? '') ? 'pvp_finished_win'
                          : 'pvp_finished_lose',
                        { name: it.opponentName, ms: it.playerScore, os: it.opponentScore },
                      )}
                    </div>
                    {it.status === 'completed' && (
                      <button type="button" onClick={() => claimPvPReward(it.id)}
                        className="px-3 py-1.5 rounded-lg bg-amber-500 text-slate-950 font-black">
                        {tr('claim')}
                      </button>
                    )}
                  </>
                ) : null}
              </div>
            );
          });
        })()}
      </section>

      {/* ── ChatDialog parity (select → aksi bar, reply label, reactions, attachments) ── */}
      {chatWith && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-slate-100">💬 {chatWith.displayName || chatWith.name}</h3>
              <div className="flex items-center gap-2">
                <button type="button" onClick={doClearChat} title={tr('chat_clear_self')}
                  className="text-slate-400 hover:text-rose-300 text-xs">🧹</button>
                <button type="button" onClick={closeChat} className="text-slate-400 text-lg leading-none">×</button>
              </div>
            </div>
            {/* typing indicator (parity typing_label, cloud only) */}
            {friendTyping && (
              <div className="text-[10px] italic text-slate-400">✍️ {tr('cloud_chat_typing')}</div>
            )}
            {/* earlier (parity _load_earlier: +50/page) */}
            <div className="text-center">
              <button type="button" onClick={() => { const nl = chatLimit + 50; setChatLimit(nl); fetchChat(chatWith, nl); }}
                className="text-[11px] text-sky-400 hover:text-sky-300">
                {tr('chat_load_earlier')}
              </button>
            </div>
            <div ref={chatListRef} className="h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
              {chatMsgs.map((m) => {
                const deleted = !!m.deletedAt;
                const body = deleted ? tr('chat_message_deleted') : m.text;
                const flagEdited = m.editedAt && !deleted;
                const flagPending = m.syncStatus === 'pending' && !deleted;
                const replyTo = m.replyToId ? chatMsgs.find((x) => String(x.id) === String(m.replyToId)) : null;
                const replyBody = m.replyToId
                  ? (replyTo ? (replyTo.deletedAt ? tr('chat_message_deleted') : (replyTo.text || '')) : tr('chat_reply_unavailable'))
                  : '';
                return (
                  <div key={m.id}
                    onClick={() => setSelectedMsg(selectedMsg?.id === m.id ? null : m)}
                    className={`text-xs cursor-pointer rounded-lg px-1.5 py-1 ${m.isSelf ? 'text-right' : ''} ${selectedMsg?.id === m.id ? 'bg-slate-800/80' : ''}`}>
                    <div className="text-[9px] text-slate-500">
                      {m.isSelf ? tr('chat_you') : tr('chat_friend')}
                      {' · '}{fmtChatTime(m.createdAt, m.epoch)}
                      {flagEdited ? ` · ${tr('chat_edited')}` : ''}
                      {flagPending ? ` · ${tr('chat_pending')}` : ''}
                    </div>
                    {m.replyToId ? (
                      <div className="text-[10px] text-slate-500 italic">↪ {replyBody.slice(0, 90)}</div>
                    ) : null}
                    <div className={deleted ? 'text-slate-600 italic' : m.isSelf ? 'text-amber-200' : 'text-slate-300'}>{body}</div>
                    {(m.attachments || []).length > 0 && !deleted && (
                      <div className="mt-1 space-y-1">
                        {(m.attachments || []).map((a: any) => (
                          <div key={a.id} className={m.isSelf ? 'text-right' : ''}>
                            {a.thumbnailData ? (
                              <img
                                src={`data:${a.mimeType || 'image/webp'};base64,${a.thumbnailData}`}
                                alt={a.originalFilename || ''}
                                className="inline-block w-24 h-24 object-cover rounded-lg border border-slate-700"
                              />
                            ) : null}
                            <div className="text-[9px] text-slate-400">📎 {a.originalFilename} ({(Number(a.sizeBytes || 0) / 1024).toFixed(1)} KB)</div>
                          </div>
                        ))}
                      </div>
                    )}
                    {!!reactionText(m.reactions) && (
                      <div className="text-[10px] text-slate-400">{reactionText(m.reactions)}</div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Action bar (parity actions: reply/edit/delete/react/remove/download) */}
            {selectedMsg && !selectedMsg.deletedAt && (
              <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-800 bg-slate-950 p-2">
                <button type="button" onClick={() => { setReplyTarget(selectedMsg); setSelectedMsg(selectedMsg); }}
                  className="px-2 py-1 rounded-lg bg-sky-700/50 text-sky-200 text-[11px] font-bold">{tr('chat_reply')}</button>
                {selectedMsg.isSelf && (
                  <>
                    <button type="button" onClick={() => { setEditingMsg(selectedMsg); setEditText(selectedMsg.text || ''); }}
                      className="px-2 py-1 rounded-lg bg-slate-700 text-slate-100 text-[11px] font-bold">{tr('chat_edit')}</button>
                    <button type="button" onClick={doDeleteMsg}
                      className="px-2 py-1 rounded-lg bg-rose-900/60 text-rose-200 text-[11px] font-bold">{tr('chat_delete_message')}</button>
                  </>
                )}
                {(selectedMsg.attachments || []).map((a: any) => (
                  <button key={a.id} type="button" onClick={() => doDownloadAttachment(a)}
                    title={tr('chat_download_attachment')}
                    className="px-2 py-1 rounded-lg bg-slate-700 text-slate-100 text-[11px] font-bold">📎</button>
                ))}
                <div className="flex gap-0.5">
                  {REACTIONS.map((e) => (
                    <button key={e} type="button" onClick={() => doReact(e)}
                      className="px-1.5 py-1 rounded-lg hover:bg-slate-800 text-sm">{e}</button>
                  ))}
                  <button type="button" onClick={() => doReact(null)} title={tr('chat_remove_reaction')}
                    className="px-1.5 py-1 rounded-lg bg-slate-800 text-slate-400 text-[10px]">{tr('chat_remove_reaction')}</button>
                </div>
              </div>
            )}

            {/* Reply label (parity reply_label) */}
            {replyTarget && (
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[10px] text-slate-400">
                <span className="truncate">{tr('chat_replying_to', { message: (replyTarget.text || '').slice(0, 120) })}</span>
                <button type="button" onClick={() => setReplyTarget(null)} className="text-slate-500">×</button>
              </div>
            )}

            {/* Edit prompt (parity chat_edit / chat_edit_prompt) */}
            {editingMsg && (
              <div className="flex gap-1.5 items-center rounded-lg border border-slate-800 bg-slate-950 p-2">
                <input value={editText} onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') doSaveEdit(); }}
                  placeholder={tr('chat_edit_prompt')}
                  className="flex-1 px-2 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-100" />
                <button type="button" onClick={doSaveEdit}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold">✓</button>
                <button type="button" onClick={() => setEditingMsg(null)}
                  className="px-2 py-1.5 rounded-lg bg-slate-800 text-slate-400 text-xs">×</button>
              </div>
            )}

            {/* Pending attachments (parity attachment_label) */}
            {pendingAttachments.length > 0 && (
              <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-950 px-2.5 py-1.5 text-[10px] text-slate-400">
                <span className="truncate">{tr('chat_attachments_ready', { files: pendingAttachments.map((a) => a.originalFilename).join(', ') })}</span>
                <button type="button" onClick={discardPending} className="text-slate-500">×</button>
              </div>
            )}

            <input ref={fileRef} type="file" multiple accept=".jpg,.jpeg,.png,.webp,.pdf,.txt,.docx,.xlsx,.pptx"
              onChange={onPickFiles} className="hidden" />
            <div className="flex gap-2">
              <button type="button" title={tr('chat_choose_attachment')}
                onClick={() => fileRef.current?.click()}
                className="px-3 py-2 rounded-xl bg-slate-800 text-slate-200 text-sm">📎</button>
              <input value={chatInput} onChange={(e) => onChatInputChange(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendChat(); }}
                placeholder={tr('chat_input_placeholder')}
                className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100" />
              <button type="button" onClick={sendChat} className="px-3 py-2 rounded-xl bg-sky-600 text-white">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── FriendProfileDialog parity (PyQt MainPyQt6.py:12726) ── */}
      {profile && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-slate-100">{tr('friend_profile_title')}</h3>
              <button type="button" onClick={() => setProfile(null)} className="text-slate-400 text-lg leading-none">×</button>
            </div>

            {/* Header: avatar + identitas */}
            <div className="flex flex-col items-center gap-1">
              <div className="w-24 h-24 rounded-full bg-slate-800 border-2 border-slate-600 flex items-center justify-center text-5xl overflow-hidden">
                {profile.avatarEmoji ? <span className="text-5xl">{profile.avatarEmoji}</span> :
                  <span className="text-4xl text-slate-400">⚔️</span>}
              </div>
              <div className="text-base font-bold text-slate-100 text-center">{profile.displayName}</div>
              <div className="text-xs text-slate-500 text-center">@{profile.username}</div>
              {(profile.relation === 'accepted' || profile.relation === 'pending') && (
                <div className="text-[10px] px-2 py-0.5 rounded-full border"
                  style={{ color: '#4dd9e0', borderColor: 'rgba(77,217,224,.4)' }}>
                  {tr(profile.relation === 'accepted' ? 'couple_status_couple' : 'couple_status_pending')}
                </div>
              )}
            </div>

            {/* Chips: level + kelas + title */}
            <div className="flex items-center justify-center gap-2 flex-wrap">
              <span className="text-xs font-bold px-2.5 py-[3px] rounded-[10px] border"
                style={{ color: '#f0c040', borderColor: 'rgba(240,192,64,.4)', background: 'rgba(240,192,64,.08)' }}>
                ⚔️ Lv {profile.level ?? 1}
              </span>
              {profile.avatarClass && (
                <span className="text-xs px-2.5 py-[3px] rounded-[10px] border"
                  style={{ color: '#e2e8f0', borderColor: 'rgba(148,163,184,.3)', background: 'rgba(148,163,184,.08)' }}>
                  🎭 {tr(`class_${profile.avatarClass}_name`)}
                </span>
              )}
              {profile.title && (
                <span className="text-xs font-bold px-2.5 py-[3px] rounded-[10px] border"
                  style={{ color: '#4dd9e0', borderColor: 'rgba(77,217,224,.35)', background: 'rgba(77,217,224,.08)' }}>
                  🏅 {profile.title}
                </span>
              )}
            </div>

            {/* Info ringkas: bio, guild, sport/rebirth/join */}
            <div className="rounded-xl bg-slate-800/50 border border-slate-700 px-3 py-2 space-y-1">
              {profile.bio && (
                <p className="text-xs italic text-slate-500">💬 {profile.bio}</p>
              )}
              {profile.guildName && (
                <p className="text-xs text-slate-300">{tr('friend_guild', { name: profile.guildName })}</p>
              )}
              {(() => {
                const mini: string[] = [];
                mini.push(tr('friend_sport_level', { lvl: profile.sportLevel ?? 0 }));
                mini.push(tr('friend_rebirth', { count: profile.rebirthCount ?? 0 }));
                if (profile.joinDate) mini.push(tr('friend_joined', { date: String(profile.joinDate).slice(0, 10) }));
                return <p className="text-[11px] text-slate-500">{mini.join('   ·   ')}</p>;
              })()}
            </div>

            {/* Progres XP */}
            <div className="space-y-1">
              <div className="text-[11px] text-slate-500">{tr('friend_xp_progress')}</div>
              <div className="h-[18px] rounded-full bg-slate-800 overflow-hidden border border-slate-700">
                <div className="h-full bg-gradient-to-r from-amber-600/80 to-amber-500/80 transition-all"
                  style={{ width: `${Math.min(100, ((profile.xp ?? 0) / Math.max(1, profile.xpNeeded ?? 1)) * 100)}%` }} />
              </div>
              <div className="text-[11px] text-slate-400">
                {profile.xp ?? 0}/{profile.xpNeeded ?? 1} XP ({tr('friend_total_xp')}: {Math.round(profile.totalXp ?? 0)})
              </div>
            </div>

            {/* Progres achievement */}
            <div className="space-y-1">
              <div className="text-[11px] text-slate-500">{tr('friend_achievements_progress', { done: profile.achievementsDone ?? 0, total: profile.achievementsTotal ?? 0 })}</div>
              <div className="h-[18px] rounded-full bg-slate-800 overflow-hidden border border-slate-700">
                <div className="h-full bg-gradient-to-r from-purple-600/80 to-purple-500/80 transition-all"
                  style={{ width: `${Math.min(100, ((profile.achievementsDone ?? 0) / Math.max(1, profile.achievementsTotal ?? 1)) * 100)}%` }} />
              </div>
              <div className="text-[11px] text-slate-400">{profile.achievementsDone ?? 0}/{profile.achievementsTotal ?? 0}</div>
            </div>

            {/* 6 achievement terbaru (2 kolom) */}
            {Array.isArray(profile.latestAchievements) && profile.latestAchievements.length > 0 && (
              <div className="space-y-1">
                <div className="text-[11px] text-slate-500">{tr('friend_latest_achievements')}</div>
                <div className="grid grid-cols-2 gap-1.5">
                  {profile.latestAchievements.map((ach: any, i: number) => (
                    <div key={i} className="rounded-lg bg-slate-800/60 border border-slate-700 px-2 py-1 flex items-center gap-1.5 min-h-0">
                      <span className="text-base shrink-0">{ach.icon || '🏆'}</span>
                      <span className="text-[11px] text-slate-300 leading-tight">{ach.name || ach.category || ''}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Statistik detail (2 kolom, 8 sel) */}
            <div className="space-y-1">
              <div className="text-[11px] text-slate-500">{tr('friend_stats_title')}</div>
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  [tr('stats_habit_today'), `${profile.stats?.habits_done_today ?? 0}/${profile.stats?.habits_total ?? 0}`],
                  [tr('stats_daily_today'), `${profile.stats?.dailies_done_today ?? 0}/${profile.stats?.dailies_total ?? 0}`],
                  [tr('stats_quest_done'), `${profile.stats?.todos_done ?? 0}/${profile.stats?.todos_total ?? 0}`],
                  [tr('friend_tasks_done'), String(profile.tasksDone ?? 0)],
                  [tr('stats_max_streak'), String(profile.stats?.max_streak ?? 0)],
                  [tr('stats_boss_killed'), String(profile.stats?.bosses_killed ?? 0)],
                  [tr('stats_pets'), String(profile.stats?.pet_count ?? 0)],
                  [tr('friend_pomodoro'), `${profile.pomodoroMinutes ?? 0} min`],
                ].map(([label, value], i) => (
                  <div key={i} className="rounded-lg bg-slate-800/60 border border-slate-700 px-2.5 py-1.5 flex flex-col gap-0.5">
                    <div className="text-sm font-bold text-slate-200">{value}</div>
                    <div className="text-[10px] text-slate-500 leading-tight">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
