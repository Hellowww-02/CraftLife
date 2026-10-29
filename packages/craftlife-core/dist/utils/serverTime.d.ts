/**
 * Utilitas tanggal ber-zona app (parity TimeSync/date.today() backend).
 * Semua fungsi membaca FIELD LOKAL dari Date yang dibangun dengan Y/M/D server
 * (lihat GameContext.nowDate) sehingga hasilnya identik di zona browser apa pun.
 */
/** YYYY-MM-DD dari field lokal (zona app), bukan toISOString (zona UTC). */
export declare function fmtYmd(d: Date | null | undefined): string;
/** Salin Date + geser hari (mutasi pada salinan, style setDate PyQt). */
export declare function addDays(d: Date, days: number): Date;
/** Bangun Date lokal dari string YYYY-MM-DD server (tidak pakai zona browser utk
 *  penentuan 'hari', hanya sebagai konstruktor kalender). Fallback bila clockNow null. */
export declare function dateFromYmd(ymd: string): Date;
/** Senin sebagai awal minggu (weekday 0=Sen..6=Min), parity Python weekday. */
export declare function startOfWeek(d: Date): Date;
/** ISO UTC timestamp utk kolom createdAt (parity datetime.utcnow().isoformat). */
export declare function nowIsoFromClock(clockNow: Date | null): string;
/** HH:MM (24h) dari field lokal. */
export declare function fmtHM(d: Date | null | undefined): string;
/** HH:MM:SS dari field lokal (parity TimeSync._fmt HH:MM:SS). */
export declare function fmtHMS(d: Date | null | undefined): string;
/**
 * Format waktu pesan chat (HH:MM) mengikuti ZONA LOKASI USER (browser) — sama
 * persis dengan jam di Navbar, jadi chat selalu sinkron dengan jam app.
 * Prioritas:
 *  1. `epochSec` (unix detik absolut dari backend) → render di zona browser user.
 *  2. `iso` ber-zona (Z / ±HH:MM, mis. pesan cloud/pending) → instan absolut.
 *  3. `iso` naif (fallback) → slice mentah (hanya utk kasus tanpa epoch).
 */
export declare function fmtChatTime(iso: string | null | undefined, epochSec?: number | null): string;
//# sourceMappingURL=serverTime.d.ts.map