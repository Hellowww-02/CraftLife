/**
 * StudioGenerateDialog.tsx — dialog konfigurasi per tipe generator Studio (A05).
 *
 * Sebelumnya klik kartu tipe di panel Studio LANGSUNG memanggil generator tanpa
 * konfigurasi apa pun (satu-satunya kontrol: counter global + topik). Sekarang setiap
 * tipe punya dialog sendiri (ala "Customize" NotebookLM) yang mengatur seluruh opsi
 * tipe tersebut, dengan pengaturan tersimpan per notebook.
 *
 * Komponen ini hanya mengurus UI + state lokal dialog; serialisasi payload dan
 * penyimpanan pengaturan ada di `studioOptions.ts` (dipakai juga oleh tombol ⚡).
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Sparkles, X, RotateCcw, FolderOpen, ChevronDown } from 'lucide-react';
import { NumberInput } from '../NumberInput';
import { QuizCountFields, QUIZ_TOTAL_MAX } from './QuizCountFields';
import {
  STUDIO_META, STUDIO_OPTIONS, StudioKind, StudioOption,
  studioDefaults, loadStudioConfig, saveStudioConfig, resetStudioConfig,
  buildStudioPayload,
} from './studioOptions';

export interface StudioGenerateDialogProps {
  kind: StudioKind;
  notebookId: string | number;
  /** Dipakai sebagai fallback jendela ringkas sumber. */
  sourcesCount: number;
  words: number;
  /** Helper i18n 3-argumen: (key, vars?, fallback?). */
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
  /** True saat generate berjalan — tombol dikunci. */
  busy?: boolean;
  onClose: () => void;
  onGenerate: (payload: Record<string, unknown>, cfg: Record<string, any>) => void;
}

