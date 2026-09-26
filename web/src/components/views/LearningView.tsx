import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { useGame } from '../../context/GameContext';
import { saveFileToComputer, downloadTargetInfo, downloadApiFile, apiPost, apiBase } from '../../api/client';
import {
  BookOpen,
  Plus,
  HelpCircle,
  Headphones,
  CheckCircle2,
  XCircle,
  Play,
  Pause,
  RotateCcw,
  Layers,
  Pencil,
  Eye,
  Download,
  ZoomIn,
  ChevronDown,
  ZoomOut,
  Maximize,
  KeyRound,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import { studio } from '../../api/studio';
import { t as tr } from '../../i18n';
import {
  QUIZ_TOTAL_MAX, QUIZ_DEFAULT_MC, QUIZ_DEFAULT_ESSAY,
} from '../learning/QuizCountFields';
import StudioGenerateDialog from '../learning/StudioGenerateDialog';
import {
  STUDIO_META, StudioKind,
  loadStudioConfig, buildStudioPayload, summarizeStudioConfig,
} from '../learning/studioOptions';
import StudioArtifactList, { ArtifactItem } from '../learning/StudioArtifactList';
import LearningShell from '../learning/LearningShell';
import NotebookRail, { LearningViewKey } from '../learning/NotebookRail';
import SourcesRail from '../learning/SourcesRail';
import ChatPanel, { buildSuggestions } from '../learning/ChatPanel';
import PodcastPlayer from '../learning/PodcastPlayer';
import { DataTableView, InfographicView, SlideDeckView } from '../learning/StudioNewViews';

// C05: 12 generator (8 lama + 4 baru di akhir, urutan lama tidak berubah).
type StudioType = 'summary' | 'study-guide' | 'flashcards' | 'faq' | 'mindmap' | 'timeline' | 'quiz' | 'podcast' | 'briefing-doc' | 'data-table' | 'infographic' | 'slide-deck';
const STUDIO_TYPES: { type: StudioType; icon: string; labelKey: string; default: string[] }[] = [
  { type: 'summary', icon: '📄', labelKey: 'learning_studio_summary', default: [] },
  { type: 'study-guide', icon: '📘', labelKey: 'learning_studio_guide', default: [] },
  { type: 'flashcards', icon: '🃏', labelKey: 'learning_studio_flashcards', default: [] },
  { type: 'faq', icon: '❓', labelKey: 'learning_studio_faq', default: [] },
  { type: 'mindmap', icon: '🗺️', labelKey: 'learning_studio_mindmap', default: [] },
  { type: 'timeline', icon: '🕒', labelKey: 'learning_studio_timeline', default: [] },
  { type: 'quiz', icon: '📝', labelKey: 'learning_studio_quiz', default: [] },
  { type: 'podcast', icon: '🎙️', labelKey: 'learning_studio_podcast_script', default: [] },
  { type: 'briefing-doc', icon: '📋', labelKey: 'learning_studio_briefing_doc', default: [] },
  { type: 'data-table', icon: '📊', labelKey: 'learning_studio_data_table', default: [] },
  { type: 'infographic', icon: '🎨', labelKey: 'learning_studio_infographic', default: [] },
  { type: 'slide-deck', icon: '📽️', labelKey: 'learning_studio_slide_deck', default: [] },
];

// Parity LearningPage._clamp_font: ukuran font 10..30, default 13.
const clampFont = (v: number) => {
  const n = Math.round(v);
  return Number.isFinite(n) ? Math.max(10, Math.min(30, n)) : 13;
};

// Parity LearningPage._render_mindmap: cari blok JSON di teks mentah, toleran
// kutip tunggal & trailing koma; pusat dari central/topic/title; maks. 8 cabang,
// masing-masing maks. 6 anak, child sebagai string.
type MindBranch = { label: string; children: string[] };

const parseMindMap = (raw: unknown): { central: string; branches: MindBranch[] } | null => {
  let data: any = raw;
  if (typeof raw === 'string') {
    const m = /\{[\s\S]*\}/.exec(raw);
    const text = m ? m[0] : raw;
    data = null;
    const fixed = text.replace(/'/g, '"').replace(/,\s*([}\]])/g, '$1');
    for (const cand of [text, fixed]) {
      try { data = JSON.parse(cand); break; } catch { /* coba kandidat berikut */ }
    }
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) return null;
  const central = String(data.central || data.topic || data.title || 'Topic');
  const branches: MindBranch[] = (Array.isArray(data.branches) ? data.branches : [])
    .filter((b: any) => b && typeof b === 'object')
    .slice(0, 8)
    .map((b: any, i: number) => ({
      label: String(b.label || `Branch ${i + 1}`),
      children: (Array.isArray(b.children) ? b.children : []).slice(0, 6).map(String),
    }));
  return { central, branches };
};

// Parity LearningPage mind map QGraphicsView: node pusat → trunk → cabang + anak,
// dengan kontrol zoom in/out/reset (≈ _fit_mindmap).
const MindMapView: React.FC<{ raw: unknown; lang: string; fontSize: number }> = ({ raw, lang, fontSize }) => {
  const [zoom, setZoom] = useState(1.15);
  const map = useMemo(() => parseMindMap(raw), [raw]);
  if (!map) {
    return (
      <pre className="text-[11px] overflow-x-auto bg-slate-950/60 border border-slate-800 rounded-xl p-3">
        {typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2)}
      </pre>
    );
  }
  const zoomStep = (d: number) => setZoom((z) => Math.max(0.4, Math.min(3, Math.round((z + d) * 10) / 10)));
  return (
    <div className="bg-slate-950/60 border border-slate-800 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-800/80">
        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
          {tr('mind_map', '🧠 Mind Map')}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => zoomStep(-0.2)} className="ct-btn ct-btn-secondary ct-btn-icon-sm text-violet-300" title="Zoom out"><ZoomOut className="w-3.5 h-3.5" /></button>
          <button onClick={() => setZoom(1.15)} className="ct-btn ct-btn-secondary ct-btn-icon-sm text-violet-300" title="Fit"><Maximize className="w-3.5 h-3.5" /></button>
          <button onClick={() => zoomStep(0.2)} className="ct-btn ct-btn-secondary ct-btn-icon-sm text-violet-300" title="Zoom in"><ZoomIn className="w-3.5 h-3.5" /></button>
        </div>
      </div>
      <div className="max-h-[440px] overflow-auto">
        <div style={{ transform: `scale(${zoom})`, transformOrigin: 'top left', fontSize }} className="inline-block min-w-full p-5">
          <div className="flex items-start gap-6">
            {/* Node pusat */}
            <div className="shrink-0 self-center px-4 py-3 rounded-2xl bg-violet-600/25 border-2 border-violet-500 font-bold text-violet-200 text-center max-w-[220px]">
              {map.central}
            </div>
            {/* Trunk → cabang */}
            <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-0 before:top-4 before:bottom-4 before:w-0.5 before:bg-violet-500/50">
              {map.branches.map((b, bi) => (
                <div key={bi} className="relative pl-4">
                  <span className="absolute left-[-24px] top-4 w-6 h-0.5 bg-violet-500/50" />
                  <div className="px-3 py-2 rounded-xl bg-indigo-950/40 border border-indigo-500/40 text-indigo-200 font-semibold inline-block">
                    {b.label}
                  </div>
                  {b.children.length > 0 && (
                    <ul className="mt-2 ml-1 space-y-1 border-l border-indigo-500/30 pl-3">
                      {b.children.map((c, ci) => (
                        <li key={ci} className="px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-800 text-slate-300 inline-block w-full">{c}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/** A15: daftar emoji notebook — satu sumber untuk dialog “Notebook Baru” & “Ganti nama”. */
const NB_EMOJI = ['📚', '🧠', '🔬', '💻', '📐', '🚀', '📝', '⚡'];

/** Pemilih emoji notebook (dipakai saat membuat & saat mengubah notebook). */
const NotebookIconPicker: React.FC<{
  value: string;
  onChange: (icon: string) => void;
  label: string;
}> = ({ value, onChange, label }) => (
  <div>
    <label className="block text-xs font-bold text-slate-400 mb-1">{label}</label>
    <div className="flex flex-wrap gap-2">
      {NB_EMOJI.map((emoji) => (
        <button
          key={emoji}
          type="button"
          onClick={() => onChange(emoji)}
          aria-label={emoji}
          aria-pressed={value === emoji}
          className={`text-xl p-2 rounded-lg border ${
            value === emoji ? 'bg-violet-600/30 border-violet-500' : 'bg-slate-950 border-slate-800'
          }`}
        >
          {emoji}
        </button>
      ))}
    </div>
  </div>
);

export const LearningView: React.FC = () => {
  const {
    notebooks,
    addNotebook,
    deleteNotebook,
    addNotebookSource,
    deleteNotebookSource,
    addNotebookChat,
    updateNotebook,
    refreshNotebooks,
    lang,
    setLang,
    showToast,
  } = useGame();

  const [activeNotebookId, setActiveNotebookId] = useState<string>(notebooks[0]?.id || '');
  // PyQt parity: auto-create a first notebook when the list is empty (PyQt seeds
  // a "First Notebook" via `db.create_learning_notebook`). Guarded to run once.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (notebooks.length === 0) {
      seededRef.current = true;
      addNotebook(tr('learning_first_notebook', 'First Notebook'), '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebooks.length]);

  // Input states
  const [chatInput, setChatInput] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);

  // New notebook modal
  const [showNewNbModal, setShowNewNbModal] = useState(false);
  useEscapeClose(showNewNbModal, () => setShowNewNbModal(false));
  const [newNbTitle, setNewNbTitle] = useState('');
  const [newNbDesc, setNewNbDesc] = useState('');
  const [newNbIcon, setNewNbIcon] = useState('📚');

  // New source modal
  const [showNewSourceModal, setShowNewSourceModal] = useState(false);
  const [newSourceTitle, setNewSourceTitle] = useState('');
  const [newSourceContent, setNewSourceContent] = useState('');
  const [newSourceType, setNewSourceType] = useState<'text' | 'doc' | 'pdf' | 'url'>('text');
  // C03: mode dialog tambah sumber (teks tempel vs URL website/YouTube).
  const [newSourceMode, setNewSourceMode] = useState<'text' | 'website' | 'youtube'>('text');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [savingSource, setSavingSource] = useState(false);
  const [sourceErr, setSourceErr] = useState('');
  // C04: modal catatan tersimpan + kartu yang dibuka.
  const [showNotesModal, setShowNotesModal] = useState(false);
  const [expandedNote, setExpandedNote] = useState<string | null>(null);
  const [geminiKey, setGeminiKey] = useState('');

  // ── Parity LearningPage: font chat/studio, rename, upload source, history ──
  const [chatFontSize, setChatFontSize] = useState(13);
  const [studioFontSize, setStudioFontSize] = useState(13);
  const [renaming, setRenaming] = useState(false);
  useEscapeClose(renaming, () => setRenaming(false));
  const [renameTitle, setRenameTitle] = useState('');
  // A15: ikon notebook ikut bisa diubah lewat dialog ganti nama (rail kiri).
  const [renameIcon, setRenameIcon] = useState('📚');
  const [studioTopic, setStudioTopic] = useState('');
  const [selectedGen, setSelectedGen] = useState<any | null>(null);
  const [viewingSource, setViewingSource] = useState<{
    id: string; title: string; content: string;
    fileName: string; mimeType: string; fileSize: number; hasFile: boolean;
  } | null>(null);
  useEscapeClose(viewingSource !== null, () => setViewingSource(null));
  const [reextracting, setReextracting] = useState(false);
  // A07: judul notebook di topbar bisa diganti langsung (inline-rename).
  // Draf disinkronkan setiap kali notebook aktif berganti (lihat useEffect di bawah).
  const [nbTitleDraft, setNbTitleDraft] = useState('');

  /** A15: buka dialog ganti nama dengan judul & ikon notebook aktif yang sudah terisi. */
  const openRenameDialog = () => {
    if (!activeNotebook) return;
    setRenameTitle(activeNotebook.title);
    setRenameIcon(activeNotebook.icon || '📚');
    setRenaming(true);
  };

  const handleRename = async () => {
    if (!activeNotebook || !renameTitle.trim()) return;
    try {
      // A15: ikut mengirim ikon supaya emoji yang dipilih benar-benar tersimpan.
      const r = await studio.renameNotebook(activeNotebook.id, renameTitle.trim(), renameIcon);
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr('learning_no_title', 'Judul tidak boleh kosong.'), ''); return; }
      updateNotebook(activeNotebook.id, { title: renameTitle.trim(), icon: renameIcon });
      refreshNotebooks();
      setRenaming(false);
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  // A07: commit inline-rename dari topbar (Enter / blur). Dianggap sukses bila
  // judul benar-benar berubah — kalau tidak, tidak ada panggilan API sama sekali.
  const commitNotebookTitle = async () => {
    if (!activeNotebook) return;
    const next = nbTitleDraft.trim();
    if (!next || next === activeNotebook.title) { setNbTitleDraft(activeNotebook.title); return; }
    try {
      const r = await studio.renameNotebook(activeNotebook.id, next);
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr('learning_no_title', 'Judul tidak boleh kosong.'), ''); setNbTitleDraft(activeNotebook.title); return; }
      updateNotebook(activeNotebook.id, { title: next });
      refreshNotebooks();
    } catch (e) {
      showToast('damage', String((e as any)?.message || e), '');
      setNbTitleDraft(activeNotebook.title);
    }
  };

  // A07: pemilih bahasa di rail → set bahasa global (sama seperti SettingsView).
  const handleLanguageChange = (next: 'id' | 'en') => {
    if (next === lang) return;
    setLang(next);
    apiPost('/api/settings', { language: next }).catch(() => undefined);
  };

  const handleDeleteGeneration = async (genId: string) => {
    if (!activeNotebook || !window.confirm(tr('learning_delete_gen', 'Hapus hasil generasi ini?'))) return;
    try {
      await studio.deleteGeneration(activeNotebook.id, genId);
      if (selectedGen?.id === genId) setSelectedGen(null);
      refreshNotebooks();
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  // ── A06: aksi daftar artefak Studio ────────────────────────────────────────
  // Daftar artefak menggantikan riwayat chip lama; kartunya bisa dibuka (interaktif),
  // diganti nama, diekspor, diduplikat, dan dihapus.
  const normalizeArtifactType = (t: string): StudioType => {
    const v = String(t || '').toLowerCase().replace(/_/g, '-');
    if (v === 'audio-overview' || v === 'podcast') return 'podcast';
    if (v === 'mind-map') return 'mindmap';
    if (v === 'study-guide') return 'study-guide';
    if ((STUDIO_TYPES as { type: string }[]).some((x) => x.type === v)) return v as StudioType;
    return 'summary';
  };

  const handleOpenArtifact = (a: ArtifactItem) => {
    const t = normalizeArtifactType(a.gtype);
    setActiveStudioType(t);
    setSelectedGen(a);
    setShowStudioPreview(true);
    if (interactiveArtifactId && String(a.id) !== interactiveArtifactId) {
      // Jujur ke user: area interaktif selalu memakai hasil TERBARU tipe tersebut;
      // isi artefak yang diklik tetap bisa dibaca pada pratinjau akordeon di daftar.
      showToast('info', tr('learning_artifact_open', 'Buka'),
        tr('learning_artifact_not_latest', 'Pratinjau di daftar menampilkan hasil yang diklik; area interaktif memakai hasil terbaru tipe ini.'));
    }
  };

  const handleRenameArtifact = async (a: ArtifactItem, title: string) => {
    if (!activeNotebook) return;
    try {
      const r = await studio.renameGeneration(activeNotebook.id, a.id, title);
      const res = r?.result || r;
      if (res?.ok === false) {
        showToast('damage', tr('learning_artifact_rename', 'Ganti nama'),
          tr(res?.msg || 'learning_not_found', 'Hasil tidak ditemukan.'));
        return;
      }
      setSelectedGen((prev: any) => (prev && String(prev.id) === String(a.id) ? { ...prev, title } : prev));
      showToast('success', tr('learning_artifact_renamed', 'Nama hasil diperbarui'), title);
      refreshNotebooks();
    } catch (e) {
      showToast('damage', String((e as any)?.message || e), '');
    }
  };

  const handleDuplicateArtifact = async (a: ArtifactItem) => {
    if (!activeNotebook) return;
    try {
      const r = await studio.duplicateGeneration(activeNotebook.id, a.id);
      const res = r?.result || r;
      if (res?.ok === false) {
        showToast('damage', tr('learning_artifact_duplicate', 'Duplikat'),
          tr(res?.msg || 'learning_not_found', 'Hasil tidak ditemukan.'));
        return;
      }
      showToast('success', tr('learning_artifact_duplicated', 'Hasil diduplikat'), res?.title || '');
      refreshNotebooks();
    } catch (e) {
      showToast('damage', String((e as any)?.message || e), '');
    }
  };

  const handleDeleteArtifact = async (a: ArtifactItem) => {
    await handleDeleteGeneration(a.id);
    showToast('success', tr('learning_artifact_deleted', 'Hasil dihapus'), a.title || '');
  };

  // Ekspor artefak: server menyiapkan berkas (staged) → diunduh lewat jalur unduhan
  // A03.5 (`/api/system/download-file`) sehingga berkas benar-benar sampai ke komputer.
  const handleExportArtifact = async (a: ArtifactItem, format: 'md' | 'txt' | 'csv' | 'html') => {
    if (!activeNotebook) return;
    try {
      const res = await studio.exportGeneration(activeNotebook.id, a.id, format);
      if (!res?.ok || !res?.id) {
        showToast('damage', tr('learning_artifact_export_failed', 'Ekspor gagal'),
          tr(res?.msg || 'learning_not_found', 'Hasil tidak ditemukan.'));
        return;
      }
      downloadApiFile(`/api/system/download-file?id=${encodeURIComponent(res.id)}`, res.name || `${a.title}.${format}`);
      downloadTargetInfo().then((info) => {
        showToast('success', tr('learning_artifact_export_done', 'Ekspor selesai'),
          tr('download_saved_msg', 'Tersimpan di: {path}').replace('{path}',
            info.lastPath || info.dir || tr('download_folder_default', 'folder unduhan CraftLife')));
      }).catch(() => showToast('success', tr('learning_artifact_export_done', 'Ekspor selesai'), res.name || ''));
    } catch (e) {
      showToast('damage', tr('learning_artifact_export_failed', 'Ekspor gagal'), String((e as any)?.message || e));
    }
  };

  // C02: unggah SATU berkas untuk antrean SourcesRail (refresh/toast di handleQueueDone).
  const uploadOneSource = async (file: File): Promise<{ ok: boolean; msg?: string }> => {
    if (!activeNotebook || !file) return { ok: false, msg: 'learning_not_found' };
    try {
      const r = await studio.uploadLearningSource(activeNotebook.id, file);
      const res = r?.result || r;
      if (res?.ok === false) return { ok: false, msg: String(res?.msg || 'learning_source_empty_file') };
      const warns = (res as any)?.warnings;
      if (Array.isArray(warns) && warns.length) {
        // Berkas tersimpan tapi butuh API key (gambar/audio) — beri tahu sekali per berkas.
        showToast('info', tr(String(warns[0]), 'Berkas tersimpan; tambah API key lalu Ekstrak ulang.'), file.name);
      }
      return { ok: true };
    } catch (e) { return { ok: false, msg: String((e as any)?.message || e) }; }
  };

  const handleQueueDone = (okCount: number, failCount: number) => {
    refreshNotebooks();
    if (okCount > 0) showToast('success', trq('learning_queue_ok', { n: okCount }, '{n} sumber ditambahkan'), '');
    if (failCount > 0) showToast('damage', trq('learning_queue_fail', { n: failCount }, '{n} gagal'), '');
  };

  const handleViewSource = async (sourceId: string) => {
    if (!activeNotebook) return;
    try {
      const r = await studio.learningSourceContent(activeNotebook.id, sourceId);
      const res = r?.result || r;
      if (!res?.ok) { showToast('damage', tr(res?.msg || 'learning_not_found', 'Tidak ditemukan.'), ''); return; }
      const src = res.source || res;
      setViewingSource({
        id: String(src.id || sourceId),
        title: src.title || 'Source',
        content: src.content || '',
        fileName: src.file_name || src.fileName || '',
        mimeType: src.mime_type || src.mimeType || '',
        fileSize: Number(src.file_size ?? src.fileSize) || 0,
        hasFile: Boolean(src.file_path || src.hasFile),
      });
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  // C02: ekstrak ulang dari berkas asli (mis. setelah isi API key untuk gambar/audio).
  const handleReextract = async () => {
    if (!activeNotebook || !viewingSource || reextracting) return;
    setReextracting(true);
    try {
      const r = await studio.reextractSource(activeNotebook.id, viewingSource.id);
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr(res?.msg || 'learning_not_found', 'Tidak ditemukan.'), ''); return; }
      showToast('success', tr('learning_reextracted', 'Ekstraksi diperbarui'), '');
      refreshNotebooks();
      handleViewSource(viewingSource.id);
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
    finally { setReextracting(false); }
  };

  const fmtFileSize = (n: number) => {
    if (!n || n <= 0) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let v = n; let i = 0;
    while (v >= 1024 && i < units.length - 1) { v /= 1024; i += 1; }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
  };

  // C04: simpan jawaban AI jadi catatan (judul = baris bermakna pertama).
  const handleSaveNote = async (text: string) => {
    if (!activeNotebook || !text.trim()) return;
    const lines = text.split('\n').map((l) => l.trim()).filter((l) => l);
    let firstLine = '';
    for (const l of lines) {
      let t = l;
      while (t && '#*>-0123456789. '.includes(t[0])) t = t.slice(1);
      t = t.trim();
      if (t) { firstLine = t; break; }
    }
    try {
      const r = await studio.addNote(activeNotebook.id, firstLine.slice(0, 60) || tr('learning_notes_title', 'Catatan'), text);
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr(res?.msg || 'learning_not_found', 'Tidak ditemukan.'), ''); return; }
      showToast('success', tr('learning_note_saved', 'Catatan disimpan'), '');
      refreshNotebooks();
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  const handleCopyNote = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      showToast('success', tr('learning_note_copied', 'Catatan disalin'), '');
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  const handleDeleteNote = async (noteId: string) => {
    if (!activeNotebook) return;
    if (!window.confirm(tr('learning_note_delete_confirm', 'Hapus catatan ini?'))) return;
    try {
      await studio.deleteNote(activeNotebook.id, noteId);
      setExpandedNote((prev) => (prev === noteId ? null : prev));
      refreshNotebooks();
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  // C03: simpan sumber — teks via jalur lama, URL via fetch server (async + error).
  const handleSaveSource = async () => {
    if (!activeNotebook || savingSource) return;
    if (newSourceMode === 'text') {
      if (!newSourceTitle.trim() || !newSourceContent.trim()) return;
      addNotebookSource(activeNotebook.id, newSourceTitle.trim(), newSourceContent.trim(), newSourceType);
      setShowNewSourceModal(false); setNewSourceTitle(''); setNewSourceContent(''); setSourceErr('');
      return;
    }
    const url = newSourceUrl.trim();
    let urlOk = url.length >= 12;
    try {
      const pu = new URL(url);
      urlOk = urlOk && (pu.protocol === 'http:' || pu.protocol === 'https:');
    } catch { urlOk = false; }
    if (!urlOk) { setSourceErr(tr('learning_url_invalid', 'URL tidak valid')); return; }
    setSavingSource(true); setSourceErr('');
    try {
      const r = await studio.addSourceFromUrl(activeNotebook.id, { url, type: newSourceMode, title: newSourceTitle.trim() });
      const res = r?.result || r;
      if (res?.ok === false) { setSourceErr(tr(res?.msg || 'learning_source_fetch_failed', 'Sumber tidak dapat diambil.')); return; }
      showToast('success', tr('learning_source_added', 'Source ditambahkan'), newSourceTitle.trim() || url);
      refreshNotebooks();
      setShowNewSourceModal(false); setNewSourceTitle(''); setNewSourceUrl(''); setSourceErr('');
    } catch (e) { setSourceErr(String((e as any)?.message || e)); }
    finally { setSavingSource(false); }
  };

  // Ekspor hasil Studio ke .txt via download browser (parity _export_studio
  // bagian Text (*.txt); body docx/pdf butuh lib binary — txt = jalur terverifikasi).
  const handleExportStudio = () => {
    if (!activeNotebook) return;
    const nb: any = activeNotebook;
    const parts: string[] = [];
    if (selectedGen?.content) parts.push(String(selectedGen.content));
    if (!parts.length && nb.studyGuide) parts.push(String(nb.studyGuide));
    if (!parts.length && nb.summary) parts.push(String(nb.summary));
    if (!parts.length && nb.faq) parts.push(String(nb.faq));
    if (!parts.length && nb.timeline) parts.push(String(nb.timeline));
    if (!parts.length && nb.mindMap) parts.push(typeof nb.mindMap === 'string' ? nb.mindMap : JSON.stringify(nb.mindMap, null, 2));
    if (!parts.length) return;
    // A03.5: ekspor via attachment server (dulu blob dibuang diam-diam oleh Qt WebEngine).
    saveFileToComputer({
      name: `${(activeNotebook.title || 'studio').replace(/[^\w\- ]+/g, '').trim() || 'studio'}.txt`,
      mime: 'text/plain',
      text: parts.join('\n\n'),
    });
    downloadTargetInfo().then((info) => {
      showToast('success', tr('learning_export_done', 'Ekspor selesai'),
        tr('download_saved_msg', 'Tersimpan di: {path}').replace('{path}',
          info.lastPath || info.dir || tr('download_folder_default', 'folder unduhan CraftLife')));
    }).catch(() => showToast('success', tr('learning_export_done', 'Ekspor selesai'), ''));
  };

  // Flashcards state
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isCardFlipped, setIsCardFlipped] = useState(false);

  // Quiz state
  // A04: kunci jawaban TIDAK lagi memakai indeks soal. `activeNotebook` di-refetch
  // setelah generate (`refreshNotebooks()`), dan indeks bisa bergeser/berbeda antar
  // render → jawaban tampak hilang. Sekarang kuncinya ID SOAL yang stabil (q.id).
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, number>>({});
  // A04: `quizReviewed` = mode PENILAIAN (skor + kunci + pembahasan). Dipisah dari
  // kemampuan menjawab, sehingga textarea essay tidak pernah ikut terkunci.
  const [quizReviewed, setQuizReviewed] = useState(false);
  // P56/A04: jawaban essay (teks bebas) per ID soal + penilaian mandiri (1 / 0.5 / 0).
  const [essayAnswers, setEssayAnswers] = useState<Record<string, string>>({});
  const [essayMarks, setEssayMarks] = useState<Record<string, number>>({});
  // A04: mode latihan — tampilkan seluruh jawaban contoh sekaligus.
  const [showModelAnswers, setShowModelAnswers] = useState(false);
  // A05: dialog konfigurasi per tipe Studio. Counter PG/Essay (A04) kini hidup DI DALAM
  // dialog tipe Quiz — bukan lagi di panel — supaya tidak ada dua tempat mengatur hal sama.
  const [studioDialogKind, setStudioDialogKind] = useState<StudioKind | null>(null);
  // A06: area interaktif (kuis bisa dikerjakan, kartu dibalik, podcast diputar) tetap ada
  // di panel, tapi kini bisa dilipat karena daftar artefak menjadi isi utama panel.
  const [showStudioPreview, setShowStudioPreview] = useState(true);
  // Ringkasan "pengaturan terakhir" untuk tipe yang sedang aktif (diperbarui setelah dialog).
  const [cfgTick, setCfgTick] = useState(0);

  // Podcast / Audio playback state
  const [isPodcastPlaying, setIsPodcastPlaying] = useState(false);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);

  // ── Parity LearningPage 3-panel: output type, count (quiz/flashcards 10-30),
  //    panel toggles & navigasi antar kolom (A07). ──
  const [activeStudioType, setActiveStudioType] = useState<StudioType>('summary');
  // A08: audio podcast dua host (MP3 nyata + offset tiap giliran untuk pemutar interaktif).
  const [podcastAudio, setPodcastAudio] = useState<any | null>(null);
  const [podcastBusy, setPodcastBusy] = useState(false);
  // A07: satu state navigasi untuk rail + tab mobile; di desktop 'sources'/'chat'
  // adalah isi kolom tengah, 'studio' berarti kolom Studio yang ditonjolkan.
  const [view, setView] = useState<LearningViewKey>('sources');
  // A07: status "dipakai" per sumber (grounding). Semua sumber dipakai secara default;
  // A08 akan menghubungkan pilihan ini ke API (`sourceIds`) — bentuk kartunya sudah siap.
  const [usedSourceIds, setUsedSourceIds] = useState<string[]>([]);
  const toggleSourceUsed = (id: string, next: boolean) => {
    setUsedSourceIds((prev) => (next ? Array.from(new Set([...prev, String(id)])) : prev.filter((x) => x !== String(id))));
  };

  // Math Problem state
  const [mathProblem, setMathProblem] = useState('x^2 - 5x + 6 = 0');
  const [mathSolution, setMathSolution] = useState('');
  const [isSolvingMath, setIsSolvingMath] = useState(false);

  const activeNotebook = notebooks.find((nb) => nb.id === activeNotebookId) || notebooks[0];
  const activeGenList: any[] = (activeNotebook as any)?.generations || [];

  // A04: helper terjemahan ber-interpolasi (tr bawaan i18n hanya 2 argumen).
  // A07: draf judul mengikuti notebook aktif (kecuali user sedang mengetik di input —
  // useState+useEffect sederhana sudah cukup karena commit terjadi onBlur/Enter).
  useEffect(() => {
    setNbTitleDraft(activeNotebook?.title || '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNotebook?.id, activeNotebook?.title]);

  const trv = (key: string, fallback: string, vars?: Record<string, string | number>) => {
    let out = tr(key, fallback);
    if (vars) for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(String(v));
    return out;
  };
  // Bentuk yang dipakai komponen QuizCountFields: (key, vars?, fallback?)
  const trq = (key: string, vars?: Record<string, string | number>, fallback?: string) =>
    trv(key, fallback || key, vars);

  // A04: kunci draft jawaban kuis = notebook + generasi kuis terbaru.
  const quizGen = useMemo(
    () => activeGenList.find((g: any) => String(g?.gtype || '') === 'quiz'),
    [activeGenList],
  );
  const quizDraftKey = `cl_learning_quiz_draft_${activeNotebook?.id ?? 'nb'}_${quizGen?.id ?? 'local'}`;

  // A05: ringkasan sumber untuk dialog (jumlah sumber + total kata).
  const sourceWords = useMemo(() => {
    const list = (activeNotebook?.sources || []) as any[];
    // A07: pakai `wordCount` dari server (dihitung dari isi penuh) bila tersedia;
    // fallback ke hitung dari `content` (dipotong 4000 char oleh API) seperti A05.
    return list.reduce((sum, s) => {
      const wc = Number(s?.wordCount);
      if (Number.isFinite(wc) && wc > 0) return sum + wc;
      return sum + String(s?.content || '').trim().split(/\s+/).filter(Boolean).length;
    }, 0);
  }, [activeNotebook]);
  const sourceCount = ((activeNotebook?.sources || []) as any[]).length;

  // A07: sumber baru otomatis "dipakai"; sumber yang dihapus dibuang dari daftar
  // pilihan supaya chip Dipakai/Tidak dipakai selalu konsisten dengan kartu yang tampak.
  const sourceIdsKey = ((activeNotebook?.sources || []) as any[]).map((x) => String(x?.id)).join(',');
  useEffect(() => {
    const ids = sourceIdsKey ? sourceIdsKey.split(',') : [];
    setUsedSourceIds((prev) => {
      const kept = prev.filter((id) => ids.includes(id));
      const added = ids.filter((id) => !prev.includes(id));
      return added.length ? [...kept, ...added] : kept;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sourceIdsKey]);

  // A05: pengaturan terakhir tipe aktif — ditampilkan di panel sebagai ringkasan.
  const activeStudioKind = activeStudioType as StudioKind;
  const lastCfgSummary = useMemo(() => {
    if (!activeNotebook?.id) return '';
    return summarizeStudioConfig(activeStudioKind, loadStudioConfig(activeNotebook.id, activeStudioKind), trq);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNotebook?.id, activeStudioKind, cfgTick]);
  const draftLoadedRef = useRef<string>('');

  // A04: muat draft (jawaban + nilai mandiri) saat notebook/generasi kuis berganti.
  useEffect(() => {
    if (!activeNotebook?.id) return;
    if (draftLoadedRef.current === quizDraftKey) return;
    draftLoadedRef.current = quizDraftKey;
    setQuizReviewed(false);
    setShowModelAnswers(false);
    let draft: any = null;
    try {
      draft = JSON.parse(localStorage.getItem(quizDraftKey) || 'null');
    } catch {
      draft = null;
    }
    setSelectedAnswers(draft?.answers || {});
    setEssayAnswers(draft?.essays || {});
    setEssayMarks(draft?.marks || {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quizDraftKey, activeNotebook?.id]);

  // A04: auto-save draft — jawaban tidak hilang saat pindah panel/tab atau refresh.
  useEffect(() => {
    if (!activeNotebook?.id) return;
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(quizDraftKey, JSON.stringify({
          answers: selectedAnswers, essays: essayAnswers, marks: essayMarks, at: Date.now(),
        }));
      } catch { /* localStorage penuh / diblokir — abaikan */ }
    }, 400);
    return () => clearTimeout(timer);
  }, [selectedAnswers, essayAnswers, essayMarks, quizDraftKey, activeNotebook?.id]);

  // ── Studio output renderers (parity LearningPage studio_output_stack) ──
  const renderFlashcards = () => {
    const cards = activeNotebook?.flashcards || [];
    if (!cards.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500"><Layers className="w-8 h-8 mx-auto mb-2 text-slate-600" /><p className="text-sm font-medium">{tr('no_flashcards_yet', 'No flashcards yet.')}</p><p className="text-xs mt-1">{tr('click_the_flashcards_button', 'Click the Flashcards button.')}</p></div>
      );
    }
    const idx = Math.min(currentCardIndex, cards.length - 1);
    return (
      <div className="flex flex-col items-center space-y-4 py-2">
        <div onClick={() => setIsCardFlipped(!isCardFlipped)} className="w-full min-h-[200px] p-6 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700/80 rounded-2xl shadow-xl flex flex-col items-center justify-center text-center cursor-pointer transition-all hover:border-violet-500/50 select-none">
          <span className="text-xs font-bold text-slate-500 mb-1">{idx + 1} / {cards.length}</span>
          <span className="text-xs font-bold uppercase tracking-wider text-violet-400 mb-2">{isCardFlipped ? tr('answer', 'Answer') : tr('question', 'Question')}</span>
          <p className="text-base font-semibold text-slate-100">{isCardFlipped ? cards[idx]?.answer : cards[idx]?.question}</p>
          <span className="text-[11px] text-slate-500 mt-2">{tr('click_to_flip', 'Click to flip')}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { setIsCardFlipped(false); setCurrentCardIndex((p) => (p > 0 ? p - 1 : cards.length - 1)); }} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200">{tr('prev', '‹ Prev')}</button>
          <button onClick={() => setIsCardFlipped(!isCardFlipped)} className="px-3 py-1.5 bg-violet-600/30 hover:bg-violet-600/40 text-violet-300 text-xs font-bold rounded-lg border border-violet-500/30">{tr('flip', 'Flip')}</button>
          <button onClick={() => { setIsCardFlipped(false); setCurrentCardIndex((p) => (p < cards.length - 1 ? p + 1 : 0)); }} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200">{tr('next', 'Next ›')}</button>
        </div>
      </div>
    );
  };

  const renderQuiz = () => {
    const rawQuizzes: any[] = (activeNotebook?.quizzes || []) as any[];
    if (!rawQuizzes.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500"><HelpCircle className="w-8 h-8 mx-auto mb-2 text-slate-600" /><p className="text-sm font-medium">{tr('no_quiz_yet', 'No quiz yet.')}</p><p className="text-xs mt-1">{tr('click_the_quiz_button', 'Click the Quiz button.')}</p></div>
      );
    }
    // A04: normalisasi soal — kunci jawaban memakai ID SOAL (stabil), dan soal esai
    // tetap dikenali walau server/model lupa mengirim `type` (ciri: tanpa opsi tapi
    // punya jawaban contoh). Sebelumnya soal esai kehilangan penandanya saat
    // notebook di-refetch → tampil seperti PG tanpa opsi = "tidak bisa mengetik".
    const items = rawQuizzes.map((q: any, i: number) => {
      const options = Array.isArray(q.options) ? q.options : [];
      const modelAnswer = String(q.modelAnswer || q.model_answer || '');
      const type = String(q.type || '').toLowerCase();
      const isEssay = type === 'essay' || (type !== 'mc' && !options.length && !!modelAnswer);
      return { ...q, key: String(q.id ?? i), options, modelAnswer, isEssay };
    });
    const mcItems = items.filter((q) => !q.isEssay);
    const essayItems = items.filter((q) => q.isEssay);
    const mcCorrect = mcItems.filter((q) => Number(selectedAnswers[q.key]) === Number(q.correctAnswerIndex)).length;
    const essayPoints = essayItems.reduce((sum, q) => sum + (Number(essayMarks[q.key]) || 0), 0);
    const scoreTotal = mcItems.length + essayItems.length;
    const scoreGot = mcCorrect + essayPoints;
    const scorePct = scoreTotal ? Math.round((scoreGot / scoreTotal) * 100) : 0;
    const fmtScore = (v: number) => (Number.isInteger(v) ? String(v) : v.toFixed(1));

    return (
      <div className="space-y-4">
        {quizReviewed && (
          <div className="p-3 bg-violet-950/40 border border-violet-500/40 rounded-xl space-y-1">
            <div className="text-sm font-black text-violet-100">
              {tr('quiz_score', 'Skor')}: {fmtScore(scoreGot)}/{scoreTotal} ({scorePct}%)
            </div>
            <div className="text-[11px] text-violet-200/80">
              {trv('learning_quiz_score_detail', 'PG {mcCorrect}/{mcTotal} · Essay {essayPoints}/{essayTotal}', {
                mcCorrect, mcTotal: mcItems.length, essayPoints: fmtScore(essayPoints), essayTotal: essayItems.length,
              })}
            </div>
            <div className="text-[10px] text-violet-200/60">
              {trv('learning_quiz_score_hint', 'Nilai essay diisi mandiri (Sesuai = 1 · Sebagian = 0.5).', {})}
            </div>
          </div>
        )}
        {items.map((q, qIndex) => {
          const userChoice = selectedAnswers[q.key];
          const isCorrect = Number(userChoice) === Number(q.correctAnswerIndex);
          return (
            <div key={q.key} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
              <h4 className="font-bold text-sm text-slate-200">{qIndex + 1}. {q.question}{q.isEssay && <span className="ml-2 text-[10px] uppercase px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 align-middle">Essay</span>}</h4>
              {q.isEssay ? (
                <>
                  {/* A04: textarea TIDAK PERNAH disabled — user tetap bisa memperbaiki
                      jawaban setelah menekan Evaluate (dulu `disabled={quizSubmitted}`
                      membuat kolom jawaban terkunci). */}
                  <textarea
                    value={essayAnswers[q.key] ?? ''}
                    onChange={(e) => setEssayAnswers((prev) => ({ ...prev, [q.key]: e.target.value }))}
                    placeholder={tr('essay_answer_ph', 'Tulis jawabanmu di sini…')}
                    rows={3}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 resize-y focus:outline-none focus:border-violet-500"
                  />
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">{tr('learning_quiz_essay_self_mark', 'Nilai mandiri')}</span>
                    {([
                      [1, 'learning_quiz_essay_done', '✅ Sesuai'],
                      [0.5, 'learning_quiz_essay_partial', '🟡 Sebagian'],
                      [0, 'learning_quiz_essay_missing', '❌ Belum'],
                    ] as const).map(([val, key, fb]) => {
                      const active = (Number(essayMarks[q.key]) || 0) === val && (essayMarks[q.key] !== undefined);
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => setEssayMarks((prev) => ({ ...prev, [q.key]: val }))}
                          className={`px-2 py-1 rounded-lg text-[10px] font-bold border transition-colors ${active ? 'bg-emerald-600/25 border-emerald-500/50 text-emerald-200' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-emerald-500/40'}`}
                        >
                          {tr(key, fb)}
                        </button>
                      );
                    })}
                    <span className="ml-auto text-[10px] font-mono text-slate-500">{fmtScore(Number(essayMarks[q.key]) || 0)} / 1</span>
                  </div>
                  {(showModelAnswers || quizReviewed) && (q.modelAnswer ? (
                    <p className="text-xs text-slate-400 bg-slate-900/80 p-2 rounded-lg border border-slate-800/80"><span className="font-bold text-slate-300">{tr('quiz_model_answer', '💡 Jawaban contoh')}:</span> {q.modelAnswer}</p>
                  ) : (
                    <p className="text-[10px] text-amber-300">{tr('learning_quiz_no_model_answer', 'Soal ini tidak menyertakan jawaban contoh.')}</p>
                  ))}
                </>
              ) : (
                <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {q.options.map((opt: string, optIndex: number) => {
                  const isSelected = Number(userChoice) === optIndex;
                  let btnStyle = 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700';
                  if (quizReviewed) {
                    if (optIndex === Number(q.correctAnswerIndex)) btnStyle = 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300 font-semibold';
                    else if (isSelected && !isCorrect) btnStyle = 'bg-rose-950/60 border-rose-500/60 text-rose-300';
                  } else if (isSelected) btnStyle = 'bg-violet-950/60 border-violet-500/60 text-violet-200 font-semibold';
                  return (
                    <button key={optIndex} disabled={quizReviewed} onClick={() => setSelectedAnswers((prev) => ({ ...prev, [q.key]: optIndex }))} className={`p-2.5 text-left rounded-xl border text-xs transition-colors flex items-center justify-between ${btnStyle}`}>
                      <span>{opt}</span>
                      {quizReviewed && optIndex === Number(q.correctAnswerIndex) && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                      {quizReviewed && isSelected && !isCorrect && <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                    </button>
                  );
                })}
              </div>
              {quizReviewed && q.explanation && <p className="text-xs text-slate-400 bg-slate-900/80 p-2 rounded-lg border border-slate-800/80"><span className="font-bold text-slate-300">{tr('explanation', 'Explanation:')}</span> {q.explanation}</p>}
                </>
              )}
            </div>
          );
        })}
        <div className="flex flex-wrap justify-end gap-2 pt-1">
          <button onClick={() => setShowModelAnswers((v) => !v)} className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-xl">
            <Eye className="w-3.5 h-3.5" />
            <span>{showModelAnswers ? tr('learning_quiz_hide_model_answers', 'Sembunyikan jawaban contoh') : tr('learning_quiz_show_model_answers', 'Lihat semua jawaban contoh')}</span>
          </button>
          {!quizReviewed ? (
            <button onClick={() => { setQuizReviewed(true); showToast('success', tr('learning_quiz_evaluated', 'Quiz Evaluated'), tr('learning_quiz_check_score', 'Check your score.')); }} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl">{tr('evaluate', 'Evaluate')}</button>
          ) : (
            <>
              <button onClick={() => setQuizReviewed(false)} className="flex items-center gap-1.5 px-4 py-2 bg-violet-600/30 hover:bg-violet-600/40 text-violet-200 font-bold text-xs rounded-xl border border-violet-500/40">
                <RotateCcw className="w-3.5 h-3.5" /><span>{tr('learning_quiz_review_again', 'Evaluasi ulang')}</span>
              </button>
              <button onClick={() => { setQuizReviewed(false); setSelectedAnswers({}); setEssayAnswers({}); setEssayMarks({}); try { localStorage.removeItem(quizDraftKey); } catch { /* ignore */ } }} className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-xl">
                <RotateCcw className="w-3.5 h-3.5" /><span>{tr('retake', 'Retake')}</span>
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  const renderPodcast = () => {
    const lines: any[] = (activeNotebook as any)?.podcast || [];
    if (!lines.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
          <Headphones className="w-8 h-8 mx-auto mb-2 text-slate-600" />
          <p className="text-sm font-medium">{tr('no_episode_yet', 'No episode yet.')}</p>
          <p className="text-xs mt-1">{tr('click_the_podcast_button', 'Click the Podcast button.')}</p>
        </div>
      );
    }
    const gen = selectedGen && normalizeArtifactType((selectedGen as any).gtype) === 'podcast'
      ? selectedGen as any : latestPodcastGen;
    return (
      <PodcastPlayer
        audio={podcastAudio}
        title={gen?.title || gen?.topic || tr('deep_dive_episode', 'Deep Dive Episode')}
        generationId={gen ? String(gen.id) : undefined}
        fontSize={studioFontSize}
        busy={podcastBusy}
        onGenerate={(force) => handleGeneratePodcastAudio(force)}
        tr={trq}
      />
    );
  };

  const renderStudioMarkdown = () => {
    if (activeStudioType === 'mindmap') {
      return <MindMapView raw={(activeNotebook as any).mindMap} lang={lang} fontSize={studioFontSize} />;
    }
    // C05: 3 tipe JSON baru memakai slot server (terbaru, pola mindmap).
    if (activeStudioType === 'data-table') {
      return <DataTableView data={(activeNotebook as any).dataTable} tr={trq} />;
    }
    if (activeStudioType === 'infographic') {
      return <InfographicView data={(activeNotebook as any).infographic} tr={trq} />;
    }
    if (activeStudioType === 'slide-deck') {
      return <SlideDeckView data={(activeNotebook as any).slideDeck} tr={trq} />;
    }
    if (selectedGen) {
      return (
        <div className="space-y-2"><div className="text-[10px] uppercase tracking-wider text-violet-400">{selectedGen.gtype} · {selectedGen.topic || '-'} · {selectedGen.createdAt || ''}</div><ReactMarkdown>{String(selectedGen.content || '')}</ReactMarkdown></div>
      );
    }
    return (<>{['studyGuide', 'faq', 'timeline', 'summary', 'briefingDoc'].map((f) => ((activeNotebook as any)[f] ? <ReactMarkdown key={f}>{String((activeNotebook as any)[f])}</ReactMarkdown> : null))}</>);
  };

  // AI Chat Handler
  // P48 FIX (chat AI terkirim dobel): addNotebookChat kini murni append lokal,
  // sehingga studio.chat() di bawah adalah SATU-SATUNYA request per pesan.
  // (Dulu: addNotebookChat('user') ikut memanggil API + await studio.chat()
  // lagi di sini = 2 request → 2 blok user + 2 jawaban tersimpan di server.)
  // A07: `override` = teks eksplisit dari kartu saran; pemanggilan dari onClick biasa
  // mengirim MouseEvent, karena itu argumen non-string diabaikan.
  const handleSendChat = async (override?: string) => {
    const raw = typeof override === 'string' ? override : chatInput;
    if (!raw.trim() || !activeNotebook || isAiLoading) return;
    const userMsg = raw.trim();
    setChatInput('');
    // Tampil optimistic lokal; server menyimpan pasangan user+jawaban pada
    // request di bawah (source of truth tetap tabel learning_chats).
    addNotebookChat(activeNotebook.id, userMsg, 'user');
    setIsAiLoading(true);

    try {
      // A08: kirim daftar sumber terpilih → AI hanya menjawab dari sumber itu
      // dan mengembalikan sitasi yang bisa diklik.
      const data = await studio.chat(activeNotebook.id, userMsg, usedSourceIds);
      const result = data.result || data;
      const reply = result.answer || data.answer || data.reply;
      const citations = result.citations || data.citations || [];
      addNotebookChat(activeNotebook.id, reply || data.error || 'Failed to get response', 'ai', citations);
      if (citations.length) {
        showToast('info', tr('learning_citations', 'Sitasi'),
          trv('learning_citations_found', '{n} kutipan sumber ditandai pada jawaban.', { n: citations.length }));
      }
    } catch {
      addNotebookChat(
        activeNotebook.id,
        `[Local Knowledge Response]\nReviewed sources for "${activeNotebook.title}". Query "${userMsg}" analyzed.`,
        'ai'
      );
    } finally {
      setIsAiLoading(false);
    }
  };

  // Generate Flashcards
  // A05: `extra` = opsi dari dialog (jumlah kartu, gaya kartu, kesulitan, bahasa, fokus).
  const handleGenerateFlashcards = async (extra: Record<string, unknown> = {}) => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', tr('ai_thinking', 'AI Thinking'), tr('learning_gen_flashcards', 'Menyusun kartu belajar…'));

    try {
      const data = await studio.generate('flashcards', {
        content: combined,
        topic: studioTopic.trim() || activeNotebook.title,
        notebookId: activeNotebook.id,
        count: Number(extra.count) || 15,
        ...extra,
      });
      const cards = data.flashcards || data.result?.flashcards || [];
      if (cards.length > 0) {
        setActiveStudioType('flashcards');
        setCurrentCardIndex(0);
        setIsCardFlipped(false);
        updateNotebook(activeNotebook.id, {
          flashcards: cards.map((f: any, i: number) => ({ id: 'fc_' + Date.now() + '_' + i, ...f })),
        });
        showToast('success', tr('learning_gen_done_title', 'Selesai'), trv('learning_gen_flashcards_done', '{n} kartu siap.', { n: cards.length }));
        refreshNotebooks();
      } else {
        showToast('damage', 'AI', data.msg || 'empty');
      }
    } catch {
      showToast('damage', 'AI Error', tr('learning_gen_flashcards_failed', 'Gagal membuat kartu belajar.'));
    } finally {
      setIsAiLoading(false);
    }
  };

  // Generate Quiz
  // A04: mengirim DUA counter (mcCount/essayCount) — jumlah PG & essay diatur user,
  // total gabungan dijaga ≤ 30 di UI dan di server (learning_helper).
  const handleGenerateQuiz = async (extra: Record<string, unknown> = {}) => {
    if (!activeNotebook) return;
    const mc = Number(extra.mcCount ?? QUIZ_DEFAULT_MC) || 0;
    const essay = Number(extra.essayCount ?? QUIZ_DEFAULT_ESSAY) || 0;
    const total = mc + essay;
    if (total > QUIZ_TOTAL_MAX) {
      showToast('damage', tr('learning_quiz_count_title', 'Jumlah soal kuis'),
        tr('learning_quiz_total_over', 'Total melebihi 30 soal — kurangi salah satu.'));
      return;
    }
    if (total <= 0) {
      showToast('damage', tr('learning_quiz_count_title', 'Jumlah soal kuis'),
        tr('learning_quiz_total_zero', 'Isi minimal satu jenis soal.'));
      return;
    }
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', tr('ai_thinking', 'AI Thinking'),
      trv('learning_quiz_generating', 'Menyusun {mc} soal PG + {essay} soal essay…', { mc, essay }));

    try {
      const data = await studio.generate('quiz', {
        content: combined,
        topic: studioTopic.trim() || activeNotebook.title,
        notebookId: activeNotebook.id,
        count: total,
        mcCount: mc,
        essayCount: essay,
        ...extra,
      });
      const quiz = data.quiz || data.result?.quiz || [];
      if (quiz.length > 0) {
        setActiveStudioType('quiz');
        updateNotebook(activeNotebook.id, {
          quizzes: quiz.map((q: any, i: number) => ({ id: 'q_' + Date.now() + '_' + i, ...q })),
        });
        setSelectedAnswers({});
        setQuizReviewed(false);
        setEssayAnswers({});
        setEssayMarks({});
        setShowModelAnswers(false);
        try { localStorage.removeItem(quizDraftKey); } catch { /* ignore */ }
        showToast('success', tr('learning_quiz_ready_title', 'Kuis siap'),
          trv('learning_quiz_ready_msg', '{n} soal siap dikerjakan.', { n: quiz.length }));
        refreshNotebooks();
      } else {
        showToast('damage', 'AI', data.msg || 'empty');
      }
    } catch {
      showToast('damage', 'AI Error', 'Could not generate quiz.');
    } finally {
      setIsAiLoading(false);
    }
  };

  // Generate Podcast Script
  const handleGeneratePodcast = async (extra: Record<string, unknown> = {}) => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', tr('learning_gen_audio_title', 'AI Audio Overview'), tr('learning_gen_audio', 'Menulis dialog dua host…'));

    try {
      const data = await studio.generate('podcast', {
        content: combined,
        topic: studioTopic.trim() || activeNotebook.title,
        notebookId: activeNotebook.id,
        ...extra,
      });
      const dialogue = data.podcast || data.dialogue || data.result?.podcast || [];
      if (dialogue.length > 0) {
        setActiveStudioType('podcast');
        setCurrentLineIndex(0);
        updateNotebook(activeNotebook.id, { podcast: dialogue });
        showToast('success', tr('learning_gen_done_title', 'Selesai'), trv('learning_gen_audio_done', '{n} giliran dialog siap.', { n: dialogue.length }));
        refreshNotebooks();
      } else {
        showToast('damage', 'AI', data.msg || 'empty');
      }
    } catch {
      showToast('damage', 'AI Error', tr('learning_gen_audio_failed', 'Gagal membuat dialog audio.'));
    } finally {
      setIsAiLoading(false);
    }
  };

  // Solve Math Problem
  const handleSolveMath = async () => {
    if (!mathProblem.trim()) return;
    setIsSolvingMath(true);
    try {
      const data = await studio.generate('solve-math', { expression: mathProblem, content: mathProblem });
      setMathSolution(data.preview || data.solution || data.result?.preview || 'No solution available.');
    } catch {
      setMathSolution('### Formula Breakdown\n\n- Quadratic: $x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$\n- Roots: $x = 2, x = 3$');
    } finally {
      setIsSolvingMath(false);
    }
  };


  const handleGenerateStudio = async (kind: string, extra: Record<string, unknown> = {}) => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    try {
      const data = await studio.generate(kind, {
        content: combined,
        topic: studioTopic.trim() || activeNotebook.title,
        notebookId: activeNotebook.id,
        ...extra,
      });
      const payload: any = {};
      if (kind === 'study-guide') payload.studyGuide = data.studyGuide || data.result?.studyGuide || data.raw;
      if (kind === 'mindmap') payload.mindMap = data.mindMap || data.result?.mindMap;
      if (kind === 'faq') payload.faq = data.faq || data.result?.faq || data.raw;
      if (kind === 'timeline') payload.timeline = data.timeline || data.result?.timeline || data.raw;
      if (kind === 'summary') payload.summary = data.summary || data.result?.summary || data.raw;
      if (kind === 'briefing-doc') payload.briefingDoc = data.briefingDoc || data.result?.briefingDoc || data.raw;
      if (kind === 'data-table') payload.dataTable = data.dataTable || data.result?.dataTable;
      if (kind === 'infographic') payload.infographic = data.infographic || data.result?.infographic;
      if (kind === 'slide-deck') payload.slideDeck = data.slideDeck || data.result?.slideDeck;
      updateNotebook(activeNotebook.id, payload);
      setActiveStudioType(kind as StudioType);
      showToast('success', tr('learning_gen_done_title', 'Selesai'), trv('learning_gen_done_msg', '{type} siap dipakai.', { type: kind }));
      setSelectedGen(null);
      refreshNotebooks();
    } catch {
      showToast('damage', 'AI Error', kind);
    } finally {
      setIsAiLoading(false);
    }
  };

  // A08: generasi podcast terbaru + audio tersimpan (agar audio lama tetap bisa diputar
  // setelah reload tanpa menyusun ulang).
  const latestPodcastGen = useMemo(
    () => (activeGenList as any[]).find((g: any) => normalizeArtifactType(g.gtype) === 'podcast') || null,
    [activeGenList],
  );
  useEffect(() => {
    const saved = latestPodcastGen?.audio;
    setPodcastAudio(saved ? { ...saved, url: `${apiBase()}${saved.url || ''}` } : null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeNotebook?.id, latestPodcastGen?.id, latestPodcastGen?.audio?.url]);

  // A06: kartu yang isinya SAMA dengan area interaktif = generasi TERBARU tipe itu
  // (server mengirim `generations` urut terbaru → terlama).
  const interactiveArtifactId = useMemo(() => {
    const hit = (activeGenList as any[]).find((g: any) => normalizeArtifactType(g.gtype) === activeStudioType);
    return hit ? String(hit.id) : null;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGenList, activeStudioType]);

  // A06: daftar artefak = seluruh generasi notebook ini (urut terbaru dari server).
  const artifacts: ArtifactItem[] = useMemo(
    () => (activeGenList as any[]).map((g: any) => ({
      id: String(g.id ?? ''),
      gtype: String(g.gtype || 'summary'),
      title: String(g.title || g.topic || ''),
      createdAt: g.createdAt || '',
      updatedAt: g.updatedAt || '',
      content: g.content || '',
      itemCount: Number(g.itemCount) || 0,
      words: Number(g.words) || 0,
      sizeBytes: Number(g.sizeBytes) || 0,
    })),
    [activeGenList],
  );

  // A05: satu pintu masuk dari dialog/quick-generate ke handler per tipe.
  const dispatchStudioGenerate = (kind: StudioKind, payload: Record<string, unknown>) => {
    if (kind === 'quiz') return handleGenerateQuiz(payload);
    if (kind === 'flashcards') return handleGenerateFlashcards(payload);
    if (kind === 'podcast') return handleGeneratePodcast(payload);
    return handleGenerateStudio(STUDIO_META[kind].apiKind, payload);
  };

  // A05: klik dialog "Generate sekarang" — payload sudah diserialisasi oleh dialog.
  const handleDialogGenerate = (kind: StudioKind, payload: Record<string, unknown>) => {
    setStudioDialogKind(null);
    setCfgTick((v) => v + 1);
    dispatchStudioGenerate(kind, payload);
  };

  // A05: tombol ⚡ di kartu — generate langsung dengan pengaturan terakhir (power user).
  const handleQuickGenerate = (kind: StudioKind) => {
    if (!activeNotebook?.id) return;
    setCfgTick((v) => v + 1);
    dispatchStudioGenerate(kind, buildStudioPayload(kind, loadStudioConfig(activeNotebook.id, kind)));
  };

  // A08: buat / buat-ulang audio podcast dua host.
  // Dulu pemutar memakai `window.speechSynthesis` TANPA `lang` sehingga suara
  // Inggris membacakan teks Indonesia; kini audio MP3 nyata dengan suara yang
  // mengikuti bahasa transkrip + offset per giliran supaya bisa dilompati.
  const handleGeneratePodcastAudio = async (force = false) => {
    if (!activeNotebook) return;
    const bySelected = selectedGen && normalizeArtifactType((selectedGen as any).gtype) === 'podcast'
      ? selectedGen as any : null;
    const gen = bySelected || (activeGenList as any[]).find((g: any) => normalizeArtifactType(g.gtype) === 'podcast');
    if (!gen?.id) {
      showToast('damage', tr('learning_podcast_generate', 'Buat voice'),
        tr('learning_no_podcast', 'Buat transkrip Podcast dulu, lalu susun audionya.'));
      return;
    }
    setPodcastBusy(true);
    try {
      const r = await studio.podcastAudio(activeNotebook.id, String(gen.id), force);
      const res = r?.result || r;
      if (res?.ok === false) {
        showToast('damage', tr('learning_podcast_audio_failed', 'Gagal membuat audio'),
          String(res?.msg || '').slice(0, 160));
        return;
      }
      setPodcastAudio({
        // `apiBase()` penting agar <audio src> tetap benar saat dibuka lewat WebEngine.
        url: `${apiBase()}${res.url || ''}`,
        durationSec: res.durationSec || 0,
        sizeBytes: res.sizeBytes || 0,
        language: res.language || 'id',
        engine: res.engine || '',
        voiceA: res.voiceA || '',
        voiceB: res.voiceB || '',
        turns: res.turns || [],
      });
      showToast('success', tr('learning_podcast_audio_ready', 'Audio siap'),
        tr('learning_podcast_audio_ready_detail',
          'Klik salah satu giliran untuk melompat ke bagian itu.'));
    } catch (e) {
      showToast('damage', tr('learning_podcast_audio_failed', 'Gagal membuat audio'),
        String((e as any)?.message || e));
    } finally {
      setPodcastBusy(false);
    }
  };

  return (
    <div id="learning-workspace-view" className="space-y-4">
      {/* Header halaman (parity _page_header) — ringkas; kontrol notebook kini tinggal di
          topbar LearningShell (A07) supaya tata letak menyerupai NotebookLM. */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-11 h-11 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-xl">📚</div>
          <div>
            <h1 className="text-lg font-bold text-slate-100">{tr('ai_learning_workspace', 'AI Learning Workspace')}</h1>
            <p className="text-[11px] text-slate-400">{tr('sources_chat_studio_in_one_grounded_learning_wor', 'Sources + Chat + Studio in one grounded learning workspace.')}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="ct-nlm-chip ct-nlm-num">{tr('ai', 'AI')}</span>
          {/* Parity _manage_api_key */}
          <button
            onClick={() => { const k = window.prompt(tr('learning_api_key_label', 'Gemini API key'), geminiKey); if (k !== null && k !== geminiKey) { setGeminiKey(k); studio.setGeminiKey(k).then(() => showToast('success', 'Gemini', 'saved')).catch((e) => showToast('damage', String(e), '')); } }}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-[11px] font-bold rounded-xl border border-slate-700"
          >
            <KeyRound className="w-3.5 h-3.5" /><span>{tr('learning_api_btn', 'API Key')}</span>
          </button>
          <button onClick={() => setShowNewNbModal(true)} className="flex items-center gap-1.5 px-3 py-2 bg-violet-600 hover:bg-violet-500 text-white text-[11px] font-bold rounded-xl">
            <Plus className="w-3.5 h-3.5" /><span>{tr('learning_new_notebook_title', 'New Notebook')}</span>
          </button>
        </div>
      </div>

      {activeNotebook ? (
        <LearningShell
          view={view}
          onView={setView}
          tr={trq}
          rail={
            <NotebookRail
              // A15: ikon notebook diteruskan apa adanya ke rail kiri (kini tersimpan di server).
              notebooks={notebooks.map((nb) => ({ id: nb.id, title: nb.title, icon: nb.icon }))}
              activeId={activeNotebook.id}
              expanded={false}
              onToggleExpanded={() => undefined}
              onSelect={(id) => setActiveNotebookId(id)}
              onCreate={() => setShowNewNbModal(true)}
              onRename={openRenameDialog}
              onDelete={() => { if (notebooks.length > 1 && window.confirm(tr('learning_delete_confirm', 'Hapus notebook ini?'))) deleteNotebook(activeNotebook.id); }}
              lang={lang}
              onLang={handleLanguageChange}
              tr={trq}
            />
          }
          topbar={
            /* Topbar: judul notebook bisa langsung diganti (inline) + chip status + aksi. */
            <div className="ct-nlm-topbar p-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-lg leading-none">{activeNotebook.icon || '📚'}</span>
                <input
                  value={nbTitleDraft}
                  onChange={(e) => setNbTitleDraft(e.target.value)}
                  onBlur={commitNotebookTitle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') { e.preventDefault(); commitNotebookTitle(); }
                    if (e.key === 'Escape') setNbTitleDraft(activeNotebook.title);
                  }}
                  className="ct-nlm-title-input text-[15px] flex-1 min-w-[8rem]"
                  title={tr('learning_rename_notebook', 'Ganti nama notebook')}
                />
                <span className="ct-nlm-chip ct-nlm-num">
                  {trq('learning_topbar_sources', { n: sourceCount }, '{n} sumber')}
                </span>
                <span className="ct-nlm-chip is-muted ct-nlm-num">
                  {sourceWords} {tr('words', 'kata')}
                </span>
                <span className="ct-nlm-chip is-ok hidden sm:inline-flex">
                  {tr('learning_topbar_ready', 'Siap dijawab AI')}
                </span>
                <div className="ml-auto flex items-center gap-1.5">
                  <button
                    onClick={openRenameDialog}
                    className="ct-btn ct-btn-secondary ct-btn-sm hidden lg:inline-flex items-center gap-1"
                    title={tr('learning_rename_notebook', 'Ganti nama notebook')}
                  >
                    <Pencil className="w-3.5 h-3.5" />{tr('learning_rename_short', 'Ganti nama')}
                  </button>
                  <button
                    onClick={handleExportStudio}
                    className="ct-btn ct-btn-success ct-btn-sm flex items-center gap-1"
                    title={tr('learning_export', 'Ekspor')}
                  >
                    <Download className="w-3.5 h-3.5" /><span className="hidden sm:inline">{tr('learning_export_compact', 'Ekspor')}</span>
                  </button>
                </div>
              </div>
            </div>
          }
          sources={
            <SourcesRail
              sources={(activeNotebook.sources || []).map((src) => ({
                id: String(src.id),
                title: src.title,
                type: String((src as any).type || 'text'),
                wordCount: Number(src.wordCount) || 0,
                createdAt: (src as any).createdAt,
                fileName: (src as any).fileName || '',
                fileSize: Number((src as any).fileSize) || 0,
                hasFile: Boolean((src as any).hasFile),
                summary: (src as any).summary || '',
              }))}
              uploadOne={uploadOneSource}
              onQueueDone={handleQueueDone}
              usedIds={usedSourceIds}
              onToggleUsed={toggleSourceUsed}
              onAddPaste={() => setShowNewSourceModal(true)}
              onOpenSource={handleViewSource}
              onDeleteSource={(id) => deleteNotebookSource(activeNotebook.id, id)}
              onOpenFull={() => setView('chat')}
              tr={trq}
            />
          }
          chat={
            <ChatPanel
              messages={(activeNotebook.chatHistory || []).map((m: any) => ({
                sender: m.sender,
                text: m.text,
                timestamp: m.timestamp,
                citations: Array.isArray(m.citations) ? m.citations : [],
              })) as any}
              input={chatInput}
              onInput={setChatInput}
              onSend={handleSendChat}
              loading={isAiLoading}
              font={chatFontSize}
              onFont={(d) => setChatFontSize((v) => clampFont(v + d))}
              onClear={() => {
                // P48: bersihkan JUGA history di server — dulu hanya set state
                // lokal sehingga chat muncul lagi setelah reload/restart.
                studio.clearChat(activeNotebook.id)
                  .catch(() => undefined)
                  .finally(() => updateNotebook(activeNotebook.id, { chatHistory: [] }));
              }}
              onSuggestion={(text) => { setChatInput(''); handleSendChat(text); }}
              suggestions={buildSuggestions((activeNotebook.sources || []).map((s: any) => s.title), trq)}
              onSaveNote={handleSaveNote}
              notesCount={((activeNotebook as any).savedNotes || []).length}
              onOpenNotes={() => { setExpandedNote(null); setShowNotesModal(true); }}
              sourcesUsed={usedSourceIds.length}
              sourcesTotal={(activeNotebook.sources || []).length}
              onOpenSources={() => setView('sources')}
              onOpenSource={(sid) => { void handleViewSource(sid); }}
              tr={trq}
            />
          }
          studio={
            /* ── STUDIO PANEL (daftar artefak A06 + peluncur 8 generator A05) ── */
            <section className="ct-nlm-panel flex flex-col p-3 gap-2.5" aria-label={tr('learning_studio_panel', 'Studio')}>
                <div className="flex items-center justify-between">
                  <span className="text-[12px] font-black uppercase tracking-wider text-slate-300">{tr('learning_studio_panel', 'Studio')}</span>
                  <span className="text-[10px] text-slate-500">{tr('learning_studio_hint', 'Buat materi dari sumber')}</span>
                </div>

                {/* Font controls (parity studio font row) */}
                <div className="flex items-center gap-1 text-[11px] text-slate-400">
                  <span>{tr('learning_font_studio', 'Font Hasil')}:</span>
                  <button onClick={() => setStudioFontSize((v) => clampFont(v - 1))} className="ct-btn ct-btn-secondary ct-btn-sm">{tr('learning_font_decrease', 'A−')}</button>
                  <span className="px-1 font-bold text-slate-200 ct-nlm-num">{studioFontSize}px</span>
                  <button onClick={() => setStudioFontSize((v) => clampFont(v + 1))} className="ct-btn ct-btn-secondary ct-btn-sm">{tr('learning_font_increase', 'A+')}</button>
                  <button onClick={() => setStudioFontSize(13)} className="ct-btn ct-btn-secondary ct-btn-sm">{tr('learning_font_reset', 'Reset')}</button>
                  <button onClick={handleExportStudio} className="ct-btn ct-btn-success ct-btn-sm ml-auto flex items-center gap-1" title={tr('learning_export', 'Ekspor')}><Download className="w-3.5 h-3.5" /><span>{tr('learning_export_compact', 'Ekspor')}</span></button>
                </div>

                {/* Topic input */}
                <input type="text" value={studioTopic} onChange={(e) => setStudioTopic(e.target.value)} placeholder={tr('learning_topic_label', 'Topik (kosongkan = semua):')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200" />
                {/* C05: grid 12 tipe — A05: klik = BUKA DIALOG
                    konfigurasi tipe tersebut; tombol ⚡ = generate langsung dengan
                    pengaturan terakhir (perilaku lama tetap tersedia untuk power user). */}
                <div className="grid grid-cols-2 gap-2">
                  {STUDIO_TYPES.map((s) => {
                    const k = s.type as StudioKind;
                    const meta = STUDIO_META[k];
                    return (
                      <div
                        key={s.type}
                        className={`flex items-stretch rounded-lg border transition-colors overflow-hidden ${activeStudioType === s.type ? 'bg-violet-600/20 border-violet-500/50' : 'bg-slate-800 border-slate-700 hover:border-violet-500/40'}`}
                      >
                        <button
                          disabled={isAiLoading}
                          onClick={() => { setStudioDialogKind(k); setActiveStudioType(k); }}
                          className={`flex-1 px-2 py-2 text-xs font-semibold text-left disabled:opacity-50 ${activeStudioType === s.type ? 'text-violet-200' : 'text-slate-300'}`}
                          title={tr('learning_dialog_open_hint', 'Buka pengaturan untuk tipe ini')}
                        >
                          <span className="text-sm mr-1">{s.icon}</span>{tr(s.labelKey, s.type)}
                        </button>
                        <button
                          disabled={isAiLoading}
                          onClick={() => handleQuickGenerate(k)}
                          className="px-1.5 border-l border-slate-700/70 text-amber-300 hover:bg-amber-500/10 disabled:opacity-50"
                          title={tr('learning_dialog_quick_hint', '⚡ Langsung generate dengan pengaturan terakhir')}
                        >
                          ⚡
                        </button>
                      </div>
                    );
                  })}
                </div>

                {/* A05: ringkasan pengaturan terakhir tipe aktif + jalan pintas ke dialog.
                    (Counter PG/Essay & jumlah kartu kini diatur DI DALAM dialog.) */}
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-2.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">{tr('learning_dialog_last_settings', 'Pengaturan terakhir')}</span>
                    <button
                      onClick={() => setStudioDialogKind(activeStudioKind)}
                      disabled={isAiLoading}
                      className="ml-auto text-[10px] font-bold text-violet-300 hover:text-violet-200 disabled:opacity-50"
                    >
                      {tr('learning_dialog_edit_settings', 'Ubah pengaturan')}
                    </button>
                  </div>
                  <p className="text-[10px] text-slate-400 leading-relaxed">{lastCfgSummary || '—'}</p>
                  <p className="text-[9px] text-slate-500">{tr('learning_dialog_quick_hint', '⚡ Langsung generate dengan pengaturan terakhir')}</p>
                </div>

                {/* Output area (parity studio_output_stack) — A06: bisa dilipat karena
                    daftar artefak di bawahnya kini menjadi isi utama panel. */}
                <div className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                  <button
                    onClick={() => setShowStudioPreview((v) => !v)}
                    className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-slate-500 font-bold hover:text-slate-300"
                  >
                    <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showStudioPreview ? '' : '-rotate-90'}`} />
                    {tr('learning_artifact_interactive', 'Pratinjau interaktif')}
                    <span className="text-violet-300 normal-case">· {tr(STUDIO_TYPES.find((x) => x.type === activeStudioType)?.labelKey || '', activeStudioType)}</span>
                  </button>
                  {selectedGen && (
                    <button onClick={() => setSelectedGen(null)} className="ml-auto text-[10px] text-slate-500 hover:text-slate-300">
                      {tr('btn_close', 'Tutup')}
                    </button>
                  )}
                </div>
                {showStudioPreview && (
                  <div style={{ fontSize: studioFontSize }} className="overflow-y-auto max-h-[360px] space-y-3">
                    {activeStudioType === 'flashcards' ? renderFlashcards() : activeStudioType === 'quiz' ? renderQuiz() : activeStudioType === 'podcast' ? renderPodcast() : renderStudioMarkdown()}
                  </div>
                )}

                {/* A06: daftar artefak Studio (list ke bawah) — menggantikan riwayat chip kecil.
                    Kartu: judul · tipe · waktu relatif · jumlah item · ukuran, dengan aksi
                    Buka / Ganti nama / Ekspor .md / Ekspor .txt / Duplikat / Hapus, plus
                    pratinjau isi yang terbuka tepat di bawah kartu (satu scroll). */}
                <div className="pt-2 border-t border-slate-800/80">
                  <StudioArtifactList
                    artifacts={artifacts}
                    activeType={activeStudioType}
                    activeArtifactId={selectedGen ? String(selectedGen.id) : interactiveArtifactId}
                    tr={trq}
                    busy={isAiLoading}
                    onOpen={handleOpenArtifact}
                    onRename={handleRenameArtifact}
                    onDuplicate={handleDuplicateArtifact}
                    onDelete={handleDeleteArtifact}
                    onExport={handleExportArtifact}
                    onSelectType={(t) => setActiveStudioType(normalizeArtifactType(t))}
                  />
                </div>
            </section>
          }
        />
      ) : (
        <div className="p-12 text-center ct-nlm-panel text-slate-500">
          <BookOpen className="w-12 h-12 mx-auto mb-3 text-slate-600" />
          <p className="text-base font-semibold">{tr('select_or_create_a_notebook', 'Select or create a notebook.')}</p>
        </div>
      )}

      {/* A05: dialog konfigurasi per tipe Studio */}
      {studioDialogKind && activeNotebook && (
        <StudioGenerateDialog
          kind={studioDialogKind}
          notebookId={activeNotebook.id}
          sourcesCount={sourceCount}
          words={sourceWords}
          tr={trq}
          busy={isAiLoading}
          onClose={() => setStudioDialogKind(null)}
          onGenerate={(payload) => handleDialogGenerate(studioDialogKind, payload)}
        />
      )}

      {/* Modal: New Notebook */}
      {showNewNbModal && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="ct-dialog p-6 max-w-md w-full space-y-4">
            <h3 className="font-bold text-lg text-slate-100">{tr('create_new_notebook', 'Create New Notebook')}</h3>
            <div className="space-y-3 text-sm">
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('learning_title_label', 'Title')}</label><input type="text" value={newNbTitle} onChange={(e) => setNewNbTitle(e.target.value)} placeholder={tr('learning_nb_title_ph', 'e.g. Physics Dynamics, Machine Learning')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('description', 'Description')}</label><input type="text" value={newNbDesc} onChange={(e) => setNewNbDesc(e.target.value)} placeholder={tr('learning_nb_desc_ph', 'Short summary of this notebook...')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <NotebookIconPicker value={newNbIcon} onChange={setNewNbIcon} label={tr('learning_icon_label', 'Emoji Icon')} />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowNewNbModal(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl">Cancel</button>
              <button onClick={() => { if (!newNbTitle.trim()) return; addNotebook(newNbTitle.trim(), newNbDesc.trim(), newNbIcon); setShowNewNbModal(false); setNewNbTitle(''); setNewNbDesc(''); setNewNbIcon('📚'); }} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white rounded-xl">{tr('create_notebook', 'Create Notebook')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Rename Notebook (parity LearningPage._rename_notebook) */}
      {renaming && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{tr('learning_rename_title', 'Judul notebook baru:')}</h3>
            <input type="text" value={renameTitle} onChange={(e) => setRenameTitle(e.target.value)} autoFocus className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" />
            <NotebookIconPicker value={renameIcon} onChange={setRenameIcon} label={tr('learning_icon_label', 'Emoji Icon')} />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setRenaming(false)} className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-slate-200">{tr('msg_cancel', 'Batal')}</button>
              <button onClick={handleRename} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">{tr('msg_ok', 'OK')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: View Source (parity LearningPage._view_source + berkas asli C02) */}
      {viewingSource && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100 mb-3 shrink-0">{viewingSource.title}</h3>
            {/* Kartu berkas asli */}
            <div className="shrink-0 mb-3 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
              <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">{tr('learning_source_file', 'Berkas asli')}</span>
              {viewingSource.hasFile ? (
                <>
                  <span className="min-w-0 flex-1 truncate text-[11px] font-semibold text-slate-200" title={viewingSource.fileName}>
                    {viewingSource.fileName || viewingSource.title}
                    {viewingSource.fileSize > 0 && <span className="ml-1.5 text-slate-500 ct-nlm-num">· {fmtFileSize(viewingSource.fileSize)}</span>}
                  </span>
                  <button
                    onClick={() => downloadApiFile(studio.learningSourceFileUrl(viewingSource.id), viewingSource.fileName || 'source')}
                    className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1 text-[10px] shrink-0"
                  >
                    <Download className="w-3 h-3" />{tr('learning_source_download', 'Unduh asli')}
                  </button>
                  <button
                    onClick={handleReextract}
                    disabled={reextracting}
                    className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1 text-[10px] shrink-0 disabled:opacity-50"
                  >
                    {reextracting ? '…' : tr('learning_reextract', 'Ekstrak ulang')}
                  </button>
                </>
              ) : (
                <span className="text-[11px] text-slate-500">{tr('learning_nofile', 'Sumber ini tidak punya berkas asli')}</span>
              )}
            </div>
            <div className="overflow-y-auto pr-1 flex-1"><pre className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300 font-mono bg-slate-950/60 border border-slate-800 rounded-xl p-4">{viewingSource.content}</pre></div>
            <div className="flex justify-end mt-4 shrink-0"><button onClick={() => setViewingSource(null)} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">{tr('btn_close', 'Tutup')}</button></div>
          </div>
        </div>
      )}

      {/* Modal C04: Catatan tersimpan */}
      {showNotesModal && activeNotebook && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full max-h-[85vh] flex flex-col shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100 mb-3 shrink-0">{tr('learning_notes_title', 'Catatan tersimpan')}</h3>
            <div className="overflow-y-auto pr-1 flex-1 space-y-2">
              {(((activeNotebook as any).savedNotes || []).length === 0) && (
                <p className="text-[12px] text-slate-500 text-center py-6">{tr('learning_notes_empty', 'Belum ada catatan.')}</p>
              )}
              {((activeNotebook as any).savedNotes || []).map((n: any) => {
                const open = expandedNote === String(n.id);
                const body = String(n.content || '');
                return (
                  <div key={n.id} className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <button onClick={() => setExpandedNote(open ? null : String(n.id))} className="block w-full text-left">
                      <h4 className="font-bold text-[12px] text-slate-100 truncate">{n.title || tr('learning_notes_title', 'Catatan')}</h4>
                      <p className="text-[10px] text-slate-500 mt-0.5">{n.createdAt || ''}</p>
                      {!open && <p className="ct-guide-clamp text-[11px] text-slate-400 mt-1">{body}</p>}
                    </button>
                    {open && <pre className="whitespace-pre-wrap text-[11px] leading-relaxed text-slate-300 font-mono mt-2 max-h-64 overflow-y-auto">{body}</pre>}
                    <div className="flex gap-2 mt-2">
                      <button onClick={() => handleCopyNote(body)} className="ct-btn ct-btn-secondary ct-btn-sm text-[10px]">{tr('learning_note_copy', 'Salin')}</button>
                      <button onClick={() => handleDeleteNote(String(n.id))} className="ct-btn ct-btn-secondary ct-btn-sm text-[10px] text-rose-300">{tr('learning_delete', 'Hapus')}</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="flex justify-end mt-4 shrink-0"><button onClick={() => setShowNotesModal(false)} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">{tr('btn_close', 'Tutup')}</button></div>
          </div>
        </div>
      )}
      {/* Modal: New Source */}
      {showNewSourceModal && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{tr('add_study_source', 'Add Study Source')}</h3>
            <div className="space-y-3 text-sm">
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('source_title', 'Source Title')}</label><input type="text" value={newSourceTitle} onChange={(e) => setNewSourceTitle(e.target.value)} placeholder={tr('learning_source_title_ph', 'e.g. Chapter 1 Notes, Article summary')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('learning_type_label', 'Type')}</label><div className="flex gap-2">{(['text', 'website', 'youtube'] as const).map((mm) => (<button key={mm} onClick={() => { setNewSourceMode(mm); setSourceErr(''); }} className={`ct-socket px-3 py-1.5 text-xs font-bold rounded-lg ${newSourceMode === mm ? 'ct-glow bg-violet-600/30 border-violet-500 text-violet-300' : 'text-slate-400'}`}>{mm === 'text' ? tr('learning_add_text', 'Teks') : mm === 'website' ? tr('learning_add_website', 'Website') : tr('learning_add_youtube', 'YouTube')}</button>))}</div></div>
              {newSourceMode === 'text' && (<div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('learning_type_label', 'Type')}</label><div className="flex gap-2">{(['text', 'doc', 'pdf', 'url'] as const).map((tt) => (<button key={tt} onClick={() => setNewSourceType(tt)} className={`ct-socket px-3 py-1.5 uppercase text-xs font-bold rounded-lg ${newSourceType === tt ? 'ct-glow bg-violet-600/30 border-violet-500 text-violet-300' : 'text-slate-400'}`}>{tt}</button>))}</div></div>)}
              {newSourceMode === 'text' ? (<div><label className="block text-xs font-bold text-slate-400 mb-1">{tr('content_text', 'Content / Text')}</label><textarea rows={6} value={newSourceContent} onChange={(e) => setNewSourceContent(e.target.value)} placeholder={tr('learning_source_content_ph', 'Paste notes, textbook paragraphs, or document content here...')} className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 text-xs focus:outline-none focus:border-violet-500 font-mono" /></div>) : (<div><label className="block text-xs font-bold text-slate-400 mb-1">{newSourceMode === 'youtube' ? tr('learning_add_youtube', 'YouTube') : tr('learning_add_website', 'Website')} URL</label><input type="url" value={newSourceUrl} onChange={(e) => setNewSourceUrl(e.target.value)} placeholder={tr('learning_url_ph', 'https://…')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /><p className="text-[10px] text-slate-500 mt-1">{trq('learning_add_url_prompt', { type: newSourceMode === 'youtube' ? tr('learning_add_youtube', 'YouTube') : tr('learning_add_website', 'Website') }, 'Tempel URL')}</p>{sourceErr && (<p className="text-[11px] text-rose-400 mt-1">{sourceErr}</p>)}</div>)}
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => { setShowNewSourceModal(false); setSourceErr(''); }} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl">Cancel</button>
              <button onClick={handleSaveSource} disabled={savingSource} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white rounded-xl">{savingSource ? tr('learning_fetching_source', 'Mengambil…') : newSourceMode === 'text' ? tr('save_source', 'Save Source') : tr('learning_fetch_save', 'Ambil & simpan')}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
