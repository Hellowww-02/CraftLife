/**
 * StudioNewViews.tsx — tampilan interaktif 3 tipe Studio C05 (JSON terstruktur).
 *
 * DataTableView (tabel), InfographicView (SVG), SlideDeckView (navigasi slide).
 * Parser diekspor agar dipakai ulang pratinjau artefak + uji. Semua defensif:
 * bentuk tak dikenal → tampilkan mentah; kosong → pesan isi-kosong.
 */
import React, { useState } from 'react';

export interface DataTableData { title: string; columns: string[]; rows: string[][]; }
export interface InfographicData {
  title: string; subtitle: string;
  stats: { value: string; label: string }[];
  points: { heading: string; text: string }[];
}
export interface SlideDeckData { title: string; slides: { title: string; bullets: string[]; notes?: string }[]; }

type Tr = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

const stripFence = (t: string) => String(t || '').replace(/^```(?:json)?/i, '').replace(/```$/, '').trim();

/** Terima slot objek / string mentah / bungkus {raw} → objek atau null. */
function asObj(raw: unknown): any {
  let d: any = raw;
  if (typeof d === 'string') {
    try { d = JSON.parse(stripFence(d)); } catch { return null; }
  }
  if (d && typeof d === 'object' && typeof d.raw === 'string' && !d.columns && !d.points && !d.slides) {
    try { d = JSON.parse(stripFence(d.raw)); } catch { return null; }
  }
  return d && typeof d === 'object' ? d : null;
}

function rawText(raw: unknown): string {
  if (typeof raw === 'string') return raw.trim();
  const r = (raw as any)?.raw;
  return typeof r === 'string' ? r.trim() : '';
}

export function parseDataTable(raw: unknown): DataTableData | null {
  const d = asObj(raw);
  if (!d) return null;
  const columns = ((d.columns || []) as any[]).map((c) => String(c ?? '')).slice(0, 8);
  if (!columns.length) return null;
  const rows = ((d.rows || []) as any[]).slice(0, 30).map((r) => {
    const cells = (Array.isArray(r) ? r : [r]).map((c) => String(c ?? ''));
    while (cells.length < columns.length) cells.push('');
    return cells.slice(0, columns.length);
  });
  return { title: String(d.title || ''), columns, rows };
}

export function parseInfographic(raw: unknown): InfographicData | null {
  const d = asObj(raw);
  if (!d || !Array.isArray(d.points)) return null;
  const points = (d.points as any[]).filter((p) => p && typeof p === 'object').slice(0, 15).map((p) => ({
    heading: String(p.heading || ''), text: String(p.text || ''),
  }));
  if (!points.length) return null;
  const stats = ((d.stats || []) as any[]).filter((s) => s && typeof s === 'object').slice(0, 6).map((s) => ({
    value: String(s.value || ''), label: String(s.label || ''),
  }));
  return { title: String(d.title || ''), subtitle: String(d.subtitle || ''), stats, points };
}

export function parseSlideDeck(raw: unknown): SlideDeckData | null {
  const d = asObj(raw);
  if (!d || !Array.isArray(d.slides)) return null;
  const slides = (d.slides as any[]).filter((s) => s && typeof s === 'object').slice(0, 25).map((s) => {
    const slide: { title: string; bullets: string[]; notes?: string } = {
      title: String(s.title || ''),
      bullets: ((s.bullets || []) as any[]).map((b) => String(b ?? '')).slice(0, 8),
    };
    // H01/H03: speaker notes opsional dari prompt baru (deck lama tetap valid).
    if (s.notes) slide.notes = String(s.notes).slice(0, 1000);
    return slide;
  });
  if (!slides.length) return null;
  return { title: String(d.title || ''), slides };
}

const EmptyOrRaw: React.FC<{ raw: unknown; tr: Tr }> = ({ raw, tr }) => {
  const txt = rawText(raw);
  if (txt) {
    return <pre className="text-[10px] text-slate-300 whitespace-pre-wrap bg-slate-950/60 border border-slate-800 rounded-xl p-2.5 max-h-52 overflow-y-auto">{txt}</pre>;
  }
  return <p className="text-[11px] text-slate-500">{tr('learning_artifact_empty_content', {}, '(isi kosong)')}</p>;
};

