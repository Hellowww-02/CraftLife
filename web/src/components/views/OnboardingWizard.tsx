import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { life } from '../../api/life';
import { t } from '../../i18n';
import { AVATAR_CLASSES } from '../../data/gameData';
import { AvatarClass } from '../../types';
import { Sparkles, Rocket, Palette, Languages, Volume2, Check, ArrowRight, ArrowLeft } from 'lucide-react';

const AVATAR_EMOJIS: Record<AvatarClass, string> = {
  warrior: '⚔️',
  mage: '🧙',
  rogue: '🗡️',
  paladin: '🛡️',
  ranger: '🏹',
  healer: '❤️',
};

const COLORS = ['#ef4444', '#f59e0b', '#10b981', '#06b6d4', '#8b5cf6', '#ec4899'];

/** First-time onboarding wizard (parity with PyQt OnboardingWizard). */
export const OnboardingWizard: React.FC<{ onDone: () => void }> = ({ onDone }) => {
  const { lang, setLang, completeOnboarding, setSoundEnabled, showToast } = useGame();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState('');
  const [cls, setCls] = useState<AvatarClass>('warrior');
  const [color, setColor] = useState(COLORS[2]);
  const [useDailies, setUseDailies] = useState(true);
  const [useHabits, setUseHabits] = useState(false);
  const [soundOn, setSoundOn] = useState(true);

  const total = 4;
  const steps = [
    { icon: <Sparkles className="w-4 h-4" />, label: lang === 'id' ? 'Selamat Datang' : 'Welcome' },
    { icon: <Palette className="w-4 h-4" />, label: lang === 'id' ? 'Hero' : 'Hero' },
    { icon: <Languages className="w-4 h-4" />, label: lang === 'id' ? 'Preferensi' : 'Preferences' },
    { icon: <Volume2 className="w-4 h-4" />, label: lang === 'id' ? 'Mulai' : 'Start' },
  ];

  const clz = AVATAR_CLASSES[cls] || AVATAR_CLASSES.warrior;

  const finish = async () => {
    setBusy(true);
    try {
      if (useDailies) life.applyTemplate('daily', 'morning_routine_d').catch(() => {});
      if (useHabits) life.applyTemplate('habit', 'morning_routine').catch(() => {});
      setSoundEnabled(soundOn);
      await completeOnboarding({
        displayName: name.trim() || undefined,
        avatarClass: cls,
        avatarEmoji: AVATAR_EMOJIS[cls],
        heroClass: cls,
        avatarColor: color,
        language: lang,
      });
      setBusy(false);
      onDone();
    } catch {
      setBusy(false);
      showToast('damage', 'Onboarding', 'Something went wrong. Please retry.');
    }
  };

  const next = () => { if (step < total - 1) setStep(step + 1); };
  const prev = () => { if (step > 0) setStep(step - 1); };

  return (
    <div className="fixed inset-0 z-[60] bg-slate-950 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-6">
          {steps.map((s, i) => (
            <div key={i} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold ${i === step ? 'bg-emerald-600 text-white' : i < step ? 'bg-emerald-900/60 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
              {s.icon}<span className="hidden sm:inline">{s.label}</span>
            </div>
          ))}
        </div>

        {step === 0 && (
          <div className="text-center space-y-4">
            <div className="text-6xl">🏰</div>
            <h2 className="text-2xl font-black text-slate-100">{lang === 'id' ? 'Selamat datang di CraftLife!' : 'Welcome to CraftLife!'}</h2>
            <p className="text-sm text-slate-400 leading-relaxed">
              {lang === 'id'
                ? 'Ubah kebiasaan sehari-hari jadi petualangan RPG. Selesaikan tugas, kumpulkan XP & gold, kalahkan boss, dan naik level bersama karaktermu.'
                : 'Turn your daily habits into an RPG adventure. Complete tasks, earn XP & gold, defeat bosses, and level up your hero.'}
            </p>
            <button onClick={next} className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition-colors">
              <Rocket className="w-4 h-4" /> {lang === 'id' ? 'Mulai' : 'Get Started'} <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="space-y-5">
            <div className="text-center space-y-1">
              <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Pilih Hero-mu' : 'Choose Your Hero'}</h2>
              <p className="text-xs text-slate-400">{lang === 'id' ? 'Kelas menentukan buff kamu.' : 'Your class determines your buffs.'}</p>
            </div>
            <form onSubmit={(e) => { e.preventDefault(); next(); }} className="space-y-4">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={lang === 'id' ? 'Nama pahlawan (opsional)' : 'Hero name (optional)'}
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <div className="grid grid-cols-3 gap-2">
                {(Object.keys(AVATAR_CLASSES) as AvatarClass[]).map((k) => {
                  const c = AVATAR_CLASSES[k];
                  const sel = cls === k;
                  return (
                    <button type="button" key={k} onClick={() => setCls(k)}
                      className={`p-3 rounded-xl border text-center transition-all ${sel ? 'bg-emerald-600/20 border-emerald-500' : 'bg-slate-950 border-slate-800 hover:border-slate-600'}`}>
                      <div className="text-2xl">{AVATAR_EMOJIS[k]}</div>
                      <div className="text-xs font-bold text-slate-200 mt-1">{c.name}</div>
                      <div className="text-[9px] text-slate-500 leading-tight">{c.desc}</div>
                    </button>
                  );
                })}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">{lang === 'id' ? 'Warna' : 'Color'}:</span>
                {COLORS.map((cc) => (
                  <button type="button" key={cc} onClick={() => setColor(cc)}
                    className={`w-7 h-7 rounded-full border-2 ${color === cc ? 'border-white' : 'border-transparent'}`} style={{ backgroundColor: cc }} />
                ))}
              </div>
              <div className="flex justify-between pt-2">
                <button type="button" onClick={prev} className="inline-flex items-center gap-1 px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold"><ArrowLeft className="w-3.5 h-3.5" /></button>
                <button type="submit" className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-emerald-600 text-white text-xs font-bold">OK <ArrowRight className="w-3.5 h-3.5" /></button>
              </div>
            </form>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div className="text-center space-y-1">
              <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Preferensi' : 'Preferences'}</h2>
              <p className="text-xs text-slate-400">{lang === 'id' ? 'Atur bahasa & peluncur tugas.' : 'Set language & starter tasks.'}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button onClick={() => setLang('id')} className={`p-3 rounded-xl border text-left transition-all ${lang === 'id' ? 'bg-emerald-600/20 border-emerald-500' : 'bg-slate-950 border-slate-800'}`}>
                <div className="text-xl">🇮🇩</div><div className="text-xs font-bold text-slate-200">Bahasa Indonesia</div>
              </button>
              <button onClick={() => setLang('en')} className={`p-3 rounded-xl border text-left transition-all ${lang === 'en' ? 'bg-emerald-600/20 border-emerald-500' : 'bg-slate-950 border-slate-800'}`}>
                <div className="text-xl">🇬🇧</div><div className="text-xs font-bold text-slate-200">English</div>
              </button>
            </div>
            <div className="space-y-2">
              <ToggleRow checked={useDailies} onChange={setUseDailies}
                label={lang === 'id' ? 'Tambahkan rutinitas pagi (dailies)' : 'Add a morning routine (dailies)'} />
              <ToggleRow checked={useHabits} onChange={setUseHabits}
                label={lang === 'id' ? 'Tambahkan habit pelacak' : 'Add habit tracker items'} />
              <ToggleRow checked={soundOn} onChange={setSoundOn}
                label={lang === 'id' ? 'Aktifkan suara' : 'Enable sound'} />
            </div>
            <div className="flex justify-between pt-2">
              <button onClick={prev} className="inline-flex items-center gap-1 px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-bold"><ArrowLeft className="w-3.5 h-3.5" /></button>
              <button onClick={next} className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-xl bg-emerald-600 text-white text-xs font-bold">{lang === 'id' ? 'Lanjut' : 'Next'} <ArrowRight className="w-3.5 h-3.5" /></button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="text-center space-y-5">
            <div className={`text-6xl ${cls ? '' : ''}`}>{AVATAR_EMOJIS[cls]}</div>
            <h2 className="text-xl font-black text-slate-100">
              {name.trim() || (lang === 'id' ? 'Petualang' : 'Adventurer')} · {clz.name}
            </h2>
            <p className="text-sm text-slate-400">{lang === 'id'
              ? 'Semua siap! Mulai level-up karakter dan selesaikan misi harianmu.'
              : 'All set! Start leveling up your hero and complete your daily quests.'}</p>
            <button onClick={finish} disabled={busy} className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition-colors disabled:opacity-50">
              {busy ? <span className="animate-pulse">…</span> : <Check className="w-4 h-4" />} {lang === 'id' ? 'Mulai Petualangan' : 'Start Adventure'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

const ToggleRow: React.FC<{ checked: boolean; onChange: (v: boolean) => void; label: string }> = ({ checked, onChange, label }) => (
  <button onClick={() => onChange(!checked)} className="w-full flex items-center justify-between p-3 rounded-xl bg-slate-950 border border-slate-800 text-left">
    <span className="text-xs text-slate-200">{label}</span>
    <span className={`w-9 h-5 rounded-full flex items-center px-0.5 transition-colors ${checked ? 'bg-emerald-500 justify-end' : 'bg-slate-700 justify-start'}`}>
      <span className="w-4 h-4 rounded-full bg-white" />
    </span>
  </button>
);
