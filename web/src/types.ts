export type ActiveView =
  | 'dashboard'
  | 'profile'
  | 'habits'
  | 'dailies'
  | 'quests'
  | 'sport'
  | 'nutrition'
  | 'shop'
  | 'craft'
  | 'pets'
  | 'boss'
  | 'economy'
  | 'supplies'
  | 'notes'
  | 'health'
  | 'learning'
  | 'music'
  | 'love'
  | 'lovespace'
  | 'social'
  | 'friends'
  | 'guild'
  | 'reminders'
  | 'pomodoro'
  | 'calendar'
  | 'achievements'
  | 'leaderboard'
  | 'settings';

export type NavTab = ActiveView;

export type BossTier = 'beginner' | 'normal' | 'hard' | 'elite' | 'legendary' | 'seasonal';

export type ShopItemType = 'weapon' | 'armor' | 'tool' | 'consumable' | 'legendary' | 'special';

export type AvatarClass = 'warrior' | 'mage' | 'rogue' | 'paladin' | 'ranger' | 'healer';

export type TaskDifficulty = 'trivial' | 'easy' | 'medium' | 'hard' | 'epic';

export interface UserProfile {
  id: string;
  username: string;
  displayName: string;
  name?: string;
  bio: string;
  avatarClass: AvatarClass;
  heroClass?: string;
  avatarEmoji: string;
  avatar?: string;
  avatarColor: string;
  level: number;
  xp: number;
  xpToNextLevel: number;
  hp: number;
  maxHp: number;
  mp: number;
  maxMp: number;
  gold: number;
  goldLocal?: number;
  goldCloud?: number | null;
  cloudLinked?: boolean;
  gems: number;
  rebirthCount: number;
  sportLevel: number;
  sportXp: number;
  activePetId: string | null;
  equippedWeapon: string | null;
  equippedArmor: string | null;
  equippedTool: string | null;
  equippedLegendary: string | null;
  freezeSlots: number;
  createdAt: string;
  currency?: string;
  fontScale?: number;
  longestStreak?: number;
  highContrast?: boolean;
  language?: string;
  onboardingDone?: boolean;
}

export interface Habit {
  id: string;
  title: string;
  notes?: string;
  folderId?: string | null;
  difficulty: TaskDifficulty;
  isPositive: boolean;
  isNegative: boolean;
  positiveStreak: number;
  negativeStreak: number;
  history: { date: string; type: 'pos' | 'neg' }[];
  createdAt: string;
  sortOrder?: number;
}

export interface Daily {
  id: string;
  title: string;
  notes?: string;
  folderId?: string | null;
  difficulty: TaskDifficulty;
  streak: number;
  isCompletedToday: boolean;
  repeatDays: number[]; // 0=Sun, 1=Mon, ..., 6=Sat
  lastCompletedDate?: string | null;
  isFrozen?: boolean;
  createdAt: string;
  sortOrder?: number;
}

export interface Quest {
  id: string;
  title: string;
  notes?: string;
  folderId?: string | null;
  difficulty: TaskDifficulty;
  dueDate?: string | null;
  isCompleted: boolean;
  completedAt?: string | null;
  createdAt: string;
  sortOrder?: number;
}

export interface TaskFolder {
  id: string;
  name: string;
  icon: string;
  color?: string;
  mode?: 'habit' | 'daily' | 'todo' | 'sport';
}

export interface SportLog {
  id: string;
  sportType: string;
  sportName: string;
  icon: string;
  durationMinutes: number;
  caloriesBurned: number;
  intensity: 'light' | 'moderate' | 'vigorous';
  notes?: string;
  date: string;
  sportXpEarned: number;
  done?: boolean;
}

export interface FoodItem {
  id: string;
  nameId: string;
  nameEn: string;
  icon: string;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  serving: string;
  isCustom?: boolean;
}

export interface MealLog {
  id: string;
  mealType: 'breakfast' | 'lunch' | 'dinner' | 'snack';
  foodName: string;
  icon: string;
  portion: number;
  calories: number;
  protein: number;
  carbs: number;
  fat: number;
  date: string;
}

export interface WaterLog {
  date: string;
  amountMl: number;
  targetMl: number;
}

