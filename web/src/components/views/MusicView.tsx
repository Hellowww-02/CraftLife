import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useGame } from '../../context/GameContext';
import { useMusicPlayer, type LibraryEntry } from '../../music/MusicPlayerContext';
import { LyricsDrawer } from '../../components/music/LyricsDrawer';
import { PlaylistIconDialog } from '../../components/music/PlaylistIconDialog';
import { studio } from '../../api/studio';
import { t } from '../../i18n';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Volume2,
  VolumeX,
  Sparkles,
  Heart,
  Search,
  Trash2,
  Plus,
  FileAudio,
  Shuffle,
  Repeat,
  FolderInput,
  FolderOutput,
  Download,
  ChevronDown,
  Palette,
} from 'lucide-react';

// ── Tipe (parity MusicPage PyQt) ─────────────────────────────────────────────
interface PlaylistEntry {
  id: string | number;
  name: string;
  isFavorite?: number | boolean;
  icon?: string;
  tracks?: string[];
}
interface HistoryEntry {
  path?: string;
  title?: string;
  artist?: string;
  played_at?: string;
  created_at?: string;
}
interface TrackRow {
  path: string;
  title: string;
  artist: string;
  album: string;
  duration: number;
  missing: boolean;
}

const fmtDuration = (sec: number) => {
  if (!sec) return '';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};
const fmtTime = (ms: number) => {
  const s = Math.max(0, Math.round(ms / 1000));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
};

// P57: nama file basis (untuk entri antrean tanpa metadata).
const baseName = (p: string) => p.split(/[\\/]/).pop() || p;

// P58: kunci lirik per track — path file bila ada, selain itu slug artis::judul.
const trackKeyFor = (e: { path?: string; artist?: string; title?: string; name?: string } | null) =>
  !e ? '' : e.path ? `path:${e.path}` : `meta:${(e.artist || '').toLowerCase()}::${(e.title || e.name || '').toLowerCase()}`;

// Parity MusicPage._parse_lrc: [mm:ss.xx] baris → daftar {ms,text} terurut.
const parseLrc = (text: string): { ms: number; text: string }[] => {
  if (!text) return [];
  const out: { ms: number; text: string }[] = [];
  const re = /\[(\d+):(\d+(?:\.\d+)?)\]/g;
  for (const raw of text.split('\n')) {
    const stamps = Array.from(raw.matchAll(re));
    const content = raw.replace(re, '').trim();
    if (!stamps.length || !content) continue;
    for (const m of stamps) {
      out.push({ ms: (parseInt(m[1], 10) || 0) * 60000 + Math.round(parseFloat(m[2] || '0') * 1000), text: content });
    }
  }
  out.sort((a, b) => a.ms - b.ms);
  return out;
};

