/**
 * memoryUtils.ts — logika murni tab `memories` & bagian **Bucket List** Love Space (A10).
 *
 * Semua fungsi bebas React/DOM supaya bisa diuji langsung dengan node (lihat laporan A10)
 * dan dipakai bersama oleh `LoveSpaceView` (toolbar/pencarian/filter/kartu),
 * `LoveMemoryDialog` & `LoveBucketDialog` (validasi + nilai awal).
 *
 * Aturan yang disamakan dengan server:
 *  · tag dinormalisasi huruf kecil, unik, maksimum 12 (parity `database._love_tags_norm`);
 *  · prioritas bucket 0–3 (0 = tanpa prioritas);
 *  · "terlewat" = belum selesai dan `targetDate` sudah lampau (parity
 *    `database.get_relationship_bucket_stats`).
 */

export type BucketFilter = 'all' | 'open' | 'done' | 'late';
export type MemorySort = 'newest' | 'oldest';

export interface LoveMemory {
  id: string;
  title: string;
  date: string;
  description: string;
  emoji: string;
  tags: string[];
  isFavorite: boolean;
  photoId: string;
  updatedAt: string;
}

export interface LoveBucketItem {
  id: string;
  title: string;
  isCompleted: boolean;
  completedDate: string;
  category: string;
  targetDate: string;
  daysToTarget: number | null;
  isOverdue: boolean;
  notes: string;
  priority: number;
  promotedMemoryId: string;
}

/** Emoji bawaan picker kenangan (bisa diganti emoji apa pun). */
export const MEMORY_EMOJIS = ['💖', '🥰', '🏖️', '🎂', '🌹', '🎉', '🍽️', '🎢', '🌅', '🐾', '🏡', '✨'];

/** Kategori bucket list + ikon (label i18n: `love_bucket_category_<id>`). */
export const BUCKET_CATEGORIES: Array<{ id: string; icon: string }> = [
  { id: 'dream', icon: '🌟' },
  { id: 'travel', icon: '✈️' },
  { id: 'experience', icon: '🎢' },
  { id: 'learning', icon: '📚' },
  { id: 'gift', icon: '🎁' },
  { id: 'home', icon: '🏡' },
];

/** Tingkat prioritas (0 = tanpa prioritas). */
export const BUCKET_PRIORITIES = [0, 1, 2, 3];

// ────────────────────────────────────────────────────────────────────────────
// Tanggal (dipakai bucket list; acara memakai `eventUtils`)
// ────────────────────────────────────────────────────────────────────────────
function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function todayISO(today?: string): string {
  if (today) return String(today).slice(0, 10);
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Selisih hari `iso` − hari ini; null bila tanggal tidak lengkap/tidak sah. */
export function daysTo(iso?: string, today?: string): number | null {
  const a = String(iso || '').slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(a)) return null;
  const b = todayISO(today);
  const [y1, m1, d1] = a.split('-').map(Number);
  const [y2, m2, d2] = b.split('-').map(Number);
  const diff = (Date.UTC(y1, m1 - 1, d1) - Date.UTC(y2, m2 - 1, d2)) / 86400000;
  return Number.isFinite(diff) ? Math.round(diff) : null;
}

/** Jenis badge target bucket list: terlewat / hari ini / ≤30 hari / masih jauh. */
export function targetBadge(days: number | null): 'none' | 'overdue' | 'today' | 'soon' | 'later' {
  if (days === null) return 'none';
  if (days < 0) return 'overdue';
  if (days === 0) return 'today';
  return days <= 30 ? 'soon' : 'later';
}

// ────────────────────────────────────────────────────────────────────────────
// Tag
// ────────────────────────────────────────────────────────────────────────────
/** "Liburan, pantai; liburan" → ["liburan", "pantai"] (huruf kecil, unik, ≤12). */
export function normalizeTags(input: string | string[] | null | undefined): string[] {
  const parts = Array.isArray(input) ? input : String(input || '').replace(/[;|]/g, ',').split(',');
  const out: string[] = [];
  parts.forEach((raw) => {
    const tag = String(raw || '').trim().toLowerCase().slice(0, 24);
    if (tag && !out.includes(tag)) out.push(tag);
  });
  return out.slice(0, 12);
}

/** Kebalikan `normalizeTags` — untuk mengisi input teks. */
export function tagsToInput(tags: string[] | null | undefined): string {
  return normalizeTags(tags).join(', ');
}

// ────────────────────────────────────────────────────────────────────────────
// Kenangan
// ────────────────────────────────────────────────────────────────────────────
/** Bentuk mentah (snapshot server) → struktur aman untuk UI. */
export function normalizeMemory(raw: any): LoveMemory {
  return {
    id: String(raw?.id ?? ''),
    title: String(raw?.title ?? ''),
    date: String(raw?.date ?? ''),
    description: String(raw?.description ?? ''),
    emoji: String(raw?.emoji || '💖'),
    tags: normalizeTags(raw?.tags),
    isFavorite: !!raw?.isFavorite,
    photoId: raw?.photoId ? String(raw.photoId) : '',
    updatedAt: String(raw?.updatedAt ?? ''),
  };
}

export interface MemoryFilters {
  query?: string;
  year?: string;
  tag?: string;
  onlyFav?: boolean;
  sort?: MemorySort;
}

export interface MemoryView {
  items: LoveMemory[];
  total: number;
  matched: number;
  favorites: number;
  withPhoto: number;
}

