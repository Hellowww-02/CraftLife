import React, { useEffect, useRef, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { apiGet, apiPost, apiUploadFile, apiBase } from '../../api/client';
import { life } from '../../api/life';
import { t } from '../../i18n';
import { User, Camera, Trash2 } from 'lucide-react';

/** Panel foto profil (parity _ImagePickerDialog PyQt: PNG/JPEG → server
 * normalisasi via Pillow; hapus = kembali ke avatar emoji). */
const ProfilePhotoCard: React.FC<{ lang: string; showToast: (k: any, a: string, b: string) => void }> = ({ lang, showToast }) => {
  const { user, updateUserProfile } = useGame();
  const [photoVersion, setPhotoVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const pick = () => fileRef.current?.click();
  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    e.target.value = '';
    if (!f) return;
    setBusy(true);
    try {
      const r: any = await apiUploadFile('profile_photo', f);
      if (r?.ok === false) {
        showToast('info', r?.result?.msg || r?.error || 'upload_failed', '');
        return;
      }
      updateUserProfile({ hasProfilePhoto: true });
      setPhotoVersion((v) => v + 1);
      showToast('success', t('profile_photo_change', 'Ganti Foto'), '');
    } catch (err: any) {
      showToast('info', String(err?.message || err), '');
    } finally {
      setBusy(false);
    }
  };
  const remove = async () => {
    if (!window.confirm(t('profile_photo_remove_confirm', 'Kembalikan foto profil ke avatar default?'))) return;
    setBusy(true);
    try {
      await life.removeProfilePhoto();
      updateUserProfile({ hasProfilePhoto: false });
      setPhotoVersion((v) => v + 1);
      showToast('success', t('profile_photo_remove', 'Hapus Foto'), '');
    } catch (err: any) {
      showToast('info', String(err?.message || err), '');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-3">
      <div className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Foto profil' : 'Profile photo'}</div>
      <div className="flex items-center gap-4">
        <div className="w-20 h-20 rounded-2xl bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center text-4xl shrink-0">
          {user.hasProfilePhoto ? (
            <img
              src={`${apiBase()}/api/profile/photo?v=${photoVersion}`}
              alt="profile"
              className="w-full h-full object-cover"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          ) : (
            <span>{user.avatarEmoji || '⚔️'}</span>
          )}
        </div>
        <div className="flex flex-col gap-2">
          <button type="button" disabled={busy} onClick={pick}
            className="px-3 py-2 rounded-xl bg-yellow-500 text-slate-950 text-xs font-black flex items-center gap-1.5 disabled:opacity-50">
            <Camera className="w-3.5 h-3.5" /> {t('profile_photo_change', 'Ganti Foto')}
          </button>
          <button type="button" disabled={busy || !user.hasProfilePhoto} onClick={remove}
            className="px-3 py-2 rounded-xl bg-rose-900/60 border border-rose-700/50 text-rose-200 text-xs font-black flex items-center gap-1.5 disabled:opacity-40">
            <Trash2 className="w-3.5 h-3.5" /> {t('profile_photo_remove', 'Hapus Foto')}
          </button>
        </div>
        <input ref={fileRef} type="file" accept="image/png,image/jpeg" className="hidden" onChange={onFile} />
      </div>
    </div>
  );
};

/** Panel 🎖️ Title (parity _fill_title_cb PyQt): yang terbuka bisa dipilih,
 * yang terkunci tampil sebagai hint (maks 4). */
const ProfileTitleCard: React.FC<{ lang: string; showToast: (k: any, a: string, b: string) => void }> = ({ lang, showToast }) => {
  const { user, updateUserProfile } = useGame();
  const [state, setState] = useState<any>(null);
  const [sel, setSel] = useState(user.selectedTitle || '');

  useEffect(() => {
    life.profileTitles()
      .then((d) => {
        if (d?.ok === false) return;
        setState(d);
        setSel(d?.selectedTitle ?? user.selectedTitle ?? '');
      })
      .catch(() => setState(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const titles: any[] = Array.isArray(state?.titles) ? state.titles : [];
  const unlocked = titles.filter((t0) => t0.unlocked);
  const lockedHints = titles
    .filter((t0) => !t0.unlocked)
    .map((t0) =>
      t('title_locked_hint', '🔒 {name} — butuh {target} (kamu: {current})')
        .replace('{name}', String(t0.name))
        .replace('{target}', String(t0.target))
        .replace('{current}', String(t0.current))
    )
    .slice(0, 4);

  const apply = async (key: string) => {
    setSel(key);
    try {
      const r: any = await life.selectTitle(key);
      if (r?.ok === false) {
        showToast('info', r?.error || 'title_locked', '');
        setSel(user.selectedTitle || '');
        return;
      }
      updateUserProfile({ selectedTitle: key });
      showToast('success', key || t('title_none', '(Tanpa gelar)'), '');
    } catch (err: any) {
      showToast('info', String(err?.message || err), '');
    }
  };

  return (
    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-2">
      <label className="block text-xs font-bold text-slate-300">
        {t('title_selector_label', '🎖️ Gelar Profil (tampil di leaderboard):')}
      </label>
      <select value={sel} onChange={(e) => apply(e.target.value)}
        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-sm">
        <option value="">{t('title_none', '(Tanpa gelar)')}</option>
        {unlocked.map((t0) => (
          <option key={t0.key} value={t0.key}>{t0.name}</option>
        ))}
      </select>
      {lockedHints.map((h, i) => (
        <p key={i} className="text-[10px] text-slate-500 leading-snug"
          dangerouslySetInnerHTML={{ __html: h.replace(/</g, '&lt;') }} />
      ))}
    </div>
  );
};

const TalentPanel: React.FC<{ lang: string; showToast: (k: any, a: string, b: string) => void }> = ({ lang, showToast }) => {
  const [state, setState] = useState<any>(null);
  const load = () => {
    apiGet<any>('/api/profile/talents').then((r) => setState(r.talents || r.result || r)).catch(() => undefined);
  };
  useEffect(() => { load(); }, []);
  const tiers = state?.tiers || {};
  return (
    <div className="rounded-2xl border border-amber-500/30 bg-amber-950/10 p-4 space-y-3">
      <div className="text-sm font-black text-amber-200">{lang === 'id' ? 'Pohon talent' : 'Talent tree'}</div>
      <p className="text-[11px] text-slate-400">{lang === 'id' ? 'Poin' : 'Points'}: {state?.points ?? '—'}</p>
      {[1, 2, 3].map((t) => (
        <div key={t} className="space-y-1">
          <div className="text-[10px] uppercase text-slate-500">Tier {t}</div>
          <div className="grid sm:grid-cols-2 gap-2">
            {(tiers[t] || []).map((n: any) => (
              <div key={n.key} className="rounded-xl bg-slate-950 border border-slate-800 p-2 text-xs">
                <div className="font-bold">{n.icon} {n.name}</div>
                <div className="text-slate-500">{n.desc}</div>
                {n.unlocked ? (
                  <span className="text-emerald-400 text-[10px]">OK</span>
                ) : (
                  <button
                    type="button"
                    className="mt-1 px-2 py-1 rounded bg-amber-500 text-slate-950 text-[10px] font-black"
                    onClick={() => apiPost('/api/profile/talent', { key: n.key }).then(() => { showToast('success', n.key, ''); load(); }).catch((e) => showToast('info', String(e?.message || e), ''))}
                  >
                    Unlock
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

/** Rebirth info + conditions + type-to-confirm (parity ProfilePage._rebirth). */
const RebirthCard: React.FC<{ lang: string; showToast: (k: any, a: string, b: string) => void }> = ({ lang, showToast }) => {
  const { user, rebirthCharacter, updateUserProfile } = useGame();
  const [status, setStatus] = useState<any>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');

  const load = () => {
    apiGet<any>('/api/profile/rebirth/status').then((r) => setStatus(r?.ok ? r : null)).catch(() => setStatus(null));
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    // freskan setelah rebirth (user.rebirthCount berubah)
    if (user && status && user.rebirthCount !== status.rebirthCount) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.rebirthCount]);

  const conds = status?.conditions || {};
  const rows: { key: string; lbl: string }[] = [
    { key: 'achievements', lbl: t('profile_rebirth_cond_achievements', '🏆 Achievement: {count} / {need}') },
    { key: 'level', lbl: t('profile_rebirth_cond_level', '⭐ Level: {level} / {need}') },
    { key: 'pets', lbl: t('profile_rebirth_cond_pets', '🐾 Pet: {count} / {need}') },
    { key: 'items', lbl: t('profile_rebirth_cond_items', '🎒 Item: {count} / {need}') },
  ];
  const fill = (lbl: string, c: any) =>
    lbl
      .replace('{count}', String(c?.count ?? 0))
      .replace('{need}', String(c?.need ?? 0))
      .replace('{level}', String(c?.count ?? 0));

  const doRebirth = () => {
    if (confirmText.trim().toUpperCase() !== 'REBIRTH') {
      showToast('info', t('reset_confirm_invalid', 'Teks konfirmasi tidak sesuai.'), '');
      return;
    }
    rebirthCharacter();
    setModalOpen(false);
    setConfirmText('');
  };

  return (
    <div className="rounded-2xl border border-violet-500/30 bg-violet-950/20 p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm font-black text-violet-200">
        <User className="w-4 h-4" /> {t('profile_rebirth_title', '🔄 Rebirth')}
      </div>
      <p className="text-xs text-violet-300/90">
        {t('profile_rebirth_info', 'Rebirth: {count} kali  |  Bonus XP: +{xp_bonus}%  |  Bonus Gold: +{gold_bonus}%')
          .replace('{count}', String(status?.rebirthCount ?? user.rebirthCount ?? 0))
          .replace('{xp_bonus}', String(status?.xpBonus ?? 0))
          .replace('{gold_bonus}', String(status?.goldBonus ?? 0))}
      </p>

      <div className="space-y-1 text-[11px]">
        {rows.map((r) => {
          const c = conds[r.key];
          const met = c?.met;
          return (
            <div key={r.key} className={`flex items-center gap-1.5 ${met ? 'text-emerald-400' : 'text-rose-400'}`}>
              <span>{met ? '✅' : '❌'}</span>
              <span>{fill(r.lbl, c)}</span>
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={() => { load(); setModalOpen(true); }}
        className="px-4 py-2 rounded-xl bg-violet-500 text-slate-950 text-xs font-black disabled:opacity-50"
        disabled={status ? !status.canRebirth : false}
      >
        {t('profile_rebirth_btn', '🌀 Lakukan Rebirth')}
      </button>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">{t('profile_rebirth_confirm_title', '🌀 Konfirmasi Rebirth')}</h3>
            <p className="text-sm font-bold text-rose-300">{t('profile_rebirth_confirm_warning', 'Anda yakin ingin melakukan Rebirth?')}</p>
            <p className="text-xs text-slate-400 leading-relaxed">{t('profile_rebirth_confirm_detail', 'Progres akan direset, tetapi inventory, pet, task, dan folder dipertahankan.')}</p>
            <p className="text-xs text-emerald-300">{t('profile_rebirth_confirm_benefit', '✅ +{xp}% XP  ·  +{gold}% Gold  (permanen)').replace('{xp}', '10').replace('{gold}', '5')}</p>
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-1">{t('reset_confirm_type_label', 'Ketik untuk mengonfirmasi')}</label>
              <input
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                placeholder={t('profile_rebirth_confirm_placeholder', 'REBIRTH')}
                className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-sm"
              />
            </div>
            <div className="flex items-center justify-end gap-2 pt-1">
              <button type="button" onClick={() => { setModalOpen(false); setConfirmText(''); }} className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold">
                {lang === 'id' ? 'Batal' : 'Cancel'}
              </button>
              <button type="button" onClick={doRebirth} className="px-4 py-2 rounded-xl bg-violet-500 text-slate-950 font-bold">
                {t('profile_rebirth_confirm_btn', '🌀 Rebirth')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/** Mirror ProfilePage: identitas, class, rebirth, redeem — bukan Settings. */
export const ProfileView: React.FC<{ onOpenSettings?: () => void }> = ({ onOpenSettings }) => {
  const { user, lang, inventory, userPets, habits, dailies, quests, updateUserProfile, showToast } = useGame();
  const [name, setName] = useState(user.displayName || user.name || '');
  const [bio, setBio] = useState(user.bio || '');
  const [emoji, setEmoji] = useState(user.avatarEmoji || user.avatar || '⚔️');
  const [heroClass, setHeroClass] = useState(String(user.avatarClass || user.heroClass || 'warrior').toLowerCase());
  const [code, setCode] = useState('');
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [lockPw, setLockPw] = useState('');
  const [secQ, setSecQ] = useState('1');
  const [secA, setSecA] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[] | null>(null);
  const [locked, setLocked] = useState(Boolean(user.locked));

  // Sinkronkan status lock saat user object dari snapshot berubah (mis. setelah
  // lock/unlock di tempat lain, atau pindah akun).
  useEffect(() => { setLocked(Boolean(user.locked)); }, [user.locked]);

  const save = () => {
    updateUserProfile({ displayName: name, name, bio, avatarEmoji: emoji, avatar: emoji, heroClass, avatarClass: heroClass as any });
    apiPost('/api/settings', { displayName: name, bio, avatar: emoji, heroClass }).catch(() => undefined);
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="rounded-3xl bg-slate-900 border border-slate-800 p-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-2xl bg-slate-800 text-4xl flex items-center justify-center">{emoji}</div>
          <div className="flex-1">
            <h2 className="text-xl font-black">{user.displayName || user.name}</h2>
            <p className="text-xs text-slate-400">
              @{user.username} · {heroClass} · Lv {user.level}
            </p>
          </div>
          <button type="button" onClick={onOpenSettings} className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold">
            {lang === 'id' ? 'Pengaturan' : 'Settings'}
          </button>
        </div>
        <div className="grid sm:grid-cols-2 gap-2 text-xs">
          <input value={name} onChange={(e) => setName(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800" />
          <select value={heroClass} onChange={(e) => setHeroClass(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800">
            {['warrior', 'mage', 'rogue', 'paladin', 'ranger', 'healer'].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <input value={emoji} onChange={(e) => setEmoji(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800" />
          <input value={bio} onChange={(e) => setBio(e.target.value)} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800" placeholder="bio" />
        </div>
        <button type="button" onClick={save} className="px-4 py-2 rounded-xl bg-yellow-500 text-slate-950 text-xs font-black">
          {lang === 'id' ? 'Simpan profil' : 'Save profile'}
        </button>
      </div>

      {/* P3 parity ProfilePage: foto profil (ubah/hapus, normalisasi server) */}
      <ProfilePhotoCard lang={lang} showToast={showToast} />

      {/* P3 parity ProfilePage: 🎖️ pemilihan gelar profil */}
      <ProfileTitleCard lang={lang} showToast={showToast} />

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        {[
          ['HP', `${user.hp}/${user.maxHp}`],
          ['MP', `${user.mp}/${user.maxMp}`],
          ['Gold', String(user.gold)],
          ['XP', `${user.xp}/${user.xpToNextLevel}`],
          ['Habits', String(habits.length)],
          ['Dailies', String(dailies.length)],
          ['Quests', String(quests.length)],
          ['Pets', String(userPets.length)],
          ['Sport Lv', String(user.sportLevel || 1)],
          ['Rebirth', String(user.rebirthCount || 0)],
          ['Gems', String(user.gems || 0)],
          ['Inv', String(inventory.length)],
        ].map(([k, v]) => (
          <div key={k} className="rounded-2xl bg-slate-900 border border-slate-800 p-3">
            <div className="text-[10px] uppercase text-slate-500">{k}</div>
            <div className="font-black">{v}</div>
          </div>
        ))}
      </div>

      <RebirthCard lang={lang} showToast={showToast} />

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-2">
        <div className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Warna avatar' : 'Avatar color'}</div>
        <div className="flex flex-wrap gap-2">
          {['#5a8a2e', '#d04020', '#4da6ff', '#f0a800', '#9a50e0', '#4dd9e0', '#e8e8e8', '#ff6a00'].map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => {
                apiPost('/api/settings', { avatarColor: c }).catch(() => undefined);
                showToast('success', c, '');
              }}
              className="w-8 h-8 rounded-lg border border-slate-700"
              style={{ background: c }}
            />
          ))}
        </div>
        <div className="text-xs font-bold text-slate-300 pt-2">{lang === 'id' ? 'Emoji' : 'Emoji'}</div>
        <div className="flex flex-wrap gap-1">
          {['⚔️', '🧙', '🏹', '💊', '🗡️', '🛡️', '🔮', '🌟', '👑', '🐉', '🦊', '🐺'].map((em) => (
            <button
              key={em}
              type="button"
              onClick={() => {
                setEmoji(em);
                updateUserProfile({ avatarEmoji: em, avatar: em });
                apiPost('/api/settings', { avatar: em }).catch(() => undefined);
              }}
              className="w-9 h-9 rounded-lg bg-slate-950 border border-slate-800 text-lg"
            >
              {em}
            </button>
          ))}
        </div>
      </div>

      <TalentPanel lang={lang} showToast={showToast} />

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-2">
        <div className="text-xs font-bold text-slate-300">{t('profile_security', '🔐 Pertanyaan Keamanan (untuk reset password)')}</div>
        <select
          value={secQ}
          onChange={(e) => setSecQ(e.target.value)}
          className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs"
        >
          {Array.from({ length: 7 }, (_, i) => i + 1).map((i) => (
            <option key={i} value={String(i)}>{t(`security_q${i}`, `Q${i}`)}</option>
          ))}
        </select>
        <input value={secA} onChange={(e) => setSecA(e.target.value)} placeholder={t('profile_security_answer', 'Jawaban (simpan baik-baik)')} className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
        <button
          type="button"
          onClick={() => {
            if (!secA.trim()) {
              showToast('info', t('security_questions_not_empty', 'Jawaban tidak boleh kosong'), '');
              return;
            }
            apiPost('/api/profile/security', { question: secQ, answer: secA }).then((r: any) => {
              showToast('success', t('security_questions_saved', 'Pertanyaan keamanan berhasil disimpan!'), '');
              setSecA('');
            }).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold"
        >
          {t('profile_save_security_btn', 'Simpan Pertanyaan Keamanan')}
        </button>

        <div className="pt-1 border-t border-slate-800" />
        <div className="text-xs font-bold text-slate-300">{t('backup_codes_title', 'Kode Cadangan')}</div>
        <p className="text-[11px] text-slate-400 leading-relaxed">{t('backup_codes_intro', 'Kode Cadangan Anda (simpan baik-baik, jangan sampai hilang):')}</p>
        {backupCodes && (
          <div className="rounded-xl bg-slate-950 border border-amber-500/40 p-3 space-y-1">
            {Array.isArray(backupCodes) && backupCodes.map((c, i) => (
              <div key={i} className="text-xs font-mono text-amber-200">{i + 1}. {c}</div>
            ))}
            <button
              type="button"
              onClick={() => {
                try {
                  navigator.clipboard?.writeText(backupCodes.join('\n'));
                  showToast('success', t('backup_codes_copy', 'Salin kode'), '');
                } catch { /* clipboard unavailable */ }
              }}
              className="mt-1 px-3 py-1.5 rounded-xl bg-amber-500/20 text-amber-300 text-[11px] font-bold"
            >
              {t('backup_codes_copy', 'Salin kode')}
            </button>
          </div>
        )}
        <p className="text-[10px] text-rose-400/90 leading-relaxed">{t('backup_codes_warning', 'Setiap kode hanya bisa dipakai SEKALI untuk reset password. Simpan di tempat aman!')}</p>
        <button
          type="button"
          onClick={() => {
            apiPost<any>('/api/profile/backup-codes', {}).then((r) => {
              const codes = r.result || r.codes || [];
              setBackupCodes(Array.isArray(codes) ? codes : String(codes).split(/\s+/).filter(Boolean));
            }).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          className="px-3 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black"
        >
          {lang === 'id' ? 'Generate kode cadangan' : 'Generate backup codes'}
        </button>
      </div>

      {/* Account security: change password + lock/unlock (parity with PyQt) */}
      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-2">
        <div className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Keamanan Akun' : 'Account Security'}</div>
        <div className="grid sm:grid-cols-2 gap-2">
          <input type="password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} placeholder={lang === 'id' ? 'Kata sandi lama' : 'Current password'} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} placeholder={lang === 'id' ? 'Kata sandi baru (min. 8)' : 'New password (min. 8)'} className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
        </div>
        <button
          type="button"
          onClick={() => {
            apiPost<any>('/api/profile/password', { oldPassword: oldPw, newPassword: newPw }).then((r) => {
              showToast(r.ok ? 'success' : 'info', r.result?.msg || r.error || 'password', '');
              if (r.ok) { setOldPw(''); setNewPw(''); }
            }).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold"
        >
          {lang === 'id' ? 'Ganti kata sandi' : 'Change password'}
        </button>
        <div className="pt-2 border-t border-slate-800" />
        <div className="text-xs font-bold text-slate-300">{t('profile_lock_account', '🔒 Lock Akun (Freeze Tracking)')}</div>
        {locked ? (
          <>
            <p className="text-[11px] font-bold text-rose-300">{t('profile_account_locked', '🔒 Akun sedang di-LOCK. Tracking dinonaktifkan.')}</p>
            <div className="flex gap-2">
              <input type="password" value={lockPw} onChange={(e) => setLockPw(e.target.value)} placeholder={t('profile_unlock_confirm', 'Masukkan password untuk membuka lock:')} className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
              <button
                type="button"
                onClick={() => {
                  apiPost<any>('/api/profile/lock', { unlock: true, password: lockPw }).then((r: any) => {
                    if (r?.ok) { showToast('success', 'unlocked', ''); setLockPw(''); setLocked(false); }
                    else { showToast('info', r?.result?.msg || r?.error || 'unlock_failed', ''); }
                  }).catch((e) => showToast('info', String(e?.message || e), ''));
                }}
                className="px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold"
              >
                {t('profile_unlock_account', '🔓 Buka Lock Akun')}
              </button>
            </div>
          </>
        ) : (
          <div className="flex gap-2">
            <input type="password" value={lockPw} onChange={(e) => setLockPw(e.target.value)} placeholder={t('profile_lock_confirm', 'Masukkan password untuk mengunci akun:')} className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
            <button
              type="button"
              onClick={() => {
                apiPost<any>('/api/profile/lock', { password: lockPw }).then((r: any) => {
                  if (r?.ok) { showToast('success', 'locked', ''); setLockPw(''); setLocked(true); }
                  else { showToast('info', r?.result?.msg || r?.error || 'lock_failed', ''); }
                }).catch((e) => showToast('info', String(e?.message || e), ''));
              }}
              className="px-3 py-2 rounded-xl bg-rose-600 text-white text-xs font-bold"
            >
              {t('profile_lock_account', '🔒 Lock Akun')}
            </button>
          </div>
        )}
      </div>

      <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4 space-y-2">
        <div className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Kode redeem' : 'Redeem code'}</div>
        <div className="flex gap-2">
          <input value={code} onChange={(e) => setCode(e.target.value)} className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
          <button
            type="button"
            onClick={() => {
              apiPost<any>('/api/profile/redeem', { code }).then((r) => {
                showToast(r.ok ? 'success' : 'info', r.result?.msg || r.error || 'redeem', '');
                setCode('');
              }).catch((e) => showToast('info', String(e?.message || e), ''));
            }}
            className="px-3 py-2 rounded-xl bg-emerald-500 text-slate-950 text-xs font-black"
          >
            Redeem
          </button>
        </div>
      </div>
    </div>
  );
};
