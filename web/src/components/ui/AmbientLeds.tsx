import React, { useEffect, useMemo, useRef } from 'react';

/**
 * v1.7.4 rev-C — AmbientLeds: pencahayaan ambient di PERIMETER lingkungan
 * CraftLife (seperti LED strip di frame sebuah setup), BUKAN di atas
 * konten. Desain mengikuti praktik skill UI/UX yang terpasang:
 *  - decor terpisah dari konten (pointer-events-none, tepi frame saja),
 *  - animasi murah (opacity/transform), masuk akal & tidak idle-berat,
 *  - interaktif: node terdekat kursor menyala; event (toast/naik level)
 *    memicu gelombang pulse; ganti halaman = signature baru,
 *  - variasi: 3 mode gerak (breathe/chase/twinkle) dipilih deterministik
 *    per halaman; 12 tema menyetel warna/bentuk/tempo via [data-theme],
 *  - a11y: aria-hidden penuh; prefers-reduced-motion → statis;
 *    on/off di Settings (html[data-fx-leds]).
 */

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return Math.abs(h);
}

type Mode = 'breathe' | 'chase' | 'twinkle';
const MODES: Mode[] = ['breathe', 'chase', 'twinkle'];

export const AmbientLeds: React.FC<{ seed: string }> = ({ seed }) => {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const litRef = useRef<HTMLElement | null>(null);
  const pulseTimer = useRef<number | null>(null);

  // Signature halaman: mode gerak, jumlah node, arah, tempo, pasangan warna.
  const cfg = useMemo(() => {
    const h = hash(seed || 'dashboard');
    return {
      mode: MODES[h % 3],
      left: 10 + (h % 6),                 // node rail kiri 10–15
      right: 10 + ((h >> 3) % 6),         // node rail kanan 10–15
      bottom: 14 + ((h >> 6) % 8),        // node rail bawah 14–21
      rev: ((h >> 9) & 1) === 1,          // arah chase
      pair: (h >> 10) % 4,                // pasangan warna aksen
      tempo: 0.85 + ((h >> 12) % 5) * 0.12, // pengali kecepatan per halaman
    };
  }, [seed]);

  // Interaksi kursor: node terdekat (radius 130px) menyala terang.
  useEffect(() => {
    let raf = 0;
    const onMove = (e: PointerEvent) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const el = wrapRef.current;
        if (!el) return;
        const nodes = el.querySelectorAll<HTMLElement>('.ct-amb-node');
        let best: HTMLElement | null = null;
        let bd = 130 * 130;
        nodes.forEach((n) => {
          const r = n.getBoundingClientRect();
          const dx = r.left + r.width / 2 - e.clientX;
          const dy = r.top + r.height / 2 - e.clientY;
          const d = dx * dx + dy * dy;
          if (d < bd) { bd = d; best = n; }
        });
        if (litRef.current && litRef.current !== best) {
          litRef.current.classList.remove('ct-amb-node--lit');
        }
        // TS tidak melacak mutasi di dalam closure forEach — cast eksplisit aman.
        const found = best as unknown as HTMLElement | null;
        if (found) found.classList.add('ct-amb-node--lit');
        litRef.current = found;
      });
    };
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => {
      window.removeEventListener('pointermove', onMove);
      if (raf) cancelAnimationFrame(raf);
      litRef.current?.classList.remove('ct-amb-node--lit');
      litRef.current = null;
    };
  }, []);

  // Gelombang pulse saat event aplikasi (toast, level-up, craft, spin).
  useEffect(() => {
    const onPulse = () => {
      const el = wrapRef.current;
      if (!el) return;
      el.classList.remove('ct-amb-pulsing');
      // reflow kecil agar animasi bisa dipicu ulang berturut-turut
      void el.offsetWidth;
      el.classList.add('ct-amb-pulsing');
      if (pulseTimer.current) window.clearTimeout(pulseTimer.current);
      pulseTimer.current = window.setTimeout(() => el.classList.remove('ct-amb-pulsing'), 1100);
    };
    window.addEventListener('ct-led-pulse', onPulse);
    return () => {
      window.removeEventListener('ct-led-pulse', onPulse);
      if (pulseTimer.current) window.clearTimeout(pulseTimer.current);
    };
  }, []);

  // Delay per node: chase = berurutan (arah per halaman), breathe/twinkle
  // = offset bergelombang; twinkle memakai langkah pseudo-acak deterministik.
  const delayFor = (i: number, n: number): number => {
    const idx = cfg.rev ? n - 1 - i : i;
    if (cfg.mode === 'chase') return idx * 160 * cfg.tempo;
    if (cfg.mode === 'twinkle') return ((idx * 37) % Math.max(1, n)) * 120 * cfg.tempo;
    return Math.abs(i - (n - 1) / 2) * 110 * cfg.tempo; // breathe dari tengah
  };

  const rail = (n: number) =>
    Array.from({ length: n }).map((_, i) => (
      <span
        key={i}
        className={`ct-amb-node${(i + cfg.pair) % 5 === 0 ? ' ct-amb-node--hi' : ''}`}
        style={{ ['--ct-amb-d' as any]: `${Math.round(delayFor(i, n))}ms` }}
      />
    ));

  return (
    <div
      ref={wrapRef}
      className="ct-amb"
      data-mode={cfg.mode}
      data-pair={cfg.pair}
      aria-hidden="true"
    >
      {/* Rel perimeter — hanya di tepi frame, tidak menyentuh konten */}
      <div className="ct-amb-rail ct-amb-rail--left">{rail(cfg.left)}</div>
      <div className="ct-amb-rail ct-amb-rail--right">{rail(cfg.right)}</div>
      <div className="ct-amb-rail ct-amb-rail--bottom">{rail(cfg.bottom)}</div>
      {/* Aksen sudut + tumpahan cahaya tepi (sangat tipis) */}
      <div className="ct-amb-corner ct-amb-corner--tl"><i /><i /><i /></div>
      <div className="ct-amb-corner ct-amb-corner--tr"><i /><i /><i /></div>
      <div className="ct-amb-corner ct-amb-corner--br"><i /><i /><i /></div>
      <div className="ct-amb-spill ct-amb-spill--l" />
      <div className="ct-amb-spill ct-amb-spill--r" />
      <div className="ct-amb-spill ct-amb-spill--b" />
    </div>
  );
};