/** Saring + urutkan kenangan (pencarian judul/catatan/tag, tahun, tag, favorit). */
export function filterMemories(rawList: any[] | null | undefined, filters: MemoryFilters = {}): MemoryView {
  const list = (rawList || []).map(normalizeMemory);
  const q = String(filters.query || '').trim().toLowerCase();
  const tag = String(filters.tag || '').trim().toLowerCase();
  const year = String(filters.year || '').trim();
  const filtered = list.filter((m) => {
    if (filters.onlyFav && !m.isFavorite) return false;
    if (year && m.date.slice(0, 4) !== year) return false;
    if (tag && !m.tags.includes(tag)) return false;
    if (q) {
      const hay = [m.title, m.description, m.tags.join(' ')].join(' ').toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const dir = filters.sort === 'oldest' ? 1 : -1;
  filtered.sort((a, b) => (a.date === b.date ? a.title.localeCompare(b.title) : (a.date < b.date ? -dir : dir)));
  return {
    items: filtered,
    total: list.length,
    matched: filtered.length,
    favorites: list.filter((m) => m.isFavorite).length,
    withPhoto: list.filter((m) => !!m.photoId).length,
  };
}

/** Daftar tahun (terbaru dulu) & tag (paling sering dulu) untuk toolbar filter. */
export function memoryFacets(
  rawList: any[] | null | undefined,
  limit = 40,
): { years: string[]; tags: Array<{ tag: string; count: number }> } {
  const list = (rawList || []).map(normalizeMemory);
  const years: string[] = [];
  const counts = new Map<string, number>();
  list.forEach((m) => {
    const y = m.date.slice(0, 4);
    if (/^\d{4}$/.test(y) && !years.includes(y)) years.push(y);
    m.tags.forEach((t) => counts.set(t, (counts.get(t) || 0) + 1));
  });
  years.sort((a, b) => b.localeCompare(a));
  const tags = Array.from(counts.entries())
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => (b.count - a.count) || a.tag.localeCompare(b.tag))
    .slice(0, limit);
  return { years, tags };
}

// ────────────────────────────────────────────────────────────────────────────
// Bucket list
// ────────────────────────────────────────────────────────────────────────────
/** Bentuk mentah (snapshot server) → struktur aman; hitung ulang terlewat bila perlu. */
export function normalizeBucket(raw: any, today?: string): LoveBucketItem {
  const targetDate = String(raw?.targetDate ?? '').slice(0, 10);
  const days = typeof raw?.daysToTarget === 'number' ? raw.daysToTarget : daysTo(targetDate, today);
  const done = !!raw?.isCompleted;
  return {
    id: String(raw?.id ?? ''),
    title: String(raw?.title ?? ''),
    isCompleted: done,
    completedDate: String(raw?.completedDate ?? ''),
    category: String(raw?.category || 'dream'),
    targetDate,
    daysToTarget: days,
    isOverdue: done ? false : (typeof raw?.isOverdue === 'boolean' ? raw.isOverdue : (days !== null && days < 0)),
    notes: String(raw?.notes ?? ''),
    priority: Math.max(0, Math.min(3, Number(raw?.priority || 0))),
    promotedMemoryId: raw?.promotedMemoryId ? String(raw.promotedMemoryId) : '',
  };
}

export interface BucketStats {
  total: number;
  done: number;
  open: number;
  overdue: number;
  percent: number;
  targeted: number;
}

/** Statistik bucket list — sama rumusnya dengan `database.get_relationship_bucket_stats`. */
export function bucketStats(rawList: any[] | null | undefined, today?: string): BucketStats {
  const list = (rawList || []).map((b) => normalizeBucket(b, today));
  const total = list.length;
  const done = list.filter((b) => b.isCompleted).length;
  const overdue = list.filter((b) => b.isOverdue).length;
  return {
    total,
    done,
    open: total - done,
    overdue,
    percent: total ? Math.round((done * 100) / total) : 0,
    targeted: list.filter((b) => !!b.targetDate).length,
  };
}

/** Saring bucket: semua / belum / selesai / terlewat (+ pencarian judul & catatan). */
export function filterBucket(
  rawList: any[] | null | undefined,
  filter: BucketFilter = 'all',
  query = '',
  today?: string,
): LoveBucketItem[] {
  const q = String(query || '').trim().toLowerCase();
  return (rawList || [])
    .map((b) => normalizeBucket(b, today))
    .filter((b) => {
      if (filter === 'open' && b.isCompleted) return false;
      if (filter === 'done' && !b.isCompleted) return false;
      if (filter === 'late' && !b.isOverdue) return false;
      if (q && !`${b.title} ${b.notes}`.toLowerCase().includes(q)) return false;
      return true;
    })
    .sort((a, b) => {
      if (a.isCompleted !== b.isCompleted) return a.isCompleted ? 1 : -1;
      if (a.priority !== b.priority) return b.priority - a.priority;
      const at = a.targetDate || '9999-12-31';
      const bt = b.targetDate || '9999-12-31';
      if (at !== bt) return at < bt ? -1 : 1;
      return a.title.localeCompare(b.title);
    });
}

/** Teks progres bucket list memakai kunci i18n (fallback Indonesia). */
export function bucketProgressText(
  stats: BucketStats,
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string,
): string {
  return tr('love_bucket_progress', { done: stats.done, total: stats.total },
    `${stats.done} dari ${stats.total} tercapai`);
}

/** Ikon kategori bucket (fallback 🌟 bila kategori tak dikenal). */
export function bucketCategoryIcon(category: string): string {
  return (BUCKET_CATEGORIES.find((c) => c.id === category) || BUCKET_CATEGORIES[0]).icon;
}
