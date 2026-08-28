import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { studio } from '../../api/studio';
import { t } from '../../i18n';
import { Flame, Send, Users } from 'lucide-react';

/** Mirror FriendsPage — PvP + chat + permintaan, terpisah dari GuildPage. */
export const FriendsView: React.FC = () => {
  const {
    friends,
    chatMessages,
    sendChatMessage,
    pvpChallenges,
    claimPvPReward,
    sendFriendRequest,
    sendPvpChallenge,
    friendRequests,
    acceptFriendRequest,
    rejectFriendRequest,
    respondPvpChallenge,
    refreshSocial,
    lang,
  } = useGame();

  const [tab, setTab] = useState<'friends' | 'pvp' | 'chat'>('friends');
  const [friendName, setFriendName] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [chatFriendId, setChatFriendId] = useState('');
  const [coupleRequests, setCoupleRequests] = useState<{ id: string; name: string; direction: string }[]>([]);
  const [profile, setProfile] = useState<any>(null);

  useEffect(() => {
    refreshSocial();
    studio.friends().then((d) => {
      if (Array.isArray(d?.coupleRequests)) setCoupleRequests(d.coupleRequests);
    }).catch(() => undefined);
  }, [refreshSocial]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-black text-slate-100 flex items-center gap-2">
          <Users className="w-6 h-6 text-sky-400" />
          {lang === 'id' ? 'Teman & PvP' : 'Friends & PvP'}
        </h2>
        <div className="flex gap-1 bg-slate-900 p-1 rounded-xl text-xs">
          {(['friends', 'pvp', 'chat'] as const).map((k) => (
            <button key={k} type="button" onClick={() => setTab(k)} className={`px-3 py-1.5 rounded-lg font-bold ${tab === k ? 'bg-sky-600 text-white' : 'text-slate-400'}`}>
              {k}
            </button>
          ))}
        </div>
      </div>

      {tab === 'friends' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input value={friendName} onChange={(e) => setFriendName(e.target.value)} placeholder={t('cloud_friend_username', 'username')} className="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs" />
            <button
              type="button"
              onClick={() => {
                if (friendName.trim()) {
                  sendFriendRequest(friendName.trim());
                  setFriendName('');
                }
              }}
              className="px-3 py-2 rounded-xl bg-sky-600 text-white text-xs font-black"
            >
              {lang === 'id' ? 'Kirim permintaan' : 'Send request'}
            </button>
          </div>
          {coupleRequests.map((req) => (
            <div key={req.id} className="flex items-center justify-between text-xs bg-slate-900 border border-pink-800/40 rounded-xl p-3">
              <span>{req.name} · {req.direction}</span>
              <div className="flex gap-1">
                {req.direction === 'incoming' ? (
                  <>
                    <button type="button" onClick={() => studio.coupleRespond(req.id, true).then(() => refreshSocial())} className="px-2 py-1 rounded-lg bg-emerald-600 text-white font-bold">
                      {lang === 'id' ? 'Terima couple' : 'Accept couple'}
                    </button>
                    <button type="button" onClick={() => studio.coupleRespond(req.id, false).then(() => refreshSocial())} className="px-2 py-1 rounded-lg bg-slate-700">
                      {lang === 'id' ? 'Tolak' : 'Reject'}
                    </button>
                  </>
                ) : (
                  <button type="button" onClick={() => studio.coupleCancel(req.id).then(() => refreshSocial())} className="px-2 py-1 rounded-lg bg-slate-700">
                    {lang === 'id' ? 'Batal' : 'Cancel'}
                  </button>
                )}
              </div>
            </div>
          ))}
          {(friendRequests || []).map((req) => (
            <div key={req.id} className="flex items-center justify-between text-xs bg-slate-900 border border-slate-800 rounded-xl p-3">
              <span>{req.name || req.username}</span>
              <div className="flex gap-1">
                <button type="button" onClick={() => acceptFriendRequest(req.id)} className="px-2 py-1 rounded-lg bg-emerald-600 text-white font-bold">
                  {lang === 'id' ? 'Terima' : 'Accept'}
                </button>
                <button type="button" onClick={() => rejectFriendRequest(req.id)} className="px-2 py-1 rounded-lg bg-slate-700">
                  {lang === 'id' ? 'Tolak' : 'Reject'}
                </button>
              </div>
            </div>
          ))}
          <div className="grid sm:grid-cols-2 gap-3">
            {friends.map((f) => (
              <div key={f.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="font-bold text-sm">{f.displayName || f.name} · Lv {f.level}</div>
                <div className="text-[11px] text-amber-400 flex items-center gap-1">
                  <Flame className="w-3 h-3" /> {f.streak || 0}
                </div>
                <button type="button" onClick={() => studio.friendProfile(f.id).then((d) => setProfile(d?.profile || null))} className="text-xs px-2 py-1 rounded-lg bg-slate-800 font-bold">
                  {lang === 'id' ? 'Profil' : 'Profile'}
                </button>
                <button type="button" onClick={() => sendPvpChallenge(f.id)} className="text-xs px-2 py-1 rounded-lg bg-amber-600 text-white font-bold">
                  {lang === 'id' ? 'Tantang PvP' : 'Challenge PvP'}
                </button>
                <button type="button" onClick={() => studio.coupleRequest(f.id).then(() => refreshSocial())} className="text-xs px-2 py-1 rounded-lg bg-pink-600 text-white font-bold">
                  Couple
                </button>
                <button type="button" onClick={() => { if (window.confirm(lang === 'id' ? 'Akhiri couple?' : 'End couple?')) studio.endCouple().then(() => refreshSocial()); }} className="text-xs px-2 py-1 rounded-lg bg-rose-900 text-rose-100 font-bold">
                  {lang === 'id' ? 'Akhiri' : 'End'}
                </button>
                <button type="button" onClick={() => { if (window.confirm(lang === 'id' ? 'Hapus teman?' : 'Remove friend?')) studio.removeFriend(f.id).then(() => refreshSocial()); }} className="text-xs px-2 py-1 rounded-lg bg-slate-800 text-rose-300 font-bold">
                  {lang === 'id' ? 'Hapus' : 'Remove'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'pvp' && (
        <div className="grid md:grid-cols-2 gap-3">
          {pvpChallenges.map((chal) => (
            <div key={chal.id} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="flex justify-between text-sm font-bold">
                <span>{chal.opponentName}</span>
                <span className="text-amber-300">{chal.status}</span>
              </div>
              <p className="text-xs text-slate-400">
                +{chal.rewardXp} XP · +{chal.rewardGold}g
              </p>
              {chal.status === 'pending' && (
                <div className="flex gap-2">
                  <button type="button" onClick={() => respondPvpChallenge(chal.id, true)} className="px-2 py-1 text-xs rounded-lg bg-emerald-600 text-white font-bold">
                    {lang === 'id' ? 'Terima' : 'Accept'}
                  </button>
                  <button type="button" onClick={() => respondPvpChallenge(chal.id, false)} className="px-2 py-1 text-xs rounded-lg bg-slate-700">
                    {lang === 'id' ? 'Tolak' : 'Decline'}
                  </button>
                </div>
              )}
              {chal.status === 'completed' && (
                <button type="button" onClick={() => claimPvPReward(chal.id)} className="px-2 py-1 text-xs rounded-lg bg-amber-500 text-slate-950 font-black">
                  {lang === 'id' ? 'Klaim' : 'Claim'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {tab === 'chat' && (
        <div className="space-y-3">
          <select value={chatFriendId} onChange={(e) => setChatFriendId(e.target.value)} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs">
            <option value="">{t('cloud_chat_pick_friend', 'Pick friend')}</option>
            {friends.map((f) => (
              <option key={f.id} value={f.id}>
                {f.displayName || f.name}
              </option>
            ))}
          </select>
          <div className="h-72 overflow-y-auto rounded-xl border border-slate-800 bg-slate-950 p-3 space-y-2">
            {chatMessages.map((m) => (
              <div key={m.id} className={`text-xs ${m.isSelf ? 'text-right text-amber-200' : 'text-slate-300'}`}>
                {m.text}
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && chatInput.trim()) {
                  sendChatMessage(chatInput.trim(), chatFriendId || undefined);
                  setChatInput('');
                }
              }}
              className="flex-1 px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs"
            />
            <button
              type="button"
              onClick={() => {
                if (!chatInput.trim()) return;
                sendChatMessage(chatInput.trim(), chatFriendId || undefined);
                setChatInput('');
              }}
              className="px-3 py-2 rounded-xl bg-sky-600"
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
