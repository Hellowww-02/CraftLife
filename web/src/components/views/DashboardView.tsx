import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { rpg } from '../../api/rpg';
import { AVATAR_CLASSES, PETS_DATA } from '../../data/gameData';
import {
  Zap,
  CalendarCheck,
  CheckSquare,
  Activity,
  Salad,
  Swords,
  Coins,
  Gem,
  Plus,
  ArrowRight,
  Shield,
  Droplets,
  Flame,
  BookOpen,
  Music2,
  Heart,
  Users,
  Calendar as CalendarIcon,
  Settings2,
  Trophy,
} from 'lucide-react';
import { ActiveView, NavTab } from '../../types';
import { ProgressRing } from '../charts';
import { DashboardWidgetsDialog } from '../DashboardWidgetsDialog';
import { YearWrappedDialog } from '../YearWrappedDialog';

export const DashboardView: React.FC<{ onNavigate?: (tab: ActiveView) => void; setActiveTab?: (tab: NavTab) => void }> = ({ onNavigate, setActiveTab }) => {
  const navigate = (tab: ActiveView) => {
    if (onNavigate) onNavigate(tab);
    if (setActiveTab) setActiveTab(tab);
  };
  const { user, lang, habits, dailies, quests, sportLogs, mealLogs, waterLog, activeBoss, activeBossHp, triggerHabit, toggleDaily, toggleQuest, dailyTaskCounts } = useGame();
  const [widgetsOpen, setWidgetsOpen] = useState(false);
  const [wrappedOpen, setWrappedOpen] = useState(false);

  const currentClass = AVATAR_CLASSES[user.avatarClass] || AVATAR_CLASSES.warrior;
  const lvlXpPct = Math.min(100, Math.round((user.xp / Math.max(1, user.xpToNextLevel)) * 100));

  const completedDailiesCount = dailies.filter((d) => d.isCompletedToday).length;
  const totalDailiesCount = dailies.length;
  const pendingQuests = quests.filter((q) => !q.isCompleted);
  const totalCaloriesToday = mealLogs.reduce((acc, m) => acc + m.calories, 0);

  return (
    <div className="space-y-6">
      {/* Top Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border border-slate-700/60 p-5 sm:p-6 shadow-xl">
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
          <div className="flex items-center gap-4">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl font-bold border-2 shadow-xl shrink-0"
              style={{
                backgroundColor: `${currentClass.color}25`,
                borderColor: currentClass.color,
              }}
            >
              {user.avatarEmoji || currentClass.icon}
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black text-slate-100">{user.displayName || user.username}</h1>
                <span className="px-2 py-0.5 text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-full">
                  Lv.{user.level} {currentClass.name}
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-1 max-w-lg">
                {user.bio || 'Your daily habit progress fuels your character strength and equips you for legendary quests!'}
              </p>
            </div>
          </div>

          {/* ProgressRing (Level/XP) — parity with PyQt ProgressRing */}
          <div className="flex items-center gap-4">
            <ProgressRing size={72} strokeWidth={7} progress={lvlXpPct / 100} color="#f59e0b">
              <div className="text-center">
                <div className="text-[10px] text-slate-400 font-bold uppercase">Lv</div>
                <div className="text-lg font-black text-amber-300 leading-none">{user.level}</div>
              </div>
            </ProgressRing>
            <div className="flex flex-col gap-1.5">
              <button
                type="button"
                onClick={() => setWrappedOpen(true)}
                className="px-3 py-1.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center gap-1.5 hover:bg-amber-500/30"
              >
                <Trophy className="w-3.5 h-3.5" /> {lang === 'id' ? 'Tahun Ini' : 'Year Wrapped'}
              </button>
              <button
                type="button"
                onClick={() => setWidgetsOpen(true)}
                className="px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 text-xs font-bold flex items-center gap-1.5 hover:bg-slate-700"
              >
                <Settings2 className="w-3.5 h-3.5" /> {lang === 'id' ? 'Atur Widget' : 'Widgets'}
              </button>
            </div>
          </div>

          {/* Quick Action Stats */}
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <div className="px-3.5 py-2 rounded-xl bg-slate-950/70 border border-slate-700 text-center min-w-[70px]">
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Dailies' : 'Dailies'}</div>
              <div className="text-sm font-extrabold text-emerald-400">{completedDailiesCount}/{totalDailiesCount}</div>
            </div>

            <div className="px-3.5 py-2 rounded-xl bg-slate-950/70 border border-slate-700 text-center min-w-[70px]">
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Quests' : 'Quests'}</div>
              <div className="text-sm font-extrabold text-sky-400">{pendingQuests.length}</div>
            </div>

            <div className="px-3.5 py-2 rounded-xl bg-slate-950/70 border border-slate-700 text-center min-w-[70px]">
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Air' : 'Water'}</div>
              <div className="text-sm font-extrabold text-cyan-400">{Math.round((waterLog.amountMl / waterLog.targetMl) * 100)}%</div>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
        <h3 className="text-xs font-bold text-slate-300 mb-2">{lang === 'id' ? 'Heatmap 28 hari (dailies selesai)' : '28-day heatmap (dailies done)'}</h3>
        <div className="grid grid-cols-7 gap-1">
          {Array.from({ length: 28 }).map((_, i) => {
            const d = new Date();
            d.setDate(d.getDate() - (27 - i));
            const key = d.toISOString().slice(0, 10);
            // Sumber data heatmap: `task_history` per hari (authoritative).
            // Fallback ke jumlah daily yang selesai hari itu bila belum tersedia.
            const n = dailyTaskCounts[key] ?? dailies.filter((x) => x.lastCompletedDate === key || (x.isCompletedToday && i === 27)).length;
            const bg = n === 0 ? 'bg-slate-800' : n < 2 ? 'bg-emerald-900' : n < 4 ? 'bg-emerald-600' : 'bg-emerald-400';
            return <div key={key} title={`${key}: ${n}`} className={`h-4 rounded-sm ${bg}`} />;
          })}
        </div>
      </div>

      {/* Quick Adventure Hub */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        <button
          onClick={() => navigate('learning')}
          className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-violet-500/50 rounded-2xl text-left transition-all group flex items-center gap-3 shadow-sm"
        >
          <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400 group-hover:scale-105 transition-transform shrink-0">
            <BookOpen className="w-5 h-5" />
          </div>
          <div className="truncate">
            <h4 className="font-bold text-xs text-slate-200 group-hover:text-violet-300 transition-colors truncate">
              {lang === 'id' ? 'Belajar AI' : 'AI Study'}
            </h4>
            <span className="text-[10px] text-slate-500">NotebookLM</span>
          </div>
        </button>

        <button
          onClick={() => navigate('music')}
          className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/50 rounded-2xl text-left transition-all group flex items-center gap-3 shadow-sm"
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-105 transition-transform shrink-0">
            <Music2 className="w-5 h-5" />
          </div>
          <div className="truncate">
            <h4 className="font-bold text-xs text-slate-200 group-hover:text-emerald-300 transition-colors truncate">
              {lang === 'id' ? 'Musik & Lofi' : 'Focus Audio'}
            </h4>
            <span className="text-[10px] text-slate-500">Spotify / Synth</span>
          </div>
        </button>

        <button
          onClick={() => navigate('lovespace')}
          className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-rose-500/50 rounded-2xl text-left transition-all group flex items-center gap-3 shadow-sm"
        >
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 group-hover:scale-105 transition-transform shrink-0">
            <Heart className="w-5 h-5" />
          </div>
          <div className="truncate">
            <h4 className="font-bold text-xs text-slate-200 group-hover:text-rose-300 transition-colors truncate">
              {lang === 'id' ? 'Ruang Cinta' : 'Love Space'}
            </h4>
            <span className="text-[10px] text-slate-500">Couple Sync</span>
          </div>
        </button>

        <button
          onClick={() => navigate('guild')}
          className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-amber-500/50 rounded-2xl text-left transition-all group flex items-center gap-3 shadow-sm"
        >
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 group-hover:scale-105 transition-transform shrink-0">
            <Users className="w-5 h-5" />
          </div>
          <div className="truncate">
            <h4 className="font-bold text-xs text-slate-200 group-hover:text-amber-300 transition-colors truncate">
              {lang === 'id' ? 'Guild & PvP' : 'Guild & PvP'}
            </h4>
            <span className="text-[10px] text-slate-500">Boss Raid</span>
          </div>
        </button>

        <button
          onClick={() => navigate('calendar')}
          className="p-3 bg-slate-900/60 hover:bg-slate-900 border border-slate-800 hover:border-cyan-500/50 rounded-2xl text-left transition-all group flex items-center gap-3 shadow-sm col-span-2 sm:col-span-1"
        >
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform shrink-0">
            <CalendarIcon className="w-5 h-5" />
          </div>
          <div className="truncate">
            <h4 className="font-bold text-xs text-slate-200 group-hover:text-cyan-300 transition-colors truncate">
              {lang === 'id' ? 'Kalender' : 'Calendar'}
            </h4>
            <span className="text-[10px] text-slate-500">Holidays / Alarm</span>
          </div>
        </button>
      </div>

      {/* Grid Overview Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Dailies Section */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <CalendarCheck className="w-5 h-5 text-emerald-400" />
                <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Rutinitas Harian (Dailies)' : 'Daily Routine'}</h3>
              </div>
              <button
                onClick={() => navigate('dailies')}
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-colors"
              >
                <span>{lang === 'id' ? 'Lihat Semua' : 'View All'}</span> <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-2">
              {dailies.slice(0, 3).map((daily) => (
                <div
                  key={daily.id}
                  onClick={() => toggleDaily(daily.id)}
                  className={`p-2.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                    daily.isCompletedToday
                      ? 'bg-emerald-950/20 border-emerald-500/30 text-slate-400 line-through'
                      : 'bg-slate-800/60 border-slate-700/60 text-slate-200 hover:border-emerald-500/50'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <input
                      type="checkbox"
                      checked={daily.isCompletedToday}
                      onChange={() => {}}
                      className="w-4 h-4 rounded text-emerald-500 bg-slate-900 border-slate-700 focus:ring-0 pointer-events-none"
                    />
                    <span className="text-xs font-medium truncate">{daily.title}</span>
                  </div>
                  <div className="flex items-center gap-1 text-[11px] font-bold text-amber-400 shrink-0">
                    <Flame className="w-3 h-3 text-amber-500 fill-amber-500" /> {daily.streak}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => navigate('dailies')}
            className="w-full mt-4 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700/80 text-xs font-semibold text-slate-300 transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> {lang === 'id' ? 'Kelola Dailies' : 'Manage Dailies'}
          </button>
        </div>

        {/* Habits Section */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4.5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Habit Tracker' : 'Habit Tracker'}</h3>
              </div>
              <button
                onClick={() => navigate('habits')}
                className="text-xs font-semibold text-amber-400 hover:text-amber-300 flex items-center gap-1 transition-colors"
              >
                <span>{lang === 'id' ? 'Lihat Semua' : 'View All'}</span> <ArrowRight className="w-3 h-3" />
              </button>
            </div>

            <div className="space-y-2">
              {habits.slice(0, 3).map((habit) => (
                <div
                  key={habit.id}
                  className="p-2.5 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between gap-2"
                >
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-slate-200 truncate">{habit.title}</div>
                    <div className="text-[10px] text-slate-400">🔥 Streak: {habit.positiveStreak}</div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {habit.isPositive && (
                      <button
                        onClick={() => triggerHabit(habit.id, true)}
                        className="w-7 h-7 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 font-bold text-xs flex items-center justify-center border border-emerald-500/40 transition-colors"
                        title="+ Positive Action"
                      >
                        +
                      </button>
                    )}
                    {habit.isNegative && (
                      <button
                        onClick={() => triggerHabit(habit.id, false)}
                        className="w-7 h-7 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 font-bold text-xs flex items-center justify-center border border-rose-500/40 transition-colors"
                        title="- Negative Action"
                      >
                        -
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => navigate('habits')}
            className="w-full mt-4 py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700/80 text-xs font-semibold text-slate-300 transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> {lang === 'id' ? 'Kelola Habits' : 'Manage Habits'}
          </button>
        </div>

        {/* Active Boss Encounter */}
        <div className="rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-red-500/30 p-4.5 flex flex-col justify-between shadow-lg">
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Swords className="w-5 h-5 text-red-400" />
                <h3 className="font-bold text-sm text-red-300">{lang === 'id' ? 'Dungeon Boss' : 'Dungeon Boss'}</h3>
              </div>
              {activeBoss && (
                <span className="px-2 py-0.5 text-[10px] font-bold uppercase rounded-full bg-red-500/20 text-red-300 border border-red-500/30">
                  {activeBoss.tier}
                </span>
              )}
            </div>

            {activeBoss ? (
              <div className="space-y-3 text-center">
                <div className="w-14 h-14 mx-auto rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center text-3xl">
                  {activeBoss.icon}
                </div>
                <div>
                  <div className="font-extrabold text-sm text-slate-100">{activeBoss.name}</div>
                  <div className="text-[11px] text-slate-400">Atk: {activeBoss.atk} · Bounty: +{activeBoss.goldReward} Gold</div>
                </div>

                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[10px] font-semibold text-slate-300">
                    <span>Boss HP</span>
                    <span>{activeBossHp} / {activeBoss.maxHp}</span>
                  </div>
                  <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
                    <div
                      className="h-full bg-gradient-to-r from-red-600 to-rose-500 transition-all duration-300"
                      style={{ width: `${Math.max(0, Math.min(100, (activeBossHp / activeBoss.maxHp) * 100))}%` }}
                    />
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-400">
                {lang === 'id' ? 'Tidak ada boss aktif. Pilih boss di Boss Arena!' : 'No active boss. Select one in Boss Arena!'}
              </div>
            )}
          </div>

          <button
            onClick={() => navigate('boss')}
            className="w-full mt-4 py-2 px-3 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-xs font-bold text-red-300 border border-red-500/40 transition-colors flex items-center justify-center gap-1.5"
          >
            <Swords className="w-3.5 h-3.5" /> {lang === 'id' ? 'Masuk Boss Arena' : 'Enter Boss Arena'}
          </button>
        </div>
      </div>

      {/* Bottom Row: Quests, Sport, Water */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Active Quests Preview */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-sky-400" />
              <h4 className="font-bold text-xs text-slate-200">{lang === 'id' ? 'Quests (To-Do)' : 'Quests (To-Do)'}</h4>
            </div>
            <button onClick={() => navigate('quests')} className="text-[11px] text-sky-400 font-semibold hover:underline">
              {lang === 'id' ? 'Buka' : 'Open'}
            </button>
          </div>
          <div className="space-y-1.5">
            {pendingQuests.length > 0 ? (
              pendingQuests.slice(0, 3).map((q) => (
                <div
                  key={q.id}
                  onClick={() => toggleQuest(q.id)}
                  className="p-2 rounded-lg bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/50 flex items-center justify-between text-xs cursor-pointer transition-colors"
                >
                  <span className="truncate">{q.title}</span>
                  <span className="text-[10px] text-amber-400 font-bold uppercase ml-2">{q.difficulty}</span>
                </div>
              ))
            ) : (
              <div className="text-xs text-slate-400 text-center py-4">
                {lang === 'id' ? 'Semua quest selesai! 🏆' : 'All quests completed! 🏆'}
              </div>
            )}
          </div>
        </div>

        {/* Workout Progress Preview */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-rose-400" />
              <h4 className="font-bold text-xs text-slate-200">{lang === 'id' ? 'SportTrack' : 'SportTrack'}</h4>
            </div>
            <button onClick={() => navigate('sport')} className="text-[11px] text-rose-400 font-semibold hover:underline">
              {lang === 'id' ? 'Buka' : 'Open'}
            </button>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{lang === 'id' ? 'Sport Level' : 'Sport Level'}:</span>
              <span className="font-bold text-rose-400">Lv. {user.sportLevel}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{lang === 'id' ? 'Sesi Latihan' : 'Total Sessions'}:</span>
              <span className="font-bold text-slate-200">{sportLogs.length}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">{lang === 'id' ? 'Kalori Masuk Hari Ini' : 'Calories Eaten'}:</span>
              <span className="font-bold text-amber-400">{totalCaloriesToday} kcal</span>
            </div>
          </div>
        </div>

        {/* Water Hydration */}
        <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Droplets className="w-4 h-4 text-cyan-400" />
              <h4 className="font-bold text-xs text-slate-200">{lang === 'id' ? 'Hidrasi Air' : 'Water Hydration'}</h4>
            </div>
            <button onClick={() => navigate('nutrition')} className="text-[11px] text-cyan-400 font-semibold hover:underline">
              {lang === 'id' ? 'Buka' : 'Open'}
            </button>
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-center justify-between text-slate-300">
              <span>{waterLog.amountMl} ml / {waterLog.targetMl} ml</span>
              <span className="font-bold text-cyan-400">{Math.round((waterLog.amountMl / waterLog.targetMl) * 100)}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300"
                style={{ width: `${Math.min(100, (waterLog.amountMl / waterLog.targetMl) * 100)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {widgetsOpen && <DashboardWidgetsDialog onClose={() => setWidgetsOpen(false)} />}
      {wrappedOpen && <YearWrappedDialog onClose={() => setWrappedOpen(false)} displayName={user.displayName || user.username} />}
    </div>
  );
};
