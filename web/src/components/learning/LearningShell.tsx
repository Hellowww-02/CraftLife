/**
 * LearningShell.tsx — kerangka tata letak Learning Page ala NotebookLM (A07).
 *
 * Struktur (>= 1024px):
 *   [ rail notebook ] [ topbar + kolom tengah (Sumber ⇄ Chat) ] [ kolom Studio ]
 * Di bawah 1024px: rail menjadi bottom-bar dan tiap kolom menjadi TAB penuh
 * (Sumber / Chat / Studio) — sekali lagi tanpa scroll ganda.
 *
 * Resize manual (drag pembatas) digantikan **preset lebar + collapse** karena drag di
 * WebEngine rawan: pengguna memilih Sempit / Sedang / Lebar, atau menyembunyikan panel.
 * Preferensi disimpan di `localStorage` key `cl_learning_layout`, dan **migrasi otomatis**
 * dari key lama `cl_learning_panel_widths` (lebar piksel → preset terdekat).
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PanelRightClose, PanelRightOpen, Columns3 } from 'lucide-react';
import { LearningViewKey } from './NotebookRail';

export type StudioWidth = 'narrow' | 'medium' | 'wide';

const WIDTHS: Record<StudioWidth, number> = { narrow: 320, medium: 420, wide: 560 };
const PRESET_ORDER: StudioWidth[] = ['narrow', 'medium', 'wide'];
const LS_KEY = 'cl_learning_layout';
const LS_LEGACY_KEY = 'cl_learning_panel_widths';
/** Lebar rail kiri: sempit 72px (ikon saja) / melebar 220px (ikon + judul). */
const RAIL_COLLAPSED = 72;
const RAIL_EXPANDED = 220;

export interface LearningShellState {
  studioWidth: StudioWidth;
  studioOpen: boolean;
  railExpanded: boolean;
}

/** Baca preferensi tata letak (+ migrasi dari format lama berbasis piksel). */
export function loadShellState(): LearningShellState {
  const fallback: LearningShellState = { studioWidth: 'medium', studioOpen: true, railExpanded: false };
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const v = JSON.parse(raw) as Partial<LearningShellState>;
      return {
        studioWidth: (PRESET_ORDER as string[]).includes(String(v.studioWidth)) ? (v.studioWidth as StudioWidth) : fallback.studioWidth,
        studioOpen: v.studioOpen !== false,
        railExpanded: v.railExpanded === true,
      };
    }
    // Migrasi key lama: `{src, stu}` dalam piksel → preset terdekat.
    const legacy = localStorage.getItem(LS_LEGACY_KEY);
    if (legacy) {
      const v = JSON.parse(legacy) as { stu?: unknown };
      const px = Number(v.stu);
      if (Number.isFinite(px)) {
        let best: StudioWidth = 'medium';
        let dist = Infinity;
        for (const k of PRESET_ORDER) {
          const d = Math.abs(WIDTHS[k] - px);
          if (d < dist) { dist = d; best = k; }
        }
        return { ...fallback, studioWidth: best };
      }
    }
  } catch { /* abaikan — pakai default */ }
  return fallback;
}

export function saveShellState(state: LearningShellState): void {
  try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch { /* abaikan */ }
}

export interface LearningShellProps {
  rail: React.ReactNode;
  topbar: React.ReactNode;
  sources: React.ReactNode;
  chat: React.ReactNode;
  studio: React.ReactNode;
  /** View aktif (dipakai rail + tab mobile; di desktop 'studio' tetap menampilkan studio). */
  view: LearningViewKey;
  onView: (v: LearningViewKey) => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
  /** Dipanggil saat preferensi tata letak berubah (agar induk bisa menyimpan state lain bila perlu). */
  onStateChange?: (state: LearningShellState) => void;
}

