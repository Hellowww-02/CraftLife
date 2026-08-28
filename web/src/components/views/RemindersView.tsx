import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { Bell, BellOff, Clock, Plus, Trash2 } from 'lucide-react';

/** Mirror RemindersPage (MainPyQt6) — halaman terpisah dari CalendarPage. */
export const RemindersView: React.FC = () => {
  const { reminders, addReminder, toggleReminder, deleteReminder, lang } = useGame();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [time, setTime] = useState('09:00');
  const [repeat, setRepeat] = useState<'none' | 'daily' | 'weekdays' | 'weekly'>('daily');
  const [sound, setSound] = useState<'beep' | 'bell' | 'magic' | 'fanfare'>('bell');

  const testBeep = () => {
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
      }, 180);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-black text-slate-100 flex items-center gap-2">
            <Clock className="w-6 h-6 text-amber-300" />
            {lang === 'id' ? 'Pengingat Alarm' : 'Reminders'}
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Sama seperti RemindersPage PyQt: tambah, nyala/mati, hapus, uji bunyi.'
              : 'Same as PyQt RemindersPage: add, toggle, delete, test sound.'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black flex items-center gap-1"
        >
          <Plus className="w-4 h-4" /> {lang === 'id' ? 'Set pengingat' : 'Add reminder'}
        </button>
      </div>

      <div className="space-y-2">
        {reminders.map((rem) => (
          <div
            key={rem.id}
            className={`p-3 rounded-xl border flex items-center justify-between gap-3 ${
              rem.isActive ? 'bg-slate-900 border-slate-800' : 'bg-slate-950/40 border-slate-900 opacity-60'
            }`}
          >
            <div className="flex items-center gap-3">
              <button type="button" onClick={() => toggleReminder(rem.id)} className="p-2 rounded-lg bg-slate-800">
                {rem.isActive ? <Bell className="w-4 h-4 text-amber-300" /> : <BellOff className="w-4 h-4 text-slate-500" />}
              </button>
              <div>
                <div className="text-sm font-bold text-slate-100">{rem.title}</div>
                <div className="text-[11px] text-slate-400 font-mono">
                  {rem.time} · {rem.repeat} · {rem.sound}
                </div>
              </div>
            </div>
            <div className="flex gap-1">
              <button type="button" onClick={testBeep} className="px-2 py-1 text-[11px] rounded-lg bg-slate-800 text-slate-300">
                {lang === 'id' ? 'Uji' : 'Test'}
              </button>
              <button type="button" onClick={() => deleteReminder(rem.id)} className="p-2 text-rose-400">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
        {reminders.length === 0 && (
          <p className="text-xs text-slate-500 text-center py-8">{lang === 'id' ? 'Belum ada pengingat.' : 'No reminders yet.'}</p>
        )}
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 w-full max-w-md space-y-3">
            <h3 className="font-black text-slate-100">{lang === 'id' ? 'Pengingat baru' : 'New reminder'}</h3>
            <input value={title} onChange={(e) => setTitle(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm" placeholder="Title" />
            <input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono" />
            <div className="grid grid-cols-2 gap-2">
              {(['none', 'daily', 'weekdays', 'weekly'] as const).map((r) => (
                <button key={r} type="button" onClick={() => setRepeat(r)} className={`py-1.5 text-xs rounded-lg border ${repeat === r ? 'border-amber-400 text-amber-300' : 'border-slate-800 text-slate-400'}`}>
                  {r}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(['beep', 'bell', 'magic', 'fanfare'] as const).map((s) => (
                <button key={s} type="button" onClick={() => setSound(s)} className={`py-1.5 text-xs rounded-lg border ${sound === s ? 'border-amber-400 text-amber-300' : 'border-slate-800 text-slate-400'}`}>
                  {s}
                </button>
              ))}
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="px-3 py-2 text-xs rounded-xl bg-slate-800">
                {lang === 'id' ? 'Batal' : 'Cancel'}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (!title.trim()) return;
                  addReminder(title.trim(), time, repeat, sound);
                  setOpen(false);
                  setTitle('');
                }}
                className="px-3 py-2 text-xs rounded-xl bg-amber-500 text-slate-950 font-black"
              >
                {lang === 'id' ? 'Simpan' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
