/**
 * MoneyInput.tsx — Input nominal uang dengan format currency aktif (P30).
 *
 * Parity AddEconomyDialog / dialog economy PyQt: input ditulis dalam mata uang
 * pilihan user (bukan IDR). Komponen ini menampilkan simbol currency sebagai
 * prefix dan memformat pemisah ribuan; nilai numeriknya diteruskan apa adanya
 * (server mengonversi ke IDR via db.convert_to_idr).
 *
 * P49 FIX (input nominal "balik ke 0/nilai lama"):
 *  - Dulu `useEffect([value])` mereformat teks pada SETIAP ketikan (karena
 *    parent meng-echo nilai yang sama kita emit) → pemisah ribuan muncul di
 *    tengah mengetik, cursor lompat, dan backspace ke kosong membuat `onBlur`
 *    mengembalikan teks ke nilai lama.
 *  - Sekarang: reformat HANYA saat blur; kotak yang dikosongkan TETAP kosong
 *    (form menerima 0 → validasi Save `<= 0` menangkap isian kosong); dan
 *    sinkronisasi dari `value` luar (ganti item yang diedit / reset dialog)
 *    tetap jalan lewat guard `lastEmitted`.
 *  - Nilai 0 eksternal (form baru) tampil sebagai kotak kosong, bukan "0".
 */
import React from 'react';
import { currencySymbol, maskMoney, parseMoneyInput } from '../utils/currency';

interface MoneyInputProps {
  value: number | string;
  onValueChange: (n: number) => void;
  currency?: string;
  /** Kelas untuk wrapper (lebar/padding luar). */
  className?: string;
  /** Kelas untuk elemen <input> (ukuran/rounding). Default: py-2 text-sm rounded-xl. */
  inputClassName?: string;
  placeholder?: string;
  disabled?: boolean;
}

export const MoneyInput: React.FC<MoneyInputProps> = ({
  value,
  onValueChange,
  currency = 'IDR',
  className = '',
  inputClassName,
  placeholder,
  disabled,
}) => {
  /** 0 eksternal (form baru) tampil kosong; nominal lain terformat ribuan. */
  const toDisplay = (v: number | string): string =>
    Number(v) === 0 ? '' : maskMoney(v);

  const [text, setText] = React.useState<string>(() => toDisplay(value));
  const lastEmitted = React.useRef<number | null>(null);

  // Sinkron dari luar HANYA bila bukan gema emit sendiri — mencegah reformat
  // ribuan di tengah ketikan (cursor lompat) yang terjadi pada versi lama.
  React.useEffect(() => {
    const n = typeof value === 'number' ? value : parseMoneyInput(String(value));
    if (n !== null && n === lastEmitted.current) return;
    setText(toDisplay(value));
  }, [value]);

  return (
    <div className={`relative ${className}`}>
      <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[10px] font-bold text-slate-500 select-none">
        {currencySymbol(currency)}
      </span>
      <input
        type="text"
        inputMode="decimal"
        value={text}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => {
          setText(e.target.value);
          const n = parseMoneyInput(e.target.value);
          // P49: kosong/aneh → form 0, tapi kotak TETAP kosong (tidak snap-back).
          const out = n === null ? 0 : n;
          lastEmitted.current = out;
          onValueChange(out);
        }}
        onBlur={() => {
          const n = parseMoneyInput(text);
          // P49: kotak kosong dibiarkan kosong — bukan dikembalikan ke nilai lama.
          setText(n === null ? '' : maskMoney(n));
        }}
        className={`ct-input w-full pl-8 pr-2 text-slate-100 ${inputClassName ?? 'py-2 text-sm rounded-xl'}`}
      />
    </div>
  );
};
