import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActiveView } from '../types';
import { t } from '../i18n';
import { useGame } from '../context/GameContext';
import { useFocusTrap } from '../hooks/useFocusTrap';

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

type Item =
  | { kind: 'page'; id: string; label: string }
  | { kind: 'habit' | 'daily' | 'quest'; id: string; label: string };

export const CommandPalette: React.FC<{
  open: boolean;
  onClose: () => void;
  onSelectView: (v: ActiveView) => void;
}> = ({ open, onClose, onSelectView }) => {
  const { habits, dailies, quests, triggerHabit, toggleDaily, toggleQuest, lang } = useGame();
  const [q, setQ] = useState('');
  const [sel, setSel] = useState(0);
  const listRef = useRef<HTMLDivElement | null>(null);
  const trapRef = useFocusTrap<HTMLDivElement>(open);

  useEffect(() => {
    if (!open) {
      setQ('');
      setSel(0);
    }
  }, [open ]);

  const pages = useMemo(() => {
    const s = q.trim().toLowerCase();
    return PAGES.filter(
      (p) => !s || p.fallback.toLowerCase().includes(s) || p.id.includes(s) || t(p.i18n, p.fallback).toLowerCase().includes(s)
    ).map((p): Item => ({ kind: 'page', id: p.id, label: t(p.i18n, p.fallback) }));
  }, [q, lang]);

  const actions = useMemo(() => {
    const s = q.trim().toLowerCase();
    const match = (title: string) => !s || title.toLowerCase().includes(s);
    const out: Item[] = [];
    // E01: aksi cepat Habit/Daily/Quest yg belum selesai (dulu cuma habit).
    habits.filter((h) => match(h.title)).slice(0, 6).forEach((h) => out.push({ kind: 'habit', id: h.id, label: `+ ${h.title}` }));
    dailies.filter((d) => !d.isCompletedToday && match(d.title)).slice(0, 5).forEach((d) => out.push({ kind: 'daily', id: d.id, label: `+ ${d.title}` }));
    quests.filter((x) => !x.isCompleted && match(x.title)).slice(0, 5).forEach((x) => out.push({ kind: 'quest', id: x.id, label: `+ ${x.title}` }));
    return out;
  }, [q, habits, dailies, quests]);

  const items = useMemo(() => [...pages, ...actions], [pages, actions]);

  useEffect(() => {
    setSel(0);
  }, [q]);

  // E01: jaga opsi terpilih tetap terlihat saat navigasi keyboard.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${sel}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [sel, open]);

  if (!open) return null;

  const run = (it: Item) => {
    if (it.kind === 'page') onSelectView(it.id as ActiveView);
    else if (it.kind === 'habit') triggerHabit(it.id, true);
    else if (it.kind === 'daily') toggleDaily(it.id);
    else toggleQuest(it.id);
    onClose();
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    // E01: Ctrl+1..9 = lompat ke halaman cepat (sesuai janji key palette_footer).
    if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '9') {
      const pg = pages[Number(e.key) - 1];
      if (pg) {
        e.preventDefault();
        run(pg);
      }
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSel((v) => (items.length ? (v + 1) % items.length : 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSel((v) => (items.length ? (v - 1 + items.length) % items.length : 0));
    } else if (e.key === 'Enter') {
      const it = items[sel];
      if (it) {
        e.preventDefault();
        run(it);
      }
    }
  };

  const renderBtn = (it: Item, idx: number) => (
    <button
      key={it.kind + it.id}
      type="button"
      role="option"
      aria-selected={sel === idx}
      data-idx={idx}
      id={`palette-opt-${idx}`}
      onMouseMove={() => { if (sel !== idx) setSel(idx); }}
      className={`ct-palette-item w-full text-left px-3 py-2 rounded-xl text-sm text-slate-200 ${sel === idx ? 'bg-slate-800' : 'hover:bg-slate-800'}`}
      onClick={() => run(it)}
    >
      {it.label}
    </button>
  );

  return (
    <div className="ct-backdrop fixed inset-0 z-[80] flex items-start justify-center pt-24" onClick={onClose}>
      <div
        ref={trapRef}
        className="ct-dialog w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={onKeyDown}
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-listbox"
          aria-activedescendant={items.length ? `palette-opt-${sel}` : undefined}
          placeholder={t('web_palette_placeholder', 'Cari halaman atau tugas… (Ctrl+K)')}
          className="w-full px-4 py-3.5 bg-transparent text-[15px] font-medium text-slate-100 placeholder:text-slate-500 outline-none border-b border-slate-800"
        />
        <div ref={listRef} id="palette-listbox" role="listbox" aria-label={t('palette_title', 'Lompat ke mana saja…')} className="ct-stagger max-h-72 overflow-y-auto p-2 space-y-1">
          {pages.length > 0 && (
            <div className="px-3 pt-1 text-[10px] font-black uppercase tracking-wider text-slate-500">
              {t('palette_section_pages', 'Halaman')}
            </div>
          )}
          {pages.map((it, i) => renderBtn(it, i))}
          {actions.length > 0 && (
            <div className="px-3 pt-2 text-[10px] font-black uppercase tracking-wider text-slate-500">
              {t('palette_section_actions', 'Aksi')}
            </div>
          )}
          {actions.map((it, i) => renderBtn(it, pages.length + i))}
          {items.length === 0 && (
            <div className="px-3 py-6 text-center text-sm text-slate-500">
              {t('palette_no_results', 'Tidak ada hasil')}
            </div>
          )}
        </div>
        <div className="px-4 py-2 border-t border-slate-800 text-[11px] text-slate-500">
          {t('shortcuts_hint', 'Tekan ? untuk semua pintasan')}
        </div>
      </div>
    </div>
  );
};
