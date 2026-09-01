import type { ThemePalette } from '../types';

/**
 * Sistem tema Web (parity db.THEMES / SettingsPage theme radios).
 * Karena UI dibangun dgn Tailwind (kelas hardcoded `bg-slate-950`), kita
 * menerapkan palet tema sbg CSS *custom properties* di :root agar seluruh
 * permukaan inti (shell, sidebar, navbar, panel, card) bisa memakai warna
 * tema — bukan theme dummy. Aturan: PyQt = source of truth; tema boleh
 * implementasi React-native, tapi palet & perilaku harus equivalent.
 */

const VAR_MAP: Array<[keyof ThemePalette, string]> = [
  ['primary', '--ct-primary'],
  ['light', '--ct-light'],
  ['bg', '--ct-bg'],
  ['bg2', '--ct-bg2'],
  ['bg3', '--ct-bg3'],
  ['panel', '--ct-panel'],
  ['border', '--ct-border'],
  ['accent', '--ct-accent'],
  ['accent2', '--ct-accent2'],
  ['accent3', '--ct-accent3'],
  ['glow', '--ct-glow'],
  ['text', '--ct-text'],
  ['muted', '--ct-muted'],
];

export function applyTheme(palette: ThemePalette | null | undefined): void {
  if (typeof document === 'undefined') return;
  if (!palette) return;
  const root = document.documentElement;
  for (const [key, cssVar] of VAR_MAP) {
    const val = palette[key];
    if (val) root.style.setProperty(cssVar, val);
  }
  root.style.setProperty('--ct-theme', palette.key);
  root.setAttribute('data-theme', palette.key);
}

/** Heksadesimal (#rrggbb) → butuh alpha (rgba) utk overlay dynamic. */
export function hexToRgba(hex: string, alpha: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex || '');
  if (!m) return hex;
  const [, r, g, b] = m;
  const n = (h: string) => parseInt(h, 16);
  return `rgba(${n(r)},${n(g)},${n(b)},${alpha})`;
}
