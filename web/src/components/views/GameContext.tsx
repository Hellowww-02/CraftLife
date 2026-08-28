import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
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
  InvestmentItem,
  SubscriptionItem,
  DebtNote,
  NoteFolder,
  Note,
  Achievement,
  HealthMetricLog,
  PomodoroSession,
  TaskDifficulty,
  AvatarClass,
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
  INITIAL_ACHIEVEMENTS,
  AVATAR_CLASSES,
  CRAFT_RECIPES,
} from '../data/gameData';
import { DEFAULT_NOTEBOOKS } from '../data/learningSampleData';
import { apiGet, apiPost } from '../api/client';
import { rpg } from '../api/rpg';
import { life } from '../api/life';
import { studio } from '../api/studio';
import { loadMessages } from '../i18n';
import { applyBootstrapCatalogs, liveShopItems, livePets } from '../data/liveCatalog';
import {
  DEFAULT_LOVE_SPACE,
  DEFAULT_FRIENDS,
  DEFAULT_CHAT_MESSAGES,
  DEFAULT_GUILD,
  DEFAULT_PVP_CHALLENGES,
} from '../data/socialSampleData';

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
  updateUserStats: (xpDelta: number, goldDelta: number, hpDelta?: number, mpDelta?: number) => void;
  updateUserProfile: (profile: Partial<UserProfile>) => void;
  rebirthCharacter: () => void;
  changeAvatarClass: (newClass: AvatarClass) => void;

  // Language & Settings
  lang: 'id' | 'en';
  setLang: (lang: 'id' | 'en') => void;
  soundEnabled: boolean;
  setSoundEnabled: React.Dispatch<React.SetStateAction<boolean>>;
  activeTheme: 'dark' | 'emerald' | 'amber' | 'slate';
  setActiveTheme: (theme: 'dark' | 'emerald' | 'amber' | 'slate') => void;

  // Folders
  taskFolders: TaskFolder[];
  addTaskFolder: (name: string, icon: string, color?: string, mode?: string) => void;
  deleteTaskFolder: (id: string, mode?: string) => void;

  // Habits
  habits: Habit[];
  addHabit: (title: string, difficulty: TaskDifficulty, isPositive: boolean, isNegative: boolean, folderId?: string | null, notes?: string) => void;
  editHabit: (id: string, updates: Partial<Habit>) => void;
  duplicateHabit: (id: string) => void;
  deleteHabit: (id: string) => void;
  triggerHabit: (id: string, isPos: boolean) => void;
  reorderHabits: (ordered: Habit[]) => void;
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
  addSportLog: (sportType: string, sportName: string, icon: string, durationMinutes: number, caloriesBurned: number, intensity: 'light' | 'moderate' | 'vigorous', notes?: string) => void;
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
  sellItem: (itemId: string) => void;
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
  unequipPet: () => void;

  // Boss Combat
  activeBoss: Boss | null;
  activeBossHp: number;
  startBossFight: (bossId: string) => void;
  attackBoss: (action?: string | boolean) => void;
  fleeBoss: () => void;
  useClassSkill: () => void;

  // Economy & Budget
  transactions: Transaction[];
  addTransaction: (type: 'income' | 'expense', category: string, amount: number, notes?: string) => void;
  deleteTransaction: (id: string) => void;
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
  notes: Note[];
  addNote: (title: string, content: string, folderId?: string | null) => void;
  archiveNote: (id: string, archived: boolean) => void;
  duplicateNoteItem: (id: string) => void;
  updateNote: (id: string, title: string, content: string, folderId?: string | null) => void;
  deleteNote: (id: string) => void;

  // Health Metrics & Pomodoro
  healthLogs: HealthMetricLog[];
  addHealthLog: (steps: number, sleepHours: number, weightKg?: number, heartRate?: number, mood?: 'great' | 'good' | 'neutral' | 'tired' | 'stressed', notes?: string) => void;
  pomodoroSessions: PomodoroSession[];
  completePomodoroSession: (durationMinutes: number, label: string) => void;

  // Achievements
  achievements: Achievement[];
  claimAchievement: (id: string) => void;

  // Learning & AI Workspace (NotebookLM)
  notebooks: LearningNotebook[];
  addNotebook: (title: string, description: string, icon?: string) => void;
  updateNotebook: (id: string, updates: Partial<LearningNotebook>) => void;
  deleteNotebook: (id: string) => void;
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
  refreshSocial: () => void;
  guild: GuildData;
  attackGuildBoss: (damage: number) => void;
  pvpChallenges: PvPChallenge[];
  claimPvPReward: (id: string) => void;

  // Calendar & Reminders
  reminders: ReminderItem[];
  addReminder: (title: string, time: string, repeat?: 'none' | 'daily' | 'weekdays' | 'weekly', sound?: 'beep' | 'bell' | 'magic' | 'fanfare') => void;
  toggleReminder: (id: string) => void;
  deleteReminder: (id: string) => void;
  calendarNotes: { date: string; note: string }[];
  saveCalendarNote: (date: string, note: string) => void;

  // Level Up Celebrations & Toasts
  levelUpInfo: { level: number; hpGain: number; mpGain: number; goldGain: number } | null;
  closeLevelUpModal: () => void;
  toasts: NotificationToast[];
  removeToast: (id: string) => void;
  showToast: (type: 'success' | 'damage' | 'level_up' | 'info' | 'boss', title: string, message: string) => void;

  // Calculated Stats
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
  resetAllData: () => void;
}

