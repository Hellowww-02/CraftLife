/**
 * useDragReorder — parity for PyQt `DraggableCard` / `TaskPage` drag reordering.
 *
 * Provides the state + HTML5 drag handlers to reorder items in a list and to
 * move an item across group boundaries (e.g. tasks between folders or between
 * habit/daily/quest lists). It calls `onReorder` with the reordered array.
 *
 * Design is "presentational": the caller renders list items and spreads the
 * returned handlers. No DOM assumptions beyond HTML5 drag events.
 */
import { useCallback, useRef, useState } from 'react';
import type { DragEvent as ReactDragEvent } from 'react';

interface DragMeta {
  /** index in the source list */
  fromIndex: number;
  /** optional source/group id the item came from */
  fromGroup?: string;
}

export interface DragReorderState {
  /** index currently being dragged (or null) */
  dragIndex: number | null;
  /** group the drag originated from */
  dragGroup: string | null;
  /** index currently hovered/dropped onto (or null) */
  overIndex: number | null;
  /** index that this item is "lifted" to visually before dropping */
  isDragging: (index: number) => boolean;
  isOver: (index: number) => boolean;
  onDragStart: (index: number, group: string) => (e: ReactDragEvent) => void;
  onDragOver: (e: ReactDragEvent, index: number) => void;
  onDragEnter: (index: number) => void;
  onDrop: (e: ReactDragEvent, index: number) => void;
  onDragEnd: () => void;
}

/**
 * @param items    Current ordered items (any array).
 * @param group    Identifier of this group/list (for cross-group moves).
 * @param onReorder Callback with index in this group (from, to) — caller reorders its own array.
 * @param onMoveCross Optional: called with (item/index, fromGroup, toGroup) for cross-list moves.
 */
export function useDragReorder<T>(
  items: T[],
  group: string,
  onReorder: (from: number, to: number) => void,
  onMoveCross?: (index: number, fromGroup: string, toGroup: string) => void,
): DragReorderState {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragGroup, setDragGroup] = useState<string | null>(null);
  const [overIndex, setOverIndex] = useState<number | null>(null);
  const metaRef = useRef<DragMeta>({ fromIndex: -1 });
  // keep items referenced so the generic T is bound (used by callers to render arrays)
  void items;

  const onDragStart = useCallback(
    (index: number, fromGroup: string) => (e: ReactDragEvent) => {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', String(index));
      setDragIndex(index);
      setDragGroup(fromGroup);
      metaRef.current = { fromIndex: index, fromGroup };
    },
    [],
  );

  const onDragOver = useCallback((e: ReactDragEvent, index: number) => {
    // allow dropping anywhere in the list
    if (e.preventDefault) e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (overIndex !== index) setOverIndex(index);
  }, [overIndex]);

  const onDragEnter = useCallback((index: number) => {
    if (overIndex !== index) setOverIndex(index);
  }, [overIndex]);

  const _commit = useCallback(
    (toIndex: number) => {
      const from = metaRef.current.fromIndex;
      const fromGroup = metaRef.current.fromGroup;
      if (from < 0) return;
      if (fromGroup === group) {
        onReorder(from, toIndex);
      } else if (fromGroup !== undefined && onMoveCross) {
        onMoveCross(from, fromGroup, group);
      }
      setDragIndex(null);
      setDragGroup(null);
      setOverIndex(null);
      metaRef.current = { fromIndex: -1 };
    },
    [group, onReorder, onMoveCross],
  );

  const onDrop = useCallback((e: ReactDragEvent, index: number) => {
    if (e.preventDefault) e.preventDefault();
    _commit(index);
  }, [_commit]);

  const onDragEnd = useCallback(() => {
    setDragIndex(null);
    setDragGroup(null);
    setOverIndex(null);
    metaRef.current = { fromIndex: -1 };
  }, []);

  const isDragging = useCallback((index: number) => dragIndex === index, [dragIndex]);
  const isOver = useCallback((index: number) => overIndex === index && dragIndex !== null && overIndex !== dragIndex, [overIndex, dragIndex]);

  return {
    dragIndex,
    dragGroup,
    overIndex,
    isDragging,
    isOver,
    onDragStart,
    onDragOver,
    onDragEnter,
    onDrop,
    onDragEnd,
  };
}

/** Reorder helper: move `from` to `to` in a shallow copy. */
export function reorderList<T>(list: T[], from: number, to: number): T[] {
  const next = list.slice();
  if (from < 0 || from >= next.length || to < 0 || to >= next.length) return next;
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next;
}

/** Move item from one list into another at `to`. Returns new arrays via setter callbacks. */
export function moveAcrossLists<T>(
  source: T[],
  target: T[],
  from: number,
  to: number,
): { source: T[]; target: T[] } {
  const nextSource = source.slice();
  const nextTarget = target.slice();
  if (from < 0 || from >= nextSource.length) return { source, target };
  const [moved] = nextSource.splice(from, 1);
  const targetIndex = Math.max(0, Math.min(to, nextTarget.length));
  nextTarget.splice(targetIndex, 0, moved);
  return { source: nextSource, target: nextTarget };
}
