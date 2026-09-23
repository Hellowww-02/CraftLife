/**
 * SourcesRail.tsx — panel Sumber Learning (A07, multi-upload di C02).
 *
 * Isi: header jumlah sumber · tombol **Upload** (multi-file + drag-and-drop,
 * PDF/Word/Excel/PowerPoint/CSV/teks/Markdown/EPUB/gambar/audio) & **Tambah**
 * (tempel teks/tautan) · antrean upload dengan progres per berkas · pencarian
 * sumber · daftar `SourceCard` · footer grounding.
 *
 * Antrean: berkas diproses berurutan lewat prop `uploadOne` (satu janji per
 * berkas) agar server tidak dibanjiri request base64 besar sekaligus; induk
 * cukup me-refresh sekali lewat `onQueueDone`.
 */
import React, { useMemo, useRef, useState } from 'react';
import { Plus, Upload, Search, FileText, Pencil, Loader2, CheckCircle2, XCircle, X } from 'lucide-react';
import SourceCard, { SourceItem } from './SourceCard';

/** Daftar ekstensi sumber (C02) — cermin whitelist server di `_handle_upload_file`. */
export const ACCEPT_SOURCES =
  '.pdf,.docx,.xlsx,.xls,.pptx,.csv,.tsv,.txt,.md,.markdown,.rtf,.epub' +
  ',.png,.jpg,.jpeg,.webp,.gif' +
  ',.mp3,.wav,.m4a,.ogg,.opus,.flac';

export interface QueueItem {
  key: string;
  name: string;
  status: 'queued' | 'active' | 'done' | 'error';
  error?: string;
}

/** Hitung ringkasan antrean (murni — bisa diuji). */
export function queueCounts(items: QueueItem[]): { done: number; total: number; ok: number; fail: number; busy: boolean } {
  const done = items.filter((i) => i.status === 'done' || i.status === 'error').length;
  return {
    done,
    total: items.length,
    ok: items.filter((i) => i.status === 'done').length,
    fail: items.filter((i) => i.status === 'error').length,
    busy: items.some((i) => i.status === 'queued' || i.status === 'active'),
  };
}

