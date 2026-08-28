import React, { useState, useRef, useEffect } from 'react';
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
  Radio,
  Sliders,
  Sparkles,
  Waves,
  Heart,
  Search,
  Disc,
} from 'lucide-react';

export const MusicView: React.FC = () => {
  const { lang, showToast } = useGame();

  const [tracks, setTracks] = useState<MusicTrack[]>(DEFAULT_MUSIC_TRACKS);
  const [currentTrackIndex, setCurrentTrackIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [activeCategory, setActiveCategory] = useState<'all' | 'lofi' | 'focus' | 'ambient' | 'synth'>('all');
  const [volume, setVolume] = useState<number>(75);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [trackProgress, setTrackProgress] = useState<number>(30); // 0 - 100%

  // Ambient sound mixer volumes
  const [ambientVolumes, setAmbientVolumes] = useState<Record<string, number>>({
    rain: 0,
    fire: 0,
    waves: 0,
    birds: 0,
    cafe: 0,
    wind: 0,
    whitenoise: 0,
  });

  // Audio elements ref
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const currentTrack = tracks[currentTrackIndex] || tracks[0];

  // Synthesizer Binaural Beat generator using Web Audio API
  const audioContextRef = useRef<AudioContext | null>(null);
  const oscRef = useRef<{ left: OscillatorNode; right: OscillatorNode; gain: GainNode } | null>(null);
  const [isSynthRunning, setIsSynthRunning] = useState<boolean>(false);
  const [synthPreset, setSynthPreset] = useState<'alpha' | 'beta' | 'theta' | 'delta'>('alpha');
  const [ytQuery, setYtQuery] = useState('');
  const [ytBusy, setYtBusy] = useState(false);
  const [ytResults, setYtResults] = useState<{ id: string; title: string; url: string }[]>([]);
  const [ytJob, setYtJob] = useState<{ done?: boolean; percent?: string } | null>(null);
  const [library, setLibrary] = useState<{ path: string; name: string }[]>([]);
  const [playlists, setPlaylists] = useState<{ id: string | number; name: string }[]>([]);

  useEffect(() => {
    studio.musicLibrary().then((d) => setLibrary(d.library || [])).catch(() => {});
    fetch('/api/music/playlists', { credentials: 'include' })
      .then((r) => r.json())
      .then((d) => setPlaylists(d.playlists || []))
      .catch(() => {});
  }, []);

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
        else {
          const lib = await studio.musicLibrary();
          setLibrary(lib.library || []);
        }
      };
      poll();
    } catch {
      showToast('damage', 'yt-dlp', 'download failed');
    }
  };

  const startBinauralSynth = (preset: 'alpha' | 'beta' | 'theta' | 'delta') => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
      }
      const ctx = audioContextRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      if (oscRef.current) {
        oscRef.current.left.stop();
        oscRef.current.right.stop();
      }

      const baseFreq = 220; // A3 base tone
      let beatFreq = 10; // Alpha
      if (preset === 'beta') beatFreq = 18;
      if (preset === 'theta') beatFreq = 6;
      if (preset === 'delta') beatFreq = 2;

      const merger = ctx.createChannelMerger(2);
      const gain = ctx.createGain();
      gain.gain.setValueAtTime(0.08, ctx.currentTime);

      const oscL = ctx.createOscillator();
      const oscR = ctx.createOscillator();

      oscL.type = 'sine';
      oscR.type = 'sine';
      oscL.frequency.setValueAtTime(baseFreq, ctx.currentTime);
      oscR.frequency.setValueAtTime(baseFreq + beatFreq, ctx.currentTime);

      oscL.connect(merger, 0, 0);
      oscR.connect(merger, 0, 1);
      merger.connect(gain);
      gain.connect(ctx.destination);

      oscL.start();
      oscR.start();

      oscRef.current = { left: oscL, right: oscR, gain };
      setIsSynthRunning(true);
      setSynthPreset(preset);
      showToast('info', 'Binaural Synth', `Generated ${preset.toUpperCase()} waves (${beatFreq}Hz)`);
    } catch {
      showToast('damage', 'Audio Warning', 'AudioContext is restricted in this environment.');
    }
  };

  const stopBinauralSynth = () => {
    if (oscRef.current) {
      try {
        oscRef.current.left.stop();
        oscRef.current.right.stop();
      } catch {}
      oscRef.current = null;
    }
    setIsSynthRunning(false);
  };

  const toggleTrackPlay = () => {
    const nextPlay = !isPlaying;
    setIsPlaying(nextPlay);
    if (audioRef.current) {
      if (nextPlay) {
        audioRef.current.play().catch(() => {});
      } else {
        audioRef.current.pause();
      }
    }
  };

  const handleNextTrack = () => {
    setCurrentTrackIndex((prev) => {
      if (shuffle) return Math.floor(Math.random() * Math.max(1, tracks.length));
      return prev < tracks.length - 1 ? prev + 1 : 0;
    });
    setIsPlaying(true);
  };

  const handlePrevTrack = () => {
    setCurrentTrackIndex((prev) => (prev > 0 ? prev - 1 : tracks.length - 1));
    setIsPlaying(true);
  };

  const filteredTracks = tracks.filter((t) => {
    const matchesCat = activeCategory === 'all' || t.category === activeCategory;
    const matchesSearch =
      t.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.artist.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCat && matchesSearch;
  });

  return (
    <div id="music-audio-studio-view" className="space-y-6">
      {/* Hidden HTML Audio element */}
      <audio
        ref={audioRef}
        src={currentTrack?.url}
        onEnded={repeat ? undefined : handleNextTrack}
        loop={repeat}
      />

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-2xl">
            🎵
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'id' ? 'Studio Musik & Suasana Fokus' : 'Music & Ambient Audio Studio'}</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-medium">
                Spotify & Lofi Inspired
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Dengarkan alunan lofi, campur efek suara alam, dan aktifkan gelombang binaural untuk fokus maksimal.'
                : 'Stream lofi focus tracks, mix ambient nature soundscapes, and trigger binaural frequencies.'}
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: Now Playing Hero & Playlist + Ambient Mixer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Spotify Style Player & Playlist */}
        <div className="lg:col-span-2 space-y-6">
          {/* Hero Player Card */}
          <div className="p-6 bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-950 border border-slate-800 rounded-2xl space-y-6 shadow-xl">
            <div className="flex flex-col sm:flex-row items-center gap-6">
              <div className="w-28 h-28 sm:w-32 sm:h-32 rounded-2xl bg-slate-900 border border-emerald-500/30 flex items-center justify-center text-5xl shadow-2xl shrink-0">
                {currentTrack?.coverEmoji || '🎧'}
              </div>
              <div className="space-y-1 text-center sm:text-left flex-1">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">Now Playing</span>
                <h2 className="text-xl font-bold text-slate-100">{currentTrack?.title || 'Relaxing Beats'}</h2>
                <p className="text-sm text-slate-400">{currentTrack?.artist || 'CraftLife Focus Radio'}</p>
                <div className="flex items-center justify-center sm:justify-start gap-2 pt-2">
                  <span className="text-xs px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono">
                    {currentTrack?.category?.toUpperCase()}
                  </span>
                  <span className="text-xs text-slate-500">{currentTrack?.duration || '3:30'}</span>
                </div>
              </div>
            </div>

            {/* Progress Scrub Bar */}
            <div className="space-y-1.5">
              <div
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const pct = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
                  setTrackProgress(pct);
                }}
                className="w-full h-2 bg-slate-800 rounded-full cursor-pointer overflow-hidden relative"
              >
                <div
                  className="h-full bg-emerald-500 rounded-full transition-all"
                  style={{ width: `${trackProgress}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-slate-500 font-mono">
                <span>01:15</span>
                <span>{currentTrack?.duration || '03:45'}</span>
              </div>
            </div>

            {/* Controls Center */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
              <div className="flex items-center gap-4 mx-auto sm:mx-0">
                <button
                  onClick={handlePrevTrack}
                  className="p-2 text-slate-400 hover:text-slate-100 transition-colors"
                >
                  <SkipBack className="w-5 h-5" />
                </button>
                <button
                  onClick={toggleTrackPlay}
                  className="w-14 h-14 rounded-2xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold flex items-center justify-center transition-all shadow-lg shadow-emerald-500/20"
                >
                  {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-1" />}
                </button>
                <button
                  onClick={handleNextTrack}
                  className="p-2 text-slate-400 hover:text-slate-100 transition-colors"
                >
                  <SkipForward className="w-5 h-5" />
                </button>
              </div>

              {/* Volume Slider */}
              <div className="flex items-center gap-2.5 mx-auto sm:mx-0">
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  {isMuted || volume === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </button>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => {
                    setVolume(Number(e.target.value));
                    setIsMuted(false);
                    if (audioRef.current) audioRef.current.volume = Number(e.target.value) / 100;
                  }}
                  className="w-24 accent-emerald-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                />
                <span className="text-xs text-slate-400 font-mono w-8">{isMuted ? '0%' : `${volume}%`}</span>
              </div>
            </div>
          </div>

          {/* Playlist & Tracks Table */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Disc className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Daftar Lagu Lofi & Fokus' : 'Focus Playlist Library'}</span>
              </h3>

              {/* Search & Category Filter */}
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search tracks..."
                    className="bg-slate-950 border border-slate-800 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>
            </div>

            <div className="flex gap-1.5 border-b border-slate-800 pb-3 text-xs">
              {(['all', 'lofi', 'focus', 'ambient', 'synth'] as const).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-3 py-1 rounded-lg capitalize font-medium transition-colors ${
                    activeCategory === cat ? 'bg-emerald-600/30 text-emerald-300 border border-emerald-500/30' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Tracks List */}
            <div className="space-y-1.5 max-h-[300px] overflow-y-auto pr-1">
              {filteredTracks.map((track, idx) => {
                const isSelected = track.id === currentTrack.id;
                return (
                  <div
                    key={track.id}
                    onClick={() => {
                      const realIndex = tracks.findIndex((t) => t.id === track.id);
                      if (realIndex !== -1) {
                        setCurrentTrackIndex(realIndex);
                        setIsPlaying(true);
                      }
                    }}
                    className={`p-3 rounded-xl border flex items-center justify-between gap-3 cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200 shadow-md'
                        : 'bg-slate-950/50 border-slate-800/80 text-slate-300 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{track.coverEmoji}</span>
                      <div>
                        <h4 className="font-semibold text-xs text-slate-100">{track.title}</h4>
                        <p className="text-[11px] text-slate-500">{track.artist}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono text-slate-500">{track.duration}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setTracks((prev) =>
                            prev.map((t) => (t.id === track.id ? { ...t, isFavorite: !t.isFavorite } : t))
                          );
                        }}
                        className={`p-1.5 ${track.isFavorite ? 'text-rose-400' : 'text-slate-600 hover:text-slate-400'}`}
                      >
                        <Heart className="w-3.5 h-3.5 fill-current" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right 1 Column: Ambient Sound Mixer & Binaural Synthesizer */}
        <div className="space-y-6">
          {/* Ambient Soundscapes Mixer */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Sliders className="w-4 h-4 text-emerald-400" />
                <span>{lang === 'id' ? 'Mixer Suara Alam' : 'Ambient Soundscape Mixer'}</span>
              </h3>
              <button
                onClick={() =>
                  setAmbientVolumes({ rain: 0, fire: 0, waves: 0, birds: 0, cafe: 0, wind: 0, whitenoise: 0 })
                }
                className="text-[11px] text-slate-500 hover:text-slate-300"
              >
                Reset
              </button>
            </div>

            <div className="space-y-3.5">
              {AMBIENT_SOUNDS.map((snd) => {
                const vol = ambientVolumes[snd.id] || 0;
                return (
                  <div key={snd.id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="flex items-center gap-2 text-slate-300">
                        <span>{snd.icon}</span>
                        <span>{lang === 'id' ? snd.nameId : snd.nameEn}</span>
                      </span>
                      <span className="font-mono text-slate-500 text-[11px]">{vol}%</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="100"
                      value={vol}
                      onChange={(e) =>
                        setAmbientVolumes((prev) => ({ ...prev, [snd.id]: Number(e.target.value) }))
                      }
                      className="w-full accent-emerald-500 h-1.5 bg-slate-950 rounded-lg cursor-pointer"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3">
            <h3 className="font-bold text-sm text-slate-200">
              {lang === 'id' ? 'Unduh musik (yt-dlp)' : 'Download music (yt-dlp)'}
            </h3>
            <div className="flex gap-2">
              <input
                value={ytQuery}
                onChange={(e) => setYtQuery(e.target.value)}
                placeholder={lang === 'id' ? 'Cari YouTube…' : 'Search YouTube…'}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-xs"
              />
              <button onClick={searchYt} disabled={ytBusy} className="px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold">
                {lang === 'id' ? 'Cari' : 'Search'}
              </button>
            </div>
            {ytJob && !ytJob.done && (
              <p className="text-xs text-emerald-300">{lang === 'id' ? 'Mengunduh' : 'Downloading'} {ytJob.percent}</p>
            )}
            <div className="space-y-1 max-h-40 overflow-y-auto">
              {ytResults.map((r) => (
                <div key={r.id} className="flex items-center justify-between gap-2 text-xs p-2 rounded-lg bg-slate-950 border border-slate-800">
                  <span className="truncate text-slate-200">{r.title}</span>
                  <button onClick={() => downloadYt(r.url)} className="shrink-0 px-2 py-1 rounded-lg bg-emerald-500/20 text-emerald-300">
                    {lang === 'id' ? 'Unduh' : 'Download'}
                  </button>
                </div>
              ))}
            </div>
            {library.length > 0 && (
              <div className="text-[11px] text-slate-500 space-y-0.5">
                {library.slice(0, 8).map((f) => (
                  <div key={f.path} className="flex items-center justify-between gap-2">
                    <span className="truncate">{f.name}</span>
                    {playlists[0] && (
                      <button
                        type="button"
                        className="shrink-0 text-emerald-400"
                        onClick={() => studio.addPlaylistTrack(playlists[0].id, f.path)}
                      >
                        +PL
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Binaural Frequency Synthesizer */}
          <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
                <Waves className="w-4 h-4 text-violet-400" />
                <span>{lang === 'id' ? 'Binaural Focus Synth' : 'Binaural Focus Synth'}</span>
              </h3>
              {isSynthRunning && (
                <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-violet-500/20 text-violet-300 font-bold animate-pulse">
                  ACTIVE
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {lang === 'id'
                ? 'Synthesizer frekuensi audio gelombang otak untuk konsentrasi, kreativitas, atau relaksasi.'
                : 'Generates dual frequency sine waves to guide brainwave states for deep work.'}
            </p>

            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={() => (isSynthRunning && synthPreset === 'alpha' ? stopBinauralSynth() : startBinauralSynth('alpha'))}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all text-left ${
                  isSynthRunning && synthPreset === 'alpha'
                    ? 'bg-violet-600 text-white border-violet-500'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div>Alpha 10Hz</div>
                <span className="text-[10px] font-normal text-slate-400">Deep Focus & Flow</span>
              </button>
              <button
                onClick={() => (isSynthRunning && synthPreset === 'beta' ? stopBinauralSynth() : startBinauralSynth('beta'))}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all text-left ${
                  isSynthRunning && synthPreset === 'beta'
                    ? 'bg-violet-600 text-white border-violet-500'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div>Beta 18Hz</div>
                <span className="text-[10px] font-normal text-slate-400">Problem Solving</span>
              </button>
              <button
                onClick={() => (isSynthRunning && synthPreset === 'theta' ? stopBinauralSynth() : startBinauralSynth('theta'))}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all text-left ${
                  isSynthRunning && synthPreset === 'theta'
                    ? 'bg-violet-600 text-white border-violet-500'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div>Theta 6Hz</div>
                <span className="text-[10px] font-normal text-slate-400">Creative Insight</span>
              </button>
              <button
                onClick={() => (isSynthRunning && synthPreset === 'delta' ? stopBinauralSynth() : startBinauralSynth('delta'))}
                className={`p-2.5 rounded-xl border text-xs font-bold transition-all text-left ${
                  isSynthRunning && synthPreset === 'delta'
                    ? 'bg-violet-600 text-white border-violet-500'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                <div>Delta 2Hz</div>
                <span className="text-[10px] font-normal text-slate-400">Rest & Sleep</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
