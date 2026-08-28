import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { studio } from '../../api/studio';
import {
  Users,
  Shield,
  Swords,
  MessageSquare,
  Trophy,
  Crown,
  Zap,
  Send,
  Sparkles,
  Flame,
  Award,
  ChevronRight,
} from 'lucide-react';

type SocialTab = 'guild' | 'pvp' | 'friends' | 'chat';

export const SocialGuildView: React.FC<{ initialTab?: SocialTab }> = ({ initialTab = 'guild' }) => {
  const {
    guild,
    attackGuildBoss,
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
    approveGuildRequest,
    rejectGuildRequest,
    refreshSocial,
    user,
    lang,
    showToast,
  } = useGame();

  const [activeTab, setActiveTab] = useState<SocialTab>(initialTab);
  const [chatInput, setChatInput] = useState('');
  const [pvpAttackingId, setPvpAttackingId] = useState<string | null>(null);
  const [friendName, setFriendName] = useState('');
  const [chatFriendId, setChatFriendId] = useState<string>('');
  const [guildName, setGuildName] = useState('');
  const [joinId, setJoinId] = useState('');

  useEffect(() => {
    refreshSocial();
    const id = window.setInterval(() => refreshSocial(), 5000);
    return () => window.clearInterval(id);
  }, [refreshSocial]);

  const handleSendChat = () => {
    if (!chatInput.trim()) return;
    sendChatMessage(chatInput.trim(), chatFriendId || undefined);
    setChatInput('');
  };

  const handleRespondPvP = (id: string, accept: boolean) => {
    setPvpAttackingId(id);
    respondPvpChallenge(id, accept);
    setPvpAttackingId(null);
  };

  const handleSimulatePvP = (id: string) => {
    setPvpAttackingId(id);
    sendPvpChallenge(id);
    window.setTimeout(() => setPvpAttackingId((c) => (c === id ? null : c)), 600);
    void refreshSocial;
  };

  return (
    <div id="social-guild-pvp-view" className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-2xl">
            🛡️
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'id' ? 'Guild, Sahabat & Arena PvP' : 'Guild, Friends & PvP Arena'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-medium">
                Multiplayer Ecosystem
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Bergabung bersama anggota guild melawan World Boss, tantang teman di PvP, dan berinteraksi di chat.'
                : 'Co-op raid guild bosses, challenge friends in the PvP arena, and connect in realtime chat.'}
            </p>
          </div>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('guild')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'guild' ? 'bg-amber-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Guild</span>
          </button>
          <button
            onClick={() => setActiveTab('pvp')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'pvp' ? 'bg-amber-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Swords className="w-3.5 h-3.5" />
            <span>PvP Arena</span>
          </button>
          <button
            onClick={() => setActiveTab('friends')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'friends' ? 'bg-amber-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            <span>{lang === 'id' ? 'Sahabat' : 'Friends'} ({friends.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
              activeTab === 'chat' ? 'bg-amber-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Global Chat</span>
          </button>
        </div>
      </div>

      {/* TAB 1: GUILD HQ & WORLD BOSS RAID */}
      {activeTab === 'guild' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 p-3 bg-slate-900/70 border border-slate-800 rounded-2xl">
            <input value={guildName} onChange={(e) => setGuildName(e.target.value)} placeholder={lang === 'id' ? 'Nama guild baru' : 'New guild name'} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs flex-1 min-w-[140px]" />
            <button type="button" onClick={() => { if (guildName.trim()) { studio.createGuild(guildName.trim()).then((r) => { showToast(r.ok ? 'success' : 'info', r.result?.msg || 'guild', ''); refreshSocial(); }); setGuildName(''); } }} className="px-3 py-2 rounded-xl bg-amber-600 text-white text-xs font-bold">{lang === 'id' ? 'Buat guild' : 'Create guild'}</button>
            <input value={joinId} onChange={(e) => setJoinId(e.target.value)} placeholder="Guild ID" className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs w-28" />
            <button type="button" onClick={() => { if (joinId.trim()) { studio.joinGuild(joinId.trim()).then((r) => { showToast(r.ok ? 'success' : 'info', r.result?.msg || 'join', ''); refreshSocial(); }); } }} className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold text-slate-200">{lang === 'id' ? 'Minta gabung' : 'Request join'}</button>
          </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Columns: Guild Banner & Boss Raid */}
          <div className="lg:col-span-2 space-y-6">
            {/* Guild Card */}
            <div className="p-6 bg-gradient-to-br from-amber-950/40 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl space-y-5 shadow-xl">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                <div className="flex items-center gap-4">
                  <span className="text-4xl p-3 bg-amber-500/10 border border-amber-500/30 rounded-2xl shadow-lg">
                    {guild.badgeEmoji || '🛡️'}
                  </span>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-slate-100">{guild.name}</h2>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-mono font-bold">
                        LV. {guild.level}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">{guild.description}</p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs text-slate-500 block">Guild EXP</span>
                  <span className="text-sm font-bold font-mono text-amber-400">
                    {guild.exp} / {guild.maxExp} XP
                  </span>
                </div>
              </div>

              {/* Boss Raid Arena */}
              <div className="p-5 bg-slate-950/80 border border-amber-500/20 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl animate-bounce">🐲</span>
                    <div>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-rose-400">Guild World Boss</span>
                      <h3 className="font-bold text-base text-slate-100">{guild.bossName}</h3>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-rose-400">
                      {guild.bossHp} / {guild.bossMaxHp} HP
                    </span>
                  </div>
                </div>

                {/* HP Bar */}
                <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
                  <div
                    className="h-full bg-gradient-to-r from-rose-600 to-amber-500 rounded-full transition-all duration-300"
                    style={{ width: `${Math.max(5, (guild.bossHp / guild.bossMaxHp) * 100)}%` }}
                  />
                </div>

                {/* Attack Controls */}
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-slate-400">
                    {lang === 'id' ? 'Serang bersama anggota guild untuk EXP & Gold bonus!' : 'Raid with guild members for massive XP & Guild tokens!'}
                  </span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => attackGuildBoss(25)}
                      className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs rounded-xl transition-colors shadow-md shadow-amber-600/20 flex items-center gap-1.5"
                    >
                      <Zap className="w-3.5 h-3.5" />
                      <span>Strike (25 DMG)</span>
                    </button>
                    <button
                      onClick={() => attackGuildBoss(60)}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl transition-colors shadow-md shadow-rose-600/20 flex items-center gap-1.5"
                    >
                      <Flame className="w-3.5 h-3.5" />
                      <span>Ultimate (60 DMG)</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Right 1 Column: Guild Roster */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Users className="w-4 h-4 text-amber-400" />
                <span>{lang === 'id' ? 'Anggota Guild' : 'Guild Roster'} ({guild.members?.length || 0})</span>
              </h3>
              <Crown className="w-4 h-4 text-amber-400" />
            </div>

            <div className="space-y-2.5">
              {guild.members?.map((mem) => (
                <div
                  key={mem.id}
                  className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-xl">{mem.avatarEmoji || mem.avatar || '🛡️'}</span>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <h4 className="font-semibold text-xs text-slate-100">{mem.displayName || mem.name}</h4>
                        {mem.role === 'leader' && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 font-bold">
                            LEADER
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-slate-500">Lv. {mem.level} · {mem.classTitle || 'Adventurer'}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono font-bold text-amber-400/80">+{mem.weeklyContribution || mem.contribution || 0}</span>
                    <span className="block text-[10px] text-slate-500">Contrib</span>
                  </div>
                </div>
              ))}
            </div>
            {(guild.requests || []).length > 0 && (
              <div className="p-4 bg-slate-950/80 border border-slate-800 rounded-xl space-y-2">
                <h4 className="text-xs font-bold text-amber-300 uppercase">{lang === 'id' ? 'Permintaan gabung' : 'Join requests'}</h4>
                {(guild.requests || []).map((req) => (
                  <div key={req.id} className="flex items-center justify-between gap-2 text-xs">
                    <span className="text-slate-200">{req.name || req.username}</span>
                    <div className="flex gap-1">
                      <button type="button" onClick={() => approveGuildRequest(req.id)} className="px-2 py-1 rounded-lg bg-emerald-600 text-white font-bold">{lang === 'id' ? 'Setujui' : 'Approve'}</button>
                      <button type="button" onClick={() => rejectGuildRequest(req.id)} className="px-2 py-1 rounded-lg bg-slate-700 text-slate-200">{lang === 'id' ? 'Tolak' : 'Reject'}</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        </div>
      )}

      {/* TAB 2: PVP ARENA */}
      {activeTab === 'pvp' && (
        <div className="space-y-6">
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
                  <Swords className="w-5 h-5 text-amber-400" />
                  <span>{lang === 'id' ? 'Tantangan Arena PvP Real-time' : 'PvP Arena Challenges'}</span>
                </h3>
                <p className="text-xs text-slate-400">
                  {lang === 'id'
                    ? 'Bertarung adu produktivitas dan stamina melawan petarung lain.'
                    : 'Compete in productivity duels and claim glorious gold and XP bounties.'}
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {pvpChallenges.map((chal) => (
                <div
                  key={chal.id}
                  className="p-5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-4 relative overflow-hidden"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-3xl p-2 bg-slate-900 rounded-xl border border-slate-800">
                        {chal.opponentAvatar}
                      </span>
                      <div>
                        <h4 className="font-bold text-sm text-slate-100">{chal.opponentName}</h4>
                        <p className="text-xs text-slate-500">
                          Opponent Score: <span className="font-mono text-slate-300">{chal.opponentScore} PTS</span>
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs px-2.5 py-1 rounded-full uppercase font-bold ${
                        chal.status === 'completed'
                          ? 'bg-emerald-500/20 text-emerald-300'
                          : 'bg-amber-500/20 text-amber-300'
                      }`}
                    >
                      {chal.status}
                    </span>
                  </div>

                  {/* Rewards */}
                  <div className="flex items-center justify-between bg-slate-900/90 p-3 rounded-lg border border-slate-800/80 text-xs">
                    <span className="text-slate-400">Bounty:</span>
                    <span className="font-bold text-amber-400 font-mono">
                      +{chal.rewardXp} XP · +{chal.rewardGold} Gold
                    </span>
                  </div>

                  {/* Action Button */}
                  <button
                    disabled={chal.status === 'completed' || pvpAttackingId === chal.id}
                    onClick={() => handleSimulatePvP(chal.id)}
                    className="w-full py-2.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white font-bold text-xs rounded-xl transition-colors shadow-md shadow-amber-600/20 flex items-center justify-center gap-2"
                  >
                    {pvpAttackingId === chal.id ? (
                      <>
                        <Sparkles className="w-4 h-4 animate-spin" />
                        <span>Battling...</span>
                      </>
                    ) : chal.status === 'completed' ? (
                      <span>Defeated & Claimed</span>
                    ) : (
                      <>
                        <Swords className="w-4 h-4" />
                        <span>Duel Opponent</span>
                      </>
                    )}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: FRIENDS LIST */}
      {activeTab === 'friends' && (
        <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <h3 className="font-bold text-base text-slate-100 flex items-center gap-2">
              <Users className="w-5 h-5 text-amber-400" />
              <span>{lang === 'id' ? 'Daftar Teman & Status' : 'Friends List & Online Presence'}</span>
            </h3>
            <div className="flex gap-2">
              <input
                value={friendName}
                onChange={(e) => setFriendName(e.target.value)}
                placeholder={t('cloud_friend_username', lang === 'id' ? 'Username cloud teman' : 'Friend cloud username')}
                className="px-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100"
              />
              <button
                onClick={() => { if (friendName.trim()) { sendFriendRequest(friendName.trim()); setFriendName(''); } }}
                className="px-3 py-1.5 rounded-xl bg-amber-600 text-white text-xs font-bold"
              >
                {t('cloud_friend_add', lang === 'id' ? 'Kirim permintaan' : 'Send request')}
              </button>
            </div>
          </div>

          {(friendRequests || []).length > 0 && (
            <div className="space-y-2 p-3 bg-slate-950/70 border border-slate-800 rounded-xl">
              <h4 className="text-xs font-bold uppercase text-amber-300">{lang === 'id' ? 'Permintaan pertemanan' : 'Friend requests'}</h4>
              {friendRequests.map((req) => (
                <div key={req.id} className="flex items-center justify-between gap-2 text-xs">
                  <span className="text-slate-200">{req.name || req.username}</span>
                  <div className="flex gap-1">
                    <button type="button" onClick={() => acceptFriendRequest(req.id)} className="px-2 py-1 rounded-lg bg-emerald-600 text-white font-bold">{lang === 'id' ? 'Terima' : 'Accept'}</button>
                    <button type="button" onClick={() => rejectFriendRequest(req.id)} className="px-2 py-1 rounded-lg bg-slate-700">{lang === 'id' ? 'Tolak' : 'Reject'}</button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {friends.map((friend) => (
              <div
                key={friend.id}
                className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <span className="text-2xl">{friend.avatarEmoji || friend.avatar || '🧙'}</span>
                      <span
                        className={`w-2.5 h-2.5 rounded-full absolute -bottom-0.5 -right-0.5 ring-2 ring-slate-950 ${
                          friend.status === 'online' ? 'bg-emerald-500' : 'bg-slate-600'
                        }`}
                      />
                    </div>
                    <div>
                      <h4 className="font-bold text-sm text-slate-100">{friend.displayName || friend.name}</h4>
                      <p className="text-xs text-slate-500">{friend.classTitle || friend.heroClass || 'Adventurer'} · Lv. {friend.level}</p>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-900">
                  <span className="flex items-center gap-1 text-amber-400">
                    <Flame className="w-3.5 h-3.5" />
                    <span>{friend.streakDays || friend.streak || 0} Day Streak</span>
                  </span>
                  <span className="text-[11px] text-slate-500">
                    {friend.status === 'online' ? 'Active now' : `Last seen ${friend.lastSeen || 'recently'}`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: REAL-TIME GLOBAL CHAT */}
      {activeTab === 'chat' && (
        <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-amber-400" />
              <span>{lang === 'id' ? 'Ruang Percakapan Global' : 'Global Realm Chat'}</span>
            </h3>
            <select
              value={chatFriendId}
              onChange={(e) => setChatFriendId(e.target.value)}
              className="text-xs bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-slate-200"
            >
              <option value="">{t('cloud_chat_pick_friend', lang === 'id' ? 'Pilih teman' : 'Pick a friend')}</option>
              {friends.map((f) => (
                <option key={f.id} value={f.id}>{f.displayName || f.name || f.id}</option>
              ))}
            </select>
          </div>

          {/* Messages Container */}
          <div className="h-[400px] overflow-y-auto space-y-3 p-4 bg-slate-950/80 rounded-xl border border-slate-800">
            {chatMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${msg.isSelf ? 'justify-end' : 'justify-start'}`}
              >
                {!msg.isSelf && (
                  <span className="text-xl p-1 bg-slate-900 border border-slate-800 rounded-lg h-fit">
                    {msg.senderAvatar || '👤'}
                  </span>
                )}
                <div
                  className={`p-3 rounded-xl max-w-md text-xs leading-relaxed ${
                    msg.isSelf
                      ? 'bg-amber-600 text-white rounded-br-none'
                      : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {!msg.isSelf && (
                    <span className="block font-bold text-amber-300 text-[11px] mb-0.5">{msg.senderName}</span>
                  )}
                  <p>{msg.text}</p>
                  <span className="block text-[10px] text-slate-400 mt-1 text-right">{msg.timestamp}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Chat Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
              placeholder={lang === 'id' ? 'Kirim pesan ke seluruh pemain...' : 'Send message to global adventurers...'}
              className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500"
            />
            <button
              onClick={handleSendChat}
              disabled={!chatInput.trim()}
              className="px-4 py-2.5 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white rounded-xl font-semibold text-xs transition-colors flex items-center gap-1.5"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
