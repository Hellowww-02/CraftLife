/**
 * useTaskReorder — wiring helper for the task views (Habits / Dailies / Quests).
 *
 * A task view shows a *filtered* subset of the full list (by folder tab, search,
 * difficulty). Dragging reorders within that visible subset; this hook computes
 * the new order of the FULL list by re-inserting the reordered subset into its
 * original slots and delegates the new full array to `onReorderAll` (which
 * optimistically updates state and persists via /api/tasks/reorder).
 */
import { useDragReorder, reorderList, DragReorderState } from './useDragReorder';

/** Re-insert the reordered subset into its original positions within `all`. */
function spliceBack<T extends { id: string }>(all: T[], filtered: T[], nextFiltered: T[]): T[] {
  if (filtered.length !== nextFiltered.length) return all;
  let cursor = 0;
  return all.map((item) => {
    // Keep only the exact same object references that were part of the subset.
    if (filtered.some((f) => f.id === item.id)) {
      return nextFiltered[cursor++] ?? item;
    }
    return item;
  });
}

export function useTaskReorder<T extends { id: string }>(
  all: T[],
  filtered: T[],
  onReorderAll: (next: T[]) => void,
): DragReorderState {
  return useDragReorder<T>(
    filtered,
    'list',
    (from, to) => {
      const nextFiltered = reorderList(filtered, from, to);
      onReorderAll(spliceBack(all, filtered, nextFiltered));
    },
  );
}
