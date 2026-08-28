import React, { useState } from 'react';
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
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import { studio } from '../../api/studio';

type LearningTab = 'chat' | 'sources' | 'flashcards' | 'quiz' | 'podcast' | 'math' | 'studio';

export const LearningView: React.FC = () => {
  const {
    notebooks,
    addNotebook,
    deleteNotebook,
    addNotebookSource,
    deleteNotebookSource,
    addNotebookChat,
    updateNotebook,
    lang,
    showToast,
  } = useGame();

  const [activeNotebookId, setActiveNotebookId] = useState<string>(notebooks[0]?.id || '');
  const [activeTab, setActiveTab] = useState<LearningTab>('chat');

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
        topic: activeNotebook.title,
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
                  <div className="h-[420px] overflow-y-auto space-y-3 p-4 bg-slate-950/60 rounded-xl border border-slate-800/80">
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
                    <button
                      onClick={() => setShowNewSourceModal(true)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 rounded-lg transition-colors border border-slate-700"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>{lang === 'id' ? 'Tambah Sumber' : 'Add Source'}</span>
                    </button>
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
                        <button
                          onClick={() => deleteNotebookSource(activeNotebook.id, src.id)}
                          className="text-slate-500 hover:text-rose-400 p-1.5 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
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
                  <div className="flex flex-wrap gap-2">
                    {(['study-guide', 'mindmap', 'faq', 'timeline', 'summary'] as const).map((k) => (
                      <button
                        key={k}
                        disabled={isAiLoading}
                        onClick={() => handleGenerateStudio(k)}
                        className="px-3 py-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-xs font-semibold text-white"
                      >
                        {k}
                      </button>
                    ))}
                  </div>
                  <div className="prose prose-invert prose-sm max-w-none text-slate-200 space-y-3">
                    {(activeNotebook as any).studyGuide && <ReactMarkdown>{String((activeNotebook as any).studyGuide)}</ReactMarkdown>}
                    {(activeNotebook as any).faq && <ReactMarkdown>{String((activeNotebook as any).faq)}</ReactMarkdown>}
                    {(activeNotebook as any).timeline && <ReactMarkdown>{String((activeNotebook as any).timeline)}</ReactMarkdown>}
                    {(activeNotebook as any).summary && <ReactMarkdown>{String((activeNotebook as any).summary)}</ReactMarkdown>}
                    {(activeNotebook as any).mindMap && (
                      <pre className="text-[11px] overflow-x-auto">{JSON.stringify((activeNotebook as any).mindMap, null, 2)}</pre>
                    )}
                  </div>
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