const STORAGE_KEY = 'craftlife_app_data_v1';

const defaultUser: UserProfile = {
  id: 'user_default',
  username: 'steve',
  displayName: 'Steve The Miner',
  bio: 'Turning daily routines into legendary quests!',
  avatarClass: 'warrior',
  avatarEmoji: '⚔️',
  avatarColor: '#ef4444',
  level: 1,
  xp: 0,
  xpToNextLevel: 100,
  hp: 100,
  maxHp: 100,
  mp: 50,
  maxMp: 50,
  gold: 80,
  gems: 5,
  rebirthCount: 0,
  sportLevel: 1,
  sportXp: 0,
  activePetId: null,
  equippedWeapon: null,
  equippedArmor: null,
  equippedTool: null,
  equippedLegendary: null,
  freezeSlots: 1,
  createdAt: new Date().toISOString(),
};

const defaultFolders: TaskFolder[] = [
  { id: 'f_health', name: 'Health & Fitness', icon: '💪', color: '#10b981' },
  { id: 'f_work', name: 'Work & Study', icon: '📚', color: '#3b82f6' },
  { id: 'f_lifestyle', name: 'Mindset & Habits', icon: '✨', color: '#8b5cf6' },
];

const defaultHabits: Habit[] = [
  {
    id: 'h_water',
    title: 'Drink 2L Water Daily',
    notes: 'Stay hydrated for high energy',
    folderId: 'f_health',
    difficulty: 'easy',
    isPositive: true,
    isNegative: false,
    positiveStreak: 4,
    negativeStreak: 0,
    history: [],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'h_read',
    title: 'Read 15 mins of a Book',
    notes: 'Expand wisdom and focus',
    folderId: 'f_work',
    difficulty: 'medium',
    isPositive: true,
    isNegative: false,
    positiveStreak: 2,
    negativeStreak: 0,
    history: [],
    createdAt: new Date().toISOString(),
  },
  {
    id: 'h_junkfood',
    title: 'Late Night Sugary Snacks',
    notes: 'Avoid empty calories after 9pm',
    folderId: 'f_health',
    difficulty: 'medium',
    isPositive: false,
    isNegative: true,
    positiveStreak: 0,
    negativeStreak: 1,
    history: [],
    createdAt: new Date().toISOString(),
  },
];

const defaultDailies: Daily[] = [
  {
    id: 'd_morning',
    title: 'Morning 10-Minute Stretch & Pushups',
    notes: 'Awaken muscles and spine',
    folderId: 'f_health',
    difficulty: 'easy',
    streak: 5,
    isCompletedToday: false,
    repeatDays: [0, 1, 2, 3, 4, 5, 6],
    lastCompletedDate: null,
    isFrozen: false,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'd_plan',
    title: 'Plan Daily Priority Objectives',
    notes: 'Organize top 3 tasks for the day',
    folderId: 'f_work',
    difficulty: 'medium',
    streak: 3,
    isCompletedToday: false,
    repeatDays: [1, 2, 3, 4, 5],
    lastCompletedDate: null,
    isFrozen: false,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'd_sleep',
    title: 'Sleep Before 11:30 PM',
    notes: 'Deep 8-hour restoration sleep',
    folderId: 'f_lifestyle',
    difficulty: 'hard',
    streak: 2,
    isCompletedToday: false,
    repeatDays: [0, 1, 2, 3, 4, 5, 6],
    lastCompletedDate: null,
    isFrozen: false,
    createdAt: new Date().toISOString(),
  },
];

const defaultQuests: Quest[] = [
  {
    id: 'q_project',
    title: 'Finalize CraftLife Web Architecture',
    notes: 'Complete responsive React UI with game engine integration',
    folderId: 'f_work',
    difficulty: 'hard',
    dueDate: new Date(Date.now() + 86400000 * 2).toISOString().split('T')[0],
    isCompleted: false,
    completedAt: null,
    createdAt: new Date().toISOString(),
  },
  {
    id: 'q_clean',
    title: 'Declutter workspace desk',
    notes: 'Clear monitors and cables',
    folderId: 'f_lifestyle',
    difficulty: 'easy',
    dueDate: null,
    isCompleted: false,
    completedAt: null,
    createdAt: new Date().toISOString(),
  },
];

