import React from 'react';
import { Play, Pause, SkipForward, Music2, Shuffle, Repeat } from 'lucide-react';
import { useMusicPlayer } from '../music/MusicPlayerContext';
import { t as i18nT } from '../i18n';

const t = (key: string, fallback: string) => i18nT(key, fallback);

/**
 * P57 — Mini-player global di Navbar: kontrol musik tetap terlihat dari
 * halaman mana pun (judul + play/pause + next). Klik judul → buka halaman Musik.
 */
export const MiniPlayer: React.FC<{ onOpenMusic?: () => void }> = ({ onOpenMusic }) => {
  const music = useMusicPlayer();
  if (!music.playingFile) return null;
  const title = music.playingFile.title || music.playingFile.name || '';
  return (
    <div
      className="flex items-center gap-0.5 pl-2 pr-1 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-200"
      title={`${t('music_miniplayer_now_playing', 'Sedang diputar')}: ${title}`}
    >
      <button
        type="button"
        onClick={onOpenMusic}
        className="flex items-center gap-1.5 min-w-0 group"
        title={t('music_miniplayer_open', 'Buka halaman Musik')}
      >
        <Music2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
        <span className={`ct-eq ${music.isPlaying ? 'is-playing' : ''}`}><span></span><span></span><span></span></span>
        <span className="hidden md:inline text-[11px] font-bold truncate max-w-[110px] lg:max-w-[180px] group-hover:text-white transition-colors">
          {title}
        </span>
      </button>
      {/* P59: indikator + toggle shuffle/repeat terlihat dari semua halaman. */}
      <button
        type="button"
        onClick={music.toggleShuffle}
        aria-pressed={music.shuffle}
        title={t('music_shuffle', 'Acak')}
        className={`p-1.5 rounded-lg hover:bg-emerald-500/20 transition-colors ${music.shuffle ? 'text-emerald-300 bg-emerald-500/20' : 'text-slate-400'}`}
      >
        <Shuffle className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        onClick={music.toggleRepeat}
        aria-pressed={music.repeat}
        title={t('music_repeat', 'Ulangi')}
        className={`p-1.5 rounded-lg hover:bg-sky-500/20 transition-colors ${music.repeat ? 'text-sky-300 bg-sky-500/20' : 'text-slate-400'}`}
      >
        <Repeat className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        onClick={music.togglePlay}
        className="p-1.5 rounded-lg hover:bg-emerald-500/20 transition-colors"
        title={music.isPlaying ? t('music_pause', 'Jeda') : t('music_play', 'Putar')}
      >
        {music.isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
      </button>
      <button
        type="button"
        onClick={music.next}
        className="p-1.5 rounded-lg hover:bg-emerald-500/20 transition-colors"
        title={t('music_next', 'Selanjutnya')}
      >
        <SkipForward className="w-3.5 h-3.5" />
      </button>
    </div>
  );
};
