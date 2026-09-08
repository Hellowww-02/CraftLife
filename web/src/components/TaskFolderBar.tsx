import React, { useState } from 'react';
import { useGame } from '../context/GameContext';
import { TaskFolder } from '../types';
import { t } from '../i18n';

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

  const rename = (f: TaskFolder) => {
    const next = window.prompt(t('folder_rename_prompt', 'Folder name:'), f.name);
    if (next === null) return;
    const trimmed = next.trim();
    if (!trimmed || trimmed === f.name) return;
    renameTaskFolder(f.id, trimmed, mode);
  };

  const duplicate = (f: TaskFolder) => {
    duplicateTaskFolder(f.id, mode);
  };

  return (
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
            onClick={() => rename(f)}
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
