export type CurrencyCode = string;
/** Ambil kurs dari server (/api/catalog/currency → db.CURRENCY_RATES). Sekali per sesi. */
export declare function ensureCurrencyRates(): Promise<Record<string, number>>;
export declare function getCurrencyRates(): Record<string, number>;
export declare function currencySymbol(currency: CurrencyCode): string;
/** IDR → mata uang user (db.convert_from_idr). */
export declare function fromIdr(amountIdr: number, currency: CurrencyCode): number;
/**
 * Format parity PyQt format_currency(): simbol + ribuan, 0 desimal.
 * Amount dianggap tersimpan sebagai IDR.
 */
export declare function formatMoney(amountIdr: number, currency: CurrencyCode): string;
/**
 * parse_amount parity `_parse_positive_amount` PyQt:
 * terima "1000", "1000.5", "1.000,5" tidak — PyQt mengganti koma→titik ("12,5"→12.5).
 * Return float > 0, atau null bila kosong/bukan angka/<=0.
 */
export declare function parseAmount(text: string): number | null;
/**
 * P30: parse input nominal uang yang sedang diketik user (mata uang apa pun).
 * Menangani pemisah ribuan & desimal gaya EN ("1,234,567.89") maupun ID ("1.234.567,89")
 * sehingga input tetap benar walau currency aktif bukan IDR.
 * Return number, atau null bila kosong/tidak valid.
 */
export declare function parseMoneyInput(text: string): number | null;
/**
 * P30: format nilai untuk ditampilkan di dalam input uang (pemisah ribuan,
 * maks 2 desimal). Menerima number ataupun string.
 */
export declare function maskMoney(value: string | number | null | undefined): string;
//# sourceMappingURL=currency.d.ts.map