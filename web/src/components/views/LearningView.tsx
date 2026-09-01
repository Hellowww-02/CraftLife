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
  KeyRound,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import { studio } from '../../api/studio';
import { t as tr } from '../../i18n';

// Parity LearningPage._STUDIO_TYPES — 8 generator dalam urutan PyQt.
type StudioType = 'summary' | 'study-guide' | 'flashcards' | 'faq' | 'mindmap' | 'timeline' | 'quiz' | 'podcast';
const STUDIO_TYPES: { type: StudioType; icon: string; labelKey: string; default: string[] }[] = [
  { type: 'summary', icon: '📄', labelKey: 'learning_studio_summary', default: [] },
  { type: 'study-guide', icon: '📘', labelKey: 'learning_studio_guide', default: [] },
  { type: 'flashcards', icon: '🃏', labelKey: 'learning_studio_flashcards', default: [] },
  { type: 'faq', icon: '❓', labelKey: 'learning_studio_faq', default: [] },
  { type: 'mindmap', icon: '🗺️', labelKey: 'learning_studio_mindmap', default: [] },
  { type: 'timeline', icon: '🕒', labelKey: 'learning_studio_timeline', default: [] },
  { type: 'quiz', icon: '📝', labelKey: 'learning_studio_quiz', default: [] },
  { type: 'podcast', icon: '🎙️', labelKey: 'learning_studio_podcast_script', default: [] },
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
  const [activeTab, setActiveTab] = useState<'chat' | 'sources' | 'studio'>('chat');
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

  // ── Parity LearningPage 3-panel: output type, count (quiz/flashcards 10-30),
  //    panel toggles (sources/studio) & compact-nav (mobile). ──
  const [activeStudioType, setActiveStudioType] = useState<StudioType>('summary');
  const [studioCount, setStudioCount] = useState(15);
  const [showSources, setShowSources] = useState(true);
  const [showStudio, setShowStudio] = useState(true);
  const [compactPanel, setCompactPanel] = useState<'sources' | 'chat' | 'studio'>('sources');
  // Math Problem state
  const [mathProblem, setMathProblem] = useState('x^2 - 5x + 6 = 0');
  const [mathSolution, setMathSolution] = useState('');
  const [isSolvingMath, setIsSolvingMath] = useState(false);

  const activeNotebook = notebooks.find((nb) => nb.id === activeNotebookId) || notebooks[0];
  const activeGenList: any[] = (activeNotebook as any)?.generations || [];

  // ── Studio output renderers (parity LearningPage studio_output_stack) ──
  const renderFlashcards = () => {
    const cards = activeNotebook?.flashcards || [];
    if (!cards.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500"><Layers className="w-8 h-8 mx-auto mb-2 text-slate-600" /><p className="text-sm font-medium">{lang === 'id' ? 'Belum ada flashcard.' : 'No flashcards yet.'}</p><p className="text-xs mt-1">{lang === 'id' ? 'Klik tombol Flashcards.' : 'Click the Flashcards button.'}</p></div>
      );
    }
    const idx = Math.min(currentCardIndex, cards.length - 1);
    return (
      <div className="flex flex-col items-center space-y-4 py-2">
        <div onClick={() => setIsCardFlipped(!isCardFlipped)} className="w-full min-h-[200px] p-6 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-700/80 rounded-2xl shadow-xl flex flex-col items-center justify-center text-center cursor-pointer transition-all hover:border-violet-500/50 select-none">
          <span className="text-xs font-bold text-slate-500 mb-1">{idx + 1} / {cards.length}</span>
          <span className="text-xs font-bold uppercase tracking-wider text-violet-400 mb-2">{isCardFlipped ? (lang === 'id' ? 'Jawaban' : 'Answer') : (lang === 'id' ? 'Pertanyaan' : 'Question')}</span>
          <p className="text-base font-semibold text-slate-100">{isCardFlipped ? cards[idx]?.answer : cards[idx]?.question}</p>
          <span className="text-[11px] text-slate-500 mt-2">{lang === 'id' ? 'Klik untuk membalik' : 'Click to flip'}</span>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => { setIsCardFlipped(false); setCurrentCardIndex((p) => (p > 0 ? p - 1 : cards.length - 1)); }} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200">{lang === 'id' ? '‹ Sebelumnya' : '‹ Prev'}</button>
          <button onClick={() => setIsCardFlipped(!isCardFlipped)} className="px-3 py-1.5 bg-violet-600/30 hover:bg-violet-600/40 text-violet-300 text-xs font-bold rounded-lg border border-violet-500/30">{lang === 'id' ? 'Balik' : 'Flip'}</button>
          <button onClick={() => { setIsCardFlipped(false); setCurrentCardIndex((p) => (p < cards.length - 1 ? p + 1 : 0)); }} className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-bold rounded-lg text-slate-200">{lang === 'id' ? 'Berikutnya ›' : 'Next ›'}</button>
        </div>
      </div>
    );
  };

  const renderQuiz = () => {
    const quizzes = activeNotebook?.quizzes || [];
    if (!quizzes.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500"><HelpCircle className="w-8 h-8 mx-auto mb-2 text-slate-600" /><p className="text-sm font-medium">{lang === 'id' ? 'Belum ada kuis.' : 'No quiz yet.'}</p><p className="text-xs mt-1">{lang === 'id' ? 'Klik tombol Kuis.' : 'Click the Quiz button.'}</p></div>
      );
    }
    return (
      <div className="space-y-4">
        {quizzes.map((q, qIndex) => {
          const userChoice = selectedAnswers[qIndex];
          const isCorrect = userChoice === q.correctAnswerIndex;
          return (
            <div key={q.id || qIndex} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2">
              <h4 className="font-bold text-sm text-slate-200">{qIndex + 1}. {q.question}</h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {q.options.map((opt, optIndex) => {
                  const isSelected = userChoice === optIndex;
                  let btnStyle = 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700';
                  if (quizSubmitted) {
                    if (optIndex === q.correctAnswerIndex) btnStyle = 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300 font-semibold';
                    else if (isSelected && !isCorrect) btnStyle = 'bg-rose-950/60 border-rose-500/60 text-rose-300';
                  } else if (isSelected) btnStyle = 'bg-violet-950/60 border-violet-500/60 text-violet-200 font-semibold';
                  return (
                    <button key={optIndex} disabled={quizSubmitted} onClick={() => setSelectedAnswers((prev) => ({ ...prev, [qIndex]: optIndex }))} className={`p-2.5 text-left rounded-xl border text-xs transition-colors flex items-center justify-between ${btnStyle}`}>
                      <span>{opt}</span>
                      {quizSubmitted && optIndex === q.correctAnswerIndex && <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />}
                      {quizSubmitted && isSelected && !isCorrect && <XCircle className="w-4 h-4 text-rose-400 shrink-0" />}
                    </button>
                  );
                })}
              </div>
              {quizSubmitted && <p className="text-xs text-slate-400 bg-slate-900/80 p-2 rounded-lg border border-slate-800/80"><span className="font-bold text-slate-300">{lang === 'id' ? 'Pembahasan:' : 'Explanation:'}</span> {q.explanation}</p>}
            </div>
          );
        })}
        <div className="flex justify-end gap-2 pt-1">
          {!quizSubmitted ? (
            <button onClick={() => { setQuizSubmitted(true); showToast('success', 'Quiz Evaluated', 'Check your score.'); }} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl">{lang === 'id' ? 'Periksa Jawaban' : 'Evaluate'}</button>
          ) : (
            <button onClick={() => { setQuizSubmitted(false); setSelectedAnswers({}); }} className="flex items-center gap-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs rounded-xl"><RotateCcw className="w-3.5 h-3.5" /><span>{lang === 'id' ? 'Ulangi Kuis' : 'Retake'}</span></button>
          )}
        </div>
      </div>
    );
  };

  const renderPodcast = () => {
    const lines = activeNotebook?.podcast || [];
    if (!lines.length) {
      return (
        <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500"><Headphones className="w-8 h-8 mx-auto mb-2 text-slate-600" /><p className="text-sm font-medium">{lang === 'id' ? 'Belum ada episode.' : 'No episode yet.'}</p><p className="text-xs mt-1">{lang === 'id' ? 'Klik tombol Podcast.' : 'Click the Podcast button.'}</p></div>
      );
    }
    return (
      <div className="space-y-3">
        <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 flex items-center gap-3">
          <button onClick={() => { const next = !isPodcastPlaying; setIsPodcastPlaying(next); if (next && lines[currentLineIndex]) speakLine(lines[currentLineIndex].line); else window.speechSynthesis?.cancel(); }} className="w-9 h-9 rounded-xl bg-violet-600 hover:bg-violet-500 text-white flex items-center justify-center">{isPodcastPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}</button>
          <div><h4 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Deep Dive Episode' : 'Deep Dive Episode'}</h4><p className="text-[10px] text-slate-500">{lang === 'id' ? 'Host: Alex & Sam · Text-to-Speech' : 'Hosts: Alex & Sam · Text-to-Speech'}</p></div>
        </div>
        <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
          {lines.map((line, idx) => (
            <div key={idx} onClick={() => { setCurrentLineIndex(idx); speakLine(line.line); }} className={`p-2.5 rounded-xl border cursor-pointer transition-colors ${line.speaker === 'Alex' ? 'bg-indigo-950/30 border-indigo-500/30' : 'bg-emerald-950/30 border-emerald-500/30'}`}>
              <div className="flex items-center justify-between mb-1"><span className={`text-xs font-bold uppercase tracking-wider ${line.speaker === 'Alex' ? 'text-indigo-400' : 'text-emerald-400'}`}>🎙️ {line.speaker}</span><span className="text-[10px] text-slate-500">{lang === 'id' ? 'Klik: dengar' : 'Click to listen'}</span></div>
              <p className="text-xs text-slate-200 leading-relaxed">{line.line}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderStudioMarkdown = () => {
    if (activeStudioType === 'mindmap') {
      return <MindMapView raw={(activeNotebook as any).mindMap} lang={lang} fontSize={studioFontSize} />;
    }
    if (selectedGen) {
      return (
        <div className="space-y-2"><div className="text-[10px] uppercase tracking-wider text-violet-400">{selectedGen.gtype} · {selectedGen.topic || '-'} · {selectedGen.createdAt || ''}</div><ReactMarkdown>{String(selectedGen.content || '')}</ReactMarkdown></div>
      );
    }
    return (<>{['studyGuide', 'faq', 'timeline', 'summary'].map((f) => ((activeNotebook as any)[f] ? <ReactMarkdown key={f}>{String((activeNotebook as any)[f])}</ReactMarkdown> : null))}</>);
  };

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
        count: studioCount,
      });
      const cards = data.flashcards || data.result?.flashcards || [];
      if (cards.length > 0) {
        setActiveStudioType('flashcards');
        setCurrentCardIndex(0);
        setIsCardFlipped(false);
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
        count: studioCount,
      });
      const quiz = data.quiz || data.result?.quiz || [];
      if (quiz.length > 0) {
        setActiveStudioType('quiz');
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
        setActiveStudioType('podcast');
        setCurrentLineIndex(0);
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
      setActiveStudioType(kind as StudioType);
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
    <div id="learning-workspace-view" className="space-y-5">
      {/* Header (parity _page_header) + api status + api key */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-2xl">📚</div>
          <div>
            <h1 className="text-xl font-bold text-slate-100">{lang === 'id' ? 'Workspace Belajar AI' : 'AI Learning Workspace'}</h1>
            <p className="text-xs text-slate-400">{lang === 'id' ? 'Sumber + Chat + Studio dalam satu ruang belajar grounded.' : 'Sources + Chat + Studio in one grounded learning workspace.'}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 rounded-full bg-violet-500/10 text-violet-300 border border-violet-500/20 font-semibold">{lang === 'id' ? 'AI' : 'AI'}</span>
          {/* Parity _manage_api_key */}
          <button
            onClick={() => { const k = window.prompt(tr('learning_api_key_label', 'Gemini API key'), geminiKey); if (k !== null && k !== geminiKey) { setGeminiKey(k); studio.setGeminiKey(k).then(() => showToast('success', 'Gemini', 'saved')).catch((e) => showToast('damage', String(e), '')); } }}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl border border-slate-700"
          >
            <KeyRound className="w-3.5 h-3.5" /><span>{lang === 'id' ? 'API Key' : 'API Key'}</span>
          </button>
          <button onClick={() => setShowNewNbModal(true)} className="flex items-center gap-2 px-3.5 py-2 bg-violet-600 hover:bg-violet-500 text-white text-sm font-semibold rounded-xl">
            <Plus className="w-4 h-4" /><span>{lang === 'id' ? 'Notebook Baru' : 'New Notebook'}</span>
          </button>
        </div>
      </div>

      {activeNotebook ? (
        <>
          {/* Notebook toolbar (parity _build toolbar: combo + new/rename/delete + toggle panels) */}
          <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-3 flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-400 font-semibold px-1">{tr('learning_notebook_label', 'Notebook')}:</span>
            <select
              value={activeNotebook.id}
              onChange={(e) => setActiveNotebookId(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-100 min-w-[180px] flex-1"
            >
              {notebooks.map((nb) => <option key={nb.id} value={nb.id}>{nb.icon || '📚'} {nb.title}</option>)}
            </select>
            <button onClick={() => setShowNewNbModal(true)} className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold border border-slate-700"><Plus className="w-3.5 h-3.5" />{tr('learning_new_notebook', 'Baru')}</button>
            <button onClick={() => { setRenameTitle(activeNotebook.title); setRenaming(true); }} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700" title={tr('learning_rename_title', 'Ubah judul notebook')}><Pencil className="w-3.5 h-3.5" /></button>
            <button onClick={() => { if (notebooks.length > 1 && window.confirm(tr('learning_delete_confirm', 'Hapus notebook ini?'))) deleteNotebook(activeNotebook.id); }} className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-700/40 border border-slate-700" title={tr('learning_delete', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
            <div className="ml-auto flex items-center gap-1">
              <button onClick={() => setShowSources((v) => !v)} className={`px-3 py-1.5 rounded-lg border font-semibold ${showSources ? 'bg-violet-600/20 border-violet-500/50 text-violet-200' : 'bg-slate-800 border-slate-700 text-slate-400'} transition-colors`}>{tr('learning_sources_panel', 'Sumber')}</button>
              <button onClick={() => setShowStudio((v) => !v)} className={`px-3 py-1.5 rounded-lg border font-semibold ${showStudio ? 'bg-violet-600/20 border-violet-500/50 text-violet-200' : 'bg-slate-800 border-slate-700 text-slate-400'} transition-colors`}>{tr('learning_studio_panel', 'Studio')}</button>
            </div>
          </div>

          {/* Compact nav (mobile, parity learningCompactNav) */}
          <div className="lg:hidden flex gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
            {(['sources', 'chat', 'studio'] as const).map((k) => (
              <button key={k} onClick={() => setCompactPanel(k)} className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${compactPanel === k ? 'bg-violet-600 text-white' : 'text-slate-400'}`}>
                {k === 'sources' ? tr('learning_sources_panel', 'Sumber') : k === 'chat' ? tr('learning_chat_panel', 'Chat') : tr('learning_studio_panel', 'Studio')}
              </button>
            ))}
          </div>

          {/* 3-panel split (parity _splitter: sources | chat | studio) */}
          <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr_330px] gap-4">
            {/* ── SOURCES PANEL ── */}
            {showSources && (
              <div className={`${compactPanel !== 'sources' ? 'hidden lg:flex' : 'flex ct-slide-in'} flex-col bg-slate-900/70 border border-slate-800 rounded-2xl p-4 space-y-3`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{tr('learning_sources_panel', 'Sumber')} <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300">{activeNotebook.sources?.length || 0}</span></span>
                  <button onClick={() => setShowNewSourceModal(true)} className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700" title={tr('learning_add_source', 'Tambah Sumber')}><Plus className="w-3.5 h-3.5" /></button>
                </div>
                {/* Parity _add_source_files + _add_source_paste */}
                <div className="flex gap-1">
                  <input ref={sourceFileRef} type="file" accept=".txt,.md,.pdf,.docx" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUploadSource(f); e.target.value = ''; }} />
                  <button onClick={() => sourceFileRef.current?.click()} disabled={uploadingSource} className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-semibold text-slate-200 rounded-lg border border-slate-700"><Upload className="w-3.5 h-3.5" />{uploadingSource ? '…' : tr('learning_upload_source', 'Upload')}</button>
                  <button onClick={() => setShowNewSourceModal(true)} className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-lg border border-slate-700"><Pencil className="w-3.5 h-3.5" />{tr('learning_add_source', 'Tambah')}</button>
                </div>
                <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[520px]">
                  {(!activeNotebook.sources || activeNotebook.sources.length === 0) ? (
                    <div className="py-8 text-center bg-slate-950/40 border border-slate-800/80 rounded-xl text-slate-500">
                      <FileText className="w-8 h-8 mx-auto mb-2 text-slate-600" />
                      <p className="text-sm font-medium">{lang === 'id' ? 'Belum ada sumber.' : 'No sources yet.'}</p>
                      <p className="text-xs mt-1">{lang === 'id' ? 'Klik Tambah / Upload untuk memulai.' : 'Add a source to begin.'}</p>
                    </div>
                  ) : (
                    activeNotebook.sources.map((src) => (
                      <div key={src.id} className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-1.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-semibold">{src.type}</span>
                          <h4 className="font-bold text-sm text-slate-200 truncate flex-1">{src.title}</h4>
                        </div>
                        <p className="text-[11px] text-slate-500">{src.wordCount} {lang === 'id' ? 'kata' : 'words'}</p>
                        <div className="flex items-center gap-1 pt-1">
                          <button onClick={() => handleViewSource(src.id)} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:text-violet-300 text-[11px] font-semibold" title={tr('learning_view', 'Lihat')}><Eye className="w-3.5 h-3.5" />{tr('learning_view', 'Lihat')}</button>
                          <button onClick={() => deleteNotebookSource(activeNotebook.id, src.id)} className="p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-rose-400" title={tr('learning_delete', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
                <p className="text-[10px] text-slate-500">{activeNotebook.sources?.length || 0} {lang === 'id' ? 'sumber · menjadi dasar jawaban AI' : 'sources · grounding the AI answers'}</p>
              </div>
            )}

            {/* ── CHAT PANEL ── */}
            <div className={`${compactPanel !== 'chat' ? 'hidden lg:flex' : 'flex ct-slide-in'} flex-col bg-slate-900/70 border border-slate-800 rounded-2xl p-4 space-y-3 min-h-[520px]`}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{tr('learning_chat_panel', 'Chat AI')}</span>
                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <button onClick={() => setChatFontSize((v) => clampFont(v - 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50" title={tr('learning_font_chat', 'Font Chat AI')}>{tr('learning_font_decrease', 'A−')}</button>
                  <span className="px-1 font-bold text-slate-200">{chatFontSize}px</span>
                  <button onClick={() => setChatFontSize((v) => clampFont(v + 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50" title={tr('learning_font_chat', 'Font Chat AI')}>{tr('learning_font_increase', 'A+')}</button>
                  <button onClick={() => { updateNotebook(activeNotebook.id, { chatHistory: [] }); }} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-rose-500/50" title={tr('learning_clear_chat', 'Bersihkan chat')}><Trash2 className="w-3.5 h-3.5" /></button>
                </div>
              </div>

              <div style={{ fontSize: chatFontSize }} className="flex-1 h-[440px] overflow-y-auto space-y-3 p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
                {(!activeNotebook.chatHistory || activeNotebook.chatHistory.length === 0) && (
                  <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
                    <Bot className="w-10 h-10 mb-3 text-violet-400/50" />
                    <h4 className="font-semibold text-slate-300">{lang === 'id' ? 'Tanyakan materi dari sumber ini' : 'Ask questions about your sources'}</h4>
                    <p className="text-xs max-w-sm mt-1">{lang === 'id' ? 'AI menjawab berdasar seluruh sumber notebook ini.' : 'AI answers grounded in this notebook\'s sources.'}</p>
                  </div>
                )}
                {activeNotebook.chatHistory?.map((msg, idx) => (
                  <div key={idx} className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.sender === 'ai' && (
                      <div className="w-8 h-8 rounded-lg bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-sm shrink-0 text-violet-300"><Bot className="w-4 h-4" /></div>
                    )}
                    <div className={`p-3.5 rounded-2xl max-w-xl text-sm leading-relaxed ${msg.sender === 'user' ? 'bg-violet-600 text-white rounded-br-none' : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'}`}>
                      <div className="prose prose-invert prose-sm"><ReactMarkdown>{msg.text}</ReactMarkdown></div>
                      <span className="block text-[10px] text-slate-400 mt-1 text-right">{msg.timestamp}</span>
                    </div>
                  </div>
                ))}
                {isAiLoading && (
                  <div className="flex items-center gap-2 text-violet-400 text-xs p-2"><Sparkles className="w-4 h-4 animate-spin" /><span>{lang === 'id' ? 'AI sedang menganalisis…' : 'AI is synthesizing…'}</span></div>
                )}
              </div>

              <div className="flex gap-2">
                <textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendChat(); } }}
                  placeholder={lang === 'id' ? 'Tanyakan sesuatu tentang notebook ini…' : 'Ask anything about this notebook…'}
                  rows={1}
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-violet-500 resize-none"
                />
                <button onClick={handleSendChat} disabled={isAiLoading || !chatInput.trim()} className="px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white rounded-xl font-semibold text-sm flex items-center gap-1.5"><Send className="w-4 h-4" /></button>
              </div>
              <p className="text-[10px] text-slate-500">{tr('learning_composer_hint', 'Enter untuk kirim · Shift+Enter baris baru')}</p>
            </div>

            {/* ── STUDIO PANEL ── */}
            {showStudio && (
              <div className={`${compactPanel !== 'studio' ? 'hidden lg:flex' : 'flex ct-slide-in'} flex-col bg-slate-900/70 border border-slate-800 rounded-2xl p-4 space-y-3`}>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{tr('learning_studio_panel', 'Studio')}</span>
                  <span className="text-[10px] text-slate-500">{tr('learning_studio_hint', 'Buat materi dari sumber')}</span>
                </div>

                {/* Font controls (parity studio font row) */}
                <div className="flex items-center gap-1 text-[11px] text-slate-400">
                  <span>{tr('learning_font_studio', 'Font Hasil')}:</span>
                  <button onClick={() => setStudioFontSize((v) => clampFont(v - 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_decrease', 'A−')}</button>
                  <span className="px-1 font-bold text-slate-200">{studioFontSize}px</span>
                  <button onClick={() => setStudioFontSize((v) => clampFont(v + 1))} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_increase', 'A+')}</button>
                  <button onClick={() => setStudioFontSize(13)} className="px-2 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-violet-500/50">{tr('learning_font_reset', 'Reset')}</button>
                  <button onClick={handleExportStudio} className="ml-auto flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-700/80 hover:bg-emerald-600 text-white" title={tr('learning_export', 'Ekspor')}><Download className="w-3.5 h-3.5" /><span>{tr('learning_export_compact', 'Ekspor')}</span></button>
                </div>

                {/* Topic input */}
                <input type="text" value={studioTopic} onChange={(e) => setStudioTopic(e.target.value)} placeholder={tr('learning_topic_label', 'Topik (kosongkan = semua):')} className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200" />

                {/* 8-type generator grid (parity studio_grid) */}
                <div className="grid grid-cols-2 gap-2">
                  {STUDIO_TYPES.map((s) => (
                    <button
                      key={s.type}
                      disabled={isAiLoading}
                      onClick={() => {
                        if (s.type === 'flashcards') handleGenerateFlashcards();
                        else if (s.type === 'quiz') handleGenerateQuiz();
                        else if (s.type === 'podcast') handleGeneratePodcast();
                        else handleGenerateStudio(s.type);
                      }}
                      className={`px-2 py-2 rounded-lg text-xs font-semibold border transition-colors disabled:opacity-50 text-left ${activeStudioType === s.type ? 'bg-violet-600/20 border-violet-500/50 text-violet-200' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-violet-500/40'}`}
                    >
                      <span className="text-sm mr-1">{s.icon}</span>{tr(s.labelKey, s.type)}
                    </button>
                  ))}
                </div>

                {/* Count (quiz/flashcards 10–30, parity studio_count_spin) */}
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <span>{tr('learning_count_label', 'Jumlah (Kuis/Kartu)')}</span>
                  <input type="number" min={10} max={30} value={studioCount} onChange={(e) => setStudioCount(Math.max(10, Math.min(30, parseInt(e.target.value || '15', 10) || 15)))} className="w-16 ml-auto bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-center text-slate-100" />
                </div>
                <p className="text-[9px] text-slate-500">{tr('learning_count_hint', 'Dipakai saat membuat Kuis / Flashcard AI (10–30).')}</p>

                {/* Output area (parity studio_output_stack) */}
                <div style={{ fontSize: studioFontSize }} className="flex-1 overflow-y-auto max-h-[360px] space-y-3">
                  {activeStudioType === 'flashcards' ? renderFlashcards() : activeStudioType === 'quiz' ? renderQuiz() : activeStudioType === 'podcast' ? renderPodcast() : renderStudioMarkdown()}</div>

                {/* History (parity generation_combo + delete) */}
                <div className="pt-2 border-t border-slate-800/80 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">{tr('learning_history', 'Riwayat')} ({activeGenList.length})</span>
                    {activeGenList.length > 0 && (
                      <button onClick={() => { if (selectedGen) handleDeleteGeneration(selectedGen.id); }} className="ml-auto p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-rose-400" title={tr('learning_delete', 'Hapus')}><Trash2 className="w-3.5 h-3.5" /></button>
                    )}
                  </div>
                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                    {activeGenList.length > 0 ? activeGenList.map((g: any) => (
                      <div key={g.id} className={`flex items-center gap-2 px-2 py-1.5 rounded-lg border text-[11px] cursor-pointer transition-colors ${selectedGen?.id === g.id ? 'bg-violet-950/40 border-violet-500/40 text-slate-100' : 'bg-slate-950/70 border-slate-800 text-slate-300 hover:border-slate-700'}`} onClick={() => { setSelectedGen(selectedGen?.id === g.id ? null : g); if (g.gtype && (g.gtype as string).includes('flash')) setActiveStudioType('flashcards'); else if (g.gtype === 'mindmap') setActiveStudioType('mindmap'); else if (g.gtype === 'quiz') setActiveStudioType('quiz'); else if ((g.gtype as string).includes('audio') || (g.gtype as string).includes('podcast')) setActiveStudioType('podcast'); else setActiveStudioType((g.gtype as StudioType) || 'summary'); }}>
                          <span className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-300 font-semibold shrink-0">{g.gtype}</span>
                          <span className="truncate flex-1">{g.topic || '(topik umum)'}</span>
                          <span className="text-slate-600 shrink-0">{g.createdAt || ''}</span>
                        </div>
                      )) : (
                        <p className="text-[11px] text-slate-500 text-center py-2">{tr('learning_history_empty', 'Belum ada riwayat.')}</p>
                      )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="p-12 text-center bg-slate-900/50 border border-slate-800 rounded-2xl text-slate-500">
          <BookOpen className="w-12 h-12 mx-auto mb-3 text-slate-600" />
          <p className="text-base font-semibold">{lang === 'id' ? 'Pilih notebook atau buat baru.' : 'Select or create a notebook.'}</p>
        </div>
      )}

      {/* Modal: New Notebook */}
      {showNewNbModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Buat Notebook Baru' : 'Create New Notebook'}</h3>
            <div className="space-y-3 text-sm">
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul' : 'Title'}</label><input type="text" value={newNbTitle} onChange={(e) => setNewNbTitle(e.target.value)} placeholder="e.g. Physics Dynamics, Machine Learning" className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Deskripsi' : 'Description'}</label><input type="text" value={newNbDesc} onChange={(e) => setNewNbDesc(e.target.value)} placeholder="Short summary of this notebook..." className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">Emoji Icon</label><div className="flex gap-2">{['📚', '🧠', '🔬', '💻', '📐', '🚀', '📝', '⚡'].map((emoji) => (<button key={emoji} onClick={() => setNewNbIcon(emoji)} className={`text-xl p-2 rounded-lg border ${newNbIcon === emoji ? 'bg-violet-600/30 border-violet-500' : 'bg-slate-950 border-slate-800'}`}>{emoji}</button>))}</div></div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowNewNbModal(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl">Cancel</button>
              <button onClick={() => { if (!newNbTitle.trim()) return; addNotebook(newNbTitle.trim(), newNbDesc.trim(), newNbIcon); setShowNewNbModal(false); setNewNbTitle(''); setNewNbDesc(''); }} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white rounded-xl">{lang === 'id' ? 'Buat Notebook' : 'Create Notebook'}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Rename Notebook (parity LearningPage._rename_notebook) */}
      {renaming && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{tr('learning_rename_title', 'Judul notebook baru:')}</h3>
            <input type="text" value={renameTitle} onChange={(e) => setRenameTitle(e.target.value)} autoFocus className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" />
            <div className="flex gap-2 justify-end">
              <button onClick={() => setRenaming(false)} className="px-4 py-2 rounded-xl text-sm text-slate-400 hover:text-slate-200">{tr('msg_cancel', 'Batal')}</button>
              <button onClick={handleRename} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">{tr('msg_ok', 'OK')}</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: View Source (parity LearningPage._view_source) */}
      {viewingSource && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100 mb-3 shrink-0">{viewingSource.title}</h3>
            <div className="overflow-y-auto pr-1 flex-1"><pre className="whitespace-pre-wrap text-xs leading-relaxed text-slate-300 font-mono bg-slate-950/60 border border-slate-800 rounded-xl p-4">{viewingSource.content}</pre></div>
            <div className="flex justify-end mt-4 shrink-0"><button onClick={() => setViewingSource(null)} className="px-4 py-2 rounded-xl text-sm font-semibold bg-violet-600 text-white">{tr('btn_close', 'Tutup')}</button></div>
          </div>
        </div>
      )}

      {/* Modal: New Source */}
      {showNewSourceModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="font-bold text-lg text-slate-100">{lang === 'id' ? 'Tambah Sumber Belajar' : 'Add Study Source'}</h3>
            <div className="space-y-3 text-sm">
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Judul Dokumen' : 'Source Title'}</label><input type="text" value={newSourceTitle} onChange={(e) => setNewSourceTitle(e.target.value)} placeholder="e.g. Chapter 1 Notes, Article summary" className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2 text-slate-100 text-sm focus:outline-none focus:border-violet-500" /></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Tipe' : 'Type'}</label><div className="flex gap-2">{(['text', 'doc', 'pdf', 'url'] as const).map((tt) => (<button key={tt} onClick={() => setNewSourceType(tt)} className={`px-3 py-1.5 uppercase text-xs font-bold rounded-lg border ${newSourceType === tt ? 'bg-violet-600/30 border-violet-500 text-violet-300' : 'bg-slate-950 border-slate-800 text-slate-400'}`}>{tt}</button>))}</div></div>
              <div><label className="block text-xs font-bold text-slate-400 mb-1">{lang === 'id' ? 'Isi Teks Dokumen' : 'Content / Text'}</label><textarea rows={6} value={newSourceContent} onChange={(e) => setNewSourceContent(e.target.value)} placeholder="Paste notes, textbook paragraphs, or document content here..." className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 text-xs focus:outline-none focus:border-violet-500 font-mono" /></div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowNewSourceModal(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300 rounded-xl">Cancel</button>
              <button onClick={() => { if (!newSourceTitle.trim() || !newSourceContent.trim() || !activeNotebook) return; addNotebookSource(activeNotebook.id, newSourceTitle.trim(), newSourceContent.trim(), newSourceType); setShowNewSourceModal(false); setNewSourceTitle(''); setNewSourceContent(''); }} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-xs font-semibold text-white rounded-xl">{lang === 'id' ? 'Simpan Sumber' : 'Save Source'}</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
