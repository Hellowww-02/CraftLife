/**
 * wrappedUtils.ts — logika murni untuk Year Wrapped (fase A13).
 *
 * Semua fungsi di sini bebas DOM supaya bisa diuji tanpa browser (pola yang sama
 * dengan `love/overviewUtils.ts`, `connectionUtils.ts`, dst).
 *
 * ATURAN UANG: seluruh nilai dari server adalah **IDR mentah**. Format tampilan
 * WAJIB lewat `web/src/utils/currency.ts` (`formatMoney`) — berkas ini hanya
 * **menerima** formatter itu sebagai parameter supaya tetap murni & mudah diuji.
 */
export interface WrappedData {
  year: number;
  total_done: number;
  by_type: Record<string, number>;
  active_days: number;
  best_day: string | null;
  best_day_count: number;
  top_habits: { name: string; icon: string; count: number }[];
  focus_sessions: number;
  focus_minutes: number;
  income: number;
  expense: number;
  level: number;
  longest_streak: number;
}

export type TFn = (key: string, fallback: string) => string;
export type TrvFn = (key: string, vars: Record<string, string | number>, fallback: string) => string;
export type MoneyFn = (amountIdr: number, currency: string) => string;

export interface TypeRow { type: string; key: string; count: number; pct: number; barPct: number; }
export interface HabitRow { name: string; icon: string; count: number; barPct: number; }

/** Ada aktivitas? Dipakai untuk memilih empty state vs laporan penuh. */
export function wrappedHasData(w?: WrappedData | null): boolean {
  if (!w) return false;
  return Number(w.total_done || 0) > 0 || Number(w.focus_sessions || 0) > 0;
}

/** Selisih bersih = pemasukan − pengeluaran (IDR). */
export function wrappedNet(w?: WrappedData | null): number {
  if (!w) return 0;
  return Number(w.income || 0) - Number(w.expense || 0);
}

/** Rasio tabungan (%) dari pemasukan; `null` bila pemasukan 0/kosong. */
export function wrappedSavingRate(w?: WrappedData | null): number | null {
  const income = Number(w?.income || 0);
  if (income <= 0) return null;
  const rate = (income - Number(w?.expense || 0)) / income * 100;
  return Math.round(rate);
}

/** Label tipe task (habit/daily/todo/sport) — TODO: `t` dipakai bila ada. */
export function wrappedTypeLabel(type: string, t: TFn): string {
  switch (String(type || '').toLowerCase()) {
    case 'habit': return t('wrapped_type_habit', 'Habits');
    case 'daily': return t('wrapped_type_daily', 'Dailies');
    case 'todo':
    case 'quest': return t('wrapped_type_todo', 'Quests');
    case 'sport': return t('wrapped_type_sport', 'Sport');
    default: return t('wrapped_type_other', 'Other');
  }
}

/** Rincian per tipe: urut dari terbanyak, lengkap dengan persentase & lebar bar. */
export function wrappedTypeRows(byType: Record<string, number> = {}, t: TFn): TypeRow[] {
  const rows = Object.entries(byType || {})
    .map(([type, count]) => ({ type, count: Number(count) || 0 }))
    .filter((r) => r.count > 0)
    .sort((a, b) => b.count - a.count || a.type.localeCompare(b.type));
  const total = rows.reduce((sum, r) => sum + r.count, 0);
  const max = rows.length ? rows[0].count : 0;
  return rows.map((r) => ({
    ...r,
    key: `wrapped-type-${r.type}`,
    pct: total ? Math.round((r.count / total) * 100) : 0,
    barPct: max ? Math.max(4, Math.round((r.count / max) * 100)) : 0,
  }));
}

/** Top habit dengan lebar bar relatif terhadap yang teratas. */
export function wrappedHabitRows(top: WrappedData['top_habits'] = []): HabitRow[] {
  const rows = (top || []).map((h) => ({
    name: h?.name || '—', icon: h?.icon || '🏅', count: Number(h?.count) || 0,
  }));
  const max = rows.reduce((m, h) => Math.max(m, h.count), 0);
  return rows.map((h) => ({ ...h, barPct: max ? Math.max(4, Math.round((h.count / max) * 100)) : 0 }));
}

/** Nama berkas unduhan. */
export function wrappedFileName(year: number | string): string {
  return `craftlife-wrapped-${year || 'year'}.txt`;
}

