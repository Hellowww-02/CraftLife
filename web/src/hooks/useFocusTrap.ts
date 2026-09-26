import { useEffect, useRef } from 'react';

/**
 * E04 (v1.6.7): kunci fokus keyboard di dalam dialog selagi aktif.
 * - Fokus awal otomatis ke elemen pertama yg bisa difokus.
 * - Tab / Shift+Tab berputar di dalam panel (tak lolos ke belakang backdrop).
 * - Non-intrusif: hanya keydown Tab, tanpa mengubah focus saat nonaktif.
 */
const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

export function useFocusTrap<T extends HTMLElement>(active: boolean) {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    if (!active) return;
    const node = ref.current;
    if (!node) return;

    const items = () =>
      Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null || el === document.activeElement
      );

    // Fokus awal: elemen autofocus bila ada, sonst yg pertama.
    const initial = node.querySelector<HTMLElement>('[data-autofocus]') ?? items()[0];
    try {
      initial?.focus({ preventScroll: true });
    } catch {
      /* abaikan */
    }

    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const f = items();
      if (f.length === 0) {
        e.preventDefault();
        return;
      }
      const first = f[0];
      const last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [active]);

  return ref;
}
