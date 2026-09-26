import React, { useEffect, useState, lazy, Suspense } from 'react';
import { GameProvider, useGame } from './context/GameContext';
import { MusicPlayerProvider } from './music/MusicPlayerContext';
import { OnboardingWizard } from './components/views/OnboardingWizard';
import { ActiveView } from './types';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { ToastContainer } from './components/ToastContainer';
import { DownloadToaster } from './components/DownloadToaster';
import { UndoToast } from './components/UndoToast';
import { UpdateDialogHost } from './components/UpdateDialogHost';
import { LevelUpModal } from './components/LevelUpModal';
import { CommandPalette } from './components/CommandPalette';
import { QuickAddDialog } from './components/QuickAddDialog';
import { LoginView } from './components/views/LoginView';
import { ViewFallback } from './components/ViewFallback';
import { ErrorBoundary } from './components/ErrorBoundary';
import { ShortcutsDialog } from './components/ShortcutsDialog';
import { t } from './i18n';

// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const DashboardView = lazy(() => import('./components/views/DashboardView').then((m) => ({ default: m.DashboardView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const HabitsView = lazy(() => import('./components/views/HabitsView').then((m) => ({ default: m.HabitsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const DailiesView = lazy(() => import('./components/views/DailiesView').then((m) => ({ default: m.DailiesView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const QuestsView = lazy(() => import('./components/views/QuestsView').then((m) => ({ default: m.QuestsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const SportView = lazy(() => import('./components/views/SportView').then((m) => ({ default: m.SportView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const HealthFoodView = lazy(() => import('./components/views/HealthFoodView').then((m) => ({ default: m.HealthFoodView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const ShopView = lazy(() => import('./components/views/ShopView').then((m) => ({ default: m.ShopView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const CraftView = lazy(() => import('./components/views/CraftView').then((m) => ({ default: m.CraftView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const PetsView = lazy(() => import('./components/views/PetsView').then((m) => ({ default: m.PetsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const EconomyView = lazy(() => import('./components/views/EconomyView').then((m) => ({ default: m.EconomyView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const NotesView = lazy(() => import('./components/views/NotesView').then((m) => ({ default: m.NotesView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const PomodoroView = lazy(() => import('./components/views/PomodoroView').then((m) => ({ default: m.PomodoroView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const RemindersView = lazy(() => import('./components/views/RemindersView').then((m) => ({ default: m.RemindersView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const FriendsView = lazy(() => import('./components/views/FriendsView').then((m) => ({ default: m.FriendsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const GuildView = lazy(() => import('./components/views/GuildView').then((m) => ({ default: m.GuildView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const AchievementsView = lazy(() => import('./components/views/AchievementsView').then((m) => ({ default: m.AchievementsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const SettingsView = lazy(() => import('./components/views/SettingsView').then((m) => ({ default: m.SettingsView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const ProfileView = lazy(() => import('./components/views/ProfileView').then((m) => ({ default: m.ProfileView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const LeaderboardView = lazy(() => import('./components/views/LeaderboardView').then((m) => ({ default: m.LeaderboardView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const LearningView = lazy(() => import('./components/views/LearningView').then((m) => ({ default: m.LearningView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const MusicView = lazy(() => import('./components/views/MusicView').then((m) => ({ default: m.MusicView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const LoveSpaceView = lazy(() => import('./components/views/LoveSpaceView').then((m) => ({ default: m.LoveSpaceView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const CalendarView = lazy(() => import('./components/views/CalendarView').then((m) => ({ default: m.CalendarView })));
// D01 (v1.6.7): code-split — tiap view jadi chunk sendiri, dimuat saat dibuka.
const SuppliesView = lazy(() => import('./components/views/SuppliesView').then((m) => ({ default: m.SuppliesView })));

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
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
      if (e.key === 'Escape') setPaletteOpen(false);
      // D04 (v1.6.7): `?` membuka bantuan pintasan — kecuali sedang mengetik.
      if (e.key === '?') {
        const el = e.target as HTMLElement | null;
        const typing = !!el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);
        if (!typing) {
          e.preventDefault();
          setShortcutsOpen(true);
        }
      }
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
        // A12: aksi cepat tab overview Love Space bisa melompat halaman.
        return <LoveSpaceView onNavigate={(v) => setActiveView(v as ActiveView)} />;
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
    // Shell 1:1 dengan MainWindow PyQt: TopBar full-width di atas, lalu body row
    // = [nav rail | main content] (parity self._topbar + body.addWidget(nav_scroll|_stack)).
    <div className="h-screen ct-app flex flex-col overflow-hidden selection:bg-emerald-500/20 selection:text-emerald-300">
      {/* Ambient scene — dekoratif murni (aria-hidden), tanpa logika */}
      <div className="ct-scene" aria-hidden="true">
        <div className="ct-scene-aurora" />
        <div className="ct-scene-orbs" />
        <div className="ct-scene-grain" />
      </div>

      <Navbar
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onOpenSettings={() => setActiveView('settings')}
        onOpenAchievements={() => setActiveView('achievements')}
        onOpenPalette={() => setPaletteOpen(true)}
        onOpenMusic={() => setActiveView('music')}
      />

      <div className="flex-1 flex min-h-0">
        <Sidebar
          activeView={activeView}
          onSelectView={(view) => setActiveView(view)}
          isOpen={isSidebarOpen}
          onClose={() => setIsSidebarOpen(false)}
        />

        <main className="flex-1 min-w-0 min-h-0 overflow-y-auto overflow-x-hidden p-4 sm:p-6 lg:p-8">
          <div key={activeView} className={`ct-view${activeView === 'music' ? ' h-full' : ''}`}>
            <ErrorBoundary key={activeView}>
              <Suspense fallback={<ViewFallback />}>{renderActiveView()}</Suspense>
            </ErrorBoundary>
          </div>
        </main>
      </div>

      <ToastContainer />
      <DownloadToaster />
      <UndoToast />
      <UpdateDialogHost />
      <QuickAddDialog />
      <LevelUpModal />
      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectView={(v) => setActiveView(v)}
      />
      {shortcutsOpen && <ShortcutsDialog onClose={() => setShortcutsOpen(false)} />}
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
      <div className="h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-4 p-8 text-center ct-enter">
        <div className="text-5xl ct-float">⛏️</div>
        <h1 className="text-xl font-black text-rose-400">{t('web_api_offline', 'API lokal tidak merespons. Jalankan api_server di port 8765.')}</h1>
        <p className="text-sm text-slate-400 max-w-md">{t('web_offline_gate_hint', 'Koneksi ke server lokal terputus. Pastikan CraftLife API berjalan lalu coba lagi.')}</p>
        <code className="text-xs bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-500">{apiError}</code>
        <button
          type="button"
          onClick={retryBootstrap}
          className="mt-2 px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition-colors ct-press"
        >
          {t('web_retry', 'Coba lagi')}
        </button>
      </div>
    );
  }

  if (!hydrated) {
    return (
      <div className="h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-3 ct-app">
        <div className="text-4xl ct-float">⛏️</div>
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
      {/* P57: music engine global — <audio> hidup di luar switch view,
          sehingga musik tidak berhenti saat pindah halaman. */}
      <MusicPlayerProvider>
        <ErrorBoundary>
          <HydrationGate />
        </ErrorBoundary>
      </MusicPlayerProvider>
    </GameProvider>
  );
}
