/**
 * overviewUtils.ts — logika murni untuk tab `overview` Love Space (fase A12).
 *
 * Semua fungsi di sini bebas DOM supaya bisa diuji tanpa browser (pola yang sama
 * dengan `connectionUtils.ts` / `cycleUtils.ts` / `galleryUtils.ts` dari A11).
 * Yang dihitung di sini hanya **turunan tampilan** dari data yang sudah ada di
 * payload `loveSpace` + daftar `upcoming` dari `GET /api/love/events/upcoming`:
 * hitungan hari bersama, hari istimewa terdekat, rincian skor kedekatan, dan
 * statistik ringkas. Tidak ada perhitungan yang menggantikan mesin server —
 * tanggal kejadian berikutnya (termasuk 29 Feb & hari dari profil) tetap milik
 * `upcoming_relationship_events`; `nextSpecialFromProfile()` dipakai hanya
 * sebagai cadangan/chip Home yang tidak memanggil API.
 */
import { checkinStats, shiftDay } from './connectionUtils';

export interface UpcomingItem {
  id: string;
  kind?: string;          // 'event' | 'profile'
  source?: string;        // 'event' | 'profile'
  title: string;
  category?: string;
  icon?: string;
  location?: string;
  notes?: string;
  date?: string;          // tanggal asli
  nextDate?: string;      // tanggal kejadian berikutnya
  daysUntil?: number;
  isSpecial?: boolean;
  recurring?: string;     // 'none' | 'yearly'
  remindDaysBefore?: number;
  remindDate?: string;
  yearsCount?: number;
}

export interface OverviewStats {
  memories: number;
  bucketDone: number;
  bucketTotal: number;
  photos: number;
  albums: number;
  prompts: number;
  checkinsMonth: number;
  favorites: number;
  events: number;
}

export interface ScoreBreakdown {
  score: number;
  streak: number;
  total: number;
  avgMy: number;
  avgPartner: number;
  avgScore: number;
  lastDate: string;
  hasToday: boolean;
}

const iso = (value?: string | null) => String(value || '').slice(0, 10);

/** Tanggal hari ini dalam format YYYY-MM-DD (menerima Date atau string). */
export function todayIso(value?: string | Date | null): string {
  if (value instanceof Date) {
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  }
  return iso(value as string);
}

