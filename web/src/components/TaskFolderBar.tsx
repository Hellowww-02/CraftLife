import React, { useState } from 'react';
import { useGame } from '../context/GameContext';
import { TaskFolder } from '../types';
import { t } from '../i18n';
import { FolderIconPicker } from './FolderIconPicker';

type Mode = 'habit' | 'daily' | 'todo' | 'sport' | 'economy';

export function useModeFolders(mode: Mode): TaskFolder[] {
  const { taskFolders } = useGame();
  return taskFolders.filter((f) => !f.mode || f.mode === mode);
}

/**
 * TaskFolderBar — parity for the PyQt `FolderDialog` + TaskPage folder strip.
 * Supports: folder create, rename (pencil), duplicate, delete, and
 * **cross-folder drag&drop** targets (a task dragged onto a folder chip moves
 * into it). Emits `onDropInto(folderId)` so the parent view can persist via
 * the reorder API (which also sets folder_id).
 */
export const TaskFolderBar: React.FC<{
  mode: Mode;
  selected: string;
  onSelect: (id: string) => void;
  accent: string;
  allLabel: string;
  allCount: number;
  onDropInto?: (folderId: string) => void;
}> = ({ mode, selected, onSelect, accent, allLabel, allCount, onDropInto }) => {
  const { addTaskFolder, renameTaskFolder, duplicateTaskFolder, deleteTaskFolder } = useGame();
  const folders = useModeFolders(mode);
  const [name, setName] = useState('');
  const [dragOver, setDragOver] = useState<string | null>(null);
  // P56: dialog edit folder — nama + ikon (grid FolderIconPicker).
  const [editing, setEditing] = useState<TaskFolder | null>(null);
  const [editName, setEditName] = useState('');
  const [editIcon, setEditIcon] = useState('📁');
  const [showIconGrid, setShowIconGrid] = useState(false);

  const openEdit = (f: TaskFolder) => {
    setEditing(f);
    setEditName(f.name);
    setEditIcon(f.icon || '📁');
  };

  const saveEdit = () => {
    if (!editing) return;
    const trimmed = editName.trim();
    if (!trimmed) return;
    renameTaskFolder(editing.id, trimmed, mode, editIcon || '📁');
    setEditing(null);
  };

  const duplicate = (f: TaskFolder) => {
    duplicateTaskFolder(f.id, mode);
  };

  return (
    <>
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
      <button
        type="button"
        onClick={() => onSelect('all')}
        className={`px-3 py-1.5 rounded-xl font-semibold shrink-0 ${
          selected === 'all' ? accent : 'bg-slate-800/60 text-slate-400 hover:text-slate-100 border border-transparent hover:border-slate-700'
        }`}
      >
        {allLabel} ({allCount})
      </button>
      <button
        type="button"
        onClick={() => onSelect('unorganized')}
        className={`px-3 py-1.5 rounded-xl font-semibold shrink-0 ${
          selected === 'unorganized' ? accent : 'bg-slate-800/60 text-slate-400 hover:text-slate-100 border border-transparent hover:border-slate-700'
        }`}
      >
        {t('ungrouped', 'Ungrouped')}
      </button>
      <div className="flex items-center gap-1 shrink-0">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t('folder_new_placeholder', 'New folder')}
          className="ct-input px-2 py-1 rounded-lg text-[11px] w-28"
        />
        <button
          type="button"
          onClick={() => {
            if (!name.trim()) return;
            addTaskFolder(name.trim(), '📁', '#10b981', mode);
            setName('');
          }}
          className="ct-socket ct-press px-2 py-1 rounded-lg text-slate-200 text-[11px] font-bold border-0"
        >
          +
        </button>
      </div>
      {folders.map((f) => (
        <div key={f.id} className="flex items-center shrink-0 rounded-xl overflow-hidden">
          <button
            type="button"
            onClick={() => onSelect(f.id)}
            onDragOver={(e) => { if (onDropInto) { e.preventDefault(); setDragOver(f.id); } }}
            onDragLeave={() => setDragOver(null)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(null);
              if (onDropInto) onDropInto(f.id);
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 font-semibold transition-all ${
              dragOver === f.id
                ? 'bg-amber-500/30 text-amber-100 ring-1 ring-amber-400'
                : selected === f.id ? accent : 'bg-slate-800/60 text-slate-400 hover:text-slate-100 border border-transparent hover:border-slate-700'
            }`}
          >
            <span>{f.icon}</span>
            <span>{f.name}</span>
          </button>
          <button
            type="button"
            onClick={() => openEdit(f)}
            className="ct-act text-sky-400 rounded-none"
            title={t('folder_tooltip_edit', 'Edit folder')}
          >
            ✎
          </button>
          <button
            type="button"
            onClick={() => duplicate(f)}
            className="ct-act text-emerald-400 rounded-none"
            title={t('folder_tooltip_dup', 'Duplicate folder')}
          >
            ⧉
          </button>
          <button
            type="button"
            onClick={() => deleteTaskFolder(f.id, mode)}
            className="ct-act text-rose-400 rounded-none"
            title={t('folder_tooltip_del', 'Delete folder')}
          >
            ×
          </button>
        </div>
      ))}
      </div>

      {/* P56: dialog edit folder — nama + ikon */}
      {editing && (
        <div className="ct-backdrop fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => setEditing(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-2xl p-5 max-w-sm w-full shadow-2xl space-y-3" onClick={(e) => e.stopPropagation()}>
            <p className="text-sm font-bold text-slate-200">{t('folder_edit_title', '✏️ Edit Folder')}</p>
            <div>
              <label className="block text-[11px] font-bold text-slate-400 mb-1">{t('folder_rename_prompt', 'Folder name:')}</label>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') saveEdit(); }}
                className="ct-input w-full px-3 py-2 rounded-xl text-sm text-slate-100"
                autoFocus
              />
            </div>
            <div>
              <span className="block text-[11px] font-bold text-slate-400 mb-1">{t('folder_edit_icon', 'Ikon')}</span>
              <button
                type="button"
                onClick={() => setShowIconGrid(true)}
                className="text-2xl p-2 rounded-xl bg-slate-950 border border-slate-800 hover:border-cyan-500/50"
                title={t('folder_icon_picker_title', 'Pilih ikon folder')}
              >
                {editIcon}
              </button>
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" onClick={() => setEditing(null)} className="ct-btn ct-btn-secondary ct-btn-sm">{t('btn_cancel', 'Batal')}</button>
              <button type="button" onClick={saveEdit} className="ct-btn ct-btn-primary ct-btn-sm">{t('btn_save', '💾 Simpan')}</button>
            </div>
          </div>
        </div>
      )}

      {/* P56: grid pemilih ikon (terbuka dari dialog edit) */}
      {editing && showIconGrid && (
        <FolderIconPicker
          current={editIcon}
          onPick={(ic) => { setEditIcon(ic); setShowIconGrid(false); }}
          onClose={() => setShowIconGrid(false)}
        />
      )}
    </>
  );
};

export function filterByFolder<T extends { folderId?: string | null }>(
  items: T[],
  selected: string
): T[] {
  if (selected === 'all') return items;
  if (selected === 'unorganized') return items.filter((i) => !i.folderId);
  return items.filter((i) => i.folderId === selected);
}
