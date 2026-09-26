import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  X, Sparkles, Copy, Download, RefreshCw, Trophy, Flame, Timer, CalendarDays,
  TrendingUp, TrendingDown, Scale, PiggyBank, CheckCircle2,
} from 'lucide-react';
import confetti from 'canvas-confetti';
import { rpg } from '../api/rpg';
import { saveBlobToFile } from '../api/client';
import { useGame } from '../context/GameContext';
import { t } from '../i18n';
import { useFocusTrap } from '../hooks/useFocusTrap';
import {
  currencySymbol, ensureCurrencyRates, formatMoney, getCurrencyRates,
} from '../utils/currency';
import {
  wrappedCurrencyNote, wrappedFileName, wrappedHabitRows, wrappedHasData, wrappedNet,
  wrappedSavingRate, wrappedSummaryText, wrappedTypeLabel, wrappedTypeRows, wrappedYearOptions,
  type WrappedData,
} from './wrapped/wrappedUtils';

/** Helper varian: `wrapped_total` = "{n} tugas diselesaikan". */
function trv(key: string, vars: Record<string, string | number>, fallback: string): string {
  let s = t(key, fallback);
  Object.entries(vars).forEach(([k, v]) => { s = s.split(`{${k}}`).join(String(v)); });
  return s;
}

const TYPE_ICON: Record<string, string> = {
  habit: '🎯', daily: '🔁', todo: '📜', quest: '📜', sport: '🏃', other: '📦',
};

/**
 * YearWrappedDialog (fase A13) — laporan tahunan "CraftLife Wrapped".
 *
 * Perubahan A13:
 *  · **mata uang aktif user** — semua angka uang lewat `formatMoney(v, user.currency)`
 *    (satu-satunya formatter resmi; tidak ada "Rp" hardcoded) + chip mata uang &
 *    catatan kurs kecil;
 *  · **i18n penuh** (id/en) — dulu seluruh teks hardcoded Indonesia;
 *  · polish: selisih bersih berwarna dinamis, rasio tabungan, rincian per tipe task,
 *    top habit dengan bar relatif, **pemilih tahun** (`GET /api/year-wrapped?year=`),
 *    **Salin ringkasan** + **Unduh .txt**, confetti saat laporan terbuka;
 *  · empty-state dipisah dari error (dulu keduanya tampil "tidak ada aktivitas").
 */
