/**
 * SourceCard.tsx — kartu sumber ala NotebookLM (A07).
 *
 * Menampilkan: ikon tipe · judul · jumlah kata · tanggal · chip "Dipakai".
 * Chip "Dipakai"/"Tidak dipakai" disiapkan sejak sekarang supaya pemilihan sumber
 * (grounding) di **A08** tidak perlu mengubah bentuk kartu lagi — cukup mengisi
 * prop `used`/`onToggleUsed`.
 */
import React from 'react';
import { Eye, Trash2, FileText, FileType2, Link2, Video, AlignLeft } from 'lucide-react';

export interface SourceItem {
  id: string;
  title: string;
  type: string;
  wordCount: number;
  createdAt?: string;
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
          </div>
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
