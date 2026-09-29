import React from 'react';
import { CountUp } from '../CountUp';

/**
 * I03 (v1.7.2) — SignatureKit: toolkit presentasi bersama untuk "tanda tangan"
 * tiap halaman (I04–I06). Prinsip:
 *  - R2 token-driven: warna dari --ct-* tokens; aksen halaman boleh override
 *    lewat prop `accent` (hex/var) yang tetap mengalir ke token --ct-sig-*.
 *  - R4 a11y: dekorasi selalu aria-hidden; heading semantik; reduced-motion
 *    sudah diguard di CSS (.ct-sig-* menghormati prefers-reduced-motion).
 *  - K3: murni presentasi — tidak menyentuh state, API, atau aturan game.
 *  - Semua animasi on-change/hover/masuk — tidak ada animasi paint idle.
 */

/* ────────────────────────────────────────────────────────────────────────
 * 1) PageSignature — kepala halaman khas: emblem soket + judul display +
 *    tagline + strip pola dekoratif (6 varian, khas per halaman).
 * ──────────────────────────────────────────────────────────────────────── */
export type SigPattern = 'wave' | 'grid' | 'orbit' | 'peaks' | 'dots' | 'circuit';

export const PageSignature: React.FC<{
  icon: React.ReactNode;
  title: string;
  tagline?: string;
  /** Nada aksen (hex atau var css) — dipakai emblem + strip. */
  accent?: string;
  pattern?: SigPattern;
  /** Slot kanan (mis. ring statistik cepat / tombol aksi). */
  right?: React.ReactNode;
  as?: 'h1' | 'h2';
  className?: string;
}> = ({ icon, title, tagline, accent, pattern = 'wave', right, as: Tag = 'h1', className = '' }) => {
  const vars = accent ? ({ ['--ct-sig-accent' as any]: accent } as React.CSSProperties) : undefined;
  return (
    <header
      className={`ct-sig ${className}`}
      style={vars}
      data-pattern={pattern}
    >
      <SigStrip variant={pattern} />
      <div className="ct-sig-row">
        <div className="ct-sig-emblem" aria-hidden="true">
          <span className="ct-sig-emblem-ring" />
          <span className="ct-sig-emblem-core">{icon}</span>
        </div>
        <div className="min-w-0">
          <Tag className="ct-sig-title" title={title}>{title}</Tag>
          {tagline && <p className="ct-sig-tag">{tagline}</p>}
        </div>
        {right && <div className="ct-sig-right">{right}</div>}
      </div>
    </header>
  );
};

/** Strip SVG dekoratif (aria-hidden) — geometri berbeda per varian.
 *  Diekspor agar halaman dengan banner kustom (Sport/Nutrition) bisa
 *  memasang pola khasnya sendiri di dalam kartu mereka. */
export const SigStrip: React.FC<{ variant: SigPattern }> = ({ variant }) => {
  const stroke = 'var(--ct-sig-accent, var(--ct-primary))';
  const common = {
    className: 'ct-sig-strip',
    viewBox: '0 0 600 64',
    preserveAspectRatio: 'none',
    'aria-hidden': true as const,
    focusable: false as const,
  };
  switch (variant) {
    case 'grid':
      return (
        <svg {...common}>
          {Array.from({ length: 15 }).map((_, i) => (
            <line key={`v${i}`} x1={i * 42} y1="0" x2={i * 42} y2="64" stroke={stroke} strokeWidth="1" />
          ))}
          <line x1="0" y1="32" x2="600" y2="32" stroke={stroke} strokeWidth="1.5" />
        </svg>
      );
    case 'orbit':
      return (
        <svg {...common}>
          <ellipse cx="520" cy="32" rx="90" ry="26" fill="none" stroke={stroke} strokeWidth="1.5" />
          <ellipse cx="520" cy="32" rx="150" ry="14" fill="none" stroke={stroke} strokeWidth="1" />
          <circle cx="430" cy="40" r="4" fill={stroke} />
          <circle cx="600" cy="22" r="3" fill={stroke} />
        </svg>
      );
    case 'peaks':
      return (
        <svg {...common}>
          <polyline
            points="0,58 60,40 120,50 180,22 240,44 300,12 360,38 420,20 480,46 540,28 600,50"
            fill="none" stroke={stroke} strokeWidth="2" strokeLinejoin="round"
          />
          <polyline
            points="0,62 80,52 160,58 240,40 320,56 400,34 480,54 560,44 600,58"
            fill="none" stroke={stroke} strokeWidth="1" opacity="0.55"
          />
        </svg>
      );
    case 'dots':
      return (
        <svg {...common}>
          {Array.from({ length: 8 }).map((_, r) =>
            Array.from({ length: 30 }).map((_, c) => (
              <circle key={`${r}-${c}`} cx={c * 20 + (r % 2 ? 10 : 0)} cy={r * 8 + 4} r="1.4" fill={stroke} />
            )),
          )}
        </svg>
      );
    case 'circuit':
      return (
        <svg {...common}>
          <path d="M0 48 H120 V20 H260 V44 H420 V14 H600" fill="none" stroke={stroke} strokeWidth="1.6" />
          <path d="M0 16 H80 V40 H200 V56 H360 V30 H520 V52 H600" fill="none" stroke={stroke} strokeWidth="1" opacity="0.5" />
          <circle cx="120" cy="20" r="3.2" fill={stroke} />
          <circle cx="260" cy="44" r="3.2" fill={stroke} />
          <circle cx="420" cy="14" r="3.2" fill={stroke} />
        </svg>
      );
    case 'wave':
    default:
      return (
        <svg {...common}>
          <path d="M0 40 Q 75 12 150 34 T 300 32 T 450 30 T 600 36" fill="none" stroke={stroke} strokeWidth="2" />
          <path d="M0 52 Q 90 30 180 46 T 360 44 T 600 48" fill="none" stroke={stroke} strokeWidth="1.2" opacity="0.5" />
        </svg>
      );
  }
};

