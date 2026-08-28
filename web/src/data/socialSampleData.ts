import { FriendUser, ChatMessage, GuildData, PvPChallenge, LoveSpaceData } from '../types';

export const DEFAULT_LOVE_SPACE: LoveSpaceData = {
  isEnabled: true,
  partnerName: 'Aria',
  partnerAvatar: '🌸',
  anniversaryDate: '2024-02-14',
  connectionScore: 92,
  dailyLoveNote: 'Thank you for always supporting my goals and keeping our daily streaks alive! ❤️',
  memories: [
    {
      id: 'mem_1',
      title: 'First Coffee Date & Sunset Walk',
      date: '2024-02-14',
      description: 'Shared matcha latte and watched the sunset by the harbor.',
      emoji: '🌅',
    },
    {
      id: 'mem_2',
      title: 'Stargazing Camping Trip',
      date: '2025-07-20',
      description: 'Camped in the pine forest, roasted marshmallows, and saw shooting stars.',
      emoji: '⛺',
    },
  ],
  prompts: [
    {
      id: 'p_1',
      prompt: 'What was your favorite moment together this past week?',
      userAnswer: 'Cooking pasta together while listening to relaxing lofi beats!',
      partnerAnswer: 'Walking in the morning breeze before work starts.',
      date: '2026-08-25',
    },
    {
      id: 'p_2',
      prompt: 'Where is one dream destination we want to explore next?',
      userAnswer: 'Kyoto bamboo gardens during autumn leaves.',
      date: '2026-08-26',
    },
  ],
  bucketList: [
    { id: 'b_1', title: 'Visit Kyoto in Spring', isCompleted: false, targetYear: 2027 },
    { id: 'b_2', title: 'Complete a 10K Marathon Together', isCompleted: true, completedDate: '2025-11-12' },
    { id: 'b_3', title: 'Adopt a Rescue Puppy', isCompleted: false, targetYear: 2026 },
  ],
};

export const DEFAULT_FRIENDS: FriendUser[] = [
  { id: 'u_1', name: 'Kaelen Shadowblade', avatar: '🗡️', heroClass: 'Rogue', level: 18, status: 'online', streak: 42 },
  { id: 'u_2', name: 'Elena Sunweaver', avatar: '🧙‍♀️', heroClass: 'Mage', level: 24, status: 'online', streak: 65 },
  { id: 'u_3', name: 'Thorin Ironclad', avatar: '🛡️', heroClass: 'Paladin', level: 15, status: 'away', streak: 19 },
  { id: 'u_4', name: 'Sylvia Starbreeze', avatar: '🏹', heroClass: 'Ranger', level: 21, status: 'offline', streak: 30 },
];

export const DEFAULT_CHAT_MESSAGES: ChatMessage[] = [
  { id: 'm_1', senderId: 'u_1', senderName: 'Kaelen Shadowblade', senderAvatar: '🗡️', text: 'Hey! Ready for today’s Guild Boss raid?', timestamp: '09:40 AM', isSelf: false },
  { id: 'm_2', senderId: 'self', senderName: 'Hero', senderAvatar: '⚔️', text: 'Just completed my daily workout and quests! Entering the arena now.', timestamp: '09:42 AM', isSelf: true },
  { id: 'm_3', senderId: 'u_1', senderName: 'Kaelen Shadowblade', senderAvatar: '🗡️', text: 'Awesome! Let’s defeat the Shadow Dragon before reset.', timestamp: '09:43 AM', isSelf: false },
];

export const DEFAULT_GUILD: GuildData = {
  id: 'g_valkyrie',
  name: 'Valkyrie Vanguard',
  tag: 'VLV',
  level: 8,
  exp: 14200,
  maxExp: 20000,
  description: 'Top-tier productivity guild committed to relentless daily habits and legendary boss conquests.',
  members: [
    { id: 'self', name: 'Hero (You)', role: 'officer', level: 12, contribution: 3450, avatar: '⚔️' },
    { id: 'u_1', name: 'Elena Sunweaver', role: 'leader', level: 24, contribution: 7200, avatar: '🧙‍♀️' },
    { id: 'u_2', name: 'Kaelen Shadowblade', role: 'officer', level: 18, contribution: 5100, avatar: '🗡️' },
    { id: 'u_3', name: 'Thorin Ironclad', role: 'member', level: 15, contribution: 2900, avatar: '🛡️' },
    { id: 'u_4', name: 'Sylvia Starbreeze', role: 'member', level: 21, contribution: 4800, avatar: '🏹' },
  ],
  bossHp: 6500,
  bossMaxHp: 15000,
  bossName: 'Ancient Nether Dragon',
};

export const DEFAULT_PVP_CHALLENGES: PvPChallenge[] = [
  {
    id: 'pvp_1',
    opponentName: 'Kaelen Shadowblade',
    opponentAvatar: '🗡️',
    opponentLevel: 18,
    status: 'active',
    playerScore: 450,
    opponentScore: 380,
    rewardGold: 120,
    rewardXp: 250,
  },
  {
    id: 'pvp_2',
    opponentName: 'Thorin Ironclad',
    opponentAvatar: '🛡️',
    opponentLevel: 15,
    status: 'pending',
    playerScore: 0,
    opponentScore: 0,
    rewardGold: 80,
    rewardXp: 180,
  },
];
