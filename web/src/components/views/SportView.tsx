import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { SPORT_TYPES, SPORT_INTENSITY_FACTOR } from '../../data/gameData';
import { t } from '../../i18n';
import { Activity, Plus, Flame, Timer, Trash2, Dumbbell, Award, TrendingUp, X, Pencil, FolderOpen } from 'lucide-react';
import { BarChart } from '../charts';
import { TaskDifficulty } from '../../types';
import { TaskFolderBar, filterByFolder, useModeFolders } from '../TaskFolderBar';
import { useTaskReorder } from '../../hooks/useTaskReorder';

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
  const { user, sportLogs, addSportLog, updateSportLog, completeSportLog, deleteSportLog, reorderSportLogs, moveTaskAcrossFolders, applyTaskTemplate, showToast } = useGame();
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
      showToast('info', t('sport_empty_activity', 'Nama aktivitas kosong'), '');
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
  const [repsSummary, setRepsSummary] = useState<{ activities: any[]; series: any[] }>({ activities: [], series: [] });
  const [repsModal, setRepsModal] = useState<{ open: boolean; activity: any }>({ open: false, activity: null });
  const [repSets, setRepSets] = useState(1);
  const [repReps, setRepReps] = useState(10);
  const [repNote, setRepNote] = useState('');
  const [repInfo, setRepInfo] = useState<any>(null);

  const refreshRepsSummary = () => {
    life.sportRepsSummary()
      .then((d) => setRepsSummary({ activities: d?.activities || [], series: d?.series || [] }))
      .catch(() => setRepsSummary({ activities: [], series: [] }));
  };

  useEffect(() => {
    refreshRepsSummary();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    // Parity LogSportRepsDialog._save: `reps` yang dicatat = SETS × REPS (total),
    // bukan reps per-set. PyQt memanggil add_sport_rep_log(uid, id, self._total(), sets).
    const totalReps = repSets * repReps;
    const res = await life.sportReps(repsModal.activity.id, totalReps, repSets);
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
    refreshRepsSummary();
    if (res?.result && res.result.rank_up) {
      const key = String(res.result.rank_after?.key || 'rookie');
      showToast('level_up', t('sport_rank_up', '🏆 Rank UP! Kamu sekarang {rank}!').replace('{rank}', t('sport_rank_' + key, key)), '');
    }
  };

  // Chart reps 7 hari (parity SportRepsChartWidget PyQt: db.get_sport_rep_series → bar harian zero-fill global).
  const repChartData = (repsSummary.series || []).map((s: any) => ({ label: String(s.date || '').slice(5), value: Number(s.reps || 0) }));
  const hasRepData = repChartData.some((p) => p.value > 0);
  const totalRepsAll = (repsSummary.activities || []).reduce((acc: number, a: any) => acc + Number(a.totalReps || 0), 0);

  const rankKeyOf = (rank: any) => String(rank?.key || 'rookie');
  const rankColorOf = (rank: any) => SPORT_RANK_COLORS[rankKeyOf(rank)] || '#9aa0a6';

  // ---- Folder (parity SportTrackPage: db.get_task_folders(uid, "sport") + FolderWidget) ----
  const [selectedFolderFilter, setSelectedFolderFilter] = useState<string>('all');
  const sportFolders = useModeFolders('sport');
  const filteredSports = filterByFolder(sportLogs, selectedFolderFilter);
  const drag = useTaskReorder(sportLogs, filteredSports, reorderSportLogs);

  return (
    <div className="space-y-6">
      {/* Header & Sport Level Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-2xl bg-gradient-to-r from-rose-950/40 via-slate-900 to-slate-900 border border-rose-500/30 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Activity className="w-6 h-6 text-rose-400" />
              <h2 className="text-xl font-black text-slate-100">{t('page_sport_title', 'Sport & Workout Tracker')}</h2>
            </div>
            <p className="text-xs text-slate-400">
              {t('page_sport_subtitle', 'Catat sesi latihan harianmu, bakar kalori, naikkan Sport Level, dan perkuat karakter RPG-mu!')}
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t border-slate-800">
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{t('sport_total_sessions', 'Workouts')}</div>
              <div className="text-base font-extrabold text-slate-200">{sportLogs.length}</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{t('sport_total_duration', 'Duration')}</div>
              <div className="text-base font-extrabold text-rose-400">{totalMinutes} m</div>
            </div>
            <div>
              <div className="text-[10px] text-slate-400 font-bold uppercase">{t('sport_calories_burned', 'Calories')}</div>
              <div className="text-base font-extrabold text-amber-400">{totalCaloriesBurned} kcal</div>
            </div>
          </div>
        </div>

        {/* Sport Level Card */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{t('sport_mastery', 'Sport Mastery')}</span>
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
              <Plus className="w-4 h-4" /> {t('sport_log_workout', 'Log Workout')}
            </button>
          </div>
        </div>
      </div>

      {/* Reps Chart (parity SportRepsChartWidget — bar harian 7 hari) */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-sky-400" />
            <h3 className="font-bold text-sm text-slate-200">{t('sport_reps_chart', 'Reps Chart')}</h3>
          </div>
          <div className="text-xs text-slate-400">{t('sport_total_reps_label', 'Total reps')}: <span className="text-sky-300 font-bold">{totalRepsAll}</span></div>
        </div>
        {!hasRepData ? (
          <p className="text-sm text-slate-500 text-center py-6">{t('sport_reps_empty', 'Belum ada sesi reps. Catat set×reps lewat tombol "Reps".')}</p>
        ) : (
          <div className="overflow-x-auto">
            <div className="min-w-[420px]">
              <BarChart data={repChartData} color="#38bdf8" />
            </div>
          </div>
        )}
      </div>

      {/* Kartu aktivitas (parity _build_card_content SportTrackPage PyQt) */}
      <div className="space-y-3">
        <TaskFolderBar
          mode="sport"
          selected={selectedFolderFilter}
          onSelect={setSelectedFolderFilter}
          accent="bg-sky-500/20 text-sky-300 border border-sky-500/40"
          allLabel={t('sport_filter_all', 'All')}
          allCount={sportLogs.length}
          onDropInto={(fid) => {
            const idx = drag.dragIndex;
            if (idx === null) return;
            const it = filteredSports[idx];
            if (it) moveTaskAcrossFolders('sport', it.id, fid);
          }}
        />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-sm text-slate-200">{t('sport_activities_title', 'Aktivitas Olahraga')}</h3>
          <button
            type="button"
            onClick={() => applyTaskTemplate('sport', 'running_starter_s')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 text-[11px] font-bold text-slate-200"
          >
            {t('sport_pyqt_templates', 'Template PyQt')}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {filteredSports.map((log: any, idx: number) => {
            const folder = sportFolders.find((f) => f.id === log.folderId);
            const cals = Number(log.caloriesBurned) || 0;
            const dur = Number(log.durationMinutes) || 0;
            const kpm = dur > 0 ? cals / dur : 0;
            const metChip = (SPORT_TYPES.find((s) => s.id === log.sportType)?.met ?? 4.0).toFixed(1);
            const streakTxt = Number(log.streak) > 0 ? t('task_streak_days', '🔥 {streak} hari').replace('{streak}', String(log.streak)) : '';
            return (
              <div
                key={log.id}
                draggable
                onDragStart={drag.onDragStart(idx, 'list')}
                onDragOver={(e) => drag.onDragOver(e, idx)}
                onDragEnter={() => drag.onDragEnter(idx)}
                onDrop={(e) => drag.onDrop(e, idx)}
                onDragEnd={drag.onDragEnd}
                className={`p-4 rounded-2xl bg-slate-900/80 border flex flex-col gap-2 transition-all cursor-grab ${
                  drag.isDragging(idx)
                    ? 'opacity-40 border-amber-500'
                    : drag.isOver(idx)
                      ? 'border-amber-500/70'
                      : log.done ? 'border-emerald-600/40 opacity-80' : 'border-slate-800 hover:border-slate-700'
                }`}
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
                  <div className="flex items-center gap-1.5 shrink-0">
                    {folder && (
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1 bg-slate-800 rounded-md px-2 py-0.5">
                        <span>{folder.icon}</span> {folder.name}
                      </span>
                    )}
                    <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 capitalize ${
                      log.difficulty === 'epic' ? 'text-purple-300' : log.difficulty === 'hard' ? 'text-rose-300' : log.difficulty === 'medium' ? 'text-amber-300' : 'text-emerald-300'
                    }`}>
                      {t('task_difficulty_' + (log.difficulty || 'medium'), log.difficulty || 'medium')}
                    </span>
                  </div>
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
                        {t('sport_complete_xp', 'Selesai +XP')}
                      </button>
                      <button
                        type="button"
                        onClick={() => openEdit(log)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-amber-300 hover:bg-amber-500/10 transition-colors"
                        title={t('task_edit_title', 'Edit')}
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </button>
                    </>
                  )}
                  <button
                    type="button"
                    onClick={() => life.duplicateSport(log.id).then(() => life.sportRepsSummary().catch(() => undefined)).catch(() => undefined)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-sky-300 text-[10px] font-bold"
                    title={t('task_duplicate_title', 'Duplicate')}
                  >
                    Dup
                  </button>
                  <button
                    onClick={() => deleteSportLog(log.id)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors ml-auto"
                    title={t('task_delete_title', 'Delete')}
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {filteredSports.length === 0 && (
          <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
            <Dumbbell className="w-8 h-8 text-rose-500/40 mx-auto mb-2" />
            <p className="text-sm font-semibold">
              {sportLogs.length === 0
                ? t('sport_no_logs_yet', 'Belum ada catatan olahraga.')
                : t('folder_empty', 'Folder kosong')}
            </p>
          </div>
        )}

        {/* Drop area "keluar dari folder" (parity drop_here_to_remove_folder PyQt) */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const idx = drag.dragIndex;
            if (idx === null) return;
            const it = filteredSports[idx];
            if (it) moveTaskAcrossFolders('sport', it.id, null);
          }}
          className="flex items-center justify-center gap-2 mt-1 rounded-xl border-2 border-dashed border-slate-700/70 hover:border-sky-500/60 hover:bg-slate-900/60 transition-colors py-3 text-slate-500 text-xs font-semibold cursor-pointer"
        >
          <FolderOpen className="w-4 h-4" />
          {t('drop_here_to_remove_folder', '📂 Taruh di sini untuk keluarkan dari folder')}
        </div>
      </div>

      {/* Modal Tambah/Edit (parity AddSportActivityDialog) */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-black text-slate-100">
              {form.id ? t('sport_edit_title', 'Edit Aktivitas Olahraga') : t('sport_log_session_title', 'Catat Aktivitas Olahraga')}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('sport_activity_name', 'Nama aktivitas')}</label>
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
                <label className="block text-slate-300 font-semibold mb-2">{t('sport_type_label', 'Jenis Olahraga')}</label>
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
                  <label className="block text-slate-300 font-semibold mb-1">{t('sport_difficulty_label', 'Tingkat Kesulitan')}</label>
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
                  <label className="block text-slate-300 font-semibold mb-1">{t('sport_weight_label', 'Berat Badan (kg)')}</label>
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
                <label className="block text-slate-300 font-semibold mb-1">{t('sport_duration', 'Durasi (menit)')}</label>
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
                <span className="text-slate-300">✨ {t('sport_auto_calc', 'Hitung otomatis (MET × berat × durasi × intensitas)')}</span>
              </label>

              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 text-center text-xs">
                {form.autoCalc ? (
                  <span className="font-extrabold text-amber-400 flex items-center justify-center gap-1">
                    <Flame className="w-4 h-4" /> {calories} kcal • {kcalPerMin.toFixed(1)} kcal/min • MET {met.toFixed(1)} × {factor.toFixed(2)}
                  </span>
                ) : (
                  <span className="text-slate-300">✏️ {t('sport_manual', 'Manual')}: {form.calories} kcal</span>
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
                <label className="block text-slate-300 font-semibold mb-1">{t('sport_notes_label', 'Catatan')}</label>
                <input
                  type="text"
                  value={form.notes}
                  onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                  placeholder={t('sport_notes_ph', 'e.g. 5km morning loop, 4 sets pullups')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                />
              </div>

              <p className="text-[10px] text-slate-500 italic">💡 {t('sport_formula', 'Rumus: Kalori = MET × Berat(kg) × Durasi(jam) × Faktor Intensitas')}</p>

              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {t('sport_cancel', 'Batal')}
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
                {t('sport_reps_session_title', 'Catat Sesi Reps')} — {repsModal.activity.sportName || repsModal.activity.name}
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

            <input value={repNote} onChange={(e) => setRepNote(e.target.value)} placeholder={t('sport_reps_note_ph', 'Catatan…')} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />

            {repInfo && repInfo.history && repInfo.history.length > 0 && (
              <div className="space-y-1">
                {repInfo.history.map((h: any, i: number) => (
                  <p key={i} className="text-[10px] text-slate-500">💪 {h.reps} reps ×{h.sets} set · {h.log_date}{h.note ? ` — ${h.note}` : ''}</p>
                ))}
              </div>
            )}

            <div className="flex items-center justify-end gap-2">
              <button onClick={() => setRepsModal({ open: false, activity: null })} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">{t('sport_cancel', 'Batal')}</button>
              <button onClick={submitReps} disabled={repReps <= 0} className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-slate-950 font-bold text-xs">{t('dialog_save', '💾 Simpan')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
