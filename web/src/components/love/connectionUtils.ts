/**
 * connectionUtils.ts — logika murni tab `connection` (fase A11).
 *
 * Dipisahkan dari React/DOM supaya bisa diuji langsung di Node (pola yang sama
 * dengan `eventUtils.ts` A09 dan `memoryUtils.ts` A10). Semua fungsi menerima
 * data apa adanya dari snapshot `loveSpace` sehingga tidak ada ketergantungan
 * pada clock global — `today` selalu dioper eksplisit (Y-M-D).
 */

export type Prompt = [string, string, string]; // [key, category, i18nKey]

/** Bank prompt Connection — parity LovePage.PROMPTS (key, category, trKey). */
export const PROMPTS: Prompt[] = [
  ['connection_seen', 'connection', 'love_prompt_connection_seen'],
  ['connection_safe', 'connection', 'love_prompt_connection_safe'],
  ['connection_listen', 'connection', 'love_prompt_connection_listen'],
  ['connection_closer', 'connection', 'love_prompt_connection_closer'],
  ['appreciation_small', 'appreciation', 'love_prompt_appreciation_small'],
  ['appreciation_quality', 'appreciation', 'love_prompt_appreciation_quality'],
  ['appreciation_memory', 'appreciation', 'love_prompt_appreciation_memory'],
  ['appreciation_growth', 'appreciation', 'love_prompt_appreciation_growth'],
  ['support_stress', 'support', 'love_prompt_support_stress'],
  ['support_request', 'support', 'love_prompt_support_request'],
  ['support_energy', 'support', 'love_prompt_support_energy'],
  ['support_team', 'support', 'love_prompt_support_team'],
  ['future_year', 'future', 'love_prompt_future_year'],
  ['future_home', 'future', 'love_prompt_future_home'],
  ['future_skill', 'future', 'love_prompt_future_skill'],
  ['future_priority', 'future', 'love_prompt_future_priority'],
  ['fun_date', 'fun', 'love_prompt_fun_date'],
  ['fun_laugh', 'fun', 'love_prompt_fun_laugh'],
  ['fun_adventure', 'fun', 'love_prompt_fun_adventure'],
  ['fun_switch', 'fun', 'love_prompt_fun_switch'],
];

export const PROMPT_CATEGORIES = ['all', 'connection', 'appreciation', 'support', 'future', 'fun', 'favorites'] as const;

/** Prompt yang bisa dipilih untuk sebuah kategori (`favorites` = dari daftar favorit). */
export function promptPool(category: string, favorites: string[] = []): Prompt[] {
  if (category === 'favorites') return PROMPTS.filter((p) => favorites.includes(p[0]));
  if (category === 'all') return PROMPTS;
  return PROMPTS.filter((p) => p[1] === category);
}

/** Pilih prompt acak (menghindari prompt yang sedang tampil bila ada alternatif). */
export function pickPrompt(pool: Prompt[], current?: Prompt | null, rand: () => number = Math.random): Prompt | null {
  if (!pool.length) return null;
  const alternatives = pool.filter((p) => !current || p[0] !== current[0]);
  const use = alternatives.length ? alternatives : pool;
  return use[Math.floor(rand() * use.length)] || pool[0];
}

/** Cari prompt berdasarkan key (dipakai saat mengulang jawaban lama / dari favorit). */
export function promptByKey(key: string): Prompt | null {
  return PROMPTS.find((p) => p[0] === key) || null;
}

/** Geser tanggal Y-M-D sejumlah hari (tanpa timezone — murni kalender). */
export function shiftDay(iso: string, days: number): string {
  const [y, m, d] = String(iso).slice(0, 10).split('-').map((x) => parseInt(x, 10));
  if (!y || !m || !d) return iso;
  const dt = new Date(Date.UTC(y, m - 1, d));
  dt.setUTCDate(dt.getUTCDate() + days);
  return dt.toISOString().slice(0, 10);
}

/** Senin dari minggu yang memuat `iso` (format Y-M-D). */
export function weekStartOf(iso: string): string {
  const s = String(iso).slice(0, 10);
  const [y, m, d] = s.split('-').map((x) => parseInt(x, 10));
  if (!y || !m || !d) return s;
  const dt = new Date(Date.UTC(y, m - 1, d));
  const dow = (dt.getUTCDay() + 6) % 7; // Senin = 0
  dt.setUTCDate(dt.getUTCDate() - dow);
  return dt.toISOString().slice(0, 10);
}

export interface CheckinRow {
  id?: string;
  date: string;
  myMood: number;
  partnerMood: number;
  connectionScore: number;
  note?: string;
}

