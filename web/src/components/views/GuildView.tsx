import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { studio } from '../../api/studio';
import { BossView } from './BossView';
import { Crown, Shield, Users, Zap } from 'lucide-react';

/** Mirror GuildPage: guild admin + boss (BossView sebagai seksi, bukan nav terpisah). */
export const GuildView: React.FC = () => {
  const { guild, attackGuildBoss, approveGuildRequest, rejectGuildRequest, refreshSocial, lang, showToast } = useGame();
  const [guildName, setGuildName] = useState('');
  const [joinId, setJoinId] = useState('');
  const [showBoss, setShowBoss] = useState(true);
  const [chatText, setChatText] = useState('');
  const [descDraft, setDescDraft] = useState('');
  const [inviteUser, setInviteUser] = useState('');
  const [invites, setInvites] = useState<{ id: string; guildName: string }[]>([]);

  useEffect(() => {
    refreshSocial();
    studio.guild().then((d) => {
      if (Array.isArray(d?.guildInvites)) setInvites(d.guildInvites);
    }).catch(() => undefined);
  }, [refreshSocial]);

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-black text-slate-100 flex items-center gap-2">
        <Shield className="w-6 h-6 text-amber-400" />
        {lang === 'id' ? 'Guild' : 'Guild'}
      </h2>

      <div className="flex flex-wrap gap-2 p-3 bg-slate-900 border border-slate-800 rounded-2xl">
        <input value={guildName} onChange={(e) => setGuildName(e.target.value)} placeholder={lang === 'id' ? 'Nama guild' : 'Guild name'} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs flex-1 min-w-[120px]" />
        <button
          type="button"
          onClick={() => {
            if (!guildName.trim()) return;
            studio.createGuild(guildName.trim()).then((r) => {
              showToast(r.ok ? 'success' : 'info', r.result?.msg || 'guild', '');
              refreshSocial();
            });
            setGuildName('');
          }}
          className="px-3 py-2 rounded-xl bg-amber-600 text-white text-xs font-bold"
        >
          {lang === 'id' ? 'Buat' : 'Create'}
        </button>
        <input value={joinId} onChange={(e) => setJoinId(e.target.value)} placeholder="ID" className="w-24 px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs" />
        <button
          type="button"
          onClick={() => {
            if (!joinId.trim()) return;
            studio.joinGuild(joinId.trim()).then((r) => {
              showToast(r.ok ? 'success' : 'info', r.result?.msg || 'join', '');
              refreshSocial();
            });
          }}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold"
        >
          {lang === 'id' ? 'Gabung' : 'Join'}
        </button>
        <button
          type="button"
          onClick={() => {
            studio.leaveGuild().then((r) => {
              showToast(r.ok ? 'success' : 'info', r.result?.msg || 'leave', '');
              refreshSocial();
            });
          }}
          className="px-3 py-2 rounded-xl bg-rose-900/50 text-rose-200 text-xs font-bold"
        >
          {lang === 'id' ? 'Keluar guild' : 'Leave guild'}
        </button>
        <button
          type="button"
          onClick={() => {
            studio.customBoss({ name: 'Custom Boss', hp: 2000, atk: 30 }).then((r) => {
              showToast(r.ok ? 'success' : 'info', r.result?.msg || 'boss', '');
              refreshSocial();
            });
          }}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold"
        >
          {lang === 'id' ? 'Boss kustom' : 'Custom boss'}
        </button>
      </div>

      <div className="p-5 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
        <div className="flex items-center gap-3">
          <Crown className="w-5 h-5 text-amber-400" />
          <div>
            <div className="font-black text-slate-100">{guild.name || (lang === 'id' ? 'Belum ada guild' : 'No guild')}</div>
            <div className="text-xs text-slate-400">Lv {guild.level} · {guild.exp}/{guild.maxExp} XP</div>
          </div>
        </div>
        {guild.bossMaxHp > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-rose-300">
              {guild.bossName || 'Boss'} {guild.bossHp}/{guild.bossMaxHp}
            </div>
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full bg-rose-500" style={{ width: `${Math.max(4, (guild.bossHp / guild.bossMaxHp) * 100)}%` }} />
            </div>
            <button type="button" onClick={() => attackGuildBoss(25)} className="px-3 py-2 rounded-xl bg-amber-600 text-white text-xs font-bold inline-flex items-center gap-1">
              <Zap className="w-3 h-3" /> {lang === 'id' ? 'Serang boss guild' : 'Strike guild boss'}
            </button>
          </div>
        )}
        <div className="space-y-1">
          <div className="text-xs font-bold text-slate-400 flex items-center gap-1">
            <Users className="w-3 h-3" /> {lang === 'id' ? 'Anggota' : 'Members'}
          </div>
          {(guild.members || []).map((m) => (
            <div key={m.id} className="text-xs text-slate-300 flex items-center justify-between gap-2">
              <span>{m.displayName || m.name} · {m.role} · Lv {m.level}</span>
              {m.role !== 'leader' && (
                <span className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => {
                      studio.kickGuild(m.id).then((r) => {
                        showToast(r.ok ? 'success' : 'info', r.result?.msg || 'kick', '');
                        refreshSocial();
                      });
                    }}
                    className="px-2 py-0.5 rounded bg-rose-900/50 text-rose-200 font-bold"
                  >
                    Kick
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      if (!window.confirm(lang === 'id' ? 'Transfer leadership?' : 'Transfer leadership?')) return;
                      studio.transferGuild(m.id).then((r) => {
                        showToast(r.ok ? 'success' : 'info', r.result?.msg || 'transfer', '');
                        refreshSocial();
                      });
                    }}
                    className="px-2 py-0.5 rounded bg-amber-900/50 text-amber-200 font-bold"
                  >
                    {lang === 'id' ? 'Transfer' : 'Transfer'}
                  </button>
                </span>
              )}
            </div>
          ))}
        </div>
        {(guild.requests || []).map((req) => (
          <div key={req.id} className="flex justify-between text-xs">
            <span>{req.name}</span>
            <span className="flex gap-1">
              <button type="button" onClick={() => approveGuildRequest(req.id)} className="px-2 py-1 bg-emerald-600 rounded-lg text-white">
                OK
              </button>
              <button type="button" onClick={() => rejectGuildRequest(req.id)} className="px-2 py-1 bg-slate-700 rounded-lg">
                X
              </button>
            </span>
          </div>
        ))}
      </div>

      <button type="button" onClick={() => setShowBoss(!showBoss)} className="text-xs text-amber-300 font-bold">
        {showBoss ? (lang === 'id' ? 'Sembunyikan arena boss solo' : 'Hide solo boss arena') : lang === 'id' ? 'Arena boss (seperti GuildPage)' : 'Solo boss arena (GuildPage)'}
      </button>
      {showBoss && <BossView />}
    </div>
  );
};
