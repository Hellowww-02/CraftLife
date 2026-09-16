/**
 * StudioArtifactList.tsx — daftar artefak Studio (A06).
 *
 * Permintaan user: *"setiap generate studio berbentuk list ke bawah — ada di dalam list rapi."*
 *
 * Sebelumnya hasil generate hanya tampil satu per satu di area `max-h-[360px]` untuk tipe
 * yang sedang aktif, ditambah daftar riwayat kecil (chip `gtype + topic + tanggal`) yang
 * mudah terlupakan. Sekarang SEMUA hasil generate adalah satu daftar vertikal:
 *
 *  - kartu artefak: ikon tipe · judul · badge tipe · waktu relatif · jumlah item
 *    ("15 soal" / "20 kartu" / "18 giliran" / "340 kata") · ukuran · tanggal;
 *  - filter chips per tipe · pencarian judul · urutan (Terbaru/Terlama/Tipe);
 *  - klik kartu → pratinjau isi terlihat tepat di bawah kartu (akordeon, satu scroll);
 *  - aksi per kartu: **Buka** (tampilan interaktif) · **Ganti nama** · **Ekspor .md** ·
 *    **Ekspor .txt** · **Duplikat** · **Hapus**.
 *
 * Komponen ini tidak menyimpan data sendiri — semua aksi diteruskan ke pemanggil
 * (LearningView) supaya state notebook tetap satu sumber kebenaran.
 */
import React, { useMemo, useState } from 'react';
import {
  Search, ArrowDownUp, Pencil, Copy, Trash2, Download, ExternalLink, ChevronDown,
  FileText, Layers, Clock, ListChecks, X, Check, Inbox,
} from 'lucide-react';

export interface ArtifactItem {
  id: string;
  gtype: string;
  title: string;
  createdAt?: string;
  updatedAt?: string;
  content?: string;
  itemCount?: number;
  words?: number;
  sizeBytes?: number;
}

export interface StudioArtifactListProps {
  artifacts: ArtifactItem[];
  /** Tipe yang sedang ditampilkan di area interaktif (ditandai "aktif"). */
  activeType?: string;
  activeArtifactId?: string | null;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
  busy?: boolean;
  onOpen: (artifact: ArtifactItem) => void;
  onRename: (artifact: ArtifactItem, title: string) => void;
  onDuplicate: (artifact: ArtifactItem) => void;
  onDelete: (artifact: ArtifactItem) => void;
  onExport: (artifact: ArtifactItem, format: 'md' | 'txt') => void;
  onSelectType?: (type: string) => void;
}

const TYPE_META: Record<string, { icon: string; scope: string }> = {
  quiz: { icon: '📝', scope: 'quiz' },
  flashcards: { icon: '🃏', scope: 'cards' },
  'audio-overview': { icon: '🎙️', scope: 'turns' },
  audio_overview: { icon: '🎙️', scope: 'turns' },
  podcast: { icon: '🎙️', scope: 'turns' },
  mindmap: { icon: '🗺️', scope: 'words' },
  mind_map: { icon: '🗺️', scope: 'words' },
  'study-guide': { icon: '📘', scope: 'words' },
  study_guide: { icon: '📘', scope: 'words' },
  faq: { icon: '❓', scope: 'words' },
  timeline: { icon: '🕒', scope: 'words' },
  summary: { icon: '📄', scope: 'words' },
};

const normalizeType = (t: string) => {
  const v = String(t || '').toLowerCase().replace(/_/g, '-');
  if (v === 'audio-overview' || v === 'podcast') return 'podcast';
  if (v === 'mind-map') return 'mindmap';
  if (v === 'study-guide') return 'study-guide';
  return v;
};

/** Waktu relatif sederhana ("3 menit lalu") — tanpa dependensi tanggal eksternal. */
function relTime(iso: string, tr: StudioArtifactListProps['tr']): string {
  const t = Date.parse(String(iso || '').replace(' ', 'T'));
  if (!t || Number.isNaN(t)) return String(iso || '');
  const diff = Math.max(0, Date.now() - t);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return tr('learning_artifact_now', {}, 'baru saja');
  if (mins < 60) return tr('learning_artifact_min_ago', { n: mins }, '{n} menit lalu');
  const hours = Math.floor(mins / 60);
  if (hours < 24) return tr('learning_artifact_hour_ago', { n: hours }, '{n} jam lalu');
  const days = Math.floor(hours / 24);
  if (days < 30) return tr('learning_artifact_day_ago', { n: days }, '{n} hari lalu');
  return String(iso || '').slice(0, 10);
}

