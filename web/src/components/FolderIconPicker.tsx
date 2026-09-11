/**
 * FolderIconPicker.tsx — dialog pemilih ikon folder (P56).
 *
 * Dipakai TaskFolderBar (habits/dailies/quests/sport) untuk mengganti ikon
 * folder (kolom task_folders.icon, default 📁). Reusable: modal + grid emoji
 * + tombol reset.
 */
import React from 'react';
import { t } from '../i18n';

export const FOLDER_ICON_SET: string[] = [
  '📁', '📂', '📚', '📖', '📝', '🗂️', '💼', '🎓', '🔬', '💡', '🎯', '🧠',
  '⭐', '❤️', '🔥', '🌱', '🌍', '🌙', '☀️', '⚡', '✨', '🔮', '🏆', '🥇',
  '⚔️', '🛡️', '🏹', '🐉', '🧪', '⚗️', '🔭', '🧮', '💻', '🎮', '🎨', '🎵',
  '🏃', '💪', '🏋️', '🧘', '⚽', '🏀', '🎾', '🍎', '🥗', '🍳', '☕', '🛒',
  '💰', '🏦', '📈', '📉', '🐾', '🐶', '🐱', '🦊', '⏰', '📅', '✅', '🚀',
  '🛠️', '🧰', '🔧', '🏠', '🚗', '✈️', '🎁', '✉️',
];

export const FolderIconPicker: React.FC<{
  current: string;
  onPick: (icon: string) => void;
  onClose: () => void;
}> = ({ current, onPick, onClose }) => {
  const label = (icon: string) => (
    <button
      key={icon}
      type="button"
      onClick={() => onPick(icon)}
      className={`text-xl p-2 rounded-xl border transition-colors ${
        current === icon
          ? 'bg-cyan-500/20 border-cyan-500/60 ring-1 ring-cyan-400/40'
          : 'bg-slate-950 border-slate-800 hover:border-cyan-500/50'
      }`}
    >
      {icon}
    </button>
  );
  return (
    <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl p-5 max-w-sm w-full shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-bold text-slate-200">{t('folder_icon_picker_title', 'Pilih ikon folder')}</p>
          <button type="button" onClick={onClose} className="text-slate-400 text-lg leading-none hover:text-slate-200">×</button>
        </div>
        <div className="grid grid-cols-8 gap-1.5 max-h-64 overflow-y-auto pr-1">
          {FOLDER_ICON_SET.map((ic) => label(ic))}
        </div>
        <button
          type="button"
          onClick={() => onPick('📁')}
          className="mt-3 w-full py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-300"
        >
          {t('folder_icon_reset', 'Reset ke default 📁')}
        </button>
      </div>
    </div>
  );
};
