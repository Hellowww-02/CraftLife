import React, { useEffect, useState } from 'react';
import { rpg } from '../api/rpg';
import { X, Sparkles } from 'lucide-react';

type Wrapped = {
  year: number;
  total_done: number;
  by_type: Record<string, number>;
  active_days: number;
  best_day: string | null;
  best_day_count: number;
  top_habits: { name: string; icon: string; count: number }[];
  focus_sessions: number;
  focus_minutes: number;
  income: number;
  expense: number;
  level: number;
  longest_streak: number;
};

export const YearWrappedDialog: React.FC<{ onClose: () => void; displayName?: string }> = ({ onClose, displayName }) => {
  const [w, setW] = useState<Wrapped | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    rpg.yearWrapped().then((d) => setW(d?.wrapped || null)).catch(() => setW(null)).finally(() => setLoaded(true));
  }, []);

  if (!loaded) return null;

  const money = (v: number) => `Rp ${Math.round(Number(v || 0)).toLocaleString()}`;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="max-w-md w-full bg-slate-900 border border-amber-500/40 rounded-2xl p-6 shadow-2xl space-y-3 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-black text-amber-300 flex items-center gap-2">
            <Sparkles className="w-5 h-5" /> CraftLife Wrapped {(w?.year) || ''}
          </h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
        </div>
        {!w || (!w.total_done && !w.focus_sessions) ? (
          <p className="text-sm text-slate-400 text-center py-10">Belum ada aktivitas di tahun ini. Mulai catat task-mu!</p>
        ) : (
          <div className="space-y-3">
            <div className="text-center">
              <div className="text-xl font-black text-amber-200">⭐ {displayName || 'Penyintas'} — Ringkasan {w.year} ⭐</div>
            </div>
            <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-4 space-y-2 text-center">
              <div className="text-4xl font-black text-amber-300">{w.total_done}</div>
              <div className="text-xs text-slate-400">tugas diselesaikan</div>
              <div className="text-xs text-slate-300">{w.active_days} hari aktif</div>
              {w.best_day && <div className="text-xs text-emerald-300">Hari terbaik: {w.best_day} ({w.best_day_count} tugas)</div>}
            </div>
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3">
                <div className="text-lg font-black text-sky-300">{w.focus_sessions}</div>
                <div className="text-[10px] text-slate-400">sesi fokus · {w.focus_minutes} mnt</div>
              </div>
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3">
                <div className="text-lg font-black text-emerald-300">Lv {w.level}</div>
                <div className="text-[10px] text-slate-400">streak terpanjang {w.longest_streak}</div>
              </div>
            </div>
            {w.top_habits.length > 0 && (
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3 space-y-1">
                <div className="text-[10px] uppercase text-slate-400 font-bold">Kebiasaan teratas</div>
                {w.top_habits.map((h) => (
                  <div key={h.name} className="flex justify-between text-xs text-slate-300">
                    <span>{h.icon} {h.name}</span>
                    <span className="text-amber-300 font-bold">×{h.count}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl bg-emerald-950/40 border border-emerald-500/30 p-3">
                <div className="text-[10px] uppercase text-slate-400 font-bold">Pemasukan total</div>
                <div className="text-sm font-black text-emerald-300">{money(w.income)}</div>
              </div>
              <div className="rounded-xl bg-rose-950/40 border border-rose-500/30 p-3">
                <div className="text-[10px] uppercase text-slate-400 font-bold">Pengeluaran total</div>
                <div className="text-sm font-black text-rose-300">{money(w.expense)}</div>
              </div>
            </div>
          </div>
        )}
        <div className="flex justify-end"><button onClick={onClose} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 font-semibold text-xs">Tutup</button></div>
      </div>
    </div>
  );
};
