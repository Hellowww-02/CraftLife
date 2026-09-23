/**
 * shellState.ts — status tata letak Learning Page (C01).
 *
 * Helper murni (tanpa React) agar mudah diuji: migrasi format preferensi lama
 * ke format v2 + clamp lebar panel. LearningShell.tsx hanya memakai modul ini
 * untuk membaca/menyimpan/membatasi ukuran — tidak ada logika duplikat.
 *
 * Format:
 *  - v2 (C01): { v: 2, srcPx, stuPx, srcOpen, stuOpen, railExpanded } (piksel drag).
 *  - v1 (A07/A15): { studioWidth: 'narrow'|'medium'|'wide', studioOpen, railExpanded }.
 *  - legacy: { src?, stu? } piksel di key `cl_learning_panel_widths`.
 */

export type ShellPanel = 'src' | 'stu';

export interface LearningShellState {
  v: 2;
  srcPx: number;
  stuPx: number;
  srcOpen: boolean;
  stuOpen: boolean;
  railExpanded: boolean;
}

export const LS_KEY = 'cl_learning_layout';
export const LS_LEGACY_KEY = 'cl_learning_panel_widths';

/** Batas lebar panel Sumber (px). */
export const SRC_MIN = 220;
export const SRC_MAX = 480;
export const SRC_DEFAULT = 300;
/** Batas lebar panel Studio (px). */
export const STU_MIN = 280;
export const STU_MAX = 640;
export const STU_DEFAULT = 400;
/** Kolom Chat tidak boleh lebih sempit dari ini (px). */
export const CHAT_MIN = 300;
/** Lebar strip ramping saat panel di-collapse (px). */
export const STRIP_W = 36;
/** Lebar rail notebook (px). */
export const RAIL_COLLAPSED = 72;
export const RAIL_EXPANDED = 220;
/** Cadangan untuk gap/padding antar kolom (px). */
const GAPS = 32;

/** Peta preset v1 → piksel (nilai asli A07, tidak diubah). */
const PRESET_PX: Record<string, number> = { narrow: 320, medium: 420, wide: 560 };

export function defaultShellState(): LearningShellState {
  return {
    v: 2,
    srcPx: SRC_DEFAULT,
    stuPx: STU_DEFAULT,
    srcOpen: true,
    stuOpen: true,
    railExpanded: false,
  };
}

function num(v: unknown, fb: number): number {
  const n = Number(v);
  return Number.isFinite(n) ? n : fb;
}

/**
 * Jepit lebar panel ke [min, max]. Bila `total` (lebar shell) diketahui, batas
 * atas ikut dikurangi agar kolom Chat masih ≥ CHAT_MIN; `reserved` = lebar rail
 * + panel seberang (atau strip-nya bila tertutup).
 */
export function clampPanel(px: number, min: number, max: number, total = 0, reserved = 0): number {
  let hi = max;
  if (total > 0) {
    const byChat = total - reserved - CHAT_MIN - GAPS;
    hi = Math.min(max, Math.max(min, byChat));
  }
  return Math.round(Math.min(hi, Math.max(min, px)));
}

export function clampSrcPx(px: number, total = 0, reserved = 0): number {
  return clampPanel(px, SRC_MIN, SRC_MAX, total, reserved);
}

export function clampStuPx(px: number, total = 0, reserved = 0): number {
  return clampPanel(px, STU_MIN, STU_MAX, total, reserved);
}

/**
 * Migrasi nilai mentah localStorage → state v2. Menerima format v2, v1 (preset),
 * dan legacy {src, stu} piksel. Nilai rusak/asing → default yang aman.
 */
export function migrateShellState(raw: string | null, legacyRaw: string | null): LearningShellState {
  const fb = defaultShellState();
  try {
    if (raw) {
      const v = JSON.parse(raw) as Partial<LearningShellState> & {
        studioWidth?: unknown;
        studioOpen?: unknown;
      };
      if ((v as { v?: unknown }).v === 2) {
        return {
          v: 2,
          srcPx: clampSrcPx(num(v.srcPx, SRC_DEFAULT)),
          stuPx: clampStuPx(num(v.stuPx, STU_DEFAULT)),
          srcOpen: v.srcOpen !== false,
          stuOpen: v.stuOpen !== false,
          railExpanded: v.railExpanded === true,
        };
      }
      // v1 (A07/A15): preset → piksel ekuivalen; panel Sumber selalu default (baru di C01).
      if (typeof v.studioWidth === 'string') {
        const mapped = PRESET_PX[v.studioWidth];
        return {
          ...fb,
          stuPx: mapped !== undefined ? mapped : STU_DEFAULT,
          stuOpen: v.studioOpen !== false,
          railExpanded: v.railExpanded === true,
        };
      }
      if ('studioOpen' in v || 'railExpanded' in v) {
        return {
          ...fb,
          stuOpen: v.studioOpen !== false,
          railExpanded: v.railExpanded === true,
        };
      }
    }
    if (legacyRaw) {
      const v = JSON.parse(legacyRaw) as { src?: unknown; stu?: unknown };
      const out = { ...fb };
      if (Number.isFinite(Number(v.src))) out.srcPx = clampSrcPx(Number(v.src));
      if (Number.isFinite(Number(v.stu))) out.stuPx = clampStuPx(Number(v.stu));
      return out;
    }
  } catch {
    /* abaikan — pakai default */
  }
  return fb;
}

/** Baca preferensi dari localStorage (+ semua migrasi di atas). */
export function loadShellState(): LearningShellState {
  try {
    return migrateShellState(localStorage.getItem(LS_KEY), localStorage.getItem(LS_LEGACY_KEY));
  } catch {
    return defaultShellState();
  }
}

/** Simpan preferensi (format v2). */
export function saveShellState(s: LearningShellState): void {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(s));
  } catch {
    /* abaikan */
  }
}
