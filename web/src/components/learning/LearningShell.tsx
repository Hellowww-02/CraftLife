/**
 * LearningShell.tsx — kerangka 3 panel Learning Page ala NotebookLM (C01).
 *
 * Desktop (≥1024px):
 *   [ rail notebook ] [ panel Sumber ] ‖ [ panel Chat ] ‖ [ panel Studio ]
 *   - Divider ‖ bisa **diseret** untuk mengubah lebar (menggantikan tombol preset
 *     Sempit/Sedang/Lebar yang dihapus di C01 atas permintaan user).
 *   - Panel Sumber & Studio bisa **di-collapse** (tombol di divider atau klik-ganda
 *     divider); strip ramping dengan tombol muncul untuk membukanya kembali.
 *   - Preferensi (lebar px + buka/tutup) tersimpan di localStorage `cl_learning_layout`
 *     format v2; format preset v1 dan key legacy dimigrasi otomatis (shellState.ts).
 * Mobile (<1024px): rail menjadi bottom-bar dan tiap kolom menjadi TAB penuh
 * (Sumber / Chat / Studio).
 *
 * Drag aman WebEngine: pointer events + listener window (tanpa HTML5 DnD), tanpa
 * `backdrop-filter`, tanpa animasi selama drag, `user-select: none` hanya saat drag.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { LearningViewKey } from './NotebookRail';
import {
  LearningShellState,
  ShellPanel,
  clampSrcPx,
  clampStuPx,
  loadShellState,
  saveShellState,
  STRIP_W,
  RAIL_COLLAPSED,
  RAIL_EXPANDED,
} from './shellState';

export interface LearningShellProps {
  rail: React.ReactNode;
  topbar: React.ReactNode;
  sources: React.ReactNode;
  chat: React.ReactNode;
  studio: React.ReactNode;
  /** Tab aktif — hanya dipakai di mobile; di desktop ketiga panel tampil sejajar. */
  view: LearningViewKey;
  onView: (v: LearningViewKey) => void;
  tr: (key: string, vars?: Record<string, string | number>, fallback?: string) => string;
  /** Dipanggil saat preferensi tata letak berubah (agar induk bisa menyimpan state lain bila perlu). */
  onStateChange?: (state: LearningShellState) => void;
}

interface SplitterProps {
  which: ShellPanel;
  dragging: boolean;
  dragHint: string;
  toggleLabel: string;
  onDragStart: (which: ShellPanel) => (e: React.PointerEvent) => void;
  onToggle: () => void;
}

/** Divider seret antar panel + tombol collapse di tengahnya. */
const Splitter: React.FC<SplitterProps> = ({
  which, dragging, dragHint, toggleLabel, onDragStart, onToggle,
}) => (
  <div
    role="separator"
    aria-orientation="vertical"
    aria-label={dragHint}
    title={dragHint}
    data-testid={which === 'src' ? 'splitter-sources' : 'splitter-studio'}
    className={`ct-nlm-splitter max-lg:hidden${dragging ? ' is-drag' : ''}`}
    onPointerDown={onDragStart(which)}
    onDoubleClick={onToggle}
  >
    <button
      type="button"
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => { e.stopPropagation(); onToggle(); }}
      title={toggleLabel}
      aria-label={toggleLabel}
      data-testid={which === 'src' ? 'collapse-sources' : 'collapse-studio'}
      className="ct-nlm-splitbtn"
    >
      {which === 'src' ? <PanelLeftClose className="w-3.5 h-3.5" /> : <PanelRightClose className="w-3.5 h-3.5" />}
    </button>
  </div>
);

interface StripProps {
  which: ShellPanel;
  showLabel: string;
  shortLabel: string;
  onShow: () => void;
}

/** Strip ramping pengganti panel yang di-collapse (desktop saja). */
const ClosedStrip: React.FC<StripProps> = ({ which, showLabel, shortLabel, onShow }) => (
  <button
    type="button"
    onClick={onShow}
    title={showLabel}
    aria-label={showLabel}
    data-testid={which === 'src' ? 'strip-sources' : 'strip-studio'}
    className="ct-nlm-strip max-lg:hidden"
    style={{ width: `${STRIP_W}px` }}
  >
    {which === 'src' ? <PanelLeftOpen className="w-4 h-4 shrink-0" /> : <PanelRightOpen className="w-4 h-4 shrink-0" />}
    <span className="ct-nlm-strip-label">{shortLabel}</span>
  </button>
);