const LearningShell: React.FC<LearningShellProps> = ({
  rail, topbar, sources, chat, studio, view, onView, tr, onStateChange,
}) => {
  const initial = useMemo(loadShellState, []);
  const [studioWidth, setStudioWidth] = useState<StudioWidth>(initial.studioWidth);
  const [studioOpen, setStudioOpen] = useState(initial.studioOpen);
  const [railExpanded, setRailExpanded] = useState(initial.railExpanded);
  const shellRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const state = { studioWidth, studioOpen, railExpanded };
    saveShellState(state);
    onStateChange?.(state);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studioWidth, studioOpen, railExpanded]);

  // Kolom tengah: desktop menampilkan Sumber atau Chat (toggle), mobile memakai `view`.
  const centerIsChat = view === 'chat';

  // Lebar efektif kolom studio: dijaga agar kolom tengah tetap ≥ 360px (desktop).
  const [studioPx, setStudioPx] = useState(WIDTHS[studioWidth]);
  useEffect(() => {
    const fit = () => {
      const total = shellRef.current?.getBoundingClientRect().width ?? 0;
      if (!total || window.innerWidth < 1024) { setStudioPx(WIDTHS[studioWidth]); return; }
      const rail = railExpanded ? RAIL_EXPANDED : RAIL_COLLAPSED;
      const maxAllowed = Math.max(WIDTHS.narrow, total - rail - 360 - 24);
      setStudioPx(Math.min(WIDTHS[studioWidth], maxAllowed));
    };
    fit();
    window.addEventListener('resize', fit);
    return () => window.removeEventListener('resize', fit);
  }, [studioWidth, railExpanded, studioOpen]);

  const cycleWidth = () => {
    const i = PRESET_ORDER.indexOf(studioWidth);
    setStudioWidth(PRESET_ORDER[(i + 1) % PRESET_ORDER.length]);
  };

  return (
    <div
      ref={shellRef}
      className="ct-nlm flex flex-col lg:flex-row gap-3 lg:gap-4 lg:h-[calc(100vh-190px)] lg:min-h-[560px]"
      style={{ '--rail-w': `${railExpanded ? RAIL_EXPANDED : RAIL_COLLAPSED}px` } as React.CSSProperties}
    >
      {/* Rail kiri (desktop) / bottom-bar (mobile) */}
      <div className="order-2 lg:order-1 lg:h-full">
        {React.isValidElement(rail)
          ? React.cloneElement(rail as React.ReactElement<any>, { expanded: railExpanded, onToggleExpanded: () => setRailExpanded((v) => !v) })
          : rail}
      </div>

      {/* Kolom tengah */}
      <div className={`order-1 lg:order-2 flex-1 min-w-0 flex-col gap-3 ${view === 'studio' ? 'hidden lg:flex' : 'flex'}`}>
        {topbar}

        {/* Tab Sumber ⇄ Chat (desktop) */}
        <div className="hidden lg:flex items-center gap-1.5">
          <button
            onClick={() => onView('sources')}
            className={`ct-nlm-tab ${!centerIsChat ? 'is-active' : ''}`}
          >
            {tr('learning_view_sources', {}, 'Sumber')}
          </button>
          <button
            onClick={() => onView('chat')}
            className={`ct-nlm-tab ${centerIsChat ? 'is-active' : ''}`}
          >
            {tr('learning_view_chat', {}, 'Chat')}
          </button>
          <div className="ml-auto flex items-center gap-1.5">
            <button
              onClick={cycleWidth}
              className="ct-nlm-tab"
              title={tr('learning_panel_width_hint', {}, 'Lebar panel Studio')}
            >
              <Columns3 className="w-3.5 h-3.5" />
              {studioWidth === 'narrow' ? tr('learning_panel_narrow', {}, 'Sempit')
                : studioWidth === 'wide' ? tr('learning_panel_wide', {}, 'Lebar')
                  : tr('learning_panel_medium', {}, 'Sedang')}
            </button>
            <button
              onClick={() => { setStudioOpen((v) => !v); onView(studioOpen ? (centerIsChat ? 'chat' : 'sources') : 'studio'); }}
              className={`ct-nlm-tab ${studioOpen ? 'is-active' : ''}`}
              title={studioOpen ? tr('learning_panel_collapse', {}, 'Sembunyikan panel') : tr('learning_view_studio', {}, 'Studio')}
            >
              {studioOpen ? <PanelRightClose className="w-3.5 h-3.5" /> : <PanelRightOpen className="w-3.5 h-3.5" />}
              {tr('learning_view_studio', {}, 'Studio')}
            </button>
          </div>
        </div>

        {/* Isi kolom tengah */}
        <div className="flex-1 min-h-0">
          {centerIsChat ? chat : sources}
        </div>
      </div>

      {/* Kolom Studio */}
      <div
        className={`order-3 flex-col min-w-0 lg:h-full ${view === 'studio' ? 'flex' : 'hidden lg:flex'} ${studioOpen ? '' : 'lg:hidden'}`}
        style={{ width: `${studioPx}px`, maxWidth: '100%' }}
      >
        <div className="ct-nlm-scroll flex-1 min-h-0 overflow-y-auto">{studio}</div>
      </div>

      {/* Tab mobile (bottom) — rail sudah menjadi bottom-bar, tab ini mengatur kolom tengah */}
      <div className="order-4 lg:hidden flex gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
        {(['sources', 'chat', 'studio'] as const).map((k) => (
          <button
            key={k}
            onClick={() => onView(k)}
            className={`flex-1 py-2 rounded-lg text-[11px] font-bold transition-colors ${view === k ? 'bg-[var(--ct-primary)] text-white' : 'text-slate-400'}`}
          >
            {k === 'sources' ? tr('learning_view_sources', {}, 'Sumber')
              : k === 'chat' ? tr('learning_view_chat', {}, 'Chat')
                : tr('learning_view_studio', {}, 'Studio')}
          </button>
        ))}
      </div>
    </div>
  );
};

export default LearningShell;
