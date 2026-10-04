/**
 * charts.tsx — Lightweight SVG chart primitives for CraftLife (Phase P0).
 *
 * Purpose: deliver pixel-light, dependency-free visualization so every view can
 * reach parity with the PyQt QPainter-based widgets (EconomyTrendWidget,
 * SportRepsChartWidget, HealthChartWidget, ProgressRing, HeatmapWidget)
 * without pulling in a heavy chart library.
 *
 * All components are pure SVG + Tailwind-friendly inline props and are
 * deliberately "dumb": they render data and call callbacks; no game logic here.
 * (No charts for trivial single-value data — ProgressRing covers that.)
 *
 * P30: LineChart / DualLineChart / BarChart / Sparkline are now RESPONSIVE —
 * they measure their container width (ResizeObserver) and stretch edge-to-edge
 * instead of being pinned to the fixed `width` prop (fix "chart mentok kiri").
 */
import React, { useId, useLayoutEffect, useRef, useState } from 'react';

/* ------------------------------------------------------------------ types */

interface ChartPoint {
  label: string;
  value: number;
}

interface BaseSeries {
  /** CSS color-string, e.g. '#34d399' or 'class="text-emerald-400"' resolves via `color` */
  color: string;
}

/* ------------------------------------------------------ responsive helper */

/**
 * Ukur lebar container (clientWidth) dan pantau perubahan ukurannya.
 * Fallback ke 0 sampai pengukuran pertama selesai.
 */
function useMeasuredWidth(): [React.RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(0);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const update = () => setW(el.clientWidth);
    update();
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(() => update());
      ro.observe(el);
      return () => ro.disconnect();
    }
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);
  return [ref, w];
}

/* J03 (v1.7.2 rev): format angka tooltip — ribuan lokal, 2 desimal aman. */
const fmtChartVal = (v: number) => {
  const n = Number.isFinite(v) ? v : 0;
  const rounded = Math.round(n * 100) / 100;
  return rounded.toLocaleString();
};

/* ---------------------------------------------------------- ProgressRing */

interface ProgressRingProps {
  size?: number;
  strokeWidth?: number;
  /** 0..1 */
  progress: number;
  color?: string;
  trackColor?: string;
  children?: React.ReactNode;
  className?: string;
}

/**
 * Circular progress indicator (parity with PyQt `ProgressRing`).
 * `progress` is clamped to [0,1]. Children render in the center.
 */
export function ProgressRing({
  size = 96,
  strokeWidth = 10,
  progress,
  color = '#34d399',
  trackColor = 'rgba(148,163,184,0.18)',
  children,
  className,
}: ProgressRingProps) {
  const gid = useId();
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const p = Math.max(0, Math.min(1, progress));
  const offset = c * (1 - p);
  const center = size / 2;
  return (
    <div className={className} style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} role="img" aria-hidden="true">
        <defs>
          <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} />
            <stop offset="100%" stopColor={color} stopOpacity="0.7" />
          </linearGradient>
        </defs>
        <circle cx={center} cy={center} r={r} fill="none" stroke={trackColor} strokeWidth={strokeWidth} />
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={`url(#${gid})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${center} ${center})`}
          style={{ transition: 'stroke-dashoffset 0.4s ease' }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {children}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ Sparkline */

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  className?: string;
}

/** Tiny trend line for compact cards (income/expense/XP etc.). */
export function Sparkline({ data, width = 120, height = 36, color = '#34d399', className }: SparklineProps) {
  const [ref, measured] = useMeasuredWidth();
  const resolved = measured > 0 ? measured : width;
  const min = data && data.length ? Math.min(...data) : 0;
  const max = data && data.length ? Math.max(...data) : 1;
  const range = max - min || 1;
  const stepX = data && data.length > 1 ? resolved / (data.length - 1) : resolved;
  const pts = (data || []).map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  });
  const area = `0,${height} ${pts.join(' ')} ${resolved},${height}`;
  return (
    <div ref={ref} className={`w-full ${className ?? ''}`}>
      <svg width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}>
        {data && data.length > 0 && (
          <>
            <polygon points={area} fill={color} opacity="0.12" />
            <polyline points={pts.join(' ')} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </>
        )}
      </svg>
    </div>
  );
}

/* ------------------------------------------------------------- LineChart */

interface LineChartProps {
  data: ChartPoint[];
  width?: number;
  height?: number;
  color?: string;
  showGrid?: boolean;
  labels?: boolean;
  className?: string;
  /** J03: formatter nilai tooltip (default: angka lokal). */
  formatValue?: (v: number) => string;
}

