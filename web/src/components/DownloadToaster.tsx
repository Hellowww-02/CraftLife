import React, { useEffect } from 'react';
import { useGame } from '../context/GameContext';
import { onDownloadEvent } from '../api/client';
import { t } from '../i18n';

/**
 * A03.5 — DownloadToaster.
 *
 * Shell PyQt (web_shell.py) memanggil `window.craftlifeDownloadEvent(status, name, path)`
 * setelah Qt benar-benar menulis berkas ke komputer. Komponen ini menerjemahkannya
 * menjadi toast berisi LOKASI berkas ("Tersimpan di: C:\\Users\\…\\Downloads\\CraftLife\\…"),
 * sehingga tidak ada lagi unduhan yang "hilang tanpa kabar".
 */
export const DownloadToaster: React.FC = () => {
  const { showToast, lang } = useGame();

  useEffect(() => {
    const off = onDownloadEvent((e) => {
      const tr = (key: string, fb: string, vars?: Record<string, string>) => {
        let s = t(key, fb);
        if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(v);
        return s;
      };
      if (e.status === 'start') return; // cukup berisik kalau ditampilkan
      if (e.status === 'failed') {
        showToast('damage', tr('download_failed_title', 'Unduhan gagal'),
          tr('download_failed_msg', 'Berkas tidak tersimpan. Coba lagi.'));
        return;
      }
      showToast('success', tr('download_saved_title', 'Berkas tersimpan'),
        tr('download_saved_msg', 'Tersimpan di: {path}', { path: e.path || e.name }));
    });
    return off;
  }, [showToast, lang]);

  return null;
};
