import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { life } from '../api/life';
import { t } from '../i18n';

/**
 * TaskTemplateDialog — parity for PyQt `HabitTemplateDialog` (MainPyQt6.py).
 *
 * Opens a scrolled list of ready-made template packs for the given mode
 * (habit / daily / todo / sport). Each card shows an icon, localized name,
 * description and item count, plus an "Apply" button. Applying adds the pack
 * to the local DB (db.apply_template_by_mode) and shows a success toast.
 *
 * This replaces the previous hardcoded single-template button in
 * HabitsView / DailiesView / QuestsView (which was a simplified React
 * implementation, NOT PyQt parity).
 */
export const TaskTemplateDialog: React.FC<{
  mode: string;
  open: boolean;
  onClose: () => void;
}> = ({ mode, open, onClose }) => {
  const { lang, showToast } = useGame();
  const [templates, setTemplates] = useState<{
    key: string;
    icon: string;
    name: string;
    desc: string;
    count: number;
  }[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    life
      .listTemplates(mode)
      .then((r) => {
        if (Array.isArray(r?.templates)) setTemplates(r.templates);
        else setTemplates([]);
      })
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, [open, mode]);

  const apply = (tpl: { key: string; name: string }) => {
    life
      .applyTemplate(mode, tpl.key)
      .then((res) => {
        const n = res?.result?.count ?? res?.count ?? 0;
        showToast(
          'success',
          t('template_title', '📋 Template Habit Siap Pakai'),
          t('template_applied', `{n} habit dari template '{name}' ditambahkan! 🎉`)
            .replace('{n}', String(n))
            .replace('{name}', tpl.name)
        );
        onClose();
      })
      .catch((e) => {
        showToast('info', String(e?.message || e), '');
      });
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
      <div className="max-w-lg w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-hidden flex flex-col">
        <div>
          <h3 className="text-lg font-black text-slate-100">
            {t('template_title', '📋 Template Habit Siap Pakai')}
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            {t(
              'template_subtitle',
              'Pilih paket, langsung dapat daftar habit — bisa diedit lagi nanti.'
            )}
          </p>
        </div>

        <div className="space-y-2 overflow-y-auto pr-1">
          {loading && (
            <p className="text-xs text-slate-400 py-6 text-center">
              {lang === 'id' ? 'Memuat…' : 'Loading…'}
            </p>
          )}

          {!loading && templates.length === 0 && (
            <p className="text-xs text-slate-400 py-6 text-center">
              {t('template_no_templates', 'Belum ada template untuk kategori ini.')}
            </p>
          )}

          {!loading &&
            templates.map((tpl) => (
              <div
                key={tpl.key}
                className="flex items-center gap-3 p-3 rounded-xl bg-slate-800/60 border border-slate-700"
              >
                <span className="text-2xl shrink-0">{tpl.icon || '📋'}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-bold text-slate-100">{tpl.name}</div>
                  {tpl.desc && (
                    <div className="text-[11px] text-slate-400 leading-relaxed">{tpl.desc}</div>
                  )}
                  <div className="text-[11px] text-slate-500 mt-0.5">
                    {t('template_count', '{n} habit').replace('{n}', String(tpl.count))}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => apply(tpl)}
                  className="px-3 py-1.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shrink-0"
                >
                  {t('template_apply', '⚡ Terapkan')}
                </button>
              </div>
            ))}
        </div>

        <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
          >
            {lang === 'id' ? 'Tutup' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  );
};
