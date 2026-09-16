import React, { useEffect, useState } from 'react';
import { X, Search, Check, Music2, AlertTriangle, Clock, Download } from 'lucide-react';
import { studio } from '../../api/studio';

type TrFn = (key: string, vars?: Record<string, string | number>, fb?: string) => string;

export interface LyricsCandidate {
  artist: string;
  title: string;
  album: string;
  duration: number | null;
  durationDelta: number | null;
  synced: boolean;
  plain: boolean;
  source: string;
  score: number;
  badges: string[];
  versionMarkers?: string[];
  preview: string;
  syncedText?: string;
  plainText?: string;
}

const fmtDur = (sec: number | null | undefined) => {
  if (!sec && sec !== 0) return '—';
  const s = Math.max(0, Math.round(Number(sec)));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

/**
 * A02 — LyricsSearchDialog: daftar KANDIDAT lirik untuk trek aktif.
 *
 * Alasan: pencarian otomatis kadang memilih versi yang salah (live/remix/karaoke/
 * official-video). Dialog ini menampilkan semua kandidat dari LRCLIB get/search +
 * lyrics.ovh + lirik tertanam file beserta ALBUM, DURASI (delta vs trek), badge
 * SYNCED/PLAIN, skor kecocokan, dan pratinjau 5 baris — lalu user memilih sendiri.
 * Pilihan disimpan sebagai source "user-pick" sehingga tidak pernah tertimpa.
 */
export const LyricsSearchDialog: React.FC<{
  trackTitle: string;
  trackArtist: string;
  trackAlbum?: string;
  trackDurationSec?: number;
  tr: TrFn;
  onClose: () => void;
  onPick: (c: LyricsCandidate) => void;
  onLoad?: () => void;
}> = ({ trackTitle, trackArtist, trackAlbum = '', trackDurationSec = 0, tr, onClose, onPick }) => {
  const [loading, setLoading] = useState(true);
  const [rows, setRows] = useState<LyricsCandidate[]>([]);
  const [err, setErr] = useState('');

  const fetchCandidates = (limit = 12) => {
    setLoading(true);
    setErr('');
    studio.musicLyricsCandidates({
      artist: trackArtist, title: trackTitle, album: trackAlbum,
      duration: trackDurationSec || undefined, limit,
    })
      .then((d) => setRows(Array.isArray(d?.candidates) ? d.candidates : []))
      .catch((e) => setErr(String(e?.message || e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCandidates();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trackTitle, trackArtist, trackAlbum, trackDurationSec]);

  const srcLabel = (src: string) => {
    if (src === 'ovh') return tr('music_lyrics_source_ovh');
    if (src === 'embedded') return tr('music_lyrics_source_embedded');
    if (src === 'user' || src === 'user-pick') return tr('music_lyrics_source_user');
    return tr('music_lyrics_source_lrclib');
  };

  const durChip = (c: LyricsCandidate) => {
    if (!trackDurationSec || c.duration === null || c.duration === undefined) return null;
    const delta = c.durationDelta;
    if (delta === null || delta === undefined) return null;
    const abs = Math.abs(delta);
    const cls = abs <= 2
      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
      : abs <= 15
        ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
        : 'bg-rose-500/15 text-rose-300 border-rose-500/30';
    return (
      <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md border text-[10px] font-bold ${cls}`}>
        <Clock className="w-3 h-3" />
        {abs <= 2
          ? tr('music_lyrics_duration_match', { sec: Math.round(c.duration) })
          : tr('music_lyrics_duration_off', { diff: delta > 0 ? `+${delta}` : String(delta) })}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl bg-[#181818] border border-slate-700 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-emerald-500/15 flex items-center justify-center shrink-0">
            <Search className="w-4 h-4 text-emerald-300" />
          </div>
          <div className="min-w-0 mr-auto">
            <h2 className="text-sm font-black text-white truncate">{tr('music_lyrics_candidates')}</h2>
            <p className="text-[11px] text-slate-400 truncate flex items-center gap-1">
              <Music2 className="w-3 h-3 shrink-0" />
              {trackTitle || '—'}
              {trackArtist ? ` · ${trackArtist}` : ''}
              {trackAlbum ? ` · ${trackAlbum}` : ''}
              {trackDurationSec ? ` · ${fmtDur(trackDurationSec)}` : ''}
            </p>
          </div>
          <button type="button" onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Toolbar */}
        <div className="px-5 py-2.5 border-b border-slate-800 flex items-center gap-2">
          <button type="button" onClick={() => fetchCandidates(12)} disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-[11px] font-bold text-white">
            <Search className="w-3.5 h-3.5" />{tr('music_lyrics_search_expand')}
          </button>
          <span className="text-[10px] text-slate-500 ml-auto">{tr('music_lyrics_index_hint')}</span>
        </div>

        {/* Daftar kandidat */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {loading && (
            <div className="space-y-3">
              {[0, 1, 2].map((i) => (
                <div key={i} className="rounded-xl border border-slate-800 p-4 space-y-2">
                  <div className="ct-skeleton h-3 w-1/2 rounded" />
                  <div className="ct-skeleton h-2.5 w-3/4 rounded" />
                  <div className="ct-skeleton h-2.5 w-2/3 rounded" />
                </div>
              ))}
              <p className="text-center text-[11px] text-slate-500">{tr('music_lyrics_searching')}</p>
            </div>
          )}

          {!loading && err && (
            <p className="text-[11px] text-rose-300">{err}</p>
          )}

          {!loading && !err && rows.length === 0 && (
            <div className="text-center py-10">
              <AlertTriangle className="w-6 h-6 text-amber-300 mx-auto mb-2" />
              <p className="text-xs text-slate-400">{tr('music_lyrics_no_candidates')}</p>
            </div>
          )}

          {!loading && rows.map((c, i) => (
            <div key={`${c.source}_${c.title}_${i}`}
              className="rounded-xl border border-slate-800 bg-[#121212]/60 p-4 hover:border-emerald-600/40 transition-colors">
              <div className="flex items-start gap-3">
                <div className="min-w-0 mr-auto">
                  <p className="text-xs font-bold text-slate-100 truncate">{c.title || '—'}</p>
                  <p className="text-[11px] text-slate-400 truncate">
                    {c.artist || '—'}{c.album ? ` · ${c.album}` : ''} · {fmtDur(c.duration)}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5 mt-2">
                    <span className="px-1.5 py-0.5 rounded-md bg-slate-800 text-[10px] font-bold text-slate-300">
                      {srcLabel(c.source)}
                    </span>
                    {c.badges?.includes('SYNCED') && (
                      <span className="px-1.5 py-0.5 rounded-md bg-[#1ed760]/15 text-[#1ed760] text-[10px] font-black">SYNCED</span>
                    )}
                    {c.badges?.includes('PLAIN') && (
                      <span className="px-1.5 py-0.5 rounded-md bg-slate-700 text-slate-200 text-[10px] font-bold">PLAIN</span>
                    )}
                    {durChip(c)}
                    <span className="px-1.5 py-0.5 rounded-md bg-slate-800 text-[10px] font-mono text-slate-400">
                      {tr('music_lyrics_score')} {c.score}
                    </span>
                    {!!(c.versionMarkers && c.versionMarkers.length) && (
                      <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-rose-500/15 border border-rose-500/30 text-rose-300 text-[10px] font-bold"
                        title={tr('music_lyrics_version_warning')}>
                        <AlertTriangle className="w-3 h-3" />{c.versionMarkers.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
                <button type="button" onClick={() => onPick(c)}
                  className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-xl bg-[#1ed760] hover:bg-emerald-400 text-[#0b0b0b] text-[11px] font-black">
                  <Check className="w-3.5 h-3.5" />{tr('music_lyrics_use')}
                </button>
              </div>
              {c.preview && (
                <pre className="mt-3 max-h-24 overflow-hidden whitespace-pre-wrap text-[10px] leading-relaxed text-slate-400 border-t border-slate-800 pt-2">{c.preview}</pre>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-800 flex items-center gap-2">
          <Download className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-[10px] text-slate-500 mr-auto">{tr('music_lyrics_track_change_hint')}</span>
          <button type="button" onClick={onClose}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-200">
            {tr('music_lyrics_close')}
          </button>
        </div>
      </div>
    </div>
  );
};
