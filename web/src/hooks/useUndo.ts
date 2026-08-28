/**
 * useUndo — parity for the PyQt `UndoToast` behaviour.
 *
 * Lets an action be "undone" within a short window by pushing an undo entry
 * that carries a redo action and a friendly label. The caller invokes the
 * redo when the user clicks Undo, and/or after a timeout.
 */
import { useCallback, useRef, useState } from 'react';

export interface UndoEntry {
  /** key (e.g. 'task.delete') for i18n-friendly rendering */
  key: string;
  /** short label already localised by the caller */
  label: string;
  /** invoked when the user presses Undo */
  redo: () => void;
}

interface UndoState {
  entry: UndoEntry | null;
  /** trigger undo */
  undo: () => void;
  /** push a new undoable action; replaces any pending one (previous redo is dropped) */
  push: (entry: UndoEntry) => void;
  /** clear without undoing */
  dismiss: () => void;
}

/**
 * @param timeoutMs auto-dismiss window; pass 0 to require explicit user dismiss.
 */
export function useUndo(timeoutMs = 5000): UndoState {
  const [entry, setEntry] = useState<UndoEntry | null>(null);
  const timerRef = useRef<number | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const push = useCallback(
    (next: UndoEntry) => {
      clearTimer();
      setEntry(next);
      if (timeoutMs > 0) {
        timerRef.current = window.setTimeout(() => {
          setEntry(null);
          timerRef.current = null;
        }, timeoutMs);
      }
    },
    [clearTimer, timeoutMs],
  );

  const undo = useCallback(() => {
    clearTimer();
    setEntry((curr) => {
      curr?.redo();
      return null;
    });
  }, [clearTimer]);

  const dismiss = useCallback(() => {
    clearTimer();
    setEntry(null);
  }, [clearTimer]);

  return { entry, undo, push, dismiss };
}
