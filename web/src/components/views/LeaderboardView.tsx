import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { Trophy } from 'lucide-react';
import { apiGet } from '../../api/client';
import { t } from '../../i18n';

// Parity MainPyQt6.LeaderboardPage:
// - combo mode: produktivitas online / guild online / ranking lokal
//   (cloud mode memanggil RPC supabase via /api/cloud/leaderboard; fallback
//   lokal bila belum linked, sama seperti PyQt)
// - tabel lokal 7 kolom: user · level · xp · gold · sport · pet · rebirth
// - nama = displayName + judul terlokalisasi + 💞 bila coupled
//   (tooltip partner / single; warna pink bila coupled)
// - sport ditampilkan "Lv.n" berwarna, rebirth berwarna oranye (parity)
// - cloud mode render kolom: rank · user/guild · points/exp · events/members

type LocalRow = {
  id: string;
  username: string;
  displayName: string;
  level: number;
  xp: number;
  gold: number;
  sportLevel: number;
  pets: number;
  rebirth: number;
  title: string;
  partner?: string;
  presence?: string;
  cloudUserId?: string;
};

type CloudRow = Record<string, any>;

type Mode = 'local' | 'cloud_productivity' | 'cloud_guild';

export const LeaderboardView: React.FC = () => {
  const { user } = useGame();
  const [mode, setMode] = useState<Mode>('local');
  const [rows, setRows] = useState<LocalRow[]>([]);
  const [cloudRows, setCloudRows] = useState<CloudRow[]>([]);
  const [cloudLinked, setCloudLinked] = useState(true);
  const [cloudError, setCloudError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setCloudError('');
    if (mode === 'local') {
      apiGet<any>('/api/leaderboard')
        .then((d) => setRows(d.leaderboard || []))
        .catch(() => setRows([]))
        .finally(() => setLoading(false));
      return;
    }
    apiGet<any>(`/api/cloud/leaderboard?mode=${mode}`)
      .then((d) => {
        if (d?.ok === false) {
          setCloudError(String(d.error || 'error'));
          setCloudRows([]);
          return;
        }
        setCloudLinked(Boolean(d?.linked));
        setCloudRows(d?.rows || []);
        if (!d?.linked) {
          // Parity PyQt: mode cloud tanpa link → render data lokal di tabel yang sama.
          apiGet<any>('/api/leaderboard')
            .then((lb) => setRows(lb.leaderboard || []))
            .catch(() => setRows([]));
        }
      })
      .catch((e) => {
        setCloudError(String(e?.message || e));
        setCloudRows([]);
      })
      .finally(() => setLoading(false));
  }, [mode]);

  const localColumns = [
    { key: 'user', label: t('leaderboard_col_user', 'User') },
    { key: 'level', label: t('leaderboard_col_level', 'Level') },
    { key: 'xp', label: t('leaderboard_col_xp', 'XP') },
    { key: 'gold', label: t('leaderboard_col_gold', 'Gold') },
    { key: 'sport', label: t('leaderboard_col_sport', 'Sport') },
    { key: 'pet', label: t('leaderboard_col_pet', 'Pet') },
    { key: 'rebirth', label: t('leaderboard_col_rebirth', 'Rebirth') },
  ];

  // Parity _render_cloud_leaderboard: header tergantung mode
  const cloudColumns =
    mode === 'cloud_guild'
      ? [t('leaderboard_rank', 'Rank'), t('leaderboard_guild', 'Guild'),
         t('leaderboard_col_level', 'Level'), t('cloud_leaderboard_exp', 'EXP'),
         t('cloud_leaderboard_members', 'Members')]
      : [t('leaderboard_rank', 'Rank'), t('leaderboard_col_user', 'User'),
         t('cloud_leaderboard_points', 'Points'), t('cloud_leaderboard_events', 'Events')];

  return (
    <div className="space-y-4 w-full mx-auto max-w-5xl">
      <div className="flex items-center gap-2">
        <Trophy className="w-6 h-6 text-amber-400" />
        <h2 className="text-xl font-black text-slate-100">{t('leaderboard_title', '🏆  Leaderboard')}</h2>
      </div>

      {/* Parity: combo mode (urutan sama seperti PyQt) */}
      <div className="flex items-center gap-3 flex-wrap">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as Mode)}
          className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
        >
          <option value="cloud_productivity">{t('cloud_leaderboard_productivity', 'Produktivitas Online')}</option>
          <option value="cloud_guild">{t('cloud_leaderboard_guild', 'Guild Online')}</option>
          <option value="local">{t('cloud_leaderboard_local', 'Ranking Lokal')}</option>
        </select>
        {mode === 'local' && (
          <p className="text-[11px] text-slate-500">{t('leaderboard_local_hint', 'You, friends, and guild members — local data.')}</p>
        )}
      </div>

      {/* Cloud fallback parity: bila mode cloud tapi belum linked → kembali lokal (seperti PyQt) */}
      {mode !== 'local' && !loading && !cloudLinked && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
          {t('leaderboard_cloud_fallback', 'Account not linked to cloud — falling back to local ranking (same as the desktop app).')}
          <button
            type="button"
            onClick={() => setMode('local')}
            className="ml-2 underline font-bold"
          >
            {t('cloud_leaderboard_local', 'Ranking Lokal')}
          </button>
        </div>
      )}
      {cloudError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-200">
          {cloudError}
        </div>
      )}

      {mode === 'local' || !cloudLinked ? (
        <div className="rounded-2xl border border-slate-800 overflow-hidden overflow-x-auto">
          <table className="w-full text-xs min-w-[680px]">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="p-2 text-left">#</th>
                {localColumns.map((c, i) => (
                  <th key={c.key} className={`p-2 ${i === 0 ? 'text-left' : 'text-center'}`}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const isSelf = String(user.id) === r.id;
                return (
                  <tr
                    key={r.id}
                    className={`border-t border-slate-800 ${isSelf ? 'bg-emerald-950/40 text-emerald-200' : 'text-slate-200'}`}
                  >
                    <td className="p-2 font-bold">
                      {i + 1 === 1 ? '🥇' : i + 1 === 2 ? '🥈' : i + 1 === 3 ? '🥉' : i + 1}
                    </td>
                    <td className="p-2 font-semibold whitespace-nowrap">
                      {r.displayName || r.username}
                      {r.title ? <span className="text-slate-400 font-normal">  {r.title}</span> : null}
                      {r.partner ? (
                        <span
                          className="ml-1 text-pink-400"
                          title={t('leaderboard_partner_tip', '💞 Punya pasangan: {name}').replace('{name}', r.partner)}
                        >
                          💞
                        </span>
                      ) : null}
                      {r.presence && r.presence !== 'offline' ? (
                        <span className="ml-1 text-[10px] text-emerald-400">{r.presence}</span>
                      ) : null}
                    </td>
                    <td className="p-2 text-center">{r.level}</td>
                    <td className="p-2 text-center">{r.xp}</td>
                    <td className="p-2 text-center">{Number(r.gold).toFixed(0)}</td>
                    {/* Parity: sport "Lv.n" kuning */}
                    <td className="p-2 text-center font-bold text-amber-400">{`Lv.${r.sportLevel || 1}`}</td>
                    <td className="p-2 text-center">{r.pets}</td>
                    {/* Parity: rebirth oranye */}
                    <td className="p-2 text-center font-bold text-orange-500">{r.rebirth}</td>
                  </tr>
                );
              })}
              {!loading && rows.length === 0 && (
                <tr>
                  <td colSpan={8} className="p-4 text-slate-500 text-center">
                    {t('leaderboard_empty', 'No rows yet.')}
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={8} className="p-4 text-slate-500 text-center">…</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-800 overflow-hidden overflow-x-auto">
          <table className="w-full text-xs min-w-[520px]">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                {cloudColumns.map((c, i) => (
                  <th key={c} className={`p-2 ${i === 1 ? 'text-left' : 'text-center'}`}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {cloudRows.map((r, i) => (
                <tr key={i} className="border-t border-slate-800 text-slate-200">
                  <td className="p-2 text-center font-bold">
                    {i + 1 === 1 ? '🥇' : i + 1 === 2 ? '🥈' : i + 1 === 3 ? '🥉' : i + 1}
                  </td>
                  {mode === 'cloud_guild' ? (
                    <>
                      <td className="p-2 font-semibold">{r.name || ''}</td>
                      <td className="p-2 text-center">{r.level ?? 1}</td>
                      <td className="p-2 text-center">{r.exp ?? 0}</td>
                      <td className="p-2 text-center">{r.member_count ?? 0}</td>
                    </>
                  ) : (
                    <>
                      <td className="p-2 font-semibold">{r.display_name || r.username || ''}</td>
                      <td className="p-2 text-center">{r.total_points ?? 0}</td>
                      <td className="p-2 text-center">{r.event_count ?? 0}</td>
                    </>
                  )}
                </tr>
              ))}
              {!loading && cloudRows.length === 0 && !cloudError && (
                <tr>
                  <td colSpan={cloudColumns.length} className="p-4 text-slate-500 text-center">
                    {t('leaderboard_cloud_empty', 'No cloud rows yet.')}
                  </td>
                </tr>
              )}
              {loading && (
                <tr>
                  <td colSpan={cloudColumns.length} className="p-4 text-slate-500 text-center">…</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