/* ────────────────────────────────────────────────────────────────────────
 * 2) SigStat — tile statistik: ikon, label, angka count-up, delta opsional.
 * ──────────────────────────────────────────────────────────────────────── */
export const SigStat: React.FC<{
  icon?: React.ReactNode;
  label: string;
  value: number;
  format?: (n: number) => string;
  /** Mis. "+12%" / "▲ 3" — teks bebas, tampil sebagai chip kecil. */
  delta?: string;
  deltaTone?: 'up' | 'down' | 'flat';
  tone?: 'primary' | 'accent' | 'success' | 'warn' | 'danger';
  className?: string;
}> = ({ icon, label, value, format, delta, deltaTone = 'flat', tone = 'primary', className = '' }) => (
  <div className={`ct-sig-stat ct-sig-stat--${tone} ${className}`}>
    {icon && <span className="ct-sig-stat-icon" aria-hidden="true">{icon}</span>}
    <div className="min-w-0">
      <p className="ct-sig-stat-label">{label}</p>
      <p className="ct-sig-stat-value">
        <CountUp value={value} format={format} />
        {delta && <span className={`ct-sig-delta ct-sig-delta--${deltaTone}`}>{delta}</span>}
      </p>
    </div>
  </div>
);

/* ────────────────────────────────────────────────────────────────────────
 * 3) SigRing — cincin progres SVG; animasi dashoffset saat nilai berubah.
 * ──────────────────────────────────────────────────────────────────────── */
export const SigRing: React.FC<{
  /** 0..1 */
  ratio: number;
  size?: number;
  stroke?: number;
  accent?: string;
  label?: string;
  children?: React.ReactNode;
  className?: string;
}> = ({ ratio, size = 72, stroke = 7, accent, label, children, className = '' }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(1, Number.isFinite(ratio) ? ratio : 0));
  return (
    <div
      className={`ct-sig-ring ${className}`}
      role="img"
      aria-label={label || `${Math.round(clamped * 100)}%`}
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" focusable="false">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} className="ct-sig-ring-track" />
        <circle
          cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke}
          strokeLinecap="round"
          className="ct-sig-ring-arc"
          style={{
            stroke: accent || undefined,
            strokeDasharray: c,
            strokeDashoffset: c * (1 - clamped),
          }}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </svg>
      {children && <span className="ct-sig-ring-center">{children}</span>}
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────────
 * 4) SigBar — bar progres dengan kilau on-change + label/value opsional.
 * ──────────────────────────────────────────────────────────────────────── */
