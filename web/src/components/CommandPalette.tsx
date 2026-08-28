import React, { useEffect, useMemo, useState } from 'react';
import { ActiveView } from '../types';
import { t } from '../i18n';
import { useGame } from '../context/GameContext';

/** Sama urutan NavBar._TABS (+ boss via palet, tidak di sidebar utama). */
const PAGES: { id: ActiveView; i18n: string; fallback: string }[] = [
  { id: 'dashboard', i18n: 'nav_home', fallback: 'Home' },
  { id: 'profile', i18n: 'nav_profile', fallback: 'Profile' },
  { id: 'habits', i18n: 'nav_habits', fallback: 'Habits' },
  { id: 'dailies', i18n: 'nav_dailies', fallback: 'Dailies' },
  { id: 'quests', i18n: 'nav_quests', fallback: 'Quests' },
  { id: 'sport', i18n: 'nav_sporttrack', fallback: 'SportTrack' },
  { id: 'economy', i18n: 'nav_economy', fallback: 'Economy' },
  { id: 'supplies', i18n: 'nav_supplies', fallback: 'Supplies' },
  { id: 'nutrition', i18n: 'nav_health_food', fallback: 'Health & Food' },
  { id: 'lovespace', i18n: 'nav_love', fallback: 'Love Space' },
  { id: 'learning', i18n: 'nav_learning', fallback: 'Learning' },
  { id: 'pomodoro', i18n: 'nav_pomodoro', fallback: 'Pomodoro' },
  { id: 'music', i18n: 'nav_music', fallback: 'Music' },
  { id: 'notes', i18n: 'nav_notes', fallback: 'Notes' },
  { id: 'reminders', i18n: 'nav_reminders', fallback: 'Reminders' },
  { id: 'calendar', i18n: 'nav_calendar', fallback: 'Calendar' },
  { id: 'craft', i18n: 'nav_crafting', fallback: 'Crafting' },
  { id: 'shop', i18n: 'nav_shop', fallback: 'Shop' },
  { id: 'pets', i18n: 'nav_pets', fallback: 'Pets' },
  { id: 'friends', i18n: 'nav_friends', fallback: 'Friends' },
  { id: 'guild', i18n: 'nav_guild', fallback: 'Guild' },
  { id: 'achievements', i18n: 'nav_achievement', fallback: 'Achievement' },
  { id: 'leaderboard', i18n: 'nav_leaderboard', fallback: 'Leaderboard' },
  { id: 'settings', i18n: 'nav_settings', fallback: 'Settings' },
  { id: 'boss', i18n: 'nav_boss', fallback: 'Boss' },
];

export const CommandPalette: React.FC<{
  open: boolean;
  onClose: () => void;
  onSelectView: (v: ActiveView) => void;
}> = ({ open, onClose, onSelectView }) => {
  const { habits, triggerHabit, lang } = useGame();
  const [q, setQ] = useState('');

  useEffect(() => {
    if (!open) setQ('');
  }, [open]);

  const items = useMemo(() => {
    const s = q.trim().toLowerCase();
    const pages = PAGES.filter(
      (p) => !s || p.fallback.toLowerCase().includes(s) || p.id.includes(s) || t(p.i18n, p.fallback).toLowerCase().includes(s)
    ).map((p) => ({ kind: 'page' as const, id: p.id, label: t(p.i18n, lang === 'id' ? p.fallback : p.fallback) }));
    const acts = habits
      .filter((h) => !s || h.title.toLowerCase().includes(s))
      .slice(0, 8)
      .map((h) => ({ kind: 'habit' as const, id: h.id, label: `+ ${h.title}` }));
    return [...pages, ...acts];
  }, [q, habits, lang]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[80] bg-slate-950/70 backdrop-blur-sm flex items-start justify-center pt-24" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t('web_palette_placeholder', 'Cari halaman atau habit… (Ctrl+K)')}
          className="w-full px-4 py-3 bg-transparent text-sm outline-none border-b border-slate-800"
        />
        <div className="max-h-72 overflow-y-auto p-2 space-y-1">
          {items.map((it) => (
            <button
              key={it.kind + it.id}
              type="button"
              className="w-full text-left px-3 py-2 rounded-xl text-sm hover:bg-slate-800 text-slate-200"
              onClick={() => {
                if (it.kind === 'page') onSelectView(it.id as ActiveView);
                else triggerHabit(it.id, true);
                onClose();
              }}
            >
              {it.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
