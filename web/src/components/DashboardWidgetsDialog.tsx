import React, { useEffect, useState } from 'react';
import { rpg } from '../api/rpg';
import { X, Eye, EyeOff, ChevronUp, ChevronDown } from 'lucide-react';

type WidgetCfg = { key: string; visible: boolean; compact: boolean };

export const DashboardWidgetsDialog: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [cfg, setCfg] = useState<WidgetCfg[]>([]);
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    rpg.getDashboardWidgets().then((d) => {
      const w = d?.widgets;
      if (Array.isArray(w) && w.length) {
        setCfg(w.map((x: any) => ({ key: x.key, visible: x.visible !== false, compact: !!x.compact })));
      } else {
        setCfg([]);
      }
      setLoaded(true);
    }).catch(() => setLoaded(true));
  }, []);

  const labels: Record<string, string> = {
    heatmap: 'Heatmap 28 hari',
    insights: 'Ringkasan / Insight',
    health_chart: 'Grafik Kesehatan',
  };

  const move = (i: number, dir: -1 | 1) => {
    setCfg((prev) => {
      const next = [...prev];
      const j = i + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  };

  const toggleVisible = (i: number) => setCfg((prev) => prev.map((c, idx) => (idx === i ? { ...c, visible: !c.visible } : c)));
  const toggleCompact = (i: number) => setCfg((prev) => prev.map((c, idx) => (idx === i ? { ...c, compact: !c.compact } : c)));

  const save = async () => {
    setSaving(true);
    try {
      await rpg.saveDashboardWidgets(cfg);
      onClose();
    } catch {
      setSaving(false);
    }
  };

  if (!loaded) return null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-black text-slate-100">Atur Widget Dashboard</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-200"><X className="w-5 h-5" /></button>
        </div>
        <p className="text-xs text-slate-400">Aktifkan/nonaktifkan, ubah urutan, dan atur kepadatan widget di beranda.</p>
        {cfg.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">Widget default akan dipakai.</p>
        ) : (
          <div className="space-y-2">
            {cfg.map((c, i) => (
              <div key={c.key} className="flex items-center justify-between gap-2 p-3 rounded-xl bg-slate-800 border border-slate-700">
                <div className="flex items-center gap-2">
                  <button onClick={() => move(i, -1)} className="p-1 text-slate-400 hover:text-slate-200"><ChevronUp className="w-4 h-4" /></button>
                  <button onClick={() => move(i, 1)} className="p-1 text-slate-400 hover:text-slate-200"><ChevronDown className="w-4 h-4" /></button>
                  <span className="text-sm font-semibold text-slate-100">{labels[c.key] || c.key}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => toggleVisible(i)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold flex items-center gap-1 ${c.visible ? 'bg-emerald-500/20 text-emerald-300' : 'bg-slate-700 text-slate-400'}`}
                  >
                    {c.visible ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
                    {c.visible ? 'Tampil' : 'Sembunyi'}
                  </button>
                  <button
                    onClick={() => toggleCompact(i)}
                    className={`px-2 py-1 rounded-lg text-[10px] font-bold ${c.compact ? 'bg-amber-500/20 text-amber-300' : 'bg-slate-700 text-slate-400'}`}
                  >
                    {c.compact ? 'Ringkas' : 'Lebar'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="flex items-center justify-end gap-2 pt-1">
          <button onClick={onClose} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold text-xs">Batal</button>
          <button onClick={save} disabled={saving || cfg.length === 0} className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs">Simpan</button>
        </div>
      </div>
    </div>
  );
};
