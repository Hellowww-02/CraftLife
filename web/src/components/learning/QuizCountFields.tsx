import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { NumberInput } from '../NumberInput';

type TrFn = (key: string, vars?: Record<string, string | number>, fallback?: string) => string;

export const QUIZ_MC_MIN = 0;
export const QUIZ_MC_MAX = 30;
export const QUIZ_ESSAY_MIN = 0;
export const QUIZ_ESSAY_MAX = 30;
/** Total gabungan soal (PG + essay) tidak boleh melebihi angka ini — keputusan user. */
export const QUIZ_TOTAL_MAX = 30;
export const QUIZ_DEFAULT_MC = 10;
export const QUIZ_DEFAULT_ESSAY = 5;

export const QUIZ_PRESETS: { mc: number; essay: number; labelKey: string; fallback: string }[] = [
  { mc: 10, essay: 5, labelKey: 'learning_quiz_preset_default', fallback: '10 PG + 5 Esai' },
  { mc: 20, essay: 10, labelKey: 'learning_quiz_preset_full', fallback: '20 PG + 10 Esai' },
  { mc: 30, essay: 0, labelKey: 'learning_quiz_preset_mc_only', fallback: '30 PG saja' },
  { mc: 0, essay: 10, labelKey: 'learning_quiz_preset_essay_only', fallback: '10 Esai saja' },
];

/**
 * A04 — QuizCountFields: DUA counter terpisah untuk kuis.
 *
 * Sebelumnya hanya ada satu input `Jumlah (Kuis/Kartu)` (10–30) dan backend membagi
 * otomatis 70/30 PG:esai, sehingga user tidak bisa mengatur komposisi. Sekarang user
 * menentukan sendiri **jumlah PG** dan **jumlah essay**, dengan indikator total live
 * dan tombol preset. Total gabungan dijaga ≤ 30 di UI *dan* di server
 * (`learning_helper.generate_studio_content`).
 */
export const QuizCountFields: React.FC<{
  mc: number;
  essay: number;
  onMcChange: (n: number) => void;
  onEssayChange: (n: number) => void;
  tr: TrFn;
  disabled?: boolean;
  compact?: boolean;
}> = ({ mc, essay, onMcChange, onEssayChange, tr, disabled = false, compact = false }) => {
  const total = (Number(mc) || 0) + (Number(essay) || 0);
  const over = total > QUIZ_TOTAL_MAX;
  const zero = total <= 0;

  const inputCls = 'w-16 ml-auto bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-center text-slate-100 disabled:opacity-50';

  return (
    <div className={`space-y-2 ${compact ? '' : 'rounded-xl border border-slate-800 bg-slate-950/50 p-3'}`}>
      <div className="flex items-center gap-2 text-xs text-slate-300">
        <span className="mr-auto">{tr('learning_quiz_count_title', undefined, 'Jumlah soal kuis')}</span>
        <span
          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
            over || zero
              ? 'bg-rose-500/15 border-rose-500/40 text-rose-300'
              : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
          }`}
          title={tr('learning_quiz_total_count', { total }, 'Total: {total}/30')}
        >
          {tr('learning_quiz_total_count', { total }, 'Total: {total}/30')}
        </span>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span>{tr('learning_quiz_mc_count', undefined, 'Jumlah soal pilihan ganda')}</span>
        <NumberInput
          value={mc}
          onValueChange={onMcChange}
          min={QUIZ_MC_MIN}
          max={QUIZ_MC_MAX}
          integer
          emptyValue={0}
          disabled={disabled}
          inputClassName={inputCls}
        />
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span>{tr('learning_quiz_essay_count', undefined, 'Jumlah soal essay')}</span>
        <NumberInput
          value={essay}
          onValueChange={onEssayChange}
          min={QUIZ_ESSAY_MIN}
          max={QUIZ_ESSAY_MAX}
          integer
          emptyValue={0}
          disabled={disabled}
          inputClassName={inputCls}
        />
      </div>

      <div className="flex flex-wrap items-center gap-1.5">
        {QUIZ_PRESETS.map((p) => {
          const active = (Number(mc) || 0) === p.mc && (Number(essay) || 0) === p.essay;
          return (
            <button
              key={`${p.mc}_${p.essay}`}
              type="button"
              disabled={disabled}
              onClick={() => { onMcChange(p.mc); onEssayChange(p.essay); }}
              className={`px-2 py-1 rounded-lg text-[10px] font-bold border transition-colors disabled:opacity-50 ${
                active
                  ? 'bg-violet-600/30 border-violet-500/50 text-violet-200'
                  : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-violet-500/40'
              }`}
            >
              {tr(p.labelKey, undefined, p.fallback)}
            </button>
          );
        })}
      </div>

      {over && (
        <p className="flex items-start gap-1.5 text-[10px] text-rose-300">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {tr('learning_quiz_total_over', undefined, 'Total melebihi 30 soal — kurangi salah satu.')}
        </p>
      )}
      {!over && zero && (
        <p className="flex items-start gap-1.5 text-[10px] text-amber-300">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
          {tr('learning_quiz_total_zero', undefined, 'Isi minimal satu jenis soal.')}
        </p>
      )}
      <p className="text-[9px] text-slate-500">{tr('learning_quiz_answer_hint', undefined, 'Jawabanmu otomatis tersimpan sebagai draft.')}</p>
    </div>
  );
};
