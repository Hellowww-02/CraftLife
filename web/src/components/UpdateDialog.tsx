import React, { useEffect, useRef, useState } from 'react';
import { t } from '../i18n';
import { studio } from '../api/studio';

export interface UpdateInfo {
  version: string;
  notes?: string;
  size_bytes?: number;
}

type Phase = 'offer' | 'downloading' | 'ready' | 'applying' | 'restarting' | 'error';

const COUNTDOWN_SECONDS = 15;

function fmtBytes(n: number): string {
  if (!n || n <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let v = n;
  let u = 0;
  while (v >= 1024 && u < units.length - 1) {
    v /= 1024;
    u += 1;
  }
  return `${v >= 100 ? Math.round(v) : v.toFixed(1)} ${units[u]}`;
}

/** C07: dialog update global — tawar → unduh (progres) → countdown → apply → restart. */
export const UpdateDialog: React.FC<{ info: UpdateInfo; onDismiss: () => void }> = ({ info, onDismiss }) => {
  const [phase, setPhase] = useState<Phase>('offer');
  const [done, setDone] = useState(0);
  const [total, setTotal] = useState(0);
  const [count, setCount] = useState(COUNTDOWN_SECONDS);
  const [error, setError] = useState('');
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  const pollDownload = () => {
    const timer = window.setInterval(async () => {
      try {
        const res = await studio.updateStatus();
        const st = res?.status;
        if (!alive.current) {
          window.clearInterval(timer);
          return;
        }
        if (!res?.ok || !st) {
          window.clearInterval(timer);
          setError(String(res?.error || 'update_status_failed'));
          setPhase('error');
          return;
        }
        setDone(Number(st.done) || 0);
        setTotal(Number(st.total) || 0);
        if (st.state === 'ready') {
          window.clearInterval(timer);
          setCount(COUNTDOWN_SECONDS);
          setPhase('ready');
        } else if (st.state === 'error') {
          window.clearInterval(timer);
          setError(String(st.error || 'download_failed'));
          setPhase('error');
        }
      } catch (e) {
        window.clearInterval(timer);
        if (alive.current) {
          setError(e instanceof Error ? e.message : String(e));
          setPhase('error');
        }
      }
    }, 800);
  };

  const startDownload = async () => {
    setPhase('downloading');
    setDone(0);
    setTotal(0);
    try {
      const res = await studio.updateDownload();
      if (!alive.current) return;
      if (!res?.ok) {
        setError(String(res?.error || 'update_download_failed'));
        setPhase('error');
        return;
      }
      const st = res?.status;
      if (st) {
        setDone(Number(st.done) || 0);
        setTotal(Number(st.total) || 0);
        if (st.state === 'ready') {
          setCount(COUNTDOWN_SECONDS);
          setPhase('ready');
          return;
        }
        if (st.state === 'error') {
          setError(String(st.error || 'download_failed'));
          setPhase('error');
          return;
        }
      }
      pollDownload();
    } catch (e) {
      if (alive.current) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase('error');
      }
    }
  };

  const applyNow = async () => {
    setPhase('applying');
    try {
      const res = await studio.updateApply();
      if (!alive.current) return;
      if (res?.ok) {
        setPhase('restarting');
      } else {
        setError(String(res?.error || 'update_apply_failed'));
        setPhase('error');
      }
    } catch (e) {
      if (alive.current) {
        setError(e instanceof Error ? e.message : String(e));
        setPhase('error');
      }
    }
  };

  // Countdown auto-apply saat fase ready (keputusan user: Nanti membatalkan).
  const applyRef = useRef(applyNow);
  applyRef.current = applyNow;
  useEffect(() => {
    if (phase !== 'ready') return;
    if (count <= 0) {
      applyRef.current();
      return;
    }
    const timer = window.setTimeout(() => alive.current && setCount((c) => c - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [phase, count]);

  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  const sizeNum = Number(info.size_bytes) || 0;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/60 p-4">
      <div className="ct-panel w-full max-w-lg p-6 space-y-4">
        <h2 className="text-base font-bold text-slate-100">
          {t('update_available_title', 'Pembaruan Tersedia')}
        </h2>
        <p className="text-sm text-slate-300">
          {t('update_available', 'Update tersedia: v{version}').replace('{version}', String(info.version))}
        </p>
        {sizeNum > 0 && (
          <p className="text-[11px] text-slate-400">
            {t('update_size', 'Ukuran: {size}').replace('{size}', fmtBytes(sizeNum))}
          </p>
        )}
        {info.notes && (
          <div className="rounded-xl border border-slate-700 bg-slate-900/60 p-3 space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wide text-slate-400">
              {t('update_notes_label', 'Catatan rilis')}
            </span>
            <p className="text-xs text-slate-300 whitespace-pre-wrap max-h-40 overflow-y-auto">{info.notes}</p>
          </div>
        )}

        {(phase === 'downloading' || phase === 'ready') && (
          <div className="space-y-1">
            <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-emerald-500 transition-all" style={{ width: `${phase === 'ready' ? 100 : pct}%` }} />
            </div>
            <p className="text-[11px] text-slate-400">
              {phase === 'ready'
                ? t('update_downloaded', 'Update terunduh. Siap diterapkan.')
                : `${t('update_downloading', 'Mengunduh update… {pct}%').replace('{pct}', String(pct))} · ${fmtBytes(done)} / ${fmtBytes(total)}`}
            </p>
          </div>
        )}
        {phase === 'ready' && (
          <p className="text-[11px] text-amber-300/90">
            {t('update_auto_countdown', 'Aplikasi akan diperbarui & dimulai ulang otomatis dalam {n} detik…').replace('{n}', String(count))}
          </p>
        )}
        {phase === 'applying' && (
          <p className="text-xs text-slate-300">{t('update_applying', 'Menerapkan update…')}</p>
        )}
        {phase === 'restarting' && (
          <div className="space-y-1">
            <p className="text-xs text-emerald-300">{t('update_restarting', 'Menerapkan update & memulai ulang…')}</p>
            <p className="text-[11px] text-slate-400">{t('update_reopen_note', 'Server dimatikan untuk update. Buka kembali aplikasi setelah update selesai.')}</p>
          </div>
        )}
        {phase === 'error' && (
          <p className="text-xs text-rose-300">
            {t('update_failed', 'Update gagal: {error}').replace('{error}', error)}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          {phase === 'offer' && (
            <>
              <button
                type="button"
                onClick={onDismiss}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
              >
                {t('update_later', 'Nanti')}
              </button>
              <button
                type="button"
                onClick={startDownload}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white"
              >
                {t('update_download', '⬇ Unduh Update')}
              </button>
            </>
          )}
          {phase === 'downloading' && (
            <button
              type="button"
              onClick={onDismiss}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
            >
              {t('update_later', 'Nanti')}
            </button>
          )}
          {phase === 'ready' && (
            <>
              <button
                type="button"
                onClick={onDismiss}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
              >
                {t('update_later', 'Nanti')}
              </button>
              <button
                type="button"
                onClick={applyNow}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white"
              >
                {t('update_apply', '🔄 Update Sekarang')}
              </button>
            </>
          )}
          {(phase === 'error' || phase === 'restarting') && (
            <button
              type="button"
              onClick={onDismiss}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
            >
              {t('btn_close', 'Tutup')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
