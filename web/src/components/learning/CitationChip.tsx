/**
 * CitationChip.tsx — chip sitasi sumber di jawaban AI (A08).
 *
 * Jawaban AI memakai penanda `[S1]`, `[S2]`; ChatPanel mengubahnya menjadi tautan
 * `[1](#cite-1)` supaya Markdown tetap utuh, lalu komponen `a` di-Override menjadi
 * chip ini. Klik chip → popover berisi judul sumber + kalimat yang dikutip +
 * tombol **Buka sumber** (membuka isi penuh lewat endpoint `source-content`).
 */
import React, { useEffect, useRef, useState } from 'react';
import { FileText, ExternalLink } from 'lucide-react';

export interface Citation {
  index: number;
  sourceId: string;
  title: string;
  marker: string;
  snippet: string;
}

export interface CitationChipProps {
  citation: Citation;
  onOpenSource?: (sourceId: string) => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

/** Ubah penanda `[S1]` menjadi tautan markdown `[1](#cite-1)` — hanya bila sitasinya dikenal. */
export function linkifyCitations(text: string, citations?: Citation[]): string {
  if (!text || !citations || !citations.length) return text;
  return text.replace(/\[S(\d{1,2})\]/g, (whole, num) => {
    const found = citations.find((c) => Number(c.index) === Number(num));
    return found ? `[${num}](#cite-${found.index})` : whole;
  });
}

/**
 * Pabrik `components` untuk `<ReactMarkdown>`: tautan `#cite-N` → CitationChip,
 * tautan biasa tetap tautan biasa. Dipakai ChatPanel supaya format jawaban
 * (bullet, bold, heading) tidak berubah sama sekali.
 */
export function citationMarkdownComponents(
  citations: Citation[],
  onOpenSource: ((sourceId: string) => void) | undefined,
  tr: CitationChipProps['tr'],
) {
  return {
    a: ({ href, children, ...rest }: any) => {
      const match = /^#cite-(\d+)$/.exec(String(href || ''));
      if (!match) {
        return (
          <a href={href} target="_blank" rel="noreferrer" className="text-[var(--ct-light)] underline" {...rest}>
            {children}
          </a>
        );
      }
      const citation = citations.find((c) => Number(c.index) === Number(match[1]));
      if (!citation) return <span>{children}</span>;
      return <CitationChip citation={citation} onOpenSource={onOpenSource} tr={tr} />;
    },
  };
}

const CitationChip: React.FC<CitationChipProps> = ({ citation, onOpenSource, tr }) => {
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLSpanElement | null>(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDocClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  return (
    <span ref={boxRef} className="relative inline-block align-super">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mx-0.5 px-1.5 py-0.5 rounded-md text-[10px] font-black bg-[color-mix(in_srgb,var(--ct-primary)_22%,transparent)] text-[var(--ct-light)] border border-[color-mix(in_srgb,var(--ct-primary)_45%,transparent)] hover:brightness-125 align-super"
        title={citation.title || tr('learning_citation_source_n', { n: citation.index }, 'Sumber {n}')}
        aria-label={tr('learning_citation_source_n', { n: citation.index }, 'Sumber {n}') + `: ${citation.title}`}
      >
        {citation.index}
      </button>
      {open && (
        <span className="absolute z-30 left-0 top-6 w-64 p-2.5 rounded-xl bg-slate-900 border border-slate-700 shadow-xl text-left block">
          <span className="flex items-start gap-1.5 mb-1">
            <FileText className="w-3.5 h-3.5 text-[var(--ct-light)] mt-0.5 shrink-0" />
            <span className="text-[11px] font-bold text-slate-100 leading-snug">
              {citation.title || tr('learning_citation_source_n', { n: citation.index }, 'Sumber {n}')}
            </span>
          </span>
          {citation.snippet && (
            <span className="block text-[10px] text-slate-400 leading-relaxed mb-2">{citation.snippet}</span>
          )}
          {onOpenSource && citation.sourceId && (
            <button
              type="button"
              onClick={() => { setOpen(false); onOpenSource(String(citation.sourceId)); }}
              className="flex items-center gap-1 text-[10px] font-bold text-[var(--ct-light)] hover:brightness-125"
            >
              <ExternalLink className="w-3 h-3" />
              {tr('learning_open_source', {}, 'Buka sumber')}
            </button>
          )}
        </span>
      )}
    </span>
  );
};

export default CitationChip;
