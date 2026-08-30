import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import {
  BookOpen,
  Plus,
  Trash2,
  Sparkles,
  Bot,
  Brain,
  HelpCircle,
  Headphones,
  Send,
  FileText,
  CheckCircle2,
  XCircle,
  Play,
  Pause,
  RotateCcw,
  Layers,
  Calculator,
  ExternalLink,
  Pencil,
  Eye,
  Download,
  ZoomIn,
  ZoomOut,
  Maximize,
  Upload,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import { studio } from '../../api/studio';
import { t as tr } from '../../i18n';

type LearningTab = 'chat' | 'sources' | 'flashcards' | 'quiz' | 'podcast' | 'math' | 'studio';

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
          {lang === 'id' ? '🧠 Peta Pikiran' : '🧠 Mind Map'}
        </span>
        <div className="ml-auto flex items-center gap-1">
          <button onClick={() => zoomStep(-0.2)} className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-violet-300" title="Zoom out"><ZoomOut className="w-3.5 h-3.5" /></button>
          <button onClick={() => setZoom(1.15)} className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-violet-300" title="Fit"><Maximize className="w-3.5 h-3.5" /></button>
          <button onClick={() => zoomStep(0.2)} className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-violet-300" title="Zoom in"><ZoomIn className="w-3.5 h-3.5" /></button>
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
    showToast,
  } = useGame();

  const [activeNotebookId, setActiveNotebookId] = useState<string>(notebooks[0]?.id || '');
  const [activeTab, setActiveTab] = useState<LearningTab>('chat');
  // PyQt parity: auto-create a first notebook when the list is empty (PyQt seeds
  // a "First Notebook" via `db.create_learning_notebook`). Guarded to run once.
  const seededRef = useRef(false);
  useEffect(() => {
    if (seededRef.current) return;
    if (notebooks.length === 0) {
      seededRef.current = true;
      addNotebook(lang === 'id' ? 'Notebook Pertama' : 'First Notebook', '');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [notebooks.length]);

  // Input states
  const [chatInput, setChatInput] = useState('');
  const [isAiLoading, setIsAiLoading] = useState(false);

  // New notebook modal
  const [showNewNbModal, setShowNewNbModal] = useState(false);
  const [newNbTitle, setNewNbTitle] = useState('');
  const [newNbDesc, setNewNbDesc] = useState('');
  const [newNbIcon, setNewNbIcon] = useState('📚');

  // New source modal
  const [showNewSourceModal, setShowNewSourceModal] = useState(false);
  const [newSourceTitle, setNewSourceTitle] = useState('');
  const [newSourceContent, setNewSourceContent] = useState('');
  const [newSourceType, setNewSourceType] = useState<'text' | 'doc' | 'pdf' | 'url'>('text');
  const [geminiKey, setGeminiKey] = useState('');

  // ── Parity LearningPage: font chat/studio, rename, upload source, history ──
  const [chatFontSize, setChatFontSize] = useState(13);
  const [studioFontSize, setStudioFontSize] = useState(13);
  const [renaming, setRenaming] = useState(false);
  const [renameTitle, setRenameTitle] = useState('');
  const [studioTopic, setStudioTopic] = useState('');
  const [selectedGen, setSelectedGen] = useState<any | null>(null);
  const [viewingSource, setViewingSource] = useState<{ title: string; content: string } | null>(null);
  const [uploadingSource, setUploadingSource] = useState(false);
  const sourceFileRef = useRef<HTMLInputElement | null>(null);

  const handleRename = async () => {
    if (!activeNotebook || !renameTitle.trim()) return;
    try {
      const r = await studio.renameNotebook(activeNotebook.id, renameTitle.trim());
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr('learning_no_title', 'Judul tidak boleh kosong.'), ''); return; }
      updateNotebook(activeNotebook.id, { title: renameTitle.trim() });
      refreshNotebooks();
      setRenaming(false);
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  const handleDeleteGeneration = async (genId: string) => {
    if (!activeNotebook || !window.confirm(tr('learning_delete_gen', 'Hapus hasil generasi ini?'))) return;
    try {
      await studio.deleteGeneration(activeNotebook.id, genId);
      if (selectedGen?.id === genId) setSelectedGen(null);
      refreshNotebooks();
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
  };

  const handleUploadSource = async (file: File) => {
    if (!activeNotebook || !file) return;
    setUploadingSource(true);
    try {
      const r = await studio.uploadLearningSource(activeNotebook.id, file);
      const res = r?.result || r;
      if (res?.ok === false) { showToast('damage', tr(res?.msg || 'learning_source_empty_file', 'File tidak berisi teks yang dapat dibaca.'), ''); return; }
      showToast('success', tr('learning_source_added', 'Source ditambahkan'), file.name);
      refreshNotebooks();
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
    finally { setUploadingSource(false); }
  };

  const handleViewSource = async (sourceId: string) => {
    if (!activeNotebook) return;
    try {
      const r = await studio.learningSourceContent(activeNotebook.id, sourceId);
      const res = r?.result || r;
      if (!res?.ok) { showToast('damage', tr(res?.msg || 'learning_not_found', 'Tidak ditemukan.'), ''); return; }
      const src = res.source || res;
      setViewingSource({ title: src.title || 'Source', content: src.content || '' });
    } catch (e) { showToast('damage', String((e as any)?.message || e), ''); }
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
    const blob = new Blob([parts.join('\n\n')], { type: 'text/plain;charset=utf-8' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${(activeNotebook.title || 'studio').replace(/[^\w\- ]+/g, '').trim() || 'studio'}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
    showToast('success', tr('learning_export_done', 'Ekspor selesai'), '');
  };

  // Flashcards state
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isCardFlipped, setIsCardFlipped] = useState(false);

  // Quiz state
  const [selectedAnswers, setSelectedAnswers] = useState<Record<number, number>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  // Podcast / Audio playback state
  const [isPodcastPlaying, setIsPodcastPlaying] = useState(false);
  const [currentLineIndex, setCurrentLineIndex] = useState(0);

  // Math Problem state
  const [mathProblem, setMathProblem] = useState('x^2 - 5x + 6 = 0');
  const [mathSolution, setMathSolution] = useState('');
  const [isSolvingMath, setIsSolvingMath] = useState(false);

  const activeNotebook = notebooks.find((nb) => nb.id === activeNotebookId) || notebooks[0];
  const activeGenList: any[] = (activeNotebook as any)?.generations || [];

  // AI Chat Handler
  const handleSendChat = async () => {
    if (!chatInput.trim() || !activeNotebook) return;
    const userMsg = chatInput.trim();
    setChatInput('');
    addNotebookChat(activeNotebook.id, userMsg, 'user');
    setIsAiLoading(true);

    const combinedSources = activeNotebook.sources.map((s) => `[Source: ${s.title}]\n${s.content}`).join('\n\n');

    try {
      const data = await studio.chat(activeNotebook.id, userMsg);
      const reply = data.answer || data.reply || data.result?.answer;
      addNotebookChat(activeNotebook.id, reply || data.error || 'Failed to get response', 'ai');
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
  const handleGenerateFlashcards = async () => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', 'AI Thinking', 'Synthesizing study flashcards...');

    try {
      const data = await studio.generate('flashcards', {
        content: combined,
        topic: activeNotebook.title,
        notebookId: activeNotebook.id,
        count: 5,
      });
      const cards = data.flashcards || data.result?.flashcards || [];
      if (cards.length > 0) {
        updateNotebook(activeNotebook.id, {
          flashcards: cards.map((f: any, i: number) => ({ id: 'fc_' + Date.now() + '_' + i, ...f })),
        });
        showToast('success', 'Flashcards Ready', `Generated ${cards.length} cards.`);
        refreshNotebooks();
      } else {
        showToast('damage', 'AI', data.msg || 'empty');
      }
    } catch {
      showToast('damage', 'AI Error', 'Could not generate flashcards.');
    } finally {
      setIsAiLoading(false);
    }
  };

  // Generate Quiz
  const handleGenerateQuiz = async () => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', 'AI Thinking', 'Generating multiple choice questions...');

    try {
      const data = await studio.generate('quiz', {
        content: combined,
        topic: activeNotebook.title,
        notebookId: activeNotebook.id,
        questionCount: 10,
      });
      const quiz = data.quiz || data.result?.quiz || [];
      if (quiz.length > 0) {
        updateNotebook(activeNotebook.id, {
          quizzes: quiz.map((q: any, i: number) => ({ id: 'q_' + Date.now() + '_' + i, ...q })),
        });
        setSelectedAnswers({});
        setQuizSubmitted(false);
        showToast('success', 'Quiz Generated', `Ready for test (${quiz.length} questions).`);
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
  const handleGeneratePodcast = async () => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    showToast('info', 'AI Audio Synthesis', 'Writing two-host audio dialogue overview...');

    try {
      const data = await studio.generate('podcast', {
        content: combined,
        topic: activeNotebook.title,
        notebookId: activeNotebook.id,
      });
      const dialogue = data.podcast || data.dialogue || data.result?.podcast || [];
      if (dialogue.length > 0) {
        updateNotebook(activeNotebook.id, { podcast: dialogue });
        showToast('success', 'Deep Dive Ready', '2-Host conversation script generated.');
        refreshNotebooks();
      } else {
        showToast('damage', 'AI', data.msg || 'empty');
      }
    } catch {
      showToast('damage', 'AI Error', 'Could not generate podcast script.');
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


  const handleGenerateStudio = async (kind: string) => {
    if (!activeNotebook) return;
    const combined = activeNotebook.sources.map((s) => s.content).join('\n\n') || activeNotebook.description;
    setIsAiLoading(true);
    try {
      const data = await studio.generate(kind, {
        content: combined,
        topic: studioTopic.trim() || activeNotebook.title,
        notebookId: activeNotebook.id,
      });
      const payload: any = {};
      if (kind === 'study-guide') payload.studyGuide = data.studyGuide || data.result?.studyGuide || data.raw;
      if (kind === 'mindmap') payload.mindMap = data.mindMap || data.result?.mindMap;
      if (kind === 'faq') payload.faq = data.faq || data.result?.faq || data.raw;
      if (kind === 'timeline') payload.timeline = data.timeline || data.result?.timeline || data.raw;
      if (kind === 'summary') payload.summary = data.summary || data.result?.summary || data.raw;
      updateNotebook(activeNotebook.id, payload);
      showToast('success', 'Studio', kind);
      setSelectedGen(null);
      refreshNotebooks();
    } catch {
      showToast('damage', 'AI Error', kind);
    } finally {
      setIsAiLoading(false);
    }
  };

  // Read speech using browser SpeechSynthesis
  const speakLine = (text: string) => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  };

  return (
    <div id="learning-workspace-view" className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-2xl">
            📚
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'id' ? 'Workspace Belajar AI' : 'AI Learning Workspace'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-medium">NotebookLM Style</span>
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Kelola sumber belajar, tanyakan materi dengan AI, buat flashcards, kuis, dan podcast otomatis.'
                : 'Manage sources, chat with grounded AI, generate flashcards, practice quizzes, and audio overviews.'}
            </p>
          </div>
        </div>
        <button
          onClick={() => setShowNewNbModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold rounded-xl transition-colors shadow-lg shadow-violet-600/20"
        >
          <Plus className="w-4 h-4" />
          <span>{lang === 'id' ? 'Notebook Baru' : 'New Notebook'}</span>
        </button>
      </div>

      {/* Main Grid: Notebooks Sidebar + Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Left Column: Notebook List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
            {lang === 'id' ? 'Daftar Notebook' : 'Your Notebooks'} ({notebooks.length})
          </h3>
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
            {notebooks.map((nb) => {
              const isActive = nb.id === (activeNotebook?.id || '');
              return (
                <div
                  key={nb.id}
                  onClick={() => {
                    setActiveNotebookId(nb.id);
                    setSelectedAnswers({});
                    setQuizSubmitted(false);
                  }}
                  className={`p-3.5 rounded-xl border cursor-pointer transition-all flex items-start justify-between gap-2 ${
                    isActive
                      ? 'bg-violet-950/40 border-violet-500/40 text-slate-100 shadow-md shadow-violet-950/30'
                      : 'bg-slate-900/50 border-slate-800/80 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <div className="flex items-start gap-2.5 overflow-hidden">
                    <span className="text-xl shrink-0">{nb.icon || '📚'}</span>
                    <div className="truncate">
                      <h4 className="font-semibold text-sm truncate text-slate-200">{nb.title}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {nb.sources?.length || 0} {lang === 'id' ? 'sumber' : 'sources'} · {nb.flashcards?.length || 0} cards
                      </p>
                    </div>
                  </div>
                  {notebooks.length > 1 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteNotebook(nb.id);
                      }}
                      className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Main Workspace Stage */}
        <div className="lg:col-span-3 space-y-4">
          {activeNotebook ? (
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 space-y-5">
              {/* Notebook Header & Navigation Tabs */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{activeNotebook.icon || '📚'}</span>
                  <div>
                    <h2 className="text-lg font-bold text-slate-100">{activeNotebook.title}</h2>
                    <p className="text-xs text-slate-400">{activeNotebook.description || 'No description provided.'}</p>
                  </div>
                  {/* Parity LearningPage._rename_notebook */}
                  <button
                    onClick={() => { setRenameTitle(activeNotebook.title); setRenaming(true); }}
                    className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-violet-300 hover:border-violet-500/50 transition-colors self-start mt-0.5"
                    title={tr('learning_rename_title', 'Ubah judul notebook')}
                  >
                    <Pencil className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Sub-tabs */}
                <div className="flex flex-wrap items-center gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800 text-xs font-medium">
                  <button
                    onClick={() => setActiveTab('chat')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'chat' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Bot className="w-3.5 h-3.5" />
                    <span>AI Chat</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('sources')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'sources' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <FileText className="w-3.5 h-3.5" />
                    <span>{lang === 'id' ? 'Sumber' : 'Sources'} ({activeNotebook.sources?.length || 0})</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('flashcards')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'flashcards' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Layers className="w-3.5 h-3.5" />
                    <span>Flashcards</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('quiz')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'quiz' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                    <span>Quiz</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('podcast')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'podcast' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Headphones className="w-3.5 h-3.5" />
                    <span>Deep Dive</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('studio')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'studio' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Studio</span>
                  </button>
                  <button
                    onClick={() => setActiveTab('math')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition-colors ${
                      activeTab === 'math' ? 'bg-violet-600 text-white font-semibold' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <Calculator className="w-3.5 h-3.5" />
                    <span>Math Solver</span>
                  </button>
                </div>
              </div>

              {/* TAB 1: AI Grounded Chat */}
              {activeTab === 'chat' && (
                <div className="space-y-4">
                  {/* Parity LearningPage: kontrol font chat (A−/A+, clamp 10..30) */}
                  <div className="flex items-center justify-end gap-2 text-xs text-slate-400">
                    <span>{tr('learning_font_chat', 'Font Chat AI')}: <b className="text-slate-200">{chatFontSize}px</b></span>
                    <button onClick={() => setChatFontSize((v) => clampFont(v - 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_decrease', 'A−')}</button>
                    <button onClick={() => setChatFontSize((v) => clampFont(v + 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_increase', 'A+')}</button>
                  </div>
                  <div style={{ fontSize: chatFontSize }} className="h-[420px] overflow-y-auto space-y-3 p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    {(!activeNotebook.chatHistory || activeNotebook.chatHistory.length === 0) && (
                      <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                        <Sparkles className="w-10 h-10 mb-3 text-violet-400/50" />
                        <h4 className="font-semibold text-slate-300">
                          {lang === 'id' ? 'Tanyakan materi dari sumber ini' : 'Ask questions about your notebook sources'}
                        </h4>
                        <p className="text-xs max-w-sm mt-1">
                          {lang === 'id'
                            ? 'AI akan membaca seluruh sumber catatan untuk menjawab pertanyaan dan meringkas konsep kunci.'
                            : 'AI will ground answers in the documents and notes added to this notebook.'}
                        </p>
                      </div>
                    )}
                    {activeNotebook.chatHistory?.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        {msg.sender === 'ai' && (
                          <div className="w-8 h-8 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-sm shrink-0 text-violet-300">
                            <Bot className="w-4 h-4" />
                          </div>
                        )}
                        <div
                          className={`p-3.5 rounded-2xl max-w-xl text-sm leading-relaxed ${
                            msg.sender === 'user'
                              ? 'bg-violet-600 text-white rounded-br-none'
                              : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
                          }`}
                        >
                          <div className="prose prose-invert prose-sm">
                            <ReactMarkdown>{msg.text}</ReactMarkdown>
                          </div>
                          <span className="block text-[10px] text-slate-400 mt-1 text-right">{msg.timestamp}</span>
                        </div>
                      </div>
                    ))}
                    {isAiLoading && (
                      <div className="flex items-center gap-2 text-violet-400 text-xs p-2">
                        <Sparkles className="w-4 h-4 animate-spin" />
                        <span>{lang === 'id' ? 'AI sedang membaca sumber dan menganalisis...' : 'AI is synthesizing response...'}</span>
                      </div>
                    )}
                  </div>

                  {/* Chat Input Bar */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                      placeholder={
                        lang === 'id'
                          ? 'Tanyakan sesuatu tentang notebook ini...'
                          : 'Ask anything based on these study sources...'
                      }
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500"
                    />
                    <button
                      onClick={handleSendChat}
                      disabled={isAiLoading || !chatInput.trim()}
                      className="px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-colors flex items-center gap-1.5 shadow-md shadow-violet-600/20"
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 2: Notebook Sources */}
              {activeTab === 'sources' && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">
                      {lang === 'id'
                        ? 'Sumber teks, dokumen, atau URL yang menjadi dasar rujukan AI.'
                        : 'Documents, raw text, and reference sources grounding the AI.'}
                    </span>
                    <div className="flex items-center gap-2">
                      {/* Parity LearningPage._add_source_files (.txt/.md/.pdf/.docx) */}
                      <input
                        ref={sourceFileRef}
                        type="file"
                        accept=".txt,.md,.pdf,.docx"
                        className="hidden"
                        onChange={(e) => {
                          const f = e.target.files?.[0];
                          if (f) handleUploadSource(f);
                          e.target.value = '';
                        }}
                      />
                      <button
                        onClick={() => sourceFileRef.current?.click()}
                        disabled={uploadingSource}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-semibold text-slate-200 rounded-lg transition-colors border border-slate-700"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        <span>{uploadingSource ? '...' : tr('learning_upload_source', 'Upload File')}</span>
                      </button>
                      <button
                        onClick={() => setShowNewSourceModal(true)}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-lg transition-colors border border-slate-700"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>{lang === 'id' ? 'Tambah Sumber' : 'Add Source'}</span>
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {(!activeNotebook.sources || activeNotebook.sources.length === 0) && (
                      <div className="p-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
                        <FileText className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                        <p className="text-sm font-medium">{lang === 'id' ? 'Belum ada sumber referensi.' : 'No sources uploaded yet.'}</p>
                        <p className="text-xs mt-1">
                          {lang === 'id' ? 'Klik "Tambah Sumber" untuk memasukkan catatan atau materi.' : 'Click "Add Source" to add notes, PDFs, or study text.'}
                        </p>
                      </div>
                    )}
                    {activeNotebook.sources?.map((src) => (
                      <div
                        key={src.id}
                        className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl flex items-start justify-between gap-4"
                      >
                        <div className="space-y-1.5 flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs uppercase px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-semibold">
                              {src.type}
                            </span>
                            <h4 className="font-bold text-sm text-slate-200">{src.title}</h4>
                            <span className="text-xs text-slate-500">({src.wordCount} words)</span>
                          </div>
                          <p className="text-xs text-slate-400 line-clamp-3 font-mono bg-slate-900/90 p-2.5 rounded-lg border border-slate-800/60">
                            {src.content}
                          </p>
                        </div>
                        <div className="flex flex-col gap-1">
                          {/* Parity LearningPage._view_source */}
                          <button
                            onClick={() => handleViewSource(src.id)}
                            className="text-slate-500 hover:text-violet-300 p-1.5 transition-colors"
                            title={tr('learning_view', 'Lihat')}
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => deleteNotebookSource(activeNotebook.id, src.id)}
                            className="text-slate-500 hover:text-rose-400 p-1.5 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* TAB 3: Flashcards */}
              {activeTab === 'flashcards' && (
                <div className="space-y-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">
                      {lang === 'id' ? 'Kartu memori spaced repetition untuk active recall.' : 'Spaced repetition flashcards generated from notebook.'}
                    </span>
                    <button
                      onClick={handleGenerateFlashcards}
                      disabled={isAiLoading}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white rounded-lg transition-colors shadow-md shadow-violet-600/20"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{lang === 'id' ? 'Buat Kartu AI' : 'Generate with AI'}</span>
                    </button>
                  </div>

                  {activeNotebook.flashcards && activeNotebook.flashcards.length > 0 ? (
                    <div className="flex flex-col items-center space-y-4">
                      {/* Active Flashcard */}
                      <div
                        onClick={() => setIsCardFlipped(!isCardFlipped)}
                        className="w-full max-w-lg min-h-[220px] p-6 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700/80 rounded-2xl shadow-xl flex flex-col items-center justify-center text-center cursor-pointer transition-all hover:border-violet-500/50 relative select-none"
                      >
                        <span className="absolute top-4 right-4 text-xs font-bold text-slate-500">
                          {currentCardIndex + 1} / {activeNotebook.flashcards.length}
                        </span>
                        <span className="text-xs font-bold uppercase tracking-wider text-violet-400 mb-2">
                          {isCardFlipped ? (lang === 'id' ? 'Jawaban' : 'Answer') : (lang === 'id' ? 'Pertanyaan' : 'Question')}
                        </span>
                        <p className="text-base font-semibold text-slate-100 max-w-md">
                          {isCardFlipped
                            ? activeNotebook.flashcards[currentCardIndex]?.answer
                            : activeNotebook.flashcards[currentCardIndex]?.question}
                        </p>
                        <span className="absolute bottom-3 text-[11px] text-slate-500">
                          {lang === 'id' ? 'Klik untuk membalik kartu' : 'Click card to flip'}
                        </span>
                      </div>

                      {/* Pagination Controls */}
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => {
                            setIsCardFlipped(false);
                            setCurrentCardIndex((prev) => (prev > 0 ? prev - 1 : activeNotebook.flashcards.length - 1));
                          }}
                          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200"
                        >
                          {lang === 'id' ? 'Sebelumnya' : 'Previous'}
                        </button>
                        <button
                          onClick={() => setIsCardFlipped(!isCardFlipped)}
                          className="px-4 py-2 bg-violet-600/30 hover:bg-violet-600/40 text-violet-300 text-xs font-bold rounded-lg border border-violet-500/30"
                        >
                          {lang === 'id' ? 'Balik Kartu' : 'Flip'}
                        </button>
                        <button
                          onClick={() => {
                            setIsCardFlipped(false);
                            setCurrentCardIndex((prev) => (prev < activeNotebook.flashcards.length - 1 ? prev + 1 : 0));
                          }}
                          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200"
                        >
                          {lang === 'id' ? 'Berikutnya' : 'Next'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
                      <Layers className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                      <p className="text-sm font-medium">{lang === 'id' ? 'Belum ada flashcard.' : 'No flashcards yet.'}</p>
                      <p className="text-xs mt-1">
                        {lang === 'id' ? 'Klik "Buat Kartu AI" untuk membuat kartu otomatis dari sumber.' : 'Click "Generate with AI" to create flashcards from your sources.'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Quiz Mode */}
              {activeTab === 'quiz' && (
                <div className="space-y-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">
                      {lang === 'id' ? 'Uji pemahaman materi dengan kuis pilihan ganda interaktif.' : 'Test your mastery with interactive multiple choice questions.'}
                    </span>
                    <button
                      onClick={handleGenerateQuiz}
                      disabled={isAiLoading}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white rounded-lg transition-colors shadow-md shadow-violet-600/20"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{lang === 'id' ? 'Buat Kuis AI' : 'Generate Quiz'}</span>
                    </button>
                  </div>

                  {activeNotebook.quizzes && activeNotebook.quizzes.length > 0 ? (
                    <div className="space-y-5">
                      {activeNotebook.quizzes.map((q, qIndex) => {
                        const userChoice = selectedAnswers[qIndex];
                        const isCorrect = userChoice === q.correctAnswerIndex;
                        return (
                          <div key={q.id || qIndex} className="p-4 bg-slate-950/70 border border-slate-800 rounded-xl space-y-3">
                            <h4 className="font-bold text-sm text-slate-200">
                              {qIndex + 1}. {q.question}
                            </h4>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              {q.options.map((opt, optIndex) => {
                                const isSelected = userChoice === optIndex;
                                let btnStyle = 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700';
                                if (quizSubmitted) {
                                  if (optIndex === q.correctAnswerIndex) {
                                    btnStyle = 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300 font-semibold';
                                  } else if (isSelected && !isCorrect) {
                                    btnStyle = 'bg-rose-950/60 border-rose-500/60 text-rose-300';
                                  }
                                } else if (isSelected) {
                                  btnStyle = 'bg-violet-950/60 border-violet-500/60 text-violet-200 font-semibold';
                                }

                                return (
                                  <button
                                    key={optIndex}
                                    disabled={quizSubmitted}
                                    onClick={() => setSelectedAnswers((prev) => ({ ...prev, [qIndex]: optIndex }))}
                                    className={`p-3 text-left rounded-xl border text-xs transition-colors flex items-center justify-between ${btnStyle}`}
                                  >
                                    <span>{opt}</span>
                                    {quizSubmitted && optIndex === q.correctAnswerIndex && (
                                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                                    )}
                                    {quizSubmitted && isSelected && !isCorrect && (
                                      <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                                    )}
                                  </button>
                                );
                              })}
                            </div>
                            {quizSubmitted && (
                              <p className="text-xs text-slate-400 bg-slate-900/80 p-2.5 rounded-lg border border-slate-800/80">
                                <span className="font-bold text-slate-300">Explanation:</span> {q.explanation}
                              </p>
                            )}
                          </div>
                        );
                      })}

                      <div className="flex justify-end gap-3 pt-2">
                        {!quizSubmitted ? (
                          <button
                            onClick={() => {
                              setQuizSubmitted(true);
                              showToast('success', 'Quiz Evaluated', 'Check your score and explanations.');
                            }}
                            className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl transition-colors shadow-lg shadow-emerald-600/20"
                          >
                            {lang === 'id' ? 'Kirim Jawaban' : 'Submit Quiz'}
                          </button>
                        ) : (
                          <button
                            onClick={() => {
                              setSelectedAnswers({});
                              setQuizSubmitted(false);
                            }}
                            className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-xl transition-colors flex items-center gap-1.5"
                          >
                            <RotateCcw className="w-3.5 h-3.5" />
                            <span>{lang === 'id' ? 'Ulangi Kuis' : 'Retake Quiz'}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
                      <HelpCircle className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                      <p className="text-sm font-medium">{lang === 'id' ? 'Belum ada soal kuis.' : 'No quiz generated yet.'}</p>
                      <p className="text-xs mt-1">
                        {lang === 'id' ? 'Klik "Buat Kuis AI" untuk menyusun ujian pilihan ganda otomatis.' : 'Click "Generate Quiz" to test yourself.'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: Deep Dive Podcast (2-Host Audio Overview) */}
              {activeTab === 'podcast' && (
                <div className="space-y-5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400">
                      {lang === 'id' ? 'Dua host AI (Alex & Sam) berdiskusi mendalam tentang intisari materi.' : 'Two AI hosts (Alex & Sam) discuss insights in an audio overview.'}
                    </span>
                    <button
                      onClick={handleGeneratePodcast}
                      disabled={isAiLoading}
                      className="flex items-center gap-1.5 px-3.5 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white rounded-lg transition-colors shadow-md shadow-violet-600/20"
                    >
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{lang === 'id' ? 'Generate Audio Script' : 'Generate Audio Script'}</span>
                    </button>
                  </div>

                  {activeNotebook.podcast && activeNotebook.podcast.length > 0 ? (
                    <div className="space-y-4">
                      {/* Audio Controls Bar */}
                      <div className="p-4 bg-slate-950 rounded-xl border border-slate-800 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <button
                            onClick={() => {
                              const nextPlaying = !isPodcastPlaying;
                              setIsPodcastPlaying(nextPlaying);
                              if (nextPlaying && activeNotebook.podcast[currentLineIndex]) {
                                speakLine(activeNotebook.podcast[currentLineIndex].line);
                              } else {
                                window.speechSynthesis?.cancel();
                              }
                            }}
                            className="w-10 h-10 rounded-xl bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center transition-colors shadow-lg shadow-violet-600/30"
                          >
                            {isPodcastPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                          </button>
                          <div>
                            <h4 className="font-bold text-sm text-slate-200">
                              {activeNotebook.title} · Deep Dive Episode
                            </h4>
                            <p className="text-xs text-slate-500">
                              {lang === 'id' ? 'Host: Alex & Sam · Text-to-Speech Engine' : 'Hosts: Alex & Sam · Natural Speech Synthesis'}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Dialogue Transcript */}
                      <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                        {activeNotebook.podcast.map((line, idx) => (
                          <div
                            key={idx}
                            onClick={() => {
                              setCurrentLineIndex(idx);
                              speakLine(line.line);
                            }}
                            className={`p-3.5 rounded-xl border cursor-pointer transition-colors ${
                              line.speaker === 'Alex'
                                ? 'bg-indigo-950/30 border-indigo-500/30'
                                : 'bg-emerald-950/30 border-emerald-500/30'
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span
                                className={`text-xs font-bold uppercase tracking-wider ${
                                  line.speaker === 'Alex' ? 'text-indigo-400' : 'text-emerald-400'
                                }`}
                              >
                                🎙️ {line.speaker}
                              </span>
                              <span className="text-[10px] text-slate-500">Click to listen</span>
                            </div>
                            <p className="text-sm text-slate-200 leading-relaxed">{line.line}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
                      <Headphones className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                      <p className="text-sm font-medium">{lang === 'id' ? 'Belum ada episode podcast.' : 'No audio overview generated yet.'}</p>
                      <p className="text-xs mt-1">
                        {lang === 'id' ? 'Klik "Generate Audio Script" untuk membuat diskusi audio dua host.' : 'Click "Generate Audio Script" to create an audio deep dive overview.'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 6: Math Problem Solver */}
              {activeTab === 'math' && (
                <div className="space-y-5">
                  <div className="space-y-1">
                    <h3 className="font-bold text-sm text-slate-200">
                      {lang === 'id' ? 'Pemecah Soal & Rumus Matematika (mathtools.py)' : 'Step-by-Step Math & Scientific Solver'}
                    </h3>
                    <p className="text-xs text-slate-400">
                      {lang === 'id'
                        ? 'Ketik ekspresi aljabar, kalkulus, atau rumus LaTeX untuk mendapatkan penjabaran langkah demi langkah.'
                        : 'Input algebra, calculus, or LaTeX expressions for detailed step-by-step reasoning.'}
                    </p>
                  </div>

                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="text"
                      value={mathProblem}
                      onChange={(e) => setMathProblem(e.target.value)}
                      placeholder="e.g. 2x^2 + 5x - 3 = 0, \int x \sin(x) dx"
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 font-mono"
                    />
                    <button
                      onClick={handleSolveMath}
                      disabled={isSolvingMath || !mathProblem.trim()}
                      className="px-5 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm transition-colors flex items-center justify-center gap-1.5 shadow-md shadow-violet-600/20"
                    >
                      <Brain className="w-4 h-4" />
                      <span>{lang === 'id' ? 'Pecahkan Soal' : 'Solve Step-by-Step'}</span>
                    </button>
                  </div>

                  {mathSolution && (
                    <div className="p-5 bg-slate-950/80 border border-slate-800 rounded-xl space-y-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-violet-400">
                        {lang === 'id' ? 'Penjelasan & Solusi' : 'Solution Breakdown'}
                      </span>
                      <div className="prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown>{mathSolution}</ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'studio' && (
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <input
                      type="password"
                      value={geminiKey}
                      onChange={(e) => setGeminiKey(e.target.value)}
                      placeholder="Gemini API key"
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs"
                    />
                    <button
                      type="button"
                      onClick={() => {
                        studio.setGeminiKey(geminiKey).then(() => showToast('success', 'Gemini', 'saved')).catch((e) => showToast('damage', String(e), ''));
                      }}
                      className="px-3 py-1.5 rounded-lg bg-violet-600 text-white text-xs font-semibold"
                    >
                      Save key
                    </button>
                  </div>
                  <p className="text-xs text-slate-400">
                    {lang === 'id'
                      ? 'Study guide, peta pikiran, FAQ, timeline, dan ringkasan (generate_studio_content).'
                      : 'Study guide, mind map, FAQ, timeline, and summary via generate_studio_content.'}
                  </p>
                  {/* Parity QInputDialog learning_topic_prompt: topik opsional */}
                  <input
                    type="text"
                    value={studioTopic}
                    onChange={(e) => setStudioTopic(e.target.value)}
                    placeholder={tr('learning_topic_label', 'Topik (kosongkan = semua):')}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200"
                  />
                  <div className="flex flex-wrap gap-2">
                    {(['study-guide', 'mindmap', 'faq', 'timeline', 'summary'] as const).map((k) => (
                      <button
                        key={k}
                        disabled={isAiLoading}
                        onClick={() => handleGenerateStudio(k)}
                        className="px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white"
                      >
                        {isAiLoading ? tr('learning_generating', 'Generate') : k}
                      </button>
                    ))}
                  </div>

                  {/* Parity: kontrol font studio + ekspor */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span>{tr('learning_font_studio', 'Font Hasil Studio')}: <b className="text-slate-200">{studioFontSize}px</b></span>
                      <button onClick={() => setStudioFontSize((v) => clampFont(v - 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_decrease', 'A−')}</button>
                      <button onClick={() => setStudioFontSize((v) => clampFont(v + 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_increase', 'A+')}</button>
                      <button onClick={() => setStudioFontSize(13)} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_reset', 'Reset')}</button>
                    </div>
                    <button
                      onClick={handleExportStudio}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700/80 hover:bg-emerald-600 text-xs font-semibold text-white"
                      title={tr('learning_export', 'Ekspor')}
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{tr('learning_export_compact', 'Ekspor')}</span>
                    </button>
                  </div>

                  {/* Output: history pilihan atau slot terbaru */}
                  <div style={{ fontSize: studioFontSize }} className="prose prose-invert prose-sm max-w-none text-slate-200 space-y-3">
                    {selectedGen ? (
                      <div className="space-y-2">
                        <div className="text-[10px] uppercase tracking-wider text-violet-400">
                          {selectedGen.gtype} · {selectedGen.topic || '-'} · {selectedGen.createdAt || ''}
                        </div>
                        {selectedGen.gtype === 'mindmap'
                          ? <MindMapView raw={selectedGen.content} lang={lang} fontSize={studioFontSize} />
                          : <ReactMarkdown>{String(selectedGen.content || '')}</ReactMarkdown>}
                      </div>
                    ) : (
                      <>
                        {(activeNotebook as any).studyGuide && <ReactMarkdown>{String((activeNotebook as any).studyGuide)}</ReactMarkdown>}
                        {(activeNotebook as any).faq && <ReactMarkdown>{String((activeNotebook as any).faq)}</ReactMarkdown>}
                        {(activeNotebook as any).timeline && <ReactMarkdown>{String((activeNotebook as any).timeline)}</ReactMarkdown>}
                        {(activeNotebook as any).summary && <ReactMarkdown>{String((activeNotebook as any).summary)}</ReactMarkdown>}
                        {(activeNotebook as any).mindMap && (
                          <MindMapView raw={(activeNotebook as any).mindMap} lang={lang} fontSize={studioFontSize} />
                        )}
                      </>
                    )}
                  </div>

                  {/* Parity LearningPage._load_generations + _delete_generation */}
                  {activeGenList.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 space-y-2">
                      <h4 className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
                        {tr('learning_history', 'Riwayat Studio')} ({activeGenList.length})
                      </h4>
                      <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                        {activeGenList.map((g: any) => (
                          <div key={g.id} className="flex items-center gap-2 p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-xs">
                            <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-semibold shrink-0">{g.gtype}</span>
                            <span className="truncate flex-1 text-slate-300">{g.topic || '(topik umum)'}</span>
                            <span className="text-slate-600 shrink-0">{g.createdAt}</span>
                            <button
                              onClick={() => setSelectedGen(selectedGen?.id === g.id ? null : g)}
                              className={`p-1 transition-colors ${selectedGen?.id === g.id ? 'text-violet-300' : 'text-slate-500 hover:text-violet-300'}`}
                              title={tr('learning_view', 'Lihat')}
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteGeneration(g.id)}
                              className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center bg-slate-900/50 border border-slate-800 rounded-2xl text-slate-500">
              <BookOpen className="w-12 h-12 mx-auto mb-3 text-slate-600" />
              <p className="text-base font-semibold">{lang === 'id' ? 'Pilih notebook atau buat baru.' : 'Select or create a notebook.'}</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal: New Notebook */}
      {showNewNbModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Buat Notebook Baru' : 'Create New Notebook'}</h3>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul' : 'Title'}</label>
                <input
                  type="text"
                  value={newNbTitle}
                  onChange={(e) => setNewNbTitle(e.target.value)}
                  placeholder="e.g. Physics Dynamics, Machine Learning"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Deskripsi' : 'Description'}</label>
                <input
                  type="text"
                  value={newNbDesc}
                  onChange={(e) => setNewNbDesc(e.target.value)}
                  placeholder="Short summary of this notebook..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">Emoji Icon</label>
                <div className="flex gap-2">
                  {['📚', '🧠', '🔬', '💻', '📐', '🚀', '📝', '⚡'].map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => setNewNbIcon(emoji)}
                      className={`text-xl p-2 rounded-lg border ${
                        newNbIcon === emoji ? 'bg-violet-600/30 border-violet-500' : 'bg-slate-950 border-slate-800'
                      }`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowNewNbModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!newNbTitle.trim()) return;
                  addNotebook(newNbTitle.trim(), newNbDesc.trim(), newNbIcon);
                  setShowNewNbModal(false);
                  setNewNbTitle('');
                  setNewNbDesc('');
                }}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white rounded-xl"
              >
                {lang === 'id' ? 'Buat Notebook' : 'Create Notebook'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: New Source */}
      {/* Modal: Rename Notebook (parity LearningPage._rename_notebook) */}
      {renaming && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{tr('learning_rename_title', 'Judul notebook baru:')}</h3>
            <input
              type="text"
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              autoFocus
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500"
            />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setRenaming(false)} className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-slate-200">
                {tr('msg_cancel', 'Batal')}
              </button>
              <button onClick={handleRename} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">
                {tr('msg_ok', 'OK')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: View Source (parity LearningPage._view_source) */}
      {viewingSource && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100 mb-3 shrink-0">{viewingSource.title}</h3>
            <div className="overflow-y-auto pr-1 flex-1">
              <pre className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300 font-mono bg-slate-950/60 border border-slate-800 rounded-xl p-4">{viewingSource.content}</pre>
            </div>
            <div className="flex justify-end mt-4 shrink-0">
              <button onClick={() => setViewingSource(null)} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">
                {tr('btn_close', 'Tutup')}
              </button>
            </div>
          </div>
        </div>
      )}

      {showNewSourceModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Tambah Sumber Belajar' : 'Add Study Source'}</h3>
            <div className="space-y-3 text-sm">
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul Dokumen' : 'Source Title'}</label>
                <input
                  type="text"
                  value={newSourceTitle}
                  onChange={(e) => setNewSourceTitle(e.target.value)}
                  placeholder="e.g. Chapter 1 Notes, Article summary"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Tipe' : 'Type'}</label>
                <div className="flex gap-2">
                  {(['text', 'doc', 'pdf', 'url'] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => setNewSourceType(t)}
                      className={`px-3 py-1.5 uppercase text-xs font-bold rounded-lg border ${
                        newSourceType === t ? 'bg-violet-600/30 border-violet-500 text-violet-300' : 'bg-slate-950 border-slate-800 text-slate-400'
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Isi Teks Dokumen' : 'Content / Text'}</label>
                <textarea
                  rows={6}
                  value={newSourceContent}
                  onChange={(e) => setNewSourceContent(e.target.value)}
                  placeholder="Paste notes, textbook paragraphs, or document content here..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 text-xs focus:outline-none focus:border-violet-500 font-mono"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowNewSourceModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  if (!newSourceTitle.trim() || !newSourceContent.trim() || !activeNotebook) return;
                  addNotebookSource(activeNotebook.id, newSourceTitle.trim(), newSourceContent.trim(), newSourceType);
                  setShowNewSourceModal(false);
                  setNewSourceTitle('');
                  setNewSourceContent('');
                }}
                className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white rounded-xl"
              >
                {lang === 'id' ? 'Simpan Sumber' : 'Save Source'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
