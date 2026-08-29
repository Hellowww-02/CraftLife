import React, { useState, useEffect } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { SPORT_TYPES } from '../../data/gameData';
import { Activity, Plus, Flame, Timer, Trash2, Dumbbell, Award, TrendingUp, X } from 'lucide-react';
import { LineChart } from '../charts';

export const SportView: React.FC = () => {
  const { user, sportLogs, addSportLog, completeSportLog, deleteSportLog, lang, applyTaskTemplate, showToast } = useGame();
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State
  const [selectedSportId, setSelectedSportId] = useState(SPORT_TYPES[0].id);
  const [duration, setDuration] = useState<number>(30);
  const [intensity, setIntensity] = useState<'light' | 'moderate' | 'vigorous'>('moderate');
  const [customNotes, setCustomNotes] = useState('');

  const selectedSport = SPORT_TYPES.find((s) => s.id === selectedSportId) || SPORT_TYPES[0];

  // Dynamic calorie computation
  const getIntensityMultiplier = (level: 'light' | 'moderate' | 'vigorous') => {
    switch (level) {
      case 'light':
        return 0.8;
      case 'moderate':
        return 1.0;
      case 'vigorous':
        return 1.35;
    }
  };

  const estimatedCalories = Math.round(
    selectedSport.defaultCalPerMin * duration * getIntensityMultiplier(intensity)
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    addSportLog(
      selectedSport.id,
      selectedSport.name,
      selectedSport.icon,
      duration,
      estimatedCalories,
      intensity,
      customNotes
    );
    setIsModalOpen(false);
    setCustomNotes('');
  };

  const totalCaloriesBurned = sportLogs.reduce((acc, log) => acc + log.caloriesBurned, 0);
  const totalMinutes = sportLogs.reduce((acc, log) => acc + log.durationMinutes, 0);

  const nextSportLvlXp = user.sportLevel * 150;
  const sportXpPct = Math.min(100, Math.round((user.sportXp / nextSportLvlXp) * 100));

  // ---- Reps (parity with PyQt SportRepsChartWidget / LogSportRepsDialog) ----
  const [repsSummary, setRepsSummary] = useState<any>(null);
  const [repsModal, setRepsModal] = useState<{ open: boolean; activity: any }>({ open: false, activity: null });
  const [repSets, setRepSets] = useState(1);
  const [repReps, setRepReps] = useState(10);
  const [repNote, setRepNote] = useState('');
  const [repInfo, setRepInfo] = useState<any>(null);

  useEffect(() => {
    life.sportRepsSummary().then((d) => setRepsSummary(d?.activities || [])).catch(() => setRepsSummary([]));
  }, []);

  const openReps = async (activity: any) => {
    setRepsModal({ open: true, activity });
    setRepSets(1); setRepReps(10); setRepNote(''); setRepInfo(null);
    try {
      const info = await life.sportRepsInfo(activity.id);
      if (info?.ok === false) { setRepInfo({ total: 0, rank: { key: 'unranked', icon: '⭐' }, history: [] }); }
      else setRepInfo(info);
    } catch {
      setRepInfo({ total: 0, rank: { key: 'unranked', icon: '⭐' }, history: [] });
    }
  };

  const submitReps = async () => {
    if (!repsModal.activity || repReps <= 0) return;
    const res = await life.sportReps(repsModal.activity.id, repReps, repSets);
    if (res?.result?.ok === false) {
      showToast('info', String(res.result.code || 'error'), '');
      return;
    }
    try {
      const info = await life.sportRepsInfo(repsModal.activity.id);
      setRepInfo(info);
    } catch { /* ignore */ }
    life.sportRepsSummary().then((d) => setRepsSummary(d?.activities || [])).catch(() => undefined);
    // Rank-up celebration message
    if (res?.result && res.result.rank_up) {
      showToast('level_up', '🎉 ' + (lang === 'id' ? 'Rank Naik!' : 'Rank Up!'), String(res.result.rank_after?.key || ''));
    }
  };

  // Aggregate reps across all activities over the returned 7-day series
  const repSeriesByDate = new Map<string, number>();
  (repsSummary || []).forEach((a: any) => (a.series || []).forEach((s: any) => {
    repSeriesByDate.set(s.date, (repSeriesByDate.get(s.date) || 0) + Number(s.reps || 0));
  }));
  const repChartData = [...repSeriesByDate.entries()].sort((x, y) => (x[0] < y[0] ? -1 : 1)).map(([date, value]) => ({ label: date.slice(5), value }));
  const totalRepsAll = (repsSummary || []).reduce((acc: number, a: any) => acc + Number(a.totalReps || 0), 0);

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
              {user.sportXp} / {nextSportLvlXp} Sport XP ({sportXpPct}%)
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
              onClick={() => setIsModalOpen(true)}
              className="w-full py-2 px-3 rounded-xl bg-rose-500 hover:bg-rose-400 text-slate-950 font-bold text-xs shadow-lg shadow-rose-500/20 transition-all flex items-center justify-center gap-1.5"
            >
              <Plus className="w-4 h-4" /> {lang === 'id' ? 'Catat Sesi Latihan' : 'Log Workout'}
            </button>
          </div>
        </div>
      </div>

      {/* Reps Chart (parity with PyQt SportRepsChartWidget) */}
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
            <div className="min-w-[300px]">
              <LineChart data={repChartData} color="#38bdf8" width={680} height={150} />
            </div>
          </div>
        )}
      </div>

      {/* History of Workouts */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Riwayat Latihan Terbaru' : 'Recent Workout History'}</h3>
          <button
            type="button"
            onClick={() => applyTaskTemplate('sport', 'running_starter_s')}
            className="px-3 py-1.5 rounded-xl bg-slate-800 text-[11px] font-bold text-slate-200"
          >
            {lang === 'id' ? 'Template PyQt' : 'PyQt templates'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {sportLogs.map((log) => (
            <div
              key={log.id}
              className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 flex items-start justify-between gap-3"
            >
              <div className="flex items-start gap-3">
                <div className="w-11 h-11 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-xl shrink-0">
                  {log.icon}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h4 className="font-bold text-sm text-slate-100">{log.sportName}</h4>
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-400 capitalize">
                      {log.intensity}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                    <span className="flex items-center gap-1 text-rose-400 font-semibold">
                      <Timer className="w-3 h-3" /> {log.durationMinutes} mins
                    </span>
                    <span className="flex items-center gap-1 text-amber-400 font-semibold">
                      <Flame className="w-3 h-3" /> {log.caloriesBurned} kcal
                    </span>
                    <span className="text-slate-400">{log.date}</span>
                  </div>
                  {log.notes && <p className="text-xs text-slate-400 mt-1">{log.notes}</p>}
                </div>
              </div>

              <button
                onClick={() => openReps(log)}
                className="px-2 py-1 rounded-lg bg-sky-500/20 text-sky-300 text-[10px] font-bold"
              >
                {lang === 'id' ? 'Reps' : 'Reps'}
              </button>
              {!log.done && (
                <button
                  onClick={() => completeSportLog(log.id)}
                  className="px-2 py-1 rounded-lg bg-rose-500/20 text-rose-300 text-[10px] font-bold"
                >
                  {lang === 'id' ? 'Selesai +XP' : 'Complete +XP'}
                </button>
              )}
              <button
                type="button"
                onClick={() => life.duplicateSport(log.id).catch(() => undefined)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-sky-300"
                title="Duplicate"
              >
                Dup
              </button>
              <button
                onClick={() => deleteSportLog(log.id)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                title="Delete Log"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {sportLogs.length === 0 && (
          <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
            <Dumbbell className="w-8 h-8 text-rose-500/40 mx-auto mb-2" />
            <p className="text-sm font-semibold">{lang === 'id' ? 'Belum ada catatan olahraga.' : 'No workouts logged yet.'}</p>
          </div>
        )}
      </div>

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">
              {lang === 'id' ? 'Catat Aktivitas Olahraga' : 'Log Sport Session'}
            </h3>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-2">{lang === 'id' ? 'Pilih Jenis Olahraga' : 'Select Sport'}</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-48 overflow-y-auto pr-1">
                  {SPORT_TYPES.map((st) => (
                    <button
                      key={st.id}
                      type="button"
                      onClick={() => setSelectedSportId(st.id)}
                      className={`p-2 rounded-xl border flex flex-col items-center text-center transition-all ${
                        selectedSportId === st.id
                          ? 'bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-sm'
                          : 'bg-slate-800/60 text-slate-300 border-slate-700 hover:bg-slate-800'
                      }`}
                    >
                      <span className="text-xl mb-1">{st.icon}</span>
                      <span className="text-[11px] font-semibold leading-tight line-clamp-1">{st.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Durasi (Menit)' : 'Duration (Mins)'}</label>
                  <input
                    type="number"
                    min={1}
                    max={360}
                    value={duration}
                    onChange={(e) => setDuration(Number(e.target.value))}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Intensitas' : 'Intensity'}</label>
                  <select
                    value={intensity}
                    onChange={(e) => setIntensity(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                  >
                    <option value="light">Light (Santai)</option>
                    <option value="moderate">Moderate (Sedang)</option>
                    <option value="vigorous">Vigorous (Keras/Intens)</option>
                  </select>
                </div>
              </div>

              {/* Live Calorie Estimate */}
              <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 flex items-center justify-between text-xs">
                <span className="text-slate-400">{lang === 'id' ? 'Estimasi Terbakar:' : 'Estimated Burn:'}</span>
                <span className="font-extrabold text-amber-400 flex items-center gap-1">
                  <Flame className="w-4 h-4" /> {estimatedCalories} kcal
                </span>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan / Jarak / Reps' : 'Notes / Distance'}</label>
                <input
                  type="text"
                  value={customNotes}
                  onChange={(e) => setCustomNotes(e.target.value)}
                  placeholder="e.g. 5km morning loop, 4 sets pullups"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-rose-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
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
                  {lang === 'id' ? 'Simpan' : 'Save Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* LogSportReps Dialog (parity with PyQt LogSportRepsDialog) */}
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
              <p className="text-xs font-bold" style={{ color: '#9aa0a6' }}>
                {repInfo.rank?.icon || '⭐'} {repInfo.rank?.name || repInfo.rank?.key || 'Unranked'}{' '}
                · {lang === 'id' ? 'Total' : 'Total'}: {repInfo.total ?? 0} reps
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
                <label className="block text-slate-400 text-[10px] font-bold">{lang === 'id' ? 'Set' : 'Sets'}</label>
                <input type="number" min={1} max={50} value={repSets} onChange={(e) => setRepSets(Math.max(1, Number(e.target.value) || 1))} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />
              </div>
              <span className="text-slate-500 text-lg font-bold">×</span>
              <div className="flex-1">
                <label className="block text-slate-400 text-[10px] font-bold">{lang === 'id' ? 'Reps' : 'Reps'}</label>
                <input type="number" min={1} max={1000} value={repReps} onChange={(e) => setRepReps(Math.max(1, Number(e.target.value) || 1))} className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100" />
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
              <button onClick={submitReps} disabled={repReps <= 0} className="px-4 py-2 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-slate-950 font-bold text-xs">{lang === 'id' ? 'Simpan' : 'Save'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