const defaultSportLogs: SportLog[] = [
  {
    id: 'sp_1',
    sportType: 'running',
    sportName: 'Morning Jogging',
    icon: '🏃',
    durationMinutes: 30,
    caloriesBurned: 280,
    intensity: 'moderate',
    notes: '5km park loop',
    date: new Date().toISOString().split('T')[0],
    sportXpEarned: 75,
  },
];

const defaultMeals: MealLog[] = [
  {
    id: 'm_1',
    mealType: 'breakfast',
    foodName: 'Oatmeal & Boiled Eggs',
    icon: '🥣',
    portion: 1,
    calories: 320,
    protein: 18,
    carbs: 35,
    fat: 9,
    date: new Date().toISOString().split('T')[0],
  },
];

const defaultWater: WaterLog = {
  date: new Date().toISOString().split('T')[0],
  amountMl: 1250,
  targetMl: 2500,
};

const defaultTransactions: Transaction[] = [
  {
    id: 'tx_1',
    type: 'income',
    category: 'Salary / Project',
    amount: 1500000,
    date: new Date().toISOString().split('T')[0],
    notes: 'Monthly milestone reward',
  },
  {
    id: 'tx_2',
    type: 'expense',
    category: 'Food & Groceries',
    amount: 125000,
    date: new Date().toISOString().split('T')[0],
    notes: 'Healthy pantry restocking',
  },
];

