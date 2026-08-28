/**
 * UndoToast — parity for the PyQt `UndoToast` (task deleted → restore).
 *
 * Shown briefly after a task is soft-deleted (via trash_bin). Reads the last
 * delete from GameContext and offers an "Undo" button that restores it by
 * calling the /api/trash/restore endpoint. Auto-labels from localised text.
 */
import React, { useEffect } from 'react';
import { useGame } from '../context/GameContext';
import { Undo2 } from 'lucide-react';

export const UndoToast: React.FC = () => {
  const { lastDelete, undoDelete, lang } = useGame();
  const [visible, setVisible] = React.useState(false);

  useEffect(() => {
    if (lastDelete) {
      setVisible(true);
      const t = setTimeout(() => setVisible(false), 6000);
      return () => clearTimeout(t);
    }
    setVisible(false);
  }, [lastDelete]);

  if (!lastDelete || !visible) return null;

  const label = lang === 'id' ? 'Tugas dihapus' : 'Task deleted';

  return (
    <div className="fixed bottom-5 right-5 z-[80] flex items-center gap-3 px-4 py-3 rounded-xl bg-slate-800 border border-slate-600 shadow-2xl text-sm max-w-sm">
      <div className="min-w-0">
        <p className="text-slate-100 font-semibold truncate">{label}</p>
        <p className="text-xs text-slate-400 truncate">{lastDelete.label}</p>
      </div>
      <button
        type="button"
        onClick={() => {
          undoDelete();
          setVisible(false);
        }}
        className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs whitespace-nowrap flex items-center gap-1"
      >
        <Undo2 className="w-3.5 h-3.5" />
        {lang === 'id' ? 'Urungkan' : 'Undo'}
      </button>
    </div>
  );
};
