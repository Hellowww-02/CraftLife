import React, { useState } from 'react';
import { useGame } from '../context/GameContext';
import { t } from '../i18n';
import { ProgressRing, DualLineChart } from './charts';
import { RankDialog, type RankInfo } from './RankDialog';
import { Medal } from 'lucide-react';

// ===== Shared rank type keluar dari /api/dashboard/summary =====
export const toRankInfo = (summary: any): RankInfo | null =>
  summary?.rank
    ? {
        rank: Number(summary.rank.rank) || 0,
        icon: summary.rank.icon || '🥚',
        nameKey: summary.rank.nameKey || 'rank_pemula',
        descKey: summary.rank.descKey || 'rank_desc_pemula',
        score: Number(summary.rank.score) || 0,
        maxScore: Number(summary.rank.maxScore) || 100,
      }
    : null;

/** RANK CARD (parity _rank_card DashboardPage PyQt). */
export const DashboardRankCard: React.FC<{ summary: any }> = ({ summary }) => {
  const [rankOpen, setRankOpen] = useState(false);
  const rank = toRankInfo(summary);
  if (!rank) return null;
  return (
    <div className="flex items-center gap-4 rounded-2xl p-4 bg-gradient-to-r from-amber-950/60 via-slate-900 to-slate-900 border border-amber-500/50 shadow-lg">
      <div className="text-5xl">{rank.icon}</div>
      <div className="flex-1 min-w-0">
        <div className="text-amber-400 text-lg font-black">{t(rank.nameKey, rank.nameKey)}</div>
        <div className="text-xs text-slate-400">{t(rank.descKey, rank.descKey)}</div>
        <div className="text-[11px] text-slate-500 mt-1">
          {t('rank_score_label', 'Score: {score} / {max}')
            .replace('{score}', String(rank.score))
            .replace('{max}', String(rank.maxScore))}
        </div>
      </div>
      <button
        type="button"
        onClick={() => setRankOpen(true)}
        className="px-3 py-2 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold hover:bg-amber-500/30 flex items-center gap-1.5 shrink-0"
      >
        <Medal className="w-4 h-4" /> {t('rank_dialog_title', '🏆 Daftar Rank').replace(/^🏆\s*/, '')}
      </button>
      {rankOpen && <RankDialog rank={rank} onClose={() => setRankOpen(false)} />}
    </div>
  );
};

/** STAT CARDS 4×2 (parity stats_data DashboardPage). */
export const DashboardStatCards: React.FC<{ summary: any }> = ({ summary }) => {
  const { user } = useGame();
  const st = summary?.stats || {};
  const sportNeed = Math.max(1, user.sportLevel * 100);
  const cards = [
    { icon: '⭐', title: t('dashboard_level', 'Level'), value: String(user.level), sub: '', color: '#f0a800' },
    { icon: '💰', title: t('dashboard_gold', 'Gold'), value: String(user.gold), sub: '', color: '#f0a800' },
    { icon: '❤️', title: t('dashboard_hp', 'HP'), value: `${user.hp}/${user.maxHp}`, sub: '', color: '#e05050' },
    { icon: '💙', title: t('dashboard_mp', 'MP'), value: `${user.mp}/${user.maxMp}`, sub: '', color: '#4da6ff' },
    { icon: '🔥', title: t('dashboard_streak', 'Streak'), value: String(st.maxStreak ?? user.longestStreak ?? 0), sub: t('dashboard_streak_days', 'hari'), color: '#ff6b00' },
    { icon: '📜', title: t('dashboard_tasks_done', 'Tasks Done'), value: String(st.totalTasksCompleted ?? 0), sub: '', color: '#80c000' },
    { icon: '👹', title: t('dashboard_boss_killed', 'Boss Killed'), value: String(st.bossesKilled ?? 0), sub: '', color: '#a97fff' },
    { icon: '🏅', title: t('dashboard_sport_level', 'Sport Level'), value: String(user.sportLevel), sub: `${user.sportXp}/${sportNeed} SP`, color: '#f0a800' },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
      {cards.map((c) => (
        <div
          key={c.title}
          className="flex items-center gap-2.5 rounded-lg bg-slate-900 border border-slate-800 px-2.5 py-2"
          style={{ borderLeft: `4px solid ${c.color}` }}
        >
          <div className="text-xl shrink-0">{c.icon}</div>
          <div className="min-w-0">
            <div className="text-[10px] text-slate-400">{c.title}</div>
            <div className="text-base font-bold text-slate-100 truncate">{c.value}</div>
            {!!c.sub && <div className="text-[10px] text-slate-500 truncate">{c.sub}</div>}
          </div>
        </div>
      ))}
    </div>
  );
};

