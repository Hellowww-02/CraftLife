/**
 * CloudAccountDialog.tsx — dialog konfigurasi Cloud/Supabase (H06, v1.7.0).
 *
 * Menggantikan deretan tombol inline di SettingsView yang sulit dipahami
 * (keluhan user: "banyak bug/error, tidak ada dialog"). Semua fungsi LAMA
 * tetap ada (register, sign-in & link, sync, migrasi, konflik, perangkat,
 * retry antrean, sign-out) — hanya dipindahkan ke dialog 4 tab:
 *
 *   Akun · Sinkronisasi · Perangkat · Diagnostik
 *
 * Error dari server datang sebagai KODE (cloud_api.classify_cloud_error) dan
 * dipetakan ke teks bilingual cloud_err_<code> — tidak ada lagi "HTTP 400".
 */
import React, { useEffect, useState } from 'react';
import {
  X, Cloud, RefreshCw, Smartphone, LogOut, ShieldCheck, Activity,
  AlertTriangle, CheckCircle2, Database, Inbox, Link2,
} from 'lucide-react';
import {
  cloudConflict,
  cloudDevices,
  cloudLogin,
  cloudLogout,
  cloudMigrateLocal,
  cloudQueueRetry,
  cloudRegister,
  cloudRevokeDevice,
  cloudSyncNow,
  type CloudDevice,
  type CloudStatus,
} from '../api/cloud';
import { t } from '../i18n';

export type CloudRunner = (fn: () => Promise<any>, okMsg?: string) => Promise<any>;

export interface CloudAccountDialogProps {
  open: boolean;
  onClose: () => void;
  cloud: CloudStatus | null;
  busy: boolean;
  runCloud: CloudRunner;
}

/** Petakan kode error server → teks bilingual; fallback = pesan mentah. */
export function cloudErrMsg(err: unknown): string {
  const raw = String((err as any)?.message || err || '');
  if (/^[a-z_]+$/i.test(raw) && raw.length < 48) {
    const mapped = t(`cloud_err_${raw}`, '');
    if (mapped) return mapped;
  }
  return raw;
}

const Badge: React.FC<{ ok: boolean; okLabel: string; noLabel: string; tone?: 'green' | 'sky' | 'amber' }> = ({ ok, okLabel, noLabel, tone = 'green' }) => {
  const on = tone === 'green' ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/40'
    : tone === 'sky' ? 'bg-sky-500/15 text-sky-300 border-sky-500/40'
      : 'bg-amber-500/15 text-amber-300 border-amber-500/40';
  const off = 'bg-slate-800/70 text-slate-500 border-slate-700';
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-bold ${ok ? on : off}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-current' : 'bg-slate-600'}`} aria-hidden="true" />
      {ok ? okLabel : noLabel}
    </span>
  );
};

