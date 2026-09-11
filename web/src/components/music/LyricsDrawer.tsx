import React, { useEffect, useRef } from 'react';
import { RefreshCw, Save, Trash2, Upload, Minus, Plus, RotateCcw } from 'lucide-react';

type TrFn = (key: string, vars?: Record<string, string | number>, fb?: string) => string;
export interface SyncedLine { ms: number; text: string }

const fmtTime = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

/**
 * P58 — LyricsDrawer (refactor dari inline MusicView).
 * Drawer lirik dengan: badge sumber (Web/File/Tersimpan/Disimpan-user), tombol
 * refresh (pencarian ulang dicocokkan durasi), import file .lrc/.txt, simpan,
 * hapus tersimpan, dan offset live-sync ±0.5 dtk (per track, tersimpan).
 * Auto-scroll baris aktif ke tengah (parity _update_synced_lyric).
 */
export const LyricsDrawer: React.FC<{
  loading: boolean;
  plain: string;
  syncedLines: SyncedLine[];
  activeLine: number;
  source: string;
  saved: boolean;
  offsetMs: number;
  tr: TrFn;
  onRefresh: () => void;
  onImportPick: () => void;
  onSave: () => void;
  onDeleteSaved: () => void;
  onOffset: (deltaMs: number) => void;
  onOffsetReset: () => void;
}> = ({
  loading, plain, syncedLines, activeLine, source, saved, offsetMs, tr,
  onRefresh, onImportPick, onSave, onDeleteSaved, onOffset, onOffsetReset,
}) => {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const lineRefs = useRef<(HTMLParagraphElement | null)[]>([]);

  // Auto-scroll garis aktif ke tengah panel (parity ensureCursorVisible).
  useEffect(() => {
    if (activeLine < 0) return;
    const el = lineRefs.current[activeLine];
    const box = boxRef.current;
    if (el && box) {
      const elTop = el.getBoundingClientRect().top;
      const boxTop = box.getBoundingClientRect().top;
      box.scrollTo({
        top: box.scrollTop + (elTop - boxTop) - box.clientHeight / 2 + el.clientHeight / 2,
        behavior: 'smooth',
      });
    }
  }, [activeLine]);

  const hasLyrics = !!(plain || syncedLines.length);
  const sourceBadge = saved
    ? `${source === 'user' ? '✍️' : '💾'} ${tr('music_lyrics_saved_badge')}`
    : source === 'embedded'
      ? tr('music_lyrics_from_file')
      : source
        ? tr('music_lyrics_from_web')
        : '';

  const iconBtn = 'p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors disabled:opacity-30 disabled:hover:bg-transparent';

  return (
    <div ref={boxRef} className="w-80 shrink-0 border-l border-slate-800/70 p-5 bg-[#181818] overflow-y-auto">
      {/* Header + kontrol P58 */}
      <div className="flex items-center justify-between gap-1 mb-2">
        <div className="text-white text-sm font-black">{tr('music_lyrics')}</div>
        <div className="flex items-center gap-0.5">
          <button type="button" onClick={onRefresh} title={tr('music_lyrics_match_duration')}
            className={iconBtn}><RefreshCw className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onImportPick} title={tr('music_lyrics_import')}
            className={iconBtn}><Upload className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onSave} disabled={!hasLyrics} title={tr('music_lyrics_save')}
            className={iconBtn}><Save className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onDeleteSaved} disabled={!saved} title={tr('music_lyrics_delete_saved')}
            className={`${iconBtn} hover:text-rose-300`}><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* Offset live-sync (P58): geser penyorotan bila lirik lebih cepat/lambat */}
      <div className="flex items-center gap-1 mb-3 text-[10px] text-slate-400">
        <span className="font-bold uppercase tracking-wider">{tr('music_lyrics_offset')}</span>
        <button type="button" onClick={() => onOffset(-500)} title="−0.5s"
          className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold"><Minus className="w-3 h-3" /></button>
        <button type="button" onClick={() => onOffset(500)} title="+0.5s"
          className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold"><Plus className="w-3 h-3" /></button>
        {offsetMs !== 0 && (
          <button type="button" onClick={onOffsetReset} title={tr('music_lyrics_offset_reset')}
            className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"><RotateCcw className="w-3 h-3" /></button>
        )}
        <span className="ml-auto font-mono tabular-nums text-slate-500">{(offsetMs / 1000).toFixed(1)}s</span>
      </div>

      {sourceBadge && <div className="text-[10px] font-bold text-[#1ed760] uppercase tracking-wide mb-2">{sourceBadge}</div>}

      <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
        {loading ? (
          <div className="space-y-2"><div className="ct-skeleton h-2.5 w-2/3 rounded" /><div className="ct-skeleton h-2.5 w-1/2 rounded" /><p className="text-slate-500">{tr('music_lyrics_searching')}</p></div>
        ) : syncedLines.length ? (
          <div className="space-y-1.5">
            {syncedLines.map((ln, i) => (
              <p key={i} ref={(el) => { lineRefs.current[i] = el; }}
                className={`transition-all duration-200 leading-snug ${i === activeLine ? 'ct-lyric-active text-white font-bold text-[13px]' : 'text-slate-500'}`}>
                <span className="mr-1.5 font-mono text-[10px] text-slate-600 tabular-nums">{fmtTime(ln.ms)}</span>{ln.text}
              </p>
            ))}
          </div>
        ) : plain ? (
          <span>{plain}</span>
        ) : (
          <span className="text-slate-500 italic">{tr('music_no_lyrics')}</span>
        )}
      </div>
    </div>
  );
};
