/**
 * Utilitas tanggal ber-zona app (parity TimeSync/date.today() backend).
 * Semua fungsi membaca FIELD LOKAL dari Date yang dibangun dengan Y/M/D server
 * (lihat GameContext.nowDate) sehingga hasilnya identik di zona browser apa pun.
 */

function pad(n: number) { return String(n).padStart(2, '0'); }

/** YYYY-MM-DD dari field lokal (zona app), bukan toISOString (zona UTC). */
export function fmtYmd(d: Date | null | undefined): string {
  if (!d) return '';
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Salin Date + geser hari (mutasi pada salinan, style setDate PyQt). */
export function addDays(d: Date, days: number): Date {
  const c = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  c.setDate(c.getDate() + days);
  return c;
}

/** Bangun Date lokal dari string YYYY-MM-DD server (tidak pakai zona browser utk
 *  penentuan 'hari', hanya sebagai konstruktor kalender). Fallback bila clockNow null. */
export function dateFromYmd(ymd: string): Date {
  const [y, m, d] = ymd.split('-').map((x) => parseInt(x, 10));
  return new Date(y || 1970, (m || 1) - 1, d || 1);
}

/** Senin sebagai awal minggu (weekday 0=Sen..6=Min), parity Python weekday. */
export function startOfWeek(d: Date): Date {
  const c = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dow = (c.getDay() + 6) % 7; // getDay: 0=Min → konversi 0=Sen
  c.setDate(c.getDate() - dow);
  return c;
}

/** ISO UTC timestamp utk kolom createdAt (parity datetime.utcnow().isoformat). */
export function nowIsoFromClock(clockNow: Date | null): string {
  return (clockNow ? clockNow.toISOString() : new Date().toISOString());
}

/** HH:MM (24h) dari field lokal. */
export function fmtHM(d: Date | null | undefined): string {
  if (!d) return '';
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** HH:MM:SS dari field lokal (parity TimeSync._fmt HH:MM:SS). */
export function fmtHMS(d: Date | null | undefined): string {
  if (!d) return '';
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

/**
 * Format waktu pesan chat (HH:MM) mengikuti ZONA LOKASI USER (browser) — sama
 * persis dengan jam di Navbar, jadi chat selalu sinkron dengan jam app.
 * Prioritas:
 *  1. `epochSec` (unix detik absolut dari backend) → render di zona browser user.
 *  2. `iso` ber-zona (Z / ±HH:MM, mis. pesan cloud/pending) → instan absolut.
 *  3. `iso` naif (fallback) → slice mentah (hanya utk kasus tanpa epoch).
 */
export function fmtChatTime(iso: string | null | undefined, epochSec?: number | null): string {
  if (epochSec != null && Number.isFinite(Number(epochSec))) {
    const d = new Date(Number(epochSec) * 1000);
    if (!Number.isNaN(d.getTime())) return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  if (!iso) return '';
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/.test(iso.trim());
  if (!hasZone) return iso.slice(11, 16);
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(11, 16);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
