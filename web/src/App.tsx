import React, { useEffect, useState } from 'react';
import { GameProvider, useGame } from './context/GameContext';
import { OnboardingWizard } from './components/views/OnboardingWizard';
import { ActiveView } from './types';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { ToastContainer } from './components/ToastContainer';
import { UndoToast } from './components/UndoToast';
import { LevelUpModal } from './components/LevelUpModal';
import { CommandPalette } from './components/CommandPalette';
import { QuickAddDialog } from './components/QuickAddDialog';
import { LoginView } from './components/views/LoginView';
import { t } from './i18n';

import { DashboardView } from './components/views/DashboardView';
import { HabitsView } from './components/views/HabitsView';
import { DailiesView } from './components/views/DailiesView';
import { QuestsView } from './components/views/QuestsView';
import { SportView } from './components/views/SportView';
import { HealthFoodView } from './components/views/HealthFoodView';
import { ShopView } from './components/views/ShopView';
import { CraftView } from './components/views/CraftView';
import { PetsView } from './components/views/PetsView';
import { EconomyView } from './components/views/EconomyView';
import { NotesView } from './components/views/NotesView';
import { PomodoroView } from './components/views/PomodoroView';
import { RemindersView } from './components/views/RemindersView';
import { FriendsView } from './components/views/FriendsView';
import { GuildView } from './components/views/GuildView';
import { AchievementsView } from './components/views/AchievementsView';
import { SettingsView } from './components/views/SettingsView';
import { ProfileView } from './components/views/ProfileView';
import { LeaderboardView } from './components/views/LeaderboardView';
import { LearningView } from './components/views/LearningView';
import { MusicView } from './components/views/MusicView';
import { LoveSpaceView } from './components/views/LoveSpaceView';
import { CalendarView } from './components/views/CalendarView';
import { SuppliesView } from './components/views/SuppliesView';

function wantLoginScreen() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('login') === '1') return true;
  try {
    return sessionStorage.getItem('craftlife_show_login') === '1';
  } catch {
    return false;
  }
}

const MainLayout: React.FC = () => {
  const [activeView, setActiveView] = useState<ActiveView>('dashboard');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if (e.key === 'Escape') setPaletteOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const renderActiveView = () => {
    switch (activeView) {
      case 'dashboard':
        return <DashboardView onNavigate={(view) => setActiveView(view)} />;
      case 'profile':
        return <ProfileView onOpenSettings={() => setActiveView('settings')} />;
      case 'habits':
        return <HabitsView />;
      case 'dailies':
        return <DailiesView />;
      case 'quests':
        return <QuestsView />;
      case 'sport':
        return <SportView />;
      case 'nutrition':
        return <HealthFoodView />;
      case 'shop':
        return <ShopView />;
      case 'craft':
        return <CraftView />;
      case 'pets':
        return <PetsView />;
      case 'boss':
        return <GuildView />;
      case 'economy':
        return <EconomyView onNavigate={(view) => setActiveView(view)} />;
      case 'supplies':
        return <SuppliesView onNavigate={(view) => setActiveView(view)} />;
      case 'notes':
        return <NotesView />;
      case 'health':
        return <HealthFoodView />;
      case 'pomodoro':
        return <PomodoroView />;
      case 'learning':
        return <LearningView />;
      case 'music':
        return <MusicView />;
      case 'love':
      case 'lovespace':
        return <LoveSpaceView />;
      case 'friends':
        return <FriendsView />;
      case 'guild':
        return <GuildView />;
      case 'social':
        return <FriendsView />;
      case 'reminders':
        return <RemindersView />;
      case 'calendar':
        return <CalendarView />;
      case 'achievements':
        return <AchievementsView />;
      case 'leaderboard':
        return <LeaderboardView />;
      case 'settings':
        return <SettingsView />;
      default:
        return <DashboardView onNavigate={(view) => setActiveView(view)} />;
    }
  };

  return (
    <div className="h-screen bg-slate-950 text-slate-100 flex overflow-hidden selection:bg-emerald-500/20 selection:text-emerald-300">
      <Sidebar
        activeView={activeView}
        onSelectView={(view) => setActiveView(view)}
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <Navbar
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
          onOpenSettings={() => setActiveView('settings')}
          onOpenAchievements={() => setActiveView('achievements')}
          onOpenPalette={() => setPaletteOpen(true)}
        />

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full overflow-y-auto overflow-x-hidden">
          {renderActiveView()}
        </main>
      </div>

      <ToastContainer />
      <UndoToast />
      <QuickAddDialog />
      <LevelUpModal />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectView={(v) => setActiveView(v)}
      />
    </div>
  );
};

/** Show the first-time OnboardingWizard (parity with PyQt) until onboarding_done. */
const OnboardingGate: React.FC = () => {
  const { user } = useGame();
  const [dismissed, setDismissed] = useState(false);
  if (user && user.onboardingDone === false && !dismissed) {
    return <OnboardingWizard onDone={() => setDismissed(true)} />;
  }
  return <MainLayout />;
};

/**
 * P2 Gate: UI hanya dirender SETELAH bootstrap server berhasil.
 * Gagal → layar error + tombol retry. Tidak ada lagi data demo/fake fallback.
 */
const HydrationGate: React.FC = () => {
  const { hydrated, apiError, retryBootstrap } = useGame();

  if (apiError) {
    return (
      <div className="h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4 p-8 text-center">
        <div className="text-5xl">⛏️</div>
        <h1 className="text-xl font-black text-rose-400">{t('web_api_offline', 'API lokal tidak merespons. Jalankan api_server di port 8765.')}</h1>
        <p className="text-sm text-slate-400 max-w-md">{t('web_offline_gate_hint', 'Koneksi ke server lokal terputus. Pastikan CraftLife API berjalan lalu coba lagi.')}</p>
        <code className="text-xs bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-500">{apiError}</code>
        <button
          type="button"
          onClick={retryBootstrap}
          className="mt-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition-colors"
        >
          {t('web_retry', 'Coba lagi')}
        </button>
      </div>
    );
  }

  if (!hydrated) {
    return (
      <div className="h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-3">
        <div className="text-4xl animate-bounce">⛏️</div>
        <p className="text-sm text-slate-400 font-semibold">{t('web_loading', 'Memuat...')}</p>
      </div>
    );
  }

  return <OnboardingGate />;
};

const Gate: React.FC = () => {
  const [showLogin, setShowLogin] = useState(wantLoginScreen);
  if (showLogin) {
    return (
      <LoginView
        onAuthed={() => {
          try {
            sessionStorage.removeItem('craftlife_show_login');
          } catch {
            /* ignore */
          }
          setShowLogin(false);
          window.location.reload();
        }}
      />
    );
  }
  return <OnboardingGate />;
};

export default function App() {
  return (
    <GameProvider>
      <HydrationGate />
    </GameProvider>
  );
}