export interface ShopItem {
  id: string;
  name: string;
  icon: string;
  cost: number;
  type: 'weapon' | 'armor' | 'tool' | 'consumable' | 'legendary' | 'special';
  desc: string;
  buffDesc: string;
  buff: {
    xp_pct?: number;
    gold_pct?: number;
    boss_dmg?: number;
    hp_reduc?: number;
    block_chance?: number;
    block_strength?: number;
    crit_chance?: number;
    mp_bonus?: number;
    revive?: boolean;
  };
  craftOnly?: boolean;
  seasonal?: string;
  hpRestore?: number;
  mpRestore?: number;
  maxMpPermanent?: number;
}

export interface InventoryItem {
  itemId: string;
  quantity: number;
  equipped: boolean;
  enchantLevel?: number;
}

export interface CraftRecipe {
  resultItemId: string;
  requiredItems: { itemId: string; quantity: number }[];
  goldCost: number;
}

export interface PetData {
  id: string;
  name: string;
  icon: string;
  cost: number;
  bonus: string;
  baseBuff: {
    xp_pct?: number;
    gold_pct?: number;
    hp_reduc?: number;
    boss_dmg?: number;
  };
}

export interface UserPet {
  petId: string;
  nickname: string;
  level: number;
  xp: number;
  hunger: number; // 0 to 100
  isEquipped: boolean;
  adoptedAt: string;
}

export interface Boss {
  id: string;
  name: string;
  icon: string;
  tier: 'beginner' | 'normal' | 'hard' | 'elite' | 'legendary' | 'seasonal';
  hp: number;
  maxHp: number;
  atk: number;
  xpReward: number;
  goldReward: number;
  minLevel: number;
  seasonalEvent?: string;
}

export interface Transaction {
  id: string;
  type: 'income' | 'expense';
  category: string;
  amount: number;
  date: string;
  notes?: string;
}

export interface Debt {
  id: string;
  title: string;
  type: 'payable' | 'receivable'; // hutang / piutang
  totalAmount: number;
  remainingAmount: number;
  dueDate: string;
  notes?: string;
  isPaid: boolean;
}

export interface SavingGoal {
  id: string;
  name: string;
  icon: string;
  targetAmount: number;
  currentAmount: number;
  targetDate?: string;
  notes?: string;
}

export interface InvestmentItem {
  id: string;
  name: string;
  icon: string;
  amount: number;
  notes?: string;
}

export interface SubscriptionItem {
  id: string;
  name: string;
  icon: string;
  amount: number;
  dueDate: string;
  period: string;
  notes?: string;
}

export interface DebtNote {
  id: string;
  personName: string;
  amount: number;
  date: string;
  notes?: string;
  status: string;
}

export interface NoteFolder {
  id: string;
  name: string;
  icon: string;
  parentId?: string | null;
}

export interface Note {
  id: string;
  folderId?: string | null;
  title: string;
  content: string;
  isPinned?: boolean;
  isArchived?: boolean;
  updatedAt: string;
}

export interface Achievement {
  id: string;
  title: string;
  desc: string;
  category: 'habits' | 'dailies' | 'quests' | 'level' | 'sport' | 'boss' | 'pets' | 'economy';
  icon: string;
  xpReward: number;
  goldReward: number;
  currentProgress: number;
  targetProgress: number;
  isUnlocked: boolean;
  isClaimed: boolean;
}

export interface HealthMetricLog {
  id: string;
  date: string;
  steps: number;
  sleepHours: number;
  weightKg?: number;
  heartRate?: number;
  mood: 'great' | 'good' | 'neutral' | 'tired' | 'stressed';
  notes?: string;
}

export interface PomodoroSession {
  id: string;
  durationMinutes: number;
  completedAt: string;
  xpEarned: number;
  goldEarned: number;
  label: string;
}

// ── Learning & AI Workspace (NotebookLM) ──────────────────────────────────
export interface NotebookSource {
  id: string;
  title: string;
  type: 'text' | 'doc' | 'pdf' | 'url';
  content: string;
  wordCount: number;
  createdAt: string;
}

export interface Flashcard {
  id: string;
  question: string;
  answer: string;
  box?: number;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  correctAnswerIndex: number;
  explanation: string;
}

export interface PodcastDialogue {
  speaker: 'Alex' | 'Sam';
  line: string;
}

export interface LearningNotebook {
  id: string;
  title: string;
  description: string;
  icon: string;
  sources: NotebookSource[];
  chatHistory: { sender: 'user' | 'ai'; text: string; timestamp: string }[];
  flashcards: Flashcard[];
  quizzes: QuizQuestion[];
  podcast: PodcastDialogue[];
  notes: string;
  createdAt: string;
}

