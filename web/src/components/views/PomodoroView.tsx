import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { Pause, Play, RotateCcw, Timer } from 'lucide-react';

/** Mirror PomodoroPage — terpisah dari HealthFoodPage. */
export const PomodoroView: React.FC = () => {
  const { pomodoroSessions, completePomodoroSession, lang } = useGame();
  const [phase, setPhase] = useState<'work' | 'break'>('work');
  const [workMin, setWorkMin] = useState(25);
  const [breakMin, setBreakMin] = useState(5);
  const [secondsLeft, setSecondsLeft] = useState(25 * 60);
  const [running, setRunning] = useState(false);
  const [label, setLabel] = useState('Focus');

  useEffect(() => {
    if (!running) return;
    const id = window.setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) {
          window.clearInterval(id);
          setRunning(false);
          if (phase === 'work') {
            completePomodoroSession(workMin, label);
            setPhase('break');
            return breakMin * 60;
          }
          setPhase('work');
          return workMin * 60;
        }
        return s - 1;
      });
    }, 1000);
    return () => window.clearInterval(id);
  }, [running, phase, workMin, breakMin, label, completePomodoroSession]);

  const fmt = (secs: number) =>
    `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;

  const total = pomodoroSessions.reduce((a, p) => a + p.durationMinutes, 0);

  return (
    <div className="space-y-6 max-w-xl mx-auto text-center">
      <h2 className="text-xl font-black text-slate-100 flex items-center justify-center gap-2">
        <Timer className="w-6 h-6 text-purple-400" />
        {lang === 'id' ? 'Pomodoro' : 'Pomodoro'}
      </h2>
      <p className="text-xs text-slate-400">
        {lang === 'id' ? 'Siklus kerja/istirahat seperti PomodoroPage PyQt.' : 'Work/break cycle like PyQt PomodoroPage.'}
      </p>
      <div className="rounded-3xl border border-purple-500/30 bg-slate-900 p-8 space-y-4">
        <div className="text-xs uppercase tracking-wider text-purple-300">{phase === 'work' ? 'Work' : 'Break'}</div>
        <div className="font-mono text-5xl font-black">{fmt(secondsLeft)}</div>
        <input value={label} onChange={(e) => setLabel(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-center" />
        <div className="flex justify-center gap-2 text-xs">
          <label className="flex items-center gap-1">
            work
            <input type="number" value={workMin} onChange={(e) => setWorkMin(Number(e.target.value) || 25)} className="w-14 bg-slate-800 rounded px-1 py-1" />
          </label>
          <label className="flex items-center gap-1">
            break
            <input type="number" value={breakMin} onChange={(e) => setBreakMin(Number(e.target.value) || 5)} className="w-14 bg-slate-800 rounded px-1 py-1" />
          </label>
        </div>
        <div className="flex justify-center gap-2">
          <button type="button" onClick={() => setRunning(!running)} className="px-5 py-3 rounded-2xl bg-purple-500 text-slate-950 font-black text-xs flex items-center gap-1">
            {running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {running ? (lang === 'id' ? 'Jeda' : 'Pause') : lang === 'id' ? 'Mulai' : 'Start'}
          </button>
          <button
            type="button"
            onClick={() => {
              setRunning(false);
              setPhase('work');
              setSecondsLeft(workMin * 60);
            }}
            className="p-3 rounded-2xl bg-slate-800"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => {
              setRunning(false);
              setPhase('work');
              setSecondsLeft(workMin * 60);
            }}
            className="px-3 py-3 rounded-2xl bg-rose-500/20 text-rose-300 text-xs font-bold"
          >
            {lang === 'id' ? 'Menyerah' : 'Give up'}
          </button>
          <button
            type="button"
            onClick={() => {
              try {
                const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
                const o = ctx.createOscillator();
                const g = ctx.createGain();
                o.connect(g);
                g.connect(ctx.destination);
                o.frequency.value = 880;
                g.gain.value = 0.08;
                o.start();
                setTimeout(() => {
                  o.stop();
                  ctx.close();
                }, 400);
              } catch {
                /* ignore */
              }
            }}
            className="px-3 py-3 rounded-2xl bg-slate-800 text-xs font-bold"
          >
            {lang === 'id' ? 'Uji alarm' : 'Test alarm'}
          </button>
        </div>
        <p className="text-xs text-slate-500">{lang === 'id' ? 'Total fokus' : 'Total focus'}: {total} min</p>
      </div>
    </div>
  );
};
