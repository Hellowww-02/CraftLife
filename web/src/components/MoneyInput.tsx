/**
 * MoneyInput.tsx — Input nominal uang dengan format currency aktif (P30).
 *
 * Parity AddEconomyDialog / dialog economy PyQt: input ditulis dalam mata uang
 * pilihan user (bukan IDR). Komponen ini menampilkan simbol currency sebagai
 * prefix dan memformat pemisah ribuan; nilai numeriknya diteruskan apa adanya
 * (server mengonversi ke IDR via db.convert_to_idr).
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
  const [text, setText] = React.useState<string>(maskMoney(value));

  // Sinkronkan teks saat nilai berubah dari luar (edit item, dsb.).
  React.useEffect(() => {
    setText(maskMoney(value));
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
          const raw = e.target.value;
          setText(raw);
          const n = parseMoneyInput(raw);
          if (n !== null) onValueChange(n);
        }}
        onBlur={() => setText(maskMoney(value))}
        className={`w-full pl-8 pr-2 bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500 ${inputClassName ?? 'py-2 text-sm rounded-xl'}`}
      />
    </div>
  );
};
