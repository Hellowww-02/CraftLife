/**
 * SourceCard.tsx — kartu sumber ala NotebookLM (A07).
 *
 * Menampilkan: ikon tipe · judul · jumlah kata · tanggal · chip "Dipakai".
 * Chip "Dipakai"/"Tidak dipakai" disiapkan sejak sekarang supaya pemilihan sumber
 * (grounding) di **A08** tidak perlu mengubah bentuk kartu lagi — cukup mengisi
 * prop `used`/`onToggleUsed`.
 */
import React from 'react';
import { Eye, Trash2, FileText, FileType2, Link2, Video, AlignLeft, FileSpreadsheet, Presentation, FileImage, FileAudio, BookOpen, Paperclip } from 'lucide-react';

export interface SourceItem {
  id: string;
  title: string;
  type: string;
  wordCount: number;
  createdAt?: string;
  /** C02: metadata berkas asli (kosong bila sumber teks/URL). */
  fileName?: string;
  fileSize?: number;
  hasFile?: boolean;
  /** C03: ringkasan panduan (AI tersimpan, else potongan). */
  summary?: string;
}

export interface SourceCardProps {
  source: SourceItem;
  used?: boolean;
  onToggleUsed?: (next: boolean) => void;
  onOpen: () => void;
  onDelete: () => void;
  active?: boolean;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

/** Ikon + label tipe sumber (parity `learning_source_type_*`). */
export function sourceTypeMeta(type: string): { icon: React.ReactNode; labelKey: string; fallback: string } {
  const t = String(type || 'text').toLowerCase();
  if (t.includes('pdf')) return { icon: <FileText className="w-4 h-4" />, labelKey: 'learning_source_type_pdf', fallback: 'PDF' };
  if (t.includes('doc')) return { icon: <FileType2 className="w-4 h-4" />, labelKey: 'learning_source_type_doc', fallback: 'Dokumen' };
  if (t.includes('xlsx') || t.includes('xls') || t.includes('sheet')) return { icon: <FileSpreadsheet className="w-4 h-4" />, labelKey: 'learning_source_type_sheet', fallback: 'Spreadsheet' };
  if (t.includes('pptx') || t.includes('slides') || t.includes('presentation')) return { icon: <Presentation className="w-4 h-4" />, labelKey: 'learning_source_type_slides', fallback: 'Presentasi' };
  if (t.includes('csv') || t.includes('tsv')) return { icon: <FileSpreadsheet className="w-4 h-4" />, labelKey: 'learning_source_type_csv', fallback: 'CSV' };
  if (t.includes('image') || t.includes('img') || t.includes('png') || t.includes('jpg') || t.includes('jpeg') || t.includes('webp')) return { icon: <FileImage className="w-4 h-4" />, labelKey: 'learning_source_type_image', fallback: 'Gambar' };
  if (t.includes('audio') || t.includes('mp3') || t.includes('wav') || t.includes('m4a')) return { icon: <FileAudio className="w-4 h-4" />, labelKey: 'learning_source_type_audio', fallback: 'Audio' };
  if (t.includes('epub') || t.includes('book')) return { icon: <BookOpen className="w-4 h-4" />, labelKey: 'learning_source_type_book', fallback: 'E-book' };
  if (t.includes('url') || t.includes('link')) return { icon: <Link2 className="w-4 h-4" />, labelKey: 'learning_source_type_url', fallback: 'Tautan' };
  if (t.includes('youtube') || t.includes('yt')) return { icon: <Video className="w-4 h-4" />, labelKey: 'learning_source_type_youtube', fallback: 'YouTube' };
  return { icon: <AlignLeft className="w-4 h-4" />, labelKey: 'learning_source_type_text', fallback: 'Teks' };
}

/** Tanggal pendek (yyyy-mm-dd) → tampilan lokal ringkas; aman bila kosong. */
function shortDate(value?: string): string {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const iso = raw.replace(' ', 'T');
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return raw.slice(0, 10);
  return d.toLocaleDateString();
}

/** Ukuran berkas ringkas (B/KB/MB). */
function fmtSize(n: number): string {
  if (!n || n <= 0) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let v = n; let i = 0;
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

const SourceCard: React.FC<SourceCardProps> = ({ source, used = true, onToggleUsed, onOpen, onDelete, active, tr }) => {
  const meta = sourceTypeMeta(source.type);
  const typeLabel = tr(meta.labelKey, {}, meta.fallback);
  return (
    <div className={`ct-nlm-card p-2.5 space-y-1.5 ${active ? 'is-active' : ''}`}>
      <div className="flex items-start gap-2">
        <span className="mt-0.5 w-6 h-6 rounded-lg flex items-center justify-center bg-[color-mix(in_srgb,var(--ct-primary)_16%,transparent)] text-[var(--ct-light)] shrink-0">
          {meta.icon}
        </span>
        <div className="min-w-0 flex-1">
          <button onClick={onOpen} className="block w-full text-left" title={tr('learning_view', {}, 'Lihat')}>
            <h4 className="font-bold text-[12px] text-slate-100 truncate">{source.title || tr('learning_generic_topic', {}, '(tanpa judul)')}</h4>
          </button>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-0.5 text-[10px] text-[var(--ct-nlm-dim)]">
            <span className="ct-nlm-chip is-muted">{typeLabel}</span>
            <span className="ct-nlm-num">{source.wordCount || 0} {tr('words', {}, 'kata')}</span>
            {shortDate(source.createdAt) && <span>{shortDate(source.createdAt)}</span>}
            {source.hasFile && (
              <span className="ct-nlm-chip inline-flex items-center gap-1 max-w-full" title={source.fileName || ''}>
                <Paperclip className="w-2.5 h-2.5 shrink-0" />
                <span className="truncate max-w-[7rem]">{source.fileName || typeLabel}</span>
                {Number(source.fileSize) > 0 && <span className="ct-nlm-num shrink-0">{fmtSize(Number(source.fileSize))}</span>}
              </span>
            )}
          </div>
          {source.summary ? (
            <p className="ct-guide-clamp mt-1 text-[11px] leading-snug text-slate-400">{source.summary}</p>
          ) : null}
        </div>
        {/* Chip grounding — interaktif mulai A08; sekarang menampilkan status saja. */}
        <button
          type="button"
          disabled={!onToggleUsed}
          onClick={() => onToggleUsed?.(!(used ?? true))}
          className={`ct-nlm-chip shrink-0 ${used ? 'is-ok' : 'is-muted'} ${onToggleUsed ? '' : 'cursor-default'}`}
          title={used ? tr('learning_source_used', {}, 'Dipakai') : tr('learning_source_unused', {}, 'Tidak dipakai')}
        >
          {used ? tr('learning_source_used', {}, 'Dipakai') : tr('learning_source_unused', {}, 'Tidak dipakai')}
        </button>
      </div>
      <div className="flex items-center gap-1 pl-8">
        <button onClick={onOpen} className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1 text-[10px]" title={tr('learning_view', {}, 'Lihat')}>
          <Eye className="w-3 h-3" />{tr('learning_view', {}, 'Lihat')}
        </button>
        <button onClick={onDelete} className="ct-btn ct-btn-secondary ct-btn-icon-sm p-1.5 text-slate-400 hover:text-rose-400 ml-auto" title={tr('learning_delete', {}, 'Hapus')}>
          <Trash2 className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

export default SourceCard;
