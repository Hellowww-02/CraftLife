/**
 * NumberInput.tsx — Input angka tanpa "snap-back" (P49).
 *
 * Masalah lama: pola `value={x} onChange={Number(e.target.value) || default}`
 * membuat kotak tidak bisa dikosongkan — backspace terakhir menghasilkan ''
 * → Number('') = 0 → state kembali ke nilai default → kotak "nylonong" balik
 * ke angka default/0 saat masih diedit.
 *
 * Perilaku baru:
 *  - Kotak dikosongkan → TETAP kosong; nilai form menjadi `emptyValue` (default 0),
 *    sehingga validasi Save (mis. `amount <= 0`) yang tetap menangkap isian kosong.
 *  - Tidak ada reformat/clamp pada TEKS saat user mengetik — teks selalu persis
 *    apa yang diketik; NILAI yang di-emit sudah di-clamp ke [min, max]
 *    (dan dibulatkan bila `integer`) sehingga state form selalu valid.
 *  - Normalisasi tampilan (clamp + format) hanya terjadi saat onBlur.
 *  - Nilai 0 dari luar (default form) ditampilkan sebagai kotak kosong
 *    ("belum diisi"), tapi "0" yang diketik user tetap tampil "0".
 *  - Sinkronisasi dari prop `value` (ganti item yang diedit / reset dialog)
 *    tetap berjalan lewat guard `lastEmitted` — gema dari emit sendiri tidak
 *    menimpa teks yang sedang diketik.
 */
import React from 'react';

interface NumberInputProps {
  value: number;
  onValueChange: (n: number) => void;
  /** Batas bawah (dipakai untuk clamp nilai emit & normalisasi onBlur). */
  min?: number;
  /** Batas atas. */
  max?: number;
  /** Bulatkan nilai ke integer. */
  integer?: boolean;
  /** Nilai form saat kotak dikosongkan (default 0). */
  emptyValue?: number;
  /** Kelas untuk elemen <input> (komponen tidak menambah kelas default). */
  inputClassName?: string;
  placeholder?: string;
  disabled?: boolean;
}

/** Parse input bebas: terima "12", "12.5", "12,5", "-3"; kosong/aneh → null. */
function parseNumInput(raw: string): number | null {
  const s = String(raw ?? '').trim().replace(/,/g, '.');
  if (!s || !/^-?\d*\.?\d*$/.test(s)) return null;
  const v = parseFloat(s);
  return Number.isFinite(v) ? v : null;
}

export const NumberInput: React.FC<NumberInputProps> = ({
  value,
  onValueChange,
  min,
  max,
  integer,
  emptyValue = 0,
  inputClassName,
  placeholder,
  disabled,
}) => {
  /** 0 eksternal (default form) tampil kosong; angka lain apa adanya. */
  const toDisplay = (n: number): string => (Number(n) === 0 ? '' : String(n));

  const [text, setText] = React.useState<string>(() => toDisplay(Number(value)));
  const lastEmitted = React.useRef<number | null>(null);

  // Sinkron hanya untuk perubahan EXTERNAL (bukan gema emit kita sendiri).
  React.useEffect(() => {
    if (Number(value) === lastEmitted.current) return;
    setText(toDisplay(Number(value)));
  }, [value]);

  const clamp = (n: number): number => {
    let v = n;
    if (min !== undefined && v < min) v = min;
    if (max !== undefined && v > max) v = max;
    return integer ? Math.round(v) : v;
  };

  const emit = (n: number) => {
    lastEmitted.current = n;
    onValueChange(n);
  };

  return (
    <input
      type="text"
      inputMode="decimal"
      value={text}
      disabled={disabled}
      placeholder={placeholder}
      onChange={(e) => {
        setText(e.target.value);
        const n = parseNumInput(e.target.value);
        emit(n === null ? clamp(emptyValue) : clamp(n));
      }}
      onBlur={() => {
        const n = parseNumInput(text);
        if (n === null) {
          // Kotak dibiarkan KOSONG (P49) — form sudah memegang emptyValue.
          setText('');
          return;
        }
        const c = clamp(n);
        setText(String(c));
        if (c !== lastEmitted.current) emit(c);
      }}
      className={inputClassName}
    />
  );
};
