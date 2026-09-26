import React from 'react';
import { X } from 'lucide-react';
import { t } from '../i18n';
import { useEscapeClose } from '../hooks/useEscapeClose';
import { useFocusTrap } from '../hooks/useFocusTrap';

/**
 * D04 (v1.6.7): dialog bantuan pintasan keyboard global. Dibuka dengan tombol
 * `?` (App.tsx) — tidak mengubah satu pun perilaku shortcut yg sudah ada.
 */
export const ShortcutsDialog: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  useEscapeClose(true, onClose);
  const trapRef = useFocusTrap<HTMLDivElement>(true);
  const rows: [string, string][] = [
    ['Ctrl + K', t('shortcuts_palette', 'Buka palet perintah')],
    ['Esc', t('shortcuts_close', 'Tutup dialog / panel')],
    ['Enter', t('shortcuts_confirm', 'Kirim / konfirmasi')],
    ['?', t('shortcuts_help', 'Bantuan pintasan ini')],
  ];
  return (
    <div className="ct-backdrop fixed inset-0 z-[90] flex items-center justify-center p-4" onClick={onClose} role="dialog" aria-modal="true" aria-label={t('shortcuts_title', 'Pintasan keyboard')}>
      <div ref={trapRef} className="ct-dialog p-6 w-full max-w-sm space-y-3" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-black text-slate-100">{t('shortcuts_title', 'Pintasan keyboard')}</h3>
          <button type="button" onClick={onClose} className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400" aria-label={t('btn_close', 'Tutup')}>
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="space-y-2">
          {rows.map(([key, label]) => (
            <div key={key} className="flex items-center justify-between gap-3 text-xs">
              <span className="text-slate-400">{label}</span>
              <kbd className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 font-bold text-slate-200 whitespace-nowrap">
                {key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
