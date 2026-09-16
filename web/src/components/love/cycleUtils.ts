/**
 * cycleUtils.ts — logika murni tab `cycle` (fase A11).
 *
 * Menyimpan seluruh perhitungan tanggal siklus, jendela subur, dan tingkat
 * keyakinan prediksi di satu tempat supaya bisa diuji di Node tanpa DOM.
 * Semua tanggal berformat `YYYY-MM-DD` dan dihitung murni kalender (UTC),
 * jadi bebas dari pergeseran timezone.
 */

export interface CycleRow {
  id?: string;
  startDate: string;
  endDate?: string;
  notes?: string;
  lengthDays?: number | null;
  updatedAt?: string;
}

export interface CycleStats {
  count: number;
  logged: number;
  avgLength: number;
  lastStart: string;
  lastLength: number | null;
  shortest: number | null;
  longest: number | null;
  spread: number;
  running: boolean;
}

export function toIso(value?: string | null): string {
  const s = String(value || '').slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : '';
}

export function dayDiff(from: string, to: string): number | null {
  const a = toIso(from), b = toIso(to);
  if (!a || !b) return null;
  const [ay, am, ad] = a.split('-').map(Number);
  const [by, bm, bd] = b.split('-').map(Number);
  return Math.round((Date.UTC(by, bm - 1, bd) - Date.UTC(ay, am - 1, ad)) / 86400000);
}

export function addDays(iso: string, days: number): string {
  const s = toIso(iso);
  if (!s) return '';
  const [y, m, d] = s.split('-').map(Number);
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt.toISOString().slice(0, 10);
}

/** Panjang siklus satu baris (inklusif) — 0 bila siklus masih berjalan. */
export function cycleLength(cycle: CycleRow): number | null {
  if (typeof cycle.lengthDays === 'number' && cycle.lengthDays > 0) return cycle.lengthDays;
  const start = toIso(cycle.startDate);
  const end = toIso(cycle.endDate);
  if (!start || !end) return null;
  const diff = dayDiff(start, end);
  return diff === null || diff < 0 ? null : diff + 1;
}

/** Statistik riwayat siklus: rata-rata panjang, terpendek/terpanjang, sebaran. */
export function cycleStats(cycles: CycleRow[] = [], today?: string): CycleStats {
  const rows = (cycles || []).filter((c) => c && toIso(c.startDate)).slice();
  const lengths = rows.map(cycleLength).filter((n): n is number => typeof n === 'number' && n > 0);
  const avg = lengths.length ? Math.round((lengths.reduce((a, b) => a + b, 0) / lengths.length) * 10) / 10 : 0;
  const last = rows[0];
  return {
    count: rows.length,
    logged: lengths.length,
    avgLength: avg,
    lastStart: last ? toIso(last.startDate) : '',
    lastLength: last ? cycleLength(last) : null,
    shortest: lengths.length ? Math.min(...lengths) : null,
    longest: lengths.length ? Math.max(...lengths) : null,
    spread: lengths.length ? Math.round((Math.max(...lengths) - Math.min(...lengths)) * 10) / 10 : 0,
    running: !!(last && !toIso(last.endDate) && today ? (dayDiff(toIso(last.startDate), today) ?? 99) <= 10 : false),
  };
}

export interface Confidence {
  level: 'low' | 'medium' | 'high';
  samples: number;
  spread: number;
}

/**
 * Keyakinan prediksi dari banyaknya siklus terlog + sebaran panjang siklus.
 * `high` butuh ≥ 3 siklus terlog dengan sebaran ≤ 3 hari; `low` bila < 2 sampel
 * atau sebaran > 7 hari.
 */
export function predictionConfidence(cycles: CycleRow[] = []): Confidence {
  const stats = cycleStats(cycles);
  const samples = stats.logged;
  const spread = stats.spread;
  let level: Confidence['level'] = 'low';
  if (samples >= 3 && spread <= 3) level = 'high';
  else if (samples >= 2 && spread <= 7) level = 'medium';
  return { level, samples, spread };
}

export interface FertileWindow {
  ovulation: string;
  start: string;
  end: string;
}

/**
 * Perkiraan ovulasi & jendela subur dari tanggal mulai siklus berikutnya.
 * Aturan ringkas yang lazim dipakai aplikasi tracking: ovulasi ≈ 14 hari
 * SEBELUM periode berikutnya, jendela subur = ovulasi ±2 hari.
 */
export function fertileWindow(predictedStart?: string, cycleLengthDays = 28): FertileWindow | null {
  const start = toIso(predictedStart);
  const length = Math.max(20, Math.min(45, Number(cycleLengthDays) || 28));
  if (!start) return null;
  const ovulation = addDays(start, -14);
  return { ovulation, start: addDays(ovulation, -2), end: addDays(ovulation, 2) };
}

/** Rata-rata panjang siklus dari riwayat, jatuh ke pengaturan bila riwayat kosong. */
export function effectiveCycleLength(cycles: CycleRow[] = [], fallback = 28): number {
  const stats = cycleStats(cycles);
  if (stats.avgLength >= 20 && stats.avgLength <= 45) return Math.round(stats.avgLength);
  return Math.max(20, Math.min(45, Number(fallback) || 28));
}

/** Label ringkas panjang siklus: `5 hari` / `—`. */
export function lengthLabel(cycles: CycleRow[] = [], index: number, t?: (k: string, fb: string) => string): string {
  const row = (cycles || [])[index];
  const n = row ? cycleLength(row) : null;
  if (!n) return t ? t('love_cycle_running', 'Berjalan') : '—';
  return t ? t('love_cycle_days_count', '{n} hari').replace('{n}', String(n)) : `${n}`;
}

/** Baris siklus siap tampil di tabel riwayat (urut dari server: terbaru dulu). */
export function cycleRows(cycles: CycleRow[] = []): Array<CycleRow & { length: number | null; lengthText: string }> {
  return (cycles || [])
    .filter((c) => c && toIso(c.startDate))
    .map((c) => {
      const n = cycleLength(c);
      return { ...c, startDate: toIso(c.startDate), endDate: toIso(c.endDate), length: n, lengthText: n ? `${n}` : '' };
    });
}

/** Validasi form siklus (dipakai form tambah/edit di panel). */
export function validateCycleForm(form: { startDate?: string; endDate?: string }): string | null {
  const start = toIso(form.startDate);
  if (!start) return 'love_cycle_date_required';
  const end = toIso(form.endDate);
  if (form.endDate && !end) return 'love_cycle_date_invalid';
  if (end) {
    const diff = dayDiff(start, end);
    if (diff === null || diff < 0) return 'love_cycle_range_invalid';
  }
  return null;
}