export interface SourcesRailProps {
  sources: SourceItem[];
  /** Unggah satu berkas → {ok, msg?}. Dipanggil berurutan per antrean. */
  uploadOne: (file: File) => Promise<{ ok: boolean; msg?: string }>;
  /** Dipanggil sekali saat antrean habis (okCount, failCount). */
  onQueueDone?: (okCount: number, failCount: number) => void;
  usedIds?: string[];
  onToggleUsed?: (id: string, next: boolean) => void;
  onAddPaste: () => void;
  onOpenSource: (id: string) => void;
  onDeleteSource: (id: string) => void;
  onOpenFull?: () => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

const SourcesRail: React.FC<SourcesRailProps> = ({
  sources, uploadOne, onQueueDone, usedIds, onToggleUsed, onAddPaste, onOpenSource, onDeleteSource, onOpenFull, tr,
}) => {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [query, setQuery] = useState('');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const busyRef = useRef(false);
  /** Berkas menunggu giliran (key stabil cocok dengan QueueItem di state). */
  const pendingRef = useRef<{ key: string; file: File }[]>([]);

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
  const qc = queueCounts(queue);

  /** Antrekan berkas lalu keringkan (drain) berurutan; drop saat sibuk ikut
      antre menunggu giliran — tidak ada berkas yang hilang diam-diam. */
  const processQueue = async (files: File[]) => {
    if (!files.length) return;
    const batch: QueueItem[] = files.map((f, i) => ({
      key: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}-${i}-${f.name}`,
      name: f.name,
      status: 'queued' as const,
    }));
    // Batch baru menggantikan hasil lama yang sudah selesai; batch susulan
    // (saat masih sibuk) menempel di bawahnya.
    setQueue((prev) => (prev.some((q) => q.status === 'queued' || q.status === 'active')
      ? [...prev, ...batch] : batch));
    batch.forEach((b, i) => pendingRef.current.push({ key: b.key, file: files[i] }));
    if (busyRef.current) return;
    busyRef.current = true;
    let ok = 0; let fail = 0;
    try {
      while (pendingRef.current.length > 0) {
        const item = pendingRef.current.shift();
        if (!item) break;
        const { key, file } = item;
        setQueue((prev) => prev.map((q) => (q.key === key ? { ...q, status: 'active' } : q)));
        try {
          // eslint-disable-next-line no-await-in-loop
          const r = await uploadOne(file);
          if (r?.ok) {
            ok += 1;
            setQueue((prev) => prev.map((q) => (q.key === key ? { ...q, status: 'done' } : q)));
          } else {
            fail += 1;
            setQueue((prev) => prev.map((q) => (q.key === key
              ? { ...q, status: 'error', error: r?.msg || 'learning_source_empty_file' } : q)));
          }
        } catch (e) {
          fail += 1;
          setQueue((prev) => prev.map((q) => (q.key === key
            ? { ...q, status: 'error', error: String((e as Error)?.message || e) } : q)));
        }
      }
    } finally {
      busyRef.current = false;
    }
    onQueueDone?.(ok, fail);
  };

  const hasFiles = (e: React.DragEvent) => {
    try {
      return Array.from(e.dataTransfer?.types || []).includes('Files');
    } catch {
      return false;
    }
  };

  return (
    <section
      className={`ct-nlm-panel flex flex-col min-h-[420px] lg:min-h-0 lg:h-full p-3 gap-2.5 relative${dragOver ? ' ct-drop-active' : ''}`}
      aria-label={tr('learning_sources_panel', {}, 'Sumber')}
      onDragOver={(e) => { if (hasFiles(e)) { e.preventDefault(); setDragOver(true); } }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        if (!hasFiles(e)) return;
        e.preventDefault();
        setDragOver(false);
        processQueue(Array.from(e.dataTransfer.files || []));
      }}
    >
      {/* Lapisan drop hint */}
      {dragOver && (
        <div className="absolute inset-0 z-10 ct-drop-overlay rounded-[inherit] flex items-center justify-center pointer-events-none">
          <p className="text-[12px] font-bold">{tr('learning_drop_files', {}, 'Seret & letakkan berkas di sini')}</p>
        </div>
      )}

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
          multiple
          accept={ACCEPT_SOURCES}
          className="hidden"
          onChange={(e) => {
            const files = Array.from(e.target.files || []);
            e.target.value = '';
            if (files.length) processQueue(files);
          }}
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={qc.busy}
          title={tr('learning_supported_types', {}, 'PDF · Word · Excel · PowerPoint · CSV · Teks · Markdown · EPUB · Gambar · Audio')}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800/80 hover:bg-slate-700 disabled:opacity-50 text-[11px] font-bold text-slate-200 rounded-lg border border-slate-700"
        >
          <Upload className="w-3.5 h-3.5" />{tr('learning_add_sources', {}, 'Unggah berkas (bisa banyak)')}
        </button>
        <button
          onClick={onAddPaste}
          className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800/80 hover:bg-slate-700 text-[11px] font-bold text-slate-200 rounded-lg border border-slate-700"
        >
          <Pencil className="w-3.5 h-3.5" />{tr('learning_add_source', {}, 'Tambah')}
        </button>
      </div>

      {/* Antrean upload */}
      {queue.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-2 space-y-1" data-testid="upload-queue">
          <div className="flex items-center gap-2 px-1">
            <span className="text-[10px] font-bold text-slate-300">
              {qc.busy
                ? tr('learning_queue_uploading', { done: qc.done + 1, total: qc.total }, `Mengunggah ${qc.done + 1}/${qc.total}…`)
                : `${tr('learning_queue_ok', { n: qc.ok }, `${qc.ok} sumber ditambahkan`)}${qc.fail ? ` · ${tr('learning_queue_fail', { n: qc.fail }, `${qc.fail} gagal`)}` : ''}`}
            </span>
            {!qc.busy && (
              <button
                onClick={() => setQueue([])}
                className="ml-auto flex items-center gap-1 text-[10px] font-bold text-slate-500 hover:text-slate-300"
              >
                <X className="w-3 h-3" />{tr('learning_queue_clear', {}, 'Bersihkan')}
              </button>
            )}
          </div>
          {qc.busy && qc.total > 0 && (
            <div className="h-1 rounded-full bg-slate-800 overflow-hidden" aria-hidden>
              <div className="h-full bg-[var(--ct-primary)] transition-[width]" style={{ width: `${Math.round((qc.done / qc.total) * 100)}%` }} />
            </div>
          )}
          <ul className="max-h-28 overflow-y-auto ct-nlm-scroll space-y-0.5">
            {queue.map((q) => (
              <li key={q.key} className="flex items-center gap-1.5 text-[10px] px-1" data-testid={`queue-${q.status}`}>
                {q.status === 'done' && <CheckCircle2 className="w-3 h-3 text-emerald-400 shrink-0" />}
                {q.status === 'error' && <XCircle className="w-3 h-3 text-rose-400 shrink-0" />}
                {q.status === 'active' && <Loader2 className="w-3 h-3 text-sky-300 shrink-0 animate-spin" />}
                {q.status === 'queued' && <span className="w-3 h-3 shrink-0 rounded-full border border-slate-600" aria-hidden />}
                <span className="min-w-0 flex-1 truncate text-slate-300" title={q.name}>{q.name}</span>
                {q.status === 'error' && q.error && (
                  <span className="shrink-0 text-rose-300/90 truncate max-w-[45%]" title={q.error}>
                    {tr(q.error, {}, q.error)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

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
