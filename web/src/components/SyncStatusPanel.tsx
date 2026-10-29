/**
 * SyncStatusPanel.tsx — M04c: status sync + permukaan konflik yang bisa dipulihkan.
 *
 * Dua hal yang sebelumnya tidak ada di UI sama sekali:
 *
 * 1. Status. Pengguna hanya tahu sync "berhasil/gagal" dari sebuah toast yang
 *    sudah hilang saat mereka menoleh. Panel ini menjawab: berapa yang masih
 *    menunggu, berapa yang gagal, dan kapan terakhir kali sync benar-benar jalan.
 *
 * 2. Konflik. Sebelum ini satu-satunya UI konflik adalah dialog biner
 *    "Pertahankan Data Lokal / Pulihkan Data Cloud" — pengguna diminta membuang
 *    satu snapshot penuh tanpa pernah melihat field mana yang kalah. Server
 *    sudah menyimpan sisi kalah (K11); panel ini membuatnya terlihat dan bisa
 *    dipulihkan per field, jadi memulihkan tidak berarti menimpa pekerjaan
 *    perangkat lain.
 *
 * Sengaja bukan redesign visual: kelas dan token warnanya sama dengan
 * CloudAccountDialog, hanya menambah informasi yang sebelumnya hilang.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { RefreshCw, History, Undo2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import {
  cloudConflicts,
  cloudRestoreConflict,
  cloudSyncNow,
  cloudSyncStatus,
  type SyncConflict,
  type SyncStatusSummary,
} from '../api/cloud';
import { t } from '../i18n';

export interface SyncStatusPanelProps {
  /** Akun sudah tertaut ke cloud? Kalau belum, panel tidak punya apa untuk ditanya. */
  linked: boolean;
  busy: boolean;
  /** Menambah nilai ini memaksa muat ulang — dipakai setelah sync manual. */
  refreshKey?: number;
  onSynced?: () => void;
}

function shortValue(value: string | null): string {
  const label = t('cloud_conflicts_value_empty', '(kosong)');
  if (value === null || value === '') return label;
  return value.length > 90 ? `${value.slice(0, 90)}…` : value;
}