// ── Music & Audio Studio ───────────────────────────────────────────────────
export interface MusicTrack {
  id: string;
  title: string;
  artist: string;
  duration: string;
  url: string;
  coverEmoji: string;
  category: 'lofi' | 'focus' | 'ambient' | 'synth';
  isFavorite?: boolean;
}

// ── Love Space ─────────────────────────────────────────────────────────────
export interface LoveMemory {
  id: string;
  title: string;
  date: string;
  description: string;
  emoji: string;
  photoUrl?: string;
}

export interface LovePrompt {
  id: string;
  prompt: string;
  userAnswer?: string;
  partnerAnswer?: string;
  date: string;
}

export interface LoveBucketItem {
  id: string;
  title: string;
  isCompleted: boolean;
  completedDate?: string;
  targetYear?: number;
}

export interface LoveSpaceData {
  isEnabled: boolean;
  partnerName: string;
  partnerAvatar: string;
  anniversaryDate: string;
  connectionScore: number;
  dailyLoveNote: string;
  memories: LoveMemory[];
  prompts: LovePrompt[];
  bucketList: LoveBucketItem[];
  photos?: LovePhotoMeta[];
  events?: { id: string; title: string; date: string; category?: string; notes?: string }[];
  weeklyReviews?: { id: string; weekStart: string; appreciation?: string; wins?: string }[];
  cycles?: { id: string; startDate: string; endDate?: string; notes?: string }[];
}

// ── Social, Friends, PvP & Guild ───────────────────────────────────────────
export interface FriendUser {
  id: string;
  name: string;
  displayName?: string;
  avatar: string;
  avatarEmoji?: string;
  heroClass?: string;
  classTitle?: string;
  level: number;
  status: 'online' | 'away' | 'offline';
  streak: number;
  streakDays?: number;
  lastSeen?: string;
}

export interface ChatMessage {
  id: string;
  senderId: string;
  senderName: string;
  senderAvatar: string;
  text: string;
  timestamp: string;
  isSelf: boolean;
}

export interface GuildMember {
  id: string;
  name: string;
  displayName?: string;
  role: 'leader' | 'officer' | 'member';
  level: number;
  contribution: number;
  weeklyContribution?: number;
  avatar: string;
  avatarEmoji?: string;
  classTitle?: string;
}

export interface GuildData {
  id: string;
  name: string;
  tag: string;
  level: number;
  exp: number;
  maxExp: number;
  description: string;
  badgeEmoji?: string;
  members: GuildMember[];
  bossHp: number;
  bossMaxHp: number;
  bossName: string;
  requests?: GuildJoinRequest[];
  messages?: { id: string; senderName?: string; text: string; isSelf?: boolean; timestamp?: string }[];
  leaderId?: string;
  leaderTransfers?: { id: string; oldLeaderId: string }[];
}

export interface FriendRequest {
  id: string;
  senderId: string;
  name: string;
  username?: string;
}

export interface GuildJoinRequest {
  id: string;
  userId: string;
  name: string;
  username?: string;
}

export interface LovePhotoMeta {
  id: string;
  caption: string;
  photoDate: string;
  visibility: 'private' | 'shared' | string;
  ownerUserId?: string;
  uploaderName?: string;
  createdAt?: string;
}

export interface PvPChallenge {
  id: string;
  opponentName: string;
  opponentAvatar: string;
  opponentLevel: number;
  opponentId?: string;
  status: 'pending' | 'active' | 'completed';
  rawStatus?: string;
  isChallenger?: boolean;
  playerScore: number;
  opponentScore: number;
  daysLeft?: number;
  rewardGold: number;
  rewardXp: number;
}

// ── Calendar & Reminders ───────────────────────────────────────────────────
export interface HolidayItem {
  date: string; // YYYY-MM-DD
  nameEn: string;
  nameId: string;
  type: 'national' | 'international' | 'observance';
}

export interface ReminderItem {
  id: string;
  title: string;
  time: string; // HH:mm or YYYY-MM-DDTHH:mm
  repeat: 'none' | 'daily' | 'weekdays' | 'weekly';
  isActive: boolean;
  sound: 'beep' | 'bell' | 'magic' | 'fanfare';
}

