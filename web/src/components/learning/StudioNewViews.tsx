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
export interface SlideDeckData { title: string; slides: { title: string; bullets: string[] }[]; }

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
  const slides = (d.slides as any[]).filter((s) => s && typeof s === 'object').slice(0, 25).map((s) => ({
    title: String(s.title || ''),
    bullets: ((s.bullets || []) as any[]).map((b) => String(b ?? '')).slice(0, 8),
  }));
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
  if (!deck) return <EmptyOrRaw raw={data} tr={tr} />;
  const total = deck.slides.length;
  const i = Math.max(0, Math.min(total - 1, idx));
  const s = deck.slides[i];
  const btn = 'px-3 py-1.5 rounded-lg text-[11px] font-bold border disabled:opacity-40 bg-slate-900 border-slate-700 text-slate-200 hover:border-violet-500/50';
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
      {deck.title && <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold mb-2">{deck.title}</p>}
      <h4 className="font-bold text-sm text-slate-100">{s.title || `${i + 1}`}</h4>
      {s.bullets.length > 0 && (
        <ul className="mt-2 space-y-1">
          {s.bullets.map((b, bi) => (
            <li key={bi} className="text-[11px] text-slate-300 flex gap-1.5"><span className="text-violet-300">•</span><span>{b}</span></li>
          ))}
        </ul>
      )}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/70">
        <button disabled={i === 0} onClick={() => setIdx(i - 1)} className={btn}>‹ {tr('learning_slide_prev', {}, 'Sebelumnya')}</button>
        <span className="text-[10px] text-slate-400 ct-nlm-num">{tr('learning_slide_of', { n: i + 1, total }, `${i + 1} / ${total}`)}</span>
        <button disabled={i >= total - 1} onClick={() => setIdx(i + 1)} className={btn}>{tr('learning_slide_next', {}, 'Berikutnya')} ›</button>
      </div>
    </div>
  );
};

export default SlideDeckView;
