/**
 * StudioArtifactList.tsx — pemilih artefak Studio berbentuk DROPDOWN (H02, v1.7.0).
 *
 * A06 dulu menampilkan semua hasil sebagai list vertikal (max-h 420px) di bawah
 * pratinjau interaktif — list itu menutupi/mengecilkan preview (keluhan user
 * v1.7.0: "interactive preview jadi kecil"). Sekarang riwayat artefak menjadi
 * SATU combobox ringkas:
 *
 *  - trigger menampilkan artefak aktif (ikon tipe · judul · badge tipe · jumlah
 *    item · waktu relatif);
 *  - panel dropdown: pencarian judul + urutan (Terbaru/Terlama/Tipe) + daftar
 *    dikelompokkan per tipe; klik baris = buka artefak di pratinjau interaktif;
 *  - baris aksi artefak terpilih: Ganti nama · Ekspor (.md/.txt, +.csv/.html
 *    sesuai tipe) · Duplikat · Hapus.
 *
 * Komponen tidak menyimpan data — semua aksi diteruskan ke LearningView supaya
 * state notebook tetap satu sumber kebenaran. Keyboard penuh: ↑↓ Enter Esc
 * (aria listbox/option), focus trap tidak diperlukan karena panel bukan modal.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Search, ArrowDownUp, Pencil, Copy, Trash2, Download, ChevronDown, Check, Inbox, X,
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
  /** Tipe yang sedang ditampilkan di area interaktif (fallback penanda aktif). */
  activeType?: string;
  activeArtifactId?: string | null;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
  busy?: boolean;
  onOpen: (artifact: ArtifactItem) => void;
  onRename: (artifact: ArtifactItem, title: string) => void;
  onDuplicate: (artifact: ArtifactItem) => void;
  onDelete: (artifact: ArtifactItem) => void;
  onExport: (artifact: ArtifactItem, format: 'md' | 'txt' | 'csv' | 'html') => void;
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
  'briefing-doc': { icon: '📋', scope: 'words' },
  briefing_doc: { icon: '📋', scope: 'words' },
  'data-table': { icon: '📊', scope: 'rows' },
  data_table: { icon: '📊', scope: 'rows' },
  infographic: { icon: '🎨', scope: 'points' },
  'slide-deck': { icon: '📽️', scope: 'slides' },
  slide_deck: { icon: '📽️', scope: 'slides' },
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

/** Item count per tipe → teks yang tepat ("15 soal" / "20 kartu" / "18 giliran"). */
function itemLabel(a: ArtifactItem, tr: StudioArtifactListProps['tr']): string {
  const meta = TYPE_META[a.gtype] || TYPE_META[normalizeType(a.gtype)] || { icon: '📄', scope: 'words' };
  if (meta.scope === 'quiz') return tr('learning_artifact_items_quiz', { n: a.itemCount || 0 }, '{n} soal');
  if (meta.scope === 'cards') return tr('learning_artifact_items_cards', { n: a.itemCount || 0 }, '{n} kartu');
  if (meta.scope === 'turns') return tr('learning_artifact_items_turns', { n: a.itemCount || 0 }, '{n} giliran');
  if (meta.scope === 'rows') return tr('learning_artifact_items_rows', { n: a.itemCount || 0 }, '{n} baris');
  if (meta.scope === 'slides') return tr('learning_artifact_items_slides', { n: a.itemCount || 0 }, '{n} slide');
  if (meta.scope === 'points') return tr('learning_artifact_items_points', { n: a.itemCount || 0 }, '{n} poin');
  return tr('learning_artifact_items_words', { n: a.words || 0 }, '{n} kata');
}

