import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { FileText, Plus, Trash2, Edit3, Folder, FolderPlus, Pin, Calculator, Sparkles, BookOpen } from 'lucide-react';
import Markdown from 'react-markdown';

export const NotesView: React.FC = () => {
  const { notes, addNote, updateNote, deleteNote, archiveNote, duplicateNoteItem, noteFolders, addNoteFolder, deleteNoteFolder, lang, notebooks, addNotebookSource, addNotebook } = useGame();
  const [noteSearch, setNoteSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);

  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);
  const [activeNoteId, setActiveNoteId] = useState<string | null>(notes[0]?.id || null);

  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');

  const [isNewFolderModalOpen, setIsNewFolderModalOpen] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  const [newFolderIcon, setNewFolderIcon] = useState('📁');

  // Math Tools calculation helper
  const [mathInput, setMathInput] = useState('');
  const [mathResult, setMathResult] = useState<string | null>(null);
  const [zoom, setZoom] = useState(100);

  const wrapSel = (before: string, after: string) => {
    setEditContent((c) => `${before}${c}${after}`);
    setIsEditing(true);
  };

  const activeNote = notes.find((n) => n.id === activeNoteId);

  const handleSelectNote = (id: string) => {
    setActiveNoteId(id);
    const n = notes.find((item) => item.id === id);
    if (n) {
      setEditTitle(n.title);
      setEditContent(n.content);
      setIsEditing(false);
    }
  };

  const handleCreateNewNote = () => {
    const newTitle = lang === 'id' ? 'Catatan Baru' : 'Untitled Note';
    const newContent = lang === 'id' ? 'Tulis catatan, ide, atau rumus matematika di sini...' : 'Write your notes or formulas here...';
    addNote(newTitle, newContent, selectedFolderId);
  };

  const handleSaveNote = () => {
    if (!activeNoteId) return;
    updateNote(activeNoteId, editTitle, editContent, activeNote?.folderId);
    setIsEditing(false);
  };

  const handleCreateFolder = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;
    addNoteFolder(newFolderName, newFolderIcon);
    setIsNewFolderModalOpen(false);
    setNewFolderName('');
  };

  const handleEvaluateMath = () => {
    try {
      const sanitized = mathInput.replace(/[^0-9+\-*/().%^]/g, '');
      const res = Function(`'use strict'; return (${sanitized})`)();
      setMathResult(String(res));
    } catch {
      setMathResult('Error');
    }
  };

  const handlePreviewLatex = () => {
    const src = (isEditing ? editContent : activeNote?.content) || mathInput || '';
    if (!src.trim()) {
      setMathResult(lang === 'id' ? 'Tidak ada rumus' : 'Nothing to preview');
      return;
    }
    life
      .previewMath(src)
      .then((res) => {
        const preview = res?.preview || res?.result?.preview;
        setMathResult(preview != null ? String(preview) : (lang === 'id' ? 'Pratinjau kosong' : 'Empty preview'));
      })
      .catch((e) => setMathResult(String(e?.message || e)));
  };

  const filteredNotes = notes.filter((n) => {
    if (!showArchived && n.isArchived) return false;
    if (selectedFolderId !== null && n.folderId !== selectedFolderId) return false;
    if (noteSearch && !(`${n.title} ${n.content}`.toLowerCase().includes(noteSearch.toLowerCase()))) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-6 h-6 text-cyan-400" />
            <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Catatan & Alat Matematika' : 'Notes & Math Tools'}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Tulis strategi petualangan, catatan harian, struktur folder, atau hitung rumus matematika dengan cepat.'
              : 'Record strategy journals, habit learnings, nested folders, and evaluate quick math expressions.'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsNewFolderModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs border border-slate-700 transition-colors"
          >
            <FolderPlus className="w-4 h-4 text-amber-400" />
            <span>{lang === 'id' ? 'Folder Baru' : 'New Folder'}</span>
          </button>
          <button
            onClick={handleCreateNewNote}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs shadow-lg shadow-cyan-500/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>{lang === 'id' ? 'Catatan Baru' : 'New Note'}</span>
          </button>
        </div>
      </div>

      {/* Main Split Layout: Left Explorer & Right Editor */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Left Column: Folders and Note List */}
        <div className="space-y-4">
          {/* Folders Bar */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <button
              onClick={() => setSelectedFolderId(null)}
              className={`px-3 py-1.5 rounded-xl font-semibold shrink-0 transition-colors ${
                selectedFolderId === null
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200'
              }`}
            >
              {lang === 'id' ? 'Semua' : 'All'}
            </button>
            {noteFolders.map((f) => (
              <div key={f.id} className="relative group shrink-0">
                <button
                  onClick={() => setSelectedFolderId(f.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl font-semibold transition-colors ${
                    selectedFolderId === f.id
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{f.icon}</span>
                  <span>{f.name}</span>
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteNoteFolder(f.id);
                    if (selectedFolderId === f.id) setSelectedFolderId(null);
                  }}
                  className="absolute -top-1 -right-1 hidden group-hover:flex p-0.5 rounded bg-rose-500/80 text-white"
                  title="Delete folder"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <input
              value={noteSearch}
              onChange={(e) => setNoteSearch(e.target.value)}
              placeholder={lang === 'id' ? 'Cari catatan...' : 'Search notes...'}
              className="flex-1 px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100"
            />
            <button
              type="button"
              onClick={() => setShowArchived((v) => !v)}
              className="px-2 py-1 rounded-lg bg-slate-800 text-[10px] text-slate-300"
            >
              {showArchived ? (lang === 'id' ? 'Sembunyikan arsip' : 'Hide archive') : (lang === 'id' ? 'Arsip' : 'Archive')}
            </button>
          </div>

          {/* Notes List */}
          <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
            {filteredNotes.map((note) => {
              const isActive = activeNoteId === note.id;

              return (
                <div
                  key={note.id}
                  onClick={() => handleSelectNote(note.id)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all ${
                    isActive
                      ? 'bg-cyan-950/25 border-cyan-500/50 shadow-md'
                      : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <h4 className={`font-bold text-xs truncate ${isActive ? 'text-cyan-300' : 'text-slate-200'}`}>
                      {note.title || 'Untitled Note'}
                    </h4>
                    {note.isPinned && <Pin className="w-3.5 h-3.5 text-amber-400 shrink-0 fill-amber-400" />}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {note.content}
                  </p>
                  <div className="text-[10px] text-slate-400 mt-2">
                    {new Date(note.updatedAt).toLocaleDateString()}
                  </div>
                </div>
              );
            })}

            {filteredNotes.length === 0 && (
              <div className="text-center py-8 text-xs text-slate-400 bg-slate-900/40 rounded-xl border border-slate-800/80">
                {lang === 'id' ? 'Tidak ada catatan di folder ini.' : 'No notes in this folder.'}
              </div>
            )}
          </div>

          {/* Quick Math Tool Box */}
          <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-300">
              <Calculator className="w-4 h-4 text-cyan-400" />
              <span>{lang === 'id' ? 'Kalkulator Cepat (MathTools)' : 'Quick Math Evaluator'}</span>
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                value={mathInput}
                onChange={(e) => setMathInput(e.target.value)}
                placeholder="e.g. (150 * 4) / 2"
                className="flex-1 px-2.5 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-100 focus:outline-none focus:border-cyan-500"
              />
              <button
                onClick={handleEvaluateMath}
                className="px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs"
              >
                =
              </button>
            </div>

            <button
              type="button"
              onClick={handlePreviewLatex}
              className="w-full px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 font-bold text-xs"
            >
              {lang === 'id' ? 'Pratinjau LaTeX catatan' : 'Preview note LaTeX'}
            </button>
            {mathResult !== null && (
              <div className="p-2 rounded-lg bg-slate-800 text-xs flex items-center justify-between">
                <span className="text-slate-400">Result:</span>
                <span className="font-mono font-bold text-cyan-300 text-sm">{mathResult}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Note Editor / Markdown Preview */}
        <div className="md:col-span-2 rounded-2xl bg-slate-900 border border-slate-800 p-5 flex flex-col justify-between min-h-[500px]">
          {activeNote ? (
            <div className="space-y-4 flex-1 flex flex-col">
              {/* Note Header & Action buttons */}
              <div className="flex items-center justify-between gap-3 pb-3 border-b border-slate-800">
                {isEditing ? (
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="flex-1 px-3 py-1.5 rounded-xl bg-slate-800 border border-slate-700 text-base font-bold text-slate-100 focus:outline-none focus:border-cyan-500"
                  />
                ) : (
                  <h3 className="text-lg font-black text-slate-100 truncate">{activeNote.title}</h3>
                )}

                <div className="flex items-center gap-2 shrink-0">
                  {isEditing ? (
                    <button
                      onClick={handleSaveNote}
                      className="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs"
                    >
                      {lang === 'id' ? 'Simpan' : 'Save'}
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setEditTitle(activeNote.title);
                        setEditContent(activeNote.content);
                        setIsEditing(true);
                      }}
                      className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs flex items-center gap-1"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      <span>{lang === 'id' ? 'Edit' : 'Edit'}</span>
                    </button>
                  )}

                  <button
                    type="button"
                    onClick={() => duplicateNoteItem(activeNote.id)}
                    className="px-2 py-1.5 rounded-xl bg-slate-800 text-[10px] font-bold text-slate-300"
                  >
                    {lang === 'id' ? 'Duplikat' : 'Duplicate'}
                  </button>
                  <button
                    type="button"
                    onClick={() => archiveNote(activeNote.id, !activeNote.isArchived)}
                    className="px-2 py-1.5 rounded-xl bg-slate-800 text-[10px] font-bold text-slate-300"
                  >
                    {activeNote.isArchived ? (lang === 'id' ? 'Buka arsip' : 'Unarchive') : (lang === 'id' ? 'Arsip' : 'Archive')}
                  </button>
                  <button
                    onClick={() => deleteNote(activeNote.id)}
                    className="p-2 rounded-xl text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
                    title="Delete Note"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {isEditing && (
                <div className="flex flex-wrap gap-1 text-[10px]">
                  <button type="button" className="px-2 py-1 rounded bg-slate-800" onClick={() => wrapSel('**', '**')}>B</button>
                  <button type="button" className="px-2 py-1 rounded bg-slate-800 italic" onClick={() => wrapSel('*', '*')}>I</button>
                  <button type="button" className="px-2 py-1 rounded bg-slate-800" onClick={() => wrapSel('`', '`')}>code</button>
                  <button type="button" className="px-2 py-1 rounded bg-slate-800" onClick={() => wrapSel('$$\n', '\n$$')}>LaTeX</button>
                  <button type="button" className="px-2 py-1 rounded bg-slate-800" onClick={() => setZoom((z) => Math.min(160, z + 10))}>A+</button>
                  <button type="button" className="px-2 py-1 rounded bg-slate-800" onClick={() => setZoom((z) => Math.max(80, z - 10))}>A-</button>
                  <button
                    type="button"
                    className="px-2 py-1 rounded bg-violet-700 text-white"
                    onClick={() => {
                      if (!activeNote) return;
                      const nb = notebooks[0];
                      if (nb) addNotebookSource(nb.id, activeNote.title, activeNote.content, 'text');
                      else addNotebook(activeNote.title, activeNote.content.slice(0, 80), '📝');
                    }}
                  >
                    {lang === 'id' ? 'Kirim ke Learning' : 'Send to Learning'}
                  </button>
                </div>
              )}
              {/* Editor / Markdown Body */}
              {isEditing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  placeholder="Write Markdown formatted notes here..."
                  style={{ fontSize: `${zoom}%` }}
                  className="flex-1 w-full p-4 rounded-xl bg-slate-800/60 border border-slate-700/80 text-xs text-slate-100 font-mono focus:outline-none focus:border-cyan-500 resize-none min-h-[350px]"
                />
              ) : (
                <div className="flex-1 overflow-y-auto p-4 rounded-xl bg-slate-950/40 border border-slate-800/60 text-xs text-slate-300 leading-relaxed min-h-[350px]">
                  <div className="markdown-body">
                    <Markdown>{activeNote.content}</Markdown>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 text-center py-12">
              <BookOpen className="w-10 h-10 text-slate-600 mb-2" />
              <p className="text-sm font-semibold">{lang === 'id' ? 'Pilih catatan atau buat baru' : 'Select a note or create a new one'}</p>
            </div>
          )}
        </div>
      </div>

      {/* Folder Modal */}
      {isNewFolderModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{lang === 'id' ? 'Buat Folder Baru' : 'New Folder'}</h3>

            <form onSubmit={handleCreateFolder} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nama Folder' : 'Folder Name'}</label>
                <input
                  type="text"
                  required
                  value={newFolderName}
                  onChange={(e) => setNewFolderName(e.target.value)}
                  placeholder="e.g. Kampus, Kerja, Quest Log..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Emoji Icon</label>
                <input
                  type="text"
                  value={newFolderIcon}
                  onChange={(e) => setNewFolderIcon(e.target.value)}
                  className="w-20 px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-center text-lg"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewFolderModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