const LearningShell: React.FC<LearningShellProps> = ({
  rail, topbar, sources, chat, studio, view, onView, tr, onStateChange,
}) => {
  const initial = useMemo(loadShellState, []);
  const [srcPx, setSrcPx] = useState(initial.srcPx);
  const [stuPx, setStuPx] = useState(initial.stuPx);
  const [srcOpen, setSrcOpen] = useState(initial.srcOpen);
  const [stuOpen, setStuOpen] = useState(initial.stuOpen);
  const [railExpanded, setRailExpanded] = useState(initial.railExpanded);
  const [dragging, setDragging] = useState<ShellPanel | null>(null);
  const shellRef = useRef<HTMLDivElement | null>(null);
  // Cermin ref agar handler drag memakai lebar terbaru tanpa re-subscribe listener.
  const widthsRef = useRef({ srcPx, stuPx, srcOpen, stuOpen });
  widthsRef.current = { srcPx, stuPx, srcOpen, stuOpen };

  useEffect(() => {
    const state: LearningShellState = { v: 2, srcPx, stuPx, srcOpen, stuOpen, railExpanded };
    saveShellState(state);
    onStateChange?.(state);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [srcPx, stuPx, srcOpen, stuOpen, railExpanded]);

  const railW = railExpanded ? RAIL_EXPANDED : RAIL_COLLAPSED;

  const startDrag = (which: ShellPanel) => (e: React.PointerEvent) => {
    // Hanya tombol utama; abaikan klik kanan / tombol tengah.
    if (e.pointerType === 'mouse' && e.button !== 0) return;
    e.preventDefault();
    const startX = e.clientX;
    const start = { ...widthsRef.current };
    const total = shellRef.current?.getBoundingClientRect().width ?? 0;
    setDragging(which);
    const prevSelect = document.body.style.userSelect;
    document.body.style.userSelect = 'none';
    const move = (ev: PointerEvent) => {
      const dx = ev.clientX - startX;
      if (which === 'src') {
        // Panel Sumber tumbuh ke kanan; ruang panel Studio (atau strip-nya) dilindungi.
        const stuW = start.stuOpen ? start.stuPx : STRIP_W;
        setSrcPx(clampSrcPx(start.srcPx + dx, total, railW + stuW));
      } else {
        const srcW = start.srcOpen ? start.srcPx : STRIP_W;
        setStuPx(clampStuPx(start.stuPx - dx, total, railW + srcW));
      }
    };
    const up = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', up);
      window.removeEventListener('pointercancel', up);
      document.body.style.userSelect = prevSelect;
      setDragging(null);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', up);
    window.addEventListener('pointercancel', up);
  };

  const centerIsChat = view === 'chat';
  const dragHint = tr('learning_drag_hint', {}, 'Drag to resize panels');

  return (
    <div
      ref={shellRef}
      className="ct-nlm flex flex-col lg:flex-row gap-3 lg:gap-4 lg:h-[calc(100vh-190px)] lg:min-h-[560px]"
      style={{ '--rail-w': `${railW}px` } as React.CSSProperties}
    >
      {/* Rail kiri (desktop) / bottom-bar (mobile) */}
      <div className="order-2 lg:order-1 lg:h-full">
        {React.isValidElement(rail)
          ? React.cloneElement(rail as React.ReactElement<any>, { expanded: railExpanded, onToggleExpanded: () => setRailExpanded((v) => !v) })
          : rail}
      </div>

      {/* Kolom kanan: topbar + 3 panel */}
      <div className="order-1 lg:order-2 flex-1 min-w-0 flex flex-col gap-3 min-h-0">
        {topbar}

        {/* Desktop: Sumber ‖ Chat ‖ Studio sejajar */}
        <div className="hidden lg:flex flex-1 min-h-0 items-stretch">
          {srcOpen ? (
            <section
              aria-label={tr('learning_view_sources', {}, 'Sources')}
              data-testid="panel-sources"
              className="min-h-0 min-w-0 flex flex-col"
              style={{ width: `${srcPx}px`, flex: '0 0 auto' }}
            >
              <div className="ct-nlm-scroll flex-1 min-h-0 overflow-y-auto">{sources}</div>
            </section>
          ) : (
            <ClosedStrip
              which="src"
              showLabel={tr('learning_src_show', {}, 'Show Sources panel')}
              shortLabel={tr('learning_view_sources', {}, 'Sources')}
              onShow={() => setSrcOpen(true)}
            />
          )}
          {srcOpen && (
            <Splitter
              which="src"
              dragging={dragging === 'src'}
              dragHint={dragHint}
              toggleLabel={tr('learning_src_hide', {}, 'Hide Sources panel')}
              onDragStart={startDrag}
              onToggle={() => setSrcOpen(false)}
            />
          )}

          <section
            aria-label={tr('learning_view_chat', {}, 'Chat')}
            data-testid="panel-chat"
            className="min-h-0 min-w-0 flex-1 flex flex-col"
          >
            {chat}
          </section>

          {stuOpen && (
            <Splitter
              which="stu"
              dragging={dragging === 'stu'}
              dragHint={dragHint}
              toggleLabel={tr('learning_studio_hide', {}, 'Hide Studio panel')}
              onDragStart={startDrag}
              onToggle={() => setStuOpen(false)}
            />
          )}
          {stuOpen ? (
            <section
              aria-label={tr('learning_view_studio', {}, 'Studio')}
              data-testid="panel-studio"
              className="min-h-0 min-w-0 flex flex-col"
              style={{ width: `${stuPx}px`, flex: '0 0 auto' }}
            >
              <div className="ct-nlm-scroll flex-1 min-h-0 overflow-y-auto">{studio}</div>
            </section>
          ) : (
            <ClosedStrip
              which="stu"
              showLabel={tr('learning_studio_show', {}, 'Show Studio panel')}
              shortLabel={tr('learning_view_studio', {}, 'Studio')}
              onShow={() => setStuOpen(true)}
            />
          )}
        </div>

        {/* Mobile: satu view penuh */}
        <div className="lg:hidden flex-1 min-h-0">
          {view === 'studio' ? studio : centerIsChat ? chat : sources}
        </div>
      </div>

      {/* Tab mobile (bottom) */}
      <div className="order-3 lg:hidden flex gap-1 bg-slate-950/70 p-1 rounded-xl border border-slate-800">
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
