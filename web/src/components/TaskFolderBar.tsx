import React, { useEffect, useState } from 'react';
import { useGame } from '../context/GameContext';
import { life } from '../api/life';
import { TaskFolder } from '../types';

type Mode = 'habit' | 'daily' | 'todo' | 'sport';

export function useModeFolders(mode: Mode): TaskFolder[] {
  const { taskFolders } = useGame();
  return taskFolders.filter((f) => !f.mode || f.mode === mode);
}

export const TaskFolderBar: React.FC<{
  mode: Mode;
  selected: string;
  onSelect: (id: string) => void;
  accent: string;
  allLabel: string;
  allCount: number;
}> = ({ mode, selected, onSelect, accent, allLabel, allCount }) => {
  const { addTaskFolder, deleteTaskFolder, applyTaskTemplate, lang } = useGame();
  const folders = useModeFolders(mode);
  const [name, setName] = useState('');
  const [templates, setTemplates] = useState<{ key: string; name: string; icon: string }[]>([]);

  useEffect(() => {
    life
      .listTemplates(mode)
      .then((r) => {
        if (Array.isArray(r?.templates)) setTemplates(r.templates);
      })
      .catch(() => {});
  }, [mode]);

  return (
    <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
      <button
        type="button"
        onClick={() => onSelect('all')}
        className={`px-3 py-1.5 rounded-xl font-semibold shrink-0 ${
          selected === 'all' ? accent : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
        }`}
      >
        {allLabel} ({allCount})
      </button>
      <button
        type="button"
        onClick={() => onSelect('unorganized')}
        className={`px-3 py-1.5 rounded-xl font-semibold shrink-0 ${
          selected === 'unorganized' ? accent : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
        }`}
      >
        {lang === 'id' ? 'Tanpa folder' : 'Ungrouped'}
      </button>
      {templates.slice(0, 4).map((tpl) => (
        <button
          key={tpl.key}
          type="button"
          onClick={() => applyTaskTemplate(mode, tpl.key)}
          className="px-2 py-1.5 rounded-xl bg-slate-800/80 text-slate-300 text-[11px] font-semibold hover:text-slate-100 shrink-0"
          title={tpl.name}
        >
          {tpl.icon} {tpl.name}
        </button>
      ))}
      <div className="flex items-center gap-1 shrink-0">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={lang === 'id' ? 'Folder baru' : 'New folder'}
          className="px-2 py-1 rounded-lg bg-slate-800 border border-slate-700 text-[11px] w-28"
        />
        <button
          type="button"
          onClick={() => {
            if (!name.trim()) return;
            addTaskFolder(name.trim(), '📁', '#10b981', mode);
            setName('');
          }}
          className="px-2 py-1 rounded-lg bg-slate-700 text-slate-100 text-[11px] font-bold"
        >
          +
        </button>
      </div>
      {folders.map((f) => (
        <div key={f.id} className="flex items-center shrink-0">
          <button
            type="button"
            onClick={() => onSelect(f.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-l-xl font-semibold ${
              selected === f.id ? accent : 'bg-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            <span>{f.icon}</span>
            <span>{f.name}</span>
          </button>
          <button
            type="button"
            onClick={() => deleteTaskFolder(f.id, mode)}
            className="px-1.5 py-1.5 rounded-r-xl bg-slate-800/80 text-rose-400 hover:bg-rose-500/20"
            title={lang === 'id' ? 'Hapus folder' : 'Delete folder'}
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
