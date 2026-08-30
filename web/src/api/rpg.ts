import { apiGet, apiPost } from './client';

export const rpg = {
  bootstrap: () => apiGet<any>('/api/bootstrap'),
  completeHabit: (id: string, positive: boolean) =>
    apiPost<any>(`/api/habits/${id}/complete`, { positive }),
  addHabit: (body: Record<string, unknown>) => apiPost<any>('/api/habits', body),
  updateHabit: (id: string, body: Record<string, unknown>) => apiPost<any>(`/api/habits/${id}/update`, body),
  duplicateHabit: (id: string) => apiPost<any>(`/api/habits/${id}/duplicate`, {}),
  deleteHabit: (id: string) => apiPost<any>(`/api/habits/${id}/delete`, {}),
  completeDaily: (id: string) => apiPost<any>(`/api/dailies/${id}/complete`, {}),
  failDaily: (id: string) => apiPost<any>(`/api/dailies/${id}/fail`, {}),
  freezeDaily: (id: string) => apiPost<any>(`/api/dailies/${id}/freeze`, {}),
  addDaily: (body: Record<string, unknown>) => apiPost<any>('/api/dailies', body),
  updateDaily: (id: string, body: Record<string, unknown>) => apiPost<any>(`/api/dailies/${id}/update`, body),
  duplicateDaily: (id: string) => apiPost<any>(`/api/dailies/${id}/duplicate`, {}),
  deleteDaily: (id: string) => apiPost<any>(`/api/dailies/${id}/delete`, {}),
  completeQuest: (id: string) => apiPost<any>(`/api/todos/${id}/complete`, {}),
  addQuest: (body: Record<string, unknown>) => apiPost<any>('/api/todos', body),
  updateQuest: (id: string, body: Record<string, unknown>) => apiPost<any>(`/api/todos/${id}/update`, body),
  duplicateQuest: (id: string) => apiPost<any>(`/api/todos/${id}/duplicate`, {}),
  deleteQuest: (id: string) => apiPost<any>(`/api/todos/${id}/delete`, {}),
  buyItem: (itemId: string, idempotencyKey?: string) =>
    apiPost<any>('/api/shop/buy', { itemId, idempotencyKey: idempotencyKey || crypto.randomUUID() }),
  sellItem: (itemId: string, quantity: number = 1) =>
    apiPost<any>('/api/shop/sell', { itemId, quantity }),
  useItem: (itemId: string) => apiPost<any>('/api/shop/use', { itemId }),
  equipItem: (itemId: string, equipped: boolean) =>
    apiPost<any>('/api/shop/equip', { itemId, equipped }),
  craftItem: (recipeId: string, idempotencyKey?: string) =>
    apiPost<any>('/api/shop/craft', { recipeId, idempotencyKey: idempotencyKey || crypto.randomUUID() }),
  enchantItem: (itemId: string, idempotencyKey?: string) =>
    apiPost<any>('/api/shop/enchant', { itemId, idempotencyKey: idempotencyKey || crypto.randomUUID() }),
  adoptPet: (petId: string) => apiPost<any>('/api/pets/adopt', { petId }),
  feedPet: (petId: string) => apiPost<any>('/api/pets/feed', { petId }),
  trainPet: (petId: string) => apiPost<any>('/api/pets/train', { petId }),
  equipPet: (petId: string) => apiPost<any>('/api/pets/equip', { petId }),
  unequipPet: (petId: string) => apiPost<any>('/api/pets/unequip', { petId }),
  startBoss: (bossId: string) => apiPost<any>('/api/boss/start', { bossId }),
  attackBoss: (action: string) => apiPost<any>('/api/boss/attack', { action }),
  fleeBoss: () => apiPost<any>('/api/boss/flee', {}),
  useClassSkill: () => apiPost<any>('/api/skill/use', {}),
  claimAchievement: (id: string) => apiPost<any>(`/api/achievements/${id}/claim`, {}),
  // ── Phase P1: drag & drop reorder + trash restore ──
  reorderTasks: (mode: 'habit' | 'daily' | 'todo' | 'quest', items: { id: string; folderId?: string | null }[]) =>
    apiPost<any>('/api/tasks/reorder', { mode, items }),
  restoreTask: (trashId: string) =>
    apiPost<any>('/api/trash/restore', { trashId }),
  // ── Phase P5: dashboard widgets + year wrapped ──
  getDashboardWidgets: () => apiGet<any>('/api/dashboard/widgets'),
  saveDashboardWidgets: (widgets: Record<string, unknown>[]) =>
    apiPost<any>('/api/dashboard/widgets', { widgets }),
  yearWrapped: () => apiGet<any>('/api/year-wrapped'),
  // ── Phase P6: notes drag & drop reorder ──
  reorderNotes: (items: { id: string | number; folderId?: string | number | null }[]) =>
    apiPost<any>('/api/notes/reorder', { items }),
};
