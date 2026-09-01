import React, { createContext, useContext, useState, useEffect, useCallback, useRef, ReactNode } from 'react';
import { t as i18nT } from '../i18n';
import { startPomoAlarm, stopPomoAlarm } from '../utils/pomoAlarm';
import { playReminderSound, ReminderSound, startReminderLoop, stopReminderLoop } from '../utils/sound';
import confetti from 'canvas-confetti';
import {
  UserProfile,
  Habit,
  Daily,
  Quest,
  TaskFolder,
  SportLog,
  MealLog,
  WaterLog,
  InventoryItem,
  UserPet,
  Boss,
  Transaction,
  Debt,
  SavingGoal,
  ServerClock,
  ThemePalette,
  InvestmentItem,
  SubscriptionItem,
  DebtNote,
  NoteFolder,
  Note,
  Achievement,
  HealthMetricLog,
  PomodoroSession,
  TaskDifficulty,
  LearningNotebook,
  LoveSpaceData,
  FriendUser,
  FriendRequest,
  ChatMessage,
  GuildData,
  PvPChallenge,
  ReminderItem,
} from '../types';
import {
  SHOP_ITEMS,
  PETS_DATA,
  BOSSES,
  CRAFT_RECIPES,
} from '../data/gameData';
import { apiGet, apiPost } from '../api/client';
import { ensureCurrencyRates } from '../utils/currency';
import { rpg } from '../api/rpg';
import { life } from '../api/life';
import { studio } from '../api/studio';
import { loadMessages, t } from '../i18n';
import { applyTheme } from '../utils/theme';
import { applyBootstrapCatalogs, liveShopItems, livePets } from '../data/liveCatalog';

interface NotificationToast {
  id: string;
  type: 'success' | 'damage' | 'level_up' | 'info' | 'boss';
  title: string;
  message: string;
}

interface GameContextType {
  // User Profile
  user: UserProfile;
  setUser: React.Dispatch<React.SetStateAction<UserProfile>>;
  /** Terapkan payload server ({ok, result, user, ...snapshot}) ke state — satu
   * sumber kebenaran perberubahan (parity _ok_payload/api_server). */
  applyLive: (res: any) => boolean;
  updateUserProfile: (profile: Partial<UserProfile>) => void;
  completeOnboarding: (profile?: Partial<UserProfile>) => Promise<void>;
  rebirthCharacter: () => void;
  hydrated: boolean;
  apiError: string | null;
  retryBootstrap: () => void;

  // Language & Settings
  lang: 'id' | 'en';
  setLang: (lang: 'id' | 'en') => void;
  soundEnabled: boolean;
  setSoundEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  activeTheme: string;
  setActiveTheme: (theme: string) => void;
  themePalettes: Record<string, ThemePalette>;
  /** Contoh palet yg aktif (utk render/swatch). */
  activePalette: ThemePalette | null;

  // ── Server clock (parity TimeSync): 'today' + jam konsisten dgn backend. ──
  serverNow: ServerClock | null;
  /** Waktu wall-clock server sekarang sebagai Date (berjalan maju tiap tick). */
  clockNow: () => Date | null;
  /** Date 'kalender' hari ini dalam zona app (field lokal = Y/M/D yang benar
   *  di zona browser APAPUN — bisa dipakai .getFullYear/.getMonth/.getDate/.getDay). */
  nowDate: () => Date | null;
  /** Tanggal server (YYYY-MM-DD) — sumber 'today' tunggal, bukan new Date(). */
  today: string;
  serverClockOffsetMs: number;

  // Folders
  taskFolders: TaskFolder[];
  addTaskFolder: (name: string, icon: string, color?: string, mode?: string) => void;
  renameTaskFolder: (id: string, name: string, mode?: string) => void;
  duplicateTaskFolder: (id: string, mode?: string) => void;
  deleteTaskFolder: (id: string, mode?: string) => void;

  // Habits
  habits: Habit[];
  addHabit: (title: string, difficulty: TaskDifficulty, isPositive: boolean, isNegative: boolean, folderId?: string | null, notes?: string) => void;
  editHabit: (id: string, updates: Partial<Habit>) => void;
  duplicateHabit: (id: string) => void;
  deleteHabit: (id: string) => void;
  triggerHabit: (id: string, isPos: boolean) => void;
  reorderHabits: (ordered: Habit[]) => void;
  moveTaskAcrossFolders: (mode: string, id: string, folderId: string | null) => void;
  restoreTask: (trashId: string) => void;
  lastDelete: { trashId: string; label: string } | null;
  undoDelete: () => void;

  // Dailies
  dailies: Daily[];
  addDaily: (title: string, difficulty: TaskDifficulty, repeatDays: number[], folderId?: string | null, notes?: string) => void;
  editDaily: (id: string, updates: Partial<Daily>) => void;
  duplicateDaily: (id: string) => void;
  deleteDaily: (id: string) => void;
  toggleDaily: (id: string) => void;
  failDaily: (id: string) => void;
  useDailyFreeze: (id: string) => void;
  reorderDailies: (ordered: Daily[]) => void;

  // Quests / Todos
  quests: Quest[];
  addQuest: (title: string, difficulty: TaskDifficulty, dueDate?: string | null, folderId?: string | null, notes?: string) => void;
  editQuest: (id: string, updates: Partial<Quest>) => void;
  duplicateQuest: (id: string) => void;
  deleteQuest: (id: string) => void;
  toggleQuest: (id: string) => void;
  reorderQuests: (ordered: Quest[]) => void;

  // Sport Tracker
  sportLogs: SportLog[];
  addSportLog: (sportType: string, sportName: string, icon: string, durationMinutes: number, caloriesBurned: number, intensity: 'light' | 'moderate' | 'vigorous', notes?: string, difficulty?: string) => void;
  updateSportLog: (id: string, body: Record<string, unknown>) => void;
  completeSportLog: (id: string) => void;
  deleteSportLog: (id: string) => void;

  // Nutrition & Water
  mealLogs: MealLog[];
  addMealLog: (mealType: 'breakfast' | 'lunch' | 'dinner' | 'snack', foodName: string, icon: string, portion: number, calories: number, protein: number, carbs: number, fat: number) => void;
  deleteMealLog: (id: string) => void;
  waterLog: WaterLog;
  addWater: (amountMl: number) => void;
  resetWater: () => void;

  // Shop & Inventory & Crafting
  inventory: InventoryItem[];
  buyItem: (itemId: string) => boolean;
  sellItem: (itemId: string, quantity?: number) => void;
  useConsumable: (itemId: string) => boolean;
  equipItem: (itemId: string) => void;
  unequipItem: (itemId: string) => void;
  craftItem: (recipeResultId: string) => boolean;
  enchantItem: (itemId: string) => void;

  // Pets
  userPets: UserPet[];
  adoptPet: (petId: string, nickname?: string) => boolean;
  feedPet: (petId: string) => void;
  trainPet: (petId: string) => void;
  equipPet: (petId: string) => void;
  unequipPet: (petId: string) => void;

  // Boss Combat
  activeBoss: Boss | null;
  activeBossHp: number;
  startBossFight: (bossId: string) => void;
  attackBoss: (action?: string | boolean) => void;
  fleeBoss: () => void;
  useClassSkill: () => void;

  // Economy & Budget
  transactions: Transaction[];
  addTransaction: (type: 'income' | 'expense', category: string, amount: number, notes?: string, folderId?: string | null, name?: string, date?: string) => void;
  deleteTransaction: (id: string) => void;
  moveTransaction: (id: string, folderId: string | null) => void;
  debts: Debt[];
  addDebt: (title: string, type: 'payable' | 'receivable', totalAmount: number, dueDate: string, notes?: string) => void;
  payDebtInstallment: (id: string, amount: number) => void;
  deleteDebt: (id: string) => void;
  savings: SavingGoal[];
  addSaving: (name: string, targetAmount: number, currentAmount?: number, targetDate?: string) => void;
  addToSaving: (id: string, amount: number) => void;
  withdrawFromSaving: (id: string, amount: number) => void;
  deleteSaving: (id: string) => void;
  investments: InvestmentItem[];
  addInvestment: (name: string, amount: number, notes?: string) => void;
  collectInvestmentReturn: (id: string) => void;
  withdrawInvestment: (id: string) => void;
  subscriptions: SubscriptionItem[];
  addSubscription: (name: string, amount: number, dueDate: string, period?: string) => void;
  renewSubscription: (id: string) => void;
  deleteSubscription: (id: string) => void;
  debtNotes: DebtNote[];
  addDebtNote: (personName: string, amount: number, date?: string, notes?: string) => void;
  settleDebtNote: (id: string) => void;
  deleteDebtNote: (id: string) => void;
  applyTaskTemplate: (mode: string, key: string) => void;

  // Notes
  noteFolders: NoteFolder[];
  addNoteFolder: (name: string, icon: string, parentId?: string | null) => void;
  deleteNoteFolder: (id: string) => void;
  updateNoteFolder: (id: string, updates: { name?: string; icon?: string }) => void;
  duplicateNoteFolder: (id: string) => void;
  notes: Note[];
  addNote: (title: string, content: string, folderId?: string | null) => void;
  archiveNote: (id: string, archived: boolean) => void;
  duplicateNoteItem: (id: string) => void;
  updateNote: (id: string, title: string, content: string, folderId?: string | null) => void;
  deleteNote: (id: string) => void;
  reorderNotes: (orderedIds: string[]) => void;

  // Health Metrics & Pomodoro
  healthLogs: HealthMetricLog[];
  addHealthLog: (steps: number, sleepHours: number, weightKg?: number, heartRate?: number, mood?: 'great' | 'good' | 'neutral' | 'tired' | 'stressed', notes?: string) => void;
  pomodoroSessions: PomodoroSession[];
  pomodoroStats: { todaySessions: number; todayMinutes: number; totalSessions: number; totalMinutes: number };
  completePomodoroSession: (durationMinutes: number, label: string) => void;
  // ── Pomodoro engine (parity PomodoroPage; hidup di context → tidak reset
  // saat pindah halaman; timestamp-based endsAt bukan tick lokal) ──
  pomo: {
    phase: 'idle' | 'focus' | 'break';
    paused: boolean;
    remainingSec: number;
    totalSec: number;
    focusMin: number;
    breakMin: number;
    taskLabel: string;
  };
  pomoAlert: { phase: 'focus' | 'break'; title: string; msg: string } | null;
  pomoStart: () => void;
  pomoPauseToggle: () => void;
  pomoReset: () => void;
  pomoGiveUp: () => void;
  pomoSetDurations: (focusMin: number, breakMin: number) => void;
  pomoSetTask: (label: string) => void;
  pomoAckAlert: () => void;
  pomoTestAlarm: () => void;

