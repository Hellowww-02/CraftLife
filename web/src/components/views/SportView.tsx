import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { SPORT_TYPES, SPORT_INTENSITY_FACTOR } from '../../data/gameData';
import { t } from '../../i18n';
import { Activity, Plus, Flame, Timer, Trash2, Dumbbell, Award, TrendingUp, X, Pencil } from 'lucide-react';
import { BarChart } from '../charts';
import { TaskDifficulty } from '../../types';

// Parity SPORT_RANK_COLORS (MainPyQt6.py)
const SPORT_RANK_COLORS: Record<string, string> = {
  rookie: '#9aa0a6', bronze: '#cd7f32', silver: '#c0c0c0',
  gold: '#f0c040', platinum: '#4dd9e0', diamond: '#6fb7ff',
  master: '#a97fff', mythic: '#ff6fd8',
};

interface SportFormState {
  id: string | null;
  name: string;
  sportType: string;
  difficulty: TaskDifficulty;
  weight: number;
  duration: number;
  autoCalc: boolean;
  calories: number;
  notes: string;
}

const DIFFICULTIES: TaskDifficulty[] = ['easy', 'medium', 'hard', 'epic'];

export const SportView: React.FC = () => {
  const { user, sportLogs, addSportLog, updateSportLog, completeSportLog, deleteSportLog, lang, applyTaskTemplate, showToast } = useGame();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form state (parity AddSportActivityDialog PyQt)
  const [form, setForm] = useState<SportFormState>({
    id: null, name: '', sportType: 'running', difficulty: 'medium',
    weight: 65.0, duration: 30, autoCalc: true, calories: 100, notes: '',
  });

  // Prefill berat: default 65 kg, ditimpa health_log terakhir (parity PyQt).
  useEffect(() => {
    if (!isModalOpen) return;
    life.dashboardSummary()
      .then((d) => {
        const w = Number(d?.weightKg);
        if (w > 0 && !form.id) setForm((f) => ({ ...f, weight: w }));
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isModalOpen]);

  const met = SPORT_TYPES.find((s) => s.id === form.sportType)?.met ?? 4.0;
  const factor = SPORT_INTENSITY_FACTOR[form.difficulty] ?? 1.0;
  // Parity _calc_calories: MET × berat(kg) × jam × faktor intensitas.
  const autoCalories = Math.round(met * form.weight * (form.duration / 60) * factor);
  const calories = form.autoCalc ? autoCalories : form.calories;
  const kcalPerMin = form.duration > 0 ? calories / form.duration : 0;

  const openAdd = () => {
    setForm({ id: null, name: '', sportType: 'running', difficulty: 'medium', weight: 65.0, duration: 30, autoCalc: true, calories: 100, notes: '' });
    setIsModalOpen(true);
  };

  const openEdit = (log: any) => {
    setForm({
      id: String(log.id),
      name: log.sportName || '',
      sportType: SPORT_TYPES.some((s) => s.id === log.sportType) ? log.sportType : 'other',
      difficulty: (['easy', 'medium', 'hard', 'epic'].includes(String(log.difficulty)) ? log.difficulty : log.intensity === 'light' ? 'easy' : log.intensity === 'vigorous' ? 'hard' : 'medium') as TaskDifficulty,
      weight: 65.0,
      duration: Number(log.durationMinutes) || 30,
      autoCalc: false,
      calories: Number(log.caloriesBurned) || 0,
      notes: log.notes || '',
    });
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim()) {
      showToast('info', lang === 'id' ? 'Nama aktivitas kosong' : 'Empty activity name', '');
      return;
    }
    const body = {
      sportType: form.sportType,
      sportName: form.name.trim(),
      icon: SPORT_TYPES.find((s) => s.id === form.sportType)?.icon || '🏅',
      durationMinutes: form.duration,
      caloriesBurned: calories,
      difficulty: form.difficulty,
      intensity: form.difficulty === 'easy' ? 'light' : form.difficulty === 'medium' ? 'moderate' : 'vigorous',
      notes: form.notes,
    } as const;
    if (form.id) {
      updateSportLog(form.id, {
        name: form.name.trim(),
        sportType: form.sportType,
        difficulty: form.difficulty,
        notes: form.notes,
        caloriesBurned: calories,
        durationMinutes: form.duration,
      });
    } else {
      addSportLog(body.sportType, body.sportName, body.icon, body.durationMinutes, body.caloriesBurned, body.intensity as any, body.notes, body.difficulty);
    }
    setIsModalOpen(false);
  };

  const totalCaloriesBurned = sportLogs.reduce((acc, log) => acc + log.caloriesBurned, 0);
  const totalMinutes = sportLogs.reduce((acc, log) => acc + log.durationMinutes, 0);

  const nextSportLvlSp = user.sportLevel * 100; // parity: sport_need = sport_level*100
  const sportXpPct = Math.min(100, Math.round((user.sportXp / Math.max(1, nextSportLvlSp)) * 100));

  // ---- Reps (parity LogSportRepsDialog + SportRepsChartWidget PyQt) ----
  const [repsSummary, setRepsSummary] = useState<any>(null);
  const [repsModal, setRepsModal] = useState<{ open: boolean; activity: any }>({ open: false, activity: null });
  const [repSets, setRepSets] = useState(1);
  const [repReps, setRepReps] = useState(10);
  const [repNote, setRepNote] = useState('');
  const [repInfo, setRepInfo] = useState<any>(null);

  useEffect(() => {
    life.sportRepsSummary().then((d) => setRepsSummary(d?.activities || [])).catch(() => setRepsSummary([]));
  }, [sportLogs.length]);

  const openReps = async (activity: any) => {
    setRepsModal({ open: true, activity });
    setRepSets(1); setRepReps(10); setRepNote(''); setRepInfo(null);
    try {
      const info = await life.sportRepsInfo(activity.id);
      if (info?.ok === false) { setRepInfo({ total: 0, rank: { key: 'rookie', icon: '🌱' }, history: [] }); }
      else setRepInfo(info);
    } catch {
      setRepInfo({ total: 0, rank: { key: 'rookie', icon: '🌱' }, history: [] });
    }
  };

  const submitReps = async () => {
    if (!repsModal.activity || repReps <= 0) return;
    const res = await life.sportReps(repsModal.activity.id, repReps, repSets);
    if (res?.result?.ok === false) {
      showToast('info', String(res.result.code || 'error'), '');
      return;
    }
    const logged = repSets * repReps;
    const newTotal = Number(res?.result?.total_reps) || 0;
    showToast('success', t('sport_reps_logged', '💪 +{reps} reps! (total: {total})').replace('{reps}', String(logged)).replace('{total}', String(newTotal)), '');
    try {
      const info = await life.sportRepsInfo(repsModal.activity.id);
      setRepInfo(info);
    } catch { /* ignore */ }
    life.sportRepsSummary().then((d) => setRepsSummary(d?.activities || [])).catch(() => undefined);
    if (res?.result && res.result.rank_up) {
      const key = String(res.result.rank_after?.key || 'rookie');
      showToast('level_up', t('sport_rank_up', '🏆 Rank UP! Kamu sekarang {rank}!').replace('{rank}', t('sport_rank_' + key, key)), '');
    }
  };

  // Agregasi chart reps 7 hari (parity SportRepsChartWidget: bar harian zero-fill).
  const repSeriesByDate = new Map<string, number>();
  (repsSummary || []).forEach((a: any) => (a.series || []).forEach((s: any) => {
    repSeriesByDate.set(s.date, (repSeriesByDate.get(s.date) || 0) + Number(s.reps || 0));
  }));
  const repChartData = [...repSeriesByDate.entries()].sort((x, y) => (x[0] < y[0] ? -1 : 1)).map(([date, value]) => ({ label: date.slice(5), value }));
  const totalRepsAll = (repsSummary || []).reduce((acc: number, a: any) => acc + Number(a.totalReps || 0), 0);

  const rankKeyOf = (rank: any) => String(rank?.key || 'rookie');
  const rankColorOf = (rank: any) => SPORT_RANK_COLORS[rankKeyOf(rank)] || '#9aa0a6';

  return (
    <div className="space-y-6">
      {/* Header & Sport Level Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/30 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-6 h-6 text-rose-400" />
              <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Pelacak Olahraga & Kebugaran' : 'Sport & Workout Tracker'}</h2>
            </div>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Catat sesi latihan harianmu, bakar kalori, naikkan Sport Level, dan perkuat karakter RPG-mu!'
                : 'Log workouts, burn calories, level up your Sport Mastery, and enhance your overall character endurance!'}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-800">
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Total Sesi' : 'Workouts'}</div>
              <div className="text-base font-extrabold text-slate-200">{sportLogs.length}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Total Durasi' : 'Duration'}</div>
              <div className="text-base font-extrabold text-rose-400">{totalMinutes} m</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{lang === 'id' ? 'Kalori Terbakar' : 'Calories'}</div>
              <div className="text-base font-extrabold text-amber-400">{totalCaloriesBurned} kcal</div>
            </div>
          </div>
        </div>

        {/* Sport Level Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{lang === 'id' ? 'Tingkat Kebugaran' : 'Sport Mastery'}</span>
              <Award className="w-5 h-5 text-rose-400" />
            </div>
            <div className="text-2xl font-black text-rose-400 mt-2">Level {user.sportLevel}</div>
            <div className="text-xs text-slate-400 mt-1">
              {user.sportXp} / {nextSportLvlSp} Sport XP ({sportXpPct}%)
            </div>
          </div>

          <div className="space-y-2 mt-4">
            <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
              <div
                className="h-full bg-gradient-to-r from-rose-500 to-amber-500 transition-all duration-300"
                style={{ width: `${sportXpPct}%` }}
              />
            </div>
            <button
              onClick={openAdd}
              className="w-full py-2 px-3 rounded-xl bg-rose-500 hover:bg-rose-400 text-slate-950 font-bold text-xs shadow-lg shadow-rose-500/20 transition-all flex items-center justify-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> {lang === 'id' ? 'Catat Sesi Latihan' : 'Log Workout'}
            </button>
          </div>
        </div>
      </div>

      {/* Reps Chart (parity SportRepsChartWidget — bar harian 7 hari) */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-sky-400" />
            <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Grafik Reps' : 'Reps Chart'}</h3>
          </div>
          <div className="text-xs text-slate-400">{lang === 'id' ? 'Total reps' : 'Total reps'}: <span className="text-sky-300 font-bold">{totalRepsAll}</span></div>
        </div>
        {repChartData.length === 0 ? (
          <p className="text-sm text-slate-500 text-center py-6">{lang === 'id' ? 'Belum ada sesi reps. Catat set×reps lewat tombol “Reps”.' : 'No rep sessions yet. Log sets×reps via the "Reps" button.'}</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[420px]">
              <BarChart data={repChartData} color="#38bdf8" width={680} height={170} />
            </div>
          </div>
        )}
      </div>

      {/* Kartu aktivitas (parity _build_card_content SportTrackPage PyQt) */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Aktivitas Olahraga' : 'Sport Activities'}</h3>
          <button
            type="button"
            onClick={() => applyTaskTemplate('sport', 'running_starter_s')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 text-[11px] font-bold text-slate-200"
          >
            {lang === 'id' ? 'Template PyQt' : 'PyQt templates'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sportLogs.map((log: any) => {
            const cals = Number(log.caloriesBurned) || 0;
            const dur = Number(log.durationMinutes) || 0;
            const kpm = dur > 0 ? cals / dur : 0;
            const metChip = (SPORT_TYPES.find((s) => s.id === log.sportType)?.met ?? 4.0).toFixed(1);
            const streakTxt = Number(log.streak) > 0 ? t('task_streak_days', '🔥 {streak} hari').replace('{streak}', String(log.streak)) : '';
            return (
              <div
                key={log.id}
                className={`p-4 rounded-2xl bg-slate-900/80 border flex flex-col gap-2 ${log.done ? 'border-emerald-600/40 opacity-80' : 'border-slate-800'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="w-11 h-11 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xl shrink-0">
                      {log.icon}
                    </div>
                    <div className="min-w-0">
                      <h4 className={`font-bold text-sm truncate ${log.done ? 'line-through text-slate-500' : 'text-slate-100'}`}>{log.sportName}</h4>
                      <div className="text-[11px] text-amber-400 font-bold mt-0.5">
                        {t('sport_type_' + log.sportType, log.sportType)}
                        <span className="text-slate-400">  ·  +{Number(log.xpReward) || 0} XP  ·  +{Number(log.goldReward) || 0} G  ·  +{Number(log.sportPointsReward) || 0} SP  {streakTxt}</span>
                      </div>
                    </div>
                  </div>
                  <span className={`shrink-0 px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 capitalize ${
                    log.difficulty === 'epic' ? 'text-purple-300' : log.difficulty === 'hard' ? 'text-rose-300' : log.difficulty === 'medium' ? 'text-amber-300' : 'text-emerald-300'
                  }`}>
                    {t('task_difficulty_' + (log.difficulty || 'medium'), log.difficulty || 'medium')}
                  </span>
                </div>

                {/* Professional Calorie Row (parity FIX 7) */}
                {cals > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-orange-400 font-bold text-[11px] bg-orange-500/10 rounded-md px-2 py-0.5">🔥 {cals} kcal</span>
                    {dur > 0 && <span className="text-slate-500 text-[10px] flex items-center gap-1"><Timer className="w-3 h-3" /> {dur} min • {kpm.toFixed(1)} kcal/min</span>}
                    <span className="text-slate-500 text-[10px] bg-slate-800 rounded-md px-2 py-0.5">MET {metChip}</span>
                    {Number(log.totalReps) > 0 && <span className="text-sky-300 text-[10px] bg-sky-500/10 rounded-md px-2 py-0.5">💪 {log.totalReps} reps</span>}
                  </div>
                )}

                {log.notes && <p className="text-xs text-slate-400">{log.notes}</p>}

                <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                  <button
                    onClick={() => openReps(log)}
                    className="px-2 py-1 rounded-lg bg-sky-500/20 text-sky-300 text-[10px] font-bold"
                  >
                    Reps
                  </button>
                  {!log.done && (
                    <>
                      <button
                        onClick={() => completeSportLog(log.id)}
                        className="px-2 py-1 rounded-lg bg-rose-500/20 text-rose-300 text-[10px] font-bold"
                      >
                        {lang === 'id' ? 'Selesai +XP' : 'Complete +XP'}
                      </button>
                      <button
                        type="button"
                        onClick={() => openEdit(log)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors"
                        title="Edit"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={() => life.duplicateSport(log.id).then(() => life.sportRepsSummary().catch(() => undefined)).catch(() => undefined)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-sky-300 text-[10px] font-bold"
                    title="Duplicate"
                  >
                    Dup
                  </button>
                  <button
                    onClick={() => deleteSportLog(log.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-auto"
                    title="Delete"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {sportLogs.length === 0 && (
          <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
            <Dumbbell className="w-8 h-8 text-rose-500/40 mx-auto mb-2" />
            <p className="text-sm font-semibold">{lang === 'id' ? 'Belum ada catatan olahraga.' : 'No workouts logged yet.'}</p>
          </div>
        )}
      </div>

      {/* Modal Tambah/Edit (parity AddSportActivityDialog) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-black text-slate-100">
              {form.id ? (lang === 'id' ? 'Edit Aktivitas Olahraga' : 'Edit Sport Activity') : (lang === 'id' ? 'Catat Aktivitas Olahraga' : 'Log Sport Session')}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nama aktivitas' : 'Activity name'}</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder={t('sport_activity_ph', 'Contoh: Lari pagi 5 km…')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-2">{lang === 'id' ? 'Jenis Olahraga' : 'Sport Type'}</label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 max-h-40 overflow-y-auto pr-1">
                  {SPORT_TYPES.map((st) => (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, sportType: st.id }))}
                      className={`p-2 rounded-xl border flex flex-col items-center text-center transition-all ${
                        form.sportType === st.id
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-sm'
                          : 'bg-slate-800/60 text-slate-300 border-slate-700 hover:bg-slate-800'
                      }`}
                    >
                      <span className="text-xl mb-1">{st.icon}</span>
                      <span className="text-[10px] font-semibold leading-tight line-clamp-1">{t('sport_type_' + st.id, st.name)}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Tingkat Kesulitan' : 'Difficulty'}</label>
                  <select
                    value={form.difficulty}
                    onChange={(e) => setForm((f) => ({ ...f, difficulty: e.target.value as TaskDifficulty }))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                  >
                    {DIFFICULTIES.map((d) => (
                      <option key={d} value={d}>{t('task_difficulty_' + d, d)}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Berat Badan (kg)' : 'Body Weight (kg)'}</label>
                  <input
                    type="number"
                    min={30}
                    max={200}
                    step={0.5}
                    value={form.weight}
                    onChange={(e) => setForm((f) => ({ ...f, weight: Number(e.target.value) || 65 }))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Durasi (Menit)' : 'Duration (mins)'}</label>
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={form.duration}
                  onChange={(e) => setForm((f) => ({ ...f, duration: Math.max(1, Number(e.target.value) || 1) }))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={form.autoCalc}
                  onChange={(e) => setForm((f) => ({ ...f, autoCalc: e.target.checked }))}
                  className="w-4 h-4 rounded text-rose-500 bg-slate-900 border-slate-700"
                />
                <span className="text-slate-300">✨ {lang === 'id' ? 'Hitung otomatis (MET × berat × durasi × intensitas)' : 'Auto-calculate (MET × weight × duration × intensity)'}</span>
              </label>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 text-center text-xs">
                {form.autoCalc ? (
                  <span className="font-extrabold text-amber-400 flex items-center justify-center gap-1">
                    <Flame className="w-4 h-4" /> {calories} kcal • {kcalPerMin.toFixed(1)} kcal/min • MET {met.toFixed(1)} × {factor.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-slate-300">✏️ {lang === 'id' ? 'Manual' : 'Manual'}: {form.calories} kcal</span>
                )}
              </div>

              <div className="flex items-center justify-between gap-2">
                <label className="text-slate-300 font-semibold">{t('sport_calories_label', 'Perkiraan Kalori Terbakar (kcal)')}</label>
                <input
                  type="number"
                  min={0}
                  max={5000}
                  value={calories}
                  disabled={form.autoCalc}
                  onChange={(e) => setForm((f) => ({ ...f, calories: Math.max(0, Number(e.target.value) || 0) }))}
                  className={`w-28 px-3 py-2 rounded-xl border text-center font-bold focus:outline-none ${
                    form.autoCalc
                      ? 'bg-slate-900 border-slate-800 text-amber-300'
                      : 'bg-slate-800 border-slate-700 text-slate-100 focus:border-rose-500'
                  }`}
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan' : 'Notes'}</label>
                <input
                  type="text"
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder="e.g. 5km morning loop, 4 sets pullups"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                />
              </div>

              <p className="text-[10px] text-slate-500 italic">💡 {lang === 'id' ? 'Rumus: Kalori = MET × Berat(kg) × Durasi(jam) × Faktor Intensitas' : 'Formula: Calories = MET × Weight(kg) × Duration(hrs) × Intensity factor'}</p>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-400 text-slate-950 font-bold"
                >
                  {form.id ? t('dialog_save', '💾 Simpan') : t('dialog_add', '➕  Tambah')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LogSportReps Dialog (parity LogSportRepsDialog PyQt) */}
      {repsModal.open && repsModal.activity && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">
                {lang === 'id' ? 'Catat Sesi Reps' : 'Log Reps'} — {repsModal.activity.sportName || repsModal.activity.name}
              </h3>
              <button onClick={() => setRepsModal({ open: false, activity: null })} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            {repInfo && (
              <p className="text-xs font-bold" style={{ color: rankColorOf(repInfo.rank) }}>
                {repInfo.rank?.icon || '⭐'} {t('sport_rank_' + rankKeyOf(repInfo.rank), rankKeyOf(repInfo.rank))}{' '}
                · {t('sport_reps_total_label', 'Total: {n} reps').replace('{n}', String(repInfo.total ?? 0))}
              </p>
            )}

            <div className="flex gap-2 flex-wrap">
              {[5, 10, 25, 50].map((n) => (
                <button key={n} onClick={() => setRepReps((v) => v + n)} className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 text-xs font-bold hover:bg-slate-700">
                  +{n}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <div className="flex-1">
                <label className="block text-slate-400 text-[10px] font-bold">{t('sport_log_reps_sets', 'Set')}</label>
                <input type="number" min={1} max={50} value={repSets} onChange={(e) => setRepSets(Math.max(1, Math.min(50, Number(e.target.value) || 1)))} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />
              </div>
              <span className="text-slate-500 text-lg font-bold">×</span>
              <div className="flex-1">
                <label className="block text-slate-400 text-[10px] font-bold">{t('sport_log_reps_reps', 'Reps')}</label>
                <input type="number" min={1} max={1000} value={repReps} onChange={(e) => setRepReps(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />
              </div>
              <div className="text-sky-300 font-black text-xl">{repSets * repReps}</div>
            </div>

            <input value={repNote} onChange={(e) => setRepNote(e.target.value)} placeholder={lang === 'id' ? 'Catatan…' : 'Note…'} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />

            {repInfo && repInfo.history && repInfo.history.length > 0 && (
              <div className="space-y-1">
                {repInfo.history.map((h: any, i: number) => (
                  <p key={i} className="text-[10px] text-slate-500">💪 {h.reps} reps ×{h.sets} set · {h.log_date}{h.note ? ` — ${h.note}` : ''}</p>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setRepsModal({ open: false, activity: null })} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{lang === 'id' ? 'Batal' : 'Cancel'}</button>
              <button onClick={submitReps} disabled={repReps <= 0} className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-slate-950 font-bold text-xs">{t('dialog_save', '💾 Simpan')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