const CloudAccountDialog: React.FC<CloudAccountDialogProps> = ({ open, onClose, cloud, busy, runCloud }) => {
  const [tab, setTab] = useState<'account' | 'sync' | 'devices' | 'diag'>('account');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [devices, setDevices] = useState<CloudDevice[]>([]);
  const [devBusy, setDevBusy] = useState(false);

  const linked = Boolean(cloud?.linked && cloud?.configured);
  const pending = (cloud?.queue?.pending || 0) + (cloud?.queue?.retry || 0);
  const conflict = cloud?.personal?.conflict_status === 'needs_resolution';

  useEffect(() => {
    if (!open) return;
    if (linked) void refreshDevices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, linked]);

  const refreshDevices = async () => {
    setDevBusy(true);
    try {
      const d = await cloudDevices();
      setDevices(Array.isArray(d.devices) ? d.devices : []);
    } catch { /* ditampilkan lewat diagnostik bila gagal */ }
    finally { setDevBusy(false); }
  };

  const tr = t;
  const tabs = [
    { id: 'account' as const, label: tr('cloud_tab_account', 'Akun'), icon: <ShieldCheck className="w-3.5 h-3.5" aria-hidden="true" /> },
    { id: 'sync' as const, label: tr('cloud_tab_sync', 'Sinkronisasi'), icon: <RefreshCw className="w-3.5 h-3.5" aria-hidden="true" /> },
    { id: 'devices' as const, label: tr('cloud_tab_devices', 'Perangkat'), icon: <Smartphone className="w-3.5 h-3.5" aria-hidden="true" /> },
    { id: 'diag' as const, label: tr('cloud_tab_diag', 'Diagnostik'), icon: <Activity className="w-3.5 h-3.5" aria-hidden="true" /> },
  ];

  if (!open) return null;

  return (
    <div className="ct-backdrop fixed inset-0 z-[80] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label={tr('cloud_dialog_title', 'Konfigurasi Cloud (Supabase)')}>
      <div className="ct-dialog w-full max-w-xl p-0 overflow-hidden max-h-[86vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center gap-3 px-5 py-4 border-b border-slate-800 bg-slate-950/60">
          <span className="w-9 h-9 rounded-xl bg-sky-500/15 border border-sky-500/40 flex items-center justify-center shrink-0">
            <Cloud className="w-4.5 h-4.5 text-sky-400" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-black text-slate-100">{tr('cloud_dialog_title', 'Konfigurasi Cloud (Supabase)')}</h3>
            <div className="flex flex-wrap gap-1.5 mt-1">
              <Badge ok={!!cloud?.configured} tone="amber" okLabel={tr('cloud_badge_configured', 'Terkonfigurasi')} noLabel={tr('cloud_badge_not_configured', 'Belum dikonfigurasi')} />
              <Badge ok={linked} tone="sky" okLabel={linked ? `${tr('cloud_badge_linked', 'Terhubung')}: ${cloud?.email || ''}` : tr('cloud_badge_unlinked', 'Belum terhubung')} noLabel={tr('cloud_badge_unlinked', 'Belum terhubung')} />
              <Badge ok={!!cloud?.realtime_connected} tone="green" okLabel={tr('cloud_realtime_on', 'Realtime aktif')} noLabel={tr('cloud_realtime_off', 'Realtime nonaktif')} />
              <Badge ok={pending === 0} tone="green" okLabel={tr('cloud_queue_clear', 'Antrean kosong')} noLabel={tr('cloud_queue_pending', '{n} antrean').replace('{n}', String(pending))} />
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label={tr('btn_close', 'Tutup')} className="text-slate-400 hover:text-slate-200 shrink-0">
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-4 pt-3 border-b border-slate-800" role="tablist" aria-label={tr('cloud_dialog_title', 'Konfigurasi Cloud (Supabase)')}>
          {tabs.map((tb) => (
            <button
              key={tb.id}
              type="button"
              role="tab"
              aria-selected={tab === tb.id}
              onClick={() => setTab(tb.id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-[11px] font-bold rounded-t-lg border-b-2 transition-colors ${
                tab === tb.id ? 'border-sky-400 text-sky-300 bg-sky-500/10' : 'border-transparent text-slate-500 hover:text-slate-300'
              }`}
            >
              {tb.icon}{tb.label}
            </button>
          ))}
        </div>

        {/* Isi */}
        <div className="overflow-y-auto p-5 space-y-4">
          {/* ══ TAB AKUN ══ */}
          {tab === 'account' && (
            <div className="space-y-4">
              <p className="text-xs text-slate-400">{tr('cloud_dialog_account_hint', 'Buat akun cloud baru, atau hubungkan akun lokal ini dengan email yang sudah terdaftar.')}</p>
              {linked ? (
                <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/5 p-4 space-y-3">
                  <p className="text-xs text-emerald-200 flex items-center gap-2">
                    <Link2 className="w-4 h-4 shrink-0" aria-hidden="true" />
                    {tr('cloud_status_linked', 'Terhubung: {email}').replace('{email}', cloud?.email || '')}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    {tr('cloud_last_sync', 'Sinkron terakhir')}: <span className="text-slate-200 ct-nlm-num">{cloud?.link?.last_sync_at || tr('cloud_never', 'belum pernah')}</span>
                  </p>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void runCloud(() => cloudLogout())}
                    className="ct-btn ct-btn-danger ct-btn-sm inline-flex items-center gap-1.5"
                  >
                    <LogOut className="w-3.5 h-3.5" aria-hidden="true" />{tr('cloud_sign_out', 'Sign Out Cloud')}
                  </button>
                </div>
              ) : (
                <form
                  className="space-y-3"
                  onSubmit={(e) => { e.preventDefault(); void runCloud(() => cloudLogin(email, password), tr('cloud_account_created', 'Akun terhubung.')); }}
                >
                  <label className="block space-y-1">
                    <span className="text-[11px] font-bold text-slate-400">{tr('cloud_email', 'Cloud email')}</span>
                    <input
                      type="email" autoComplete="email" name="cloud-email" value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="nama@email.com"
                      className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-sky-500"
                    />
                  </label>
                  <label className="block space-y-1">
                    <span className="text-[11px] font-bold text-slate-400">{tr('cloud_password', 'Password cloud (min. 8)')}</span>
                    <input
                      type="password" autoComplete="current-password" name="cloud-password" value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full px-3 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 text-xs focus:outline-none focus:border-sky-500"
                    />
                  </label>
                  {password && password.length < 8 && (
                    <p className="text-[10px] text-amber-300 flex items-center gap-1"><AlertTriangle className="w-3 h-3" aria-hidden="true" />{tr('cloud_err_credentials_invalid', 'Password minimal 8 karakter.')}</p>
                  )}
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="submit"
                      disabled={busy || !email.includes('@') || password.length < 8}
                      className="ct-btn ct-btn-primary ct-btn-sm font-black disabled:opacity-40"
                    >
                      {tr('cloud_signin_link', 'Sign In & Link')}
                    </button>
                    <button
                      type="button"
                      disabled={busy || !email.includes('@') || password.length < 8}
                      onClick={() => void runCloud(() => cloudRegister(email, password), tr('cloud_verification_sent', 'Cek inbox untuk verifikasi email.'))}
                      className="ct-btn ct-btn-secondary ct-btn-sm font-bold disabled:opacity-40"
                    >
                      {tr('cloud_create_account', 'Buat Akun Cloud')}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* ══ TAB SINKRONISASI ══ */}
          {tab === 'sync' && (
            <div className="space-y-3">
              {!linked && (
                <p className="text-xs text-amber-300 flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  {tr('cloud_err_auth_required', 'Belum terhubung ke cloud. Sign In terlebih dahulu di tab Akun.')}
                </p>
              )}
              {conflict && (
                <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-3.5 space-y-2.5">
                  <p className="text-xs text-amber-200 font-bold">{tr('cloud_conflict_title', 'Konflik data terdeteksi')}</p>
                  <p className="text-[11px] text-amber-200/80">{tr('cloud_conflict_hint', 'Data tracker berubah di perangkat ini dan perangkat lain. Pilih sumber yang ingin dipertahankan.')}</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button" disabled={busy}
                      onClick={() => { if (window.confirm(tr('cloud_conflict_keep_local_confirm', 'Keep local?'))) void runCloud(() => cloudConflict('local'), tr('cloud_conflict_resolved', 'Conflict resolved')); }}
                      className="ct-btn ct-btn-gold ct-btn-sm font-black"
                    >
                      {tr('cloud_conflict_keep_local', 'Pertahankan Data Lokal')}
                    </button>
                    <button
                      type="button" disabled={busy}
                      onClick={() => { if (window.confirm(tr('cloud_conflict_use_remote_confirm', 'Restore cloud?'))) void runCloud(() => cloudConflict('cloud'), tr('cloud_conflict_resolved', 'Conflict resolved')); }}
                      className="ct-btn ct-btn-danger ct-btn-sm font-black"
                    >
                      {tr('cloud_conflict_use_remote', 'Pulihkan Data Cloud')}
                    </button>
                  </div>
                </div>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <button
                  type="button" disabled={busy || !linked}
                  onClick={() => void runCloud(() => cloudSyncNow(), tr('cloud_sync_success', 'Cloud sync selesai.'))}
                  className="ct-btn ct-btn-gold h-11 font-black inline-flex items-center justify-center gap-1.5 disabled:opacity-40"
                >
                  <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} aria-hidden="true" />
                  {tr('cloud_sync_now', 'Sync Sekarang')}
                </button>
                <button
                  type="button" disabled={busy || !linked}
                  onClick={() => { if (window.confirm(tr('cloud_migrate_local_confirm', 'Antrikan data lokal ke cloud?'))) void runCloud(() => cloudMigrateLocal()); }}
                  className="ct-btn ct-btn-secondary h-11 font-bold inline-flex items-center justify-center gap-1.5 disabled:opacity-40"
                >
                  <Database className="w-4 h-4" aria-hidden="true" />
                  {tr('cloud_migrate_local', 'Migrasikan Data Lokal')}
                </button>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3.5 space-y-1.5">
                <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500">{tr('cloud_queue_title', 'Antrean sinkronisasi')}</p>
                <div className="grid grid-cols-4 gap-2 text-center">
                  {([
                    ['pending', cloud?.queue?.pending || 0, 'text-amber-300'],
                    ['retry', cloud?.queue?.retry || 0, 'text-orange-300'],
                    ['done', cloud?.queue?.done || 0, 'text-emerald-300'],
                    ['failed', cloud?.queue?.failed || 0, 'text-rose-300'],
                  ] as const).map(([k, v, color]) => (
                    <div key={k}>
                      <p className={`text-base font-black ct-nlm-num ${color}`}>{v}</p>
                      <p className="text-[9px] uppercase tracking-wider text-slate-500 font-bold">{tr(`cloud_queue_stat_${k}`, k)}</p>
                    </div>
                  ))}
                </div>
                <button
                  type="button" disabled={busy || !linked}
                  onClick={() => void runCloud(() => cloudQueueRetry())}
                  className="ct-btn ct-btn-secondary ct-btn-sm mt-1 disabled:opacity-40"
                >
                  {tr('cloud_queue_retry', 'Coba Lagi')}
                </button>
              </div>
            </div>
          )}

          {/* ══ TAB PERANGKAT ══ */}
          {tab === 'devices' && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between">
                <p className="text-[11px] text-slate-500">{tr('cloud_devices_info', 'UUID perangkat bukan credential.')}</p>
                <button type="button" onClick={() => void refreshDevices()} disabled={devBusy}
                  className="ct-btn ct-btn-secondary ct-btn-sm disabled:opacity-40">
                  {tr('btn_refresh', 'Muat ulang')}
                </button>
              </div>
              {!linked && <p className="text-xs text-amber-300">{tr('cloud_err_auth_required', 'Belum terhubung ke cloud. Sign In terlebih dahulu.')}</p>}
              {linked && devices.length === 0 && !devBusy && (
                <p className="text-xs text-slate-500 flex items-center gap-2"><Inbox className="w-4 h-4" aria-hidden="true" />{tr('cloud_devices_empty', 'Belum ada perangkat terdaftar.')}</p>
              )}
              {devices.map((d) => (
                <div key={d.id} className={`flex items-center justify-between gap-2 rounded-xl border p-3 text-xs ${d.current ? 'border-sky-500/40 bg-sky-500/5' : 'border-slate-800 bg-slate-950/50'}`}>
                  <div className="min-w-0">
                    <p className="font-bold text-slate-200 truncate">
                      {d.current && <span className="text-sky-300">★ </span>}
                      {d.device_name || d.id}
                    </p>
                    <p className="text-[10px] text-slate-500 ct-nlm-num">
                      {d.platform || '—'} · {d.last_seen_at ? `${tr('cloud_device_seen', 'terakhir dilihat')}: ${d.last_seen_at}` : '—'}
                      {d.revoked_at ? ` · ${tr('cloud_device_revoked', 'revoked')}` : ''}
                    </p>
                  </div>
                  {!d.current && !d.revoked_at && (
                    <button
                      type="button"
                      onClick={async () => {
                        try { await cloudRevokeDevice(d.id); await refreshDevices(); } catch (e) { window.alert(cloudErrMsg(e)); }
                      }}
                      className="ct-btn ct-btn-danger ct-btn-sm shrink-0"
                    >
                      {tr('cloud_device_revoke', 'Revoke')}
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ══ TAB DIAGNOSTIK ══ */}
          {tab === 'diag' && (
            <div className="space-y-2 text-xs">
              {([
                ['Supabase .env', !!cloud?.configured],
                [t('cloud_diag_sdk', 'Paket SDK supabase'), !!cloud?.sdk_available],
                [t('cloud_diag_keyring', 'Keyring (penyimpan sesi)'), !!cloud?.keyring_available],
                [t('cloud_diag_auth', 'Terautentikasi'), !!cloud?.authenticated],
                [t('cloud_diag_linked', 'Akun lokal terhubung'), linked],
                [t('cloud_realtime_on', 'Realtime aktif'), !!cloud?.realtime_connected],
              ] as [string, boolean][]).map(([label, ok]) => (
                <div key={label} className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
                  <span className="text-slate-400">{label}</span>
                  {ok
                    ? <span className="text-emerald-300 font-bold inline-flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" aria-hidden="true" />OK</span>
                    : <span className="text-slate-600 font-bold inline-flex items-center gap-1"><X className="w-3.5 h-3.5" aria-hidden="true" />—</span>}
                </div>
              ))}
              {cloud?.device && (
                <div className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1">{tr('cloud_tab_devices', 'Perangkat')}</p>
                  <p className="text-slate-300 break-all ct-nlm-num">{cloud.device.device_id}</p>
                  <p className="text-[10px] text-slate-500">{cloud.device.device_name || '—'} · {cloud.device.platform || '—'}</p>
                </div>
              )}
              {(cloud?.queue_failed_samples?.length || 0) > 0 && (
                <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 px-3 py-2 space-y-1.5">
                  <p className="text-[10px] uppercase tracking-wider font-bold text-rose-300">{tr('cloud_diag_failed_samples', 'Contoh kegagalan antrean')}</p>
                  {(cloud?.queue_failed_samples || []).map((s, i) => (
                    <p key={i} className="text-[10px] text-slate-400 break-words">
                      [{s.entity_type}] {cloudErrMsg(s.last_error || '')}
                    </p>
                  ))}
                </div>
              )}
              {cloud?.last_error && (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-3 py-2">
                  <p className="text-[10px] uppercase tracking-wider font-bold text-amber-300 mb-1">{tr('cloud_diag_last_error', 'Error terakhir')}</p>
                  <p className="text-[11px] text-slate-300 break-words">{cloudErrMsg(cloud.last_error)}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CloudAccountDialog;
