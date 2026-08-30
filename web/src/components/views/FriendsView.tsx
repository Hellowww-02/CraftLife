import React, { useEffect, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { studio } from '../../api/studio';
import { t } from '../../i18n';
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
    refreshSocial, lang, showToast, applyLive,
  } = useGame();

  const [friendName, setFriendName] = useState('');
  const [coupleRequests, setCoupleRequests] = useState<{ id: string; name: string; direction: string }[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [chatWith, setChatWith] = useState<any | null>(null);
  const [chatMsgs, setChatMsgs] = useState<any[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLimit, setChatLimit] = useState(100);
  const [selectedMsg, setSelectedMsg] = useState<any | null>(null);
  const [replyTarget, setReplyTarget] = useState<any | null>(null);
  const [editingMsg, setEditingMsg] = useState<any | null>(null);
  const [editText, setEditText] = useState('');
  const [tick, setTick] = useState(0);
  const chatTimer = useRef<ReturnType<typeof setInterval> | null>(null);

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
        reload();
      })
      .catch(() => setChatMsgs([]));
  };
  const openChat = (f: any) => {
    setChatWith(f);
    setChatLimit(100);
    setSelectedMsg(null);
    setReplyTarget(null);
    setEditingMsg(null);
    fetchChat(f);
    // PyQt: QTimer 3 detik refresh pesan saat dialog aktif.
    if (chatTimer.current) clearInterval(chatTimer.current);
    chatTimer.current = setInterval(() => fetchChat(f), 3000);
  };
  const closeChat = () => {
    if (chatTimer.current) { clearInterval(chatTimer.current); chatTimer.current = null; }
    setChatWith(null);
  };
  useEffect(() => () => { if (chatTimer.current) clearInterval(chatTimer.current); }, []);

  const sendChat = () => {
    const text = chatInput.trim();
    if (!text || !chatWith) return;
    const replyId = replyTarget?.id || null;
    setChatInput('');
    setChatMsgs((prev) => [...prev, {
      id: `tmp-${Date.now()}`, text, isSelf: true, senderId: String(user.id ?? ''),
      createdAt: new Date().toISOString(), replyToId: replyId, reactions: {},
    }]);
    setReplyTarget(null);
    studio.sendFriendChat(chatWith.id, text, replyId)
      .then(() => fetchChat(chatWith))
      .catch((e) => showToast('info', String(e?.message || e), ''));
  };

  const doClearChat = () => {
    if (!chatWith) return;
    if (!window.confirm(tr('chat_clear_confirm_self'))) return;
    studio.clearFriendChat(chatWith.id).then(() => fetchChat(chatWith)).catch(() => undefined);
  };

  const doDeleteMsg = () => {
    if (!selectedMsg?.id || String(selectedMsg.id).startsWith('tmp-')) return;
    if (!window.confirm(tr('chat_delete_confirm'))) return;
    studio.deleteFriendMessage(selectedMsg.id)
      .then(() => { setSelectedMsg(null); fetchChat(chatWith); })
      .catch(() => undefined);
  };

  const doReact = (emoji: string | null) => {
    if (!selectedMsg?.id || String(selectedMsg.id).startsWith('tmp-')) return;
    studio.reactFriendMessage(selectedMsg.id, emoji)
      .then(() => { setSelectedMsg(null); fetchChat(chatWith); })
      .catch(() => undefined);
  };

  const doSaveEdit = () => {
    if (!editingMsg || !editText.trim()) return;
    studio.editFriendMessage(editingMsg.id, editText.trim())
      .then(() => { setEditingMsg(null); fetchChat(chatWith); })
      .catch((e) => showToast('info', String(e?.message || e), ''));
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
                        {lang === 'id' ? 'Klaim' : 'Claim'}
                      </button>
                    )}
                  </>
                ) : null}
              </div>
            );
          });
        })()}
      </section>

      {/* ── ChatDialog parity (select → aksi bar, reply label, reactions) ── */}
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
            {/* earlier (parity _load_earlier) */}
            <div className="text-center">
              <button type="button" onClick={() => { const nl = chatLimit + 100; setChatLimit(nl); fetchChat(chatWith, nl); }}
                className="text-[11px] text-sky-400 hover:text-sky-300">
                {lang === 'id' ? 'Muat pesan lebih lama' : 'Load earlier messages'}
              </button>
            </div>
            <div className="h-64 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
              {chatMsgs.map((m) => {
                const deleted = !!m.deletedAt;
                const body = deleted ? tr('chat_message_deleted') : m.text;
                const flagEdited = m.editedAt && !deleted;
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
                      {' · '}{(m.createdAt || '').slice(11, 16)}
                      {flagEdited ? ` · ${tr('chat_edited')}` : ''}
                    </div>
                    {m.replyToId ? (
                      <div className="text-[10px] text-slate-500 italic">↪ {replyBody.slice(0, 90)}</div>
                    ) : null}
                    <div className={deleted ? 'text-slate-600 italic' : m.isSelf ? 'text-amber-200' : 'text-slate-300'}>{body}</div>
                    {!!reactionText(m.reactions) && (
                      <div className="text-[10px] text-slate-400">{reactionText(m.reactions)}</div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Action bar (parity actions: reply/edit/delete/react/remove) */}
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

            <div className="flex gap-2">
              <input value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') sendChat(); }}
                className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100" />
              <button type="button" onClick={sendChat} className="px-3 py-2 rounded-xl bg-sky-600 text-white">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── FriendProfileDialog parity ── */}
      {profile && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-slate-100">{profile.displayName} <span className="text-slate-500">@{profile.username}</span></h3>
              <button type="button" onClick={() => setProfile(null)} className="text-slate-400 text-lg leading-none">×</button>
            </div>
            <div className="text-xs text-slate-300 space-y-1">
              <p>{tr('level_abbr', { level: profile.level ?? 1 })} · {profile.avatarClass} · {profile.title || ''}</p>
              <p className="text-slate-500">{profile.bio || ''}</p>
              <p>XP: {profile.xp}/{profile.xpNeeded} · Total XP: {profile.totalXp}</p>
              <p>{lang === 'id' ? 'Prestasi' : 'Achievements'}: {profile.achievementsDone}/{profile.achievementsTotal}</p>
              <p>{lang === 'id' ? 'Guild' : 'Guild'}: {profile.guildName || '—'}</p>
              <p>{lang === 'id' ? 'Bergabung' : 'Joined'}: {(profile.joinDate || '').slice(0, 10)}</p>
              <p>{lang === 'id' ? 'Tugas selesai' : 'Tasks done'}: {profile.tasksDone} · 🍅 {profile.pomodoroMinutes}m</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
