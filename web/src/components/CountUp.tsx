import React, { useEffect, useRef, useState } from 'react';

interface CountUpProps {
  /** Nilai akhir (bilangan bulat: gold, nominal uang). */
  value: number;
  /** Pemformat tampilan; default ribuan lokal. */
  format?: (n: number) => string;
  /** Durasi animasi ms; 0 = instan. */
  duration?: number;
  className?: string;
}

/**
 * D04 (v1.6.7, backlog v2.1 "count-up angka"): angka penting menghitung naik
 * saat tampil/berubah — tanpa mengubah nilai akhirnya sedikit pun.
 * `prefers-reduced-motion` → langsung nilai akhir (R4).
 */
export const CountUp: React.FC<CountUpProps> = ({ value, format, duration = 600, className }) => {
  const target = Math.round(Number.isFinite(value) ? value : 0);
  const [shown, setShown] = useState(target);
  const fromRef = useRef(0);
  const rafRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    if (
      from === target ||
      duration <= 0 ||
      (typeof window !== 'undefined' &&
        typeof window.matchMedia === 'function' &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches)
    ) {
      setShown(target);
      fromRef.current = target;
      return;
    }
    const t0 = performance.now();
    const tick = (now: number) => {
      const p = Math.min(1, (now - t0) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(from + (target - from) * eased));
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        fromRef.current = target;
      }
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(rafRef.current);
      fromRef.current = target;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  const fmt = format ?? ((n: number) => n.toLocaleString());
  return <span className={className}>{fmt(shown)}</span>;
};
