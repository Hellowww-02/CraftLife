/**
 * LoveCyclePanel.tsx — tab `cycle` Love Space (fase A11).
 *
 * Isi: statistik siklus, prediksi (periode berikutnya · ovulasi · jendela subur ·
 * keyakinan prediksi), tombol "Jadikan pengingat", pengaturan siklus, dan tabel
 * riwayat yang kini bisa **ditambah manual, diedit, dan diberi catatan**.
 */
import React, { useMemo, useState } from 'react';
import { Bell, Pencil, Plus, Trash2 } from 'lucide-react';
import { NumberInput } from '../NumberInput';
import {
  cycleRows,
  cycleStats,
  effectiveCycleLength,
  fertileWindow,
  predictionConfidence,
  toIso,
  validateCycleForm,
} from './cycleUtils';

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';
const btnDanger = 'ct-btn ct-btn-danger ct-btn-sm';

export interface LoveCyclePanelProps {
  t: (k: string, fb: string) => string;
  trv: (k: string, vars: Record<string, string | number>, fb: string) => string;
  loveSpace: any;
  today: string;
  onSaveSettings: (settings: { trackedPerson: string; lastPeriodStart: string; cycleLength: number; periodLength: number }) => void;
  onLogToday: () => void;
  onAddCycle: (payload: { startDate: string; endDate?: string; notes?: string }) => void;
  onUpdateCycle: (id: string, payload: { startDate?: string; endDate?: string; notes?: string }) => void;
  onDeleteCycle: (id: string) => void;
  onReminder: (daysBefore: number) => void;
  showToast: (kind: any, title: string, msg: string) => void;
}

