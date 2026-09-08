import React from 'react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { Pause, Play, RotateCcw, Volume2, X } from 'lucide-react';
import { ProgressRing } from '../charts';

/** Interpolasi {var} sederhana (gaya trv di LoveSpaceView). */
const trv = (key: string, vars: Record<string, string | number>, fb: string) =>
  Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), t(key, fb));

/**
 * Mirror penuh PomodoroPage PyQt:
 * - kartu timer (state label berwarna, mm:ss, progress bar, tombol sesuai fase)
 * - settings (task, durasi fokus 5–120 / istirahat 1–30 menit, uji alarm)
 * - statistik (hari ini / total / 5 sesi terakhir)
 * Engine-nya hidup di GameContext (timestamp-based) sehingga timer tidak pernah
 * reset saat berpindah halaman — insiden issue #7.
 */
export const PomodoroView: React.FC = () => {
  const {
    pomo, pomodoroSessions, pomodoroStats,
    pomoStart, pomoPauseToggle, pomoReset, pomoGiveUp,
    pomoSetDurations, pomoSetTask, pomoTestAlarm,
  } = useGame();

  const running = pomo.phase !== 'idle';
  const mins = String(Math.floor(pomo.remainingSec / 60)).padStart(2, '0');
  const secs = String(pomo.remainingSec % 60).padStart(2, '0');
  const progress = pomo.totalSec > 0 ? Math.round(((pomo.totalSec - pomo.remainingSec) / pomo.totalSec) * 100) : 0;

  const stateLabel =
    pomo.phase === 'focus' ? t('pomodoro_state_focus', '🎯 FOKUS')
    : pomo.phase === 'break' ? t('pomodoro_state_break', '☕ ISTIRAHAT')
    : t('pomodoro_state_idle', 'Siap memulai?');
  const stateCls =
    pomo.phase === 'focus' ? 'text-violet-400'
    : pomo.phase === 'break' ? 'text-[#7ac74c]'
    : 'text-slate-400';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-black text-slate-100">{t('pomodoro', '🍅 Pomodoro')}</h2>
        <p className="text-xs text-slate-400 mt-1">{t('nav_pomodoro', 'Pomodoro')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* ── Kartu Timer (Parity: timer_card stretch 3) ─────────────── */}
        <div className={`lg:col-span-3 ct-panel rounded-3xl p-8 flex flex-col items-center gap-5 ${pomo.phase === 'break' ? 'ct-pomo-break' : 'ct-pomo-focus'}`}>
          <span className={`ct-chip text-xs font-bold px-3 py-1 ${stateCls}`}>{stateLabel}</span>
          <ProgressRing
            size={230}
            strokeWidth={11}
            progress={progress / 100}
            color={pomo.phase === 'break' ? '#7ac74c' : '#a78bfa'}
            className="ct-ring"
          >
            <div className="ct-pomo-time font-mono text-6xl font-black text-slate-100 tabular-nums tracking-tight">
              {mins}:{secs}
            </div>
          </ProgressRing>
          <div className="w-full h-1.5 rounded-full overflow-hidden ct-bar-track">
            <div
              className={`h-full rounded-full transition-all duration-1000 ct-bar-fill ${pomo.phase === 'break' ? 'bg-[#7ac74c]' : 'bg-violet-500'}`}
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="flex flex-wrap justify-center gap-2 w-full">
            {/* _update_controls: Start hanya saat idle */}
            {!running && (
              <button
                onClick={pomoStart}
                className="ct-btn ct-btn-primary ct-btn-lg"
              >
                <Play className="w-4 h-4" />
                {t('pomodoro_start', '▶ Mulai Fokus')}
              </button>
            )}
            {running && (
              <button
                onClick={pomoPauseToggle}
                className="ct-btn ct-btn-secondary ct-btn-lg"
              >
                <Pause className="w-4 h-4" />
                {pomo.paused ? t('pomodoro_resume', '▶ Lanjut') : t('pomodoro_pause', '⏸ Jeda')}
              </button>
            )}
            {/* Reset selalu terlihat (parity) */}
            <button
              onClick={pomoReset}
              className="ct-btn ct-btn-secondary ct-btn-lg"
            >
              <RotateCcw className="w-4 h-4" />
              {t('pomodoro_reset', '↺ Reset')}
            </button>
            {running && (
              <button
                onClick={pomoGiveUp}
                className="ct-btn ct-btn-danger ct-btn-lg"
              >
                <X className="w-4 h-4" />
                {t('pomodoro_give_up', '✖ Menyerah (tanpa hadiah)')}
              </button>
            )}
          </div>
          <div className="flex-1" />
        </div>

        {/* ── Kolom kanan: Settings + Stats (Parity: stretch 2) ─────── */}
        <div className="lg:col-span-2 space-y-4">
          <div className="ct-panel p-5 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              {t('pomodoro_task_label', 'Sedang mengerjakan apa? (opsional)')}
            </h3>
            <input
              type="text"
              value={pomo.taskLabel}
              onChange={(e) => pomoSetTask(e.target.value)}
              disabled={running}
              placeholder={t('pomodoro_task_placeholder', 'mis. Menulis laporan, Belajar bab 3...')}
              className="ct-input w-full rounded-xl px-3.5 py-2.5 text-sm disabled:opacity-50 focus:border-transparent"
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">{t('pomodoro_focus_label', 'Durasi Fokus')}</label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number" min={5} max={120}
                    value={pomo.focusMin}
                    disabled={running}
                    onChange={(e) => pomoSetDurations(Number(e.target.value), pomo.breakMin)}
                    className="ct-input w-full rounded-lg px-2.5 py-2 text-sm disabled:opacity-50"
                  />
                  <span className="text-[11px] text-slate-500 shrink-0">{t('pomodoro_minutes_unit', 'menit')}</span>
                </div>
              </div>
              <div>
                <label className="block text-[11px] text-slate-500 mb-1">{t('pomodoro_break_label', 'Durasi Istirahat')}</label>
                <div className="flex items-center gap-1.5">
                  <input
                    type="number" min={1} max={30}
                    value={pomo.breakMin}
                    disabled={running}
                    onChange={(e) => pomoSetDurations(pomo.focusMin, Number(e.target.value))}
                    className="ct-input w-full rounded-lg px-2.5 py-2 text-sm disabled:opacity-50"
                  />
                  <span className="text-[11px] text-slate-500 shrink-0">{t('pomodoro_minutes_unit', 'menit')}</span>
                </div>
              </div>
            </div>
            <button
              onClick={pomoTestAlarm}
              className="ct-btn ct-btn-secondary ct-btn-sm w-full justify-center text-indigo-200"
            >
              <Volume2 className="w-4 h-4" />
              {t('pomodoro_test_alarm', 'Uji Alarm Berulang')}
            </button>
          </div>

          <div className="ct-panel p-5 space-y-3">
            <p className="text-xs text-slate-300">
              📅 {t('pomodoro_today', 'Hari ini')}: {trv('pomodoro_stat_sessions', { n: pomodoroStats.todaySessions }, '{n} sesi')}
              {' · '}{trv('pomodoro_stat_minutes', { n: pomodoroStats.todayMinutes }, '{n} menit')}
            </p>
            <p className="text-xs text-slate-300">
              🏆 {t('pomodoro_total', 'Total')}: {trv('pomodoro_stat_sessions', { n: pomodoroStats.totalSessions }, '{n} sesi')}
              {' · '}{trv('pomodoro_stat_minutes', { n: pomodoroStats.totalMinutes }, '{n} menit')}
            </p>
            <div className="border-t border-slate-800" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              {t('pomodoro_recent', 'Sesi Terakhir')}
            </h3>
            {pomodoroSessions.length === 0 ? (
              <p className="text-[11px] text-slate-500">{t('pomodoro_no_recent', 'Belum ada sesi. Yuk mulai yang pertama!')}</p>
            ) : (
              <div className="space-y-1.5">
                {/* parity: 5 terbaru, format 🍅 25′ label · MM-DD HH:mm */}
                {pomodoroSessions.slice(0, 5).map((s) => (
                  <p key={s.id} className="text-[11px] text-slate-400">
                    🍅 {s.durationMinutes}′ {s.label || '—'} · {(s.completedAt || '').slice(5, 16).replace('T', ' ')}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
