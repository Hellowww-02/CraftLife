/**
 * Currency single-source (P2).
 *
 * Parity dengan EconomyPage/AddEconomyDialog PyQt:
 *  - DB SELALU menyimpan IDR (add_economy dkk.).
 *  - Input dialog ditulis dalam mata uang user → server konversi via db.convert_to_idr.
 *  - Display = convert_from_idr(amount_idr) lalu simbol + pemisah ribuan TANPA desimal
 *    (PyQt: f"{symbol} {converted:,.0f}").
 *
 * Semua formatter uang di Web UI WAJIB lewat modul ini — tidak ada lagi "Rp" hardcoded.
 */
import { apiGet } from '../api/client';

export type CurrencyCode = string;

let RATES: Record<string, number> = { IDR: 1, USD: 17800, EUR: 20700 };
let ratesLoaded = false;

/** Ambil kurs dari server (/api/catalog/currency → db.CURRENCY_RATES). Sekali per sesi. */
export async function ensureCurrencyRates(): Promise<Record<string, number>> {
  if (ratesLoaded) return RATES;
  try {
    const d = await apiGet<any>('/api/catalog/currency');
    if (d?.rates && typeof d.rates === 'object') {
      RATES = { ...RATES, ...d.rates };
    }
  } catch {
    // fallback ke kurs bawaan (sama dengan database.py)
  }
  ratesLoaded = true;
  return RATES;
}

export function getCurrencyRates(): Record<string, number> {
  return RATES;
}

export function currencySymbol(currency: CurrencyCode): string {
  const symbols: Record<string, string> = { IDR: 'Rp', USD: '$', EUR: '€' };
  return symbols[currency] || currency || 'Rp';
}

/** IDR → mata uang user (db.convert_from_idr). */
export function fromIdr(amountIdr: number, currency: CurrencyCode): number {
  const rate = RATES[currency] || 1;
  return currency === 'IDR' ? amountIdr : amountIdr / rate;
}

/**
 * Format parity PyQt format_currency(): simbol + ribuan, 0 desimal.
 * Amount dianggap tersimpan sebagai IDR.
 */
export function formatMoney(amountIdr: number, currency: CurrencyCode): string {
  const converted = fromIdr(Number(amountIdr) || 0, currency);
  return `${currencySymbol(currency)} ${converted.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

/**
 * parse_amount parity `_parse_positive_amount` PyQt:
 * terima "1000", "1000.5", "1.000,5" tidak — PyQt mengganti koma→titik ("12,5"→12.5).
 * Return float > 0, atau null bila kosong/bukan angka/<=0.
 */
export function parseAmount(text: string): number | null {
  try {
    const val = parseFloat(String(text || '').trim().replace(/,/g, '.'));
    if (Number.isNaN(val) || val <= 0) return null;
    return val;
  } catch {
    return null;
  }
}