export const MusicView: React.FC = () => {
  const { lang, showToast } = useGame();
  const tr = (key: string, vars?: Record<string, string | number>, fb?: string) => {
    let s = t(key, fb || key);
    if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
    return s;
  };

  // P57: player GLOBAL — semua state & elemen <audio> hidup di
  // MusicPlayerContext (App root, di luar switch view) sehingga musik TIDAK
  // berhenti saat pindah halaman. MusicView kini "remote control"
  // (parity MusicPage PyQt yang hidup di MainWindow, bukan per-page).
  const music = useMusicPlayer();
  const { playingFile, isPlaying, shuffle, repeat, volume, isMuted, progressMs, durationMs } = music;
  const isLibraryPlaying = music.isPlayingLibrary;
  // Override lokal saat slider progress diseret (timeupdate global tak menimpa).
  const [dragging, setDragging] = useState(false);
  const [dragMs, setDragMs] = useState(0);

  // Playlists / library (parity _reload_playlists + _metadata)
  const [playlists, setPlaylists] = useState<PlaylistEntry[]>([]);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<string | number | null>(null);
  const [library, setLibrary] = useState<LibraryEntry[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [newPlaylistName, setNewPlaylistName] = useState('');

  // Import
  const [importing, setImporting] = useState(false);
  const [importingFolder, setImportingFolder] = useState(false);
  const importFilesRef = useRef<HTMLInputElement | null>(null);
  const importFolderRef = useRef<HTMLInputElement | null>(null);

  // Lyrics drawer (parity _toggle_lyrics + _load_lyrics + _update_synced_lyric)
  // P58: + source/saved/offsetMs per track (tersimpan di server, table song_lyrics).
  const [lyricsOpen, setLyricsOpen] = useState(false);
  const [lyrics, setLyrics] = useState<{ plain: string; synced: string; source: string; saved: boolean; offsetMs: number }>({ plain: '', synced: '', source: '', saved: false, offsetMs: 0 });
  const [lyricsLoading, setLyricsLoading] = useState(false);
  const [activeLyricLine, setActiveLyricLine] = useState(-1);
  const syncedLines = useMemo(() => parseLrc(lyrics.synced), [lyrics.synced]);
  const importLyricsRef = useRef<HTMLInputElement | null>(null);

  // yt-dlp downloader modal (parity _open_downloader)
  const [dlOpen, setDlOpen] = useState(false);
  const [ytQuery, setYtQuery] = useState('');
  const [ytBusy, setYtBusy] = useState(false);
  const [ytResults, setYtResults] = useState<{ id: string; title: string; url: string }[]>([]);
  const [ytJob, setYtJob] = useState<{ done?: boolean; percent?: string } | null>(null);
  const [ytUrl, setYtUrl] = useState('');
  const [dlTargetId, setDlTargetId] = useState<string | number>('');

  // Track context menu (parity _track_menu)
  const [menuOpenFor, setMenuOpenFor] = useState<number | null>(null);
  // P59: dialog ganti icon playlist (emoji / foto dari komputer).
  const [iconDlgFor, setIconDlgFor] = useState<PlaylistEntry | null>(null);


  useEffect(() => {
    setActiveLyricLine(-1);
  }, [syncedLines]);

  const activePlaylist = playlists.find((p) => p.id === selectedPlaylistId) ?? null;
  const activeTracks = activePlaylist?.tracks || [];

  // P57: playSrc dihitung provider (satu-satunya <audio> ada di App root).

  // Metadata join: path → LibraryEntry (parity _metadata / _render_tracks).
  const metaFor = useCallback((path: string) => library.find((f) => f.path === path), [library]);
  // P57: snapshot antrean (LibraryEntry) untuk player global — dipakai next/prev.
  const queueFor = (paths: string[]): LibraryEntry[] =>
    paths.map((p) => metaFor(p) || { path: p, name: baseName(p), title: baseName(p), size: 0 });
  const trackRows: TrackRow[] = activeTracks.map((path) => {
    const m = metaFor(path);
    const base = path.split(/[\\\\/]/).pop() || path;
    return {
      path,
      title: m?.title || base,
      artist: m?.artist || tr('music_unknown_artist'),
      album: m?.album || tr('music_unknown_album'),
      duration: m?.duration || 0,
      missing: !m,
    };
  });
  const filteredRows = trackRows.filter((r) => {
    const needle = searchQuery.trim().toLowerCase();
    if (!needle) return true;
    return `${r.title} ${r.artist} ${r.album}`.toLowerCase().includes(needle);
  });

  // Track index (parity current_index) → selectRow setelact.
  // P57: index dihitung dari antrean global (snapshot playlist saat main).
  const currentIndex = playingFile ? music.queue.findIndex((e) => e.path === playingFile.path) : -1;

  // ── Data loading ───────────────────────────────────────────────────────────
  const refreshMusic = useCallback((selectId?: string | number | null) => {
    studio.musicPlaylists().then((d) => {
      const pls: PlaylistEntry[] = (d.playlists || []).map((p: any) => ({
        id: p.id,
        name: p.name,
        // parity: DB mengembalikan is_favorite (snake_case) → normalisasi.
        isFavorite: p.isFavorite ?? p.is_favorite,
        icon: typeof p.icon === 'string' ? p.icon : '',
        tracks: Array.isArray(p.tracks) ? p.tracks : [],
      }));
      setPlaylists(pls);
      setHistory((d.history || []).map((h: any) => ({
        path: h.path || '', title: h.title || '', artist: h.artist || '',
        played_at: h.played_at || h.created_at || '',
      })));
      setSelectedPlaylistId((prev) => {
        if (selectId !== undefined) return selectId;
        if (prev !== null && pls.some((p) => p.id === prev)) return prev;
        return pls.length ? pls[0].id : null;
      });
    }).catch(() => {});
  }, []);

  const refreshLibrary = () => studio.musicLibrary().then((d) => setLibrary(d.library || [])).catch(() => {});

  useEffect(() => {
    refreshLibrary();
    refreshMusic();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Playback (parity _play_path / _play_pause / _next / _previous) ─────────
  const handlePlayLibraryFile = (entry: LibraryEntry) => {
    // P57: antrean = snapshot daftar putar aktif saat mulai main, sehingga
    // next/prev tetap benar walau user pindah halaman / ganti playlist.
    music.playFile(entry, queueFor(activeTracks));
    refreshMusic();
    loadLyrics(entry);
    showToast('info', tr('music_now_playing'), entry.title || entry.name);
  };

  const playLibraryPath = (path: string) => {
    const entry = metaFor(path);
    const base = path.split(/[\\\\/]/).pop() || path;
    handlePlayLibraryFile(entry || { path, name: base, title: base, size: 0 });
  };

  // P57: next/prev/toggle didelegasikan ke player global (antrean di provider).
  const handleNextTrack = () => music.next();
  const handlePrevTrack = () => music.prev();
  const toggleTrackPlay = () => music.togglePlay();

  // ── Playlist actions (parity _create/_rename/_delete + _add_paths) ─────────
  const createPlaylist = () => {
    const name = window.prompt(tr('music_new_playlist'), tr('music_playlist_name'))?.trim();
    if (!name) return;
    studio.createPlaylist(name).then(() => refreshMusic()).catch(() => {});
    setNewPlaylistName('');
  };
  const renamePlaylist = (p: PlaylistEntry) => {
    if (p.isFavorite) return; // parity: favorit tak bisa di-rename
    const name = window.prompt(tr('music_rename_playlist'), p.name)?.trim();
    if (!name) return;
    studio.renamePlaylist(p.id, name).then(() => refreshMusic(selectedPlaylistId)).catch(() => {});
  };
  const deletePlaylist = (p: PlaylistEntry) => {
    if (p.isFavorite) { showToast('info', tr('music_delete_playlist'), tr('msg_no')); return; }
    if (!window.confirm(tr('music_delete_playlist_confirm'))) return;
    studio.deletePlaylist(p.id).then(() => { setSelectedPlaylistId(null); refreshMusic(null); }).catch(() => {});
  };

  const MUSIC_EXT = ['.mp3', '.wav', '.flac', '.m4a', '.mp4', '.ogg'];
  const handleImport = async (files: FileList | File[], folderMode: boolean) => {
    if (selectedPlaylistId === null) return; // parity: current_playlist_id None → return
    const list = Array.from(files).sort((a, b) => {
      const ra = (a as any).webkitRelativePath || a.name;
      const rb = (b as any).webkitRelativePath || b.name;
      return String(ra).localeCompare(String(rb));
    });
    folderMode ? setImportingFolder(true) : setImporting(true);
    let added = 0, skipped = 0;
    for (const f of list) {
      const ext = `.${(f.name.split('.').pop() || '').toLowerCase()}`;
      if (!MUSIC_EXT.includes(ext)) { skipped++; continue; }
      try {
        const up = await studio.uploadMusicFile(f);
        if (up?.ok && up.path) { await studio.addPlaylistTrack(selectedPlaylistId, up.path); added++; }
        else skipped++;
      } catch { skipped++; }
    }
    setImporting(false);
    setImportingFolder(false);
    if (added) {
      showToast('success', tr('music_add_files'), tr('music_add_song'));
      refreshMusic(selectedPlaylistId);
      refreshLibrary();
    }
    if (skipped) showToast('info', '', tr('music_format_error'));
  };

  const addToFavorites = (path: string) => {
    const fav = playlists.find((p) => p.isFavorite);
    if (!fav) { showToast('info', tr('music_add_to_favorites'), tr('msg_no')); return; }
    studio.addPlaylistTrack(fav.id, path).then(() => refreshMusic(selectedPlaylistId)).catch(() => {});
  };

  const addToPlaylist = (path: string) => {
    if (!selectedPlaylistId) return;
    studio.addPlaylistTrack(selectedPlaylistId, path).then(() => refreshMusic(selectedPlaylistId)).catch(() => {});
  };
  const removeFromPlaylist = (index: number) => {
    if (selectedPlaylistId === null) return;
    studio.removePlaylistTrack(selectedPlaylistId, index).then(() => refreshMusic(selectedPlaylistId)).catch(() => {});
  };
  const moveTrackTo = (index: number, targetId: string | number | null, copy: boolean) => {
    if (!targetId || selectedPlaylistId === null || String(targetId) === String(selectedPlaylistId)) return;
    const fn = copy ? studio.copyPlaylistTrack : studio.movePlaylistTrack;
    fn(selectedPlaylistId, targetId, index).then(() => refreshMusic(selectedPlaylistId)).catch(() => {});
  };

  // ── Lyrics (P58: tersimpan dulu → web; kunci per track; durasi utk akurasi) ──
  const loadLyrics = useCallback((entry: { path?: string; artist?: string; title?: string; name?: string; duration?: number } | null, refresh = false) => {
    if (!entry) return;
    const title = entry.title || entry.name || '';
    if (!title) return;
    setLyricsLoading(true);
    setLyrics({ plain: '', synced: '', source: '', saved: false, offsetMs: 0 });
    studio.musicLyrics(entry.artist || '', title, entry.path || '', {
      key: trackKeyFor(entry), duration: entry.duration || undefined, refresh,
    }).then((res) => {
      const d = res?.lyrics || res?.result || res || {};
      setLyrics({
        plain: typeof d.plain === 'string' ? d.plain : '',
        synced: typeof d.synced === 'string' ? d.synced : '',
        source: typeof d.source === 'string' ? d.source : '',
        saved: !!d.saved,
        offsetMs: Number(d.offsetMs) || 0,
      });
      setLyricsLoading(false);
    }).catch(() => setLyricsLoading(false));
  }, []);

  const toggleLyrics = () => {
    setLyricsOpen((o) => {
      const next = !o;
      if (next && playingFile) loadLyrics(playingFile);
      return next;
    });
  };

  // P58: simpan / hapus / offset — lirik tersimpan per track di server.
  const saveLyrics = () => {
    if (!playingFile || (!lyrics.plain && !lyrics.synced)) return;
    studio.musicLyricsSave({
      key: trackKeyFor(playingFile),
      title: playingFile.title || playingFile.name || '',
      artist: playingFile.artist || '',
      source: lyrics.source === 'user' ? 'user' : (lyrics.source || 'web'),
      plain: lyrics.plain, synced: lyrics.synced, offsetMs: lyrics.offsetMs,
    }).then((res) => {
      if (res?.result?.ok) { setLyrics((p) => ({ ...p, saved: true })); showToast('success', tr('music_lyrics_saved_ok'), ''); }
    }).catch(() => {});
  };
  const deleteSavedLyrics = () => {
    if (!playingFile) return;
    studio.musicLyricsDelete(trackKeyFor(playingFile)).then(() => {
      setLyrics((p) => ({ ...p, saved: false, offsetMs: 0 }));
    }).catch(() => {});
  };
  const shiftLyricsOffset = (deltaMs: number) => {
    if (!playingFile) return;
    const next = Math.max(-10000, Math.min(10000, lyrics.offsetMs + deltaMs));
    setLyrics((p) => ({ ...p, offsetMs: next }));
    // Offset per track harus TERSIMPAN → upsert lirik beserta offset barunya.
    studio.musicLyricsSave({
      key: trackKeyFor(playingFile),
      title: playingFile.title || playingFile.name || '',
      artist: playingFile.artist || '',
      source: lyrics.source === 'user' ? 'user' : (lyrics.source || 'web'),
      plain: lyrics.plain, synced: lyrics.synced, offsetMs: next,
    }).then((res) => {
      if (res?.result?.ok) setLyrics((p) => ({ ...p, saved: true }));
    }).catch(() => {});
  };
  const handleImportLyricsFile = (f: File) => {
    if (!playingFile) return;
    const title = playingFile.title || playingFile.name || '';
    const reader = new FileReader();
    reader.onload = () => {
      const content = String(reader.result || '');
      studio.musicLyricsImport({ key: trackKeyFor(playingFile), title, artist: playingFile.artist || '', content })
        .then((res) => {
          const d = res?.result || {};
          if (d.ok && d.lyrics) {
            setLyrics({ plain: d.lyrics.plain || '', synced: d.lyrics.synced || '', source: 'user', saved: true, offsetMs: 0 });
            showToast('success', tr('music_lyrics_import_ok'), '');
          } else showToast('info', tr('music_lyrics_import_invalid'), '');
        }).catch(() => showToast('info', tr('music_lyrics_import_invalid'), ''));
    };
    reader.readAsText(f);
  };

  // P57: event audio kini ditangani MusicPlayerProvider. View hanya menurunkan
  // garis lirik aktif dari progressMs global; P58: memakai OFFSET per track
  // (lirik yang geser bisa dikoreksi ±0.5 dtk dari drawer).
  useEffect(() => {
    let idx = -1;
    const matchMs = progressMs - lyrics.offsetMs;
    for (let i = 0; i < syncedLines.length; i++) { if (syncedLines[i].ms <= matchMs) idx = i; else break; }
    setActiveLyricLine((p) => (p === idx ? p : idx));
  }, [progressMs, syncedLines, lyrics.offsetMs]);

  // Now playing display (parity _update_now_playing)
  const nowTitle = isLibraryPlaying ? (playingFile?.title || playingFile?.name || '') : tr('music_nothing_playing');
  const nowArtist = isLibraryPlaying ? (playingFile?.artist || playingFile?.name || '') : tr('music_choose_track');
  const nowAlbum = isLibraryPlaying ? (playingFile?.album || '') : '';

  // ── yt-dlp downloader (parity _open_downloader) ───────────────────────────
  const searchYt = async () => {
    if (!ytQuery.trim()) return;
    setYtBusy(true);
    try {
      const d = await studio.searchMusic(ytQuery.trim());
      const rows = d.results || d.result?.results || [];
      setYtResults(rows.map((x: any, i: number) => ({ id: String(x.id || i), title: x.title || x.url, url: x.url || x.webpage_url || '' })));
    } catch { showToast('damage', 'yt-dlp', 'search failed'); }
    finally { setYtBusy(false); }
  };
  const downloadYt = async (url: string) => {
    if (!url) return;
    const targetId = dlTargetId || selectedPlaylistId;
    if (targetId === null) return;
    try {
      const d = await studio.downloadMusic(url);
      const jid = d.jobId || d.result?.jobId;
      if (!jid) return;
      setYtJob({ done: false, percent: '0%' });
      const poll = async () => {
        const j = await studio.musicJob(jid);
        const job = j.job || j;
        setYtJob({ done: !!job.done, percent: String(job.percent || job.progress || '') });
        if (!job.done && !job.error) setTimeout(poll, 1500);
        else {
          // P27: parity PyQt MusicPage._open_downloader → on_done → db.add_song_to_playlist.
          // File hasil unduhan HARUS didaftarkan ke playlist terpilih, bukan hanya
          // muncul di library (scan folder). Jika tidak, lagu "berhasil diunduh"
          // tapi tidak masuk daftar putar.
          if (!job.error && job.path) {
            await studio.addPlaylistTrack(targetId, job.path).then(() => undefined).catch(() => undefined);
          }
          if (job.error) showToast('damage', 'yt-dlp', job.error);
          refreshLibrary();
          refreshMusic(selectedPlaylistId);
        }
      };
      poll();
    } catch { showToast('damage', 'yt-dlp', 'download failed'); }
  };

  const libMeta = (path: string) => metaFor(path);
  const renderRow = (r: TrackRow, idx: number) => (
    <tr key={`${r.path}_${idx}`}
      onDoubleClick={() => playLibraryPath(r.path)}
      onClick={() => setMenuOpenFor(null)}
      className={`border-b border-slate-800/60 ${currentIndex === activeTracks.indexOf(r.path) ? 'bg-emerald-500/10 text-emerald-200' : 'hover:bg-slate-800/30'} ${r.missing ? 'text-rose-400/70' : 'text-slate-300'} cursor-pointer`}>
      <td className="px-3 py-2 text-slate-500 text-xs w-8">{idx + 1}</td>
      <td className="px-3 py-2 text-xs font-semibold">
        <span className="flex items-center gap-2"><FileAudio className={`w-3.5 h-3.5 ${r.missing ? 'text-rose-400' : 'text-emerald-400'} shrink-0`} />{r.title}</span>
      </td>
      <td className="px-3 py-2 text-xs">{r.artist}</td>
      <td className="px-3 py-2 text-xs">{r.album}</td>
      <td className="px-3 py-2 text-xs text-center font-mono">{r.duration ? fmtDuration(r.duration) : '—'}</td>
      <td className="px-2 py-2 text-right w-8">
        <button onClick={(e) => { e.stopPropagation(); setMenuOpenFor(menuOpenFor === idx ? null : idx); }}
          className="p-1 text-slate-500 hover:text-slate-200"><ChevronDown className="w-3.5 h-3.5" /></button>
      </td>
    </tr>
  );

  return (
    <div className="h-full flex flex-col bg-[#121212] text-slate-100">
      {/* P57: elemen <audio> kini milik MusicPlayerProvider di App root. */}

      {/* Header (parity _page_header("music") + actions) */}
      <div className="px-6 py-4 flex flex-wrap items-center gap-3 border-b border-slate-800/70">
        <div className="mr-auto flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center text-xl">🎵</div>
          <div>
            <h1 className="text-lg font-black">{tr('music')}</h1>
            <p className="text-[11px] text-slate-400">{tr('music_subtitle')}</p>
          </div>
        </div>
        <input ref={importFilesRef} type="file" multiple accept=".mp3,.wav,.flac,.m4a,.mp4,.ogg,audio/*"
          className="hidden" onChange={(e) => { if (e.target.files?.length) handleImport(e.target.files, false); e.target.value = ''; }} />
        <input ref={importFolderRef} type="file" multiple {...({ webkitdirectory: '', directory: '' } as any)}
          className="hidden" onChange={(e) => { if (e.target.files?.length) handleImport(e.target.files, true); e.target.value = ''; }} />
        {/* P58: import lirik manual (.lrc bertimestamp / .txt polos) */}
        <input ref={importLyricsRef} type="file" accept=".lrc,.txt,text/plain"
          className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportLyricsFile(f); e.target.value = ''; }} />
        <button onClick={() => importFilesRef.current?.click()} disabled={importing || selectedPlaylistId === null}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-sm font-bold">
          <FolderInput className="w-4 h-4" />{tr('music_add_files')}
        </button>
        <button onClick={() => importFolderRef.current?.click()} disabled={importingFolder || selectedPlaylistId === null}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-sm font-bold">
          <FolderInput className="w-4 h-4" />{tr('music_select_folder')}
        </button>
        <button onClick={() => setDlOpen(true)}
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-600/20 border border-emerald-500/40 text-emerald-200 hover:bg-emerald-600/35 text-sm font-bold">
          <Download className="w-4 h-4" />{tr('music_download_title')}
        </button>
      </div>

      <div className="flex flex-1 min-h-0">
        {/* ── Sidebar playlist rail (parity musicSidebar) ── */}
        <div className="w-60 shrink-0 flex flex-col min-h-0 border-r border-slate-800/70 p-4 space-y-3 bg-[#090909]">
          <div className="text-emerald-400 text-xs font-black tracking-widest">CRAFTLIFE&nbsp;MUSIC</div>
          <div className="text-xs text-slate-400 font-bold uppercase tracking-wider">{tr('music_your_library')}</div>
          <div className="flex-1 min-h-0 space-y-1 overflow-y-auto">
            {playlists.length === 0 && <p className="text-[11px] text-slate-600">{tr('music_no_tracks_to_save')}</p>}
            {playlists.map((p) => {
              const count = p.tracks?.length || 0;
              const iconEl = p.icon && p.icon.startsWith('photo:') ? (
                <img src={`/api/music/playlist-icon/image?id=${p.icon.slice(6)}`} alt="" className="w-4 h-4 rounded-full object-cover inline-block align-[-2px] shrink-0" />
              ) : (
                <span className="text-emerald-400">{p.isFavorite ? '♥' : (p.icon || '♫')}</span>
              );
              return (
                <button key={p.id} onClick={() => refreshMusic(p.id)} onDoubleClick={() => renamePlaylist(p)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs ${selectedPlaylistId === p.id ? 'bg-slate-800 text-white font-bold' : 'text-slate-400 hover:bg-slate-900 hover:text-white'} transition-colors`}>
                  {iconEl}{' '}
                  <span>{p.name}</span>
                  <span className="block text-[10px] text-slate-500">{tr('music_track_count', { count })}</span>
                </button>
              );
            })}
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={createPlaylist} className="px-2 py-1.5 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-[11px] font-bold">{tr('music_new_playlist')}</button>
            <div className="grid grid-cols-3 gap-1">
              <button onClick={() => activePlaylist && renamePlaylist(activePlaylist)} className="px-1 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px]">{tr('music_rename_playlist')}</button>
              <button onClick={() => activePlaylist && setIconDlgFor(activePlaylist)} title={tr('music_playlist_icon_change')} className="px-1 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px]"><Palette className="w-3 h-3 mx-auto" /></button>
              <button onClick={() => activePlaylist && deletePlaylist(activePlaylist)} className="px-1 py-1.5 rounded-lg bg-rose-600/80 hover:bg-rose-500 text-[11px]"><Trash2 className="w-3 h-3 mx-auto" /></button>
            </div>
          </div>
        </div>

        {/* ── Center: hero + search + track table ── */}
        <div className="flex-1 min-w-0 flex flex-col min-h-0 overflow-y-auto p-5 pb-6 space-y-4">
          {/* Hero (parity musicHero) */}
          <div className="ct-reveal rounded-2xl p-5 flex items-center gap-5 bg-gradient-to-br from-emerald-800/50 to-slate-900 border border-emerald-900/30">
            <div className={`ct-art-disc w-24 h-24 sm:w-32 sm:h-32 flex items-center justify-center text-5xl shrink-0 ${isLibraryPlaying ? 'ct-spinning' : ''}`}>
              {isLibraryPlaying ? <FileAudio className="w-12 h-12 text-emerald-300" /> : '♫'}
            </div>
            <div className="min-w-0">
              <div className="text-emerald-300 text-[10px] font-black tracking-widest uppercase">{tr('music_now_playing_kicker')}</div>
              <div className="text-2xl font-black truncate">{nowTitle || tr('music_nothing_playing')}</div>
              <div className="text-sm text-slate-300 truncate">{nowArtist || tr('music_choose_track')}</div>
              {nowAlbum && <div className="text-[11px] text-slate-400 truncate">{nowAlbum}</div>}
              {(shuffle || repeat) && (
                <div className="flex items-center gap-1.5 mt-1">
                  {shuffle && <span title={tr('music_shuffle')} className="px-1.5 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">🔀 SHUFFLE</span>}
                  {repeat && <span title={tr('music_repeat')} className="px-1.5 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-sky-500/20 text-sky-300 border border-sky-400/40">🔁 REPEAT</span>}
                </div>
              )}
            </div>
          </div>

          {/* Toolbar: search + count */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder={tr('music_search_placeholder')}
                className="ct-input w-full rounded-full pl-9 pr-3 py-2 text-sm placeholder-slate-500" />
            </div>
            <span className="text-[11px] text-slate-500 whitespace-nowrap">{tr('music_track_count', { count: activeTracks.length })}</span>
          </div>

          {/* Track table (parity musicTracks) */}
          <div className="rounded-2xl border border-slate-800 bg-[#121212]">
            <table className="w-full text-left border-collapse">
              <thead className="sticky top-0 bg-[#121212] text-slate-400 text-[10px] uppercase tracking-wider">
                <tr>
                  <th className="px-3 py-2 w-8">#</th>
                  <th className="px-3 py-2">{tr('music_track_title')}</th>
                  <th className="px-3 py-2">{tr('music_artist')}</th>
                  <th className="px-3 py-2">{tr('music_album')}</th>
                  <th className="px-3 py-2 text-center">{tr('music_duration')}</th>
                  <th className="px-2 py-2 w-8" />
                </tr>
              </thead>
              <tbody>
                {filteredRows.length === 0 && (
                  <tr><td colSpan={6} className="px-3 py-10 text-center text-xs text-slate-600">{tr('music_no_results')}</td></tr>
                )}
                {filteredRows.map((r, idx) => renderRow(r, activeTracks.indexOf(r.path)))}
              </tbody>
            </table>
          </div>

          {/* Track context menu (parity _track_menu) */}
          {menuOpenFor !== null && filteredRows[menuOpenFor] && (() => {
            const r = filteredRows[menuOpenFor];
            const idx = activeTracks.indexOf(r.path);
            const otherPls = playlists.filter((p) => String(p.id) !== String(selectedPlaylistId));
            return (
              <div className="fixed inset-0 z-40" onClick={() => setMenuOpenFor(null)}>
                <div onClick={(e) => e.stopPropagation()}
                  className="absolute right-6 top-1/2 -translate-y-1/2 w-56 rounded-xl bg-slate-800 border border-slate-700 p-1 shadow-2xl text-xs">
                  <button onClick={() => { playLibraryPath(r.path); setMenuOpenFor(null); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-700">{tr('music_play')}</button>
                  <button onClick={() => { addToFavorites(r.path); setMenuOpenFor(null); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-700 flex items-center gap-2"><Heart className="w-3 h-3" />{tr('music_add_to_favorites')}</button>
                  <div className="px-3 py-1 text-slate-500 text-[10px] uppercase">{tr('music_move_to_playlist')}</div>
                  {otherPls.map((p) => <button key={p.id} onClick={() => { moveTrackTo(idx, p.id, false); setMenuOpenFor(null); }} className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-slate-700 pl-6">{p.name}</button>)}
                  {otherPls.length === 0 && <div className="px-3 py-1 pl-6 text-slate-600">{tr('music_no_tracks_to_save')}</div>}
                  <div className="px-3 py-1 text-slate-500 text-[10px] uppercase">{tr('music_copy_to_playlist')}</div>
                  {otherPls.map((p) => <button key={p.id} onClick={() => { moveTrackTo(idx, p.id, true); setMenuOpenFor(null); }} className="w-full text-left px-3 py-1.5 rounded-lg hover:bg-slate-700 pl-6 flex items-center gap-1.5"><FolderOutput className="w-3 h-3" />{p.name}</button>)}
                  <div className="border-t border-slate-700 mt-1 pt-1" />
                  <button onClick={() => { removeFromPlaylist(idx); setMenuOpenFor(null); }} className="w-full text-left px-3 py-2 rounded-lg hover:bg-rose-600/30 text-rose-300 flex items-center gap-2"><Trash2 className="w-3 h-3" />{tr('music_remove_from_playlist')}</button>
                </div>
              </div>
            );
          })()}
        </div>

        {/* ── Lyrics drawer (P58: refactor ke komponen + simpan/import/offset) ── */}
        {lyricsOpen && (
          <LyricsDrawer
            loading={lyricsLoading}
            plain={lyrics.plain}
            syncedLines={syncedLines}
            activeLine={activeLyricLine}
            source={lyrics.source}
            saved={lyrics.saved}
            offsetMs={lyrics.offsetMs}
            tr={tr}
            onRefresh={() => loadLyrics(playingFile, true)}
            onImportPick={() => importLyricsRef.current?.click()}
            onSave={saveLyrics}
            onDeleteSaved={deleteSavedLyrics}
            onOffset={(d) => shiftLyricsOffset(d)}
            onOffsetReset={() => shiftLyricsOffset(-lyrics.offsetMs)}
          />
        )}
      </div>

      {/* ── Persistent player deck (parity musicDeck) ── */}
      <div className="border-t border-slate-800/70 bg-[#181818] px-5 py-3">
        {/* Progress row */}
        <div className="flex items-center gap-3">
          <span className="text-[10px] text-slate-400 font-mono shrink-0">{fmtTime(dragging ? dragMs : progressMs)}</span>
          <input type="range" min={0} max={Math.max(1, durationMs)} value={dragging ? dragMs : progressMs}
            onPointerDown={() => { setDragging(true); setDragMs(progressMs); }}
            onChange={(e) => setDragMs(Number(e.target.value))}
            onPointerUp={(e) => { setDragging(false); music.seekMs(Number((e.target as HTMLInputElement).value)); }}
            onPointerCancel={() => setDragging(false)}
            className="flex-1 accent-emerald-500 h-1.5 bg-slate-700 rounded-lg" />
          <span className="text-[10px] text-slate-400 font-mono shrink-0">{fmtTime(durationMs)}</span>
        </div>
        {/* Controls row */}
        <div className="flex items-center gap-3 mt-1">
          <div className="min-w-0 flex-1 truncate text-sm font-bold flex items-center gap-2">
            {isLibraryPlaying ? (playingFile?.title || playingFile?.name) : tr('music_nothing_playing')}
            <span className={`ct-eq ${isPlaying ? 'is-playing' : ''}`}><span></span><span></span><span></span></span>
            {shuffle && <span title={tr('music_shuffle')} className="hidden sm:inline-flex shrink-0 items-center px-1.5 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-emerald-500/20 text-emerald-300 border border-emerald-400/40">🔀 SHUFFLE</span>}
            {repeat && <span title={tr('music_repeat')} className="hidden sm:inline-flex shrink-0 items-center px-1.5 py-0.5 rounded-full text-[9px] font-black tracking-wider bg-sky-500/20 text-sky-300 border border-sky-400/40">🔁 REPEAT</span>}
          </div>
          <button onClick={music.toggleShuffle} title={tr('music_shuffle')} aria-pressed={shuffle}
            className={`ct-btn ct-btn-ghost ct-btn-icon-sm rounded-full border ${shuffle ? 'text-emerald-300 bg-emerald-500/25 border-emerald-400/50' : 'text-slate-500 border-transparent hover:text-slate-300'}`}><Shuffle className="w-4 h-4" /></button>
          <button onClick={handlePrevTrack} title={tr('music_prev')} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400"><SkipBack className="w-5 h-5" /></button>
          <button onClick={toggleTrackPlay} className="ct-btn ct-btn-gold w-12 h-12 rounded-full justify-center">
            {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
          </button>
          <button onClick={handleNextTrack} title={tr('music_next')} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400"><SkipForward className="w-5 h-5" /></button>
          <button onClick={music.toggleRepeat} title={tr('music_repeat')} aria-pressed={repeat}
            className={`ct-btn ct-btn-ghost ct-btn-icon-sm rounded-full border ${repeat ? 'text-sky-300 bg-sky-500/25 border-sky-400/50' : 'text-slate-500 border-transparent hover:text-slate-300'}`}><Repeat className="w-4 h-4" /></button>
          <button onClick={toggleLyrics} className={`ct-tab ${lyricsOpen ? 'ct-tab-on' : ''}`}>
            <Sparkles className="w-3.5 h-3.5 inline mr-1" />{tr('music_lyrics')}
          </button>
          <div className="flex items-center gap-2">
            <button onClick={music.toggleMute} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400">
              {isMuted || volume === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
            </button>
            <input type="range" min={0} max={100} value={isMuted ? 0 : volume} onChange={(e) => music.setVolume(Number(e.target.value))}
              className="w-24 accent-emerald-500 h-1 bg-slate-700 rounded-lg" />
          </div>
        </div>
      </div>

      {/* P59: dialog ganti icon playlist (emoji / foto) */}
      {iconDlgFor && (
        <PlaylistIconDialog
          playlist={iconDlgFor}
          tr={tr}
          showToast={showToast}
          onClose={() => setIconDlgFor(null)}
          onSaved={() => { setIconDlgFor(null); refreshMusic(selectedPlaylistId); }}
        />
      )}

      {/* ── yt-dlp downloader modal (parity _open_downloader) ── */}
      {dlOpen && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="ct-dialog p-5 w-full max-w-2xl space-y-3 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-black flex items-center gap-2"><Download className="w-4 h-4 text-emerald-400" />{tr('music_download_title')}</h3>
              <button onClick={() => setDlOpen(false)} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400">✕</button>
            </div>
            <div className="flex gap-2">
              <input value={ytQuery} onChange={(e) => setYtQuery(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') searchYt(); }} placeholder={tr('music_search_web')}
                className="ct-input flex-1 rounded-xl px-3 py-2 text-sm" />
              <button onClick={searchYt} disabled={ytBusy} className="ct-btn ct-btn-success ct-btn-sm">{tr('music_btn_search')}</button>
            </div>
            <input value={ytUrl} onChange={(e) => setYtUrl(e.target.value)} placeholder={tr('music_url_placeholder')}
              className="ct-input w-full rounded-xl px-3 py-2 text-sm" />
            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400">{tr('music_target_playlist')}</span>
              <select value={String(dlTargetId || selectedPlaylistId || '')} onChange={(e) => setDlTargetId(e.target.value)}
                className="ct-input flex-1 rounded-xl px-2 py-1.5 text-sm text-slate-100">
                {playlists.map((p) => <option key={p.id} value={String(p.id)}>{p.name}</option>)}
              </select>
            </div>
            <div className="space-y-1 max-h-64 overflow-y-auto">
              {ytResults.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 text-xs p-2 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="truncate text-slate-200">{r.title}</span>
                  <button onClick={() => downloadYt(r.url)} className="ct-btn ct-btn-sm shrink-0 bg-emerald-500/20 text-emerald-300">{tr('music_btn_download')}</button>
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <button onClick={() => downloadYt(ytUrl)} className="ct-btn ct-btn-success ct-btn-sm w-full justify-center">{tr('music_download')}</button>
            </div>
            {ytJob && !ytJob.done && <p className="text-xs text-emerald-300">{tr('music_downloading', { pct: ytJob.percent || '0%' })}</p>}
          </div>
        </div>
      )}
    </div>
  );
};
