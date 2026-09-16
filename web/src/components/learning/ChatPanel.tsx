/**
 * ChatPanel.tsx — panel Chat AI (kolom tengah, A07).
 *
 * Isi: header (judul + kontrol font + bersihkan chat) · daftar balon pesan
 * (pengguna kanan / AI kiri) · **kartu saran** saat chat masih kosong (ala NotebookLM,
 * memakai 4 key `learning_suggestion_q1..q4`) · composer (Enter kirim, Shift+Enter baris
 * baru) + hint. Balon AI memakai permukaan CraftLife — bukan gaya Google.
 */
import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Bot, Send, Sparkles, Trash2, User, BookMarked } from 'lucide-react';
import { Citation, citationMarkdownComponents, linkifyCitations } from './CitationChip';

export interface ChatMessage {
  sender: 'user' | 'ai';
  text: string;
  timestamp?: string;
  /** A08: sitasi sumber yang dipakai jawaban ini (chip `[1]`, `[2]`, …). */
  citations?: Citation[];
}

export interface ChatPanelProps {
  messages: ChatMessage[];
  input: string;
  onInput: (v: string) => void;
  onSend: () => void;
  loading?: boolean;
  font: number;
  onFont: (delta: number) => void;
  onClear: () => void;
  /** Klik kartu saran → teks saran dikirim sebagai pertanyaan. */
  onSuggestion: (text: string) => void;
  /** A08: grounding — berapa sumber dipakai dari total, dan jalan pintas ke panel Sumber. */
  sourcesUsed?: number;
  sourcesTotal?: number;
  onOpenSources?: () => void;
  /** A08: klik chip sitasi → buka isi sumber penuh. */
  onOpenSource?: (sourceId: string) => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

const SUGGESTIONS: { key: string; fallback: string }[] = [
  { key: 'learning_suggestion_q1', fallback: 'Jelaskan konsep utama dari sumber ini' },
  { key: 'learning_suggestion_q2', fallback: 'Buat rangkuman singkat untuk belajar cepat' },
  { key: 'learning_suggestion_q3', fallback: 'Apa yang sering ditanyakan dari materi ini?' },
  { key: 'learning_suggestion_q4', fallback: 'Buatkan kuis dari materi ini' },
];

const ChatPanel: React.FC<ChatPanelProps> = ({
  messages, input, onInput, onSend, loading, font, onFont, onClear, onSuggestion,
  sourcesUsed = 0, sourcesTotal = 0, onOpenSources, onOpenSource, tr,
}) => {
  const listRef = useRef<HTMLDivElement | null>(null);
  const markdownRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll ke pesan terbaru saat jumlah pesan / status loading berubah.
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length, loading]);

  const empty = messages.length === 0;

  return (
    <section className="ct-nlm-panel flex flex-col min-h-[460px] lg:min-h-0 lg:h-full p-3 gap-2.5" aria-label={tr('learning_view_chat', {}, 'Chat')}>
      <header className="flex items-center gap-2">
        <Bot className="w-4 h-4 text-[var(--ct-light)]" />
        <h3 className="text-[12px] font-black uppercase tracking-wider text-slate-300">
          {tr('learning_view_chat', {}, 'Chat')}
        </h3>
        {/* A08: chip grounding — berapa sumber yang dipakai untuk menjawab. */}
        <button
          type="button"
          onClick={onOpenSources}
          className={`ct-nlm-chip hidden sm:inline-flex ${sourcesUsed > 0 ? 'is-ok' : 'is-muted'} ${onOpenSources ? 'hover:brightness-125' : ''}`}
          title={tr('learning_grounding_on', {}, 'Grounding aktif')}
        >
          <BookMarked className="w-3 h-3" />
          {tr('learning_sources_selected_count', { n: sourcesUsed, total: sourcesTotal },
            '{n} dari {total} sumber dipakai')}
        </button>
        <div className="ml-auto flex items-center gap-1 text-[11px] text-slate-400">
          <button onClick={() => onFont(-1)} className="ct-btn ct-btn-secondary ct-btn-sm" title={tr('learning_font_chat', {}, 'Font Chat AI')}>
            {tr('learning_font_decrease', {}, 'A−')}
          </button>
          <span className="px-1 font-bold text-slate-200 ct-nlm-num">{font}px</span>
          <button onClick={() => onFont(1)} className="ct-btn ct-btn-secondary ct-btn-sm" title={tr('learning_font_chat', {}, 'Font Chat AI')}>
            {tr('learning_font_increase', {}, 'A+')}
          </button>
          <button onClick={onClear} className="ct-btn ct-btn-secondary ct-btn-sm" title={tr('learning_clear_chat', {}, 'Bersihkan chat')}>
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      <div
        ref={listRef}
        style={{ fontSize: font }}
        className="ct-nlm-scroll flex-1 overflow-y-auto space-y-3 p-3 bg-[color-mix(in_srgb,var(--ct-bg)_45%,transparent)] rounded-xl border border-[var(--ct-nlm-line-soft)] lg:min-h-0 min-h-[300px]"
      >
        {empty && !loading && (
          <div className="h-full flex flex-col items-center justify-center text-center p-4">
            <Bot className="w-9 h-9 mb-2 text-[var(--ct-light)]/70" />
            <h4 className="font-bold text-[13px] text-slate-200">
              {tr('ask_questions_about_your_sources', {}, 'Tanyakan apa pun tentang sumbermu')}
            </h4>
            <p className="text-[11px] text-slate-500 max-w-sm mt-1">
              {tr('ai_answers_grounded_in_this_notebook_s_sources', {}, 'Jawaban AI bersandar pada sumber notebook ini.')}
            </p>
            {/* Kartu saran ala NotebookLM */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-4 w-full max-w-xl">
              {SUGGESTIONS.map((s) => (
                <button key={s.key} onClick={() => onSuggestion(tr(s.key, {}, s.fallback))} className="ct-nlm-suggestion">
                  <span className="flex items-start gap-2">
                    <Sparkles className="w-3.5 h-3.5 mt-0.5 text-[var(--ct-light)] shrink-0" />
                    <span>{tr(s.key, {}, s.fallback)}</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-2.5 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.sender === 'ai' && (
              <div className="ct-nlm-avatar shrink-0" aria-hidden><Bot className="w-3.5 h-3.5" /></div>
            )}
            <div className={`px-3.5 py-2.5 rounded-2xl max-w-[85%] sm:max-w-xl text-[13px] leading-relaxed ${msg.sender === 'user' ? 'ct-nlm-bubble-user' : 'ct-nlm-bubble-ai text-slate-200'}`}>
              {/* Markdown tetap dirender seperti sebelumnya (ReactMarkdown + prose) supaya
                  format jawaban AI tidak berubah — hanya tampilan balonnya yang baru.
                  A08: penanda `[S1]` diubah menjadi chip sitasi yang bisa diklik. */}
              <div
                ref={idx === messages.length - 1 && msg.sender === 'ai' ? markdownRef : undefined}
                data-chat-msg={idx}
                className="prose prose-invert prose-sm max-w-none [&_p]:my-1 [&_ul]:my-1 [&_ol]:my-1"
              >
                <ReactMarkdown
                  components={msg.sender === 'ai'
                    ? citationMarkdownComponents(msg.citations || [], onOpenSource, tr)
                    : undefined}
                >
                  {msg.sender === 'ai' ? linkifyCitations(msg.text, msg.citations) : msg.text}
                </ReactMarkdown>
              </div>
              {/* A08: bila jawaban memakai sumber, tampilkan ringkasannya di bawah balon. */}
              {msg.sender === 'ai' && (msg.citations?.length || 0) > 0 && (
                <span className="flex flex-wrap items-center gap-1 mt-1.5 text-[10px] text-slate-400">
                  <BookMarked className="w-3 h-3 text-[var(--ct-light)]" />
                  {tr('learning_citations', {}, 'Sitasi')}:
                  {(msg.citations || []).map((c) => (
                    <button
                      key={`${c.index}-${c.sourceId}`}
                      type="button"
                      onClick={() => c.sourceId && onOpenSource?.(String(c.sourceId))}
                      className="px-1.5 py-0.5 rounded-md bg-slate-800/80 border border-slate-700 hover:border-[var(--ct-primary)] text-slate-300 truncate max-w-[10rem]"
                      title={c.snippet || c.title}
                    >
                      {c.index}. {c.title}
                    </button>
                  ))}
                </span>
              )}
              {msg.timestamp && (
                <span className={`block text-[10px] mt-1 text-right ${msg.sender === 'user' ? 'text-white/70' : 'text-slate-500'}`}>
                  {msg.timestamp}
                </span>
              )}
            </div>
            {msg.sender === 'user' && (
              <div className="w-8 h-8 rounded-xl bg-slate-800/80 border border-slate-700 flex items-center justify-center shrink-0 text-slate-300" aria-hidden>
                <User className="w-3.5 h-3.5" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 text-[var(--ct-light)] text-[11px] p-2">
            <Sparkles className="w-4 h-4 animate-spin" />
            <span>{tr('ai_is_synthesizing', {}, 'AI sedang menyusun…')}</span>
          </div>
        )}
      </div>

      <div className="flex gap-2 items-end">
        <textarea
          value={input}
          onChange={(e) => onInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              onSend();
            }
          }}
          placeholder={tr('ask_anything_about_this_notebook', {}, 'Tanyakan apa pun tentang notebook ini…')}
          rows={1}
          className="flex-1 bg-slate-950/70 border border-slate-800 rounded-xl px-3.5 py-2.5 text-[13px] text-slate-100 placeholder-slate-500 focus:outline-none focus:border-[var(--ct-primary)] resize-none"
        />
        <button
          onClick={onSend}
          disabled={loading || !input.trim()}
          className="px-3.5 py-2.5 bg-[var(--ct-primary)] hover:brightness-110 disabled:opacity-50 text-white rounded-xl font-bold text-[13px] flex items-center gap-1.5"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
      <p className="text-[10px] text-slate-500">
        {tr('learning_composer_hint', {}, 'Enter untuk kirim · Shift+Enter baris baru')}
      </p>
    </section>
  );
};

export default ChatPanel;