export const SigBar: React.FC<{
  ratio: number;
  accent?: string;
  label?: string;
  valueText?: string;
  segmented?: number;
  className?: string;
}> = ({ ratio, accent, label, valueText, segmented, className = '' }) => {
  const pct = Math.round(Math.max(0, Math.min(1, Number.isFinite(ratio) ? ratio : 0)) * 100);
  return (
    <div className={`ct-sig-barwrap ${className}`}>
      {(label || valueText) && (
        <div className="ct-sig-bar-meta">
          {label && <span className="ct-sig-bar-label">{label}</span>}
          {valueText && <span className="ct-sig-bar-value">{valueText}</span>}
        </div>
      )}
      <div
        className="ct-sig-bar"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label || undefined}
      >
        <div
          className={`ct-sig-bar-fill${segmented ? ' ct-sig-bar-fill--segmented' : ''}`}
          style={{ width: `${pct}%`, background: accent || undefined, ['--ct-sig-seg' as any]: segmented || 10 }}
        />
      </div>
    </div>
  );
};

/* ────────────────────────────────────────────────────────────────────────
 * 5) SigBadge — chip status kecil (tone + titik).
 * ──────────────────────────────────────────────────────────────────────── */
export const SigBadge: React.FC<{
  tone?: 'primary' | 'accent' | 'success' | 'warn' | 'danger' | 'muted';
  dot?: boolean;
  children: React.ReactNode;
  className?: string;
}> = ({ tone = 'muted', dot, children, className = '' }) => (
  <span className={`ct-sig-badge ct-sig-badge--${tone} ${className}`}>
    {dot && <span className="ct-sig-badge-dot" aria-hidden="true" />}
    {children}
  </span>
);

/* ────────────────────────────────────────────────────────────────────────
 * 6) SigSection — judul seksi: garis aksen + judul + hitungan + slot kanan.
 * ──────────────────────────────────────────────────────────────────────── */
export const SigSection: React.FC<{
  icon?: React.ReactNode;
  title: string;
  count?: number | string;
  right?: React.ReactNode;
  accent?: string;
  className?: string;
}> = ({ icon, title, count, right, accent, className = '' }) => (
  <div className={`ct-sig-section ${className}`} style={accent ? ({ ['--ct-sig-accent' as any]: accent } as React.CSSProperties) : undefined}>
    <span className="ct-sig-section-rule" aria-hidden="true" />
    {icon && <span className="ct-sig-section-icon" aria-hidden="true">{icon}</span>}
    <h3 className="ct-sig-section-title">{title}</h3>
    {count !== undefined && <span className="ct-sig-section-count">{count}</span>}
    {right && <span className="ml-auto flex items-center gap-2">{right}</span>}
  </div>
);

/* ────────────────────────────────────────────────────────────────────────
 * 7) SigEmpty — empty state khas (ikon besar + judul + petunjuk + aksi).
 * ──────────────────────────────────────────────────────────────────────── */
export const SigEmpty: React.FC<{
  icon: React.ReactNode;
  title: string;
  hint?: string;
  action?: React.ReactNode;
  className?: string;
}> = ({ icon, title, hint, action, className = '' }) => (
  <div className={`ct-sig-empty ${className}`}>
    <span className="ct-sig-empty-icon" aria-hidden="true">{icon}</span>
    <p className="ct-sig-empty-title">{title}</p>
    {hint && <p className="ct-sig-empty-hint">{hint}</p>}
    {action && <div className="mt-3">{action}</div>}
  </div>
);

/* ────────────────────────────────────────────────────────────────────────
 * 8) SigCard — kartu interaktif: hover lift + border aksen + reveal.
 * ──────────────────────────────────────────────────────────────────────── */
export const SigCard: React.FC<{
  children: React.ReactNode;
  accent?: string;
  /** delay ms untuk stagger reveal. */
  delay?: number;
  className?: string;
  onClick?: React.MouseEventHandler;
}> = ({ children, accent, delay = 0, className = '', onClick }) => {
  const El: any = onClick ? 'button' : 'div';
  return (
    <El
      className={`ct-sig-card ct-enter ${className}`}
      style={{ animationDelay: delay ? `${delay}ms` : undefined, ['--ct-sig-accent' as any]: accent || undefined }}
      onClick={onClick}
      type={onClick ? 'button' : undefined}
    >
      {children}
    </El>
  );
};

/* ────────────────────────────────────────────────────────────────────────
 * 9) useStagger — helper delay reveal berjenjang (R10: tanpa layout thrash).
 * ──────────────────────────────────────────────────────────────────────── */
export const stagger = (index: number, step = 45, cap = 480): React.CSSProperties => ({
  animationDelay: `${Math.min(index * step, cap)}ms`,
});
