import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { studio } from '../api/studio';
import { stopReminderLoop } from '../utils/sound';
import { stopPomoAlarm } from '../utils/pomoAlarm';

/**
 * P57 — Music Engine Global.
 * Semua state player + SATU elemen <audio> hidup di provider ini (dipasang di
 * App root, DI LUAR switch view) sehingga musik TIDAK berhenti saat pindah
 * halaman. MusicView menjadi "remote control"; Navbar menampilkan MiniPlayer.
 *
 * Context sengaja DIPISAH dari GameContext agar tick progress (timeupdate ±4×/dtk)
 * tidak me-render ulang seluruh konsumen GameContext — hanya MiniPlayer + MusicView.
 */

export interface LibraryEntry {
  name: string;
  path: string;
  size: number;
  title?: string;
  artist?: string;
  album?: string;
  duration?: number;
}

export interface MusicPlayerApi {
  playingFile: LibraryEntry | null;
  /** True bila ada trek dari library yang sedang diputar (parity isLibraryPlaying). */
  isPlayingLibrary: boolean;
  isPlaying: boolean;
  shuffle: boolean;
  repeat: boolean;
  volume: number;
  isMuted: boolean;
  progressMs: number;
  durationMs: number;
  /** Antrean (snapshot playlist saat mulai main) — next/prev mengikuti antrean ini. */
  queue: LibraryEntry[];
  playFile: (entry: LibraryEntry, queue?: LibraryEntry[]) => void;
  togglePlay: () => void;
  next: () => void;
  prev: () => void;
  seekMs: (ms: number) => void;
  setVolume: (v: number) => void;
  toggleMute: () => void;
  toggleShuffle: () => void;
  toggleRepeat: () => void;
  /** Hentikan total (logout / ditutup shell PyQt): pause + reset + hentikan alarm. */
  stopAll: () => void;
}

const MusicPlayerContext = createContext<MusicPlayerApi | null>(null);

export const useMusicPlayer = (): MusicPlayerApi => {
  const ctx = useContext(MusicPlayerContext);
  if (!ctx) throw new Error('useMusicPlayer must be used within <MusicPlayerProvider>');
  return ctx;
};

