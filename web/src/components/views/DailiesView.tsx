import React, { useState } from 'react';
import { useGame } from '../../context/GameContext';
import { TaskDifficulty } from '../../types';
import { CalendarCheck, Plus, Trash2, Edit3, Flame, Shield, Snowflake, Check, RefreshCw } from 'lucide-react';
import { TaskFolderBar, filterByFolder, useModeFolders } from '../TaskFolderBar';
import { useTaskReorder } from '../../hooks/useTaskReorder';
import { TaskTemplateDialog } from '../TaskTemplateDialog';

const DAYS_SHORT = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
// Parity WeekdaySelector PyQt: urutan Senin→Minggu; indeks JS getDay (0=Minggu).
const DAYS_SHORT_ID = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min'];
const DAILY_DAY_ORDER = [1, 2, 3, 4, 5, 6, 0]; // posisi button → js getDay()

export const DailiesView: React.FC = () => {
  const { dailies, addDaily, editDaily, duplicateDaily, deleteDaily, toggleDaily, failDaily, useDailyFreeze, reorderDailies, moveTaskAcrossFolders, lang, user } = useGame();
  const dailyFolders = useModeFolders('daily');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isTemplateOpen, setIsTemplateOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Form
  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState<TaskDifficulty>('medium');
  const [repeatDays, setRepeatDays] = useState<number[]>([]);
  const [folderId, setFolderId] = useState<string>('');
  const [notes, setNotes] = useState('');

  const [selectedFolderFilter, setSelectedFolderFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [diffFilter, setDiffFilter] = useState<string>('all');

  const openCreateModal = () => {
    setEditingId(null);
    setTitle('');
    setDifficulty('medium');
    setRepeatDays([0, 1, 2, 3, 4, 5, 6]);
    setFolderId('');
    setNotes('');
    setIsModalOpen(true);
  };

  const openEditModal = (d: (typeof dailies)[0]) => {
    setEditingId(d.id);
    setTitle(d.title);
    setDifficulty(d.difficulty);
    setRepeatDays(d.repeatDays);
    setFolderId(d.folderId || '');
    setNotes(d.notes || '');
    setIsModalOpen(true);
  };

  const toggleDaySelection = (dayIdx: number) => {
    if (repeatDays.includes(dayIdx)) {
      // PyQt: kosong = tiap hari; boleh menghapus sampai 0 hari terpilih.
      setRepeatDays(repeatDays.filter((d) => d !== dayIdx));
    } else {
      setRepeatDays([...repeatDays, dayIdx].sort());
    }
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;

    if (editingId) {
      editDaily(editingId, {
        title,
        difficulty,
        repeatDays,
        folderId: folderId || null,
        notes,
      });
    } else {
      addDaily(title, difficulty, repeatDays, folderId || null, notes);
    }
    setIsModalOpen(false);
  };

  const filteredDailies = filterByFolder(dailies, selectedFolderFilter).filter((d) => {
    if (search && !d.title.toLowerCase().includes(search.toLowerCase())) return false;
    if (diffFilter !== 'all' && d.difficulty !== diffFilter) return false;
    return true;
  });

  const drag = useTaskReorder(dailies, filteredDailies, reorderDailies);

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
            <CalendarCheck className="w-6 h-6 text-emerald-400" />
            <h2 className="text-xl font-black text-slate-100">{lang === 'id' ? 'Rutinitas Harian (Dailies)' : 'Daily Routine (Dailies)'}</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {lang === 'id'
              ? 'Tugas berulang setiap hari. Jaga streak harianmu dan dapatkan bonus multiplier untuk menyerang Boss!'
              : 'Recurring daily objectives. Maintain streaks to earn extra rewards and unleash powerful attacks on Bosses!'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1 px-3 py-2 rounded-xl bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 text-xs font-bold">
            <Snowflake className="w-4 h-4 text-cyan-400" />
            <span>Freeze Shields: {user.freezeSlots}</span>
          </div>

          <button
            type="button"
            onClick={() => setIsTemplateOpen(true)}
            className="px-3 py-2 rounded-xl bg-slate-800 text-xs font-bold text-slate-200"
          >
            {lang === 'id' ? '📋 Template' : '📋 Templates'}
          </button>
          <button
            id="btn-create-daily"
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs shadow-lg shadow-emerald-500/20 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" /> {lang === 'id' ? 'Buat Daily Baru' : 'New Daily'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={lang === 'id' ? 'Cari daily…' : 'Search dailies…'}
          className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-100 w-48"
        />
        <select
          value={diffFilter}
          onChange={(e) => setDiffFilter(e.target.value)}
          className="px-2 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200"
        >
          <option value="all">{lang === 'id' ? 'Semua kesulitan' : 'All difficulty'}</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
          <option value="epic">Epic</option>
        </select>
      </div>

      <TaskFolderBar
        mode="daily"
        selected={selectedFolderFilter}
        onSelect={setSelectedFolderFilter}
        accent="bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
        allLabel={lang === 'id' ? 'Semua Daily' : 'All Dailies'}
        allCount={dailies.length}
        onDropInto={(fid) => {
          const idx = drag.dragIndex;
          if (idx === null) return;
          const it = filteredDailies[idx];
          if (it) moveTaskAcrossFolders('daily', it.id, fid);
        }}
      />

      {/* Dailies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredDailies.map((daily, idx) => {
          const folder = dailyFolders.find((f) => f.id === daily.folderId);

          return (
            <div
              key={daily.id}
              draggable
              onDragStart={drag.onDragStart(idx, 'list')}
              onDragOver={(e) => drag.onDragOver(e, idx)}
              onDragEnter={() => drag.onDragEnter(idx)}
              onDrop={(e) => drag.onDrop(e, idx)}
              onDragEnd={drag.onDragEnd}
              className={`rounded-2xl border p-4.5 flex flex-col justify-between gap-4 transition-all cursor-grab ${
                drag.isDragging(idx) ? 'opacity-40 border-emerald-500' : drag.isOver(idx) ? 'border-emerald-500/70 shadow-emerald-500/10' : ''
              } ${
                daily.isCompletedToday
                  ? 'bg-emerald-950/15 border-emerald-500/30'
                  : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    {getDifficultyBadge(daily.difficulty)}
                    {folder && (
                      <span className="text-[10px] font-semibold text-slate-400 flex items-center gap-1">
                        <span>{folder.icon}</span> {folder.name}
                      </span>
                    )}
                    {daily.isFrozen && (
                      <span className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center gap-1">
                        <Snowflake className="w-3 h-3" /> Frozen
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1">
                    {!daily.isCompletedToday && (
                      <button
                        onClick={() => failDaily(daily.id)}
                        className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title={lang === 'id' ? 'Gagal (HP)' : 'Fail (HP)'}
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                      </button>
                    )}
                    <button
                      onClick={() => duplicateDaily(daily.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors"
                      title={lang === 'id' ? 'Duplikasi' : 'Duplicate'}
                    >
                      <Shield className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => useDailyFreeze(daily.id)}
                      className="p-1.5 rounded-lg text-cyan-400 hover:bg-cyan-500/10 transition-colors"
                      title="Freeze Streak with Ice Shield"
                    >
                      <Snowflake className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => openEditModal(daily)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      title="Edit Daily"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => deleteDaily(daily.id)}
                      className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 transition-colors"
                      title="Delete Daily"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Title & Checkbox */}
                <div
                  onClick={() => toggleDaily(daily.id)}
                  className="flex items-center gap-3 cursor-pointer select-none"
                >
                  <div
                    className={`w-6 h-6 rounded-lg flex items-center justify-center border transition-all ${
                      daily.isCompletedToday
                        ? 'bg-emerald-500 border-emerald-400 text-slate-950 font-bold'
                        : 'bg-slate-800 border-slate-700 hover:border-emerald-500/50'
                    }`}
                  >
                    {daily.isCompletedToday && <Check className="w-4 h-4" />}
                  </div>

                  <div className="min-w-0">
                    <h3
                      className={`font-bold text-sm transition-all ${
                        daily.isCompletedToday ? 'line-through text-slate-400' : 'text-slate-100'
                      }`}
                    >
                      {daily.title}
                    </h3>
                    {daily.notes && <p className="text-xs text-slate-400 mt-0.5">{daily.notes}</p>}
                  </div>
                </div>
              </div>

              {/* Bottom Schedule & Streaks */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                {/* Active Days */}
                <div className="flex items-center gap-1">
                  {(lang === 'id' ? DAYS_SHORT_ID : DAYS_SHORT).map((day, pos) => {
                    const jsDay = DAILY_DAY_ORDER[pos];
                    const isScheduled = daily.repeatDays.includes(jsDay);
                    return (
                      <span
                        key={day}
                        className={`w-5 h-5 rounded-md flex items-center justify-center text-[10px] font-bold ${
                          isScheduled
                            ? 'bg-slate-800 text-emerald-400 border border-emerald-500/30'
                            : 'bg-slate-900/40 text-slate-400'
                        }`}
                      >
                        {day[0]}
                      </span>
                    );
                  })}
                </div>

                <div className="flex items-center gap-1 font-bold text-amber-400">
                  <Flame className="w-4 h-4 fill-amber-500 text-amber-500" />
                  <span>{daily.streak} {lang === 'id' ? 'Hari' : 'Days'}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {filteredDailies.length === 0 && (
        <div className="text-center py-12 text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800/80">
          <CalendarCheck className="w-8 h-8 text-emerald-500/40 mx-auto mb-2" />
          <p className="text-sm font-semibold">{lang === 'id' ? 'Belum ada daily task di kategori ini.' : 'No daily tasks in this category.'}</p>
        </div>
      )}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-black text-slate-100">
              {editingId ? (lang === 'id' ? 'Edit Daily' : 'Edit Daily') : (lang === 'id' ? 'Buat Daily Baru' : 'New Daily')}
            </h3>

            <form onSubmit={handleSave} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Judul Tugas Harian' : 'Daily Task Title'}</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. 20 Pushups & Stretching"
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Tingkat Kesulitan' : 'Difficulty'}</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value as TaskDifficulty)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="trivial">Trivial</option>
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                    <option value="epic">Epic</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Folder' : 'Folder'}</label>
                  <select
                    value={folderId}
                    onChange={(e) => setFolderId(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="">{lang === 'id' ? 'Tanpa Folder' : 'No Folder'}</option>
                    {dailyFolders.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.icon} {f.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1.5">{lang === 'id' ? 'Jadwal Hari Pengulangan' : 'Repeat Days'}</label>
                <div className="grid grid-cols-7 gap-1.5">
                  {(lang === 'id' ? DAYS_SHORT_ID : DAYS_SHORT).map((day, pos) => {
                    const jsDay = DAILY_DAY_ORDER[pos];
                    const isSelected = repeatDays.includes(jsDay);
                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDaySelection(jsDay)}
                        className={`py-2 rounded-xl text-xs font-bold border transition-colors ${
                          isSelected
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}
                      >
                        {day}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">{lang === 'id' ? 'Catatan' : 'Notes'}</label>
                <textarea
                  rows={2}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Routine instructions..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-100 focus:outline-none focus:border-emerald-500"
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
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                >
                  {lang === 'id' ? 'Simpan' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <TaskTemplateDialog mode="daily" open={isTemplateOpen} onClose={() => setIsTemplateOpen(false)} />
    </div>
  );
};
