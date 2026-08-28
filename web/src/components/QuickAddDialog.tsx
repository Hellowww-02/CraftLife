/**
 * QuickAddDialog — parity for the PyQt `QuickAddDialog` (instant capture of a
 * new Habit / Daily / Quest from a single title field, no full editor).
 */
import React, { useState } from 'react';
import { useGame } from '../context/GameContext';
import { Plus, X, Zap, CalendarCheck, CheckSquare } from 'lucide-react';

type QuickAddMode = 'habit' | 'daily' | 'quest';

const MODES: { key: QuickAddMode; icon: React.ReactNode; labelId: string; labelEn: string }[] = [
  { key: 'habit', icon: <Zap className="w-3.5 h-3.5" />, labelId: 'Habit', labelEn: 'Habit' },
  { key: 'daily', icon: <CalendarCheck className="w-3.5 h-3.5" />, labelId: 'Daily', labelEn: 'Daily' },
  { key: 'quest', icon: <CheckSquare className="w-3.5 h-3.5" />, labelId: 'Quest', labelEn: 'Quest' },
];

export const QuickAddDialog: React.FC = () => {
  const { addHabit, addDaily, addQuest, lang } = useGame();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<QuickAddMode>('habit');
  const [title, setTitle] = useState('');

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = title.trim();
    if (!t) return;
    if (mode === 'habit') addHabit(t, 'medium', true, false, null, '');
    else if (mode === 'daily') addDaily(t, 'medium', [0, 1, 2, 3, 4, 5, 6], null, '');
    else addQuest(t, 'medium', null, null, '');
    setTitle('');
    setOpen(false);
  };

  const placeholder =
    lang === 'id'
      ? mode === 'habit'
        ? 'Tulis judul kebiasaan…'
        : mode === 'daily'
        ? 'Tulis judul rutinitas…'
        : 'Tulis judul quest…'
      : mode === 'habit'
      ? 'Enter a habit title…'
      : mode === 'daily'
      ? 'Enter a daily title…'
      : 'Enter a quest title…';

  const addLabel = lang === 'id' ? 'Tambah' : 'Add';
  const cancelLabel = lang === 'id' ? 'Batal' : 'Cancel';

  return (
    <>
      <button
        type="button"
        onClick={() => {
          setMode('habit');
          setTitle('');
          setOpen(true);
        }}
        className="fixed bottom-5 left-5 z-[80] w-12 h-12 rounded-full bg-amber-500 hover:bg-amber-400 text-slate-950 flex items-center justify-center shadow-lg shadow-amber-500/30 transition-all"
        title="Quick Add"
      >
        <Plus className="w-6 h-6" />
      </button>

      {open && (
        <div className="fixed inset-0 z-[70] flex items-start justify-center pt-24 p-4 bg-slate-950/70 backdrop-blur-sm">
          <form
            onSubmit={submit}
            className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-5 shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Tambah Cepat' : 'Quick Add'}</h3>
              <button type="button" onClick={() => setOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => setMode(m.key)}
                  className={`flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl text-xs font-bold border transition-colors ${
                    mode === m.key
                      ? 'bg-amber-500/20 border-amber-500/50 text-amber-300'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {m.icon}
                  {lang === 'id' ? m.labelId : m.labelEn}
                </button>
              ))}
            </div>

            <input
              type="text"
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={placeholder}
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
            />

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs"
              >
                {cancelLabel}
              </button>
              <button
                type="submit"
                disabled={!title.trim()}
                className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-40 text-slate-950 font-bold text-xs"
              >
                {addLabel}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
};
