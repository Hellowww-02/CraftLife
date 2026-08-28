import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { TaskDifficulty } from '../../types';
import { CheckSquare, Plus, Trash2, Edit3, Calendar, Check, Clock } from 'lucide-react';
import { TaskFolderBar, filterByFolder, useModeFolders } from '../TaskFolderBar';

export const QuestsView: React.FC = () => {
  const { quests, addQuest, editQuest, deleteQuest, toggleQuest, duplicateQuest, lang, applyTaskTemplate } = useGame();
  const questFolders = useModeFolders('todo');
  const [selectedFolderFilter, setSelectedFolderFilter] = useState<string>('all');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form
  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState<TaskDifficulty>('medium');
  const [dueDate, setDueDate] = useState<string>('');
  const [folderId, setFolderId] = useState<string>('');
  const [notes, setNotes] = useState('');

  const [activeFilter, setActiveFilter] = useState<'pending' | 'completed' | 'all'>('pending');
  const [search, setSearch] = useState('');
  const [diffFilter, setDiffFilter] = useState<string>('all');

  const openCreateModal = () => {
    setEditingId(null);
    setTitle('');
    setDifficulty('medium');
    setDueDate('');
    setFolderId('');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (q: (typeof quests)[0]) => {
    setEditingId(q.id);
    setTitle(q.title);
    setDifficulty(q.difficulty);
    setDueDate(q.dueDate || '');
    setFolderId(q.folderId || '');
    setNotes(q.notes || '');
    setIsModalOpen(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingId) {
      editQuest(editingId, {
        title,
        difficulty,
        dueDate: dueDate || null,
        folderId: folderId || null,
        notes,
      });
    } else {
      addQuest(title, difficulty, dueDate || null, folderId || null, notes);
    }
    setIsModalOpen(false);
  };

  const filteredQuests = filterByFolder(quests, selectedFolderFilter).filter((q) => {
    if (activeFilter === 'pending' && q.isCompleted) return false;
    if (activeFilter === 'completed' && !q.isCompleted) return false;
    if (search && !q.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (diffFilter !== 'all' && q.difficulty !== diffFilter) return false;
    return true;
  });

  const getDifficultyBadge = (diff: TaskDifficulty) => {
    switch (diff) {
      case 'trivial':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-800 text-slate-300">Trivial</span>;
      case 'easy':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Easy</span>;
      case 'medium':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">Medium</span>;
      case 'hard':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">Hard</span>;
      case 'epic':
        return <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">Epic</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Daftar Quest & Tugas' : 'Quest & To-Do List'}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Selesaikan tugas satu kali (To-Do) untuk mendapatkan hadiah besar XP, Gold, dan menyerang Boss secara dahsyat!'
              : 'Complete one-time tasks and project goals for huge XP & Gold rewards and high critical strikes against Bosses!'}
          </p>
        </div>

        <button
          type="button"
          onClick={() => applyTaskTemplate('todo', 'project_launch_t')}
          className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold text-slate-200"
        >
          {lang === 'id' ? 'Template PyQt' : 'PyQt templates'}
        </button>
        <button
          id="btn-create-quest"
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-blue-500 hover:bg-blue-400 text-slate-950 font-bold text-xs shadow-lg shadow-blue-500/20 transition-all shrink-0"
        >
          <Plus className="w-4 h-4" /> {lang === 'id' ? 'Buat Quest Baru' : 'New Quest'}
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={lang === 'id' ? 'Cari quest…' : 'Search quests…'}
          className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 w-48"
        />
        <select
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
          className="px-2 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200"
        >
          <option value="all">{lang === 'id' ? 'Semua prioritas' : 'All priorities'}</option>
          <option value="trivial">Trivial</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
          <option value="epic">Epic</option>
        </select>
      </div>

      <TaskFolderBar
        mode="todo"
        selected={selectedFolderFilter}
        onSelect={setSelectedFolderFilter}
        accent="bg-blue-500/20 text-blue-300 border border-blue-500/40"
        allLabel={lang === 'id' ? 'Semua Quest' : 'All Quests'}
        allCount={quests.length}
      />

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-2 text-xs">
        <button
          onClick={() => setActiveFilter('pending')}
          className={`px-3 py-1.5 rounded-xl font-semibold transition-colors ${
            activeFilter === 'pending'
              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
              : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
          }`}
        >
          {lang === 'id' ? 'Belum Selesai' : 'Pending'} ({quests.filter((q) => !q.isCompleted).length})
        </button>

        <button
          onClick={() => setActiveFilter('completed')}
          className={`px-3 py-1.5 rounded-xl font-semibold transition-colors ${
            activeFilter === 'completed'
              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
              : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
          }`}
        >
          {lang === 'id' ? 'Selesai' : 'Completed'} ({quests.filter((q) => q.isCompleted).length})
        </button>

        <button
          onClick={() => setActiveFilter('all')}
          className={`px-3 py-1.5 rounded-xl font-semibold transition-colors ${
            activeFilter === 'all'
              ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
              : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
          }`}
        >
          {lang === 'id' ? 'Semua' : 'All'} ({quests.length})
        </button>
      </div>

      {/* Quests List */}
      <div className="space-y-3">
        {filteredQuests.map((quest) => {
          const folder = questFolders.find((f) => f.id === quest.folderId);

          return (
            <div
              key={quest.id}
              className={`rounded-2xl border p-4 flex items-center justify-between gap-3 transition-all ${
                quest.isCompleted
                  ? 'bg-slate-900/40 border-slate-800/60 opacity-70'
                  : 'bg-slate-900/90 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-3.5 min-w-0">
                <div
                  onClick={() => toggleQuest(quest.id)}
                  className={`w-6 h-6 rounded-lg flex items-center justify-center border cursor-pointer shrink-0 transition-all ${
                    quest.isCompleted
                      ? 'bg-blue-500 border-blue-400 text-slate-950 font-bold'
                      : 'bg-slate-800 border-slate-700 hover:border-blue-500/50'
                  }`}
                >
                  {quest.isCompleted && <Check className="w-4 h-4" />}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {getDifficultyBadge(quest.difficulty)}
                    {folder && (
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <span>{folder.icon}</span> {folder.name}
                      </span>
                    )}
                    {quest.dueDate && (
                      <span className="text-[10px] text-amber-400 flex items-center gap-1 font-semibold">
                        <Clock className="w-3 h-3" /> {quest.dueDate}
                      </span>
                    )}
                  </div>

                  <h3
                    className={`font-bold text-sm truncate ${
                      quest.isCompleted ? 'line-through text-slate-400' : 'text-slate-100'
                    }`}
                  >
                    {quest.title}
                  </h3>
                  {quest.notes && <p className="text-xs text-slate-400 mt-0.5 truncate">{quest.notes}</p>}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => duplicateQuest(quest.id)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                  title={lang === 'id' ? 'Duplikasi' : 'Duplicate'}
                >
                  <Calendar className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => openEditModal(quest)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                  title="Edit Quest"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => deleteQuest(quest.id)}
                  className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
                  title="Delete Quest"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredQuests.length === 0 && (
        <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
          <CheckSquare className="w-8 h-8 text-blue-500/40 mx-auto mb-2" />
          <p className="text-sm font-semibold">{lang === 'id' ? 'Tidak ada quest dalam daftar ini.' : 'No quests in this category.'}</p>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">
              {editingId ? (lang === 'id' ? 'Edit Quest' : 'Edit Quest') : (lang === 'id' ? 'Buat Quest Baru' : 'New Quest')}
            </h3>

            <form onSubmit={handleSave} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Judul Quest / Tugas' : 'Quest Title'}</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Selesaikan Laporan Keuangan Q3"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Tingkat Kesulitan' : 'Difficulty'}</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as TaskDifficulty)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                  >
                    <option value="trivial">Trivial</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                    <option value="epic">Epic</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Tenggat Waktu' : 'Due Date'}</label>
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Folder' : 'Folder'}</label>
                <select
                  value={folderId}
                  onChange={(e) => setFolderId(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                >
                  <option value="">{lang === 'id' ? 'Tanpa Folder' : 'No Folder'}</option>
                  {questFolders.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.icon} {f.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan Tambahan' : 'Notes'}</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Task details and deliverables..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-blue-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  {lang === 'id' ? 'Batal' : 'Cancel'}
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-blue-500 hover:bg-blue-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
