/**
 * LoveBucketDialog.tsx — dialog Tambah/Edit item Bucket List Love Space (A10).
 *
 * Sebelumnya Bucket List hanya punya satu input judul + checkbox + hapus
 * (`LoveSpaceView` L1063–1090 versi lama): tidak ada kategori, target tanggal,
 * catatan, maupun prioritas. Dialog ini menutup semuanya sekaligus, plus
 * pratinjau hitung mundur target dan (di mode Edit) penanda "sudah tercapai".
 */
import React, { useState } from 'react';
import { X, CalendarDays, Star, StickyNote, CheckSquare, ListChecks } from 'lucide-react';
import { BUCKET_CATEGORIES, BUCKET_PRIORITIES, daysTo, targetBadge } from './memoryUtils';

export interface LoveBucketForm {
  id?: string;
  title: string;
  category: string;
  targetDate: string;
  notes: string;
  priority: number;
  isCompleted: boolean;
}

export interface LoveBucketDialogProps {
  open: boolean;
  mode: 'add' | 'edit';
  initial?: Partial<LoveBucketForm> | null;
  onClose: () => void;
  onSave: (data: LoveBucketForm) => void;
  saving?: boolean;
  today?: string;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

export const EMPTY_BUCKET: LoveBucketForm = {
  title: '', category: 'dream', targetDate: '', notes: '', priority: 0, isCompleted: false,
};

/** Validasi formulir bucket — "" bila sah, atau kunci pesan kesalahan (i18n). */
export function validateBucketForm(form: { title?: string }): string {
  if (!String(form?.title || '').trim()) return 'love_bucket_title_required';
  return '';
}

/** Nilai awal formulir dari data item (dipakai juga oleh mode Edit). */
export function buildInitialBucketForm(initial?: Partial<LoveBucketForm> | null): LoveBucketForm {
  return {
    ...EMPTY_BUCKET,
    ...(initial || {}),
    title: String(initial?.title || ''),
    category: String(initial?.category || 'dream'),
    targetDate: String(initial?.targetDate || '').slice(0, 10),
    notes: String(initial?.notes || ''),
    priority: Math.max(0, Math.min(3, Number(initial?.priority || 0))),
    isCompleted: !!initial?.isCompleted,
  };
}

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';

const LoveBucketDialog: React.FC<LoveBucketDialogProps> = ({
  open, mode, initial, onClose, onSave, saving, today, tr,
}) => {
  const [form, setForm] = useState<LoveBucketForm>(() => buildInitialBucketForm(initial));
  const [error, setError] = useState('');
  if (!open) return null;

  const set = <K extends keyof LoveBucketForm>(key: K, value: LoveBucketForm[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const submit = () => {
    const msg = validateBucketForm(form);
    if (msg) { setError(msg); return; }
    setError('');
    onSave({ ...form, title: form.title.trim(), notes: form.notes.trim() });
  };

  const days = form.targetDate ? daysTo(form.targetDate, today) : null;
  const kind = targetBadge(days);
  const targetHint = (() => {
    if (!form.targetDate || days === null) return '';
    if (kind === 'overdue') {
      return tr('love_bucket_target_past', { n: Math.abs(days) },
        `Target sudah lewat ${Math.abs(days)} hari — perbarui atau tandai tercapai.`);
    }
    if (kind === 'today') return tr('love_event_today', undefined, 'Hari ini!');
    return tr('love_event_in_days', { n: days }, `${days} hari lagi`);
  })();

  return (
    <div className="ct-backdrop fixed inset-0 z-[120] flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="ct-dialog w-full max-w-lg p-5 space-y-3 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="love-bucket-dialog"
      >
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
            <ListChecks className="w-4 h-4 text-rose-400" />
            {mode === 'edit'
              ? tr('love_bucket_edit_title', undefined, 'Edit item bucket list')
              : tr('love_bucket_add_title', undefined, 'Tambah item bucket list')}
          </h3>
          <button type="button" onClick={onClose} className="ct-act" aria-label="close"><X className="w-4 h-4" /></button>
        </div>

        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {tr('love_title_label', undefined, 'Judul')}
          </label>
          <input
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            className={inputCls}
            placeholder={tr('love_bucket_title_ph', undefined, 'mis. Nonton konser bareng, umrah, beli rumah')}
          />
        </div>

        {/* Kategori */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {tr('love_bucket_category', undefined, 'Kategori')}
          </label>
          <div className="flex flex-wrap gap-1.5">
            {BUCKET_CATEGORIES.map((cat) => (
              <button
                key={cat.id}
                type="button"
                data-testid="love-bucket-category"
                onClick={() => set('category', cat.id)}
                className={`px-2.5 h-8 rounded-lg border text-[11px] flex items-center gap-1.5 ${
                  form.category === cat.id
                    ? 'border-rose-500 bg-rose-500/15 text-rose-100'
                    : 'border-slate-700 bg-slate-900/60 text-slate-300 hover:border-rose-500/50'
                }`}
              >
                <span>{cat.icon}</span>
                {tr(`love_bucket_category_${cat.id}`, undefined, cat.id)}
              </button>
            ))}
          </div>
        </div>

        {/* Target & prioritas */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          <div className="space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
              <CalendarDays className="w-3 h-3" /> {tr('love_bucket_target_date', undefined, 'Target tanggal')}
            </label>
            <input type="date" value={form.targetDate} onChange={(e) => set('targetDate', e.target.value)} className={inputCls} />
            <p className="text-[10px] text-slate-500" data-testid="love-bucket-target-hint">
              {targetHint || tr('love_bucket_target_optional', undefined, 'Opsional — biarkan kosong bila belum ada target.')}
            </p>
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
              <Star className="w-3 h-3" /> {tr('love_bucket_priority', undefined, 'Prioritas')}
            </label>
            <div className="flex items-center gap-1.5">
              {BUCKET_PRIORITIES.map((p) => (
                <button
                  key={p}
                  type="button"
                  data-testid="love-bucket-priority"
                  onClick={() => set('priority', p)}
                  title={p === 0
                    ? tr('love_bucket_priority_none', undefined, 'Tanpa prioritas')
                    : tr('love_bucket_priority_n', { n: p }, `Prioritas ${p}`)}
                  className={`h-8 px-2 rounded-lg border text-[11px] flex items-center gap-1 ${
                    form.priority === p ? 'border-amber-400/70 bg-amber-400/10 text-amber-200' : 'border-slate-700 text-slate-300'
                  }`}
                >
                  {p === 0 ? tr('love_bucket_priority_none', undefined, 'Tanpa') : '⭐'.repeat(p)}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Catatan */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
            <StickyNote className="w-3 h-3" /> {tr('love_bucket_notes', undefined, 'Catatan')}
          </label>
          <textarea
            value={form.notes}
            onChange={(e) => set('notes', e.target.value)}
            rows={3}
            className={inputCls}
            placeholder={tr('love_bucket_notes_ph', undefined, 'Rencana, biaya, siapa yang mengurus apa…')}
          />
        </div>

        {mode === 'edit' && (
          <button
            type="button"
            onClick={() => set('isCompleted', !form.isCompleted)}
            data-testid="love-bucket-done-toggle"
            className={`w-full flex items-center justify-between px-3 py-2 rounded-xl border text-xs ${
              form.isCompleted ? 'border-emerald-400/60 bg-emerald-400/10 text-emerald-200' : 'border-slate-700 text-slate-300'
            }`}
          >
            <span className="flex items-center gap-2 font-bold">
              <CheckSquare className="w-3.5 h-3.5" />
              {form.isCompleted
                ? tr('love_bucket_mark_open', undefined, 'Tandai belum tercapai')
                : tr('love_bucket_mark_done', undefined, 'Tandai sudah tercapai')}
            </span>
            <span>{form.isCompleted ? tr('love_bucket_filter_done', undefined, 'Selesai') : tr('love_bucket_filter_open', undefined, 'Belum')}</span>
          </button>
        )}

        {error && <p className="text-[11px] text-rose-300" data-testid="love-bucket-error">{tr(error, undefined, error)}</p>}

        <div className="flex justify-end gap-2">
          <button type="button" className={btnGhost} onClick={onClose}>{tr('msg_cancel', undefined, 'Batal')}</button>
          <button type="button" className={btnRose} onClick={submit} disabled={!!saving} data-testid="love-bucket-save">
            {saving
              ? tr('love_bucket_saving', undefined, 'Menyimpan…')
              : mode === 'edit'
                ? tr('love_bucket_save', undefined, 'Simpan perubahan')
                : tr('love_bucket_create', undefined, 'Tambah item')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoveBucketDialog;
