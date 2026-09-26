import React from 'react';
import { t } from '../i18n';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Dipanggil setelah state error dibersihkan (mis. navigasi ulang). */
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * D02 (v1.6.7): batas crash per-view + root. Sebelumnya satu render error
 * membuat seluruh aplikasi jadi layar putih kosong tanpa jalan keluar.
 * Sekarang: panel dwibahasa + tombol pulih. Data tidak tersentuh sama sekali.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error): void {
    // Mengapa dicatat: satu-satunya jejak crash render di app offline ini.
    console.error('[CraftLife] view crash:', error);
  }

  private handleRetry = (): void => {
    this.setState({ error: null });
    this.props.onRetry?.();
  };

  private handleReloadApp = (): void => {
    window.location.reload();
  };

  render(): React.ReactNode {
    if (!this.state.error) return this.props.children;
    const msg = this.state.error.message || String(this.state.error);
    return (
      <div className="ct-view" role="alert" aria-live="assertive">
        <div className="ct-card max-w-lg mx-auto mt-10 p-6 text-center border-rose-500/40">
          <div className="text-4xl mb-3" aria-hidden="true">
            🧱
          </div>
          <h2 className="text-lg font-black text-rose-400 mb-2">{t('crash_title', 'Ups, halaman ini gagal dimuat')}</h2>
          <p className="text-sm text-slate-400 mb-5">{t('crash_msg', 'Terjadi kesalahan tak terduga. Data kamu aman.')}</p>
          <div className="flex flex-wrap gap-2 justify-center">
            <button type="button" onClick={this.handleRetry} className="ct-btn ct-btn-primary ct-btn-sm">
              {t('crash_retry', 'Muat ulang halaman')}
            </button>
            <button type="button" onClick={this.handleReloadApp} className="ct-btn ct-btn-ghost ct-btn-sm">
              {t('crash_reload_app', 'Muat ulang aplikasi')}
            </button>
          </div>
          <details className="mt-4 text-left">
            <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300">
              {t('crash_details', 'Detail teknis')}
            </summary>
            <pre className="mt-2 text-[11px] leading-relaxed bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-slate-400 overflow-x-auto whitespace-pre-wrap break-words">
              {msg}
            </pre>
          </details>
        </div>
      </div>
    );
  }
}