  // Achievements
  achievements: Achievement[];
  claimAchievement: (id: string) => void;

  // Learning & AI Workspace (NotebookLM)
  notebooks: LearningNotebook[];
  addNotebook: (title: string, description: string, icon?: string) => void;
  updateNotebook: (id: string, updates: Partial<LearningNotebook>) => void;
  deleteNotebook: (id: string) => void;
  refreshNotebooks: () => void;
  addNotebookSource: (notebookId: string, title: string, content: string, type?: 'text' | 'doc' | 'pdf' | 'url') => void;
  deleteNotebookSource: (notebookId: string, sourceId: string) => void;
  addNotebookChat: (notebookId: string, text: string, sender: 'user' | 'ai') => void;

  // Love Space
  loveSpace: LoveSpaceData;
  updateLoveSpace: (updates: Partial<LoveSpaceData>) => void;
  addLoveMemory: (title: string, date: string, description: string, emoji: string) => void;
  toggleLoveBucketItem: (id: string) => void;
  answerLovePrompt: (promptId: string, answer: string) => void;

  // Social, Friends, PvP & Guild
  friends: FriendUser[];
  chatMessages: ChatMessage[];
  sendChatMessage: (text: string, otherId?: string) => void;
  sendFriendRequest: (username: string) => void;
  acceptFriendRequest: (id: string) => void;
  rejectFriendRequest: (id: string) => void;
  respondPvpChallenge: (id: string, accept: boolean) => void;
  approveGuildRequest: (id: string) => void;
  rejectGuildRequest: (id: string) => void;
  updateLovePhotoMeta: (id: string, body: Record<string, unknown>) => void;
  friendRequests: FriendRequest[];
  sendPvpChallenge: (friendId: string) => void;
  loveCheckin: (body: Record<string, unknown>) => void;
  lovePhoto: (path: string) => void;
  loveEvent: (body: Record<string, unknown>) => void;
  loveWeekly: (body: Record<string, unknown>) => void;
  loveCycle: (body: Record<string, unknown>) => void;
  // LovePage parity ops (P5)
  refreshLoveSpace: () => void;
  deleteLoveMemory: (id: string) => void;
  deleteLovePrompt: (id: string) => void;
  deleteLoveWeekly: (id: string) => void;
  deleteLoveCycle: (id: string) => void;
  deleteLoveEvent: (id: string) => void;
  deleteLoveBucket: (id: string) => void;
  deleteLovePhoto: (id: string) => void;
  lovePromptFavorite: (promptKey: string) => void;
  createLoveAlbum: (name: string, scope: string) => void;
  renameLoveAlbum: (id: string, name: string) => void;
  deleteLoveAlbum: (id: string) => void;
  loveAlbumAddPhoto: (albumId: string, photoId: string) => void;
  loveAlbumMovePhoto: (albumId: string, photoId: string, sourceAlbumId?: string | null) => void;
  loveAlbumRemovePhoto: (albumId: string, photoId: string) => void;
  refreshSocial: () => void;
  guild: GuildData;
  attackGuildBoss: (action?: 'light' | 'heavy' | 'block' | 'ultimate') => void;
  pvpChallenges: PvPChallenge[];
  claimPvPReward: (id: string) => void;

  // Calendar & Reminders
  reminders: ReminderItem[];
  // Parity ReminderDialog._save — payload penuh (title, description, datetime
  // "YYYY-MM-DD HH:mm:ss", repeat, repeatDays, soundType, soundFile).
  addReminder: (payload: { title: string; description?: string; reminderDatetime: string; repeat?: 'none' | 'daily' | 'weekly' | 'custom'; repeatDays?: string; soundType?: 'default' | 'beep1' | 'beep2' | 'custom'; soundFile?: string }) => void;
  editReminder: (id: string, payload: { title: string; description?: string; reminderDatetime: string; repeat?: 'none' | 'daily' | 'weekly' | 'custom'; repeatDays?: string; soundType?: 'default' | 'beep1' | 'beep2' | 'custom'; soundFile?: string }) => void;
  dismissReminderAlarm: () => void;
  toggleReminder: (id: string) => void;
  deleteReminder: (id: string) => void;
  calendarNotes: { date: string; note: string }[];
  dailyTaskCounts: Record<string, number>;
  saveCalendarNote: (date: string, note: string) => void;
  deleteCalendarNote: (date: string) => void;

  // Level Up Celebrations & Toasts
  levelUpInfo: { level: number; hpGain: number; mpGain: number; goldGain: number } | null;
  closeLevelUpModal: () => void;
  toasts: NotificationToast[];
  removeToast: (id: string) => void;
  showToast: (type: 'success' | 'damage' | 'level_up' | 'info' | 'boss', title: string, message: string) => void;

  // Calculated Stats
  activeBuffs: string[];
  totalBuffs: {
    xp_pct: number;
    gold_pct: number;
    boss_dmg: number;
    hp_reduc: number;
    block_chance: number;
    block_strength: number;
    crit_chance: number;
  };

  // State Management Export / Import / Reset
  exportDataJson: () => string;
  importDataJson: (jsonStr: string) => boolean;
  resetAllData: (password?: string) => Promise<boolean>;
}

const STORAGE_KEY = 'craftlife_app_data_v1';

// ── P2: Data demo/seed dihapus ───────────────────────────────────────────────
// Server (SQLite via /api/bootstrap dan _ok_payload setiap aksi) adalah satu-satunya
// sumber kebenaran. Bentuk kosong di bawah hanya shape awal sebelum bootstrap;
// App meng-gate UI memakai hydrated/apiError sehingga bentuk ini tidak pernah
// tampil sebagai data palsu.
const emptyUser: UserProfile = {
  id: '', username: '', displayName: '', bio: '',
  avatarClass: 'warrior', avatarEmoji: '⚔️', avatarColor: '#ef4444',
  level: 1, xp: 0, xpToNextLevel: 150,
  hp: 50, maxHp: 50, mp: 30, maxMp: 30,
  gold: 0, gems: 0, rebirthCount: 0, sportLevel: 1, sportXp: 0,
  activePetId: null, equippedWeapon: null, equippedArmor: null,
  equippedTool: null, equippedLegendary: null,
  freezeSlots: 0, createdAt: '',
};

const emptyWaterLog: WaterLog = { date: '', amountMl: 0, targetMl: 2000 };

const emptyLoveSpace: LoveSpaceData = {
  isEnabled: false, partnerName: '', partnerAvatar: '', anniversaryDate: '',
  connectionScore: 0, dailyLoveNote: '', memories: [], prompts: [], bucketList: [],
};

