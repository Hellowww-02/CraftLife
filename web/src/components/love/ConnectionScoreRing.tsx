/**
 * ConnectionScoreRing.tsx — cincin skor kedekatan + rincian (A12).
 *
 * Komponen ini **tidak** menggambar cincin sendiri: ia menyusun `ProgressRing`
 * milik `web/src/components/charts.tsx` (satu sumber kebenaran SVG) dan
 * menambahkan rincian yang selama ini belum pernah terlihat di UI —
 * check-in terakhir, streak, dan rata-rata mood kedua sisi.
 */
import React from 'react';
import { ProgressRing } from '../charts';
import type { ScoreBreakdown } from './overviewUtils';

export interface ConnectionScoreRingProps {
  t: (k: string, fb: string) => string;
  trv: (k: string, vars: Record<string, string | number>, fb: string) => string;
  breakdown: ScoreBreakdown;
  lastCheckinText: string;
  size?: number;
}

export const ConnectionScoreRing: React.FC<ConnectionScoreRingProps> = ({
  t, trv, breakdown, lastCheckinText, size = 132,
}) => {
  const items = [
    { icon: '🗓️', label: t('love_score_last_checkin', 'Check-in terakhir'), value: lastCheckinText, testid: 'love-score-last' },
    { icon: '🔥', label: t('love_conn_streak_sub', 'Streak check-in'), value: trv('love_conn_streak', { n: breakdown.streak }, `${breakdown.streak} hari`), testid: 'love-score-streak' },
    { icon: '🙂', label: t('love_score_avg_my', 'Rata mood kamu'), value: String(breakdown.avgMy || '—'), testid: 'love-score-avg-my' },
    { icon: '💞', label: t('love_score_avg_partner', 'Rata mood pasangan'), value: String(breakdown.avgPartner || '—'), testid: 'love-score-avg-partner' },
  ];
  return (
    <div className="p-5 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-3" data-testid="love-score-card">
      <h3 className="font-bold text-sm text-slate-200">{t('love_score_ring', 'Skor kedekatan')}</h3>
      <div className="flex flex-col sm:flex-row items-center gap-4">
        <div className="relative shrink-0">
          <ProgressRing progress={Math.max(0, Math.min(1, breakdown.score / 100))} size={size} strokeWidth={11} color="#fb7185" />
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl font-extrabold text-rose-300 font-mono" data-testid="love-score-value">{breakdown.score}%</span>
            <span className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">
              {t('love_score_short', 'Kedekatan')}
            </span>
          </div>
        </div>
        <div className="flex-1 w-full space-y-1.5">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">
            {t('love_score_breakdown', 'Rincian')} · {trv('love_conn_stat_total', { n: breakdown.total }, `${breakdown.total} check-in`)}
          </p>
          {items.map((it) => (
            <div key={it.testid} className="flex items-center gap-2 text-xs" data-testid={it.testid}>
              <span className="shrink-0">{it.icon}</span>
              <span className="text-slate-400 flex-1 truncate">{it.label}</span>
              <span className="text-slate-100 font-bold font-mono">{it.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ConnectionScoreRing;
