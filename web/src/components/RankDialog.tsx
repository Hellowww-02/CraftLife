import React from 'react';
import { t } from '../i18n';
import { X } from 'lucide-react';

/** Parity 1:1 dengan `RankListDialog` PyQt.
 * 10 rank tetap (score 0..90), badge status, footer progress skor. */
export interface RankInfo {
  rank: number; // index rank saat ini (0..9)
  icon: string;
  nameKey: string;
  descKey: string;
  score: number;
  maxScore: number;
}

const RANKS = [
  { minScore: 0, nameKey: 'rank_pemula', icon: '🥚', descKey: 'rank_desc_pemula' },
  { minScore: 10, nameKey: 'rank_penambang', icon: '⛏️', descKey: 'rank_desc_penambang' },
  { minScore: 20, nameKey: 'rank_penjelajah', icon: '🪓', descKey: 'rank_desc_penjelajah' },
  { minScore: 30, nameKey: 'rank_petualang', icon: '⚔️', descKey: 'rank_desc_petualang' },
  { minScore: 40, nameKey: 'rank_ksatria', icon: '🛡️', descKey: 'rank_desc_ksatria' },
  { minScore: 50, nameKey: 'rank_veteran', icon: '⭐', descKey: 'rank_desc_veteran' },
  { minScore: 60, nameKey: 'rank_legenda', icon: '🌟', descKey: 'rank_desc_legenda' },
  { minScore: 70, nameKey: 'rank_raja', icon: '👑', descKey: 'rank_desc_raja' },
  { minScore: 80, nameKey: 'rank_penguasa_naga', icon: '🐉', descKey: 'rank_desc_penguasa_naga' },
  { minScore: 90, nameKey: 'rank_dewa', icon: '🌌', descKey: 'rank_desc_dewa' },
];

export const RankDialog: React.FC<{ rank: RankInfo; onClose: () => void }> = ({ rank, onClose }) => {
  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm" onClick={onClose}>
      <div
        className="w-full max-w-lg max-h-[85vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-3"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-black text-slate-100">{t('rank_dialog_title', '🏆 Daftar Rank')}</h3>
          <button type="button" onClick={onClose} className="text-slate-400 hover:text-slate-200">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-2">
          {RANKS.map((r, i) => {
            const unlocked = rank.score >= r.minScore;
            const isCurrent = i === rank.rank;
            return (
              <div
                key={r.nameKey}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl ${
                  isCurrent
                    ? 'bg-slate-800 border-2 border-amber-500'
                    : unlocked
                      ? 'bg-slate-800 border border-slate-700'
                      : 'bg-slate-950 border border-dashed border-slate-800 opacity-60'
                }`}
              >
                <div className="text-3xl w-11 text-center shrink-0">{r.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold text-sm text-slate-100">{t(r.nameKey, r.nameKey)}</div>
                  <div className="text-[11px] text-slate-400">{t(r.descKey, r.descKey)}</div>
                  <div className="text-[10px] text-slate-500">
                    {t('rank_required_score', 'Butuh score: {score}').replace('{score}', String(r.minScore))}
                  </div>
                </div>
                {isCurrent ? (
                  <span className="shrink-0 text-amber-400 font-bold text-[11px] bg-amber-950/60 px-2.5 py-0.5 rounded-full">
                    {t('rank_current_badge', '⭐ SAAT INI')}
                  </span>
                ) : unlocked ? (
                  <span className="shrink-0 text-emerald-400 font-bold text-[11px] bg-emerald-950/50 px-2.5 py-0.5 rounded-full">
                    {t('rank_unlocked_badge', '✅ TERCAPAI')}
                  </span>
                ) : (
                  <span className="shrink-0 text-rose-400 font-bold text-[11px] bg-rose-950/40 px-2.5 py-0.5 rounded-full">
                    {t('rank_locked_badge', '🔒 TERKUNCI')}
                  </span>
                )}
              </div>
            );
          })}
        </div>

        <p className="text-center text-[11px] text-slate-400 pt-1">
          {t('rank_footer_progress', 'Score Anda: {score} / {max}')
            .replace('{score}', String(rank.score))
            .replace('{max}', String(rank.maxScore))}
        </p>
      </div>
    </div>
  );
};