export const LoveCyclePanel: React.FC<LoveCyclePanelProps> = ({
  t, trv, loveSpace, today, onSaveSettings, onLogToday, onAddCycle, onUpdateCycle, onDeleteCycle, onReminder, showToast,
}) => {
  const cs = loveSpace.cycleSettings || { trackedPerson: 'partner', lastPeriodStart: '', cycleLength: 28, periodLength: 5 };
  const cycles = loveSpace.cycles || [];
  const prediction = loveSpace.cyclePrediction;

  const [cycPerson, setCycPerson] = useState<'self' | 'partner'>(cs.trackedPerson || 'partner');
  const [cycStart, setCycStart] = useState(cs.lastPeriodStart || today);
  const [cycLen, setCycLen] = useState<number>(cs.cycleLength || 28);
  const [perLen, setPerLen] = useState<number>(cs.periodLength || 5);

  // form tambah/edit riwayat siklus
  const [editing, setEditing] = useState<{ id: string; startDate: string; endDate: string; notes: string } | null>(null);
  const [adding, setAdding] = useState(false);
  const [newCycle, setNewCycle] = useState({ startDate: '', endDate: '', notes: '' });

  const stats = useMemo(() => cycleStats(cycles, today), [cycles, today]);
  const confidence = useMemo(() => predictionConfidence(cycles), [cycles]);
  const rows = useMemo(() => cycleRows(cycles), [cycles]);
  const avgLength = useMemo(() => effectiveCycleLength(cycles, cs.cycleLength), [cycles, cs.cycleLength]);
  const fertile = useMemo(
    () => (prediction?.predictedStart ? fertileWindow(prediction.predictedStart, avgLength) : null),
    [prediction, avgLength],
  );

  const confidenceKey = `love_cycle_confidence_${confidence.level}`;
  const confidenceText = t(confidenceKey, confidence.level);

  return (
    <div className="space-y-4" data-testid="love-cycle-panel">
      {/* ── Statistik ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: '🗓️', label: String(stats.count), sub: t('love_cycle_stat_count', 'Siklus terlog'), testid: 'love-cycle-stat-count' },
          { icon: '📏', label: stats.avgLength ? `${stats.avgLength}` : '—', sub: t('love_cycle_stat_avg', 'Rata-rata panjang (hari)'), testid: 'love-cycle-stat-avg' },
          { icon: '⏱️', label: stats.lastLength ? `${stats.lastLength}` : (stats.running ? t('love_cycle_running', 'Berjalan') : '—'), sub: t('love_cycle_stat_last', 'Siklus terakhir'), testid: 'love-cycle-stat-last' },
          { icon: '🩸', label: String(cs.periodLength || 5), sub: t('love_period_length', 'Lama periode'), testid: 'love-cycle-stat-period' },
        ].map((c) => (
          <div key={c.testid} data-testid={c.testid} className="p-3 rounded-2xl bg-slate-900/70 border border-slate-800">
            <div className="text-lg leading-none">{c.icon}</div>
            <div className="text-sm font-bold text-slate-100 mt-1 truncate">{c.label}</div>
            <div className="text-[10px] text-slate-500">{c.sub}</div>
          </div>
        ))}
      </div>

      {/* ── Prediksi ── */}
      <div className="p-5 bg-slate-900/70 border border-rose-500/20 rounded-2xl space-y-3" data-testid="love-cycle-prediction">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_cycle_next', 'Perkiraan siklus berikutnya')}</h3>
          {/* A11: badge keyakinan hanya bermakna bila ada prediksi — tanpa itu
              panel sudah menampilkan arahan "belum cukup data". */}
          {prediction?.predictedStart && (
            <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700 bg-slate-800 text-slate-300" data-testid="love-cycle-confidence">
              {trv('love_cycle_confidence', { level: confidenceText }, `Keyakinan prediksi: ${confidenceText}`)}
            </span>
          )}
        </div>
        {prediction ? (
          <>
            <p className="text-sm text-rose-300 font-bold" data-testid="love-cycle-range">
              {trv('love_cycle_range', { start: prediction.predictedStart, end: prediction.predictedEnd }, `Perkiraan mulai ${prediction.predictedStart} hingga ${prediction.predictedEnd}`)}
            </p>
            <p className="text-xs text-slate-400">{trv('love_cycle_days_until', { days: prediction.daysUntil }, `${prediction.daysUntil} hari dari hari ini`)}</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500">{t('love_cycle_ovulation', 'Perkiraan ovulasi')}</div>
                <div className="text-sm font-bold text-slate-100" data-testid="love-cycle-ovulation">{fertile?.ovulation || '—'}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500">{t('love_cycle_fertile', 'Jendela subur')}</div>
                <div className="text-sm font-bold text-slate-100" data-testid="love-cycle-fertile">
                  {fertile ? `${fertile.start} → ${fertile.end}` : '—'}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
                <div className="text-[10px] text-slate-500">{t('love_cycle_based_on', 'Dasar prediksi')}</div>
                <div className="text-sm font-bold text-slate-100" data-testid="love-cycle-based">
                  {trv('love_cycle_based_on_value', { n: confidence.samples, spread: confidence.spread }, `${confidence.samples} siklus · sebaran ${confidence.spread} hari`)}
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button
                type="button"
                className={btnRose}
                data-testid="love-cycle-reminder"
                onClick={() => onReminder(3)}
              >
                <Bell className="w-3.5 h-3.5 inline mr-1" />
                {trv('love_cycle_add_reminder', { n: 3 }, 'Jadikan pengingat (H-3)')}
              </button>
              <button
                type="button"
                className={btnGhost}
                onClick={() => onReminder(1)}
              >
                {trv('love_cycle_add_reminder', { n: 1 }, 'Jadikan pengingat (H-1)')}
              </button>
            </div>
          </>
        ) : (
          <p className="text-sm text-slate-300 font-bold" data-testid="love-cycle-no-data">{t('love_cycle_no_data', 'Belum cukup data untuk prediksi.')}</p>
        )}
        <p className="text-[10px] text-slate-500">{t('love_cycle_disclaimer', 'Prediksi hanya perkiraan — bukan pengganti saran medis.')}</p>
      </div>

      {/* ── Pengaturan ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="space-y-1 text-xs">
            <span className="block text-slate-400">{t('love_cycle_for', 'Siklus untuk')}</span>
            <select value={cycPerson} onChange={(e) => setCycPerson(e.target.value as 'self' | 'partner')} className={inputCls}>
              <option value="partner">{loveSpace.partnerName || 'Partner'}</option>
              <option value="self">{t('love_myself', 'Diriku')}</option>
            </select>
          </label>
          <label className="space-y-1 text-xs">
            <span className="block text-slate-400">{t('love_last_period', 'Periode terakhir')}</span>
            <input type="date" value={cycStart} onChange={(e) => setCycStart(e.target.value)} className={inputCls} />
          </label>
          <label className="space-y-1 text-xs">
            <span className="block text-slate-400">{t('love_cycle_length', 'Panjang siklus')}</span>
            <NumberInput value={cycLen} onValueChange={setCycLen} min={20} max={45} integer emptyValue={28} inputClassName={inputCls} />
          </label>
          <label className="space-y-1 text-xs">
            <span className="block text-slate-400">{t('love_period_length', 'Lama periode')}</span>
            <NumberInput value={perLen} onValueChange={setPerLen} min={2} max={10} integer emptyValue={5} inputClassName={inputCls} />
          </label>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onSaveSettings({ trackedPerson: cycPerson, lastPeriodStart: cycStart, cycleLength: cycLen, periodLength: perLen })}
            className={btnRose}
          >
            {t('love_save_cycle', 'Simpan Pengaturan Siklus')}
          </button>
          <button type="button" onClick={onLogToday} className={btnGhost}>{t('love_log_cycle', 'Catat Periode Hari Ini')}</button>
        </div>
      </div>

      {/* ── Riwayat siklus ── */}
      <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-cycle-history">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-bold text-sm text-slate-200 flex-1">{t('love_cycle_history', 'Riwayat siklus')}</h3>
          {/* kolom ringkas: rata-rata & sebaran */}
          <span className="text-[10px] text-slate-500">
            {trv('love_cycle_history_summary', { n: stats.count, avg: stats.avgLength || '—' }, `${stats.count} siklus · rata-rata ${stats.avgLength || '—'} hari`)}
          </span>
          <button
            type="button"
            className={btnGhost}
            data-testid="love-cycle-add-toggle"
            onClick={() => { setAdding((v) => !v); setNewCycle({ startDate: today, endDate: '', notes: '' }); }}
          >
            <Plus className="w-3.5 h-3.5 inline mr-1" />{t('love_cycle_add', 'Tambah manual')}
          </button>
        </div>

        {adding && (
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2" data-testid="love-cycle-add-form">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_period_start', 'Mulai')}</span>
                <input type="date" value={newCycle.startDate} onChange={(e) => setNewCycle((f) => ({ ...f, startDate: e.target.value }))} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_period_end', 'Selesai')}</span>
                <input type="date" value={newCycle.endDate} onChange={(e) => setNewCycle((f) => ({ ...f, endDate: e.target.value }))} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_cycle_notes', 'Catatan siklus')}</span>
                <input value={newCycle.notes} onChange={(e) => setNewCycle((f) => ({ ...f, notes: e.target.value }))} className={inputCls} placeholder={t('love_cycle_notes_ph', 'Derita/kram, obat, kondisi…')} />
              </label>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className={btnRose}
                data-testid="love-cycle-add-save"
                onClick={() => {
                  const err = validateCycleForm(newCycle);
                  if (err) { showToast('info', t('msg_error', 'Error'), t(err, 'Tanggal siklus tidak valid.')); return; }
                  onAddCycle({ startDate: toIso(newCycle.startDate), endDate: toIso(newCycle.endDate) || undefined, notes: newCycle.notes });
                  setAdding(false);
                  setNewCycle({ startDate: '', endDate: '', notes: '' });
                }}
              >
                {t('love_cycle_save', 'Simpan siklus')}
              </button>
              <button type="button" className={btnGhost} onClick={() => setAdding(false)}>{t('msg_cancel', 'Batal')}</button>
            </div>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-slate-300">
            <thead>
              <tr className="text-[10px] text-slate-500 text-left">
                <th className="py-1 pr-2 font-normal">{t('love_period_start', 'Mulai')}</th>
                <th className="py-1 pr-2 font-normal">{t('love_period_end', 'Selesai')}</th>
                <th className="py-1 pr-2 font-normal">{t('love_cycle_length', 'Panjang')}</th>
                <th className="py-1 pr-2 font-normal">{t('love_cycle_notes', 'Catatan')}</th>
                <th className="py-1 font-normal text-right">{t('love_actions', 'Aksi')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.id} className="border-t border-slate-800/60" data-testid="love-cycle-row">
                  <td className="py-1 pr-2 whitespace-nowrap">{c.startDate}</td>
                  <td className="py-1 pr-2 whitespace-nowrap">{c.endDate || t('love_cycle_running', 'Berjalan')}</td>
                  <td className="py-1 pr-2 whitespace-nowrap">{c.length ? trv('love_cycle_days_count', { n: c.length }, `${c.length} hari`) : '—'}</td>
                  <td className="py-1 pr-2 max-w-[12rem] truncate" title={c.notes || ''}>{c.notes || '—'}</td>
                  <td className="py-1 text-right whitespace-nowrap">
                    <button
                      type="button"
                      className="p-1 text-slate-400 hover:text-rose-300"
                      title={t('love_cycle_edit_title', 'Edit siklus')}
                      data-testid="love-cycle-edit"
                      onClick={() => setEditing({ id: String(c.id), startDate: c.startDate, endDate: c.endDate || '', notes: c.notes || '' })}
                    >
                      <Pencil className="w-3.5 h-3.5" />
                    </button>
                    <button type="button" className="p-1 text-slate-500 hover:text-rose-400" title={t('love_delete_selected', 'Hapus')} onClick={() => c.id && onDeleteCycle(String(c.id))}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
              {!rows.length && (
                <tr><td colSpan={5} className="py-2 text-slate-500" data-testid="love-cycle-history-empty">{t('love_cycle_history_empty', 'Belum ada siklus terlog — catat periode atau tambahkan manual.')}</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {editing && (
          <div className="p-3 rounded-xl bg-slate-950/60 border border-rose-500/20 space-y-2" data-testid="love-cycle-edit-form">
            <div className="text-[11px] text-rose-200 font-bold">{t('love_cycle_edit_title', 'Edit siklus')}</div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_period_start', 'Mulai')}</span>
                <input type="date" value={editing.startDate} onChange={(e) => setEditing((f) => (f ? { ...f, startDate: e.target.value } : f))} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_period_end', 'Selesai')}</span>
                <input type="date" value={editing.endDate} onChange={(e) => setEditing((f) => (f ? { ...f, endDate: e.target.value } : f))} className={inputCls} />
              </label>
              <label className="space-y-1 text-xs">
                <span className="block text-slate-400">{t('love_cycle_notes', 'Catatan siklus')}</span>
                <input value={editing.notes} onChange={(e) => setEditing((f) => (f ? { ...f, notes: e.target.value } : f))} className={inputCls} />
              </label>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                className={btnRose}
                data-testid="love-cycle-edit-save"
                onClick={() => {
                  const err = validateCycleForm(editing);
                  if (err) { showToast('info', t('msg_error', 'Error'), t(err, 'Tanggal siklus tidak valid.')); return; }
                  onUpdateCycle(editing.id, { startDate: toIso(editing.startDate), endDate: toIso(editing.endDate), notes: editing.notes });
                  setEditing(null);
                }}
              >
                {t('love_cycle_save_edit', 'Simpan perubahan')}
              </button>
              <button type="button" className={btnGhost} onClick={() => setEditing(null)}>{t('msg_cancel', 'Batal')}</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
