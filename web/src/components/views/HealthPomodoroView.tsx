import React, { useState, useEffect } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { Timer, Heart, Moon, Footprints, Scale, Smile, Play, Pause, RotateCcw, Plus, Award } from 'lucide-react';

export const HealthPomodoroView: React.FC = () => {
  const { healthLogs, addHealthLog, pomodoroSessions, completePomodoroSession, lang } = useGame();

  // Pomodoro State
  const [timerMinutes, setTimerMinutes] = useState(25);
  const [secondsLeft, setSecondsLeft] = useState(25 * 60);
  const [isRunning, setIsRunning] = useState(false);
  const [sessionLabel, setSessionLabel] = useState('Deep Quest Focus');

  // Health Metrics Form State
  const [steps, setSteps] = useState(6500);
  const [sleepHours, setSleepHours] = useState(7.5);
  const [weightKg, setWeightKg] = useState(68);
  const [heartRate, setHeartRate] = useState(72);
  const [mood, setMood] = useState<'great' | 'good' | 'neutral' | 'tired' | 'stressed'>('great');
  const [healthNotes, setHealthNotes] = useState('');
  const [bmiH, setBmiH] = useState(170);
  const [bmiW, setBmiW] = useState(70);
  const [bmiAge, setBmiAge] = useState(25);
  const [bmiG, setBmiG] = useState('male');
  const [bmiAct, setBmiAct] = useState(1.55);

  useEffect(() => {
    life.getBmi().then((d) => {
      const b = d.bmi || {};
      if (b.height_cm) setBmiH(Number(b.height_cm));
      if (b.weight_kg) setBmiW(Number(b.weight_kg));
      if (b.age) setBmiAge(Number(b.age));
      if (b.gender) setBmiG(String(b.gender));
    }).catch(() => undefined);
  }, []);

  // Pomodoro countdown timer effect
  useEffect(() => {
    let interval: any = null;
    if (isRunning && secondsLeft > 0) {
      interval = setInterval(() => {
        setSecondsLeft((prev) => prev - 1);
      }, 1000);
    } else if (secondsLeft === 0 && isRunning) {
      setIsRunning(false);
      completePomodoroSession(timerMinutes, sessionLabel);
      setSecondsLeft(timerMinutes * 60);
    }
    return () => clearInterval(interval);
  }, [isRunning, secondsLeft, timerMinutes, sessionLabel, completePomodoroSession]);

  const handleStartTimer = (mins: number) => {
    setTimerMinutes(mins);
    setSecondsLeft(mins * 60);
    setIsRunning(true);
  };

  const handleResetTimer = () => {
    setIsRunning(false);
    setSecondsLeft(timerMinutes * 60);
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  const handleSaveHealthLog = (e: React.FormEvent) => {
    e.preventDefault();
    addHealthLog(steps, sleepHours, weightKg, heartRate, mood, healthNotes);
    setHealthNotes('');
  };

  const totalFocusMinutes = pomodoroSessions.reduce((acc, p) => acc + p.durationMinutes, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Timer className="w-6 h-6 text-purple-400" />
          <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Kesehatan Harian & Fokus Pomodoro' : 'Health Metrics & Focus Pomodoro'}</h2>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          {lang === 'id'
            ? 'Gunakan timer fokus Pomodoro untuk menyelesaikan tugas nyata dan catat metrik kesehatan seperti langkah, tidur, dan suasana hati.'
            : 'Boost real-world productivity with gamified Pomodoro focus intervals, and monitor lifestyle health stats.'}
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pomodoro Focus Chamber */}
        <div className="rounded-3xl bg-gradient-to-b from-purple-950/30 via-slate-900 to-slate-950 border border-purple-500/30 p-6 flex flex-col justify-between items-center text-center space-y-6 shadow-xl">
          <div className="w-full flex items-center justify-between">
            <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">{lang === 'id' ? 'Ruang Fokus Mental' : 'Pomodoro Focus Chamber'}</span>
            <span className="text-xs font-semibold text-slate-400">Total: {totalFocusMinutes} mins</span>
          </div>

          {/* Big Timer Circle */}
          <div className="relative flex items-center justify-center">
            <div className="w-48 h-48 rounded-full border-4 border-purple-500/20 flex flex-col items-center justify-center bg-slate-900/80 shadow-2xl shadow-purple-500/20">
              <span className="font-mono text-4xl font-black text-slate-100 tracking-wider">
                {formatTime(secondsLeft)}
              </span>
              <span className="text-xs font-semibold text-purple-400 mt-1">{sessionLabel}</span>
            </div>
          </div>

          {/* Quick Preset Buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleStartTimer(25)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                timerMinutes === 25 ? 'bg-purple-500 text-slate-950 shadow' : 'bg-slate-800 text-slate-300'
              }`}
            >
              25 min (Standard)
            </button>
            <button
              onClick={() => handleStartTimer(50)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                timerMinutes === 50 ? 'bg-purple-500 text-slate-950 shadow' : 'bg-slate-800 text-slate-300'
              }`}
            >
              50 min (Deep Work)
            </button>
            <button
              onClick={() => handleStartTimer(5)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all ${
                timerMinutes === 5 ? 'bg-purple-500 text-slate-950 shadow' : 'bg-slate-800 text-slate-300'
              }`}
            >
              5 min (Short Rest)
            </button>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3 w-full max-w-xs">
            <button
              onClick={() => setIsRunning(!isRunning)}
              className={`flex-1 py-3 rounded-2xl font-bold text-xs shadow-lg flex items-center justify-center gap-2 transition-all ${
                isRunning
                  ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-amber-500/20'
                  : 'bg-purple-500 hover:bg-purple-400 text-slate-950 shadow-purple-500/20'
              }`}
            >
              {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              <span>{isRunning ? (lang === 'id' ? 'Jeda' : 'Pause') : (lang === 'id' ? 'Mulai Fokus' : 'Start Focus')}</span>
            </button>

            <button
              onClick={handleResetTimer}
              className="p-3 rounded-2xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold"
              title="Reset Timer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Daily Health Log Form */}
        <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
              <Heart className="w-4 h-4 text-rose-400" />
              <span>{lang === 'id' ? 'Catatan Kesehatan Harian' : 'Daily Health Metrics'}</span>
            </h3>
            <span className="text-xs text-slate-400">{new Date().toISOString().split('T')[0]}</span>
          </div>

          <form onSubmit={handleSaveHealthLog} className="space-y-3.5 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <Footprints className="w-3.5 h-3.5 text-emerald-400" /> {lang === 'id' ? 'Langkah Kaki' : 'Daily Steps'}
                </label>
                <input
                  type="number"
                  step="500"
                  value={steps}
                  onChange={(e) => setSteps(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <Moon className="w-3.5 h-3.5 text-sky-400" /> {lang === 'id' ? 'Tidur (Jam)' : 'Sleep (Hours)'}
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={sleepHours}
                  onChange={(e) => setSleepHours(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <Scale className="w-3.5 h-3.5 text-amber-400" /> {lang === 'id' ? 'Berat Badan (Kg)' : 'Weight (Kg)'}
                </label>
                <input
                  type="number"
                  step="0.5"
                  value={weightKg}
                  onChange={(e) => setWeightKg(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1 flex items-center gap-1.5">
                  <Heart className="w-3.5 h-3.5 text-rose-400" /> {lang === 'id' ? 'Detak Jantung (Bpm)' : 'Resting BPM'}
                </label>
                <input
                  type="number"
                  value={heartRate}
                  onChange={(e) => setHeartRate(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1.5 flex items-center gap-1.5">
                <Smile className="w-3.5 h-3.5 text-yellow-400" /> {lang === 'id' ? 'Suasana Hati (Mood)' : 'Mood & Mindset'}
              </label>
              <div className="grid grid-cols-5 gap-1.5 text-center">
                {(['great', 'good', 'neutral', 'tired', 'stressed'] as const).map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMood(m)}
                    className={`py-2 rounded-xl border capitalize font-semibold transition-all ${
                      mood === m
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/50 shadow'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}
                  >
                    {m === 'great' ? '😄' : m === 'good' ? '🙂' : m === 'neutral' ? '😐' : m === 'tired' ? '🥱' : '😫'}
                    <span className="block text-[10px] mt-0.5">{m}</span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan Refleksi' : 'Daily Reflection Notes'}</label>
              <input
                type="text"
                value={healthNotes}
                onChange={(e) => setHealthNotes(e.target.value)}
                placeholder="e.g. Slept deeply, had high focus today..."
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-purple-500"
              />
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-xl bg-purple-500 hover:bg-purple-400 text-slate-950 font-bold text-xs shadow-lg shadow-purple-500/20 transition-all flex items-center justify-center gap-2"
            >
              <Plus className="w-4 h-4" /> {lang === 'id' ? 'Simpan Metrik Kesehatan' : 'Save Health Entry'}
            </button>
          </form>
        </div>
      </div>

      <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
        <h3 className="text-sm font-bold text-slate-200">{lang === 'id' ? 'BMI / tujuan tubuh' : 'BMI / body goals'}</h3>
        <div className="flex flex-wrap gap-2 text-xs">
          <input type="number" value={bmiH} onChange={(e) => setBmiH(Number(e.target.value))} className="w-20 px-2 py-1 rounded-lg bg-slate-950 border border-slate-700" title="cm" />
          <input type="number" value={bmiW} onChange={(e) => setBmiW(Number(e.target.value))} className="w-20 px-2 py-1 rounded-lg bg-slate-950 border border-slate-700" title="kg" />
          <input type="number" value={bmiAge} onChange={(e) => setBmiAge(Number(e.target.value))} className="w-16 px-2 py-1 rounded-lg bg-slate-950 border border-slate-700" />
          <select value={bmiG} onChange={(e) => setBmiG(e.target.value)} className="px-2 py-1 rounded-lg bg-slate-950 border border-slate-700">
            <option value="male">M</option>
            <option value="female">F</option>
          </select>
          <select value={bmiAct} onChange={(e) => setBmiAct(Number(e.target.value))} className="px-2 py-1 rounded-lg bg-slate-950 border border-slate-700">
            <option value={1.2}>{lang === 'id' ? 'Santai' : 'Sedentary'}</option>
            <option value={1.375}>{lang === 'id' ? 'Ringan' : 'Light'}</option>
            <option value={1.55}>{lang === 'id' ? 'Sedang' : 'Moderate'}</option>
            <option value={1.725}>{lang === 'id' ? 'Aktif' : 'Active'}</option>
            <option value={1.9}>{lang === 'id' ? 'Sangat aktif' : 'Very active'}</option>
          </select>
          <button type="button" onClick={() => life.saveBmi({ heightCm: bmiH, weightKg: bmiW, age: bmiAge, gender: bmiG, activityFactor: bmiAct })} className="px-3 py-1 rounded-lg bg-purple-600 text-white font-bold">
            {lang === 'id' ? 'Simpan BMI' : 'Save BMI'}
          </button>
          <span className="text-slate-400 self-center">
            BMI {bmiH > 0 ? (bmiW / ((bmiH / 100) ** 2)).toFixed(1) : '—'}
            {' · '}
            TDEE {Math.round(((10 * bmiW) + (6.25 * bmiH) - (5 * bmiAge) + (bmiG === 'female' ? -161 : 5)) * bmiAct)} kcal
          </span>
        </div>
      </div>

      {healthLogs.length > 0 && (
        <div className="p-4 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-2">
          <h3 className="text-sm font-bold text-slate-200">{lang === 'id' ? 'Riwayat kesehatan' : 'Health history'}</h3>
          {healthLogs.slice(0, 8).map((h) => (
            <div key={h.id} className="flex justify-between text-xs text-slate-400 border-b border-slate-800/80 pb-1">
              <span>{h.date}</span>
              <span>{h.steps} {lang === 'id' ? 'langkah' : 'steps'} · {h.sleepHours}h · {h.mood}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
