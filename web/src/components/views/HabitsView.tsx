import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { TaskDifficulty } from '../../types';
import { t } from '../../i18n';
import { Zap, Plus, Trash2, Edit3, Folder, Flame, TrendingUp, TrendingDown, Check, X } from 'lucide-react';
import { TaskFolderBar, filterByFolder, useModeFolders } from '../TaskFolderBar';
import { useTaskReorder } from '../../hooks/useTaskReorder';
import { TaskTemplateDialog } from '../TaskTemplateDialog';

export const HabitsView: React.FC = () => {
  const { habits, addHabit, editHabit, duplicateHabit, deleteHabit, triggerHabit, reorderHabits, moveTaskAcrossFolders, lang } = useGame();
  const habitFolders = useModeFolders('habit');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTemplateOpen, setIsTemplateOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState<TaskDifficulty>('medium');
  const [isPositive, setIsPositive] = useState(true);
  const [isNegative, setIsNegative] = useState(false);
  const [folderId, setFolderId] = useState<string>('');
  const [notes, setNotes] = useState('');

  const [selectedFolderFilter, setSelectedFolderFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [diffFilter, setDiffFilter] = useState<string>('all');

  const openCreateModal = () => {
    setEditingId(null);
    setTitle('');
    setDifficulty('medium');
    setIsPositive(true);
    setIsNegative(false);
    setFolderId('');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (h: (typeof habits)[0]) => {
    setEditingId(h.id);
    setTitle(h.title);
    setDifficulty(h.difficulty);
    setIsPositive(h.isPositive);
    setIsNegative(h.isNegative);
    setFolderId(h.folderId || '');
    setNotes(h.notes || '');
    setIsModalOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingId) {
      editHabit(editingId, {
        title,
        difficulty,
        isPositive,
        isNegative,
        folderId: folderId || null,
        notes,
      });
    } else {
      addHabit(title, difficulty, isPositive, isNegative, folderId || null, notes);
    }
    setIsModalOpen(false);
  };

  const filteredHabits = filterByFolder(habits, selectedFolderFilter).filter((h) => {
    if (search && !h.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (diffFilter !== 'all' && h.difficulty !== diffFilter) return false;
    return true;
  });

  const drag = useTaskReorder(habits, filteredHabits, reorderHabits);

  const getDifficultyBadge = (diff: TaskDifficulty) => {
    switch (diff) {
      case 'trivial':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-300">{t('task_difficulty_trivial', 'Trivial')}</span>;
      case 'easy':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">{t('task_difficulty_easy', 'Easy')}</span>;
      case 'medium':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">{t('task_difficulty_medium', 'Medium')}</span>;
      case 'hard':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">{t('task_difficulty_hard', 'Hard')}</span>;
      case 'epic':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">{t('task_difficulty_epic', 'Epic')}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="w-6 h-6 text-amber-400" />
            <h2 className="text-xl font-black text-slate-100">{t('habit_habit_tracker', 'Habit Tracker')}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {t('habit_subtitle', 'Execute positive habits (+) to gain XP/Gold and damage Bosses, and eliminate negative habits (-) to safeguard your HP.')}
          </p>
        </div>

        {/* Group aksi kanan: Template + New Habit berdampingan (parity TaskPage header).
            Sebelumnya justify-between menyebar keduanya jauh terpisah. */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setIsTemplateOpen(true)}
            className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold text-slate-200"
          >
            {t('habit_templates', '📋 Templates')}
          </button>
          <button
            id="btn-create-habit"
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs shadow-lg shadow-amber-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {t('habit_new_habit', 'New Habit')}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('habit_search_habits', 'Search habits…')}
          className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 w-48"
        />
        <select
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
          className="px-2 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200"
        >
          <option value="all">{t('habit_all_difficulty', 'All difficulty')}</option>
          <option value="easy">{t('task_difficulty_easy', 'Easy')}</option>
          <option value="medium">{t('task_difficulty_medium', 'Medium')}</option>
          <option value="hard">{t('task_difficulty_hard', 'Hard')}</option>
          <option value="epic">{t('task_difficulty_epic', 'Epic')}</option>
        </select>
      </div>

      <TaskFolderBar
        mode="habit"
        selected={selectedFolderFilter}
        onSelect={setSelectedFolderFilter}
        accent="bg-amber-500/20 text-amber-300 border border-amber-500/40"
        allLabel={t('habit_all_habits', 'All Habits')}
        allCount={habits.length}
        onDropInto={(fid) => {
          const idx = drag.dragIndex;
          if (idx === null) return;
          const it = filteredHabits[idx];
          if (it) moveTaskAcrossFolders('habit', it.id, fid);
        }}
      />

      {/* Habits List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredHabits.map((habit, idx) => {
          const folder = habitFolders.find((f) => f.id === habit.folderId);

          return (
            <div
              key={habit.id}
              draggable
              onDragStart={drag.onDragStart(idx, 'list')}
              onDragOver={(e) => drag.onDragOver(e, idx)}
              onDragEnter={() => drag.onDragEnter(idx)}
              onDrop={(e) => drag.onDrop(e, idx)}
              onDragEnd={drag.onDragEnd}
              className={`rounded-2xl bg-slate-900/80 border p-4 flex flex-col justify-between gap-4 transition-all shadow-md cursor-grab ${
                drag.isDragging(idx) ? 'opacity-40 border-amber-500' : drag.isOver(idx) ? 'border-amber-500/70 shadow-amber-500/10' : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    {getDifficultyBadge(habit.difficulty)}
                    {folder && (
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <span>{folder.icon}</span> {folder.name}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => duplicateHabit(habit.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      title={t('habit_duplicate', 'Duplicate')}
                    >
                      <Folder className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => openEditModal(habit)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      title={t('habit_edit_habit', 'Edit Habit')}
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteHabit(habit.id)}
                      className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
                      title={t('task_delete_title', 'Delete')}
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <h3 className="font-bold text-sm text-slate-100">{habit.title}</h3>
                {habit.notes && <p className="text-xs text-slate-400 mt-1 leading-relaxed">{habit.notes}</p>}
              </div>

              {/* Action Buttons & Streaks */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1 text-emerald-400 font-bold">
                    <TrendingUp className="w-3.5 h-3.5" /> +{habit.positiveStreak}
                  </div>
                  {habit.isNegative && (
                    <div className="flex items-center gap-1 text-rose-400 font-bold">
                      <TrendingDown className="w-3.5 h-3.5" /> -{habit.negativeStreak}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  {habit.isPositive && (
                    <button
                      id={`btn-habit-pos-${habit.id}`}
                      onClick={() => triggerHabit(habit.id, true)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 font-extrabold text-xs border border-emerald-500/40 active:scale-95 transition-all shadow-sm"
                    >
                      <Plus className="w-3.5 h-3.5" /> {t('habit_good', 'Good')}
                    </button>
                  )}
                  {habit.isNegative && (
                    <button
                      id={`btn-habit-neg-${habit.id}`}
                      onClick={() => triggerHabit(habit.id, false)}
                      className="flex items-center gap-1 px-3 py-1.5 rounded-xl bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 font-extrabold text-xs border border-rose-500/40 active:scale-95 transition-all shadow-sm"
                    >
                      <X className="w-3.5 h-3.5" /> {t('habit_bad', 'Bad')}
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredHabits.length === 0 && (
        <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
          <Zap className="w-8 h-8 text-amber-500/40 mx-auto mb-2" />
          <p className="text-sm font-semibold">{t('habit_no_habits_in_this_category', 'No habits in this category.')}</p>
          <button
            onClick={openCreateModal}
            className="mt-3 px-4 py-2 rounded-xl bg-amber-500 text-slate-950 text-xs font-bold hover:bg-amber-400"
          >
            {t('habit_create_first_habit', 'Create First Habit')}
          </button>
        </div>
      )}

      {/* Create / Edit Habit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">
              {editingId ? (t('habit_edit_habit', 'Edit Habit')) : (t('habit_new_habit', 'New Habit'))}
            </h3>

            <form onSubmit={handleSave} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('habit_habit_title', 'Habit Title')}</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder={t('ph_e_g_minum_2l_air_read_15_mins', 'e.g. Minum 2L Air / Read 15 mins')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{t('habit_difficulty', 'Difficulty')}</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as TaskDifficulty)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                  >
                    <option value="trivial">{t('task_difficulty_trivial', 'Trivial')}</option>
                    <option value="easy">{t('task_difficulty_easy', 'Easy')}</option>
                    <option value="medium">{t('task_difficulty_medium', 'Medium')}</option>
                    <option value="hard">{t('task_difficulty_hard', 'Hard')}</option>
                    <option value="epic">{t('task_difficulty_epic', 'Epic')}</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{t('habit_folder', 'Folder')}</label>
                  <select
                    value={folderId}
                    onChange={(e) => setFolderId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                  >
                    <option value="">{t('habit_no_folder', 'No Folder')}</option>
                    {habitFolders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.icon} {f.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('habit_habit_nature', 'Habit Nature')}</label>
                <div className="grid grid-cols-2 gap-3">
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-800 border border-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isPositive}
                      onChange={(e) => setIsPositive(e.target.checked)}
                      className="rounded text-emerald-500 focus:ring-0"
                    />
                    <span className="text-emerald-400 font-bold">{t('habit_positive', '+ Positive')}</span>
                  </label>
                  <label className="flex items-center gap-2 p-2.5 rounded-xl bg-slate-800 border border-slate-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isNegative}
                      onChange={(e) => setIsNegative(e.target.checked)}
                      className="rounded text-rose-500 focus:ring-0"
                    />
                    <span className="text-rose-400 font-bold">{t('habit_negative', '- Negative')}</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{t('habit_notes', 'Notes')}</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t('ph_tips_or_motivations', 'Tips or motivations...')}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {t('habit_cancel', 'Cancel')}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold"
                >
                  {t('habit_save', 'Save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <TaskTemplateDialog mode="habit" open={isTemplateOpen} onClose={() => setIsTemplateOpen(false)} />
    </div>
  );
};
