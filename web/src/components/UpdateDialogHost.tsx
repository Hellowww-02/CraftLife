import React, { useEffect } from 'react';
import { useGame } from '../context/GameContext';
import { UpdateDialog } from './UpdateDialog';

/** C07: mount global dialog update — tampil bila context membawa pendingUpdate. */
export const UpdateDialogHost: React.FC = () => {
  const { pendingUpdate, setPendingUpdate } = useGame();
  const offeredVersion = pendingUpdate?.version || '';
  useEffect(() => {
    if (offeredVersion) {
      try {
        sessionStorage.setItem('craftlife_update_offered', offeredVersion);
      } catch {
        /* abaikan */
      }
    }
  }, [offeredVersion]);
  if (!pendingUpdate) return null;
  return <UpdateDialog info={pendingUpdate} onDismiss={() => setPendingUpdate(null)} />;
};
