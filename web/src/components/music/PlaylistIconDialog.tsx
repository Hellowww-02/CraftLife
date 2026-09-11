import React, { useRef, useState } from 'react';
import { Image as ImageIcon, Upload, RotateCcw } from 'lucide-react';
import { studio } from '../../api/studio';

type TrFn = (key: string, vars?: Record<string, string | number>, fb?: string) => string;
type ShowToast = (type: 'boss' | 'success' | 'damage' | 'level_up' | 'info', title: string, message: string) => void;

export interface PlaylistEntryLite {
  id: string | number;
  name: string;
  icon?: string;
}

const PLAYLIST_EMOJIS = [
  '🎵', '🎶', '🎼', '🎤', '🎧', '🎸', '🎹', '🥁',
  '🎻', '🎺', '🎷', '🪕', '💽', '💿', '📻', '🔊',
  '💃', '🕺', '😎', '🔥', '⚡', '🌙', '☀️', '🌧️',
  '🌊', '🍀', '🌸', '🎮', '🚀', '⭐', '💜', '❤️',
  '🧠', '💪', '📚', '✈️', '🏠', '🐱', '🐶', '🍕',
  '☕', '🎉', '💎', '🏆', '🎧', '🎸', '🎹', '🥁',
];

const iconUrl = (icon: string) => `/api/music/playlist-icon/image?id=${icon.slice('photo:'.length)}`;

const renderIcon = (icon: string | undefined, sizeClass = 'w-8 h-8') =>
  icon && icon.startsWith('photo:')
    ? <img src={iconUrl(icon)} alt="" className={`${sizeClass} rounded-full object-cover`} />
    : <span className={`${sizeClass} flex items-center justify-center text-2xl`}>{icon || '🎵'}</span>;

/**
 * P59 — Dialog ganti icon playlist: tab Emoji (grid) atau Foto dari komputer
 * (resize otomatis ≤512px di server). Reset ke default 🎵 tersedia.
 */
export const PlaylistIconDialog: React.FC<{
  playlist: PlaylistEntryLite;
  tr: TrFn;
  showToast: ShowToast;
  onClose: () => void;
  onSaved: () => void;
}> = ({ playlist, tr, showToast, onClose, onSaved }) => {
  const [tab, setTab] = useState<'emoji' | 'photo'>('emoji');
  const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState<File | null>(null);
  const [pickUrl, setPickUrl] = useState('');
  const fileRef = useRef<HTMLInputElement | null>(null);

  const setEmoji = async (emoji: string) => {
    setBusy(true);
    try {
      const res = await studio.musicPlaylistIcon(playlist.id, emoji);
      if (res?.result?.ok) {
        showToast('success', tr('music_playlist_icon_ok'), '');
        onSaved();
      }
    } catch { /* ignore */ }
    setBusy(false);
  };

  const uploadPhoto = async () => {
    if (!pick) return;
    setBusy(true);
    try {
      const res = await studio.uploadPlaylistIcon(playlist.id, pick);
      if (res?.ok && res.icon) {
        showToast('success', tr('music_playlist_icon_ok'), '');
        onSaved();
      } else if (res?.error === 'file_too_large') {
        showToast('info', tr('music_playlist_icon_too_large'), '');
      } else if (res?.error === 'bad_type') {
        showToast('info', tr('photo_error_file_type'), '');
      }
    } catch { showToast('info', tr('music_playlist_icon_too_large'), ''); }
    setBusy(false);
  };

  return (
    <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="ct-dialog p-5 w-full max-w-md space-y-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-black flex items-center gap-2">
            <ImageIcon className="w-4 h-4 text-emerald-400" />
            {tr('music_playlist_icon_change')} — {playlist.name}
          </h3>
          <button onClick={onClose} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400">✕</button>
        </div>

        {/* Icon saat ini + reset */}
        <div className="flex items-center gap-3">
          {renderIcon(playlist.icon)}
          <div className="flex-1 text-xs text-slate-400">{playlist.name}</div>
          <button
            onClick={() => setEmoji('🎵')}
            disabled={busy}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 disabled:opacity-40"
          >
            <RotateCcw className="w-3 h-3" />{tr('music_playlist_icon_reset')}
          </button>
        </div>

        {/* Tab */}
        <div className="flex gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
          <button onClick={() => setTab('emoji')} className={`flex-1 py-1.5 rounded-lg text-[11px] font-bold ${tab === 'emoji' ? 'bg-emerald-600 text-white' : 'text-slate-400'}`}>
            {tr('music_playlist_icon_emoji')}
          </button>
          <button onClick={() => setTab('photo')} className={`flex-1 py-1.5 rounded-lg text-[11px] font-bold ${tab === 'photo' ? 'bg-emerald-600 text-white' : 'text-slate-400'}`}>
            {tr('music_playlist_icon_photo')}
          </button>
        </div>

        {tab === 'emoji' ? (
          <div className="grid grid-cols-8 gap-1.5 max-h-56 overflow-y-auto">
            {PLAYLIST_EMOJIS.map((e, i) => (
              <button key={`${e}_${i}`} onClick={() => setEmoji(e)} disabled={busy}
                className="aspect-square rounded-lg bg-slate-800 hover:bg-emerald-600/40 text-xl flex items-center justify-center transition-colors disabled:opacity-40">
                {e}
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            <input ref={fileRef} type="file" accept="image/*" className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0] || null;
                setPick(f);
                setPickUrl(f ? URL.createObjectURL(f) : '');
                e.target.value = '';
              }} />
            <div className="flex items-center gap-3">
              <div className="w-16 h-16 rounded-full overflow-hidden bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                {pickUrl ? <img src={pickUrl} alt="" className="w-full h-full object-cover" /> : <span className="text-2xl">🖼️</span>}
              </div>
              <button onClick={() => fileRef.current?.click()} disabled={busy}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-bold text-slate-200 disabled:opacity-40">
                <Upload className="w-3.5 h-3.5" />{tr('music_playlist_icon_photo')}
              </button>
              {pick && (
                <button onClick={uploadPhoto} disabled={busy}
                  className="px-3 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white disabled:opacity-40">
                  {busy ? '…' : 'OK'}
                </button>
              )}
            </div>
            <p className="text-[10px] text-slate-500">
              {tr('music_playlist_icon_hint')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
