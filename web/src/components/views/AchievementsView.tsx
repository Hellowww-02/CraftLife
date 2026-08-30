import React, { useEffect, useMemo, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { apiGet, apiPost } from '../../api/client';
import { t } from '../../i18n';

// Parity MainPyQt6.AchievementPage: search + combo kategori (all + 15),
// grid kartu 3 kolom; nama/deskripsi SELALU via db.tr_achievement (server
// melokalisasi field title/desc), progress bar + reward + status klaim.

interface Achievement {
  id: string;
  title: string;
  desc: string;
  category: string;
  icon: string;
  xpReward: number;
  goldReward: number;
  currentProgress: number;
  targetProgress: number;
  isUnlocked: boolean;
  isClaimed: boolean;
}

const CATEGORIES = [
  'level', 'habit', 'daily', 'todo', 'sport', 'economy', 'pet', 'guild',
  'boss', 'social', 'health', 'nutrition', 'special', 'focus', 'crafting',
];

export const AchievementsView: React.FC = () => {
  const { lang, showToast } = useGame();
  const [items, setItems] = useState<Achievement[]>([]);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [busyId, setBusyId] = useState<string | null>(null);
  const isId = lang === 'id';

  const load = async () => {
    try {
      const res = await apiGet<any>('/api/achievements');
      setItems(res.achievements || []);
    } catch {
      // biarkan kosong; bootstrap error sudah dihandle global shell
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    let list = items;
    if (category !== 'all') list = list.filter((a) => a.category === category);
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (a) => a.title.toLowerCase().includes(q) || a.desc.toLowerCase().includes(q),
      );
    }
    return list;
  }, [items, search, category]);

  const claim = async (a: Achievement) => {
    setBusyId(a.id);
    try {
      const res = await apiPost<any>(`/api/achievements/${a.id}/claim`, {});
      if (res?.ok === false) {
        showToast('info', res.error || t('msg_error', 'Terjadi kesalahan'), '');
      } else {
        showToast(
          'success',
          isId ? `Reward diklaim: +${a.xpReward} XP +${a.goldReward} Gold` : `Reward claimed: +${a.xpReward} XP +${a.goldReward} Gold`,
          '',
        );
        await load();
        // snapshot diisi ulang lewat bootstrap agar XP/gold di header segar
      }
    } catch (e: any) {
      showToast('info', String(e?.message || e), '');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-5 max-w-6xl">
      <div>
        <h2 className="text-xl font-black text-slate-100">🏆 {t('nav_achievements', 'Achievement')}</h2>
        <p className="text-xs text-slate-400 mt-1">
          {isId
            ? 'Koleksi pencapaian dari semua aktivitasmu. Claim reward untuk setiap kesuksesan.'
            : 'A collection of milestones across every activity. Claim the reward for each success.'}
        </p>
      </div>

      {/* Parity AchievementPage: search input + combo kategori */}
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('achievement_search', '🔍 Cari achievement...')}
          className="flex-1 px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm focus:outline-none focus:border-amber-500"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="px-3 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-100 text-sm capitalize focus:outline-none focus:border-amber-500"
        >
          <option value="all">{t('achievement_all', 'Semua')}</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {t(`achievement_category_${c}`, c)}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-10 text-center text-slate-400 text-sm">
          {t('achievement_empty', 'Belum ada achievement yang cocok.')}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((a) => {
            const pct = Math.max(
              0,
              Math.min(100, Math.round((a.currentProgress / Math.max(1, a.targetProgress)) * 100)),
            );
            return (
              <div
                key={a.id}
                className={`rounded-2xl p-4 border flex flex-col gap-2 transition-all ${
                  a.isUnlocked
                    ? 'bg-slate-900 border-amber-500/50 shadow-lg shadow-amber-500/5'
                    : 'bg-slate-900/70 border-slate-800 opacity-80'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-11 h-11 rounded-2xl text-2xl flex items-center justify-center shrink-0 ${
                      a.isUnlocked ? 'bg-amber-500/15' : 'bg-slate-800 grayscale'
                    }`}
                  >
                    <span className={a.isUnlocked ? '' : 'opacity-50'}>{a.icon}</span>
                  </div>
                  <div className="min-w-0">
                    <p className="font-bold text-sm text-slate-100 truncate">{a.title}</p>
                    <p className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{a.desc}</p>
                  </div>
                </div>

                {/* progress bar parity achievement_progress_format */}
                <div>
                  <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className={`h-full transition-all ${a.isUnlocked ? 'bg-amber-400' : 'bg-sky-500/70'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-slate-500 mt-1 font-mono">
                    {t('achievement_progress_format', '{progress} / {req} ({percent}%)')
                      .replace('{progress}', String(a.currentProgress))
                      .replace('{req}', String(a.targetProgress))
                      .replace('{percent}', String(pct))}
                  </p>
                </div>

                <p className="text-[11px] font-bold text-amber-300">
                  {t('achievement_reward_format', '🏆 Reward: +{xp} XP  +{gold} Gold')
                    .replace('{xp}', String(a.xpReward))
                    .replace('{gold}', String(a.goldReward))}
                </p>

                {/* status parity: locked / unlocked+claim / claimed */}
                <div className="mt-auto pt-1">
                  {!a.isUnlocked ? (
                    <p className="text-[11px] text-slate-500 font-bold">{t('achievement_locked', '🔒 Terkunci')}</p>
                  ) : !a.isClaimed ? (
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[11px] text-emerald-400 font-bold">
                        {t('achievement_unlocked', '✅ UNLOCKED')}
                      </span>
                      <button
                        type="button"
                        disabled={busyId === a.id}
                        onClick={() => claim(a)}
                        className="px-3 py-1.5 rounded-xl bg-amber-400 hover:bg-amber-300 text-slate-950 text-[11px] font-black disabled:opacity-50 active:scale-95 transition-all"
                      >
                        {t('achievement_claim', 'Klaim Reward')}
                      </button>
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-400 font-bold">
                      {t('achievement_claimed', '✅ Reward Diklaim')}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