function humanSize(bytes: number): string {
  const b = Number(bytes) || 0;
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
}

/** Item count per tipe → teks yang tepat ("15 soal" / "20 kartu" / "18 giliran" / "340 kata"). */
function itemLabel(a: ArtifactItem, tr: StudioArtifactListProps['tr']): string {
  const meta = TYPE_META[a.gtype] || TYPE_META[normalizeType(a.gtype)] || { icon: '📄', scope: 'words' };
  if (meta.scope === 'quiz') return tr('learning_artifact_items_quiz', { n: a.itemCount || 0 }, '{n} soal');
  if (meta.scope === 'cards') return tr('learning_artifact_items_cards', { n: a.itemCount || 0 }, '{n} kartu');
  if (meta.scope === 'turns') return tr('learning_artifact_items_turns', { n: a.itemCount || 0 }, '{n} giliran');
  return tr('learning_artifact_items_words', { n: a.words || 0 }, '{n} kata');
}

/**
 * Pratinjau isi artefak (dibaca dari `content` milik kartu itu sendiri, read-only).
 * Quiz & flashcards ditampilkan sebagai daftar tanya-jawab; podcast sebagai dialog;
 * mind map sebagai JSON; tipe teks apa adanya.
 */
export const ArtifactPreview: React.FC<{
  artifact: ArtifactItem;
  tr: StudioArtifactListProps['tr'];
}> = ({ artifact, tr }) => {
  const type = normalizeType(artifact.gtype);
  const raw = String(artifact.content || '').trim();
  const strip = (t: string) => t.replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();

  const quiz = useMemo(() => {
    if (type !== 'quiz') return null;
    try {
      const data = JSON.parse(strip(raw));
      const qs = Array.isArray(data) ? data : data.questions || [];
      return qs as any[];
    } catch {
      return null;
    }
  }, [type, raw]);

  const cards = useMemo(() => {
    if (type !== 'flashcards') return null;
    try {
      const data = JSON.parse(strip(raw));
      const arr = Array.isArray(data) ? data : data.cards || data.flashcards || [];
      return arr as any[];
    } catch {
      return null;
    }
  }, [type, raw]);

  const podcast = useMemo(() => {
    if (type !== 'podcast') return null;
    return raw.split('\n').filter((l) => l.includes('|')).map((l) => {
      const [sp, ...rest] = l.split('|');
      return { speaker: sp.trim().replace('HOST_A', 'Alex').replace('HOST_B', 'Sam'), line: rest.join('|').trim() };
    });
  }, [type, raw]);

  if (quiz) {
    return (
      <div className="space-y-2">
        {quiz.length === 0 && <p className="text-[11px] text-slate-500">{tr('learning_artifact_empty_content', {}, '(isi kosong)')}</p>}
        {quiz.map((q: any, i: number) => {
          const isEssay = String(q.type || '').toLowerCase() === 'essay'
            || (!q.options?.length && (q.modelAnswer || q.model_answer));
          const answer = q.answer ?? q.correctAnswerIndex ?? 0;
          return (
            <div key={i} className="bg-slate-950/60 border border-slate-800 rounded-xl p-2.5">
              <p className="text-[11px] font-semibold text-slate-200">
                {i + 1}. {q.question || q.q || ''}
                {isEssay && <span className="ml-1.5 text-[9px] uppercase px-1 py-0.5 rounded bg-violet-500/20 text-violet-300">Essay</span>}
              </p>
              {isEssay ? (
                <p className="text-[10px] text-slate-400 mt-1">
                  <span className="font-bold text-slate-300">{tr('quiz_model_answer', {}, '💡 Jawaban contoh')}:</span>{' '}
                  {q.modelAnswer || q.model_answer || '-'}
                </p>
              ) : (
                <ul className="mt-1 space-y-0.5">
                  {(q.options || []).map((opt: string, oi: number) => (
                    <li key={oi} className={`text-[10px] ${oi === Number(answer) ? 'text-emerald-300 font-semibold' : 'text-slate-400'}`}>
                      {oi === Number(answer) ? '✅ ' : '• '}{opt}
                    </li>
                  ))}
                </ul>
              )}
              {(q.explanation || q.explain) && (
                <p className="text-[10px] text-slate-500 mt-1">{q.explanation || q.explain}</p>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  if (cards) {
    return (
      <div className="space-y-1.5">
        {cards.length === 0 && <p className="text-[11px] text-slate-500">{tr('learning_artifact_empty_content', {}, '(isi kosong)')}</p>}
        {cards.map((c: any, i: number) => (
          <div key={i} className="bg-slate-950/60 border border-slate-800 rounded-xl p-2.5">
            <p className="text-[11px] font-semibold text-slate-200">{i + 1}. {c.front || c.question || ''}</p>
            <p className="text-[10px] text-slate-400 mt-0.5">{c.back || c.answer || ''}</p>
          </div>
        ))}
      </div>
    );
  }

  if (podcast) {
    return (
      <div className="space-y-1.5">
        {podcast.length === 0 && <p className="text-[11px] text-slate-500">{tr('learning_artifact_empty_content', {}, '(isi kosong)')}</p>}
        {podcast.map((p, i) => (
          <p key={i} className="text-[11px] text-slate-300">
            <span className="font-bold text-violet-300">{p.speaker}:</span> {p.line}
          </p>
        ))}
      </div>
    );
  }

  if (type === 'mindmap') {
    try {
      return <pre className="text-[10px] text-slate-300 bg-slate-950/60 border border-slate-800 rounded-xl p-2.5 overflow-x-auto">{JSON.stringify(JSON.parse(strip(raw)), null, 2)}</pre>;
    } catch {
      return <pre className="text-[10px] text-slate-300 whitespace-pre-wrap bg-slate-950/60 border border-slate-800 rounded-xl p-2.5 max-h-52 overflow-y-auto">{raw}</pre>;
    }
  }

  return (
    <pre className="text-[10px] text-slate-300 whitespace-pre-wrap bg-slate-950/60 border border-slate-800 rounded-xl p-2.5 max-h-52 overflow-y-auto">
      {raw || tr('learning_artifact_empty_content', {}, '(isi kosong)')}
    </pre>
  );
};

const StudioArtifactList: React.FC<StudioArtifactListProps> = ({
  artifacts, activeType, activeArtifactId, tr, busy,
  onOpen, onRename, onDuplicate, onDelete, onExport, onSelectType,
}) => {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<string>('all');
  const [sort, setSort] = useState<'newest' | 'oldest' | 'type'>('newest');
  const [expanded, setExpanded] = useState<string | null>(null);
  const [renaming, setRenaming] = useState<ArtifactItem | null>(null);
  const [renameValue, setRenameValue] = useState('');

  // Daftar tipe yang benar-benar ada di notebook ini → chip filter dinamis.
  const types = useMemo(() => {
    const set = new Set<string>();
    artifacts.forEach((a) => set.add(normalizeType(a.gtype)));
    return Array.from(set);
  }, [artifacts]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = artifacts.filter((a) => {
      if (filter !== 'all' && normalizeType(a.gtype) !== filter) return false;
      if (!q) return true;
      return `${a.title || ''} ${a.gtype || ''}`.toLowerCase().includes(q);
    });
    list = [...list].sort((a, b) => {
      if (sort === 'type') return normalizeType(a.gtype).localeCompare(normalizeType(b.gtype));
      const ta = Date.parse(String(a.createdAt || '').replace(' ', 'T')) || 0;
      const tb = Date.parse(String(b.createdAt || '').replace(' ', 'T')) || 0;
      return sort === 'newest' ? tb - ta : ta - tb;
    });
    return list;
  }, [artifacts, filter, query, sort]);

  const typeLabel = (t: string) => {
    const n = normalizeType(t);
    return tr(`learning_studio_${n === 'podcast' ? 'podcast_script' : n === 'mindmap' ? 'mindmap' : n === 'study-guide' ? 'guide' : n}`, {}, n);
  };

  const startRename = (a: ArtifactItem) => {
    setRenaming(a);
    setRenameValue(a.title || '');
  };

  return (
    <div className="space-y-2.5">
      {/* Header + kontrol */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          {tr('learning_artifacts', {}, 'Hasil Studio')}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-bold">
          {tr('learning_artifacts_count', { n: artifacts.length }, '{n} hasil')}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <div className="relative">
            <Search className="w-3 h-3 text-slate-500 absolute left-2 top-1/2 -translate-y-1/2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={tr('learning_artifact_search_ph', {}, 'Cari hasil…')}
              className="w-28 sm:w-40 bg-slate-950 border border-slate-800 rounded-lg pl-6 pr-2 py-1 text-[11px] text-slate-200"
            />
          </div>
          <button
            onClick={() => setSort(sort === 'newest' ? 'oldest' : sort === 'oldest' ? 'type' : 'newest')}
            className="flex items-center gap-1 px-2 py-1 bg-slate-950 border border-slate-800 rounded-lg text-[10px] font-bold text-slate-300"
            title={tr('learning_artifact_sort', {}, 'Urutan')}
          >
            <ArrowDownUp className="w-3 h-3" />
            {sort === 'newest' ? tr('learning_artifact_sort_newest', {}, 'Terbaru')
              : sort === 'oldest' ? tr('learning_artifact_sort_oldest', {}, 'Terlama')
                : tr('learning_artifact_sort_type', {}, 'Tipe')}
          </button>
        </div>
      </div>

      {/* Filter chips */}
      {artifacts.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setFilter('all')}
            className={`px-2 py-1 rounded-lg text-[10px] font-bold border ${filter === 'all' ? 'bg-violet-600/25 border-violet-500/60 text-violet-100' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-violet-500/40'}`}
          >
            {tr('learning_artifact_filter_all', {}, 'Semua')} ({artifacts.length})
          </button>
          {types.map((t) => {
            const n = artifacts.filter((a) => normalizeType(a.gtype) === t).length;
            return (
              <button
                key={t}
                onClick={() => setFilter(filter === t ? 'all' : t)}
                className={`px-2 py-1 rounded-lg text-[10px] font-bold border ${filter === t ? 'bg-violet-600/25 border-violet-500/60 text-violet-100' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-violet-500/40'}`}
              >
                {TYPE_META[t]?.icon || '📄'} {typeLabel(t)} ({n})
              </button>
            );
          })}
        </div>
      )}

      {/* Daftar (list ke bawah) */}
      <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
        {artifacts.length === 0 && (
          <div className="text-center py-8 bg-slate-950/40 border border-slate-800/80 rounded-xl">
            <Inbox className="w-8 h-8 mx-auto mb-2 text-slate-600" />
            <p className="text-sm font-medium text-slate-400">{tr('learning_artifact_empty_title', {}, 'Belum ada hasil Studio')}</p>
            <p className="text-[11px] text-slate-500 mt-1">{tr('learning_artifact_empty_hint', {}, 'Pilih salah satu tipe di atas untuk membuat materi baru.')}</p>
          </div>
        )}

        {artifacts.length > 0 && filtered.length === 0 && (
          <p className="text-[11px] text-slate-500 text-center py-4">{tr('learning_artifact_empty_filtered', {}, 'Tidak ada hasil untuk filter ini.')}</p>
        )}

        {filtered.map((a) => {
          const t = normalizeType(a.gtype);
          const isOpen = expanded === a.id;
          const isActive = activeArtifactId ? activeArtifactId === a.id : activeType === a.gtype;
          return (
            <div
              key={a.id}
              className={`rounded-xl border transition-colors ${isActive ? 'bg-violet-950/25 border-violet-500/40' : 'bg-slate-950/70 border-slate-800'}`}
            >
              <div className="flex items-start gap-2 p-2.5">
                <button
                  onClick={() => { setExpanded(isOpen ? null : a.id); onSelectType?.(a.gtype); }}
                  className="flex items-start gap-2 flex-1 min-w-0 text-left"
                  title={tr('learning_artifact_preview', {}, 'Pratinjau')}
                >
                  <span className="text-base leading-none mt-0.5">{TYPE_META[t]?.icon || '📄'}</span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-1.5">
                      <span className="text-[11px] font-bold text-slate-100 truncate">{a.title || tr('learning_generic_topic', {}, '(topik umum)')}</span>
                      <span className="text-[9px] uppercase px-1 py-0.5 rounded bg-slate-700/60 text-slate-300 shrink-0">{typeLabel(a.gtype)}</span>
                      {isActive && <span className="text-[9px] font-bold text-violet-300 shrink-0">• {tr('learning_artifact_active', {}, 'aktif')}</span>}
                    </span>
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-[10px] text-slate-500">
                      <span className="flex items-center gap-1"><ListChecks className="w-2.5 h-2.5" />{itemLabel(a, tr)}</span>
                      <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" />{relTime(a.createdAt || '', tr)}</span>
                      <span className="flex items-center gap-1"><FileText className="w-2.5 h-2.5" />{humanSize(a.sizeBytes || 0)}</span>
                      {a.updatedAt && a.updatedAt !== a.createdAt && <span>✎ {tr('learning_artifact_edited', {}, 'diedit')}</span>}
                    </span>
                  </span>
                  <ChevronDown className={`w-3.5 h-3.5 text-slate-500 shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                </button>
              </div>

              {/* Aksi kartu */}
              <div className="flex flex-wrap items-center gap-1 px-2.5 pb-2.5">
                <button
                  disabled={busy}
                  onClick={() => onOpen(a)}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-violet-600/25 hover:bg-violet-600/40 border border-violet-500/40 text-violet-100 text-[10px] font-bold disabled:opacity-50"
                  title={tr('learning_artifact_open_hint', {}, 'Tampilkan versi interaktif (kuis bisa dikerjakan)')}
                >
                  <ExternalLink className="w-3 h-3" />{tr('learning_artifact_open', {}, 'Buka')}
                </button>
                <button
                  disabled={busy}
                  onClick={() => startRename(a)}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
                >
                  <Pencil className="w-3 h-3" />{tr('learning_artifact_rename', {}, 'Ganti nama')}
                </button>
                <button
                  disabled={busy}
                  onClick={() => onExport(a, 'md')}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
                >
                  <Download className="w-3 h-3" />{tr('learning_artifact_export_md', {}, 'Ekspor .md')}
                </button>
                <button
                  disabled={busy}
                  onClick={() => onExport(a, 'txt')}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
                >
                  <Download className="w-3 h-3" />{tr('learning_artifact_export_txt', {}, 'Ekspor .txt')}
                </button>
                <button
                  disabled={busy}
                  onClick={() => onDuplicate(a)}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
                >
                  <Copy className="w-3 h-3" />{tr('learning_artifact_duplicate', {}, 'Duplikat')}
                </button>
                <button
                  disabled={busy}
                  onClick={() => onDelete(a)}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-400 hover:text-rose-300 text-[10px] font-bold ml-auto disabled:opacity-50"
                >
                  <Trash2 className="w-3 h-3" />{tr('learning_artifact_delete', {}, 'Hapus')}
                </button>
              </div>

              {/* Pratinjau akordeon (satu list, satu scroll) */}
              {isOpen && (
                <div className="px-2.5 pb-2.5 border-t border-slate-800/70 pt-2">
                  <ArtifactPreview artifact={a} tr={tr} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Dialog ganti nama */}
      {renaming && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="ct-dialog max-w-sm w-full p-5 space-y-3">
            <h3 className="font-bold text-sm text-slate-100">{tr('learning_artifact_rename_title', {}, 'Nama baru hasil Studio')}</h3>
            <input
              autoFocus
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && renameValue.trim()) { onRename(renaming, renameValue.trim()); setRenaming(null); }
                if (e.key === 'Escape') setRenaming(null);
              }}
              maxLength={120}
              placeholder={tr('learning_artifact_rename_ph', {}, 'mis. Kuis Bab 3')}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-violet-500"
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setRenaming(null)} className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-[11px] font-bold">
                <X className="w-3 h-3" />{tr('msg_cancel', {}, 'Batal')}
              </button>
              <button
                disabled={!renameValue.trim()}
                onClick={() => { onRename(renaming, renameValue.trim()); setRenaming(null); }}
                className="flex items-center gap-1 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl text-[11px] font-bold"
              >
                <Check className="w-3 h-3" />{tr('msg_ok', {}, 'OK')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudioArtifactList;