const StudioArtifactList: React.FC<StudioArtifactListProps> = ({
  artifacts, activeType, activeArtifactId, tr, busy,
  onOpen, onRename, onDuplicate, onDelete, onExport, onSelectType,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [sort, setSort] = useState<'newest' | 'oldest' | 'type'>('newest');
  const [renaming, setRenaming] = useState<ArtifactItem | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const rootRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const searchRef = useRef<HTMLInputElement | null>(null);

  const active = useMemo(
    () => artifacts.find((a) => (activeArtifactId ? String(a.id) === String(activeArtifactId) : normalizeType(a.gtype) === normalizeType(activeType || ''))) || artifacts[0] || null,
    [artifacts, activeArtifactId, activeType],
  );

  // Daftar terfilter + terurut (dipakai panel dropdown).
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    let list = artifacts.filter((a) => {
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
  }, [artifacts, query, sort]);

  // Grup per tipe (urutan grup mengikuti kemunculan di `filtered`).
  const groups = useMemo(() => {
    const map = new Map<string, ArtifactItem[]>();
    for (const a of filtered) {
      const t = normalizeType(a.gtype);
      if (!map.has(t)) map.set(t, []);
      map.get(t)!.push(a);
    }
    return Array.from(map.entries());
  }, [filtered]);

  const typeLabel = (t: string) => {
    const n = normalizeType(t);
    const key = n === 'podcast' ? 'podcast_script' : n === 'mindmap' ? 'mindmap' : n === 'study-guide' ? 'guide'
      : ({ 'briefing-doc': 'briefing_doc', 'data-table': 'data_table', infographic: 'infographic', 'slide-deck': 'slide_deck' } as Record<string, string>)[n] || n;
    return tr(`learning_studio_${key}`, {}, n);
  };

  // Tutup saat klik di luar dropdown.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [open]);

  // Fokus ke pencarian tiap panel terbuka.
  useEffect(() => {
    if (open) window.setTimeout(() => searchRef.current?.focus(), 30);
  }, [open]);

  const selectArtifact = (a: ArtifactItem) => {
    setOpen(false);
    onSelectType?.(a.gtype);
    onOpen(a);
    triggerRef.current?.focus();
  };

  const onPanelKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      const panel = rootRef.current?.querySelector<HTMLElement>('[data-artifact-panel]');
      if (!panel) return;
      const rows = Array.from(panel.querySelectorAll<HTMLButtonElement>('[data-artifact-row]'));
      if (!rows.length) return;
      const idx = rows.findIndex((r) => r === document.activeElement);
      const next = e.key === 'ArrowDown'
        ? rows[Math.min(rows.length - 1, idx + 1)]
        : rows[Math.max(0, idx <= 0 ? 0 : idx - 1)];
      next?.focus();
    }
  };

  const activeMeta = active ? (TYPE_META[normalizeType(active.gtype)] || { icon: '📄' }) : { icon: '📄' };
  const activeT = active ? normalizeType(active.gtype) : '';

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
          {tr('learning_artifacts', {}, 'Hasil Studio')}
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-bold ct-nlm-num">
          {tr('learning_artifacts_count', { n: artifacts.length }, '{n} hasil')}
        </span>
      </div>

      {/* Dropdown pemilih artefak */}
      <div className="relative" ref={rootRef}>
        <button
          type="button"
          ref={triggerRef}
          onClick={() => setOpen((v) => !v)}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown' && !open) { e.preventDefault(); setOpen(true); }
          }}
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={tr('learning_artifact_select', {}, 'Pilih hasil Studio')}
          className={`w-full flex items-center gap-2.5 rounded-xl border px-3 py-2.5 text-left transition-colors ${
            open ? 'bg-violet-950/30 border-violet-500/50' : 'bg-slate-950 border-slate-800 hover:border-violet-500/40'
          }`}
        >
          {active ? (
            <>
              <span className="text-lg leading-none shrink-0" aria-hidden="true">{activeMeta.icon}</span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5">
                  <span className="text-xs font-bold text-slate-100 truncate">{active.title || tr('learning_generic_topic', {}, '(topik umum)')}</span>
                  <span className="text-[9px] uppercase px-1 py-0.5 rounded bg-violet-500/20 text-violet-300 font-bold shrink-0">{typeLabel(active.gtype)}</span>
                </span>
                <span className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-500 ct-nlm-num">
                  <span>{itemLabel(active, tr)}</span>
                  <span>· {relTime(active.createdAt || '', tr)}</span>
                </span>
              </span>
            </>
          ) : (
            <span className="flex items-center gap-2 flex-1 text-xs text-slate-500">
              <Inbox className="w-4 h-4" aria-hidden="true" />
              {tr('learning_artifact_empty_title', {}, 'Belum ada hasil Studio')}
            </span>
          )}
          <ChevronDown
            aria-hidden="true"
            className={`w-4 h-4 text-slate-500 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`}
          />
        </button>

        {open && (
          <div
            data-artifact-panel
            onKeyDown={onPanelKey}
            className="absolute left-0 right-0 top-full mt-2 z-30 ct-dialog p-0 overflow-hidden ct-pop"
          >
            {/* Kontrol: cari + urutan */}
            <div className="flex items-center gap-1.5 p-2 border-b border-slate-800/80">
              <div className="relative flex-1">
                <Search className="w-3 h-3 text-slate-500 absolute left-2 top-1/2 -translate-y-1/2" aria-hidden="true" />
                <input
                  ref={searchRef}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={tr('learning_artifact_search_ph', {}, 'Cari hasil…')}
                  aria-label={tr('learning_artifact_search_ph', {}, 'Cari hasil…')}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-6 pr-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-violet-500"
                />
              </div>
              <button
                type="button"
                onClick={() => setSort(sort === 'newest' ? 'oldest' : sort === 'oldest' ? 'type' : 'newest')}
                className="flex items-center gap-1 px-2 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-[10px] font-bold text-slate-300 hover:border-violet-500/40 shrink-0"
                title={tr('learning_artifact_sort', {}, 'Urutan')}
              >
                <ArrowDownUp className="w-3 h-3" aria-hidden="true" />
                {sort === 'newest' ? tr('learning_artifact_sort_newest', {}, 'Terbaru')
                  : sort === 'oldest' ? tr('learning_artifact_sort_oldest', {}, 'Terlama')
                    : tr('learning_artifact_sort_type', {}, 'Tipe')}
              </button>
            </div>

            {/* Daftar (grup per tipe) */}
            <div role="listbox" aria-label={tr('learning_artifacts', {}, 'Hasil Studio')} className="max-h-72 overflow-y-auto p-1.5">
              {artifacts.length === 0 && (
                <div className="text-center py-6 px-3">
                  <Inbox className="w-7 h-7 mx-auto mb-2 text-slate-600" aria-hidden="true" />
                  <p className="text-xs font-medium text-slate-400">{tr('learning_artifact_empty_title', {}, 'Belum ada hasil Studio')}</p>
                  <p className="text-[10px] text-slate-500 mt-1">{tr('learning_artifact_empty_hint', {}, 'Pilih salah satu tipe di atas untuk membuat materi baru.')}</p>
                </div>
              )}
              {artifacts.length > 0 && filtered.length === 0 && (
                <p className="text-[11px] text-slate-500 text-center py-4">{tr('learning_artifact_empty_filtered', {}, 'Tidak ada hasil untuk filter ini.')}</p>
              )}
              {groups.map(([t, items]) => (
                <div key={t}>
                  <p className="px-2 pt-2 pb-1 text-[9px] uppercase tracking-wider text-slate-500 font-bold flex items-center gap-1.5">
                    <span aria-hidden="true">{TYPE_META[t]?.icon || '📄'}</span>
                    {typeLabel(t)}
                    <span className="ct-nlm-num">({items.length})</span>
                  </p>
                  {items.map((a) => {
                    const isActive = active ? String(active.id) === String(a.id) : false;
                    return (
                      <button
                        key={a.id}
                        type="button"
                        role="option"
                        aria-selected={isActive}
                        data-artifact-row
                        onClick={() => selectArtifact(a)}
                        className={`w-full flex items-center gap-2 rounded-lg px-2 py-1.5 text-left transition-colors ${
                          isActive ? 'bg-violet-600/25 text-violet-100' : 'text-slate-300 hover:bg-slate-800/70'
                        }`}
                      >
                        <span className="min-w-0 flex-1">
                          <span className="block text-[11px] font-semibold truncate">{a.title || tr('learning_generic_topic', {}, '(topik umum)')}</span>
                          <span className="block text-[9px] text-slate-500 ct-nlm-num">{itemLabel(a, tr)} · {relTime(a.createdAt || '', tr)}</span>
                        </span>
                        {isActive && <Check className="w-3.5 h-3.5 text-violet-300 shrink-0" aria-hidden="true" />}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Baris aksi artefak terpilih */}
      {active && (
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            disabled={busy}
            onClick={() => { setRenaming(active); setRenameValue(active.title || ''); }}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
            title={tr('learning_artifact_rename', {}, 'Ganti nama')}
          >
            <Pencil className="w-3 h-3" aria-hidden="true" />{tr('learning_artifact_rename', {}, 'Ganti nama')}
          </button>
          <span className="flex items-center gap-0.5 rounded-lg bg-slate-950 border border-slate-800 px-1 py-0.5">
            <Download className="w-3 h-3 text-slate-500 mx-0.5" aria-hidden="true" />
            {(['md', 'txt'] as ('md' | 'txt' | 'csv' | 'html')[])
              .concat(activeT === 'data-table' ? ['csv'] : [], activeT === 'slide-deck' ? ['html'] : [])
              .map((fmt) => (
              <button
                key={fmt}
                type="button"
                disabled={busy}
                onClick={() => onExport(active, fmt)}
                className="px-1.5 py-0.5 rounded-md text-[10px] font-bold text-slate-300 hover:bg-slate-800 disabled:opacity-50 ct-nlm-num"
                title={tr('learning_artifact_export_fmt', { fmt }, 'Ekspor .{fmt}')}
              >
                .{fmt}
              </button>
            ))}
          </span>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDuplicate(active)}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-bold disabled:opacity-50"
            title={tr('learning_artifact_duplicate', {}, 'Duplikat')}
          >
            <Copy className="w-3 h-3" aria-hidden="true" />{tr('learning_artifact_duplicate', {}, 'Duplikat')}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => onDelete(active)}
            className="flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-800 hover:bg-rose-900/40 text-slate-400 hover:text-rose-300 text-[10px] font-bold disabled:opacity-50 ml-auto"
            title={tr('learning_artifact_delete', {}, 'Hapus')}
          >
            <Trash2 className="w-3 h-3" aria-hidden="true" />{tr('learning_artifact_delete', {}, 'Hapus')}
          </button>
        </div>
      )}

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
              aria-label={tr('learning_artifact_rename_title', {}, 'Nama baru hasil Studio')}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-violet-500"
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setRenaming(null)} className="flex items-center gap-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-[11px] font-bold">
                <X className="w-3 h-3" aria-hidden="true" />{tr('msg_cancel', {}, 'Batal')}
              </button>
              <button
                type="button"
                disabled={!renameValue.trim()}
                onClick={() => { onRename(renaming, renameValue.trim()); setRenaming(null); }}
                className="flex items-center gap-1 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl text-[11px] font-bold"
              >
                <Check className="w-3 h-3" aria-hidden="true" />{tr('msg_ok', {}, 'OK')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudioArtifactList;
