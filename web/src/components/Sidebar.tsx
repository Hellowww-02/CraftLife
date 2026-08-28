import React from 'react';
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

/** Urutan sama NavBar._TABS di MainPyQt6.py */
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

  return (
    <>
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden transition-opacity"
        />
      )}

      <aside
        className={`w-64 shrink-0 h-full bg-slate-900 border-r border-slate-800/80 p-3 flex flex-col justify-between z-50 transition-transform duration-300 ease-in-out
          max-lg:fixed max-lg:inset-y-0 max-lg:left-0
          ${isOpen ? 'max-lg:translate-x-0' : 'max-lg:-translate-x-full'}
          lg:translate-x-0 lg:static`}
      >
        <div className="space-y-1 overflow-y-auto">
          <div className="flex items-center justify-between px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            <span>{t('nav_adventure_menu', lang === 'id' ? 'Menu Petualangan' : 'Adventure Menu')}</span>
            {onClose && (
              <button type="button" onClick={onClose} className="lg:hidden p-1 text-slate-400 hover:text-slate-200">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <nav className="space-y-0.5">
            {TAB_ORDER.map((item) => {
              const isActive =
                currentTab === item.id ||
                (item.id === 'lovespace' && currentTab === 'love') ||
                (item.id === 'nutrition' && currentTab === 'health');
              const badge = badges[item.id] || 0;
              const label = t(item.i18n, lang === 'id' ? item.fallbackId : item.fallbackEn);
              return (
                <button
                  key={item.id}
                  type="button"
                  id={`nav-tab-${item.id}`}
                  onClick={() => handleSelect(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-gradient-to-r from-emerald-600/30 to-slate-800 text-emerald-300 border border-emerald-500/40 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className={item.color || 'text-slate-400'}>{item.icon}</span>
                    <span className="truncate">{label}</span>
                  </div>
                  {badge > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] font-black rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                      {badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-800/80 px-2 text-left">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>{t('nav_prestige_level', lang === 'id' ? 'Tingkat Rebirth' : 'Prestige Level')}:</span>
            <span className="font-extrabold text-cyan-400">★ {user.rebirthCount}</span>
          </div>
          <div className="text-[10px] text-slate-400 mt-0.5">
            {t('web_offline_first', 'CraftLife v1.4.0 · Offline-First')}
          </div>
        </div>
      </aside>
    </>
  );
};
