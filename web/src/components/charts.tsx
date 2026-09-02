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
}

/** Simple multi-purpose line/area chart. Data should be ordered by x (index). */
export function LineChart({ data, width = 320, height = 160, color = '#34d399', showGrid = true, labels = true, className }: LineChartProps) {
  const [ref, measured] = useMeasuredWidth();
  const resolved = measured > 0 ? measured : width;
  const pad = 8;
  const innerW = Math.max(1, resolved - pad * 2);
  const innerH = height - (labels ? 24 : pad);
  const values = (data || []).map((d) => d.value);
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 0;
  const range = max - min || 1;
  const stepX = data && data.length > 1 ? innerW / (data.length - 1) : innerW;
  const pts = (data || []).map((d, i) => {
    const x = pad + i * stepX;
    const y = pad + (1 - (d.value - min) / range) * innerH;
    return { x, y, point: d };
  });
  const line = pts.map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ');
  const area = `${pad},${pad + innerH} ${line} ${pad + innerW},${pad + innerH}`;
  const gridLines = showGrid ? [0.25, 0.5, 0.75].map((t) => pad + t * innerH) : [];
  return (
    <div ref={ref} className={`w-full ${className ?? ''}`}>
      <svg width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}>
        {data && data.length > 0 && (
          <>
            {gridLines.map((y, i) => (
              <line key={`gl-${i}`} x1={pad} y1={y} x2={resolved - pad} y2={y} stroke="rgba(148,163,184,0.12)" strokeWidth="1" />
            ))}
            <polygon points={area} fill={color} opacity="0.1" />
            <polyline points={line} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
            {pts.map((p, i) => (
              <circle key={`pt-${i}`} cx={p.x} cy={p.y} r="2.5" fill={color} />
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
  return (
    <div ref={ref} className={`w-full ${className ?? ''}`}>
      <svg width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}>
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
            {ptsA.map((p, i) => (
              <circle key={`pa-${i}`} cx={p.x} cy={p.y} r="2.5" fill={colorA} />
            ))}
            {ptsB.map((p, i) => (
              <circle key={`pb-${i}`} cx={p.x} cy={p.y} r="2.5" fill={colorB} />
            ))}
            {Array.from({ length: labelCount }).map((_, i) => (
              <text key={`lb-${i}`} x={pad + (i * innerW) / Math.max(1, n - 1)} y={height - 6} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.85)">
                {lbl(i)}
              </text>
            ))}
          </>
        )}
      </svg>
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
  const resolved = measured > 0 ? measured : width;
  const pad = 8;
  const innerH = height - (labels ? 24 : pad * 2);
  const values = (data || []).map((d) => d.value);
  const max = Math.max(...values, 1);
  const barGap = 6;
  const barW = data && data.length ? Math.max(2, (resolved - pad * 2 - barGap * (data.length - 1)) / data.length) : 0;
  return (
    <div ref={ref} className={`w-full ${className ?? ''}`}>
      <svg width={resolved} height={height} aria-hidden="true" viewBox={`0 0 ${resolved} ${height}`}>
        {(data || []).map((d, i) => {
          const h = (d.value / max) * (innerH - pad);
          const x = pad + i * (barW + barGap);
          const y = height - (labels ? 24 : pad) - h;
          return (
            <g key={`bar-${i}`}>
              <rect x={x} y={y} width={barW} height={h} rx="3" fill={color} opacity="0.85" />
              {labels && (
                <text x={x + barW / 2} y={height - 6} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.85)">
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>
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
  const r = (size - strokeWidth) / 2;
  const c = 2 * Math.PI * r;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  const center = size / 2;
  let acc = 0;
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
              strokeWidth={strokeWidth}
              strokeDasharray={`${dash} ${c - dash}`}
              strokeDashoffset={-acc * c}
              strokeLinecap="butt"
              transform={`rotate(-90 ${center} ${center})`}
            />
          );
          acc += frac;
          return el;
        })}
      </svg>
      {(centerLabel || centerSub) && (
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
          {centerLabel && <div className="font-bold text-slate-100 text-sm leading-tight">{centerLabel}</div>}
          {centerSub && <div className="text-slate-400 text-[10px]">{centerSub}</div>}
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
        return <rect key={`hc-${i}`} x={x} y={y} width={cell} height={cell} rx="3" fill={color} opacity={t > 0 ? Math.max(0.25, t) : 0.2} />;
      })}
    </svg>
  );
}

/* ------------------------------------------------------------- GroupBar */

interface GroupBarProps {
  /** Absolute values — rendered proportional to the sum. */
  data: (BaseSeries & { value: number })[];
  height?: number;
  className?: string;
}

/** Horizontal stacked bar (macros, budget split). Values proportional to sum. */
export function GroupBar({ data, height = 14, className }: GroupBarProps) {
  const total = data.reduce((s, d) => s + d.value, 0) || 1;
  return (
    <div className={`flex w-full overflow-hidden rounded-full ${className ?? ''}`} style={{ height }}>
      {data.map((d, i) => (
        <div key={`gb-${i}`} style={{ width: `${(d.value / total) * 100}%`, background: d.color, transition: 'width 0.4s ease' }} />
      ))}
    </div>
  );
}