/**
 * Daftar tahun untuk pemilih: gabungan dari server + tahun berjalan, menurun,
 * maksimal `limit` entri (default 10).
 */
export function wrappedYearOptions(years: number[] = [], currentYear?: number, limit = 10): number[] {
  const set = new Set<number>();
  (years || []).forEach((y) => { const n = Number(y); if (Number.isFinite(n) && n > 1900) set.add(n); });
  const now = Number(currentYear) || new Date().getFullYear();
  set.add(now);
  return [...set].sort((a, b) => b - a).slice(0, limit);
}

/**
 * Catatan mata uang kecil di bawah kartu ekonomi — supaya angka transparan.
 * IDR (mata uang bawaan) tidak menampilkan kurs karena rasionya 1:1.
 */
export function wrappedCurrencyNote(
  currency: string, rates: Record<string, number>, t: TFn, trv: TrvFn, money: MoneyFn,
): string {
  const cur = currency || 'IDR';
  const rate = Number(rates?.[cur] ?? 1) || 1;
  if (cur === 'IDR' || rate === 1) return t('wrapped_currency_note_idr', 'Shown in IDR (base currency)');
  return trv('wrapped_currency_note', { currency: cur, rate: money(rate, 'IDR') },
    `Shown in ${cur} (rate 1 ${cur} = ${money(rate, 'IDR')})`);
}

/**
 * Teks ringkasan rapi untuk "Salin ringkasan" / "Unduh .txt".
 * Semua label lewat i18n; angka uang lewat formatter resmi.
 */
export function wrappedSummaryText(
  w: WrappedData,
  opts: { displayName?: string; currency: string; t: TFn; trv: TrvFn; money: MoneyFn },
): string {
  const { displayName, currency, t, trv, money } = opts;
  const lines: string[] = [];
  lines.push(trv('wrapped_title', { year: w.year }, `CraftLife Wrapped ${w.year}`));
  if (displayName) lines.push(trv('wrapped_hero', { name: displayName, year: w.year }, `${displayName} — ${w.year}`));
  lines.push('');
  lines.push(`✅ ${trv('wrapped_total', { n: w.total_done }, `${w.total_done} tasks completed`)}`);
  lines.push(`📆 ${trv('wrapped_active_days', { n: w.active_days }, `${w.active_days} active days`)}`);
  if (w.best_day) {
    lines.push(`🏆 ${trv('wrapped_best', { date: w.best_day, n: w.best_day_count },
      `Best day: ${w.best_day} (${w.best_day_count} tasks)`)}`);
  }
  lines.push(`🍅 ${trv('wrapped_focus', { n: w.focus_sessions, m: w.focus_minutes },
    `${w.focus_sessions} focus sessions · ${w.focus_minutes} minutes`)}`);
  lines.push(`⭐ ${trv('wrapped_level', { n: w.level }, `Reached level ${w.level}`)}`);
  lines.push(`🔥 ${trv('wrapped_streak', { n: w.longest_streak }, `Longest streak: ${w.longest_streak}`)}`);
  const habits = wrappedHabitRows(w.top_habits);
  if (habits.length) {
    lines.push('');
    lines.push(t('wrapped_habits_top', 'Top habits:'));
    habits.forEach((h) => lines.push(`   ${h.icon} ${h.name} ×${h.count}`));
  }
  const types = wrappedTypeRows(w.by_type, t);
  if (types.length) {
    lines.push('');
    lines.push(`${t('wrapped_by_type', 'Breakdown by type')}:`);
    types.forEach((r) => lines.push(`   ${wrappedTypeLabel(r.type, t)}: ${r.count} (${r.pct}%)`));
  }
  lines.push('');
  lines.push(`💰 ${t('wrapped_income', 'Total income')}: ${money(w.income, currency)}`);
  lines.push(`💸 ${t('wrapped_expense', 'Total expenses')}: ${money(w.expense, currency)}`);
  lines.push(`⚖️ ${t('wrapped_net', 'Net balance')}: ${money(wrappedNet(w), currency)}`);
  const saving = wrappedSavingRate(w);
  if (saving !== null) {
    lines.push(`🏦 ${t('wrapped_saving_rate', 'Saving rate')} ${saving}%`);
  }
  return lines.join('\n');
}
