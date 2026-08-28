import { LearningNotebook } from '../types';

export const DEFAULT_NOTEBOOKS: LearningNotebook[] = [
  {
    id: 'nb_productivity_rpg',
    title: 'Gamified Productivity & Habit Loops',
    description: 'Core concepts on dopamine pathways, quest design, and habit formation loops.',
    icon: '⚡',
    sources: [
      {
        id: 'src_1',
        title: 'Habit Loop Principles.txt',
        type: 'text',
        content: `A habit consists of four key components: Cue, Craving, Response, and Reward.
Gamification introduces immediate feedback loops by awarding XP, Gold, and Streaks.
When everyday tasks grant visual rewards and character progression, motivation shifts from willpower-dependent to intrinsically engaging.
Positive reinforcement reduces friction, while small incremental daily improvements compound exponentially over time.`,
        wordCount: 52,
        createdAt: '2026-08-20T10:00:00Z',
      },
      {
        id: 'src_2',
        title: 'Deep Work & Focus Optimization.txt',
        type: 'text',
        content: `Deep work requires uninterrupted blocks of 25-50 minutes (Pomodoro technique).
Minimizing context switching preserves executive cognitive function.
Pairing study intervals with binaural beats (Alpha/Theta frequencies) enhances sustained attention and working memory consolidation.`,
        wordCount: 36,
        createdAt: '2026-08-22T14:30:00Z',
      },
    ],
    chatHistory: [
      {
        sender: 'user',
        text: 'How does gamifying daily routines prevent burnout?',
        timestamp: '10:15 AM',
      },
      {
        sender: 'ai',
        text: 'Gamification transforms ambiguous life goals into clear, bite-sized quests with quantifiable progress. By providing instant feedback (XP, Level-ups, Gold) and streak protections, it shifts focus to daily micro-wins instead of overwhelming end outcomes.',
        timestamp: '10:15 AM',
      },
    ],
    flashcards: [
      { id: 'fc_1', question: 'What are the 4 stages of the Habit Loop?', answer: '1. Cue (trigger), 2. Craving (desire), 3. Response (action), 4. Reward (satisfaction).' },
      { id: 'fc_2', question: 'Why is spaced repetition effective for retention?', answer: 'It interrupts the forgetting curve at optimal intervals, transferring knowledge from short-term to long-term memory.' },
      { id: 'fc_3', question: 'What is active recall?', answer: 'Testing yourself to retrieve information from memory rather than passively re-reading notes.' },
    ],
    quizzes: [
      {
        id: 'q_1',
        question: 'Which brain chemical is most closely linked to anticipation of reward and motivation?',
        options: ['Dopamine', 'Cortisol', 'Melatonin', 'Adrenaline'],
        correctAnswerIndex: 0,
        explanation: 'Dopamine drives desire and motivates action when expecting a reward.',
      },
      {
        id: 'q_2',
        question: 'What is the optimal focus duration in the classic Pomodoro Technique?',
        options: ['25 minutes', '90 minutes', '10 minutes', '180 minutes'],
        correctAnswerIndex: 0,
        explanation: '25 minutes of high-intensity focus followed by a 5-minute restorative break.',
      },
    ],
    podcast: [
      { speaker: 'Alex', line: 'Welcome back to the Deep Dive! Today we are exploring how RPG mechanics turn boring chores into dopamine-fueled questlines.' },
      { speaker: 'Sam', line: 'Honestly, the psychology is fascinating. When you see your character level up after finishing laundry or coding, your brain registers immediate satisfaction.' },
      { speaker: 'Alex', line: 'And the streak mechanics keep momentum alive on days when raw motivation is low.' },
      { speaker: 'Sam', line: 'Exactly! Let us look at how habit cues and instant rewards synchronize in CraftLife.' },
    ],
    notes: '# Personal Study Insights\n- Implement 25-min sprints daily\n- Use Active Recall for flashcard revision\n- Celebrate small daily streak wins',
    createdAt: '2026-08-20T10:00:00Z',
  },
];