const emptyGuild: GuildData = {
  id: '', name: '', tag: '', level: 1, exp: 0, maxExp: 0,
  description: '', members: [], bossHp: 0, bossMaxHp: 0, bossName: '',
};

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  // Load initial state from LocalStorage or defaults
  const loadSavedState = () => {
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (data) {
        return JSON.parse(data);
      }
    } catch {
      // Fallback
    }
    return null;
  };

  const saved = loadSavedState();

  const [user, setUser] = useState<UserProfile>(emptyUser);
  const [lang, setLang] = useState<'id' | 'en'>(saved?.lang || 'en');
  const [soundEnabled, setSoundEnabled] = useState<boolean>(saved?.soundEnabled !== undefined ? saved.soundEnabled : true);

  // ── Server clock (parity TimeSync) ────────────────────────────────────────
  // serverNow = waktu pada saat bootstrap diterima. Untuk merender jam digital
  // yang terus berjalan kita simpan base epoch + base receive-moment, lalu
  // clockNow() menambahkan elapsed (Date.now() - receivedAt) — jadi jam selalu
  // forward walau re-render. Tanggal/kuadran waktu memakai zona app (Jakarta).
  const [serverNow, setServerNow] = useState<ServerClock | null>(null);
  const serverClockBase = useRef<{ epoch: number; receivedAt: number; tzOffsetMin: number } | null>(null);
  const clockNow = useCallback(() => {
    const base = serverClockBase.current;
    if (!base) return null;
    // epoch (server instant) + elapsed sejak diterima = sekarang.
    // Render file .getUTC*() di Navbar agar menampilkan wall-clock server
    // (bukan zona browser). Untuk tanggal lihat /serverDateKey.
    const ms = (base.epoch * 1000) + (Date.now() - base.receivedAt);
    return new Date(ms);
  }, []);
  /** Tanggal wall-clock server (YYYY-MM-DD) dihitung dari jam server + tz offset. */
  const serverDateKey = useCallback(() => {
    const base = serverClockBase.current;
    if (!base) return '';
    const ms = (base.epoch * 1000) + (Date.now() - base.receivedAt) + (base.tzOffsetMin * 60000);
    try { return new Date(ms).toISOString().slice(0, 10); } catch { return ''; }
  }, []);
  const today = serverNow?.date || serverDateKey() || (() => { try { return new Date().toISOString().slice(0, 10); } catch { return ''; } })();
  const serverClockOffsetMs = serverNow ? (serverNow.epoch * 1000 + serverNow.tzOffsetMin * 60000) - Date.now() : 0;
  /** Return Date kalender (field lokal=zona app). Lihat catatan nowDate di nilai konteks. */
  const nowDate = useCallback((): Date | null => {
    const base = serverClockBase.current;
    if (!base) return null;
    const ms = (base.epoch * 1000) + (Date.now() - base.receivedAt) + (base.tzOffsetMin * 60000);
    try {
      const w = new Date(ms); // UTC fields = wall-clock server
      // Bangun objek Date lokal dengan Y/M/D server agar getFullYear/... akurat
      // di zona browser apa pun.
      return new Date(w.getUTCFullYear(), w.getUTCMonth(), w.getUTCDate());
    } catch { return null; }
  }, []);
  // ── Sistem Tema (parity db.THEMES / SettingsPage theme radios) ─────────
  // activeTheme = key tema (mis. 'modern_dark'). Palet diterapkan ke CSS vars
  // lewat applyTheme() (utils/theme.ts) — bukan LOCALSTORAGE dummy.
  const [themePalettes, setThemePalettes] = useState<Record<string, ThemePalette>>({});
  const [activeTheme, setActiveThemeState] = useState<string>(saved?.activeTheme || 'modern_dark');
  const activePalette = themePalettes[activeTheme] || null;

  // Load katalog tema (palet penuh) dari server — parity SettingsPage theme radios.
  useEffect(() => {
    let alive = true;
    apiGet<any>('/api/catalog/themes')
      .then((d) => {
        if (!alive || !Array.isArray(d?.themes)) return;
        const m: Record<string, ThemePalette> = {};
        for (const p of d.themes) if (p?.key) m[p.key] = p;
        setThemePalettes(m);
      })
      .catch(() => undefined);
    return () => { alive = false; };
  }, []);

  // Terapkan theme yg aktif ke CSS vars setiap kali palet tersedia / key berubah.
  useEffect(() => {
    const pal = themePalettes[activeTheme] || activePalette;
    if (pal) applyTheme(pal);
  }, [activeTheme, themePalettes, activePalette]);

  const setActiveTheme = useCallback((theme: string) => {
    setActiveThemeState(theme);
    const pal = themePalettes[theme];
    if (pal) applyTheme(pal);
    // Persist ke user via API (parity SettingsPage: POST /api/settings {theme}).
    apiPost('/api/settings', { theme }).catch(() => undefined);
  }, [themePalettes]);

  const [taskFolders, setTaskFolders] = useState<TaskFolder[]>([]);
  const [habits, setHabits] = useState<Habit[]>([]);
  const [dailies, setDailies] = useState<Daily[]>([]);
  // P8 Heatmap: jumlah task sukses per hari (28 hari), dari `task_history`.
  const [dailyTaskCounts, setDailyTaskCounts] = useState<Record<string, number>>({});
  const [quests, setQuests] = useState<Quest[]>([]);
  const [sportLogs, setSportLogs] = useState<SportLog[]>([]);
  const [mealLogs, setMealLogs] = useState<MealLog[]>([]);
  const [waterLog, setWaterLog] = useState<WaterLog>(emptyWaterLog);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [userPets, setUserPets] = useState<UserPet[]>([]);
  const [activeBuffs, setActiveBuffs] = useState<string[]>([]);
  const [activeBoss, setActiveBoss] = useState<Boss | null>(null);
  const [activeBossHp, setActiveBossHp] = useState<number>(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [savings, setSavings] = useState<SavingGoal[]>([]);
  const [investments, setInvestments] = useState<InvestmentItem[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionItem[]>([]);
  const [debtNotes, setDebtNotes] = useState<DebtNote[]>([]);
  const [noteFolders, setNoteFolders] = useState<NoteFolder[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [healthLogs, setHealthLogs] = useState<HealthMetricLog[]>([]);
  const [pomodoroSessions, setPomodoroSessions] = useState<PomodoroSession[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);

  // New modules
  const [notebooks, setNotebooks] = useState<LearningNotebook[]>([]);
  const [loveSpace, setLoveSpace] = useState<LoveSpaceData>(emptyLoveSpace);
  const [friends, setFriends] = useState<FriendUser[]>([]);
  const [friendRequests, setFriendRequests] = useState<FriendRequest[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [guild, setGuild] = useState<GuildData>(emptyGuild);
  const [pvpChallenges, setPvpChallenges] = useState<PvPChallenge[]>([]);
  const [reminders, setReminders] = useState<ReminderItem[]>([]);
  const [calendarNotes, setCalendarNotes] = useState<{ date: string; note: string }[]>([]);

  const [toasts, setToasts] = useState<NotificationToast[]>([]);
  const [levelUpInfo, setLevelUpInfo] = useState<{ level: number; hpGain: number; mpGain: number; goldGain: number } | null>(null);
  const [lastDelete, setLastDelete] = useState<{ trashId: string; label: string } | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const fetchBootstrap = useCallback(async () => {
    setApiError(null);
    try {
      // Kurs mata uang (single source dari server: db.CURRENCY_RATES)
      await ensureCurrencyRates();
      const data = await apiGet<any>('/api/bootstrap');
      // ── Server clock: ikat base jam server agar 'today' & jam konsisten dgn
      //    reset harian backend (bukan new Date() browser). ──
      if (data?.serverNow?.epoch) {
        setServerNow(data.serverNow);
        serverClockBase.current = { epoch: data.serverNow.epoch, receivedAt: Date.now(), tzOffsetMin: data.serverNow.tzOffsetMin || 0 };
        lastServerDate.current = data.serverNow.date;
      }
      if (data?.user) {
        setUser((prev) => ({
          ...prev,
          ...data.user,
          xpToNextLevel: data.user.xpToNextLevel || (data.user.level || 1) * 150,
        }));
        // ── Tema terkait user (parity SettingsPage): terapkan palet dari DB. ──
        const uTheme = (data.user as any).theme;
        if (uTheme && themePalettes[uTheme] && uTheme !== activeTheme) {
          setActiveThemeState(uTheme);
        }
      }
      if (Array.isArray(data.taskFolders)) setTaskFolders(data.taskFolders);
      if (Array.isArray(data.habits)) setHabits(data.habits);
      if (Array.isArray(data.dailies)) setDailies(data.dailies);
      if (Array.isArray(data.quests)) setQuests(data.quests);
      if (Array.isArray(data.inventory)) setInventory(data.inventory);
      if (Array.isArray(data.userPets)) setUserPets(data.userPets);
      if (Array.isArray(data.achievements)) setAchievements(data.achievements);
      if (Array.isArray(data.sportLogs)) setSportLogs(data.sportLogs);
      if (Array.isArray(data.mealLogs)) setMealLogs(data.mealLogs);
      if (data.waterLog) setWaterLog(data.waterLog);
      if (Array.isArray(data.transactions)) setTransactions(data.transactions);
      if (Array.isArray(data.debts)) setDebts(data.debts);
      if (Array.isArray(data.savings)) setSavings(data.savings);
      if (Array.isArray(data.investments)) setInvestments(data.investments);
      if (Array.isArray(data.subscriptions)) setSubscriptions(data.subscriptions);
      if (Array.isArray(data.debtNotes)) setDebtNotes(data.debtNotes);
      if (Array.isArray(data.notes)) setNotes(data.notes);
      if (Array.isArray(data.noteFolders)) setNoteFolders(data.noteFolders);
      if (Array.isArray(data.reminders)) setReminders(data.reminders);
      if (Array.isArray(data.calendarNotes)) setCalendarNotes(data.calendarNotes);
      if (data.dailyTaskCounts && typeof data.dailyTaskCounts === 'object') setDailyTaskCounts(data.dailyTaskCounts);
      if (Array.isArray(data.healthLogs)) setHealthLogs(data.healthLogs);
      if (Array.isArray(data.pomodoroSessions)) setPomodoroSessions(data.pomodoroSessions);
      if (data.pomodoroStats && typeof data.pomodoroStats === 'object') setPomodoroStats(data.pomodoroStats);
      if (Array.isArray(data.notebooks)) setNotebooks(data.notebooks);
      if (data.loveSpace) setLoveSpace((prev) => ({ ...prev, ...data.loveSpace }));
      if (Array.isArray(data.friends)) setFriends(data.friends);
      if (Array.isArray(data.friendRequests)) setFriendRequests(data.friendRequests);
      if (Array.isArray(data.chatMessages)) setChatMessages(data.chatMessages);
      if (data.guild) setGuild((prev) => ({ ...prev, ...data.guild }));
      if (Array.isArray(data.pvpChallenges)) setPvpChallenges(data.pvpChallenges);
      if (data.lang === 'id' || data.lang === 'en') setLang(data.lang);
      applyBootstrapCatalogs(data);
      await loadMessages(data.lang === 'en' ? 'en' : 'id');
      setHydrated(true);
    } catch (e) {
      // P2: TIDAK ada lagi fallback data demo — tampilkan error gate (App.tsx).
      setApiError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  const lastServerDate = useRef<string>('');

  useEffect(() => {
    fetchBootstrap();
  }, [fetchBootstrap]);

  // ── Day-rollover heartbeat (parity TaskPage.load): bila app dibiarkan terbuka
  //    melewati tengah malam (zona app), server.date berubah → reset harian task
  //    harus dijalankan lagi. Dihitung lokal dari jam server (serverDateKey);
  //    jika tanggal berbeda dari bootstrap terakhir → re-bootstrap (reset done_today).
  useEffect(() => {
    const tick = () => {
      const key = serverDateKey();
      if (key && lastServerDate.current && key !== lastServerDate.current) {
        lastServerDate.current = key;
        fetchBootstrap();
      } else if (key && !lastServerDate.current) {
        lastServerDate.current = key;
      }
    };
    const t = window.setInterval(tick, 30000);
    // re-bootstrap sekali setelah 60s agar jam/offset tetap fresh
    const t2 = window.setTimeout(fetchBootstrap, 60000);
    return () => { window.clearInterval(t); window.clearTimeout(t2); };
  }, [fetchBootstrap, serverDateKey]);

  const retryBootstrap = useCallback(() => {
    fetchBootstrap();
  }, [fetchBootstrap]);

  // P2: localStorage hanya untuk PREFERENSI lokal (bukan data server).
  // Data user selalu hidup di SQLite dan dimuat ulang via bootstrap —
  // mencegah stale-state / dual persistence (gold lama muncul setelah reload).
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ lang, soundEnabled, activeTheme }));
    } catch {
      // Ignore storage errors
    }
  }, [lang, soundEnabled, activeTheme]);

  const showToast = useCallback((type: 'success' | 'damage' | 'level_up' | 'info' | 'boss', title: string, message: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // ── P2 Error policy: TIDAK ADA silent failure ─────────────────────────────
  // PyQt menampilkan dialog error saat aksi gagal (_show(...,"error")).
  // Versi web: setiap aksi API yang gagal memunculkan toast 'damage'.
  // Dedup 4 detik agar retry beruntun tidak membanjiri layar.
  const lastErrRef = useRef<{ key: string; at: number }>({ key: '', at: 0 });
  const notifyApiErr = useCallback((e: unknown) => {
    const msg = e instanceof Error ? e.message : String(e);
    const now = Date.now();
    if (lastErrRef.current.key === msg && now - lastErrRef.current.at < 4000) return;
    lastErrRef.current = { key: msg, at: now };
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, {
      id,
      type: 'damage',
      title: t('web_err_action', lang === 'id' ? 'Aksi gagal' : 'Action failed'),
      message: msg,
    }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((x) => x.id !== id));
    }, 5000);
  }, [lang]);

  const applyLive = useCallback((res: any) => {
    if (!res || !res.ok) return false;
    if (res.user) {
      setUser((prev) => ({
        ...prev,
        ...res.user,
        xpToNextLevel: res.user.xpToNextLevel || (res.user.level || 1) * 150,
      }));
    }
    if (res.pomodoroStats && typeof res.pomodoroStats === 'object') setPomodoroStats(res.pomodoroStats);
    if (Array.isArray(res.taskFolders)) setTaskFolders(res.taskFolders);
    if (Array.isArray(res.habits)) setHabits(res.habits);
    if (Array.isArray(res.dailies)) setDailies(res.dailies);
    if (Array.isArray(res.quests)) setQuests(res.quests);
    if (Array.isArray(res.inventory)) setInventory(res.inventory);
    if (Array.isArray(res.userPets)) setUserPets(res.userPets);
    if (Array.isArray(res.activeBuffs)) setActiveBuffs(res.activeBuffs);
    if (Array.isArray(res.achievements) && res.achievements.length) setAchievements(res.achievements);
    if (Array.isArray(res.sportLogs)) setSportLogs(res.sportLogs);
    if (Array.isArray(res.mealLogs)) setMealLogs(res.mealLogs);
    if (res.waterLog) setWaterLog(res.waterLog);
    if (Array.isArray(res.transactions)) setTransactions(res.transactions);
    if (Array.isArray(res.debts)) setDebts(res.debts);
    if (Array.isArray(res.savings)) setSavings(res.savings);
    if (Array.isArray(res.investments)) setInvestments(res.investments);
    if (Array.isArray(res.subscriptions)) setSubscriptions(res.subscriptions);
    if (Array.isArray(res.debtNotes)) setDebtNotes(res.debtNotes);
    if (Array.isArray(res.notes)) setNotes(res.notes);
    if (Array.isArray(res.noteFolders)) setNoteFolders(res.noteFolders);
    if (Array.isArray(res.reminders)) setReminders(res.reminders);
    if (Array.isArray(res.calendarNotes)) setCalendarNotes(res.calendarNotes);
    if (res.dailyTaskCounts && typeof res.dailyTaskCounts === 'object') setDailyTaskCounts(res.dailyTaskCounts);
    if (Array.isArray(res.healthLogs)) setHealthLogs(res.healthLogs);
    if (Array.isArray(res.pomodoroSessions)) setPomodoroSessions(res.pomodoroSessions);
    if (Array.isArray(res.notebooks)) setNotebooks(res.notebooks);
    if (res.loveSpace) setLoveSpace((prev) => ({ ...prev, ...res.loveSpace }));
    if (Array.isArray(res.friends)) setFriends(res.friends);
    if (Array.isArray(res.friendRequests)) setFriendRequests(res.friendRequests);
    if (Array.isArray(res.chatMessages)) setChatMessages(res.chatMessages);
    if (res.guild) setGuild((prev) => ({ ...prev, ...res.guild }));
    if (Array.isArray(res.pvpChallenges)) setPvpChallenges(res.pvpChallenges);
    if (res.activeBoss === null) {
      setActiveBoss(null);
      setActiveBossHp(0);
    } else if (res.activeBoss && typeof res.activeBoss === 'object') {
      setActiveBoss((prev) => ({
        id: res.activeBoss.id || prev?.id || '',
        name: res.activeBoss.name || prev?.name || '',
        icon: res.activeBoss.icon || prev?.icon || '🐉',
        tier: res.activeBoss.tier || prev?.tier || 'normal',
        hp: Number(res.activeBoss.maxHp || res.activeBoss.hp || prev?.hp || 0),
        maxHp: Number(res.activeBoss.maxHp || res.activeBoss.hp || prev?.maxHp || 0),
        atk: Number(res.activeBoss.atk || prev?.atk || 0),
        xpReward: Number(res.activeBoss.xpReward || prev?.xpReward || 0),
        goldReward: Number(res.activeBoss.goldReward || prev?.goldReward || 0),
        minLevel: Number(res.activeBoss.minLevel || prev?.minLevel || 1),
      }));
    }
    if (typeof res.activeBossHp === 'number') setActiveBossHp(res.activeBossHp);
    if (res.result && typeof res.result.boss_hp_left === 'number') setActiveBossHp(res.result.boss_hp_left);
    if (res.result?.defeated || res.result?.fled) {
      setActiveBoss(null);
      setActiveBossHp(0);
    }
    if (res.levelUp) {
      setLevelUpInfo({
        level: res.levelUp.level,
        hpGain: res.levelUp.hpGain,
        mpGain: res.levelUp.mpGain,
        goldGain: res.levelUp.goldGain,
      });
    }
    const msg = res.result?.msg;
    if (msg) showToast(res.levelUp ? 'level_up' : 'success', msg, '');
    return true;
  }, [showToast]);


  // Compute Active Buffs from Equipped Items & Active Pet
  const totalBuffs = React.useMemo(() => {
    const buffs = {
      xp_pct: 0,
      gold_pct: 0,
      boss_dmg: 0,
      hp_reduc: 0,
      block_chance: 0,
      block_strength: 0,
      crit_chance: 0,
    };

    // Item Buffs
    inventory.forEach((inv) => {
      if (inv.equipped) {
        const item = SHOP_ITEMS[inv.itemId];
        if (item && item.buff) {
          if (item.buff.xp_pct) buffs.xp_pct += item.buff.xp_pct;
          if (item.buff.gold_pct) buffs.gold_pct += item.buff.gold_pct;
          if (item.buff.boss_dmg) buffs.boss_dmg += item.buff.boss_dmg;
          if (item.buff.hp_reduc) buffs.hp_reduc += item.buff.hp_reduc;
          if (item.buff.block_chance) buffs.block_chance += item.buff.block_chance;
          if (item.buff.block_strength) buffs.block_strength += item.buff.block_strength;
          if (item.buff.crit_chance) buffs.crit_chance += item.buff.crit_chance;
        }
      }
    });

    // Pet Buffs
    const activePet = userPets.find((p) => p.isEquipped);
    if (activePet) {
      const petMeta = livePets()[activePet.petId];
      if (petMeta && petMeta.baseBuff) {
        const petLvlMultiplier = 1 + (activePet.level - 1) * 0.2;
        if (petMeta.baseBuff.xp_pct) buffs.xp_pct += Math.round(petMeta.baseBuff.xp_pct * petLvlMultiplier);
        if (petMeta.baseBuff.gold_pct) buffs.gold_pct += Math.round(petMeta.baseBuff.gold_pct * petLvlMultiplier);
        if (petMeta.baseBuff.boss_dmg) buffs.boss_dmg += Math.round(petMeta.baseBuff.boss_dmg * petLvlMultiplier);
        if (petMeta.baseBuff.hp_reduc) buffs.hp_reduc += Math.round(petMeta.baseBuff.hp_reduc * petLvlMultiplier);
      }
    }

    return buffs;
  }, [inventory, userPets]);

  // Update user stats with XP, Gold, HP, MP, and handle leveling up


  const closeLevelUpModal = useCallback(() => {
    setLevelUpInfo(null);
  }, []);



  const rebirthCharacter = useCallback(() => {
    apiPost<any>('/api/profile/rebirth', {}).then((res) => {
      applyLive(res);
      confetti({ particleCount: 120, spread: 90 });
    }).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const updateUserProfile = useCallback((profile: Partial<UserProfile>) => {
    setUser((prev) => ({
      ...prev,
      ...profile,
      displayName: profile.displayName || profile.name || prev.displayName,
      avatarEmoji: profile.avatarEmoji || profile.avatar || prev.avatarEmoji,
    }));
    showToast('success', 'Profile Updated', 'Your character details have been saved.');
  }, [showToast]);

  // Mark first-time onboarding complete (persists to SQLite via /api/settings and
  // refreshes the user object returned by the server).
  const completeOnboarding = useCallback(async (profile?: Partial<UserProfile>) => {
    let res: any;
    try {
      res = await apiPost<any>('/api/settings', { onboardingDone: true, ...profile });
    } catch {
      res = null;
    }
    setUser((prev) => ({
      ...prev,
      ...profile,
      ...(res?.user || {}),
      onboardingDone: true,
    }));
  }, []);

  // Tasks & Folders
  const addTaskFolder = useCallback((name: string, icon: string, color?: string, mode?: string) => {
    life.addTaskFolder({ name, icon, mode: mode || 'habit', color }).then((res) => applyLive(res)).catch(() => {
      const newFolder: TaskFolder = { id: `f_${Date.now()}`, name, icon, color: color || '#10b981' };
      setTaskFolders((prev) => [...prev, newFolder]);
    });
  }, [applyLive]);

  const deleteTaskFolder = useCallback((id: string, mode?: string) => {
    life.deleteTaskFolder(id, mode).then((res) => applyLive(res)).catch(() => setTaskFolders((prev) => prev.filter((f) => f.id !== id)));
  }, [applyLive]);

  const refreshFolders = useCallback(() => {
    apiGet<any>('/api/task-folders').then((d) => {
      if (Array.isArray(d?.taskFolders)) setTaskFolders(d.taskFolders);
    }).catch(() => undefined);
  }, []);

  const renameTaskFolder = useCallback((id: string, name: string, mode?: string) => {
    life.updateTaskFolder(id, { name, mode }).then((res) => {
      applyLive(res);
      refreshFolders();
    }).catch(() => undefined);
  }, [applyLive, refreshFolders]);

  const duplicateTaskFolder = useCallback((id: string, mode?: string) => {
    life.duplicateTaskFolder(id, mode).then((res) => {
      applyLive(res);
      refreshFolders();
    }).catch(() => undefined);
  }, [applyLive, refreshFolders]);

  // Habits
  const addHabit = useCallback((title: string, difficulty: TaskDifficulty, isPositive: boolean, isNegative: boolean, folderId?: string | null, notes?: string) => {
    rpg.addHabit({ title, difficulty, isPositive, isNegative, notes, folderId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const editHabit = useCallback((id: string, updates: Partial<Habit>) => {
    rpg.updateHabit(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setHabits((prev) => prev.map((h) => (h.id === id ? { ...h, ...updates } : h)));
    });
  }, [applyLive]);

  const duplicateHabit = useCallback((id: string) => {
    rpg.duplicateHabit(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  const deleteHabit = useCallback((id: string) => {
    setHabits((prev) => prev.filter((h) => h.id !== id));
    rpg.deleteHabit(id).then((res) => {
      const trashId = res?.result?.trash_id || res?.trash_id;
      if (trashId) {
        const label = habits.find((h) => h.id === id)?.title || '';
        setLastDelete({ trashId: String(trashId), label });
      }
      applyLive(res);
    }).catch(notifyApiErr);
  }, [applyLive, habits])

  const triggerHabit = useCallback((id: string, isPos: boolean) => {
    rpg.completeHabit(id, isPos).then((res) => {
      if (!applyLive(res)) return;
      const habit = habits.find((h) => h.id === id);
      if (habit) {
        showToast(isPos ? 'success' : 'damage', habit.title, res.result?.msg || '');
      }
    }).catch(notifyApiErr);
  }, [habits, applyLive, showToast])

  const reorderHabits = useCallback((ordered: Habit[]) => {
    setHabits(ordered);
    rpg.reorderTasks('habit', ordered.map((h) => ({ id: h.id, folderId: h.folderId })))
      .then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Dailies
  const addDaily = useCallback((title: string, difficulty: TaskDifficulty, repeatDays: number[], folderId?: string | null, notes?: string) => {
    rpg.addDaily({ title, difficulty, repeatDays, notes, folderId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const editDaily = useCallback((id: string, updates: Partial<Daily>) => {
    rpg.updateDaily(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setDailies((prev) => prev.map((d) => (d.id === id ? { ...d, ...updates } : d)));
    });
  }, [applyLive]);

  const duplicateDaily = useCallback((id: string) => {
    rpg.duplicateDaily(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  const deleteDaily = useCallback((id: string) => {
    setDailies((prev) => prev.filter((d) => d.id !== id));
    rpg.deleteDaily(id).then((res) => {
      const trashId = res?.result?.trash_id || res?.trash_id;
      if (trashId) {
        const label = dailies.find((d) => d.id === id)?.title || '';
        setLastDelete({ trashId: String(trashId), label });
      }
      applyLive(res);
    }).catch(notifyApiErr);
  }, [applyLive, dailies])

  const toggleDaily = useCallback((id: string) => {
    rpg.completeDaily(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const useDailyFreeze = useCallback((id: string) => {
    rpg.freezeDaily(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const failDaily = useCallback((id: string) => {
    rpg.failDaily(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  const reorderDailies = useCallback((ordered: Daily[]) => {
    setDailies(ordered);
    rpg.reorderTasks('daily', ordered.map((d) => ({ id: d.id, folderId: d.folderId })))
      .then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Quests / Todos
  const addQuest = useCallback((title: string, difficulty: TaskDifficulty, dueDate?: string | null, folderId?: string | null, notes?: string) => {
    rpg.addQuest({ title, difficulty, dueDate, notes, folderId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const editQuest = useCallback((id: string, updates: Partial<Quest>) => {
    rpg.updateQuest(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setQuests((prev) => prev.map((q) => (q.id === id ? { ...q, ...updates } : q)));
    });
  }, [applyLive]);

  const duplicateQuest = useCallback((id: string) => {
    rpg.duplicateQuest(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  const deleteQuest = useCallback((id: string) => {
    setQuests((prev) => prev.filter((q) => q.id !== id));
    rpg.deleteQuest(id).then((res) => {
      const trashId = res?.result?.trash_id || res?.trash_id;
      if (trashId) {
        const label = quests.find((q) => q.id === id)?.title || '';
        setLastDelete({ trashId: String(trashId), label });
      }
      applyLive(res);
    }).catch(notifyApiErr);
  }, [applyLive, quests])

  const toggleQuest = useCallback((id: string) => {
    rpg.completeQuest(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const reorderQuests = useCallback((ordered: Quest[]) => {
    setQuests(ordered);
    rpg.reorderTasks('quest', ordered.map((q) => ({ id: q.id, folderId: q.folderId })))
      .then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const moveTaskAcrossFolders = useCallback((mode: string, id: string, folderId: string | null) => {
    const fid = folderId || null;
    if (mode === 'habit') {
      setHabits((prev) => prev.map((h) => (h.id === id ? { ...h, folderId: fid } : h)));
      rpg.reorderTasks('habit', [{ id, folderId: fid }]).then((res) => applyLive(res)).catch(notifyApiErr);
    } else if (mode === 'daily') {
      setDailies((prev) => prev.map((d) => (d.id === id ? { ...d, folderId: fid } : d)));
      rpg.reorderTasks('daily', [{ id, folderId: fid }]).then((res) => applyLive(res)).catch(notifyApiErr);
    } else {
      setQuests((prev) => prev.map((q) => (q.id === id ? { ...q, folderId: fid } : q)));
      rpg.reorderTasks('quest', [{ id, folderId: fid }]).then((res) => applyLive(res)).catch(notifyApiErr);
    }
  }, [applyLive])

  const restoreTask = useCallback((trashId: string) => {
    rpg.restoreTask(trashId).then((res) => {
      if (applyLive(res)) {
        showToast('success', lang === 'id' ? 'Tugas dipulihkan' : 'Task restored', '');
      }
    }).catch(notifyApiErr);
  }, [applyLive, showToast, lang])

  const undoDelete = useCallback(() => {
    if (!lastDelete) return;
    const { trashId } = lastDelete;
    setLastDelete(null);
    restoreTask(trashId);
  }, [lastDelete, restoreTask])

  // Sport Tracker
  const addSportLog = useCallback((sportType: string, sportName: string, icon: string, durationMinutes: number, caloriesBurned: number, intensity: 'light' | 'moderate' | 'vigorous', notes?: string, difficulty?: string) => {
    life.addSport({ sportType, sportName, icon, durationMinutes, caloriesBurned, intensity, difficulty, notes, complete: false }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const updateSportLog = useCallback((id: string, body: Record<string, unknown>) => {
    life.updateSport(id, body).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const completeSportLog = useCallback((id: string) => {
    life.completeSport(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteSportLog = useCallback((id: string) => {
    life.deleteSport(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Nutrition
  const addMealLog = useCallback((mealType: 'breakfast' | 'lunch' | 'dinner' | 'snack', foodName: string, icon: string, portion: number, calories: number, protein: number, carbs: number, fat: number) => {
    life.logFood({ mealType, foodName, icon, portion, calories, protein, carbs, fat }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteMealLog = useCallback((id: string) => {
    life.deleteFoodLog(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const addWater = useCallback((amountMl: number) => {
    life.addWater(amountMl).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const resetWater = useCallback(() => {
    setWaterLog((prev) => ({ ...prev, amountMl: 0 }));
    life.resetWater().then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // Shop & Inventory & Crafting
  const buyItem = useCallback((itemId: string): boolean => {
    rpg.buyItem(itemId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
    return true;
  }, [applyLive, showToast])

  const sellItem = useCallback((itemId: string, quantity: number = 1) => {
    rpg.sellItem(itemId, quantity).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const useConsumable = useCallback((itemId: string): boolean => {
    rpg.useItem(itemId).then((res) => applyLive(res)).catch(notifyApiErr);
    return true;
  }, [applyLive])

  const equipItem = useCallback((itemId: string) => {
    rpg.equipItem(itemId, true).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const unequipItem = useCallback((itemId: string) => {
    rpg.equipItem(itemId, false).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const craftItem = useCallback((recipeResultId: string): boolean => {
    rpg.craftItem(recipeResultId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
    return true;
  }, [applyLive, showToast])

  const enchantItem = useCallback((itemId: string) => {
    rpg.enchantItem(itemId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast])

  // Pets
  const adoptPet = useCallback((petId: string, nickname?: string): boolean => {
    rpg.adoptPet(petId).then((res) => applyLive(res)).catch(notifyApiErr);
    return true;
  }, [applyLive])

  const feedPet = useCallback((petId: string) => {
    rpg.feedPet(petId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const trainPet = useCallback((petId: string) => {
    rpg.trainPet(petId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const equipPet = useCallback((petId: string) => {
    rpg.equipPet(petId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Parity PetsPage._unequip: lepas pet spesifik (tanpa fallback auto).
  const unequipPet = useCallback((petId: string) => {
    if (petId) rpg.unequipPet(petId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive, notifyApiErr])

  // Boss Combat
  const startBossFight = useCallback((bossId: string) => {
    const boss = BOSSES[bossId];
    if (boss) {
      setActiveBoss(boss);
      setActiveBossHp(boss.hp);
    }
    rpg.startBoss(bossId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const attackBoss = useCallback((action: string | boolean = 'light') => {
    const act = action === true ? 'heavy' : action === false ? 'light' : String(action || 'light');
    rpg.attackBoss(act).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const useClassSkill = useCallback(() => {
    rpg.useClassSkill().then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const fleeBoss = useCallback(() => {
    setActiveBoss(null);
    setActiveBossHp(0);
    rpg.fleeBoss().then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // Economy
  const addTransaction = useCallback((type: 'income' | 'expense', category: string, amount: number, notes?: string, folderId?: string | null, name?: string, date?: string) => {
    life.addEconomy({ type, category, amount, notes, folderId: folderId || undefined, name, date }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const moveTransaction = useCallback((id: string, folderId: string | null) => {
    life.moveEconomy(id, folderId).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteTransaction = useCallback((id: string) => {
    life.deleteEconomy(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const addDebt = useCallback((title: string, type: 'payable' | 'receivable', totalAmount: number, dueDate: string, notes?: string) => {
    life.addDebt({ title, type, totalAmount, dueDate, notes }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const payDebtInstallment = useCallback((id: string, amount: number) => {
    life.payDebt(id, amount).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteDebt = useCallback((id: string) => {
    life.deleteDebt(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const addSaving = useCallback((name: string, targetAmount: number, currentAmount?: number, targetDate?: string) => {
    life.addSaving({ name, targetAmount, currentAmount: currentAmount || 0, targetDate }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const addToSaving = useCallback((id: string, amount: number) => {
    life.addToSaving(id, amount).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const withdrawFromSaving = useCallback((id: string, amount: number) => {
    life.withdrawSaving(id, amount).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const deleteSaving = useCallback((id: string) => {
    life.deleteSaving(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const addInvestment = useCallback((name: string, amount: number, notes?: string) => {
    life.addInvestment({ name, amount, notes }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const collectInvestmentReturn = useCallback((id: string) => {
    life.investmentReturn(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const withdrawInvestment = useCallback((id: string) => {
    life.withdrawInvestment(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const addSubscription = useCallback((name: string, amount: number, dueDate: string, period?: string) => {
    life.addSubscription({ name, amount, dueDate, period: period || 'monthly' }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const renewSubscription = useCallback((id: string) => {
    life.renewSubscription(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const deleteSubscription = useCallback((id: string) => {
    life.deleteSubscription(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const addDebtNote = useCallback((personName: string, amount: number, date?: string, notes?: string) => {
    life.addDebtNote({ personName, amount, date, notes }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const settleDebtNote = useCallback((id: string) => {
    life.settleDebtNote(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const deleteDebtNote = useCallback((id: string) => {
    life.deleteDebtNote(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const applyTaskTemplate = useCallback((mode: string, key: string) => {
    life.applyTemplate(mode, key).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // Notes
  const updateNoteFolder = useCallback((id: string, updates: { name?: string; icon?: string }) => {
    life.updateNoteFolder(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive, notifyApiErr]);

  const duplicateNoteFolder = useCallback((id: string) => {
    life.duplicateNoteFolder(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive, notifyApiErr]);

  const addNoteFolder = useCallback((name: string, icon: string, parentId?: string | null) => {
    life.addNoteFolder({ name, icon, parentId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteNoteFolder = useCallback((id: string) => {
    life.deleteNoteFolder(id).then((res) => applyLive(res)).catch(() => setNoteFolders((prev) => prev.filter((f) => f.id !== id)));
  }, [applyLive]);

  const addNote = useCallback((title: string, content: string, folderId?: string | null) => {
    life.addNote({ title, content, folderId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const updateNote = useCallback((id: string, title: string, content: string, folderId?: string | null) => {
    life.updateNote(id, { title, content, folderId }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteNote = useCallback((id: string) => {
    life.deleteNote(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const archiveNote = useCallback((id: string, archived: boolean) => {
    life.archiveNote(id, archived).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  const duplicateNoteItem = useCallback((id: string) => {
    life.duplicateNote(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // Optimistic notes reorder (drag & drop within a folder), then persist to DB.
  const reorderNotes = useCallback((orderedIds: string[]) => {
    const idSet = new Set(orderedIds);
    setNotes((prev) => {
      const byId = new Map(prev.map((n) => [n.id, n]));
      const reordered = orderedIds
        .map((id) => byId.get(id))
        .filter((n): n is Note => Boolean(n));
      return [...reordered, ...prev.filter((n) => !idSet.has(n.id))];
    });
    rpg
      .reorderNotes(orderedIds.map((id) => ({ id })))
      .then((res) => applyLive(res))
      .catch(notifyApiErr);
  }, [applyLive]);

  // Health Metrics
  const addHealthLog = useCallback((steps: number, sleepHours: number, weightKg?: number, heartRate?: number, mood: 'great' | 'good' | 'neutral' | 'tired' | 'stressed' = 'good', notes?: string) => {
    life.addHealth({ steps, sleepHours, weightKg, heartRate, mood, notes }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const completePomodoroSession = useCallback((durationMinutes: number, label: string) => {
    life.completePomodoro(durationMinutes, label).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const [pomodoroStats, setPomodoroStats] = useState({ todaySessions: 0, todayMinutes: 0, totalSessions: 0, totalMinutes: 0 });

  // ── Pomodoro engine parity PomodoroPage ────────────────────────────────────
  // State machine idle→focus→(alert)→break→(alert)→idle. Timer memakai deadline
  // absolut (endsAt Ref) sehingga akurat walau komponen PomodoroView unmount atau
  // tab browser throttle — penyebab issue #7 (reset saat ganti halaman).
  interface PomoState {
    phase: 'idle' | 'focus' | 'break';
    paused: boolean;
    remainingSec: number;
    totalSec: number;
    focusMin: number;
    breakMin: number;
    taskLabel: string;
  }
  const [pomo, setPomo] = useState<PomoState>({
    phase: 'idle', paused: false, remainingSec: 25 * 60, totalSec: 25 * 60,
    focusMin: 25, breakMin: 5, taskLabel: '',
  });
  const [pomoAlert, setPomoAlert] = useState<{ phase: 'focus' | 'break'; title: string; msg: string } | null>(null);
  const pomoRef = useRef(pomo);
  pomoRef.current = pomo;
  const pomoDeadlineRef = useRef<number | null>(null);
  const pomoRemainingRef = useRef<number>(25 * 60);

  const pomoBeginPhase = useCallback((phase: 'focus' | 'break') => {
    const st = pomoRef.current;
    // parity _begin_phase: baca durasi dari "spin" yang sudah di-clamp range.
    const focusMin = Math.min(120, Math.max(5, Math.round(st.focusMin) || 25));
    const breakMin = Math.min(30, Math.max(1, Math.round(st.breakMin) || 5));
    const minutes = phase === 'focus' ? focusMin : breakMin;
    const total = minutes * 60;
    pomoDeadlineRef.current = Date.now() + total * 1000;
    pomoRemainingRef.current = total;
    setPomo((p) => ({ ...p, phase, paused: false, totalSec: total, remainingSec: total, focusMin, breakMin }));
  }, []);

  const pomoFinishFocus = useCallback(async () => {
    const st = pomoRef.current;
    pomoDeadlineRef.current = null;
    const minutes = Math.min(120, Math.max(5, Math.round(st.focusMin) || 25));
    let xp = 0, gold = 0, extra = '';
    try {
      const res = await life.completePomodoro(minutes, st.taskLabel.trim());
      applyLive(res);
      const r = (res as any)?.result || res || {};
      xp = Number(r.xp_gained || r.xpGained || 0);
      gold = Number(r.gold_gained || r.goldGained || 0);
      if (r.leveled_up && r.new_level) {
        extra = `\n🎉 ${i18nT('level_up_msg', 'Naik ke Level {lvl}!').replace('{lvl}', String(r.new_level))}`;
      }
    } catch { /* offline: pesan tanpa hadiah */ }
    const msg = i18nT('pomodoro_complete_msg', 'Kerja bagus! +{xp} XP, +{gold} G dari {mins} menit fokus.')
      .replace('{xp}', String(xp)).replace('{gold}', String(gold)).replace('{mins}', String(minutes)) + extra;
    // Alarm berulang sampai diakui; break DIMULAI setelah ack (parity PyQt).
    startPomoAlarm('focus');
    setPomoAlert({ phase: 'focus', title: i18nT('pomodoro_complete_title', 'Sesi Fokus Selesai! 🎉'), msg });
  }, [applyLive]);

  const pomoFinishBreak = useCallback(() => {
    pomoDeadlineRef.current = null;
    const st = pomoRef.current;
    const focusMin = Math.min(120, Math.max(5, Math.round(st.focusMin) || 25));
    const total = focusMin * 60;
    pomoRemainingRef.current = total;
    setPomo((p) => ({ ...p, phase: 'idle', paused: false, remainingSec: total, totalSec: total }));
    startPomoAlarm('break');
    setPomoAlert({
      phase: 'break',
      title: i18nT('pomodoro_break_done_title', 'Istirahat Selesai'),
      msg: i18nT('pomodoro_break_done', 'Istirahat selesai — tubuh dan pikiranmu sudah siap untuk fokus kembali.'),
    });
  }, []);

  // Interval tunggal hidup di provider — PERMANEN selama app jalan.
  useEffect(() => {
    const id = window.setInterval(() => {
      const st = pomoRef.current;
      if (st.phase === 'idle' || st.paused || !pomoDeadlineRef.current) return;
      const rem = Math.max(0, Math.ceil((pomoDeadlineRef.current - Date.now()) / 1000));
      if (rem <= 0) {
        const phase = st.phase;
        setPomo((p) => ({ ...p, remainingSec: 0 }));
        if (phase === 'focus') { void pomoFinishFocus(); } else { void pomoFinishBreak(); }
        return;
      }
      pomoRemainingRef.current = rem;
      setPomo((p) => (p.remainingSec === rem ? p : { ...p, remainingSec: rem }));
    }, 1000);
    return () => window.clearInterval(id);
  }, [pomoFinishFocus, pomoFinishBreak]);

  const pomoStart = useCallback(() => { pomoBeginPhase('focus'); }, [pomoBeginPhase]);
  const pomoPauseToggle = useCallback(() => {
    const st = pomoRef.current;
    if (st.phase === 'idle') return; // parity: pause tidak berlaku saat idle
    if (st.paused) {
      pomoDeadlineRef.current = Date.now() + pomoRemainingRef.current * 1000;
    } else {
      pomoRemainingRef.current = st.remainingSec;
      pomoDeadlineRef.current = null;
    }
    setPomo((p) => ({ ...p, paused: !p.paused }));
  }, []);
  const pomoReset = useCallback(() => {
    stopPomoAlarm();
    pomoDeadlineRef.current = null;
    const st = pomoRef.current;
    const focusMin = Math.min(120, Math.max(5, Math.round(st.focusMin) || 25));
    const total = focusMin * 60;
    pomoRemainingRef.current = total;
    setPomo((p) => ({ ...p, phase: 'idle', paused: false, remainingSec: total, totalSec: total }));
  }, []);
  const pomoGiveUp = useCallback(() => {
    if (pomoRef.current.phase === 'idle') return; // parity _give_up guard
    pomoReset();
  }, [pomoReset]);
  const pomoSetDurations = useCallback((focusMin: number, breakMin: number) => {
    const st = pomoRef.current;
    if (st.phase !== 'idle') return; // parity: spin disabled saat running
    const f = Math.min(120, Math.max(5, Math.round(focusMin) || 25));
    const b = Math.min(30, Math.max(1, Math.round(breakMin) || 5));
    pomoRemainingRef.current = f * 60;
    setPomo((p) => ({ ...p, focusMin: f, breakMin: b, remainingSec: f * 60, totalSec: f * 60 }));
  }, []);
  const pomoSetTask = useCallback((label: string) => {
    setPomo((p) => (p.phase === 'idle' ? { ...p, taskLabel: label } : p)); // parity: input disabled saat running
  }, []);
  const pomoAckAlert = useCallback(() => {
    const alert = pomoAlert;
    stopPomoAlarm();
    setPomoAlert(null);
    if (alert?.phase === 'focus') pomoBeginPhase('break'); // parity: break setelah akui
  }, [pomoAlert, pomoBeginPhase]);
  const pomoTestAlarm = useCallback(() => {
    startPomoAlarm('focus');
    window.setTimeout(stopPomoAlarm, 6000); // parity _test_alarm 6 detik
    showToast('info', i18nT('pomodoro_test_alarm', 'Uji Alarm Berulang'),
      i18nT('pomodoro_test_alarm_info', 'Alarm akan berulang selama 6 detik.'));
  }, [showToast]);

  // Achievements
  const claimAchievement = useCallback((id: string) => {
    rpg.claimAchievement(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Learning Notebook Actions
  const addNotebook = useCallback((title: string, description: string, icon: string = '📚') => {
    studio.addNotebook(title, description, icon).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const updateNotebook = useCallback((id: string, updates: Partial<LearningNotebook>) => {
    setNotebooks((prev) => prev.map((nb) => (nb.id === id ? { ...nb, ...updates } : nb)));
  }, []);

  const deleteNotebook = useCallback((id: string) => {
    studio.deleteNotebook(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const refreshNotebooks = useCallback(() => {
    studio.listNotebooks().then((res) => {
      if (res?.ok && Array.isArray(res.notebooks)) setNotebooks(res.notebooks);
    }).catch(notifyApiErr);
  }, [notifyApiErr]);

  const addNotebookSource = useCallback((notebookId: string, title: string, content: string, type: 'text' | 'doc' | 'pdf' | 'url' = 'text') => {
    studio.addSource(notebookId, title, content, type).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteNotebookSource = useCallback((notebookId: string, sourceId: string) => {
    studio.deleteSource(notebookId, sourceId).then((res) => applyLive(res)).catch(() => {
      setNotebooks((prev) =>
        prev.map((nb) => (nb.id === notebookId ? { ...nb, sources: nb.sources.filter((s) => s.id !== sourceId) } : nb))
      );
    });
  }, [applyLive]);

  const addNotebookChat = useCallback((notebookId: string, text: string, sender: 'user' | 'ai') => {
    if (sender !== 'user') return;
    studio.chat(notebookId, text).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Love Space Actions
  const updateLoveSpace = useCallback((updates: Partial<LoveSpaceData>) => {
    studio.updateLove(updates as Record<string, unknown>).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const addLoveMemory = useCallback((title: string, date: string, description: string, emoji: string) => {
    studio.addMemory(title, date, description, emoji).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const toggleLoveBucketItem = useCallback((id: string) => {
    studio.toggleBucket(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const answerLovePrompt = useCallback((promptId: string, answer: string) => {
    studio.lovePrompt({ id: promptId, answer }).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // Social & Guild Actions
  const sendChatMessage = useCallback((text: string, otherId?: string) => {
    studio.sendChat(text, otherId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const sendFriendRequest = useCallback((username: string) => {
    studio.friendRequest(username).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const acceptFriendRequest = useCallback((id: string) => {
    studio.acceptFriend(id).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const rejectFriendRequest = useCallback((id: string) => {
    studio.rejectFriend(id).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const respondPvpChallenge = useCallback((id: string, accept: boolean) => {
    studio.respondPvp(id, accept).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const approveGuildRequest = useCallback((id: string) => {
    studio.approveGuildRequest(id).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const rejectGuildRequest = useCallback((id: string) => {
    studio.rejectGuildRequest(id).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const updateLovePhotoMeta = useCallback((id: string, body: Record<string, unknown>) => {
    studio.lovePhotoMeta(id, body).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const sendPvpChallenge = useCallback((friendId: string) => {
    studio.sendPvp(friendId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const loveCheckin = useCallback((body: Record<string, unknown>) => {
    studio.loveCheckin(body).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const lovePhoto = useCallback((path: string) => {
    studio.lovePhoto(path).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const loveEvent = useCallback((body: Record<string, unknown>) => {
    studio.loveEvent(body).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const loveWeekly = useCallback((body: Record<string, unknown>) => {
    studio.loveWeekly(body).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const loveCycle = useCallback((body: Record<string, unknown>) => {
    studio.loveCycle(body).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  // --- LovePage parity ops (P5): delete handlers + album + favorit prompt ---
  const loveOp = useCallback((p: Promise<any>) => {
    p.then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [applyLive, showToast]);

  const refreshLoveSpace = useCallback(() => {
    studio.love().then((res) => {
      if (res?.loveSpace) setLoveSpace((prev) => ({ ...prev, ...res.loveSpace }));
    }).catch((e) => showToast('info', String(e?.message || e), ''));
  }, [showToast]);

  const deleteLoveMemory = useCallback((id: string) => loveOp(studio.deleteLoveMemory(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLovePrompt = useCallback((id: string) => loveOp(studio.deleteLovePrompt(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLoveWeekly = useCallback((id: string) => loveOp(studio.deleteLoveWeekly(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLoveCycle = useCallback((id: string) => loveOp(studio.deleteLoveCycle(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLoveEvent = useCallback((id: string) => loveOp(studio.deleteLoveEvent(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLoveBucket = useCallback((id: string) => loveOp(studio.deleteLoveBucket(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLovePhoto = useCallback((id: string) => loveOp(studio.deleteLovePhoto(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const lovePromptFavorite = useCallback((promptKey: string) => loveOp(studio.lovePromptFavorite(promptKey).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const createLoveAlbum = useCallback((name: string, scope: string) => loveOp(studio.createLoveAlbum({ name, scope }).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const renameLoveAlbum = useCallback((id: string, name: string) => loveOp(studio.renameLoveAlbum(id, name).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const deleteLoveAlbum = useCallback((id: string) => loveOp(studio.deleteLoveAlbum(id).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const loveAlbumAddPhoto = useCallback((albumId: string, photoId: string) => loveOp(studio.loveAlbumAddPhoto(albumId, photoId).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const loveAlbumMovePhoto = useCallback((albumId: string, photoId: string, sourceAlbumId?: string | null) => loveOp(studio.loveAlbumMovePhoto(albumId, photoId, sourceAlbumId).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);
  const loveAlbumRemovePhoto = useCallback((albumId: string, photoId: string) => loveOp(studio.loveAlbumRemovePhoto(albumId, photoId).then((r) => { refreshLoveSpace(); return r; })), [loveOp, refreshLoveSpace]);

  const refreshSocial = useCallback(() => {
    Promise.all([studio.friends(), studio.guild(), studio.pvp(), studio.love()])
      .then(([f, g, p, l]) => {
        applyLive({
          ok: true,
          friends: f.friends,
          friendRequests: f.friendRequests,
          guild: g.guild,
          pvpChallenges: p.pvpChallenges,
          loveSpace: l.loveSpace,
        });
      })
      .catch(() => undefined);
  }, [applyLive]);

  const attackGuildBoss = useCallback((action: 'light' | 'heavy' | 'block' | 'ultimate' = 'light') => {
    studio.attackGuildBoss(action).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const claimPvPReward = useCallback((id: string) => {
    studio.claimPvp(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  // Calendar Reminders
  const addReminder = useCallback((payload: { title: string; description?: string; reminderDatetime: string; repeat?: 'none' | 'daily' | 'weekly' | 'custom'; repeatDays?: string; soundType?: 'default' | 'beep1' | 'beep2' | 'custom'; soundFile?: string }) => {
    life.addReminder(payload).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])
  const editReminder = useCallback((id: string, payload: { title: string; description?: string; reminderDatetime: string; repeat?: 'none' | 'daily' | 'weekly' | 'custom'; repeatDays?: string; soundType?: 'default' | 'beep1' | 'beep2' | 'custom'; soundFile?: string }) => {
    life.updateReminder(id, payload).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const toggleReminder = useCallback((id: string) => {
    life.toggleReminder(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const deleteReminder = useCallback((id: string) => {
    life.deleteReminder(id).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive])

  const saveCalendarNote = useCallback((date: string, note: string) => {
    life.saveCalendarNote(date, note).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);
  const deleteCalendarNote = useCallback((date: string) => {
    life.deleteCalendarNote(date).then((res) => applyLive(res)).catch(notifyApiErr);
  }, [applyLive]);

  // ── Phase P8: Reminder auto-trigger (sound + toast) — parity dengan RemindersPage PyQt ──
  // Parity MainWindow._check_reminders (QTimer 5 detik → web poling tiap 10
  // detik ke GET /api/reminders/due). Reminder yang due dibunyikan sebagai
  // ALARM LOOP (beep tiap 2 detik / MP3 custom loop) sampai pengguna menekan
  // OK (dismissReminderAlarm) — lalu POST /trigger per reminder agar server
  // menjadwalkan ulang repeat (logika jadwal tetap di Python, parity db).
  const dueAlarmRef = useRef<any[]>([])
  const [alarmDue, setAlarmDue] = useState<any[]>([])
  const alarmLockRef = useRef(false)
  const dismissReminderAlarm = useCallback(() => {
    stopReminderLoop()
    const dueList = dueAlarmRef.current
    dueAlarmRef.current = []
    setAlarmDue([])
    alarmLockRef.current = false
    for (const r of dueList) {
      life.triggerReminder(r.id).then((res) => applyLive(res)).catch(() => { /* abaikan */ })
    }
  }, [applyLive])
  useEffect(() => {
    const poll = () => {
      life.dueReminders().then((res) => {
        const dueList = (res?.due as any[]) || []
        if (!dueList.length) return
        // kunci: satu alarm aktif; reminder berikutnya ikut antre (parity dialog berurut)
        if (alarmLockRef.current) return
        alarmLockRef.current = true
        dueAlarmRef.current = dueList
        setAlarmDue(dueList)
        const first = dueList[0]
        // File streaming lewat /music/stream (route yang sama seperti MusicPage web).
        const fileUrl = first.soundFile ? `/music/stream?path=${encodeURIComponent(first.soundFile)}` : undefined
        startReminderLoop(first.sound, fileUrl)
        const titles = dueList.map((r: any) => r.title).join(', ') || (lang === 'id' ? 'Pengingat' : 'Reminder')
        showToast('info', '⏰ ' + titles, lang === 'id' ? 'Alarm berbunyi — tekan OK untuk menghentikan.' : 'Alarm ringing — press OK to stop.')
      }).catch(() => { /* server tidak tersedia */ })
    }
    poll()
    const id = setInterval(poll, 10000)
    return () => { clearInterval(id); stopReminderLoop(); }
  }, [showToast, lang])


  // JSON Export / Import / Reset
  const exportDataJson = useCallback(() => {
    const fullData = {
      user,
      taskFolders,
      habits,
      dailies,
      quests,
      sportLogs,
      mealLogs,
      waterLog,
      inventory,
      userPets,
      transactions,
      debts,
      noteFolders,
      notes,
      healthLogs,
      pomodoroSessions,
      achievements,
      exportDate: new Date().toISOString(),
    };
    return JSON.stringify(fullData, null, 2);
  }, [
    user,
    taskFolders,
    habits,
    dailies,
    quests,
    sportLogs,
    mealLogs,
    waterLog,
    inventory,
    userPets,
    transactions,
    debts,
    noteFolders,
    notes,
    healthLogs,
    pomodoroSessions,
    achievements,
  ]);

  const importDataJson = useCallback((jsonStr: string): boolean => {
    try {
      const data = JSON.parse(jsonStr);
      if (data.user) setUser(data.user);
      if (data.habits) setHabits(data.habits);
      if (data.dailies) setDailies(data.dailies);
      if (data.quests) setQuests(data.quests);
      if (data.inventory) setInventory(data.inventory);
      if (data.userPets) setUserPets(data.userPets);
      if (data.sportLogs) setSportLogs(data.sportLogs);
      if (data.mealLogs) setMealLogs(data.mealLogs);
      if (data.transactions) setTransactions(data.transactions);
      if (data.notes) setNotes(data.notes);
      showToast('success', 'Data Restored', 'Game progress successfully imported!');
      return true;
    } catch {
      showToast('damage', 'Invalid Backup File', 'Could not parse JSON save file.');
      return false;
    }
  }, [showToast]);

  // Parity SettingsPage._reset_progress PyQt: verifikasi password di server,
  // db.reset_user_progress, lalu paksa reload agar kembali ke login/bootstrap bersih.
  const resetAllData = useCallback(async (password?: string): Promise<boolean> => {
    try {
      const res = await apiPost<any>('/api/tracker/reset', { password: password || '' });
      if (!res?.ok) return false;
      localStorage.removeItem(STORAGE_KEY);
      window.location.reload();
      return true;
    } catch {
      notifyApiErr(new Error('wrong_password'));
      return false;
    }
  }, [notifyApiErr]);

  return (
    <GameContext.Provider
      value={{
        user,
        setUser,
        applyLive,
        updateUserProfile,
        completeOnboarding,
        rebirthCharacter,
        hydrated,
        apiError,
        retryBootstrap,
        lang,
        setLang,
        soundEnabled,
        setSoundEnabled,
        activeTheme,
        setActiveTheme,
        themePalettes,
        activePalette,
        serverNow,
        clockNow,
        nowDate,
        today,
        serverClockOffsetMs,
        taskFolders,
        addTaskFolder,
        renameTaskFolder,
        duplicateTaskFolder,
        deleteTaskFolder,
        habits,
        addHabit,
        editHabit,
        duplicateHabit,
        deleteHabit,
        triggerHabit,
        reorderHabits,
        moveTaskAcrossFolders,
        restoreTask,
        lastDelete,
        undoDelete,
        dailies,
        addDaily,
        editDaily,
        duplicateDaily,
        deleteDaily,
        toggleDaily,
        failDaily,
        useDailyFreeze,
        reorderDailies,
        quests,
        addQuest,
        editQuest,
        duplicateQuest,
        deleteQuest,
        toggleQuest,
        reorderQuests,
        sportLogs,
        addSportLog,
        updateSportLog,
        completeSportLog,
        deleteSportLog,
        mealLogs,
        addMealLog,
        deleteMealLog,
        waterLog,
        addWater,
        resetWater,
        inventory,
        buyItem,
        sellItem,
        useConsumable,
        equipItem,
        unequipItem,
        craftItem,
        enchantItem,
        userPets,
        adoptPet,
        feedPet,
        trainPet,
        equipPet,
        unequipPet,
        activeBoss,
        activeBossHp,
        startBossFight,
        attackBoss,
        fleeBoss,
        useClassSkill,
        transactions,
        addTransaction,
        deleteTransaction,
        moveTransaction,
        debts,
        addDebt,
        payDebtInstallment,
        deleteDebt,
        savings,
        addSaving,
        addToSaving,
        withdrawFromSaving,
        deleteSaving,
        investments,
        addInvestment,
        collectInvestmentReturn,
        withdrawInvestment,
        subscriptions,
        addSubscription,
        renewSubscription,
        deleteSubscription,
        debtNotes,
        addDebtNote,
        settleDebtNote,
        deleteDebtNote,
        applyTaskTemplate,
        noteFolders,
        addNoteFolder,
        deleteNoteFolder,
        updateNoteFolder,
        duplicateNoteFolder,
        notes,
        addNote,
        updateNote,
        deleteNote,
        archiveNote,
        duplicateNoteItem,
        reorderNotes,
        healthLogs,
        addHealthLog,
        pomodoroSessions,
        completePomodoroSession,
        pomodoroStats,
        pomo, pomoAlert, pomoStart, pomoPauseToggle, pomoReset, pomoGiveUp,
        pomoSetDurations, pomoSetTask, pomoAckAlert, pomoTestAlarm,
        achievements,
        claimAchievement,
        notebooks,
        addNotebook,
        updateNotebook,
        deleteNotebook,
        refreshNotebooks,
        addNotebookSource,
        deleteNotebookSource,
        addNotebookChat,
        loveSpace,
        updateLoveSpace,
        addLoveMemory,
        toggleLoveBucketItem,
        answerLovePrompt,
        friends,
        chatMessages,
        sendChatMessage,
        sendFriendRequest,
        acceptFriendRequest,
        rejectFriendRequest,
        respondPvpChallenge,
        approveGuildRequest,
        rejectGuildRequest,
        updateLovePhotoMeta,
        refreshLoveSpace,
        deleteLoveMemory,
        deleteLovePrompt,
        deleteLoveWeekly,
        deleteLoveCycle,
        deleteLoveEvent,
        deleteLoveBucket,
        deleteLovePhoto,
        lovePromptFavorite,
        createLoveAlbum,
        renameLoveAlbum,
        deleteLoveAlbum,
        loveAlbumAddPhoto,
        loveAlbumMovePhoto,
        loveAlbumRemovePhoto,
        friendRequests,
        sendPvpChallenge,
        loveCheckin,
        lovePhoto,
        loveEvent,
        loveWeekly,
        loveCycle,
        refreshSocial,
        guild,
        attackGuildBoss,
        pvpChallenges,
        claimPvPReward,
        reminders,
        addReminder,
        editReminder,
        dismissReminderAlarm,
        toggleReminder,
        deleteReminder,
        calendarNotes,
        saveCalendarNote,
        deleteCalendarNote,
        dailyTaskCounts,
        levelUpInfo,
        closeLevelUpModal,
        toasts,
        removeToast,
        showToast,
        activeBuffs,
        totalBuffs,
        exportDataJson,
        importDataJson,
        resetAllData,
      }}
    >
      {children}
      {alarmDue.length > 0 && (
        <div className="fixed inset-0 z-[95] bg-slate-950/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-amber-500/60 rounded-2xl p-6 w-full max-w-md text-center space-y-4 shadow-2xl shadow-amber-500/20">
            <div className="text-4xl animate-pulse">⏰</div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {alarmDue.map((r: any) => (
                <div key={r.id}>
                  <div className="text-base font-black text-slate-100">{r.title}</div>
                  {r.description ? <div className="text-xs text-slate-400">{r.description}</div> : null}
                  <div className="text-[11px] text-slate-500 font-mono">{(r.datetime || '').slice(0, 16).replace('T', ' ')}</div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={dismissReminderAlarm}
              className="w-full py-3 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-sm"
            >
              {lang === 'id' ? 'OK — Hentikan Alarm' : 'OK — Stop Alarm'}
            </button>
          </div>
        </div>
      )}
      {/* Alert fase Pomodoro global: timer bisa selesai di halaman mana pun
          (parity _show_phase_alert + alarm loop sampai diakui). */}
      {pomoAlert && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-[90] flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl p-8 max-w-md w-full space-y-5 shadow-2xl text-center">
            <div className="text-4xl">{pomoAlert.phase === 'focus' ? '✓' : '☕'}</div>
            <h3 className="text-lg font-black text-slate-100">{pomoAlert.title}</h3>
            <p className="text-sm text-slate-300 whitespace-pre-wrap">{pomoAlert.msg}</p>
            <button
              onClick={pomoAckAlert}
              className="w-full py-3 rounded-2xl bg-violet-600 hover:bg-violet-500 text-white font-bold text-sm transition-colors"
            >
              {pomoAlert.phase === 'focus'
                ? i18nT('pomodoro_start_break', 'Mulai Istirahat')
                : i18nT('pomodoro_back_to_focus', 'Siap Fokus Lagi')}
            </button>
          </div>
        </div>
      )}
    </GameContext.Provider>
  );
};

export const useGame = () => {
  const context = useContext(GameContext);
  if (!context) {
    throw new Error('web_use_game_error');
  }
  return context;
};