/** Hari bersama sejak `startDate` (minimal 1 bila tanggalnya belum diisi). */
export function daysTogether(startDate?: string, today?: string | Date | null): number {
  const start = iso(startDate);
  if (!start || !/^\d{4}-\d{2}-\d{2}$/.test(start)) return 0;
  const now = todayIso(today) || new Date().toISOString().slice(0, 10);
  const a = Date.parse(`${start}T00:00:00Z`);
  const b = Date.parse(`${now}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return 0;
  return Math.max(1, Math.round((b - a) / 86400000) + 1);
}

/** Pecah jumlah hari menjadi { years, days } (1 tahun = 365 hari, konsisten dgn UI). */
export function durationParts(totalDays: number): { years: number; days: number } {
  const n = Math.max(0, Math.floor(Number(totalDays) || 0));
  if (n < 365) return { years: 0, days: n };
  return { years: Math.floor(n / 365), days: n % 365 };
}

/** Teks durasi siap tampil: "12 hari" / "1 tahun 20 hari" (pakai key i18n A12). */
export function durationText(totalDays: number, trv: (k: string, vars: Record<string, string | number>, fb: string) => string): string {
  const { years, days } = durationParts(totalDays);
  if (years <= 0) return trv('love_together_days', { days }, `Bersama selama ${days} hari`);
  return trv('love_together_years', { years, days }, `${years} tahun ${days} hari`);
}

/** Badge hitung mundur hari istimewa: "Hari ini!" / "Besok" / "H-12". */
export function countdownBadge(daysUntil: number | undefined, t: (k: string, fb: string) => string): string {
  const n = Number(daysUntil);
  if (!Number.isFinite(n)) return '';
  if (n <= 0) return t('love_special_today', 'Hari ini!');
  if (n === 1) return t('love_special_tomorrow', 'Besok');
  return t('love_in_days', '{days} hari lagi').replace('{days}', String(n));
}

/** Ikon baris hari istimewa: ikon acara → ikon kategori → ikon khusus profil. */
export function specialIcon(item: UpcomingItem | undefined): string {
  if (!item) return '✨';
  if (item.icon) return item.icon;
  if (item.category === 'birthday') return '🎂';
  if (item.category === 'anniversary') return '💞';
  return '✨';
}

/** Hari istimewa terdekat: prioritas `isSpecial`, lalu urut `daysUntil`. */
export function nextSpecialDay(items: UpcomingItem[] = []): UpcomingItem | null {
  const rows = (items || []).filter((it) => it && (it.nextDate || it.date));
  if (!rows.length) return null;
  const specials = rows.filter((it) => it.isSpecial);
  const pool = specials.length ? specials : rows;
  return [...pool].sort((a, b) => (Number(a.daysUntil ?? 9999) - Number(b.daysUntil ?? 9999))
    || String(a.title).localeCompare(String(b.title)))[0] || null;
}

/**
 * Cadangan tanpa API (dipakai chip Home): kejadian tahunan terdekat dari
 * acara `yearly` + hari jadi (`startDate`) + ulang tahun profil.
 */
export function nextSpecialFromProfile(
  opts: { events?: Array<{ id?: string; title?: string; date?: string; recurring?: string; isSpecial?: boolean; icon?: string; category?: string }>;
    startDate?: string; myBirthdate?: string; partnerBirthdate?: string; myName?: string; partnerName?: string } = {},
  today?: string | Date | null,
  t?: (k: string, fb: string) => string,
): UpcomingItem | null {
  const tr = (k: string, fb: string) => (t ? t(k, fb) : fb);
  const now = todayIso(today) || new Date().toISOString().slice(0, 10);
  const out: UpcomingItem[] = [];
  const yearlyNext = (date: string): string | null => {
    const d = iso(date);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(d)) return null;
    const [, m, day] = d.split('-').map((x) => parseInt(x, 10));
    // Tahun berjalan diambil dari `now` — BUKAN dari tahun pada tanggal aslinya —
    // supaya ulang tahun/hari jadi lama (mis. 2020) tetap muncul di tahun ini.
    const nowYear = parseInt(now.slice(0, 4), 10);
    const clampDay = (yy: number) => {
      const dim = new Date(Date.UTC(yy, m, 0)).getUTCDate();   // hari terakhir bulan m
      return Math.min(day, dim);                              // 29 Feb → 28 Feb tahun non-kabisat
    };
    const pad = (n: number) => String(n).padStart(2, '0');
    const cand = `${nowYear}-${pad(m)}-${pad(clampDay(nowYear))}`;
    if (cand >= now) return cand;
    const nextYear = nowYear + 1;
    return `${nextYear}-${pad(m)}-${pad(clampDay(nextYear))}`;
  };
  const daysBetween = (a: string, b: string) => Math.round((Date.parse(`${a}T00:00:00Z`) - Date.parse(`${b}T00:00:00Z`)) / 86400000);
  const push = (item: Omit<UpcomingItem, 'nextDate' | 'daysUntil'>, raw?: string) => {
    const next = raw ? yearlyNext(raw) : null;
    if (!next) return;
    out.push({ ...item, nextDate: next, daysUntil: Math.max(0, daysBetween(next, now)) });
  };
  for (const ev of (opts.events || [])) {
    const recurring = String(ev.recurring || 'none') === 'yearly';
    if (!recurring) continue;   // acara sekali-jalan ditangani tab `plans`
    push({ id: String(ev.id || ''), title: ev.title || '', category: ev.category, icon: ev.icon,
      isSpecial: !!ev.isSpecial, recurring: 'yearly', source: 'event', kind: 'event' }, ev.date);
  }
  const birthday = (name: string) => tr('love_reminder_birthday', 'Ulang tahun {name}').replace('{name}', name);
  push({ id: 'start_date', title: tr('love_reminder_anniversary', 'Hari jadi hubungan'), category: 'anniversary',
    isSpecial: true, recurring: 'yearly', source: 'profile', kind: 'profile' }, opts.startDate);
  push({ id: 'my_birthdate', title: birthday(opts.myName || tr('love_me', 'Aku')), category: 'birthday',
    isSpecial: true, recurring: 'yearly', source: 'profile', kind: 'profile' }, opts.myBirthdate);
  push({ id: 'partner_birthdate', title: birthday(opts.partnerName || tr('love_partner_not_set', 'Pasangan')),
    category: 'birthday', isSpecial: true, recurring: 'yearly', source: 'profile', kind: 'profile' }, opts.partnerBirthdate);
  return nextSpecialDay(out);
}

/** Statistik perjalanan dari payload `loveSpace` (tanpa panggilan API baru). */
export function overviewStats(loveSpace: any = {}, today?: string | Date | null): OverviewStats {
  const month = (todayIso(today) || new Date().toISOString().slice(0, 10)).slice(0, 7);
  const memories = loveSpace.memories || [];
  const bucket = loveSpace.bucketList || loveSpace.bucketItems || [];
  const checkins = loveSpace.checkins || [];
  return {
    memories: memories.length,
    bucketDone: bucket.filter((b: any) => b && (b.isCompleted || b.isDone || b.done)).length,
    bucketTotal: bucket.length,
    photos: (loveSpace.photos || []).length,
    albums: (loveSpace.albums || []).length,
    prompts: (loveSpace.promptResponses || []).length,
    checkinsMonth: checkins.filter((c: any) => String(c?.date || '').slice(0, 7) === month).length,
    favorites: (loveSpace.promptFavorites || []).length,
    events: (loveSpace.events || []).length,
  };
}

/** Rincian skor kedekatan (memakai `checkinStats` dari connectionUtils). */
export function scoreBreakdown(loveSpace: any = {}, today?: string | Date | null): ScoreBreakdown {
  const now = todayIso(today) || new Date().toISOString().slice(0, 10);
  const rows = loveSpace.checkins || [];
  const stats = checkinStats(rows, now);
  const latest = [...rows].sort((a: any, b: any) => String(b?.date || '').localeCompare(String(a?.date || '')))[0];
  return {
    score: Math.max(0, Math.min(100, Number(loveSpace.connectionScore) || 0)),
    streak: stats.streak,
    total: stats.total,
    avgMy: stats.avgMy,
    avgPartner: stats.avgPartner,
    avgScore: stats.avgScore,
    lastDate: iso(latest?.date),
    hasToday: stats.hasToday,
  };
}

/** Kalimat pendek "belum check-in N hari" — dipakai di kartu skor. */
export function lastCheckinText(breakdown: ScoreBreakdown, today: string | Date | null, t: (k: string, fb: string) => string): string {
  if (!breakdown.lastDate) return t('love_score_no_checkin', 'Belum ada check-in');
  if (breakdown.lastDate === todayIso(today)) return t('love_checkin_today_short', 'Hari ini');
  let cursor = todayIso(today);
  let gap = 0;
  while (cursor > breakdown.lastDate && gap < 400) { cursor = shiftDay(cursor, -1); gap += 1; }
  return t('love_days_ago', '{days} hari lalu').replace('{days}', String(gap));
}

/** Agenda berikutnya (acara biasa) — untuk kartu "Akan datang" ringkas. */
export function nextAgenda(items: UpcomingItem[] = [], excludeId = ''): UpcomingItem | null {
  const rows = (items || []).filter((it) => it && it.id !== excludeId);
  if (!rows.length) return null;
  return [...rows].sort((a, b) => (Number(a.daysUntil ?? 9999) - Number(b.daysUntil ?? 9999)))[0] || null;
}

/** Aksi cepat untuk dashboard (label i18n + id tab tujuan / aksi khusus). */
export function quickActions(): Array<{ id: string; icon: string; labelKey: string; fallback: string; action: 'checkin' | 'memory' | 'event' | 'bucket' | 'reminders' }> {
  return [
    { id: 'checkin', icon: '💗', labelKey: 'love_quick_checkin', fallback: 'Check-in hari ini', action: 'checkin' },
    { id: 'memory', icon: '📸', labelKey: 'love_quick_memory', fallback: 'Tambah kenangan', action: 'memory' },
    { id: 'event', icon: '📅', labelKey: 'love_quick_event', fallback: 'Tambah acara', action: 'event' },
    { id: 'bucket', icon: '🎯', labelKey: 'love_quick_bucket', fallback: 'Tambah bucket', action: 'bucket' },
    { id: 'reminders', icon: '🔔', labelKey: 'love_quick_reminders', fallback: 'Lihat pengingat', action: 'reminders' },
  ];
}

/** Label jenis hubungan (i18n) — kosong bila belum diisi. */
export function relationshipLabel(value: string | undefined, t: (k: string, fb: string) => string): string {
  const v = String(value || '').toLowerCase();
  if (!v) return '';
  if (v === 'dating') return t('love_rel_dating', 'Pacaran');
  if (v === 'engaged') return t('love_rel_engaged', 'Bertunangan');
  if (v === 'married') return t('love_rel_married', 'Menikah');
  return String(value);
}

/** Apakah hari istimewa datang dari profil (bukan acara manual). */
export function isProfileSpecial(item: UpcomingItem | undefined): boolean {
  return !!item && (item.source === 'profile' || item.kind === 'profile');
}
