import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useGame } from '../../context/GameContext';
import { DEFAULT_MUSIC_TRACKS, AMBIENT_SOUNDS } from '../../data/musicData';
import { MusicTrack } from '../../types';
import { studio } from '../../api/studio';
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  Volume2,
  VolumeX,
  Sliders,
  Sparkles,
  Waves,
  Heart,
  Search,
  Disc,
  Music2,
  ListMusic,
  Clock3,
  Trash2,
  FolderInput,
  FolderOutput,
  Plus,
  FileAudio,
} from 'lucide-react';

interface LibraryEntry {
  name: string;
  path: string;
  size: number;
  title?: string;
  artist?: string;
  album?: string;
  duration?: number;
}
interface PlaylistEntry {
  id: string | number;
  name: string;
  isFavorite?: number | boolean;
  tracks?: string[];
}
interface HistoryEntry {
  path?: string;
  title?: string;
  artist?: string;
  played_at?: string;
  created_at?: string;
}

const fmtDuration = (sec: number) => {
  if (!sec) return '';
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

export const MusicView: React.FC = () => {
  const { lang, showToast } = useGame();

  // Lofi default player
  const [tracks, setTracks] = useState<MusicTrack[]>(DEFAULT_MUSIC_TRACKS);
  const [currentTrackIndex, setCurrentTrackIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeCategory, setActiveCategory] = useState<'all' | 'lofi' | 'focus' | 'ambient' | 'synth'>('all');
  const [volume, setVolume] = useState<number>(75);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [trackProgress, setTrackProgress] = useState<number>(30);
  const [elapsed, setElapsed] = useState('01:15');

  // Real local-file playback state (parity dengan QMediaPlayer PyQt)
  const [playingFile, setPlayingFile] = useState<LibraryEntry | null>(null);
  const [isLibraryPlaying, setIsLibraryPlaying] = useState(false);

  // Ambient mixer
  const [ambientVolumes, setAmbientVolumes] = useState<Record<string, number>>({
    rain: 0, fire: 0, waves: 0, birds: 0, cafe: 0, wind: 0, whitenoise: 0,
  });

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscRef = useRef<{ left: OscillatorNode; right: OscillatorNode; gain: GainNode } | null>(null);
  const [isSynthRunning, setIsSynthRunning] = useState<boolean>(false);
  const [synthPreset, setSynthPreset] = useState<'alpha' | 'beta' | 'theta' | 'delta'>('alpha');

  // yt-dlp search/download
  const [ytQuery, setYtQuery] = useState('');
  const [ytBusy, setYtBusy] = useState(false);
  const [ytResults, setYtResults] = useState<{ id: string; title: string; url: string }[]>([]);
  const [ytJob, setYtJob] = useState<{ done?: boolean; percent?: string } | null>(null);

  // Library, playlists, history
  const [library, setLibrary] = useState<LibraryEntry[]>([]);
  const [playlists, setPlaylists] = useState<PlaylistEntry[]>([]);
  const [selectedPlaylistId, setSelectedPlaylistId] = useState<string | number | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [newPlaylistName, setNewPlaylistName] = useState('');

  // Lyrics
  const [lyricsOpen, setLyricsOpen] = useState(false);
  const [lyrics, setLyrics] = useState<{ plain: string; synced: string }>({ plain: '', synced: '' });
  const [lyricsLoading, setLyricsLoading] = useState(false);
  const [lyricsSource, setLyricsSource] = useState('');

  const currentTrack = tracks[currentTrackIndex] || tracks[0];

  const refreshMusic = useCallback(() => {
    return studio.musicPlaylists().then((d) => {
      const pls: PlaylistEntry[] = d.playlists || [];
      setPlaylists(pls);
      setHistory((d.history || []).map((h: any) => ({
        path: h.path || '', title: h.title || '', artist: h.artist || '',
        played_at: h.played_at || h.created_at || '',
      })));
      if (selectedPlaylistId === null && pls.length) setSelectedPlaylistId(pls[0].id);
    }).catch(() => {});
  }, [selectedPlaylistId]);

  useEffect(() => {
    studio.musicLibrary().then((d) => setLibrary(d.library || [])).catch(() => {});
    refreshMusic();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const activePlaylist = playlists.find((p) => p.id === selectedPlaylistId) ?? null;
  const activeTracks = activePlaylist?.tracks || [];

  const loadLyrics = useCallback((artist: string, title: string) => {
    if (!title) return;
    setLyricsLoading(true);
    setLyrics({ plain: '', synced: '' });
    setLyricsSource('');
    studio.musicLyrics(artist || '', title).then((res) => {
      // Defensive: hanya ambil field string dari respons; jangan pernah
      // menyimpan objek mentah ke state (mencegah React error #31).
      const d = res?.result || res || {};
      const plain = typeof d.plain === 'string' ? d.plain : (typeof d.lyrics === 'string' ? d.lyrics : '');
      const synced = typeof d.synced === 'string' ? d.synced : '';
      setLyrics({ plain, synced });
      setLyricsSource(typeof d.source === 'string' ? d.source : '');
      setLyricsLoading(false);
    }).catch(() => setLyricsLoading(false));
  }, []);

  const loadLyricsForCurrent = useCallback(() => {
    if (isLibraryPlaying && playingFile) {
      loadLyrics(playingFile.artist || '', playingFile.title || playingFile.name);
    } else {
      loadLyrics(currentTrack?.artist || '', currentTrack?.title || '');
    }
  }, [isLibraryPlaying, playingFile, currentTrack, loadLyrics]);

  const handlePlayLibraryFile = (entry: LibraryEntry) => {
    setPlayingFile(entry);
    setIsLibraryPlaying(true);
    setIsPlaying(true);
    if (audioRef.current) {
      audioRef.current.src = `/music/stream?path=${encodeURIComponent(entry.path)}`;
      audioRef.current.play().catch(() => {});
    }
    studio.logMusic(entry.path, entry.title || entry.name, entry.artist || '').then(() => refreshMusic()).catch(() => {});
    loadLyrics(entry.artist || '', entry.title || entry.name);
    showToast('info', 'Now Playing', entry.title || entry.name);
  };

  const playLofiTrack = (index: number) => {
    setIsLibraryPlaying(false);
    setPlayingFile(null);
    setCurrentTrackIndex(index);
    setIsPlaying(true);
    loadLyrics(tracks[index]?.artist || '', tracks[index]?.title || '');
  };

  const refreshLibrary = () => studio.musicLibrary().then((d) => setLibrary(d.library || [])).catch(() => {});

  const searchYt = async () => {
    if (!ytQuery.trim()) return;
    setYtBusy(true);
    try {
      const d = await studio.searchMusic(ytQuery.trim());
      const rows = d.results || d.result?.results || [];
      setYtResults(rows.map((x: any, i: number) => ({ id: String(x.id || i), title: x.title || x.url, url: x.url || x.webpage_url || '' })));
    } catch {
      showToast('damage', 'yt-dlp', 'search failed');
    } finally {
      setYtBusy(false);
    }
  };

  const downloadYt = async (url: string) => {
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
        else refreshLibrary();
      };
      poll();
    } catch {
      showToast('damage', 'yt-dlp', 'download failed');
    }
  };

  const createPlaylist = async () => {
    const name = newPlaylistName.trim();
    if (!name) return;
    await studio.createPlaylist(name).catch(() => {});
    setNewPlaylistName('');
    refreshMusic();
  };

  const renamePlaylist = (p: PlaylistEntry) => {
    const name = window.prompt(lang === 'id' ? 'Nama playlist baru' : 'New playlist name', p.name);
    if (!name?.trim()) return;
    studio.renamePlaylist(p.id, name.trim()).then(() => refreshMusic()).catch(() => {});
  };

  const deletePlaylist = (p: PlaylistEntry) => {
    if (p.isFavorite) { showToast('info', 'Playlist', lang === 'id' ? 'Tidak bisa menghapus favorit' : 'Cannot delete favorite'); return; }
    studio.deletePlaylist(p.id).then((r) => {
      const ok = r?.result?.ok;
      if (ok === false) showToast('damage', 'Playlist', lang === 'id' ? 'Gagal menghapus' : 'Delete failed');
      refreshMusic();
    }).catch(() => {});
  };

  const addToPlaylist = (path: string) => {
    if (!selectedPlaylistId) { showToast('info', 'Playlist', lang === 'id' ? 'Buat/pilih playlist dulu' : 'Create/select a playlist first'); return; }
    studio.addPlaylistTrack(selectedPlaylistId, path).then(() => refreshMusic()).catch(() => {});
  };

  const removeFromPlaylist = (index: number) => {
    if (selectedPlaylistId === null) return;
    studio.removePlaylistTrack(selectedPlaylistId, index).then(() => refreshMusic()).catch(() => {});
  };

  const moveTrackTo = (index: number, targetId: string | number | null, copy: boolean) => {
    if (!targetId || selectedPlaylistId === null || String(targetId) === String(selectedPlaylistId)) return;
    const fn = copy ? studio.copyPlaylistTrack : studio.movePlaylistTrack;
    fn(selectedPlaylistId, targetId, index).then(() => refreshMusic()).catch(() => {});
  };

  // Binaural synth
  const startBinauralSynth = (preset: 'alpha' | 'beta' | 'theta' | 'delta') => {
    try {
      if (!audioContextRef.current) audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') ctx.resume();
      if (oscRef.current) { oscRef.current.left.stop(); oscRef.current.right.stop(); }
      const baseFreq = 220;
      let beatFreq = 10;
      if (preset === 'beta') beatFreq = 18;
      if (preset === 'theta') beatFreq = 6;
      if (preset === 'delta') beatFreq = 2;
      const merger = ctx.createChannelMerger(2);
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.08, ctx.currentTime);
      const oscL = ctx.createOscillator();
      const oscR = ctx.createOscillator();
      oscL.type = 'sine'; oscR.type = 'sine';
      oscL.frequency.setValueAtTime(baseFreq, ctx.currentTime);
      oscR.frequency.setValueAtTime(baseFreq + beatFreq, ctx.currentTime);
      oscL.connect(merger, 0, 0); oscR.connect(merger, 0, 1);
      merger.connect(gain); gain.connect(ctx.destination);
      oscL.start(); oscR.start();
      oscRef.current = { left: oscL, right: oscR, gain };
      setIsSynthRunning(true); setSynthPreset(preset);
      showToast('info', 'Binaural Synth', `Generated ${preset.toUpperCase()} waves (${beatFreq}Hz)`);
    } catch {
      showToast('damage', 'Audio Warning', 'AudioContext is restricted in this environment.');
    }
  };
  const stopBinauralSynth = () => {
    if (oscRef.current) { try { oscRef.current.left.stop(); oscRef.current.right.stop(); } catch {} oscRef.current = null; }
    setIsSynthRunning(false);
  };

  // Audio progress
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => {
      const d = audio.duration || 0;
      const t = audio.currentTime || 0;
      if (d) setTrackProgress((t / d) * 100);
      const m = Math.floor(t / 60); const s = Math.floor(t % 60);
      setElapsed(`${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
    };
    const onEnded = () => {
      if (repeat) { audio.currentTime = 0; audio.play().catch(() => {}); return; }
      if (isLibraryPlaying) { setIsPlaying(false); return; }
      handleNextTrack();
    };
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('ended', onEnded);
    return () => { audio.removeEventListener('timeupdate', onTime); audio.removeEventListener('ended', onEnded); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repeat, isLibraryPlaying]);

  const handleNextTrack = () => {
    if (!isLibraryPlaying) setCurrentTrackIndex((p) => shuffle ? Math.floor(Math.random() * Math.max(1, tracks.length)) : (p < tracks.length - 1 ? p + 1 : 0));
    setIsPlaying(true);
  };
  const handlePrevTrack = () => {
    if (!isLibraryPlaying) setCurrentTrackIndex((p) => (p > 0 ? p - 1 : tracks.length - 1));
    setIsPlaying(true);
  };

  const toggleTrackPlay = () => {
    const nextPlay = !isPlaying;
    setIsPlaying(nextPlay);
    if (audioRef.current) {
      if (nextPlay) audioRef.current.play().catch(() => {}); else audioRef.current.pause();
    }
  };

  const toggleSongFavorite = (track: MusicTrack) => {
    setTracks((prev) => prev.map((t) => (t.id === track.id ? { ...t, isFavorite: !t.isFavorite } : t)));
  };

  const filteredTracks = tracks.filter((t) => {
    const matchesCat = activeCategory === 'all' || t.category === activeCategory;
    const matchesSearch = t.title.toLowerCase().includes(searchQuery.toLowerCase()) || t.artist.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  const libraryFiltered = library.filter((f) =>
    !searchQuery || `${f.title || f.name} ${f.artist || ''}`.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div id="music-audio-studio-view" className="space-y-6">
      <audio
        ref={audioRef}
        src={isLibraryPlaying && playingFile ? `/music/stream?path=${encodeURIComponent(playingFile.path)}` : currentTrack?.url}
        loop={false}
        onEnded={() => {}}
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-2xl">🎵</div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'id' ? 'Studio Musik & Suasana Fokus' : 'Music & Ambient Audio Studio'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-medium">Local • {isLibraryPlaying ? (playingFile?.title || playingFile?.name) : 'Lofi'}</span>
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'id' ? 'Putar file musik lokal, baca lirik, kelola playlist, dan aktifkan gelombang binaural.' : 'Play local music files, read lyrics, manage playlists, and trigger binaural frequencies.'}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Hero Player */}
          <div className="p-6 bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="w-28 h-28 sm:w-32 sm:h-32 rounded-2xl bg-slate-900 border border-emerald-500/30 flex items-center justify-center text-5xl shadow-2xl shrink-0">
                {isLibraryPlaying ? <FileAudio className="w-14 h-14 text-emerald-300" /> : (currentTrack?.coverEmoji || '🎧')}
              </div>
              <div className="space-y-1 text-center sm:text-left flex-1">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Now Playing</span>
                <h2 className="text-xl font-bold text-slate-100">
                  {isLibraryPlaying ? (playingFile?.title || playingFile?.name || 'Local Track') : (currentTrack?.title || 'Relaxing Beats')}
                </h2>
                <p className="text-sm text-slate-400">
                  {isLibraryPlaying ? (playingFile?.artist || 'Local file') : (currentTrack?.artist || 'CraftLife Focus Radio')}
                </p>
                <div className="flex items-center justify-center sm:justify-start gap-2 pt-2">
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                    {isLibraryPlaying ? 'LOCAL' : (currentTrack?.category?.toUpperCase() || 'LOFI')}
                  </span>
                  <span className="text-xs text-slate-500">{isLibraryPlaying ? fmtDuration(playingFile?.duration || 0) : (currentTrack?.duration || '3:30')}</span>
                </div>
              </div>
            </div>

            {/* Progress */}
            <div className="space-y-1.5">
              <div
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const pct = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
                  setTrackProgress(pct);
                  const a = audioRef.current;
                  if (a && a.duration) a.currentTime = (pct / 100) * a.duration;
                }}
                className="w-full h-2 bg-slate-800 rounded-full cursor-pointer overflow-hidden relative"
              >
                <div className="h-full bg-emerald-500 rounded-full transition-all" style={{ width: `${trackProgress}%` }} />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                <span>{elapsed}</span>
                <span>{isLibraryPlaying ? fmtDuration(playingFile?.duration || 0) : (currentTrack?.duration || '03:45')}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
              <div className="flex items-center gap-4 mx-auto sm:mx-0">
                <button onClick={handlePrevTrack} className="p-2 text-slate-400 hover:text-slate-100 transition-colors"><SkipBack className="w-5 h-5" /></button>
                <button onClick={toggleTrackPlay} className="w-14 h-14 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold flex items-center justify-center transition-all shadow-lg shadow-emerald-500/20">
                  {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-1" />}
                </button>
                <button onClick={handleNextTrack} className="p-2 text-slate-400 hover:text-slate-100 transition-colors"><SkipForward className="w-5 h-5" /></button>
              </div>
              <div className="flex items-center gap-2.5 mx-auto sm:mx-0">
                <button onClick={() => setIsMuted(!isMuted)} className="text-slate-400 hover:text-slate-200">
                  {isMuted || volume === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
                <input type="range" min="0" max="100" value={isMuted ? 0 : volume}
                  onChange={(e) => { setVolume(Number(e.target.value)); setIsMuted(false); if (audioRef.current) audioRef.current.volume = Number(e.target.value) / 100; }}
                  className="w-24 accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer" />
                <span className="text-xs text-slate-400 font-mono w-8">{isMuted ? '0%' : `${volume}%`}</span>
              </div>
            </div>

            {/* Lyrics toggle */}
            <div className="flex items-center justify-between gap-2 pt-1">
              <button onClick={() => { setLyricsOpen((o) => !o); if (!lyricsOpen) loadLyricsForCurrent(); }} className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs">
                <Sparkles className="w-3.5 h-3.5" />
                <span>{lang === 'id' ? 'Lirik' : 'Lyrics'}</span>
              </button>
              {lyricsOpen && (
                <div className="text-[10px] text-slate-500">
                  {lyricsLoading ? (lang === 'id' ? 'Mencari lirik…' : 'Searching lyrics…') : lyricsSource ? `via ${lyricsSource}` : (lang === 'id' ? 'Tidak ada lirik' : 'No lyrics')}
                </div>
              )}
            </div>
            {lyricsOpen && (
              <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/70 max-h-56 overflow-y-auto text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                {lyricsLoading ? <span className="text-slate-500">{lang === 'id' ? 'Mencari lirik…' : 'Searching…'}</span> : (lyrics.plain || lyrics.synced || (
                  <span className="text-slate-500 italic">{lang === 'id' ? 'Lirik tidak ditemukan untuk lagu ini.' : 'No lyrics found for this track.'}</span>
                ))}
              </div>
            )}
          </div>

          {/* Playlists */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <ListMusic className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Playlist' : 'Playlists'}</span>
              </h3>
              <div className="flex items-center gap-2">
                <input value={newPlaylistName} onChange={(e) => setNewPlaylistName(e.target.value)} placeholder={lang === 'id' ? 'Nama playlist…' : 'Playlist name…'}
                  className="bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500" />
                <button onClick={createPlaylist} className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs">
                  <Plus className="w-3.5 h-3.5" /> <span>{lang === 'id' ? 'Buat' : 'Create'}</span>
                </button>
              </div>
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {playlists.map((p) => (
                <button key={p.id} onClick={() => setSelectedPlaylistId(p.id)} onDoubleClick={() => renamePlaylist(p)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${selectedPlaylistId === p.id ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/40' : 'bg-slate-950 border border-slate-800 text-slate-400 hover:text-slate-200'}`}>
                  {p.isFavorite ? <Heart className="w-3 h-3 fill-rose-400 text-rose-400" /> : <Music2 className="w-3 h-3" />}
                  <span>{p.name}</span>
                </button>
              ))}
            </div>
            {selectedPlaylistId !== null && (
              <div className="flex items-center gap-2 text-xs">
                <span className="text-slate-400">{lang === 'id' ? 'Klik ganda untuk rename.' : 'Double-click to rename.'}</span>
                <button onClick={() => activePlaylist && deletePlaylist(activePlaylist)} className="px-2 py-1 rounded-lg bg-rose-500/20 text-rose-300"><Trash2 className="w-3 h-3" /></button>
              </div>
            )}
            {activePlaylist && activeTracks.length > 0 && (
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {activeTracks.map((path, idx) => {
                  const base = path.split(/[\\/]/).pop() || path;
                  return (
                    <div key={`${path}_${idx}`} className="p-2.5 rounded-xl border border-slate-800/80 bg-slate-950/50 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <FileAudio className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                        <button onClick={() => handlePlayLibraryFile({ path, name: base, title: base, size: 0 })} className="truncate text-xs text-slate-200 hover:text-emerald-300">{base}</button>
                      </div>
                      <div className="flex items-center gap-1.5 shrink-0">
                        <select title={lang === 'id' ? 'Pindah/salin ke' : 'Move/copy to'}
                          defaultValue=""
                          onChange={(e) => { if (e.target.value) moveTrackTo(idx, e.target.value, false); }}
                          className="bg-slate-800 border border-slate-700 rounded-lg text-[10px] text-slate-300 px-1 py-0.5">
                          <option value="">{lang === 'id' ? 'Pindah…' : 'Move…'}</option>
                          {playlists.filter((p) => String(p.id) !== String(selectedPlaylistId)).map((p) => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                          ))}
                        </select>
                        <button title={lang === 'id' ? 'Salin ke' : 'Copy to'} onClick={() => moveTrackTo(idx, playlists.find((p) => String(p.id) !== String(selectedPlaylistId))?.id ?? null, true)}
                          className="p-1 rounded-lg text-slate-400 hover:text-emerald-300"><FolderOutput className="w-3.5 h-3.5" /></button>
                        <button onClick={() => removeFromPlaylist(idx)} className="p-1 rounded-lg text-slate-400 hover:text-rose-400"><Trash2 className="w-3.5 h-3.5" /></button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {activePlaylist && activeTracks.length === 0 && (
              <p className="text-[11px] text-slate-500">{lang === 'id' ? 'Playlist kosong. Tambahkan lagu dari perpustakaan di bawah.' : 'Empty playlist. Add tracks from the library below.'}</p>
            )}
          </div>

          {/* Playlist & Lofi Tracks table */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Disc className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Daftar Lagu Lofi & Fokus' : 'Focus Playlist Library'}</span>
              </h3>
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search tracks..."
                  className="bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500" />
              </div>
            </div>
            <div className="flex gap-1.5 border-b border-slate-800 pb-3 text-xs flex-wrap">
              {(['all', 'lofi', 'focus', 'ambient', 'synth'] as const).map((cat) => (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1 rounded-lg capitalize font-medium transition-colors ${activeCategory === cat ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'}`}>
                  {cat}
                </button>
              ))}
            </div>
            <div className="space-y-1.5 max-h-[280px] overflow-y-auto pr-1">
              {filteredTracks.map((track, idx) => {
                const isSelected = !isLibraryPlaying && track.id === currentTrack.id;
                const realIndex = tracks.findIndex((t) => t.id === track.id);
                return (
                  <div key={track.id} onClick={() => playLofiTrack(realIndex)}
                    className={`p-3 rounded-xl border flex items-center justify-between gap-3 cursor-pointer transition-all ${isSelected ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200 shadow-md' : 'bg-slate-950/50 border-slate-800/80 text-slate-300 hover:border-slate-700'}`}>
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{track.coverEmoji}</span>
                      <div>
                        <h4 className="font-semibold text-xs text-slate-100">{track.title}</h4>
                        <p className="text-[11px] text-slate-500">{track.artist}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <button onClick={(e) => { e.stopPropagation(); loadLyrics(track.artist, track.title); }} title="Lyrics"><Sparkles className="w-3.5 h-3.5 text-slate-500 hover:text-emerald-300" /></button>
                      <span className="text-xs font-mono text-slate-500">{track.duration}</span>
                      <button onClick={(e) => { e.stopPropagation(); toggleSongFavorite(track); }}
                        className={`p-1.5 ${track.isFavorite ? 'text-rose-400' : 'text-slate-600 hover:text-slate-400'}`}>
                        <Heart className="w-3.5 h-3.5 fill-current" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Local Library */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <FolderInput className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Perpustakaan Lokal' : 'Local Library'}</span>
              </h3>
              <button onClick={refreshLibrary} className="text-[11px] text-slate-500 hover:text-slate-300">↻</button>
            </div>
            {library.length === 0 && <p className="text-[11px] text-slate-500">{lang === 'id' ? 'Unduh lagu melalui yt-dlp di bawah.' : 'Download tracks via yt-dlp below.'}</p>}
            <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
              {libraryFiltered.map((f) => (
                <div key={f.path} className="p-2 rounded-xl border border-slate-800/80 bg-slate-950/50 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <button onClick={() => handlePlayLibraryFile(f)} className="block truncate text-xs text-slate-200 hover:text-emerald-300 font-semibold">{f.title || f.name}</button>
                    <p className="text-[10px] text-slate-500 truncate">{f.artist || f.name}</p>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button onClick={() => handlePlayLibraryFile(f)} className="p-1.5 text-emerald-400">{isLibraryPlaying && playingFile?.path === f.path ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}</button>
                    <button onClick={() => loadLyrics(f.artist || '', f.title || f.name)} title="Lyrics"><Sparkles className="w-3.5 h-3.5 text-slate-400 hover:text-emerald-300" /></button>
                    <button onClick={() => addToPlaylist(f.path)} title="Add to playlist"><Plus className="w-3.5 h-3.5 text-slate-400 hover:text-emerald-300" /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Ambient mixer */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Mixer Suara Alam' : 'Ambient Soundscape Mixer'}</span>
              </h3>
              <button onClick={() => setAmbientVolumes({ rain: 0, fire: 0, waves: 0, birds: 0, cafe: 0, wind: 0, whitenoise: 0 })}
                className="text-[11px] text-slate-500 hover:text-slate-300">Reset</button>
            </div>
            <div className="space-y-3.5">
              {AMBIENT_SOUNDS.map((snd) => {
                const vol = ambientVolumes[snd.id] || 0;
                return (
                  <div key={snd.id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-2 text-slate-300"><span>{snd.icon}</span><span>{lang === 'id' ? snd.nameId : snd.nameEn}</span></span>
                      <span className="font-mono text-slate-500 text-[11px]">{vol}%</span>
                    </div>
                    <input type="range" min="0" max="100" value={vol}
                      onChange={(e) => setAmbientVolumes((prev) => ({ ...prev, [snd.id]: Number(e.target.value) }))}
                      className="w-full accent-emerald-500 h-1.5 bg-slate-950 rounded-lg cursor-pointer" />
                  </div>
                );
              })}
            </div>
          </div>

          {/* yt-dlp */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <h3 className="font-bold text-sm text-slate-200">{lang === 'id' ? 'Unduh musik (yt-dlp)' : 'Download music (yt-dlp)'}</h3>
            <div className="flex gap-2">
              <input value={ytQuery} onChange={(e) => setYtQuery(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') searchYt(); }}
                placeholder={lang === 'id' ? 'Cari YouTube…' : 'Search YouTube…'}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs" />
              <button onClick={searchYt} disabled={ytBusy} className="px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold">{lang === 'id' ? 'Cari' : 'Search'}</button>
            </div>
            {ytJob && !ytJob.done && <p className="text-xs text-emerald-300">{lang === 'id' ? 'Mengunduh' : 'Downloading'} {ytJob.percent}</p>}
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {ytResults.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 text-xs p-2 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="truncate text-slate-200">{r.title}</span>
                  <button onClick={() => downloadYt(r.url)} className="shrink-0 px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300">{lang === 'id' ? 'Unduh' : 'Download'}</button>
                </div>
              ))}
            </div>
          </div>

          {/* Binaural */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Waves className="w-4 h-4 text-violet-400" />
                <span>{lang === 'id' ? 'Binaural Focus Synth' : 'Binaural Focus Synth'}</span>
              </h3>
              {isSynthRunning && <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-bold animate-pulse">ACTIVE</span>}
            </div>
            <p className="text-xs text-slate-400">{lang === 'id' ? 'Synthesizer frekuensi audio gelombang otak untuk konsentrasi, kreativitas, atau relaksasi.' : 'Generates dual frequency sine waves to guide brainwave states for deep work.'}</p>
            <div className="grid grid-cols-2 gap-2">
              {([
                ['alpha', 'Alpha 10Hz', 'Deep Focus & Flow'],
                ['beta', 'Beta 18Hz', 'Problem Solving'],
                ['theta', 'Theta 6Hz', 'Creative Insight'],
                ['delta', 'Delta 2Hz', 'Rest & Sleep'],
              ] as const).map(([key, title, desc]) => (
                <button key={key}
                  onClick={() => (isSynthRunning && synthPreset === key ? stopBinauralSynth() : startBinauralSynth(key))}
                  className={`p-2.5 rounded-xl border text-xs font-bold transition-all text-left ${isSynthRunning && synthPreset === key ? 'bg-violet-600 text-white border-violet-500' : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'}`}>
                  <div>{title}</div>
                  <span className="text-[10px] font-normal text-slate-400">{desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Recently played */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
              <Clock3 className="w-4 h-4 text-emerald-400" />
              <span>{lang === 'id' ? 'Baru Diputar' : 'Recently Played'}</span>
            </h3>
            {history.length === 0 && <p className="text-[11px] text-slate-500">{lang === 'id' ? 'Belum ada riwayat.' : 'No play history yet.'}</p>}
            <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
              {history.slice(0, 20).map((h, i) => (
                <div key={`${h.path}_${i}`} className="flex items-center justify-between gap-2 text-xs p-2 rounded-lg bg-slate-950 border border-slate-800/70">
                  <div className="min-w-0">
                    <button onClick={() => { const p = h.path || ''; if (p) handlePlayLibraryFile({ path: p, name: p.split(/[\\/]/).pop() || '', title: h.title || p.split(/[\\/]/).pop() || '', artist: h.artist || '', size: 0 }); }}
                      className="block truncate text-slate-200 hover:text-emerald-300">{h.title || (h.path || '').split(/[\\/]/).pop()}</button>
                    <p className="text-[10px] text-slate-500">{h.artist || ''} · {h.played_at ? new Date(h.played_at).toLocaleString() : ''}</p>
                  </div>
                  <Play className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
