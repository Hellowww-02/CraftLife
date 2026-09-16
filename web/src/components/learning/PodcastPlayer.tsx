/**
 * PodcastPlayer.tsx — pemutar Audio Overview dua host (A08).
 *
 * Menggantikan pemutar lama yang memakai `window.speechSynthesis` TANPA `lang`,
 * sehingga suara Inggris membacakan teks Indonesia (dan terasa tidak interaktif).
 *
 * Sekarang: audio MP3 NYATA dari server (`POST /api/learning/podcast/audio`) dengan
 *   · suara mengikuti bahasa transkrip (id → Ardi & Gadis, en → Andrew & Ava, …);
 *   · **daftar giliran yang bisa diklik** → langsung melompat ke detik giliran itu;
 *   · giliran aktif **disorot otomatis** + auto-scroll saat mengikuti playback;
 *   · progress bar bisa di-drag, tombol ±15 detik, kecepatan 0,75×–2×, loop, unduh;
 *   · tombol **Buat voice** untuk menyusun audio (dengan status progres), dan
 *     **Buat ulang** bila ingin versi baru; cache di server membuat buka-ulang instan.
 */
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Headphones, Play, Pause, RotateCcw, RotateCw, Loader2, Download, Repeat,
  Mic, Gauge, CheckCircle2, AlertTriangle,
} from 'lucide-react';
import { downloadApiFile } from '../../api/client';

export interface PodcastTurn {
  index: number;
  speaker: 'A' | 'B' | string;
  voice?: string;
  text: string;
  startSec: number;
  endSec: number;
}

export interface PodcastAudioMeta {
  url: string;
  durationSec: number;
  sizeBytes?: number;
  language?: string;
  engine?: string;
  voiceA?: string;
  voiceB?: string;
  turns?: PodcastTurn[];
  createdAt?: string;
}

export interface PodcastPlayerProps {
  /** Meta audio tersimpan (null bila belum pernah dibuat). */
  audio: PodcastAudioMeta | null;
  /** Judul episode (dari judul artefak). */
  title?: string;
  generationId?: string;
  /** Ukuran font teks transkrip. */
  fontSize?: number;
  busy?: boolean;
  onGenerate: (force: boolean) => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
}

const RATES = [0.75, 1, 1.25, 1.5, 2];
const RATE_KEY = 'cl_learning_podcast_rate';

// localStorage dijaga (bisa tidak tersedia: render di server / mode privasi ketat).
function readSavedRate(): number {
  try {
    const saved = Number(localStorage.getItem(RATE_KEY));
    return RATES.includes(saved) ? saved : 1;
  } catch { return 1; }
}
function writeSavedRate(rate: number) {
  try { localStorage.setItem(RATE_KEY, String(rate)); } catch { /* abaikan */ }
}

/** Nama pendek suara: "id-ID-ArdiNeural" → "Ardi". */
export function shortVoice(voice?: string): string {
  const raw = String(voice || '').trim();
  if (!raw) return '';
  const part = raw.split('-').filter(Boolean);
  const last = part[part.length - 1] || raw;
  return last.replace(/Neural$/i, '').replace(/Multilingual$/i, '');
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(Number(seconds) || 0));
  const m = Math.floor(s / 60);
  const rest = s % 60;
  return `${m}:${String(rest).padStart(2, '0')}`;
}

/**
 * Giliran yang sedang berbunyi pada detik `time` (indeks di `turns`, -1 bila belum mulai).
 * Fungsi murni supaya bisa diuji tanpa browser.
 */
export function findActiveTurnIndex(turns: Array<{ startSec: number }>, time: number): number {
  if (!turns || !turns.length) return -1;
  let found = -1;
  for (let i = 0; i < turns.length; i += 1) {
    if (time + 0.05 >= turns[i].startSec) found = i;
    else break;
  }
  return found;
}

