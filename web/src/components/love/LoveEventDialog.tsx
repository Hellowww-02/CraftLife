/**
 * LoveEventDialog.tsx — dialog Tambah/Edit acara Love Space (A09).
 *
 * Menutup dua lubang yang ditemukan saat audit tab `plans`:
 *  1. **catatan event** — `LoveSpaceView` sudah menyimpan state `evNotes` dan mengirimnya
 *     ke `loveEvent({... notes: evNotes})`, tetapi tidak ada satu pun input yang mengikatnya,
 *     jadi catatan mustahil diisi. Dialog ini punya textarea catatan yang benar-benar terhubung.
 *  2. **edit event** — dulu hanya bisa hapus. Dialog yang sama dipakai dua mode (Tambah/Edit).
 *
 * Plus konsep baru: **Special Day** (ikon, lokasi, ulang tiap tahun, pengingat H-n) dengan
 * pratinjau hitung mundur langsung saat tanggal dipilih.
 */
import React, { useMemo, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { X, CalendarDays, MapPin, Bell, Repeat, Star, StickyNote, Check } from 'lucide-react';
import { daysUntil, nextOccurrence } from './eventUtils';

export type LoveEventCategory = 'date' | 'gift' | 'milestone' | 'dream' | 'anniversary' | 'trip';

export interface LoveEventForm {
  id?: string;
  title: string;
  date: string;
  category: string;
  icon: string;
  location: string;
  notes: string;
  isSpecial: boolean;
  recurring: 'none' | 'yearly';
  remindDaysBefore: number;
}

export interface LoveEventDialogProps {
  open: boolean;
  mode: 'add' | 'edit';
  initial?: Partial<LoveEventForm> | null;
  onClose: () => void;
  onSave: (data: LoveEventForm) => void;
  saving?: boolean;
  today?: string;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

/** Kategori + ikon bawaan (label i18n: `love_category_<id>`). */
export const EVENT_CATEGORIES: Array<{ id: LoveEventCategory; icon: string }> = [
  { id: 'date', icon: '💕' },
  { id: 'gift', icon: '🎁' },
  { id: 'milestone', icon: '🏆' },
  { id: 'dream', icon: '🌟' },
  { id: 'anniversary', icon: '💞' },
  { id: 'trip', icon: '✈️' },
];

export const EVENT_ICONS = ['💕', '🎂', '🎉', '💍', '✈️', '🍽️', '🎁', '🏖️', '🎬', '🌹', '⭐', '🏆'];

export const REMIND_OPTIONS = [0, 1, 3, 7, 14, 30];

export const EMPTY_EVENT: LoveEventForm = {
  title: '', date: '', category: 'date', icon: '', location: '', notes: '',
  isSpecial: false, recurring: 'none', remindDaysBefore: 0,
};

/**
 * Validasi formulir acara — dipisah agar bisa diuji tanpa DOM.
 * Mengembalikan "" bila sah, atau kunci pesan kesalahan (i18n).
 */
export function validateEventForm(form: { title?: string; date?: string }): string {
  if (!String(form?.title || '').trim()) return 'love_event_title_required';
  if (!String(form?.date || '').trim()) return 'love_event_date_required';
  return '';
}

/** Nilai awal formulir dari data acara (dipakai juga oleh mode Edit). */
export function buildInitialForm(initial?: Partial<LoveEventForm> | null): LoveEventForm {
  return {
    ...EMPTY_EVENT,
    ...(initial || {}),
    title: String(initial?.title || ''),
    date: String(initial?.date || ''),
    category: String(initial?.category || 'date'),
    icon: String(initial?.icon || ''),
    location: String(initial?.location || ''),
    notes: String(initial?.notes || ''),
    isSpecial: Boolean(initial?.isSpecial),
    recurring: initial?.recurring === 'yearly' ? 'yearly' : 'none',
    remindDaysBefore: Number(initial?.remindDaysBefore || 0),
  };
}

const LoveEventDialog: React.FC<LoveEventDialogProps> = ({
  open, mode, initial, onClose, onSave, saving, today, tr,
}) => {
  useEscapeClose(open, onClose);
  const trapRef = useFocusTrap<HTMLDivElement>(open);
  // Nilai awal dihitung saat render (bukan lewat useEffect) supaya mode edit langsung
  // terisi — termasuk catatan — dan bisa diverifikasi dengan render server.
  // Parent me-remount lewat prop `key` setiap kali dialog dibuka.
  const [form, setForm] = useState<LoveEventForm>(() => buildInitialForm(initial));
  const [err, setErr] = useState('');

  const set = <K extends keyof LoveEventForm>(key: K, value: LoveEventForm[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  // Pratinjau hitung mundur (dihitung ulang setiap tanggal/ulang-tahun berubah).
  const preview = useMemo(() => {
    const target = form.recurring === 'yearly'
      ? nextOccurrence(form.date, 'yearly', today)
      : form.date;
    const delta = daysUntil(target, today);
    return { target, delta };
  }, [form.date, form.recurring, today]);

  const previewText = () => {
    if (!form.date || preview.delta === null) {
      return tr('love_event_pick_date', {}, 'Pilih tanggal untuk melihat hitung mundurnya.');
    }
    if (preview.delta === 0) return tr('love_event_today', {}, 'Hari ini!');
    if (preview.delta < 0) {
      return tr('love_event_in_past', { n: Math.abs(preview.delta) },
        `Sudah lewat ${Math.abs(preview.delta)} hari (bisa dijadikan hari istimewa tahunan).`);
    }
    if (preview.delta === 1) return tr('love_event_tomorrow', {}, 'Besok!');
    return tr('love_event_in_days', { n: preview.delta }, `${preview.delta} hari lagi`);
  };

  const submit = () => {
    const problem = validateEventForm(form);
    if (problem) {
      setErr(tr(problem, {},
        problem === 'love_event_title_required'
          ? 'Judul acara wajib diisi.'
          : 'Tanggal acara wajib diisi.'));
      return;
    }
    setErr('');
    onSave({
      ...form,
      title: form.title.trim(),
      location: form.location.trim(),
      notes: form.notes.trim(),
      icon: form.icon.trim(),
      recurring: form.isSpecial ? form.recurring : 'none',
      remindDaysBefore: form.isSpecial ? Number(form.remindDaysBefore || 0) : 0,
    });
  };

  if (!open) return null;

  const lbl = 'text-[10px] font-bold uppercase tracking-wider text-slate-400';
  const inputCls = 'ct-input w-full px-2.5 py-2 rounded-lg text-slate-200 text-xs';

  return (
    <div className="ct-backdrop fixed inset-0 z-[120] flex items-center justify-center p-4" onClick={onClose}>
      <div
        ref={trapRef}
        className="ct-dialog w-full max-w-lg p-5 space-y-3.5 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
            <CalendarDays className="w-4 h-4 text-rose-400" />
            {mode === 'edit'
              ? tr('love_event_edit_title', {}, 'Edit acara')
              : tr('love_event_add_title', {}, 'Tambah acara')}
          </h3>
          <button onClick={onClose} className="ct-act" title={tr('msg_cancel', {}, 'Batal')}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Judul */}
        <div className="space-y-1">
          <label className={lbl}>{tr('love_title_label', {}, 'Judul')}</label>
          <input
            autoFocus
            value={form.title}
            onChange={(e) => set('title', e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') submit(); }}
            className={inputCls}
            placeholder={tr('love_event_title_ph', {}, 'mis. Kencan ke pameran, Ulang tahun Sayang')}
          />
        </div>

        {/* Tanggal + kategori */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className={lbl}>{tr('love_event_date', {}, 'Tanggal')}</label>
            <input
              type="date"
              value={form.date}
              onChange={(e) => set('date', e.target.value)}
              className={inputCls}
            />
          </div>
          <div className="space-y-1">
            <label className={lbl}>{tr('love_event_location', {}, 'Lokasi')}</label>
            <div className="relative">
              <MapPin className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                value={form.location}
                onChange={(e) => set('location', e.target.value)}
                className={`${inputCls} pl-7`}
                placeholder={tr('love_event_location_ph', {}, 'mis. Rumah, restoran, kota')}
              />
            </div>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className={lbl}>{tr('love_event_category', {}, 'Kategori')}</label>
          <div className="flex flex-wrap gap-1.5">
            {EVENT_CATEGORIES.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => set('category', c.id)}
                className={`ct-btn ct-btn-sm ${form.category === c.id ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
              >
                <span className="mr-1">{c.icon}</span>
                {tr(`love_category_${c.id}`, {}, c.id)}
              </button>
            ))}
          </div>
        </div>

        {/* Ikon */}
        <div className="space-y-1.5">
          <label className={lbl}>{tr('love_event_icon', {}, 'Ikon')}</label>
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => set('icon', '')}
              className={`ct-btn ct-btn-sm ${!form.icon ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
              title={tr('love_event_icon_default', {}, 'Ikon kategori')}
            >
              {tr('love_event_icon_auto', {}, 'Otomatis')}
            </button>
            {EVENT_ICONS.map((ic) => (
              <button
                key={ic}
                type="button"
                onClick={() => set('icon', ic)}
                className={`w-8 h-8 rounded-lg border text-base leading-none ${form.icon === ic
                  ? 'bg-rose-500/25 border-rose-400/70'
                  : 'bg-slate-800/70 border-slate-700 hover:border-rose-400/50'}`}
              >
                {ic}
              </button>
            ))}
            <input
              value={EVENT_ICONS.includes(form.icon) || !form.icon ? '' : form.icon}
              onChange={(e) => set('icon', e.target.value.slice(0, 4))}
              className={`${inputCls} w-20`}
              placeholder="🙂"
              title={tr('love_event_icon_custom', {}, 'Ikon bebas (emoji)')}
            />
          </div>
        </div>

        {/* Catatan — inti perbaikan A09 */}
        <div className="space-y-1">
          <label className={`${lbl} flex items-center gap-1.5`}>
            <StickyNote className="w-3 h-3" />
            {tr('love_event_notes', {}, 'Catatan')}
          </label>
          <textarea
            value={form.notes}
            onChange={(e) => set('notes', e.target.value)}
            rows={4}
            className={`${inputCls} resize-y leading-relaxed`}
            placeholder={tr('love_event_notes_ph', {},
              'Detail acara, rencana, hadiah, atau hal yang perlu disiapkan…')}
          />
          <p className="text-[10px] text-slate-500">
            {tr('love_event_notes_hint', {},
              'Catatan ini tersimpan bersama acaranya dan tampil di kartu tab Plans.')}
          </p>
        </div>

        {/* Special Day */}
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3 space-y-2.5">
          <button
            type="button"
            onClick={() => set('isSpecial', !form.isSpecial)}
            className="flex items-center gap-2.5 w-full text-left"
          >
            <span className={`w-9 h-5 rounded-full transition-colors relative shrink-0 ${form.isSpecial ? 'bg-rose-500' : 'bg-slate-700'}`}>
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${form.isSpecial ? 'left-[1.25rem]' : 'left-0.5'}`} />
            </span>
            <span className="min-w-0">
              <span className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
                <Star className={`w-3.5 h-3.5 ${form.isSpecial ? 'text-amber-300' : 'text-slate-500'}`} />
                {tr('love_event_special', {}, 'Special Day')}
              </span>
              <span className="block text-[10px] text-slate-500">
                {tr('love_event_special_hint', {},
                  'Tandai sebagai hari istimewa (ulang tahun, anniversary).')}
              </span>
            </span>
          </button>

          {form.isSpecial && (
            <div className="space-y-2.5 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => set('recurring', form.recurring === 'yearly' ? 'none' : 'yearly')}
                className={`ct-btn ct-btn-sm ${form.recurring === 'yearly' ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
              >
                <Repeat className="w-3.5 h-3.5 mr-1.5" />
                {tr('love_event_recurring', {}, 'Ulangi setiap tahun')}
                {form.recurring === 'yearly' && <Check className="w-3 h-3 ml-1.5" />}
              </button>
              <div className="space-y-1.5">
                <label className={`${lbl} flex items-center gap-1.5`}>
                  <Bell className="w-3 h-3" />
                  {tr('love_event_remind_before', {}, 'Ingatkan sebelumnya')}
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {REMIND_OPTIONS.map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => set('remindDaysBefore', n)}
                      className={`ct-btn ct-btn-sm ${form.remindDaysBefore === n ? 'ct-btn-rose' : 'ct-btn-secondary'}`}
                    >
                      {n === 0
                        ? tr('love_event_remind_none', {}, 'Tanpa pengingat')
                        : tr('love_event_remind_days', { n }, `${n} hari sebelum`)}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Pratinjau */}
        <div
          data-testid="love-event-preview"
          className="flex items-center justify-between gap-2 rounded-xl bg-rose-500/10 border border-rose-500/25 px-3 py-2"
        >
          <span className="text-[11px] font-bold text-rose-200">{previewText()}</span>
          {preview.target && (
            <span className="text-[10px] text-slate-400 tabular-nums">
              {form.recurring === 'yearly'
                ? tr('love_event_next_yearly', { date: preview.target }, `Berikutnya: ${preview.target}`)
                : preview.target}
            </span>
          )}
        </div>

        {err && <p className="text-[11px] text-rose-400 font-bold">{err}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <button type="button" className="ct-btn ct-btn-secondary ct-btn-sm" onClick={onClose}>
            {tr('msg_cancel', {}, 'Batal')}
          </button>
          <button
            type="button"
            className="ct-btn ct-btn-rose ct-btn-sm disabled:opacity-60"
            disabled={!!saving}
            onClick={submit}
          >
            {saving
              ? tr('love_event_saving', {}, 'Menyimpan…')
              : mode === 'edit'
                ? tr('love_event_save', {}, 'Simpan perubahan')
                : tr('love_event_create', {}, 'Tambah acara')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoveEventDialog;