export const YearWrappedDialog: React.FC<{
  onClose: () => void;
  displayName?: string;
  /** Opsional: tahun awal yang dibuka (dipakai pengujian). */
  initialYear?: number;
}> = ({ onClose, displayName, initialYear }) => {
  const { user } = useGame();
  const currency = String(user?.currency || 'IDR');
  const [w, setW] = useState<WrappedData | null>(null);
  const [years, setYears] = useState<number[]>([]);
  const [year, setYear] = useState<number | null>(initialYear ?? null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [copied, setCopied] = useState(false);
  const [ratesTick, setRatesTick] = useState(0);

  const money = useCallback((v: number, cur: string = currency) => formatMoney(v, cur), [currency]);

  const load = useCallback(async (y?: number | null) => {
    setLoading(true);
    setFailed(false);
    try {
      const d = await rpg.yearWrapped(y || undefined);
      if (!d || d.ok === false) {
        setFailed(true);
        setW(null);
      } else {
        setW((d.wrapped || null) as WrappedData | null);
        setYears(Array.isArray(d.years) ? d.years : []);
        if (d.wrapped?.year) setYear(Number(d.wrapped.year));
      }
    } catch {
      setFailed(true);
      setW(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(initialYear ?? null); }, [load, initialYear]);

  // Kurs resmi (sekali per sesi) → supaya catatan kurs ikut benar; kalau server
  // belum menjawab, formatter memakai kurs bawaan (sama dengan database.py).
  useEffect(() => {
    let alive = true;
    ensureCurrencyRates().then(() => { if (alive) setRatesTick((n) => n + 1); });
    return () => { alive = false; };
  }, []);

  const rates = useMemo(() => getCurrencyRates(), [ratesTick]);

  // Confetti hanya sekali per laporan yang memang berisi aktivitas.
  useEffect(() => {
    if (loading || failed || !wrappedHasData(w)) return;
    let alive = true;
    const id = window.setTimeout(() => {
      if (!alive) return;
      try {
        confetti({ particleCount: 90, spread: 78, origin: { y: 0.3 }, disableForReducedMotion: true });
      } catch { /* confetti opsional — jangan sampai memblokir dialog */ }
    }, 220);
    return () => { alive = false; window.clearTimeout(id); };
  }, [loading, failed, w]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  const trapRef = useFocusTrap<HTMLDivElement>(true);

  const yearOptions = useMemo(
    () => wrappedYearOptions([...(years || []), ...(w?.year ? [w.year] : []), new Date().getFullYear()]),
    [years, w],
  );
  const typeRows = useMemo(() => wrappedTypeRows(w?.by_type || {}, t), [w]);
  const habitRows = useMemo(() => wrappedHabitRows(w?.top_habits || []), [w]);
  const net = wrappedNet(w);
  const saving = wrappedSavingRate(w);
  const netPositive = net >= 0;
  const note = w ? wrappedCurrencyNote(currency, rates, t, trv, formatMoney) : '';

  const summaryText = useCallback(() => (w ? wrappedSummaryText(w, {
    displayName, currency, t, trv, money: (v, c) => formatMoney(v, c),
  }) : ''), [w, displayName, currency, money]);

  const doCopy = useCallback(async () => {
    const text = summaryText();
    if (!text) return;
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch {
      // Fallback lingkungan tanpa izin clipboard (mis. iframe sandbox).
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        ok = document.execCommand('copy');
        ta.remove();
      } catch { ok = false; }
    }
    if (ok) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2200);
    }
  }, [summaryText]);

  const doDownload = useCallback(() => {
    const text = summaryText();
    if (!text) return;
    saveBlobToFile(new Blob([text], { type: 'text/plain;charset=utf-8' }), wrappedFileName(w?.year || ''));
  }, [summaryText, w]);

  const pickYear = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const y = Number(e.target.value) || null;
    setYear(y);
    load(y);
  };

  return (
    <div className="ct-backdrop fixed inset-0 z-[70] flex items-center justify-center p-4" onClick={onClose}>
      <div
        ref={trapRef}
        className="ct-dialog max-w-lg w-full p-6 space-y-3 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
        data-testid="year-wrapped-dialog"
      >
        {/* ── Header: judul + pemilih tahun + tutup ── */}
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-lg font-black text-amber-300 flex items-center gap-2">
            <Sparkles className="w-5 h-5" />{' '}
            {w?.year ? trv('wrapped_title', { year: w.year }, `CraftLife Wrapped ${w.year}`)
              : t('wrapped_open', 'Year Wrapped')}
          </h3>
          <div className="flex items-center gap-1.5">
            <label className="flex items-center gap-1 text-[10px] uppercase tracking-wider text-slate-500">
              <CalendarDays className="w-3.5 h-3.5" />
              <span className="sr-only">{t('wrapped_pick_year', 'Pick a year')}</span>
              <select
                value={String(year ?? w?.year ?? new Date().getFullYear())}
                onChange={pickYear}
                title={t('wrapped_pick_year', 'Pick a year')}
                data-testid="wrapped-year-select"
                className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-1 text-xs text-slate-200 font-bold"
              >
                {yearOptions.map((y) => <option key={y} value={y}>{y}</option>)}
              </select>
            </label>
            <button
              type="button" onClick={onClose} title={t('btn_close', 'Close')}
              className="ct-btn ct-btn-ghost ct-btn-icon-sm text-slate-400" data-testid="wrapped-close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* ── Error (dipisah dari empty-state) ── */}
        {failed && !loading && (
          <div className="rounded-xl bg-rose-950/40 border border-rose-500/30 p-4 text-center space-y-2" data-testid="wrapped-error">
            <p className="text-sm text-rose-300 font-bold">{t('wrapped_error', "Failed to load this year's report.")}</p>
            <button type="button" onClick={() => load(year)}
              className="ct-btn ct-btn-secondary ct-btn-sm inline-flex items-center gap-1.5">
              <RefreshCw className="w-3.5 h-3.5" /> {t('web_retry', 'Try again')}
            </button>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center gap-2 py-10 text-slate-500 text-sm" data-testid="wrapped-loading">
            <RefreshCw className="w-4 h-4 animate-spin" /> {t('loading', 'Loading…')}
          </div>
        )}

        {/* ── Empty-state ── */}
        {!loading && !failed && !wrappedHasData(w) && (
          <div className="text-center py-10 space-y-2" data-testid="wrapped-empty">
            <div className="text-3xl">🎁</div>
            <p className="text-sm text-slate-400">{t('wrapped_empty', 'No activity this year yet. Start logging your tasks!')}</p>
            {String(w?.year || year || '') !== '' && (
              <p className="text-[11px] text-slate-500">{w?.year || year}</p>
            )}
          </div>
        )}

        {/* ── Laporan ── */}
        {!loading && !failed && wrappedHasData(w) && w && (
          <div className="space-y-3">
            <div className="text-center">
              <div className="text-lg font-black text-amber-200">
                {trv('wrapped_hero', { name: displayName || '⭐', year: w.year },
                  `⭐ ${displayName || ''} — ${w.year} in Review ⭐`)}
              </div>
            </div>

            {/* Kartu utama: tugas */}
            <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-4 space-y-2 text-center">
              <div className="text-4xl font-black text-amber-300">{w.total_done}</div>
              <div className="text-xs text-slate-400">{t('wrapped_tasks_done', 'tasks completed')}</div>
              <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[11px] text-slate-300">
                <span className="inline-flex items-center gap-1">
                  <CalendarDays className="w-3.5 h-3.5 text-sky-300" />
                  {trv('wrapped_active_days', { n: w.active_days }, 'active days')}
                </span>
                {w.best_day && (
                  <span className="inline-flex items-center gap-1 text-emerald-300">
                    <Trophy className="w-3.5 h-3.5" />
                    {trv('wrapped_best', { date: w.best_day, n: w.best_day_count }, `Best day: ${w.best_day}`)}
                  </span>
                )}
              </div>
            </div>

            {/* Fokus + level/streak */}
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3">
                <div className="text-lg font-black text-sky-300 inline-flex items-center gap-1.5">
                  <Timer className="w-4 h-4" /> {w.focus_sessions}
                </div>
                <div className="text-[10px] text-slate-400">
                  {trv('wrapped_focus', { n: w.focus_sessions, m: w.focus_minutes },
                    `${w.focus_sessions} focus sessions · ${w.focus_minutes} minutes`)}
                </div>
              </div>
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3">
                <div className="text-lg font-black text-emerald-300">
                  {trv('wrapped_level', { n: w.level }, `Reached level ${w.level}`)}
                </div>
                <div className="text-[10px] text-slate-400 inline-flex items-center gap-1">
                  <Flame className="w-3 h-3 text-amber-400" />
                  {trv('wrapped_streak', { n: w.longest_streak }, `Longest streak: ${w.longest_streak}`)}
                </div>
              </div>
            </div>

            {/* Rincian per tipe task */}
            {typeRows.length > 0 && (
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3 space-y-2" data-testid="wrapped-by-type">
                <div className="text-[10px] uppercase text-slate-400 font-bold tracking-wider">
                  {t('wrapped_by_type', 'Breakdown by type')}
                </div>
                {typeRows.map((row) => (
                  <div key={row.key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-slate-300">
                      <span>{TYPE_ICON[row.type] || TYPE_ICON.other} {wrappedTypeLabel(row.type, t)}</span>
                      <span className="font-bold text-slate-400">{row.count} · {row.pct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-900/80 overflow-hidden">
                      <div className="h-full rounded-full bg-violet-500/70" style={{ width: `${row.barPct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Top habit + bar relatif */}
            {habitRows.length > 0 && (
              <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3 space-y-2" data-testid="wrapped-top-habits">
                <div className="text-[10px] uppercase text-slate-400 font-bold tracking-wider">
                  🏅 {t('wrapped_top_habits', 'Top habits')}
                </div>
                {habitRows.map((h) => (
                  <div key={h.name} className="space-y-1">
                    <div className="flex items-center justify-between text-xs text-slate-300">
                      <span className="truncate">{h.icon} {h.name}</span>
                      <span className="text-amber-300 font-bold shrink-0">×{h.count}</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-slate-900/80 overflow-hidden">
                      <div className="h-full rounded-full bg-amber-400/70" style={{ width: `${h.barPct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Ekonomi: pemasukan · pengeluaran · selisih bersih (mata uang user) */}
            <div className="rounded-xl bg-slate-800/60 border border-slate-700 p-3 space-y-2" data-testid="wrapped-economy">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] uppercase text-slate-400 font-bold tracking-wider">
                  💰 {t('wrapped_income', 'Total income')} / {t('wrapped_expense', 'Total expense')}
                </span>
                <span
                  className="text-[10px] px-2 py-0.5 rounded-full border font-bold bg-slate-900/70 text-slate-300 border-slate-600 shrink-0"
                  data-testid="wrapped-currency-chip"
                  title={note}
                >
                  {currencySymbol(currency)} {currency}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-xl bg-emerald-950/40 border border-emerald-500/30 p-3">
                  <div className="text-[10px] uppercase text-slate-400 font-bold">{t('wrapped_income', 'Total income')}</div>
                  <div className="text-sm font-black text-emerald-300 inline-flex items-center gap-1">
                    <TrendingUp className="w-3.5 h-3.5" /> {money(w.income)}
                  </div>
                </div>
                <div className="rounded-xl bg-rose-950/40 border border-rose-500/30 p-3">
                  <div className="text-[10px] uppercase text-slate-400 font-bold">{t('wrapped_expense', 'Total expense')}</div>
                  <div className="text-sm font-black text-rose-300 inline-flex items-center gap-1">
                    <TrendingDown className="w-3.5 h-3.5" /> {money(w.expense)}
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 text-center">
                <div className="rounded-xl bg-slate-900/60 border border-slate-700 p-2.5" data-testid="wrapped-net">
                  <div className="text-[10px] uppercase text-slate-400 font-bold inline-flex items-center gap-1">
                    <Scale className="w-3 h-3" /> {t('wrapped_net', 'Net balance')}
                  </div>
                  <div className={`text-sm font-black ${netPositive ? 'text-emerald-300' : 'text-rose-300'}`}>
                    {netPositive ? '+' : '−'}{money(Math.abs(net))}
                  </div>
                </div>
                <div className="rounded-xl bg-slate-900/60 border border-slate-700 p-2.5" data-testid="wrapped-saving-rate">
                  <div className="text-[10px] uppercase text-slate-400 font-bold inline-flex items-center gap-1">
                    <PiggyBank className="w-3 h-3" /> {t('wrapped_saving_rate', 'Saving rate')}
                  </div>
                  <div className={`text-sm font-black ${
                    saving === null ? 'text-slate-500' : saving >= 0 ? 'text-emerald-300' : 'text-rose-300'
                  }`}>
                    {saving === null ? '—' : `${saving}%`}
                  </div>
                </div>
              </div>
              <p className="text-[10px] text-slate-500 text-center" data-testid="wrapped-currency-note">{note}</p>
            </div>

            {/* Aksi: salin · unduh */}
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" onClick={doCopy}
                className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1.5" data-testid="wrapped-copy">
                {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                {copied ? t('wrapped_copied', 'Summary copied') : t('wrapped_copy', 'Copy summary')}
              </button>
              <button type="button" onClick={doDownload}
                className="ct-btn ct-btn-secondary ct-btn-sm flex items-center gap-1.5" data-testid="wrapped-download">
                <Download className="w-3.5 h-3.5" /> {t('wrapped_download', 'Download .txt')}
              </button>
            </div>
          </div>
        )}

        <div className="flex justify-end">
          <button onClick={onClose} className="ct-btn ct-btn-secondary ct-btn-sm">
            {t('wrapped_close', t('btn_close', 'Close'))}
          </button>
        </div>
      </div>
    </div>
  );
};

export default YearWrappedDialog;