const defaultNotes: Note[] = [
  {
    id: 'n_1',
    folderId: null,
    title: '✨ Welcome to CraftLife',
    content: `# CraftLife Adventurer Manual
Welcome to your gamified productivity realm!
- **Habits**: Train positive habits (+) and extinguish negative ones (-).
- **Dailies**: Complete your recurring daily routine to maintain streaks and deal extra boss damage.
- **Quests**: Tackle your to-do lists for large Gold & XP bounties.
- **Sport & Nutrition**: Log your workouts, calories, macros, and daily water goals.
- **RPG Forge & Shop**: Buy weapons, craft legendary gear, adopt pets, and defeat mighty dungeon bosses!`,
    isPinned: true,
    isArchived: false,
    updatedAt: new Date().toISOString(),
  },
];

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

  const [user, setUser] = useState<UserProfile>(saved?.user || defaultUser);
  const [lang, setLang] = useState<'id' | 'en'>(saved?.lang || 'en');
  const [soundEnabled, setSoundEnabled] = useState<boolean>(saved?.soundEnabled !== undefined ? saved.soundEnabled : true);
  const [activeTheme, setActiveTheme] = useState<'dark' | 'emerald' | 'amber' | 'slate'>(saved?.activeTheme || 'dark');
  const [taskFolders, setTaskFolders] = useState<TaskFolder[]>(saved?.taskFolders || defaultFolders);
  const [habits, setHabits] = useState<Habit[]>(saved?.habits || defaultHabits);
  const [dailies, setDailies] = useState<Daily[]>(saved?.dailies || defaultDailies);
  const [quests, setQuests] = useState<Quest[]>(saved?.quests || defaultQuests);
  const [sportLogs, setSportLogs] = useState<SportLog[]>(saved?.sportLogs || defaultSportLogs);
  const [mealLogs, setMealLogs] = useState<MealLog[]>(saved?.mealLogs || defaultMeals);
  const [waterLog, setWaterLog] = useState<WaterLog>(saved?.waterLog || defaultWater);
  const [inventory, setInventory] = useState<InventoryItem[]>(saved?.inventory || [
    { itemId: 'wooden_sword', quantity: 1, equipped: true },
    { itemId: 'health_potion', quantity: 2, equipped: false },
    { itemId: 'ice_block', quantity: 1, equipped: false },
  ]);
  const [userPets, setUserPets] = useState<UserPet[]>(saved?.userPets || [
    { petId: 'wolf', nickname: 'Fang', level: 1, xp: 20, hunger: 90, isEquipped: true, adoptedAt: new Date().toISOString() },
  ]);
  const [activeBoss, setActiveBoss] = useState<Boss | null>(saved?.activeBoss || null);
  const [activeBossHp, setActiveBossHp] = useState<number>(saved?.activeBossHp !== undefined ? saved.activeBossHp : 0);
  const [transactions, setTransactions] = useState<Transaction[]>(saved?.transactions || defaultTransactions);
  const [debts, setDebts] = useState<Debt[]>(saved?.debts || []);
  const [savings, setSavings] = useState<SavingGoal[]>([]);
  const [investments, setInvestments] = useState<InvestmentItem[]>([]);
  const [subscriptions, setSubscriptions] = useState<SubscriptionItem[]>([]);
  const [debtNotes, setDebtNotes] = useState<DebtNote[]>([]);
  const [noteFolders, setNoteFolders] = useState<NoteFolder[]>(saved?.noteFolders || []);
  const [notes, setNotes] = useState<Note[]>(saved?.notes || defaultNotes);
  const [healthLogs, setHealthLogs] = useState<HealthMetricLog[]>(saved?.healthLogs || []);
  const [pomodoroSessions, setPomodoroSessions] = useState<PomodoroSession[]>(saved?.pomodoroSessions || []);
  const [achievements, setAchievements] = useState<Achievement[]>(saved?.achievements || INITIAL_ACHIEVEMENTS);

  // New modules
  const [notebooks, setNotebooks] = useState<LearningNotebook[]>(saved?.notebooks || DEFAULT_NOTEBOOKS);
  const [loveSpace, setLoveSpace] = useState<LoveSpaceData>(saved?.loveSpace || DEFAULT_LOVE_SPACE);
  const [friends, setFriends] = useState<FriendUser[]>(saved?.friends || DEFAULT_FRIENDS);
  const [friendRequests, setFriendRequests] = useState<FriendRequest[]>(saved?.friendRequests || []);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(saved?.chatMessages || DEFAULT_CHAT_MESSAGES);
  const [guild, setGuild] = useState<GuildData>(saved?.guild || DEFAULT_GUILD);
  const [pvpChallenges, setPvpChallenges] = useState<PvPChallenge[]>(saved?.pvpChallenges || DEFAULT_PVP_CHALLENGES);
  const [reminders, setReminders] = useState<ReminderItem[]>(saved?.reminders || [
    { id: 'rem_1', title: 'Morning Hydration & Routine Check', time: '08:00', repeat: 'daily', isActive: true, sound: 'bell' },
    { id: 'rem_2', title: 'Guild Boss Raid & Daily Review', time: '20:00', repeat: 'daily', isActive: true, sound: 'magic' },
  ]);
  const [calendarNotes, setCalendarNotes] = useState<{ date: string; note: string }[]>(saved?.calendarNotes || []);

  const [toasts, setToasts] = useState<NotificationToast[]>([]);
  const [levelUpInfo, setLevelUpInfo] = useState<{ level: number; hpGain: number; mpGain: number; goldGain: number } | null>(null);
  const [lastDelete, setLastDelete] = useState<{ trashId: string; label: string } | null>(null);
  const [, setLiveHydrated] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiGet<any>('/api/bootstrap');
        if (cancelled || !data?.ok) return;
        if (data.user) {
          setUser((prev) => ({
            ...prev,
            ...data.user,
            xpToNextLevel: data.user.xpToNextLevel || (data.user.level || 1) * 150,
          }));
        }
        if (Array.isArray(data.taskFolders)) setTaskFolders(data.taskFolders);
        if (Array.isArray(data.habits)) setHabits(data.habits);
        if (Array.isArray(data.dailies)) setDailies(data.dailies);
        if (Array.isArray(data.quests)) setQuests(data.quests);
        if (Array.isArray(data.inventory)) setInventory(data.inventory);
        if (Array.isArray(data.userPets)) setUserPets(data.userPets);
        if (Array.isArray(data.achievements) && data.achievements.length) setAchievements(data.achievements);
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
        if (Array.isArray(data.healthLogs)) setHealthLogs(data.healthLogs);
        if (Array.isArray(data.pomodoroSessions)) setPomodoroSessions(data.pomodoroSessions);
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
        setLiveHydrated(true);
      } catch {
        setLiveHydrated(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Auto-persist to localStorage
  useEffect(() => {
    try {
      const state = {
        user,
        lang,
        soundEnabled,
        activeTheme,
        taskFolders,
        habits,
        dailies,
        quests,
        sportLogs,
        mealLogs,
        waterLog,
        inventory,
        userPets,
        activeBoss,
        activeBossHp,
        transactions,
        debts,
        noteFolders,
        notes,
        healthLogs,
        pomodoroSessions,
        achievements,
        notebooks,
        loveSpace,
        friends,
        chatMessages,
        guild,
        pvpChallenges,
        reminders,
        calendarNotes,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      // Ignore storage errors
    }
  }, [
    user,
    lang,
    soundEnabled,
    activeTheme,
    taskFolders,
    habits,
    dailies,
    quests,
    sportLogs,
    mealLogs,
    waterLog,
    inventory,
    userPets,
    activeBoss,
    activeBossHp,
    transactions,
    debts,
    noteFolders,
    notes,
    healthLogs,
    pomodoroSessions,
    achievements,
    notebooks,
    loveSpace,
    friends,
    chatMessages,
    guild,
    pvpChallenges,
    reminders,
    calendarNotes,
  ]);

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

  const applyLive = useCallback((res: any) => {
    if (!res || !res.ok) return false;
    if (res.user) {
      setUser((prev) => ({
        ...prev,
        ...res.user,
        xpToNextLevel: res.user.xpToNextLevel || (res.user.level || 1) * 150,
      }));
    }
    if (Array.isArray(res.taskFolders)) setTaskFolders(res.taskFolders);
    if (Array.isArray(res.habits)) setHabits(res.habits);
    if (Array.isArray(res.dailies)) setDailies(res.dailies);
    if (Array.isArray(res.quests)) setQuests(res.quests);
    if (Array.isArray(res.inventory)) setInventory(res.inventory);
    if (Array.isArray(res.userPets)) setUserPets(res.userPets);
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
  const updateUserStats = useCallback((xpDelta: number, goldDelta: number, hpDelta: number = 0, mpDelta: number = 0) => {
    setUser((prev) => {
      let finalXpGain = xpDelta;
      let finalGoldGain = goldDelta;

      if (xpDelta > 0 && totalBuffs.xp_pct > 0) {
        finalXpGain = Math.round(xpDelta * (1 + totalBuffs.xp_pct / 100));
      }
      if (goldDelta > 0 && totalBuffs.gold_pct > 0) {
        finalGoldGain = Math.round(goldDelta * (1 + totalBuffs.gold_pct / 100));
      }

      let newXp = prev.xp + finalXpGain;
      let newLevel = prev.level;
      let newXpToNext = prev.xpToNextLevel;
      let newMaxHp = prev.maxHp;
      let newMaxMp = prev.maxMp;
      let newHp = Math.min(newMaxHp, Math.max(0, prev.hp + hpDelta));
      let newMp = Math.min(newMaxMp, Math.max(0, prev.mp + mpDelta));
      let newGold = Math.max(0, prev.gold + finalGoldGain);

      // Check level up
      let leveledUp = false;
      let hpGained = 0;
      let mpGained = 0;
      let goldGained = 0;

      while (newXp >= newXpToNext) {
        newXp -= newXpToNext;
        newLevel += 1;
        newXpToNext = Math.round(100 * Math.pow(1.25, newLevel - 1));
        const hpIncrease = 15;
        const mpIncrease = 10;
        const rewardGold = newLevel * 25;

        newMaxHp += hpIncrease;
        newMaxMp += mpIncrease;
        newHp = newMaxHp; // Fully heal upon level up
        newMp = newMaxMp;
        newGold += rewardGold;

        hpGained += hpIncrease;
        mpGained += mpIncrease;
        goldGained += rewardGold;
        leveledUp = true;
      }

      if (leveledUp) {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
        setLevelUpInfo({
          level: newLevel,
          hpGain: hpGained,
          mpGain: mpGained,
          goldGain: goldGained,
        });
        showToast('level_up', `🎉 LEVEL UP! Level ${newLevel}`, `HP & MP fully restored! +${goldGained} Gold!`);
      }

      // Check Death & Totem of Undying
      if (newHp <= 0) {
        const totemItem = inventory.find((i) => i.itemId === 'totem' && i.quantity > 0);
        if (totemItem) {
          // Consume totem
          setInventory((invs) =>
            invs
              .map((i) => (i.itemId === 'totem' ? { ...i, quantity: i.quantity - 1 } : i))
              .filter((i) => i.quantity > 0)
          );
          newHp = Math.round(newMaxHp * 0.3);
          showToast('info', '🗿 Totem of Undying Triggered!', 'You were saved from fatal defeat and restored to 30% HP!');
        } else {
          // Penalize gold and restore to 20% HP
          newHp = Math.round(newMaxHp * 0.2);
          newGold = Math.max(0, newGold - 30);
          showToast('damage', '☠️ You Fainted from Exhaustion', 'Resting restored 20% HP, but 30 Gold was lost.');
        }
      }

      return {
        ...prev,
        level: newLevel,
        xp: newXp,
        xpToNextLevel: newXpToNext,
        hp: newHp,
        maxHp: newMaxHp,
        mp: newMp,
        maxMp: newMaxMp,
        gold: newGold,
      };
    });
  }, [totalBuffs, inventory, showToast]);

  const closeLevelUpModal = useCallback(() => {
    setLevelUpInfo(null);
  }, []);

  const changeAvatarClass = useCallback((newClass: AvatarClass) => {
    const classMeta = AVATAR_CLASSES[newClass];
    setUser((prev) => ({
      ...prev,
      avatarClass: newClass,
      avatarEmoji: classMeta.icon,
      avatarColor: classMeta.color,
      maxHp: Math.max(50, 100 + (prev.level - 1) * 15 + classMeta.hpBonus),
      maxMp: Math.max(30, 50 + (prev.level - 1) * 10 + classMeta.mpBonus),
    }));
    showToast('success', 'Class Changed', `You are now a ${classMeta.name}!`);
  }, [showToast]);

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

  // Habits
  const addHabit = useCallback((title: string, difficulty: TaskDifficulty, isPositive: boolean, isNegative: boolean, folderId?: string | null, notes?: string) => {
    rpg.addHabit({ title, difficulty, isPositive, isNegative, notes, folderId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const editHabit = useCallback((id: string, updates: Partial<Habit>) => {
    rpg.updateHabit(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setHabits((prev) => prev.map((h) => (h.id === id ? { ...h, ...updates } : h)));
    });
  }, [applyLive]);

  const duplicateHabit = useCallback((id: string) => {
    rpg.duplicateHabit(id).then((res) => applyLive(res)).catch(() => {});
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
    }).catch(() => {});
  }, [applyLive, habits])

  const triggerHabit = useCallback((id: string, isPos: boolean) => {
    rpg.completeHabit(id, isPos).then((res) => {
      if (!applyLive(res)) return;
      const habit = habits.find((h) => h.id === id);
      if (habit) {
        showToast(isPos ? 'success' : 'damage', habit.title, res.result?.msg || '');
      }
    }).catch(() => {});
  }, [habits, applyLive, showToast])

  const reorderHabits = useCallback((ordered: Habit[]) => {
    setHabits(ordered);
    rpg.reorderTasks('habit', ordered.map((h) => ({ id: h.id, folderId: h.folderId })))
      .then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Dailies
  const addDaily = useCallback((title: string, difficulty: TaskDifficulty, repeatDays: number[], folderId?: string | null, notes?: string) => {
    rpg.addDaily({ title, difficulty, repeatDays, notes, folderId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const editDaily = useCallback((id: string, updates: Partial<Daily>) => {
    rpg.updateDaily(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setDailies((prev) => prev.map((d) => (d.id === id ? { ...d, ...updates } : d)));
    });
  }, [applyLive]);

  const duplicateDaily = useCallback((id: string) => {
    rpg.duplicateDaily(id).then((res) => applyLive(res)).catch(() => {});
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
    }).catch(() => {});
  }, [applyLive, dailies])

  const toggleDaily = useCallback((id: string) => {
    rpg.completeDaily(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const useDailyFreeze = useCallback((id: string) => {
    rpg.freezeDaily(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const failDaily = useCallback((id: string) => {
    rpg.failDaily(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  const reorderDailies = useCallback((ordered: Daily[]) => {
    setDailies(ordered);
    rpg.reorderTasks('daily', ordered.map((d) => ({ id: d.id, folderId: d.folderId })))
      .then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Quests / Todos
  const addQuest = useCallback((title: string, difficulty: TaskDifficulty, dueDate?: string | null, folderId?: string | null, notes?: string) => {
    rpg.addQuest({ title, difficulty, dueDate, notes, folderId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const editQuest = useCallback((id: string, updates: Partial<Quest>) => {
    rpg.updateQuest(id, updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {
      setQuests((prev) => prev.map((q) => (q.id === id ? { ...q, ...updates } : q)));
    });
  }, [applyLive]);

  const duplicateQuest = useCallback((id: string) => {
    rpg.duplicateQuest(id).then((res) => applyLive(res)).catch(() => {});
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
    }).catch(() => {});
  }, [applyLive, quests])

  const toggleQuest = useCallback((id: string) => {
    rpg.completeQuest(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const reorderQuests = useCallback((ordered: Quest[]) => {
    setQuests(ordered);
    rpg.reorderTasks('quest', ordered.map((q) => ({ id: q.id, folderId: q.folderId })))
      .then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const restoreTask = useCallback((trashId: string) => {
    rpg.restoreTask(trashId).then((res) => {
      if (applyLive(res)) {
        showToast('success', lang === 'id' ? 'Tugas dipulihkan' : 'Task restored', '');
      }
    }).catch(() => {});
  }, [applyLive, showToast, lang])

  const undoDelete = useCallback(() => {
    if (!lastDelete) return;
    const { trashId } = lastDelete;
    setLastDelete(null);
    restoreTask(trashId);
  }, [lastDelete, restoreTask])

  // Sport Tracker
  const addSportLog = useCallback((sportType: string, sportName: string, icon: string, durationMinutes: number, caloriesBurned: number, intensity: 'light' | 'moderate' | 'vigorous', notes?: string) => {
    life.addSport({ sportType, sportName, icon, durationMinutes, caloriesBurned, intensity, notes, complete: false }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const completeSportLog = useCallback((id: string) => {
    life.completeSport(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteSportLog = useCallback((id: string) => {
    life.deleteSport(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Nutrition
  const addMealLog = useCallback((mealType: 'breakfast' | 'lunch' | 'dinner' | 'snack', foodName: string, icon: string, portion: number, calories: number, protein: number, carbs: number, fat: number) => {
    life.logFood({ mealType, foodName, icon, portion, calories, protein, carbs, fat }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteMealLog = useCallback((id: string) => {
    life.deleteFoodLog(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const addWater = useCallback((amountMl: number) => {
    life.addWater(amountMl).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const resetWater = useCallback(() => {
    setWaterLog((prev) => ({ ...prev, amountMl: 0 }));
    life.resetWater().then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  // Shop & Inventory & Crafting
  const buyItem = useCallback((itemId: string): boolean => {
    rpg.buyItem(itemId).then((res) => applyLive(res)).catch((e) => showToast('info', String(e?.message || e), ''));
    return true;
  }, [applyLive, showToast])

  const sellItem = useCallback((itemId: string) => {
    rpg.sellItem(itemId).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const useConsumable = useCallback((itemId: string): boolean => {
    rpg.useItem(itemId).then((res) => applyLive(res)).catch(() => {});
    return true;
  }, [applyLive])

  const equipItem = useCallback((itemId: string) => {
    rpg.equipItem(itemId, true).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const unequipItem = useCallback((itemId: string) => {
    rpg.equipItem(itemId, false).then((res) => applyLive(res)).catch(() => {});
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
    rpg.adoptPet(petId).then((res) => applyLive(res)).catch(() => {});
    return true;
  }, [applyLive])

  const feedPet = useCallback((petId: string) => {
    rpg.feedPet(petId).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const trainPet = useCallback((petId: string) => {
    rpg.trainPet(petId).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const equipPet = useCallback((petId: string) => {
    rpg.equipPet(petId).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const unequipPet = useCallback(() => {
    const equipped = userPets.find((p) => p.isEquipped);
    if (equipped) rpg.unequipPet(equipped.petId).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive, userPets])

  // Boss Combat
  const startBossFight = useCallback((bossId: string) => {
    const boss = BOSSES[bossId];
    if (boss) {
      setActiveBoss(boss);
      setActiveBossHp(boss.hp);
    }
    rpg.startBoss(bossId).then((res) => applyLive(res)).catch(() => {});
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
    rpg.fleeBoss().then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  // Economy
  const addTransaction = useCallback((type: 'income' | 'expense', category: string, amount: number, notes?: string) => {
    life.addEconomy({ type, category, amount, notes }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteTransaction = useCallback((id: string) => {
    life.deleteEconomy(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const addDebt = useCallback((title: string, type: 'payable' | 'receivable', totalAmount: number, dueDate: string, notes?: string) => {
    life.addDebt({ title, type, totalAmount, dueDate, notes }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const payDebtInstallment = useCallback((id: string, amount: number) => {
    life.payDebt(id, amount).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteDebt = useCallback((id: string) => {
    life.deleteDebt(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const addSaving = useCallback((name: string, targetAmount: number, currentAmount?: number, targetDate?: string) => {
    life.addSaving({ name, targetAmount, currentAmount: currentAmount || 0, targetDate }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const addToSaving = useCallback((id: string, amount: number) => {
    life.addToSaving(id, amount).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const withdrawFromSaving = useCallback((id: string, amount: number) => {
    life.withdrawSaving(id, amount).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const deleteSaving = useCallback((id: string) => {
    life.deleteSaving(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const addInvestment = useCallback((name: string, amount: number, notes?: string) => {
    life.addInvestment({ name, amount, notes }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const collectInvestmentReturn = useCallback((id: string) => {
    life.investmentReturn(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const withdrawInvestment = useCallback((id: string) => {
    life.withdrawInvestment(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const addSubscription = useCallback((name: string, amount: number, dueDate: string, period?: string) => {
    life.addSubscription({ name, amount, dueDate, period: period || 'monthly' }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const renewSubscription = useCallback((id: string) => {
    life.renewSubscription(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const deleteSubscription = useCallback((id: string) => {
    life.deleteSubscription(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const addDebtNote = useCallback((personName: string, amount: number, date?: string, notes?: string) => {
    life.addDebtNote({ personName, amount, date, notes }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const settleDebtNote = useCallback((id: string) => {
    life.settleDebtNote(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const deleteDebtNote = useCallback((id: string) => {
    life.deleteDebtNote(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);
  const applyTaskTemplate = useCallback((mode: string, key: string) => {
    life.applyTemplate(mode, key).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  // Notes
  const addNoteFolder = useCallback((name: string, icon: string, parentId?: string | null) => {
    life.addNoteFolder({ name, icon, parentId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteNoteFolder = useCallback((id: string) => {
    life.deleteNoteFolder(id).then((res) => applyLive(res)).catch(() => setNoteFolders((prev) => prev.filter((f) => f.id !== id)));
  }, [applyLive]);

  const addNote = useCallback((title: string, content: string, folderId?: string | null) => {
    life.addNote({ title, content, folderId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const updateNote = useCallback((id: string, title: string, content: string, folderId?: string | null) => {
    life.updateNote(id, { title, content, folderId }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteNote = useCallback((id: string) => {
    life.deleteNote(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const archiveNote = useCallback((id: string, archived: boolean) => {
    life.archiveNote(id, archived).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  const duplicateNoteItem = useCallback((id: string) => {
    life.duplicateNote(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

  // Health Metrics
  const addHealthLog = useCallback((steps: number, sleepHours: number, weightKg?: number, heartRate?: number, mood: 'great' | 'good' | 'neutral' | 'tired' | 'stressed' = 'good', notes?: string) => {
    life.addHealth({ steps, sleepHours, weightKg, heartRate, mood, notes }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const completePomodoroSession = useCallback((durationMinutes: number, label: string) => {
    life.completePomodoro(durationMinutes, label).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Achievements
  const claimAchievement = useCallback((id: string) => {
    rpg.claimAchievement(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Learning Notebook Actions
  const addNotebook = useCallback((title: string, description: string, icon: string = '📚') => {
    studio.addNotebook(title, description, icon).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const updateNotebook = useCallback((id: string, updates: Partial<LearningNotebook>) => {
    setNotebooks((prev) => prev.map((nb) => (nb.id === id ? { ...nb, ...updates } : nb)));
  }, []);

  const deleteNotebook = useCallback((id: string) => {
    studio.deleteNotebook(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const addNotebookSource = useCallback((notebookId: string, title: string, content: string, type: 'text' | 'doc' | 'pdf' | 'url' = 'text') => {
    studio.addSource(notebookId, title, content, type).then((res) => applyLive(res)).catch(() => {});
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
    studio.chat(notebookId, text).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Love Space Actions
  const updateLoveSpace = useCallback((updates: Partial<LoveSpaceData>) => {
    studio.updateLove(updates as Record<string, unknown>).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const addLoveMemory = useCallback((title: string, date: string, description: string, emoji: string) => {
    studio.addMemory(title, date, description, emoji).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const toggleLoveBucketItem = useCallback((id: string) => {
    studio.toggleBucket(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const answerLovePrompt = useCallback((promptId: string, answer: string) => {
    studio.lovePrompt({ id: promptId, answer }).then((res) => applyLive(res)).catch(() => {});
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

  const attackGuildBoss = useCallback((damage: number) => {
    studio.attackGuildBoss(damage).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const claimPvPReward = useCallback((id: string) => {
    studio.claimPvp(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  // Calendar Reminders
  const addReminder = useCallback((title: string, time: string, repeat: 'none' | 'daily' | 'weekdays' | 'weekly' = 'daily', sound: 'beep' | 'bell' | 'magic' | 'fanfare' = 'bell') => {
    life.addReminder({ title, time, repeat, sound }).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const toggleReminder = useCallback((id: string) => {
    life.toggleReminder(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const deleteReminder = useCallback((id: string) => {
    life.deleteReminder(id).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive])

  const saveCalendarNote = useCallback((date: string, note: string) => {
    life.saveCalendarNote(date, note).then((res) => applyLive(res)).catch(() => {});
  }, [applyLive]);

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

  const resetAllData = useCallback(() => {
    setUser(defaultUser);
    setHabits(defaultHabits);
    setDailies(defaultDailies);
    setQuests(defaultQuests);
    setInventory([
      { itemId: 'wooden_sword', quantity: 1, equipped: true },
      { itemId: 'health_potion', quantity: 2, equipped: false },
      { itemId: 'ice_block', quantity: 1, equipped: false },
    ]);
    setUserPets([
      { petId: 'wolf', nickname: 'Fang', level: 1, xp: 20, hunger: 90, isEquipped: true, adoptedAt: new Date().toISOString() },
    ]);
    setSportLogs(defaultSportLogs);
    setMealLogs(defaultMeals);
    setTransactions(defaultTransactions);
    setNotes(defaultNotes);
    localStorage.removeItem(STORAGE_KEY);
    showToast('info', 'Progress Reset', 'Restored to clean state.');
  }, [showToast]);

  return (
    <GameContext.Provider
      value={{
        user,
        setUser,
        updateUserStats,
        updateUserProfile,
        rebirthCharacter,
        changeAvatarClass,
        lang,
        setLang,
        soundEnabled,
        setSoundEnabled,
        activeTheme,
        setActiveTheme,
        taskFolders,
        addTaskFolder,
        deleteTaskFolder,
        habits,
        addHabit,
        editHabit,
        duplicateHabit,
        deleteHabit,
        triggerHabit,
        reorderHabits,
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
        notes,
        addNote,
        updateNote,
        deleteNote,
        archiveNote,
        duplicateNoteItem,
        healthLogs,
        addHealthLog,
        pomodoroSessions,
        completePomodoroSession,
        achievements,
        claimAchievement,
        notebooks,
        addNotebook,
        updateNotebook,
        deleteNotebook,
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
        toggleReminder,
        deleteReminder,
        calendarNotes,
        saveCalendarNote,
        levelUpInfo,
        closeLevelUpModal,
        toasts,
        removeToast,
        showToast,
        totalBuffs,
        exportDataJson,
        importDataJson,
        resetAllData,
      }}
    >
      {children}
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