/** Simple multi-purpose line/area chart. Data should be ordered by x (index). */
export function LineChart({ data, width = 320, height = 160, color = '#34d399', showGrid = true, labels = true, className, formatValue }: LineChartProps) {
  const [ref, measured] = useMeasuredWidth();
  // J03 (v1.7.2 rev): titik terdekat dari kursor → guide line + tooltip.
  const [hov, setHov] = useState<number | null>(null);
  const resolved = measured > 0 ? measured : width;
  const pad = 8;
  const innerW = Math.max(1, resolved - pad * 2);
  const innerH = height - (labels ? 24 : pad);
  const values = (data || []).map((d) => d.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  // P52: seri konstan (range 0) digambar di TENGAH chart — dulu menempel dasar.
  const flat = values.length > 0 && max === min;
  const range = max - min || 1;
  const stepX = data && data.length > 1 ? innerW / (data.length - 1) : innerW;
  const pts = (data || []).map((d, i) => {
    const x = pad + i * stepX;
    const y = flat ? pad + innerH / 2 : pad + (1 - (d.value - min) / range) * innerH;
    return { x, y, point: d };
  });
  const line = pts.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const area = `${pad},${pad + innerH} ${line} ${pad + innerW},${pad + innerH}`;
  const gridLines = showGrid ? [0.25, 0.5, 0.75].map((t) => pad + t * innerH) : [];
  const fv = formatValue || fmtChartVal;
  const hp = hov !== null ? pts[hov] : null;
  return (
    <div ref={ref} className={`relative w-full ${className ?? ''}`}>
      <svg
        width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}
        onPointerMove={(e) => {
          if (!pts.length) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const idx = Math.max(0, Math.min(pts.length - 1, Math.round((x - pad) / Math.max(1, stepX))));
          setHov(idx);
        }}
        onPointerLeave={() => setHov(null)}
      >
        {data && data.length > 0 && (
          <>
            {gridLines.map((y, i) => (
              <line key={`gl-${i}`} x1={pad} y1={y} x2={resolved - pad} y2={y} stroke="rgba(148,163,184,0.12)" strokeWidth="1" />
            ))}
            <polygon points={area} fill={color} opacity="0.1" />
            <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            {/* J03: guide line vertikal + titik fokus saat hover */}
            {hp && (
              <>
                <line x1={hp.x} y1={pad} x2={hp.x} y2={pad + innerH} stroke={color} strokeWidth="1" strokeDasharray="3 3" opacity="0.4" />
                <circle cx={hp.x} cy={hp.y} r="8" fill={color} opacity="0.18" />
                <circle cx={hp.x} cy={hp.y} r="4.5" fill={color} stroke="rgba(0,0,0,0.35)" strokeWidth="1" />
              </>
            )}
            {pts.map((p, i) => (
              <circle key={`pt-${i}`} cx={p.x} cy={p.y} r={hov === i ? 0 : 2.5} fill={color} />
            ))}
            {labels &&
              pts.map((p, i) => (
                <text key={`tx-${i}`} x={p.x} y={height - 6} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.85)">
                  {p.point.label}
                </text>
              ))}
          </>
        )}
      </svg>
      {hp && (
        /* L01: tooltip clamp horizontal + flip ke bawah bila titik dekat tepi
           atas (bug lama: nilai maksimum tertutup layout chart). */
        <div className={`ct-chart-tip${hp.y < 46 ? ' ct-chart-tip--below' : ''}`}
             style={{ left: Math.max(36, Math.min(resolved - 36, hp.x)), top: hp.y }}>
          <span className="ct-chart-tip-label">{hp.point.label}</span>
          {fv(hp.point.value)}
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------- DualLineChart */

interface DualSeries {
  label: string;
  value: number;
}

interface DualLineChartProps {
  /** x-axis labels; must align index-wise with both series (or be shorter). */
  labels: string[];
  /** Primary series (e.g. income). */
  a: DualSeries[];
  /** Secondary series (e.g. expense). */
  b: DualSeries[];
  width?: number;
  height?: number;
  colorA?: string;
  colorB?: string;
  className?: string;
}

/**
 * Two-series line/area chart (parity with PyQt `EconomyTrendWidget`:
 * income vs expense over a period). Data must be ordered by x (index).
 */
export function DualLineChart({
  labels,
  a,
  b,
  width = 420,
  height = 190,
  colorA = '#34d399',
  colorB = '#f43f5e',
  className,
}: DualLineChartProps) {
  const [ref, measured] = useMeasuredWidth();
  const resolved = measured > 0 ? measured : width;
  const pad = 8;
  const innerW = Math.max(1, resolved - pad * 2);
  const innerH = height - 28;
  const n = Math.max(a.length, b.length);
  const values = [...a.map((d) => d.value), ...b.map((d) => d.value)];
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  const range = max - min || 1;
  const stepX = n > 1 ? innerW / (n - 1) : innerW;
  const toXY = (series: DualSeries[]) =>
    series.map((d, i) => {
      const x = pad + (i * innerW) / Math.max(1, n - 1);
      const y = pad + (1 - (d.value - min) / range) * innerH;
      return { x, y, point: d };
    });
  const ptsA = toXY(a);
  const ptsB = toXY(b);
  const lineA = ptsA.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const lineB = ptsB.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const areaA = `${pad},${pad + innerH} ${lineA} ${pad + innerW},${pad + innerH}`;
  const areaB = `${pad},${pad + innerH} ${lineB} ${pad + innerW},${pad + innerH}`;
  const gridLines = [0.25, 0.5, 0.75].map((t) => pad + t * innerH);
  const lbl = (i: number) => labels[i] ?? '';
  const labelCount = Math.max(a.length, b.length, labels.length);
  // J03: hover indeks terdekat → guide line + tooltip dua seri.
  const [hov, setHov] = useState<number | null>(null);
  const hA = hov !== null ? ptsA[hov] : undefined;
  const hB = hov !== null ? ptsB[hov] : undefined;
  return (
    <div ref={ref} className={`relative w-full ${className ?? ''}`}>
      <svg
        width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}
        onPointerMove={(e) => {
          if (n === 0) return;
          const rect = e.currentTarget.getBoundingClientRect();
          const x = e.clientX - rect.left;
          const idx = Math.max(0, Math.min(n - 1, Math.round((x - pad) / Math.max(1, innerW / Math.max(1, n - 1)))));
          setHov(idx);
        }}
        onPointerLeave={() => setHov(null)}
      >
        {n > 0 && (
          <>
            {gridLines.map((y, i) => (
              <line key={`gl-${i}`} x1={pad} y1={y} x2={resolved - pad} y2={y} stroke="rgba(148,163,184,0.12)" strokeWidth="1" />
            ))}
            {areaA !== `${pad},${pad + innerH} ${pad + innerW},${pad + innerH}` && (
              <polygon points={areaA} fill={colorA} opacity="0.08" />
            )}
            {areaB !== `${pad},${pad + innerH} ${pad + innerW},${pad + innerH}` && (
              <polygon points={areaB} fill={colorB} opacity="0.08" />
            )}
            {lineA && <polyline points={lineA} fill="none" stroke={colorA} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />}
            {lineB && <polyline points={lineB} fill="none" stroke={colorB} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />}
            {/* J03: guide line + titik fokus hover */}
            {hov !== null && (hA || hB) && (
              <line x1={pad + (hov * innerW) / Math.max(1, n - 1)} y1={pad} x2={pad + (hov * innerW) / Math.max(1, n - 1)} y2={pad + innerH} stroke="rgba(148,163,184,0.45)" strokeWidth="1" strokeDasharray="3 3" />
            )}
            {ptsA.map((p, i) => (
              <circle key={`pa-${i}`} cx={p.x} cy={p.y} r={hov === i ? 4.5 : 2.5} fill={colorA} opacity={hov === null || hov === i ? 1 : 0.45} />
            ))}
            {ptsB.map((p, i) => (
              <circle key={`pb-${i}`} cx={p.x} cy={p.y} r={hov === i ? 4.5 : 2.5} fill={colorB} opacity={hov === null || hov === i ? 1 : 0.45} />
            ))}
            {Array.from({ length: labelCount }).map((_, i) => (
              <text key={`lb-${i}`} x={pad + (i * innerW) / Math.max(1, n - 1)} y={height - 6} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.85)">
                {lbl(i)}
              </text>
            ))}
          </>
        )}
      </svg>
      {hov !== null && (hA || hB) && (
        /* L01: clamp + flip tooltip dua seri. */
        <div className={`ct-chart-tip${Math.min(hA?.y ?? 999, hB?.y ?? 999) < 52 ? ' ct-chart-tip--below' : ''}`}
             style={{ left: Math.max(44, Math.min(resolved - 44, pad + (hov * innerW) / Math.max(1, n - 1))), top: Math.min(hA?.y ?? 999, hB?.y ?? 999) }}>
          <span className="ct-chart-tip-label">{lbl(hov)}</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: 99, background: colorA, display: 'inline-block' }} />
            {hA ? fmtChartVal(hA.point.value) : '—'}
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 7, height: 7, borderRadius: 99, background: colorB, display: 'inline-block' }} />
            {hB ? fmtChartVal(hB.point.value) : '—'}
          </span>
        </div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------- BarChart */

interface BarChartProps {
  data: ChartPoint[];
  width?: number;
  height?: number;
  color?: string;
  labels?: boolean;
  className?: string;
}

/** Vertical bar chart for categories (e.g. calories per day, spending split). */
export function BarChart({ data, width = 320, height = 160, color = '#34d399', labels = true, className }: BarChartProps) {
  const [ref, measured] = useMeasuredWidth();
  // J03: batang yang disorot → terang + tooltip di puncaknya.
  const [hov, setHov] = useState<number | null>(null);
  const resolved = measured > 0 ? measured : width;
  const pad = 8;
  const innerH = height - (labels ? 24 : pad * 2);
  const values = (data || []).map((d) => d.value);
  const max = Math.max(...values, 1);
  const barGap = 6;
  const barW = data && data.length ? Math.max(2, (resolved - pad * 2 - barGap * (data.length - 1)) / data.length) : 0;
  const hoverFor = (x: number) => {
    const idx = Math.floor((x - pad) / Math.max(1, barW + barGap));
    return idx >= 0 && idx < (data?.length || 0) ? idx : null;
  };
  const hd = hov !== null && data ? data[hov] : null;
  const hY = hd ? height - (labels ? 24 : pad) - (hd.value / max) * (innerH - pad) : 0;
  return (
    <div ref={ref} className={`relative w-full ${className ?? ''}`}>
      <svg
        width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}
        onPointerMove={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          setHov(hoverFor(e.clientX - rect.left));
        }}
        onPointerLeave={() => setHov(null)}
      >
        {(data || []).map((d, i) => {
          const h = (d.value / max) * (innerH - pad);
          const x = pad + i * (barW + barGap);
          const y = height - (labels ? 24 : pad) - h;
          return (
            <g key={`bar-${i}`}>
              <rect x={x} y={y} width={barW} height={h} rx="3" fill={color}
                opacity={hov === null ? 0.85 : hov === i ? 1 : 0.38}
                style={{ transition: 'opacity 0.15s ease' }} />
              {hov === i && <rect x={x} y={y - 2} width={barW} height={2} rx="1" fill={color} />}
              {labels && (
                <text x={x + barW / 2} y={height - 6} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.85)">
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      {hd && hov !== null && (
        /* L01: clamp + flip tooltip batang. */
        <div className={`ct-chart-tip${hY < 46 ? ' ct-chart-tip--below' : ''}`}
             style={{ left: Math.max(36, Math.min(resolved - 36, pad + hov * (barW + barGap) + barW / 2)), top: hY }}>
          <span className="ct-chart-tip-label">{hd.label}</span>
          {fmtChartVal(hd.value)}
        </div>
      )}
    </div>
  );
}

/* ----------------------------------------------------------- DonutChart */

interface DonutSeg {
  label: string;
  value: number;
  color: string;
}

interface DonutChartProps {
  data: DonutSeg[];
  size?: number;
  strokeWidth?: number;
  centerLabel?: string;
  centerSub?: string;
  className?: string;
}

/** Segmented donut (macros split, spending categories, goal completion). */
export function DonutChart({ data, size = 140, strokeWidth = 18, centerLabel, centerSub, className }: DonutChartProps) {
  const gid = useId();
  // J03: hover segmen → segmen menebal, pusat menampilkan label+nilai+persen.
  const [hov, setHov] = useState<number | null>(null);
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const center = size / 2;
  let acc = 0;
  const hs = hov !== null ? data[hov] : null;
  return (
    <div className={className} style={{ position: 'relative', width: size, height: size }}>
      <svg width={size} height={size} aria-hidden="true">
        <defs>
          {data.map((d, i) => (
            <linearGradient id={`${gid}-g${i}`} key={`lg-${i}`} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={d.color} />
              <stop offset="100%" stopColor={d.color} stopOpacity="0.75" />
            </linearGradient>
          ))}
        </defs>
        {data.map((d, i) => {
          const frac = d.value / total;
          const dash = frac * c;
          const el = (
            <circle
              key={`seg-${i}`}
              cx={center}
              cy={center}
              r={r}
              fill="none"
              stroke={`url(#${gid}-g${i})`}
              strokeWidth={hov === i ? strokeWidth + 5 : strokeWidth}
              strokeDasharray={`${dash} ${c - dash}`}
              strokeDashoffset={-acc * c}
              strokeLinecap="butt"
              transform={`rotate(-90 ${center} ${center})`}
              opacity={hov === null || hov === i ? 1 : 0.4}
              style={{ transition: 'stroke-width 0.15s ease, opacity 0.15s ease', cursor: 'pointer' }}
              onPointerEnter={() => setHov(i)}
              onPointerLeave={() => setHov(null)}
            />
          );
          acc += frac;
          return el;
        })}
      </svg>
      {/* J03: saat hover, pusat menampilkan segmen aktif; selain itu label bawaan. */}
      {(hs || centerLabel || centerSub) && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', pointerEvents: 'none' }}>
          {hs ? (
            <>
              <div className="font-bold text-slate-100 text-sm leading-tight" style={{ color: hs.color }}>{fmtChartVal(hs.value)}</div>
              <div className="text-slate-400 text-[10px] px-3 truncate w-full">{hs.label}</div>
              <div className="text-slate-500 text-[9px]">{Math.round((hs.value / total) * 100)}%</div>
            </>
          ) : (
            <>
              {centerLabel && <div className="font-bold text-slate-100 text-sm leading-tight">{centerLabel}</div>}
              {centerSub && <div className="text-slate-400 text-[10px]">{centerSub}</div>}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------- Heatmap */

interface HeatmapProps {
  /** Row-major values; intensity is normalised per cell against `max`. */
  values: number[];
  columns?: number;
  max?: number;
  colors?: [string, string];
  cell?: number;
  gap?: number;
  className?: string;
}

/** GitHub-style activity heatmap (parity with PyQt `HeatmapWidget`). */
export function Heatmap({ values, columns = 7, max, colors = ['#0f172a', '#34d399'], cell = 18, gap = 4, className }: HeatmapProps) {
  const peak = max ?? Math.max(...values, 1);
  const rows = Math.ceil(values.length / columns);
  const w = columns * (cell + gap);
  const h = rows * (cell + gap);
  return (
    <svg width={w} height={h} className={className} aria-hidden="true" viewBox={`0 0 ${w} ${h}`}>
      {values.map((v, i) => {
        const col = i % columns;
        const row = Math.floor(i / columns);
        const x = col * (cell + gap);
        const y = row * (cell + gap);
        const t = Math.min(1, v / peak);
        const color = t > 0 ? colors[1] : colors[0];
        return (
          <rect key={`hc-${i}`} x={x} y={y} width={cell} height={cell} rx="3" fill={color} opacity={t > 0 ? Math.max(0.25, t) : 0.2}
            style={{ transition: 'opacity 0.15s ease' }} className="hover:stroke-slate-300" stroke="transparent" strokeWidth="1">
            {/* J03: keterangan bawaan per sel (native tooltip aksesibel). */}
            <title>{`${v}`}</title>
          </rect>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------- GroupBar */

interface GroupBarProps {
  /** Absolute values — rendered proportional to the sum. J03: `label`
   *  opsional dipakai tooltip hover. */
  data: (BaseSeries & { value: number; label?: string })[];
  height?: number;
  className?: string;
}

/** Horizontal stacked bar (macros, budget split). Values proportional to sum.
 *  J03: hover segmen → tooltip label+nilai di atas segmen. */
export function GroupBar({ data, height = 14, className }: GroupBarProps) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const [hov, setHov] = useState<number | null>(null);
  // Posisi kiri (persen kumulatif) pusat tiap segmen utk tooltip.
  let accPct = 0;
  const centers = data.map((d) => {
    const w = (d.value / total) * 100;
    const ctr = accPct + w / 2;
    accPct += w;
    return ctr;
  });
  return (
    <div className={`relative w-full ${className ?? ''}`}>
      <div className="flex w-full overflow-hidden rounded-full" style={{ height }}>
        {data.map((d, i) => (
          <div key={`gb-${i}`}
            onPointerEnter={() => setHov(i)} onPointerLeave={() => setHov(null)}
            style={{ width: `${(d.value / total) * 100}%`, background: d.color, transition: 'width 0.4s ease, filter 0.15s ease', filter: hov === i ? 'brightness(1.25)' : hov === null ? 'none' : 'brightness(0.7)', cursor: 'pointer' }} />
        ))}
      </div>
      {hov !== null && data[hov] && (
        <div className="ct-chart-tip" style={{ left: `${centers[hov]}%`, top: 0 }}>
          <span className="ct-chart-tip-label">{data[hov].label ?? ''}</span>
          {fmtChartVal(data[hov].value)}
        </div>
      )}
    </div>
  );
}
