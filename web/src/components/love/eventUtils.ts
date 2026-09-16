/**
 * eventUtils.ts — logika murni tab `plans` Love Space (A09).
 *
 * Semua fungsi di sini bebas React/DOM supaya bisa diuji langsung dengan node
 * (lihat laporan A09) dan dipakai bersama oleh `LoveEventDialog` (pratinjau
 * hitung mundur) serta `LoveSpaceView` (pengelompokan Akan datang/Sudah lewat).
 *
 * Aturan tanggal disamakan dengan server (`database._love_next_occurrence`):
 *  · `yearly` → bulan/tanggal sama pada tahun berjalan; sudah lewat → tahun depan;
 *  · 29 February pada tahun non-kabisat → 28 February;
 *  · selain `yearly` → tanggal aslinya, atau "" bila sudah lewat (tak akan datang lagi).
 */

export type Recurring = 'none' | 'yearly';

function pad(n: number): string {
  return String(n).padStart(2, '0');
}

function toISO(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function parseDay(iso?: string): Date | null {
  if (!iso) return null;
  const parts = String(iso).slice(0, 10).split('-').map(Number);
  if (parts.length !== 3 || parts.some((x) => Number.isNaN(x))) return null;
  const d = new Date(parts[0], parts[1] - 1, parts[2]);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** Tengah malam hari ini (atau tanggal `todayISO`). */
export function midnight(todayISO?: string): Date {
  const base = todayISO ? parseDay(todayISO) : null;
  const now = base || new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

/** Tanggal kejadian berikutnya (lihat aturan di atas). "" = tidak akan datang lagi. */
export function nextOccurrence(isoDate: string, recurring: string, todayISO?: string): string {
  const base = parseDay(isoDate);
  if (!base) return '';
  const today = midnight(todayISO);
  if (String(recurring) !== 'yearly') return base >= today ? toISO(base) : '';

  const build = (year: number) => {
    const candidate = new Date(year, base.getMonth(), base.getDate());
    // 29 Feb pada tahun non-kabisat → JS membawa ke 1 Mar; pakai hari terakhir Feb.
    if (candidate.getMonth() !== base.getMonth()) return new Date(year, base.getMonth() + 1, 0);
    return candidate;
  };
  let next = build(today.getFullYear());
  if (next < today) next = build(today.getFullYear() + 1);
  return toISO(next);
}

/** Selisih hari (bulat) antara `isoDate` dan hari ini; null bila tanggal tidak sah. */
export function daysUntil(isoDate: string, todayISO?: string): number | null {
  const target = parseDay(isoDate);
  if (!target) return null;
  return Math.round((target.getTime() - midnight(todayISO).getTime()) / 86400000);
}

export interface EnrichedEvent {
  id: string;
  title: string;
  date: string;
  category: string;
  icon: string;
  location: string;
  notes: string;
  isSpecial: boolean;
  recurring: Recurring;
  remindDaysBefore: number;
  nextDate: string;
  daysUntil: number | null;
  isUpcoming: boolean;
}

/** Lengkapi acara dengan tanggal berikutnya + hitung mundur + penanda akan datang. */
export function enrichEvents(events: any[], todayISO?: string): EnrichedEvent[] {
  return (events || []).map((ev: any) => {
    const recurring: Recurring = ev?.recurring === 'yearly' ? 'yearly' : 'none';
    const nextDate = recurring === 'yearly'
      ? nextOccurrence(ev?.date, 'yearly', todayISO)
      : String(ev?.date || '').slice(0, 10);
    const delta = daysUntil(nextDate, todayISO);
    return {
      id: String(ev?.id ?? ''),
      title: String(ev?.title || ''),
      date: String(ev?.date || '').slice(0, 10),
      category: String(ev?.category || 'date'),
      icon: String(ev?.icon || ''),
      location: String(ev?.location || ''),
      notes: String(ev?.notes || ''),
      isSpecial: Boolean(ev?.isSpecial),
      recurring,
      remindDaysBefore: Number(ev?.remindDaysBefore || 0),
      nextDate,
      daysUntil: delta,
      isUpcoming: delta !== null && delta >= 0,
    };
  });
}

export interface EventFilter {
  query?: string;
  category?: string;
  onlySpecial?: boolean;
}

/** Pencarian (judul/lokasi/catatan) + filter kategori + hanya hari istimewa. */
export function filterEvents(list: EnrichedEvent[], opts: EventFilter = {}): EnrichedEvent[] {
  const q = String(opts.query || '').trim().toLowerCase();
  const cat = opts.category && opts.category !== 'all' ? opts.category : '';
  return (list || []).filter((ev) => {
    if (q) {
      const hay = `${ev.title} ${ev.location} ${ev.notes}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (cat && ev.category !== cat) return false;
    if (opts.onlySpecial && !ev.isSpecial) return false;
    return true;
  });
}

export interface GroupedEvents {
  total: number;
  specialCount: number;
  upcoming: EnrichedEvent[];
  past: EnrichedEvent[];
}

/**
 * Kelompokkan acara: **Akan datang** (urut hari terdekat, lalu judul) dan
 * **Sudah lewat** (urut tanggal terbaru lebih dulu).
 */
export function groupEvents(events: any[], opts: EventFilter = {}, todayISO?: string): GroupedEvents {
  const all = enrichEvents(events, todayISO);
  const filtered = filterEvents(all, opts);
  return {
    total: all.length,
    specialCount: all.filter((e) => e.isSpecial).length,
    upcoming: filtered
      .filter((e) => e.isUpcoming)
      .sort((a, b) => ((a.daysUntil as number) - (b.daysUntil as number)) || a.title.localeCompare(b.title)),
    past: filtered
      .filter((e) => !e.isUpcoming)
      .sort((a, b) => b.date.localeCompare(a.date)),
  };
}

export type BadgeKind = 'today' | 'upcoming' | 'past';

/** Jenis lencana hitung mundur: `Hari ini!` / `H-12` / `+30` (sudah lewat). */
export function badgeKind(days: number | null): BadgeKind {
  if (days !== null && days <= 0) return days === 0 ? 'today' : 'past';
  return 'upcoming';
}
