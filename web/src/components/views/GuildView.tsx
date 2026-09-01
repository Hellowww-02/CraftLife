import React, { useEffect, useMemo, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { studio } from '../../api/studio';
import { authToken } from '../../api/client';
import { t } from '../../i18n';
import { X } from 'lucide-react';

const tr = (key: string, vars?: Record<string, string | number>) => {
  let s = t(key, key);
  if (!vars) return s;
  return s.replace(/\{(\w+)(:[^}]*)?\}/g, (m, name) =>
    name in vars ? String(vars[name]) : m);
};

const CUSTOM_BOSS_ICONS = ['👾', '👹', '🤖', '🦖', '🐙', '🦂', '🧌', '🐉', '🦇', '🍄'];
const TIERS = ['all', 'beginner', 'normal', 'hard', 'elite', 'legendary', 'seasonal'] as const;

interface BossItem {
  id: string; name: string; icon: string; tier: string; hp: number; atk: number;
  xp: number; gold: number; minLevel: number; maxLevel: number | null; available: boolean;
}

export const GuildView: React.FC = () => {
  const { user, guild, friends, refreshSocial, lang, showToast, applyLive } = useGame();
  const isLeader = !!guild.leaderId && String(guild.leaderId) === String(user.id ?? '');

  const [tick, setTick] = useState(0);
  const reload = () => { refreshSocial(); setTick((x) => x + 1); };
  const post = (p: Promise<any>, okMsg?: string) =>
    p.then((r) => { applyLive(r); const m = r?.result || r; showToast(m?.ok === false ? 'info' : 'success', m?.msg || okMsg || 'OK', ''); reload(); })
     .catch((e) => showToast('info', String(e?.message || e), ''));

  // ── Data tambahan: invites, rewards belum diklaim, katalog boss, class skills ──
  const [invites, setInvites] = useState<{ id: string; guildName: string }[]>([]);
  const [rewards, setRewards] = useState<any[]>([]);
  const [rewardDlg, setRewardDlg] = useState(false);
  const [bossList, setBossList] = useState<BossItem[]>([]);
  const [skills, setSkills] = useState<Record<string, { name: string; icon: string; mp_cost: number; desc: string }>>({});

  useEffect(() => { reload(); /* mount */ }, []);
  useEffect(() => {
    studio.guild().then((d) => { if (Array.isArray(d?.guildInvites)) setInvites(d.guildInvites); }).catch(() => undefined);
    studio.guildRewards().then((d) => {
      const arr = Array.isArray(d?.rewards) ? d.rewards : [];
      setRewards(arr);
      if (arr.length) setRewardDlg(true); // parity _show_unclaimed_rewards (auto dialog saat load)
    }).catch(() => undefined);
    fetch('/api/guild/bosses', { headers: authToken() ? { Authorization: `Bearer ${authToken()}` } : {} })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d && Array.isArray(d.bosses)) setBossList(d.bosses); })
      .catch(() => undefined);
    fetch('/api/catalog/class-skills', { headers: authToken() ? { Authorization: `Bearer ${authToken()}` } : {} })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => { if (d?.skills) setSkills(d.skills); })
      .catch(() => undefined);
  }, [tick]);

  // ── No-guild state ──
  const [gName, setGName] = useState('');
  const [gDesc, setGDesc] = useState('');
  const [joinId, setJoinId] = useState('');

  // ── Boss selector + raid team (parity _boss_selector/_show_team_selection) ──
  const [tier, setTier] = useState<(typeof TIERS)[number]>('all');
  const [bossId, setBossId] = useState('');
  const [teamDlg, setTeamDlg] = useState(false);
  const [teamSel, setTeamSel] = useState<Set<string>>(new Set());

  // ── Custom boss dialog (parity CustomBossDialog) ──
  const [bossModal, setBossModal] = useState(false);
  const [cbName, setCbName] = useState('');
  const [cbIcon, setCbIcon] = useState('👾');
  const [cbHp, setCbHp] = useState(1000);
  const [cbAtk, setCbAtk] = useState(20);
  const [cbMinLvl, setCbMinLvl] = useState(10);

  // ── Deskripsi & chat & invite member ──
  const [descDraft, setDescDraft] = useState('');
  const [chatText, setChatText] = useState('');

  // ── P26: undang teman ke guild (leader only) ──
  const [inviteFriendDlg, setInviteFriendDlg] = useState(false);

  const members: any[] = guild.members || [];
  const memberCount = members.length;
  const leader = members.find((m) => m.role === 'leader');
  const regular = members.filter((m) => m.role !== 'leader');

  const filteredBosses = useMemo(
    () => bossList.filter((b) => (tier === 'all' ? true : b.tier === tier) && b.available),
    [bossList, tier],
  );
  const selectedBoss = filteredBosses.find((b) => b.id === bossId) || null;

  const myClass = (user as any).avatarClass || 'warrior';
  const skill = skills[myClass] || { name: 'Shield Bash', icon: '🛡️', mp_cost: 10, desc: '' };

  // ═══ aksi ═══
  const startSolo = () => {
    if (!bossId) { showToast('info', tr('msg_error'), tr('raid_select_boss_first')); return; }
    void post(studio.startGuildBoss(bossId));
  };
  const openTeamDialog = () => {
    if (!bossId) { showToast('info', tr('msg_error'), tr('raid_select_boss_first')); return; }
    setTeamSel(new Set());
    setTeamDlg(true);
  };
  const participantOfTeam = (mid: string) => teamSel.has(mid);
  const toggleTeam = (mid: string) => {
    setTeamSel((prev) => {
      const next = new Set(prev);
      if (next.has(mid)) next.delete(mid);
      else if (next.size < 4) next.add(mid); // maks 4 + leader
      return next;
    });
  };
  const startWithTeam = () => {
    void post(studio.startGuildBoss(bossId, [...teamSel]));
    setTeamDlg(false);
  };
  const attack = (action: 'light' | 'heavy' | 'block' | 'ultimate') => {
    if ((user.hp || 0) <= 0) {
      showToast('info', tr('hp_habis_title'), tr('guild_hp_zero_msg'));
      return;
    }
    void post(studio.attackGuildBoss(action));
  };

  const myHpZero = (user.hp || 0) <= 0;

  // ═══ Admin block (parity load(): admin tidak pakai guild lokal) ═══
  if ((user as any).isAdmin) {
    return (
      <div className="px-4 md:px-8 pb-24 pt-4 max-w-3xl mx-auto animate-fade-in-up">
        <p className="text-center text-slate-500 py-10">{tr('guild_admin_warning')}</p>
      </div>
    );
  }

  // ═══ render ═══
  if (!guild.id) {
    return (
      <div className="px-4 md:px-8 pb-24 pt-4 max-w-3xl mx-auto space-y-4 animate-fade-in-up">
        <header>
          <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">{tr('page_guild_subtitle')}</p>
          <h2 className="text-2xl font-black text-slate-100">{tr('page_guild_title')}</h2>
        </header>
        <p className="text-sm text-slate-500">{tr('guild_no_guild')}</p>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
          <h3 className="text-sm font-black text-slate-100">{tr('guild_create')}</h3>
          <label className="block space-y-1">
            <span className="text-xs text-slate-500">{tr('dialog_name')}</span>
            <input value={gName} onChange={(e) => setGName(e.target.value)} placeholder={tr('guild_name')}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
          </label>
          <label className="block space-y-1">
            <span className="text-xs text-slate-500">{tr('guild_desc')}</span>
            <input value={gDesc} onChange={(e) => setGDesc(e.target.value)} placeholder={tr('guild_desc')}
              className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
          </label>
          <button type="button"
            onClick={() => { if (gName.trim()) void post(studio.createGuild(gName.trim(), gDesc.trim())); }}
            className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
            {tr('guild_create_btn')}
          </button>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
          <h3 className="text-sm font-black text-slate-100">{tr('guild_request')}</h3>
          <input type="number" min={1} value={joinId} onChange={(e) => setJoinId(e.target.value)} placeholder="ID"
            className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
          <button type="button"
            onClick={() => { if (joinId.trim()) void post(studio.joinGuild(joinId.trim())); }}
            className="w-full py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 text-xs font-bold">
            {tr('guild_accept')}
          </button>
        </div>

        {/* Invites juga bisa masuk saat belum punya guild — parity _add_requests_and_invites */}
        {invites.length > 0 && (
          <InvitesBlock invites={invites} onAct={(id, ok) => void post(ok ? studio.acceptGuildInvite(id) : studio.rejectGuildInvite(id))} />
        )}
      </div>
    );
  }

  const need = (guild.level || 1) * 500;

  return (
    <div className="px-4 md:px-8 pb-24 pt-4 max-w-6xl mx-auto space-y-4 animate-fade-in-up">
      {/* Header: judul + level + xp/progress (parity _make_header) */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.2em] text-amber-400/80 font-bold">{tr('page_guild_subtitle')}</p>
          <h2 className="text-2xl font-black text-slate-100">{guild.name}</h2>
          <p className="text-xs text-slate-400">{tr('guild_id_level', { id: guild.id, level: guild.level || 1 })}</p>
          {guild.description && <p className="text-xs text-slate-400">{tr('guild_description_label', { desc: guild.description })}</p>}
        </div>
        <div className="flex items-center gap-2">
          {isLeader && (
            <button type="button" onClick={() => setInviteFriendDlg(true)}
              className="px-3 py-2 rounded-xl bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold">
              {tr('guild_invite_friend_btn')}
            </button>
          )}
          {isLeader && (
            <button type="button" onClick={() => setDescDraft(guild.description || '')}
              className="px-3 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold">
              ✏️ {lang === 'id' ? 'Edit' : 'Edit'}
            </button>
          )}
          <button type="button" onClick={() => { if (window.confirm(tr('cloud_guild_leave_confirm'))) void post(studio.leaveGuild()); }}
            className="px-3 py-2 rounded-xl bg-rose-900/50 hover:bg-rose-900/80 text-rose-200 text-xs font-bold">
            {tr('guild_leave_btn')}
          </button>
        </div>
      </header>

      {descDraft !== '' && (
        <div className="flex gap-2 p-3 rounded-xl border border-slate-800 bg-slate-900/80">
          <input value={descDraft} onChange={(e) => setDescDraft(e.target.value)}
            className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100" />
          <button type="button"
            onClick={() => { void post(studio.guildDescription(descDraft.trim())); setDescDraft(''); }}
            className="px-3 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">{tr('dialog_save')}</button>
          <button type="button" onClick={() => setDescDraft('')}
            className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold">{tr('btn_cancel')}</button>
        </div>
      )}

      {/* Stat cards (parity _make_stats) */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5">
        {[
          [tr('guild_stats_level'), tr('guild_stats_level_value', { level: guild.level || 1 }), 'text-lime-400'],
          [tr('guild_stats_members'), tr('guild_stats_members_value', { count: memberCount }), 'text-sky-400'],
          [tr('guild_stats_bonus_xp'), tr('guild_stats_bonus_xp_value', { xp: guild.buffXp ?? 0 }), 'text-amber-400'],
          [tr('guild_stats_bonus_gold'), tr('guild_stats_bonus_gold_value', { gold: guild.buffGold ?? 0 }), 'text-amber-400'],
          [tr('guild_stats_bonus_damage'), tr('guild_stats_bonus_damage_value', { damage: guild.buffDamage ?? 0 }), 'text-rose-400'],
          [tr('guild_stats_bonus_crit'), tr('guild_stats_bonus_crit_value', { crit: guild.critChance ?? 0 }), 'text-violet-400'],
        ].map(([title, value, color], i) => (
          <div key={i} className="rounded-xl border border-slate-800 bg-slate-900/70 p-3 text-center">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">{title}</div>
            <div className={`text-sm font-black ${color}`}>{value}</div>
          </div>
        ))}
        <div className="col-span-2 md:col-span-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3 space-y-2">
          <div className="text-xs text-slate-300">{tr('guild_exp_progress', { exp: guild.exp || 0, need })}</div>
          <div className="h-4 rounded-full bg-slate-800 overflow-hidden">
            <div className="h-full bg-lime-500" style={{ width: `${Math.min(100, ((guild.exp || 0) / Math.max(1, need)) * 100)}%` }} />
          </div>
        </div>
      </div>

      {/* Skill bar (parity _make_actions) */}
      <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-3">
        <p className="flex-1 text-xs text-slate-300">
          {tr('guild_skill_info', { mp: user.mp || 0, max_mp: user.maxMp || 0, skill_icon: skill.icon, skill_name: skill.name, skill_cost: skill.mp_cost })}
        </p>
        <button type="button" onClick={() => void post(studio.guildSkill())}
          className="min-w-[140px] px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-black">
          {tr('guild_use_skill_with_icon', { icon: skill.icon })}
        </button>
      </div>

      {/* Jika ada reward belum diklaim → tombol buka dialog */}
      {rewards.length > 0 && !rewardDlg && (
        <button type="button" onClick={() => setRewardDlg(true)}
          className="w-full py-2.5 rounded-xl bg-amber-500/20 border border-amber-500/50 text-amber-300 text-xs font-black">
          🎁 {lang === 'id' ? `${rewards.length} reward boss belum diklaim` : `${rewards.length} unclaimed boss rewards`}
        </button>
      )}

      {/* SECTION MEMBERS (parity _make_members_section) */}
      <section className="space-y-2">
        <h3 className="text-sm font-black text-slate-100">{tr('guild_members', { count: memberCount })}</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
          {leader && <MemberCard m={leader} isLeader currentUserId={String(user.id ?? '')} isMe leadersView={isLeader}
            onKick={(id) => void post(studio.kickGuild(id))}
            onTransfer={(id) => { if (window.confirm(tr('guild_transfer_confirm_msg'))) void post(studio.transferGuild(id)); }} />}
          {regular.map((m) => (
            <MemberCard key={m.id} m={m} isLeader={false} currentUserId={String(user.id ?? '')} isMe={String(m.id) === String(user.id ?? '')} leadersView={isLeader}
              onKick={(id) => void post(studio.kickGuild(id))}
              onTransfer={(id) => { if (window.confirm(tr('guild_transfer_confirm_msg'))) void post(studio.transferGuild(id)); }} />
          ))}
        </div>
      </section>

      {/* SECTION BOSS (parity _make_boss_section) */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-3">
        <h3 className="text-sm font-black text-slate-100">{tr('guild_boss_battle')}</h3>
        {guild.bossMaxHp > 0 ? (
          <>
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-rose-300">{guild.bossName || 'Boss'}</span>
              <span className="text-slate-400 font-mono">{guild.bossHp}/{guild.bossMaxHp}</span>
            </div>
            <div className="h-5 rounded-xl bg-slate-800 overflow-hidden">
              <div className="h-full bg-rose-500" style={{ width: `${Math.max(3, (guild.bossHp / guild.bossMaxHp) * 100)}%` }} />
            </div>
            <p className="text-xs text-slate-400">
              {tr('guild_boss_atk_info', { atk: guild.bossAttack ?? 0, bonus: (user as any).bossDamageBonus ?? 0, total: 25 + ((user as any).bossDamageBonus ?? 0) })}
            </p>
            <p className="text-xs font-bold text-amber-300">
              {tr('raid_ultimate_label', { name: tr(`boss_ultimate_name_${myClass}`) })}
            </p>
            {myHpZero ? (
              <>
                <p className="text-xs font-bold text-rose-400">{tr('guild_hp_zero')}</p>
                <button type="button" onClick={() => void post(studio.guildQuickHeal())}
                  className="w-full py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
                  {tr('guild_quick_heal')}
                </button>
              </>
            ) : (
              <div className="grid grid-cols-2 gap-2.5">
                <button type="button" title={tr('boss_action_light_tip')} onClick={() => attack('light')}
                  className="h-11 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-black">{tr('boss_action_light_label')}</button>
                <button type="button" title={tr('boss_action_heavy_tip')} onClick={() => attack('heavy')}
                  className="h-11 rounded-xl bg-rose-700 hover:bg-rose-600 text-white text-xs font-black">{tr('boss_action_heavy_label')}</button>
                <button type="button" title={tr('boss_action_block_tip')} onClick={() => attack('block')}
                  className="h-11 rounded-xl bg-slate-700 hover:bg-slate-600 text-slate-100 text-xs font-black">{tr('boss_action_block_label')}</button>
                <button type="button" title={tr('boss_action_ultimate_tip')} onClick={() => attack('ultimate')}
                  className="h-11 rounded-xl bg-violet-700 hover:bg-violet-600 text-white text-xs font-black">{tr('boss_action_ultimate_label')}</button>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="text-xs text-slate-500">{tr('guild_boss_none')}</p>
            {/* Selector (parity _boss_selector: tier filter + item gabungan) */}
            <div className="flex flex-wrap gap-2">
              <select value={tier} onChange={(e) => setTier(e.target.value as typeof tier)}
                className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100">
                {TIERS.map((t2) => <option key={t2} value={t2}>{t2.toUpperCase()}</option>)}
              </select>
              <select value={bossId} onChange={(e) => setBossId(e.target.value)}
                className="flex-1 min-w-[200px] px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100">
                <option value="">—</option>
                {filteredBosses.map((b) => (
                  <option key={b.id} value={b.id}>
                    {tr('guild_boss_selector_item', {
                      lock: (user.level || 1) < b.minLevel ? '🔒 ' : '',
                      icon: b.icon, name: b.name, tier: b.tier.toUpperCase(), hp: b.hp, min_level: b.minLevel,
                    })}
                  </option>
                ))}
              </select>
            </div>
            {/* Info boss terpilih (parity _update_boss_info: spyglass = detail penuh) */}
            {selectedBoss && (
              <div className="text-xs text-slate-300">
                {tr('guild_boss_info_format', {
                  color: '',
                  icon: selectedBoss.icon,
                  name: selectedBoss.name,
                  tier: selectedBoss.tier.toUpperCase(),
                  hp: selectedBoss.hp,
                  atk: selectedBoss.atk,
                  xp: selectedBoss.xp,
                  gold: selectedBoss.gold,
                  min_level: selectedBoss.minLevel,
                  ok: (user.level || 1) >= selectedBoss.minLevel ? '✅' : '🔒',
                }).replace(/<[^>]+>/g, '')}
                {(user as any).hasSpyglass ? ` · 🔭 ${tr('guild_spyglass_detail')}` : ''}
              </div>
            )}
            {(user as any).hasSpyglass && (
              <p className="text-[11px] italic text-amber-300">{tr('guild_spyglass_active')}</p>
            )}
            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={startSolo}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-black">
                ⚔️ {lang === 'id' ? 'Mulai (Solo)' : 'Start (Solo)'}
              </button>
              <button type="button" onClick={openTeamDialog}
                className="px-4 py-2 rounded-xl bg-violet-700 hover:bg-violet-600 text-white text-xs font-black">
                🛡️ {tr('raid_team_selection')}
              </button>
              <button type="button" onClick={() => { setBossModal(true); setCbName(''); setCbIcon('👾'); setCbHp(1000); setCbAtk(20); setCbMinLvl(10); }}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-bold">
                {lang === 'id' ? 'Boss kustom' : 'Custom boss'}
              </button>
            </div>
          </>
        )}
      </section>

      {/* Invites & join requests (parity _add_requests_and_invites) */}
      <InvitesBlock invites={invites} onAct={(id, ok) => void post(ok ? studio.acceptGuildInvite(id) : studio.rejectGuildInvite(id))} />
      {isLeader && (guild.requests || []).length > 0 && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
          <h3 className="text-sm font-black text-slate-100">{tr('guild_join_requests')}</h3>
          {(guild.requests || []).map((req: any) => (
            <div key={req.id} className="flex items-center justify-between text-xs">
              <span>{tr('guild_join_request_format', { name: req.name, username: req.username })}</span>
              <span className="flex gap-1.5">
                <button type="button" onClick={() => void post(studio.approveGuildRequest(req.id))}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold">{tr('guild_accept')}</button>
                <button type="button" onClick={() => void post(studio.rejectGuildRequest(req.id))}
                  className="px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-200 font-bold">{tr('guild_reject')}</button>
              </span>
            </div>
          ))}
        </section>
      )}

      {/* Guild chat (parity _open_guild_chat inline) */}
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-black text-slate-100">💬 <b>{tr('guild_chat_title')}</b></h3>
          {isLeader && (
            <button type="button" onClick={() => { if (window.confirm(tr('chat_clear_all_confirm'))) void post(studio.clearGuildChat()); }}
              className="text-[11px] px-2 py-1 rounded-lg bg-slate-800 text-slate-400">{tr('chat_clear_all')}</button>
          )}
        </div>
        <div className="max-h-48 overflow-y-auto space-y-1.5">
          {(guild.messages || []).slice(-30).map((m: any) => (
            <div key={m.id} className={`text-xs ${m.isSelf ? 'text-amber-200' : 'text-slate-300'}`}>
              <span className="font-bold">{m.senderName}: </span>{m.text}
            </div>
          ))}
        </div>
        <div className="flex gap-2">
          <input value={chatText} onChange={(e) => setChatText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && chatText.trim()) { void post(studio.sendGuild(chatText.trim())); setChatText(''); } }}
            className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100" />
          <button type="button" onClick={() => { if (chatText.trim()) { void post(studio.sendGuild(chatText.trim())); setChatText(''); } }}
            className="px-4 py-2 rounded-xl bg-sky-600 text-white text-xs font-bold">➤</button>
        </div>
      </section>

      {/* ── Dialog raid team (parity _show_team_selection) ── */}
      {teamDlg && selectedBoss && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-3">
            <h3 className="text-lg font-black text-slate-100">{tr('raid_team_selection')}</h3>
            <p className="text-xs text-slate-400">
              {(lang === 'id'
                ? `Pilih anggota tim (maks 4 anggota + leader).\nMin level: ${selectedBoss.minLevel}, Max level: ${selectedBoss.maxLevel ?? '∞'}`
                : `Pick raid members (max 4 + leader).\nMin level: ${selectedBoss.minLevel}, Max level: ${selectedBoss.maxLevel ?? '∞'}`)}
            </p>
            <div className="space-y-1.5 max-h-60 overflow-y-auto">
              {regular
                .filter((m) => m.level >= selectedBoss.minLevel && (!selectedBoss.maxLevel || m.level <= selectedBoss.maxLevel))
                .map((m) => (
                  <label key={m.id} className="flex items-center gap-2 text-sm text-slate-200">
                    <input type="checkbox" checked={participantOfTeam(String(m.id))} onChange={() => toggleTeam(String(m.id))}
                      className="accent-amber-400" />
                    {m.displayName || m.name} (Lv.{m.level})
                  </label>
                ))}
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setTeamDlg(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold">{tr('btn_cancel')}</button>
              <button type="button" onClick={startWithTeam}
                className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black">⚔️</button>
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog reward (parity _show_unclaimed_rewards) ── */}
      {rewardDlg && rewards.length > 0 && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">🎁 {lang === 'id' ? 'Reward Boss' : 'Boss Rewards'}</h3>
              <button type="button" onClick={() => setRewardDlg(false)} className="text-slate-400"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {rewards.map((r: any) => (
                <div key={r.id} className="flex items-center justify-between text-xs bg-slate-950 rounded-xl p-3 border border-slate-800">
                  <span className="text-slate-300">
                    {r.boss_name || 'Boss'} · +{r.xp_reward ?? r.xp ?? 0} XP · +{r.gold_reward ?? r.gold ?? 0} G
                  </span>
                  <button type="button"
                    onClick={() => void post(studio.claimGuildReward(String(r.id))).then(() => {
                      setRewards((prev) => prev.filter((x) => x.id !== r.id));
                    })}
                    className="px-3 py-1.5 rounded-lg bg-amber-500 text-slate-950 font-black">
                    {lang === 'id' ? 'Klaim' : 'Claim'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Dialog custom boss (parity CustomBossDialog) ── */}
      {bossModal && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Buat Boss Kustom' : 'Create Custom Boss'}</h3>
              <button type="button" onClick={() => setBossModal(false)} className="text-slate-400"><X className="w-5 h-5" /></button>
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold">{lang === 'id' ? 'Nama' : 'Name'}</label>
              <input value={cbName} onChange={(e) => setCbName(e.target.value)} placeholder="👾 ..."
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
            </div>
            <div>
              <label className="text-xs text-slate-400 font-semibold">{lang === 'id' ? 'Ikon' : 'Icon'}</label>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {CUSTOM_BOSS_ICONS.map((ic) => (
                  <button key={ic} type="button" onClick={() => setCbIcon(ic)}
                    className={`w-9 h-9 rounded-lg text-lg flex items-center justify-center border ${cbIcon === ic ? 'bg-amber-500/20 border-amber-500/60' : 'bg-slate-800 border-slate-700'}`}>{ic}</button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="text-xs text-slate-400 font-semibold">HP</label>
                <input type="number" min={100} max={10000} step={100} value={cbHp}
                  onChange={(e) => setCbHp(Math.max(100, Number(e.target.value) || 100))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-400 font-semibold">ATK</label>
                <input type="number" min={1} max={150} value={cbAtk}
                  onChange={(e) => setCbAtk(Math.max(1, Number(e.target.value) || 1))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
              </div>
              <div>
                <label className="text-xs text-slate-400 font-semibold">{lang === 'id' ? 'Min. level' : 'Min level'}</label>
                <input type="number" min={1} max={99} value={cbMinLvl}
                  onChange={(e) => setCbMinLvl(Math.max(1, Number(e.target.value) || 1))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-sm" />
              </div>
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button type="button" onClick={() => setBossModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button type="button"
                onClick={() => {
                  if (!cbName.trim()) return;
                  void post(studio.customBoss({ name: cbName.trim(), icon: cbIcon, hp: cbHp, atk: cbAtk, minLevel: cbMinLvl }));
                  setBossModal(false);
                }}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs">
                {lang === 'id' ? 'Buat Boss' : 'Create Boss'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── P26: Leader undang teman (server-enforced) ── */}
      {inviteFriendDlg && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-5 space-y-3 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black text-slate-100">{tr('guild_invite_friend_title')}</h3>
              <button type="button" onClick={() => setInviteFriendDlg(false)} className="text-slate-400 text-lg leading-none">×</button>
            </div>
            {(friends || []).length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">{tr('guild_invite_friend_empty')}</p>
            ) : (
              <div className="space-y-2">
                {(friends || []).map((f: any) => (
                  <div key={f.id} className="flex items-center gap-2 rounded-lg bg-slate-800/60 border border-slate-700 px-3 py-2">
                    <span className="text-xl">{f.avatarEmoji || '⚔️'}</span>
                    <span className="flex-1 text-xs">
                      <b className="text-slate-100">{f.displayName || f.name}</b>
                      <span className="text-slate-500 block">@{f.username}</span>
                    </span>
                    <button type="button"
                      onClick={() => void post(studio.inviteGuildFriend(String(f.id)))}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-bold">
                      {tr('guild_invite_friend_send')}
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-end">
              <button type="button" onClick={() => setInviteFriendDlg(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold">{tr('btn_close')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

function MemberCard({ m, isLeader, currentUserId, isMe, leadersView, onKick, onTransfer }: {
  m: any; isLeader: boolean; currentUserId: string; isMe?: boolean; leadersView: boolean;
  onKick: (id: string) => void; onTransfer: (id: string) => void;
}) {
  const hp = Number(m.hp ?? 0); const maxHp = Math.max(1, Number(m.maxHp ?? 1));
  return (
    <div className={`rounded-xl border p-3 space-y-1.5 bg-slate-900/80 ${isLeader ? 'border-amber-500/70' : 'border-slate-800'}`}>
      <div className="flex items-center gap-2">
        <span className="text-2xl">{m.avatarEmoji || '⚔️'}</span>
        <span className="flex-1 text-xs font-bold text-slate-100">{m.displayName || m.name}</span>
        {isLeader && <span className="text-sm">👑</span>}
      </div>
      <div className="text-[10px] text-slate-500">{tr('level_abbr', { level: m.level || 1 })}</div>
      <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
        <div className={`h-full ${hp > 0 ? 'bg-lime-500' : 'bg-rose-500'}`}
          style={{ width: `${Math.max(2, (hp / maxHp) * 100)}%` }} />
      </div>
      {leadersView && !isMe && String(m.id) !== currentUserId && (
        <div className="flex gap-1.5 pt-1">
          <button type="button" onClick={() => onKick(String(m.id))}
            className="min-w-[45px] px-2 py-1 rounded-lg bg-rose-900/50 hover:bg-rose-900/80 text-rose-200 text-[11px] font-bold">{tr('guild_kick')}</button>
          <button type="button" onClick={() => onTransfer(String(m.id))}
            className="min-w-[60px] px-2 py-1 rounded-lg bg-amber-900/50 hover:bg-amber-900/80 text-amber-200 text-[11px] font-bold">{tr('guild_transfer')}</button>
        </div>
      )}
    </div>
  );
}

function InvitesBlock({ invites, onAct }: { invites: { id: string; guildName: string }[]; onAct: (id: string, ok: boolean) => void }) {
  if (!invites.length) return null;
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 space-y-2">
      <h3 className="text-sm font-black text-slate-100">{tr('guild_invites')}</h3>
      {invites.map((inv) => (
        <div key={inv.id} className="flex items-center justify-between text-xs">
          <span>{tr('guild_invite_from', { name: inv.guildName })}</span>
          <span className="flex gap-1.5">
            <button type="button" onClick={() => onAct(inv.id, true)}
              className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold">{tr('guild_accept')}</button>
            <button type="button" onClick={() => onAct(inv.id, false)}
              className="px-3 py-1.5 rounded-lg bg-rose-900/60 text-rose-200 font-bold">{tr('guild_reject')}</button>
          </span>
        </div>
      ))}
    </section>
  );
}