export const DataTableView: React.FC<{ data: unknown; tr: Tr }> = ({ data, tr }) => {
  const t = parseDataTable(data);
  if (!t) return <EmptyOrRaw raw={data} tr={tr} />;
  return (
    <div className="space-y-1.5">
      {t.title && <p className="text-[11px] font-bold text-slate-100">{t.title}</p>}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-[11px] text-slate-200">
          <thead>
            <tr>{t.columns.map((c, i) => (
              <th key={i} className="text-left font-bold px-2 py-1.5 bg-slate-900 text-violet-200 border-b border-slate-800 whitespace-nowrap">{c}</th>
            ))}</tr>
          </thead>
          <tbody>
            {t.rows.map((r, i) => (
              <tr key={i} className={i % 2 ? 'bg-slate-950/40' : ''}>
                {r.map((c, j) => (<td key={j} className="px-2 py-1 border-b border-slate-800/60 align-top">{c}</td>))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/** Potong teks jadi baris-baris ≤max karakter (SVG tidak wrap otomatis). */
function wrapLines(text: string, max = 46): string[] {
  const words = String(text || '').split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let cur = '';
  for (const w of words) {
    const next = cur ? `${cur} ${w}` : w;
    if (next.length > max && cur) { lines.push(cur); cur = w; }
    else cur = next;
  }
  if (cur) lines.push(cur);
  return lines.length ? lines : [''];
}

export const InfographicView: React.FC<{ data: unknown; tr: Tr }> = ({ data, tr }) => {
  const info = parseInfographic(data);
  if (!info) return <EmptyOrRaw raw={data} tr={tr} />;
  const W = 560;
  const perRow = Math.min(4, Math.max(1, info.stats.length));
  const statRows = Math.ceil(info.stats.length / perRow);
  const boxW = (W - 40 - (perRow - 1) * 10) / perRow;
  const statsH = info.stats.length ? statRows * 64 + 8 : 0;
  const blocks = info.points.map((p) => wrapLines(p.text, 52));
  const pointsH = blocks.reduce((sum, lines) => sum + 26 + lines.length * 14 + 8, 0);
  const H = 66 + statsH + pointsH + 16;
  let py = 66 + statsH;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-xl border border-slate-800 bg-slate-950" role="img">
      <text x="20" y="28" fontSize="17" fontWeight="bold" fill="#e2e8f0">{info.title}</text>
      {info.subtitle && <text x="20" y="48" fontSize="11" fill="#94a3b8">{info.subtitle}</text>}
      {info.stats.map((s, i) => {
        const col = i % perRow;
        const row = Math.floor(i / perRow);
        const x = 20 + col * (boxW + 10);
        const y = 60 + row * 64;
        const labelLines = wrapLines(s.label, 18).slice(0, 2);
        return (
          <g key={i}>
            <rect x={x} y={y} width={boxW} height="56" rx="10" fill="#7c3aed22" stroke="#7c3aed66" />
            <text x={x + 10} y={y + 22} fontSize="15" fontWeight="bold" fill="#c4b5fd">{s.value}</text>
            {labelLines.map((ln, li) => (
              <text key={li} x={x + 10} y={y + 37 + li * 12} fontSize="9" fill="#94a3b8">{ln}</text>
            ))}
          </g>
        );
      })}
      {info.points.map((p, i) => {
        const y = py;
        py += 26 + blocks[i].length * 14 + 8;
        return (
          <g key={i}>
            <circle cx="31" cy={y + 6} r="11" fill="#7c3aed" />
            <text x="31" y={y + 10} fontSize="11" fontWeight="bold" fill="#fff" textAnchor="middle">{i + 1}</text>
            <text x="50" y={y + 10} fontSize="12" fontWeight="bold" fill="#f1f5f9">{p.heading}</text>
            {blocks[i].map((ln, li) => (
              <text key={li} x="50" y={y + 26 + li * 14} fontSize="10" fill="#cbd5e1">{ln}</text>
            ))}
          </g>
        );
      })}
    </svg>
  );
};

export const SlideDeckView: React.FC<{ data: unknown; tr: Tr }> = ({ data, tr }) => {
  const deck = parseSlideDeck(data);
  const [idx, setIdx] = useState(0);
  const [showNotes, setShowNotes] = useState(false);
  if (!deck) return <EmptyOrRaw raw={data} tr={tr} />;
  const total = deck.slides.length;
  const i = Math.max(0, Math.min(total - 1, idx));
  const s = deck.slides[i];
  const btn = 'px-3 py-1.5 rounded-lg text-[11px] font-bold border disabled:opacity-40 bg-slate-900 border-slate-700 text-slate-200 hover:border-violet-500/50';
  const anyNotes = deck.slides.some((sl) => sl.notes);
  return (
    // H03 (v1.7.0): viewer presentasi premium — panggung slide 16:10, titik
    // navigasi, keyboard ←/→, dan panel catatan presenter (field `notes` H01).
    <div
      className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-500/60"
      tabIndex={0}
      role="group"
      aria-label={tr('learning_slide_deck_aria', {}, 'Penampil presentasi')}
      onKeyDown={(e) => {
        if (e.key === 'ArrowRight' && i < total - 1) { e.preventDefault(); setIdx(i + 1); }
        else if (e.key === 'ArrowLeft' && i > 0) { e.preventDefault(); setIdx(i - 1); }
      }}
    >
      {deck.title && <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">{deck.title}</p>}

      {/* Panggung slide */}
      <div className="relative rounded-xl border border-slate-700/70 bg-gradient-to-br from-slate-900 via-slate-950 to-violet-950/40 p-5 min-h-[190px] flex flex-col overflow-hidden">
        <span className="absolute top-2.5 right-3 text-[9px] font-bold text-slate-500 ct-nlm-num">{tr('learning_slide_of', { n: i + 1, total }, `${i + 1} / ${total}`)}</span>
        <div className="h-0.5 w-10 rounded-full bg-violet-500/70 mb-3" aria-hidden="true" />
        <h4 className="font-bold text-base text-slate-100 break-words">{s.title || `${i + 1}`}</h4>
        {s.bullets.length > 0 && (
          <ul className="mt-3 space-y-1.5">
            {s.bullets.map((b, bi) => (
              <li key={bi} className="text-[11px] text-slate-300 flex gap-1.5">
                <span className="text-violet-300 shrink-0" aria-hidden="true">▸</span>
                <span className="break-words min-w-0">{b}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Titik navigasi slide */}
      {total > 1 && (
        <div className="flex items-center justify-center gap-1.5" role="tablist" aria-label={tr('learning_slide_of', { n: i + 1, total }, `${i + 1} / ${total}`)}>
          {deck.slides.map((_, di) => (
            <button
              key={di}
              type="button"
              role="tab"
              aria-selected={di === i}
              aria-label={tr('learning_slide_go', { n: di + 1 }, `Slide ${di + 1}`)}
              onClick={() => setIdx(di)}
              className={`h-1.5 rounded-full transition-all ${di === i ? 'w-5 bg-violet-400' : 'w-1.5 bg-slate-700 hover:bg-slate-600'}`}
            />
          ))}
        </div>
      )}

      {/* Catatan presenter (H01: field notes) */}
      {s.notes && showNotes && (
        <div className="rounded-lg border border-amber-500/25 bg-amber-500/5 p-2.5">
          <p className="text-[9px] uppercase tracking-wider font-bold text-amber-300/90 mb-1">{tr('learning_slide_notes', {}, 'Catatan presenter')}</p>
          <p className="text-[11px] text-slate-300 break-words">{s.notes}</p>
        </div>
      )}

      <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-800/70">
        <button disabled={i === 0} onClick={() => setIdx(i - 1)} className={btn}>‹ {tr('learning_slide_prev', {}, 'Sebelumnya')}</button>
        <div className="flex items-center gap-1.5">
          {anyNotes && (
            <button
              type="button"
              onClick={() => setShowNotes((v) => !v)}
              aria-pressed={showNotes}
              className={`px-2.5 py-1.5 rounded-lg text-[10px] font-bold border transition-colors ${showNotes ? 'bg-amber-500/20 border-amber-500/50 text-amber-200' : 'bg-slate-900 border-slate-700 text-slate-400 hover:border-amber-500/40'}`}
              title={tr('learning_slide_notes', {}, 'Catatan presenter')}
            >
              📝 {tr('learning_slide_notes_short', {}, 'Catatan')}
            </button>
          )}
        </div>
        <button disabled={i >= total - 1} onClick={() => setIdx(i + 1)} className={btn}>{tr('learning_slide_next', {}, 'Berikutnya')} ›</button>
      </div>
    </div>
  );
};

export default SlideDeckView;