export const MusicPlayerProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [playingFile, setPlayingFile] = useState<LibraryEntry | null>(null);
  const [queue, setQueueState] = useState<LibraryEntry[]>([]);
  const [isPlaying, setIsPlaying] = useState(true);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const [volume, setVolumeState] = useState<number>(72); // parity audio_output.setVolume(.72)
  const [isMuted, setIsMuted] = useState(false);
  const [progressMs, setProgressMs] = useState(0);
  const [durationMs, setDurationMs] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Salinan state utk handler event audio (listener di-attach SEKALI, tanpa re-attach).
  const stateRef = useRef({
    playingFile: null as LibraryEntry | null,
    queue: [] as LibraryEntry[],
    shuffle: false,
    repeat: false,
  });
  useEffect(() => {
    stateRef.current = { playingFile, queue, shuffle, repeat };
  }, [playingFile, queue, shuffle, repeat]);

  // Satu playSrc agar tidak ada race re-render yang menimpa src + membatalkan
  // play (parity QMediaPlayer / P16 fix).
  const playSrc = playingFile ? `/music/stream?path=${encodeURIComponent(playingFile.path)}` : '';

  const playFile = useCallback((entry: LibraryEntry, queueEntries?: LibraryEntry[]) => {
    setPlayingFile(entry);
    setQueueState(queueEntries && queueEntries.length ? queueEntries : [entry]);
    setIsPlaying(true);
    setProgressMs(0);
    setDurationMs(0);
    // Parity: setiap play tercatat di history — termasuk auto-advance yang kini
    // bisa terjadi saat user berada di halaman lain (player global).
    studio.logMusic(entry.path, entry.title || entry.name, entry.artist || '').catch(() => {});
  }, []);

  const next = useCallback(() => {
    const { queue: q, shuffle: sh } = stateRef.current;
    if (!q.length) return;
    let idx = q.findIndex((e) => e.path === stateRef.current.playingFile?.path);
    if (idx < 0) idx = 0;
    if (sh && q.length > 1) {
      const choices = q.filter((_, i) => i !== idx);
      playFile(choices[Math.floor(Math.random() * choices.length)], q);
    } else {
      playFile(q[(idx + 1) % q.length], q);
    }
  }, [playFile]);

  const prev = useCallback(() => {
    const a = audioRef.current;
    if (a && a.currentTime > 3) { a.currentTime = 0; return; } // parity _previous: pos>3dtk restart
    const { queue: q } = stateRef.current;
    if (!q.length) return;
    let idx = q.findIndex((e) => e.path === stateRef.current.playingFile?.path);
    if (idx < 0) idx = 0;
    playFile(q[(idx - 1 + q.length) % q.length], q);
  }, [playFile]);

  const togglePlay = useCallback(() => setIsPlaying((p) => !p), []);
  const toggleShuffle = useCallback(() => setShuffle((s) => !s), []);
  const toggleRepeat = useCallback(() => setRepeat((r) => !r), []);
  const toggleMute = useCallback(() => setIsMuted((m) => !m), []);
  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
    if (v > 0) setIsMuted(false);
  }, []);

  const seekMs = useCallback((ms: number) => {
    const a = audioRef.current;
    if (a && a.duration) { a.currentTime = ms / 1000; setProgressMs(ms); }
  }, []);

  const stopAll = useCallback(() => {
    const a = audioRef.current;
    if (a) {
      try { a.pause(); a.removeAttribute('src'); a.load(); } catch { /* ignore */ }
    }
    setPlayingFile(null);
    setQueueState([]);
    setIsPlaying(false);
    setProgressMs(0);
    setDurationMs(0);
    // Alarm pomodoro/reminder (WebAudio + loop) ikut dihentikan.
    try { stopReminderLoop(); } catch { /* ignore */ }
    try { stopPomoAlarm(); } catch { /* ignore */ }
    // Fallback: elemen audio/video lain yang mungkin tersebar di DOM.
    try {
      document.querySelectorAll('audio,video').forEach((el) => { (el as HTMLMediaElement).pause(); });
    } catch { /* ignore */ }
  }, []);

  // ── Audio element events (parity _connect_player; listener SEKALI) ────────
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => setProgressMs((audio.currentTime || 0) * 1000);
    const onDur = () => setDurationMs((audio.duration || 0) * 1000);
    const onEnded = () => {
      // parity _media_status_changed: repeat → ulangi; else auto-advance next().
      if (stateRef.current.repeat) { audio.currentTime = 0; audio.play().catch(() => {}); return; }
      next();
    };
    audio.addEventListener('timeupdate', onTime);
    audio.addEventListener('durationchange', onDur);
    audio.addEventListener('ended', onEnded);
    return () => {
      audio.removeEventListener('timeupdate', onTime);
      audio.removeEventListener('durationchange', onDur);
      audio.removeEventListener('ended', onEnded);
    };
  }, [next]);

  // P16 fix parity: play/pause terpusat pada source yang SUDAH dikommit React.
  useEffect(() => {
    const a = audioRef.current;
    if (!a) return;
    a.volume = (isMuted ? 0 : volume) / 100;
    if (isPlaying && playSrc) { a.play().catch(() => {}); }
    else if (!isPlaying) { a.pause(); }
  }, [playSrc, isPlaying, volume, isMuted]);

  // P57: hook global untuk shell PyQt (web_shell.closeEvent / MainPyQt6._logout)
  // dan untuk logout dari UI web — musik berhenti seketika.
  useEffect(() => {
    (window as any).craftlifeStopAllAudio = () => stopAll();
    return () => {
      try { delete (window as any).craftlifeStopAllAudio; } catch { /* ignore */ }
    };
  }, [stopAll]);

  const value: MusicPlayerApi = {
    playingFile,
    isPlayingLibrary: playingFile !== null,
    isPlaying,
    shuffle,
    repeat,
    volume,
    isMuted,
    progressMs,
    durationMs,
    queue,
    playFile,
    togglePlay,
    next,
    prev,
    seekMs,
    setVolume,
    toggleMute,
    toggleShuffle,
    toggleRepeat,
    stopAll,
  };

  return (
    <MusicPlayerContext.Provider value={value}>
      {children}
      {/* P57: elemen <audio> tunggal milik GLOBAL — di provider (App root, di
          luar switch view) sehingga tidak ikut hancur saat pindah halaman. */}
      <audio
        ref={audioRef}
        src={playSrc}
        preload="auto"
        onError={() => console.error('[MusicPlayer] audio error, src=', playSrc)}
      />
    </MusicPlayerContext.Provider>
  );
};
