import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { t } from '../../i18n';
import { life } from '../../api/life';
import {
  Archive, ArchiveRestore, ChevronDown, ChevronRight, Copy, FolderPlus, FolderX,
  Pencil, Plus, Save, Search, Send, Sigma, Smile, Trash2, Type, X,
} from 'lucide-react';

const trv = (key: string, vars: Record<string, string | number>, fb: string) =>
  Object.entries(vars).reduce((acc, [k, v]) => acc.split(`{${k}}`).join(String(v)), t(key, fb));

// Set simbol standar untuk menu Σ (parity _insert_symbol — insertPlainText).
const SYMBOLS = [
  '∑', 'π', '√', '∞', '±', '×', '÷', '∫', '≠', '≤', '≥', '≈', '∂', '∆', '∇',
  'α', 'β', 'γ', 'δ', 'θ', 'λ', 'μ', 'σ', 'φ', 'ω', 'Ω', 'Ω',
  '²', '³', 'ⁿ', '₀', '₁', '₂', '₃', '½', '¼', '¾', '°', '€', '£', '¥', '©', '®', '™',
  '→', '←', '↔', '⇒', '✓', '✗', '★', '♥', '☀', '☂', '♫',
];
// Pilihan ikon folder (parity _IconSelectorDialog — grid klik-untuk-pilih).
const FOLDER_ICONS = ['📁', '📂', '📚', '📖', '📝', '🗂️', '💼', '🎓', '🔬', '💡', '🎯', '🧠', '⭐', '❤️', '🔥', '🌱'];
const ZOOM_LEVELS = [50, 75, 90, 100, 110, 125, 150, 200];
const FONT_SIZES = [10, 12, 14, 16, 18, 20, 24, 28, 32];
const DEFAULT_EMOJI = '📁';

type FolderNode = { id: string; name: string; icon: string; parentId: string | null; children: FolderNode[] };

