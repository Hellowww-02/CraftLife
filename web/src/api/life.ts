import { apiGet, apiPost } from './client';

export const life = {
  addSport: (body: Record<string, unknown>) => apiPost<any>('/api/sport', body),
  completeSport: (id: string) => apiPost<any>(`/api/sport/${id}/complete`, {}),
  sportReps: (id: string, reps: number, sets?: number) =>
    apiPost<any>(`/api/sport/${id}/reps`, { reps, sets: sets || 1 }),
  sportRepsInfo: (id: string) => apiGet<any>(`/api/sport/${id}/reps`),
  sportRepsSummary: () => apiGet<any>('/api/sport/reps'),
  deleteSport: (id: string) => apiPost<any>(`/api/sport/${id}/delete`, {}),
  updateSport: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/sport/${id}/update`, body),
  duplicateSport: (id: string) => apiPost<any>(`/api/sport/${id}/duplicate`, {}),
  dashboardSummary: () => apiGet<any>('/api/dashboard/summary'),
  profileTitles: () => apiGet<any>('/api/profile/titles'),
  selectTitle: (key: string) => apiPost<any>('/api/profile/title', { key }),
  removeProfilePhoto: () => apiPost<any>('/api/profile/photo/remove', {}),
  foodItems: () => apiGet<any>('/api/food/items'),
  addCustomFood: (body: Record<string, unknown>) => apiPost<any>('/api/food/custom', body),
  logFood: (body: Record<string, unknown>) => apiPost<any>('/api/food/log', body),
  deleteFoodLog: (id: string) => apiPost<any>(`/api/food/log/${id}/delete`, {}),
  nutritionGoals: () => apiGet<any>('/api/nutrition/goals'),
  saveNutritionGoals: (body: Record<string, unknown>) => apiPost<any>('/api/nutrition/goals', body),
  saveHealthGoals: (body: Record<string, unknown>) => apiPost<any>('/api/health/goals', body),
  listRecipes: () => apiGet<any>('/api/recipes'),
  addRecipe: (body: Record<string, unknown>) => apiPost<any>('/api/recipes', body),
  deleteRecipe: (id: string) => apiPost<any>(`/api/recipes/${id}/delete`, {}),
  logRecipe: (id: string, body: Record<string, unknown>) => apiPost<any>(`/api/recipes/${id}/log`, body),
  addWater: (amountMl: number, logDate?: string) =>
    apiPost<any>('/api/water', { amountMl, logDate }),
  deleteWaterLog: (id: string) => apiPost<any>('/api/water/log/delete', { id }),
  waterLogs: (date?: string) =>
    apiGet<any>(`/api/water/logs${date ? `?date=${date}` : ''}`),
  healthfoodDay: (date: string) => apiGet<any>(`/api/healthfood/day?date=${date}`),
  healthfoodHistory: () => apiGet<any>('/api/healthfood/history'),
  moveFoodLog: (id: string, mealType: string) =>
    apiPost<any>('/api/food/log/move', { id, mealType }),
  nutritionBonus: (logDate?: string) => apiPost<any>('/api/nutrition/bonus', { logDate }),
  autoNutritionGoals: (body: Record<string, unknown>) =>
    apiPost<any>('/api/nutrition/goals/auto', body),
  /** Input kesehatan versi penuh (parity HealthFoodPage._save_health). */
  saveHealthFull: (body: {
    steps: number; sleepHours: number; heartRate: number;
    weightKg?: number; heightCm?: number; mood: string; stress: string;
    notes: string; logDate?: string;
  }) => apiPost<any>('/api/health', body),
  resetWater: () => apiPost<any>('/api/water/reset', {}),
  setWaterGoal: (targetMl: number) => apiPost<any>('/api/water/goal', { targetMl }),
  addEconomy: (body: Record<string, unknown>) => apiPost<any>('/api/economy', body),
  deleteEconomy: (id: string) => apiPost<any>(`/api/economy/${id}/delete`, {}),
  moveEconomy: (id: string, folderId: string | null) =>
    apiPost<any>(`/api/economy/${id}/move`, { folderId }),
  updateEconomy: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/economy/${id}/update`, body),
  updateDebt: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/debts/${id}/update`, body),
  updateSubscription: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/subscriptions/${id}/update`, body),
  addDebt: (body: Record<string, unknown>) => apiPost<any>('/api/debts', body),
  payDebt: (id: string, amount: number) => apiPost<any>(`/api/debts/${id}/pay`, { amount }),
  deleteDebt: (id: string) => apiPost<any>(`/api/debts/${id}/delete`, {}),
  addNote: (body: Record<string, unknown>) => apiPost<any>('/api/notes', body),
  updateNote: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/notes/${id}/update`, body),
  deleteNote: (id: string) => apiPost<any>(`/api/notes/${id}/delete`, {}),
  addNoteFolder: (body: Record<string, unknown>) => apiPost<any>('/api/note-folders', body),
  deleteNoteFolder: (id: string) => apiPost<any>(`/api/note-folders/${id}/delete`, {}),
  updateNoteFolder: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/note-folders/${id}/update`, body),
  duplicateNoteFolder: (id: string) => apiPost<any>(`/api/note-folders/${id}/duplicate`, {}),
  previewMath: (content: string) => apiPost<any>('/api/notes/preview-math', { content }),
  mathChunks: (content: string) => apiPost<any>('/api/notes/math-chunks', { content }),
  archiveNote: (id: string, archived: boolean) => apiPost<any>(`/api/notes/${id}/archive`, { archived }),
  duplicateNote: (id: string, folderId?: string | null) =>
    apiPost<any>(`/api/notes/${id}/duplicate`, { folderId }),
  addReminder: (body: Record<string, unknown>) => apiPost<any>('/api/reminders', body),
  updateReminder: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/reminders/${id}/update`, body),
  toggleReminder: (id: string) => apiPost<any>(`/api/reminders/${id}/toggle`, {}),
  deleteReminder: (id: string) => apiPost<any>(`/api/reminders/${id}/delete`, {}),
  // Parity MainWindow._check_reminders: polling due → bunyikan loop → POST trigger
  dueReminders: () => apiGet<any>('/api/reminders/due'),
  triggerReminder: (id: string) => apiPost<any>(`/api/reminders/${id}/trigger`, {}),
  saveCalendarNote: (date: string, note: string) =>
    apiPost<any>('/api/calendar/note', { date, note }),
  deleteCalendarNote: (date: string) => apiPost<any>('/api/calendar/note/delete', { date }),
  addHealth: (body: Record<string, unknown>) => apiPost<any>('/api/health', body),
  getBmi: () => apiGet<any>('/api/health/bmi'),
  saveBmi: (body: Record<string, unknown>) => apiPost<any>('/api/health/bmi', body),
  completePomodoro: (durationMinutes: number, label: string) =>
    apiPost<any>('/api/pomodoro/complete', { durationMinutes, label }),
  addSaving: (body: Record<string, unknown>) => apiPost<any>('/api/savings', body),
  addToSaving: (id: string, amount: number) => apiPost<any>(`/api/savings/${id}/add`, { amount }),
  withdrawSaving: (id: string, amount: number) => apiPost<any>(`/api/savings/${id}/withdraw`, { amount }),
  deleteSaving: (id: string) => apiPost<any>(`/api/savings/${id}/delete`, {}),
  addInvestment: (body: Record<string, unknown>) => apiPost<any>('/api/investments', body),
  investmentReturn: (id: string, percent?: number) =>
    apiPost<any>(`/api/investments/${id}/return`, { percent: percent || 5 }),
  addInvestmentReturn: (id: string, amount: number) =>
    apiPost<any>(`/api/investments/${id}/add-return`, { amount }),
  deleteInvestment: (id: string) => apiPost<any>(`/api/investments/${id}/delete`, {}),
  withdrawInvestment: (id: string) => apiPost<any>(`/api/investments/${id}/withdraw`, {}),
  addSubscription: (body: Record<string, unknown>) => apiPost<any>('/api/subscriptions', body),
  renewSubscription: (id: string) => apiPost<any>(`/api/subscriptions/${id}/renew`, {}),
  deleteSubscription: (id: string) => apiPost<any>(`/api/subscriptions/${id}/delete`, {}),
  addDebtNote: (body: Record<string, unknown>) => apiPost<any>('/api/debt-notes', body),
  settleDebtNote: (id: string) => apiPost<any>(`/api/debt-notes/${id}/settle`, {}),
  deleteDebtNote: (id: string) => apiPost<any>(`/api/debt-notes/${id}/delete`, {}),
  applyTemplate: (mode: string, key: string) => apiPost<any>('/api/templates/apply', { mode, key }),
  listTemplates: (mode: string) => apiGet<any>(`/api/templates/${mode}`),
  addTaskFolder: (body: Record<string, unknown>) => apiPost<any>('/api/task-folders', body),
  updateTaskFolder: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/task-folders/${id}/update`, body),
  duplicateTaskFolder: (id: string, mode?: string) =>
    apiPost<any>(`/api/task-folders/${id}/duplicate`, { mode: mode || 'habit' }),
  deleteTaskFolder: (id: string, mode?: string) =>
    apiPost<any>(`/api/task-folders/${id}/delete`, { mode: mode || 'habit' }),
  listSupplies: (qs?: { search?: string; category?: string }) => {
    const q = [qs?.search ? `search=${encodeURIComponent(qs.search)}` : '', qs?.category ? `category=${encodeURIComponent(qs.category)}` : ''].filter(Boolean).join('&');
    return apiGet<any>(`/api/supplies${q ? `?${q}` : ''}`);
  },
  supplyHistory: (itemId?: string) =>
    apiGet<any>(`/api/supplies/history${itemId ? `?itemId=${itemId}` : ''}`),
  addSupply: (body: Record<string, unknown>) => apiPost<any>('/api/supplies', body),
  supplyTx: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/supplies/${id}/tx`, body),
  updateSupply: (id: string, body: Record<string, unknown>) =>
    apiPost<any>(`/api/supplies/${id}/update`, body),
  deleteSupply: (id: string) => apiPost<any>(`/api/supplies/${id}/delete`, {}),
};
