/**
 * LoveMemoryDialog.tsx — dialog Tambah/Edit kenangan Love Space (A10).
 *
 * Menutup dua lubang yang ditemukan saat audit tab `memories`:
 *  1. **tidak ada edit** — dulu hanya bisa tambah lalu hapus; kini satu dialog dua mode.
 *  2. **emoji selalu hardcoded 💖** — kini emoji bisa dipilih (atau ditulis sendiri).
 *
 * Plus: tag, bintang favorit, dan **tautan foto** dari galeri Love Space (thumbnail
 * langsung terlihat), sehingga kenangan tidak lagi terputus dari album.
 */
import React, { useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { useFocusTrap } from '../../hooks/useFocusTrap';
import { X, Star, StickyNote, Image as ImageIcon, Tag, Heart, Check } from 'lucide-react';
import { MEMORY_EMOJIS, normalizeTags, tagsToInput } from './memoryUtils';

export interface LoveMemoryForm {
  id?: string;
  title: string;
  date: string;
  description: string;
  emoji: string;
  tags: string;
  isFavorite: boolean;
  photoId: string;
}

export interface GalleryPhoto {
  id: string;
  caption?: string;
  photoDate?: string;
}

export interface LoveMemoryDialogProps {
  open: boolean;
  mode: 'add' | 'edit';
  initial?: Partial<LoveMemoryForm> | null;
  photos?: GalleryPhoto[];
  onClose: () => void;
  onSave: (data: LoveMemoryForm) => void;
  saving?: boolean;
  today?: string;
  photoThumb?: (photoId: string) => string;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

export const EMPTY_MEMORY: LoveMemoryForm = {
  title: '', date: '', description: '', emoji: '💖', tags: '', isFavorite: false, photoId: '',
};

/** Validasi formulir kenangan — "" bila sah, atau kunci pesan kesalahan (i18n). */
export function validateMemoryForm(form: { title?: string; date?: string }): string {
  if (!String(form?.title || '').trim()) return 'love_memory_title_required';
  if (!String(form?.date || '').trim()) return 'love_memory_date_required';
  return '';
}

/** Nilai awal formulir dari data kenangan (dipakai juga oleh mode Edit). */
export function buildInitialMemoryForm(initial?: Partial<LoveMemoryForm> | null): LoveMemoryForm {
  return {
    ...EMPTY_MEMORY,
    ...(initial || {}),
    title: String(initial?.title || ''),
    date: String(initial?.date || '').slice(0, 10),
    description: String(initial?.description || ''),
    emoji: String(initial?.emoji || '💖'),
    tags: typeof initial?.tags === 'string' ? String(initial.tags) : tagsToInput((initial as any)?.tags || []),
    isFavorite: !!initial?.isFavorite,
    photoId: initial?.photoId ? String(initial.photoId) : '',
  };
}

const inputCls = 'ct-input w-full px-2 py-1.5 rounded-lg text-slate-200 text-xs';
const btnRose = 'ct-btn ct-btn-rose ct-btn-sm';
const btnGhost = 'ct-btn ct-btn-secondary ct-btn-sm';

const LoveMemoryDialog: React.FC<LoveMemoryDialogProps> = ({
  open, mode, initial, photos = [], onClose, onSave, saving, today, photoThumb, tr,
}) => {
  useEscapeClose(open, onClose);
  const trapRef = useFocusTrap<HTMLDivElement>(open);
  // Nilai awal dihitung sekali saat mount; pemanggil memakai `key` ber-nonce agar
  // dialog selalu segar (lihat komentar serupa di LoveEventDialog A09).
  const [form, setForm] = useState<LoveMemoryForm>(() => {
    const base = buildInitialMemoryForm(initial);
    if (!base.date && today) base.date = today;
    return base;
  });
  const [error, setError] = useState('');
  const [customEmoji, setCustomEmoji] = useState(false);
  if (!open) return null;

  const set = <K extends keyof LoveMemoryForm>(key: K, value: LoveMemoryForm[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const submit = () => {
    const msg = validateMemoryForm(form);
    if (msg) { setError(msg); return; }
    setError('');
    onSave({
      ...form,
      title: form.title.trim(),
      description: form.description.trim(),
      emoji: (form.emoji || '💖').slice(0, 8),
      tags: normalizeTags(form.tags).join(', '),
    });
  };

  const tagPreview = normalizeTags(form.tags);

  return (
    <div className="ct-backdrop fixed inset-0 z-[120] flex items-center justify-center p-4" onClick={onClose}>
      <div
        ref={trapRef}
        className="ct-dialog w-full max-w-lg p-5 space-y-3 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="love-memory-dialog"
      >
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
            <Heart className="w-4 h-4 text-rose-400" />
            {mode === 'edit'
              ? tr('love_memory_edit_title', undefined, 'Edit kenangan')
              : tr('love_memory_add_title', undefined, 'Tambah kenangan')}
          </h3>
          <button type="button" onClick={onClose} className="ct-act" aria-label="close"><X className="w-4 h-4" /></button>
        </div>

        {/* Emoji */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
            {tr('love_memory_emoji', undefined, 'Emoji kenangan')}
          </label>
          <div className="flex flex-wrap items-center gap-1.5">
            {MEMORY_EMOJIS.map((em) => (
              <button
                key={em}
                type="button"
                onClick={() => { set('emoji', em); setCustomEmoji(false); }}
                data-testid="love-memory-emoji"
                className={`w-8 h-8 rounded-lg border text-base leading-none ${
                  form.emoji === em ? 'border-rose-500 bg-rose-500/15' : 'border-slate-700 bg-slate-900/60 hover:border-rose-500/50'
                }`}
              >{em}</button>
            ))}
            <button
              type="button"
              onClick={() => setCustomEmoji((v) => !v)}
              className={`px-2 h-8 rounded-lg border text-[11px] ${
                customEmoji ? 'border-rose-500 text-rose-200' : 'border-slate-700 text-slate-300'
              }`}
            >{tr('love_memory_emoji_custom', undefined, 'Emoji bebas')}</button>
          </div>
          {customEmoji && (
            <input
              value={form.emoji}
              maxLength={8}
              onChange={(e) => set('emoji', e.target.value)}
              className={inputCls}
              placeholder="🦋"
            />
          )}
        </div>

        {/* Judul & tanggal */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          <div className="md:col-span-2 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
              {tr('love_memory_title', undefined, 'Judul')}
            </label>
            <input
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              className={inputCls}
              placeholder={tr('love_memory_title_ph', undefined, 'mis. Liburan pertama ke Bali')}
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400">
              {tr('love_event_date', undefined, 'Tanggal')}
            </label>
            <input type="date" value={form.date} onChange={(e) => set('date', e.target.value)} className={inputCls} />
          </div>
        </div>

        {/* Tag */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
            <Tag className="w-3 h-3" /> {tr('love_memory_tags', undefined, 'Tag')}
          </label>
          <input
            value={form.tags}
            onChange={(e) => set('tags', e.target.value)}
            className={inputCls}
            placeholder={tr('love_memory_tags_ph', undefined, 'mis. liburan, pertama kali, keluarga')}
          />
          {tagPreview.length > 0 && (
            <div className="flex flex-wrap gap-1" data-testid="love-memory-tag-preview">
              {tagPreview.map((tg) => (
                <span key={tg} className="px-2 py-0.5 rounded-full bg-rose-500/10 text-rose-200 text-[10px] border border-rose-500/25">#{tg}</span>
              ))}
            </div>
          )}
        </div>

        {/* Catatan */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
            <StickyNote className="w-3 h-3" /> {tr('love_memory_notes', undefined, 'Cerita kenangan')}
          </label>
          <textarea
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            rows={3}
            className={inputCls}
            placeholder={tr('love_memory_notes_ph', undefined, 'Apa yang terjadi, siapa yang ada, hal yang bikin ketawa…')}
          />
        </div>

        {/* Foto dari galeri */}
        <div className="space-y-1">
          <label className="text-[11px] font-bold uppercase tracking-wide text-slate-400 flex items-center gap-1">
            <ImageIcon className="w-3 h-3" /> {tr('love_memory_link_photo', undefined, 'Tautkan foto')}
          </label>
          {photos.length ? (
            <div className="flex items-center gap-2">
              <select value={form.photoId} onChange={(e) => set('photoId', e.target.value)} className={inputCls}>
                <option value="">{tr('love_memory_photo_none', undefined, 'Tanpa foto')}</option>
                {photos.map((ph) => (
                  <option key={ph.id} value={ph.id}>
                    {ph.caption || ph.photoDate || `#${ph.id}`}
                  </option>
                ))}
              </select>
              {photoThumb && form.photoId && (
                <img src={photoThumb(form.photoId) || ''} alt="" className="w-10 h-10 rounded-lg object-cover border border-slate-700" />
              )}
            </div>
          ) : (
            <p className="text-[11px] text-slate-500">
              {tr('love_memory_photo_empty', undefined, 'Galeri masih kosong — unggah foto di tab Galeri lalu tautkan di sini.')}
            </p>
          )}
        </div>

        {/* Favorit */}
        <button
          type="button"
          onClick={() => set('isFavorite', !form.isFavorite)}
          data-testid="love-memory-favorite-toggle"
          className={`w-full flex items-center justify-between px-3 py-2 rounded-xl border text-xs ${
            form.isFavorite ? 'border-amber-400/60 bg-amber-400/10 text-amber-200' : 'border-slate-700 text-slate-300'
          }`}
        >
          <span className="flex items-center gap-2 font-bold">
            <Star className={`w-3.5 h-3.5 ${form.isFavorite ? 'text-amber-300' : ''}`} />
            {tr('love_memory_favorite', undefined, 'Tandai favorit')}
          </span>
          <span>{form.isFavorite ? tr('love_memory_favorite_on', undefined, 'Favorit') : tr('love_memory_favorite_off', undefined, 'Biasa')}</span>
        </button>

        {error && (
          <p className="text-[11px] text-rose-300" data-testid="love-memory-error">{tr(error, undefined, error)}</p>
        )}

        <div className="flex justify-end gap-2">
          <button type="button" className={btnGhost} onClick={onClose}>{tr('msg_cancel', undefined, 'Batal')}</button>
          <button type="button" className={btnRose} onClick={submit} disabled={!!saving} data-testid="love-memory-save">
            <Check className="w-3.5 h-3.5 inline mr-1" />
            {saving
              ? tr('love_memory_saving', undefined, 'Menyimpan…')
              : mode === 'edit'
                ? tr('love_memory_save', undefined, 'Simpan perubahan')
                : tr('love_memory_create', undefined, 'Tambah kenangan')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default LoveMemoryDialog;
