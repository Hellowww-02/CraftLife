import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { apiGet, apiPost } from '../../api/client';
import {
  cloudConflict,
  cloudDevices,
  cloudLogin,
  cloudLogout,
  cloudMigrateLocal,
  cloudQueueRetry,
  cloudRegister,
  cloudRevokeDevice,
  cloudStatus,
  cloudSyncNow,
  type CloudDevice,
  type CloudStatus,
} from '../../api/cloud';
import { t } from '../../i18n';
import { Settings, User, Volume2, VolumeX, Globe, Download, Upload, Trash2, Cloud, RefreshCw, LogOut, Smartphone, Palette, Database, RefreshCcw } from 'lucide-react';

// ===== Parity SettingsPage: panel admin (debug cheats, gated is_admin) =====
const AdminDebugPanel: React.FC = () => {
  const [xp, setXp] = useState(1000);
  const [gold, setGold] = useState(500);
  const [petExp, setPetExp] = useState(100);
  const run = (action: string, amount?: number) => {
    apiPost('/api/admin/debug', { action, amount }).then(() => window.location.reload()).catch(() => undefined);
  };
  return (
    <div className="rounded-2xl bg-slate-900 border border-rose-800/40 p-5 space-y-3">
      <h3 className="font-bold text-xs text-rose-300 uppercase tracking-wider">{t('admin_panel', 'Panel Admin')}</h3>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <input type="number" value={xp} onChange={(e) => setXp(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('add_xp', xp)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_add_xp', '+ XP')}</button>
        <input type="number" value={gold} onChange={(e) => setGold(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('add_gold', gold)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_add_gold', '+ Gold')}</button>
        <button type="button" onClick={() => run('fill_hp_mp')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_fill_hp_mp', 'Isi HP/MP')}</button>
        <button type="button" onClick={() => run('max_level')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_max_level', 'Max Level (50)')}</button>
        <button type="button" onClick={() => run('complete_tasks')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_complete_tasks', 'Tuntaskan Semua Tugas')}</button>
        <button type="button" onClick={() => run('pet_level_up')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_pet_level_up', 'Pet +1 Level')}</button>
        <input type="number" value={petExp} onChange={(e) => setPetExp(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('pet_add_exp', petExp)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_pet_add_exp', 'Pet + EXP')}</button>
        <button type="button" onClick={() => run('pet_feed')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{t('admin_pet_feed', 'Beri Makan Semua Pet')}</button>
      </div>
      <p className="text-[11px] text-rose-300/80">{t('admin_warning', 'Alat debug — mengubah data game Anda. Gunakan untuk keperluan pengujian.')}</p>
    </div>
  );
};

interface ThemeRow { key: string; label: string; primary: string; glow: string; }

export const SettingsView: React.FC = () => {
  const { user, soundEnabled, setSoundEnabled, lang, setLang, resetAllData, showToast, today, activeTheme, setActiveTheme } = useGame();

  const [cloud, setCloud] = useState<CloudStatus | null>(null);
  const [cloudBusy, setCloudBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [devices, setDevices] = useState<CloudDevice[]>([]);
  const [showDevices, setShowDevices] = useState(false);

  // Parity SettingsPage state: theme, currency, font scale, high contrast
  const [themes, setThemes] = useState<ThemeRow[]>([]);

  const [currency, setCurrency] = useState(String(user.currency || 'IDR'));
  const [fontScale, setFontScale] = useState(Number(user.fontScale || 100));
  const [highContrast, setHighContrast] = useState(Boolean((user as any).highContrast));
  const [dbPath, setDbPath] = useState('');
  const [appVersion, setAppVersion] = useState('');

  const isAdmin = Boolean((user as any).isAdmin);

  const loadCloud = async () => {
    try {
      const st = await cloudStatus();
      setCloud(st);
    } catch {
      setCloud({ ok: false, configured: false });
    }
  };

  useEffect(() => {
    loadCloud();
    // Katalog tema (parity SettingsPage theme radios dari db.THEMES)
    apiGet<any>('/api/catalog/themes')
      .then((d) => setThemes(d.themes || []))
      .catch(() => setThemes([]));
    // Versi app + path DB (parity update_version + settings_db_path)
    apiGet<any>('/api/version')
      .then((d) => {
        setAppVersion(String(d?.version || ''));
        setDbPath(String(d?.dbPath || ''));
      })
      .catch(() => undefined);
  }, []);

  /** Parity: perubahan setting tertentu butuh restart (web = reload). */
  const confirmRestart = () => {
    if (window.confirm(t('settings_change_restart_msg', 'Perubahan ini membutuhkan muat ulang agar diterapkan sepenuhnya. Muat ulang sekarang?'))) {
      window.location.reload();
    }
  };

  const changeLanguage = (l: 'id' | 'en') => {
    setLang(l);
    apiPost('/api/settings', { language: l })
      .then(() => {
        if (window.confirm(
          t('settings_language_restart_msg', 'Bahasa telah diganti. Muat ulang sekarang untuk menerapkan sepenuhnya?'),
        )) {
          window.location.reload();
        }
      })
      .catch(() => undefined);
  };

  const handleExportData = async () => {
    if (isAdmin) {
      // Parity: admin diblokir dari ekspor/impor (admin_export_blocked)
      showToast('info', t('admin_export_blocked', 'Ekspor dinonaktifkan untuk akun admin.'), '');
      return;
    }
    try {
      const res = await apiGet<any>('/api/tracker/export');
      const payload = res?.tracker ?? res;
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `craftlife_tracker_${today}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('success', t('export_success', 'Data tracker diekspor!'), '');
    } catch (err: any) {
      showToast('info', t('export_failed', 'Ekspor gagal: {error}').replace('{error}', String(err?.message || err)), '');
    }
  };

  const handleImportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (isAdmin) {
      showToast('info', t('admin_import_blocked', 'Impor dinonaktifkan untuk akun admin.'), '');
      e.target.value = '';
      return;
    }
    if (!window.confirm(t('import_confirm_warning', 'Semua data tracker saat ini akan DIGANTI. Data akun tetap aman. Lanjutkan?'))) {
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        const res = await apiPost<any>('/api/tracker/import', { tracker: parsed.tracker || parsed });
        if (res?.ok === false) throw new Error(res.error || 'import');
        showToast('success', t('import_success', 'Data tracker diimpor!'), '');
        window.location.reload();
      } catch (err: any) {
        showToast('info', t('import_failed', 'Impor gagal: {error}').replace('{error}', String(err?.message || err)), '');
      }
    };
    reader.readAsText(file);
  };

  /** Parity _manual_backup → db.backup_database() */
  const handleBackupNow = async () => {
    try {
      const res = await apiPost<any>('/api/settings/backup', {});
      if (res?.ok === false) throw new Error(res.error || 'backup');
      showToast('success', t('berhasil_title', 'Berhasil'), String(res?.path || ''));
    } catch (err: any) {
      showToast('info', t('msg_error', 'Error'), String(err?.message || err));
    }
  };

  /** Parity update group → /api/update/check */
  const handleCheckUpdate = async () => {
    try {
      const res = await apiGet<any>('/api/update/check');
      if (res?.update) {
        const ver = res.update.version || res.update.latest || '';
        showToast('success', t('update_available', 'Update tersedia: v{version}').replace('{version}', String(ver)), '');
      } else {
        showToast('success', t('update_latest', 'Kamu sudah di versi terbaru.'), '');
      }
    } catch {
      showToast('info', t('update_check_offline', 'Tidak bisa memeriksa update.'), '');
    }
  };

  const switchLocalAccount = () => {
    try {
      sessionStorage.setItem('craftlife_show_login', '1');
    } catch {
      /* ignore */
    }
    window.location.reload();
  };

  /** Parity Reset Progress: password verify → dialog ketik "RESET PROGRESS" → reset → toast sukses → reload */
  const handleResetProgress = async () => {
    const pwd = window.prompt(
      `${t('reset_verify_password_title', 'Verifikasi Password')}\n${t('reset_verify_password_prompt', 'Masukkan password akun kamu untuk melanjutkan:')}`,
    );
    if (!pwd) return;

    const typed = window.prompt(
      `${t('reset_confirm_title', 'Konfirmasi Reset Progress')}\n\n` +
      `${t('reset_confirm_warning', 'PERINGATAN: Seluruh progress tracker akan DIHAPUS!')}\n` +
      `${t('reset_confirm_type_label', 'Ketik "RESET PROGRESS" untuk konfirmasi:')}`,
    );
    if (typed === null) return;
    if (typed.trim().toUpperCase() !== 'RESET PROGRESS') {
      showToast('info', t('reset_confirm_invalid', 'Konfirmasi tidak cocok. Reset dibatalkan.'), '');
      return;
    }
    const ok = await resetAllData(pwd);
    if (ok) {
      toastResetSuccess();
    }
  };

  const toastResetSuccess = () => {
    showToast('success', t('reset_success_title', 'Berhasil'), t('reset_success_msg', 'Progress berhasil direset.'));
  };

  const runCloud = async (fn: () => Promise<any>, okMsg?: string) => {
    setCloudBusy(true);
    try {
      const result = await fn();
      if (result?.status) setCloud(result.status);
      else await loadCloud();
      if (result?.ok === false) {
        showToast('info', t('cloud_error', 'Cloud error').replace('{error}', String(result.error || result.code || 'error')), '');
      } else if (okMsg) {
        showToast('success', okMsg, '');
      }
      return result;
    } catch (err: any) {
      showToast('info', String(err?.message || err), '');
    } finally {
      setCloudBusy(false);
    }
  };

  const conflict = cloud?.personal?.conflict_status === 'needs_resolution';
  const linked = Boolean(cloud?.linked && cloud?.configured);
  const pending = (cloud?.queue?.pending || 0) + (cloud?.queue?.retry || 0);

  let statusText = t('cloud_status_not_configured', 'Supabase belum dikonfigurasi.');
  if (cloud && !cloud.configured) {
    statusText = t('cloud_off_hint', 'Cloud mati: tidak ada .env di samping aplikasi.');
  } else if (cloud?.configured && linked) {
    const last = cloud.link?.last_sync_at || t('cloud_never', 'belum pernah');
    statusText = t('cloud_status_linked', `Linked: ${cloud.email} · queue ${pending} · last sync ${last}`)
      .replace('{email}', cloud.email || '')
      .replace('{pending}', String(pending))
      .replace('{last}', String(last));
  } else if (cloud?.configured) {
    statusText = t('cloud_status_ready_unlinked', 'Supabase siap. Hubungkan akun lokal ini dengan email cloud.');
  }

  return (
    <div className="space-y-6 w-full mx-auto max-w-4xl">
      <div>
        <div className="flex items-center gap-2">
          <Settings className="w-6 h-6 text-slate-400" />
          <h2 className="text-xl font-black text-slate-100">{t('settings_title', 'Pengaturan')}</h2>
        </div>
      </div>

      {/* ===== Akun lokal (custom web) ===== */}
      <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-3">
        <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
          <User className="w-4 h-4 text-emerald-400" />
          <span>{t('web_local_account', 'Local game account')}</span>
        </h3>
        <p className="text-xs text-slate-400">
          {user.name} · @{String((user as any).username || '')} · Lv {user.level}
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={switchLocalAccount}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs font-bold text-slate-200"
          >
            {t('web_switch_local', 'Ganti akun lokal')}
          </button>
        </div>
      </div>

      {/* ===== Cloud & Sync (sudah ada, dipertahankan) ===== */}
      <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4">
        <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
          <Cloud className="w-4 h-4 text-sky-400" />
          <span>{t('cloud_group', 'Cloud & Sync')}</span>
        </h3>
        <p className="text-xs text-slate-400 whitespace-pre-wrap">{statusText}</p>
        {cloud?.configured && cloud.realtime_connected && (
          <p className="text-[11px] text-emerald-400">{t('cloud_realtime_on', 'Realtime aktif')}</p>
        )}
        {conflict && (
          <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-3 space-y-2">
            <p className="text-xs text-amber-200">{t('cloud_conflict_hint', 'Data tracker berubah di perangkat ini dan perangkat lain. Pilih sumber yang ingin dipertahankan.')}</p>
            <div className="flex flex-wrap gap-2">
              <button disabled={cloudBusy} onClick={() => { if (window.confirm(t('cloud_conflict_keep_local_confirm', 'Keep local?'))) runCloud(() => cloudConflict('local'), t('cloud_conflict_resolved', 'Conflict resolved')); }} className="px-3 py-2 rounded-xl bg-yellow-500 text-slate-950 text-xs font-black">
                {t('cloud_conflict_keep_local', 'Pertahankan Data Lokal')}
              </button>
              <button disabled={cloudBusy} onClick={() => { if (window.confirm(t('cloud_conflict_use_remote_confirm', 'Restore cloud?'))) runCloud(() => cloudConflict('cloud'), t('cloud_conflict_resolved', 'Conflict resolved')); }} className="px-3 py-2 rounded-xl bg-rose-500/80 text-white text-xs font-black">
                {t('cloud_conflict_use_remote', 'Pulihkan Data Cloud')}
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t('cloud_email', 'Cloud email')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t('cloud_password', 'Password cloud (min. 8)')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs" />
        </div>

        <div className="flex flex-wrap gap-2">
          <button disabled={cloudBusy || linked} onClick={() => runCloud(() => cloudRegister(email, password), t('cloud_verification_sent', 'Cek inbox untuk verifikasi email.'))} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs font-bold text-slate-200 disabled:opacity-40">
            {t('cloud_create_account', 'Buat Akun Cloud')}
          </button>
          <button disabled={cloudBusy || linked} onClick={() => runCloud(() => cloudLogin(email, password), t('cloud_account_created', 'Akun terhubung.'))} className="px-3 py-2 rounded-xl bg-sky-500 text-slate-950 text-xs font-black disabled:opacity-40">
            {t('cloud_signin_link', 'Sign In & Link')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => runCloud(() => cloudSyncNow(), t('cloud_sync_success', 'Cloud sync selesai.'))} className="px-3 py-2 rounded-xl bg-yellow-500 disabled:opacity-40 text-slate-950 text-xs font-black inline-flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> {t('cloud_sync_now', 'Sync Sekarang')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => { if (window.confirm(t('cloud_migrate_local', 'Antrikan data lokal ke cloud?'))) runCloud(() => cloudMigrateLocal()); }} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 disabled:opacity-40 text-xs font-bold text-slate-200">
            {t('cloud_migrate_local', 'Migrasikan Data Lokal')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={async () => {
            setShowDevices(true);
            try {
              const d = await cloudDevices();
              setDevices(d.devices || []);
              if (d.register_error) showToast('info', d.register_error, '');
            } catch (e: any) {
              showToast('info', String(e?.message || e), '');
            }
          }} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 disabled:opacity-40 text-xs font-bold text-slate-200 inline-flex items-center gap-1">
            <Smartphone className="w-3 h-3" /> {t('cloud_devices_title', 'Kelola Perangkat')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => runCloud(() => cloudQueueRetry())} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 disabled:opacity-40 text-xs font-bold text-slate-200">
            {t('cloud_queue_retry', 'Coba Lagi')}
          </button>
          <button disabled={cloudBusy || !cloud?.linked} onClick={() => runCloud(() => cloudLogout())} className="px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-bold inline-flex items-center gap-1">
            <LogOut className="w-3 h-3" /> {t('cloud_sign_out', 'Sign Out Cloud')}
          </button>
        </div>

        {showDevices && (
          <div className="rounded-2xl bg-slate-950 border border-slate-800 p-3 space-y-2">
            <p className="text-[11px] text-slate-500">{t('cloud_devices_info', 'UUID perangkat bukan credential.')}</p>
            {(devices.length ? devices : []).map((d) => (
              <div key={d.id} className="flex items-center justify-between gap-2 text-xs text-slate-300">
                <span>{d.current ? '★ ' : ''}{d.device_name || d.id} · {d.platform} · {d.revoked_at ? t('cloud_device_revoked', 'revoked') : t('cloud_device_active', 'active')}</span>
                {!d.current && !d.revoked_at && (
                  <button className="text-rose-400" onClick={async () => {
                    try {
                      await cloudRevokeDevice(d.id);
                      const next = await cloudDevices();
                      setDevices(next.devices || []);
                    } catch (e: any) {
                      showToast('info', String(e?.message || e), '');
                    }
                  }}>{t('cloud_device_revoke', 'Revoke')}</button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ===== Parity SettingsPage: THEME group — radio semua db.THEMES + glow preview dot ===== */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
        <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
          <Palette className="w-4 h-4 text-fuchsia-400" /> {t('settings_theme', 'Tema')}
        </span>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {themes.map((th) => {
            const active = activeTheme === th.key;
            return (
              <button
                type="button"
                key={th.key}
                onClick={() => {
                  if (active) return;
                  // Parity SettingsPage theme radios: terapkan + persist via GameContext
                  // (yang juga mengaplikasikan CSS vars — bukan theme dummy).
                  setActiveTheme(th.key);
                  showToast('success', t('settings_theme_changed', 'Tema diganti: {name}').replace('{name}', th.label), '');
                }}
                className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-xs font-bold transition-all ${
                  active
                    ? 'bg-fuchsia-500/15 border-fuchsia-400/60 text-fuchsia-200'
                    : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700'
                }`}
              >
                <span
                  className="w-4 h-4 rounded-full shrink-0"
                  style={{
                    background: th.glow || th.primary || '#a78bfa',
                    boxShadow: `0 0 8px 2px ${th.glow || th.primary || '#a78bfa'}`,
                  }}
                />
                <span className="truncate">{th.label}</span>
              </button>
            );
          })}
          {themes.length === 0 && (
            <p className="text-[11px] text-slate-500 col-span-3">{lang === 'id' ? 'Memuat katalog tema…' : 'Loading theme catalog…'}</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* ===== Parity SettingsPage: LANGUAGE group (id/en + restart prompt) ===== */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
          <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
            <Globe className="w-4 h-4 text-sky-400" /> {t('settings_language', 'Bahasa')}
          </span>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => changeLanguage('id')}
              className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                lang === 'id'
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/50'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              🇮🇩 {t('settings_language_id', 'Bahasa Indonesia')}
            </button>
            <button
              onClick={() => changeLanguage('en')}
              className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                lang === 'en'
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/50'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              🇬🇧 {t('settings_language_en', 'English')}
            </button>
          </div>
        </div>

        {/* ===== Parity SettingsPage: SOUND group ===== */}
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
              {soundEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
              {t('settings_sound', 'Suara')}
            </span>
            <button
              onClick={() => {
                const next = !soundEnabled;
                setSoundEnabled(next);
                apiPost('/api/settings', { soundEnabled: next }).catch(() => undefined);
              }}
              className={`w-11 h-6 rounded-full transition-colors relative ${
                soundEnabled ? 'bg-emerald-500' : 'bg-slate-800'
              }`}
              aria-label={t('settings_sound_enable', 'Aktifkan suara efek')}
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-1 ${
                  soundEnabled ? 'right-1' : 'left-1'
                }`}
              />
            </button>
          </div>
          <p className="text-[11px] text-slate-400">{t('settings_sound_hint', 'Efek suara kecil untuk aksi penting (klaim, level up, dsb.)')}</p>
        </div>
      </div>

      {/* ===== Parity SettingsPage: CURRENCY combo IDR/USD/EUR ===== */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2">
        <span className="text-xs font-bold text-slate-300">{t('settings_currency', 'Mata uang')}</span>
        <select
          value={currency}
          onChange={(e) => {
            const v = e.target.value;
            apiPost('/api/settings', { currency: v }).then(() => {
              setCurrency(v);
              confirmRestart();
            }).catch(() => undefined);
          }}
          className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs"
        >
          {['IDR', 'USD', 'EUR'].map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {/* ===== Parity SettingsPage: A11Y group (font scale combo + high contrast + hint) ===== */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
        <span className="text-xs font-bold text-slate-300">{t('a11y_group', 'Aksesibilitas')}</span>
        <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300">
          <label className="flex items-center gap-2">
            {t('a11y_font_scale', 'Skala font')}
            <select
              value={fontScale}
              onChange={(e) => {
                const v = Number(e.target.value);
                document.documentElement.style.fontSize = `${(v / 100) * 16}px`;
                apiPost('/api/settings', { fontScale: v }).then(() => {
                  setFontScale(v);
                  confirmRestart();
                }).catch(() => undefined);
              }}
              className="px-2 py-1.5 rounded-lg bg-slate-800 border border-slate-700"
            >
              {[80, 90, 100, 110, 120, 130, 140].map((v) => (
                <option key={v} value={v}>{v}%</option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2">
            {t('a11y_high_contrast', 'Kontras tinggi')}
            <input
              type="checkbox"
              checked={highContrast}
              onChange={(e) => {
                const v = e.target.checked;
                document.documentElement.classList.toggle('high-contrast', v);
                apiPost('/api/settings', { highContrast: v }).then(() => setHighContrast(v)).catch(() => undefined);
              }}
            />
          </label>
        </div>
        <p className="text-[11px] text-slate-500">{t('a11y_font_apply_hint', 'Perubahan skala font diterapkan setelah muat ulang.')}</p>
      </div>

      {/* ===== Parity SettingsPage: ADMIN panel (is_admin gated) ===== */}
      {isAdmin && <AdminDebugPanel />}

      {/* ===== Parity SettingsPage: DATA MANAGEMENT (export/import + backup) ===== */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <h3 className="font-bold text-xs text-slate-300 uppercase tracking-wider">{t('settings_data_management', 'Manajemen Data')}</h3>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleExportData}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 flex items-center justify-center gap-2 transition-colors"
          >
            <Download className="w-4 h-4 text-sky-400" />
            <span>{t('settings_export_tracker', 'Ekspor Tracker (JSON)')}</span>
          </button>

          <label className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 flex items-center justify-center gap-2 cursor-pointer transition-colors">
            <Upload className="w-4 h-4 text-emerald-400" />
            <span>{t('settings_import_tracker', 'Impor Tracker (JSON)')}</span>
            <input type="file" accept=".json" onChange={handleImportData} className="hidden" />
          </label>

          {/* Parity _manual_backup: tombol Backup Sekarang → db.backup_database() di server */}
          <button
            onClick={handleBackupNow}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 flex items-center justify-center gap-2 transition-colors"
          >
            <RefreshCcw className="w-4 h-4 text-amber-400" />
            <span>{t('settings_backup_now', 'Backup Sekarang')}</span>
          </button>

          {/* Parity Reset Progress */}
          <button
            onClick={handleResetProgress}
            className="w-full sm:w-auto sm:ml-auto px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 font-bold text-xs border border-rose-500/30 flex items-center justify-center gap-2 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span>{t('settings_reset_btn', 'Reset Progress')}</span>
          </button>
        </div>
        <p className="text-[11px] text-rose-300/70">{t('settings_reset_warning', 'Reset menghapus SEMUA progress tracker (tidak bisa dibatalkan).')}</p>
      </div>

      {/* ===== Parity SettingsPage: UPDATE + DATABASE group ===== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2">
          <span className="text-xs font-bold text-slate-300">{t('update_group_title', 'Pembaruan Aplikasi')}</span>
          <p className="text-[11px] text-slate-400">
            {t('update_version', 'Versi: {version}').replace('{version}', appVersion || '…')}
          </p>
          <button
            type="button"
            onClick={handleCheckUpdate}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
          >
            {t('update_check', 'Cek Pembaruan')}
          </button>
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2">
          <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
            <Database className="w-4 h-4 text-amber-400" /> {t('settings_database', 'Database')}
          </span>
          <p className="text-[11px] text-slate-500 break-all font-mono">
            {t('settings_db_path', 'Lokasi database lokal:')} {dbPath || '…'}
          </p>
          <button
            type="button"
            onClick={handleBackupNow}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-bold text-slate-200"
          >
            {t('settings_backup_now', 'Backup Sekarang')}
          </button>
        </div>
      </div>
    </div>
  );
};