/** PROGRESS RINGS (parity rings_group 2×2; web layout 2×2/4 responsive). */
export const DashboardRings: React.FC<{ summary: any }> = ({ summary }) => {
  const { user } = useGame();
  const xpNeed = Math.max(1, user.level * 150); // parity: need = level*150
  const sportNeed = Math.max(1, user.sportLevel * 100); // parity: sport_need = level*100
  const calGoal = Number(summary?.calorieGoal) || 2000;
  const calToday = Number(summary?.caloriesToday) || 0;
  const rings = [
    { value: user.xp, max: xpNeed, label: t('dashboard_level_progress', 'Level Progress'), color: '#80c000' },
    { value: user.hp, max: Math.max(1, user.maxHp), label: t('dashboard_hp_progress', 'HP'), color: '#e05050' },
    { value: user.sportXp, max: sportNeed, label: t('dashboard_sport_progress', 'Sport'), color: '#f0a800' },
    { value: calToday, max: calGoal, label: t('dashboard_calories', 'Calories'), color: '#4da6ff' },
  ];
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
      <h4 className="text-sm font-bold text-slate-200 mb-4">{t('dashboard_progress', '📈 Progress')}</h4>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 justify-items-center">
        {rings.map((r) => {
          const pct = Math.min(100, Math.round((r.value / Math.max(1, r.max)) * 100));
          return (
            <div key={r.label} className="flex flex-col items-center gap-1">
              <ProgressRing size={75} strokeWidth={8} progress={pct / 100} color={r.color}>
                <span className="text-sm font-black" style={{ color: r.color }}>{pct}%</span>
              </ProgressRing>
              <div className="text-[10px] font-bold text-slate-200 text-center max-w-[95px] leading-tight">{r.label}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** WEEKLY CHART XP/Gold (parity dashboard_weekly_chart). */
export const DashboardWeeklyChart: React.FC<{ summary: any }> = ({ summary }) => {
  const weekly = Array.isArray(summary?.weekly) ? summary.weekly : [];
  const a = weekly.map((w: any) => ({ label: String(w.day || '').slice(5), value: Number(w.xp) || 0 }));
  const b = weekly.map((w: any) => ({ label: String(w.day || '').slice(5), value: Number(w.gold) || 0 }));
  if (!a.length) return null;
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
      <h4 className="text-sm font-bold text-slate-200 mb-3">{t('dashboard_weekly_chart', '📊 7 Hari Terakhir')}</h4>
      <div className="overflow-x-auto">
        <div className="min-w-[420px]">
          <DualLineChart labels={a.map((d: any) => d.label)} a={a} b={b} colorA="#80c000" colorB="#f0a800" width={680} height={170} />
        </div>
      </div>
    </div>
  );
};

/** INSIGHTS CARD (parity _refresh_insights + insights card). */
export const DashboardInsightsCard: React.FC<{ summary: any; compact?: boolean }> = ({ summary, compact }) => {
  const ins = summary?.insights || {};
  const lines: string[] = [];
  if (ins?.has_data) {
    if (ins.top_weekday) lines.push(t('insights_top_day', '📅 Hari terproduktifmu: {day} ({n} aktivitas)').replace('{day}', ins.top_weekday).replace('{n}', String(ins.top_weekday_count ?? 0)));
    if (ins.best_day) lines.push(t('insights_best_day', '🏆 Hari terbaik: {n} task ({date})').replace('{n}', String(ins.best_day_count ?? 0)).replace('{date}', String(ins.best_day)));
    lines.push(t('insights_longest', '⛓️ Streak terpanjang: {n} hari').replace('{n}', String(ins.longest_streak ?? 0)));
    lines.push(t('insights_active', '🔥 Daily aktif: {n}').replace('{n}', String(ins.active_streaks ?? 0)));
    lines.push(t('insights_focus', '🍅 Fokus total: {n} menit').replace('{n}', String(ins.focus_minutes ?? 0)));
  }
  const shown = compact ? lines.slice(0, 2) : lines; // parity: compact = 2 baris
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
      <h4 className="text-sm font-bold text-slate-200">💡 {summary ? t('insights_title', '💡 Insight Otomatis').replace(/^💡\s*/, '') : t('insights_title', '💡 Insight Otomatis')}</h4>
      {shown.length === 0 ? (
        <p className="text-xs text-slate-500 py-2">{t('insights_no_data', 'Selesaikan beberapa task dulu untuk melihat insight!')}</p>
      ) : (
        <div className="mt-2 space-y-1">
          {shown.map((l, i) => (
            <p key={i} className="text-xs text-slate-300">{l.replace(/\*\*/g, '')}</p>
          ))}
        </div>
      )}
    </div>
  );
};

/** HEALTH CHART (parity _refresh_health_chart: tidur ↔ produktivitas + korelasi). */
export const DashboardHealthChart: React.FC<{ summary: any; compact?: boolean }> = ({ summary, compact }) => {
  const hc = summary?.healthChart || {};
  const series: any[] = Array.isArray(hc.series) ? hc.series : [];
  const corr = Number(hc.correlation) || 0;
  const hasSleep = Number(hc.daysWithSleepData) || 0;
  // Tampilkan 14 hari terakhir agar ringkas (parity grafik 30 hari → compact)
  const view = series.slice(compact ? -7 : -14);
  const labels = view.map((d) => String(d.date || '').slice(5));
  const sleep = view.map((d) => ({ label: String(d.date || '').slice(5), value: Number(d.sleep) || 0 }));
  const tasks = view.map((d) => ({ label: String(d.date || '').slice(5), value: Number(d.tasks) || 0 }));
  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 p-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-sm font-bold text-slate-200">{t('widget_health_chart', '😴 Grafik Tidur↔Produktivitas')}</h4>
        <span className="text-[10px] text-slate-500">r = {corr.toFixed(2)}</span>
      </div>
      {hasSleep === 0 ? (
        <p className="text-xs text-slate-500 py-2">—</p>
      ) : (
        <div className="overflow-x-auto">
          <div className="min-w-[380px]">
            <DualLineChart labels={labels} a={sleep} b={tasks} colorA="#7c8cff" colorB="#80c000" width={620} height={compact ? 120 : 160} />
          </div>
        </div>
      )}
    </div>
  );
};
