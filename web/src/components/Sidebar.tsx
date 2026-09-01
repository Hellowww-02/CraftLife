import React, { useEffect, useRef } from 'react';
import { useGame } from '../context/GameContext';
import { t } from '../i18n';
import { ActiveView, NavTab } from '../types';
import {
  LayoutDashboard,
  Zap,
  CalendarCheck,
  CheckSquare,
  Activity,
  Salad,
  ShoppingBag,
  Hammer,
  Package,
  Dog,
  Wallet,
  FileText,
  Timer,
  Trophy,
  Settings,
  X,
  BookOpen,
  Music2,
  Heart,
  Users,
  Calendar as CalendarIcon,
  Bell,
  Shield,
  UserPlus,
} from 'lucide-react';

export interface SidebarProps {
  activeView?: ActiveView;
  activeTab?: NavTab;
  onSelectView?: (view: ActiveView) => void;
  setActiveTab?: (tab: NavTab) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

/** Urutan & label sama persis NavBar._TABS di MainPyQt6.py (icon di atas, label di bawah). */
const TAB_ORDER: { id: ActiveView; i18n: string; fallbackId: string; fallbackEn: string; icon: React.ReactNode; color?: string }[] = [
  { id: 'dashboard', i18n: 'nav_home', fallbackId: 'Beranda', fallbackEn: 'Home', icon: <LayoutDashboard className="w-4 h-4" /> },
  { id: 'profile', i18n: 'nav_profile', fallbackId: 'Profil', fallbackEn: 'Profile', icon: <Settings className="w-4 h-4" /> },
  { id: 'habits', i18n: 'nav_habits', fallbackId: 'Habits', fallbackEn: 'Habits', icon: <Zap className="w-4 h-4" />, color: 'text-amber-400' },
  { id: 'dailies', i18n: 'nav_dailies', fallbackId: 'Dailies', fallbackEn: 'Dailies', icon: <CalendarCheck className="w-4 h-4" />, color: 'text-emerald-400' },
  { id: 'quests', i18n: 'nav_quests', fallbackId: 'Quests', fallbackEn: 'Quests', icon: <CheckSquare className="w-4 h-4" />, color: 'text-blue-400' },
  { id: 'sport', i18n: 'nav_sporttrack', fallbackId: 'SportTrack', fallbackEn: 'SportTrack', icon: <Activity className="w-4 h-4" />, color: 'text-rose-400' },
  { id: 'economy', i18n: 'nav_economy', fallbackId: 'Economy', fallbackEn: 'Economy', icon: <Wallet className="w-4 h-4" />, color: 'text-green-400' },
  { id: 'supplies', i18n: 'nav_supplies', fallbackId: 'Supplies', fallbackEn: 'Supplies', icon: <Package className="w-4 h-4" />, color: 'text-amber-400' },
  { id: 'nutrition', i18n: 'nav_health_food', fallbackId: 'Health & Food', fallbackEn: 'Health & Food', icon: <Salad className="w-4 h-4" />, color: 'text-teal-400' },
  { id: 'lovespace', i18n: 'nav_love', fallbackId: 'Love Space', fallbackEn: 'Love Space', icon: <Heart className="w-4 h-4" />, color: 'text-rose-400' },
  { id: 'learning', i18n: 'nav_learning', fallbackId: 'Learning', fallbackEn: 'Learning', icon: <BookOpen className="w-4 h-4" />, color: 'text-violet-400' },
  { id: 'pomodoro', i18n: 'nav_pomodoro', fallbackId: 'Pomodoro', fallbackEn: 'Pomodoro', icon: <Timer className="w-4 h-4" />, color: 'text-purple-400' },
  { id: 'music', i18n: 'nav_music', fallbackId: 'Music', fallbackEn: 'Music', icon: <Music2 className="w-4 h-4" />, color: 'text-emerald-400' },
  { id: 'notes', i18n: 'nav_notes', fallbackId: 'Notes', fallbackEn: 'Notes', icon: <FileText className="w-4 h-4" />, color: 'text-cyan-400' },
  { id: 'reminders', i18n: 'nav_reminders', fallbackId: 'Reminders', fallbackEn: 'Reminders', icon: <Bell className="w-4 h-4" />, color: 'text-amber-300' },
  { id: 'calendar', i18n: 'nav_calendar', fallbackId: 'Kalender', fallbackEn: 'Calendar', icon: <CalendarIcon className="w-4 h-4" />, color: 'text-cyan-400' },
  { id: 'craft', i18n: 'nav_crafting', fallbackId: 'Crafting', fallbackEn: 'Crafting', icon: <Hammer className="w-4 h-4" />, color: 'text-amber-400' },
  { id: 'shop', i18n: 'nav_shop', fallbackId: 'Shop', fallbackEn: 'Shop', icon: <ShoppingBag className="w-4 h-4" />, color: 'text-yellow-400' },
  { id: 'pets', i18n: 'nav_pets', fallbackId: 'Pets', fallbackEn: 'Pets', icon: <Dog className="w-4 h-4" />, color: 'text-indigo-400' },
  { id: 'friends', i18n: 'nav_friends', fallbackId: 'Friends', fallbackEn: 'Friends', icon: <UserPlus className="w-4 h-4" />, color: 'text-sky-400' },
  { id: 'guild', i18n: 'nav_guild', fallbackId: 'Guild', fallbackEn: 'Guild', icon: <Shield className="w-4 h-4" />, color: 'text-amber-400' },
  { id: 'achievements', i18n: 'nav_achievement', fallbackId: 'Achievement', fallbackEn: 'Achievement', icon: <Trophy className="w-4 h-4" />, color: 'text-amber-300' },
  { id: 'leaderboard', i18n: 'nav_leaderboard', fallbackId: 'Leaderboard', fallbackEn: 'Leaderboard', icon: <Trophy className="w-4 h-4" />, color: 'text-yellow-400' },
  { id: 'settings', i18n: 'nav_settings', fallbackId: 'Settings', fallbackEn: 'Settings', icon: <Settings className="w-4 h-4" /> },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeView,
  activeTab,
  onSelectView,
  setActiveTab,
  isOpen = false,
  onClose,
}) => {
  const { lang, user, dailies, quests, achievements } = useGame();

  const currentTab = activeView || activeTab || 'dashboard';
  const handleSelect = (tab: ActiveView) => {
    if (onSelectView) onSelectView(tab);
    if (setActiveTab) setActiveTab(tab);
    if (onClose) onClose();
  };

  const pendingDailies = dailies.filter((d) => !d.isCompletedToday).length;
  const pendingQuests = quests.filter((q) => !q.isCompleted).length;
  const unclaimedAchievements = achievements.filter((a) => a.isUnlocked && !a.isClaimed).length;
  const badges: Partial<Record<ActiveView, number>> = {
    dailies: pendingDailies,
    quests: pendingQuests,
    achievements: unclaimedAchievements,
  };

  // Auto-scroll item aktif ke view (parity NavBar._select → ensureWidgetVisible).
  const activeRef = useRef<HTMLButtonElement | null>(null);
  useEffect(() => {
    if (activeRef.current && (typeof activeRef.current.scrollIntoView === 'function')) {
      try { activeRef.current.scrollIntoView({ block: 'nearest' }); } catch { /* ignore */ }
    }
  }, [currentTab]);

  return (
    <>
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      {/* ── Left nav rail (parity NavBar + nav_scroll di MainWindow._build) ── */}
      <aside
        className={`w-[92px] shrink-0 h-full ct-surface-solid border-r ct-border flex flex-col z-50 transition-transform duration-300 ease-in-out
          max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:w-64
          ${isOpen ? 'max-lg:translate-x-0' : 'max-lg:-translate-x-full'}
          lg:translate-x-0 lg:static`}
      >
        {/* Mobile header */}
        <div className="lg:hidden flex items-center justify-between px-4 py-3 text-[11px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800/80">
          <span>{t('nav_adventure_menu', lang === 'id' ? 'Menu Petualangan' : 'Adventure Menu')}</span>
          {onClose && (
            <button type="button" onClick={onClose} className="p-1 text-slate-400 hover:text-slate-200">
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Scrollable nav (nav_scroll) */}
        <nav className="flex-1 overflow-y-auto overflow-x-hidden px-1.5 py-2 space-y-1">
          {TAB_ORDER.map((item) => {
            const isActive =
              currentTab === item.id ||
              (item.id === 'lovespace' && currentTab === 'love') ||
              (item.id === 'nutrition' && currentTab === 'health');
            const badge = badges[item.id] || 0;
            const label = t(item.i18n, lang === 'id' ? item.fallbackId : item.fallbackEn);
            const accent = item.color || 'text-slate-400';
            return (
              <button
                key={item.id}
                ref={isActive ? activeRef : undefined}
                type="button"
                id={`nav-tab-${item.id}`}
                onClick={() => handleSelect(item.id)}
                title={label}
                className={`relative w-full flex flex-col items-center gap-1 px-1 py-2 rounded-xl border text-[10px] font-bold leading-tight transition-all
                  ${isActive
                    ? 'bg-gradient-to-b from-emerald-600/25 to-slate-800 border-emerald-500/40 text-emerald-200 shadow-sm'
                    : 'border-transparent text-slate-400 hover:bg-slate-800/70 hover:text-slate-100'}`}
              >
                {/* Active left indicator (parity navindicator / border-left) */}
                <span
                  className={`absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-7 rounded-r-full transition-all ${
                    isActive ? 'bg-emerald-400' : 'bg-transparent'
                  }`}
                />
                <span className={`relative text-xl leading-none ${isActive ? '' : accent}`}>
                  {item.icon}
                  {badge > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 px-0.5 rounded-full bg-emerald-500 text-slate-950 text-[9px] font-black flex items-center justify-center border border-emerald-300">
                      {badge > 99 ? '99+' : badge}
                    </span>
                  )}
                </span>
                <span className="text-center truncate w-full">{label}</span>
              </button>
            );
          })}
        </nav>

        {/* Footer (parity prestige + version) */}
        <div className="mt-auto pt-2 pb-3 border-t border-slate-800/80 px-2 text-center">
          <div className="text-[10px] text-slate-400">
            <span className="font-extrabold text-cyan-400 text-xs">★ {user.rebirthCount}</span>
            <span className="block mt-0.5">{t('nav_prestige_level', lang === 'id' ? 'Tingkat Rebirth' : 'Prestige Level')}</span>
          </div>
          <div className="text-[8px] text-slate-600 mt-1">{t('web_offline_first', 'CraftLife v1.4.0 · Offline-First')}</div>
        </div>
      </aside>
    </>
  );
};
