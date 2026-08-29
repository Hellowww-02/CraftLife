import React, { useEffect, useState } from 'react';
import { useGame } from '../../context/GameContext';
import { apiGet, apiPost } from '../../api/client';
import { User } from 'lucide-react';

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

/** Mirror ProfilePage: identitas, class, rebirth, redeem — bukan Settings. */
export const ProfileView: React.FC<{ onOpenSettings?: () => void }> = ({ onOpenSettings }) => {
  const { user, lang, inventory, userPets, habits, dailies, quests, rebirthCharacter, updateUserProfile, showToast } = useGame();
  const [name, setName] = useState(user.displayName || user.name || '');
  const [bio, setBio] = useState(user.bio || '');
  const [emoji, setEmoji] = useState(user.avatarEmoji || user.avatar || '⚔️');
  const [heroClass, setHeroClass] = useState(String(user.avatarClass || user.heroClass || 'warrior').toLowerCase());
  const [code, setCode] = useState('');
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [lockPw, setLockPw] = useState('');

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

      <div className="rounded-2xl border border-violet-500/30 bg-violet-950/20 p-4 space-y-2">
        <div className="flex items-center gap-2 text-sm font-black text-violet-200">
          <User className="w-4 h-4" /> {lang === 'id' ? 'Rebirth' : 'Rebirth'}
        </div>
        <p className="text-xs text-slate-400">
          {lang === 'id'
            ? 'Reset level seperti ProfilePage PyQt. Buff rebirth dihitung di Python.'
            : 'Reset level like PyQt ProfilePage. Rebirth buffs are computed in Python.'}
        </p>
        <button
          type="button"
          onClick={() => {
            if (window.confirm(lang === 'id' ? 'Rebirth sekarang?' : 'Rebirth now?')) rebirthCharacter();
          }}
          className="px-4 py-2 rounded-xl bg-violet-500 text-slate-950 text-xs font-black"
        >
          {lang === 'id' ? 'Rebirth' : 'Rebirth'}
        </button>
      </div>

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
        <div className="text-xs font-bold text-slate-300">{lang === 'id' ? 'Pertanyaan keamanan' : 'Security question'}</div>
        <select
          defaultValue="1"
          id="sec-q"
          className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs"
        >
          {[1, 2, 3, 4, 5, 6, 7].map((i) => (
            <option key={i} value={String(i)}>Q{i}</option>
          ))}
        </select>
        <input id="sec-a" placeholder={lang === 'id' ? 'Jawaban' : 'Answer'} className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
        <button
          type="button"
          onClick={() => {
            const q = (document.getElementById('sec-q') as HTMLSelectElement)?.value;
            const a = (document.getElementById('sec-a') as HTMLInputElement)?.value;
            apiPost('/api/profile/security', { question: q, answer: a }).then((r: any) => showToast('success', r.result?.msg || 'ok', '')).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold"
        >
          {lang === 'id' ? 'Simpan keamanan' : 'Save security'}
        </button>
        <button
          type="button"
          onClick={() => {
            apiPost<any>('/api/profile/backup-codes', {}).then((r) => {
              const codes = r.result || r.codes || [];
              showToast('success', Array.isArray(codes) ? codes.join('  ') : String(codes), '');
            }).catch((e) => showToast('info', String(e?.message || e), ''));
          }}
          className="px-3 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-black"
        >
          {lang === 'id' ? 'Generate backup codes' : 'Generate backup codes'}
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
        <div className="flex gap-2 pt-1">
          <input type="password" value={lockPw} onChange={(e) => setLockPw(e.target.value)} placeholder={lang === 'id' ? 'Kata sandi kunci' : 'Lock password'} className="flex-1 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs" />
          <button type="button" onClick={() => { apiPost<any>('/api/profile/lock', { password: lockPw }).then(() => showToast('success', 'locked', '')); setLockPw(''); }}
            className="px-3 py-2 rounded-xl bg-rose-600 text-white text-xs font-bold">{lang === 'id' ? 'Kunci' : 'Lock'}</button>
          <button type="button" onClick={() => { apiPost<any>('/api/profile/lock', { unlock: true, password: lockPw }).then(() => showToast('success', 'unlocked', '')); setLockPw(''); }}
            className="px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold">{lang === 'id' ? 'Buka' : 'Unlock'}</button>
        </div>
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