const PodcastPlayer: React.FC<PodcastPlayerProps> = ({
  audio, title, generationId, fontSize = 13, busy, onGenerate, tr,
}) => {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const turnRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [playing, setPlaying] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(Number(audio?.durationSec) || 0);
  const [rate, setRate] = useState<number>(readSavedRate);
  const [loop, setLoop] = useState(false);
  const [follow, setFollow] = useState(true);

  const turns = useMemo(() => (audio?.turns || []).slice().sort((a, b) => a.startSec - b.startSec), [audio]);

  useEffect(() => {
    setDuration(Number(audio?.durationSec) || 0);
    setTime(0);
    setPlaying(false);
  }, [audio?.url, audio?.durationSec]);

  useEffect(() => {
    writeSavedRate(rate);
    if (audioRef.current) audioRef.current.playbackRate = rate;
  }, [rate]);

  // Giliran aktif dihitung dari posisi waktu (bukan state terpisah per klik),
  // supaya sorotan selalu sinkron walau user men-drag progress bar.
  const activeIndex = useMemo(() => findActiveTurnIndex(turns, time), [turns, time]);

  useEffect(() => {
    if (!follow || activeIndex < 0) return;
    const el = turnRefs.current[activeIndex];
    if (el && listRef.current) {
      const box = listRef.current;
      const top = el.offsetTop - box.offsetTop;
      if (top < box.scrollTop || top + el.offsetHeight > box.scrollTop + box.clientHeight - 8) {
        box.scrollTo({ top: Math.max(0, top - 24), behavior: 'smooth' });
      }
    }
  }, [activeIndex, follow]);

  const toggle = useCallback(() => {
    const el = audioRef.current;
    if (!el) return;
    if (el.paused) {
      el.playbackRate = rate;
      void el.play();
    } else {
      el.pause();
    }
  }, [rate]);

  const seek = useCallback((seconds: number) => {
    const el = audioRef.current;
    if (!el) return;
    const next = Math.max(0, Math.min(seconds, Number.isFinite(el.duration) && el.duration > 0 ? el.duration : Infinity));
    el.currentTime = next;
    setTime(next);
  }, []);

  const hasAudio = Boolean(audio?.url && audio?.turns?.length);
  const src = audio?.url || '';
  const progress = duration > 0 ? Math.min(100, (time / duration) * 100) : 0;

  return (
    <div className="space-y-2.5">
      <audio
        ref={audioRef}
        src={src || undefined}
        preload="metadata"
        loop={loop}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => {
          const d = e.currentTarget.duration;
          if (Number.isFinite(d) && d > 0) setDuration(d);
        }}
        onError={() => setPlaying(false)}
        data-testid="podcast-audio"
        className="hidden"
      />

      {/* ── Kartu kontrol utama ── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3 space-y-2.5">
        <div className="flex items-center gap-2">
          <span className="w-8 h-8 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-violet-200 shrink-0">
            <Headphones className="w-4 h-4" />
          </span>
          <div className="min-w-0 flex-1">
            <h4 className="text-[12px] font-bold text-slate-100 truncate">
              {title || tr('learning_podcast_title', {}, 'Audio Overview')}
            </h4>
            <p className="text-[10px] text-slate-500 truncate">
              {hasAudio
                ? tr('learning_podcast_hosts_voices', {
                  a: shortVoice(audio?.voiceA) || 'A',
                  b: shortVoice(audio?.voiceB) || 'B',
                  lang: (audio?.language || 'id').toUpperCase(),
                }, 'Host {a} & {b} · suara {lang} · {n} giliran')
                : tr('learning_podcast_not_generated', {}, 'Transkrip siap. Buat voice untuk menghasilkan audio.')}
            </p>
          </div>
          {hasAudio && (
            <span className="ct-nlm-chip is-ok shrink-0">
              <CheckCircle2 className="w-3 h-3" />
              {tr('learning_podcast_ready', {}, 'Audio siap')}
            </span>
          )}
        </div>

        {hasAudio ? (
          <>
            {/* Progress + waktu: bisa diklik untuk seek */}
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400 tabular-nums w-9 text-right">{formatClock(time)}</span>
              <input
                type="range"
                min={0}
                max={Math.max(1, duration)}
                step={0.1}
                value={Math.min(time, duration || 0)}
                onChange={(e) => seek(Number(e.target.value))}
                className="flex-1 accent-violet-500 h-1.5 bg-slate-800 rounded-lg cursor-pointer"
                aria-label={tr('learning_podcast_seek', {}, 'Geser posisi audio')}
              />
              <span className="text-[10px] font-bold text-slate-400 tabular-nums w-9">{formatClock(duration)}</span>
            </div>

            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => seek(time - 15)}
                className="ct-btn ct-btn-secondary ct-btn-icon-sm p-1.5"
                title={tr('learning_podcast_back15', {}, 'Mundur 15 detik')}
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={toggle}
                className="ct-btn ct-btn-primary w-10 h-10 rounded-xl justify-center"
                title={playing ? tr('pause', {}, 'Pause') : tr('play', {}, 'Play')}
              >
                {playing ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4 ml-0.5" />}
              </button>
              <button
                onClick={() => seek(time + 15)}
                className="ct-btn ct-btn-secondary ct-btn-icon-sm p-1.5"
                title={tr('learning_podcast_fwd15', {}, 'Maju 15 detik')}
              >
                <RotateCw className="w-3.5 h-3.5" />
              </button>

              <button
                onClick={() => setRate(RATES[(RATES.indexOf(rate) + 1) % RATES.length])}
                className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1 ml-1"
                title={tr('learning_podcast_speed', {}, 'Kecepatan putar')}
              >
                <Gauge className="w-3.5 h-3.5" />
                {rate}×
              </button>
              <button
                onClick={() => setLoop((v) => !v)}
                className={`ct-btn ct-btn-sm flex items-center gap-1 ${loop ? 'ct-btn-primary' : 'ct-btn-secondary'}`}
                title={tr('learning_podcast_loop', {}, 'Putar berulang')}
              >
                <Repeat className="w-3.5 h-3.5" />
                {tr('learning_podcast_loop_short', {}, 'Loop')}
              </button>
              <button
                onClick={() => setFollow((v) => !v)}
                className={`ct-btn ct-btn-sm ${follow ? 'ct-btn-primary' : 'ct-btn-secondary'}`}
                title={tr('learning_podcast_follow', {}, 'Ikuti giliran otomatis')}
              >
                {tr('learning_podcast_follow_short', {}, 'Ikuti')}
              </button>
              <div className="ml-auto flex items-center gap-1.5">
                <button
                  onClick={() => downloadApiFile(src, `podcast-${generationId || 'audio'}.mp3`)}
                  className="ct-btn ct-btn-success ct-btn-sm flex items-center gap-1"
                  title={tr('learning_podcast_download', {}, 'Unduh MP3')}
                >
                  <Download className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{tr('learning_podcast_download_short', {}, 'MP3')}</span>
                </button>
                <button
                  onClick={() => onGenerate(true)}
                  disabled={busy}
                  className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1 disabled:opacity-50"
                  title={tr('learning_podcast_regenerate', {}, 'Buat ulang audio')}
                >
                  <Mic className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">{tr('learning_podcast_regenerate_short', {}, 'Buat ulang')}</span>
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => onGenerate(false)}
                disabled={busy}
                className="ct-btn ct-btn-primary flex items-center gap-2 disabled:opacity-60"
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mic className="w-4 h-4" />}
                {busy
                  ? tr('learning_podcast_generating', {}, 'Menyusun audio…')
                  : tr('learning_podcast_generate', {}, 'Buat voice')}
              </button>
              <span className="text-[10px] text-slate-500 leading-relaxed">
                {busy
                  ? tr('learning_podcast_generating_hint', {}, 'Suara dua host disusun per giliran — bisa 1–2 menit untuk episode panjang.')
                  : tr('learning_podcast_generate_hint', {}, 'Suara otomatis mengikuti bahasa transkrip (Indonesia → suara Indonesia).')}
              </span>
            </div>
          </div>
        )}

        {audio?.engine && hasAudio && (
          <p className="text-[9px] text-slate-500">
            {tr('learning_podcast_engine', { engine: audio.engine }, 'Mesin suara: {engine}')}
            {audio.sizeBytes ? ` · ${Math.round(audio.sizeBytes / 1024)} KB` : ''}
            {audio.durationSec ? ` · ${formatClock(audio.durationSec)}` : ''}
          </p>
        )}
      </div>

      {/* ── Daftar giliran (klik = lompat ke detiknya) ── */}
      <div ref={listRef} className="space-y-1.5 max-h-[340px] overflow-y-auto pr-1">
        {turns.map((turn, i) => {
          const isActive = i === activeIndex;
          const isA = String(turn.speaker).toUpperCase() === 'A' || String(turn.speaker).toLowerCase() === 'alex';
          return (
            <button
              key={`${turn.index}-${i}`}
              ref={(el) => { turnRefs.current[i] = el; }}
              onClick={() => {
                setFollow(true);
                seek(turn.startSec + 0.01);
                const el = audioRef.current;
                if (el && el.paused) void el.play();
              }}
              data-turn={i}
              data-start={turn.startSec}
              className={`w-full text-left p-2.5 rounded-xl border transition-colors flex gap-2.5 ${isActive
                ? 'bg-violet-600/20 border-violet-500/60'
                : isA ? 'bg-indigo-950/25 border-indigo-500/25 hover:border-indigo-400/50'
                  : 'bg-emerald-950/25 border-emerald-500/25 hover:border-emerald-400/50'}`}
            >
              <span className={`shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-[11px] font-black ${isA ? 'bg-indigo-500/20 text-indigo-200' : 'bg-emerald-500/20 text-emerald-200'}`}>
                {isA ? 'A' : 'B'}
              </span>
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-1.5 mb-0.5">
                  <span className={`text-[10px] font-bold uppercase tracking-wider ${isA ? 'text-indigo-300' : 'text-emerald-300'}`}>
                    {tr('learning_podcast_host', { n: isA ? 'A' : 'B' }, 'Host')}
                    {turn.voice ? ` · ${shortVoice(turn.voice)}` : ''}
                  </span>
                  <span className="text-[9px] text-slate-500 tabular-nums">{formatClock(turn.startSec)}</span>
                  {isActive && playing && (
                    <span className="text-[9px] text-violet-300 font-bold">
                      {tr('learning_podcast_now', {}, 'berbunyi…')}
                    </span>
                  )}
                </span>
                <span
                  style={{ fontSize: `${fontSize}px` }}
                  className={`block leading-relaxed ${isActive ? 'text-slate-100' : 'text-slate-300'}`}
                >
                  {turn.text}
                </span>
              </span>
            </button>
          );
        })}
        {!turns.length && (
          <div className="py-6 text-center text-slate-500">
            <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-slate-600" />
            <p className="text-[11px]">
              {tr('learning_podcast_no_turns', {}, 'Belum ada giliran yang bisa diputar.')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PodcastPlayer;
