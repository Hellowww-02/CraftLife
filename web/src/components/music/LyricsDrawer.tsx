import React, { useEffect, useRef, useState } from 'react';
import { RefreshCw, Save, Trash2, Upload, Minus, Plus, RotateCcw, PauseCircle, Search, Download, HelpCircle } from 'lucide-react';

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
 * Auto-scroll baris aktif ke tengah panel (parity _update_synced_lyric).
 *
 * A01 — Lirik mengikuti lagu yang sedang diputar:
 *   • header menampilkan TREK AKTIF (judul · artis · durasi) sehingga jelas lirik
 *     ini milik lagu mana ketika musik berganti sendiri (auto-advance/Next/MiniPlayer);
 *   • state "belum ada trek" yang eksplisit (bukan lirik trek sebelumnya);
 *   • auto-scroll dijeda 3 detik saat pengguna menggulir manual (membaca lirik),
 *     lalu menyusul kembali — bukan melawan jari pengguna.
 */
export const LyricsDrawer: React.FC<{
  loading: boolean;
  plain: string;
  syncedLines: SyncedLine[];
  activeLine: number;
  source: string;
  saved: boolean;
  offsetMs: number;
  /** A01: kunci trek aktif — reset perilaku drawer saat lagu berganti. */
  trackKey?: string;
  trackTitle?: string;
  trackArtist?: string;
  trackDurationMs?: number;
  tr: TrFn;
  onRefresh: () => void;
  /** A02: buka dialog kandidat lirik (album + durasi + versi). */
  onSearchCandidates?: () => void;
  onImportPick: () => void;
  /** A03: ekspor lirik (server bila tersimpan, selain itu dari tampilan saat ini). */
  onExport?: (format: 'lrc' | 'txt') => void;
  /** A03: buka panduan format lirik (dialog import tab Panduan). */
  onOpenGuide?: () => void;
  onSave: () => void;
  onDeleteSaved: () => void;
  onOffset: (deltaMs: number) => void;
  onOffsetReset: () => void;
}> = ({
  loading, plain, syncedLines, activeLine, source, saved, offsetMs,
  trackKey = '', trackTitle = '', trackArtist = '', trackDurationMs = 0, tr,
  onRefresh, onSearchCandidates, onImportPick, onSave, onDeleteSaved, onOffset, onOffsetReset,
  onExport, onOpenGuide,
}) => {
  const boxRef = useRef<HTMLDivElement | null>(null);
  const lineRefs = useRef<(HTMLParagraphElement | null)[]>([]);

  // A01: auto-scroll dijeda sementara saat pengguna menggulir sendiri.
  const [followPaused, setFollowPaused] = useState(false);
  // A03: menu ekspor (.lrc / .txt) — dikontrol state agar menutup setelah dipilih.
  const [exportMenu, setExportMenu] = useState(false);
  const pauseTimerRef = useRef<number | null>(null);
  const pauseFollow = () => {
    setFollowPaused(true);
    if (pauseTimerRef.current) window.clearTimeout(pauseTimerRef.current);
    pauseTimerRef.current = window.setTimeout(() => setFollowPaused(false), 3000);
  };
  useEffect(() => () => {
    if (pauseTimerRef.current) window.clearTimeout(pauseTimerRef.current);
  }, []);

  // Ganti lagu → segarkan perilaku drawer (ikuti lagi dari baris pertama).
  useEffect(() => {
    setFollowPaused(false);
    lineRefs.current = [];
    if (pauseTimerRef.current) window.clearTimeout(pauseTimerRef.current);
  }, [trackKey]);

  // Auto-scroll garis aktif ke tengah panel (parity ensureCursorVisible).
  useEffect(() => {
    if (activeLine < 0 || followPaused) return;
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
  }, [activeLine, followPaused]);

  const hasTrack = !!trackKey;
  const hasLyrics = !!(plain || syncedLines.length);
  // A02: asal lirik ditampilkan eksplisit (LRCLIB / lyrics.ovh / tertanam di file /
  // import manual / pilihan user) supaya jelas lirik ini datang dari mana.
  const sourceLabel = source === 'ovh' ? tr('music_lyrics_source_ovh')
    : source === 'embedded' ? tr('music_lyrics_source_embedded')
      : source === 'user' ? tr('music_lyrics_source_user')
        : source === 'user-pick' ? tr('music_lyrics_source_pick')
          : source === 'lrclib' ? tr('music_lyrics_source_lrclib')
            : '';
  const sourceBadge = saved
    ? `${source === 'user' || source === 'user-pick' ? '✍️' : '💾'} ${sourceLabel || tr('music_lyrics_saved_badge')}`
    : sourceLabel || '';

  const iconBtn = 'p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors disabled:opacity-30 disabled:hover:bg-transparent';

  return (
    <div
      ref={boxRef}
      onWheel={pauseFollow}
      onTouchMove={pauseFollow}
      className="w-80 shrink-0 border-l border-slate-800/70 p-5 bg-[#181818] overflow-y-auto"
    >
      {/* Header + kontrol P58 */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <div className="text-white text-sm font-black">{tr('music_lyrics')}</div>
          {hasTrack ? (
            <div className="mt-0.5 min-w-0" title={tr('music_lyrics_track_change_hint')}>
              <p className="text-[11px] font-bold text-emerald-300 truncate">
                ♫ {trackTitle || '—'}
              </p>
              <p className="text-[10px] text-slate-500 truncate">
                {trackArtist || '—'}{trackDurationMs ? ` · ${fmtTime(trackDurationMs)}` : ''}
              </p>
            </div>
          ) : (
            <p className="mt-0.5 text-[10px] text-slate-500">{tr('music_lyrics_disabled_no_track')}</p>
          )}
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button type="button" onClick={onRefresh} disabled={!hasTrack} title={tr('music_lyrics_match_duration')}
            className={iconBtn}><RefreshCw className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onSearchCandidates} disabled={!hasTrack || !onSearchCandidates}
            title={tr('music_lyrics_search_expand')} className={`${iconBtn} hover:text-emerald-300`}>
            <Search className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onImportPick} disabled={!hasTrack} title={tr('music_lyrics_import')}
            className={iconBtn}><Upload className="w-3.5 h-3.5" /></button>
          <div className="relative">
            <button type="button" disabled={!hasTrack || !hasLyrics || !onExport}
              title={tr('music_lyrics_export')} className={iconBtn}
              onClick={() => setExportMenu((v) => !v)}>
              <Download className="w-3.5 h-3.5" />
            </button>
            {exportMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setExportMenu(false)} />
                <div className="absolute right-0 top-full mt-1 w-36 rounded-lg bg-slate-800 border border-slate-700 p-1 shadow-2xl z-20 text-[10px]">
                  <button type="button" className="w-full text-left px-2 py-1.5 rounded hover:bg-slate-700 text-slate-200"
                    onClick={() => { setExportMenu(false); onExport?.('lrc'); }}>.lrc — timestamp + tag</button>
                  <button type="button" className="w-full text-left px-2 py-1.5 rounded hover:bg-slate-700 text-slate-200"
                    onClick={() => { setExportMenu(false); onExport?.('txt'); }}>.txt — teks polos</button>
                </div>
              </>
            )}
          </div>
          <button type="button" onClick={onOpenGuide} disabled={!onOpenGuide}
            title={tr('music_lyrics_import_guide')} className={iconBtn}>
            <HelpCircle className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onSave} disabled={!hasTrack || !hasLyrics} title={tr('music_lyrics_save')}
            className={iconBtn}><Save className="w-3.5 h-3.5" /></button>
          <button type="button" onClick={onDeleteSaved} disabled={!saved} title={tr('music_lyrics_delete_saved')}
            className={`${iconBtn} hover:text-rose-300`}><Trash2 className="w-3.5 h-3.5" /></button>
        </div>
      </div>

      {/* Offset live-sync (P58): geser penyorotan bila lirik lebih cepat/lambat */}
      <div className="flex items-center gap-1 mb-3 text-[10px] text-slate-400">
        <span className="font-bold uppercase tracking-wider">{tr('music_lyrics_offset')}</span>
        <button type="button" onClick={() => onOffset(-500)} title="−0.5s" disabled={!hasTrack}
          className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold disabled:opacity-30"><Minus className="w-3 h-3" /></button>
        <button type="button" onClick={() => onOffset(500)} title="+0.5s" disabled={!hasTrack}
          className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold disabled:opacity-30"><Plus className="w-3 h-3" /></button>
        {offsetMs !== 0 && (
          <button type="button" onClick={onOffsetReset} title={tr('music_lyrics_offset_reset')}
            className="px-1.5 py-0.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300"><RotateCcw className="w-3 h-3" /></button>
        )}
        {followPaused && (
          <span className="inline-flex items-center gap-0.5 text-[9px] font-bold uppercase tracking-wider text-amber-300/90"
            title={tr('music_lyrics_scroll_paused')}>
            <PauseCircle className="w-3 h-3" />{tr('music_lyrics_scroll_paused')}
          </span>
        )}
        <span className="ml-auto font-mono tabular-nums text-slate-500">{(offsetMs / 1000).toFixed(1)}s</span>
      </div>

      {sourceBadge && hasTrack && (
        <div className="text-[10px] font-bold text-[#1ed760] uppercase tracking-wide mb-2">{sourceBadge}</div>
      )}

      <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
        {!hasTrack ? (
          <span className="text-slate-500 italic">{tr('music_lyrics_disabled_no_track')}</span>
        ) : loading ? (
          <div className="space-y-2">
            <div className="ct-skeleton h-2.5 w-2/3 rounded" /><div className="ct-skeleton h-2.5 w-1/2 rounded" />
            <p className="text-slate-500">{tr('music_lyrics_searching')}</p>
            {trackTitle && <p className="text-[10px] text-slate-600">{tr('music_lyrics_now_for', { title: trackTitle })}</p>}
          </div>
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
