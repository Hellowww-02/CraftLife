import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { SPORT_TYPES } from '../../data/gameData';
import { Activity, Plus, Flame, Timer, Trash2, Dumbbell, Award } from 'lucide-react';

export const SportView: React.FC = () => {
  const { user, sportLogs, addSportLog, completeSportLog, deleteSportLog, lang, applyTaskTemplate } = useGame();
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
    </div>
  );
};
