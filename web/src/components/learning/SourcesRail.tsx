/**
 * SourcesRail.tsx — panel Sumber (kolom tengah view utama, A07).
 *
 * Isi: header jumlah sumber · tombol **Upload** & **Tambah** (tempel teks/tautan) ·
 * pencarian sumber · daftar `SourceCard` · empty state yang mengarahkan user menambah
 * sumber pertama · footer "n sumber · grounding jawaban AI".
 *
 * Grounding (pemilihan sumber) disiapkan lewat prop `usedIds`/`onToggleUsed` → diaktifkan
 * penuh pada A08 tanpa mengubah bentuk panel.
 */
import React, { useMemo, useRef, useState } from 'react';
import { Plus, Upload, Search, FileText, Pencil } from 'lucide-react';
import SourceCard, { SourceItem } from './SourceCard';

export interface SourcesRailProps {
  sources: SourceItem[];
  uploading?: boolean;
  usedIds?: string[];
  onToggleUsed?: (id: string, next: boolean) => void;
  onUpload: (file: File) => void;
  onAddPaste: () => void;
  onOpenSource: (id: string) => void;
  onDeleteSource: (id: string) => void;
  onOpenFull?: () => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

const SourcesRail: React.FC<SourcesRailProps> = ({
  sources, uploading, usedIds, onToggleUsed, onUpload, onAddPaste, onOpenSource, onDeleteSource, onOpenFull, tr,
}) => {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return sources;
    return sources.filter((s) => `${s.title} ${s.type}`.toLowerCase().includes(q));
  }, [sources, query]);

  const totalWords = useMemo(
    () => sources.reduce((sum, s) => sum + (Number(s.wordCount) || 0), 0),
    [sources],
  );

  // A08: grounding — berapa sumber yang dipakai untuk menjawab/menghasilkan materi.
  const usedCount = useMemo(
    () => sources.filter((s) => (usedIds ? usedIds.includes(String(s.id)) : true)).length,
    [sources, usedIds],
  );
  const allUsed = usedCount === sources.length;

  return (
    <section className="ct-nlm-panel flex flex-col min-h-[420px] lg:min-h-0 lg:h-full p-3 gap-2.5" aria-label={tr('learning_sources_panel', {}, 'Sumber')}>
      <header className="flex items-center gap-2">
        <FileText className="w-4 h-4 text-[var(--ct-light)]" />
        <h3 className="text-[12px] font-black uppercase tracking-wider text-slate-300">
          {tr('learning_view_sources', {}, 'Sumber')}
        </h3>
        <span className="ct-nlm-chip ct-nlm-num">{sources.length}</span>
        {onToggleUsed && sources.length > 0 && (
          <button
            type="button"
            onClick={() => {
              // A08: satu klik untuk pakai semua / kosongkan pilihan grounding.
              sources.forEach((src) => onToggleUsed(src.id, !allUsed));
            }}
            className={`ct-nlm-chip ${allUsed ? 'is-muted' : 'is-ok'}`}
            title={tr('learning_filter_sources', {}, 'Pilih sumber')}
          >
            {tr('learning_sources_selected_count', { n: usedCount, total: sources.length },
              '{n} dari {total} sumber dipakai')}
          </button>
        )}
        <button
          onClick={onOpenFull}
          className="ml-auto lg:hidden ct-btn ct-btn-secondary ct-btn-sm text-[10px]"
        >
          {tr('learning_view_chat', {}, 'Chat')}
        </button>
      </header>

      {/* Tambah sumber */}
      <div className="flex gap-1.5">
        <input
          ref={fileRef}
          type="file"
          accept=".txt,.md,.pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onUpload(f);
            e.target.value = '';
          }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800/80 hover:bg-slate-700 disabled:opacity-50 text-[11px] font-bold text-slate-200 rounded-lg border border-slate-700"
        >
          <Upload className="w-3.5 h-3.5" />{uploading ? '…' : tr('learning_upload_source', {}, 'Upload')}
        </button>
        <button
          onClick={onAddPaste}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-[11px] font-bold text-slate-200 rounded-lg border border-slate-700"
        >
          <Pencil className="w-3.5 h-3.5" />{tr('learning_add_source', {}, 'Tambah')}
        </button>
      </div>

      {/* Pencarian (muncul bila sumber > 3 agar tidak berisik) */}
      {sources.length > 3 && (
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tr('learning_source_search_ph', {}, 'Cari sumber…')}
            className="w-full bg-slate-950/70 border border-slate-800 rounded-lg pl-8 pr-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-[var(--ct-primary)]"
          />
        </div>
      )}

      {/* Daftar */}
      <div className="ct-nlm-scroll flex-1 overflow-y-auto space-y-2 pr-1 max-h-[520px] lg:max-h-none">
        {sources.length === 0 ? (
          <div className="py-10 px-4 text-center bg-slate-950/40 border border-dashed border-slate-800 rounded-xl">
            <Plus className="w-7 h-7 mx-auto mb-2 text-slate-600" />
            <p className="text-[12px] font-semibold text-slate-300">{tr('no_sources_yet', {}, 'Belum ada sumber.')}</p>
            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
              {tr('learning_add_source_hint', {}, 'Tambahkan sumber untuk memulai — PDF, dokumen, teks, atau tautan.')}
            </p>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-[11px] text-slate-500 text-center py-4">{tr('learning_source_no_match', {}, 'Tidak ada sumber yang cocok.')}</p>
        ) : (
          filtered.map((s) => (
            <SourceCard
              key={s.id}
              source={s}
              used={usedIds ? usedIds.includes(String(s.id)) : true}
              onToggleUsed={onToggleUsed ? (next) => onToggleUsed(s.id, next) : undefined}
              onOpen={() => onOpenSource(s.id)}
              onDelete={() => onDeleteSource(s.id)}
              tr={tr}
            />
          ))
        )}
      </div>

      <footer className="flex items-center gap-2 pt-1.5 border-t border-[var(--ct-nlm-line-soft)] text-[10px] text-[var(--ct-nlm-dim)]">
        <span className="ct-nlm-num">{usedCount}/{sources.length}</span>
        <span>{tr('learning_grounding_on', {}, 'Grounding aktif')} · {tr('sources_grounding_the_ai_answers', {}, 'grounding jawaban AI')}</span>
        <span className="ml-auto ct-nlm-num">{totalWords} {tr('words', {}, 'kata')}</span>
      </footer>
    </section>
  );
};

export default SourcesRail;
