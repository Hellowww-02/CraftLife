import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { studio } from '../api/studio';
import { AVATAR_CLASSES } from '../data/gameData';
import { t as i18nT } from '../i18n';
import { Heart, Sparkles, Coins, Menu, Settings, Trophy, Globe, Bell, Clock } from 'lucide-react';

/** Interpolasi kecil (parity pola `tr` di view lain): {var} → nilai. */
const tr = (key: string, vars?: Record<string, string | number>, fallback?: string) => {
  let s = i18nT(key, fallback ?? key);
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  return s;
};

/** `t` alias yg dipakai di JSX (bukan `window.setInterval` scope). */
const t = (key: string, fallback: string) => i18nT(key, fallback);

interface NavbarProps {
  onToggleSidebar?: () => void;
  onOpenSettings?: () => void;
  onOpenAchievements?: () => void;
  onOpenPalette?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onToggleSidebar,
  onOpenSettings,
  onOpenAchievements,
  onOpenPalette,
}) => {
  const { user, lang, setLang, achievements, clockNow, today, activeBuffs, activeBuffsDetail } = useGame();
  const [notifOpen, setNotifOpen] = useState(false);

  // ── Digital clock (parity TopBar._update_time): jam berjalan maju tiap detik.
  //    Ditampilkan dalam ZONA LOKASI USER (browser), bukan zona server — karena
  //    timezone harus mengikuti lokasi user. clockNow() memberi instan UTC yang
  //    sinkron dgn server; field .getHours() dst. dibaca di zona browser user. ──
  const [clockTick, setClockTick] = useState('--:--:--');
  useEffect(() => {
    const pad = (n: number) => String(n).padStart(2, '0');
    const renderClock = () => {
      const d = clockNow();
      if (!d) { setClockTick('--:--:--'); return; }
      setClockTick(`${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`);
    };
    renderClock();
    const t = window.setInterval(renderClock, 1000);
    return () => window.clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clockNow]);
  const [notifs, setNotifs] = useState<{ id: string; message: string; type: string; isRead: boolean; createdAt: string }[]>([]);
  const loadNotifs = () => {
    studio.notifications().then((d) => {
      if (Array.isArray(d?.notifications)) setNotifs(d.notifications);
    }).catch(() => undefined);
  };
  useEffect(() => {
    loadNotifs();
    const t = window.setInterval(loadNotifs, 30000);
    return () => window.clearInterval(t);
  }, []);
  const unread = notifs.filter((n) => !n.isRead).length;
  const currentClass = AVATAR_CLASSES[user.avatarClass] || AVATAR_CLASSES.warrior;
  const unclaimedAchievements = achievements.filter((a) => a.isUnlocked && !a.isClaimed).length;

  const hpPercentage = Math.max(0, Math.min(100, Math.round((user.hp / user.maxHp) * 100)));
  const mpPercentage = Math.max(0, Math.min(100, Math.round((user.mp / user.maxMp) * 100)));
  const xpPercentage = Math.max(0, Math.min(100, Math.round((user.xp / user.xpToNextLevel) * 100)));

  // Daftar buff aktif (parity ShopPage._buff_bar): prefer detail terstruktur, fallback string.
  const buffChips: { key: string; label: string }[] =
    activeBuffsDetail.length > 0
      ? activeBuffsDetail.map((b, i) => ({ key: `buff-${i}`, label: tr(b.key, b) }))
      : activeBuffs.map((s, i) => ({ key: `buffs-${i}`, label: s }));
  const hasBuffs = buffChips.length > 0;

  return (
    <header className="shrink-0 z-30 ct-surface-solid backdrop-blur-md border-b ct-border px-4 py-2.5">
      <div className="flex items-center justify-between gap-3">
        {/* Left: Mobile Toggle + User Avatar & Vitals */}
        <div className="flex items-center gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-2 rounded-xl bg-slate-800 text-slate-300 hover:text-slate-100 hover:bg-slate-700"
              title={t('nav_toggle_menu', 'Toggle Menu')}
            >
              <Menu className="w-5 h-5" />
            </button>
          )}

          <div className="relative cursor-pointer" onClick={onOpenSettings} title={t('nav_hero_profile', 'Hero Profile')}>
            <div
              className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl flex items-center justify-center text-xl font-bold border-2 shadow-inner transition-transform hover:scale-105"
              style={{
                backgroundColor: `${currentClass.color}20`,
                borderColor: currentClass.color,
              }}
            >
              {user.avatarEmoji || user.avatar || currentClass.icon}
            </div>
            <span className="absolute -bottom-1.5 -right-1.5 px-1.5 py-0.2 text-[9px] font-bold bg-amber-500 text-slate-950 rounded-full border border-amber-300">
              Lv.{user.level}
            </span>
          </div>

          <div className="flex flex-col gap-0.5 min-w-[140px] sm:min-w-[200px]">
            <div className="flex items-center justify-between text-xs">
              <span className="font-bold text-slate-200 truncate max-w-[100px] sm:max-w-[130px]">
                {user.displayName || user.name || user.username}
              </span>
              <span className="text-[10px] text-amber-400 font-semibold">{currentClass.name}</span>
            </div>

            {/* HP Bar */}
            <div className="space-y-0.5">
              <div className="flex items-center justify-between text-[9px] font-medium text-slate-400">
                <span className="flex items-center gap-1 text-red-400">
                  <Heart className="w-2.5 h-2.5 fill-red-500 text-red-500" /> {t('nav_hp_abbr', 'HP')}
                </span>
                <span>{user.hp}/{user.maxHp}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-red-600 to-rose-500 transition-all duration-300 rounded-full"
                  style={{ width: `${hpPercentage}%` }}
                />
              </div>
            </div>

            {/* MP Bar */}
            <div className="space-y-0.5">
              <div className="flex items-center justify-between text-[9px] font-medium text-slate-400">
                <span className="flex items-center gap-1 text-sky-400">
                  <Sparkles className="w-2.5 h-2.5 text-sky-400" /> {t('nav_mp_abbr', 'MP')}
                </span>
                <span>{user.mp}/{user.maxMp}</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-sky-600 to-blue-500 transition-all duration-300 rounded-full"
                  style={{ width: `${mpPercentage}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Center: XP Progress Bar (Desktop) */}
        <div className="hidden lg:flex flex-col items-center justify-center min-w-[220px] max-w-md flex-1">
          <div className="flex items-center justify-between w-full text-[10px] font-semibold text-slate-300 mb-0.5">
            <span className="text-amber-300">{tr('nav_level_progress', { level: user.level })}</span>
            <span className="text-slate-400">{user.xp} / {user.xpToNextLevel} ({xpPercentage}%)</span>
          </div>
          <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 transition-all duration-300 rounded-full"
              style={{ width: `${xpPercentage}%` }}
            />
          </div>
        </div>

        {/* Right: Currencies & Quick Links */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Gold — nilai LOKAL (offline-first source of truth). Sinkronisasi cloud
              best-effort; status sync lihat Settings → Cloud & Sync. */}
          <div className="flex items-center gap-1 px-2.5 py-1 sm:px-3 sm:py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 font-extrabold text-xs sm:text-sm">
            <Coins className="w-3.5 h-3.5 text-amber-400" />
            <span>{(user.gold ?? 0).toLocaleString()}</span>
          </div>

          {/* Buff count (mobile-only; daftar lengkap tampil di strip bawah pada desktop) */}
          <span
            className="lg:hidden px-2 py-1 rounded-xl bg-slate-800 text-[10px] font-bold text-slate-300 border border-slate-700/60"
            title={buffChips.map((b) => b.label).join(' · ') || t('buff_bar_empty', 'No active buffs.')}
          >
            ⚡{buffChips.length}
          </span>

          {/* Digital clock + date (parity TimeSync / TopBar chip_time) */}
          <div
            className="hidden sm:flex flex-col items-end px-3 py-1 rounded-xl bg-slate-950/60 border border-slate-700/70 text-slate-200"
            title={today}
          >
            <span className="font-mono text-[13px] font-bold leading-none tabular-nums">{clockTick}</span>
            <span className="text-[9px] text-slate-500 font-semibold mt-0.5">{today}</span>
          </div>

          {onOpenPalette && (
            <button
              onClick={onOpenPalette}
              className="hidden sm:flex items-center gap-1 px-2 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-400"
              title="Ctrl+K"
            >
              ⌘K
            </button>
          )}

          {/* Achievements */}
          {onOpenAchievements && (
            <button
              onClick={onOpenAchievements}
              className="relative p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-amber-400 transition-colors"
              title={t('nav_achievements', 'Achievements')}
            >
              <Trophy className="w-4 h-4" />
              {unclaimedAchievements > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-500 text-slate-950 text-[10px] font-black flex items-center justify-center">
                  {unclaimedAchievements}
                </span>
              )}
            </button>
          )}

          {/* Settings Button */}
          {onOpenSettings && (
            <button
              onClick={onOpenSettings}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-slate-100 transition-colors"
              title={t('nav_settings', 'Settings')}
            >
              <Settings className="w-4 h-4" />
            </button>
          )}

          {/* Language Toggle */}
          <button
            onClick={() => setLang(lang === 'en' ? 'id' : 'en')}
            className="flex items-center gap-1 px-2 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-bold text-slate-300 transition-colors"
            title={t('nav_toggle_language', 'Toggle Language')}
          >
            <Globe className="w-3.5 h-3.5 text-sky-400" />
            <span>{lang.toUpperCase()}</span>
          </button>
        </div>
      </div>

      {/* Active Buffs — strip lebar penuh, tersebar rata kanan–kiri
          (parity ShopPage._buff_bar: seluruh buff aktif user). */}
      {hasBuffs && (
        <div className="hidden lg:flex flex-wrap items-center justify-evenly gap-x-2 gap-y-1.5 pt-2 mt-2 border-t border-slate-800/70">
          {buffChips.map((b) => (
            <span
              key={b.key}
              title={b.label}
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-semibold bg-slate-800/80 border border-slate-700/60 text-slate-300 whitespace-nowrap"
            >
              {b.label}
            </span>
          ))}
        </div>
      )}
    </header>
  );
};
