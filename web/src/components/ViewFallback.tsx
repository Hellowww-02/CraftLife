import React from 'react';
import { t } from '../i18n';

/**
 * D01 (v1.6.7): skeleton pengganti isi view saat chunk lazy-loading.
 * Memakai bahasa visual skeleton yang sudah ada (ct-skeleton, U1/U11) agar
 * transisi pindah halaman tetap terasa sama seperti state loading lain.
 * Satu-satunya string memakai key lama `web_loading` — nol key i18n baru.
 */
export const ViewFallback: React.FC = () => (
  <div aria-busy="true" aria-label={t('web_loading', 'Memuat...')}>
    <span className="sr-only">{t('web_loading', 'Memuat...')}</span>
    <div className="ct-skeleton h-28 rounded-2xl mb-4" aria-hidden="true" />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3" aria-hidden="true">
      <div className="ct-skeleton h-36 rounded-2xl" />
      <div className="ct-skeleton h-36 rounded-2xl" />
      <div className="ct-skeleton h-36 rounded-2xl" />
    </div>
  </div>
);