const SyncStatusPanel: React.FC<SyncStatusPanelProps> = ({ linked, busy, refreshKey = 0, onSynced }) => {
  const [status, setStatus] = useState<SyncStatusSummary | null>(null);
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async () => {
    if (!linked) return;
    setLoading(true);
    setError(null);
    try {
      const [s, c] = await Promise.all([cloudSyncStatus(), cloudConflicts()]);
      setStatus(s);
      setConflicts(c.conflicts || []);
    } catch (err) {
      setError(String((err as any)?.message || err || ''));
    } finally {
      setLoading(false);
    }
  }, [linked]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await cloudSyncNow();
      await load();
      onSynced?.();
    } catch (err) {
      setError(String((err as any)?.message || err || ''));
    } finally {
      setSyncing(false);
    }
  };

  const handleRestore = async (conflictId: number) => {
    setRestoring(conflictId);
    try {
      const res = await cloudRestoreConflict(conflictId);
      if (!res.ok) throw new Error(res.error || res.code || 'cloud_conflict_restore_failed');
      await load();
    } catch (err) {
      setError(String((err as any)?.message || err || ''));
    } finally {
      setRestoring(null);
    }
  };

  const stats: Array<{ label: string; value: number; tone: string }> = [
    {
      label: t('cloud_sync_status_pending', '{n} menunggu').replace('{n}', ''),
      value: status?.pending ?? 0,
      tone: 'text-amber-300',
    },
    {
      label: t('cloud_sync_status_failed', '{n} gagal').replace('{n}', ''),
      value: status?.failed ?? 0,
      tone: 'text-rose-300',
    },
    {
      label: t('cloud_sync_status_conflicts', '{n} konflik').replace('{n}', ''),
      value: status?.unresolved_conflicts ?? 0,
      tone: 'text-sky-300',
    },
  ];

  const busyNow = busy || syncing;

  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3.5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 inline-flex items-center gap-1.5">
          <History className="w-3.5 h-3.5" aria-hidden="true" />
          {t('cloud_sync_status_title', 'Status Sinkronisasi')}
        </p>
        <button
          type="button"
          disabled={busyNow || !linked}
          onClick={() => void handleSync()}
          className="ct-btn ct-btn-gold ct-btn-sm font-black inline-flex items-center gap-1.5 disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${busyNow ? 'animate-spin' : ''}`} aria-hidden="true" />
          {t('cloud_sync_now', 'Sync Sekarang')}
        </button>
      </div>

      {error && (
        <p className="text-[11px] text-rose-300 font-bold inline-flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          {error}
        </p>
      )}

      <div className="grid grid-cols-3 gap-2 text-center">
        {stats.map((s) => (
          <div key={s.label}>
            <p className={`text-base font-black ct-nlm-num ${s.value > 0 ? s.tone : 'text-slate-500'}`}>{s.value}</p>
            <p className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">{s.label.trim()}</p>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-slate-400">
        {status?.last_synced_at
          ? t('cloud_sync_status_last', 'Terakhir sync: {when}').replace('{when}', status.last_synced_at)
          : t('cloud_sync_status_never', 'Belum pernah sync')}
        {status && status.pending === 0 && status.failed === 0 && (
          <span className="ml-1.5 text-emerald-300 font-bold inline-flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
            {t('cloud_sync_status_up_to_date', 'Semua tersinkron')}
          </span>
        )}
      </p>

      {status && status.failed > 0 && (
        <ul className="space-y-1">
          {status.failed_jobs.slice(0, 3).map((job, i) => (
            <li key={`${job.entity_type}-${i}`} className="text-[10px] text-rose-300/80 truncate">
              {job.entity_type} · {job.operation} · retry {job.retry_count} — {job.last_error}
            </li>
          ))}
        </ul>
      )}

      {conflicts.length > 0 && (
        <div className="space-y-2 border-t border-slate-800 pt-3">
          <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500">
            {t('cloud_conflicts_title', 'Konflik yang diselesaikan otomatis')}
          </p>
          <p className="text-[10px] text-slate-500">{t('cloud_conflicts_desc', '')}</p>
          <ul className="space-y-2">
            {conflicts.map((c) => (
              <li key={c.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-2.5 space-y-1.5">
                <p className="text-[11px] font-bold text-slate-200">
                  {t('cloud_conflicts_field', '{table} · {field}')
                    .replace('{table}', c.table_name)
                    .replace('{field}', c.field)}
                  <span className="ml-1.5 text-[9px] uppercase tracking-wider text-slate-500 font-bold">
                    {c.kept_side === 'cloud'
                      ? t('cloud_conflicts_side_cloud', 'Cloud lebih baru')
                      : t('cloud_conflicts_side_local', 'Perangkat ini lebih baru')}
                  </span>
                </p>
                <p className="text-[10px] text-emerald-300/80">
                  {t('cloud_conflicts_kept', 'Dipakai: {value}').replace('{value}', shortValue(c.kept_value))}
                </p>
                <p className="text-[10px] text-amber-300/80">
                  {t('cloud_conflicts_lost', 'Tertimpa: {value}').replace('{value}', shortValue(c.lost_value))}
                </p>
                <button
                  type="button"
                  disabled={busyNow || restoring === c.id}
                  onClick={() => void handleRestore(c.id)}
                  className="ct-btn ct-btn-secondary ct-btn-sm font-bold inline-flex items-center gap-1.5 disabled:opacity-40"
                >
                  <Undo2 className={`w-3.5 h-3.5 ${restoring === c.id ? 'animate-pulse' : ''}`} aria-hidden="true" />
                  {t('cloud_conflicts_restore', '↩️ Pulihkan nilai saya')}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {conflicts.length === 0 && !loading && (
        <p className="text-[10px] text-slate-600">{t('cloud_conflicts_empty', 'Tidak ada konflik yang perlu ditinjau.')}</p>
      )}
    </section>
  );
};

export default SyncStatusPanel;