interface NotesViewProps {}
export const NotesView: React.FC<NotesViewProps> = () => {
  const {
    notes, noteFolders, notebooks,
    addNote, updateNote, deleteNote, archiveNote, duplicateNoteItem, reorderNotes,
    addNoteFolder, deleteNoteFolder, updateNoteFolder, duplicateNoteFolder,
    addNotebookSource, lang, showToast,
  } = useGame();

  // ── Selection state (parity: current_folder_id; -1=Semua, 0=Tanpa Folder) ──
  const [currentFolderId, setCurrentFolderId] = useState<number>(-1);
  const [currentNoteId, setCurrentNoteId] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [showArchived, setShowArchived] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  // ── Editor state ──
  const [editTitle, setEditTitle] = useState('');
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [zoom, setZoom] = useState(100); // display-only (parity _on_zoom_changed)
  const [fontSize, setFontSize] = useState(16);
  const [fontColor, setFontColor] = useState('#e2e8f0');
  const contentRef = useRef<HTMLDivElement | null>(null);

  // ── Modals / dropdowns ──
  const [showSymbols, setShowSymbols] = useState(false);
  const [showLatexMenu, setShowLatexMenu] = useState(false);
  const [mathChunks, setMathChunks] = useState<{ raw: string; converted: string }[] | null>(null);
  const [iconPickerFor, setIconPickerFor] = useState<string | null>(null);
  const [renameFor, setRenameFor] = useState<{ id: string; name: string } | null>(null);
  const [fractionFor, setFractionFor] = useState<{ num: string; den: string } | null>(null);
  const [learnPicker, setLearnPicker] = useState(false);
  const [newFolderName, setNewFolderName] = useState<string | null>(null);

  // ── Folder tree data (parity _load_folder_tree + _populate_tree_items) ──
  const tree = useMemo(() => {
    const nodes = new Map<string, FolderNode>();
    for (const f of noteFolders) nodes.set(String(f.id), { id: String(f.id), name: f.name, icon: f.icon || DEFAULT_EMOJI, parentId: f.parentId ? String(f.parentId) : null, children: [] });
    const roots: FolderNode[] = [];
    for (const n of nodes.values()) {
      if (n.parentId && nodes.has(n.parentId)) nodes.get(n.parentId)!.children.push(n);
      else roots.push(n);
    }
    const sortRec = (list: FolderNode[]) => { list.sort((a, b) => a.name.localeCompare(b.name)); list.forEach((n) => sortRec(n.children)); };
    sortRec(roots);
    return roots;
  }, [noteFolders]);

  // Parity _get_all_subfolder_ids (rekursif).
  const subtreeIds = (rootId: string): string[] => {
    const out = [String(rootId)];
    const findNode = (list: FolderNode[]): FolderNode | undefined => {
      for (const n of list) {
        if (n.id === String(rootId)) return n;
        const d = findNode(n.children);
        if (d) return d;
      }
      return undefined;
    };
    const walk = (n: FolderNode) => { for (const c of n.children) { out.push(c.id); walk(c); } };
    const start = findNode(tree);
    if (start) walk(start);
    return out;
  };

  // Parity _load_notes: filter folder (rekursif subfolder) + search + archived.
  const visibleNotes = useMemo(() => {
    let list = notes.filter((n) => (showArchived ? true : !n.isArchived));
    const fid = currentFolderId;
    const s = searchText.trim().toLowerCase();
    if (s) {
      if (fid === -1) { /* semua catatan — tanpa filter folder */ }
      else if (fid === 0) list = list.filter((n) => !n.folderId);
      else list = list.filter((n) => n.folderId && new Set(subtreeIds(String(fid))).has(String(n.folderId)));
      list = list.filter((n) => (n.title || '').toLowerCase().includes(s) || (n.content || '').toLowerCase().includes(s));
    } else {
      if (fid === -1) { /* semua */ }
      else if (fid === 0) list = list.filter((n) => !n.folderId);
      else list = list.filter((n) => n.folderId && new Set(subtreeIds(String(fid))).has(String(n.folderId)));
    }
    return list;
  }, [notes, currentFolderId, searchText, showArchived, tree]);

  const activeNote = notes.find((n) => String(n.id) === String(currentNoteId)) || null;

  // Load title/content saat ganti note (parity _load_note).
  useEffect(() => {
    setDirty(false);
    if (!activeNote) { setEditTitle(''); if (contentRef.current) contentRef.current.innerHTML = ''; return; }
    setEditTitle(activeNote.title || '');
    if (contentRef.current) contentRef.current.innerHTML = activeNote.content || '';
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNoteId]);

  // Klik di luar → tutup dropdown simbol/latex.
  const closeDropdowns = () => { setShowSymbols(false); setShowLatexMenu(false); };

  // ── Operasi note (parity) ──
  const handleAddNote = () => {
    // Parity _add_note: folder mengikuti item tree terpilih; -1/0 → tanpa folder.
    const fid = currentFolderId > 0 ? String(currentFolderId) : null;
    addNote(t('notes_default_title', 'Catatan Baru'), '', fid);
  };

  const handleSave = async () => {
    if (!activeNote) return;
    setSaving(true);
    try {
      const html = contentRef.current?.innerHTML ?? '';
      updateNote(activeNote.id, (editTitle.trim() || 'Untitled'), html, activeNote.folderId ?? null);
      setDirty(false);
      showToast('success', t('berhasil_title', 'Berhasil'), t('notes_saved', 'Catatan disimpan!'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = () => {
    if (!activeNote) return;
    if (!window.confirm(t('notes_delete_confirm', 'Hapus catatan ini?'))) return;
    deleteNote(activeNote.id);
    setCurrentNoteId(null);
  };

  const handleArchiveToggle = () => {
    if (!activeNote) return;
    archiveNote(activeNote.id, !activeNote.isArchived);
  };

  const handleDuplicateNote = () => {
    if (!activeNote) return;
    duplicateNoteItem(activeNote.id);
  };

  // ── Folder ops (parity menu konteks tree) ──
  const handleAddFolder = () => { setNewFolderName(''); };
  const confirmDeleteFolder = (f: FolderNode) => {
    if (!window.confirm(t('notes_folder_delete_confirm', 'Hapus folder beserta isinya?'))) return;
    deleteNoteFolder(f.id);
    if (String(currentFolderId) === f.id) setCurrentFolderId(-1);
  };

  // ── Editor formatting (parity format toolbar) ──
  const exec = (cmd: string, value?: string) => {
    contentRef.current?.focus();
    try { document.execCommand(cmd, false, value); } catch { /* browser lama */ }
    setDirty(true);
  };
  const insertHtmlAtCaret = (html: string) => {
    contentRef.current?.focus();
    try {
      if (!document.execCommand('insertHTML', false, html)) insertTextFallback(html);
    } catch { insertTextFallback(html); }
    setDirty(true);
  };
  const insertTextFallback = (text: string) => { document.execCommand('insertText', false, text); setDirty(true); };

  const selectionText = () => window.getSelection()?.toString() || '';
  const editorPlainText = () => contentRef.current?.innerText ?? '';
  const setEditorHtml = (html: string) => { if (contentRef.current) { contentRef.current.innerHTML = html; setDirty(true); } };

  // LaTeX via server (mathtools) — parity _latex_*.
  const latexConvertSelection = async () => {
    const sel = selectionText();
    if (!sel.trim()) { showToast('info', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_none', 'Tidak ada rumus LaTeX.')); return; }
    const r = await life.previewMath(sel).catch(() => null);
    const conv = r?.result?.preview;
    if (!conv) { showToast('info', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_none', 'Tidak ada rumus LaTeX.')); return; }
    insertTextFallback(conv);
    showToast('success', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_converted', 'Dikonversi ke unicode!'));
  };
  const latexConvertAll = async () => {
    const full = editorPlainText();
    if (!full.trim()) { showToast('info', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_none', 'Tidak ada rumus LaTeX.')); return; }
    const r = await life.previewMath(full).catch(() => null);
    const conv = r?.result?.preview;
    if (!conv) return;
    // Convert-all mengganti seluruh plain text (parity setPlainText).
    setEditorHtml(conv.replace(/</g, '&lt;').replace(/\n/g, '<br>'));
    showToast('success', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_converted', 'Dikonversi ke unicode!'));
  };
  const latexPreview = async () => {
    const full = editorPlainText();
    const r = await life.mathChunks(full).catch(() => null);
    const chunks = r?.result?.chunks;
    if (!Array.isArray(chunks) || !chunks.length) {
      showToast('info', t('notes_math_preview_title', 'Pratinjau Matematika'), t('notes_math_none', 'Tidak ada rumus LaTeX.'));
      return;
    }
    setMathChunks(chunks);
  };
  const insertFraction = () => {
    const sel = selectionText();
    if (sel.trim()) {
      // parity: seleksi jadi pembilang, penyebut 'b'.
      insertHtmlAtCaret(`<span style="font-size:${fontSize}px;color:${fontColor};"><sup>${sel.trim()}</sup>/<sub>b</sub></span> `);
      return;
    }
    setFractionFor({ num: '', den: '' });
  };

  // ── Send to learning (parity _send_to_learning) ──
  const handleSendToLearning = (notebookId: string) => {
    if (!activeNote) { showToast('damage', t('msg_error', 'Error'), t('notes_to_learning_no_note', 'Pilih catatan dulu.')); return; }
    const title = editTitle || activeNote.title || 'Note';
    const text = editorPlainText().trim();
    addNotebookSource(notebookId, title, text, 'text');
    setLearnPicker(false);
    showToast('success', t('berhasil_title', 'Berhasil'), t('notes_to_learning_done', 'Dikirim ke Learning!'));
  };

  // ── Reorder (drag sederhana via tombol ↑↓ dalam folder yang sama) ──
  const moveNoteInList = (id: string, dir: -1 | 1) => {
    if (searchText.trim() || currentFolderId <= 0) return; // reorder hanya di folder konkret tanpa search (parity constraint tampilan)
    const list = visibleNotes.map((n) => String(n.id));
    const i = list.indexOf(String(id));
    const j = i + dir;
    if (i < 0 || j < 0 || j >= list.length) return;
    const next = [...list]; [next[i], next[j]] = [next[j], next[i]];
    reorderNotes(next);
  };

  // ── Render folder tree recursive ──
  const renderFolder = (node: FolderNode, depth: number) => {
    const isOpen = expanded[node.id] !== false;
    const selected = String(currentFolderId) === node.id;
    const hasKids = node.children.length > 0;
    return (
      <div key={node.id}>
        <div
          className={`group flex items-center gap-1 py-1.5 pr-1 rounded-lg cursor-pointer text-xs ${selected ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-500/40' : 'text-slate-300 hover:bg-slate-800/70 border border-transparent'}`}
          style={{ paddingLeft: `${6 + depth * 14}px` }}
          onClick={() => { setCurrentFolderId(parseInt(node.id) || -1); setCurrentNoteId(null); }}
        >
          <button
            className="w-4 shrink-0 text-slate-500 hover:text-slate-200"
            onClick={(e) => { e.stopPropagation(); setExpanded((x) => ({ ...x, [node.id]: !isOpen })); }}
            tabIndex={-1}
          >
            {hasKids ? (isOpen ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />) : ' '}
          </button>
          <span className="shrink-0">{node.icon}</span>
          <span className="truncate flex-1 font-semibold">{node.name}</span>
          {/* Aksi konteks folder (parity menu) */}
          <div className="hidden group-hover:flex items-center gap-0.5 shrink-0" onClick={(e) => e.stopPropagation()}>
            <button title={t('notes_add_subfolder', 'Tambah subfolder')} onClick={() => setNewFolderName(node.id)} className="p-1 text-slate-500 hover:text-cyan-300"><FolderPlus className="w-3 h-3" /></button>
            <button title={t('notes_edit_folder', 'Ubah nama folder')} onClick={() => setRenameFor({ id: node.id, name: node.name })} className="p-1 text-slate-500 hover:text-cyan-300"><Pencil className="w-3 h-3" /></button>
            <button title={t('notes_edit_icon', 'Ubah ikon')} onClick={() => setIconPickerFor(node.id)} className="p-1 text-slate-500 hover:text-cyan-300"><Smile className="w-3 h-3" /></button>
            <button title={t('notes_duplicate_folder', 'Duplikat folder')} onClick={() => duplicateNoteFolder(node.id)} className="p-1 text-slate-500 hover:text-cyan-300"><Copy className="w-3 h-3" /></button>
            <button title={t('notes_delete', 'Hapus')} onClick={() => confirmDeleteFolder(node)} className="p-1 text-slate-500 hover:text-rose-400"><Trash2 className="w-3 h-3" /></button>
          </div>
        </div>
        {isOpen && node.children.map((c) => renderFolder(c, depth + 1))}
      </div>
    );
  };

  const folderChildCount = (folderId: string | null): number => {
    let count = notes.filter((n) => String(n.folderId) === String(folderId)).length;
    for (const f of noteFolders.filter((x) => String(x.parentId) === String(folderId))) count += folderChildCount(String(f.id));
    return count;
  };

  return (
    <div className="space-y-5" onClick={closeDropdowns}>
      {/* ── Header (parity _page_header + actions) ── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h2 className="text-2xl font-black text-slate-100">{t('notes_title', '📝 Catatan')}</h2>
          <p className="text-xs text-slate-400 mt-1">{t('nav_notes', 'Notes')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleArchiveToggle}
            disabled={!activeNote}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200 disabled:opacity-40"
          >
            <Archive className="w-3.5 h-3.5" />
            {activeNote?.isArchived ? t('notes_unarchive', 'Kembalikan') : t('notes_archive', 'Arsipkan')}
          </button>
          <button
            onClick={() => setShowArchived((s) => !s)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold border ${showArchived ? 'bg-cyan-950/60 border-cyan-500/50 text-cyan-300' : 'bg-slate-800 border-slate-700 text-slate-200 hover:bg-slate-700'}`}
          >
            <ArchiveRestore className="w-3.5 h-3.5" />
            {showArchived ? t('notes_hide_archived', 'Sembunyikan arsip') : t('notes_show_archived', 'Tampilkan Arsip')}
          </button>
        </div>
      </div>

      {/* ── Search (parity search bar textChanged) ── */}
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder={t('notes_search_placeholder', 'Cari catatan...')}
          className="w-full bg-slate-900/80 border border-slate-800 rounded-2xl pl-10 pr-4 py-2.5 text-sm text-slate-100 focus:outline-none focus:border-cyan-500"
        />
      </div>

      {/* ── Toolbar (parity buttons row) ── */}
      <div className="flex items-center gap-2 flex-wrap">
        <button onClick={handleAddFolder} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200">
          <FolderPlus className="w-3.5 h-3.5" /> {t('notes_add_folder', '+ Folder')}
        </button>
        <button onClick={handleAddNote} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-black">
          <Plus className="w-3.5 h-3.5" /> {t('notes_add_note', '+ Catatan')}
        </button>
        <button
          onClick={handleDuplicateNote} disabled={!activeNote} title={t('notes_duplicate_tooltip', 'Duplikat catatan aktif')}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200 disabled:opacity-40">
          <Copy className="w-3.5 h-3.5" /> {t('notes_duplicate_btn', 'Duplikat')}
        </button>
        <button
          onClick={() => (activeNote ? setLearnPicker(true) : showToast('damage', t('msg_error', 'Error'), t('notes_to_learning_no_note', 'Pilih catatan dulu.')))}
          title={t('notes_to_learning_title', 'Kirim ke Learning sebagai source')}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200">
          <Send className="w-3.5 h-3.5" /> {t('notes_to_learning', '→ Learning')}
        </button>
        <button onClick={handleDelete} disabled={!activeNote} className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-rose-600/90 hover:bg-rose-500 text-xs font-bold text-white disabled:opacity-40">
          <Trash2 className="w-3.5 h-3.5" /> {t('notes_delete', 'Hapus')}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* ── LEFT: folder tree + notes list (parity splitter left) ── */}
        <div className="lg:col-span-4 xl:col-span-3 space-y-3">
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-3">
            <div className="flex items-center justify-between mb-1.5 px-1">
              <span className="text-[11px] font-bold text-slate-400">{t('notes_folder_label', 'Folder')}</span>
              <div className="flex gap-1">
                <button onClick={() => setExpanded(Object.fromEntries(tree.map((n) => [n.id, true])))} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-slate-200">{t('expand_all', 'Expand')}</button>
                <button onClick={() => setExpanded({})} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 hover:text-slate-200">{t('collapse_all', 'Collapse')}</button>
              </div>
            </div>
            <div className="max-h-56 overflow-y-auto pr-1">
              {/* "Semua Catatan" (-1) & "Tanpa Folder" (0) parity item khusus */}
              <button
                onClick={() => { setCurrentFolderId(-1); setCurrentNoteId(null); }}
                className={`w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-semibold ${currentFolderId === -1 ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-500/40' : 'text-slate-300 hover:bg-slate-800/70 border border-transparent'}`}>
                📋 <span className="truncate">{t('notes_all', 'Semua Catatan')}</span>
                <span className="ml-auto text-[10px] text-slate-500">{notes.filter((n) => showArchived || !n.isArchived).length}</span>
              </button>
              <button
                onClick={() => { setCurrentFolderId(0); setCurrentNoteId(null); }}
                className={`w-full flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs font-semibold ${currentFolderId === 0 ? 'bg-cyan-950/60 text-cyan-300 border border-cyan-500/40' : 'text-slate-300 hover:bg-slate-800/70 border border-transparent'}`}>
                📄 <span className="truncate">{t('notes_no_folder', 'Tanpa Folder')}</span>
                <span className="ml-auto text-[10px] text-slate-500">{notes.filter((n) => !n.folderId && (showArchived || !n.isArchived)).length}</span>
              </button>
              {tree.map((n) => renderFolder(n, 0))}
            </div>
          </div>

          {/* Notes list (parity notes_list) */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-2 space-y-1.5 max-h-[430px] overflow-y-auto">
            {visibleNotes.length === 0 && (
              <p className="text-[11px] text-slate-500 text-center py-6">{t('notes_empty', 'Tidak ada catatan.')}</p>
            )}
            {visibleNotes.map((n, idx) => (
              <div
                key={n.id}
                onClick={() => setCurrentNoteId(String(n.id))}
                className={`group p-2.5 rounded-xl border cursor-pointer transition-all ${String(currentNoteId) === String(n.id) ? 'bg-cyan-950/50 border-cyan-500/40' : 'bg-slate-950/50 border-slate-800/80 hover:border-slate-700'}`}
              >
                <div className="flex items-center gap-1.5">
                  <span className={`font-bold text-xs truncate flex-1 ${String(currentNoteId) === String(n.id) ? 'text-cyan-300' : 'text-slate-200'}`}>
                    {n.title || 'Untitled'}
                  </span>
                  {n.isArchived && <Archive className="w-3 h-3 text-slate-500 shrink-0" />}
                  {/* Reorder via ↑↓ (drag-drop browser→ tombol parity konversi) */}
                  {currentFolderId > 0 && !searchText.trim() && (
                    <span className="hidden group-hover:inline-flex gap-0.5" onClick={(e) => e.stopPropagation()}>
                      <button disabled={idx === 0} onClick={() => moveNoteInList(String(n.id), -1)} className="text-[10px] px-1 text-slate-500 hover:text-cyan-300 disabled:opacity-30">↑</button>
                      <button disabled={idx === visibleNotes.length - 1} onClick={() => moveNoteInList(String(n.id), 1)} className="text-[10px] px-1 text-slate-500 hover:text-cyan-300 disabled:opacity-30">↓</button>
                    </span>
                  )}
                </div>
                <p className="text-[10px] text-slate-500 truncate mt-0.5">
                  {(n.content || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 60)}
                </p>
                <p className="text-[9px] text-slate-600 mt-0.5">{(n.updatedAt || '').replace('T', ' ').slice(0, 16)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── RIGHT: editor (parity notes editor pane) ── */}
        <div className="lg:col-span-8 xl:col-span-9">
          {!activeNote ? (
            <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-14 text-center text-slate-500">
              <p className="text-base font-semibold">{t('notes_select_hint', 'Pilih atau buat catatan untuk mulai menulis.')}</p>
            </div>
          ) : (
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-4 space-y-3" onClick={(e) => e.stopPropagation()}>
              {/* Format toolbar */}
              <div className="flex items-center gap-1.5 flex-wrap border-b border-slate-800 pb-2.5">
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => exec('bold')} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-sm font-black text-slate-200 hover:bg-slate-700" title="Bold">B</button>
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => exec('italic')} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-sm italic text-slate-200 hover:bg-slate-700" title="Italic">I</button>
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => exec('underline')} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-sm underline text-slate-200 hover:bg-slate-700" title="Underline">U</button>
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => exec('strikeThrough')} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-sm line-through text-slate-200 hover:bg-slate-700" title="Strike">S</button>
                <select
                  value={fontSize}
                  onChange={(e) => { const v = Number(e.target.value); setFontSize(v); exec('fontSize', String(Math.min(7, Math.max(1, Math.round(v / 4) + 1)))); }}
                  className="bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 px-1.5 py-1.5"
                  title={t('learning_font_size', 'Ukuran Font')}
                >
                  {FONT_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
                <label className="flex items-center gap-1 px-1.5 py-1 rounded-lg bg-slate-800 text-xs text-slate-300 cursor-pointer" title={t('notes_color', 'Warna teks')}>
                  <Type className="w-3.5 h-3.5" />
                  <input type="color" value={fontColor} onChange={(e) => { setFontColor(e.target.value); exec('foreColor', e.target.value); }} className="w-5 h-5 bg-transparent border-0 cursor-pointer" />
                </label>
                <label className="flex items-center px-1.5 py-1 rounded-lg bg-slate-800 text-xs text-slate-300 cursor-pointer" title={t('notes_highlight', 'Highlight')}>
                  🖍
                  <input type="color" defaultValue="#facc15" onChange={(e) => exec('hiliteColor', e.target.value)} className="w-5 h-5 bg-transparent border-0 cursor-pointer" />
                </label>
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => {
                  const sel = selectionText();
                  if (sel) insertHtmlAtCaret(`<sup>${sel}</sup>`); else insertTextFallback('x²');
                }} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-200 hover:bg-slate-700" title="Superscript">x²</button>
                <button onMouseDown={(e) => e.preventDefault()} onClick={() => {
                  const sel = selectionText();
                  if (sel) insertHtmlAtCaret(`<sub>${sel}</sub>`); else insertTextFallback('x₁');
                }} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-200 hover:bg-slate-700" title="Subscript">x₁</button>
                <button onMouseDown={(e) => e.preventDefault()} onClick={insertFraction} className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-xs text-slate-200 hover:bg-slate-700" title={t('notes_fraction', 'Pecahan')}>⅟</button>

                {/* Menu simbol Σ */}
                <div className="relative" onClick={(e) => e.stopPropagation()}>
                  <button onMouseDown={(e) => e.preventDefault()} onClick={() => { setShowSymbols((s) => !s); setShowLatexMenu(false); }}
                    className="px-2.5 py-1.5 rounded-lg bg-slate-800 text-sm text-slate-200 hover:bg-slate-700" title={t('notes_symbols', 'Simbol')}>Σ</button>
                  {showSymbols && (
                    <div className="absolute top-full mt-1 left-0 z-30 w-64 bg-slate-900 border border-slate-700 rounded-xl p-2 shadow-2xl grid grid-cols-6 gap-1">
                      {SYMBOLS.map((s, i) => (
                        <button key={`${s}_${i}`} onMouseDown={(e) => e.preventDefault()} onClick={() => { insertTextFallback(s); setShowSymbols(false); }}
                          className="text-base py-1 rounded-lg hover:bg-slate-700 text-slate-200">{s}</button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Menu ∑ LaTeX (parity _latex_menu) */}
                <div className="relative" onClick={(e) => e.stopPropagation()}>
                  <button onMouseDown={(e) => e.preventDefault()} onClick={() => { setShowLatexMenu((s) => !s); setShowSymbols(false); }}
                    className="px-2.5 py-1.5 rounded-lg bg-indigo-900/60 border border-indigo-500/40 text-sm text-indigo-200 hover:bg-indigo-800/60" title="LaTeX">∑</button>
                  {showLatexMenu && (
                    <div className="absolute top-full mt-1 left-0 z-30 w-56 bg-slate-900 border border-slate-700 rounded-xl p-1 shadow-2xl text-xs">
                      <button onClick={() => { latexConvertSelection(); setShowLatexMenu(false); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-200">{t('notes_math_convert_sel', 'Konversi seleksi LaTeX → Unicode')}</button>
                      <button onClick={() => { latexConvertAll(); setShowLatexMenu(false); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-200">{t('notes_math_convert_all', 'Konversi semua LaTeX → Unicode')}</button>
                      <div className="border-t border-slate-800 my-1" />
                      <button onClick={() => { latexPreview(); setShowLatexMenu(false); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-800 text-slate-200">{t('notes_math_preview', 'Pratinjau LaTeX')}</button>
                    </div>
                  )}
                </div>

                {/* Zoom (display-only, parity zoom slider) */}
                <div className="ml-auto flex items-center gap-1.5">
                  <span className="text-[10px] text-slate-500">{zoom}%</span>
                  <input
                    type="range" min={50} max={200} step={10} value={zoom}
                    onChange={(e) => setZoom(Number(e.target.value))}
                    className="w-24 accent-cyan-500"
                  />
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-black disabled:opacity-50"
                  >
                    <Save className="w-3.5 h-3.5" /> {t('notes_save', 'Simpan')}{dirty ? '*' : ''}
                  </button>
                </div>
              </div>

              {/* Title (parity title_edit) */}
              <input
                value={editTitle}
                onChange={(e) => { setEditTitle(e.target.value); setDirty(true); }}
                placeholder={t('notes_title_label', 'Judul')}
                className="w-full bg-transparent text-lg font-black text-slate-100 focus:outline-none border-b border-slate-800 pb-2"
              />

              {/* Content (parity content_edit rich text + zoom CSS) */}
              <div
                ref={contentRef}
                contentEditable
                suppressContentEditableWarning
                onInput={() => setDirty(true)}
                className="min-h-[340px] max-h-[60vh] overflow-y-auto bg-slate-950/60 border border-slate-800 rounded-xl p-4 text-slate-100 focus:outline-none focus:border-cyan-500"
                style={{ fontSize: `${(fontSize * zoom) / 100}px`, zoom: zoom / 100 }}
              />
              <p className="text-[10px] text-slate-600">
                {activeNote.updatedAt ? `${t('notes_updated', 'Diubah')}: ${String(activeNote.updatedAt).replace('T', ' ').slice(0, 16)}` : ''}
                {dirty ? ` · ${t('notes_unsaved', 'Belum disimpan')}` : ''}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* ── Modal: pratinjau chunk LaTeX (parity MathPreviewDialog) ── */}
      {mathChunks && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setMathChunks(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-bold text-lg text-slate-100 mb-3">{t('notes_math_preview_title', 'Pratinjau Matematika')}</h3>
            <div className="overflow-y-auto space-y-2 flex-1 pr-1">
              {mathChunks.map((c, i) => (
                <div key={i} className="bg-slate-950/60 border border-slate-800 rounded-xl p-3">
                  <p className="text-[10px] text-slate-500 font-mono break-all">{c.raw}</p>
                  <p className="text-base text-cyan-300 font-semibold mt-1">{c.converted}</p>
                </div>
              ))}
            </div>
            <button onClick={() => setMathChunks(null)} className="mt-4 w-full py-2.5 rounded-xl bg-cyan-600 text-white font-bold text-sm">{t('btn_close', 'Tutup')}</button>
          </div>
        </div>
      )}

      {/* ── Modal: ikon folder (parity IconSelectorDialog) ── */}
      {iconPickerFor && (
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4" onClick={() => setIconPickerFor(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-xs w-full" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200 mb-3">{t('notes_select_icon', 'Klik icon yang diinginkan:')}</p>
            <div className="grid grid-cols-4 gap-2">
              {FOLDER_ICONS.map((ic) => (
                <button key={ic} onClick={() => { updateNoteFolder(iconPickerFor, { icon: ic }); setIconPickerFor(null); }}
                  className="text-2xl p-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500">{ic}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: rename folder (parity _edit_folder_name) ── */}
      {renameFor && (
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4" onClick={() => setRenameFor(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-sm w-full space-y-3" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200">{t('notes_edit_folder', 'Ubah nama folder')}</p>
            <input autoFocus defaultValue={renameFor.name}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const v = (e.target as HTMLInputElement).value.trim();
                  if (v) updateNoteFolder(renameFor.id, { name: v });
                  setRenameFor(null);
                } else if (e.key === 'Escape') setRenameFor(null);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100" />
          </div>
        </div>
      )}

      {/* ── Modal: pecahan (parity _insert_fraction dialog) ── */}
      {fractionFor && (
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4" onClick={() => setFractionFor(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-xs w-full space-y-3" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200">{t('notes_fraction_title', 'Sisipkan Pecahan')}</p>
            <input autoFocus placeholder={t('notes_numerator', 'Pembilang')} value={fractionFor.num}
              onChange={(e) => setFractionFor({ ...fractionFor, num: e.target.value })}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100" />
            <input placeholder={t('notes_denominator', 'Penyebut')} value={fractionFor.den}
              onChange={(e) => setFractionFor({ ...fractionFor, den: e.target.value })}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setFractionFor(null)} className="px-4 py-2 text-sm text-slate-400">{t('msg_cancel', 'Batal')}</button>
              <button
                onClick={() => {
                  if (!fractionFor.num.trim() || !fractionFor.den.trim()) return;
                  insertHtmlAtCaret(`<span style="font-size:${fontSize}px;color:${fontColor};"><sup>${fractionFor.num.trim()}</sup>/<sub>${fractionFor.den.trim()}</sub></span> `);
                  setFractionFor(null);
                }}
                className="px-4 py-2 rounded-xl bg-cyan-600 text-white text-sm font-bold"
              >
                {t('msg_ok', 'OK')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: kirim ke Learning (parity dialog pilih notebook) ── */}
      {learnPicker && (
        <div className="fixed inset-0 bg-slate-950/80 z-50 flex items-center justify-center p-4" onClick={() => setLearnPicker(false)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-sm w-full space-y-3" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200 flex items-center justify-between">
              {t('notes_to_learning_title', 'Kirim ke Learning sebagai source')}
              <button onClick={() => setLearnPicker(false)} className="text-slate-500 hover:text-slate-300"><X className="w-4 h-4" /></button>
            </p>
            <div className="space-y-1.5 max-h-64 overflow-y-auto">
              {notebooks.map((nb) => (
                <button key={nb.id} onClick={() => handleSendToLearning(nb.id)}
                  className="w-full text-left px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 hover:border-violet-500 text-sm text-slate-200">
                  {nb.icon || '📚'} {nb.title}
                </button>
              ))}
              {notebooks.length === 0 && <p className="text-xs text-slate-500">{t('learning_no_notebook', 'Buat notebook dulu!')}</p>}
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: new folder/subfolder (parity QInputDialog) ── */}
      {newFolderName !== null && (
        <div className="fixed inset-0 bg-slate-950/80 z-[55] flex items-center justify-center p-4" onClick={() => setNewFolderName(null)}>
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 max-w-sm w-full space-y-3" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200">
              {newFolderName === '' ? t('notes_folder_name', 'Nama folder') : t('notes_subfolder_title', 'Subfolder baru')}
            </p>
            <input
              autoFocus
              placeholder={newFolderName === '' ? t('notes_folder_name_ph', 'Nama folder baru') : t('notes_subfolder_name', 'Nama subfolder')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const v = (e.target as HTMLInputElement).value.trim();
                  if (v) addNoteFolder(v, DEFAULT_EMOJI, newFolderName === '' ? null : String(newFolderName));
                  setNewFolderName(null);
                } else if (e.key === 'Escape') setNewFolderName(null);
              }}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100"
            />
          </div>
        </div>
      )}
    </div>
  );
};
