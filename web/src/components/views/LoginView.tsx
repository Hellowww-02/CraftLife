import React, { useEffect, useState } from 'react';
import { apiPost, apiGet } from '../../api/client';
import { t } from '../../i18n';

export const LoginView: React.FC<{ onAuthed: () => void }> = ({ onAuthed }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'reset'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [bio, setBio] = useState('');
  const [avatarClass, setAvatarClass] = useState('warrior');
  const [classes, setClasses] = useState<Record<string, { name: string; icon: string; bonus: string }>>({});
  const [backupCode, setBackupCode] = useState('');
  // P24: metode reset (parity PyQt reset dialog — security answer atau backup code)
  const [resetMethod, setResetMethod] = useState<'backup' | 'security'>('backup');
  const [secAnswer, setSecAnswer] = useState('');

  // Parity _register_tab: combobox class dari db.AVATAR_CLASSES (name + bonus).
  useEffect(() => {
    if (mode !== 'register') return;
    apiGet<any>('/api/catalog/avatar-classes')
      .then((d) => { if (d?.classes) setClasses(d.classes); })
      .catch(() => undefined);
  }, [mode]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      if (mode === 'reset') {
        // P24: kirim method + code (backup) atau answer (security) sesuai pilihan.
        const res = await apiPost<any>('/api/auth/reset', {
          username, password, method: resetMethod,
          ...(resetMethod === 'security' ? { answer: secAnswer } : { code: backupCode }),
        });
        if (!res?.ok) {
          setError(res?.error || 'reset_failed');
          return;
        }
        setMode('login');
        setError('');
        return;
      }
      const path = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
      const res = await apiPost<any>(path, { username, password, displayName, ...(mode === 'register' ? { bio, avatarClass } : {}) });
      if (!res?.ok) {
        setError(res?.error || res?.result?.msg || 'Gagal');
        return;
      }
      if (res.token) {
        try {
          sessionStorage.setItem('craftlife_token', res.token);
        } catch {
          /* ignore */
        }
      }
      onAuthed();
    } catch (err: any) {
      setError(String(err?.message || err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-xl"
      >
        <div>
          <h1 className="text-xl font-black text-emerald-300">{t('app_logo', 'CraftLife')}</h1>
          <p className="text-xs text-slate-400 mt-1">
            {mode === 'login'
              ? t('web_login_subtitle', 'Masuk ke petualanganmu')
              : t('web_register_subtitle', 'Buat akun petualang baru')}
          </p>
        </div>
        <input
          className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
          placeholder={t('web_username', 'Username')}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
        />
        {mode === 'register' && (
          <>
            <input
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
              placeholder={t('web_display_name', 'Nama tampilan')}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
            {/* Parity _register_tab: bio + combobox kelas (ikon — nama — bonus) */}
            <input
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
              placeholder={t('register_bio', 'Bio')}
              value={bio}
              onChange={(e) => setBio(e.target.value)}
            />
            <select
              className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm text-slate-100"
              value={avatarClass}
              onChange={(e) => setAvatarClass(e.target.value)}
            >
              {Object.entries(classes).length
                ? Object.entries(classes).map(([cid, c]) => (
                    <option key={cid} value={cid}>{c.icon}  {c.name}  —  {c.bonus}</option>
                  ))
                : <option value="warrior">⚔️  Warrior</option>}
            </select>
          </>
        )}
        {mode === 'reset' && (
          <>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setResetMethod('backup')}
                className={`flex-1 py-1.5 rounded-xl text-[11px] font-bold border ${
                  resetMethod === 'backup'
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-200'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                {t('reset_method_backup', 'Kode Cadangan')}
              </button>
              <button
                type="button"
                onClick={() => setResetMethod('security')}
                className={`flex-1 py-1.5 rounded-xl text-[11px] font-bold border ${
                  resetMethod === 'security'
                    ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-200'
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}
              >
                {t('reset_method_security', 'Pertanyaan Keamanan')}
              </button>
            </div>
            {resetMethod === 'backup' ? (
              <input
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
                placeholder={t('web_backup_code', 'Kode cadangan')}
                value={backupCode}
                onChange={(e) => setBackupCode(e.target.value)}
              />
            ) : (
              <input
                className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
                placeholder={t('reset_password_security_question', 'Jawaban pertanyaan keamanan')}
                value={secAnswer}
                onChange={(e) => setSecAnswer(e.target.value)}
              />
            )}
          </>
        )}
        <input
          type="password"
          className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-sm"
          placeholder={t('web_password', 'Password')}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <div className="text-xs text-rose-400">{error}</div>}
        <button
          type="submit"
          disabled={busy}
          className="w-full py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-black text-sm"
        >
          {busy
            ? t('web_connecting', 'Menghubungkan…')
            : mode === 'login'
              ? t('web_login_btn', 'Masuk')
              : t('web_register_btn', 'Daftar')}
        </button>
        {(() => {
          try {
            return sessionStorage.getItem('craftlife_show_login') === '1';
          } catch {
            return false;
          }
        })() && (
          <button
            type="button"
            className="w-full text-xs text-emerald-400 hover:text-emerald-200"
            onClick={() => {
              try {
                sessionStorage.removeItem('craftlife_show_login');
              } catch {
                /* ignore */
              }
              window.location.reload();
            }}
          >
            {t('web_stay_logged_in', 'Stay on this account')}
          </button>
        )}
        <button
          type="button"
          className="w-full text-xs text-slate-400 hover:text-slate-200"
          onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
        >
          {mode === 'login'
            ? t('web_need_account', 'Belum punya akun? Daftar')
            : t('web_have_account', 'Sudah punya akun? Masuk')}
        </button>
        {mode !== 'reset' ? (
          <button type="button" className="w-full text-xs text-amber-400" onClick={() => setMode('reset')}>
            {t('web_forgot_password', 'Lupa password? (kode cadangan)')}
          </button>
        ) : (
          <button type="button" className="w-full text-xs text-slate-400" onClick={() => setMode('login')}>
            {t('web_have_account', 'Sudah punya akun? Masuk')}
          </button>
        )}
      </form>
    </div>
  );
};