export interface CheckinStats {
  total: number;
  streak: number;
  avgMy: number;
  avgPartner: number;
  avgScore: number;
  lastDate: string;
  hasToday: boolean;
}

const round1 = (n: number) => Math.round(n * 10) / 10;

/** Statistik check-in: total, rata-rata mood/skor, dan streak hari berturut-turut. */
export function checkinStats(checkins: CheckinRow[] = [], today: string): CheckinStats {
  const rows = (checkins || []).filter((c) => c && c.date);
  const n = rows.length;
  const avg = (pick: (c: CheckinRow) => number) =>
    n ? round1(rows.reduce((sum, c) => sum + (Number(pick(c)) || 0), 0) / n) : 0;
  const dates = new Set(rows.map((c) => String(c.date).slice(0, 10)));
  let streak = 0;
  let cursor = dates.has(today) ? today : shiftDay(today, -1);
  while (dates.has(cursor)) {
    streak += 1;
    cursor = shiftDay(cursor, -1);
  }
  return {
    total: n,
    streak,
    avgMy: avg((c) => c.myMood),
    avgPartner: avg((c) => c.partnerMood),
    avgScore: avg((c) => c.connectionScore),
    lastDate: n ? String(rows[0].date).slice(0, 10) : '',
    hasToday: dates.has(today),
  };
}

export interface MoodSeries {
  labels: string[];
  my: Array<{ value: number }>;
  partner: Array<{ value: number }>;
  score: Array<{ value: number }>;
  days: number;
  empty: boolean;
}

/**
 * Deret data untuk grafik tren mood: hanya hari yang punya check-in (dipakai
 * sebagai titik), dengan rentang 30/90 hari terakhir dari `today`.
 */
export function buildMoodSeries(checkins: CheckinRow[] = [], today: string, days = 30): MoodSeries {
  const from = shiftDay(today, -(days - 1));
  const rows = (checkins || [])
    .filter((c) => c && c.date && String(c.date).slice(0, 10) >= from && String(c.date).slice(0, 10) <= today)
    .sort((a, b) => String(a.date).localeCompare(String(b.date)));
  return {
    labels: rows.map((c) => String(c.date).slice(5)),
    my: rows.map((c) => ({ value: Number(c.myMood) || 0 })),
    partner: rows.map((c) => ({ value: Number(c.partnerMood) || 0 })),
    score: rows.map((c) => ({ value: Number(c.connectionScore) || 0 })),
    days,
    empty: rows.length === 0,
  };
}

export interface HistoryFilter {
  query?: string;
  category?: string;
  onlyFavorites?: boolean;
}

export interface ResponseRow {
  id?: string;
  promptKey: string;
  category: string;
  prompt: string;
  answer?: string;
  partnerAnswer?: string;
  createdAt?: string;
}

/** Saring riwayat jawaban: pencarian bebas + kategori + hanya favorit. */
export function filterResponses(
  responses: ResponseRow[] = [],
  filter: HistoryFilter = {},
  favorites: string[] = [],
): ResponseRow[] {
  const q = String(filter.query || '').trim().toLowerCase();
  const cat = String(filter.category || 'all');
  return (responses || []).filter((r) => {
    if (cat !== 'all' && String(r.category || '') !== cat) return false;
    if (filter.onlyFavorites && !favorites.includes(r.promptKey)) return false;
    if (!q) return true;
    const hay = `${r.prompt || ''} ${r.answer || ''} ${r.partnerAnswer || ''} ${r.promptKey || ''}`.toLowerCase();
    return hay.includes(q);
  });
}

/** Kategori yang benar-benar ada di riwayat + jumlahnya (untuk dropdown filter). */
export function historyCategories(responses: ResponseRow[] = []): Array<{ id: string; count: number }> {
  const counts = new Map<string, number>();
  (responses || []).forEach((r) => {
    const key = String(r.category || 'daily');
    counts.set(key, (counts.get(key) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([id, count]) => ({ id, count }))
    .sort((a, b) => (a.id === b.id ? 0 : a.id < b.id ? -1 : 1));
}

/** Daftar prompt favorit siap tampil (key + label i18n), urut abjad label. */
export function favoritePrompts(favorites: string[] = []): Prompt[] {
  const set = new Set(favorites || []);
  return PROMPTS.filter((p) => set.has(p[0]));
}

/** Tanggal ramah untuk baris riwayat: `2026-09-16T10:00` → `2026-09-16`. */
export function historyDate(createdAt?: string): string {
  return String(createdAt || '').slice(0, 10);
}
