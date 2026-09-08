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
        className="ct-fab fixed bottom-5 left-5 z-[80] w-12 h-12 rounded-full flex items-center justify-center"
        title="Quick Add"
      >
        <Plus className="w-6 h-6" />
      </button>

      {open && (
        <div className="ct-backdrop fixed inset-0 z-[70] flex items-start justify-center pt-24 p-4">
          <form
            onSubmit={submit}
            className="ct-dialog max-w-md w-full p-5 space-y-4"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Tambah Cepat' : 'Quick Add'}</h3>
              <button type="button" onClick={() => setOpen(false)} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-2">
              {MODES.map((m) => (
                <button
                  key={m.key}
                  type="button"
                  onClick={() => setMode(m.key)}
                  className={`flex items-center justify-center gap-1.5 px-2 py-2 rounded-xl text-xs font-bold border transition-colors ct-press ${
                    mode === m.key
                      ? 'ct-socket border-amber-500/50 bg-amber-500/15 text-amber-300'
                      : 'ct-socket border-slate-700 bg-slate-800/60 text-slate-300 hover:bg-slate-700'
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
              className="ct-input w-full px-3 py-2 rounded-xl focus:border-transparent"
            />

            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="ct-btn ct-btn-secondary ct-btn-sm"
              >
                {cancelLabel}
              </button>
              <button
                type="submit"
                disabled={!title.trim()}
                className="ct-btn ct-btn-gold ct-btn-sm"
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
