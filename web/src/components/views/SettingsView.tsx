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
import { Settings, User, Volume2, VolumeX, Globe, Download, Upload, Trash2, Check, Cloud, RefreshCw, LogOut, Smartphone } from 'lucide-react';

const AdminDebugPanel: React.FC<{ lang: string }> = ({ lang }) => {
  const [xp, setXp] = useState(1000);
  const [gold, setGold] = useState(500);
  const [petExp, setPetExp] = useState(100);
  const run = (action: string, amount?: number) => {
    apiPost('/api/admin/debug', { action, amount }).then(() => window.location.reload()).catch(() => undefined);
  };
  return (
    <div className="rounded-2xl bg-slate-900 border border-rose-800/40 p-5 space-y-3">
      <h3 className="font-bold text-xs text-rose-300 uppercase">{lang === 'id' ? 'Panel admin' : 'Admin debug'}</h3>
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <input type="number" value={xp} onChange={(e) => setXp(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('xp', xp)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">+XP</button>
        <input type="number" value={gold} onChange={(e) => setGold(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('gold', gold)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">+Gold</button>
        <button type="button" onClick={() => run('fill')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">HP/MP</button>
        <button type="button" onClick={() => run('maxLevel')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">Lv50</button>
        <button type="button" onClick={() => run('completeTasks')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{lang === 'id' ? 'Selesai tugas' : 'Complete tasks'}</button>
        <button type="button" onClick={() => run('petLevel')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">Pet +1</button>
        <input type="number" value={petExp} onChange={(e) => setPetExp(Number(e.target.value))} className="w-24 px-2 py-1 rounded-lg bg-slate-800 border border-slate-700" />
        <button type="button" onClick={() => run('petExp', petExp)} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">Pet EXP</button>
        <button type="button" onClick={() => run('feedPets')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 font-bold">{lang === 'id' ? 'Feed pets' : 'Feed pets'}</button>
      </div>
    </div>
  );
};

export const SettingsView: React.FC = () => {
  const { user, updateUserProfile, soundEnabled, setSoundEnabled, lang, setLang, resetAllData, showToast } = useGame();

  const [name, setName] = useState(user.name);
  const [avatar, setAvatar] = useState(user.avatar);
  const [heroClass, setHeroClass] = useState(user.heroClass);
  const [bio, setBio] = useState(user.bio || '');
  const [isSaved, setIsSaved] = useState(false);

  const [cloud, setCloud] = useState<CloudStatus | null>(null);
  const [cloudBusy, setCloudBusy] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [devices, setDevices] = useState<CloudDevice[]>([]);
  const [showDevices, setShowDevices] = useState(false);

  const AVATAR_OPTIONS = ['🧙‍♂️', '🧝‍♀️', '⚔️', '🛡️', '🏹', '🥷', '🧙‍♀️', '👑', '🐉', '🐺', '🦊', '🦅'];
  const CLASS_OPTIONS = [
    { id: 'warrior', label: 'Warrior (Pejuang)', bonus: '+HP / armor' },
    { id: 'mage', label: 'Mage (Penyihir)', bonus: '+MP / skill' },
    { id: 'rogue', label: 'Rogue (Pencuri)', bonus: '+gold / crit' },
    { id: 'paladin', label: 'Paladin', bonus: 'tank / shield' },
    { id: 'ranger', label: 'Ranger (Archer)', bonus: 'ranged / pet' },
    { id: 'healer', label: 'Healer (Penyembuh)', bonus: '+HP recovery' },
  ];

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
  }, []);

  const handleSaveProfile = (e: React.FormEvent) => {
    e.preventDefault();
    updateUserProfile({
      name,
      avatar,
      heroClass,
      bio,
    });
    apiPost('/api/settings', { displayName: name, avatar, heroClass, bio }).catch(() => undefined);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleExportData = async () => {
    try {
      const res = await apiGet<any>('/api/tracker/export');
      const payload = res?.tracker ?? res;
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `craftlife_tracker_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast('success', t('export_success', 'Tracker data exported successfully!'), '');
    } catch (err: any) {
      showToast('info', t('export_failed', 'Export failed: {error}').replace('{error}', String(err?.message || err)), '');
    }
  };

  const handleImportData = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!window.confirm(t('import_confirm_warning', lang === 'id'
      ? 'Semua data tracker saat ini akan DIGANTI. Data akun tetap aman. Lanjutkan?'
      : 'All current tracker data will be REPLACED. Account data remains safe. Continue?'))) {
      e.target.value = '';
      return;
    }
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        const res = await apiPost<any>('/api/tracker/import', { tracker: parsed.tracker || parsed });
        if (res?.ok === false) throw new Error(res.error || 'import');
        showToast('success', t('import_success', 'Tracker data imported successfully!'), '');
        window.location.reload();
      } catch (err: any) {
        showToast('info', t('import_failed', 'Import failed: {error}').replace('{error}', String(err?.message || err)), '');
      }
    };
    reader.readAsText(file);
  };

  const handleCheckUpdate = async () => {
    try {
      const res = await apiGet<any>('/api/update/check');
      if (res?.update) {
        const ver = res.update.version || res.update.latest || '';
        showToast('success', t('update_available', 'Update available: v{version}').replace('{version}', String(ver)), '');
      } else {
        showToast('success', t('update_latest', 'You are on the latest version.'), '');
      }
    } catch (err: any) {
      showToast('info', t('update_check_offline', 'Could not check for updates.'), '');
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

  let statusText = t('cloud_status_not_configured', lang === 'id'
    ? 'Supabase belum dikonfigurasi. Isi SUPABASE_URL dan SUPABASE_PUBLISHABLE_KEY pada file .env lokal.'
    : 'Supabase is not configured. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in the local .env file.');
  if (cloud && !cloud.configured) {
    statusText = t('cloud_off_hint', lang === 'id'
      ? 'Cloud mati: tidak ada .env (SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY) di samping aplikasi. Fitur lokal tetap jalan.'
      : 'Cloud is off: no .env (SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY) beside the app. Local features still work.');
  } else if (cloud?.configured && linked) {
    const last = cloud.link?.last_sync_at || t('cloud_never', lang === 'id' ? 'belum pernah' : 'never');
    statusText = t('cloud_status_linked', `Linked: ${cloud.email} · queue ${pending} · last sync ${last}`)
      .replace('{email}', cloud.email || '')
      .replace('{pending}', String(pending))
      .replace('{last}', String(last));
  } else if (cloud?.configured) {
    statusText = t('cloud_status_ready_unlinked', lang === 'id'
      ? 'Supabase siap. Hubungkan akun lokal ini dengan email cloud yang sudah diverifikasi.'
      : 'Supabase is ready. Link this local account to a verified cloud email.');
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <div className="flex items-center gap-2">
          <Settings className="w-6 h-6 text-slate-400" />
          <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Pengaturan & Profil Hero' : 'Settings & Hero Profile'}</h2>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          {lang === 'id'
            ? 'Kustomisasi identitas karakter, preferensi suara, bahasa aplikasi, dan cadangkan data kemajuanmu.'
            : 'Customize your hero persona, class specializations, sound effects, language, and data backups.'}
        </p>
      </div>

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
            {t('web_switch_local', lang === 'id' ? 'Ganti akun lokal' : 'Switch local account')}
          </button>
          <button
            type="button"
            onClick={handleCheckUpdate}
            className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs font-bold text-slate-200"
          >
            {t('web_check_update', lang === 'id' ? 'Cek pembaruan' : 'Check for updates')}
          </button>
        </div>
      </div>

      <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4">
        <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
          <Cloud className="w-4 h-4 text-sky-400" />
          <span>{t('cloud_group', 'Cloud & Sync')}</span>
        </h3>
        <p className="text-xs text-slate-400 whitespace-pre-wrap">{statusText}</p>
        {cloud?.configured && cloud.realtime_connected && (
          <p className="text-[11px] text-emerald-400">{t('cloud_realtime_on', lang === 'id' ? 'Realtime aktif' : 'Realtime connected')}</p>
        )}
        {conflict && (
          <div className="rounded-2xl border border-amber-500/40 bg-amber-500/10 p-3 space-y-2">
            <p className="text-xs text-amber-200">{t('cloud_conflict_hint', lang === 'id'
              ? 'Data tracker berubah di perangkat ini dan perangkat lain. Pilih sumber yang ingin dipertahankan.'
              : 'Tracker data changed on this device and another device. Choose which source to keep.')}</p>
            <div className="flex flex-wrap gap-2">
              <button disabled={cloudBusy} onClick={() => { if (window.confirm(t('cloud_conflict_keep_local_confirm', 'Keep local?'))) runCloud(() => cloudConflict('local'), t('cloud_conflict_resolved', 'Conflict resolved')); }} className="px-3 py-2 rounded-xl bg-yellow-500 text-slate-950 text-xs font-black">
                {t('cloud_conflict_keep_local', lang === 'id' ? 'Pertahankan Data Lokal' : 'Keep Local Data')}
              </button>
              <button disabled={cloudBusy} onClick={() => { if (window.confirm(t('cloud_conflict_use_remote_confirm', 'Restore cloud?'))) runCloud(() => cloudConflict('cloud'), t('cloud_conflict_resolved', 'Conflict resolved')); }} className="px-3 py-2 rounded-xl bg-rose-500/80 text-white text-xs font-black">
                {t('cloud_conflict_use_remote', lang === 'id' ? 'Pulihkan Data Cloud' : 'Restore Cloud Data')}
              </button>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={t('cloud_email', 'Cloud email')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs" />
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={t('cloud_password', lang === 'id' ? 'Password cloud (min. 8)' : 'Cloud password (min. 8)')} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 text-xs" />
        </div>

        <div className="flex flex-wrap gap-2">
          <button disabled={cloudBusy || linked} onClick={() => runCloud(() => cloudRegister(email, password), t('cloud_verification_sent', lang === 'id' ? 'Cek inbox untuk verifikasi email.' : 'Check your inbox to verify email.'))} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs font-bold text-slate-200 disabled:opacity-40">
            {t('cloud_create_account', lang === 'id' ? 'Buat Akun Cloud' : 'Create Cloud Account')}
          </button>
          <button disabled={cloudBusy || linked} onClick={() => runCloud(() => cloudLogin(email, password), t('cloud_account_created', lang === 'id' ? 'Akun terhubung.' : 'Account linked.'))} className="px-3 py-2 rounded-xl bg-sky-500 text-slate-950 text-xs font-black disabled:opacity-40">
            {t('cloud_signin_link', 'Sign In & Link')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => runCloud(() => cloudSyncNow(), t('cloud_sync_success', lang === 'id' ? 'Cloud sync selesai.' : 'Cloud sync complete.'))} className="px-3 py-2 rounded-xl bg-yellow-500 disabled:opacity-40 text-slate-950 text-xs font-black inline-flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> {t('cloud_sync_now', lang === 'id' ? 'Sync Sekarang' : 'Sync Now')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => { if (window.confirm(t('cloud_migrate_local', lang === 'id' ? 'Antrikan data lokal ke cloud?' : 'Queue local data to cloud?'))) runCloud(() => cloudMigrateLocal()); }} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 disabled:opacity-40 text-xs font-bold text-slate-200">
            {t('cloud_migrate_local', lang === 'id' ? 'Migrasikan Data Lokal' : 'Migrate Local Data')}
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
            <Smartphone className="w-3 h-3" /> {t('cloud_devices_title', lang === 'id' ? 'Kelola Perangkat' : 'Manage Devices')}
          </button>
          <button disabled={cloudBusy || !linked} onClick={() => runCloud(() => cloudQueueRetry())} className="px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 disabled:opacity-40 text-xs font-bold text-slate-200">
            {t('cloud_queue_retry', lang === 'id' ? 'Coba Lagi' : 'Retry')}
          </button>
          <button disabled={cloudBusy || !cloud?.linked} onClick={() => runCloud(() => cloudLogout())} className="px-3 py-2 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-bold inline-flex items-center gap-1">
            <LogOut className="w-3 h-3" /> {t('cloud_sign_out', 'Sign Out Cloud')}
          </button>
        </div>

        {showDevices && (
          <div className="rounded-2xl bg-slate-950 border border-slate-800 p-3 space-y-2">
            <p className="text-[11px] text-slate-500">{t('cloud_devices_info', lang === 'id' ? 'UUID perangkat bukan credential.' : 'A device UUID is not a credential.')}</p>
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

      <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-6">
        <h3 className="font-bold text-sm text-slate-200 flex items-center gap-2">
          <User className="w-4 h-4 text-yellow-400" />
          <span>{lang === 'id' ? 'Kustomisasi Karakter & Kelas' : 'Hero Customization & Class'}</span>
        </h3>

        <form onSubmit={handleSaveProfile} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-semibold mb-2">{lang === 'id' ? 'Pilih Avatar Karakter' : 'Hero Avatar'}</label>
            <div className="flex items-center gap-2 flex-wrap">
              {AVATAR_OPTIONS.map((av) => (
                <button
                  key={av}
                  type="button"
                  onClick={() => setAvatar(av)}
                  className={`w-11 h-11 rounded-2xl text-2xl flex items-center justify-center transition-all ${
                    avatar === av
                      ? 'bg-yellow-500/20 border-2 border-yellow-400 scale-105 shadow-md shadow-yellow-500/20'
                      : 'bg-slate-800 border border-slate-700 hover:bg-slate-700'
                  }`}
                >
                  {av}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Nama Pahlawan' : 'Hero Name'}</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-yellow-500"
              />
            </div>

            <div>
              <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Kelas Karakter' : 'Hero Class'}</label>
              <select
                value={heroClass}
                onChange={(e) => setHeroClass(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-yellow-500"
              >
                {CLASS_OPTIONS.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label} - {c.bonus}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Motto & Bio Pahlawan' : 'Hero Bio & Motto'}</label>
            <input
              type="text"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              placeholder="e.g. Master of habits, conqueror of procrastination."
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-yellow-500"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            {isSaved ? (
              <span className="text-emerald-400 font-bold text-xs flex items-center gap-1">
                <Check className="w-4 h-4" /> {lang === 'id' ? 'Profil tersimpan!' : 'Profile updated!'}
              </span>
            ) : <div />}

            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-black text-xs shadow-lg shadow-yellow-500/20 active:scale-95 transition-all"
            >
              {lang === 'id' ? 'Simpan Perubahan' : 'Save Profile'}
            </button>
          </div>
        </form>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
              <Globe className="w-4 h-4 text-sky-400" /> {lang === 'id' ? 'Bahasa Aplikasi' : 'Language'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => { setLang('id'); apiPost('/api/settings', { language: 'id' }).catch(() => undefined); }}
              className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                lang === 'id'
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/50'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              🇮🇩 Bahasa Indonesia
            </button>
            <button
              onClick={() => { setLang('en'); apiPost('/api/settings', { language: 'en' }).catch(() => undefined); }}
              className={`py-2 rounded-xl text-xs font-bold border transition-all ${
                lang === 'en'
                  ? 'bg-sky-500/20 text-sky-300 border-sky-500/50'
                  : 'bg-slate-800 text-slate-400 border-slate-700'
              }`}
            >
              🇬🇧 English
            </button>
          </div>
        </div>

        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-300 flex items-center gap-2">
              {soundEnabled ? <Volume2 className="w-4 h-4 text-emerald-400" /> : <VolumeX className="w-4 h-4 text-slate-500" />}
              {lang === 'id' ? 'Efek Suara Gamifikasi' : 'Sound Effects'}
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
            >
              <div
                className={`w-4 h-4 rounded-full bg-white transition-transform absolute top-1 ${
                  soundEnabled ? 'right-1' : 'left-1'
                }`}
              />
            </button>
          </div>

          <p className="text-[11px] text-slate-400">
            {lang === 'id'
              ? 'Memainkan audio synthesizer saat menuntaskan habit, level up, dan pertarungan boss.'
              : 'Web Audio synth chimes on completing tasks, leveling up, and winning battles.'}
          </p>
          <label className="flex items-center justify-between text-xs text-slate-300 pt-2">
            <span>{lang === 'id' ? 'Kontras tinggi' : 'High contrast'}</span>
            <input
              type="checkbox"
              defaultChecked={Boolean((user as any).highContrast)}
              onChange={(e) => {
                document.documentElement.classList.toggle('high-contrast', e.target.checked);
                apiPost('/api/settings', { highContrast: e.target.checked }).catch(() => undefined);
              }}
            />
          </label>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2">
          <span className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Mata uang (EconomyPage)' : 'Currency (EconomyPage)'}</span>
          <select
            defaultValue={user.currency || 'IDR'}
            onChange={(e) => {
              apiPost('/api/settings', { currency: e.target.value }).catch(() => undefined);
              showToast('success', e.target.value, '');
            }}
            className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-xs"
          >
            {['IDR', 'USD', 'EUR', 'SGD', 'JPY'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-2">
          <span className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Skala font' : 'Font scale'}</span>
          <input
            type="range"
            min={80}
            max={140}
            defaultValue={user.fontScale || 100}
            onChange={(e) => {
              const v = Number(e.target.value);
              document.documentElement.style.fontSize = `${(v / 100) * 16}px`;
              apiPost('/api/settings', { fontScale: v }).catch(() => undefined);
            }}
            className="w-full"
          />
        </div>
      </div>

      {(user as any).isAdmin && (
        <AdminDebugPanel lang={lang} />
      )}

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-5 space-y-4">
        <h3 className="font-bold text-xs text-slate-300 uppercase tracking-wider">{lang === 'id' ? 'Penyimpanan & Cadangan Data' : 'Backup & Storage Management'}</h3>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <button
            onClick={handleExportData}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 flex items-center justify-center gap-2 transition-colors"
          >
            <Download className="w-4 h-4 text-sky-400" />
            <span>{t('web_tracker_export', lang === 'id' ? 'Ekspor tracker SQLite' : 'Export SQLite tracker')}</span>
          </button>

          <label className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-bold text-xs border border-slate-700 flex items-center justify-center gap-2 cursor-pointer transition-colors">
            <Upload className="w-4 h-4 text-emerald-400" />
            <span>{t('web_tracker_import', lang === 'id' ? 'Impor tracker SQLite' : 'Import SQLite tracker')}</span>
            <input type="file" accept=".json" onChange={handleImportData} className="hidden" />
          </label>

          <button
            onClick={() => {
              if (window.confirm(lang === 'id' ? 'Apakah Anda yakin ingin mereset seluruh data game?' : 'Are you sure you want to reset all game data?')) {
                resetAllData();
              }
            }}
            className="w-full sm:w-auto sm:ml-auto px-4 py-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 font-bold text-xs border border-rose-500/30 flex items-center justify-center gap-2 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span>{lang === 'id' ? 'Reset Semua Data' : 'Reset All Progress'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
