export type ActiveView = 'dashboard' | 'profile' | 'habits' | 'dailies' | 'quests' | 'sport' | 'nutrition' | 'shop' | 'craft' | 'pets' | 'boss' | 'economy' | 'supplies' | 'notes' | 'health' | 'learning' | 'music' | 'love' | 'lovespace' | 'social' | 'friends' | 'guild' | 'reminders' | 'pomodoro' | 'calendar' | 'achievements' | 'leaderboard' | 'settings';
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
    lastClassChange?: string;
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
    selectedTitle?: string;
    hasProfilePhoto?: boolean;
    fontScale?: number;
    longestStreak?: number;
    highContrast?: boolean;
    language?: string;
    onboardingDone?: boolean;
    locked?: boolean;
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
    doneToday?: boolean;
    history: {
        date: string;
        type: 'pos' | 'neg';
    }[];
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
    repeatDays: number[];
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
    difficulty?: string;
    xpReward?: number;
    goldReward?: number;
    sportPointsReward?: number;
    streak?: number;
    totalReps?: number;
    folderId?: string | null;
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
    requiredItems: {
        itemId: string;
        quantity: number;
    }[];
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
    hunger: number;
    isEquipped: boolean;
    adoptedAt: string;
    /** L05/L06 (v1.7.4): meta gacha — mengalir dari PETS_DATA via API. */
    rank?: string;
    skill?: {
        key: string;
        name: string;
        name_id?: string;
        effect: string;
        base: number;
        per_level: number;
    } | null;
    skillUsedAt?: number;
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
    name?: string;
    icon?: string;
    folderId?: string | null;
}
export interface Debt {
    id: string;
    title: string;
    type: 'payable' | 'receivable';
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
    investedDate?: string;
    isActive?: boolean;
}
export interface SubscriptionItem {
    id: string;
    name: string;
    icon: string;
    amount: number;
    dueDate: string;
    period: string;
    notes?: string;
    isRecurring?: boolean;
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
/** P54: metadata lampiran catatan (file fisik di server). */
export interface NoteAttachment {
    id: string;
    noteId: string;
    fileName: string;
    mime: string;
    size: number;
    kind: 'image' | 'file';
    createdAt?: string;
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
    /** P56: 'mc' (default) | 'essay' — generator quiz menghasilkan campuran. */
    type?: 'mc' | 'essay';
    /** P56: jawaban contoh untuk soal essay. */
    modelAnswer?: string;
}
export interface PodcastDialogue {
    speaker: 'Alex' | 'Sam';
    line: string;
}
export interface LearningGeneration {
    id: string;
    gtype: 'quiz' | 'flashcards' | 'mindmap' | 'podcast' | 'summary' | 'faq' | 'timeline' | 'study-guide' | 'briefing-doc' | 'data-table' | 'infographic' | 'slide-deck';
    topic: string;
    content: string;
    fileName: string;
    createdAt: string;
}
export interface LearningNotebook {
    id: string;
    title: string;
    description: string;
    icon: string;
    sources: NotebookSource[];
    chatHistory: {
        sender: 'user' | 'ai';
        text: string;
        timestamp: string;
    }[];
    flashcards: Flashcard[];
    quizzes: QuizQuestion[];
    podcast: PodcastDialogue[];
    notes: string;
    createdAt: string;
    generations?: LearningGeneration[];
}
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
export interface LoveCheckin {
    id: string;
    date: string;
    myMood: number;
    partnerMood: number;
    connectionScore: number;
    note: string;
}
export interface LovePromptResponse {
    id: string;
    promptKey: string;
    category: string;
    prompt: string;
    answer: string;
    partnerAnswer: string;
    createdAt: string;
}
export interface LoveAlbum {
    id: string;
    name: string;
    scope: 'personal' | 'shared';
    photoIds: string[];
}
export interface LoveCycleSettings {
    trackedPerson: 'self' | 'partner';
    lastPeriodStart: string;
    cycleLength: number;
    periodLength: number;
}
export interface LoveCyclePrediction {
    predictedStart: string;
    predictedEnd: string;
    daysUntil: number;
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
    events?: {
        id: string;
        title: string;
        date: string;
        category?: string;
        notes?: string;
    }[];
    weeklyReviews?: {
        id: string;
        weekStart: string;
        appreciation?: string;
        wins?: string;
        support?: string;
        intention?: string;
    }[];
    cycles?: {
        id: string;
        startDate: string;
        endDate?: string;
        notes?: string;
    }[];
    checkins?: LoveCheckin[];
    promptResponses?: LovePromptResponse[];
    promptFavorites?: string[];
    albums?: LoveAlbum[];
    coupleActive?: boolean;
    cycleSettings?: LoveCycleSettings;
    cyclePrediction?: LoveCyclePrediction | null;
    myName?: string;
    myGender?: string;
    myAge?: number;
    myBirthdate?: string;
    partnerGender?: string;
    partnerAge?: number;
    partnerBirthdate?: string;
    relationshipType?: string;
    startDate?: string;
    linkedPartnerUsername?: string;
    cloudLoveActive?: boolean;
    healthProfile?: {
        gender: string;
        age: number;
    };
}
export interface FriendUser {
    id: string;
    name: string;
    displayName?: string;
    username?: string;
    avatar: string;
    avatarEmoji?: string;
    heroClass?: string;
    classTitle?: string;
    level: number;
    status: 'online' | 'away' | 'offline';
    streak: number;
    streakDays?: number;
    lastSeen?: string;
    coupleStatus?: 'friend' | 'pending' | 'accepted';
    presence?: string;
    unreadCount?: number;
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
    messages?: {
        id: string;
        senderName?: string;
        text: string;
        isSelf?: boolean;
        timestamp?: string;
    }[];
    leaderId?: string;
    leaderTransfers?: {
        id: string;
        oldLeaderId: string;
    }[];
    buffXp?: number;
    buffGold?: number;
    buffDamage?: number;
    critChance?: number;
    bossAttack?: number;
    bossIcon?: string;
    bossTier?: string;
    bossParticipants?: string;
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
    winnerId?: string | null;
    rewardGold: number;
    rewardXp: number;
}
export interface HolidayItem {
    date: string;
    nameEn: string;
    nameId: string;
    type: 'national' | 'international' | 'observance';
}
export interface ReminderItem {
    id: string;
    title: string;
    description: string;
    datetime: string;
    time: string;
    repeat: 'none' | 'daily' | 'weekly' | 'yearly' | 'custom';
    repeatDays: string;
    repeatUntil?: string;
    sourceRef?: string;
    isActive: boolean;
    triggered: boolean;
    sound: 'default' | 'beep1' | 'beep2' | 'custom';
    soundFile: string;
}
/** Waktu server (parity TimeSync): sumber tanggal & jam tunggal untuk web. */
export interface ServerClock {
    iso: string;
    date: string;
    time: string;
    epoch: number;
    tzOffsetMin: number;
    weekday: number;
}
/** Palet penuh tema (parity db.THEMES — source of truth untuk warna). */
export interface ThemePalette {
    key: string;
    label: string;
    primary: string;
    light: string;
    bg: string;
    bg2: string;
    bg3: string;
    panel: string;
    border: string;
    accent: string;
    accent2: string;
    accent3: string;
    glow: string;
    text: string;
    muted: string;
    /** L01 (v1.7.4): warna teks di atas isian primary/accent (kontras terjamin). */
    on_primary?: string;
    on_accent?: string;
}
//# sourceMappingURL=types.d.ts.map