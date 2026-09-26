import { useEffect } from 'react';

/**
 * D04 (v1.6.7, backlog v2.1 "Esc-per-modal"): tutup dialog saat tombol Esc
 * ditekan, hanya selama dialog terbuka. Satu hook bersama agar perilaku
 * konsisten di semua dialog — sebelumnya hanya palette + 2 dialog yg bisa Esc.
 *
 * @param open  true saat dialog tampil ( предотвра listener bocor saat tutup)
 * @param onClose  pemulih state tutup milik dialog (stabil milik pemanggil)
 */
export function useEscapeClose(open: boolean, onClose: () => void): void {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
}