const StudioGenerateDialog: React.FC<StudioGenerateDialogProps> = ({
  kind, notebookId, sourcesCount, words, tr, busy, onClose, onGenerate,
}) => {
  const meta = STUDIO_META[kind];
  const options = STUDIO_OPTIONS[kind] || [];
  const initial = useMemo(() => loadStudioConfig(notebookId, kind), [notebookId, kind]);
  const [cfg, setCfg] = useState<Record<string, any>>(initial);
  const [remember, setRemember] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [error, setError] = useState('');

  // Tutup dengan Esc (parity dialog lain di app).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const set = (id: string, value: any) => { setCfg((prev) => ({ ...prev, [id]: value })); setError(''); };

  const advancedOptions = options.filter((o) => o.advanced);
  const normalOptions = options.filter((o) => !o.advanced);

  // Validasi ringan sebelum kirim — server tetap memvalidasi ulang.
  const validate = (): string => {
    if (kind === 'quiz') {
      const total = (Number(cfg.mc) || 0) + (Number(cfg.essay) || 0);
      if (total <= 0) return tr('learning_quiz_total_zero', {}, 'Isi minimal satu jenis soal.');
      if (total > QUIZ_TOTAL_MAX) return tr('learning_quiz_total_over', {}, 'Total melebihi 30 soal — kurangi salah satu.');
    }
    if (kind === 'study-guide' && (!Array.isArray(cfg.sections) || cfg.sections.length === 0)) {
      return tr('learning_opt_sections_hint', {}, 'Minimal satu bagian harus dipilih.');
    }
    return '';
  };

  const submit = () => {
    const bad = validate();
    if (bad) { setError(bad); return; }
    if (remember) saveStudioConfig(notebookId, kind, cfg);
    onGenerate(buildStudioPayload(kind, cfg), cfg);
  };

  const renderOption = (opt: StudioOption) => {
    const label = tr(opt.labelKey, {}, opt.labelFallback);
    if (opt.kind === 'number') {
      return (
        <div key={opt.id} className="flex items-center gap-2 text-xs text-slate-400">
          <span className="flex-1">{label}</span>
          <NumberInput
            value={Number(cfg[opt.id] ?? opt.min ?? 0)}
            onValueChange={(n) => set(opt.id, n)}
            min={opt.min ?? 0}
            max={opt.max ?? 30}
            integer
            emptyValue={opt.min ?? 0}
            disabled={busy}
            inputClassName="w-16 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-center text-slate-100"
          />
        </div>
      );
    }
    if (opt.kind === 'choice') {
      return (
        <div key={opt.id} className="space-y-1.5">
          <span className="block text-xs text-slate-400">{label}</span>
          <div className="flex flex-wrap gap-1.5">
            {(opt.choices || []).map((c) => (
              <button
                key={c.value}
                type="button"
                disabled={busy}
                onClick={() => set(opt.id, c.value)}
                className={`px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border transition-colors disabled:opacity-50 ${
                  cfg[opt.id] === c.value
                    ? 'bg-violet-600/25 border-violet-500/60 text-violet-100'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-violet-500/40'
                }`}
              >
                {tr(c.labelKey, {}, c.labelFallback)}
              </button>
            ))}
          </div>
        </div>
      );
    }
    if (opt.kind === 'toggle') {
      const on = cfg[opt.id] !== false;
      return (
        <div key={opt.id} className="flex items-center gap-3 text-xs text-slate-400">
          <span className="flex-1">{label}</span>
          <button
            type="button"
            disabled={busy}
            onClick={() => set(opt.id, !on)}
            className={`relative w-10 h-5 rounded-full transition-colors ${on ? 'bg-violet-600' : 'bg-slate-700'}`}
            aria-pressed={on}
          >
            <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all ${on ? 'left-5' : 'left-0.5'}`} />
          </button>
        </div>
      );
    }
    if (opt.kind === 'multi') {
      const selected: string[] = Array.isArray(cfg[opt.id]) ? cfg[opt.id] : [];
      return (
        <div key={opt.id} className="space-y-1.5">
          <span className="block text-xs text-slate-400">{label}</span>
          <div className="flex flex-wrap gap-1.5">
            {(opt.multi || []).map((m) => {
              const active = selected.includes(m.value);
              return (
                <button
                  key={m.value}
                  type="button"
                  disabled={busy}
                  onClick={() => set(opt.id, active ? selected.filter((v) => v !== m.value) : [...selected, m.value])}
                  className={`px-2.5 py-1.5 rounded-lg text-[11px] font-semibold border transition-colors disabled:opacity-50 ${
                    active
                      ? 'bg-emerald-600/25 border-emerald-500/60 text-emerald-100'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-emerald-500/40'
                  }`}
                >
                  {active ? '✓ ' : ''}{tr(m.labelKey, {}, m.labelFallback)}
                </button>
              );
            })}
          </div>
        </div>
      );
    }
    // text
    return (
      <div key={opt.id} className="space-y-1.5">
        <span className="block text-xs text-slate-400">{label}</span>
        <textarea
          rows={opt.rows || 2}
          value={String(cfg[opt.id] ?? '')}
          disabled={busy}
          onChange={(e) => set(opt.id, e.target.value)}
          placeholder={opt.placeholderFallback}
          className="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-xs text-slate-100 resize-y focus:outline-none focus:border-violet-500"
        />
      </div>
    );
  };

  const quizTotal = (Number(cfg.mc) || 0) + (Number(cfg.essay) || 0);

  return (
    <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="ct-dialog max-w-lg w-full max-h-[88vh] overflow-y-auto p-5 space-y-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <div className="text-2xl leading-none mt-0.5">{meta.icon}</div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-base text-slate-100">
              {tr('learning_dialog_title', { type: tr(meta.labelKey, {}, meta.labelFallback) }, 'Konfigurasi {type}')}
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {tr(meta.blurbKey, {}, meta.blurbFallback)}
            </p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800" title={tr('btn_close', {}, 'Tutup')}>
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Sumber */}
        <div className="flex items-center gap-2 p-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-[11px] text-slate-300">
          <FolderOpen className="w-3.5 h-3.5 text-violet-300 shrink-0" />
          <span>{tr('learning_dialog_sources_summary', { sources: sourcesCount, words }, '{sources} sumber · {words} kata')}</span>
          {sourcesCount === 0 && <span className="text-amber-300">· {tr('learning_dialog_no_sources', {}, 'Belum ada sumber — hasil dari pengetahuan umum.')}</span>}
        </div>

        {/* Konfigurasi */}
        <div className="space-y-3">
          <span className="text-[10px] uppercase tracking-wider text-slate-500 font-bold">{tr('learning_dialog_config', {}, 'Konfigurasi')}</span>

          {/* A04 + A05: dua counter kuis dipindah ke dalam dialog (bukan lagi di panel). */}
          {kind === 'quiz' && (
            <QuizCountFields
              mc={Number(cfg.mc) || 0}
              essay={Number(cfg.essay) || 0}
              onMcChange={(n) => set('mc', n)}
              onEssayChange={(n) => set('essay', n)}
              tr={tr}
              disabled={!!busy}
            />
          )}

          {normalOptions.map(renderOption)}

          {advancedOptions.length > 0 && (
            <div className="pt-1 space-y-3 border-t border-slate-800/80">
              <button
                type="button"
                onClick={() => setShowAdvanced((v) => !v)}
                className="flex items-center gap-1.5 text-[11px] font-bold text-slate-400 hover:text-slate-200"
              >
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
                {tr('learning_dialog_advanced', {}, 'Pengaturan lanjutan')}
              </button>
              {showAdvanced && <div className="space-y-3">{advancedOptions.map(renderOption)}</div>}
            </div>
          )}
        </div>

        {/* Error validasi */}
        {error && <p className="text-[11px] text-rose-300 bg-rose-950/40 border border-rose-500/40 rounded-xl px-3 py-2">{error}</p>}

        {/* Footer */}
        <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-800/80">
          <label className="flex items-center gap-1.5 text-[10px] text-slate-400 cursor-pointer select-none">
            <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} className="accent-violet-500 w-3.5 h-3.5" />
            {tr('learning_dialog_remember', {}, 'Ingat pengaturan ini untuk notebook ini')}
          </label>
          <button
            type="button"
            onClick={() => { setCfg(resetStudioConfig(notebookId, kind)); setError(''); }}
            className="ml-auto flex items-center gap-1.5 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-[11px] rounded-xl"
          >
            <RotateCcw className="w-3.5 h-3.5" />{tr('learning_dialog_reset_default', {}, 'Reset ke default')}
          </button>
          <button onClick={onClose} className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-[11px] rounded-xl">
            {tr('msg_cancel', {}, 'Batal')}
          </button>
          <button
            onClick={submit}
            disabled={!!busy || !!validate()}
            className="flex items-center gap-1.5 px-4 py-2 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white font-bold text-[11px] rounded-xl"
          >
            <Sparkles className="w-3.5 h-3.5" />
            {busy
              ? tr('learning_dialog_generating', {}, 'Membuat…')
              : tr('learning_dialog_generate_now', {}, 'Generate sekarang')}
          </button>
        </div>

        {/* Ringkasan guard kuis supaya user tahu kenapa tombol mati. */}
        {kind === 'quiz' && quizTotal > QUIZ_TOTAL_MAX && (
          <p className="text-[10px] text-rose-300">{tr('learning_quiz_total_over', {}, 'Total melebihi 30 soal — kurangi salah satu.')}</p>
        )}
      </div>
    </div>
  );
};

export default StudioGenerateDialog;
